"""
Token Budget Service — precomputed per-verse costs from actual data.

At startup (after TAFSIR_CHUNKS is loaded from GCS), call
``precompute_verse_budgets()`` once.  This measures the *actual* character
length of every tafsir chunk for every verse across all 114 surahs, converts
to token estimates, builds prefix-sum arrays for O(1) range-cost queries,
and precomputes a max-end lookup table for every (surah, start_verse) pair.

The result is exported to ``backend/data/verse_range_map.json`` — a static,
validated artifact where every verse's maximum range is backed by actual
measured token costs.  The ``/range-limit`` endpoint does a single dict
lookup from this map.
"""

import json
import logging
import math
import os
from datetime import datetime, timezone
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


# ---------------------------------------------------------------------------
# Static range map — export / import
# ---------------------------------------------------------------------------

_RANGE_MAP_FILENAME = "verse_range_map.json"


def _default_range_map_path() -> str:
    """Return the default path for the static range map JSON file."""
    # backend/data/verse_range_map.json
    services_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(services_dir)
    return os.path.join(backend_dir, "data", _RANGE_MAP_FILENAME)


def export_range_map(filepath: str = None) -> str:
    """
    Export the precomputed range map and per-verse costs to a static JSON file.

    Every entry is backed by actual measured tafsir chunk sizes from GCS data.
    The exported file becomes the authoritative, hardcoded source for verse
    range limits.

    Returns the filepath written.
    """
    if not _PRECOMPUTED:
        raise RuntimeError("Cannot export: precomputation has not run yet")

    filepath = filepath or _default_range_map_path()
    budget = int(VERSE_AND_TAFSIR_BUDGET * SAFETY_FACTOR)

    # Count stats
    total_verses = sum(len(costs) for costs in _VERSE_TOKEN_COSTS.values())
    total_with_tafsir = sum(
        1 for costs in _VERSE_TOKEN_COSTS.values()
        for c in costs if c > VERSE_TEXT_TOKENS_PER_VERSE
    )
    constrained_count = sum(
        1 for surah_map in _MAX_END_LOOKUP.values()
        for start, end in surah_map.items()
        if end - start + 1 < ABSOLUTE_MAX_VERSES
    )

    # Build the export structure
    # Keys are strings for JSON compatibility
    export_data = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "description": (
                "Static verse range map. Every entry is the maximum end verse "
                "allowed for a given (surah, start_verse) pair, computed from "
                "actual measured tafsir chunk sizes."
            ),
            "verse_and_tafsir_budget": VERSE_AND_TAFSIR_BUDGET,
            "safety_factor": SAFETY_FACTOR,
            "effective_budget_tokens": budget,
            "absolute_max_verses": ABSOLUTE_MAX_VERSES,
            "verse_text_tokens_per_verse": VERSE_TEXT_TOKENS_PER_VERSE,
            "total_surahs": len(_MAX_END_LOOKUP),
            "total_verses": total_verses,
            "total_with_tafsir_data": total_with_tafsir,
            "budget_constrained_verses": constrained_count,
        },
        "ranges": {},
        "verse_costs": {},
    }

    for surah in sorted(_MAX_END_LOOKUP.keys()):
        surah_key = str(surah)

        # Range map: {start_verse: max_end_verse}
        range_map = _MAX_END_LOOKUP[surah]
        export_data["ranges"][surah_key] = {
            str(start): end for start, end in sorted(range_map.items())
        }

        # Per-verse token costs (0-indexed list)
        costs = _VERSE_TOKEN_COSTS.get(surah, [])
        export_data["verse_costs"][surah_key] = costs

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(export_data, f, indent=None, separators=(",", ":"))

    file_size_kb = os.path.getsize(filepath) / 1024
    logger.info(
        "[TOKEN_BUDGET] Exported static range map to %s (%.1f KB, %d surahs, "
        "%d verses, %d budget-constrained)",
        filepath, file_size_kb, len(_MAX_END_LOOKUP),
        total_verses, constrained_count,
    )
    return filepath


def load_range_map(filepath: str = None) -> bool:
    """
    Load the static range map from a JSON file.

    Populates _MAX_END_LOOKUP, _VERSE_TOKEN_COSTS, and _PREFIX_SUMS from
    the file.  Returns True if loaded successfully.
    """
    global _VERSE_TOKEN_COSTS, _PREFIX_SUMS, _MAX_END_LOOKUP, _PRECOMPUTED

    filepath = filepath or _default_range_map_path()

    if not os.path.exists(filepath):
        logger.info("[TOKEN_BUDGET] No static range map at %s", filepath)
        return False

    try:
        with open(filepath, "r") as f:
            data = json.load(f)

        meta = data.get("_meta", {})
        ranges = data.get("ranges", {})
        verse_costs = data.get("verse_costs", {})

        if not ranges:
            logger.warning("[TOKEN_BUDGET] Static range map is empty")
            return False

        # Populate module-level data structures
        loaded_max_end = {}
        loaded_costs = {}
        loaded_prefix = {}

        for surah_key, range_map in ranges.items():
            surah = int(surah_key)
            loaded_max_end[surah] = {
                int(start): end for start, end in range_map.items()
            }

        for surah_key, costs in verse_costs.items():
            surah = int(surah_key)
            loaded_costs[surah] = costs

            # Rebuild prefix sums
            prefix = [0]
            for c in costs:
                prefix.append(prefix[-1] + c)
            loaded_prefix[surah] = prefix

        _MAX_END_LOOKUP = loaded_max_end
        _VERSE_TOKEN_COSTS = loaded_costs
        _PREFIX_SUMS = loaded_prefix
        _PRECOMPUTED = True

        total_verses = sum(len(c) for c in loaded_costs.values())
        logger.info(
            "[TOKEN_BUDGET] Loaded static range map from %s "
            "(generated: %s, %d surahs, %d verses)",
            filepath,
            meta.get("generated_at", "unknown"),
            len(loaded_max_end),
            total_verses,
        )
        return True

    except Exception as e:
        logger.error("[TOKEN_BUDGET] Failed to load static range map: %s", e)
        return False


def get_range_map_info() -> dict:
    """Return summary info about the loaded range map (for debug endpoints)."""
    if not _PRECOMPUTED:
        return {"loaded": False}

    budget = int(VERSE_AND_TAFSIR_BUDGET * SAFETY_FACTOR)
    total_verses = sum(len(c) for c in _VERSE_TOKEN_COSTS.values())
    constrained = sum(
        1 for surah_map in _MAX_END_LOOKUP.values()
        for start, end in surah_map.items()
        if end - start + 1 < ABSOLUTE_MAX_VERSES
    )

    return {
        "loaded": True,
        "total_surahs": len(_MAX_END_LOOKUP),
        "total_verses": total_verses,
        "effective_budget_tokens": budget,
        "budget_constrained_verses": constrained,
        "static_file_exists": os.path.exists(_default_range_map_path()),
    }
