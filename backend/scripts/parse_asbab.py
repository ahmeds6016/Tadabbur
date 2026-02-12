#!/usr/bin/env python3
"""
Parse Asbab al-Nuzul (Al-Wahidi) into structured JSON.

Splits the raw extracted text by surah headings and [surah:verse] markers.
Each entry contains the context of revelation for a specific verse or verse range.
"""

import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "backend" / "data" / "sources" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "data" / "indexes" / "asbab_al_nuzul"

# Surah name mapping (transliterated names used in the PDF → surah number)
SURAH_NAMES = {
    "al-fâtihah": 1, "al-fatihah": 1,
    "al-baqarah": 2,
    "âl 'imrân": 3, "al 'imran": 3, "âl 'imran": 3,
    "an-nisâ'": 4, "an-nisa'": 4, "an-nisâ": 4, "an-nisa": 4,
    "al-mâ'idah": 5, "al-ma'idah": 5,
    "al-an'âm": 6, "al-an'am": 6,
    "al-a'râf": 7, "al-a'raf": 7,
    "al-anfâl": 8, "al-anfal": 8,
    "at-tawbah": 9, "al-tawbah": 9,
    "yûnus": 10, "yunus": 10,
    "hûd": 11, "hud": 11,
    "yûsuf": 12, "yusuf": 12,
    "ar-ra'd": 13, "al-ra'd": 13,
    "ibrâhîm": 14, "ibrahim": 14,
    "al-hijr": 15,
    "an-nahl": 16,
    "al-isrâ'": 17, "al-isra'": 17, "al-isra": 17,
    "al-kahf": 18,
    "maryam": 19,
    "tâ-hâ": 20, "ta-ha": 20,
    "al-anbiyâ'": 21, "al-anbiya'": 21, "al-anbiya": 21,
    "al-hajj": 22,
    "al-mu'minûn": 23, "al-mu'minun": 23,
    "an-nûr": 24, "an-nur": 24,
    "al-furqân": 25, "al-furqan": 25,
    "ash-shu'arâ'": 26, "ash-shu'ara'": 26,
    "an-naml": 27,
    "al-qasas": 28,
    "al-'ankabût": 29, "al-'ankabut": 29,
    "ar-rûm": 30, "ar-rum": 30,
    "luqmân": 31, "luqman": 31,
    "as-sajdah": 32,
    "al-ahzâb": 33, "al-ahzab": 33,
    "saba'": 34, "saba": 34,
    "fâtir": 35, "fatir": 35,
    "yâ-sîn": 36, "ya-sin": 36, "yâ sîn": 36,
    "as-sâffât": 37, "as-saffat": 37,
    "sâd": 38, "sad": 38,
    "az-zumar": 39,
    "ghâfir": 40, "ghafir": 40,
    "fussilat": 41,
    "ash-shûrâ": 42, "ash-shura": 42,
    "az-zukhruf": 43,
    "ad-dukhân": 44, "ad-dukhan": 44,
    "al-jâthiyah": 45, "al-jathiyah": 45,
    "al-ahqâf": 46, "al-ahqaf": 46,
    "muhammad": 47,
    "al-fath": 48,
    "al-hujurât": 49, "al-hujurat": 49,
    "qâf": 50, "qaf": 50,
    "adh-dhâriyât": 51, "adh-dhariyat": 51,
    "at-tûr": 52, "at-tur": 52,
    "an-najm": 53,
    "al-qamar": 54,
    "ar-rahmân": 55, "ar-rahman": 55,
    "al-wâqi'ah": 56, "al-waqi'ah": 56,
    "al-hadîd": 57, "al-hadid": 57,
    "al-mujâdilah": 58, "al-mujadilah": 58,
    "al-hashr": 59,
    "al-mumtahanah": 60,
    "as-saff": 61,
    "al-jumu'ah": 62,
    "al-munâfiqûn": 63, "al-munafiqun": 63,
    "at-taghâbun": 64, "at-taghabun": 64,
    "at-talâq": 65, "at-talaq": 65,
    "at-tahrîm": 66, "at-tahrim": 66,
    "al-mulk": 67,
    "al-qalam": 68,
    "al-hâqqah": 69, "al-haqqah": 69,
    "al-ma'ârij": 70, "al-ma'arij": 70,
    "nûh": 71, "nuh": 71,
    "al-jinn": 72,
    "al-muzzammil": 73,
    "al-muddaththir": 74,
    "al-qiyâmah": 75, "al-qiyamah": 75,
    "al-insân": 76, "al-insan": 76,
    "al-mursalât": 77, "al-mursalat": 77,
    "an-naba'": 78, "an-naba": 78,
    "an-nâzi'ât": 79, "an-nazi'at": 79,
    "'abasa": 80, "abasa": 80,
    "at-takwîr": 81, "at-takwir": 81,
    "al-infitâr": 82, "al-infitar": 82,
    "al-mutaffifîn": 83, "al-mutaffifin": 83,
    "al-inshiqâq": 84, "al-inshiqaq": 84,
    "al-burûj": 85, "al-buruj": 85,
    "at-târiq": 86, "at-tariq": 86,
    "al-a'lâ": 87, "al-a'la": 87,
    "al-ghâshiyah": 88, "al-ghashiyah": 88,
    "al-fajr": 89,
    "al-balad": 90,
    "ash-shams": 91,
    "al-layl": 92,
    "ad-dhuhâ": 93, "ad-dhuha": 93,
    "al-inshirâh": 94, "al-inshirah": 94, "ash-sharh": 94,
    "at-tîn": 95, "at-tin": 95,
    "al-'alaq": 96,
    "al-qadr": 97,
    "al-bayyinah": 98,
    "az-zalzalah": 99,
    "al-'adiyât": 100, "al-'adiyat": 100,
    "al-qâri'ah": 101, "al-qari'ah": 101,
    "at-takâthur": 102, "at-takathur": 102,
    "al-'asr": 103,
    "al-humazah": 104,
    "al-fîl": 105, "al-fil": 105,
    "quraysh": 106,
    "al-mâ'ûn": 107, "al-ma'un": 107,
    "al-kawthar": 108,
    "al-kâfirûn": 109, "al-kafirun": 109,
    "an-nasr": 110,
    "al-masad": 111,
    "al-ikhlâs": 112, "al-ikhlas": 112,
    "al-falaq": 113,
    "an-nâs": 114, "an-nas": 114,
}


def normalize_surah_name(name):
    """Normalize a surah name to find its number."""
    cleaned = name.strip().lower()
    # Remove diacritics variations
    cleaned = cleaned.replace("'", "'").replace("'", "'").replace("`", "'")

    if cleaned in SURAH_NAMES:
        return SURAH_NAMES[cleaned]

    # Try without diacritics
    simple = re.sub(r'[âāáà]', 'a', cleaned)
    simple = re.sub(r'[îīíì]', 'i', simple)
    simple = re.sub(r'[ûūúù]', 'u', simple)
    if simple in SURAH_NAMES:
        return SURAH_NAMES[simple]

    return None


def is_surah_heading(line):
    """Check if a line is a surah heading (short name in parentheses)."""
    stripped = line.strip()
    # Must be in parens, relatively short, and look like a name
    m = re.match(r'^\(([A-Za-zÂâÎîÛûĀāĪīŪū\' \-]+)\)\s*$', stripped)
    if m:
        name = m.group(1).strip()
        # Must be short (surah names are <30 chars)
        if len(name) < 35:
            return name
    return None


def parse_verse_ref(ref_str):
    """Parse a verse reference like [2:14] or [2:1-2]."""
    m = re.match(r'\[(\d+):(\d+)(?:-(\d+))?\]', ref_str.strip())
    if m:
        surah = int(m.group(1))
        verse_start = int(m.group(2))
        verse_end = int(m.group(3)) if m.group(3) else verse_start
        return surah, verse_start, verse_end
    return None, None, None


def clean_text(text):
    """Clean entry text."""
    # Remove footnote numbers (superscript-like bare numbers on their own line)
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip bare page numbers / footnote markers
        if re.match(r'^\d{1,3}$', stripped):
            continue
        if not stripped:
            if cleaned and cleaned[-1] == '':
                continue
            cleaned.append('')
            continue
        cleaned.append(line.rstrip())
    return '\n'.join(cleaned).strip()


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_file = RAW_DIR / "asbab_al_nuzul.txt"
    if not raw_file.exists():
        print(f"File not found: {raw_file}")
        return

    with open(raw_file, 'r', errors='replace') as f:
        text = f.read()

    lines = text.split('\n')

    # Find the start of content (first surah heading or first [1:...] reference)
    content_start = 0
    for i, line in enumerate(lines):
        if line.strip() == '(Al-Fâtihah)' or line.strip() == '[1:1-7]':
            # Look back for the surah heading
            content_start = i
            if i > 0 and is_surah_heading(lines[i-1]):
                content_start = i - 1
            break

    print(f"Content starts at line {content_start}")

    # Parse entries
    entries = []
    current_surah_num = None
    current_surah_name = None

    # Scan through lines finding verse markers and surah headings
    verse_pattern = re.compile(r'^\[(\d+):(\d+)(?:-(\d+))?\]\s*$')

    i = content_start
    while i < len(lines):
        line = lines[i].strip()

        # Check for surah heading
        surah_name = is_surah_heading(lines[i])
        if surah_name:
            num = normalize_surah_name(surah_name)
            if num:
                current_surah_num = num
                current_surah_name = surah_name
                print(f"  Surah {num}: {surah_name}")
            i += 1
            continue

        # Check for verse reference marker
        m = verse_pattern.match(line)
        if m:
            surah = int(m.group(1))
            verse_start = int(m.group(2))
            verse_end = int(m.group(3)) if m.group(3) else verse_start

            # Update current surah if the verse ref tells us
            if surah != current_surah_num:
                current_surah_num = surah

            # Collect text until next verse marker or surah heading
            entry_lines = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                # Stop at next verse marker
                if verse_pattern.match(next_line):
                    break
                # Stop at next surah heading
                if is_surah_heading(lines[j]):
                    sn = normalize_surah_name(is_surah_heading(lines[j]))
                    if sn:
                        break
                entry_lines.append(lines[j])
                j += 1

            entry_text = clean_text('\n'.join(entry_lines))

            if entry_text:
                entry_id = f"asbab_{surah:03d}_{verse_start:03d}"
                if verse_end != verse_start:
                    entry_id += f"_{verse_end:03d}"

                entries.append({
                    "id": entry_id,
                    "surah_number": surah,
                    "surah_name": current_surah_name or "",
                    "verse_start": verse_start,
                    "verse_end": verse_end,
                    "text": entry_text,
                    "char_count": len(entry_text),
                })

            i = j
            continue

        i += 1

    print(f"\nTotal entries: {len(entries)}")

    # Group by surah
    surahs = {}
    for entry in entries:
        s = entry["surah_number"]
        if s not in surahs:
            surahs[s] = {
                "surah_number": s,
                "surah_name": entry["surah_name"],
                "entries": [],
            }
        surahs[s]["entries"].append(entry)

    print(f"Surahs covered: {len(surahs)}")

    # Save per-surah files
    for surah_num, surah_data in sorted(surahs.items()):
        surah_file = OUTPUT_DIR / f"surah_{surah_num:03d}.json"
        with open(surah_file, 'w') as f:
            json.dump(surah_data, f, indent=2, ensure_ascii=False)

    # Build index
    index = {
        "source": "asbab_al_nuzul",
        "total_surahs": len(surahs),
        "total_entries": len(entries),
        "surahs": {
            str(s): {
                "name": d["surah_name"],
                "entries": len(d["entries"]),
                "chars": sum(e["char_count"] for e in d["entries"]),
            }
            for s, d in sorted(surahs.items())
        },
    }

    with open(OUTPUT_DIR / "_index.json", 'w') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    # Build verse map
    verse_map = {}
    for entry in entries:
        for v in range(entry["verse_start"], entry["verse_end"] + 1):
            key = f"{entry['surah_number']}:{v}"
            if key not in verse_map:
                verse_map[key] = []
            verse_map[key].append({
                "source": "asbab_al_nuzul",
                "surah": entry["surah_number"],
                "verse_start": entry["verse_start"],
                "verse_end": entry["verse_end"],
            })

    with open(OUTPUT_DIR / "_verse_map.json", 'w') as f:
        json.dump(verse_map, f, indent=2, ensure_ascii=False)

    print(f"Verse map entries: {len(verse_map)}")

    # Summary stats
    total_chars = sum(e["char_count"] for e in entries)
    print(f"Total characters: {total_chars:,}")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
