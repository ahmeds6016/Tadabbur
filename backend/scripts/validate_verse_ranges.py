#!/usr/bin/env python3
"""
Validate and regenerate the verse range map with the updated budget model.

This script:
1. Loads the existing verse_range_map.json (which has actual measured tafsir costs)
2. Recomputes max verse ranges using the NEW budget model that includes
   per-verse output allocation (OUTPUT_TOKENS_PER_VERSE)
3. Outputs statistics showing how ranges changed
4. Writes the updated verse_range_map.json

Run from backend directory:
    python scripts/validate_verse_ranges.py
"""

import json
import math
import os
import sys
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
    PROMPT_OVERHEAD_TOKENS,
    SCHOLARLY_RESERVE_TOKENS,
    SAFETY_FACTOR,
    VERSE_AND_TAFSIR_BUDGET,
    VERSE_TEXT_TOKENS_PER_VERSE,
)


def load_existing_map(filepath):
    """Load the existing verse_range_map.json to get measured tafsir costs."""
    with open(filepath) as f:
        return json.load(f)


def recompute_ranges(existing_data):
    """
    Recompute all verse ranges using the new budget model.

    Uses the existing measured tafsir costs (from GCS data) but applies
    the updated per-verse cost formula that includes output allocation.
    """
    old_costs = existing_data.get("verse_costs", {})
    old_meta = existing_data.get("_meta", {})
    old_ranges = existing_data.get("ranges", {})

    budget = int(VERSE_AND_TAFSIR_BUDGET * SAFETY_FACTOR)

    new_ranges = {}
    new_costs = {}
    stats = {
        "total_verses": 0,
        "total_with_tafsir": 0,
        "budget_constrained": 0,
        "surah_boundary_only": 0,
        "distribution": Counter(),
        "changed_from_old": 0,
    }

    # Detect what output allocation the loaded map was generated with
    old_output_alloc = old_meta.get("output_tokens_per_verse", 0)

    for surah_key in sorted(old_costs.keys(), key=int):
        old_verse_costs = old_costs[surah_key]
        surah_max = len(old_verse_costs)

        # Recompute per-verse costs with the current output allocation
        # Strip the old formula components to get raw tafsir tokens:
        #   old_cost = 250 (verse text) + tafsir_tokens + old_output_alloc
        # Then apply the new formula:
        #   new_cost = 250 (verse text) + tafsir_tokens + OUTPUT_TOKENS_PER_VERSE
        new_verse_costs = []
        for old_cost in old_verse_costs:
            raw_tafsir = old_cost - 250 - old_output_alloc
            if raw_tafsir < 0:
                raw_tafsir = 0

            new_cost = VERSE_TEXT_TOKENS_PER_VERSE + raw_tafsir + OUTPUT_TOKENS_PER_VERSE
            new_verse_costs.append(new_cost)

        new_costs[surah_key] = new_verse_costs

        # Build prefix sums
        prefix = [0]
        for c in new_verse_costs:
            prefix.append(prefix[-1] + c)

        # Compute max end verse for every start
        range_map = {}
        for start in range(1, surah_max + 1):
            best_end = start
            cap = min(start + ABSOLUTE_MAX_VERSES, surah_max + 1)
            for end in range(start, cap):
                range_cost = prefix[end] - prefix[start - 1]
                if range_cost <= budget:
                    best_end = end
                else:
                    break
            range_map[str(start)] = best_end

            # Stats
            stats["total_verses"] += 1
            allowed = best_end - start + 1
            static_max = min(start + ABSOLUTE_MAX_VERSES - 1, surah_max)
            static_allowed = static_max - start + 1

            if raw_tafsir > 0:
                stats["total_with_tafsir"] += 1

            if allowed < static_allowed:
                stats["budget_constrained"] += 1
            elif allowed < ABSOLUTE_MAX_VERSES and surah_max - start + 1 < ABSOLUTE_MAX_VERSES:
                stats["surah_boundary_only"] += 1

            stats["distribution"][allowed] += 1

            # Check if it changed from old map
            old_range = old_ranges.get(surah_key, {}).get(str(start))
            if old_range is not None and old_range != best_end:
                stats["changed_from_old"] += 1

        new_ranges[surah_key] = range_map

    return new_ranges, new_costs, stats, budget


def build_export(new_ranges, new_costs, stats, budget):
    """Build the export data structure."""
    constrained_count = sum(
        1 for surah_map in new_ranges.values()
        for start_str, end in surah_map.items()
        if end - int(start_str) + 1 < ABSOLUTE_MAX_VERSES
    )

    return {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "description": (
                "Static verse range map with per-verse output allocation. "
                "Every entry accounts for tafsir INPUT cost + Gemini OUTPUT depth "
                "to prevent quality degradation and token overflow."
            ),
            "verse_and_tafsir_budget": VERSE_AND_TAFSIR_BUDGET,
            "safety_factor": SAFETY_FACTOR,
            "effective_budget_tokens": budget,
            "absolute_max_verses": ABSOLUTE_MAX_VERSES,
            "verse_text_tokens_per_verse": VERSE_TEXT_TOKENS_PER_VERSE,
            "output_tokens_per_verse": OUTPUT_TOKENS_PER_VERSE,
            "total_surahs": len(new_ranges),
            "total_verses": stats["total_verses"],
            "total_with_tafsir_data": stats["total_with_tafsir"],
            "budget_constrained_verses": constrained_count,
        },
        "ranges": new_ranges,
        "verse_costs": new_costs,
    }


def main():
    map_path = os.path.join(BACKEND_DIR, "data", "verse_range_map.json")

    print("=" * 60)
    print("VERSE RANGE VALIDATION & REGENERATION")
    print("=" * 60)

    # Show new budget model
    budget = int(VERSE_AND_TAFSIR_BUDGET * SAFETY_FACTOR)
    print(f"\n--- NEW BUDGET MODEL ---")
    print(f"  PRACTICAL_INPUT_BUDGET:    {PRACTICAL_INPUT_BUDGET:,}")
    print(f"  - PROMPT_OVERHEAD:         {PROMPT_OVERHEAD_TOKENS:,}")
    print(f"  - SCHOLARLY_RESERVE:       {SCHOLARLY_RESERVE_TOKENS:,}")
    print(f"  = VERSE_AND_TAFSIR_BUDGET: {VERSE_AND_TAFSIR_BUDGET:,}")
    print(f"  x SAFETY_FACTOR:           {SAFETY_FACTOR}")
    print(f"  = EFFECTIVE BUDGET:        {budget:,}")
    print(f"  ABSOLUTE_MAX_VERSES:       {ABSOLUTE_MAX_VERSES}")
    print(f"  OUTPUT_TOKENS_PER_VERSE:   {OUTPUT_TOKENS_PER_VERSE:,}")
    print(f"  VERSE_TEXT_PER_VERSE:      {VERSE_TEXT_TOKENS_PER_VERSE}")

    # Per-verse examples
    print(f"\n--- PER-VERSE COST EXAMPLES ---")
    examples = [
        ("No tafsir", 0),
        ("Light tafsir (500 tok)", 500),
        ("Medium tafsir (1000 tok)", 1000),
        ("Heavy tafsir (2000 tok)", 2000),
        ("Very heavy (3000 tok)", 3000),
        ("Extreme (5000 tok)", 5000),
    ]
    for label, tafsir_tok in examples:
        verse_cost = VERSE_TEXT_TOKENS_PER_VERSE + tafsir_tok + OUTPUT_TOKENS_PER_VERSE
        max_verses = min(budget // verse_cost, ABSOLUTE_MAX_VERSES) if verse_cost > 0 else ABSOLUTE_MAX_VERSES
        print(f"  {label:30s}: {verse_cost:,} tok/verse -> max {max_verses} verses")

    # Load existing map
    print(f"\n--- LOADING EXISTING MAP ---")
    existing = load_existing_map(map_path)
    old_meta = existing.get("_meta", {})
    print(f"  Generated: {old_meta.get('generated_at', 'unknown')}")
    print(f"  Old budget: {old_meta.get('effective_budget_tokens', '?'):,}")
    print(f"  Old max: {old_meta.get('absolute_max_verses', '?')}")
    print(f"  Old constrained: {old_meta.get('budget_constrained_verses', '?')}")

    # Recompute
    print(f"\n--- RECOMPUTING RANGES ---")
    new_ranges, new_costs, stats, budget = recompute_ranges(existing)

    # Stats
    print(f"\n--- RESULTS ---")
    print(f"  Total verses:          {stats['total_verses']:,}")
    print(f"  Budget-constrained:    {stats['budget_constrained']:,} "
          f"({stats['budget_constrained']/stats['total_verses']*100:.1f}%)")
    print(f"  Surah-boundary only:   {stats['surah_boundary_only']:,}")
    print(f"  Changed from old map:  {stats['changed_from_old']:,}")

    print(f"\n--- MAX VERSES DISTRIBUTION ---")
    for allowed in sorted(stats["distribution"].keys()):
        count = stats["distribution"][allowed]
        bar = "#" * min(count // 20, 60)
        print(f"  {allowed} verse{'s' if allowed != 1 else ' '}: {count:5d} ({count/stats['total_verses']*100:5.1f}%) {bar}")

    # Sample some key verses
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
    ]
    for surah, start, label in checks:
        if surah in new_ranges and start in new_ranges[surah]:
            new_end = new_ranges[surah][start]
            old_end = existing.get("ranges", {}).get(surah, {}).get(start, "?")
            new_allowed = new_end - int(start) + 1
            old_allowed = old_end - int(start) + 1 if isinstance(old_end, int) else "?"
            print(f"  {label:25s} ({surah}:{start}): {old_allowed} -> {new_allowed} verses")

    # Write the new map
    export = build_export(new_ranges, new_costs, stats, budget)
    with open(map_path, "w") as f:
        json.dump(export, f, indent=None, separators=(",", ":"))

    file_size = os.path.getsize(map_path) / 1024
    print(f"\n--- SAVED ---")
    print(f"  Written to: {map_path}")
    print(f"  File size: {file_size:.1f} KB")
    print(f"  Budget-constrained: {export['_meta']['budget_constrained_verses']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
