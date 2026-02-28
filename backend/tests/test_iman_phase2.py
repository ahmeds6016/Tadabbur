"""
Unit tests for Iman Index Phase 2: Intelligence Layer.

Tests: safeguards, correlations, struggle catalog & progress,
digest context builder, digest prompt builder.
"""

import math
import pytest
import sys
import os
from unittest.mock import patch

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.iman_service import (
    check_behavior_cap,
    should_show_anti_riya_reminder,
    get_recalibrating_comfort,
    get_welcome_back_message,
    compute_behavior_correlations,
    select_weekly_insight,
    compute_struggle_progress,
    prepare_digest_context,
    build_digest_prompt,
    MAX_TRACKED_BEHAVIORS,
    MIN_CORRELATION_DATA_POINTS,
    MIN_CORRELATION_THRESHOLD,
    STRUGGLE_PHASE_WEEKS,
    _pearson_r,
)
from data.iman_behaviors import ALL_BEHAVIOR_IDS, BEHAVIOR_MAP
from data.iman_struggles import (
    STRUGGLE_CATALOG,
    STRUGGLE_MAP,
    ALL_STRUGGLE_IDS,
)


# ==========================================================================
# Safeguards
# ==========================================================================

class TestBehaviorCap:
    def test_under_cap_passes(self):
        ok, msg = check_behavior_cap(["a", "b", "c"])
        assert ok is True
        assert msg == ""

    def test_at_cap_passes(self):
        ids = [f"b{i}" for i in range(MAX_TRACKED_BEHAVIORS)]
        ok, msg = check_behavior_cap(ids)
        assert ok is True

    def test_over_cap_fails(self):
        ids = [f"b{i}" for i in range(MAX_TRACKED_BEHAVIORS + 1)]
        ok, msg = check_behavior_cap(ids)
        assert ok is False
        assert "Maximum" in msg
        assert str(MAX_TRACKED_BEHAVIORS) in msg

    def test_empty_passes(self):
        ok, msg = check_behavior_cap([])
        assert ok is True


class TestAntiRiya:
    def test_returns_bool(self):
        result = should_show_anti_riya_reminder()
        assert isinstance(result, bool)

    def test_probability_range(self):
        """Over many calls, should return True roughly 10% of the time."""
        results = [should_show_anti_riya_reminder() for _ in range(1000)]
        true_rate = sum(results) / len(results)
        assert 0.03 < true_rate < 0.20  # Wide range for randomness


class TestRecalibratingComfort:
    def test_under_14_days_returns_none(self):
        assert get_recalibrating_comfort(0) is None
        assert get_recalibrating_comfort(7) is None
        assert get_recalibrating_comfort(13) is None

    def test_at_14_days_returns_comfort(self):
        result = get_recalibrating_comfort(14)
        assert result is not None
        assert result["hide_trajectory"] is True
        assert "comfort_verse" in result
        assert "surah" in result["comfort_verse"]
        assert "text" in result["comfort_verse"]
        assert "message" in result

    def test_at_30_days_returns_comfort(self):
        result = get_recalibrating_comfort(30)
        assert result is not None
        assert result["hide_trajectory"] is True

    def test_verse_is_valid(self):
        result = get_recalibrating_comfort(15)
        verse = result["comfort_verse"]
        assert isinstance(verse["surah"], int)
        assert isinstance(verse["verse"], int)
        assert len(verse["text"]) > 10


class TestWelcomeBack:
    def test_less_than_2_days_returns_none(self):
        assert get_welcome_back_message(0) is None
        assert get_welcome_back_message(1) is None

    def test_short_absence(self):
        msg = get_welcome_back_message(3)
        assert msg is not None
        assert isinstance(msg, str)
        assert len(msg) > 5

    def test_medium_absence(self):
        msg = get_welcome_back_message(10)
        assert msg is not None

    def test_long_absence(self):
        msg = get_welcome_back_message(45)
        assert msg is not None
        assert "Alhamdulillah" in msg


# ==========================================================================
# Correlation Detection
# ==========================================================================

class TestBehaviorCorrelations:
    def _make_logs_with_correlation(self, bid_a, bid_b, r_target, n=30):
        """Generate synthetic daily logs with a target correlation between two behaviors.

        Uses continuous-type behaviors (minutes) for meaningful normalization.
        """
        import random
        random.seed(42)

        logs = []
        for i in range(n):
            base = 10 + random.random() * 50  # 10-60 range for minutes
            noise_a = random.gauss(0, 3)
            noise_b = random.gauss(0, 3)

            val_a = max(1, base + noise_a)
            if r_target > 0:
                val_b = max(1, base + noise_b)
            else:
                val_b = max(1, (70 - base) + noise_b)

            logs.append({
                "date": f"2026-02-{i + 1:02d}",
                "behaviors": {bid_a: val_a, bid_b: val_b},
            })
        return logs

    def test_strong_positive_detected(self):
        # Use minutes-type behaviors for meaningful float normalization
        logs = self._make_logs_with_correlation("quran_minutes", "dhikr_minutes", 0.8)
        results = compute_behavior_correlations(logs, ["quran_minutes", "dhikr_minutes"], window_days=30)
        assert len(results) >= 1
        assert results[0]["r"] > MIN_CORRELATION_THRESHOLD

    def test_weak_correlation_excluded(self):
        """Build two behaviors with near-zero correlation."""
        import random
        random.seed(99)
        logs = []
        for i in range(30):
            logs.append({
                "date": f"2026-02-{i + 1:02d}",
                "behaviors": {
                    "quran_minutes": random.randint(5, 60),
                    "sleep_hours": random.randint(4, 10),
                },
            })
        results = compute_behavior_correlations(logs, ["quran_minutes", "sleep_hours"], window_days=30)
        # Weak correlations should be filtered out
        for r in results:
            assert abs(r["r"]) >= MIN_CORRELATION_THRESHOLD

    def test_insufficient_data_returns_empty(self):
        logs = [
            {"date": "2026-02-01", "behaviors": {"quran_minutes": 15}},
            {"date": "2026-02-02", "behaviors": {"quran_minutes": 20}},
        ]
        results = compute_behavior_correlations(logs, ["quran_minutes", "dhikr_minutes"], window_days=30)
        assert results == []

    def test_insight_text_generated(self):
        logs = self._make_logs_with_correlation("quran_minutes", "dhikr_minutes", 0.8)
        results = compute_behavior_correlations(logs, ["quran_minutes", "dhikr_minutes"], window_days=30)
        if results:
            assert "insight_text" in results[0]
            assert len(results[0]["insight_text"]) > 10

    def test_result_structure(self):
        logs = self._make_logs_with_correlation("quran_minutes", "dhikr_minutes", 0.8)
        results = compute_behavior_correlations(logs, ["quran_minutes", "dhikr_minutes"], window_days=30)
        if results:
            r = results[0]
            assert "behavior_a" in r
            assert "behavior_b" in r
            assert "r" in r
            assert "insight_text" in r
            assert "direction" in r


class TestSelectWeeklyInsight:
    def test_picks_first_unseen(self):
        correlations = [
            {"behavior_a": "a", "behavior_b": "b", "insight_text": "first", "r": 0.8, "direction": "positive", "data_points": 20},
            {"behavior_a": "c", "behavior_b": "d", "insight_text": "second", "r": 0.6, "direction": "positive", "data_points": 18},
        ]
        result = select_weekly_insight(correlations, ["a|b"])
        assert result is not None
        assert result["behavior_a"] == "c"

    def test_returns_none_when_all_shown(self):
        correlations = [
            {"behavior_a": "a", "behavior_b": "b", "insight_text": "first", "r": 0.8, "direction": "positive", "data_points": 20},
        ]
        result = select_weekly_insight(correlations, ["a|b"])
        assert result is None

    def test_returns_first_when_none_shown(self):
        correlations = [
            {"behavior_a": "x", "behavior_b": "y", "insight_text": "hello", "r": 0.7, "direction": "positive", "data_points": 15},
        ]
        result = select_weekly_insight(correlations, [])
        assert result is not None
        assert result["behavior_a"] == "x"

    def test_empty_correlations(self):
        result = select_weekly_insight([], [])
        assert result is None


# ==========================================================================
# Struggle Catalog
# ==========================================================================

class TestStruggleCatalog:
    def test_has_10_struggles(self):
        assert len(STRUGGLE_CATALOG) == 10

    def test_all_ids_unique(self):
        assert len(ALL_STRUGGLE_IDS) == len(set(ALL_STRUGGLE_IDS))

    def test_map_has_all(self):
        assert len(STRUGGLE_MAP) == 10
        for sid in ALL_STRUGGLE_IDS:
            assert sid in STRUGGLE_MAP

    def test_each_has_required_fields(self):
        required = ["id", "label", "description", "icon", "color",
                     "scholarly_pointers", "comfort_verses", "linked_behaviors", "phases"]
        for s in STRUGGLE_CATALOG:
            for field in required:
                assert field in s, f"Missing {field} in {s['id']}"

    def test_each_has_4_phases(self):
        for s in STRUGGLE_CATALOG:
            assert len(s["phases"]) == 4, f"{s['id']} has {len(s['phases'])} phases, expected 4"

    def test_scholarly_pointer_format(self):
        """All pointers should match source:key=value format."""
        import re
        pattern = re.compile(r"^(ihya|madarij|riyad):.+=.+$")
        for s in STRUGGLE_CATALOG:
            for pointer in s["scholarly_pointers"]:
                assert pattern.match(pointer), f"Invalid pointer format: {pointer} in {s['id']}"

    def test_linked_behaviors_are_valid(self):
        for s in STRUGGLE_CATALOG:
            for bid in s["linked_behaviors"]:
                assert bid in ALL_BEHAVIOR_IDS, f"Invalid behavior {bid} in {s['id']}"

    def test_comfort_verses_have_required_fields(self):
        for s in STRUGGLE_CATALOG:
            assert len(s["comfort_verses"]) >= 1, f"{s['id']} has no comfort verses"
            for v in s["comfort_verses"]:
                assert "surah" in v
                assert "verse" in v
                assert "text" in v
                assert isinstance(v["surah"], int)
                assert isinstance(v["verse"], int)
                assert len(v["text"]) > 10


# ==========================================================================
# Struggle Progress
# ==========================================================================

class TestStruggleProgress:
    def test_week_0_phase_0(self):
        config = STRUGGLE_MAP["prayer_consistency"]
        progress = compute_struggle_progress(
            "prayer_consistency",
            "2026-02-27T00:00:00Z",
            [],
            config,
        )
        assert progress["current_phase"] == 0
        assert progress["weeks_active"] == 0

    def test_week_1_phase_1(self):
        config = STRUGGLE_MAP["anger_management"]
        # 10 days ago
        from datetime import datetime, timedelta
        declared = (datetime.utcnow() - timedelta(days=10)).isoformat() + "Z"
        progress = compute_struggle_progress(
            "anger_management", declared, [], config,
        )
        assert progress["current_phase"] == 1
        assert progress["weeks_active"] == 1

    def test_week_4_caps_at_phase_3(self):
        config = STRUGGLE_MAP["quran_disconnection"]
        from datetime import datetime, timedelta
        declared = (datetime.utcnow() - timedelta(days=35)).isoformat() + "Z"
        progress = compute_struggle_progress(
            "quran_disconnection", declared, [], config,
        )
        assert progress["current_phase"] == 3

    def test_linked_behavior_trends(self):
        config = STRUGGLE_MAP["prayer_consistency"]
        # Build 14 days of improving prayer data
        logs = []
        for i in range(14):
            logs.append({
                "date": f"2026-02-{i + 1:02d}",
                "behaviors": {
                    "fajr_prayer": 1 if i > 3 else 0,
                    "dhuhr_prayer": 1 if i > 2 else 0,
                },
            })

        from datetime import datetime, timedelta
        declared = (datetime.utcnow() - timedelta(days=14)).isoformat() + "Z"
        progress = compute_struggle_progress(
            "prayer_consistency", declared, logs, config,
        )
        trends = progress["linked_behavior_trends"]
        assert "fajr_prayer" in trends
        assert trends["fajr_prayer"] in ("improving", "stable", "declining", "insufficient_data")

    def test_phase_title_populated(self):
        config = STRUGGLE_MAP["spiritual_dryness"]
        progress = compute_struggle_progress(
            "spiritual_dryness",
            "2026-02-27T00:00:00Z",
            [],
            config,
        )
        assert len(progress["phase_title"]) > 10

    def test_phase_progress_pct_valid(self):
        config = STRUGGLE_MAP["tongue_control"]
        from datetime import datetime, timedelta
        declared = (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z"
        progress = compute_struggle_progress(
            "tongue_control", declared, [], config,
        )
        assert 0 <= progress["phase_progress_pct"] <= 100


# ==========================================================================
# Digest Context Builder
# ==========================================================================

class TestPrepareDigestContext:
    def _make_week_logs(self):
        logs = []
        for i in range(7):
            day = i + 1
            logs.append({
                "date": f"2026-02-{day + 16:02d}",
                "behaviors": {
                    "fajr_prayer": 1,
                    "quran_minutes": 15 + i * 2,
                    "dhikr_minutes": 10,
                },
                "heart_state": "grateful" if i % 2 == 0 else "peaceful",
                "heart_notes": [],
            })
        return logs

    def test_returns_all_expected_keys(self):
        logs = self._make_week_logs()
        config = {"tracked_behaviors": [
            {"id": "fajr_prayer"}, {"id": "quran_minutes"}, {"id": "dhikr_minutes"},
        ]}
        trajectory = {"current_state": "steady", "composite_display": "Steady", "volatility_state": "stable", "days_logged": 7, "growth_edges": []}

        context = prepare_digest_context(
            logs, trajectory, config, [], [], "2026-02-17", "2026-02-23",
        )

        expected_keys = [
            "week_start", "week_end", "days_logged_this_week",
            "trajectory_state", "trajectory_display", "volatility",
            "days_total", "behavior_summary", "heart_states",
            "heart_note_count", "heart_note_types", "correlations",
            "struggles", "growth_edges",
        ]
        for key in expected_keys:
            assert key in context, f"Missing key: {key}"

    def test_days_logged_count(self):
        logs = self._make_week_logs()
        config = {"tracked_behaviors": [{"id": "fajr_prayer"}]}
        trajectory = {"current_state": "steady", "days_logged": 7, "growth_edges": []}

        context = prepare_digest_context(
            logs, trajectory, config, [], [], "2026-02-17", "2026-02-23",
        )
        assert context["days_logged_this_week"] == 7

    def test_behavior_summary_populated(self):
        logs = self._make_week_logs()
        config = {"tracked_behaviors": [{"id": "fajr_prayer"}, {"id": "quran_minutes"}]}
        trajectory = {"current_state": "steady", "days_logged": 14, "growth_edges": []}

        context = prepare_digest_context(
            logs, trajectory, config, [], [], "2026-02-17", "2026-02-23",
        )
        assert "fajr_prayer" in context["behavior_summary"]
        assert "quran_minutes" in context["behavior_summary"]
        fajr = context["behavior_summary"]["fajr_prayer"]
        assert "average" in fajr
        assert "days_logged" in fajr
        assert "trend" in fajr

    def test_heart_states_counted(self):
        logs = self._make_week_logs()
        config = {"tracked_behaviors": []}

        trajectory = {"current_state": "steady", "days_logged": 7, "growth_edges": []}

        context = prepare_digest_context(
            logs, trajectory, config, [], [], "2026-02-17", "2026-02-23",
        )
        assert "grateful" in context["heart_states"]
        assert "peaceful" in context["heart_states"]

    def test_struggle_summaries_included(self):
        logs = self._make_week_logs()
        config = {"tracked_behaviors": []}

        trajectory = {"current_state": "steady", "days_logged": 7, "growth_edges": []}
        struggles = [{"label": "Test", "progress": {"weeks_active": 1, "phase_title": "Phase 1", "linked_behavior_trends": {}}}]

        context = prepare_digest_context(
            logs, trajectory, config, [], struggles, "2026-02-17", "2026-02-23",
        )
        assert len(context["struggles"]) == 1
        assert context["struggles"][0]["label"] == "Test"


# ==========================================================================
# Digest Prompt Builder
# ==========================================================================

class TestBuildDigestPrompt:
    def _make_context(self):
        return {
            "week_start": "2026-02-17",
            "week_end": "2026-02-23",
            "days_logged_this_week": 5,
            "trajectory_state": "gently_rising",
            "trajectory_display": "Gently Rising",
            "volatility": "stable",
            "days_total": 30,
            "behavior_summary": {
                "fajr_prayer": {"label": "Fajr Prayer", "average": 0.8, "days_logged": 5, "trend": "improving"},
            },
            "heart_states": {"grateful": 3, "peaceful": 2},
            "heart_note_count": 2,
            "heart_note_types": {"gratitude": 1, "dua": 1},
            "correlations": [
                {"pair": "fajr|quran", "r": 0.65, "insight": "Fajr and Quran move together"},
            ],
            "struggles": [
                {"label": "Prayer Consistency", "weeks_active": 1, "phase_title": "Anchor phase", "linked_trends": {}},
            ],
            "growth_edges": ["character"],
        }

    def test_prompt_is_string(self):
        prompt = build_digest_prompt(self._make_context())
        assert isinstance(prompt, str)
        assert len(prompt) > 200

    def test_prompt_contains_context(self):
        prompt = build_digest_prompt(self._make_context())
        assert "2026-02-17" in prompt
        assert "gently_rising" in prompt
        assert "Fajr Prayer" in prompt

    def test_prompt_contains_rules(self):
        prompt = build_digest_prompt(self._make_context())
        assert "NEVER show raw numbers" in prompt
        assert "NEVER say" in prompt
        assert "mirror" in prompt.lower()

    def test_prompt_contains_json_schema(self):
        prompt = build_digest_prompt(self._make_context())
        assert "opening" in prompt
        assert "weekly_story" in prompt
        assert "verse_to_carry" in prompt
        assert "closing" in prompt

    def test_persona_tone_used(self):
        prompt = build_digest_prompt(self._make_context(), "new_revert")
        assert "gently" in prompt.lower() or "simple" in prompt.lower()

    def test_default_persona(self):
        prompt = build_digest_prompt(self._make_context())
        # Default is practicing_muslim
        assert "balanced" in prompt.lower() or "respectful" in prompt.lower()

    def test_correlations_in_prompt(self):
        prompt = build_digest_prompt(self._make_context())
        assert "Fajr and Quran" in prompt

    def test_struggles_in_prompt(self):
        prompt = build_digest_prompt(self._make_context())
        assert "Prayer Consistency" in prompt

    def test_empty_context_no_crash(self):
        empty = {
            "week_start": "", "week_end": "", "days_logged_this_week": 0,
            "trajectory_state": "calibrating", "trajectory_display": "",
            "volatility": "", "days_total": 0, "behavior_summary": {},
            "heart_states": {}, "heart_note_count": 0, "heart_note_types": {},
            "correlations": [], "struggles": [], "growth_edges": [],
        }
        prompt = build_digest_prompt(empty)
        assert isinstance(prompt, str)
        assert len(prompt) > 100
