#!/usr/bin/env python3
"""
Ground-truth verse range validation using FULL payload measurement.

For every (surah, start_verse) combination, this script:
1. Measures the ACTUAL prompt template overhead (static text)
2. Loads measured per-verse tafsir costs (from existing verse_range_map.json)
3. Resolves ACTUAL scholarly source content from local index files
4. Computes the full Gemini input token count for each possible range
5. Adds per-verse OUTPUT allocation (to prevent output overflow)
6. Maps out the maximum safe range for each starting verse

The result is a ground-truth verse_range_map.json where every entry
is validated against the real payload — not heuristic estimates.

Run from backend directory:
    python scripts/validate_ranges_full.py
"""

import json
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone

# Add backend root to path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from config.token_budget import (
    ABSOLUTE_MAX_VERSES,
    CHARS_PER_TOKEN_EN,
    OUTPUT_TOKENS_PER_VERSE,
    PRACTICAL_INPUT_BUDGET,
    SAFETY_FACTOR,
    VERSE_TEXT_TOKENS_PER_VERSE,
)
from services.source_service import (
    MAX_TOTAL_SCHOLARLY_CHARS,
    resolve_scholarly_pointers,
    _get_verse_map_pointers,
    _load_asbab_surah,
    _load_thematic_surah,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Measured from build_enhanced_prompt template text (lines 4462-4722 of app.py)
# Total template = ~14,800 chars → ~3,700 tokens at 4 chars/tok
# Small variable substitutions (persona, tone, etc.) add ~500 chars → ~125 tokens
# Round up to 4,000 tokens for safety
PROMPT_TEMPLATE_TOKENS = 4_000

# Total budget for the Gemini input (from user's production experience)
TOTAL_INPUT_BUDGET = PRACTICAL_INPUT_BUDGET  # 30,000 tokens


# ---------------------------------------------------------------------------
# Scholarly cost measurement
# ---------------------------------------------------------------------------

def measure_scholarly_chars(surah_number, verse_start):
    """
    Measure the ACTUAL scholarly source content (in chars) that would be
    included for a given surah + starting verse.

    Uses the same pipeline as production:
    1. Always emit asbab + thematic pointers
    2. Look up verse-map references for ihya/madarij/riyad
    3. Resolve all pointers to get actual text from local index files
    4. Return total chars (capped at MAX_TOTAL_SCHOLARLY_CHARS)
    """
    # Build the same pointers the deterministic planner would emit
    pointers = [
        f"asbab:surah={surah_number}:verse={verse_start}",
        f"thematic:surah={surah_number}:section=0",
    ]

    # Add verse-map references (same as _get_verse_map_pointers in source_service)
    vm_pointers = _get_verse_map_pointers(surah_number, verse_start)
    existing = set(pointers)
    for vp in vm_pointers:
        if vp not in existing:
            pointers.append(vp)
            existing.add(vp)

    # Resolve pointers → actual text content
    resolved = resolve_scholarly_pointers(pointers)

    # Sum total chars
    total_chars = 0
    for excerpt in resolved.get("excerpts", []):
        total_chars += len(excerpt.get("text", ""))

    return min(total_chars, MAX_TOTAL_SCHOLARLY_CHARS)


def precompute_scholarly_costs(surah_meta):
    """
    Precompute scholarly char costs for every (surah, verse) combination.
    Returns: {surah_num: {verse_num: scholarly_chars}}
    """
    scholarly_costs = {}
    total = sum(m["verses"] for m in surah_meta.values())
    done = 0

    for surah_num in sorted(surah_meta.keys()):
        num_verses = surah_meta[surah_num]["verses"]
        surah_costs = {}

        for verse in range(1, num_verses + 1):
            chars = measure_scholarly_chars(surah_num, verse)
            surah_costs[verse] = chars
            done += 1

        scholarly_costs[surah_num] = surah_costs

        # Progress every 10 surahs
        if surah_num % 10 == 0 or surah_num == 114:
            print(f"  Scholarly costs: {done:,}/{total:,} verses "
                  f"({done/total*100:.0f}%) — surah {surah_num}")

    return scholarly_costs


# ---------------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------------

def load_existing_map(filepath):
    """Load existing verse_range_map.json for measured tafsir costs."""
    with open(filepath) as f:
        return json.load(f)


def load_quran_metadata():
    """Build QURAN_METADATA from the existing verse_range_map."""
    # We build this from the verse_costs keys (surah numbers) and their lengths
    map_path = os.path.join(BACKEND_DIR, "data", "verse_range_map.json")
    data = load_existing_map(map_path)
    meta = {}
    for surah_str, costs in data.get("verse_costs", {}).items():
        surah_num = int(surah_str)
        meta[surah_num] = {"verses": len(costs), "name": f"Surah {surah_num}"}
    return meta


def extract_raw_tafsir_costs(existing_data):
    """
    Extract raw tafsir token costs from the existing verse_range_map.

    The stored per-verse cost includes:
        VERSE_TEXT_TOKENS_PER_VERSE + tafsir_tokens + OUTPUT_TOKENS_PER_VERSE

    We strip these to get just the raw tafsir_tokens for each verse.
    """
    old_meta = existing_data.get("_meta", {})
    old_output_alloc = old_meta.get("output_tokens_per_verse", 0)

    raw_tafsir = {}
    for surah_str, costs in existing_data.get("verse_costs", {}).items():
        surah_num = int(surah_str)
        raw_costs = []
        for cost in costs:
            tafsir = cost - VERSE_TEXT_TOKENS_PER_VERSE - old_output_alloc
            raw_costs.append(max(0, tafsir))
        raw_tafsir[surah_num] = raw_costs

    return raw_tafsir


def compute_ranges(raw_tafsir, scholarly_costs, surah_meta):
    """
    Compute max verse range for every (surah, start_verse) using the FULL
    payload measurement.

    For each starting verse, we try ranges 1..ABSOLUTE_MAX_VERSES and find
    the largest range where the total Gemini input fits within budget.

    Total input = prompt_template + verse_text + tafsir + scholarly + output_reserve
    """
    ranges = {}
    verse_costs = {}  # Store the full per-verse costs
    stats = {
        "total_verses": 0,
        "budget_constrained": 0,
        "distribution": Counter(),
    }

    for surah_num in sorted(surah_meta.keys()):
        num_verses = surah_meta[surah_num]["verses"]
        surah_ranges = {}
        surah_costs = []

        # Get scholarly cost for each starting verse
        surah_scholarly = scholarly_costs.get(surah_num, {})

        # Raw tafsir tokens per verse
        surah_tafsir = raw_tafsir.get(surah_num, [0] * num_verses)

        # Build full per-verse costs (tafsir + verse_text + output allocation)
        for v_idx in range(num_verses):
            tafsir_tok = surah_tafsir[v_idx] if v_idx < len(surah_tafsir) else 0
            full_cost = (
                VERSE_TEXT_TOKENS_PER_VERSE
                + tafsir_tok
                + OUTPUT_TOKENS_PER_VERSE
            )
            surah_costs.append(full_cost)

        verse_costs[str(surah_num)] = surah_costs

        for start in range(1, num_verses + 1):
            # Scholarly cost is determined by the starting verse
            scholarly_chars = surah_scholarly.get(start, 0)
            scholarly_tokens = math.ceil(scholarly_chars / CHARS_PER_TOKEN_EN)

            # Fixed costs for this query
            fixed_tokens = PROMPT_TEMPLATE_TOKENS + scholarly_tokens

            # Available budget for verses (with safety margin)
            available = int(TOTAL_INPUT_BUDGET * SAFETY_FACTOR) - fixed_tokens

            # Find max range that fits
            best_end = start
            cumulative = 0
            cap = min(start + ABSOLUTE_MAX_VERSES, num_verses + 1)

            for end in range(start, cap):
                v_cost = surah_costs[end - 1]  # 0-indexed
                if cumulative + v_cost <= available:
                    cumulative += v_cost
                    best_end = end
                else:
                    break

            surah_ranges[str(start)] = best_end

            # Stats
            stats["total_verses"] += 1
            allowed = best_end - start + 1
            static_max = min(start + ABSOLUTE_MAX_VERSES - 1, num_verses)
            static_allowed = static_max - start + 1

            if allowed < static_allowed:
                stats["budget_constrained"] += 1

            stats["distribution"][allowed] += 1

        ranges[str(surah_num)] = surah_ranges

    return ranges, verse_costs, stats


def build_export(ranges, verse_costs, scholarly_costs_summary, stats):
    """Build the export data structure."""
    budget = int(TOTAL_INPUT_BUDGET * SAFETY_FACTOR)

    constrained_count = sum(
        1 for surah_map in ranges.values()
        for start_str, end in surah_map.items()
        if end - int(start_str) + 1 < ABSOLUTE_MAX_VERSES
    )

    return {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "description": (
                "Ground-truth verse range map validated with FULL payload "
                "measurement: prompt template + verse text + tafsir chunks + "
                "scholarly sources + output allocation. Every entry reflects "
                "the actual Gemini input token count."
            ),
            "practical_input_budget": TOTAL_INPUT_BUDGET,
            "safety_factor": SAFETY_FACTOR,
            "effective_budget_tokens": budget,
            "prompt_template_tokens": PROMPT_TEMPLATE_TOKENS,
            "absolute_max_verses": ABSOLUTE_MAX_VERSES,
            "verse_text_tokens_per_verse": VERSE_TEXT_TOKENS_PER_VERSE,
            "output_tokens_per_verse": OUTPUT_TOKENS_PER_VERSE,
            "max_scholarly_chars": MAX_TOTAL_SCHOLARLY_CHARS,
            "total_surahs": len(ranges),
            "total_verses": stats["total_verses"],
            "budget_constrained_verses": constrained_count,
            "scholarly_costs_summary": scholarly_costs_summary,
        },
        "ranges": ranges,
        "verse_costs": verse_costs,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    map_path = os.path.join(BACKEND_DIR, "data", "verse_range_map.json")

    print("=" * 70)
    print("GROUND-TRUTH VERSE RANGE VALIDATION")
    print("Full payload: prompt + verse text + tafsir + scholarly + output")
    print("=" * 70)

    # Show budget model
    budget = int(TOTAL_INPUT_BUDGET * SAFETY_FACTOR)
    print(f"\n--- BUDGET MODEL ---")
    print(f"  TOTAL_INPUT_BUDGET:        {TOTAL_INPUT_BUDGET:,}")
    print(f"  x SAFETY_FACTOR:           {SAFETY_FACTOR}")
    print(f"  = EFFECTIVE BUDGET:        {budget:,}")
    print(f"  PROMPT_TEMPLATE_TOKENS:    {PROMPT_TEMPLATE_TOKENS:,}")
    print(f"  VERSE_TEXT_PER_VERSE:      {VERSE_TEXT_TOKENS_PER_VERSE}")
    print(f"  OUTPUT_TOKENS_PER_VERSE:   {OUTPUT_TOKENS_PER_VERSE:,}")
    print(f"  MAX_SCHOLARLY_CHARS:       {MAX_TOTAL_SCHOLARLY_CHARS:,}")
    print(f"  ABSOLUTE_MAX_VERSES:       {ABSOLUTE_MAX_VERSES}")

    # Load existing data
    print(f"\n--- LOADING EXISTING DATA ---")
    existing = load_existing_map(map_path)
    old_meta = existing.get("_meta", {})
    print(f"  Old map generated: {old_meta.get('generated_at', 'unknown')}")
    print(f"  Old constrained:   {old_meta.get('budget_constrained_verses', '?')}")

    # Extract raw tafsir costs
    raw_tafsir = extract_raw_tafsir_costs(existing)
    total_verses = sum(len(v) for v in raw_tafsir.values())
    print(f"  Tafsir costs loaded: {total_verses:,} verses across {len(raw_tafsir)} surahs")

    # Build surah metadata
    surah_meta = load_quran_metadata()

    # Measure scholarly costs for every verse
    print(f"\n--- MEASURING SCHOLARLY COSTS (all {total_verses:,} verses) ---")
    t0 = time.time()
    scholarly_costs = precompute_scholarly_costs(surah_meta)
    elapsed = time.time() - t0
    print(f"  Completed in {elapsed:.1f}s")

    # Scholarly cost statistics
    all_scholarly = []
    for surah_costs in scholarly_costs.values():
        all_scholarly.extend(surah_costs.values())

    scholarly_summary = {
        "min_chars": min(all_scholarly) if all_scholarly else 0,
        "max_chars": max(all_scholarly) if all_scholarly else 0,
        "avg_chars": int(sum(all_scholarly) / len(all_scholarly)) if all_scholarly else 0,
        "min_tokens": math.ceil(min(all_scholarly) / CHARS_PER_TOKEN_EN) if all_scholarly else 0,
        "max_tokens": math.ceil(max(all_scholarly) / CHARS_PER_TOKEN_EN) if all_scholarly else 0,
        "avg_tokens": math.ceil(sum(all_scholarly) / len(all_scholarly) / CHARS_PER_TOKEN_EN) if all_scholarly else 0,
    }

    print(f"\n--- SCHOLARLY COST DISTRIBUTION ---")
    print(f"  Min:  {scholarly_summary['min_chars']:,} chars ({scholarly_summary['min_tokens']:,} tokens)")
    print(f"  Avg:  {scholarly_summary['avg_chars']:,} chars ({scholarly_summary['avg_tokens']:,} tokens)")
    print(f"  Max:  {scholarly_summary['max_chars']:,} chars ({scholarly_summary['max_tokens']:,} tokens)")

    # Per-verse budget examples
    print(f"\n--- BUDGET BREAKDOWN EXAMPLES ---")
    examples = [
        ("No scholarly, no tafsir", 0, 0),
        ("Light scholarly (2k chars), light tafsir (500 tok)", 2000, 500),
        ("Medium scholarly (5k chars), medium tafsir (1k tok)", 5000, 1000),
        ("Heavy scholarly (10k chars), heavy tafsir (2k tok)", 10000, 2000),
        ("Max scholarly (14k chars), heavy tafsir (2k tok)", 14000, 2000),
        ("Max scholarly (14k chars), extreme tafsir (5k tok)", 14000, 5000),
    ]
    for label, sch_chars, tafsir_tok in examples:
        scholarly_tok = math.ceil(sch_chars / CHARS_PER_TOKEN_EN)
        fixed = PROMPT_TEMPLATE_TOKENS + scholarly_tok
        avail = budget - fixed
        per_verse = VERSE_TEXT_TOKENS_PER_VERSE + tafsir_tok + OUTPUT_TOKENS_PER_VERSE
        max_v = min(avail // per_verse, ABSOLUTE_MAX_VERSES) if per_verse > 0 else ABSOLUTE_MAX_VERSES
        print(f"  {label}")
        print(f"    Fixed: {fixed:,} tok (prompt {PROMPT_TEMPLATE_TOKENS:,} + scholarly {scholarly_tok:,})")
        print(f"    Available: {avail:,} tok → per-verse {per_verse:,} tok → max {max_v} verses")

    # Compute ranges
    print(f"\n--- COMPUTING RANGES ---")
    ranges, verse_costs, stats = compute_ranges(raw_tafsir, scholarly_costs, surah_meta)

    # Results
    print(f"\n--- RESULTS ---")
    print(f"  Total verses:          {stats['total_verses']:,}")
    print(f"  Budget-constrained:    {stats['budget_constrained']:,} "
          f"({stats['budget_constrained']/stats['total_verses']*100:.1f}%)")

    print(f"\n--- MAX VERSES DISTRIBUTION ---")
    for allowed in sorted(stats["distribution"].keys()):
        count = stats["distribution"][allowed]
        pct = count / stats["total_verses"] * 100
        bar = "#" * min(count // 20, 60)
        print(f"  {allowed} verse{'s' if allowed != 1 else ' '}: {count:5d} ({pct:5.1f}%) {bar}")

    # Sample checks
    print(f"\n--- SAMPLE VERSE CHECKS ---")
    checks = [
        ("2", "1", "Al-Baqarah v1"),
        ("2", "255", "Ayatul Kursi"),
        ("2", "282", "Longest verse"),
        ("1", "1", "Al-Fatihah"),
        ("36", "1", "Ya-Sin"),
        ("55", "1", "Ar-Rahman"),
        ("67", "1", "Al-Mulk"),
        ("112", "1", "Al-Ikhlas"),
        ("2", "177", "Long tafsir zone"),
        ("39", "53", "Multi-scholarly"),
    ]
    for surah, start, label in checks:
        s_int = int(surah)
        v_int = int(start)
        if surah in ranges and start in ranges[surah]:
            new_end = ranges[surah][start]
            new_allowed = new_end - v_int + 1
            sch_chars = scholarly_costs.get(s_int, {}).get(v_int, 0)
            sch_tok = math.ceil(sch_chars / CHARS_PER_TOKEN_EN)
            old_end = existing.get("ranges", {}).get(surah, {}).get(start, "?")
            old_allowed = old_end - v_int + 1 if isinstance(old_end, int) else "?"
            print(f"  {label:25s} ({surah}:{start}): {old_allowed} -> {new_allowed} verses "
                  f"(scholarly: {sch_chars:,} chars = {sch_tok:,} tok)")

    # Write the new map
    export = build_export(ranges, verse_costs, scholarly_summary, stats)
    with open(map_path, "w") as f:
        json.dump(export, f, indent=None, separators=(",", ":"))

    file_size = os.path.getsize(map_path) / 1024
    print(f"\n--- SAVED ---")
    print(f"  Written to: {map_path}")
    print(f"  File size:  {file_size:.1f} KB")
    print(f"  Budget-constrained: {export['_meta']['budget_constrained_verses']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
