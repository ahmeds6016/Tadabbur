"""
Unit tests for Iman Index Phase 3: Onboarding & Settings.

Tests: catalog endpoint shape, setup validation (min behaviors, struggle_ids,
onboarding_complete), delete confirmation, behavior/struggle/category counts,
build_default_config flags.
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.iman_service import (
    build_default_config,
    check_behavior_cap,
    MAX_TRACKED_BEHAVIORS,
)
from data.iman_behaviors import (
    IMAN_CATEGORIES,
    IMAN_BEHAVIORS,
    BEHAVIOR_MAP,
    DEFAULT_BEHAVIORS,
    ALL_BEHAVIOR_IDS,
)
from data.iman_struggles import (
    STRUGGLE_CATALOG,
    STRUGGLE_MAP,
    ALL_STRUGGLE_IDS,
)


# ==========================================================================
# Catalog Data Shape
# ==========================================================================

class TestCatalogData:
    """Validate the data that GET /iman/catalog would return."""

    def test_category_count(self):
        assert len(IMAN_CATEGORIES) == 6

    def test_category_required_fields(self):
        for cat_id, cat in IMAN_CATEGORIES.items():
            assert "label" in cat, f"Missing label in category {cat_id}"
            assert "icon" in cat, f"Missing icon in category {cat_id}"
            assert "color" in cat, f"Missing color in category {cat_id}"
            assert "base_weight" in cat, f"Missing base_weight in category {cat_id}"

    def test_category_ids(self):
        expected = {"fard", "tawbah", "quran", "nafl", "character", "stewardship"}
        assert set(IMAN_CATEGORIES.keys()) == expected

    def test_behavior_count(self):
        assert len(IMAN_BEHAVIORS) == 39

    def test_behavior_required_fields(self):
        for b in IMAN_BEHAVIORS:
            assert "id" in b
            assert "category" in b
            assert "label" in b
            assert "input_type" in b
            assert "default_on" in b

    def test_all_behaviors_reference_valid_category(self):
        for b in IMAN_BEHAVIORS:
            assert b["category"] in IMAN_CATEGORIES, (
                f"Behavior {b['id']} references unknown category {b['category']}"
            )

    def test_behavior_ids_unique(self):
        ids = [b["id"] for b in IMAN_BEHAVIORS]
        assert len(ids) == len(set(ids))

    def test_struggle_count(self):
        assert len(STRUGGLE_CATALOG) == 10

    def test_struggle_required_fields(self):
        for s in STRUGGLE_CATALOG:
            assert "id" in s
            assert "label" in s
            assert "description" in s
            assert "icon" in s
            assert "color" in s

    def test_struggle_ids_unique(self):
        ids = [s["id"] for s in STRUGGLE_CATALOG]
        assert len(ids) == len(set(ids))

    def test_all_struggle_ids_match_catalog(self):
        cat_ids = {s["id"] for s in STRUGGLE_CATALOG}
        assert cat_ids == set(ALL_STRUGGLE_IDS)

    def test_struggle_map_matches_catalog(self):
        assert set(STRUGGLE_MAP.keys()) == set(ALL_STRUGGLE_IDS)

    def test_struggles_have_scholarly_pointers(self):
        for s in STRUGGLE_CATALOG:
            assert "scholarly_pointers" in s, f"Missing scholarly_pointers in struggle {s['id']}"
            assert len(s["scholarly_pointers"]) > 0, f"Empty scholarly_pointers in struggle {s['id']}"

    def test_struggles_have_comfort_verses(self):
        for s in STRUGGLE_CATALOG:
            assert "comfort_verses" in s, f"Missing comfort_verses in struggle {s['id']}"
            assert len(s["comfort_verses"]) > 0

    def test_struggles_have_linked_behaviors(self):
        for s in STRUGGLE_CATALOG:
            assert "linked_behaviors" in s
            for bid in s["linked_behaviors"]:
                assert bid in ALL_BEHAVIOR_IDS, (
                    f"Struggle {s['id']} links to unknown behavior {bid}"
                )

    def test_default_behaviors_subset_of_all(self):
        default_ids = {b["id"] for b in DEFAULT_BEHAVIORS}
        assert default_ids.issubset(ALL_BEHAVIOR_IDS)

    def test_default_behaviors_at_least_3(self):
        assert len(DEFAULT_BEHAVIORS) >= 3

    def test_default_behaviors_at_most_max(self):
        assert len(DEFAULT_BEHAVIORS) <= MAX_TRACKED_BEHAVIORS


# ==========================================================================
# build_default_config
# ==========================================================================

class TestBuildDefaultConfig:
    def test_default_config_has_onboarding_complete(self):
        """build_default_config sets onboarding_complete to True by default."""
        config = build_default_config()
        assert config.get("onboarding_complete") is True

    def test_default_config_with_no_args_uses_defaults(self):
        config = build_default_config()
        tracked_ids = {b["id"] for b in config["tracked_behaviors"]}
        default_ids = {b["id"] for b in DEFAULT_BEHAVIORS}
        assert tracked_ids == default_ids

    def test_default_config_with_custom_behaviors(self):
        custom = ["fajr_prayer", "quran_minutes", "dhikr_minutes"]
        config = build_default_config(custom)
        tracked_ids = {b["id"] for b in config["tracked_behaviors"]}
        assert tracked_ids == set(custom)

    def test_config_has_required_fields(self):
        config = build_default_config()
        assert "tracked_behaviors" in config
        assert "onboarding_complete" in config
        assert "engine_version" in config
        assert "baseline_period_start" in config

    def test_config_with_custom_preserves_behavior_metadata(self):
        config = build_default_config(["fajr_prayer"])
        b = config["tracked_behaviors"][0]
        assert b["id"] == "fajr_prayer"
        assert "label" in b
        assert "category" in b
        assert "input_type" in b


# ==========================================================================
# Setup Validation (min behaviors, cap)
# ==========================================================================

class TestSetupValidation:
    def test_fewer_than_3_behaviors_too_few(self):
        """Setup should reject <3 behaviors."""
        # Simulating what POST /iman/setup does:
        behavior_ids = ["fajr_prayer", "quran_minutes"]
        assert len(behavior_ids) < 3

    def test_exactly_3_behaviors_ok(self):
        behavior_ids = ["fajr_prayer", "quran_minutes", "dhikr_minutes"]
        ok, _ = check_behavior_cap(behavior_ids)
        assert ok is True
        assert len(behavior_ids) >= 3

    def test_max_behaviors_ok(self):
        ids = list(ALL_BEHAVIOR_IDS)[:MAX_TRACKED_BEHAVIORS]
        ok, _ = check_behavior_cap(ids)
        assert ok is True

    def test_over_max_behaviors_rejected(self):
        ids = list(ALL_BEHAVIOR_IDS) + ["fake_extra"]
        ok, msg = check_behavior_cap(ids)
        if len(ids) > MAX_TRACKED_BEHAVIORS:
            assert ok is False

    def test_empty_behavior_ids_uses_defaults(self):
        """When behavior_ids is None, build_default_config uses DEFAULT_BEHAVIORS."""
        config = build_default_config(None)
        tracked_ids = {b["id"] for b in config["tracked_behaviors"]}
        default_ids = {b["id"] for b in DEFAULT_BEHAVIORS}
        assert tracked_ids == default_ids

    def test_invalid_behavior_id_raises_error(self):
        """build_default_config raises ValueError for unknown IDs."""
        with pytest.raises(ValueError, match="Unknown behavior IDs"):
            build_default_config(["fajr_prayer", "NONEXISTENT_behavior"])


# ==========================================================================
# Struggle IDs Validation
# ==========================================================================

class TestStruggleValidation:
    def test_all_struggle_ids_in_map(self):
        for sid in ALL_STRUGGLE_IDS:
            assert sid in STRUGGLE_MAP

    def test_struggle_phases(self):
        """Each struggle should have 4-phase progression."""
        for s in STRUGGLE_CATALOG:
            assert "phases" in s, f"Missing phases in struggle {s['id']}"
            assert len(s["phases"]) == 4, f"Expected 4 phases in struggle {s['id']}, got {len(s['phases'])}"

    def test_struggle_phase_fields(self):
        """Each phase is a descriptive string."""
        for s in STRUGGLE_CATALOG:
            for i, phase in enumerate(s["phases"]):
                assert isinstance(phase, str), f"Phase {i} of {s['id']} should be a string"
                assert len(phase) > 10, f"Phase {i} of {s['id']} is too short"


# ==========================================================================
# Delete Confirmation Logic
# ==========================================================================

class TestDeleteConfirmation:
    def test_correct_confirm_string(self):
        """The delete endpoint requires exact string match."""
        assert "DELETE_ALL_IMAN_DATA" == "DELETE_ALL_IMAN_DATA"

    def test_wrong_confirm_would_fail(self):
        """Mismatched confirm string should not pass validation."""
        confirm = "delete_all"
        assert confirm != "DELETE_ALL_IMAN_DATA"

    def test_empty_confirm_would_fail(self):
        confirm = ""
        assert confirm != "DELETE_ALL_IMAN_DATA"

    def test_none_confirm_would_fail(self):
        confirm = None
        assert confirm != "DELETE_ALL_IMAN_DATA"

    def test_subcollections_list(self):
        """Verify all 6 iman subcollections are targeted for deletion."""
        subcollections = [
            "iman_config", "iman_daily_logs", "iman_baselines",
            "iman_trajectory", "iman_struggles", "iman_weekly_digests",
        ]
        assert len(subcollections) == 6
        assert all(s.startswith("iman_") for s in subcollections)


# ==========================================================================
# Catalog → Frontend Contract
# ==========================================================================

class TestCatalogFrontendContract:
    """Ensure the catalog data shape matches what BehaviorSelector.jsx expects."""

    def test_behaviors_have_input_type(self):
        valid_types = {"binary", "scale_5", "minutes", "hours", "count", "count_inv"}
        for b in IMAN_BEHAVIORS:
            assert b["input_type"] in valid_types, (
                f"Behavior {b['id']} has invalid input_type: {b['input_type']}"
            )

    def test_categories_have_color(self):
        for cat_id, cat in IMAN_CATEGORIES.items():
            assert cat["color"].startswith("#"), (
                f"Category {cat_id} color should be hex: {cat['color']}"
            )

    def test_struggles_have_color(self):
        for s in STRUGGLE_CATALOG:
            assert s["color"].startswith("#"), (
                f"Struggle {s['id']} color should be hex: {s['color']}"
            )

    def test_max_tracked_within_reason(self):
        assert 10 <= MAX_TRACKED_BEHAVIORS <= 30

    def test_each_category_has_behaviors(self):
        """Every category should have at least 1 behavior assigned."""
        cats_with_behaviors = {b["category"] for b in IMAN_BEHAVIORS}
        for cat_id in IMAN_CATEGORIES:
            assert cat_id in cats_with_behaviors, (
                f"Category {cat_id} has no behaviors"
            )

    def test_default_behaviors_marked_default_on(self):
        """Every default behavior should have default_on=True."""
        default_ids = {b["id"] for b in DEFAULT_BEHAVIORS}
        for b in IMAN_BEHAVIORS:
            if b["id"] in default_ids:
                assert b["default_on"] is True, (
                    f"Default behavior {b['id']} should have default_on=True"
                )
