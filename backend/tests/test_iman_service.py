"""
Unit tests for the Iman Index computation engine.

Tests Steps 1-8 of the algorithm: normalization, aggregation,
baselines, pillars, composite, trajectory state.
"""

import math
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.iman_service import (
    validate_behavior_value,
    validate_heart_note,
    validate_heart_state,
    build_default_config,
    get_tracked_behavior_ids,
    normalize_behavior_value,
    aggregate_category_scores,
    compute_baselines,
    compute_category_pillars,
    compute_composite_index,
    sigmoid_normalize,
    compute_trajectory_state,
    recompute_trajectory,
    _pearson_r,
    _linear_regression_slope,
    _median,
    _mad,
    CALIBRATION_DAYS,
)
from data.iman_behaviors import (
    IMAN_BEHAVIORS,
    IMAN_CATEGORIES,
    BEHAVIOR_MAP,
    DEFAULT_BEHAVIORS,
    ALL_BEHAVIOR_IDS,
    BASE_WEIGHTS,
    HEART_NOTE_TYPES,
    HEART_STATES,
)


# ─── Validation ──────────────────────────────────────────────────────────

class TestValidateBehaviorValue:
    def test_binary_valid(self):
        ok, err, val = validate_behavior_value("fajr_prayer", 1)
        assert ok is True
        assert val == 1

    def test_binary_zero(self):
        ok, err, val = validate_behavior_value("fajr_prayer", 0)
        assert ok is True
        assert val == 0

    def test_binary_invalid(self):
        ok, err, val = validate_behavior_value("fajr_prayer", 2)
        assert ok is False

    def test_scale_5_valid(self):
        ok, err, val = validate_behavior_value("avoided_sins", 3)
        assert ok is True
        assert val == 3

    def test_scale_5_out_of_range(self):
        ok, err, val = validate_behavior_value("avoided_sins", 6)
        assert ok is False

    def test_minutes_valid(self):
        ok, err, val = validate_behavior_value("quran_minutes", 15.5)
        assert ok is True
        assert val == 15.5

    def test_minutes_negative(self):
        ok, err, val = validate_behavior_value("quran_minutes", -1)
        assert ok is False

    def test_hours_valid(self):
        ok, err, val = validate_behavior_value("sleep_hours", 7.5)
        assert ok is True
        assert val == 7.5

    def test_hours_out_of_range(self):
        ok, err, val = validate_behavior_value("sleep_hours", 25)
        assert ok is False

    def test_count_valid(self):
        ok, err, val = validate_behavior_value("sunnah_prayers", 4)
        assert ok is True
        assert val == 4

    def test_unknown_behavior(self):
        ok, err, val = validate_behavior_value("nonexistent_xyz", 1)
        assert ok is False
        assert "Unknown" in err

    def test_invalid_type(self):
        ok, err, val = validate_behavior_value("fajr_prayer", "abc")
        assert ok is False


class TestValidateHeartNote:
    def test_valid_note(self):
        ok, err = validate_heart_note("gratitude", "Alhamdulillah for this day")
        assert ok is True

    def test_invalid_type(self):
        ok, err = validate_heart_note("invalid_type", "some text")
        assert ok is False

    def test_empty_text(self):
        ok, err = validate_heart_note("gratitude", "")
        assert ok is False

    def test_too_long(self):
        ok, err = validate_heart_note("gratitude", "x" * 281)
        assert ok is False

    def test_max_length(self):
        ok, err = validate_heart_note("dua", "x" * 280)
        assert ok is True


class TestValidateHeartState:
    def test_valid_states(self):
        for state in HEART_STATES:
            ok, err = validate_heart_state(state)
            assert ok is True, f"State {state} should be valid"

    def test_invalid_state(self):
        ok, err = validate_heart_state("happy")
        assert ok is False


# ─── Config / Setup ──────────────────────────────────────────────────────

class TestBuildDefaultConfig:
    def test_default_behaviors(self):
        config = build_default_config()
        tracked = config["tracked_behaviors"]
        assert len(tracked) == len(DEFAULT_BEHAVIORS)
        assert config["baseline_established"] is False
        assert config["engine_version"] == "1.0"

    def test_custom_behaviors(self):
        config = build_default_config(["fajr_prayer", "quran_minutes"])
        tracked = config["tracked_behaviors"]
        assert len(tracked) == 2
        ids = {b["id"] for b in tracked}
        assert ids == {"fajr_prayer", "quran_minutes"}

    def test_invalid_behavior_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            build_default_config(["fajr_prayer", "fake_behavior"])

    def test_tracked_ids_extraction(self):
        config = build_default_config(["fajr_prayer", "dhuhr_prayer", "quran_minutes"])
        ids = get_tracked_behavior_ids(config)
        assert set(ids) == {"fajr_prayer", "dhuhr_prayer", "quran_minutes"}


# ─── Step 1: Normalization ───────────────────────────────────────────────

class TestNormalizeBehavior:
    def test_binary_on(self):
        assert normalize_behavior_value("fajr_prayer", 1) == 1.0

    def test_binary_off(self):
        assert normalize_behavior_value("fajr_prayer", 0) == 0.0

    def test_scale_5_midpoint(self):
        result = normalize_behavior_value("avoided_sins", 3)
        assert abs(result - 0.6) < 0.001

    def test_scale_5_max(self):
        result = normalize_behavior_value("avoided_sins", 5)
        assert abs(result - 1.0) < 0.001

    def test_scale_5_zero(self):
        result = normalize_behavior_value("avoided_sins", 0)
        assert abs(result - 0.0) < 0.001

    def test_minutes_with_p95(self):
        result = normalize_behavior_value("quran_minutes", 20, p95=40.0)
        assert abs(result - 0.5) < 0.001

    def test_minutes_capped_at_1(self):
        result = normalize_behavior_value("quran_minutes", 60, p95=30.0)
        assert result == 1.0

    def test_minutes_default_p95(self):
        result = normalize_behavior_value("quran_minutes", 15)
        assert 0 < result <= 1.0

    def test_hours_optimal_sleep(self):
        """7.5 hours = optimal → should normalize to ~1.0"""
        result = normalize_behavior_value("sleep_hours", 7.5)
        assert abs(result - 1.0) < 0.01

    def test_hours_poor_sleep(self):
        """4 hours → well below optimal, should be low"""
        result = normalize_behavior_value("sleep_hours", 4)
        assert result < 0.15

    def test_hours_oversleep(self):
        """11 hours → oversleep, also penalized by Gaussian"""
        result = normalize_behavior_value("sleep_hours", 11)
        assert result < 0.15

    def test_count_normal(self):
        result = normalize_behavior_value("sunnah_prayers", 5, p95=10)
        assert abs(result - 0.5) < 0.001

    def test_unknown_behavior_returns_zero(self):
        result = normalize_behavior_value("nonexistent", 5)
        assert result == 0.0

    def test_invalid_value_returns_zero(self):
        result = normalize_behavior_value("fajr_prayer", "abc")
        assert result == 0.0


# ─── Step 2: Category Aggregation ────────────────────────────────────────

class TestAggregateCategoryScores:
    def test_all_fard_perfect(self):
        """All five prayers done → fard category should be 1.0"""
        behaviors = {
            "fajr_prayer": 1,
            "dhuhr_prayer": 1,
            "asr_prayer": 1,
            "maghrib_prayer": 1,
            "isha_prayer": 1,
        }
        tracked = list(behaviors.keys())
        result = aggregate_category_scores(behaviors, tracked)
        assert abs(result["fard"] - 1.0) < 0.001

    def test_partial_fard(self):
        """3 of 5 prayers done → fard = 0.6"""
        behaviors = {
            "fajr_prayer": 1,
            "dhuhr_prayer": 1,
            "asr_prayer": 1,
        }
        tracked = ["fajr_prayer", "dhuhr_prayer", "asr_prayer", "maghrib_prayer", "isha_prayer"]
        result = aggregate_category_scores(behaviors, tracked)
        assert abs(result["fard"] - 0.6) < 0.001

    def test_missing_data_counted_as_zero(self):
        """Unlogged binary behaviors count as 0"""
        behaviors = {}
        tracked = ["fajr_prayer"]
        result = aggregate_category_scores(behaviors, tracked)
        assert result["fard"] == 0.0

    def test_hours_excluded_when_missing(self):
        """Sleep not logged → hours should be excluded, not counted as 0"""
        behaviors = {}
        tracked = ["sleep_hours"]
        result = aggregate_category_scores(behaviors, tracked)
        # sleep is excluded (not penalized), so stewardship has no values → 0.0
        assert result["stewardship"] == 0.0

    def test_mixed_categories(self):
        behaviors = {
            "fajr_prayer": 1,
            "quran_minutes": {"value": 20},
            "gratitude_entry": 1,
        }
        tracked = ["fajr_prayer", "quran_minutes", "gratitude_entry"]
        result = aggregate_category_scores(behaviors, tracked)
        assert result["fard"] > 0
        assert result["quran"] > 0
        assert result["character"] > 0

    def test_dict_value_extraction(self):
        """Behavior values can be {value: X, logged_at: ...} dicts"""
        behaviors = {"fajr_prayer": {"value": 1, "logged_at": "2025-01-01"}}
        tracked = ["fajr_prayer"]
        result = aggregate_category_scores(behaviors, tracked)
        assert abs(result["fard"] - 1.0) < 0.001


# ─── Step 3: Baselines ──────────────────────────────────────────────────

class TestComputeBaselines:
    def _make_scores(self, fard_vals):
        """Helper: make daily_category_scores with given fard values."""
        return [{"fard": v, "tawbah": 0.5, "quran": 0.5, "nafl": 0.5,
                 "character": 0.5, "stewardship": 0.5} for v in fard_vals]

    def test_fresh_baselines(self):
        scores = self._make_scores([0.6, 0.7, 0.8, 0.6, 0.7, 0.8,
                                     0.6, 0.7, 0.8, 0.6, 0.7, 0.8,
                                     0.6, 0.7])
        baselines = compute_baselines(scores)
        assert "fard" in baselines
        assert "last_recalibration" in baselines
        # Median of [0.6,0.7,0.8,...] should be ~0.7
        assert 0.6 <= baselines["fard"]["median"] <= 0.8

    def test_ema_recalibration(self):
        """EMA: 0.7 * old + 0.3 * new"""
        existing = {
            "fard": {"median": 0.5, "mean": 0.5, "std_dev": 0.1,
                     "mad": 0.1, "p95": 0.8, "sample_size": 14},
        }
        new_scores = self._make_scores([0.9] * 14)
        baselines = compute_baselines(new_scores, existing)
        # New median for fard = 0.9
        # EMA: 0.7 * 0.5 + 0.3 * 0.9 = 0.35 + 0.27 = 0.62
        assert abs(baselines["fard"]["median"] - 0.62) < 0.01

    def test_all_categories_present(self):
        scores = self._make_scores([0.5] * 14)
        baselines = compute_baselines(scores)
        for cat in IMAN_CATEGORIES:
            assert cat in baselines


# ─── Helper Functions ────────────────────────────────────────────────────

class TestHelpers:
    def test_median_odd(self):
        assert _median([1, 3, 5]) == 3

    def test_median_even(self):
        assert _median([1, 3, 5, 7]) == 4.0

    def test_median_empty(self):
        assert _median([]) == 0.0

    def test_mad_stable(self):
        """All same values → MAD should be at floor (0.05)"""
        result = _mad([0.5, 0.5, 0.5, 0.5, 0.5])
        assert result == 0.05

    def test_mad_varying(self):
        result = _mad([0.1, 0.5, 0.9, 0.5, 0.1])
        assert result > 0.05

    def test_pearson_r_perfect_positive(self):
        r = _pearson_r([1, 2, 3, 4], [1, 2, 3, 4])
        assert abs(r - 1.0) < 0.001

    def test_pearson_r_perfect_negative(self):
        r = _pearson_r([1, 2, 3, 4], [4, 3, 2, 1])
        assert abs(r - (-1.0)) < 0.001

    def test_pearson_r_insufficient_data(self):
        r = _pearson_r([1, 2], [3, 4])
        assert r == 0.0

    def test_linear_regression_slope_ascending(self):
        slope = _linear_regression_slope([1, 2, 3, 4, 5])
        assert abs(slope - 1.0) < 0.001

    def test_linear_regression_slope_flat(self):
        slope = _linear_regression_slope([5, 5, 5, 5])
        assert abs(slope) < 0.001

    def test_linear_regression_slope_descending(self):
        slope = _linear_regression_slope([5, 4, 3, 2, 1])
        assert slope < 0


# ─── Steps 4-5: Category Pillars ─────────────────────────────────────────

class TestCategoryPillars:
    def test_perfect_performance(self):
        """Consistently above baseline → high performance pillar"""
        scores_7d = [0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9]
        scores_14d = [0.8] * 7 + [0.9] * 7
        result = compute_category_pillars(scores_7d, scores_14d, baseline_median=0.5, baseline_mad=0.1)
        assert result["performance"] > 0.5
        assert result["consistency"] > 0.5

    def test_below_baseline(self):
        """Below baseline → negative performance"""
        scores_7d = [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]
        scores_14d = [0.2] * 14
        result = compute_category_pillars(scores_7d, scores_14d, baseline_median=0.7, baseline_mad=0.1)
        assert result["performance"] < 0

    def test_high_consistency_low_variance(self):
        """Very stable values → high consistency"""
        scores_7d = [0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7]
        scores_14d = [0.7] * 14
        result = compute_category_pillars(scores_7d, scores_14d, baseline_median=0.7, baseline_mad=0.1)
        assert result["consistency"] > 0.9

    def test_low_consistency_high_variance(self):
        """Wild swings → low consistency"""
        scores_7d = [0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1]
        scores_14d = [0.1, 0.9] * 7
        result = compute_category_pillars(scores_7d, scores_14d, baseline_median=0.5, baseline_mad=0.1)
        assert result["consistency"] < 0.5

    def test_ascending_trajectory(self):
        """Improving over 14 days → positive trajectory"""
        scores_14d = [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6,
                      0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
        scores_7d = scores_14d[-7:]
        result = compute_category_pillars(scores_7d, scores_14d, baseline_median=0.5, baseline_mad=0.1)
        assert result["trajectory"] > 0.9

    def test_composite_formula(self):
        """Composite = 0.25*P + 0.45*K + 0.30*T"""
        scores_7d = [0.7] * 7
        scores_14d = [0.7] * 14
        result = compute_category_pillars(scores_7d, scores_14d, baseline_median=0.5, baseline_mad=0.1)
        expected = 0.25 * result["performance"] + 0.45 * result["consistency"] + 0.30 * result["trajectory"]
        assert abs(result["composite"] - expected) < 0.01

    def test_zero_activity_no_consistency_reward(self):
        """Doing nothing consistently should NOT reward consistency"""
        scores_7d = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        scores_14d = [0.0] * 14
        result = compute_category_pillars(scores_7d, scores_14d, baseline_median=0.5, baseline_mad=0.1)
        assert result["consistency"] == 0.0


# ─── Steps 5-7: Composite Index & Sigmoid ────────────────────────────────

class TestCompositeIndex:
    def test_weighted_sum(self):
        composites = {cat: 1.0 for cat in IMAN_CATEGORIES}
        result = compute_composite_index(composites)
        # Sum of all weights = 1.0
        assert abs(result - 1.0) < 0.001

    def test_zero_composites(self):
        composites = {cat: 0.0 for cat in IMAN_CATEGORIES}
        result = compute_composite_index(composites)
        assert abs(result) < 0.001

    def test_weight_priority(self):
        """fard (0.30) should outweigh stewardship (0.08)"""
        composites_fard = {cat: 0.0 for cat in IMAN_CATEGORIES}
        composites_fard["fard"] = 1.0

        composites_stew = {cat: 0.0 for cat in IMAN_CATEGORIES}
        composites_stew["stewardship"] = 1.0

        assert compute_composite_index(composites_fard) > compute_composite_index(composites_stew)

    def test_sigmoid_midpoint(self):
        """sigmoid(0) = 50"""
        assert abs(sigmoid_normalize(0.0) - 50.0) < 0.01

    def test_sigmoid_positive(self):
        """Positive input → above 50"""
        assert sigmoid_normalize(0.5) > 50

    def test_sigmoid_negative(self):
        """Negative input → below 50"""
        assert sigmoid_normalize(-0.5) < 50

    def test_sigmoid_bounded(self):
        """Always between 0 and 100"""
        assert 0 < sigmoid_normalize(-10) < 100
        assert 0 < sigmoid_normalize(10) < 100


# ─── Step 8: Trajectory State ────────────────────────────────────────────

class TestTrajectoryState:
    def test_calibrating_insufficient_data(self):
        result = compute_trajectory_state([0.5, 0.6])
        assert result["current_state"] == "calibrating"

    def test_ascending(self):
        values = [i * 0.4 for i in range(14)]  # steep upward (slope=0.4)
        result = compute_trajectory_state(values)
        assert result["current_state"] == "ascending"

    def test_steady(self):
        values = [0.5] * 14  # flat
        result = compute_trajectory_state(values)
        assert result["current_state"] == "steady"

    def test_recalibrating(self):
        values = [2.0 - i * 0.15 for i in range(14)]  # downward (slope=-0.15)
        result = compute_trajectory_state(values)
        assert result["current_state"] == "recalibrating"

    def test_never_says_declining(self):
        """We NEVER use 'declining' — always 'recalibrating'"""
        values = [0.9 - i * 0.06 for i in range(14)]
        result = compute_trajectory_state(values)
        assert "declin" not in result["current_state"].lower()
        assert "declin" not in result["composite_display"].lower()

    def test_stable_volatility(self):
        values = [0.5] * 14  # very stable
        result = compute_trajectory_state(values)
        assert result["volatility_state"] == "stable"

    def test_turbulent_volatility(self):
        values = [0.1, 0.9, 0.2, 0.8, 0.1, 0.9, 0.2,
                  0.8, 0.1, 0.9, 0.2, 0.8, 0.1, 0.9]
        result = compute_trajectory_state(values)
        assert result["volatility_state"] == "turbulent"

    def test_display_format(self):
        values = [0.5] * 14
        result = compute_trajectory_state(values)
        assert " & " in result["composite_display"]
        assert "color" in result


# ─── Full Pipeline ───────────────────────────────────────────────────────

class TestRecomputeTrajectory:
    def _make_log(self, date_str, prayer_val=1, quran_val=15):
        return {
            "date": date_str,
            "behaviors": {
                "fajr_prayer": prayer_val,
                "dhuhr_prayer": prayer_val,
                "asr_prayer": prayer_val,
                "maghrib_prayer": prayer_val,
                "isha_prayer": prayer_val,
                "avoided_sins": 4,
                "tawbah_moment": 1,
                "quran_minutes": quran_val,
                "tadabbur_session": 1,
                "sunnah_prayers": 4,
                "dhikr_minutes": 10,
                "dua_moments": 3,
                "gratitude_entry": 1,
                "sleep_hours": 7.5,
            }
        }

    def test_calibrating_phase(self):
        """Fewer than 14 days → calibrating state"""
        config = build_default_config()
        logs = [self._make_log(f"2025-01-{i+1:02d}") for i in range(5)]
        traj, baselines = recompute_trajectory(logs, config)
        assert traj["current_state"] == "calibrating"
        assert traj["baseline_established"] is False
        assert traj["calibration_days_remaining"] == 9
        assert baselines is None

    def test_baseline_establishment(self):
        """Exactly 14 days → baselines computed"""
        config = build_default_config()
        logs = [self._make_log(f"2025-01-{i+1:02d}") for i in range(14)]
        traj, baselines = recompute_trajectory(logs, config)
        assert traj["baseline_established"] is True
        assert baselines is not None
        assert "fard" in baselines

    def test_post_baseline_trajectory(self):
        """After baseline, trajectory doc includes pillars and scores"""
        config = build_default_config()
        config["baseline_established"] = True
        logs = [self._make_log(f"2025-01-{i+1:02d}") for i in range(20)]

        # Provide existing baselines
        baselines = compute_baselines(
            [aggregate_category_scores(l["behaviors"], get_tracked_behavior_ids(config))
             for l in logs[:14]]
        )

        traj, new_bl = recompute_trajectory(logs, config, baselines)
        assert traj["baseline_established"] is True
        assert "category_scores" in traj
        assert "fard" in traj["category_scores"]
        assert "performance" in traj["category_scores"]["fard"]
        assert "daily_scores" in traj
        assert "growth_edges" in traj
        assert len(traj["growth_edges"]) == 2

    def test_pipeline_returns_daily_scores(self):
        config = build_default_config()
        config["baseline_established"] = True
        logs = [self._make_log(f"2025-01-{i+1:02d}") for i in range(20)]

        baselines = compute_baselines(
            [aggregate_category_scores(l["behaviors"], get_tracked_behavior_ids(config))
             for l in logs[:14]]
        )

        traj, _ = recompute_trajectory(logs, config, baselines)
        assert len(traj["daily_scores"]) <= 90
        assert all("date" in d and "composite" in d for d in traj["daily_scores"])


# ─── Data Integrity ──────────────────────────────────────────────────────

class TestDataIntegrity:
    def test_39_behaviors(self):
        assert len(IMAN_BEHAVIORS) == 39

    def test_14_defaults(self):
        assert len(DEFAULT_BEHAVIORS) == 14

    def test_6_categories(self):
        assert len(IMAN_CATEGORIES) == 6

    def test_weights_sum_to_one(self):
        total = sum(BASE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_behaviors_have_valid_category(self):
        for b in IMAN_BEHAVIORS:
            assert b["category"] in IMAN_CATEGORIES, f"{b['id']} has invalid category"

    def test_all_behavior_ids_unique(self):
        ids = [b["id"] for b in IMAN_BEHAVIORS]
        assert len(ids) == len(set(ids))

    def test_valid_input_types(self):
        valid_types = {"binary", "scale_5", "minutes", "hours", "count", "count_inv"}
        for b in IMAN_BEHAVIORS:
            assert b["input_type"] in valid_types, f"{b['id']} has invalid input_type"

    def test_heart_note_types_nonempty(self):
        assert len(HEART_NOTE_TYPES) >= 3

    def test_heart_states_nonempty(self):
        assert len(HEART_STATES) >= 3
