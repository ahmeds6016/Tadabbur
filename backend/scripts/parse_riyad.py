#!/usr/bin/env python3
"""
Parse Riyad al-Saliheen (OCR text) into structured JSON.

Splits the OCR'd text by Chapter headings and extracts hadith entries.
Handles mixed Arabic/English content from the bilingual PDF.
"""

import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "backend" / "data" / "sources" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "data" / "indexes" / "riyad_al_saliheen"


def clean_ocr_text(text):
    """Clean OCR artifacts from Riyad text."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip page markers from our OCR output
        if stripped.startswith('--- PAGE'):
            continue
        # Skip the running header
        if 'Riyaadhos-Saaliheen' in stripped:
            continue
        if stripped in ('(Abridged)', '~ (Abridged)', '* (Abridged)'):
            continue
        # Skip bare page numbers
        if re.match(r'^\d{1,4}$', stripped):
            continue
        # Skip lines that are predominantly non-Latin (Arabic garble from OCR)
        latin_chars = sum(1 for c in stripped if c.isascii() and c.isalpha())
        total_chars = sum(1 for c in stripped if c.isalpha())
        if total_chars > 10 and latin_chars < total_chars * 0.4:
            continue
        if not stripped:
            if cleaned and cleaned[-1] == '':
                continue
            cleaned.append('')
            continue
        cleaned.append(line.rstrip())
    return '\n'.join(cleaned).strip()


def extract_quran_refs(text):
    """Extract Quran verse references from Riyad text."""
    refs = []
    # Pattern: (surah:verse) or (N: M) or [N:M]
    for m in re.finditer(r'[\(\[](\d{1,3})\s*:\s*(\d{1,3})[\)\]]', text):
        surah = int(m.group(1))
        verse = int(m.group(2))
        if 1 <= surah <= 114 and 1 <= verse <= 286:
            ref = {"surah": surah, "verse": verse}
            if ref not in refs:
                refs.append(ref)
    return refs


def find_chapters(text):
    """Find chapter headings in the OCR text."""
    lines = text.split('\n')
    chapters = []

    # Pattern: "Chapter (N)" or "Chapter( N )" or "Chapter:(N)"
    chapter_pattern = re.compile(
        r'^Chapter\s*[\(:\s]+\s*(\d+)\s*\)?',
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        stripped = line.strip()
        m = chapter_pattern.match(stripped)
        if m:
            ch_num = int(m.group(1))

            # Get chapter title from next non-empty line
            title = ""
            for j in range(i + 1, min(i + 5, len(lines))):
                candidate = lines[j].strip()
                if candidate and not chapter_pattern.match(candidate):
                    # Skip Arabic lines
                    latin_chars = sum(1 for c in candidate if c.isascii() and c.isalpha())
                    total_alpha = sum(1 for c in candidate if c.isalpha())
                    if total_alpha > 0 and latin_chars / max(total_alpha, 1) > 0.5:
                        title = candidate
                        break

            chapters.append({
                "line_index": i,
                "chapter_number": ch_num,
                "chapter_title": title,
            })

    return chapters


def find_hadith_entries(text):
    """Find individual hadith narrations in chapter text."""
    entries = []

    # Pattern: "N. Narrated..." or "Narrated..." at start of line
    # Also: "N- Narrated" or just numbered paragraphs
    hadith_pattern = re.compile(
        r'(?:^|\n)\s*(\d+)\s*[\.\-]\s*(?:Narrated|It is narrated|It was narrated)',
        re.IGNORECASE
    )

    # Also match unnumbered "Narrated X:" patterns
    narrated_pattern = re.compile(
        r'(?:^|\n)\s*(?:Narrated|It is narrated)\s+([A-Z][a-zA-Z\- \']+?)[\s:;]',
        re.IGNORECASE
    )

    # Find numbered hadith
    for m in hadith_pattern.finditer(text):
        hadith_num = int(m.group(1))
        start_pos = m.start()

        # Extract narrator name
        narrator = ""
        narrator_match = re.search(
            r'(?:Narrated|narrated)\s+([A-Z][a-zA-Z\-\' ]+?)[\s:;]',
            text[start_pos:start_pos + 200]
        )
        if narrator_match:
            narrator = narrator_match.group(1).strip()

        entries.append({
            "position": start_pos,
            "hadith_number": hadith_num,
            "narrator": narrator,
        })

    # If no numbered hadith found, try unnumbered
    if not entries:
        for m in narrated_pattern.finditer(text):
            entries.append({
                "position": m.start(),
                "hadith_number": len(entries) + 1,
                "narrator": m.group(1).strip(),
            })

    # Extract text for each hadith
    result = []
    for idx, entry in enumerate(entries):
        start = entry["position"]
        if idx + 1 < len(entries):
            end = entries[idx + 1]["position"]
        else:
            end = len(text)

        hadith_text = text[start:end].strip()

        # Extract source collection (Bukhari, Muslim, etc.)
        source_coll = ""
        source_match = re.search(
            r'\(\s*((?:Bukhari|Muslim|Abu Dawud|Tirmidhi|Nasai|Ibn Majah|Ahmad|Agreed upon)(?:\s+and\s+(?:Bukhari|Muslim|Abu Dawud|Tirmidhi|Nasai|Ibn Majah|Ahmad))?)\s*\)',
            hadith_text, re.IGNORECASE
        )
        if source_match:
            source_coll = source_match.group(1).strip()

        result.append({
            "hadith_number": entry["hadith_number"],
            "narrator": entry["narrator"],
            "text": hadith_text[:3000],  # Cap at 3000 chars
            "source_collection": source_coll,
            "char_count": len(hadith_text),
        })

    return result


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_file = RAW_DIR / "riyad_al_saliheen.txt"
    if not raw_file.exists():
        print(f"File not found: {raw_file}")
        print("Run ocr_sources.py first to OCR the scanned PDF.")
        return

    with open(raw_file, 'r', errors='replace') as f:
        text = f.read()

    print(f"Raw text: {len(text):,} chars")

    # Clean OCR text
    cleaned = clean_ocr_text(text)
    print(f"Cleaned text: {len(cleaned):,} chars")

    lines = cleaned.split('\n')

    # Find chapters
    chapters = find_chapters(cleaned)
    print(f"Found {len(chapters)} chapters")

    if not chapters:
        print("No chapters found! Check OCR quality.")
        return

    # Parse each chapter
    parsed_chapters = []
    book_number = 1  # Track book number (rough grouping)

    for idx, ch in enumerate(chapters):
        start = ch["line_index"]
        if idx + 1 < len(chapters):
            end = chapters[idx + 1]["line_index"]
        else:
            end = len(lines)

        chapter_text = '\n'.join(lines[start:end])

        # Extract hadith entries
        hadith_entries = find_hadith_entries(chapter_text)

        # Extract verse references
        quran_refs = extract_quran_refs(chapter_text)

        parsed_chapters.append({
            "chapter_number": ch["chapter_number"],
            "chapter_title": ch["chapter_title"],
            "book_number": book_number,
            "hadith_entries": hadith_entries,
            "quran_refs": quran_refs,
            "total_hadith": len(hadith_entries),
            "total_chars": len(chapter_text),
        })

    print(f"\nParsed chapters: {len(parsed_chapters)}")

    total_hadith = sum(ch["total_hadith"] for ch in parsed_chapters)
    print(f"Total hadith extracted: {total_hadith}")

    # Save per-chapter files
    for ch in parsed_chapters:
        ch_file = OUTPUT_DIR / f"book_{ch['book_number']:02d}_ch_{ch['chapter_number']:03d}.json"
        with open(ch_file, 'w') as f:
            json.dump(ch, f, indent=2, ensure_ascii=False)

    # Build index
    index = {
        "source": "riyad_al_saliheen",
        "total_books": 1,  # Simplified - treat as single book
        "total_chapters": len(parsed_chapters),
        "total_hadith": total_hadith,
        "books": {
            "1": {
                "book_name": "Riyad al-Saliheen",
                "chapters": {
                    str(ch["chapter_number"]): {
                        "title": ch["chapter_title"],
                        "hadith_count": ch["total_hadith"],
                        "chars": ch["total_chars"],
                    }
                    for ch in parsed_chapters
                },
            }
        },
    }

    with open(OUTPUT_DIR / "_index.json", 'w') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    # Build verse map
    verse_map = {}
    for ch in parsed_chapters:
        for ref in ch.get("quran_refs", []):
            key = f"{ref['surah']}:{ref['verse']}"
            if key not in verse_map:
                verse_map[key] = []
            verse_map[key].append({
                "source": "riyad_al_saliheen",
                "book": ch["book_number"],
                "chapter": ch["chapter_number"],
                "chapter_title": ch["chapter_title"],
            })

    with open(OUTPUT_DIR / "_verse_map.json", 'w') as f:
        json.dump(verse_map, f, indent=2, ensure_ascii=False)

    print(f"Verse map entries: {len(verse_map)}")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
