#!/usr/bin/env python3
"""
Performance Testing Script for Tafsir Simplified Backend
Tests and compares performance metrics between old and optimized versions
"""

import time
import json
import statistics
import asyncio
import aiohttp
from typing import Dict, List, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from tabulate import tabulate

# Configuration
BASE_URL = "http://localhost:8080"
AUTH_TOKEN = "YOUR_FIREBASE_AUTH_TOKEN"  # Replace with actual token

# Test scenarios
TEST_QUERIES = [
    # Verse-specific queries
    {
        "query": "What does verse 2:255 mean?",
        "approach": "tafsir",
        "user_profile": {"persona": "practicing_muslim"}
    },
    {
        "query": "Explain verses 39:53-54 about Allah's mercy",
        "approach": "tafsir",
        "user_profile": {"persona": "new_revert"}
    },
    {
        "query": "Tell me about Surah Al-Fatihah (1:1-7)",
        "approach": "tafsir",
        "user_profile": {"persona": "student"}
    },
    # Thematic queries
    {
        "query": "What does the Quran say about patience and perseverance?",
        "approach": "explore",
        "user_profile": {"persona": "practicing_muslim"}
    },
    {
        "query": "How does Islam view forgiveness?",
        "approach": "explore",
        "user_profile": {"persona": "new_revert"}
    }
]

class PerformanceTestResults:
    """Store and analyze performance test results"""

    def __init__(self):
        self.response_times = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.errors = []
        self.successful_requests = 0
        self.total_requests = 0

    def add_result(self, response_time: float, cache_hit: bool, error: str = None):
        """Add a test result"""
        self.total_requests += 1

        if error:
            self.errors.append(error)
        else:
            self.successful_requests += 1
            self.response_times.append(response_time)

            if cache_hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1

    def get_statistics(self) -> Dict:
        """Calculate statistics from results"""
        if not self.response_times:
            return {"error": "No successful requests"}

        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": len(self.errors),
            "avg_response_time": statistics.mean(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times),
            "p95_response_time": statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) > 20 else max(self.response_times),
            "cache_hit_rate": (self.cache_hits / self.successful_requests * 100) if self.successful_requests > 0 else 0,
            "error_rate": (len(self.errors) / self.total_requests * 100) if self.total_requests > 0 else 0
        }

def make_tafsir_request(query_data: Dict, headers: Dict) -> Tuple[float, bool, str]:
    """
    Make a single tafsir request and measure performance

    Returns:
        Tuple of (response_time, cache_hit, error_message)
    """
    try:
        start_time = time.time()

        response = requests.post(
            f"{BASE_URL}/tafsir",
            json=query_data,
            headers=headers,
            timeout=60
        )

        response_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            # Check if response indicates cache hit (would need backend to include this)
            cache_hit = response_time < 1.0  # Assume cache hit if < 1 second
            return response_time, cache_hit, None
        else:
            return response_time, False, f"HTTP {response.status_code}: {response.text}"

    except requests.exceptions.Timeout:
        return 60.0, False, "Request timeout"
    except Exception as e:
        return 0, False, str(e)

def test_sequential_performance() -> PerformanceTestResults:
    """Test performance with sequential requests"""
    print("\n🔄 Testing Sequential Performance...")

    results = PerformanceTestResults()
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

    for i, query in enumerate(TEST_QUERIES):
        print(f"  Request {i+1}/{len(TEST_QUERIES)}: {query['query'][:50]}...")

        response_time, cache_hit, error = make_tafsir_request(query, headers)
        results.add_result(response_time, cache_hit, error)

        if error:
            print(f"    ❌ Error: {error}")
        else:
            print(f"    ✅ Response time: {response_time:.2f}s (Cache: {'HIT' if cache_hit else 'MISS'})")

    return results

def test_concurrent_performance(num_concurrent: int = 10) -> PerformanceTestResults:
    """Test performance with concurrent requests"""
    print(f"\n⚡ Testing Concurrent Performance ({num_concurrent} concurrent requests)...")

    results = PerformanceTestResults()
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        # Submit all requests
        futures = []
        for i in range(num_concurrent):
            query = TEST_QUERIES[i % len(TEST_QUERIES)]
            future = executor.submit(make_tafsir_request, query, headers)
            futures.append(future)

        # Collect results
        for i, future in enumerate(as_completed(futures)):
            response_time, cache_hit, error = future.result()
            results.add_result(response_time, cache_hit, error)

            if error:
                print(f"  Request {i+1}: ❌ {error}")
            else:
                print(f"  Request {i+1}: ✅ {response_time:.2f}s")

    return results

def test_cache_effectiveness() -> Dict:
    """Test cache effectiveness by making repeated requests"""
    print("\n💾 Testing Cache Effectiveness...")

    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    query = TEST_QUERIES[0]  # Use first query for testing

    # First request (cache miss expected)
    print("  First request (expecting cache miss)...")
    time1, hit1, err1 = make_tafsir_request(query, headers)

    # Wait a moment
    time.sleep(1)

    # Second request (cache hit expected)
    print("  Second request (expecting cache hit)...")
    time2, hit2, err2 = make_tafsir_request(query, headers)

    # Third request (should also be cache hit)
    print("  Third request (expecting cache hit)...")
    time3, hit3, err3 = make_tafsir_request(query, headers)

    improvement = ((time1 - time2) / time1 * 100) if time1 > 0 else 0

    return {
        "first_request_time": time1,
        "second_request_time": time2,
        "third_request_time": time3,
        "cache_improvement": improvement,
        "cache_working": time2 < time1 * 0.5  # Cache hit should be 50% faster
    }

def test_rate_limiting() -> Dict:
    """Test rate limiting functionality"""
    print("\n🚦 Testing Rate Limiting...")

    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    query = TEST_QUERIES[0]

    # Make rapid requests to trigger rate limit
    results = []
    for i in range(25):  # Try to exceed minute limit (20 for free tier)
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/tafsir",
            json=query,
            headers=headers,
            timeout=5
        )
        elapsed = time.time() - start

        results.append({
            "request_num": i + 1,
            "status_code": response.status_code,
            "response_time": elapsed
        })

        if response.status_code == 429:
            print(f"  ✅ Rate limit triggered at request {i+1}")
            return {
                "rate_limit_working": True,
                "triggered_at_request": i + 1,
                "expected_limit": 20
            }

        print(f"  Request {i+1}: {response.status_code}")

    return {
        "rate_limit_working": False,
        "message": "Rate limit not triggered after 25 requests"
    }

def compare_with_baseline(new_stats: Dict, baseline_stats: Dict) -> Dict:
    """Compare new performance with baseline"""
    improvements = {}

    metrics = [
        ("avg_response_time", "lower"),
        ("median_response_time", "lower"),
        ("cache_hit_rate", "higher"),
        ("error_rate", "lower")
    ]

    for metric, better_direction in metrics:
        if metric in new_stats and metric in baseline_stats:
            old_val = baseline_stats[metric]
            new_val = new_stats[metric]

            if old_val > 0:
                change_pct = ((new_val - old_val) / old_val) * 100

                if better_direction == "lower":
                    improvement = -change_pct
                else:
                    improvement = change_pct

                improvements[metric] = {
                    "old": old_val,
                    "new": new_val,
                    "improvement_pct": improvement,
                    "improved": improvement > 0
                }

    return improvements

def display_results(results: Dict):
    """Display results in a formatted table"""
    print("\n" + "="*60)
    print("📊 PERFORMANCE TEST RESULTS")
    print("="*60)

    # Sequential results
    if "sequential" in results:
        print("\n🔄 Sequential Performance:")
        seq_stats = results["sequential"]
        table_data = [
            ["Metric", "Value"],
            ["Average Response Time", f"{seq_stats.get('avg_response_time', 0):.2f}s"],
            ["Median Response Time", f"{seq_stats.get('median_response_time', 0):.2f}s"],
            ["Min Response Time", f"{seq_stats.get('min_response_time', 0):.2f}s"],
            ["Max Response Time", f"{seq_stats.get('max_response_time', 0):.2f}s"],
            ["P95 Response Time", f"{seq_stats.get('p95_response_time', 0):.2f}s"],
            ["Cache Hit Rate", f"{seq_stats.get('cache_hit_rate', 0):.1f}%"],
            ["Error Rate", f"{seq_stats.get('error_rate', 0):.1f}%"]
        ]
        print(tabulate(table_data, headers="firstrow", tablefmt="grid"))

    # Concurrent results
    if "concurrent" in results:
        print("\n⚡ Concurrent Performance:")
        conc_stats = results["concurrent"]
        table_data = [
            ["Metric", "Value"],
            ["Average Response Time", f"{conc_stats.get('avg_response_time', 0):.2f}s"],
            ["Successful Requests", f"{conc_stats.get('successful_requests', 0)}/{conc_stats.get('total_requests', 0)}"],
            ["Cache Hit Rate", f"{conc_stats.get('cache_hit_rate', 0):.1f}%"]
        ]
        print(tabulate(table_data, headers="firstrow", tablefmt="grid"))

    # Cache effectiveness
    if "cache" in results:
        print("\n💾 Cache Effectiveness:")
        cache_results = results["cache"]
        table_data = [
            ["Request", "Response Time"],
            ["First (Cold)", f"{cache_results.get('first_request_time', 0):.2f}s"],
            ["Second (Warm)", f"{cache_results.get('second_request_time', 0):.2f}s"],
            ["Third (Warm)", f"{cache_results.get('third_request_time', 0):.2f}s"],
            ["Cache Improvement", f"{cache_results.get('cache_improvement', 0):.1f}%"]
        ]
        print(tabulate(table_data, headers="firstrow", tablefmt="grid"))

        if cache_results.get('cache_working'):
            print("  ✅ Cache is working effectively")
        else:
            print("  ⚠️  Cache may not be working optimally")

    # Rate limiting
    if "rate_limit" in results:
        print("\n🚦 Rate Limiting:")
        rl_results = results["rate_limit"]
        if rl_results.get('rate_limit_working'):
            print(f"  ✅ Rate limiting is working (triggered at request {rl_results.get('triggered_at_request')})")
        else:
            print(f"  ⚠️  {rl_results.get('message')}")

def main():
    """Run all performance tests"""
    print("""
╔════════════════════════════════════════════════════════════╗
║     Tafsir Simplified Performance Testing Suite           ║
║     Testing Optimized Backend Performance                 ║
╚════════════════════════════════════════════════════════════╝
    """)

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not healthy. Please start the server first.")
            return 1
    except:
        print("❌ Cannot connect to server. Please ensure the server is running on port 8080.")
        return 1

    all_results = {}

    # Run tests
    try:
        # 1. Sequential performance
        all_results["sequential"] = test_sequential_performance().get_statistics()

        # 2. Concurrent performance
        all_results["concurrent"] = test_concurrent_performance(10).get_statistics()

        # 3. Cache effectiveness
        all_results["cache"] = test_cache_effectiveness()

        # 4. Rate limiting
        all_results["rate_limit"] = test_rate_limiting()

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1

    # Display results
    display_results(all_results)

    # Performance summary
    print("\n" + "="*60)
    print("🎯 PERFORMANCE SUMMARY")
    print("="*60)

    avg_time = all_results["sequential"].get("avg_response_time", 0)
    cache_rate = all_results["sequential"].get("cache_hit_rate", 0)

    if avg_time < 5:
        print("✅ Excellent: Average response time under 5 seconds")
    elif avg_time < 10:
        print("⚠️  Good: Average response time under 10 seconds")
    else:
        print("❌ Needs improvement: Average response time over 10 seconds")

    if cache_rate > 80:
        print(f"✅ Excellent: Cache hit rate {cache_rate:.1f}%")
    elif cache_rate > 50:
        print(f"⚠️  Good: Cache hit rate {cache_rate:.1f}%")
    else:
        print(f"❌ Needs improvement: Cache hit rate {cache_rate:.1f}%")

    # Expected vs actual
    print("\n📈 Expected vs Actual Improvements:")
    print("  Expected: 70% latency reduction (48s → 3-5s)")
    print(f"  Actual: Average response time {avg_time:.2f}s")

    if avg_time <= 5:
        reduction = ((48 - avg_time) / 48) * 100
        print(f"  ✅ Achieved {reduction:.1f}% latency reduction!")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())