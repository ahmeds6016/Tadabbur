#!/usr/bin/env python3
"""
Upload tafsir source JSON files to GCS bucket.

Usage:
    python backend/scripts/upload_tafsir_to_gcs.py [--dry-run] [--file FILENAME]

Examples:
    # Upload all files
    python backend/scripts/upload_tafsir_to_gcs.py

    # Upload just the Fatiha file
    python backend/scripts/upload_tafsir_to_gcs.py --file al-Qurtubi_Fatiha.json

    # Dry run (show what would be uploaded)
    python backend/scripts/upload_tafsir_to_gcs.py --dry-run
"""

import json
import os
import sys

# File mapping: local filename → GCS path (must match source_files in app.py)
FILE_MAPPING = {
    "ibnkathir-Fatiha-Tawbah_fixed.json": "processed/ibnkathir-Fatiha-Tawbah_fixed.json",
    "ibnkathir-Yunus-Ankabut_FINAL_fixed.json": "processed/ibnkathir-Yunus-Ankabut_FINAL_fixed.json",
    "ibnkathir-Rum-Nas_FINAL_fixed.json": "processed/ibnkathir-Rum-Nas_FINAL_fixed.json",
    "al-Qurtubi_Fatiha.json": "processed/al-Qurtubi_Fatiha.json",
    "al-Qurtubi_Vol._1_FINAL_fixed.json": "processed/al-Qurtubi Vol. 1_FINAL_fixed.json",
    "al-Qurtubi_Vol._2_FINAL_fixed.json": "processed/al-Qurtubi Vol. 2_FINAL_fixed.json",
    "al-Qurtubi_Vol._3_fixed.json": "processed/al-Qurtubi Vol. 3_fixed.json",
    "al-Qurtubi_Vol._4_FINAL_fixed.json": "processed/al-Qurtubi Vol. 4_FINAL_fixed.json",
}

BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "tafsir-simplified-sources")


def main():
    dry_run = '--dry-run' in sys.argv

    # Optional: upload specific file only
    specific_file = None
    if '--file' in sys.argv:
        idx = sys.argv.index('--file')
        if idx + 1 < len(sys.argv):
            specific_file = sys.argv[idx + 1]

    source_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'tafsir_sources')
    source_dir = os.path.abspath(source_dir)

    # Filter files if specific file requested
    files_to_upload = FILE_MAPPING
    if specific_file:
        if specific_file in FILE_MAPPING:
            files_to_upload = {specific_file: FILE_MAPPING[specific_file]}
        else:
            print(f"ERROR: Unknown file '{specific_file}'")
            print(f"Available files: {', '.join(FILE_MAPPING.keys())}")
            sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Upload Tafsir Sources to GCS")
    print(f"{'='*60}")
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Files: {len(files_to_upload)}")
    print(f"{'='*60}\n")

    if not dry_run:
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(BUCKET_NAME)
        except Exception as e:
            print(f"ERROR: Cannot connect to GCS: {e}")
            print("Make sure GOOGLE_APPLICATION_CREDENTIALS is set or you're authenticated.")
            sys.exit(1)

    uploaded = 0
    skipped = 0

    for local_name, gcs_path in files_to_upload.items():
        local_path = os.path.join(source_dir, local_name)

        if not os.path.exists(local_path):
            print(f"  SKIP: {local_name} (file not found)")
            skipped += 1
            continue

        file_size = os.path.getsize(local_path)
        size_mb = file_size / (1024 * 1024)

        # Validate JSON
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            verse_count = len(data.get('verses', []))
        except json.JSONDecodeError as e:
            print(f"  ERROR: {local_name} has invalid JSON: {e}")
            skipped += 1
            continue

        if dry_run:
            print(f"  Would upload: {local_name}")
            print(f"    → gs://{BUCKET_NAME}/{gcs_path}")
            print(f"    Size: {size_mb:.2f} MB, Verses: {verse_count}")
        else:
            print(f"  Uploading: {local_name} → {gcs_path}")
            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(local_path, content_type='application/json')
            print(f"    ✅ Uploaded ({size_mb:.2f} MB, {verse_count} verses)")

        uploaded += 1

    print(f"\n{'='*60}")
    print(f"Done: {uploaded} uploaded, {skipped} skipped")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
