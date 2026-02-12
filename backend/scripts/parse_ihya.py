#!/usr/bin/env python3
"""
Parse Ihya Ulum al-Din (Vols 1-4) into structured JSON.

Splits the raw extracted text by CHAPTER headings and ALL CAPS section titles.
Extracts Quran verse references and hadith mentions.
"""

import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "backend" / "data" / "sources" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "data" / "indexes" / "ihya_ulum_al_din"

# Volume metadata
VOLUMES = {
    1: {
        "file": "ihya_vol1.txt",
        "quarter": "Acts of Worship",
        "quarter_number": 1,
    },
    2: {
        "file": "ihya_vol2.txt",
        "quarter": "Worldly Usages",
        "quarter_number": 2,
    },
    3: {
        "file": "ihya_vol3.txt",
        "quarter": "Destructive Evils",
        "quarter_number": 3,
    },
    4: {
        "file": "ihya_vol4.txt",
        "quarter": "Constructive Virtues",
        "quarter_number": 4,
    },
}

# Roman numeral conversion
ROMAN_TO_INT = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
    'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
    'VIH': 8,  # OCR error in vol1 for VIII
}


def extract_quran_refs(text):
    """Extract Quran verse references from text."""
    refs = []
    # Pattern: surah:verse or N:M format
    for m in re.finditer(r'(\d{1,3}):(\d{1,3})', text):
        surah = int(m.group(1))
        verse = int(m.group(2))
        if 1 <= surah <= 114 and 1 <= verse <= 286:
            refs.append({"surah": surah, "verse": verse})
    return refs


def extract_hadith_mentions(text):
    """Extract hadith references/mentions from text."""
    hadith = []
    # Pattern: "The Prophet said:" or "Prophet said:"
    for m in re.finditer(r'(?:The )?Prophet (?:said|has said|was reported)[:\s]+[""]?(.+?)[""]?(?:\.|$)', text, re.IGNORECASE):
        hadith.append(m.group(1).strip()[:200])  # Cap at 200 chars
    # Pattern: Hadis/Hadith reference
    for m in re.finditer(r'(?:Hadis|Hadith)[:\s]+(.+?)(?:\.|$)', text, re.IGNORECASE):
        hadith.append(m.group(1).strip()[:200])
    return hadith


def clean_text(text):
    """Clean extracted text from Ihya volumes."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip running headers
        if re.match(r'^Vol-[IVX]+', stripped):
            continue
        if stripped in ("The Book of Worship", "The Book of Worldly Usages",
                       "The Book of Destructive evils", "The Book of Destructive Evils",
                       "THE REVIVAL OF RELIGIOUS LEARNINGS",
                       "REVIVAL OF RELIGIOUS LEARNINGS"):
            continue
        # Skip bare page numbers
        if re.match(r'^\d{1,3}\s*$', stripped):
            continue
        if not stripped:
            if cleaned and cleaned[-1] == '':
                continue
            cleaned.append('')
            continue
        cleaned.append(line.rstrip())
    return '\n'.join(cleaned).strip()


def find_chapters(text):
    """Find chapter boundaries in the text."""
    lines = text.split('\n')
    chapters = []

    # Pattern: "CHAPTER [ROMAN]" or "CHAPTER [number]" at start of line
    chapter_pattern = re.compile(r'^\s*CHAPTER\s+([IVX]+|\d+)', re.IGNORECASE)
    # Also handle OCR errors like "CHPATER"
    chapter_pattern_alt = re.compile(r'^\s*CHPATER\s*([IVX]+|\d+)', re.IGNORECASE)

    for i, line in enumerate(lines):
        m = chapter_pattern.match(line) or chapter_pattern_alt.match(line)
        if m:
            roman_or_num = m.group(1).upper()
            if roman_or_num in ROMAN_TO_INT:
                ch_num = ROMAN_TO_INT[roman_or_num]
            else:
                try:
                    ch_num = int(roman_or_num)
                except ValueError:
                    continue

            # Get chapter title from next non-empty line(s)
            title = ""
            for j in range(i + 1, min(i + 5, len(lines))):
                stripped = lines[j].strip()
                if stripped and not chapter_pattern.match(stripped):
                    title = stripped
                    break

            chapters.append({
                "line_index": i,
                "chapter_number": ch_num,
                "chapter_roman": roman_or_num,
                "chapter_title": title,
            })

    return chapters


def find_sections(text):
    """Find ALL CAPS section headers within chapter text."""
    lines = text.split('\n')
    sections = []

    # ALL CAPS section headers (at least 3 words, all uppercase)
    section_pattern = re.compile(r'^[A-Z][A-Z\s,\-:]{10,}$')

    for i, line in enumerate(lines):
        stripped = line.strip()
        if section_pattern.match(stripped) and len(stripped.split()) >= 2:
            # Verify it's not a running header we missed
            if stripped not in ("THE REVIVAL OF RELIGIOUS LEARNINGS",
                              "REVIVAL OF RELIGIOUS LEARNINGS"):
                sections.append({
                    "line_index": i,
                    "title": stripped,
                })

    return sections


def parse_volume(vol_num, vol_info):
    """Parse a single Ihya volume."""
    raw_file = RAW_DIR / vol_info["file"]
    if not raw_file.exists():
        print(f"  File not found: {raw_file}")
        return None

    with open(raw_file, 'r', errors='replace') as f:
        text = f.read()

    lines = text.split('\n')

    # Find chapter boundaries
    chapters_meta = find_chapters(text)
    print(f"  Found {len(chapters_meta)} chapters")

    if not chapters_meta:
        # If no chapters found, treat whole volume as one entry
        cleaned = clean_text(text)
        return {
            "volume": vol_num,
            "quarter_name": vol_info["quarter"],
            "quarter_number": vol_info["quarter_number"],
            "chapters": [{
                "chapter_number": 1,
                "chapter_roman": "I",
                "chapter_title": vol_info["quarter"],
                "sections": [{
                    "section_title": "FULL_TEXT",
                    "text": cleaned,
                    "quran_refs": extract_quran_refs(cleaned),
                    "hadith_refs": extract_hadith_mentions(cleaned),
                    "char_count": len(cleaned),
                }],
            }],
        }

    # Filter to only content chapters (skip TOC chapter listings)
    # TOC chapters are clustered together (each ~2-3 lines apart), while content chapters
    # have substantial text between them. Find the first chapter with >200 chars of text
    # before the next chapter heading — that's where content starts.
    content_chapters = []
    for i, ch in enumerate(chapters_meta):
        if i + 1 < len(chapters_meta):
            gap = chapters_meta[i + 1]["line_index"] - ch["line_index"]
        else:
            gap = len(lines) - ch["line_index"]

        # Content chapters have >20 lines between them (not just a TOC listing)
        if gap > 20:
            content_chapters.append(ch)

    if not content_chapters:
        content_chapters = chapters_meta

    print(f"  Content chapters (after TOC filter): {len(content_chapters)}")

    parsed_chapters = []

    for idx, ch_meta in enumerate(content_chapters):
        # Get text from this chapter to the next
        start = ch_meta["line_index"]
        if idx + 1 < len(content_chapters):
            end = content_chapters[idx + 1]["line_index"]
        else:
            end = len(lines)

        chapter_text = '\n'.join(lines[start:end])
        cleaned_chapter = clean_text(chapter_text)

        # Find sections within this chapter
        section_headers = find_sections(cleaned_chapter)
        ch_lines = cleaned_chapter.split('\n')

        sections = []
        if section_headers:
            for sec_idx, sec_meta in enumerate(section_headers):
                sec_start = sec_meta["line_index"]
                if sec_idx + 1 < len(section_headers):
                    sec_end = section_headers[sec_idx + 1]["line_index"]
                else:
                    sec_end = len(ch_lines)

                sec_text = '\n'.join(ch_lines[sec_start:sec_end]).strip()
                sections.append({
                    "section_title": sec_meta["title"],
                    "text": sec_text,
                    "quran_refs": extract_quran_refs(sec_text),
                    "hadith_refs": extract_hadith_mentions(sec_text),
                    "char_count": len(sec_text),
                })
        else:
            # No sections found, treat whole chapter as one section
            sections.append({
                "section_title": ch_meta["chapter_title"].upper() if ch_meta["chapter_title"] else "MAIN",
                "text": cleaned_chapter,
                "quran_refs": extract_quran_refs(cleaned_chapter),
                "hadith_refs": extract_hadith_mentions(cleaned_chapter),
                "char_count": len(cleaned_chapter),
            })

        parsed_chapters.append({
            "chapter_number": ch_meta["chapter_number"],
            "chapter_roman": ch_meta["chapter_roman"],
            "chapter_title": ch_meta["chapter_title"],
            "sections": sections,
            "total_sections": len(sections),
            "total_chars": sum(s["char_count"] for s in sections),
        })

    return {
        "volume": vol_num,
        "quarter_name": vol_info["quarter"],
        "quarter_number": vol_info["quarter_number"],
        "chapters": parsed_chapters,
    }


def build_verse_map(all_volumes):
    """Build reverse index: surah:verse -> ihya locations."""
    verse_map = {}

    for vol_data in all_volumes:
        if not vol_data:
            continue
        vol_num = vol_data["volume"]
        for ch in vol_data["chapters"]:
            for sec in ch["sections"]:
                for ref in sec.get("quran_refs", []):
                    key = f"{ref['surah']}:{ref['verse']}"
                    if key not in verse_map:
                        verse_map[key] = []
                    verse_map[key].append({
                        "source": "ihya_ulum_al_din",
                        "volume": vol_num,
                        "chapter": ch["chapter_number"],
                        "section": sec["section_title"],
                    })

    return verse_map


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_volumes = []

    for vol_num, vol_info in VOLUMES.items():
        print(f"\nParsing Volume {vol_num}: {vol_info['quarter']}...")
        vol_data = parse_volume(vol_num, vol_info)
        if vol_data:
            all_volumes.append(vol_data)

            # Save volume file
            vol_file = OUTPUT_DIR / f"vol_{vol_num}.json"
            with open(vol_file, 'w') as f:
                json.dump(vol_data, f, indent=2, ensure_ascii=False)

            # Summary
            total_ch = len(vol_data["chapters"])
            total_sec = sum(ch["total_sections"] for ch in vol_data["chapters"])
            total_chars = sum(ch["total_chars"] for ch in vol_data["chapters"])
            print(f"  Chapters: {total_ch}")
            print(f"  Sections: {total_sec}")
            print(f"  Characters: {total_chars:,}")

    # Build index
    index = {
        "source": "ihya_ulum_al_din",
        "total_volumes": len(all_volumes),
        "volumes": {},
    }
    for vol_data in all_volumes:
        vol_num = vol_data["volume"]
        index["volumes"][str(vol_num)] = {
            "quarter_name": vol_data["quarter_name"],
            "chapters": {
                str(ch["chapter_number"]): {
                    "title": ch["chapter_title"],
                    "sections": ch["total_sections"],
                    "chars": ch["total_chars"],
                }
                for ch in vol_data["chapters"]
            },
        }

    with open(OUTPUT_DIR / "_index.json", 'w') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    # Build verse map
    verse_map = build_verse_map(all_volumes)
    with open(OUTPUT_DIR / "_verse_map.json", 'w') as f:
        json.dump(verse_map, f, indent=2, ensure_ascii=False)

    print(f"\nTotal verse map entries: {len(verse_map)}")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
