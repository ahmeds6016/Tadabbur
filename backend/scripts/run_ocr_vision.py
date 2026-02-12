#!/usr/bin/env python3
"""
OCR scanned PDF images using Google Cloud Vision API.
Much faster than Tesseract (~0.5-2 sec/page vs ~25 sec/page).
"""

import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set ADC credentials
os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/home/codespace/.config/gcloud/application_default_credentials.json"
)

from google.cloud import vision

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "backend" / "data" / "sources" / "raw"
IMAGE_DIR = PROJECT_ROOT / "backend" / "data" / "sources" / "ocr_images"


def ocr_page(client, image_path):
    """OCR a single page using Cloud Vision document_text_detection."""
    with open(image_path, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)

    if response.error.message:
        return f"[VISION ERROR: {response.error.message}]"

    return response.full_text_annotation.text if response.full_text_annotation.text else ""


def process_source(source_name, image_dir, output_file):
    """Process all images for a source using Cloud Vision."""
    images = sorted(Path(image_dir).glob("page-*.png"))
    if not images:
        print(f"  No images found in {image_dir}")
        return False

    print(f"  {source_name}: {len(images)} pages to process", flush=True)
    start_time = time.time()

    client = vision.ImageAnnotatorClient()

    results = {}
    completed = 0
    errors = 0

    # Process pages in parallel (8 workers — API can handle high concurrency)
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_page = {}
        for img in images:
            page_num = int(img.stem.split('-')[1])
            future_to_page[executor.submit(ocr_page, client, img)] = (page_num, img)

        for future in as_completed(future_to_page):
            page_num, img = future_to_page[future]
            try:
                text = future.result()
                results[page_num] = text
            except Exception as e:
                results[page_num] = f"[ERROR on page {page_num}: {e}]"
                errors += 1

            completed += 1
            if completed % 25 == 0 or completed == len(images):
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (len(images) - completed) / rate if rate > 0 else 0
                print(f"    {completed}/{len(images)} pages ({rate:.1f} pages/sec, ETA {eta:.0f}s)", flush=True)

    # Assemble in page order
    all_text = []
    for page_num in sorted(results.keys()):
        all_text.append(results[page_num])

    full_text = '\n'.join(all_text)

    # Save
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(full_text)

    elapsed = time.time() - start_time
    print(f"  {source_name}: DONE in {elapsed:.1f}s — {len(full_text):,} chars, {errors} errors", flush=True)
    print(f"  Output: {output_file}", flush=True)
    return True


def main():
    sources = []

    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = "all"

    if target in ("ihya", "all"):
        ihya_dir = IMAGE_DIR / "ihya_v4"
        if ihya_dir.exists() and list(ihya_dir.glob("page-*.png")):
            sources.append(("Ihya Vol 4", ihya_dir, RAW_DIR / "ihya_vol4.txt"))

    if target in ("riyad", "all"):
        riyad_dir = IMAGE_DIR / "riyad"
        if riyad_dir.exists() and list(riyad_dir.glob("page-*.png")):
            sources.append(("Riyad al-Saliheen", riyad_dir, RAW_DIR / "riyad_al_saliheen.txt"))

    if not sources:
        print("No image directories found. Run pdftoppm first.")
        return

    print(f"Cloud Vision OCR — processing {len(sources)} source(s)\n")

    for name, img_dir, output in sources:
        process_source(name, img_dir, output)
        print()

    print("All OCR complete!")


if __name__ == "__main__":
    main()
