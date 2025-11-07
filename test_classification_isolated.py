#!/usr/bin/env python3
"""
Isolated test of classification logic without full app initialization
"""

import re
from typing import Optional, Tuple, Dict, Any

# Minimal mock data
SURAHS_BY_NAME = {
    'al-kahf': 18,
    'al-baqarah': 2,
    'maryam': 19,
}

NAMED_VERSES = {
    'ayat al kursi': (2, 255),
    'ayatul kursi': (2, 255),
}

def normalize_query_text(query: str) -> str:
    """Normalize query for matching"""
    query = query.lower().strip()
    replacements = {
        r'\bayat\b': 'verse',
        r'\bayah\b': 'verse',
        r'\bayahs\b': 'verses',
        r'\bayat\b': 'verses',
        r'surat\b': 'surah',
        r'surah\s+': 'surah ',
        r'verse\s+': 'verse ',
        r'verses\s+': 'verses ',
        r'-': ' ',
    }
    for pattern, replacement in replacements.items():
        query = re.sub(pattern, replacement, query)
    return query

def extract_verse_range(query: str) -> Optional[Tuple[int, int, int]]:
    """Extract verse RANGE from query"""
    query_normalized = normalize_query_text(query)

    # Check for surah name patterns with ranges
    for surah_name, surah_num in sorted(SURAHS_BY_NAME.items(), key=lambda x: len(x[0]), reverse=True):
        if surah_name in query_normalized:
            patterns = [
                rf'{re.escape(surah_name)}[^\d]*(\d{{1,3}})\s*-\s*(\d{{1,3}})',  # "Al-Kahf 1-10"
                rf'{re.escape(surah_name)}[^\d]*verse[s]?\s+(\d{{1,3}})\s*-\s*(\d{{1,3}})',  # "Al-Kahf verse 1-10"
                rf'{re.escape(surah_name)}[^\d]*ayah[s]?\s+(\d{{1,3}})\s*-\s*(\d{{1,3}})',  # "Al-Kahf ayah 1-10"
            ]

            for pattern in patterns:
                match = re.search(pattern, query_normalized)
                if match:
                    try:
                        start_verse = int(match.group(1))
                        end_verse = int(match.group(2))
                        if start_verse <= end_verse:
                            return (surah_num, start_verse, end_verse)
                    except (ValueError, IndexError):
                        continue

    # Check for numeric patterns with colon
    range_pattern = r'\b(\d{1,3}):(\d{1,3})-(\d{1,3})\b'
    match = re.search(range_pattern, query_normalized)
    if match:
        try:
            surah = int(match.group(1))
            start_verse = int(match.group(2))
            end_verse = int(match.group(3))
            if start_verse <= end_verse:
                return (surah, start_verse, end_verse)
        except (ValueError, IndexError):
            pass

    return None

def extract_verse_reference_enhanced(query: str) -> Optional[Tuple[int, int]]:
    """Extract single verse reference"""
    query_normalized = normalize_query_text(query)

    # Check named verses
    for name, ref in NAMED_VERSES.items():
        if name in query_normalized:
            return ref

    # Check numeric patterns
    patterns = [
        r'\b(\d{1,3}):(\d{1,3})(?:-\d{1,3})?\b',  # 2:255 or 2:255-256
    ]

    for pattern in patterns:
        match = re.search(pattern, query_normalized)
        if match:
            try:
                surah = int(match.group(1))
                verse = int(match.group(2))
                return (surah, verse)
            except (ValueError, IndexError):
                continue

    # Check surah name + verse
    for surah_name, surah_num in SURAHS_BY_NAME.items():
        if surah_name in query_normalized:
            pattern = rf'{re.escape(surah_name)}[^\d]*(\d{{1,3}})'
            match = re.search(pattern, query_normalized)
            if match:
                verse_num = int(match.group(1))
                return (surah_num, verse_num)

    return None

def classify_query_enhanced(query: str) -> Dict[str, Any]:
    """Enhanced query classification"""
    query_normalized = normalize_query_text(query)
    verse_ref = extract_verse_reference_enhanced(query)

    if verse_ref:
        # CRITICAL FIX: Check for verse ranges
        verse_range = extract_verse_range(query)
        if verse_range:
            return {
                'query_type': 'direct_verse',
                'confidence': 0.95,
                'verse_ref': verse_ref,
            }

        # Pure numeric reference
        if re.fullmatch(r'\d{1,3}:\d{1,3}(?:-\d{1,3})?', query_normalized.strip()):
            return {
                'query_type': 'direct_verse',
                'confidence': 0.95,
                'verse_ref': verse_ref,
            }

        # Named verse
        if any(name in query_normalized for name in NAMED_VERSES.keys()):
            return {
                'query_type': 'direct_verse',
                'confidence': 0.9,
                'verse_ref': verse_ref,
            }

        # Has verse but with other content
        return {
            'query_type': 'semantic',
            'confidence': 0.7,
            'verse_ref': verse_ref,
        }

    # No verse reference
    return {
        'query_type': 'semantic',
        'confidence': 0.8,
        'verse_ref': None,
    }

# Test cases
test_queries = [
    "Surah Al-Kahf verse 1-10",
    "Al-Baqarah 255-256",
    "Surah Maryam verse 1-10",
    "2:255",
    "ayat al kursi",
    "what does patience mean in Islam"
]

print("=" * 70)
print("TESTING QUERY CLASSIFICATION FIX")
print("=" * 70)

for query in test_queries:
    print(f"\nQuery: '{query}'")
    print("-" * 40)

    verse_ref = extract_verse_reference_enhanced(query)
    verse_range = extract_verse_range(query)
    classification = classify_query_enhanced(query)

    print(f"  Verse ref: {verse_ref}")
    print(f"  Verse range: {verse_range}")
    print(f"  Classification: {classification['query_type']} (confidence: {classification['confidence']:.0%})")

    # Check correctness
    if "verse 1-10" in query or "255-256" in query:
        if classification['query_type'] == 'direct_verse':
            print(f"  ✅ CORRECT: Range query routed to direct_verse")
        else:
            print(f"  ❌ ERROR: Range query misclassified as {classification['query_type']}")
    elif verse_ref and classification['query_type'] == 'direct_verse':
        print(f"  ✅ CORRECT: Single verse routed to direct_verse")
    elif not verse_ref and classification['query_type'] == 'semantic':
        print(f"  ✅ CORRECT: Semantic query routed properly")

print("\n" + "=" * 70)