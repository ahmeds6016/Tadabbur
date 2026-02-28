"""
Unit tests for Iman Index Phase 4: Heart State Responses + Heart Note Patterns.

Tests: heart state catalog, validation alignment, temporal pattern detection,
emotional arc detection, score correlation, wrapper function shape.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.iman_heart_states import (
    HEART_STATE_CATALOG,
    HEART_STATE_MAP,
    ALL_HEART_STATE_IDS,
)
from data.iman_behaviors import HEART_STATES, HEART_NOTE_TYPES
from services.iman_service import (
    validate_heart_state,
    detect_heart_note_temporal_patterns,
    detect_heart_note_emotional_arcs,
    detect_heart_note_score_correlation,
    compute_heart_note_patterns,
    MIN_PATTERN_DATA_DAYS,
)


# ==========================================================================
# Heart State Catalog
# ==========================================================================

class TestHeartStateCatalog:
    def test_state_count(self):
        assert len(HEART_STATE_CATALOG) == 7

    def test_states_match_validation_list(self):
        """Catalog IDs must match the HEART_STATES validation list."""
        catalog_ids = {s["id"] for s in HEART_STATE_CATALOG}
        assert catalog_ids == set(HEART_STATES)

    def test_required_fields(self):
        for s in HEART_STATE_CATALOG:
            assert "id" in s, f"Missing id"
            assert "label" in s, f"Missing label in {s['id']}"
            assert "arabic" in s, f"Missing arabic in {s['id']}"
            assert "icon" in s, f"Missing icon in {s['id']}"
            assert "color" in s, f"Missing color in {s['id']}"
            assert "verse" in s, f"Missing verse in {s['id']}"
            assert "scholarly_pointers" in s, f"Missing scholarly_pointers in {s['id']}"
            assert "insight" in s, f"Missing insight in {s['id']}"
            assert "action" in s, f"Missing action in {s['id']}"

    def test_verse_has_required_fields(self):
        for s in HEART_STATE_CATALOG:
            v = s["verse"]
            assert "surah" in v, f"Missing surah in verse of {s['id']}"
            assert "verse" in v, f"Missing verse number in verse of {s['id']}"
            assert "text" in v, f"Missing text in verse of {s['id']}"
            assert isinstance(v["surah"], int)
            assert isinstance(v["verse"], int)
            assert len(v["text"]) > 10

    def test_scholarly_pointers_valid_format(self):
        for s in HEART_STATE_CATALOG:
            assert len(s["scholarly_pointers"]) > 0, f"No pointers in {s['id']}"
            for p in s["scholarly_pointers"]:
                parts = p.split(":")
                assert len(parts) >= 2
                assert parts[0] in ("ihya", "madarij", "riyad"), (
                    f"Invalid source in pointer '{p}' for {s['id']}"
                )

    def test_colors_are_hex(self):
        for s in HEART_STATE_CATALOG:
            assert s["color"].startswith("#"), f"{s['id']} color not hex: {s['color']}"

    def test_map_and_ids_consistent(self):
        assert set(HEART_STATE_MAP.keys()) == set(ALL_HEART_STATE_IDS)
        assert len(ALL_HEART_STATE_IDS) == 7

    def test_insights_are_substantial(self):
        for s in HEART_STATE_CATALOG:
            assert len(s["insight"]) > 30, f"Insight too short in {s['id']}"
            assert len(s["action"]) > 20, f"Action too short in {s['id']}"

    def test_ids_unique(self):
        ids = [s["id"] for s in HEART_STATE_CATALOG]
        assert len(ids) == len(set(ids))


# ==========================================================================
# Heart State Validation Alignment
# ==========================================================================

class TestHeartStateValidation:
    def test_all_new_states_valid(self):
        for sid in ALL_HEART_STATE_IDS:
            ok, err = validate_heart_state(sid)
            assert ok is True, f"State {sid} should be valid: {err}"

    def test_old_removed_states_invalid(self):
        """States removed in Phase 4 should now fail validation."""
        for old_state in ["peaceful", "struggling", "hopeful", "content"]:
            ok, _ = validate_heart_state(old_state)
            assert ok is False, f"Old state '{old_state}' should no longer be valid"

    def test_unknown_state_invalid(self):
        ok, _ = validate_heart_state("nonexistent_state")
        assert ok is False

    def test_new_states_present(self):
        for new_state in ["grieving", "joyful", "seeking_guidance", "remorseful"]:
            assert new_state in HEART_STATES


# ==========================================================================
# Temporal Pattern Detection
# ==========================================================================

class TestTemporalPatterns:
    def test_insufficient_data_returns_empty(self):
        logs = [{"date": "2026-02-01", "heart_notes": [{"type": "gratitude"}]}]
        result = detect_heart_note_temporal_patterns(logs)
        assert result == []

    def test_empty_logs_returns_empty(self):
        result = detect_heart_note_temporal_patterns([])
        assert result == []

    def test_no_notes_returns_empty(self):
        logs = [{"date": f"2026-02-{i+1:02d}", "heart_notes": []} for i in range(20)]
        result = detect_heart_note_temporal_patterns(logs)
        assert result == []

    def test_detects_friday_peak(self):
        """Gratitude notes only on Fridays should be detected as a peak."""
        start = datetime(2026, 2, 2)  # Monday
        logs = []
        for i in range(21):
            d = start + timedelta(days=i)
            date_str = d.strftime("%Y-%m-%d")
            notes = []
            if d.weekday() == 4:  # Friday
                notes = [{"type": "gratitude"}, {"type": "gratitude"}, {"type": "gratitude"}]
            logs.append({"date": date_str, "heart_notes": notes})
        result = detect_heart_note_temporal_patterns(logs)
        assert len(result) >= 1
        friday_patterns = [p for p in result if p["day_name"] == "Friday"]
        assert len(friday_patterns) >= 1
        assert friday_patterns[0]["note_type"] == "gratitude"
        assert friday_patterns[0]["type"] == "temporal_peak"

    def test_pattern_has_required_fields(self):
        start = datetime(2026, 2, 2)
        logs = []
        for i in range(21):
            d = start + timedelta(days=i)
            notes = [{"type": "dua"}, {"type": "dua"}] if d.weekday() == 0 else []
            logs.append({"date": d.strftime("%Y-%m-%d"), "heart_notes": notes})
        result = detect_heart_note_temporal_patterns(logs)
        if result:
            p = result[0]
            assert "type" in p
            assert "note_type" in p
            assert "day_name" in p
            assert "insight_text" in p


# ==========================================================================
# Emotional Arc Detection
# ==========================================================================

class TestEmotionalArcs:
    def test_insufficient_data_returns_empty(self):
        result = detect_heart_note_emotional_arcs([{"date": "2026-02-01"}])
        assert result == []

    def test_empty_logs_returns_empty(self):
        result = detect_heart_note_emotional_arcs([])
        assert result == []

    def test_detects_shift_from_gratitude_to_tawbah(self):
        """Clear shift from gratitude to tawbah should be detected."""
        start = datetime(2026, 2, 1)
        logs = []
        for i in range(14):
            d = start + timedelta(days=i)
            if i < 7:
                notes = [{"type": "gratitude"}, {"type": "gratitude"}]
            else:
                notes = [{"type": "tawbah"}, {"type": "tawbah"}]
            logs.append({"date": d.strftime("%Y-%m-%d"), "heart_notes": notes})
        result = detect_heart_note_emotional_arcs(logs, window_days=14)
        assert len(result) >= 1
        types_found = {a["note_type"] for a in result}
        # Should detect shift in at least one of the types
        assert "gratitude" in types_found or "tawbah" in types_found

    def test_arc_has_required_fields(self):
        start = datetime(2026, 2, 1)
        logs = []
        for i in range(14):
            d = start + timedelta(days=i)
            notes = [{"type": "gratitude"}] if i < 7 else [{"type": "tawbah"}, {"type": "tawbah"}]
            logs.append({"date": d.strftime("%Y-%m-%d"), "heart_notes": notes})
        result = detect_heart_note_emotional_arcs(logs, window_days=14)
        if result:
            a = result[0]
            assert "type" in a
            assert "note_type" in a
            assert "direction" in a
            assert a["direction"] in ("increasing", "decreasing")
            assert "shift_pct" in a
            assert "insight_text" in a

    def test_no_shift_with_stable_data(self):
        """Identical distributions should produce no arcs."""
        start = datetime(2026, 2, 1)
        logs = []
        for i in range(14):
            d = start + timedelta(days=i)
            logs.append({"date": d.strftime("%Y-%m-%d"), "heart_notes": [{"type": "gratitude"}]})
        result = detect_heart_note_emotional_arcs(logs, window_days=14)
        assert result == []


# ==========================================================================
# Score Correlation
# ==========================================================================

class TestScoreCorrelation:
    def test_insufficient_data_returns_none(self):
        result = detect_heart_note_score_correlation([], [], window_days=30)
        assert result is None

    def test_empty_behaviors_returns_none(self):
        logs = [{"date": f"2026-02-{i+1:02d}", "behaviors": {}, "heart_notes": []} for i in range(20)]
        result = detect_heart_note_score_correlation(logs, [], window_days=30)
        assert result is None

    def test_correlation_has_required_fields(self):
        """If enough data with difference, result should have right shape."""
        logs = []
        for i in range(20):
            date_str = f"2026-02-{i+1:02d}"
            if i % 2 == 0:
                # Note days: high behavior scores
                logs.append({
                    "date": date_str,
                    "behaviors": {"quran_minutes": 30, "dhikr_minutes": 20},
                    "heart_notes": [{"type": "gratitude"}],
                })
            else:
                # No note days: low behavior scores
                logs.append({
                    "date": date_str,
                    "behaviors": {"quran_minutes": 5, "dhikr_minutes": 2},
                    "heart_notes": [],
                })
        tracked = ["quran_minutes", "dhikr_minutes"]
        result = detect_heart_note_score_correlation(logs, tracked, window_days=30)
        if result is not None:
            assert "type" in result
            assert result["type"] == "score_correlation"
            assert "pct_difference" in result
            assert "insight_text" in result


# ==========================================================================
# Wrapper Function
# ==========================================================================

class TestComputeHeartNotePatterns:
    def test_returns_expected_shape(self):
        result = compute_heart_note_patterns([], [], window_days=30)
        assert "temporal_patterns" in result
        assert "emotional_arcs" in result
        assert "score_correlation" in result
        assert "has_patterns" in result
        assert "min_days_needed" in result

    def test_no_data_has_no_patterns(self):
        result = compute_heart_note_patterns([], [], window_days=30)
        assert result["has_patterns"] is False
        assert result["temporal_patterns"] == []
        assert result["emotional_arcs"] == []
        assert result["score_correlation"] is None

    def test_min_days_constant(self):
        result = compute_heart_note_patterns([], [], window_days=30)
        assert result["min_days_needed"] == MIN_PATTERN_DATA_DAYS
        assert MIN_PATTERN_DATA_DAYS == 14


# ==========================================================================
# Integration: Heart Note Types Still Valid
# ==========================================================================

class TestHeartNoteTypesUnchanged:
    def test_six_note_types(self):
        assert len(HEART_NOTE_TYPES) == 6

    def test_expected_types_present(self):
        expected = {"gratitude", "dua", "tawbah", "connection", "reflection", "quran_insight"}
        assert set(HEART_NOTE_TYPES) == expected
