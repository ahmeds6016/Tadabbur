#!/usr/bin/env python3
"""
Comprehensive Route 1 & 2 Testing with Deep Logging
Tests via the /debug/test endpoint to get full execution traces
"""

import requests
import json
import time
from datetime import datetime

# Test Configuration
DEBUG_ENDPOINT = "https://tafsir-backend-612616741510.us-central1.run.app/debug/test"

# Test cases specifically for Routes 1 & 2
TEST_QUERIES = [
    # Route 2: Single verses
    {
        "query": "2:255",
        "name": "Ayat al-Kursi (Single verse in al-Qurtubi coverage)",
        "expected_route": "ROUTE 2",
        "expected_sources": ["al-Qurtubi", "Ibn Kathir"],
        "should_succeed": True
    },
    {
        "query": "1:1",
        "name": "Al-Fatiha first verse (Single verse)",
        "expected_route": "ROUTE 2",
        "expected_sources": ["al-Qurtubi", "Ibn Kathir"],
        "should_succeed": True
    },

    # Route 2: Verse ranges
    {
        "query": "1:1-7",
        "name": "Full Al-Fatiha (Verse range)",
        "expected_route": "ROUTE 2",
        "expected_sources": ["al-Qurtubi", "Ibn Kathir"],
        "should_succeed": True
    },
    {
        "query": "2:1-5",
        "name": "Al-Baqarah 1-5 (Verse range)",
        "expected_route": "ROUTE 2",
        "expected_sources": ["al-Qurtubi", "Ibn Kathir"],
        "should_succeed": True
    },
    {
        "query": "36:1-7",
        "name": "Ya-Sin 1-7 (Outside al-Qurtubi)",
        "expected_route": "ROUTE 2",
        "expected_sources": ["Ibn Kathir"],  # Only Ibn Kathir
        "should_succeed": True
    },

    # Problematic cases from analysis
    {
        "query": "3:26-27",
        "name": "PROBLEMATIC: Surah 3:26-27",
        "expected_route": "ROUTE 2",
        "expected_sources": ["al-Qurtubi", "Ibn Kathir"],
        "should_succeed": True
    },
    {
        "query": "4:1",
        "name": "PROBLEMATIC: Surah 4:1 (Boundary)",
        "expected_route": "ROUTE 2",
        "expected_sources": ["al-Qurtubi", "Ibn Kathir"],
        "should_succeed": True
    },
]

def run_test(test_case):
    """Run a single test with comprehensive logging"""
    query = test_case["query"]

    print("\n" + "="*100)
    print(f"🧪 TEST: {test_case['name']}")
    print(f"📝 QUERY: {query}")
    print(f"🎯 EXPECTED ROUTE: {test_case['expected_route']}")
    print("="*100)

    start_time = time.time()

    try:
        # Call debug endpoint
        url = f"{DEBUG_ENDPOINT}/{query}"
        response = requests.get(url, timeout=60)
        duration = time.time() - start_time

        if response.status_code != 200:
            print(f"\n❌ HTTP ERROR: {response.status_code}")
            print(f"Response: {response.text[:1000]}")
            return {
                "status": "HTTP_ERROR",
                "error": f"HTTP {response.status_code}",
                "duration": duration
            }

        data = response.json()

        # Extract key information
        processing_steps = data.get("processing_steps", [])
        response_data = data.get("response", {})
        timings = data.get("timings", {})

        # Print processing steps
        print("\n📋 PROCESSING STEPS:")
        for i, step in enumerate(processing_steps, 1):
            step_name = step.get("step", "Unknown")
            print(f"\n  Step {i}: {step_name}")
            for key, value in step.items():
                if key != "step" and key != "timestamp":
                    print(f"    • {key}: {value}")

        # Print timings
        print("\n⏱️  TIMINGS:")
        for step, timing in timings.items():
            print(f"  • {step}: {timing}")

        # Analyze response
        print("\n📦 RESPONSE ANALYSIS:")

        # Check if it's the unfixed format (string response)
        if isinstance(response_data, str):
            print(f"  ⚠️  UNFIXED FORMAT DETECTED: Response is a STRING (not parsed JSON)")
            print(f"  • Length: {len(response_data)} chars")
            print(f"  • Preview: {response_data[:200]}...")

            result = {
                "status": "UNFIXED_FORMAT",
                "route": "UNKNOWN",
                "duration": duration,
                "response_type": "string"
            }

        elif isinstance(response_data, dict):
            # Check for extraction_error
            has_extraction_error = response_data.get("metadata", {}).get("extraction_error", False)

            if has_extraction_error:
                print(f"  ❌ EXTRACTION ERROR DETECTED")
                print(f"  • Fallback used: {response_data.get('metadata', {}).get('fallback_used')}")
                print(f"  • Response preview: {response_data.get('response', '')[:500]}...")

                result = {
                    "status": "EXTRACTION_ERROR",
                    "route": response_data.get("route", "UNKNOWN"),
                    "duration": duration,
                    "has_extraction_error": True
                }
            else:
                # Check structure
                route = response_data.get("route", "UNKNOWN")
                verses = response_data.get("verses", [])
                tafsir = response_data.get("tafsir_explanations", [])
                sources = response_data.get("sources", [])

                print(f"  ✅ PROPERLY STRUCTURED RESPONSE")
                print(f"  • Route: {route}")
                print(f"  • Verses: {len(verses)} verses")
                print(f"  • Tafsir explanations: {len(tafsir)} sources")
                print(f"  • Sources: {sources}")

                # Check verse structure
                if verses:
                    print(f"\n  📖 VERSE STRUCTURE:")
                    v = verses[0]
                    print(f"    • Surah: {v.get('surah')} (type: {type(v.get('surah')).__name__})")
                    print(f"    • Surah name: {v.get('surah_name', 'MISSING')}")
                    print(f"    • Verse number: {v.get('verse_number')}")
                    print(f"    • Has arabic: {bool(v.get('arabic_text'))}")
                    print(f"    • Has english: {bool(v.get('text_saheeh_international'))}")

                # Check tafsir
                if tafsir:
                    print(f"\n  📚 TAFSIR SOURCES:")
                    for t in tafsir:
                        source = t.get("source", "Unknown")
                        explanation = t.get("explanation", "")
                        print(f"    • {source}: {len(explanation)} chars")
                        if len(explanation) > 0:
                            print(f"      Preview: {explanation[:100]}...")

                result = {
                    "status": "SUCCESS",
                    "route": route,
                    "duration": duration,
                    "verses_count": len(verses),
                    "tafsir_count": len(tafsir),
                    "sources": sources
                }
        else:
            print(f"  ⚠️  UNEXPECTED RESPONSE TYPE: {type(response_data)}")
            result = {
                "status": "UNEXPECTED_TYPE",
                "duration": duration
            }

        # Final verdict
        print(f"\n{'='*50}")
        print(f"VERDICT: {result['status']}")
        print(f"Duration: {duration:.2f}s")
        print(f"{'='*50}")

        return result

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ EXCEPTION: {type(e).__name__}: {str(e)}")
        return {
            "status": "EXCEPTION",
            "error": str(e),
            "duration": duration
        }

def main():
    """Run all tests and generate comprehensive report"""
    print("\n" + "#"*100)
    print("# COMPREHENSIVE ROUTES 1 & 2 TEST SUITE")
    print("# Using /debug/test endpoint for full execution traces")
    print("#"*100)

    results = []

    for test_case in TEST_QUERIES:
        result = run_test(test_case)
        result["test_name"] = test_case["name"]
        result["query"] = test_case["query"]
        result["expected_route"] = test_case["expected_route"]
        results.append(result)

        # Brief pause between tests
        time.sleep(1)

    # Generate summary report
    print("\n\n" + "#"*100)
    print("# SUMMARY REPORT")
    print("#"*100)

    # Count by status
    status_counts = {}
    for r in results:
        status = r["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    total = len(results)
    print(f"\nTOTAL TESTS: {total}")
    for status, count in sorted(status_counts.items()):
        pct = count / total * 100
        print(f"  {status}: {count} ({pct:.1f}%)")

    # Detailed issues
    print(f"\n{'='*100}")
    print("ISSUES FOUND:")
    issues = [r for r in results if r["status"] != "SUCCESS"]

    if not issues:
        print("  ✅ None! All tests passed!")
    else:
        for issue in issues:
            print(f"\n  ❌ {issue['test_name']}")
            print(f"     Query: {issue['query']}")
            print(f"     Status: {issue['status']}")
            if "route" in issue:
                print(f"     Route: {issue['route']}")
            if "error" in issue:
                print(f"     Error: {issue['error']}")

    # Save detailed results
    output_file = f"route_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📄 Detailed results saved to: {output_file}")

if __name__ == "__main__":
    main()
