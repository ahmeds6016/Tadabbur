#!/usr/bin/env python3
"""
Build unified indexes across all parsed scholarly sources.

Creates:
- _unified_verse_map.json: surah:verse -> all source references
- _unified_index.json: master index of all sources with stats
- _topic_map.json: topic keywords -> source references
"""

import json
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INDEX_DIR = PROJECT_ROOT / "backend" / "data" / "indexes"
OUTPUT_DIR = INDEX_DIR


def load_json(path):
    """Load a JSON file, return empty dict if not found."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def build_unified_verse_map():
    """Merge verse maps from all sources into one unified map."""
    unified = defaultdict(list)

    # Thematic Commentary verse map
    thematic_vm = load_json(INDEX_DIR / "thematic_commentary" / "_verse_map.json")
    for key, refs in thematic_vm.items():
        unified[key].extend(refs)

    # Ihya verse map
    ihya_vm = load_json(INDEX_DIR / "ihya_ulum_al_din" / "_verse_map.json")
    for key, refs in ihya_vm.items():
        unified[key].extend(refs)

    # Madarij verse map
    madarij_vm = load_json(INDEX_DIR / "madarij_al_salikin" / "_verse_map.json")
    for key, refs in madarij_vm.items():
        unified[key].extend(refs)

    # Asbab al-Nuzul verse map
    asbab_vm = load_json(INDEX_DIR / "asbab_al_nuzul" / "_verse_map.json")
    for key, refs in asbab_vm.items():
        unified[key].extend(refs)

    # Riyad al-Saliheen verse map
    riyad_vm = load_json(INDEX_DIR / "riyad_al_saliheen" / "_verse_map.json")
    for key, refs in riyad_vm.items():
        unified[key].extend(refs)

    return dict(unified)


def build_topic_map():
    """Build a topic keyword -> source reference map from parsed data."""
    topic_map = defaultdict(list)

    # Thematic Commentary: use surah names and synopses as topic anchors
    thematic_idx = load_json(INDEX_DIR / "thematic_commentary" / "_index.json")
    if thematic_idx:
        for surah_num, info in thematic_idx.get("surahs", {}).items():
            # Add surah name as topic
            name = info.get("name", "").lower()
            if name:
                topic_map[name].append({
                    "source": "thematic_commentary",
                    "pointer": f"thematic → surah:{surah_num}",
                })

    # Ihya: use chapter titles as topics
    ihya_idx = load_json(INDEX_DIR / "ihya_ulum_al_din" / "_index.json")
    if ihya_idx:
        for vol_num, vol_info in ihya_idx.get("volumes", {}).items():
            for ch_num, ch_info in vol_info.get("chapters", {}).items():
                title = ch_info.get("title", "").lower()
                if title:
                    # Extract key topic words
                    words = title.split()
                    for word in words:
                        word = word.strip('.,;:!?()')
                        if len(word) > 3:
                            topic_map[word].append({
                                "source": "ihya_ulum_al_din",
                                "pointer": f"ihya → vol:{vol_num} → ch:{ch_num}",
                                "title": ch_info.get("title", ""),
                            })
                    # Also add full title
                    topic_map[title].append({
                        "source": "ihya_ulum_al_din",
                        "pointer": f"ihya → vol:{vol_num} → ch:{ch_num}",
                    })

    # Madarij: use station names as topics
    madarij_idx = load_json(INDEX_DIR / "madarij_al_salikin" / "_index.json")
    if madarij_idx:
        for vol_num, vol_info in madarij_idx.get("volumes", {}).items():
            for slug, st_info in vol_info.get("stations", {}).items():
                name = st_info.get("name", "").lower()
                if name:
                    topic_map[name].append({
                        "source": "madarij_al_salikin",
                        "pointer": f"madarij → vol:{vol_num} → station:{name.title()}",
                    })

    # Riyad al-Saliheen: use chapter titles as topics
    riyad_idx = load_json(INDEX_DIR / "riyad_al_saliheen" / "_index.json")
    if riyad_idx:
        for book_num, book_info in riyad_idx.get("books", {}).items():
            for ch_num, ch_info in book_info.get("chapters", {}).items():
                title = ch_info.get("title", "").lower()
                if title:
                    words = title.split()
                    for word in words:
                        word = word.strip('.,;:!?()')
                        if len(word) > 3:
                            topic_map[word].append({
                                "source": "riyad_al_saliheen",
                                "pointer": f"riyad → book:{book_num} → ch:{ch_num}",
                                "title": ch_info.get("title", ""),
                            })
                    topic_map[title].append({
                        "source": "riyad_al_saliheen",
                        "pointer": f"riyad → book:{book_num} → ch:{ch_num}",
                    })

    # Add direct topic entries for key Ihya/Madarij topics not captured by title parsing
    direct_entries = [
        {"keywords": ["soul", "nafs", "heart", "qalb"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:3 → ch:1", "title": "Soul and its Attributes"},
        {"keywords": ["good conduct", "akhlaq", "character"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:3 → ch:2", "title": "Good Conduct"},
        {"keywords": ["greed", "desire", "passion"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:3 → ch:3", "title": "Greed and Passion"},
        {"keywords": ["pride", "arrogance", "kibr"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:3 → ch:9", "title": "Pride and Self-Praise"},
        {"keywords": ["awakening", "heedlessness"], "source": "madarij_al_salikin", "pointer": "madarij → vol:1 → station:Awakening", "title": "Station of Awakening"},
        {"keywords": ["insight", "understanding"], "source": "madarij_al_salikin", "pointer": "madarij → vol:1 → station:Insight", "title": "Station of Insight"},
        # Ihya Vol 4 - Constructive Virtues
        {"keywords": ["repentance", "tawbah", "tauba", "turning back"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:4 → ch:1", "title": "Repentance (Tauba)"},
        {"keywords": ["patience", "gratitude", "gratefulness", "sabr", "shukr"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:4 → ch:2", "title": "Patience and Gratefulness"},
        {"keywords": ["fear", "hope", "khawf", "raja"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:4 → ch:3", "title": "Fear and Hope"},
        {"keywords": ["poverty", "renunciation", "zuhd", "abstinence"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:4 → ch:4", "title": "Poverty and Renunciation"},
        {"keywords": ["tawhid", "tauhid", "tawakkul", "trust", "reliance"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:4 → ch:5", "title": "Tauhid and Tawakkal"},
        {"keywords": ["love", "attachment", "devotion", "mahabbah"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:4 → ch:6", "title": "Love and Attachment"},
        {"keywords": ["intention", "niyyah", "will"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:4 → ch:7", "title": "Will or Intention"},
        {"keywords": ["meditation", "introspection", "muraqaba", "muhasaba"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:4 → ch:8", "title": "Meditation and Introspection"},
        {"keywords": ["pondering", "contemplation", "tafakkur"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:4 → ch:9", "title": "Pondering over Good"},
        {"keywords": ["death", "afterlife", "akhirah", "hereafter"], "source": "ihya_ulum_al_din", "pointer": "ihya → vol:4 → ch:10", "title": "Death and Subsequent Events"},
    ]
    for entry in direct_entries:
        for kw in entry["keywords"]:
            topic_map[kw].append({
                "source": entry["source"],
                "pointer": entry["pointer"],
                "title": entry["title"],
            })

    # Add common topic aliases
    topic_aliases = {
        "prayer": ["salah", "worship", "prayer"],
        "patience": ["patience", "sabr"],
        "gratitude": ["gratitude", "thankfulness", "shukr"],
        "repentance": ["repentance", "tawbah", "turning"],
        "knowledge": ["knowledge", "learning", "ilm"],
        "anger": ["anger", "hatred", "envy"],
        "tongue": ["tongue", "speech", "backbiting"],
        "wealth": ["wealth", "miserliness", "poverty"],
        "fear": ["fear", "hope", "khawf"],
        "love": ["love", "devotion", "desire"],
        "fasting": ["fasting", "ramadan", "sawm"],
        "pilgrimage": ["pilgrimage", "hajj"],
        "sincerity": ["sincerity", "ikhlas", "purification"],
        "soul": ["soul", "nafs", "heart", "qalb"],
        "trust": ["trust", "reliance", "tawakkul"],
        "humility": ["humility", "meekness", "modesty"],
    }

    for canonical, aliases in topic_aliases.items():
        all_refs = []
        for alias in aliases:
            if alias in topic_map:
                all_refs.extend(topic_map[alias])
        if all_refs:
            for alias in aliases:
                topic_map[alias] = all_refs

    return dict(topic_map)


def build_unified_index():
    """Build master index with stats from all sources."""
    index = {
        "sources": {},
        "totals": {
            "verse_map_entries": 0,
            "topic_map_entries": 0,
        },
    }

    # Thematic Commentary
    thematic_idx = load_json(INDEX_DIR / "thematic_commentary" / "_index.json")
    if thematic_idx:
        total_sections = sum(
            s.get("sections", 0)
            for s in thematic_idx.get("surahs", {}).values()
        )
        total_chars = sum(
            s.get("chars", 0)
            for s in thematic_idx.get("surahs", {}).values()
        )
        index["sources"]["thematic_commentary"] = {
            "description": "A Thematic Commentary on the Qur'an (Shaykh Muhammad al-Ghazali)",
            "type": "surah_level",
            "surahs": thematic_idx.get("total_surahs", 0),
            "sections": total_sections,
            "total_chars": total_chars,
            "app_tabs": ["tafsir", "lessons"],
        }

    # Ihya Ulum al-Din
    ihya_idx = load_json(INDEX_DIR / "ihya_ulum_al_din" / "_index.json")
    if ihya_idx:
        total_chapters = sum(
            len(v.get("chapters", {}))
            for v in ihya_idx.get("volumes", {}).values()
        )
        total_chars = sum(
            ch.get("chars", 0)
            for v in ihya_idx.get("volumes", {}).values()
            for ch in v.get("chapters", {}).values()
        )
        index["sources"]["ihya_ulum_al_din"] = {
            "description": "Ihya Ulum al-Din (Imam al-Ghazali, Vols 1-4)",
            "type": "topic_level",
            "volumes": ihya_idx.get("total_volumes", 0),
            "chapters": total_chapters,
            "total_chars": total_chars,
            "app_tabs": ["lessons"],
        }

    # Madarij al-Salikin
    madarij_idx = load_json(INDEX_DIR / "madarij_al_salikin" / "_index.json")
    if madarij_idx:
        total_stations = sum(
            len(v.get("stations", {}))
            for v in madarij_idx.get("volumes", {}).values()
        )
        total_chars = sum(
            st.get("chars", 0)
            for v in madarij_idx.get("volumes", {}).values()
            for st in v.get("stations", {}).values()
        )
        index["sources"]["madarij_al_salikin"] = {
            "description": "Madarij al-Salikin (Ibn Qayyim, Vols 1-2)",
            "type": "station_level",
            "volumes": madarij_idx.get("total_volumes", 0),
            "stations": total_stations,
            "total_chars": total_chars,
            "app_tabs": ["lessons"],
        }

    # Asbab al-Nuzul
    asbab_idx = load_json(INDEX_DIR / "asbab_al_nuzul" / "_index.json")
    if asbab_idx:
        total_chars = sum(
            s.get("chars", 0)
            for s in asbab_idx.get("surahs", {}).values()
        )
        index["sources"]["asbab_al_nuzul"] = {
            "description": "Asbab al-Nuzul (Al-Wahidi)",
            "type": "verse_level",
            "surahs": asbab_idx.get("total_surahs", 0),
            "entries": asbab_idx.get("total_entries", 0),
            "total_chars": total_chars,
            "app_tabs": ["tafsir"],
        }
    else:
        index["sources"]["asbab_al_nuzul"] = {
            "description": "Asbab al-Nuzul (Al-Wahidi)",
            "type": "verse_level",
            "status": "not_indexed",
            "app_tabs": ["tafsir"],
        }

    # Riyad al-Saliheen
    riyad_idx = load_json(INDEX_DIR / "riyad_al_saliheen" / "_index.json")
    if riyad_idx:
        total_hadith = sum(
            ch.get("hadith_count", 0)
            for b in riyad_idx.get("books", {}).values()
            for ch in b.get("chapters", {}).values()
        )
        total_chars = sum(
            ch.get("chars", 0)
            for b in riyad_idx.get("books", {}).values()
            for ch in b.get("chapters", {}).values()
        )
        index["sources"]["riyad_al_saliheen"] = {
            "description": "Riyad al-Saliheen (Imam al-Nawawi)",
            "type": "hadith_collection",
            "books": riyad_idx.get("total_books", 0),
            "chapters": riyad_idx.get("total_chapters", 0),
            "hadith": total_hadith,
            "total_chars": total_chars,
            "app_tabs": ["hadith", "lessons"],
        }
    else:
        index["sources"]["riyad_al_saliheen"] = {
            "description": "Riyad al-Saliheen (Imam al-Nawawi)",
            "type": "hadith_collection",
            "status": "not_indexed",
            "note": "PDF is scanned image - requires OCR",
            "app_tabs": ["hadith", "lessons"],
        }

    return index


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build unified verse map
    print("Building unified verse map...")
    verse_map = build_unified_verse_map()
    with open(OUTPUT_DIR / "_unified_verse_map.json", 'w') as f:
        json.dump(verse_map, f, indent=2, ensure_ascii=False)
    print(f"  Verse map entries: {len(verse_map)}")

    # Count coverage
    surahs_covered = set()
    for key in verse_map:
        parts = key.split(':')
        if len(parts) == 2:
            try:
                surahs_covered.add(int(parts[0]))
            except ValueError:
                pass
    print(f"  Surahs with at least one reference: {len(surahs_covered)}")

    # Build topic map
    print("\nBuilding topic map...")
    topic_map = build_topic_map()
    with open(OUTPUT_DIR / "_topic_map.json", 'w') as f:
        json.dump(topic_map, f, indent=2, ensure_ascii=False)
    print(f"  Topic entries: {len(topic_map)}")

    # Build unified index
    print("\nBuilding unified index...")
    unified_index = build_unified_index()
    unified_index["totals"]["verse_map_entries"] = len(verse_map)
    unified_index["totals"]["topic_map_entries"] = len(topic_map)
    with open(OUTPUT_DIR / "_unified_index.json", 'w') as f:
        json.dump(unified_index, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*50}")
    print("UNIFIED INDEX SUMMARY")
    print(f"{'='*50}")
    for src_key, src_info in unified_index["sources"].items():
        status = src_info.get("status", "indexed")
        print(f"  {src_key}: {status}")
        if status != "not_indexed":
            print(f"    Chars: {src_info.get('total_chars', 0):,}")
    print(f"\n  Total verse map entries: {len(verse_map)}")
    print(f"  Total topic map entries: {len(topic_map)}")
    print(f"  Surahs covered: {len(surahs_covered)}/114")
    print(f"\n  Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
