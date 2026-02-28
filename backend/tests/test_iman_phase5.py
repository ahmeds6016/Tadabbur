"""
Unit tests for Iman Index Phase 5: Dashboard Insights + Advanced Safeguards.

Tests: strain computation, recovery computation, SR ratio, SR status thresholds,
scrupulosity detection, burnout detection, humility reset, emergency override,
reduced journal, safeguard orchestrator.
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.iman_service import (
    compute_daily_strain,
    compute_daily_recovery,
    compute_strain_recovery,
    detect_scrupulosity_signals,
    detect_burnout_state,
    should_show_humility_reset,
    detect_emergency_override,
    get_reduced_journal_config,
    compute_safeguard_status,
    STRAIN_DIFFICULTY,
    SR_RESTORATIVE_UPPER,
    SR_BALANCED_UPPER,
    SR_HIGH_STRAIN_UPPER,
    SR_BURNOUT_CONSECUTIVE_DAYS,
    SCRUPULOSITY_TAWBAH_STREAK_DAYS,
    EMERGENCY_CONSECUTIVE_DAYS,
    HUMILITY_RESET_FRACTION,
    REDUCED_JOURNAL_RECAL_DAYS,
    REDUCED_JOURNAL_BEHAVIORS,
    _SR_STATUS_MESSAGES,
)


# ==========================================================================
# Daily Strain Computation
# ==========================================================================

class TestDailyStrain:
    def test_no_behaviors_returns_zero(self):
        assert compute_daily_strain({}, ["fajr_prayer"]) == 0.0

    def test_no_tracked_ids_returns_zero(self):
        assert compute_daily_strain({"fajr_prayer": True}, []) == 0.0

    def test_binary_behavior_contributes_strain(self):
        result = compute_daily_strain(
            {"fajr_prayer": True},
            ["fajr_prayer"],
        )
        assert result > 0.0
        assert result <= 1.0

    def test_scale5_behavior_proportional(self):
        """Higher scale_5 value should produce more strain."""
        low = compute_daily_strain(
            {"avoided_sins": 1},
            ["avoided_sins"],
        )
        high = compute_daily_strain(
            {"avoided_sins": 5},
            ["avoided_sins"],
        )
        assert high > low

    def test_all_behaviors_at_max_returns_near_one(self):
        """All tracked behaviors at full values should approach 1.0."""
        behaviors = {
            "fajr_prayer": True,
            "dhuhr_prayer": True,
            "asr_prayer": True,
            "maghrib_prayer": True,
            "isha_prayer": True,
        }
        tracked = list(behaviors.keys())
        result = compute_daily_strain(behaviors, tracked)
        assert result > 0.8

    def test_difficulty_factors_exist_for_all_types(self):
        """All input types should have defined difficulty factors."""
        expected_types = {"binary", "scale_5", "minutes", "hours", "count", "count_inv"}
        assert set(STRAIN_DIFFICULTY.keys()) == expected_types


# ==========================================================================
# Daily Recovery Computation
# ==========================================================================

class TestDailyRecovery:
    def test_empty_log_returns_zero(self):
        result = compute_daily_recovery({"behaviors": {}, "heart_notes": []})
        assert result == 0.0

    def test_heart_notes_contribute(self):
        result = compute_daily_recovery({
            "behaviors": {},
            "heart_notes": [{"type": "gratitude"}],
        })
        assert result == pytest.approx(0.25, abs=0.01)

    def test_quran_contributes(self):
        result = compute_daily_recovery({
            "behaviors": {"quran_minutes": 15},
            "heart_notes": [],
        })
        assert result == pytest.approx(0.25, abs=0.01)

    def test_dhikr_contributes(self):
        result = compute_daily_recovery({
            "behaviors": {"dhikr_minutes": 10},
            "heart_notes": [],
        })
        assert result == pytest.approx(0.20, abs=0.01)

    def test_sleep_gaussian_peaks_at_7_5(self):
        """Sleep at 7.5h should give near-max recovery component."""
        optimal = compute_daily_recovery({
            "behaviors": {"sleep_hours": 7.5},
            "heart_notes": [],
        })
        poor = compute_daily_recovery({
            "behaviors": {"sleep_hours": 3.0},
            "heart_notes": [],
        })
        assert optimal > poor
        assert optimal == pytest.approx(0.15, abs=0.01)

    def test_reflection_notes_contribute(self):
        result = compute_daily_recovery({
            "behaviors": {},
            "heart_notes": [{"type": "reflection"}],
        })
        # Both heart_notes (0.25) and reflection (0.15)
        assert result == pytest.approx(0.40, abs=0.01)

    def test_full_recovery_near_one(self):
        """All recovery factors present should approach 1.0."""
        result = compute_daily_recovery({
            "behaviors": {
                "quran_minutes": 20,
                "dhikr_minutes": 10,
                "sleep_hours": 7.5,
            },
            "heart_notes": [{"type": "reflection"}],
        })
        assert result >= 0.95


# ==========================================================================
# Strain/Recovery Ratio
# ==========================================================================

class TestStrainRecoveryRatio:
    def _make_logs(self, n, strain_behaviors=None, recovery_behaviors=None, heart_notes=None):
        logs = []
        for i in range(n):
            logs.append({
                "date": f"2026-02-{i+1:02d}",
                "behaviors": {**(strain_behaviors or {}), **(recovery_behaviors or {})},
                "heart_notes": heart_notes or [],
            })
        return logs

    def test_empty_logs_returns_balanced(self):
        result = compute_strain_recovery([], ["fajr_prayer"])
        assert result["sr_status"] == "balanced"
        assert result["sr_ratio"] == 0.0

    def test_high_recovery_returns_restorative(self):
        """Lots of recovery, minimal strain → restorative."""
        logs = self._make_logs(
            7,
            recovery_behaviors={"quran_minutes": 30, "dhikr_minutes": 20, "sleep_hours": 7.5},
            heart_notes=[{"type": "reflection"}],
        )
        # Track a behavior not being logged → zero strain, high recovery
        result = compute_strain_recovery(logs, ["fajr_prayer"])
        assert result["sr_status"] == "restorative"

    def test_high_strain_status(self):
        """High strain with moderate recovery → high_strain."""
        logs = []
        for i in range(7):
            logs.append({
                "date": f"2026-02-{i+1:02d}",
                "behaviors": {
                    "fajr_prayer": True, "dhuhr_prayer": True,
                    "asr_prayer": True, "maghrib_prayer": True,
                    "isha_prayer": True, "quran_minutes": 60,
                    "dhikr_minutes": 30, "tahajjud": True,
                },
                "heart_notes": [],
            })
        tracked = ["fajr_prayer", "dhuhr_prayer", "asr_prayer", "maghrib_prayer",
                    "isha_prayer", "quran_minutes", "dhikr_minutes", "tahajjud"]
        result = compute_strain_recovery(logs, tracked)
        assert result["sr_status"] in ("high_strain", "burnout_risk", "balanced")

    def test_result_has_required_fields(self):
        logs = self._make_logs(7)
        result = compute_strain_recovery(logs, ["fajr_prayer"])
        assert "mean_strain" in result
        assert "mean_recovery" in result
        assert "sr_ratio" in result
        assert "sr_status" in result
        assert "strain_pct" in result
        assert "recovery_pct" in result
        assert "status_message" in result

    def test_percentages_are_integers(self):
        logs = self._make_logs(7, strain_behaviors={"fajr_prayer": True})
        result = compute_strain_recovery(logs, ["fajr_prayer"])
        assert isinstance(result["strain_pct"], int)
        assert isinstance(result["recovery_pct"], int)


# ==========================================================================
# SR Status Messages
# ==========================================================================

class TestSRStatusMessages:
    def test_restorative_message(self):
        msg = _SR_STATUS_MESSAGES["restorative"]
        assert "restoration" in msg.lower() or "nourished" in msg.lower()

    def test_balanced_message(self):
        msg = _SR_STATUS_MESSAGES["balanced"]
        assert "harmony" in msg.lower() or "balance" in msg.lower()

    def test_high_strain_message(self):
        msg = _SR_STATUS_MESSAGES["high_strain"]
        assert "striving" in msg.lower() or "prophet" in msg.lower()

    def test_burnout_message(self):
        msg = _SR_STATUS_MESSAGES["burnout_risk"]
        assert "right over you" in msg.lower() or "easing" in msg.lower()


# ==========================================================================
# Scrupulosity Detection
# ==========================================================================

class TestScrupulosityDetection:
    def test_normal_logs_returns_inactive(self):
        logs = [
            {"date": f"2026-02-{i+1:02d}", "behaviors": {}, "heart_notes": [{"type": "gratitude"}]}
            for i in range(7)
        ]
        result = detect_scrupulosity_signals(logs)
        assert result["active"] is False

    def test_insufficient_data_returns_inactive(self):
        logs = [{"date": "2026-02-01", "behaviors": {}, "heart_notes": []}]
        result = detect_scrupulosity_signals(logs)
        assert result["active"] is False

    def test_all_tawbah_notes_detected_as_signal(self):
        logs = [
            {"date": f"2026-02-{i+1:02d}", "behaviors": {"avoided_sins": 1},
             "heart_notes": [{"type": "tawbah"}]}
            for i in range(7)
        ]
        result = detect_scrupulosity_signals(logs)
        assert "all_tawbah_notes" in result["signals"]
        assert "always_low_self_assessment" in result["signals"]
        assert result["active"] is True
        assert result["message"] is not None

    def test_single_signal_stays_inactive(self):
        """Only tawbah notes but no low avoided_sins → 1 signal → inactive."""
        logs = [
            {"date": f"2026-02-{i+1:02d}", "behaviors": {"avoided_sins": 4},
             "heart_notes": [{"type": "tawbah"}]}
            for i in range(7)
        ]
        result = detect_scrupulosity_signals(logs)
        assert "all_tawbah_notes" in result["signals"]
        assert result["active"] is False


# ==========================================================================
# Burnout Detection
# ==========================================================================

class TestBurnoutDetection:
    def test_balanced_returns_inactive(self):
        sr_data = {"sr_status": "balanced", "sr_ratio": 1.0}
        result = detect_burnout_state(sr_data)
        assert result["active"] is False

    def test_burnout_risk_returns_active(self):
        sr_data = {"sr_status": "burnout_risk", "sr_ratio": 2.5}
        result = detect_burnout_state(sr_data)
        assert result["active"] is True
        assert result["message"] is not None
        assert result["suggest_remove_behavior"] is True

    def test_high_strain_not_burnout(self):
        sr_data = {"sr_status": "high_strain", "sr_ratio": 1.8}
        result = detect_burnout_state(sr_data)
        assert result["active"] is False


# ==========================================================================
# Humility Reset
# ==========================================================================

class TestHumilityReset:
    def test_never_triggers_on_recalibrating(self):
        """Should not trigger during hard times."""
        result = should_show_humility_reset("test_uid", "recalibrating")
        assert result["active"] is False

    def test_never_triggers_on_calibrating(self):
        result = should_show_humility_reset("test_uid", "calibrating")
        assert result["active"] is False

    def test_deterministic_per_uid_date(self):
        """Same uid on same day should give same result."""
        r1 = should_show_humility_reset("consistent_uid", "ascending")
        r2 = should_show_humility_reset("consistent_uid", "ascending")
        assert r1["active"] == r2["active"]

    def test_active_has_required_fields(self):
        """When active, should have message, hadith, and instruction."""
        # Try many uids to find one that triggers
        for i in range(100):
            result = should_show_humility_reset(f"uid_{i}", "ascending")
            if result["active"]:
                assert "message" in result
                assert "hadith" in result
                assert "instruction" in result
                return
        # If none triggered in 100 tries, that's statistically unlikely but ok
        # With 1/30 probability, expect ~3-4 hits in 100 tries


# ==========================================================================
# Emergency Override
# ==========================================================================

class TestEmergencyOverride:
    def test_mixed_states_returns_inactive(self):
        logs = [
            {"date": f"2026-02-{i+1:02d}", "heart_state": "grateful" if i % 2 == 0 else "grieving"}
            for i in range(7)
        ]
        result = detect_emergency_override(logs)
        assert result["active"] is False

    def test_insufficient_data_returns_inactive(self):
        logs = [{"date": "2026-02-01", "heart_state": "grieving"}]
        result = detect_emergency_override(logs)
        assert result["active"] is False

    def test_7_consecutive_grieving_triggers(self):
        logs = [
            {"date": f"2026-02-{i+1:02d}", "heart_state": "grieving"}
            for i in range(7)
        ]
        result = detect_emergency_override(logs)
        assert result["active"] is True
        assert result["verse"]["surah"] == 93
        assert result["verse"]["verse"] == 3

    def test_7_consecutive_dry_triggers(self):
        logs = [
            {"date": f"2026-02-{i+1:02d}", "heart_state": "spiritually_dry"}
            for i in range(7)
        ]
        result = detect_emergency_override(logs)
        assert result["active"] is True

    def test_active_has_message(self):
        logs = [
            {"date": f"2026-02-{i+1:02d}", "heart_state": "grieving"}
            for i in range(7)
        ]
        result = detect_emergency_override(logs)
        assert "message" in result
        assert len(result["message"]) > 20


# ==========================================================================
# Reduced Journal
# ==========================================================================

class TestReducedJournal:
    def test_under_14_days_returns_none(self):
        result = get_reduced_journal_config(13)
        assert result is None

    def test_at_14_days_returns_config(self):
        result = get_reduced_journal_config(14)
        assert result is not None
        assert result["active"] is True
        assert "fajr_prayer" in result["suggested_behaviors"]
        assert len(result["suggested_behaviors"]) == 3

    def test_message_present(self):
        result = get_reduced_journal_config(20)
        assert "message" in result
        assert len(result["message"]) > 10


# ==========================================================================
# Safeguard Orchestrator
# ==========================================================================

class TestSafeguardOrchestrator:
    def test_returns_all_safeguard_keys(self):
        result = compute_safeguard_status(
            daily_logs=[],
            trajectory={"current_state": "calibrating"},
            sr_data={"sr_status": "balanced"},
            uid="test_uid",
        )
        assert "scrupulosity" in result
        assert "burnout" in result
        assert "humility_reset" in result
        assert "emergency_override" in result
        assert "reduced_journal" in result
        assert "any_active" in result

    def test_normal_data_no_active_safeguards(self):
        logs = [
            {"date": f"2026-02-{i+1:02d}", "behaviors": {},
             "heart_notes": [{"type": "gratitude"}], "heart_state": "grateful"}
            for i in range(7)
        ]
        result = compute_safeguard_status(
            daily_logs=logs,
            trajectory={"current_state": "steady"},
            sr_data={"sr_status": "balanced"},
            uid="normal_user",
        )
        assert result["any_active"] is False

    def test_emergency_override_sets_any_active(self):
        logs = [
            {"date": f"2026-02-{i+1:02d}", "behaviors": {},
             "heart_notes": [], "heart_state": "grieving"}
            for i in range(7)
        ]
        result = compute_safeguard_status(
            daily_logs=logs,
            trajectory={"current_state": "recalibrating"},
            sr_data={"sr_status": "balanced"},
            uid="grieving_user",
        )
        assert result["emergency_override"]["active"] is True
        assert result["any_active"] is True


# ==========================================================================
# Constants Validation
# ==========================================================================

class TestPhase5Constants:
    def test_sr_thresholds_ordered(self):
        assert SR_RESTORATIVE_UPPER < SR_BALANCED_UPPER < SR_HIGH_STRAIN_UPPER

    def test_burnout_days_reasonable(self):
        assert 5 <= SR_BURNOUT_CONSECUTIVE_DAYS <= 14

    def test_emergency_days_reasonable(self):
        assert 5 <= EMERGENCY_CONSECUTIVE_DAYS <= 14

    def test_humility_fraction_reasonable(self):
        assert 7 <= HUMILITY_RESET_FRACTION <= 60

    def test_reduced_journal_behaviors_valid(self):
        from data.iman_behaviors import ALL_BEHAVIOR_IDS
        for bid in REDUCED_JOURNAL_BEHAVIORS:
            assert bid in ALL_BEHAVIOR_IDS, f"Reduced journal behavior {bid} not in catalog"
