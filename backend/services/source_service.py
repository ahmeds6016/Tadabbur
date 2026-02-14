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
MAX_IHYA_CHARS = 3000
MAX_MADARIJ_CHARS = 3000
MAX_RIYAD_CHARS = 2500
MAX_TOTAL_SCHOLARLY_CHARS = 14000


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


# ═══════════════════════════════════════════════════════════════════
# TWO-STAGE SCHOLARLY RETRIEVAL: Plan → Fetch → Answer
# ═══════════════════════════════════════════════════════════════════

# --- Source Catalog (Minimap) for the planning model ---

SCHOLARLY_SOURCE_CATALOG = """
SCHOLARLY SOURCE CATALOG
========================
You have access to 5 indexed scholarly sources. For each, decide if it is
relevant to the queried verse and output pointers to fetch specific content.

━━━ SOURCE 1: ASBAB AL-NUZUL (Al-Wahidi) ━━━
Purpose: Historical context of revelation — WHY a specific verse was revealed.
Coverage: 83 of 114 surahs; 446 verse-level entries (not every verse has one).
Pointer format: asbab:surah=N:verse=V
Rule: ALWAYS emit this pointer for the queried verse. If no entry exists,
  the system returns empty — no harm done.

━━━ SOURCE 2: THEMATIC COMMENTARY (Shaykh Muhammad al-Ghazali) ━━━
Purpose: Surah-level thematic overview explaining the surah's major themes.
Coverage: All 114 surahs. Each surah has 1-5 sections (section 0 is the main one).
Pointer format: thematic:surah=N:section=S
Rule: ALWAYS emit thematic:surah=N:section=0 for the queried surah.

━━━ SOURCE 3: IHYA ULUM AL-DIN (Imam al-Ghazali) ━━━
Purpose: Spiritual and ethical teachings organized by topic.
Structure: 4 volumes → chapters → sections.
Pointer format: ihya:vol=V:ch=C:sec=0

ROUTING TABLE (use ONLY these mappings):
  Vol 1 — Acts of Worship:
    prayer/salah → ihya:vol=1:ch=4:sec=0
    fasting/sawm → ihya:vol=1:ch=6:sec=0
    pilgrimage/hajj → ihya:vol=1:ch=7:sec=0
    quran/recitation → ihya:vol=1:ch=8:sec=0
    remembrance/dhikr → ihya:vol=1:ch=9:sec=0
  Vol 2 — Worldly Usages:
    marriage/spouse → ihya:vol=2:ch=2:sec=0
    halal/haram → ihya:vol=2:ch=4:sec=0
    brotherhood/friendship → ihya:vol=2:ch=5:sec=0
  Vol 3 — Destructive Evils:
    soul/nafs/heart → ihya:vol=3:ch=1:sec=0
    conduct/character → ihya:vol=3:ch=2:sec=0
    greed/desire → ihya:vol=3:ch=3:sec=0
    tongue/speech/backbiting → ihya:vol=3:ch=4:sec=0
    anger/envy/hatred → ihya:vol=3:ch=5:sec=0
    wealth/miserliness → ihya:vol=3:ch=7:sec=0
    pride/arrogance → ihya:vol=3:ch=9:sec=0
  Vol 4 — Constructive Virtues:
    repentance/tawbah → ihya:vol=4:ch=1:sec=0
    patience/sabr/gratitude/shukr → ihya:vol=4:ch=2:sec=0
    fear/hope/khawf/raja → ihya:vol=4:ch=3:sec=0
    poverty/renunciation/zuhd → ihya:vol=4:ch=4:sec=0
    trust/tawakkul/reliance → ihya:vol=4:ch=5:sec=0
    love/devotion → ihya:vol=4:ch=6:sec=0
    intention/niyyah → ihya:vol=4:ch=7:sec=0
    meditation/introspection → ihya:vol=4:ch=8:sec=0
    death/afterlife/hereafter → ihya:vol=4:ch=10:sec=0

Rule: ONLY emit if a keyword from the routing table appears in the verse text
  or Ibn Kathir themes. Use the EXACT pointer from the table.

━━━ SOURCE 4: MADARIJ AL-SALIKIN (Ibn Qayyim al-Jawziyyah) ━━━
Purpose: Spiritual stations/ranks on the path to God.
Structure: 2 volumes → named stations → subsections.
Pointer format: madarij:vol=V:station=SLUG:sub=0

STATIONS (use ONLY these slugs):
  Vol 1: awakening, insight, purpose, resolve, reflection,
         annihilation, self_reckoning, repentance
  Vol 2: oft_returning, remembrance, holding_fast, fleeing,
         disciplining, listening, grief, fear, trembling,
         humility, meekness, renunciation, scrupulousness,
         devotion, hope, desire, shepherding, watchfulness,
         purification, refinement_and_correction, standing_firm,
         trusting_reliance, relegation, trust_in_god, submission,
         patience, joyful_contentment

Rule: ONLY emit if the verse discusses a spiritual state matching a station
  above. Max 2 pointers.

━━━ SOURCE 5: RIYAD AL-SALIHEEN (Imam al-Nawawi) ━━━
Purpose: Authenticated hadith organized by moral/ethical topics.
Structure: 687 chapters → hadith entries.
Pointer format: riyad:book=1:ch=C:hadith=0

ROUTING TABLE (use ONLY these mappings):
  sincerity/intention → riyad:book=1:ch=1:hadith=0
  repentance/tawbah → riyad:book=1:ch=2:hadith=0
  patience/sabr → riyad:book=1:ch=3:hadith=0
  truthfulness → riyad:book=1:ch=4:hadith=0
  self_accountability → riyad:book=1:ch=5:hadith=0
  piety/taqwa → riyad:book=1:ch=6:hadith=0
  certitude/yaqin → riyad:book=1:ch=7:hadith=0
  uprightness → riyad:book=1:ch=8:hadith=0
  reflection → riyad:book=1:ch=9:hadith=0
  striving/jihad → riyad:book=1:ch=11:hadith=0
  fear/khawf → riyad:book=1:ch=49:hadith=0
  forgiveness/mercy → riyad:book=1:ch=50:hadith=0
  weeping → riyad:book=1:ch=53:hadith=0
  renunciation/zuhd → riyad:book=1:ch=54:hadith=0
  contentment → riyad:book=1:ch=56:hadith=0
  generosity → riyad:book=1:ch=58:hadith=0

Rule: ONLY emit if a keyword matches. Prefer this over the model generating
  hadith from memory. Max 3 pointers.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POINTER GRAMMAR (STRICT — no other formats accepted):
  {source_id}:{key}={value}:{key}={value}:...
  All values are lowercase. Integer values have no leading zeros.
Examples:
  asbab:surah=39:verse=53
  thematic:surah=39:section=0
  ihya:vol=4:ch=1:sec=0
  madarij:vol=1:station=repentance:sub=0
  riyad:book=1:ch=2:hadith=0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# --- Badge metadata templates ---

_SOURCE_BADGE_MAP = {
    "asbab": {
        "key": "asbab",
        "name": "Asbab al-Nuzul",
        "author": "Al-Wahidi",
        "type": "Context of Revelation",
    },
    "thematic": {
        "key": "thematic",
        "name": "Thematic Commentary",
        "author": "Shaykh al-Ghazali",
        "type": "Surah Commentary",
    },
    "ihya": {
        "key": "ihya",
        "name": "Ihya Ulum al-Din",
        "author": "Imam al-Ghazali",
        "type": "Spiritual Teaching",
    },
    "madarij": {
        "key": "madarij",
        "name": "Madarij al-Salikin",
        "author": "Ibn Qayyim",
        "type": "Spiritual Development",
    },
    "riyad": {
        "key": "riyad",
        "name": "Riyad al-Saliheen",
        "author": "Imam al-Nawawi",
        "type": "Hadith Collection",
    },
}


# --- Pointer parsing ---

def _parse_pointer(pointer_str):
    """
    Parse 'source_id:key1=val1:key2=val2' into (source_id, {key1: val1, ...}).
    Returns (None, None) if malformed.
    """
    if not pointer_str or not isinstance(pointer_str, str):
        return None, None

    parts = pointer_str.strip().split(":")
    if len(parts) < 2:
        return None, None

    source_id = parts[0].lower()
    if source_id not in _SOURCE_BADGE_MAP:
        return None, None

    params = {}
    for part in parts[1:]:
        if "=" not in part:
            return None, None
        key, val = part.split("=", 1)
        key = key.strip().lower()
        val = val.strip()
        try:
            params[key] = int(val)
        except ValueError:
            params[key] = val.lower()

    return source_id, params


# --- Individual resolvers ---

def _resolve_asbab(params):
    """Resolve asbab:surah=N:verse=V → text excerpt."""
    surah = params.get("surah")
    verse = params.get("verse")
    if surah is None or verse is None:
        return None

    data = _load_asbab_surah(surah)
    if not data:
        return None

    for entry in data.get("entries", []):
        if entry["verse_start"] <= verse <= entry["verse_end"]:
            text = entry.get("text", "")
            if len(text) > MAX_ASBAB_CHARS:
                text = text[:MAX_ASBAB_CHARS] + "..."
            return {
                "source_id": "asbab",
                "source": "Asbab al-Nuzul (Al-Wahidi)",
                "title": f"Context of Revelation — Verse {verse}",
                "text": text,
            }

    return None


def _resolve_thematic(params):
    """Resolve thematic:surah=N:section=S → text excerpt."""
    surah = params.get("surah")
    section_idx = params.get("section", 0)
    if surah is None:
        return None

    data = _load_thematic_surah(surah)
    if not data:
        return None

    synopsis = data.get("synopsis", "")
    surah_name = data.get("surah_name", f"Surah {surah}")
    sections = data.get("sections", [])

    text_parts = []
    if synopsis:
        text_parts.append(f"Thematic Overview: {synopsis}")

    if isinstance(section_idx, int) and 0 <= section_idx < len(sections):
        sec_text = sections[section_idx].get("text", "")
        if sec_text:
            text_parts.append(sec_text)

    combined = "\n\n".join(text_parts)
    if not combined.strip():
        return None

    if len(combined) > MAX_THEMATIC_CHARS:
        combined = combined[:MAX_THEMATIC_CHARS] + "..."

    return {
        "source_id": "thematic",
        "source": "A Thematic Commentary on the Qur'an (Shaykh al-Ghazali)",
        "title": f"Thematic Commentary — {surah_name}",
        "text": combined,
    }


def _resolve_ihya(params):
    """Resolve ihya:vol=V:ch=C:sec=S → text excerpt (up to 2 sections)."""
    vol = params.get("vol")
    ch_num = params.get("ch")
    sec_idx = params.get("sec", 0)
    if vol is None or ch_num is None:
        return None

    vol_data = _load_ihya_volume(vol)
    if not vol_data:
        return None

    for ch in vol_data.get("chapters", []):
        if ch["chapter_number"] == ch_num:
            sections = ch.get("sections", [])
            start = sec_idx if isinstance(sec_idx, int) else 0
            collected = []
            total_len = 0
            for try_idx in range(start, min(start + 5, len(sections))):
                text = sections[try_idx].get("text", "")
                if len(text.strip()) < 50:
                    continue  # skip headings
                if total_len + len(text) > MAX_IHYA_CHARS:
                    text = text[:MAX_IHYA_CHARS - total_len] + "..."
                    collected.append(text)
                    break
                collected.append(text)
                total_len += len(text)
                if len(collected) >= 2:
                    break
            if collected:
                return {
                    "source_id": "ihya",
                    "source": "Ihya Ulum al-Din (Imam al-Ghazali)",
                    "title": ch["chapter_title"],
                    "text": "\n\n".join(collected),
                }
            break

    return None


def _resolve_madarij(params):
    """Resolve madarij:vol=V:station=SLUG:sub=S → text excerpt (up to 2 subsections)."""
    vol = params.get("vol")
    station_slug = params.get("station")
    sub_idx = params.get("sub", 0)
    if vol is None or station_slug is None:
        return None

    vol_data = _load_madarij_volume(vol)
    if not vol_data:
        return None

    for st in vol_data.get("stations", []):
        if st.get("station_slug", "").lower() == str(station_slug).lower():
            subsections = st.get("subsections", [])
            start = sub_idx if isinstance(sub_idx, int) else 0
            collected = []
            total_len = 0
            for i in range(start, min(start + 2, len(subsections))):
                text = subsections[i].get("text", "")
                if not text.strip():
                    continue
                if total_len + len(text) > MAX_MADARIJ_CHARS:
                    text = text[:MAX_MADARIJ_CHARS - total_len] + "..."
                    collected.append(text)
                    break
                collected.append(text)
                total_len += len(text)
            if collected:
                return {
                    "source_id": "madarij",
                    "source": "Madarij al-Salikin (Ibn Qayyim al-Jawziyyah)",
                    "title": f"Station of {st['station_name']}",
                    "text": "\n\n".join(collected),
                }
            break

    return None


def _resolve_riyad(params):
    """Resolve riyad:book=B:ch=C:hadith=H → text excerpt (up to 2 hadiths)."""
    book = params.get("book", 1)
    ch_num = params.get("ch")
    hadith_idx = params.get("hadith", 0)
    if ch_num is None:
        return None

    ch_data = _load_riyad_chapter(book, ch_num)
    if not ch_data:
        return None

    entries = ch_data.get("hadith_entries", [])
    start = hadith_idx if isinstance(hadith_idx, int) else 0
    collected = []
    total_len = 0
    title = None

    for i in range(start, min(start + 2, len(entries))):
        h = entries[i]
        text = h.get("text", "")
        if not text.strip():
            continue
        if total_len + len(text) > MAX_RIYAD_CHARS:
            text = text[:MAX_RIYAD_CHARS - total_len] + "..."
            collected.append(text)
            if title is None:
                narrator = h.get("narrator", "")
                h_num = h.get("hadith_number", "")
                title = f"Hadith #{h_num}" if h_num else "Hadith"
                if narrator:
                    title += f" (narrated by {narrator})"
            break
        collected.append(text)
        total_len += len(text)
        if title is None:
            narrator = h.get("narrator", "")
            h_num = h.get("hadith_number", "")
            title = f"Hadith #{h_num}" if h_num else "Hadith"
            if narrator:
                title += f" (narrated by {narrator})"

    if not collected:
        return None

    ch_title = ch_data.get("chapter_title", "")
    if ch_title and title:
        title += f" — {ch_title}"

    return {
        "source_id": "riyad",
        "source": "Riyad al-Saliheen (Imam al-Nawawi)",
        "title": title or "Hadith",
        "text": "\n\n".join(collected),
    }


# --- Main pointer dispatcher ---

_RESOLVERS = {
    "asbab": _resolve_asbab,
    "thematic": _resolve_thematic,
    "ihya": _resolve_ihya,
    "madarij": _resolve_madarij,
    "riyad": _resolve_riyad,
}


def resolve_scholarly_pointers(pointers):
    """
    Resolve a list of pointer strings into text excerpts.

    Args:
        pointers: List of pointer strings, e.g.
            ["asbab:surah=39:verse=53", "thematic:surah=39:section=0"]

    Returns:
        dict with:
          "excerpts": list of {source_id, source, title, text} dicts
          "sources_used": list of badge metadata dicts (for frontend)
    """
    if not pointers:
        return {"excerpts": [], "sources_used": []}

    excerpts = []
    sources_seen = set()
    total_chars = 0

    for pointer_str in pointers:
        if total_chars >= MAX_TOTAL_SCHOLARLY_CHARS:
            break

        source_id, params = _parse_pointer(pointer_str)
        if source_id is None:
            continue

        resolver = _RESOLVERS.get(source_id)
        if not resolver:
            continue

        try:
            result = resolver(params)
        except Exception as e:
            print(f"  Pointer resolve error for '{pointer_str}': {e}")
            continue

        if result and result.get("text"):
            text = result["text"]
            remaining = MAX_TOTAL_SCHOLARLY_CHARS - total_chars
            if len(text) > remaining:
                text = text[:remaining] + "..."
                result["text"] = text

            excerpts.append(result)
            total_chars += len(text)
            sources_seen.add(source_id)

    # Build badge list from what actually resolved
    sources_used = []
    for sid in sources_seen:
        badge = _SOURCE_BADGE_MAP.get(sid)
        if badge:
            sources_used.append(dict(badge))

    return {"excerpts": excerpts, "sources_used": sources_used}


# --- Prompt builders ---

def format_scholarly_excerpts_for_prompt(resolved_data):
    """Format resolved scholarly excerpts for the generation prompt."""
    if not resolved_data or not resolved_data.get("excerpts"):
        return ""

    parts = []
    parts.append("")
    parts.append("=" * 60)
    parts.append("SCHOLARLY SOURCE EXCERPTS (Retrieved for this verse)")
    parts.append("=" * 60)
    parts.append("")
    parts.append("CRITICAL INSTRUCTIONS:")
    parts.append("- Use ONLY the excerpts below for scholarly content. Do NOT fabricate.")
    parts.append("- Cite sources by name: 'Al-Wahidi narrates...', 'As al-Ghazali notes...', etc.")
    parts.append("- If a Riyad hadith excerpt is provided, use it in the hadith section.")
    parts.append("- If NO hadith excerpt is provided, leave the hadith array EMPTY [].")
    parts.append("- Integrate scholarly insights naturally into lessons_practical_applications.")
    parts.append("")

    for i, excerpt in enumerate(resolved_data["excerpts"], 1):
        parts.append(f"--- EXCERPT {i}: {excerpt['source']} ---")
        if excerpt.get("title"):
            parts.append(f"Section: {excerpt['title']}")
        parts.append(excerpt["text"])
        parts.append("")

    return "\n".join(parts)


def build_scholarly_planning_prompt(surah_number, verse_start, verse_end,
                                     verse_text, ibn_kathir_summary, query):
    """
    Build the planning prompt for scholarly source retrieval (Call 1).

    Args:
        surah_number: int
        verse_start: int
        verse_end: int or None
        verse_text: English translation (truncated to ~300 chars)
        ibn_kathir_summary: First ~500 chars of Ibn Kathir tafsir
        query: Original user query string

    Returns:
        Prompt string for the planning Gemini call.
    """
    verse_ref = f"{surah_number}:{verse_start}"
    if verse_end and verse_end != verse_start:
        verse_ref += f"-{verse_end}"

    return f"""{SCHOLARLY_SOURCE_CATALOG}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEW-SHOT EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXAMPLE 1 — Verse with many topical matches:
  Verse: 39:53 "Say, O My servants who have transgressed against themselves,
    do not despair of the mercy of Allah..."
  Ibn Kathir themes: mercy, forgiveness, repentance, despair, hope
  Output:
  {{
    "pointers": [
      "asbab:surah=39:verse=53",
      "thematic:surah=39:section=0",
      "ihya:vol=4:ch=3:sec=0",
      "madarij:vol=2:station=hope:sub=0",
      "riyad:book=1:ch=50:hadith=0",
      "riyad:book=1:ch=2:hadith=0"
    ],
    "reasoning": "Verse about mercy/hope/repentance matches Ihya fear+hope, Madarij hope station, Riyad forgiveness+repentance chapters."
  }}

EXAMPLE 2 — Verse with few topical matches:
  Verse: 33:16 "Say, Never will fleeing benefit you if you should flee from death..."
  Ibn Kathir themes: death, fleeing battle, hypocrisy, divine decree
  Output:
  {{
    "pointers": [
      "asbab:surah=33:verse=16",
      "thematic:surah=33:section=0",
      "ihya:vol=4:ch=10:sec=0"
    ],
    "reasoning": "Verse about death matches Ihya death chapter. No clear station/hadith match."
  }}

EXAMPLE 3 — Narrative verse with no topical match:
  Verse: 12:80 "So when they had despaired of him, they secluded themselves..."
  Ibn Kathir themes: Yusuf story, brothers, despair, oath to father
  Output:
  {{
    "pointers": [
      "asbab:surah=12:verse=80",
      "thematic:surah=12:section=0"
    ],
    "reasoning": "Narrative verse about Yusuf's brothers. No spiritual station or ethical topic matches routing tables."
  }}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUERY CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Query: "{query}"
Verse: {verse_ref}
Verse text: {verse_text[:300]}
Ibn Kathir key themes: {ibn_kathir_summary[:500]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create a retrieval plan for the verse above.

DETERMINISTIC RULES (follow exactly):
1. ALWAYS include: asbab:surah={surah_number}:verse={verse_start}
2. ALWAYS include: thematic:surah={surah_number}:section=0
3. Scan the verse text and Ibn Kathir themes for keywords that appear in the
   ROUTING TABLES above (Ihya, Madarij, Riyad).
4. For each keyword match, emit the EXACT pointer from the routing table.
   Do NOT modify or invent pointers.
5. If NO keywords match any routing table, emit ONLY the asbab + thematic pointers.
6. Maximum 10 pointers total.
7. Every pointer MUST follow the grammar: source_id:key=value:key=value:...

OUTPUT (strict JSON, nothing else):
{{
  "pointers": ["..."],
  "reasoning": "one sentence"
}}"""


# ═══════════════════════════════════════════════════════════════════
# DETERMINISTIC SCHOLARLY PLANNER (replaces Gemini planning call)
# ═══════════════════════════════════════════════════════════════════

# Routing tables: keyword → pointer
# Each entry: (set of trigger keywords, pointer string)
# Keywords are checked against lowercase verse_text + ibn_kathir_summary

_IHYA_ROUTING = [
    # Vol 1 — Acts of Worship
    ({"prayer", "salah", "salat", "pray", "praying"}, "ihya:vol=1:ch=4:sec=0"),
    ({"fasting", "sawm", "fast", "ramadan"}, "ihya:vol=1:ch=6:sec=0"),
    ({"pilgrimage", "hajj"}, "ihya:vol=1:ch=7:sec=0"),
    ({"quran", "recitation", "recite", "reading"}, "ihya:vol=1:ch=8:sec=0"),
    ({"remembrance", "dhikr", "zikr"}, "ihya:vol=1:ch=9:sec=0"),
    # Vol 2 — Worldly Usages
    ({"marriage", "spouse", "husband", "wife", "wives"}, "ihya:vol=2:ch=2:sec=0"),
    ({"halal", "haram", "lawful", "unlawful", "forbidden", "permitted"}, "ihya:vol=2:ch=4:sec=0"),
    ({"brotherhood", "friendship", "companion"}, "ihya:vol=2:ch=5:sec=0"),
    # Vol 3 — Destructive Evils
    ({"soul", "nafs", "heart", "qalb"}, "ihya:vol=3:ch=1:sec=0"),
    ({"conduct", "character", "manners", "akhlaq"}, "ihya:vol=3:ch=2:sec=0"),
    ({"greed", "desire", "appetite", "lust"}, "ihya:vol=3:ch=3:sec=0"),
    ({"tongue", "speech", "backbiting", "slander", "gossip", "lying"}, "ihya:vol=3:ch=4:sec=0"),
    ({"anger", "envy", "hatred", "jealousy", "hasad"}, "ihya:vol=3:ch=5:sec=0"),
    ({"wealth", "miserliness", "money", "worldly", "dunya"}, "ihya:vol=3:ch=7:sec=0"),
    ({"pride", "arrogance", "kibr", "vanity", "boasting"}, "ihya:vol=3:ch=9:sec=0"),
    # Vol 4 — Constructive Virtues
    ({"repentance", "tawbah", "repent", "forgiveness", "forgive"}, "ihya:vol=4:ch=1:sec=0"),
    ({"patience", "sabr", "patient", "gratitude", "shukr", "grateful", "thankful"}, "ihya:vol=4:ch=2:sec=0"),
    ({"fear", "hope", "khawf", "raja", "afraid", "mercy", "despair"}, "ihya:vol=4:ch=3:sec=0"),
    ({"poverty", "renunciation", "zuhd", "asceticism", "worldly"}, "ihya:vol=4:ch=4:sec=0"),
    ({"trust", "tawakkul", "reliance", "rely"}, "ihya:vol=4:ch=5:sec=0"),
    ({"love", "devotion", "mahabbah"}, "ihya:vol=4:ch=6:sec=0"),
    ({"intention", "niyyah", "sincerity", "ikhlas"}, "ihya:vol=4:ch=7:sec=0"),
    ({"meditation", "introspection", "contemplation", "reflect"}, "ihya:vol=4:ch=8:sec=0"),
    ({"death", "afterlife", "hereafter", "akhirah", "grave", "dying", "judgment"}, "ihya:vol=4:ch=10:sec=0"),
    # Expanded Ihya routing
    ({"knowledge", "scholar", "learning", "ilm", "teach"}, "ihya:vol=1:ch=1:sec=0"),
    ({"hypocrisy", "hypocrite", "munafiq", "nifaq", "show"}, "ihya:vol=3:ch=8:sec=0"),
    ({"worship", "ibadah", "obedience", "obey"}, "ihya:vol=1:ch=3:sec=0"),
    ({"charity", "sadaqah", "zakat", "alms", "giving"}, "ihya:vol=1:ch=5:sec=0"),
    ({"food", "eating", "appetite", "meal"}, "ihya:vol=2:ch=1:sec=0"),
    ({"travel", "journey", "seclusion"}, "ihya:vol=2:ch=7:sec=0"),
    ({"self-deception", "delusion", "ghurur"}, "ihya:vol=3:ch=10:sec=0"),
    ({"truthfulness", "truth", "sidq"}, "ihya:vol=4:ch=9:sec=0"),
]

_MADARIJ_ROUTING = [
    # Vol 1
    ({"awakening", "wake", "heedless"}, "madarij:vol=1:station=awakening:sub=0"),
    ({"insight", "knowledge", "understanding"}, "madarij:vol=1:station=insight:sub=0"),
    ({"purpose", "determination", "resolve"}, "madarij:vol=1:station=purpose:sub=0"),
    ({"resolve", "willpower"}, "madarij:vol=1:station=resolve:sub=0"),
    ({"reflection", "contemplation", "tafakkur"}, "madarij:vol=1:station=reflection:sub=0"),
    ({"self_reckoning", "accountability", "muhasabah"}, "madarij:vol=1:station=self_reckoning:sub=0"),
    ({"repentance", "tawbah", "repent"}, "madarij:vol=1:station=repentance:sub=0"),
    # Vol 2
    ({"remembrance", "dhikr", "zikr"}, "madarij:vol=2:station=remembrance:sub=0"),
    ({"fleeing", "flee", "escape"}, "madarij:vol=2:station=fleeing:sub=0"),
    ({"grief", "sadness", "sorrow"}, "madarij:vol=2:station=grief:sub=0"),
    ({"fear", "khawf", "afraid", "dread"}, "madarij:vol=2:station=fear:sub=0"),
    ({"humility", "humble", "khushu"}, "madarij:vol=2:station=humility:sub=0"),
    ({"meekness", "meek", "gentle"}, "madarij:vol=2:station=meekness:sub=0"),
    ({"renunciation", "zuhd", "asceticism"}, "madarij:vol=2:station=renunciation:sub=0"),
    ({"devotion", "worship", "ibadah"}, "madarij:vol=2:station=devotion:sub=0"),
    ({"hope", "raja", "hopeful", "optimism"}, "madarij:vol=2:station=hope:sub=0"),
    ({"watchfulness", "muraqabah", "vigilance"}, "madarij:vol=2:station=watchfulness:sub=0"),
    ({"purification", "tazkiyah", "purify"}, "madarij:vol=2:station=purification:sub=0"),
    ({"trust", "tawakkul", "reliance"}, "madarij:vol=2:station=trusting_reliance:sub=0"),
    ({"submission", "surrender", "islam"}, "madarij:vol=2:station=submission:sub=0"),
    ({"patience", "sabr", "patient", "steadfast"}, "madarij:vol=2:station=patience:sub=0"),
    ({"contentment", "rida", "satisfied", "content"}, "madarij:vol=2:station=joyful_contentment:sub=0"),
    # Expanded Madarij routing
    ({"discipline", "training", "riyadah"}, "madarij:vol=2:station=disciplining:sub=0"),
    ({"listen", "listening", "heed"}, "madarij:vol=2:station=listening:sub=0"),
    ({"trembling", "awe", "reverence"}, "madarij:vol=2:station=trembling:sub=0"),
    ({"scrupulous", "wara", "caution"}, "madarij:vol=2:station=scrupulousness:sub=0"),
    ({"relegate", "relegation", "entrust"}, "madarij:vol=2:station=relegation:sub=0"),
    ({"standing firm", "steadfast", "istiqamah"}, "madarij:vol=2:station=standing_firm:sub=0"),
]

_RIYAD_ROUTING = [
    ({"sincerity", "intention", "ikhlas", "niyyah"}, "riyad:book=1:ch=1:hadith=0"),
    ({"repentance", "tawbah", "repent"}, "riyad:book=1:ch=2:hadith=0"),
    ({"patience", "sabr", "patient", "steadfast"}, "riyad:book=1:ch=3:hadith=0"),
    ({"truthfulness", "truth", "honest", "sidq"}, "riyad:book=1:ch=4:hadith=0"),
    ({"self_accountability", "muhasabah", "reckoning"}, "riyad:book=1:ch=5:hadith=0"),
    ({"piety", "taqwa", "god-fearing", "righteous"}, "riyad:book=1:ch=6:hadith=0"),
    ({"certitude", "yaqin", "certainty"}, "riyad:book=1:ch=7:hadith=0"),
    ({"uprightness", "istiqamah", "steadfastness"}, "riyad:book=1:ch=8:hadith=0"),
    ({"reflection", "contemplation", "tafakkur"}, "riyad:book=1:ch=9:hadith=0"),
    ({"striving", "jihad", "struggle"}, "riyad:book=1:ch=11:hadith=0"),
    ({"fear", "khawf", "afraid", "dread"}, "riyad:book=1:ch=49:hadith=0"),
    ({"forgiveness", "mercy", "rahma", "compassion"}, "riyad:book=1:ch=50:hadith=0"),
    ({"weeping", "tears", "cry", "crying"}, "riyad:book=1:ch=53:hadith=0"),
    ({"renunciation", "zuhd", "asceticism"}, "riyad:book=1:ch=54:hadith=0"),
    ({"contentment", "rida", "satisfied"}, "riyad:book=1:ch=56:hadith=0"),
    ({"generosity", "charity", "sadaqah", "generous", "giving"}, "riyad:book=1:ch=58:hadith=0"),
    # Expanded routing (from verse-map analysis)
    ({"supplication", "dua", "invoke", "call upon"}, "riyad:book=1:ch=15:hadith=0"),
    ({"enjoin", "forbid", "commanding"}, "riyad:book=1:ch=22:hadith=0"),
    ({"oppression", "injustice", "zulm", "tyrant"}, "riyad:book=1:ch=26:hadith=0"),
    ({"parent", "parents", "mother", "father", "filial"}, "riyad:book=1:ch=40:hadith=0"),
    ({"neighbor", "neighbours", "neighbour"}, "riyad:book=1:ch=43:hadith=0"),
    ({"orphan", "orphans", "yateem"}, "riyad:book=1:ch=44:hadith=0"),
    ({"elderly", "aged", "respect"}, "riyad:book=1:ch=45:hadith=0"),
    ({"sick", "illness", "visiting", "disease"}, "riyad:book=1:ch=46:hadith=0"),
    ({"clothing", "dress", "garment"}, "riyad:book=1:ch=112:hadith=0"),
    ({"greeting", "salam", "peace"}, "riyad:book=1:ch=130:hadith=0"),
    ({"travel", "journey", "traveler"}, "riyad:book=1:ch=168:hadith=0"),
    ({"obligation", "command", "duty", "obey", "obedience"}, "riyad:book=1:ch=179:hadith=0"),
    ({"zakat", "alms", "zakah"}, "riyad:book=1:ch=200:hadith=0"),
    ({"knowledge", "scholar", "learning", "ilm"}, "riyad:book=1:ch=241:hadith=0"),
    ({"dream", "vision"}, "riyad:book=1:ch=243:hadith=0"),
    ({"paradise", "jannah", "garden", "heaven"}, "riyad:book=1:ch=244:hadith=0"),
    ({"hellfire", "jahannam", "fire", "punishment"}, "riyad:book=1:ch=344:hadith=0"),
    ({"food", "eating", "drink", "meal"}, "riyad:book=1:ch=100:hadith=0"),
    ({"fasting", "ramadan", "fast"}, "riyad:book=1:ch=201:hadith=0"),
]

MAX_POINTERS = 10


def _station_name_to_slug(name):
    """Convert Madarij display name to station slug: 'Oft-Returning' → 'oft_returning'."""
    return name.lower().replace(" ", "_").replace("-", "_")


def _get_verse_map_pointers(surah_number, verse_start):
    """
    Look up pre-indexed verse→source references from the unified verse map.

    Returns up to 5 pointer strings for ihya/madarij/riyad entries
    that have been pre-computed for this specific verse.
    """
    verse_map = _load_unified_verse_map()
    key = f"{surah_number}:{verse_start}"
    refs = verse_map.get(key, [])

    if not refs:
        return []

    pointers = []
    seen = set()

    for ref in refs:
        source = ref.get("source", "")

        if source == "ihya_ulum_al_din":
            vol = ref.get("volume")
            ch = ref.get("chapter")
            if vol and ch:
                p = f"ihya:vol={vol}:ch={ch}:sec=0"
                if p not in seen:
                    seen.add(p)
                    pointers.append(p)

        elif source == "madarij_al_salikin":
            vol = ref.get("volume")
            station = ref.get("station")
            if vol and station:
                slug = _station_name_to_slug(station)
                p = f"madarij:vol={vol}:station={slug}:sub=0"
                if p not in seen:
                    seen.add(p)
                    pointers.append(p)

        elif source == "riyad_al_saliheen":
            book = ref.get("book", 1)
            ch = ref.get("chapter")
            if ch:
                p = f"riyad:book={book}:ch={ch}:hadith=0"
                if p not in seen:
                    seen.add(p)
                    pointers.append(p)

        if len(pointers) >= 5:
            break

    return pointers


def plan_scholarly_retrieval_deterministic(surah_number, verse_start, verse_end,
                                            verse_text, ibn_kathir_summary):
    """
    Deterministic scholarly retrieval planner — replaces Gemini planning call.

    Scans verse text and Ibn Kathir summary for routing keywords, then emits
    exact pointers matching the routing tables. Zero API calls, zero latency,
    zero failure modes.

    Returns dict: {"pointers": [...], "reasoning": "..."}
    """
    # Always include asbab + thematic
    pointers = [
        f"asbab:surah={surah_number}:verse={verse_start}",
        f"thematic:surah={surah_number}:section=0",
    ]

    # Build combined search text (lowercase)
    search_text = f"{verse_text} {ibn_kathir_summary}".lower()

    # Track which sources we've already added pointers for (dedup)
    ihya_added = set()
    madarij_added = set()  # max 2
    riyad_added = set()  # max 3
    matched_keywords = []

    # Scan Ihya (up to 3 pointers)
    for keywords, pointer in _IHYA_ROUTING:
        if len(pointers) >= MAX_POINTERS:
            break
        if len(ihya_added) >= 3:
            break
        if pointer in ihya_added:
            continue
        for kw in keywords:
            if kw in search_text:
                pointers.append(pointer)
                ihya_added.add(pointer)
                matched_keywords.append(kw)
                break

    # Scan Madarij (max 2 pointers)
    for keywords, pointer in _MADARIJ_ROUTING:
        if len(pointers) >= MAX_POINTERS:
            break
        if len(madarij_added) >= 2:
            break
        if pointer in madarij_added:
            continue
        for kw in keywords:
            if kw in search_text:
                pointers.append(pointer)
                madarij_added.add(pointer)
                matched_keywords.append(kw)
                break

    # Scan Riyad (max 3 pointers)
    for keywords, pointer in _RIYAD_ROUTING:
        if len(pointers) >= MAX_POINTERS:
            break
        if len(riyad_added) >= 3:
            break
        if pointer in riyad_added:
            continue
        for kw in keywords:
            if kw in search_text:
                pointers.append(pointer)
                riyad_added.add(pointer)
                matched_keywords.append(kw)
                break

    # Build reasoning
    if matched_keywords:
        reasoning = f"Matched keywords: {', '.join(matched_keywords[:8])}"
    else:
        reasoning = "No topical keywords matched routing tables; asbab + thematic only."

    # --- Stage 2: Verse-map discovery (precise references from pre-indexed data) ---
    verse_map_ptrs = _get_verse_map_pointers(surah_number, verse_start)
    existing = set(pointers)
    vm_added = 0
    for vp in verse_map_ptrs:
        if vp not in existing and len(pointers) < MAX_POINTERS:
            pointers.append(vp)
            existing.add(vp)
            vm_added += 1

    if vm_added:
        reasoning += f" + {vm_added} verse-map refs"

    return {"pointers": pointers, "reasoning": reasoning}
