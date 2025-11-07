#!/usr/bin/env python3
"""
Test the pattern matching improvements on the live Tafsir Simplified API
Tests with both scholar and new revert profiles to verify routing
"""

import requests
import json
import time
from datetime import datetime

# API endpoint
API_URL = "https://tafsir-simplified-6b262.uk.r.appspot.com/api/rag_search"

# Test profiles
PROFILES = {
    "scholar": {
        "name": "Scholar Profile",
        "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjU0NTEzMjA5OWFkNmJmNjEzODJiNmI0Y2RlOWEyZGZlZDhjYjMwZjAiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vdGFmc2lyLXNpbXBsaWZpZWQtNmIyNjIiLCJhdWQiOiJ0YWZzaXItc2ltcGxpZmllZC02YjI2MiIsImF1dGhfdGltZSI6MTc2MTUyMDUyNywidXNlcl9pZCI6ImN3MHpESWE5WXdZZTd4WklSd0VtNmlIVmxVdzEiLCJzdWIiOiJjdzB6RElhOVl3WWU3eFpJUndFbTZpSFZsVXcxIiwiaWF0IjoxNzYyNDgwMzM5LCJleHAiOjE3NjI0ODM5MzksImVtYWlsIjoiYWhtZWRzaGVpazEyMzRAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJmaXJlYmFzZSI6eyJpZGVudGl0aWVzIjp7ImVtYWlsIjpbImFobWVkc2hlaWsxMjM0QGdtYWlsLmNvbSJdfSwic2lnbl9pbl9wcm92aWRlciI6InBhc3N3b3JkIn19.Qjhah0s2cric4I-g1CQ--IGxvlNbVmrBHnvIuZDvzFUtaS_o71EDooVlkqWN_3UrY5lZzBjVB6bOolf5ZyViA9wrfdcGE5IkUkvBBNZ9KcGdvNvmFf9HL-xnwAhgEd8o6ViR3yY73y1pipzbO9oVGqi_ZAvpEDxX9EssZOdP_neLrkl_S89AtLpUVaOpR6J-auUs7W_WzXJ6dn639nY3RSZhd-efIsXGFdzrP6hmPTVa7sqpLhIM3Kx3jMA7sBGk8bBnYHEQ9wR8NIjca8HVEyvWnE_PglgtZqTg-FMLl-DwokXfVDKXkl-yLdFUPGzE13w-rp4E36CEo8FYX8Jxvg"
    },
    "new_revert": {
        "name": "New Revert Profile",
        "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjU0NTEzMjA5OWFkNmJmNjEzODJiNmI0Y2RlOWEyZGZlZDhjYjMwZjAiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vdGFmc2lyLXNpbXBsaWZpZWQtNmIyNjIiLCJhdWQiOiJ0YWZzaXItc2ltcGxpZmllZC02YjI2MiIsImF1dGhfdGltZSI6MTc2MjQ4MDM1NCwidXNlcl9pZCI6Ik1pZmJtNXAyYUNOc0p1YXZ3aGdLaEd4UXNwMjMiLCJzdWIiOiJNaWZibTVwMmFDTnNKdWF2d2hnS2hHeFFzcDIzIiwiaWF0IjoxNzYyNDgwMzU0LCJleHAiOjE3NjI0ODM5NTQsImVtYWlsIjoid2Vxd2VxZXdxQGQuY29tIiwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJmaXJlYmFzZSI6eyJpZGVudGl0aWVzIjp7ImVtYWlsIjpbIndlcXdlcWV3cUBkLmNvbSJdfSwic2lnbl9pbl9wcm92aWRlciI6InBhc3N3b3JkIn19.WSFCZK_NLjRkbc0GDLGoKeqNpDk3PbaiHszcxgtuw0m0oqfxQmlqhIVNc-xeBs6BYfqCbhRN7TTS-ADu2OBAr6MEdGk865Bg8a6FJ3RkbObuDg_TpJsauaYdpws01-2Jhc9quFtEn6HbB9xE76Q1cOHBqUqqwmD1G9QEtejDc6mimohVK5TVm9DJB9xgq_qw-2yuz43wLaa3cfp-mdbN56I7iUvnpPgE-iF9Rwlp_XsZy9_cw9HnSJGy5vwqVpDmBDAkj3Ge8T2Jk87O2zJKcxsUrA2-6MSCiI8rTBFWoIFZdhx7OhPLtDm2f86_R73oxip-ca-ylZbEBSBNmYDRNQ"
    }
}

# Test queries with expected results
TEST_QUERIES = [
    {
        "query": "Surah Fatir, Verse 6",
        "description": "Comma-separated pattern (the bug from logs)",
        "expected_route": "direct_verse",
        "expected_verse": "35:6"
    },
    {
        "query": "Surah Al-Kahf verse 1-10",
        "description": "Verse range query",
        "expected_route": "direct_verse",
        "expected_range": "18:1-10"
    },
    {
        "query": "Show me ayat al kursi",
        "description": "Natural language prefix",
        "expected_route": "direct_verse",
        "expected_verse": "2:255"
    },
    {
        "query": "2.255",
        "description": "Alternative separator - period",
        "expected_route": "direct_verse",
        "expected_verse": "2:255"
    },
    {
        "query": "verse 255 of Al-Baqarah",
        "description": "Reversed order pattern",
        "expected_route": "direct_verse",
        "expected_verse": "2:255"
    },
    {
        "query": "Spider verse 41",
        "description": "English Surah name alias",
        "expected_route": "direct_verse",
        "expected_verse": "29:41"
    },
    {
        "query": "hijab verse",
        "description": "Named verse - new addition",
        "expected_route": "direct_verse",
        "expected_verse": "24:31"
    },
    {
        "query": "verses 1-5 of Surah Maryam",
        "description": "Range with reversed order",
        "expected_route": "direct_verse",
        "expected_range": "19:1-5"
    },
    {
        "query": "s2v255",
        "description": "Abbreviated format",
        "expected_route": "direct_verse",
        "expected_verse": "2:255"
    },
    {
        "query": "I want to read the throne verse",
        "description": "Complex natural language",
        "expected_route": "direct_verse",
        "expected_verse": "2:255"
    }
]

def test_query(query, token, profile_name):
    """Test a single query with given auth token"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "filters": {}
    }

    start_time = time.time()

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        response_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()

            # Extract key info
            result = {
                "success": True,
                "response_time": round(response_time, 2),
                "classification": data.get("classification", "unknown"),
                "route": data.get("route_taken", "unknown"),
                "confidence": data.get("confidence", 0),
                "verse_detected": data.get("verse_reference"),
                "status_code": response.status_code
            }

            # Check if response contains verse text
            if "response" in data:
                response_text = data["response"]
                # Check for verse numbers in response (indicates verses were returned)
                if "1." in response_text or "Verse " in response_text:
                    result["verses_returned"] = True
                else:
                    result["verses_returned"] = False

            return result

        else:
            return {
                "success": False,
                "response_time": round(response_time, 2),
                "status_code": response.status_code,
                "error": response.text[:200]
            }

    except Exception as e:
        return {
            "success": False,
            "response_time": round(time.time() - start_time, 2),
            "error": str(e)
        }

def print_results(query_info, result, profile_name):
    """Print formatted test results"""
    print(f"\n{'='*70}")
    print(f"Query: '{query_info['query']}'")
    print(f"Profile: {profile_name}")
    print(f"Description: {query_info['description']}")
    print(f"-"*70)

    if result['success']:
        # Check if classification matches expected
        route_match = result.get('classification') == query_info['expected_route']
        status_icon = "✅" if route_match else "❌"

        print(f"{status_icon} Classification: {result.get('classification')} (expected: {query_info['expected_route']})")
        print(f"   Route taken: {result.get('route', 'N/A')}")
        print(f"   Confidence: {result.get('confidence', 0):.0%}")
        print(f"   Response time: {result['response_time']}s")

        if result['response_time'] < 5:
            print(f"   ⚡ Fast response (under 5s)")
        elif result['response_time'] < 10:
            print(f"   ⏱️  Moderate response (5-10s)")
        else:
            print(f"   🐌 Slow response (over 10s)")

        if result.get('verse_detected'):
            print(f"   Verse detected: {result['verse_detected']}")

        if 'expected_range' in query_info and result.get('verses_returned'):
            print(f"   ✅ Multiple verses returned for range")
    else:
        print(f"❌ ERROR: {result.get('error', 'Unknown error')}")
        print(f"   Status code: {result.get('status_code', 'N/A')}")
        print(f"   Response time: {result['response_time']}s")

def main():
    print("="*70)
    print("TAFSIR SIMPLIFIED PATTERN MATCHING TEST")
    print(f"Testing {len(TEST_QUERIES)} queries across {len(PROFILES)} profiles")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Test with each profile
    for profile_key, profile_data in PROFILES.items():
        print(f"\n{'#'*70}")
        print(f"TESTING WITH {profile_data['name'].upper()}")
        print(f"{'#'*70}")

        success_count = 0
        fast_count = 0
        total_time = 0

        for i, query_info in enumerate(TEST_QUERIES, 1):
            print(f"\nTest {i}/{len(TEST_QUERIES)}")
            result = test_query(query_info['query'], profile_data['token'], profile_data['name'])
            print_results(query_info, result, profile_data['name'])

            if result['success']:
                if result.get('classification') == query_info['expected_route']:
                    success_count += 1
                if result['response_time'] < 5:
                    fast_count += 1
                total_time += result['response_time']

            # Small delay between requests
            time.sleep(0.5)

        # Summary for this profile
        print(f"\n{'='*70}")
        print(f"SUMMARY FOR {profile_data['name'].upper()}")
        print(f"{'='*70}")
        print(f"Correctly classified: {success_count}/{len(TEST_QUERIES)} ({success_count/len(TEST_QUERIES)*100:.0f}%)")
        print(f"Fast responses (<5s): {fast_count}/{len(TEST_QUERIES)} ({fast_count/len(TEST_QUERIES)*100:.0f}%)")
        if success_count > 0:
            avg_time = total_time / success_count
            print(f"Average response time: {avg_time:.2f}s")

        if success_count == len(TEST_QUERIES):
            print("🎉 ALL PATTERNS CORRECTLY CLASSIFIED!")
        elif success_count >= len(TEST_QUERIES) * 0.95:
            print("✅ 95%+ accuracy achieved!")
        else:
            print(f"⚠️  Below target: {success_count/len(TEST_QUERIES)*100:.0f}% (target: 95%)")

if __name__ == "__main__":
    main()