#!/usr/bin/env python3
"""
Parse A Thematic Commentary on the Qur'an into structured JSON.

Splits the raw extracted text into 114 surah entries with sections
delimited by the ጥጦ symbol. Extracts verse references and synopses.
"""

import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_FILE = PROJECT_ROOT / "backend" / "data" / "sources" / "raw" / "thematic_commentary.txt"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "data" / "indexes" / "thematic_commentary"

# Standard surah names for cross-reference resolution
SURAH_NAMES = {
    1: "Al-Fatihah", 2: "Al-Baqarah", 3: "Al Imran", 4: "Al-Nisa",
    5: "Al-Maidah", 6: "Al-Anam", 7: "Al-Araf", 8: "Al-Anfal",
    9: "Al-Tawbah", 10: "Yunus", 11: "Hud", 12: "Yusuf",
    13: "Al-Rad", 14: "Ibrahim", 15: "Al-Hijr", 16: "Al-Nahl",
    17: "Al-Isra", 18: "Al-Kahf", 19: "Maryam", 20: "Ta Ha",
    21: "Al-Anbiya", 22: "Al-Hajj", 23: "Al-Muminun", 24: "Al-Nur",
    25: "Al-Furqan", 26: "Al-Shuara", 27: "Al-Naml", 28: "Al-Qasas",
    29: "Al-Ankabut", 30: "Al-Rum", 31: "Luqman", 32: "Al-Sajdah",
    33: "Al-Ahzab", 34: "Saba", 35: "Fatir", 36: "Ya Sin",
    37: "Al-Saffat", 38: "Sad", 39: "Al-Zumar", 40: "Ghafir",
    41: "Fussilat", 42: "Al-Shura", 43: "Al-Zukhruf", 44: "Al-Dukhan",
    45: "Al-Jathiyah", 46: "Al-Ahqaf", 47: "Muhammad", 48: "Al-Fath",
    49: "Al-Hujurat", 50: "Qaf", 51: "Al-Dhariyat", 52: "Al-Tur",
    53: "Al-Najm", 54: "Al-Qamar", 55: "Al-Rahman", 56: "Al-Waqiah",
    57: "Al-Hadid", 58: "Al-Mujadilah", 59: "Al-Hashr", 60: "Al-Mumtahanah",
    61: "Al-Saff", 62: "Al-Jumuah", 63: "Al-Munafiqun", 64: "Al-Taghabun",
    65: "Al-Talaq", 66: "Al-Tahrim", 67: "Al-Mulk", 68: "Al-Qalam",
    69: "Al-Haqqah", 70: "Al-Maarij", 71: "Nuh", 72: "Al-Jinn",
    73: "Al-Muzzammil", 74: "Al-Muddaththir", 75: "Al-Qiyamah", 76: "Al-Insan",
    77: "Al-Mursalat", 78: "Al-Naba", 79: "Al-Naziat", 80: "Abasa",
    81: "Al-Takwir", 82: "Al-Infitar", 83: "Al-Mutaffifin", 84: "Al-Inshiqaq",
    85: "Al-Buruj", 86: "Al-Tariq", 87: "Al-Ala", 88: "Al-Ghashiyah",
    89: "Al-Fajr", 90: "Al-Balad", 91: "Al-Shams", 92: "Al-Layl",
    93: "Al-Duha", 94: "Al-Sharh", 95: "Al-Tin", 96: "Al-Alaq",
    97: "Al-Qadr", 98: "Al-Bayyinah", 99: "Al-Zalzalah", 100: "Al-Adiyat",
    101: "Al-Qariah", 102: "Al-Takathur", 103: "Al-Asr", 104: "Al-Humazah",
    105: "Al-Fil", 106: "Quraysh", 107: "Al-Maun", 108: "Al-Kawthar",
    109: "Al-Kafirun", 110: "Al-Nasr", 111: "Al-Masad", 112: "Al-Ikhlas",
    113: "Al-Falaq", 114: "Al-Nas",
}

# Page ranges from TOC (surah_number -> (page_start, page_end))
# Extracted from the Table of Contents
TOC_PAGES = {
    1: (1, 5), 2: (6, 29), 3: (30, 54), 4: (55, 87), 5: (88, 114),
    6: (115, 137), 7: (138, 159), 8: (160, 176), 9: (177, 196),
    10: (197, 215), 11: (216, 233), 12: (234, 249), 13: (250, 257),
    14: (258, 265), 15: (266, 273), 16: (274, 291), 17: (292, 307),
    18: (308, 322), 19: (323, 332), 20: (333, 342), 21: (343, 351),
    22: (352, 365), 23: (366, 374), 24: (375, 384), 25: (385, 393),
    26: (394, 402), 27: (403, 412), 28: (413, 424), 29: (425, 432),
    30: (433, 441), 31: (442, 446), 32: (447, 451), 33: (452, 462),
    34: (463, 470), 35: (471, 477), 36: (478, 485), 37: (486, 493),
    38: (494, 501), 39: (502, 512), 40: (513, 521), 41: (522, 529),
    42: (530, 537), 43: (538, 545), 44: (546, 550), 45: (551, 555),
    46: (556, 563), 47: (564, 568), 48: (569, 576), 49: (577, 580),
    50: (581, 584), 51: (585, 588), 52: (589, 593), 53: (594, 598),
    54: (599, 602), 55: (603, 606), 56: (607, 612), 57: (626, 632),
    58: (633, 637), 59: (638, 642), 60: (643, 648), 61: (649, 652),
    62: (653, 656), 63: (657, 659), 64: (660, 664), 65: (665, 670),
    66: (671, 675), 67: (676, 680), 68: (681, 686), 69: (687, 690),
    70: (691, 694), 71: (695, 698), 72: (699, 702), 73: (703, 706),
    74: (707, 712), 75: (713, 715), 76: (716, 719), 77: (720, 723),
    78: (724, 727), 79: (728, 729), 80: (730, 731), 81: (732, 733),
    82: (734, 735), 83: (736, 738), 84: (739, 740), 85: (741, 743),
    86: (744, 745), 87: (746, 747), 88: (748, 748), 89: (749, 750),
    90: (751, 752), 91: (753, 753), 92: (754, 755), 93: (756, 756),
    94: (757, 757), 95: (758, 759), 96: (760, 761), 97: (762, 763),
    98: (764, 765), 99: (766, 767), 100: (768, 768), 101: (769, 769),
    102: (749, 750), 103: (751, 751), 104: (753, 753), 105: (754, 755),
    106: (756, 756), 107: (757, 757), 108: (758, 759), 109: (760, 761),
    110: (762, 763), 111: (764, 765), 112: (766, 767), 113: (768, 768),
    114: (769, 770),
}


def extract_verse_refs(text):
    """Extract verse references from commentary text."""
    refs = []

    # Same-surah references: (verse) or (verse-range)
    for m in re.finditer(r'\((\d{1,3})\)', text):
        refs.append({"type": "same_surah", "verse": m.group(1)})

    # Verse ranges: (N–M) or (N-M)
    for m in re.finditer(r'\((\d{1,3})[–\-](\d{1,3})\)', text):
        refs.append({"type": "same_surah", "verse": f"{m.group(1)}-{m.group(2)}"})

    # Cross-surah references: (surah-name: verse) or (surah-name: verse-range)
    for m in re.finditer(r'\(([a-zA-Z¥ÏÏ‰¢\^|ß>®~\-\s\']+?):\s*(\d{1,3}(?:[–\-]\d{1,3})?)\)', text):
        surah_name = m.group(1).strip()
        verse = m.group(2)
        refs.append({"type": "cross_surah", "surah_name": surah_name, "verse": verse})

    return refs


def clean_text(text):
    """Clean extracted text: remove running headers, page numbers, form feeds."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip running headers like "surah N • Name" and "A Thematic Commentary on the Qur'an"
        if re.match(r'^surah \d+ • ', stripped):
            continue
        if stripped == "A Thematic Commentary on the Qur'an":
            continue
        # Skip bare page numbers
        if re.match(r'^\d{1,3}$', stripped):
            continue
        # Skip form feeds
        if stripped == '\f' or stripped == '':
            if cleaned and cleaned[-1] == '':
                continue  # Collapse multiple blank lines
            cleaned.append('')
            continue
        cleaned.append(line.rstrip())

    return '\n'.join(cleaned).strip()


def parse_thematic_commentary():
    """Parse the raw extracted text into structured surah entries."""
    with open(RAW_FILE, 'r', errors='replace') as f:
        full_text = f.read()

    lines = full_text.split('\n')

    # Find all content chapter headings: lines matching "^\s+surah \d+$"
    heading_pattern = re.compile(r'^\s+surah (\d+)\s*$')
    chapter_starts = []

    for i, line in enumerate(lines):
        m = heading_pattern.match(line)
        if m:
            surah_num = int(m.group(1))
            chapter_starts.append((i, surah_num))

    print(f"Found {len(chapter_starts)} chapter headings")

    # Find end markers: "Index of Qur'anic Quotations" marks end of last surah
    end_line = len(lines)
    for i, line in enumerate(lines):
        if "Index of Qur" in line and i > chapter_starts[-1][0]:
            end_line = i
            break

    entries = []

    for idx, (start_line, surah_num) in enumerate(chapter_starts):
        # End of this chapter is start of next, or end of book
        if idx + 1 < len(chapter_starts):
            end = chapter_starts[idx + 1][0]
        else:
            end = end_line

        # Extract the raw chapter text
        chapter_lines = lines[start_line:end]
        chapter_text = '\n'.join(chapter_lines)

        # Extract the heading info (name lines follow the "surah N" line)
        name_transliterated = ""
        name_english = ""
        content_start = 0

        for j, cline in enumerate(chapter_lines):
            stripped = cline.strip()
            if j == 0:
                continue  # Skip the "surah N" line
            if not stripped:
                continue
            if not name_transliterated and stripped and not stripped.startswith('('):
                # Skip running headers
                if '•' not in stripped and 'Commentary' not in stripped:
                    name_transliterated = stripped
                    continue
            if not name_english and stripped.startswith('(') and stripped.endswith(')'):
                name_english = stripped[1:-1]
                content_start = j + 1
                break

        # Get the actual commentary content (after heading)
        content_lines = chapter_lines[content_start:]
        raw_content = '\n'.join(content_lines)

        # Clean the content
        cleaned_content = clean_text(raw_content)

        # Split into sections by ጥጦ divider
        sections_raw = re.split(r'ጥጦ', cleaned_content)
        sections = []

        for sec_idx, sec_text in enumerate(sections_raw):
            sec_text = sec_text.strip()
            if not sec_text:
                continue

            verse_refs = extract_verse_refs(sec_text)
            sections.append({
                "section_index": sec_idx,
                "text": sec_text,
                "verse_refs": verse_refs,
                "char_count": len(sec_text),
            })

        # Extract synopsis (first ~500 chars of first section, up to first period after 200 chars)
        synopsis = ""
        if sections:
            first_text = sections[0]["text"]
            # Find a good cutoff point
            cutoff = min(len(first_text), 500)
            for i in range(200, cutoff):
                if first_text[i] == '.':
                    cutoff = i + 1
                    break
            synopsis = first_text[:cutoff].strip()

        page_range = TOC_PAGES.get(surah_num, (0, 0))

        entry = {
            "id": f"thematic_{surah_num:03d}",
            "surah_number": surah_num,
            "surah_name": SURAH_NAMES.get(surah_num, ""),
            "surah_name_transliterated": name_transliterated,
            "surah_name_english": name_english,
            "page_start": page_range[0],
            "page_end": page_range[1],
            "synopsis": synopsis,
            "sections": sections,
            "total_sections": len(sections),
            "total_chars": sum(s["char_count"] for s in sections),
        }
        entries.append(entry)

    return entries


def build_verse_map(entries):
    """Build reverse index: surah:verse -> list of thematic commentary locations."""
    verse_map = {}

    for entry in entries:
        surah_num = entry["surah_number"]
        for sec in entry["sections"]:
            for ref in sec["verse_refs"]:
                if ref["type"] == "same_surah":
                    verse_str = ref["verse"]
                    key = f"{surah_num}:{verse_str}"
                    if key not in verse_map:
                        verse_map[key] = []
                    verse_map[key].append({
                        "source": "thematic_commentary",
                        "surah": surah_num,
                        "section_index": sec["section_index"],
                    })

    return verse_map


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Parsing Thematic Commentary...")
    entries = parse_thematic_commentary()
    print(f"Parsed {len(entries)} surah entries")

    # Save individual surah files
    for entry in entries:
        surah_file = OUTPUT_DIR / f"surah_{entry['surah_number']:03d}.json"
        with open(surah_file, 'w') as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)

    # Build and save index
    index = {
        "source": "thematic_commentary",
        "total_surahs": len(entries),
        "surahs": {
            str(e["surah_number"]): {
                "name": e["surah_name"],
                "name_transliterated": e["surah_name_transliterated"],
                "name_english": e["surah_name_english"],
                "page_start": e["page_start"],
                "page_end": e["page_end"],
                "sections": e["total_sections"],
                "chars": e["total_chars"],
            }
            for e in entries
        },
    }
    with open(OUTPUT_DIR / "_index.json", 'w') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    # Build and save verse map
    verse_map = build_verse_map(entries)
    with open(OUTPUT_DIR / "_verse_map.json", 'w') as f:
        json.dump(verse_map, f, indent=2, ensure_ascii=False)

    # Summary
    total_sections = sum(e["total_sections"] for e in entries)
    total_chars = sum(e["total_chars"] for e in entries)
    total_refs = sum(
        len(ref)
        for e in entries
        for s in e["sections"]
        for ref in [s["verse_refs"]]
    )

    print(f"\nResults:")
    print(f"  Surahs parsed: {len(entries)}")
    print(f"  Total sections: {total_sections}")
    print(f"  Total characters: {total_chars:,}")
    print(f"  Total verse references: {total_refs}")
    print(f"  Verse map entries: {len(verse_map)}")
    print(f"  Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
