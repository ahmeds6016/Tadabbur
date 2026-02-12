"""
Scholarly Source Retrieval Service.

Provides retrieval of context from indexed scholarly sources:
- Asbab al-Nuzul (Al-Wahidi) — verse-level context of revelation
- Thematic Commentary (al-Ghazali) — surah-level thematic overviews
- Ihya Ulum al-Din (al-Ghazali) — spiritual/ethical teachings
- Madarij al-Salikin (Ibn Qayyim) — stations of spiritual development
- Riyad al-Saliheen (al-Nawawi) — hadith collection by topic

Used by the prompt builder to inject scholarly context into AI responses.
"""

import json
import os
from pathlib import Path
from functools import lru_cache

# Resolve paths
_SCRIPT_DIR = Path(__file__).resolve().parent
_INDEX_DIR = _SCRIPT_DIR.parent / "data" / "indexes"

# Maximum chars of scholarly context to inject into prompt
# (to avoid exceeding model token limits)
MAX_ASBAB_CHARS = 2000
MAX_THEMATIC_CHARS = 3000
MAX_IHYA_CHARS = 2000
MAX_MADARIJ_CHARS = 2000
MAX_RIYAD_CHARS = 2000
MAX_TOTAL_SCHOLARLY_CHARS = 8000


@lru_cache(maxsize=1)
def _load_unified_verse_map():
    """Load the unified verse map (cached in memory)."""
    path = _INDEX_DIR / "_unified_verse_map.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


@lru_cache(maxsize=1)
def _load_topic_map():
    """Load the topic map (cached in memory)."""
    path = _INDEX_DIR / "_topic_map.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


@lru_cache(maxsize=128)
def _load_thematic_surah(surah_number):
    """Load a single surah's thematic commentary data."""
    path = _INDEX_DIR / "thematic_commentary" / f"surah_{surah_number:03d}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


@lru_cache(maxsize=8)
def _load_ihya_volume(vol_num):
    """Load a single Ihya volume's data."""
    path = _INDEX_DIR / "ihya_ulum_al_din" / f"vol_{vol_num}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


@lru_cache(maxsize=4)
def _load_madarij_volume(vol_num):
    """Load a single Madarij volume's data."""
    path = _INDEX_DIR / "madarij_al_salikin" / f"vol_{vol_num}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


@lru_cache(maxsize=128)
def _load_asbab_surah(surah_number):
    """Load a single surah's Asbab al-Nuzul data."""
    path = _INDEX_DIR / "asbab_al_nuzul" / f"surah_{surah_number:03d}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


@lru_cache(maxsize=1)
def _load_riyad_index():
    """Load Riyad al-Saliheen index (cached in memory)."""
    path = _INDEX_DIR / "riyad_al_saliheen" / "_index.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


@lru_cache(maxsize=20)
def _load_riyad_chapter(book_num, ch_num):
    """Load a Riyad al-Saliheen chapter."""
    path = _INDEX_DIR / "riyad_al_saliheen" / f"book_{book_num:02d}_ch_{ch_num:03d}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def get_asbab_context(surah_number, verse_start=None, verse_end=None):
    """Get Asbab al-Nuzul (context of revelation) for a verse."""
    data = _load_asbab_surah(surah_number)
    if not data:
        return None

    entries = data.get("entries", [])
    if not entries:
        return None

    matched = []
    if verse_start is not None:
        target_verses = set(range(verse_start, (verse_end or verse_start) + 1))
        for entry in entries:
            entry_verses = set(range(entry["verse_start"], entry["verse_end"] + 1))
            if entry_verses & target_verses:
                matched.append(entry)
    else:
        # No specific verse — return first entry
        matched = entries[:1]

    if not matched:
        return None

    results = []
    total_chars = 0
    for entry in matched[:3]:  # Limit to 3 entries
        text = entry.get("text", "")
        if total_chars + len(text) > MAX_ASBAB_CHARS:
            text = text[:MAX_ASBAB_CHARS - total_chars] + "..."
        results.append({
            "verse_start": entry["verse_start"],
            "verse_end": entry["verse_end"],
            "text": text,
        })
        total_chars += len(text)
        if total_chars >= MAX_ASBAB_CHARS:
            break

    return {
        "source": "Asbab al-Nuzul (Al-Wahidi)",
        "entries": results,
    }


def get_riyad_context_by_verse(surah_number, verse_number):
    """Get Riyad al-Saliheen hadith related to a specific verse."""
    verse_map = _load_unified_verse_map()
    key = f"{surah_number}:{verse_number}"
    refs = verse_map.get(key, [])

    riyad_refs = [r for r in refs if r.get("source") == "riyad_al_saliheen"]
    if not riyad_refs:
        return None

    results = []
    for ref in riyad_refs[:2]:
        ch_data = _load_riyad_chapter(ref.get("book", 1), ref.get("chapter", 1))
        if ch_data and ch_data.get("hadith_entries"):
            for h in ch_data["hadith_entries"][:2]:
                text = h.get("text", "")
                if len(text) > MAX_RIYAD_CHARS:
                    text = text[:MAX_RIYAD_CHARS] + "..."
                results.append({
                    "chapter_title": ch_data.get("chapter_title", ""),
                    "hadith_number": h.get("hadith_number", ""),
                    "narrator": h.get("narrator", ""),
                    "text": text,
                    "source_collection": h.get("source_collection", ""),
                })

    if not results:
        return None

    return {
        "source": "Riyad al-Saliheen (Imam al-Nawawi)",
        "entries": results,
    }


def get_riyad_context_by_topic(topic_keywords):
    """Get Riyad hadith related to topic keywords."""
    topic_map = _load_topic_map()

    matched_refs = []
    for keyword in topic_keywords:
        keyword_lower = keyword.lower().strip()
        refs = topic_map.get(keyword_lower, [])
        for ref in refs:
            if ref.get("source") == "riyad_al_saliheen":
                matched_refs.append(ref)

    if not matched_refs:
        return None

    seen = set()
    unique_refs = []
    for ref in matched_refs:
        pointer = ref.get("pointer", "")
        if pointer not in seen:
            seen.add(pointer)
            unique_refs.append(ref)

    results = []
    for ref in unique_refs[:2]:
        pointer = ref.get("pointer", "")
        parts = pointer.split(" → ")
        book_num = None
        ch_num = None
        for part in parts:
            if part.startswith("book:"):
                book_num = int(part.split(":")[1])
            elif part.startswith("ch:"):
                ch_num = int(part.split(":")[1])

        if book_num and ch_num:
            ch_data = _load_riyad_chapter(book_num, ch_num)
            if ch_data and ch_data.get("hadith_entries"):
                h = ch_data["hadith_entries"][0]
                text = h.get("text", "")
                if len(text) > MAX_RIYAD_CHARS:
                    text = text[:MAX_RIYAD_CHARS] + "..."
                results.append({
                    "chapter_title": ch_data.get("chapter_title", ""),
                    "hadith_number": h.get("hadith_number", ""),
                    "text": text,
                })

    if not results:
        return None

    return {
        "source": "Riyad al-Saliheen (Imam al-Nawawi)",
        "entries": results,
    }


def get_thematic_context(surah_number, verse_start=None, verse_end=None):
    """
    Get thematic commentary context for a surah.

    Returns the synopsis and relevant sections based on verse references.
    """
    data = _load_thematic_surah(surah_number)
    if not data:
        return None

    result = {
        "source": "A Thematic Commentary on the Qur'an (Shaykh Muhammad al-Ghazali)",
        "surah_name": data.get("surah_name", ""),
        "synopsis": data.get("synopsis", ""),
        "sections": [],
    }

    # If specific verses requested, find sections containing those verse refs
    if verse_start is not None:
        target_verses = set(range(verse_start, (verse_end or verse_start) + 1))
        for section in data.get("sections", []):
            section_verses = set()
            for ref in section.get("verse_refs", []):
                if ref["type"] == "same_surah":
                    verse_str = ref["verse"]
                    if "-" in verse_str:
                        parts = verse_str.split("-")
                        try:
                            section_verses.update(range(int(parts[0]), int(parts[1]) + 1))
                        except ValueError:
                            pass
                    else:
                        try:
                            section_verses.add(int(verse_str))
                        except ValueError:
                            pass

            if section_verses & target_verses:
                text = section.get("text", "")
                if len(text) > MAX_THEMATIC_CHARS:
                    text = text[:MAX_THEMATIC_CHARS] + "..."
                result["sections"].append({
                    "section_index": section["section_index"],
                    "text": text,
                })
    else:
        # No specific verses — return synopsis + first section
        if data.get("sections"):
            first_sec = data["sections"][0]
            text = first_sec.get("text", "")
            if len(text) > MAX_THEMATIC_CHARS:
                text = text[:MAX_THEMATIC_CHARS] + "..."
            result["sections"].append({
                "section_index": 0,
                "text": text,
            })

    return result


def get_ihya_context_by_verse(surah_number, verse_number):
    """Get Ihya Ulum al-Din content related to a specific verse."""
    verse_map = _load_unified_verse_map()
    key = f"{surah_number}:{verse_number}"
    refs = verse_map.get(key, [])

    ihya_refs = [r for r in refs if r.get("source") == "ihya_ulum_al_din"]
    if not ihya_refs:
        return None

    results = []
    for ref in ihya_refs[:3]:  # Limit to 3 most relevant
        vol_data = _load_ihya_volume(ref["volume"])
        if not vol_data:
            continue

        for ch in vol_data.get("chapters", []):
            if ch["chapter_number"] == ref.get("chapter"):
                for sec in ch.get("sections", []):
                    if sec["section_title"] == ref.get("section"):
                        text = sec.get("text", "")
                        if len(text) > MAX_IHYA_CHARS:
                            text = text[:MAX_IHYA_CHARS] + "..."
                        results.append({
                            "volume": ref["volume"],
                            "chapter": ch["chapter_title"],
                            "section": sec["section_title"],
                            "text": text,
                        })

    if not results:
        return None

    return {
        "source": "Ihya Ulum al-Din (Imam al-Ghazali)",
        "entries": results,
    }


def get_ihya_context_by_topic(topic_keywords):
    """Get Ihya content related to topic keywords."""
    topic_map = _load_topic_map()

    matched_refs = []
    for keyword in topic_keywords:
        keyword_lower = keyword.lower().strip()
        refs = topic_map.get(keyword_lower, [])
        for ref in refs:
            if ref.get("source") == "ihya_ulum_al_din":
                matched_refs.append(ref)

    if not matched_refs:
        return None

    # Deduplicate by pointer
    seen = set()
    unique_refs = []
    for ref in matched_refs:
        pointer = ref.get("pointer", "")
        if pointer not in seen:
            seen.add(pointer)
            unique_refs.append(ref)

    # Resolve pointers to actual text
    results = []
    for ref in unique_refs[:2]:  # Limit to 2
        pointer = ref.get("pointer", "")
        # Parse pointer: "ihya → vol:N → ch:M"
        parts = pointer.split(" → ")
        vol_num = None
        ch_num = None
        for part in parts:
            if part.startswith("vol:"):
                vol_num = int(part.split(":")[1])
            elif part.startswith("ch:"):
                ch_num = int(part.split(":")[1])

        if vol_num and ch_num:
            vol_data = _load_ihya_volume(vol_num)
            if vol_data:
                for ch in vol_data.get("chapters", []):
                    if ch["chapter_number"] == ch_num:
                        # Get first section text
                        if ch.get("sections"):
                            text = ch["sections"][0].get("text", "")
                            if len(text) > MAX_IHYA_CHARS:
                                text = text[:MAX_IHYA_CHARS] + "..."
                            results.append({
                                "volume": vol_num,
                                "chapter": ch["chapter_title"],
                                "text": text,
                            })
                        break

    if not results:
        return None

    return {
        "source": "Ihya Ulum al-Din (Imam al-Ghazali)",
        "entries": results,
    }


def get_madarij_context_by_verse(surah_number, verse_number):
    """Get Madarij al-Salikin content related to a specific verse."""
    verse_map = _load_unified_verse_map()
    key = f"{surah_number}:{verse_number}"
    refs = verse_map.get(key, [])

    madarij_refs = [r for r in refs if r.get("source") == "madarij_al_salikin"]
    if not madarij_refs:
        return None

    results = []
    for ref in madarij_refs[:2]:  # Limit to 2
        vol_data = _load_madarij_volume(ref["volume"])
        if not vol_data:
            continue

        for st in vol_data.get("stations", []):
            if st["station_name"] == ref.get("station"):
                # Get the first subsection text
                if st.get("subsections"):
                    text = st["subsections"][0].get("text", "")
                    if len(text) > MAX_MADARIJ_CHARS:
                        text = text[:MAX_MADARIJ_CHARS] + "..."
                    results.append({
                        "volume": ref["volume"],
                        "station": st["station_name"],
                        "text": text,
                    })
                break

    if not results:
        return None

    return {
        "source": "Madarij al-Salikin (Ibn Qayyim al-Jawziyyah)",
        "entries": results,
    }


def get_madarij_context_by_topic(topic_keywords):
    """Get Madarij content related to topic keywords."""
    topic_map = _load_topic_map()

    matched_refs = []
    for keyword in topic_keywords:
        keyword_lower = keyword.lower().strip()
        refs = topic_map.get(keyword_lower, [])
        for ref in refs:
            if ref.get("source") == "madarij_al_salikin":
                matched_refs.append(ref)

    if not matched_refs:
        return None

    seen = set()
    unique_refs = []
    for ref in matched_refs:
        pointer = ref.get("pointer", "")
        if pointer not in seen:
            seen.add(pointer)
            unique_refs.append(ref)

    results = []
    for ref in unique_refs[:2]:
        pointer = ref.get("pointer", "")
        # Parse: "madarij → vol:N → station:Name"
        parts = pointer.split(" → ")
        vol_num = None
        station_name = None
        for part in parts:
            if part.startswith("vol:"):
                vol_num = int(part.split(":")[1])
            elif part.startswith("station:"):
                station_name = part.split(":")[1]

        if vol_num and station_name:
            vol_data = _load_madarij_volume(vol_num)
            if vol_data:
                for st in vol_data.get("stations", []):
                    if st["station_name"].lower() == station_name.lower():
                        if st.get("subsections"):
                            text = st["subsections"][0].get("text", "")
                            if len(text) > MAX_MADARIJ_CHARS:
                                text = text[:MAX_MADARIJ_CHARS] + "..."
                            results.append({
                                "volume": vol_num,
                                "station": st["station_name"],
                                "text": text,
                            })
                        break

    if not results:
        return None

    return {
        "source": "Madarij al-Salikin (Ibn Qayyim al-Jawziyyah)",
        "entries": results,
    }


def get_relevant_scholarly_context(surah_number=None, verse_start=None, verse_end=None,
                                    topic_keywords=None):
    """
    Main entry point: get all relevant scholarly context for a query.

    Returns a formatted string ready to inject into the AI prompt.
    """
    context_parts = []
    total_chars = 0

    # 0. Asbab al-Nuzul (context of revelation — most specific, goes first)
    if surah_number and verse_start:
        asbab = get_asbab_context(surah_number, verse_start, verse_end)
        if asbab and asbab.get("entries"):
            section_text = ""
            for entry in asbab["entries"]:
                verse_ref = f"{entry['verse_start']}"
                if entry['verse_end'] != entry['verse_start']:
                    verse_ref += f"-{entry['verse_end']}"
                section_text += f"**Verse {verse_ref}:** {entry.get('text', '')}\n\n"

            if section_text.strip():
                header = "### Context of Revelation (Asbab al-Nuzul)\n"
                header += f"*Source: {asbab['source']}*\n\n"
                entry_text = header + section_text.strip()
                if total_chars + len(entry_text) <= MAX_TOTAL_SCHOLARLY_CHARS:
                    context_parts.append(entry_text)
                    total_chars += len(entry_text)

    # 1. Thematic Commentary (surah-level)
    if surah_number:
        thematic = get_thematic_context(surah_number, verse_start, verse_end)
        if thematic:
            section_text = ""
            if thematic.get("synopsis"):
                section_text += f"**Thematic Overview:** {thematic['synopsis']}\n\n"
            for sec in thematic.get("sections", []):
                section_text += sec.get("text", "") + "\n\n"

            if section_text.strip():
                header = f"### Thematic Commentary — {thematic.get('surah_name', 'Surah ' + str(surah_number))}\n"
                header += f"*Source: {thematic['source']}*\n\n"
                entry = header + section_text.strip()
                if total_chars + len(entry) <= MAX_TOTAL_SCHOLARLY_CHARS:
                    context_parts.append(entry)
                    total_chars += len(entry)

    # 2. Ihya Ulum al-Din (verse-based or topic-based)
    ihya_context = None
    if surah_number and verse_start:
        ihya_context = get_ihya_context_by_verse(surah_number, verse_start)
    if not ihya_context and topic_keywords:
        ihya_context = get_ihya_context_by_topic(topic_keywords)

    if ihya_context and total_chars < MAX_TOTAL_SCHOLARLY_CHARS:
        section_text = ""
        for entry in ihya_context.get("entries", []):
            section_text += f"**{entry.get('chapter', 'Chapter')}**\n"
            section_text += entry.get("text", "") + "\n\n"

        if section_text.strip():
            header = f"### Spiritual Teaching — Ihya Ulum al-Din\n"
            header += f"*Source: {ihya_context['source']}*\n\n"
            entry_text = header + section_text.strip()
            remaining = MAX_TOTAL_SCHOLARLY_CHARS - total_chars
            if len(entry_text) > remaining:
                entry_text = entry_text[:remaining] + "..."
            context_parts.append(entry_text)
            total_chars += len(entry_text)

    # 3. Madarij al-Salikin (verse-based or topic-based)
    madarij_context = None
    if surah_number and verse_start:
        madarij_context = get_madarij_context_by_verse(surah_number, verse_start)
    if not madarij_context and topic_keywords:
        madarij_context = get_madarij_context_by_topic(topic_keywords)

    if madarij_context and total_chars < MAX_TOTAL_SCHOLARLY_CHARS:
        section_text = ""
        for entry in madarij_context.get("entries", []):
            section_text += f"**Station of {entry.get('station', 'Unknown')}**\n"
            section_text += entry.get("text", "") + "\n\n"

        if section_text.strip():
            header = f"### Spiritual Development — Madarij al-Salikin\n"
            header += f"*Source: {madarij_context['source']}*\n\n"
            entry_text = header + section_text.strip()
            remaining = MAX_TOTAL_SCHOLARLY_CHARS - total_chars
            if len(entry_text) > remaining:
                entry_text = entry_text[:remaining] + "..."
            context_parts.append(entry_text)
            total_chars += len(entry_text)

    # 4. Riyad al-Saliheen (hadith — verse-based or topic-based)
    riyad_context = None
    if surah_number and verse_start:
        riyad_context = get_riyad_context_by_verse(surah_number, verse_start)
    if not riyad_context and topic_keywords:
        riyad_context = get_riyad_context_by_topic(topic_keywords)

    if riyad_context and total_chars < MAX_TOTAL_SCHOLARLY_CHARS:
        section_text = ""
        for entry in riyad_context.get("entries", []):
            h_num = entry.get("hadith_number", "")
            narrator = entry.get("narrator", "")
            prefix = f"**Hadith #{h_num}**" if h_num else "**Hadith**"
            if narrator:
                prefix += f" (narrated by {narrator})"
            section_text += f"{prefix}\n{entry.get('text', '')}\n\n"

        if section_text.strip():
            header = "### Related Hadith — Riyad al-Saliheen\n"
            header += f"*Source: {riyad_context['source']}*\n\n"
            entry_text = header + section_text.strip()
            remaining = MAX_TOTAL_SCHOLARLY_CHARS - total_chars
            if len(entry_text) > remaining:
                entry_text = entry_text[:remaining] + "..."
            context_parts.append(entry_text)
            total_chars += len(entry_text)

    if not context_parts:
        return ""

    # Build the full scholarly context block
    result = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    result += "ADDITIONAL SCHOLARLY SOURCES (Use to enrich Lessons & context)\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    result += "\n\n".join(context_parts)
    result += "\n\n"
    result += "INSTRUCTIONS FOR SCHOLARLY SOURCES:\n"
    result += "- Use Asbab al-Nuzul to explain WHY a verse was revealed (historical context)\n"
    result += "- Use thematic commentary for surah-level context and themes\n"
    result += "- Use Ihya and Madarij for spiritual lessons and practical applications\n"
    result += "- Use Riyad al-Saliheen hadith to support lessons with prophetic traditions\n"
    result += "- When citing, attribute clearly: 'Al-Wahidi narrates...', 'As al-Ghazali notes...', 'Ibn Qayyim explains...', 'In Riyad al-Saliheen...'\n"
    result += "- These sources complement (not replace) the classical tafsir from Ibn Kathir and al-Qurtubi\n"

    return result


def extract_topic_keywords_from_query(query):
    """Extract potential topic keywords from a user query for topic-based retrieval."""
    # Common Islamic topics that map to our indexed sources
    topic_terms = {
        "patience", "sabr", "gratitude", "shukr", "repentance", "tawbah",
        "prayer", "salah", "fasting", "sawm", "knowledge", "ilm",
        "anger", "envy", "hatred", "tongue", "backbiting", "wealth",
        "poverty", "fear", "hope", "love", "devotion", "trust",
        "reliance", "tawakkul", "humility", "meekness", "soul", "nafs",
        "heart", "qalb", "purification", "sincerity", "ikhlas",
        "pilgrimage", "hajj", "zakat", "charity", "marriage",
        "discipline", "watchfulness", "remembrance", "dhikr",
        "renunciation", "contentment", "submission", "worship",
        "pride", "arrogance", "greed", "desire", "fleeing",
    }

    query_lower = query.lower()
    found = []
    for term in topic_terms:
        if term in query_lower:
            found.append(term)

    return found if found else None


def get_scholarly_sources_metadata(surah_number=None, verse_start=None, verse_end=None,
                                   topic_keywords=None):
    """
    Return lightweight metadata about which scholarly sources have data for this query.
    Used by frontend to show source attribution badges.
    """
    sources = []

    # Asbab al-Nuzul
    if surah_number and verse_start:
        asbab = get_asbab_context(surah_number, verse_start, verse_end)
        if asbab and asbab.get("entries"):
            sources.append({
                "key": "asbab",
                "name": "Asbab al-Nuzul",
                "author": "Al-Wahidi",
                "type": "Context of Revelation",
            })

    # Thematic Commentary
    if surah_number:
        thematic = get_thematic_context(surah_number, verse_start, verse_end)
        if thematic and thematic.get("synopsis"):
            sources.append({
                "key": "thematic",
                "name": "Thematic Commentary",
                "author": "Shaykh al-Ghazali",
                "type": "Surah Commentary",
            })

    # Ihya Ulum al-Din
    ihya = None
    if surah_number and verse_start:
        ihya = get_ihya_context_by_verse(surah_number, verse_start)
    if not ihya and topic_keywords:
        ihya = get_ihya_context_by_topic(topic_keywords)
    if ihya and ihya.get("entries"):
        sources.append({
            "key": "ihya",
            "name": "Ihya Ulum al-Din",
            "author": "Imam al-Ghazali",
            "type": "Spiritual Teaching",
        })

    # Madarij al-Salikin
    madarij = None
    if surah_number and verse_start:
        madarij = get_madarij_context_by_verse(surah_number, verse_start)
    if not madarij and topic_keywords:
        madarij = get_madarij_context_by_topic(topic_keywords)
    if madarij and madarij.get("entries"):
        sources.append({
            "key": "madarij",
            "name": "Madarij al-Salikin",
            "author": "Ibn Qayyim",
            "type": "Spiritual Development",
        })

    # Riyad al-Saliheen
    riyad = None
    if surah_number and verse_start:
        riyad = get_riyad_context_by_verse(surah_number, verse_start)
    if not riyad and topic_keywords:
        riyad = get_riyad_context_by_topic(topic_keywords)
    if riyad and riyad.get("entries"):
        sources.append({
            "key": "riyad",
            "name": "Riyad al-Saliheen",
            "author": "Imam al-Nawawi",
            "type": "Hadith Collection",
        })

    return sources
