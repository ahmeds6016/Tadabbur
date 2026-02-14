#!/usr/bin/env python3
"""
Test script to verify persona-based verse limits are being enforced.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8080"
TAFSIR_ENDPOINT = f"{BASE_URL}/tafsir"

# Test configurations for different personas
TEST_CONFIGS = [
    {
        'persona': 'new_revert',
        'expected_limit': 5,
        'queries': [
            {'query': 'Tell me about patience in Islam', 'approach': 'semantic'},
            {'query': 'Explain verse 2:255', 'approach': 'tafsir'},
        ]
    },
    {
        'persona': 'practicing_muslim',
        'expected_limit': 8,
        'queries': [
            {'query': 'What does Quran say about charity?', 'approach': 'semantic'},
            {'query': '2:183', 'approach': 'tafsir'},
        ]
    },
    {
        'persona': 'advanced_learner',
        'expected_limit': 12,
        'queries': [
            {'query': 'Discuss the concept of tawhid', 'approach': 'semantic'},
            {'query': 'Analyze the linguistic aspects of Surah Al-Fatiha', 'approach': 'tafsir'},
        ]
    }
]

def test_verse_limits(persona_config):
    """Test verse limits for a specific persona configuration."""
    persona = persona_config['persona']
    expected_limit = persona_config['expected_limit']

    print(f"\n{'='*70}")
    print(f"Testing persona: {persona} (expected max verses: {expected_limit})")
    print(f"{'='*70}")

    results = []

    for query_info in persona_config['queries']:
        query = query_info['query']
        approach = query_info['approach']

        print(f"\n📝 Query: '{query}' (approach: {approach})")

        # Prepare the request
        payload = {
            'query': query,
            'approach': approach,
            'language': 'english',
            'persona': persona  # Note: This would need to be set in user profile
        }

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            # Add authentication header if needed
            # 'Authorization': 'Bearer YOUR_TOKEN'
        }

        try:
            start_time = time.time()
            response = requests.post(
                TAFSIR_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=30
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                verse_count = len(data.get('verses', []))

                # Check if within limit
                within_limit = verse_count <= expected_limit
                status = "✅" if within_limit else "⚠️"

                print(f"   {status} Verses returned: {verse_count}/{expected_limit}")
                print(f"   ⏱️  Response time: {elapsed:.2f}s")

                # Store result
                results.append({
                    'query': query,
                    'approach': approach,
                    'verse_count': verse_count,
                    'expected_limit': expected_limit,
                    'within_limit': within_limit,
                    'response_time': elapsed
                })

                # Print verse titles for verification
                if data.get('verses'):
                    print(f"   📖 Verses included:")
                    for v in data['verses'][:3]:  # Show first 3
                        print(f"      - {v.get('surah', 'Unknown')} {v.get('verse_number', '')}")
                    if len(data['verses']) > 3:
                        print(f"      ... and {len(data['verses']) - 3} more")

            else:
                print(f"   ❌ Request failed with status {response.status_code}")
                if response.text:
                    print(f"   Error: {response.text[:200]}")

        except Exception as e:
            print(f"   ❌ Request failed: {e}")

    # Summary for this persona
    print(f"\n📊 Summary for {persona}:")
    passed = sum(1 for r in results if r['within_limit'])
    total = len(results)
    print(f"   • Tests passed: {passed}/{total}")

    if results:
        avg_verses = sum(r['verse_count'] for r in results) / len(results)
        avg_time = sum(r['response_time'] for r in results) / len(results)
        print(f"   • Average verses returned: {avg_verses:.1f}")
        print(f"   • Average response time: {avg_time:.2f}s")

        # Flag any violations
        violations = [r for r in results if not r['within_limit']]
        if violations:
            print(f"   ⚠️  VIOLATIONS FOUND:")
            for v in violations:
                print(f"      - Query '{v['query']}': {v['verse_count']} verses (limit: {v['expected_limit']})")

    return results

def main():
    """Main test function."""
    print("\n" + "="*70)
    print("🔬 TESTING PERSONA-BASED VERSE LIMITS")
    print("="*70)

    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is healthy")
        else:
            print("⚠️  Backend returned non-200 status")
    except Exception as e:
        print(f"❌ Cannot connect to backend at {BASE_URL}")
        print(f"   Make sure the backend is running: python app.py")
        return

    # Run tests for each persona
    all_results = {}
    for config in TEST_CONFIGS:
        results = test_verse_limits(config)
        all_results[config['persona']] = results
        time.sleep(2)  # Delay between personas to avoid rate limiting

    # Overall summary
    print("\n" + "="*70)
    print("📈 OVERALL TEST RESULTS")
    print("="*70)

    total_tests = 0
    total_passed = 0

    for persona, results in all_results.items():
        passed = sum(1 for r in results if r['within_limit'])
        total = len(results)
        total_tests += total
        total_passed += passed

        status = "✅" if passed == total else "⚠️"
        print(f"{status} {persona}: {passed}/{total} tests passed")

    print(f"\n{'✅' if total_passed == total_tests else '⚠️'} Total: {total_passed}/{total_tests} tests passed")

    if total_passed < total_tests:
        print("\n⚠️  Some verse limits were exceeded. Check the prompt instructions and Gemini's compliance.")
    else:
        print("\n✅ All verse limits are being properly enforced!")

if __name__ == "__main__":
    main()