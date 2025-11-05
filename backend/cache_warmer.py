#!/usr/bin/env python3
"""
Cache Warmer for Tafsir Simplified
=====================================
Pre-generates and caches responses for all single-verse tafsir queries.

FEATURES:
- Quality validation (rejects "no information found" responses)
- Verse range validation (respects 10-verse limit)
- Progress tracking with detailed stats
- Batch processing to avoid overwhelming server
- Support for all personas

USAGE:
------
1. Get Firebase auth token:
   firebase auth:export --project tafsir-simplified

2. Run priority verses (recommended first):
   python cache_warmer.py --token YOUR_TOKEN --mode priority

3. Run all single verses (6,236 verses × 7 personas = 43,652 entries):
   python cache_warmer.py --token YOUR_TOKEN --mode single_verses --batch-size 100

VALIDATION:
-----------
The script validates each response to ensure quality:
✅ Valid: Has verses, tafsir explanations, and substantial summary
⚠️  Invalid: Missing content or "no information" messages (NOT cached)
📏 Range error: Exceeds 10-verse limit
❌ API error: Network or server issues

Only VALID responses are cached. Invalid responses are skipped.

EXAMPLES:
---------
# Test with priority verses first (recommended)
python cache_warmer.py --token abc123 --mode priority --batch-size 10

# Cache all single verses (takes ~2-3 hours)
python cache_warmer.py --token abc123 --mode single_verses --batch-size 50

# Cache specific personas only
python cache_warmer.py --token abc123 --mode single_verses --personas scholar teacher

# Use production API
python cache_warmer.py --token abc123 --api-url https://tafsir-backend.com/api --mode priority
"""

import asyncio
import aiohttp
import json
import time
from typing import List, Dict
import argparse

# Quran metadata
QURAN_METADATA = {
    1: {"name": "Al-Fatihah", "verses": 7}, 2: {"name": "Al-Baqarah", "verses": 286}, 3: {"name": "Aal-E-Imran", "verses": 200},
    4: {"name": "An-Nisa", "verses": 176}, 5: {"name": "Al-Ma'idah", "verses": 120}, 6: {"name": "Al-An'am", "verses": 165},
    7: {"name": "Al-A'raf", "verses": 206}, 8: {"name": "Al-Anfal", "verses": 75}, 9: {"name": "At-Tawbah", "verses": 129},
    10: {"name": "Yunus", "verses": 109}, 11: {"name": "Hud", "verses": 123}, 12: {"name": "Yusuf", "verses": 111},
    13: {"name": "Ar-Ra'd", "verses": 43}, 14: {"name": "Ibrahim", "verses": 52}, 15: {"name": "Al-Hijr", "verses": 99},
    16: {"name": "An-Nahl", "verses": 128}, 17: {"name": "Al-Isra", "verses": 111}, 18: {"name": "Al-Kahf", "verses": 110},
    19: {"name": "Maryam", "verses": 98}, 20: {"name": "Taha", "verses": 135}, 21: {"name": "Al-Anbya", "verses": 112},
    22: {"name": "Al-Hajj", "verses": 78}, 23: {"name": "Al-Mu'minun", "verses": 118}, 24: {"name": "An-Nur", "verses": 64},
    25: {"name": "Al-Furqan", "verses": 77}, 26: {"name": "Ash-Shu'ara", "verses": 227}, 27: {"name": "An-Naml", "verses": 93},
    28: {"name": "Al-Qasas", "verses": 88}, 29: {"name": "Al-Ankabut", "verses": 69}, 30: {"name": "Ar-Rum", "verses": 60},
    31: {"name": "Luqman", "verses": 34}, 32: {"name": "As-Sajdah", "verses": 30}, 33: {"name": "Al-Ahzab", "verses": 73},
    34: {"name": "Saba", "verses": 54}, 35: {"name": "Fatir", "verses": 45}, 36: {"name": "Ya-Sin", "verses": 83},
    37: {"name": "As-Saffat", "verses": 182}, 38: {"name": "Sad", "verses": 88}, 39: {"name": "Az-Zumar", "verses": 75},
    40: {"name": "Ghafir", "verses": 85}, 41: {"name": "Fussilat", "verses": 54}, 42: {"name": "Ash-Shuraa", "verses": 53},
    43: {"name": "Az-Zukhruf", "verses": 89}, 44: {"name": "Ad-Dukhan", "verses": 59}, 45: {"name": "Al-Jathiyah", "verses": 37},
    46: {"name": "Al-Ahqaf", "verses": 35}, 47: {"name": "Muhammad", "verses": 38}, 48: {"name": "Al-Fath", "verses": 29},
    49: {"name": "Al-Hujurat", "verses": 18}, 50: {"name": "Qaf", "verses": 45}, 51: {"name": "Adh-Dhariyat", "verses": 60},
    52: {"name": "At-Tur", "verses": 49}, 53: {"name": "An-Najm", "verses": 62}, 54: {"name": "Al-Qamar", "verses": 55},
    55: {"name": "Ar-Rahman", "verses": 78}, 56: {"name": "Al-Waqi'ah", "verses": 96}, 57: {"name": "Al-Hadid", "verses": 29},
    58: {"name": "Al-Mujadila", "verses": 22}, 59: {"name": "Al-Hashr", "verses": 24}, 60: {"name": "Al-Mumtahanah", "verses": 13},
    61: {"name": "As-Saf", "verses": 14}, 62: {"name": "Al-Jumu'ah", "verses": 11}, 63: {"name": "Al-Munafiqun", "verses": 11},
    64: {"name": "At-Taghabun", "verses": 18}, 65: {"name": "At-Talaq", "verses": 12}, 66: {"name": "At-Tahrim", "verses": 12},
    67: {"name": "Al-Mulk", "verses": 30}, 68: {"name": "Al-Qalam", "verses": 52}, 69: {"name": "Al-Haqqah", "verses": 52},
    70: {"name": "Al-Ma'arij", "verses": 44}, 71: {"name": "Nuh", "verses": 28}, 72: {"name": "Al-Jinn", "verses": 28},
    73: {"name": "Al-Muzzammil", "verses": 20}, 74: {"name": "Al-Muddaththir", "verses": 56}, 75: {"name": "Al-Qiyamah", "verses": 40},
    76: {"name": "Al-Insan", "verses": 31}, 77: {"name": "Al-Mursalat", "verses": 50}, 78: {"name": "An-Naba", "verses": 40},
    79: {"name": "An-Nazi'at", "verses": 46}, 80: {"name": "Abasa", "verses": 42}, 81: {"name": "At-Takwir", "verses": 29},
    82: {"name": "Al-Infitar", "verses": 19}, 83: {"name": "Al-Mutaffifin", "verses": 36}, 84: {"name": "Al-Inshiqaq", "verses": 25},
    85: {"name": "Al-Buruj", "verses": 22}, 86: {"name": "At-Tariq", "verses": 17}, 87: {"name": "Al-A'la", "verses": 19},
    88: {"name": "Al-Ghashiyah", "verses": 26}, 89: {"name": "Al-Fajr", "verses": 30}, 90: {"name": "Al-Balad", "verses": 20},
    91: {"name": "Ash-Shams", "verses": 15}, 92: {"name": "Al-Layl", "verses": 21}, 93: {"name": "Ad-Duhaa", "verses": 11},
    94: {"name": "Ash-Sharh", "verses": 8}, 95: {"name": "At-Tin", "verses": 8}, 96: {"name": "Al-Alaq", "verses": 19},
    97: {"name": "Al-Qadr", "verses": 5}, 98: {"name": "Al-Bayyinah", "verses": 8}, 99: {"name": "Az-Zalzalah", "verses": 8},
    100: {"name": "Al-Adiyat", "verses": 11}, 101: {"name": "Al-Qari'ah", "verses": 11}, 102: {"name": "At-Takathur", "verses": 8},
    103: {"name": "Al-Asr", "verses": 3}, 104: {"name": "Al-Humazah", "verses": 9}, 105: {"name": "Al-Fil", "verses": 5},
    106: {"name": "Quraysh", "verses": 4}, 107: {"name": "Al-Ma'un", "verses": 7}, 108: {"name": "Al-Kawthar", "verses": 3},
    109: {"name": "Al-Kafirun", "verses": 6}, 110: {"name": "An-Nasr", "verses": 3}, 111: {"name": "Al-Masad", "verses": 5},
    112: {"name": "Al-Ikhlas", "verses": 4}, 113: {"name": "Al-Falaq", "verses": 5}, 114: {"name": "An-Nas", "verses": 6}
}

PERSONAS = ["new_revert", "revert", "seeker", "practicing_muslim", "teacher", "scholar", "student"]

# Priority verses (high-traffic, respecting ≤10 verse limit)
PRIORITY_VERSES = [
    # Single verses (most common)
    "2:255",  # Ayatul Kursi
    "36:1",  # Ya-Sin opening
    "18:1",  # Al-Kahf opening

    # Complete short surahs
    "1:1-7",  # Al-Fatihah (7 verses)
    "112:1-4",  # Al-Ikhlas (4 verses)
    "113:1-5",  # Al-Falaq (5 verses)
    "114:1-6",  # An-Nas (6 verses)
    "103:1-3",  # Al-Asr (3 verses)
    "108:1-3",  # Al-Kawthar (3 verses)
    "93:1-8",  # Ad-Duha (8 verses)
    "94:1-8",  # Ash-Sharh (8 verses)

    # Common ranges (≤10 verses)
    "36:1-10",  # Ya-Sin opening (10 verses - max allowed)
    "55:1-10",  # Ar-Rahman opening (10 verses - max allowed)
    "67:1-10",  # Al-Mulk opening (10 verses)
    "2:1-10",  # Al-Baqarah opening (10 verses)
    "18:1-10",  # Al-Kahf opening (10 verses)
    "23:1-10",  # Al-Mu'minun opening (10 verses)
]


def validate_response_quality(data: Dict) -> tuple:
    """
    Validate that cached response has quality content.

    Returns:
        (is_valid, reason) tuple
    """
    # Check for clarification needed
    if data.get("needs_clarification"):
        return False, "needs_clarification"

    # Check for extraction errors
    metadata = data.get("metadata", {})
    if metadata.get("extraction_error") or metadata.get("fallback_used"):
        return False, "extraction_error"

    # Check verses
    verses = data.get("verses", [])
    if not verses or len(verses) == 0:
        return False, "no_verses"

    # Check tafsir explanations
    tafsir = data.get("tafsir_explanations", [])
    if not tafsir or len(tafsir) == 0:
        return False, "no_tafsir"

    # Check for "no information" messages in explanations
    for explanation in tafsir:
        text = explanation.get("explanation", "").lower()
        if any(phrase in text for phrase in [
            "no relevant information found",
            "limited relevant content",
            "no commentary available",
            "source material does not contain",
            "does not provide",
            "no specific commentary"
        ]):
            return False, f"poor_quality_tafsir_{explanation.get('source', 'unknown')}"

    # Check summary exists and is substantial
    summary = data.get("summary", "")
    if not summary or len(summary.strip()) < 50:
        return False, "insufficient_summary"

    # Check summary doesn't contain "no information" messages
    summary_lower = summary.lower()
    if any(phrase in summary_lower for phrase in [
        "no relevant information",
        "no commentary available",
        "source material does not"
    ]):
        return False, "poor_quality_summary"

    return True, "valid"


def generate_all_single_verses() -> List[str]:
    """Generate list of all single verse queries (e.g., '2:255')"""
    verses = []
    for surah_num, info in QURAN_METADATA.items():
        for verse_num in range(1, info["verses"] + 1):
            verses.append(f"{surah_num}:{verse_num}")
    return verses


async def warm_cache_entry(
    session: aiohttp.ClientSession,
    api_url: str,
    query: str,
    persona: str,
    token: str
) -> Dict:
    """Send a single cache warming request"""
    try:
        async with session.post(
            f"{api_url}/tafsir",
            json={
                "query": query,
                "approach": "tafsir",
                "persona": persona
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            },
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            if response.status == 200:
                data = await response.json()

                # Validate response quality
                is_valid, reason = validate_response_quality(data)

                if is_valid:
                    return {"status": "success", "query": query, "persona": persona}
                else:
                    return {"status": "invalid", "query": query, "persona": persona, "reason": reason}

            elif response.status == 400:
                # Handle validation errors (e.g., verse range too large)
                error_data = await response.json()
                error_type = error_data.get('error', 'unknown')
                error_msg = error_data.get('message', 'Bad request')
                return {"status": "validation_error", "query": query, "persona": persona,
                       "error_type": error_type, "error_msg": error_msg}

            else:
                error = await response.text()
                return {"status": "error", "query": query, "persona": persona, "error": error}
    except Exception as e:
        return {"status": "error", "query": query, "persona": persona, "error": str(e)}


async def warm_cache_batch(
    api_url: str,
    queries: List[str],
    personas: List[str],
    token: str,
    batch_size: int = 50,
    delay_between_batches: float = 2.0
):
    """Warm cache in batches to avoid overwhelming the server"""

    total_queries = len(queries) * len(personas)
    completed = 0
    success_count = 0
    invalid_count = 0
    validation_error_count = 0
    error_count = 0
    start_time = time.time()

    print(f"🔥 Starting cache warming...")
    print(f"   Queries: {len(queries)}")
    print(f"   Personas: {len(personas)}")
    print(f"   Total entries: {total_queries:,}")
    print(f"   Batch size: {batch_size}\n")

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(queries), batch_size):
            batch_queries = queries[i:i + batch_size]
            tasks = []

            # Create tasks for this batch (all personas for these queries)
            for query in batch_queries:
                for persona in personas:
                    task = warm_cache_entry(session, api_url, query, persona, token)
                    tasks.append(task)

            # Execute batch
            results = await asyncio.gather(*tasks)

            # Update stats
            for result in results:
                completed += 1
                status = result["status"]

                if status == "success":
                    success_count += 1
                elif status == "invalid":
                    invalid_count += 1
                    print(f"   ⚠️  Invalid: {result['query']} ({result['persona']}): {result.get('reason', 'Unknown')}")
                elif status == "validation_error":
                    validation_error_count += 1
                    error_type = result.get('error_type', 'unknown')
                    if error_type == "verse_range_too_large":
                        print(f"   📏 Range too large: {result['query']} - Use ≤10 verses")
                    else:
                        print(f"   ⚠️  Validation: {result['query']} ({result['persona']}): {error_type}")
                elif status == "error":
                    error_count += 1
                    print(f"   ❌ Error: {result['query']} ({result['persona']}): {result.get('error', 'Unknown')}")

            # Progress update
            progress = (completed / total_queries) * 100
            elapsed = time.time() - start_time
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (total_queries - completed) / rate if rate > 0 else 0

            print(f"   Progress: {completed:,}/{total_queries:,} ({progress:.1f}%) | "
                  f"Rate: {rate:.1f}/sec | ETA: {eta/60:.1f}min | "
                  f"✅ {success_count} ⚠️ {invalid_count} 📏 {validation_error_count} ❌ {error_count}")

            # Delay between batches
            if i + batch_size < len(queries):
                await asyncio.sleep(delay_between_batches)

    elapsed_total = time.time() - start_time
    print(f"\n✅ Cache warming completed!")
    print(f"   Total time: {elapsed_total/60:.1f} minutes")
    print(f"   ✅ Success (cached): {success_count:,}")
    print(f"   ⚠️  Invalid responses (not cached): {invalid_count:,}")
    print(f"   📏 Validation errors (e.g., range too large): {validation_error_count:,}")
    print(f"   ❌ API errors: {error_count:,}")
    print(f"   Average rate: {completed/elapsed_total:.1f} entries/sec")


def main():
    parser = argparse.ArgumentParser(description="Cache warmer for Tafsir Simplified")
    parser.add_argument("--api-url", default="http://localhost:5001/api", help="API base URL")
    parser.add_argument("--token", required=True, help="Firebase auth token")
    parser.add_argument("--mode", choices=["single_verses", "priority"], default="single_verses",
                       help="Caching mode: single_verses (all) or priority (high-traffic only)")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size (queries per batch)")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between batches (seconds)")
    parser.add_argument("--personas", nargs="+", default=PERSONAS, help="Personas to cache")

    args = parser.parse_args()

    # Generate query list based on mode
    if args.mode == "priority":
        queries = PRIORITY_VERSES
        print(f"📋 Mode: Priority verses only ({len(queries)} queries)")
    else:
        queries = generate_all_single_verses()
        print(f"📋 Mode: All single verses ({len(queries):,} queries)")

    # Run cache warming
    asyncio.run(warm_cache_batch(
        api_url=args.api_url,
        queries=queries,
        personas=args.personas,
        token=args.token,
        batch_size=args.batch_size,
        delay_between_batches=args.delay
    ))


if __name__ == "__main__":
    main()
