#!/usr/bin/env python3
"""
Test verse extraction for tafsir queries
"""
import re
from typing import Optional, Tuple

# Copy the metadata and functions from app.py for standalone testing
QURAN_METADATA = {
    1: {"name": "Al-Fatihah", "verses": 7}, 2: {"name": "Al-Baqarah", "verses": 286}, 3: {"name": "Aal-E-Imran", "verses": 200},
    4: {"name": "An-Nisa", "verses": 176}, 5: {"name": "Al-Ma'idah", "verses": 120}, 6: {"name": "Al-An'am", "verses": 165},
    7: {"name": "Al-A'raf", "verses": 206}, 8: {"name": "Al-Anfal", "verses": 75}, 9: {"name": "At-Tawbah", "verses": 129},
    10: {"name": "Yunus", "verses": 109}, 11: {"name": "Hud", "verses": 123}, 12: {"name": "Yusuf", "verses": 111},
    13: {"name": "Ar-Ra'd", "verses": 43}, 14: {"name": "Ibrahim", "verses": 52}, 15: {"name": "Al-Hijr", "verses": 99},
    16: {"name": "An-Nahl", "verses": 128}, 17: {"name": "Al-Isra", "verses": 111}, 18: {"name": "Al-Kahf", "verses": 110},
    19: {"name": "Maryam", "verses": 98}, 20: {"name": "Taha", "verses": 135}, 21: {"name": "Al-Anbya", "verses": 112},
    22: {"name": "Al-Hajj", "verses": 78}, 23: {"name": "Al-Mu'minun", "verses": 118}, 24: {"name": "An-Nur", "verses": 64},
    25: {"name": "Al-Furqan", "verses": 77}, 26: {"name": "Ash-Shu'ara", "verses": 227}, 27: {"name": "An-Naml", "verses": 93},
    28: {"name": "Al-Qasas", "verses": 88}, 29: {"name": "Al-Ankabut", "verses": 69}, 30: {"name": "Ar-Rum", "verses": 60},
    31: {"name": "Luqman", "verses": 34}, 32: {"name": "As-Sajdah", "verses": 30}, 33: {"name": "Al-Ahzab", "verses": 73},
    34: {"name": "Saba", "verses": 54}, 35: {"name": "Fatir", "verses": 45}, 36: {"name": "Ya-Sin", "verses": 83},
    37: {"name": "As-Saffat", "verses": 182}, 38: {"name": "Sad", "verses": 88}, 39: {"name": "Az-Zumar", "verses": 75},
    40: {"name": "Ghafir", "verses": 85}, 41: {"name": "Fussilat", "verses": 54}, 42: {"name": "Ash-Shuraa", "verses": 53},
    43: {"name": "Az-Zukhruf", "verses": 89}, 44: {"name": "Ad-Dukhan", "verses": 59}, 45: {"name": "Al-Jathiyah", "verses": 37},
    46: {"name": "Al-Ahqaf", "verses": 35}, 47: {"name": "Muhammad", "verses": 38}, 48: {"name": "Al-Fath", "verses": 29},
    49: {"name": "Al-Hujurat", "verses": 18}, 50: {"name": "Qaf", "verses": 45}, 51: {"name": "Adh-Dhariyat", "verses": 60},
    52: {"name": "At-Tur", "verses": 49}, 53: {"name": "An-Najm", "verses": 62}, 54: {"name": "Al-Qamar", "verses": 55},
    55: {"name": "Ar-Rahman", "verses": 78}, 56: {"name": "Al-Waqi'ah", "verses": 96}, 57: {"name": "Al-Hadid", "verses": 29},
    58: {"name": "Al-Mujadila", "verses": 22}, 59: {"name": "Al-Hashr", "verses": 24}, 60: {"name": "Al-Mumtahanah", "verses": 13},
    61: {"name": "As-Saf", "verses": 14}, 62: {"name": "Al-Jumu'ah", "verses": 11}, 63: {"name": "Al-Munafiqun", "verses": 11},
    64: {"name": "At-Taghabun", "verses": 18}, 65: {"name": "At-Talaq", "verses": 12}, 66: {"name": "At-Tahrim", "verses": 12},
    67: {"name": "Al-Mulk", "verses": 30}, 68: {"name": "Al-Qalam", "verses": 52}, 69: {"name": "Al-Haqqah", "verses": 52},
    70: {"name": "Al-Ma'arij", "verses": 44}, 71: {"name": "Nuh", "verses": 28}, 72: {"name": "Al-Jinn", "verses": 28},
    73: {"name": "Al-Muzzammil", "verses": 20}, 74: {"name": "Al-Muddaththir", "verses": 56}, 75: {"name": "Al-Qiyamah", "verses": 40},
    76: {"name": "Al-Insan", "verses": 31}, 77: {"name": "Al-Mursalat", "verses": 50}, 78: {"name": "An-Naba", "verses": 40},
    79: {"name": "An-Nazi'at", "verses": 46}, 80: {"name": "Abasa", "verses": 42}, 81: {"name": "At-Takwir", "verses": 29},
    82: {"name": "Al-Infitar", "verses": 19}, 83: {"name": "Al-Mutaffifin", "verses": 36}, 84: {"name": "Al-Inshiqaq", "verses": 25},
    85: {"name": "Al-Buruj", "verses": 22}, 86: {"name": "At-Tariq", "verses": 17}, 87: {"name": "Al-A'la", "verses": 19},
    88: {"name": "Al-Ghashiyah", "verses": 26}, 89: {"name": "Al-Fajr", "verses": 30}, 90: {"name": "Al-Balad", "verses": 20},
    91: {"name": "Ash-Shams", "verses": 15}, 92: {"name": "Al-Layl", "verses": 21}, 93: {"name": "Ad-Duhaa", "verses": 11},
    94: {"name": "Ash-Sharh", "verses": 8}, 95: {"name": "At-Tin", "verses": 8}, 96: {"name": "Al-Alaq", "verses": 19},
    97: {"name": "Al-Qadr", "verses": 5}, 98: {"name": "Al-Bayyinah", "verses": 8}, 99: {"name": "Az-Zalzalah", "verses": 8},
    100: {"name": "Al-Adiyat", "verses": 11}, 101: {"name": "Al-Qari'ah", "verses": 11}, 102: {"name": "At-Takathur", "verses": 8},
    103: {"name": "Al-Asr", "verses": 3}, 104: {"name": "Al-Humazah", "verses": 9}, 105: {"name": "Al-Fil", "verses": 5},
    106: {"name": "Quraysh", "verses": 4}, 107: {"name": "Al-Ma'un", "verses": 7}, 108: {"name": "Al-Kawthar", "verses": 3},
    109: {"name": "Al-Kafirun", "verses": 6}, 110: {"name": "An-Nasr", "verses": 3}, 111: {"name": "Al-Masad", "verses": 5},
    112: {"name": "Al-Ikhlas", "verses": 4}, 113: {"name": "Al-Falaq", "verses": 5}, 114: {"name": "An-Nas", "verses": 6}
}

SURAHS_BY_NAME = {info["name"].lower(): num for num, info in QURAN_METADATA.items()}

def validate_verse_reference(surah: int, verse: int) -> Tuple[bool, str]:
    """Validate verse reference"""
    if surah not in QURAN_METADATA:
        return False, f"Invalid surah number: {surah}"

    max_verses = QURAN_METADATA[surah]["verses"]
    if verse < 1 or verse > max_verses:
        return False, f"Invalid verse {verse} for surah {surah} (max: {max_verses})"

    return True, ""

def normalize_query_text(query: str) -> str:
    """Normalize query for better matching"""
    query = query.lower().strip()

    # Normalize apostrophes (curly quotes to straight quotes)
    query = query.replace("'", "'").replace("'", "'").replace("`", "'")

    # Use word boundaries to avoid double replacements (e.g., "surah" becoming "surahh")
    replacements = {
        r'\bsura\b': 'surah',  # Only replace standalone "sura", not "surah"
        r'\bayat\b': 'ayah',
        r'\bverses\b': 'verse',
        'cited by': 'cited',
        'mentions': 'mentioned'
    }
    for pattern, replacement in replacements.items():
        query = re.sub(pattern, replacement, query)
    return query

def extract_verse_range(query: str) -> Optional[Tuple[int, int, int]]:
    """
    Extract verse RANGE from query.
    Returns (surah, start_verse, end_verse) or None.
    Examples: "3:190-191" -> (3, 190, 191), "2:255" -> (2, 255, 255)
              "As-Sajdah 1-9" -> (32, 1, 9), "Surah Al-Baqarah verse 255-257" -> (2, 255, 257)
    """
    query_normalized = normalize_query_text(query)

    # Strategy 1: Surah name + verse range (e.g., "As-Sajdah 1-9", "Surah Al-Baqarah verse 1-5")
    # Sort by length (longest first) to avoid substring matching issues
    for surah_name, surah_num in sorted(SURAHS_BY_NAME.items(), key=lambda x: len(x[0]), reverse=True):
        if surah_name in query_normalized:
            # Try various patterns for verse ranges with surah names
            patterns = [
                rf'{re.escape(surah_name)}[^\d]*(\d{{1,3}})\s*-\s*(\d{{1,3}})',  # "As-Sajdah 1-9"
                rf'{re.escape(surah_name)}[^\d]*verse[s]?\s+(\d{{1,3}})\s*-\s*(\d{{1,3}})',  # "As-Sajdah verse 1-9"
                rf'{re.escape(surah_name)}[^\d]*ayah[s]?\s+(\d{{1,3}})\s*-\s*(\d{{1,3}})',  # "As-Sajdah ayah 1-9"
            ]

            for pattern in patterns:
                match = re.search(pattern, query_normalized)
                if match:
                    try:
                        start_verse = int(match.group(1))
                        end_verse = int(match.group(2))

                        # Validate both verses
                        is_valid_start, _ = validate_verse_reference(surah_num, start_verse)
                        is_valid_end, _ = validate_verse_reference(surah_num, end_verse)

                        if is_valid_start and is_valid_end and start_verse <= end_verse:
                            return (surah_num, start_verse, end_verse)
                    except (ValueError, IndexError):
                        continue

    # Strategy 2: Numeric pattern with colon (e.g., "3:190-191")
    range_pattern = r'\b(\d{1,3}):(\d{1,3})-(\d{1,3})\b'
    match = re.search(range_pattern, query_normalized)

    if match:
        try:
            surah = int(match.group(1))
            start_verse = int(match.group(2))
            end_verse = int(match.group(3))

            # Validate both verses
            is_valid_start, _ = validate_verse_reference(surah, start_verse)
            is_valid_end, _ = validate_verse_reference(surah, end_verse)

            if is_valid_start and is_valid_end and start_verse <= end_verse:
                return (surah, start_verse, end_verse)
        except (ValueError, IndexError):
            pass

    # Strategy 3: Single verse fallback - return as (surah, verse, verse)
    # Numeric pattern
    single_patterns = [
        r'\b(\d{1,3}):(\d{1,3})\b',
        r'surah\s+(\d{1,3})\s+(?:verse|ayah)\s+(\d{1,3})',
    ]

    for pattern in single_patterns:
        match = re.search(pattern, query_normalized)
        if match:
            try:
                surah = int(match.group(1))
                verse = int(match.group(2))
                is_valid, _ = validate_verse_reference(surah, verse)
                if is_valid:
                    return (surah, verse, verse)
            except (ValueError, IndexError):
                continue

    # Surah name + single verse
    for surah_name, surah_num in sorted(SURAHS_BY_NAME.items(), key=lambda x: len(x[0]), reverse=True):
        if surah_name in query_normalized:
            pattern = rf'{re.escape(surah_name)}[^\d]*(\d{{1,3}})'
            match = re.search(pattern, query_normalized)
            if match:
                verse_num = int(match.group(1))
                is_valid, _ = validate_verse_reference(surah_num, verse_num)
                if is_valid:
                    return (surah_num, verse_num, verse_num)

    return None


# Test cases
TEST_CASES = [
    # User's problematic cases
    ("Surah As-Sajdah verse 1-9", (32, 1, 9)),
    ("Surah Al-Waqi'ah verse 1-9", (56, 1, 9)),

    # Numeric formats
    ("32:1-9", (32, 1, 9)),
    ("56:1-10", (56, 1, 10)),
    ("2:255", (2, 255, 255)),
    ("3:190-191", (3, 190, 191)),

    # Named formats
    ("As-Sajdah 1-9", (32, 1, 9)),
    ("Surah As-Sajdah 1-9", (32, 1, 9)),
    ("Al-Waqi'ah verse 1-9", (56, 1, 9)),
    ("Surah Al-Baqarah verse 255-257", (2, 255, 257)),

    # Single verses
    ("Surah Al-Baqarah verse 255", (2, 255, 255)),
    ("Ayatul Kursi", None),  # Named verse - not handled by extract_verse_range

    # Edge cases
    ("surah fatir, verse 6", (35, 6, 6)),
    ("chapter 35 verse 6", None),  # "chapter" not in replacements
]


def run_tests():
    """Run all test cases"""
    print("=" * 80)
    print("VERSE EXTRACTION TESTS")
    print("=" * 80)

    passed = 0
    failed = 0

    for query, expected in TEST_CASES:
        result = extract_verse_range(query)
        status = "✓ PASS" if result == expected else "✗ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"\n{status}")
        print(f"  Query:    {query}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")

        if result != expected:
            normalized = normalize_query_text(query)
            print(f"  Normalized: {normalized}")

            # Debug: Check if surah name is found
            for surah_name, surah_num in SURAHS_BY_NAME.items():
                if surah_name in normalized:
                    print(f"  Found surah: '{surah_name}' -> {surah_num}")

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
