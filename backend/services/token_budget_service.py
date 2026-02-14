"""
Token Budget Service — precomputed per-verse costs from actual data.

At startup (after TAFSIR_CHUNKS is loaded from GCS), call
``precompute_verse_budgets()`` once.  This measures the *actual* character
length of every tafsir chunk for every verse across all 114 surahs, converts
to token estimates, builds prefix-sum arrays for O(1) range-cost queries,
and precomputes a max-end lookup table for every (surah, start_verse) pair.

The ``/range-limit`` endpoint then does a single dict lookup — no estimation,
no heuristics, no per-request computation.
"""

import logging
import math
from typing import Dict, Optional, Tuple

from config.token_budget import (
    ABSOLUTE_MAX_VERSES,
    CHARS_PER_TOKEN_AR,
    CHARS_PER_TOKEN_EN,
    CHARS_PER_TOKEN_MIXED,
    SAFETY_FACTOR,
    VERSE_AND_TAFSIR_BUDGET,
    VERSE_TEXT_TOKENS_PER_VERSE,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level precomputed data (populated by precompute_verse_budgets)
# ---------------------------------------------------------------------------

# {surah_num: [cost_v1, cost_v2, ...]}  — per-verse token cost (0-indexed)
_VERSE_TOKEN_COSTS: Dict[int, list] = {}

# {surah_num: [0, sum_v1, sum_v1+v2, ...]}  — prefix sums (length = num_verses + 1)
_PREFIX_SUMS: Dict[int, list] = {}

# {surah_num: {start_verse: max_end_verse}}  — precomputed O(1) lookup
_MAX_END_LOOKUP: Dict[int, Dict[int, int]] = {}

# Set to True after precomputation completes
_PRECOMPUTED: bool = False


# ---------------------------------------------------------------------------
# Token estimation helpers (kept for general use and tests)
# ---------------------------------------------------------------------------

def estimate_tokens_for_text(text: str, lang: str = "mixed") -> int:
    """Estimate token count for a text string based on language."""
    if not text:
        return 0
    ratio = {
        "arabic": CHARS_PER_TOKEN_AR,
        "english": CHARS_PER_TOKEN_EN,
        "mixed": CHARS_PER_TOKEN_MIXED,
    }.get(lang, CHARS_PER_TOKEN_MIXED)
    return math.ceil(len(text) / ratio)


# ---------------------------------------------------------------------------
# Precomputation — called once at startup after TAFSIR_CHUNKS is populated
# ---------------------------------------------------------------------------

def precompute_verse_budgets(
    tafsir_chunks: dict,
    quran_metadata: dict,
) -> None:
    """
    Precompute per-verse token costs from *actual* in-memory tafsir data.

    For every verse in every surah:
      1. Look up actual tafsir chunk text for ibn-kathir and al-qurtubi.
      2. Convert char length → tokens (English ratio: 4 chars/token).
      3. Add fixed verse-text allowance (250 tokens for Arabic/English/transliteration).
      4. Build prefix sums per surah for O(1) range-cost queries.
      5. Precompute max-end-verse for every (surah, start) pair.

    Scholarly source cost is accounted for separately as a fixed budget
    reservation (SCHOLARLY_RESERVE_TOKENS = 3500) because scholarly content
    is capped at MAX_TOTAL_SCHOLARLY_CHARS = 12000 per query regardless of
    verse count.
    """
    global _VERSE_TOKEN_COSTS, _PREFIX_SUMS, _MAX_END_LOOKUP, _PRECOMPUTED

    budget = int(VERSE_AND_TAFSIR_BUDGET * SAFETY_FACTOR)
    total_verses = 0
    total_with_tafsir = 0

    for surah, meta in sorted(quran_metadata.items()):
        max_verse = meta["verses"]
        costs = []

        for v in range(1, max_verse + 1):
            # --- Measure actual tafsir chunk sizes ---
            tafsir_chars = 0
            for src in ("ibn-kathir", "al-qurtubi"):
                chunk = tafsir_chunks.get(f"{src}:{surah}:{v}")
                if chunk and isinstance(chunk, str):
                    tafsir_chars += len(chunk)

            tafsir_tokens = math.ceil(tafsir_chars / CHARS_PER_TOKEN_EN) if tafsir_chars > 0 else 0

            # --- Per-verse total: actual tafsir + fixed verse-text allowance ---
            verse_total = VERSE_TEXT_TOKENS_PER_VERSE + tafsir_tokens
            costs.append(verse_total)

            total_verses += 1
            if tafsir_chars > 0:
                total_with_tafsir += 1

        _VERSE_TOKEN_COSTS[surah] = costs

        # --- Build prefix sums ---
        # prefix[0] = 0, prefix[i] = sum(costs[0..i-1])
        # Range cost for verses [start, end] = prefix[end] - prefix[start-1]
        prefix = [0]
        for c in costs:
            prefix.append(prefix[-1] + c)
        _PREFIX_SUMS[surah] = prefix

        # --- Precompute max end verse for every start ---
        max_end_map = {}
        for start in range(1, max_verse + 1):
            best_end = start  # always allow at least 1 verse
            cap = min(start + ABSOLUTE_MAX_VERSES, max_verse + 1)
            for end in range(start, cap):
                range_cost = prefix[end] - prefix[start - 1]
                if range_cost <= budget:
                    best_end = end
                else:
                    break
            max_end_map[start] = best_end
        _MAX_END_LOOKUP[surah] = max_end_map

    _PRECOMPUTED = True
    logger.info(
        "[TOKEN_BUDGET] Precomputed budgets for %d surahs, %d verses "
        "(%d with tafsir data). Safety budget = %d tokens.",
        len(quran_metadata), total_verses, total_with_tafsir, budget,
    )


def is_precomputed() -> bool:
    """Return True if precomputation has been run."""
    return _PRECOMPUTED


# ---------------------------------------------------------------------------
# Public API — called by /range-limit endpoint
# ---------------------------------------------------------------------------

def compute_max_end_verse(
    surah: int,
    start_verse: int,
    surah_max_verse: int,
) -> Tuple[int, Dict]:
    """
    Look up precomputed max end verse.  O(1) dict lookup.

    Falls back to ABSOLUTE_MAX_VERSES if precomputation hasn't run yet
    (should only happen if GCS loading failed at startup).
    """
    if not _PRECOMPUTED:
        fallback_end = min(start_verse + ABSOLUTE_MAX_VERSES - 1, surah_max_verse)
        return fallback_end, {"precomputed": False, "fallback": True}

    surah_lookup = _MAX_END_LOOKUP.get(surah)
    if not surah_lookup:
        fallback_end = min(start_verse + ABSOLUTE_MAX_VERSES - 1, surah_max_verse)
        return fallback_end, {"precomputed": False, "fallback": True}

    max_end = surah_lookup.get(start_verse, start_verse)

    # --- Build metadata for debugging / logging ---
    budget = int(VERSE_AND_TAFSIR_BUDGET * SAFETY_FACTOR)
    costs = _VERSE_TOKEN_COSTS.get(surah, [])
    prefix = _PREFIX_SUMS.get(surah, [])

    per_verse = []
    if costs and 1 <= start_verse <= len(costs):
        for v in range(start_verse, max_end + 1):
            idx = v - 1
            if idx < len(costs):
                per_verse.append({"verse": v, "tokens": costs[idx]})

    budget_used = 0
    if prefix and 1 <= start_verse and max_end < len(prefix):
        budget_used = prefix[max_end] - prefix[start_verse - 1]

    metadata = {
        "precomputed": True,
        "budget_total": VERSE_AND_TAFSIR_BUDGET,
        "budget_with_safety": budget,
        "budget_used": budget_used,
        "per_verse_costs": per_verse,
    }

    return max_end, metadata


def get_verse_token_cost(surah: int, verse: int) -> int:
    """Return the precomputed token cost for a single verse.  0 if unknown."""
    costs = _VERSE_TOKEN_COSTS.get(surah, [])
    idx = verse - 1
    if 0 <= idx < len(costs):
        return costs[idx]
    return 0


def get_range_token_cost(surah: int, start: int, end: int) -> int:
    """Return the precomputed token cost for a verse range.  O(1) via prefix sums."""
    prefix = _PREFIX_SUMS.get(surah)
    if not prefix or start < 1 or end >= len(prefix):
        return 0
    return prefix[end] - prefix[start - 1]
