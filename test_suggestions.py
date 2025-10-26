#!/usr/bin/env python3
"""Test the suggestions endpoint to diagnose issues."""

import requests
import json

# Test local endpoint
def test_suggestions():
    """Test the suggestions endpoint."""

    # First test if backend is accessible
    backend_url = "https://tafsir-backend-612616741510.us-central1.run.app"

    try:
        print("Testing suggestions endpoint...")
        response = requests.get(f"{backend_url}/suggestions", timeout=10)

        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Success! Got {len(data.get('suggestions', []))} suggestions")
            print(f"Total bank size: {data.get('total_bank_size', 'N/A')}")

            # Show sample suggestions
            print("\nSample suggestions:")
            for i, suggestion in enumerate(data.get('suggestions', [])[:5]):
                print(f"  {i+1}. Query: {suggestion.get('query', 'N/A')}")
                print(f"     Approach: {suggestion.get('approach', 'N/A')}")

            # Check approach distribution
            approaches = {}
            for suggestion in data.get('suggestions', []):
                approach = suggestion.get('approach', 'unknown')
                approaches[approach] = approaches.get(approach, 0) + 1

            print(f"\nApproach distribution:")
            for approach, count in approaches.items():
                print(f"  {approach}: {count}")

        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")

    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_suggestions()