"""
Tests for two-stage scholarly retrieval: pointer parsing, resolution, prompt building.
"""
import os
import sys
import json
import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.source_service import (
    _parse_pointer,
    _resolve_asbab,
    _resolve_thematic,
    _resolve_ihya,
    _resolve_madarij,
    _resolve_riyad,
    resolve_scholarly_pointers,
    format_scholarly_excerpts_for_prompt,
    build_scholarly_planning_prompt,
    SCHOLARLY_SOURCE_CATALOG,
    _SOURCE_BADGE_MAP,
    MAX_TOTAL_SCHOLARLY_CHARS,
)


# ============================================================================
# POINTER PARSING
# ============================================================================

class TestParsePointer:
    def test_asbab_pointer(self):
        source_id, params = _parse_pointer("asbab:surah=39:verse=53")
        assert source_id == "asbab"
        assert params == {"surah": 39, "verse": 53}

    def test_thematic_pointer(self):
        source_id, params = _parse_pointer("thematic:surah=39:section=0")
        assert source_id == "thematic"
        assert params == {"surah": 39, "section": 0}

    def test_ihya_pointer(self):
        source_id, params = _parse_pointer("ihya:vol=4:ch=3:sec=0")
        assert source_id == "ihya"
        assert params == {"vol": 4, "ch": 3, "sec": 0}

    def test_madarij_pointer(self):
        source_id, params = _parse_pointer("madarij:vol=1:station=repentance:sub=0")
        assert source_id == "madarij"
        assert params == {"vol": 1, "station": "repentance", "sub": 0}

    def test_riyad_pointer(self):
        source_id, params = _parse_pointer("riyad:book=1:ch=50:hadith=0")
        assert source_id == "riyad"
        assert params == {"book": 1, "ch": 50, "hadith": 0}

    def test_malformed_no_equals(self):
        source_id, params = _parse_pointer("garbage_string")
        assert source_id is None
        assert params is None

    def test_malformed_unknown_source(self):
        source_id, params = _parse_pointer("unknown:key=val")
        assert source_id is None
        assert params is None

    def test_malformed_empty(self):
        source_id, params = _parse_pointer("")
        assert source_id is None
        assert params is None

    def test_malformed_none(self):
        source_id, params = _parse_pointer(None)
        assert source_id is None
        assert params is None

    def test_malformed_no_colon_params(self):
        source_id, params = _parse_pointer("asbab:missing_equals")
        assert source_id is None
        assert params is None

    def test_case_insensitive_source(self):
        source_id, params = _parse_pointer("ASBAB:surah=39:verse=53")
        assert source_id == "asbab"

    def test_string_value_lowered(self):
        source_id, params = _parse_pointer("madarij:vol=1:station=Repentance:sub=0")
        assert params["station"] == "repentance"


# ============================================================================
# INDIVIDUAL RESOLVERS
# ============================================================================

class TestResolveAsbab:
    def test_existing_verse(self):
        """Surah 39 verse 53 should have an asbab entry about 'prodigal'."""
        result = _resolve_asbab({"surah": 39, "verse": 53})
        assert result is not None
        assert result["source_id"] == "asbab"
        assert "prodigal" in result["text"].lower() or "despair" in result["text"].lower()

    def test_missing_verse(self):
        """Surah 39 verse 1 likely has no specific asbab entry."""
        result = _resolve_asbab({"surah": 39, "verse": 1})
        # Could be None or could exist — just verify no crash
        assert result is None or isinstance(result, dict)

    def test_missing_surah(self):
        """Nonexistent surah returns None."""
        result = _resolve_asbab({"surah": 999, "verse": 1})
        assert result is None

    def test_missing_params(self):
        result = _resolve_asbab({})
        assert result is None


class TestResolveThematic:
    def test_surah_39(self):
        """Surah 39 (Al-Zumar) should have thematic data."""
        result = _resolve_thematic({"surah": 39, "section": 0})
        assert result is not None
        assert result["source_id"] == "thematic"
        assert "Thematic" in result["source"]
        assert len(result["text"]) > 100

    def test_synopsis_included(self):
        """Synopsis should be part of the returned text."""
        result = _resolve_thematic({"surah": 39, "section": 0})
        assert result is not None
        assert "Thematic Overview" in result["text"]

    def test_missing_surah(self):
        result = _resolve_thematic({"surah": 999})
        assert result is None


class TestResolveIhya:
    def test_fear_and_hope(self):
        """Vol 4, Chapter 3 (Fear and Hope) should exist."""
        result = _resolve_ihya({"vol": 4, "ch": 3, "sec": 0})
        assert result is not None
        assert result["source_id"] == "ihya"
        assert len(result["text"]) > 50

    def test_repentance(self):
        """Vol 4, Chapter 1 (Repentance) should exist."""
        result = _resolve_ihya({"vol": 4, "ch": 1, "sec": 0})
        assert result is not None

    def test_missing_chapter(self):
        result = _resolve_ihya({"vol": 4, "ch": 99, "sec": 0})
        assert result is None

    def test_missing_params(self):
        result = _resolve_ihya({"vol": 4})
        assert result is None


class TestResolveMadarij:
    def test_repentance_station(self):
        """Vol 1, station=repentance should exist."""
        result = _resolve_madarij({"vol": 1, "station": "repentance", "sub": 0})
        assert result is not None
        assert result["source_id"] == "madarij"
        assert "Station of" in result["title"]

    def test_awakening_station(self):
        """Vol 1, station=awakening should exist."""
        result = _resolve_madarij({"vol": 1, "station": "awakening", "sub": 0})
        assert result is not None

    def test_hope_station_vol2(self):
        """Vol 2, station=hope should exist."""
        result = _resolve_madarij({"vol": 2, "station": "hope", "sub": 0})
        assert result is not None

    def test_missing_station(self):
        result = _resolve_madarij({"vol": 1, "station": "nonexistent", "sub": 0})
        assert result is None


class TestResolveRiyad:
    def test_chapter_50(self):
        """Book 1, Chapter 50 (Forgiveness) should have hadith entries."""
        result = _resolve_riyad({"book": 1, "ch": 50, "hadith": 0})
        assert result is not None
        assert result["source_id"] == "riyad"
        assert "210" in result["title"]  # Hadith #210

    def test_chapter_2(self):
        """Book 1, Chapter 2 (Repentance) should exist."""
        result = _resolve_riyad({"book": 1, "ch": 2, "hadith": 0})
        assert result is not None

    def test_missing_chapter(self):
        result = _resolve_riyad({"book": 1, "ch": 9999, "hadith": 0})
        assert result is None


# ============================================================================
# MAIN DISPATCHER
# ============================================================================

class TestResolveScholarlyPointers:
    def test_full_plan(self):
        """Resolve a realistic 5-source plan for verse 39:53."""
        pointers = [
            "asbab:surah=39:verse=53",
            "thematic:surah=39:section=0",
            "ihya:vol=4:ch=3:sec=0",
            "madarij:vol=2:station=hope:sub=0",
            "riyad:book=1:ch=50:hadith=0",
        ]
        result = resolve_scholarly_pointers(pointers)
        assert "excerpts" in result
        assert "sources_used" in result
        # At least asbab, thematic, and ihya should resolve
        assert len(result["excerpts"]) >= 3
        # Badges should match resolved sources
        badge_keys = {b["key"] for b in result["sources_used"]}
        excerpt_ids = {e["source_id"] for e in result["excerpts"]}
        assert badge_keys == excerpt_ids

    def test_char_budget(self):
        """Total chars across all excerpts should stay under MAX_TOTAL_SCHOLARLY_CHARS."""
        pointers = [
            "asbab:surah=39:verse=53",
            "thematic:surah=39:section=0",
            "ihya:vol=4:ch=1:sec=0",
            "ihya:vol=4:ch=3:sec=0",
            "madarij:vol=1:station=repentance:sub=0",
            "riyad:book=1:ch=50:hadith=0",
            "riyad:book=1:ch=2:hadith=0",
        ]
        result = resolve_scholarly_pointers(pointers)
        total = sum(len(e["text"]) for e in result["excerpts"])
        assert total <= MAX_TOTAL_SCHOLARLY_CHARS + 10  # small buffer for "..."

    def test_empty_pointers(self):
        result = resolve_scholarly_pointers([])
        assert result == {"excerpts": [], "sources_used": []}

    def test_malformed_pointers_skipped(self):
        """Malformed pointers should be skipped without error."""
        result = resolve_scholarly_pointers([
            "garbage",
            "unknown:key=val",
            "asbab:surah=39:verse=53",
        ])
        assert len(result["excerpts"]) >= 1
        assert any(e["source_id"] == "asbab" for e in result["excerpts"])

    def test_badges_only_for_resolved(self):
        """Badges should only appear for sources that returned non-empty text."""
        result = resolve_scholarly_pointers([
            "asbab:surah=39:verse=53",
            "asbab:surah=999:verse=1",  # non-existent
        ])
        badge_keys = {b["key"] for b in result["sources_used"]}
        assert "asbab" in badge_keys
        # Only one asbab badge despite two asbab pointers
        assert len([b for b in result["sources_used"] if b["key"] == "asbab"]) == 1


# ============================================================================
# FORMATTING
# ============================================================================

class TestFormatExcerpts:
    def test_format_has_headers(self):
        resolved = {
            "excerpts": [
                {
                    "source_id": "asbab",
                    "source": "Asbab al-Nuzul (Al-Wahidi)",
                    "title": "Context of Revelation — Verse 53",
                    "text": "Sample asbab text here.",
                },
                {
                    "source_id": "thematic",
                    "source": "Thematic Commentary (Shaykh al-Ghazali)",
                    "title": "Thematic Commentary — Al-Zumar",
                    "text": "Sample thematic text here.",
                },
            ],
            "sources_used": [],
        }
        output = format_scholarly_excerpts_for_prompt(resolved)
        assert "EXCERPT 1" in output
        assert "EXCERPT 2" in output
        assert "CRITICAL INSTRUCTIONS" in output
        assert "Do NOT fabricate" in output
        assert "hadith array EMPTY" in output

    def test_format_empty(self):
        assert format_scholarly_excerpts_for_prompt(None) == ""
        assert format_scholarly_excerpts_for_prompt({"excerpts": []}) == ""


# ============================================================================
# PLANNING PROMPT
# ============================================================================

class TestBuildPlanningPrompt:
    def test_contains_catalog(self):
        prompt = build_scholarly_planning_prompt(
            39, 53, 53, "O My servants who have transgressed...",
            "mercy forgiveness repentance", "Explain 39:53"
        )
        assert "SCHOLARLY SOURCE CATALOG" in prompt
        assert "POINTER GRAMMAR" in prompt
        assert "asbab:surah=39:verse=53" in prompt  # From few-shot example 1

    def test_contains_few_shot(self):
        prompt = build_scholarly_planning_prompt(
            39, 53, 53, "verse text", "themes", "query"
        )
        assert "EXAMPLE 1" in prompt
        assert "EXAMPLE 2" in prompt
        assert "EXAMPLE 3" in prompt

    def test_contains_deterministic_rules(self):
        prompt = build_scholarly_planning_prompt(
            39, 53, 53, "verse text", "themes", "query"
        )
        assert "DETERMINISTIC RULES" in prompt
        assert "ALWAYS include" in prompt
        assert "Maximum 7 pointers" in prompt

    def test_verse_ref_in_prompt(self):
        prompt = build_scholarly_planning_prompt(
            2, 255, 255, "Allah - there is no deity except Him",
            "Ayat al-Kursi throne knowledge", "Explain 2:255"
        )
        assert "2:255" in prompt
        assert "asbab:surah=2:verse=255" in prompt

    def test_verse_range(self):
        prompt = build_scholarly_planning_prompt(
            39, 53, 55, "verse text", "themes", "query"
        )
        assert "39:53-55" in prompt

    def test_query_in_prompt(self):
        prompt = build_scholarly_planning_prompt(
            39, 53, 53, "verse text", "themes", "Tell me about mercy"
        )
        assert "Tell me about mercy" in prompt


# ============================================================================
# CATALOG INTEGRITY
# ============================================================================

class TestCatalogIntegrity:
    def test_all_sources_in_catalog(self):
        """All 5 sources should be described in the catalog."""
        assert "ASBAB AL-NUZUL" in SCHOLARLY_SOURCE_CATALOG
        assert "THEMATIC COMMENTARY" in SCHOLARLY_SOURCE_CATALOG
        assert "IHYA ULUM AL-DIN" in SCHOLARLY_SOURCE_CATALOG
        assert "MADARIJ AL-SALIKIN" in SCHOLARLY_SOURCE_CATALOG
        assert "RIYAD AL-SALIHEEN" in SCHOLARLY_SOURCE_CATALOG

    def test_badge_map_complete(self):
        """Badge map should have entries for all 5 sources."""
        assert set(_SOURCE_BADGE_MAP.keys()) == {"asbab", "thematic", "ihya", "madarij", "riyad"}
        for key, badge in _SOURCE_BADGE_MAP.items():
            assert "name" in badge
            assert "author" in badge
            assert "type" in badge
            assert "key" in badge

    def test_routing_keywords_in_catalog(self):
        """Key routing keywords should be in the catalog."""
        keywords = [
            "prayer", "fasting", "pilgrimage", "repentance", "patience",
            "fear", "hope", "trust", "love", "death", "anger", "pride",
            "awakening", "humility", "renunciation", "forgiveness",
        ]
        catalog_lower = SCHOLARLY_SOURCE_CATALOG.lower()
        for kw in keywords:
            assert kw in catalog_lower, f"Keyword '{kw}' missing from catalog"


# ============================================================================
# INTEGRATION (end-to-end without Gemini)
# ============================================================================

class TestEndToEnd:
    def test_full_pipeline_39_53(self):
        """Simulate a complete plan → resolve → format pipeline."""
        # Step 1: Build planning prompt (would go to Gemini in production)
        prompt = build_scholarly_planning_prompt(
            39, 53, 53,
            "Say, O My servants who have transgressed against themselves, do not despair of the mercy of Allah.",
            "mercy, forgiveness, repentance, hope, Allah's mercy encompasses all",
            "Explain Surah 39 verse 53"
        )
        assert len(prompt) > 500

        # Step 2: Simulate Gemini response (mock)
        mock_plan = {
            "pointers": [
                "asbab:surah=39:verse=53",
                "thematic:surah=39:section=0",
                "ihya:vol=4:ch=3:sec=0",
                "madarij:vol=2:station=hope:sub=0",
                "riyad:book=1:ch=50:hadith=0",
            ],
            "reasoning": "Verse about mercy/hope matches Ihya fear+hope, Madarij hope, Riyad forgiveness."
        }

        # Step 3: Resolve pointers
        resolved = resolve_scholarly_pointers(mock_plan["pointers"])
        assert len(resolved["excerpts"]) >= 3
        assert len(resolved["sources_used"]) >= 3

        # Step 4: Format for generation prompt
        formatted = format_scholarly_excerpts_for_prompt(resolved)
        assert "EXCERPT 1" in formatted
        assert "CRITICAL INSTRUCTIONS" in formatted

        # Step 5: Verify char budget
        total_chars = sum(len(e["text"]) for e in resolved["excerpts"])
        assert total_chars <= MAX_TOTAL_SCHOLARLY_CHARS + 10

    def test_minimal_plan_narrative_verse(self):
        """Narrative verse with only asbab + thematic."""
        pointers = [
            "asbab:surah=12:verse=80",
            "thematic:surah=12:section=0",
        ]
        resolved = resolve_scholarly_pointers(pointers)
        # Thematic should always resolve for any surah
        assert any(e["source_id"] == "thematic" for e in resolved["excerpts"])
        formatted = format_scholarly_excerpts_for_prompt(resolved)
        assert len(formatted) > 50
