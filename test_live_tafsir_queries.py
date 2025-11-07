#!/usr/bin/env python3
"""
Test live tafsir queries against the backend to check verse range handling
"""
import requests
import json

# Use the live backend URL
BACKEND_URL = "https://tafsir-backend-612616741510.us-central1.run.app"

# Test queries
TEST_QUERIES = [
    {
        "name": "As-Sajdah 1-9 (user's issue)",
        "query": "Surah As-Sajdah verse 1-9",
        "expected_verses": list(range(1, 10)),
        "approach": "tafsir"
    },
    {
        "name": "Al-Kahf 1-10 (user's issue)",
        "query": "Surah Al-Kahf verse 1-10",
        "expected_verses": list(range(1, 11)),
        "approach": "tafsir"
    },
    {
        "name": "Al-Waqi'ah 1-9 (previous issue)",
        "query": "Surah Al-Waqi'ah verse 1-9",
        "expected_verses": list(range(1, 10)),
        "approach": "tafsir"
    },
    {
        "name": "Numeric format 32:1-9",
        "query": "32:1-9",
        "expected_verses": list(range(1, 10)),
        "approach": "tafsir"
    },
    {
        "name": "Al-Baqarah 255-257 (should work - popular verses)",
        "query": "Surah Al-Baqarah verse 255-257",
        "expected_verses": [255, 256, 257],
        "approach": "tafsir"
    },
    {
        "name": "Al-Fatihah 1-7 (complete short surah)",
        "query": "Surah Al-Fatihah verse 1-7",
        "expected_verses": list(range(1, 8)),
        "approach": "tafsir"
    },
]


def test_query(test_case):
    """Test a single query"""
    print(f"\n{'='*80}")
    print(f"TEST: {test_case['name']}")
    print(f"Query: {test_case['query']}")
    print(f"{'='*80}")

    payload = {
        "query": test_case["query"],
        "user_id": "test_user",
        "approach": test_case["approach"]
    }

    try:
        response = requests.post(f"{BACKEND_URL}/tafsir", json=payload, timeout=30)

        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            print(f"   {response.text[:500]}")
            return {
                "name": test_case["name"],
                "status": "error",
                "http_code": response.status_code,
                "expected_verses": len(test_case["expected_verses"]),
                "returned_verses": 0
            }

        data = response.json()

        # Check if needs clarification
        if data.get('needs_clarification'):
            print(f"⚠️  Needs clarification: {data.get('message')}")
            return {
                "name": test_case["name"],
                "status": "needs_clarification",
                "expected_verses": len(test_case["expected_verses"]),
                "returned_verses": 0
            }

        # Extract verses returned
        returned_verses = data.get('verses', [])
        returned_verse_numbers = [int(v.get('verse_number', 0)) for v in returned_verses]

        # Check tafsir explanations
        tafsir_explanations = data.get('tafsir_explanations', [])

        print(f"\n✓ Response received")
        print(f"  Expected verses: {test_case['expected_verses']}")
        print(f"  Returned verses: {returned_verse_numbers}")
        print(f"  Tafsir sources: {len(tafsir_explanations)}")

        # Check coverage
        missing_verses = set(test_case['expected_verses']) - set(returned_verse_numbers)
        extra_verses = set(returned_verse_numbers) - set(test_case['expected_verses'])

        if missing_verses:
            print(f"  ⚠️  Missing verses: {sorted(missing_verses)}")

        if extra_verses:
            print(f"  ℹ️  Extra verses: {sorted(extra_verses)}")

        # Analyze tafsir explanations
        for tafsir in tafsir_explanations:
            source = tafsir.get('source', 'Unknown')
            sections = tafsir.get('sections', [])
            text = tafsir.get('text', '')

            # Check for "limitations" or "not available" messages
            if 'limitation' in text.lower() or 'not available' in text.lower():
                print(f"  ⚠️  {source}: Contains 'limitation' or 'not available' message")
                print(f"      Preview: {text[:200]}...")

            print(f"  {source}: {len(sections)} sections, {len(text)} chars")

        # Determine status
        if missing_verses:
            status = "incomplete"
        elif any('limitation' in t.get('text', '').lower() for t in tafsir_explanations):
            status = "limited_source_data"
        else:
            status = "complete"

        return {
            "name": test_case["name"],
            "status": status,
            "expected_verses": len(test_case["expected_verses"]),
            "returned_verses": len(returned_verse_numbers),
            "missing_verses": len(missing_verses),
            "has_limitations_message": any('limitation' in t.get('text', '').lower() for t in tafsir_explanations)
        }

    except requests.Timeout:
        print(f"❌ Request timeout")
        return {
            "name": test_case["name"],
            "status": "timeout",
            "expected_verses": len(test_case["expected_verses"]),
            "returned_verses": 0
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            "name": test_case["name"],
            "status": "exception",
            "expected_verses": len(test_case["expected_verses"]),
            "returned_verses": 0,
            "error": str(e)
        }


def main():
    """Run all tests"""
    print("="*80)
    print("LIVE TAFSIR QUERY TESTING")
    print("="*80)

    results = []

    for test_case in TEST_QUERIES:
        result = test_query(test_case)
        results.append(result)

    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    complete = sum(1 for r in results if r['status'] == 'complete')
    incomplete = sum(1 for r in results if r['status'] == 'incomplete')
    limited = sum(1 for r in results if r['status'] == 'limited_source_data')
    errors = sum(1 for r in results if r['status'] in ['error', 'timeout', 'exception'])

    print(f"\nTotal tests: {len(results)}")
    print(f"  ✅ Complete: {complete}")
    print(f"  ⚠️  Incomplete verses: {incomplete}")
    print(f"  📚 Limited source data: {limited}")
    print(f"  ❌ Errors: {errors}")

    print(f"\nDetailed Results:")
    for r in results:
        status_icon = {
            'complete': '✅',
            'incomplete': '⚠️ ',
            'limited_source_data': '📚',
            'error': '❌',
            'timeout': '⏱️ ',
            'exception': '❌',
            'needs_clarification': '🤔'
        }.get(r['status'], '?')

        print(f"  {status_icon} {r['name']}: {r['returned_verses']}/{r['expected_verses']} verses")
        if r.get('missing_verses', 0) > 0:
            print(f"      Missing {r['missing_verses']} verses")
        if r.get('has_limitations_message'):
            print(f"      Contains 'limitations' message in tafsir")


if __name__ == "__main__":
    main()
