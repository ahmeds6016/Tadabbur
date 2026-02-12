#!/usr/bin/env python3
"""
Parse Madarij al-Salikin (Vols 1-2) into structured JSON.

Splits the raw extracted text by Station headings and numbered subsections.
Extracts Quran verse references and hadith mentions.
"""

import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "backend" / "data" / "sources" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "data" / "indexes" / "madarij_al_salikin"

VOLUMES = {
    1: {"file": "madarij_vol1.txt"},
    2: {"file": "madarij_vol2.txt"},
}


def extract_quran_refs(text):
    """Extract Quran verse references (surah:verse pattern)."""
    refs = []
    for m in re.finditer(r'(?:Q|Qurʾān|Quran|Q\.?)\s*(\d{1,3}):(\d{1,3})', text, re.IGNORECASE):
        surah = int(m.group(1))
        verse = int(m.group(2))
        if 1 <= surah <= 114 and 1 <= verse <= 286:
            refs.append({"surah": surah, "verse": verse})
    # Also catch bare surah:verse patterns
    for m in re.finditer(r'\b(\d{1,3}):(\d{1,3})\b', text):
        surah = int(m.group(1))
        verse = int(m.group(2))
        if 1 <= surah <= 114 and 1 <= verse <= 286:
            ref = {"surah": surah, "verse": verse}
            if ref not in refs:
                refs.append(ref)
    return refs


def extract_hadith_mentions(text):
    """Extract hadith references from text."""
    hadith = []
    patterns = [
        r'(?:The )?Prophet\s*(?:\(.*?\))?\s*(?:said|has said|stated)[:\s]+["""](.+?)["""]',
        r'ḥadīth[:\s]+(.+?)(?:\.|$)',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            hadith.append(m.group(1).strip()[:200])
    return hadith


def clean_text(text):
    """Clean extracted Madarij text."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip bare page numbers
        if re.match(r'^\d{1,4}\s*$', stripped):
            continue
        # Skip common running headers
        if stripped in ("Ranks of the Divine Seekers",
                       "ranks of the divine seekers"):
            continue
        if re.match(r'^chapter \d+', stripped, re.IGNORECASE) and len(stripped) < 30:
            continue
        if not stripped:
            if cleaned and cleaned[-1] == '':
                continue
            cleaned.append('')
            continue
        cleaned.append(line.rstrip())
    return '\n'.join(cleaned).strip()


def find_stations(text):
    """Find Station headings in the text.

    Only matches clean headings like:
    - "The Station of Awakening" (standalone line)
    - "1       The Station of Awakening" (numbered in TOC)

    Does NOT match mid-sentence occurrences.
    """
    lines = text.split('\n')
    stations = []

    # Only match lines that are EXACTLY "The Station of [Name]"
    # with optional leading number and whitespace
    heading_pattern = re.compile(
        r'^(?:\d+\s+)?(?:Interlude:\s+)?The Station of ([A-Z][A-Za-zʿāīūṣḥ\s\-\']+)$'
    )

    for i, line in enumerate(lines):
        stripped = line.strip()
        m = heading_pattern.match(stripped)
        if m:
            station_name = m.group(1).strip()
            # Skip TOC entries (they have page numbers at the end)
            if re.search(r'\s+\d{2,}\s*$', station_name):
                continue
            # Station name should be short (< 50 chars) - not a sentence
            if len(station_name) > 50:
                continue
            stations.append({
                "line_index": i,
                "name": station_name,
                "full_heading": stripped,
            })

    return stations


def find_numbered_sections(text):
    """Find numbered subsections like 1, 1.1, 2, 2.1 etc."""
    lines = text.split('\n')
    sections = []

    # Pattern: line starting with number like "1", "1.1", "2.3"
    section_pattern = re.compile(r'^(\d+(?:\.\d+)?)\s+(.+)$')

    for i, line in enumerate(lines):
        stripped = line.strip()
        m = section_pattern.match(stripped)
        if m:
            sec_num = m.group(1)
            title = m.group(2).strip()
            # Only include if the title seems like a heading (not just a sentence)
            if len(title) < 100 and not title.endswith('.'):
                sections.append({
                    "line_index": i,
                    "number": sec_num,
                    "title": title,
                })

    return sections


def parse_volume(vol_num, vol_info):
    """Parse a single Madarij volume."""
    raw_file = RAW_DIR / vol_info["file"]
    if not raw_file.exists():
        print(f"  File not found: {raw_file}")
        return None

    with open(raw_file, 'r', errors='replace') as f:
        text = f.read()

    lines = text.split('\n')

    # Find station headings
    all_stations = find_stations(text)
    print(f"  Found {len(all_stations)} station headings (raw)")

    # Deduplicate stations (same name appearing in TOC and content)
    # Keep only content stations (those with substantial text after them)
    deduped_stations = []
    seen_names = {}
    for st in all_stations:
        name_lower = st["name"].lower().strip()
        # If we've seen this name before, keep the one that's later in the file
        # (more likely to be content, not TOC)
        if name_lower in seen_names:
            # Replace with later occurrence
            seen_names[name_lower] = st
        else:
            seen_names[name_lower] = st

    # The heading_pattern already filters out TOC entries (which have page numbers).
    # Just use all deduplicated stations.
    content_stations = list(seen_names.values())

    # Sort by line index
    content_stations.sort(key=lambda x: x["line_index"])
    print(f"  Content stations: {len(content_stations)}")

    parsed_stations = []

    for idx, st in enumerate(content_stations):
        start = st["line_index"]
        if idx + 1 < len(content_stations):
            end = content_stations[idx + 1]["line_index"]
        else:
            end = len(lines)

        station_text = '\n'.join(lines[start:end])
        cleaned = clean_text(station_text)

        # Find subsections within this station
        subsection_headers = find_numbered_sections(cleaned)
        st_lines = cleaned.split('\n')

        subsections = []
        if subsection_headers and len(subsection_headers) > 1:
            for sub_idx, sub_meta in enumerate(subsection_headers):
                sub_start = sub_meta["line_index"]
                if sub_idx + 1 < len(subsection_headers):
                    sub_end = subsection_headers[sub_idx + 1]["line_index"]
                else:
                    sub_end = len(st_lines)

                sub_text = '\n'.join(st_lines[sub_start:sub_end]).strip()
                subsections.append({
                    "subsection_number": sub_meta["number"],
                    "title": sub_meta["title"],
                    "text": sub_text,
                    "quran_refs": extract_quran_refs(sub_text),
                    "hadith_refs": extract_hadith_mentions(sub_text),
                    "char_count": len(sub_text),
                })
        else:
            # No numbered subsections, treat station as single section
            subsections.append({
                "subsection_number": "1",
                "title": st["name"],
                "text": cleaned,
                "quran_refs": extract_quran_refs(cleaned),
                "hadith_refs": extract_hadith_mentions(cleaned),
                "char_count": len(cleaned),
            })

        # Create station slug from name
        slug = re.sub(r'[^a-z0-9]+', '_', st["name"].lower()).strip('_')

        parsed_stations.append({
            "station_name": st["name"],
            "station_slug": slug,
            "full_heading": st["full_heading"],
            "subsections": subsections,
            "total_subsections": len(subsections),
            "total_chars": sum(s["char_count"] for s in subsections),
        })

    return {
        "volume": vol_num,
        "stations": parsed_stations,
    }


def build_verse_map(all_volumes):
    """Build reverse index: surah:verse -> madarij locations."""
    verse_map = {}

    for vol_data in all_volumes:
        if not vol_data:
            continue
        vol_num = vol_data["volume"]
        for st in vol_data["stations"]:
            for sub in st["subsections"]:
                for ref in sub.get("quran_refs", []):
                    key = f"{ref['surah']}:{ref['verse']}"
                    if key not in verse_map:
                        verse_map[key] = []
                    verse_map[key].append({
                        "source": "madarij_al_salikin",
                        "volume": vol_num,
                        "station": st["station_name"],
                        "subsection": sub["subsection_number"],
                    })

    return verse_map


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_volumes = []

    for vol_num, vol_info in VOLUMES.items():
        print(f"\nParsing Madarij Volume {vol_num}...")
        vol_data = parse_volume(vol_num, vol_info)
        if vol_data:
            all_volumes.append(vol_data)

            vol_file = OUTPUT_DIR / f"vol_{vol_num}.json"
            with open(vol_file, 'w') as f:
                json.dump(vol_data, f, indent=2, ensure_ascii=False)

            total_st = len(vol_data["stations"])
            total_sub = sum(s["total_subsections"] for s in vol_data["stations"])
            total_chars = sum(s["total_chars"] for s in vol_data["stations"])
            print(f"  Stations: {total_st}")
            print(f"  Subsections: {total_sub}")
            print(f"  Characters: {total_chars:,}")

            # Print station names
            for st in vol_data["stations"]:
                print(f"    - {st['station_name']} ({st['total_subsections']} subsections)")

    # Build index
    index = {
        "source": "madarij_al_salikin",
        "total_volumes": len(all_volumes),
        "volumes": {},
    }
    for vol_data in all_volumes:
        vol_num = vol_data["volume"]
        index["volumes"][str(vol_num)] = {
            "stations": {
                st["station_slug"]: {
                    "name": st["station_name"],
                    "subsections": st["total_subsections"],
                    "chars": st["total_chars"],
                }
                for st in vol_data["stations"]
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
