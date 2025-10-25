#!/usr/bin/env python3
"""
Test script for sliding window reranker implementation.
Tests various chunk sizes to verify proper handling of the 1024 token limit.
"""

import requests
import json
import time
from typing import Dict, List

# Configuration
BASE_URL = "http://localhost:8080"
HEALTH_ENDPOINT = f"{BASE_URL}/health"
STATS_ENDPOINT = f"{BASE_URL}/reranker-stats"
QUERY_ENDPOINT = f"{BASE_URL}/query"

def check_health() -> Dict:
    """Check if the service is healthy and reranker is enabled."""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        return response.json()
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return None

def get_reranker_stats() -> Dict:
    """Get detailed reranker statistics."""
    try:
        response = requests.get(STATS_ENDPOINT, timeout=5)
        return response.json()
    except Exception as e:
        print(f"❌ Failed to get reranker stats: {e}")
        return None

def test_query(query: str, approach: str = "tafsir") -> Dict:
    """Test a query and return the response."""
    try:
        payload = {
            "query": query,
            "approach": approach,
            "language": "english",
            "persona": "standard"
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        print(f"\n📝 Testing query: '{query}' (approach: {approach})")
        start_time = time.time()

        response = requests.post(
            QUERY_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=30
        )

        elapsed = time.time() - start_time
        print(f"⏱️  Response time: {elapsed:.2f}s")

        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Query failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Query failed: {e}")
        return None

def analyze_sliding_window_usage(initial_stats: Dict, final_stats: Dict):
    """Analyze sliding window usage between two stat snapshots."""
    if not initial_stats or not final_stats:
        print("❌ Cannot analyze - missing statistics")
        return

    print("\n" + "="*70)
    print("📊 SLIDING WINDOW ANALYSIS")
    print("="*70)

    # Get sliding window data
    initial_sw = initial_stats.get('sliding_window', {})
    final_sw = final_stats.get('sliding_window', {})

    # Calculate differences
    chunks_using_windows = final_sw.get('chunks_using_windows', 0) - initial_sw.get('chunks_using_windows', 0)
    windows_processed = final_sw.get('total_windows_processed', 0) - initial_sw.get('total_windows_processed', 0)

    print(f"\n✅ Sliding Window Enabled: {final_sw.get('enabled', False)}")
    print(f"✅ Tokenizer Loaded: {final_sw.get('tokenizer_loaded', False)}")

    print(f"\n📈 During Test:")
    print(f"   • Chunks using sliding windows: {chunks_using_windows}")
    print(f"   • Total windows processed: {windows_processed}")

    if chunks_using_windows > 0:
        avg_windows = windows_processed / chunks_using_windows
        print(f"   • Average windows per chunk: {avg_windows:.1f}")

    print(f"\n📊 Overall Statistics:")
    print(f"   • Total chunks with windows: {final_sw.get('chunks_using_windows', 0)}")
    print(f"   • Total windows processed: {final_sw.get('total_windows_processed', 0)}")
    print(f"   • Average windows per chunk: {final_sw.get('avg_windows_per_chunk', 0):.2f}")
    print(f"   • Window usage rate: {final_sw.get('window_usage_rate', '0%')}")

    # Model configuration
    model_info = final_stats.get('model', {})
    print(f"\n⚙️  Model Configuration:")
    print(f"   • Model: {model_info.get('name', 'Unknown')}")
    print(f"   • Max length: {model_info.get('max_length', 'N/A')} tokens (query + document)")
    print(f"   • Query reserved tokens: {model_info.get('query_reserved_tokens', 'N/A')}")
    print(f"   • Max document tokens: {model_info.get('max_document_tokens', 'N/A')}")
    print(f"   • Window overlap: {model_info.get('window_overlap', 'N/A')} tokens")

def main():
    """Main test function."""
    print("\n" + "="*70)
    print("🔬 TESTING SLIDING WINDOW RERANKER IMPLEMENTATION")
    print("="*70)

    # Check health
    print("\n1️⃣  Checking service health...")
    health = check_health()
    if not health:
        print("❌ Service is not healthy. Make sure the backend is running.")
        return

    print(f"✅ Service is healthy")
    print(f"   • Chunks loaded: {health.get('chunks_loaded', 0)}")
    print(f"   • Reranker enabled: {health.get('reranker', {}).get('enabled', False)}")
    print(f"   • Reranker model: {health.get('reranker', {}).get('model', 'None')}")

    # Get initial stats
    print("\n2️⃣  Getting initial reranker statistics...")
    initial_stats = get_reranker_stats()
    if initial_stats:
        print(f"✅ Initial stats retrieved")
        print(f"   • Total calls: {initial_stats.get('performance', {}).get('total_calls', 0)}")
        print(f"   • Sliding windows used: {initial_stats.get('sliding_window', {}).get('chunks_using_windows', 0)}")

    # Test queries that should trigger sliding windows
    print("\n3️⃣  Testing queries to trigger sliding window behavior...")

    test_queries = [
        # Short query - should not trigger sliding windows for most chunks
        ("What does the Quran say about patience?", "semantic"),

        # Specific verse query - likely to get long tafsir chunks
        ("Explain verse 2:255 in detail", "tafsir"),

        # Broad topic - should retrieve many chunks, some potentially long
        ("Discuss the concept of charity and zakat in Islam", "semantic"),

        # Direct verse reference - will get full tafsir which can be very long
        ("2:183", "tafsir"),
    ]

    for query, approach in test_queries:
        result = test_query(query, approach)

        if result and 'debug' in result:
            debug_info = result.get('debug', {})
            chunks_info = debug_info.get('chunks_retrieved', [])

            # Check for sliding window usage in chunks
            windows_used = False
            for chunk_info in chunks_info:
                if isinstance(chunk_info, dict):
                    window_count = chunk_info.get('window_count', 1)
                    if window_count > 1:
                        windows_used = True
                        print(f"   📊 Chunk used {window_count} windows")

            if not windows_used:
                print(f"   ℹ️  No sliding windows needed for this query")

        time.sleep(1)  # Small delay between queries

    # Get final stats
    print("\n4️⃣  Getting final reranker statistics...")
    final_stats = get_reranker_stats()
    if final_stats:
        print(f"✅ Final stats retrieved")

    # Analyze sliding window usage
    analyze_sliding_window_usage(initial_stats, final_stats)

    print("\n" + "="*70)
    print("✅ TESTING COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()