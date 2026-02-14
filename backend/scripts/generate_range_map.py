#!/usr/bin/env python3
"""
Generate the static verse range map from actual TAFSIR_CHUNKS data.

This script connects to GCS, loads all tafsir chunks, measures their actual
token costs, and exports a hardcoded range map to:

    backend/data/verse_range_map.json

Every verse entry is backed by measured data -- no estimates, no heuristics.

Usage:
    # From the backend/ directory:
    python scripts/generate_range_map.py

    # With a specific output path:
    python scripts/generate_range_map.py --output /path/to/output.json

    # Validate specific ranges after generation:
    python scripts/generate_range_map.py --validate 2:280:283 3:190:194

Requirements:
    - GOOGLE_APPLICATION_CREDENTIALS or gcloud auth
    - Access to the GCS bucket with processed tafsir files
"""

import argparse
import json
import os
import sys

# Add backend/ to path so we can import modules
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from services.token_budget_service import (
    precompute_verse_budgets,
    export_range_map,
    compute_max_end_verse,
    get_verse_token_cost,
    get_range_token_cost,
)


def load_quran_metadata():
    """Load QURAN_METADATA inline (same as app.py)."""
    return {
        1: {"name": "Al-Fatihah", "verses": 7}, 2: {"name": "Al-Baqarah", "verses": 286},
        3: {"name": "Aal-E-Imran", "verses": 200}, 4: {"name": "An-Nisa", "verses": 176},
        5: {"name": "Al-Ma'idah", "verses": 120}, 6: {"name": "Al-An'am", "verses": 165},
        7: {"name": "Al-A'raf", "verses": 206}, 8: {"name": "Al-Anfal", "verses": 75},
        9: {"name": "At-Tawbah", "verses": 129}, 10: {"name": "Yunus", "verses": 109},
        11: {"name": "Hud", "verses": 123}, 12: {"name": "Yusuf", "verses": 111},
        13: {"name": "Ar-Ra'd", "verses": 43}, 14: {"name": "Ibrahim", "verses": 52},
        15: {"name": "Al-Hijr", "verses": 99}, 16: {"name": "An-Nahl", "verses": 128},
        17: {"name": "Al-Isra", "verses": 111}, 18: {"name": "Al-Kahf", "verses": 110},
        19: {"name": "Maryam", "verses": 98}, 20: {"name": "Taha", "verses": 135},
        21: {"name": "Al-Anbya", "verses": 112}, 22: {"name": "Al-Hajj", "verses": 78},
        23: {"name": "Al-Mu'minun", "verses": 118}, 24: {"name": "An-Nur", "verses": 64},
        25: {"name": "Al-Furqan", "verses": 77}, 26: {"name": "Ash-Shu'ara", "verses": 227},
        27: {"name": "An-Naml", "verses": 93}, 28: {"name": "Al-Qasas", "verses": 88},
        29: {"name": "Al-Ankabut", "verses": 69}, 30: {"name": "Ar-Rum", "verses": 60},
        31: {"name": "Luqman", "verses": 34}, 32: {"name": "As-Sajdah", "verses": 30},
        33: {"name": "Al-Ahzab", "verses": 73}, 34: {"name": "Saba", "verses": 54},
        35: {"name": "Fatir", "verses": 45}, 36: {"name": "Ya-Sin", "verses": 83},
        37: {"name": "As-Saffat", "verses": 182}, 38: {"name": "Sad", "verses": 88},
        39: {"name": "Az-Zumar", "verses": 75}, 40: {"name": "Ghafir", "verses": 85},
        41: {"name": "Fussilat", "verses": 54}, 42: {"name": "Ash-Shuraa", "verses": 53},
        43: {"name": "Az-Zukhruf", "verses": 89}, 44: {"name": "Ad-Dukhan", "verses": 59},
        45: {"name": "Al-Jathiyah", "verses": 37}, 46: {"name": "Al-Ahqaf", "verses": 35},
        47: {"name": "Muhammad", "verses": 38}, 48: {"name": "Al-Fath", "verses": 29},
        49: {"name": "Al-Hujurat", "verses": 18}, 50: {"name": "Qaf", "verses": 45},
        51: {"name": "Adh-Dhariyat", "verses": 60}, 52: {"name": "At-Tur", "verses": 49},
        53: {"name": "An-Najm", "verses": 62}, 54: {"name": "Al-Qamar", "verses": 55},
        55: {"name": "Ar-Rahman", "verses": 78}, 56: {"name": "Al-Waqi'ah", "verses": 96},
        57: {"name": "Al-Hadid", "verses": 29}, 58: {"name": "Al-Mujadila", "verses": 22},
        59: {"name": "Al-Hashr", "verses": 24}, 60: {"name": "Al-Mumtahanah", "verses": 13},
        61: {"name": "As-Saf", "verses": 14}, 62: {"name": "Al-Jumu'ah", "verses": 11},
        63: {"name": "Al-Munafiqun", "verses": 11}, 64: {"name": "At-Taghabun", "verses": 18},
        65: {"name": "At-Talaq", "verses": 12}, 66: {"name": "At-Tahrim", "verses": 12},
        67: {"name": "Al-Mulk", "verses": 30}, 68: {"name": "Al-Qalam", "verses": 52},
        69: {"name": "Al-Haqqah", "verses": 52}, 70: {"name": "Al-Ma'arij", "verses": 44},
        71: {"name": "Nuh", "verses": 28}, 72: {"name": "Al-Jinn", "verses": 28},
        73: {"name": "Al-Muzzammil", "verses": 20}, 74: {"name": "Al-Muddaththir", "verses": 56},
        75: {"name": "Al-Qiyamah", "verses": 40}, 76: {"name": "Al-Insan", "verses": 31},
        77: {"name": "Al-Mursalat", "verses": 50}, 78: {"name": "An-Naba", "verses": 40},
        79: {"name": "An-Nazi'at", "verses": 46}, 80: {"name": "Abasa", "verses": 42},
        81: {"name": "At-Takwir", "verses": 29}, 82: {"name": "Al-Infitar", "verses": 19},
        83: {"name": "Al-Mutaffifin", "verses": 36}, 84: {"name": "Al-Inshiqaq", "verses": 25},
        85: {"name": "Al-Buruj", "verses": 22}, 86: {"name": "At-Tariq", "verses": 17},
        87: {"name": "Al-A'la", "verses": 19}, 88: {"name": "Al-Ghashiyah", "verses": 26},
        89: {"name": "Al-Fajr", "verses": 30}, 90: {"name": "Al-Balad", "verses": 20},
        91: {"name": "Ash-Shams", "verses": 15}, 92: {"name": "Al-Layl", "verses": 21},
        93: {"name": "Ad-Duhaa", "verses": 11}, 94: {"name": "Ash-Sharh", "verses": 8},
        95: {"name": "At-Tin", "verses": 8}, 96: {"name": "Al-Alaq", "verses": 19},
        97: {"name": "Al-Qadr", "verses": 5}, 98: {"name": "Al-Bayyinah", "verses": 8},
        99: {"name": "Az-Zalzalah", "verses": 8}, 100: {"name": "Al-Adiyat", "verses": 11},
        101: {"name": "Al-Qari'ah", "verses": 11}, 102: {"name": "At-Takathur", "verses": 8},
        103: {"name": "Al-Asr", "verses": 3}, 104: {"name": "Al-Humazah", "verses": 9},
        105: {"name": "Al-Fil", "verses": 5}, 106: {"name": "Quraysh", "verses": 4},
        107: {"name": "Al-Ma'un", "verses": 7}, 108: {"name": "Al-Kawthar", "verses": 3},
        109: {"name": "Al-Kafirun", "verses": 6}, 110: {"name": "An-Nasr", "verses": 3},
        111: {"name": "Al-Masad", "verses": 5}, 112: {"name": "Al-Ikhlas", "verses": 4},
        113: {"name": "Al-Falaq", "verses": 5}, 114: {"name": "An-Nas", "verses": 6},
    }


def load_tafsir_chunks_from_gcs():
    """Load TAFSIR_CHUNKS from GCS (same as app.py loader)."""
    from google.cloud import storage as gcs_storage

    project = os.environ.get("GCP_INFRASTRUCTURE_PROJECT", "tafsir-452721")
    bucket_name = os.environ.get("GCS_BUCKET_NAME", "tafsir-simplified-sources")

    print(f"Connecting to GCS: {project}/{bucket_name}")
    client = gcs_storage.Client(project=project)
    bucket = client.bucket(bucket_name)

    source_files = [
        ("processed/ibnkathir-Fatiha-Tawbah_fixed.json", "ibn-kathir"),
        ("processed/ibnkathir-Yunus-Ankabut_FINAL_fixed.json", "ibn-kathir"),
        ("processed/ibnkathir-Rum-Nas_FINAL_fixed.json", "ibn-kathir"),
        ("processed/al-Qurtubi Vol. 1_FINAL_fixed.json", "al-qurtubi"),
        ("processed/al-Qurtubi Vol. 2_FINAL_fixed.json", "al-qurtubi"),
        ("processed/al-Qurtubi Vol. 3_fixed.json", "al-qurtubi"),
        ("processed/al-Qurtubi Vol. 4_FINAL_fixed.json", "al-qurtubi"),
    ]

    chunks = {}
    for file_path, source in source_files:
        blob = bucket.blob(file_path)
        if not blob.exists():
            print(f"  WARNING: {file_path} not found, skipping")
            continue

        data = json.loads(blob.download_as_text())
        verses = data.get("verses", [])
        count = 0

        for verse in verses:
            surah = verse.get("surah")
            verse_num = verse.get("verse_number") or verse.get("verse_numbers")
            if surah is None:
                continue

            # Handle different verse number formats
            if isinstance(verse_num, str) and "-" in verse_num:
                try:
                    parts = verse_num.split("-")
                    verse_num = int(parts[0])
                except (ValueError, IndexError):
                    continue
            elif isinstance(verse_num, list) and verse_num:
                verse_num = verse_num[0]
            elif verse_num is None:
                verse_num = 0
            else:
                try:
                    verse_num = int(verse_num)
                except (ValueError, TypeError):
                    continue

            # Build flattened text (same logic as app.py)
            chunk_parts = []
            verse_text = verse.get("verse_text", "")
            topics = verse.get("topics", [])

            if verse_text:
                chunk_parts.append(verse_text)

            if verse.get("commentary") and not topics:
                chunk_parts.append(verse["commentary"])
                for phrase in verse.get("phrase_analysis", []):
                    if isinstance(phrase, str):
                        chunk_parts.append(phrase)
                for citation in verse.get("scholar_citations", []):
                    if isinstance(citation, str):
                        chunk_parts.append(citation)

            if topics:
                for topic in topics:
                    if topic.get("topic_header"):
                        chunk_parts.append(topic["topic_header"])
                    if topic.get("commentary"):
                        chunk_parts.append(topic["commentary"])
                    for phrase in topic.get("phrase_analysis", []):
                        if isinstance(phrase, dict):
                            if phrase.get("phrase"):
                                chunk_parts.append(phrase["phrase"])
                            if phrase.get("analysis"):
                                chunk_parts.append(phrase["analysis"])

            full_text = " ".join(chunk_parts)
            if full_text.strip():
                chunk_id = f"{source}:{surah}:{verse_num}"
                chunks[chunk_id] = full_text
                count += 1

        print(f"  Loaded {count} chunks from {file_path}")

    print(f"Total chunks loaded: {len(chunks)}")
    return chunks


def validate_ranges(validations):
    """
    Validate specific (surah, start, expected_max_end) tuples.

    Each validation is a string like '2:280:283' meaning
    surah 2, start verse 280, expected max end 283.
    """
    metadata = load_quran_metadata()
    all_pass = True

    for v in validations:
        parts = v.split(":")
        if len(parts) != 3:
            print(f"  SKIP: Invalid format '{v}' (expected surah:start:expected_end)")
            continue

        surah, start, expected_end = int(parts[0]), int(parts[1]), int(parts[2])
        surah_max = metadata[surah]["verses"]
        actual_end, meta = compute_max_end_verse(surah, start, surah_max)

        status = "PASS" if actual_end == expected_end else "FAIL"
        if status == "FAIL":
            all_pass = False

        range_cost = get_range_token_cost(surah, start, actual_end)
        per_verse_costs = []
        for vn in range(start, actual_end + 1):
            per_verse_costs.append(f"v{vn}={get_verse_token_cost(surah, vn)}")

        print(f"  [{status}] {surah}:{start} -> max_end={actual_end} "
              f"(expected={expected_end}, tokens={range_cost}, "
              f"costs=[{', '.join(per_verse_costs)}])")

    return all_pass


def main():
    parser = argparse.ArgumentParser(
        description="Generate static verse range map from GCS tafsir data"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output JSON file path (default: backend/data/verse_range_map.json)",
    )
    parser.add_argument(
        "--validate", "-v",
        nargs="*",
        help="Validate specific ranges: surah:start:expected_end (e.g., 2:280:283)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Generating static verse range map")
    print("=" * 60)

    # Load data
    metadata = load_quran_metadata()
    chunks = load_tafsir_chunks_from_gcs()

    # Precompute
    print("\nPrecomputing verse budgets...")
    precompute_verse_budgets(chunks, metadata)

    # Export
    output_path = export_range_map(args.output)
    print(f"\nExported to: {output_path}")

    # Validate
    if args.validate:
        print(f"\nValidating {len(args.validate)} ranges:")
        ok = validate_ranges(args.validate)
        if not ok:
            print("\nSome validations FAILED!")
            sys.exit(1)
        else:
            print("\nAll validations passed.")

    # Always validate 2:280 -> 283 as a known baseline
    print("\nBaseline validation (2:280 -> 283):")
    validate_ranges(["2:280:283"])

    print("\nDone.")


if __name__ == "__main__":
    main()
