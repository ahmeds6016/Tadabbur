#!/usr/bin/env python3
"""
PDF Text Extraction Pipeline for Scholarly Sources.

Extracts text from text-layer PDFs using pdftotext (poppler-utils).
Scanned/image PDFs (Riyad al-Saliheen, Ihya Vol 4) are flagged for OCR.
"""

import subprocess
import os
import sys
import json
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_OUTPUT_DIR = PROJECT_ROOT / "backend" / "data" / "sources" / "raw"

# PDF source files and their metadata
SOURCES = {
    "thematic_commentary": {
        "pdf": PROJECT_ROOT / "A-Thematic-Commentary-on-the-Quran.pdf",
        "description": "A Thematic Commentary on the Qur'an (Shaykh Muhammad al-Ghazali)",
        "text_extractable": True,
        "volumes": 1,
    },
    "ihya_vol1": {
        "pdf": PROJECT_ROOT / "ihya-ulum-al-din-vol-1.pdf",
        "description": "Ihya Ulum al-Din Vol 1 - Acts of Worship",
        "text_extractable": True,
        "volumes": 1,
    },
    "ihya_vol2": {
        "pdf": PROJECT_ROOT / "ihya-ulum-al-din-vol-2.pdf",
        "description": "Ihya Ulum al-Din Vol 2 - Worldly Usages",
        "text_extractable": True,
        "volumes": 1,
    },
    "ihya_vol3": {
        "pdf": PROJECT_ROOT / "Ihya Ulum Al Din Vol 3.pdf",
        "description": "Ihya Ulum al-Din Vol 3 - Destructive Evils",
        "text_extractable": True,
        "volumes": 1,
    },
    "ihya_vol4": {
        "pdf": PROJECT_ROOT / "ihya-v4.pdf",
        "description": "Ihya Ulum al-Din Vol 4 - Constructive Virtues",
        "text_extractable": False,  # Scanned image - needs OCR
        "volumes": 1,
    },
    "madarij_vol1": {
        "pdf": PROJECT_ROOT / "Madarij al-Salikin (Ranks of the Wayfarers) by Ibn Qayyimvol1.pdf",
        "description": "Madarij al-Salikin Vol 1 (Ibn Qayyim)",
        "text_extractable": True,
        "volumes": 1,
    },
    "madarij_vol2": {
        "pdf": PROJECT_ROOT / "Madarij al-Salikin (Ranks of the Wayfarers) by Ibn Qayyim vol 2.pdf",
        "description": "Madarij al-Salikin Vol 2 (Ibn Qayyim)",
        "text_extractable": True,
        "volumes": 1,
    },
    "riyad_al_saliheen": {
        "pdf": PROJECT_ROOT / "Riyad-us-Saliheen.pdf",
        "description": "Riyad al-Saliheen (Imam al-Nawawi)",
        "text_extractable": False,  # Scanned image - needs OCR
        "volumes": 1,
    },
}


def extract_pdf_text(pdf_path: Path, output_path: Path) -> dict:
    """Extract text from a PDF using pdftotext."""
    if not pdf_path.exists():
        return {"success": False, "error": f"PDF not found: {pdf_path}"}

    try:
        # Get page count first
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True, text=True, timeout=30
        )
        pages = 0
        for line in result.stdout.split('\n'):
            if line.startswith('Pages:'):
                pages = int(line.split(':')[1].strip())
                break

        # Extract text
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), str(output_path)],
            capture_output=True, text=True, timeout=300
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr}

        # Verify output
        if output_path.exists():
            size = output_path.stat().st_size
            # Read first 200 chars to check quality
            with open(output_path, 'r', errors='replace') as f:
                sample = f.read(500)

            # Check if it's mostly form feeds (scanned PDF)
            if size < pages * 10:  # Less than 10 bytes per page = likely scanned
                return {
                    "success": False,
                    "error": "PDF appears to be scanned (no text layer)",
                    "pages": pages,
                    "file_size": size,
                }

            return {
                "success": True,
                "pages": pages,
                "file_size": size,
                "chars": size,
                "sample": sample[:200],
                "output_path": str(output_path),
            }
        else:
            return {"success": False, "error": "Output file not created"}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Extraction timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def extract_pdf_by_page(pdf_path: Path, output_dir: Path) -> dict:
    """Extract text page-by-page for more granular control."""
    if not pdf_path.exists():
        return {"success": False, "error": f"PDF not found: {pdf_path}"}

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Get page count
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True, text=True, timeout=30
        )
        pages = 0
        for line in result.stdout.split('\n'):
            if line.startswith('Pages:'):
                pages = int(line.split(':')[1].strip())
                break

        # Extract full text
        full_output = output_dir / "full.txt"
        result = subprocess.run(
            ["pdftotext", str(pdf_path), str(full_output)],
            capture_output=True, text=True, timeout=300
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr}

        # Read and split by form feeds (page breaks)
        with open(full_output, 'r', errors='replace') as f:
            content = f.read()

        page_texts = content.split('\f')
        # Filter empty pages
        page_texts = [p for p in page_texts if p.strip()]

        return {
            "success": True,
            "pages": pages,
            "extracted_pages": len(page_texts),
            "total_chars": len(content),
            "output_path": str(full_output),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def run_extraction():
    """Run extraction for all text-extractable sources."""
    RAW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for source_key, source_info in SOURCES.items():
        print(f"\n{'='*60}")
        print(f"Processing: {source_info['description']}")
        print(f"PDF: {source_info['pdf'].name}")

        if not source_info['text_extractable']:
            print(f"  SKIPPED - Scanned image, needs OCR")
            results[source_key] = {
                "status": "skipped",
                "reason": "Scanned image - requires OCR",
                "pdf": str(source_info['pdf']),
            }
            continue

        output_path = RAW_OUTPUT_DIR / f"{source_key}.txt"
        result = extract_pdf_text(source_info['pdf'], output_path)

        if result['success']:
            print(f"  SUCCESS - {result['pages']} pages, {result['chars']:,} chars")
            print(f"  Output: {result['output_path']}")
            print(f"  Sample: {result['sample'][:100]}...")
        else:
            print(f"  FAILED - {result['error']}")

        results[source_key] = result

    # Save extraction report
    report_path = RAW_OUTPUT_DIR / "_extraction_report.json"
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nExtraction report saved to: {report_path}")

    return results


if __name__ == "__main__":
    results = run_extraction()

    # Summary
    print(f"\n{'='*60}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*60}")
    success = sum(1 for r in results.values() if r.get('success'))
    skipped = sum(1 for r in results.values() if r.get('status') == 'skipped')
    failed = len(results) - success - skipped
    print(f"  Success: {success}")
    print(f"  Skipped (needs OCR): {skipped}")
    print(f"  Failed: {failed}")
