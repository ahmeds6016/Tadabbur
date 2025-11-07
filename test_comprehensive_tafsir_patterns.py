#!/usr/bin/env python3
"""
Comprehensive test suite for tafsir query pattern matching
Tests all edge cases and variations to ensure 95-98% coverage
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import (
    classify_query_enhanced,
    extract_verse_range,
    extract_verse_reference_enhanced,
    normalize_query_text
)

def run_test(query, expected_type, expected_ref=None, test_name=""):
    """Run a single test and return result"""
    classification = classify_query_enhanced(query)
    verse_ref = extract_verse_reference_enhanced(query)
    verse_range = extract_verse_range(query)

    success = classification['query_type'] == expected_type

    if expected_ref and verse_ref:
        success = success and verse_ref == expected_ref

    return {
        'query': query,
        'success': success,
        'expected_type': expected_type,
        'actual_type': classification['query_type'],
        'verse_ref': verse_ref,
        'verse_range': verse_range,
        'confidence': classification['confidence'],
        'test_name': test_name
    }

# ============================================================================
# TEST CASES
# ============================================================================

test_cases = [
    # ==== STANDARD NUMERIC PATTERNS ====
    ("2:255", "direct_verse", (2, 255), "Standard colon format"),
    ("2 : 255", "direct_verse", (2, 255), "Colon with spaces"),
    ("2.255", "direct_verse", (2, 255), "Period separator"),
    ("2 . 255", "direct_verse", (2, 255), "Period with spaces"),
    ("2/255", "direct_verse", (2, 255), "Slash separator"),
    ("s2v255", "direct_verse", (2, 255), "Abbreviated s#v#"),
    ("ch2v255", "direct_verse", (2, 255), "Chapter abbreviated"),
    ("chapter 2 verse 255", "direct_verse", (2, 255), "Explicit chapter/verse"),

    # ==== RANGE PATTERNS ====
    ("2:255-257", "direct_verse", (2, 255), "Standard range"),
    ("2:255 - 257", "direct_verse", (2, 255), "Range with spaces"),
    ("2.255-257", "direct_verse", (2, 255), "Period range"),
    ("2/255-257", "direct_verse", (2, 255), "Slash range"),
    ("surah 2 verses 255-257", "direct_verse", (2, 255), "Explicit surah range"),
    ("chapter 2 verses 255-257", "direct_verse", (2, 255), "Chapter range"),

    # ==== SURAH NAME PATTERNS ====
    ("Al-Baqarah 255", "direct_verse", (2, 255), "Surah name + verse"),
    ("Al-Baqarah verse 255", "direct_verse", (2, 255), "Surah name + 'verse'"),
    ("Al-Baqarah ayah 255", "direct_verse", (2, 255), "Surah name + 'ayah'"),
    ("Al-Baqarah v255", "direct_verse", (2, 255), "Surah name + 'v'"),
    ("Al-Baqarah (255)", "direct_verse", (2, 255), "Parenthetical"),
    ("Al-Baqarah [255]", "direct_verse", (2, 255), "Brackets"),

    # ==== COMMA-SEPARATED PATTERNS (the bug we found) ====
    ("Surah Fatir, Verse 6", "direct_verse", (35, 6), "Comma-separated"),
    ("Al-Baqarah, 255", "direct_verse", (2, 255), "Surah comma verse"),
    ("Al-Baqarah, verse 255", "direct_verse", (2, 255), "Surah comma 'verse'"),
    ("Surah Al-Baqarah, Ayah 255", "direct_verse", (2, 255), "Full comma format"),

    # ==== REVERSED ORDER PATTERNS ====
    ("verse 255 of Al-Baqarah", "direct_verse", (2, 255), "Verse X of Surah"),
    ("verse 255 from Al-Baqarah", "direct_verse", (2, 255), "Verse X from Surah"),
    ("verse 255 in Al-Baqarah", "direct_verse", (2, 255), "Verse X in Surah"),
    ("ayah 255 of surah Al-Baqarah", "direct_verse", (2, 255), "Ayah X of surah"),
    ("255 of Al-Baqarah", "direct_verse", (2, 255), "Number of Surah"),
    ("verse 255 of surah 2", "direct_verse", (2, 255), "Verse X of surah #"),

    # ==== RANGE WITH SURAH NAMES ====
    ("Surah Al-Kahf verse 1-10", "direct_verse", (18, 1), "Surah range query"),
    ("Al-Kahf 1-10", "direct_verse", (18, 1), "Simple surah range"),
    ("Al-Kahf verses 1-10", "direct_verse", (18, 1), "Surah 'verses' range"),
    ("Al-Kahf, verses 1-10", "direct_verse", (18, 1), "Comma surah range"),
    ("verses 1-10 of Al-Kahf", "direct_verse", (18, 1), "Reversed range"),
    ("verses 1-10 from Al-Kahf", "direct_verse", (18, 1), "Reversed 'from'"),

    # ==== NATURAL LANGUAGE PREFIXES ====
    ("Show me 2:255", "direct_verse", (2, 255), "Show me prefix"),
    ("Give me Al-Baqarah 255", "direct_verse", (2, 255), "Give me prefix"),
    ("Tell me about verse 2:255", "direct_verse", (2, 255), "Tell me about"),
    ("I want to read 2:255", "direct_verse", (2, 255), "I want to read"),
    ("Please show Al-Baqarah 255", "direct_verse", (2, 255), "Please show"),
    ("Can you show me 2:255", "direct_verse", (2, 255), "Can you show"),
    ("Display verse 2:255", "direct_verse", (2, 255), "Display"),
    ("Fetch Al-Baqarah 255", "direct_verse", (2, 255), "Fetch"),
    ("Find 2:255", "direct_verse", (2, 255), "Find"),
    ("Look up verse 2:255", "direct_verse", (2, 255), "Look up"),

    # ==== NAMED VERSES ====
    ("ayat al kursi", "direct_verse", (2, 255), "Ayat al Kursi"),
    ("ayatul kursi", "direct_verse", (2, 255), "Ayatul Kursi"),
    ("throne verse", "direct_verse", (2, 255), "Throne verse"),
    ("verse of the throne", "direct_verse", (2, 255), "Verse of throne"),
    ("greatest verse", "direct_verse", (2, 255), "Greatest verse"),
    ("light verse", "direct_verse", (24, 35), "Light verse"),
    ("verse of light", "direct_verse", (24, 35), "Verse of light"),
    ("debt verse", "direct_verse", (2, 282), "Debt verse"),
    ("longest verse", "direct_verse", (2, 282), "Longest verse"),
    ("bismillah", "direct_verse", (1, 1), "Bismillah"),
    ("al-fatiha", "direct_verse", (1, 1), "Al-Fatiha"),
    ("hijab verse", "direct_verse", (24, 31), "Hijab verse"),
    ("sword verse", "direct_verse", (9, 5), "Sword verse"),
    ("patience verse", "direct_verse", (2, 153), "Patience verse"),
    ("no compulsion verse", "direct_verse", (2, 256), "No compulsion"),
    ("spider verse", "direct_verse", (29, 41), "Spider verse"),

    # ==== SURAH NAME ALIASES (misspellings/variations) ====
    ("baqara 255", "direct_verse", (2, 255), "Baqara without Al"),
    ("baqarah 255", "direct_verse", (2, 255), "Baqarah without Al"),
    ("cow 255", "direct_verse", (2, 255), "English name Cow"),
    ("the cow 255", "direct_verse", (2, 255), "The Cow"),
    ("fatiha 1", "direct_verse", (1, 1), "Fatiha without Al"),
    ("opening 1", "direct_verse", (1, 1), "Opening surah"),
    ("women 24", "direct_verse", (4, 24), "English Women"),
    ("cave 10", "direct_verse", (18, 10), "English Cave"),
    ("mary 19", "direct_verse", (19, 19), "English Mary"),
    ("joseph 12", "direct_verse", (12, 12), "English Joseph"),
    ("abraham 14", "direct_verse", (14, 14), "English Abraham"),
    ("bee 68", "direct_verse", (16, 68), "English Bee"),
    ("ants 18", "direct_verse", (27, 18), "English Ants"),
    ("spider 41", "direct_verse", (29, 41), "English Spider"),
    ("elephant 1", "direct_verse", (105, 1), "English Elephant"),
    ("sincerity 1", "direct_verse", (112, 1), "English Sincerity"),

    # ==== WORD VARIATIONS (after normalization) ====
    ("sura 2 aya 255", "direct_verse", (2, 255), "Sura/aya"),
    ("surat Al-Baqarah verse 255", "direct_verse", (2, 255), "Surat"),
    ("chapter 2 verse 255", "direct_verse", (2, 255), "Chapter"),
    ("surah 2 ayat 255", "direct_verse", (2, 255), "Ayat plural"),
    ("surah 2 ayet 255", "direct_verse", (2, 255), "Ayet Turkish"),

    # ==== RANGE CONNECTOR VARIATIONS ====
    ("2:255 to 257", "direct_verse", (2, 255), "To connector"),
    ("2:255 through 257", "direct_verse", (2, 255), "Through connector"),
    ("2:255 till 257", "direct_verse", (2, 255), "Till connector"),
    ("2:255 until 257", "direct_verse", (2, 255), "Until connector"),
    ("2:255 thru 257", "direct_verse", (2, 255), "Thru connector"),

    # ==== COMPLEX MIXED PATTERNS ====
    ("Show me verses 1-10 of Surah Al-Kahf", "direct_verse", (18, 1), "Complex prefix range"),
    ("I want to read Al-Baqarah, verse 255", "direct_verse", (2, 255), "Complex prefix comma"),
    ("Please show me the throne verse", "direct_verse", (2, 255), "Prefix named verse"),
    ("Can you display chapter 2 verse 255", "direct_verse", (2, 255), "Complex chapter"),

    # ==== SEMANTIC QUERIES (should NOT be direct_verse) ====
    ("what does patience mean in Islam", "semantic", None, "Pure semantic"),
    ("explain the concept of taqwa", "semantic", None, "Concept query"),
    ("stories about prophets", "semantic", None, "Topic query"),
    ("verses about charity", "semantic", None, "Theme query"),
    ("how to pray", "semantic", None, "How-to query"),
    ("meaning of jihad", "semantic", None, "Meaning query"),

    # ==== EDGE CASES ====
    ("2:255 what does this mean", "semantic", (2, 255), "Verse with question"),
    ("explain 2:255 in detail", "semantic", (2, 255), "Verse with explanation"),
    ("2:255 and its context", "semantic", (2, 255), "Verse with context"),
    ("compare 2:255 with 2:256", "semantic", (2, 255), "Comparison query"),
]

# ============================================================================
# RUN TESTS
# ============================================================================

print("=" * 80)
print("COMPREHENSIVE TAFSIR QUERY PATTERN TEST SUITE")
print("=" * 80)
print(f"Running {len(test_cases)} test cases...")
print()

passed = 0
failed = 0
results = []

for query, expected_type, expected_ref, test_name in test_cases:
    result = run_test(query, expected_type, expected_ref, test_name)
    results.append(result)

    if result['success']:
        passed += 1
        status = "✅ PASS"
    else:
        failed += 1
        status = "❌ FAIL"

    # Print failures and interesting cases
    if not result['success'] or result['confidence'] < 0.7:
        print(f"{status} | {test_name}")
        print(f"  Query: '{query}'")
        print(f"  Expected: {expected_type}, Got: {result['actual_type']}")
        if expected_ref:
            print(f"  Expected ref: {expected_ref}, Got: {result['verse_ref']}")
        print(f"  Confidence: {result['confidence']:.0%}")
        print()

# ============================================================================
# SUMMARY
# ============================================================================

print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"Total Tests: {len(test_cases)}")
print(f"Passed: {passed} ({passed/len(test_cases)*100:.1f}%)")
print(f"Failed: {failed} ({failed/len(test_cases)*100:.1f}%)")
print()

# Group failures by category
if failed > 0:
    print("FAILED TEST CATEGORIES:")
    print("-" * 40)

    failed_tests = [r for r in results if not r['success']]
    categories = {}
    for test in failed_tests:
        cat = test['test_name'].split(' - ')[0] if ' - ' in test['test_name'] else test['test_name'].split()[0]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(test)

    for cat, tests in categories.items():
        print(f"\n{cat}: {len(tests)} failures")
        for test in tests[:3]:  # Show first 3 examples
            print(f"  - '{test['query']}' -> {test['actual_type']} (expected {test['expected_type']})")

# Performance metrics
direct_verse_tests = [r for r in results if r['expected_type'] == 'direct_verse']
semantic_tests = [r for r in results if r['expected_type'] == 'semantic']

if direct_verse_tests:
    dv_success = sum(1 for r in direct_verse_tests if r['success'])
    print(f"\nDirect Verse Accuracy: {dv_success}/{len(direct_verse_tests)} ({dv_success/len(direct_verse_tests)*100:.1f}%)")

if semantic_tests:
    sem_success = sum(1 for r in semantic_tests if r['success'])
    print(f"Semantic Query Accuracy: {sem_success}/{len(semantic_tests)} ({sem_success/len(semantic_tests)*100:.1f}%)")

# Check if we meet the target
success_rate = passed / len(test_cases) * 100
if success_rate >= 95:
    print(f"\n🎉 TARGET MET! Achieved {success_rate:.1f}% accuracy (target: 95-98%)")
else:
    print(f"\n⚠️  Below target: {success_rate:.1f}% accuracy (target: 95-98%)")

print("=" * 80)