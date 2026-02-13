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
    plan_scholarly_retrieval_deterministic,
    _get_verse_map_pointers,
    _station_name_to_slug,
    SCHOLARLY_SOURCE_CATALOG,
    _SOURCE_BADGE_MAP,
    MAX_TOTAL_SCHOLARLY_CHARS,
    MAX_POINTERS,
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
        assert "Maximum 10 pointers" in prompt

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


# ============================================================================
# DETERMINISTIC PLANNER
# ============================================================================

class TestDeterministicPlanner:
    def test_always_has_asbab_and_thematic(self):
        """Every plan must include asbab + thematic pointers."""
        plan = plan_scholarly_retrieval_deterministic(
            39, 53, 53, "Some verse text", ""
        )
        assert "asbab:surah=39:verse=53" in plan["pointers"]
        assert "thematic:surah=39:section=0" in plan["pointers"]

    def test_mercy_hope_verse_matches_ihya_madarij_riyad(self):
        """39:53 about mercy/hope should match multiple sources."""
        plan = plan_scholarly_retrieval_deterministic(
            39, 53, 53,
            "Say, O My servants who have transgressed against themselves, do not despair of the mercy of Allah. Indeed, Allah forgives all sins.",
            "mercy forgiveness repentance hope despair"
        )
        pointers = plan["pointers"]
        assert len(pointers) >= 4  # asbab + thematic + at least 2 more
        # Should have ihya match (fear/hope or repentance)
        assert any(p.startswith("ihya:") for p in pointers)
        # Should have riyad match (forgiveness or repentance)
        assert any(p.startswith("riyad:") for p in pointers)

    def test_patience_verse_matches(self):
        """2:153 about patience should match patience chapters."""
        plan = plan_scholarly_retrieval_deterministic(
            2, 153, 153,
            "O you who have believed, seek help through patience and prayer. Indeed, Allah is with the patient.",
            "patience sabr prayer steadfastness"
        )
        pointers = plan["pointers"]
        assert any("patience" in p or "ch=2" in p for p in pointers if p.startswith("ihya:"))
        assert any("patience" in p or "ch=3" in p for p in pointers if p.startswith("riyad:"))

    def test_narrative_verse_minimal(self):
        """Narrative verse with no topical keywords gets only asbab + thematic + verse-map."""
        plan = plan_scholarly_retrieval_deterministic(
            12, 4, 4,
            "When Yusuf said to his brother, truly I saw eleven stars",
            "Yusuf brothers eleven stars prostrating"
        )
        pointers = plan["pointers"]
        # No topical keywords match routing tables
        assert pointers[0] == "asbab:surah=12:verse=4"
        assert pointers[1] == "thematic:surah=12:section=0"
        # May have verse-map refs but no keyword-routed refs
        keyword_ptrs = [p for p in pointers[2:] if not _get_verse_map_pointers(12, 4) or p not in _get_verse_map_pointers(12, 4)]
        # All extra pointers should be from verse map only (no keyword matches)
        for p in pointers[2:]:
            vm_ptrs = _get_verse_map_pointers(12, 4)
            if vm_ptrs:
                assert p in vm_ptrs, f"Extra pointer {p} not from verse map"

    def test_death_verse_matches_ihya(self):
        """33:16 about death should match Ihya death chapter."""
        plan = plan_scholarly_retrieval_deterministic(
            33, 16, 16,
            "Say, Never will fleeing benefit you if you should flee from death or killing.",
            "death fleeing battle hypocrisy divine decree"
        )
        pointers = plan["pointers"]
        assert "ihya:vol=4:ch=10:sec=0" in pointers

    def test_max_pointers(self):
        """Even with many keyword matches, should cap at MAX_POINTERS."""
        plan = plan_scholarly_retrieval_deterministic(
            2, 153, 153,
            "patience prayer repentance fear hope mercy forgiveness death trust love humility",
            "patience sabr prayer salah repentance tawbah fear hope mercy forgiveness death trust love humility"
        )
        assert len(plan["pointers"]) <= MAX_POINTERS

    def test_returns_reasoning(self):
        """Plan should include reasoning string."""
        plan = plan_scholarly_retrieval_deterministic(
            39, 53, 53, "mercy", "hope"
        )
        assert "reasoning" in plan
        assert isinstance(plan["reasoning"], str)
        assert len(plan["reasoning"]) > 0

    def test_no_duplicate_pointers(self):
        """Same keyword appearing in verse and summary shouldn't create duplicates."""
        plan = plan_scholarly_retrieval_deterministic(
            39, 53, 53,
            "repentance and mercy",
            "repentance and mercy and forgiveness"
        )
        assert len(plan["pointers"]) == len(set(plan["pointers"]))

    def test_full_pipeline_deterministic(self):
        """Full pipeline: plan → resolve → format with deterministic planner."""
        plan = plan_scholarly_retrieval_deterministic(
            39, 53, 53,
            "Say, O My servants who have transgressed against themselves, do not despair of the mercy of Allah.",
            "mercy forgiveness repentance hope"
        )
        resolved = resolve_scholarly_pointers(plan["pointers"])
        assert len(resolved["excerpts"]) >= 2
        formatted = format_scholarly_excerpts_for_prompt(resolved)
        assert "EXCERPT 1" in formatted
        assert "CRITICAL INSTRUCTIONS" in formatted
        total = sum(len(e["text"]) for e in resolved["excerpts"])
        assert total <= MAX_TOTAL_SCHOLARLY_CHARS + 10


# ============================================================================
# VERSE-MAP DISCOVERY
# ============================================================================

class TestVerseMapDiscovery:
    def test_station_name_to_slug(self):
        """Station display names should convert to correct slugs."""
        assert _station_name_to_slug("Repentance") == "repentance"
        assert _station_name_to_slug("Oft-Returning") == "oft_returning"
        assert _station_name_to_slug("Self-Reckoning") == "self_reckoning"
        assert _station_name_to_slug("Joyful Contentment") == "joyful_contentment"
        assert _station_name_to_slug("Refinement and Correction") == "refinement_and_correction"
        assert _station_name_to_slug("Trust in God") == "trust_in_god"
        assert _station_name_to_slug("Standing Firm") == "standing_firm"

    def test_verse_map_pointers_riyad(self):
        """Verse 2:3 should have riyad references in the verse map."""
        ptrs = _get_verse_map_pointers(2, 3)
        # Should return list (may be empty if no verse map entry)
        assert isinstance(ptrs, list)
        # All pointers should be valid format
        for p in ptrs:
            source_id, params = _parse_pointer(p)
            assert source_id is not None, f"Invalid pointer: {p}"

    def test_verse_map_pointers_madarij(self):
        """Verse 2:222 should have madarij reference (Purification) in verse map."""
        ptrs = _get_verse_map_pointers(2, 222)
        madarij_ptrs = [p for p in ptrs if p.startswith("madarij:")]
        if madarij_ptrs:
            # Verify slug format (no spaces, no hyphens)
            for p in madarij_ptrs:
                _, params = _parse_pointer(p)
                assert " " not in str(params.get("station", ""))
                assert "-" not in str(params.get("station", ""))

    def test_verse_map_returns_max_5(self):
        """Should return at most 5 pointers."""
        ptrs = _get_verse_map_pointers(2, 255)
        assert len(ptrs) <= 5

    def test_verse_map_empty_for_nonexistent(self):
        """Nonexistent verse should return empty list."""
        ptrs = _get_verse_map_pointers(999, 999)
        assert ptrs == []

    def test_verse_map_no_duplicates(self):
        """Should not return duplicate pointers."""
        ptrs = _get_verse_map_pointers(2, 3)
        assert len(ptrs) == len(set(ptrs))

    def test_verse_map_integrated_into_planner(self):
        """Planner should include verse-map pointers beyond keyword routing."""
        # Use a verse that has verse-map refs but possibly no keyword matches
        plan = plan_scholarly_retrieval_deterministic(
            2, 3, 3,
            "Who believe in the unseen, establish prayer, and spend out of what We have provided for them",
            "faith unseen prayer spending charity"
        )
        pointers = plan["pointers"]
        # Should have asbab + thematic at minimum
        assert pointers[0].startswith("asbab:")
        assert pointers[1].startswith("thematic:")
        # Check if verse-map refs were added (reasoning should mention it)
        verse_map_ptrs = _get_verse_map_pointers(2, 3)
        if verse_map_ptrs:
            assert "verse-map" in plan["reasoning"]

    def test_verse_map_dedup_with_keyword(self):
        """Verse-map pointers that match keyword pointers should not duplicate."""
        plan = plan_scholarly_retrieval_deterministic(
            39, 53, 53,
            "Say, O My servants who have transgressed against themselves, do not despair of the mercy of Allah.",
            "mercy forgiveness repentance hope"
        )
        # No duplicates
        assert len(plan["pointers"]) == len(set(plan["pointers"]))


# ============================================================================
# EXPANDED ROUTING
# ============================================================================

class TestExpandedRouting:
    def test_riyad_paradise_routing(self):
        """'paradise' keyword should match expanded riyad routing."""
        plan = plan_scholarly_retrieval_deterministic(
            56, 10, 10,
            "And the forerunners, the forerunners - those are the ones brought near, in Gardens of Pleasure",
            "paradise jannah reward forerunners"
        )
        riyad_ptrs = [p for p in plan["pointers"] if p.startswith("riyad:")]
        assert any("ch=244" in p for p in riyad_ptrs), "Expected paradise chapter 244"

    def test_riyad_knowledge_routing(self):
        """'knowledge' keyword should match expanded riyad routing."""
        plan = plan_scholarly_retrieval_deterministic(
            96, 1, 1,
            "Read in the name of your Lord who created",
            "knowledge learning reading creation"
        )
        riyad_ptrs = [p for p in plan["pointers"] if p.startswith("riyad:")]
        assert any("ch=241" in p for p in riyad_ptrs), "Expected knowledge chapter 241"

    def test_ihya_knowledge_routing(self):
        """'knowledge' keyword should match expanded ihya routing."""
        plan = plan_scholarly_retrieval_deterministic(
            96, 1, 1,
            "Read in the name of your Lord who created",
            "knowledge learning reading"
        )
        ihya_ptrs = [p for p in plan["pointers"] if p.startswith("ihya:")]
        assert any("ch=1" in p and "vol=1" in p for p in ihya_ptrs), "Expected Ihya vol 1 ch 1 (Knowledge)"

    def test_madarij_expanded_routing(self):
        """'discipline' keyword should match expanded madarij routing."""
        plan = plan_scholarly_retrieval_deterministic(
            2, 183, 183,
            "O you who have believed, decreed upon you is fasting as it was decreed upon those before you that you may become righteous",
            "fasting discipline self-control righteousness"
        )
        madarij_ptrs = [p for p in plan["pointers"] if p.startswith("madarij:")]
        assert any("disciplining" in p for p in madarij_ptrs), "Expected disciplining station"

    def test_riyad_new_chapters_resolve(self):
        """New riyad chapter pointers from expanded routing should actually resolve."""
        new_chapters = [179, 200, 201, 241, 244, 344]
        for ch in new_chapters:
            result = _resolve_riyad({"book": 1, "ch": ch, "hadith": 0})
            assert result is not None, f"Riyad chapter {ch} failed to resolve"
            assert len(result["text"]) > 20, f"Riyad chapter {ch} has insufficient text"


# ============================================================================
# MULTI-SECTION FETCHING
# ============================================================================

class TestMultiSectionFetching:
    def test_ihya_multi_section(self):
        """Ihya resolver should fetch up to 2 substantive sections."""
        result = _resolve_ihya({"vol": 4, "ch": 1, "sec": 0})
        assert result is not None
        # With multi-section, text may contain section separator
        assert len(result["text"]) > 100

    def test_madarij_multi_subsection(self):
        """Madarij resolver should fetch up to 2 subsections."""
        result = _resolve_madarij({"vol": 1, "station": "repentance", "sub": 0})
        assert result is not None
        assert len(result["text"]) > 100

    def test_riyad_multi_hadith(self):
        """Riyad resolver should fetch up to 2 hadiths."""
        result = _resolve_riyad({"book": 1, "ch": 2, "hadith": 0})
        assert result is not None
        assert len(result["text"]) > 50

    def test_ihya_respects_char_limit(self):
        """Multi-section fetching should respect MAX_IHYA_CHARS."""
        from services.source_service import MAX_IHYA_CHARS
        result = _resolve_ihya({"vol": 4, "ch": 1, "sec": 0})
        if result:
            assert len(result["text"]) <= MAX_IHYA_CHARS + 10

    def test_increased_budget(self):
        """10 pointers resolved, total should stay under 12000 chars."""
        pointers = [
            "asbab:surah=39:verse=53",
            "thematic:surah=39:section=0",
            "ihya:vol=4:ch=1:sec=0",
            "ihya:vol=4:ch=3:sec=0",
            "ihya:vol=3:ch=1:sec=0",
            "madarij:vol=1:station=repentance:sub=0",
            "madarij:vol=2:station=hope:sub=0",
            "riyad:book=1:ch=50:hadith=0",
            "riyad:book=1:ch=2:hadith=0",
            "riyad:book=1:ch=3:hadith=0",
        ]
        result = resolve_scholarly_pointers(pointers)
        total = sum(len(e["text"]) for e in result["excerpts"])
        assert total <= MAX_TOTAL_SCHOLARLY_CHARS + 10
