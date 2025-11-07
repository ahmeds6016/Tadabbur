#!/usr/bin/env python3
"""
Check tafsir coverage for specific verses in GCS sources
"""
import os
import json
from google.cloud import storage

GCS_BUCKET_NAME = "tafsir-simplified-sources"

def check_verse_coverage(surah: int, start_verse: int, end_verse: int):
    """Check which verses have tafsir coverage in GCS sources"""

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)

    sources = ["ibn-kathir", "al-qurtubi"]

    for source in sources:
        print(f"\n{'='*70}")
        print(f"Source: {source}")
        print(f"{'='*70}")

        blob_path = f"sliding_window/{source}.json"
        blob = bucket.blob(blob_path)

        if not blob.exists():
            print(f"❌ {blob_path} not found")
            continue

        # Download and parse
        content = blob.download_as_text()
        data = json.loads(content)

        print(f"Total chunks in {source}: {len(data)}")

        # Check coverage for requested verses
        covered_verses = set()
        verse_chunks = []

        for chunk in data:
            chunk_surah = chunk.get('surah')
            verse_numbers = chunk.get('verse_numbers', [])

            if chunk_surah == surah:
                for v in verse_numbers:
                    if start_verse <= v <= end_verse:
                        covered_verses.add(v)
                        verse_chunks.append({
                            'verse': v,
                            'verse_numbers': verse_numbers,
                            'chunk_id': chunk.get('chunk_id'),
                            'has_topics': bool(chunk.get('topics')),
                            'has_commentary': bool(chunk.get('commentary')),
                            'topics_count': len(chunk.get('topics', []))
                        })

        print(f"\nCoverage for Surah {surah}, verses {start_verse}-{end_verse}:")
        print(f"  Covered verses: {sorted(covered_verses)}")
        print(f"  Missing verses: {sorted(set(range(start_verse, end_verse + 1)) - covered_verses)}")

        if verse_chunks:
            print(f"\n  Chunks found:")
            for info in verse_chunks:
                print(f"    {info['chunk_id']}: verse {info['verse']}, range={info['verse_numbers']}, "
                      f"topics={info['topics_count']}, has_commentary={info['has_commentary']}")


if __name__ == "__main__":
    # Check As-Sajdah 1-9
    print("Checking Surah As-Sajdah (32), verses 1-9")
    check_verse_coverage(32, 1, 9)

    print("\n\n")

    # Check Al-Kahf 1-10
    print("Checking Surah Al-Kahf (18), verses 1-10")
    check_verse_coverage(18, 1, 10)
