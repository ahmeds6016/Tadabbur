#!/usr/bin/env python3
"""
Test script to verify query classification fix for verse range queries
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import classify_query_enhanced, extract_verse_range, extract_verse_reference_enhanced

# Test cases that were failing
test_queries = [
    "Surah Al-Kahf verse 1-10",
    "Al-Baqarah 255-256",
    "Surah Maryam verse 1-10",
    "verses 1-10 of Al-Kahf",
    "2:255",  # Should still work for single verses
    "ayat al kursi",  # Named verse
    "what does patience mean in Islam"  # Should be semantic
]

print("=" * 70)
print("TESTING QUERY CLASSIFICATION FIX")
print("=" * 70)

for query in test_queries:
    print(f"\nQuery: '{query}'")
    print("-" * 40)

    # Test verse extraction
    verse_ref = extract_verse_reference_enhanced(query)
    verse_range = extract_verse_range(query)

    # Test classification
    classification = classify_query_enhanced(query)

    print(f"  Verse ref: {verse_ref}")
    print(f"  Verse range: {verse_range}")
    print(f"  Classification: {classification['query_type']} (confidence: {classification['confidence']:.0%})")

    # Check if it's correctly routed
    if verse_range and classification['query_type'] != 'direct_verse':
        print(f"  ❌ ERROR: Has verse range but classified as {classification['query_type']}")
    elif verse_range and classification['query_type'] == 'direct_verse':
        print(f"  ✅ CORRECT: Verse range query routed to direct_verse (Route 2)")
    elif verse_ref and not verse_range and classification['query_type'] == 'direct_verse':
        print(f"  ✅ CORRECT: Single verse query routed to direct_verse (Route 2)")
    elif not verse_ref and classification['query_type'] == 'semantic':
        print(f"  ✅ CORRECT: Semantic query routed to semantic search (Route 3)")
    else:
        print(f"  ⚠️  Check routing logic")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)