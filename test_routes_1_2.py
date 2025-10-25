#!/usr/bin/env python3
"""
Systematic test for Routes 1 & 2 (METADATA QUERY and DIRECT VERSE QUERY)
"""

import requests
import json
import time
from typing import Dict, List

# Backend URL
BACKEND_URL = "https://tafsir-backend-612616741510.us-central1.run.app/tafsir"

# Auth token
AUTH_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjlkMjEzMGZlZjAyNTg3ZmQ4ODYxODg2OTgyMjczNGVmNzZhMTExNjUiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vdGFmc2lyLXNpbXBsaWZpZWQtNmIyNjIiLCJhdWQiOiJ0YWZzaXItc2ltcGxpZmllZC02YjI2MiIsImF1dGhfdGltZSI6MTc2MDc1Mjc5NywidXNlcl9pZCI6InNnVlRKNmgyREZlUXNwRXdUTTlsaURDNkZvcTEiLCJzdWIiOiJzZ1ZUSjZoMkRGZVFzcEV3VE05bGlEQzZGb3ExIiwiaWF0IjoxNzYxMDA5Njg3LCJleHAiOjE3NjEwMTMyODcsImVtYWlsIjoidGVzdHRlc3R0ZXN0MTIzQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJlbWFpbCI6WyJ0ZXN0dGVzdHRlc3QxMjNAZ21haWwuY29tIl19LCJzaWduX2luX3Byb3ZpZGVyIjoicGFzc3dvcmQifX0.d75iY6uYNfkCzZRxrZIhW-3Xcb6NGNajV30Nzi5UWIUBsr8ztR8i4Lrk78fu1CvL4Klm6XVPO9S24r5lIIsYBBBwdO7MoOPAmE4_uwV-cYYWIZrUcD4T2DCbEm9WWm-Rt1K6OpfcNeWDU8x1I7-oFEX1MqY8PEbTrSliOI7G4shlLo0_9JinrRTtMPc5im2oW5-qY5hwUTk52Qr40atDeezfk2vyDaa5-Uy77GMX5Ninarr1P2CUsLNs5ZgMucyHoYo_vQi0_k30M-jMX9FhMdzrhXJ3V34PayeynEvpXPA4ToEFFB3vS8GwiG5CJa_XU2RwINVG8dEUTohbbO-11g"

# Test queries specifically for Routes 1 & 2
ROUTE_1_2_TESTS = [
    # ===== ROUTE 2: DIRECT VERSE QUERIES (Tafsir-based) =====
    # Should use direct lookup for verse tafsir
    {
        "name": "Single verse in al-Qurtubi coverage (Surah 2)",
        "query": "2:255",  # Ayat al-Kursi - should be in al-Qurtubi
        "expected_route": "ROUTE 2",
        "should_succeed": True
    },
    {
        "name": "Single verse in al-Qurtubi coverage (Surah 1)",
        "query": "1:1",  # Al-Fatiha first verse
        "expected_route": "ROUTE 2",
        "should_succeed": True
    },
    {
        "name": "Verse range in al-Qurtubi coverage",
        "query": "2:1-5",  # First 5 verses of Al-Baqarah
        "expected_route": "ROUTE 2",
        "should_succeed": True
    },
    {
        "name": "Problematic verse from analysis: 3:26-27",
        "query": "3:26-27",
        "expected_route": "ROUTE 2",
        "should_succeed": True  # Should be in al-Qurtubi (covers 1-4)
    },
    {
        "name": "Problematic verse from analysis: 17:23-24",
        "query": "17:23-24",
        "expected_route": "ROUTE 2",
        "should_succeed": False  # Outside al-Qurtubi, may fallback to Route 3
    },
    {
        "name": "Problematic verse from analysis: 18:65-70",
        "query": "18:65-70",
        "expected_route": "ROUTE 2",
        "should_succeed": False  # Outside al-Qurtubi coverage
    },
    {
        "name": "Single verse at boundary (Surah 4:1)",
        "query": "4:1",
        "expected_route": "ROUTE 2",
        "should_succeed": True  # Should be in al-Qurtubi
    },
    {
        "name": "Verse range multi-verse",
        "query": "1:1-7",  # All of Al-Fatiha
        "expected_route": "ROUTE 2",
        "should_succeed": True
    },

    # ===== Edge cases =====
    {
        "name": "Outside al-Qurtubi but might have Ibn Kathir",
        "query": "36:1-7",  # Ya-Sin
        "expected_route": "ROUTE 2 or 3",
        "should_succeed": None  # Depends on Ibn Kathir coverage
    },
]

def run_test(test: Dict) -> Dict:
    """Run a single test query"""
    print(f"\n{'='*80}")
    print(f"TEST: {test['name']}")
    print(f"QUERY: {test['query']}")
    print(f"EXPECTED ROUTE: {test['expected_route']}")
    print(f"{'='*80}")

    payload = {
        "query": test["query"],
        "user_id": "test_user",
        "preferences": {
            "persona": "student"
        }
    }

    start_time = time.time()

    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(BACKEND_URL, json=payload, headers=headers, timeout=30)
        duration = time.time() - start_time

        if response.status_code == 200:
            data = response.json()

            # Debug: Print raw response structure
            print(f"\n🔍 RAW RESPONSE KEYS: {list(data.keys())}")
            if "response" in data:
                resp = data["response"]
                print(f"🔍 RESPONSE TYPE: {type(resp)}")
                if isinstance(resp, dict):
                    print(f"🔍 RESPONSE KEYS: {list(resp.keys())}")
                else:
                    print(f"🔍 RESPONSE VALUE (first 200 chars): {str(resp)[:200]}")

            # Extract route information - handle both dict and string responses
            response_data = data.get("response", {})

            # If response is a string, it might be an error
            if isinstance(response_data, str):
                route = "UNKNOWN"
                answer = response_data
                sources = []
            else:
                route = response_data.get("route", "UNKNOWN")
                answer = response_data.get("answer", "")
                sources = response_data.get("sources", [])

            # Check for errors in the answer
            has_error = any(phrase in answer.lower() for phrase in [
                "malformed",
                "does not contain",
                "cannot be provided",
                "no relevant information",
                "error"
            ])

            result = {
                "status": "SUCCESS" if not has_error else "PARTIAL",
                "route": route,
                "sources": sources,
                "answer_length": len(answer),
                "duration": f"{duration:.2f}s",
                "has_error": has_error,
                "error_message": answer[:200] if has_error else None
            }

            print(f"\n✅ STATUS: {result['status']}")
            print(f"📍 ROUTE: {result['route']}")
            print(f"📚 SOURCES: {', '.join(sources) if sources else 'None'}")
            print(f"📝 ANSWER LENGTH: {result['answer_length']} chars")
            print(f"⏱️  DURATION: {result['duration']}")

            if has_error:
                print(f"\n⚠️  ERROR DETECTED IN ANSWER:")
                print(f"   {result['error_message']}...")

            return result

        else:
            print(f"\n❌ HTTP ERROR: {response.status_code}")
            print(f"   {response.text[:500]}")

            return {
                "status": "FAILED",
                "route": "N/A",
                "error": f"HTTP {response.status_code}",
                "duration": f"{duration:.2f}s"
            }

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ EXCEPTION: {str(e)}")

        return {
            "status": "EXCEPTION",
            "route": "N/A",
            "error": str(e),
            "duration": f"{duration:.2f}s"
        }

def main():
    """Run all tests and generate report"""
    print(f"\n{'#'*80}")
    print(f"# ROUTES 1 & 2 SYSTEMATIC TEST")
    print(f"# Testing METADATA QUERY and DIRECT VERSE QUERY routes")
    print(f"{'#'*80}\n")

    results = []

    for test in ROUTE_1_2_TESTS:
        result = run_test(test)
        result["test_name"] = test["name"]
        result["query"] = test["query"]
        result["expected_route"] = test["expected_route"]
        result["should_succeed"] = test["should_succeed"]
        results.append(result)

        # Brief pause between tests
        time.sleep(2)

    # Generate summary
    print(f"\n\n{'#'*80}")
    print(f"# SUMMARY REPORT")
    print(f"{'#'*80}\n")

    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    partial_count = sum(1 for r in results if r["status"] == "PARTIAL")
    failed_count = sum(1 for r in results if r["status"] in ["FAILED", "EXCEPTION"])
    total = len(results)

    print(f"TOTAL TESTS: {total}")
    print(f"✅ SUCCESS: {success_count} ({success_count/total*100:.1f}%)")
    print(f"⚠️  PARTIAL: {partial_count} ({partial_count/total*100:.1f}%)")
    print(f"❌ FAILED: {failed_count} ({failed_count/total*100:.1f}%)")

    # Route breakdown
    print(f"\n{'='*80}")
    print(f"ROUTE USAGE:")
    route_counts = {}
    for r in results:
        route = r.get("route", "N/A")
        route_counts[route] = route_counts.get(route, 0) + 1

    for route, count in sorted(route_counts.items()):
        print(f"  {route}: {count} queries")

    # Issues found
    print(f"\n{'='*80}")
    print(f"ISSUES FOUND:")

    issues = [r for r in results if r["status"] != "SUCCESS"]
    if not issues:
        print("  None! All tests passed ✅")
    else:
        for issue in issues:
            print(f"\n  ❌ {issue['test_name']}")
            print(f"     Query: {issue['query']}")
            print(f"     Status: {issue['status']}")
            print(f"     Route: {issue['route']}")
            if issue.get("error_message"):
                print(f"     Error: {issue['error_message'][:100]}...")

    # Save detailed results
    with open("test_routes_1_2_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📄 Detailed results saved to: test_routes_1_2_results.json")

if __name__ == "__main__":
    main()
