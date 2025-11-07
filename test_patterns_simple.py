#!/usr/bin/env python3
"""
Simple test of pattern matching without full app initialization
"""

import os
import re
from typing import Optional, Tuple, Dict, Any

# Mock environment variables to prevent startup error
os.environ['FIREBASE_CREDENTIAL'] = 'mock'
os.environ['GCS_BUCKET_NAME'] = 'mock'
os.environ['PROJECT_NUMBER'] = '123'
os.environ['INDEX_ENDPOINT_ID'] = 'mock'
os.environ['DEPLOYED_INDEX_ID'] = 'mock'

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Import after setting env vars
from app import (
    classify_query_enhanced,
    extract_verse_range,
    extract_verse_reference_enhanced,
    normalize_query_text
)

# Quick test cases focusing on the issues we fixed
test_cases = [
    # Original issue: verse ranges
    ("Surah Al-Kahf verse 1-10", "Should route to direct_verse for ranges"),
    ("Al-Baqarah 255-256", "Range without 'verse' keyword"),
    ("2:255-257", "Numeric range"),

    # Comma pattern (the bug from logs)
    ("Surah Fatir, Verse 6", "Comma-separated pattern"),
    ("Al-Baqarah, 255", "Surah comma verse"),

    # Alternative separators
    ("2.255", "Period separator"),
    ("2/255", "Slash separator"),

    # Reversed patterns
    ("verse 255 of Al-Baqarah", "Verse X of Surah"),
    ("verses 1-10 of Al-Kahf", "Range reversed"),

    # Natural language prefixes
    ("Show me 2:255", "Show me prefix"),
    ("Give me ayat al kursi", "Give me + named verse"),
    ("I want to read Al-Kahf 1-10", "I want prefix + range"),

    # Named verses
    ("ayat al kursi", "Named verse"),
    ("throne verse", "English named verse"),
    ("spider verse", "New named verse"),

    # Aliases
    ("cow 255", "English surah name"),
    ("cave 10", "English name"),
    ("elephant 1", "English name"),

    # Should be semantic
    ("what does patience mean", "Pure semantic"),
    ("explain the concept of taqwa", "Concept query"),
]

print("=" * 70)
print("TESTING KEY PATTERN FIXES")
print("=" * 70)

for query, description in test_cases:
    print(f"\nQuery: '{query}'")
    print(f"Description: {description}")
    print("-" * 40)

    # Test normalization
    normalized = normalize_query_text(query)
    print(f"  Normalized: '{normalized}'")

    # Test verse extraction
    verse_ref = extract_verse_reference_enhanced(query)
    verse_range = extract_verse_range(query)
    print(f"  Verse ref: {verse_ref}")
    if verse_range and verse_range[1] != verse_range[2]:  # It's an actual range
        print(f"  Verse range: {verse_range}")

    # Test classification
    classification = classify_query_enhanced(query)
    print(f"  Classification: {classification['query_type']} (confidence: {classification['confidence']:.0%})")

    # Check if it's correctly routed
    if "range" in description.lower() or "1-10" in query or "255-" in query:
        if classification['query_type'] == 'direct_verse':
            print(f"  ✅ CORRECT: Range query routed to direct_verse")
        else:
            print(f"  ❌ ERROR: Range query misclassified as {classification['query_type']}")
    elif "semantic" in description.lower():
        if classification['query_type'] == 'semantic':
            print(f"  ✅ CORRECT: Semantic query properly identified")
        else:
            print(f"  ❌ ERROR: Semantic query misclassified as {classification['query_type']}")
    elif verse_ref:
        if classification['query_type'] == 'direct_verse':
            print(f"  ✅ CORRECT: Verse query routed to direct_verse")
        else:
            print(f"  ❌ ERROR: Verse query misclassified as {classification['query_type']}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)