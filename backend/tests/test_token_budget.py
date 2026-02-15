"""
Tests for the precomputed token budget guardrail system.

These tests create mock TAFSIR_CHUNKS with known sizes, call
precompute_verse_budgets(), and verify that compute_max_end_verse()
returns correct results based on actual data — not heuristics.
"""

import math
import os
import sys

import pytest

# Ensure backend root is on the path so imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.token_budget import (
    ABSOLUTE_MAX_VERSES,
    CHARS_PER_TOKEN_AR,
    CHARS_PER_TOKEN_EN,
    OUTPUT_TOKENS_PER_VERSE,
    PRACTICAL_INPUT_BUDGET,
    PROMPT_OVERHEAD_TOKENS,
    SCHOLARLY_RESERVE_TOKENS,
    SAFETY_FACTOR,
    VERSE_AND_TAFSIR_BUDGET,
    VERSE_TEXT_TOKENS_PER_VERSE,
)

import services.token_budget_service as svc


# ===================================================================
# Helpers
# ===================================================================

def _reset_precomputed():
    """Reset module-level precomputed state between tests."""
    svc._VERSE_TOKEN_COSTS.clear()
    svc._PREFIX_SUMS.clear()
    svc._MAX_END_LOOKUP.clear()
    svc._PRECOMPUTED = False


def _make_chunks(verse_specs):
    """
    Build a mock TAFSIR_CHUNKS dict from a list of specs.

    verse_specs: list of (surah, verse, ibn_kathir_chars, qurtubi_chars)
    """
    chunks = {}
    for surah, verse, ik_chars, q_chars in verse_specs:
        if ik_chars > 0:
            chunks[f"ibn-kathir:{surah}:{verse}"] = "x" * ik_chars
        if q_chars > 0:
            chunks[f"al-qurtubi:{surah}:{verse}"] = "y" * q_chars
    return chunks


# Small surah for testing: 4 verses
SMALL_SURAH_META = {112: {"name": "Al-Ikhlas", "verses": 4}}

# Medium surah: 10 verses (fictional for testing)
MEDIUM_SURAH_META = {99: {"name": "Az-Zalzalah", "verses": 8}}


# ===================================================================
# Token estimation helpers
# ===================================================================

class TestTokenEstimation:
    def test_empty_string(self):
        assert svc.estimate_tokens_for_text("", "english") == 0

    def test_none_input(self):
        assert svc.estimate_tokens_for_text(None, "arabic") == 0

    def test_english_text(self):
        text = "This is a test sentence with exactly forty characters!!"
        tokens = svc.estimate_tokens_for_text(text, "english")
        assert tokens == math.ceil(len(text) / CHARS_PER_TOKEN_EN)

    def test_arabic_text(self):
        text = "\u0628\u0633\u0645 \u0627\u0644\u0644\u0647 \u0627\u0644\u0631\u062d\u0645\u0646 \u0627\u0644\u0631\u062d\u064a\u0645"
        tokens = svc.estimate_tokens_for_text(text, "arabic")
        assert tokens == math.ceil(len(text) / CHARS_PER_TOKEN_AR)

    def test_unknown_lang_defaults_to_mixed(self):
        text = "test"
        assert svc.estimate_tokens_for_text(text, "unknown") == svc.estimate_tokens_for_text(text, "mixed")


# ===================================================================
# Budget constants sanity checks
# ===================================================================

class TestBudgetConstants:
    def test_budget_positive(self):
        assert VERSE_AND_TAFSIR_BUDGET > 0

    def test_components_sum_to_practical(self):
        """Verify per-query fixed costs + verse budget = practical budget."""
        total = (
            PROMPT_OVERHEAD_TOKENS
            + SCHOLARLY_RESERVE_TOKENS
            + VERSE_AND_TAFSIR_BUDGET
        )
        assert total == PRACTICAL_INPUT_BUDGET

    def test_safety_factor_is_90_percent(self):
        assert SAFETY_FACTOR == 0.90

    def test_absolute_max_verses(self):
        assert ABSOLUTE_MAX_VERSES == 5

    def test_output_tokens_per_verse_is_positive(self):
        assert OUTPUT_TOKENS_PER_VERSE > 0


# ===================================================================
# Precomputation
# ===================================================================

class TestPrecomputation:
    def setup_method(self):
        _reset_precomputed()

    def test_not_precomputed_initially(self):
        assert not svc.is_precomputed()

    def test_precompute_sets_flag(self):
        chunks = _make_chunks([(112, 1, 400, 400), (112, 2, 400, 400),
                               (112, 3, 400, 400), (112, 4, 400, 400)])
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)
        assert svc.is_precomputed()

    def test_precompute_populates_all_structures(self):
        chunks = _make_chunks([(112, 1, 400, 400)])
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)
        assert 112 in svc._VERSE_TOKEN_COSTS
        assert 112 in svc._PREFIX_SUMS
        assert 112 in svc._MAX_END_LOOKUP
        assert len(svc._VERSE_TOKEN_COSTS[112]) == 4
        assert len(svc._PREFIX_SUMS[112]) == 5  # 4 verses + leading 0
        assert len(svc._MAX_END_LOOKUP[112]) == 4  # one entry per start verse

    def test_verse_cost_includes_output_allocation(self):
        """Per-verse cost = VERSE_TEXT + tafsir + OUTPUT_TOKENS_PER_VERSE."""
        # 4000 chars each source = 8000 chars total = 2000 tokens tafsir
        chunks = _make_chunks([(112, 1, 4000, 4000)])
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)

        expected = VERSE_TEXT_TOKENS_PER_VERSE + math.ceil(8000 / CHARS_PER_TOKEN_EN) + OUTPUT_TOKENS_PER_VERSE
        assert svc._VERSE_TOKEN_COSTS[112][0] == expected

    def test_missing_chunk_gives_text_plus_output_only(self):
        """Verse with no tafsir chunks: cost = verse text + output allocation."""
        chunks = {}  # no chunks at all
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)
        for cost in svc._VERSE_TOKEN_COSTS[112]:
            assert cost == VERSE_TEXT_TOKENS_PER_VERSE + OUTPUT_TOKENS_PER_VERSE

    def test_prefix_sums_correct(self):
        chunks = _make_chunks([(112, 1, 500, 500), (112, 2, 1000, 1000)])
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)

        prefix = svc._PREFIX_SUMS[112]
        c1 = VERSE_TEXT_TOKENS_PER_VERSE + math.ceil(1000 / CHARS_PER_TOKEN_EN) + OUTPUT_TOKENS_PER_VERSE
        c2 = VERSE_TEXT_TOKENS_PER_VERSE + math.ceil(2000 / CHARS_PER_TOKEN_EN) + OUTPUT_TOKENS_PER_VERSE
        c3 = VERSE_TEXT_TOKENS_PER_VERSE + OUTPUT_TOKENS_PER_VERSE
        c4 = VERSE_TEXT_TOKENS_PER_VERSE + OUTPUT_TOKENS_PER_VERSE

        assert prefix[0] == 0
        assert prefix[1] == c1
        assert prefix[2] == c1 + c2
        assert prefix[3] == c1 + c2 + c3
        assert prefix[4] == c1 + c2 + c3 + c4


# ===================================================================
# compute_max_end_verse — O(1) lookup
# ===================================================================

class TestComputeMaxEnd:
    def setup_method(self):
        _reset_precomputed()

    def test_fallback_when_not_precomputed(self):
        """Before precomputation, falls back to ABSOLUTE_MAX_VERSES."""
        max_end, meta = svc.compute_max_end_verse(112, 1, 4)
        assert max_end == min(1 + ABSOLUTE_MAX_VERSES - 1, 4)
        assert meta["fallback"] is True

    def test_small_surah_allows_full_range(self):
        """Al-Ikhlas with small tafsir chunks should allow all 4 verses."""
        chunks = _make_chunks([
            (112, 1, 400, 400), (112, 2, 400, 400),
            (112, 3, 400, 400), (112, 4, 400, 400),
        ])
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)
        max_end, meta = svc.compute_max_end_verse(112, 1, 4)
        assert max_end == 4
        assert meta["precomputed"] is True

    def test_single_verse_always_allowed(self):
        """Even if a verse has enormous tafsir, at least 1 verse is allowed."""
        # 200K chars = 50K tokens — way over budget
        chunks = _make_chunks([(112, 1, 200_000, 200_000)])
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)
        max_end, _ = svc.compute_max_end_verse(112, 1, 4)
        assert max_end >= 1

    def test_huge_tafsir_restricts_range(self):
        """Huge tafsir chunks should restrict the range significantly."""
        # Each verse: 80K chars per source = 160K chars = 40K tokens + output alloc
        # Per-verse: 250 + 40000 + 3500 = 43750 tokens
        # Budget = ~37800 tokens → only 1 verse fits (even that's over budget)
        meta = {2: {"name": "Al-Baqarah", "verses": 10}}
        chunks = _make_chunks([
            (2, v, 80_000, 80_000) for v in range(1, 11)
        ])
        svc.precompute_verse_budgets(chunks, meta)
        max_end, _ = svc.compute_max_end_verse(2, 1, 10)
        assert max_end == 1

    def test_never_exceeds_absolute_max(self):
        """Even with tiny/no tafsir, should not exceed ABSOLUTE_MAX_VERSES."""
        meta = {37: {"name": "As-Saffat", "verses": 182}}
        chunks = {}  # no tafsir → very cheap per verse
        svc.precompute_verse_budgets(chunks, meta)
        max_end, _ = svc.compute_max_end_verse(37, 1, 182)
        assert max_end <= 1 + ABSOLUTE_MAX_VERSES - 1

    def test_never_exceeds_surah_boundary(self):
        """Max end should never go past the surah's last verse."""
        chunks = {}
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)
        max_end, _ = svc.compute_max_end_verse(112, 1, 4)
        assert max_end <= 4

    def test_start_at_last_verse(self):
        """Starting at the last verse should return that verse."""
        chunks = {}
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)
        max_end, _ = svc.compute_max_end_verse(112, 4, 4)
        assert max_end == 4

    def test_metadata_structure(self):
        """Verify metadata dict has expected keys."""
        chunks = _make_chunks([(112, 1, 400, 400)])
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)
        _, meta = svc.compute_max_end_verse(112, 1, 4)
        assert "precomputed" in meta
        assert "budget_total" in meta
        assert "budget_with_safety" in meta
        assert "budget_used" in meta
        assert "per_verse_costs" in meta
        assert isinstance(meta["per_verse_costs"], list)

    def test_budget_used_matches_prefix_sum(self):
        """Verify budget_used in metadata matches manual calculation."""
        chunks = _make_chunks([
            (112, 1, 2000, 2000), (112, 2, 1000, 1000),
            (112, 3, 500, 500), (112, 4, 500, 500),
        ])
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)
        max_end, meta = svc.compute_max_end_verse(112, 1, 4)

        # Manually compute expected cost
        expected_cost = 0
        for v in range(1, max_end + 1):
            expected_cost += svc._VERSE_TOKEN_COSTS[112][v - 1]

        assert meta["budget_used"] == expected_cost


# ===================================================================
# get_verse_token_cost / get_range_token_cost
# ===================================================================

class TestCostQueries:
    def setup_method(self):
        _reset_precomputed()

    def test_get_verse_token_cost(self):
        chunks = _make_chunks([(112, 1, 4000, 4000)])
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)
        cost = svc.get_verse_token_cost(112, 1)
        expected = VERSE_TEXT_TOKENS_PER_VERSE + math.ceil(8000 / CHARS_PER_TOKEN_EN) + OUTPUT_TOKENS_PER_VERSE
        assert cost == expected

    def test_get_verse_token_cost_unknown_surah(self):
        assert svc.get_verse_token_cost(999, 1) == 0

    def test_get_range_token_cost(self):
        chunks = _make_chunks([
            (112, 1, 2000, 2000), (112, 2, 1000, 1000),
        ])
        svc.precompute_verse_budgets(chunks, SMALL_SURAH_META)

        c1 = VERSE_TEXT_TOKENS_PER_VERSE + math.ceil(4000 / CHARS_PER_TOKEN_EN) + OUTPUT_TOKENS_PER_VERSE
        c2 = VERSE_TEXT_TOKENS_PER_VERSE + math.ceil(2000 / CHARS_PER_TOKEN_EN) + OUTPUT_TOKENS_PER_VERSE

        assert svc.get_range_token_cost(112, 1, 1) == c1
        assert svc.get_range_token_cost(112, 1, 2) == c1 + c2
        assert svc.get_range_token_cost(112, 2, 2) == c2

    def test_get_range_token_cost_unknown_surah(self):
        assert svc.get_range_token_cost(999, 1, 5) == 0


# ===================================================================
# Consistency: brute-force verification
# ===================================================================

class TestBruteForceConsistency:
    def setup_method(self):
        _reset_precomputed()

    def test_precomputed_matches_brute_force(self):
        """Verify every (surah, start) result matches a naive brute-force check."""
        # Build a realistic-ish mock: 20 verses with varying tafsir sizes
        meta = {2: {"name": "Al-Baqarah", "verses": 20}}
        specs = []
        for v in range(1, 21):
            # Sizes vary: v * 1000 chars per source
            specs.append((2, v, v * 1000, v * 800))
        chunks = _make_chunks(specs)
        svc.precompute_verse_budgets(chunks, meta)

        budget = int(VERSE_AND_TAFSIR_BUDGET * SAFETY_FACTOR)

        for start in range(1, 21):
            max_end, _ = svc.compute_max_end_verse(2, start, 20)

            # Brute force
            cost = 0
            bf_max = start
            for v in range(start, min(start + ABSOLUTE_MAX_VERSES, 21)):
                verse_cost = svc._VERSE_TOKEN_COSTS[2][v - 1]
                if cost + verse_cost > budget:
                    break
                cost += verse_cost
                bf_max = v

            assert max_end == bf_max, (
                f"Mismatch at start={start}: precomputed={max_end}, brute_force={bf_max}"
            )
