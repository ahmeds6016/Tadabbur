#!/usr/bin/env python3
"""
Pre-Compute Scholarly Plans for All 6,236 Quran Verses
========================================================
Replaces the runtime Gemini scholarly planning call (~8-10s per request)
with a pre-computed JSON index. Uses FULL raw JSON objects from Ibn Kathir
and al-Qurtubi tafsir sources to give Gemini the richest possible context
for identifying scholarly source connections.

USAGE:
------
# Dry run (first 10 verses, print to stdout)
python backend/scripts/precompute_scholarly_plans.py --dry-run

# Test with specific surah
python backend/scripts/precompute_scholarly_plans.py --surah 1

# Specific verse (for debugging)
python backend/scripts/precompute_scholarly_plans.py --verse 2:255

# Resume from a specific surah:verse
python backend/scripts/precompute_scholarly_plans.py --resume-from 50:1

# Full run (all 6,236 verses)
python backend/scripts/precompute_scholarly_plans.py

OUTPUT:
-------
backend/data/indexes/_precomputed_scholarly_plans.json
"""

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import google.auth
from google.auth.transport.requests import Request as GoogleRequest
import aiohttp

# Add project root to path so we can import source_service
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.source_service import (
    plan_scholarly_retrieval_deterministic,
    _load_unified_verse_map,
    SCHOLARLY_SOURCE_CATALOG,
)

# ============================================================================
# CONFIGURATION
# ============================================================================

GCP_PROJECT = os.environ.get("GCP_INFRASTRUCTURE_PROJECT", "tafsir-simplified")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-2.5-flash")

CONCURRENCY = 30         # Parallel Gemini requests (override with --concurrency)
MAX_RETRIES = 10         # Retries per verse on failure (high for aggressive concurrency)
SAVE_EVERY = 200         # Save progress to disk every N verses
MAX_POINTERS = 10        # Max pointers per verse
TOKEN_REFRESH_INTERVAL = 400  # Refresh auth token every N verses

# Paths
DATA_DIR = PROJECT_ROOT / "backend" / "data"
TAFSIR_DIR = DATA_DIR / "tafsir_sources" / "cleaned"
INDEX_DIR = DATA_DIR / "indexes"
OUTPUT_FILE = INDEX_DIR / "_precomputed_scholarly_plans.json"
PROGRESS_FILE = INDEX_DIR / "_precompute_progress.json"

# Quran metadata (surah: {name, verses})
QURAN_METADATA = {
    1: {"name": "Al-Fatihah", "verses": 7}, 2: {"name": "Al-Baqarah", "verses": 286},
    3: {"name": "Aal-E-Imran", "verses": 200}, 4: {"name": "An-Nisa", "verses": 176},
    5: {"name": "Al-Ma'idah", "verses": 120}, 6: {"name": "Al-An'am", "verses": 165},
    7: {"name": "Al-A'raf", "verses": 206}, 8: {"name": "Al-Anfal", "verses": 75},
    9: {"name": "At-Tawbah", "verses": 129}, 10: {"name": "Yunus", "verses": 109},
    11: {"name": "Hud", "verses": 123}, 12: {"name": "Yusuf", "verses": 111},
    13: {"name": "Ar-Ra'd", "verses": 43}, 14: {"name": "Ibrahim", "verses": 52},
    15: {"name": "Al-Hijr", "verses": 99}, 16: {"name": "An-Nahl", "verses": 128},
    17: {"name": "Al-Isra", "verses": 111}, 18: {"name": "Al-Kahf", "verses": 110},
    19: {"name": "Maryam", "verses": 98}, 20: {"name": "Taha", "verses": 135},
    21: {"name": "Al-Anbya", "verses": 112}, 22: {"name": "Al-Hajj", "verses": 78},
    23: {"name": "Al-Mu'minun", "verses": 118}, 24: {"name": "An-Nur", "verses": 64},
    25: {"name": "Al-Furqan", "verses": 77}, 26: {"name": "Ash-Shu'ara", "verses": 227},
    27: {"name": "An-Naml", "verses": 93}, 28: {"name": "Al-Qasas", "verses": 88},
    29: {"name": "Al-Ankabut", "verses": 69}, 30: {"name": "Ar-Rum", "verses": 60},
    31: {"name": "Luqman", "verses": 34}, 32: {"name": "As-Sajdah", "verses": 30},
    33: {"name": "Al-Ahzab", "verses": 73}, 34: {"name": "Saba", "verses": 54},
    35: {"name": "Fatir", "verses": 45}, 36: {"name": "Ya-Sin", "verses": 83},
    37: {"name": "As-Saffat", "verses": 182}, 38: {"name": "Sad", "verses": 88},
    39: {"name": "Az-Zumar", "verses": 75}, 40: {"name": "Ghafir", "verses": 85},
    41: {"name": "Fussilat", "verses": 54}, 42: {"name": "Ash-Shuraa", "verses": 53},
    43: {"name": "Az-Zukhruf", "verses": 89}, 44: {"name": "Ad-Dukhan", "verses": 59},
    45: {"name": "Al-Jathiyah", "verses": 37}, 46: {"name": "Al-Ahqaf", "verses": 35},
    47: {"name": "Muhammad", "verses": 38}, 48: {"name": "Al-Fath", "verses": 29},
    49: {"name": "Al-Hujurat", "verses": 18}, 50: {"name": "Qaf", "verses": 45},
    51: {"name": "Adh-Dhariyat", "verses": 60}, 52: {"name": "At-Tur", "verses": 49},
    53: {"name": "An-Najm", "verses": 62}, 54: {"name": "Al-Qamar", "verses": 55},
    55: {"name": "Ar-Rahman", "verses": 78}, 56: {"name": "Al-Waqi'ah", "verses": 96},
    57: {"name": "Al-Hadid", "verses": 29}, 58: {"name": "Al-Mujadila", "verses": 22},
    59: {"name": "Al-Hashr", "verses": 24}, 60: {"name": "Al-Mumtahanah", "verses": 13},
    61: {"name": "As-Saf", "verses": 14}, 62: {"name": "Al-Jumu'ah", "verses": 11},
    63: {"name": "Al-Munafiqun", "verses": 11}, 64: {"name": "At-Taghabun", "verses": 18},
    65: {"name": "At-Talaq", "verses": 12}, 66: {"name": "At-Tahrim", "verses": 12},
    67: {"name": "Al-Mulk", "verses": 30}, 68: {"name": "Al-Qalam", "verses": 52},
    69: {"name": "Al-Haqqah", "verses": 52}, 70: {"name": "Al-Ma'arij", "verses": 44},
    71: {"name": "Nuh", "verses": 28}, 72: {"name": "Al-Jinn", "verses": 28},
    73: {"name": "Al-Muzzammil", "verses": 20}, 74: {"name": "Al-Muddaththir", "verses": 56},
    75: {"name": "Al-Qiyamah", "verses": 40}, 76: {"name": "Al-Insan", "verses": 31},
    77: {"name": "Al-Mursalat", "verses": 50}, 78: {"name": "An-Naba", "verses": 40},
    79: {"name": "An-Nazi'at", "verses": 46}, 80: {"name": "Abasa", "verses": 42},
    81: {"name": "At-Takwir", "verses": 29}, 82: {"name": "Al-Infitar", "verses": 19},
    83: {"name": "Al-Mutaffifin", "verses": 36}, 84: {"name": "Al-Inshiqaq", "verses": 25},
    85: {"name": "Al-Buruj", "verses": 22}, 86: {"name": "At-Tariq", "verses": 17},
    87: {"name": "Al-A'la", "verses": 19}, 88: {"name": "Al-Ghashiyah", "verses": 26},
    89: {"name": "Al-Fajr", "verses": 30}, 90: {"name": "Al-Balad", "verses": 20},
    91: {"name": "Ash-Shams", "verses": 15}, 92: {"name": "Al-Layl", "verses": 21},
    93: {"name": "Ad-Duhaa", "verses": 11}, 94: {"name": "Ash-Sharh", "verses": 8},
    95: {"name": "At-Tin", "verses": 8}, 96: {"name": "Al-Alaq", "verses": 19},
    97: {"name": "Al-Qadr", "verses": 5}, 98: {"name": "Al-Bayyinah", "verses": 8},
    99: {"name": "Az-Zalzalah", "verses": 8}, 100: {"name": "Al-Adiyat", "verses": 11},
    101: {"name": "Al-Qari'ah", "verses": 11}, 102: {"name": "At-Takathur", "verses": 8},
    103: {"name": "Al-Asr", "verses": 3}, 104: {"name": "Al-Humazah", "verses": 9},
    105: {"name": "Al-Fil", "verses": 5}, 106: {"name": "Quraysh", "verses": 4},
    107: {"name": "Al-Ma'un", "verses": 7}, 108: {"name": "Al-Kawthar", "verses": 3},
    109: {"name": "Al-Kafirun", "verses": 6}, 110: {"name": "An-Nasr", "verses": 3},
    111: {"name": "Al-Masad", "verses": 5}, 112: {"name": "Al-Ikhlas", "verses": 4},
    113: {"name": "Al-Falaq", "verses": 5}, 114: {"name": "An-Nas", "verses": 6},
}

# ============================================================================
# ENHANCED SCHOLARLY SOURCE CATALOG (richer than runtime version)
# ============================================================================

ENHANCED_SCHOLARLY_CATALOG = """
SCHOLARLY SOURCE CATALOG — DETAILED REFERENCE
===============================================

You have access to 5 indexed scholarly sources spanning classical Islamic scholarship.
Your task is to identify which sources are GENUINELY relevant to a given Quran verse
based on its themes, content, and scholarly commentary.

━━━ SOURCE 1: ASBAB AL-NUZUL (Al-Wahidi, d. 1075 CE) ━━━
WHAT IT IS: The earliest systematic compilation of "occasions of revelation" — the
  historical circumstances, events, and questions that prompted specific Quran verses
  to be revealed. Written by Ali ibn Ahmad al-Wahidi, a student of the great exegete
  al-Tha'labi, in Nishapur, Persia.
WHAT IT CONTAINS: Authenticated reports (with chains of narration) explaining WHY
  specific verses were revealed — e.g., a dispute among companions, a question posed
  to the Prophet (peace be upon him), a specific historical event like a battle or treaty.
  446 verse-level entries covering 83 of 114 surahs.
WHEN IT'S RELEVANT: For ANY verse — the historical context enriches understanding
  even when the verse has a general meaning. Knowing the occasion helps distinguish
  between universal rulings and context-specific guidance.
WHAT MAKES IT UNIQUE: The only source focused purely on historical causation. While
  Ibn Kathir mentions occasions within his tafsir, Al-Wahidi's standalone work is
  more systematic and includes narrations not found elsewhere.
Coverage: 83 of 114 surahs; 446 verse-level entries.
Pointer format: asbab:surah=N:verse=V
Rule: ALWAYS emit this pointer for the queried verse.

━━━ SOURCE 2: A THEMATIC COMMENTARY ON THE QURAN (Shaykh Muhammad al-Ghazali, d. 1996 CE) ━━━
WHAT IT IS: A modern thematic analysis of each surah by one of the 20th century's
  most influential Islamic scholars. Unlike verse-by-verse tafsir, al-Ghazali examines
  each surah as a unified literary and theological composition — its central themes,
  internal coherence, and relationship to other surahs.
WHAT IT CONTAINS: A synopsis and 1-5 thematic sections per surah covering the surah's
  major themes, its historical context in the Prophet's mission, its rhetorical structure,
  and its relevance to contemporary Muslim life. All 114 surahs covered.
WHEN IT'S RELEVANT: For ANY verse — the surah-level overview provides essential context
  for understanding where a verse sits within the surah's thematic arc.
WHAT MAKES IT UNIQUE: The only source that treats each surah as a unified whole rather
  than analyzing verses in isolation. Provides the "big picture" that verse-level
  commentary often misses.
Coverage: All 114 surahs. Each surah has 1-5 sections (section 0 = main overview).
Pointer format: thematic:surah=N:section=S
Rule: ALWAYS emit thematic:surah=N:section=0 for the queried surah.

━━━ SOURCE 3: IHYA ULUM AL-DIN (Imam Abu Hamid al-Ghazali, d. 1111 CE) ━━━
WHAT IT IS: "Revival of the Religious Sciences" — widely regarded as the single most
  important work on Islamic spirituality, ethics, and inner life ever written. Al-Ghazali,
  a jurist-turned-mystic, wrote it after a spiritual crisis led him to abandon his
  prestigious teaching position in Baghdad. The work bridges Islamic law (fiqh) with
  spiritual purpose (tasawwuf).
WHAT IT CONTAINS: 4 quarters, 45 chapters covering the entire spectrum of Muslim
  spiritual and ethical life:
  - Vol 1 (Acts of Worship): The spiritual dimensions of prayer, fasting, hajj, Quran
    recitation, dhikr (remembrance), and the etiquette of worship
  - Vol 2 (Worldly Usages): Ethics of daily life — marriage, earning a livelihood,
    halal/haram, brotherhood, travel, food, seclusion
  - Vol 3 (Destructive Evils): Diseases of the soul — greed, anger, envy, pride,
    arrogance, backbiting, lying, love of wealth, hypocrisy, self-deception
  - Vol 4 (Constructive Virtues): Stations of the soul — repentance, patience, gratitude,
    fear, hope, trust in God (tawakkul), love, sincerity, contemplation, death/afterlife
WHEN IT'S RELEVANT: When a verse touches on inner spiritual states, moral character,
  worship practices, ethical conduct, or the PURPOSE behind religious obligations.
  Al-Ghazali doesn't just describe what to do — he explains why it matters for the soul.
WHAT MAKES IT UNIQUE: Uniquely bridges outward religious practice with inner spiritual
  transformation. No other source in this collection addresses the "why" behind worship
  and ethics with such depth.

ROUTING TABLE (use ONLY these mappings):
  Vol 1 — Acts of Worship:
    knowledge/scholar/learning/ilm/teach → ihya:vol=1:ch=1:sec=0
    worship/ibadah/obedience/obey → ihya:vol=1:ch=3:sec=0
    prayer/salah/salat/pray/praying → ihya:vol=1:ch=4:sec=0
    charity/sadaqah/zakat/alms/giving → ihya:vol=1:ch=5:sec=0
    fasting/sawm/fast/ramadan → ihya:vol=1:ch=6:sec=0
    pilgrimage/hajj → ihya:vol=1:ch=7:sec=0
    quran/recitation/recite/reading → ihya:vol=1:ch=8:sec=0
    remembrance/dhikr/zikr → ihya:vol=1:ch=9:sec=0
  Vol 2 — Worldly Usages:
    food/eating/appetite/meal → ihya:vol=2:ch=1:sec=0
    marriage/spouse/husband/wife/wives → ihya:vol=2:ch=2:sec=0
    halal/haram/lawful/unlawful/forbidden/permitted → ihya:vol=2:ch=4:sec=0
    brotherhood/friendship/companion → ihya:vol=2:ch=5:sec=0
    travel/journey/seclusion → ihya:vol=2:ch=7:sec=0
  Vol 3 — Destructive Evils:
    soul/nafs/heart/qalb → ihya:vol=3:ch=1:sec=0
    conduct/character/manners/akhlaq → ihya:vol=3:ch=2:sec=0
    greed/desire/appetite/lust → ihya:vol=3:ch=3:sec=0
    tongue/speech/backbiting/slander/gossip/lying → ihya:vol=3:ch=4:sec=0
    anger/envy/hatred/jealousy/hasad → ihya:vol=3:ch=5:sec=0
    wealth/miserliness/money/worldly/dunya → ihya:vol=3:ch=7:sec=0
    hypocrisy/hypocrite/munafiq/nifaq/show → ihya:vol=3:ch=8:sec=0
    pride/arrogance/kibr/vanity/boasting → ihya:vol=3:ch=9:sec=0
    self-deception/delusion/ghurur → ihya:vol=3:ch=10:sec=0
  Vol 4 — Constructive Virtues:
    repentance/tawbah/repent/forgiveness/forgive → ihya:vol=4:ch=1:sec=0
    patience/sabr/patient/gratitude/shukr/grateful/thankful → ihya:vol=4:ch=2:sec=0
    fear/hope/khawf/raja/afraid/mercy/despair → ihya:vol=4:ch=3:sec=0
    poverty/renunciation/zuhd/asceticism → ihya:vol=4:ch=4:sec=0
    trust/tawakkul/reliance/rely → ihya:vol=4:ch=5:sec=0
    love/devotion/mahabbah → ihya:vol=4:ch=6:sec=0
    intention/niyyah/sincerity/ikhlas → ihya:vol=4:ch=7:sec=0
    meditation/introspection/contemplation/reflect → ihya:vol=4:ch=8:sec=0
    truthfulness/truth/sidq → ihya:vol=4:ch=9:sec=0
    death/afterlife/hereafter/akhirah/grave/dying/judgment → ihya:vol=4:ch=10:sec=0

Rule: Emit if the verse discusses a theme matching the routing table above.
  Go BEYOND exact keywords — use the Ibn Kathir/al-Qurtubi commentary to identify
  underlying themes. E.g., a verse about "fleeing from battle" implies fear/cowardice →
  consider ihya:vol=3:ch=5 (anger/destructive traits) or ihya:vol=4:ch=3 (fear/hope).
  Max 3 pointers.

━━━ SOURCE 4: MADARIJ AL-SALIKIN (Ibn Qayyim al-Jawziyyah, d. 1350 CE) ━━━
WHAT IT IS: "Ranks of the Wayfarers" — a masterwork on the spiritual stations (maqamat)
  and states (ahwal) of the soul's journey toward God. Written by Ibn Qayyim, the most
  prominent student of Ibn Taymiyyah, it is a commentary on the Sufi manual "Manazil
  al-Sa'irin" by al-Harawi, but grounded in Quran and Sunnah rather than speculative
  mysticism. Ibn Qayyim brings a uniquely balanced perspective: deeply spiritual yet
  scripturally rigorous.
WHAT IT CONTAINS: 2 volumes covering 35 spiritual stations organized as a progression
  from spiritual awakening to the highest states of the soul:
  - Vol 1: Foundational stations — Awakening (from heedlessness), Insight, Purpose,
    Resolve, Reflection, Self-Reckoning, Repentance, Annihilation of ego
  - Vol 2: Advanced stations — Oft-Returning to God, Remembrance, Holding Fast (to
    guidance), Fleeing (from sin), Disciplining the self, Listening (with the heart),
    Grief (over wasted time), Fear, Trembling, Humility, Meekness, Renunciation,
    Scrupulousness, Devotion, Hope, Desire (for God), Shepherding (the heart),
    Watchfulness, Purification, Refinement, Standing Firm, Trusting Reliance,
    Relegation, Trust in God, Submission, Patience, Joyful Contentment
WHEN IT'S RELEVANT: When a verse describes or evokes a spiritual state, inner
  transformation, relationship with God, or moral struggle. Especially relevant for
  verses about: turning to God, spiritual growth, overcoming the ego, fear/hope balance,
  trust/reliance, patience in adversity, contentment with divine decree.
WHAT MAKES IT UNIQUE: The only source that maps spiritual experiences to a structured
  progression. While al-Ghazali's Ihya describes virtues topically, Ibn Qayyim shows
  how they connect as stages in spiritual development.

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

Pointer format: madarij:vol=V:station=SLUG:sub=0
Rule: Emit if the verse discusses a spiritual state matching a station above.
  Consider the UNDERLYING spiritual dynamic, not just surface keywords. E.g.,
  a verse about "those who spend in ease and hardship" implies patience + generosity →
  consider madarij:vol=2:station=patience. Max 2 pointers.

━━━ SOURCE 5: RIYAD AL-SALIHEEN (Imam al-Nawawi, d. 1277 CE) ━━━
WHAT IT IS: "Gardens of the Righteous" — the most widely-read hadith collection in the
  Muslim world, compiled by Imam al-Nawawi of Damascus. Unlike the six major hadith
  collections (Bukhari, Muslim, etc.) which are organized by legal topics, Riyad
  al-Saliheen is organized by MORAL and ETHICAL themes, making it uniquely suited for
  spiritual guidance alongside Quranic commentary.
WHAT IT CONTAINS: 687 chapters with 1,022 hadith organized by ethical topic:
  - Sincerity/Intention (ch 1), Repentance (ch 2), Patience (ch 3), Truthfulness (ch 4),
    Self-Accountability (ch 5), Piety/Taqwa (ch 6), Certitude (ch 7), Uprightness (ch 8),
    Reflection (ch 9), Striving/Jihad (ch 11), Supplication/Dua (ch 15),
    Enjoining Good/Forbidding Evil (ch 22), Oppression/Injustice (ch 26),
    Honoring Parents (ch 40), Good Relations with Neighbors (ch 43),
    Care for Orphans (ch 44), Respecting Elders (ch 45), Visiting the Sick (ch 46),
    Fear of God (ch 49), Forgiveness/Mercy (ch 50), Weeping (ch 53),
    Renunciation/Zuhd (ch 54), Contentment (ch 56), Generosity/Charity (ch 58),
    Clothing (ch 112), Greeting/Salam (ch 130), Travel (ch 168),
    Obligation/Obedience (ch 179), Zakat/Alms (ch 200), Fasting/Ramadan (ch 201),
    Knowledge/Learning (ch 241), Dreams/Visions (ch 243),
    Paradise/Jannah (ch 244), Hellfire/Jahannam (ch 344), Food/Eating (ch 100)
WHEN IT'S RELEVANT: When a verse discusses an ethical/moral topic that has corresponding
  hadith. Especially valuable for: social ethics (parents, neighbors, orphans),
  personal virtues (patience, sincerity, truthfulness), eschatology (paradise, hellfire),
  and worship practices with ethical dimensions (charity, fasting).
WHAT MAKES IT UNIQUE: The only hadith-based source. Provides prophetic traditions that
  complement and elaborate on Quranic teachings. When Riyad hadith are available, they
  should be preferred over generated hadith.

ROUTING TABLE (use ONLY these mappings):
  sincerity/intention/ikhlas/niyyah → riyad:book=1:ch=1:hadith=0
  repentance/tawbah/repent → riyad:book=1:ch=2:hadith=0
  patience/sabr/patient/steadfast → riyad:book=1:ch=3:hadith=0
  truthfulness/truth/honest/sidq → riyad:book=1:ch=4:hadith=0
  self_accountability/muhasabah/reckoning → riyad:book=1:ch=5:hadith=0
  piety/taqwa/god-fearing/righteous → riyad:book=1:ch=6:hadith=0
  certitude/yaqin/certainty → riyad:book=1:ch=7:hadith=0
  uprightness/istiqamah/steadfastness → riyad:book=1:ch=8:hadith=0
  reflection/contemplation/tafakkur → riyad:book=1:ch=9:hadith=0
  striving/jihad/struggle → riyad:book=1:ch=11:hadith=0
  supplication/dua/invoke/call upon → riyad:book=1:ch=15:hadith=0
  enjoin/forbid/commanding → riyad:book=1:ch=22:hadith=0
  oppression/injustice/zulm/tyrant → riyad:book=1:ch=26:hadith=0
  parent/parents/mother/father/filial → riyad:book=1:ch=40:hadith=0
  neighbor/neighbours/neighbour → riyad:book=1:ch=43:hadith=0
  orphan/orphans/yateem → riyad:book=1:ch=44:hadith=0
  elderly/aged/respect → riyad:book=1:ch=45:hadith=0
  sick/illness/visiting/disease → riyad:book=1:ch=46:hadith=0
  fear/khawf/afraid/dread → riyad:book=1:ch=49:hadith=0
  forgiveness/mercy/rahma/compassion → riyad:book=1:ch=50:hadith=0
  weeping/tears/cry/crying → riyad:book=1:ch=53:hadith=0
  renunciation/zuhd/asceticism → riyad:book=1:ch=54:hadith=0
  contentment/rida/satisfied → riyad:book=1:ch=56:hadith=0
  generosity/charity/sadaqah/generous/giving → riyad:book=1:ch=58:hadith=0
  clothing/dress/garment → riyad:book=1:ch=112:hadith=0
  greeting/salam/peace → riyad:book=1:ch=130:hadith=0
  travel/journey/traveler → riyad:book=1:ch=168:hadith=0
  obligation/command/duty/obey/obedience → riyad:book=1:ch=179:hadith=0
  zakat/alms/zakah → riyad:book=1:ch=200:hadith=0
  fasting/ramadan/fast → riyad:book=1:ch=201:hadith=0
  knowledge/scholar/learning/ilm → riyad:book=1:ch=241:hadith=0
  dream/vision → riyad:book=1:ch=243:hadith=0
  paradise/jannah/garden/heaven → riyad:book=1:ch=244:hadith=0
  hellfire/jahannam/fire/punishment → riyad:book=1:ch=344:hadith=0
  food/eating/drink/meal → riyad:book=1:ch=100:hadith=0

Rule: Emit if the verse discusses an ethical topic matching the routing table. Max 3 pointers.

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

# ============================================================================
# FEW-SHOT EXAMPLES (5 examples covering diverse verse types)
# ============================================================================

FEW_SHOT_EXAMPLES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEW-SHOT EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXAMPLE 1 — Verse with many topical matches (mercy/hope/repentance):
  Verse: 39:53 "Say, O My servants who have transgressed against themselves,
    do not despair of the mercy of Allah..."
  Ibn Kathir themes: mercy, forgiveness, repentance, despair, hope
  Output:
  {{
    "pointers": [
      "asbab:surah=39:verse=53",
      "thematic:surah=39:section=0",
      "ihya:vol=4:ch=1:sec=0",
      "ihya:vol=4:ch=3:sec=0",
      "madarij:vol=2:station=hope:sub=0",
      "riyad:book=1:ch=2:hadith=0",
      "riyad:book=1:ch=50:hadith=0"
    ],
    "reasoning": "Verse about mercy/hope/repentance matches Ihya repentance (vol4 ch1) and fear+hope (vol4 ch3), Madarij hope station, Riyad repentance and forgiveness chapters."
  }}

EXAMPLE 2 — Verse with few topical matches (death/fleeing):
  Verse: 33:16 "Say, Never will fleeing benefit you if you should flee from death..."
  Ibn Kathir themes: death, fleeing battle, hypocrisy, divine decree
  Output:
  {{
    "pointers": [
      "asbab:surah=33:verse=16",
      "thematic:surah=33:section=0",
      "ihya:vol=4:ch=10:sec=0"
    ],
    "reasoning": "Verse about death and divine decree matches Ihya death/afterlife chapter. No clear spiritual station or ethical hadith match."
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
    "reasoning": "Narrative verse about Yusuf's brothers. No spiritual station or ethical topic matches the routing tables."
  }}

EXAMPLE 4 — Legal verse with implicit ethical themes:
  Verse: 2:282 "O you who believe, when you contract a debt for a specified term, write it down..."
  Ibn Kathir themes: contracts, witnesses, justice, writing, trustworthiness
  Output:
  {{
    "pointers": [
      "asbab:surah=2:verse=282",
      "thematic:surah=2:section=0",
      "ihya:vol=2:ch=4:sec=0",
      "riyad:book=1:ch=4:hadith=0",
      "riyad:book=1:ch=8:hadith=0"
    ],
    "reasoning": "Legal verse about contracts implies halal/haram (Ihya vol2 ch4). Emphasis on truthfulness in dealing (Riyad ch4) and uprightness (Riyad ch8)."
  }}

EXAMPLE 5 — Multi-theme verse (sovereignty/trust/intercession):
  Verse: 2:255 "Allah — there is no deity except Him, the Ever-Living, the Self-Sustaining..."
  Ibn Kathir themes: God's attributes, intercession, sovereignty, heavens and earth, knowledge
  Output:
  {{
    "pointers": [
      "asbab:surah=2:verse=255",
      "thematic:surah=2:section=0",
      "ihya:vol=4:ch=5:sec=0",
      "ihya:vol=4:ch=6:sec=0",
      "madarij:vol=2:station=trusting_reliance:sub=0",
      "riyad:book=1:ch=7:hadith=0"
    ],
    "reasoning": "Ayat al-Kursi: God's absolute sovereignty and protection implies trust/tawakkul (Ihya vol4 ch5), love/devotion to God (Ihya vol4 ch6), trusting reliance (Madarij), and certitude (Riyad ch7)."
  }}
"""

# ============================================================================
# DATA LOADING
# ============================================================================

def load_tafsir_sources():
    """Load all tafsir source files and index by surah:verse."""
    ibn_kathir = {}  # key: "surah:verse" → raw verse JSON object
    al_qurtubi = {}  # key: "surah:verse" → raw verse JSON object

    ik_files = [
        TAFSIR_DIR / "ibnkathir-Fatiha-Tawbah_fixed.json",
        TAFSIR_DIR / "ibnkathir-Yunus-Ankabut_FINAL_fixed.json",
        TAFSIR_DIR / "ibnkathir-Rum-Nas_FINAL_fixed.json",
    ]

    qurtubi_files = [
        TAFSIR_DIR / "al-Qurtubi_Fatiha.json",
        TAFSIR_DIR / "al-Qurtubi_Vol._1_FINAL_fixed.json",
        TAFSIR_DIR / "al-Qurtubi_Vol._2_FINAL_fixed.json",
        TAFSIR_DIR / "al-Qurtubi_Vol._3_fixed.json",
        TAFSIR_DIR / "al-Qurtubi_Vol._4_FINAL_fixed.json",
    ]

    def _index_verses(files, target_dict, source_name):
        for filepath in files:
            if not filepath.exists():
                print(f"  WARNING: {filepath.name} not found, skipping")
                continue
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            for verse in data.get("verses", []):
                surah = verse.get("surah")
                verse_num = verse.get("verse_number")
                verse_nums = verse.get("verse_numbers")

                if surah is None:
                    continue

                # Handle different verse number formats
                if isinstance(verse_num, list):
                    # List format like [1, 2, 3, 4, 5, 6, 7]
                    for v in verse_num:
                        target_dict[f"{surah}:{v}"] = verse
                elif isinstance(verse_num, str) and "-" in verse_num:
                    # Range format like "183-184"
                    try:
                        parts = verse_num.split("-")
                        for v in range(int(parts[0]), int(parts[1]) + 1):
                            target_dict[f"{surah}:{v}"] = verse
                    except (ValueError, IndexError):
                        pass
                elif verse_num is not None:
                    target_dict[f"{surah}:{int(verse_num)}"] = verse

                # Also index by verse_numbers list if present
                if isinstance(verse_nums, list):
                    for v in verse_nums:
                        key = f"{surah}:{v}"
                        if key not in target_dict:
                            target_dict[key] = verse

            print(f"  Loaded {filepath.name}: {len(data.get('verses', []))} entries")

    print("Loading Ibn Kathir sources...")
    _index_verses(ik_files, ibn_kathir, "ibn-kathir")
    print(f"  Total indexed: {len(ibn_kathir)} verse keys")

    print("Loading al-Qurtubi sources...")
    _index_verses(qurtubi_files, al_qurtubi, "al-qurtubi")
    print(f"  Total indexed: {len(al_qurtubi)} verse keys")

    return ibn_kathir, al_qurtubi


def load_verse_map():
    """Load the unified verse map for pre-indexed references."""
    return _load_unified_verse_map()


# ============================================================================
# PROMPT BUILDER
# ============================================================================

def build_batch_planning_prompt(surah_number, verse_number, surah_name,
                                 ibn_kathir_json, al_qurtubi_json,
                                 verse_map_refs):
    """
    Build an enhanced planning prompt with FULL raw JSON objects.

    Args:
        surah_number: int
        verse_number: int
        surah_name: str
        ibn_kathir_json: dict or None — full raw verse object from Ibn Kathir
        al_qurtubi_json: dict or None — full raw verse object from al-Qurtubi
        verse_map_refs: list — pre-indexed references from unified verse map
    """
    verse_ref = f"{surah_number}:{verse_number}"

    # Build source material section
    source_material = ""

    if ibn_kathir_json:
        # Serialize the full JSON object (no truncation)
        ik_str = json.dumps(ibn_kathir_json, ensure_ascii=False, indent=None)
        source_material += f"""
--- IBN KATHIR TAFSIR (Full JSON) ---
{ik_str}
"""

    if al_qurtubi_json:
        q_str = json.dumps(al_qurtubi_json, ensure_ascii=False, indent=None)
        source_material += f"""
--- AL-QURTUBI TAFSIR (Full JSON) ---
{q_str}
"""

    if not source_material.strip():
        source_material = "\n(No tafsir source material available for this verse)\n"

    # Build verse-map section
    verse_map_section = ""
    if verse_map_refs:
        refs_str = json.dumps(verse_map_refs, ensure_ascii=False, indent=2)
        verse_map_section = f"""
--- PRE-INDEXED VERSE REFERENCES (already mapped) ---
These references are already in the system. Focus on finding ADDITIONAL
connections that these don't cover:
{refs_str}
"""

    return f"""{ENHANCED_SCHOLARLY_CATALOG}

{FEW_SHOT_EXAMPLES}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERSE TO ANALYZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Surah: {surah_number} ({surah_name})
Verse: {verse_ref}

{source_material}
{verse_map_section}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analyze the verse above using the FULL tafsir commentary provided.

MATCHING STRATEGY:
1. ALWAYS include: asbab:surah={surah_number}:verse={verse_number}
2. ALWAYS include: thematic:surah={surah_number}:section=0
3. Read the Ibn Kathir commentary thoroughly — identify ALL themes discussed,
   not just what's in the verse text itself. Topic headers, hadith references,
   cross-references, and scholarly citations all reveal relevant themes.
4. If al-Qurtubi is available, use its legal rulings, historical context, and
   linguistic analysis to find additional thematic connections.
5. Match themes to the Ihya/Madarij/Riyad routing tables above.
6. Go BEYOND exact keyword matching — identify the UNDERLYING spiritual theme:
   - A verse about hardship/suffering → patience (sabr), even without the word
   - A verse about spending wealth → generosity AND renunciation (zuhd)
   - A verse warning about arrogance → Ihya pride chapter AND Madarij humility
   - A verse about God's attributes → trust/tawakkul, love/devotion
7. Prefer PRECISION over recall — only emit pointers for genuinely relevant
   connections. Don't force-match.
8. Maximum 10 pointers total.
9. Every pointer MUST follow the grammar: source_id:key=value:key=value:...

OUTPUT (strict JSON, nothing else):
{{
  "pointers": ["..."],
  "reasoning": "2-3 sentences explaining the thematic connections found"
}}"""


# ============================================================================
# GEMINI API CALL
# ============================================================================

async def call_gemini(session, prompt, token, verse_key=""):
    """Call Gemini API with retry logic. Returns parsed JSON or None."""
    endpoint = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{GCP_PROJECT}"
        f"/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"
    )

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generation_config": {
            "response_mime_type": "application/json",
            "temperature": 0.05,
            "top_k": 10,
            "top_p": 0.8,
            "maxOutputTokens": 8192,
        },
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    for attempt in range(MAX_RETRIES):
        retry_delay = 2 ** (attempt + 1) + random.uniform(0, 2)  # jitter to avoid thundering herd
        try:
            async with session.post(
                endpoint, headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=90)
            ) as resp:
                if resp.status == 429:
                    if attempt < MAX_RETRIES - 1:
                        print(f"    [{verse_key}] Rate limited (429), waiting {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        continue
                    return None

                if resp.status == 503:
                    if attempt < MAX_RETRIES - 1:
                        print(f"    [{verse_key}] Service unavailable (503), waiting {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        continue
                    return None

                if resp.status != 200:
                    err_text = await resp.text()
                    print(f"    [{verse_key}] Gemini error: HTTP {resp.status}: {err_text[:300]}")
                    return None

                data = await resp.json()

            candidates = data.get("candidates", [])
            if candidates:
                finish_reason = candidates[0].get("finishReason", "unknown")
                if finish_reason not in ("STOP", "stop"):
                    print(f"    [{verse_key}] finishReason: {finish_reason}")
            text = (
                candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if candidates else ""
            )

            if not text:
                return None

            # Parse JSON response
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                match = re.search(r"\{[\s\S]*\}", text)
                if match:
                    try:
                        return json.loads(match.group())
                    except json.JSONDecodeError:
                        pass
                print(f"    [{verse_key}] Failed to parse JSON ({len(text)} chars)")
                return None

        except asyncio.TimeoutError:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(retry_delay)
                continue
            return None
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(retry_delay)
                continue
            print(f"    [{verse_key}] Error: {type(e).__name__}: {e}")
            return None

    return None


def get_auth_token():
    """Get GCP auth token."""
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = GoogleRequest()
    credentials.refresh(auth_req)
    return credentials.token


# ============================================================================
# VALIDATION
# ============================================================================

# Valid pointer prefixes
VALID_SOURCES = {"asbab", "thematic", "ihya", "madarij", "riyad"}

def validate_plan(plan, surah, verse):
    """Validate a scholarly plan response. Returns (is_valid, reason)."""
    if not isinstance(plan, dict):
        return False, "Not a dict"

    pointers = plan.get("pointers")
    if not isinstance(pointers, list):
        return False, "No pointers list"

    if len(pointers) == 0:
        return False, "Empty pointers"

    if len(pointers) > MAX_POINTERS:
        return False, f"Too many pointers ({len(pointers)} > {MAX_POINTERS})"

    reasoning = plan.get("reasoning")
    if not reasoning or not isinstance(reasoning, str) or len(reasoning) < 10:
        return False, "Missing or too-short reasoning"

    # Validate each pointer format
    for p in pointers:
        if not isinstance(p, str):
            return False, f"Pointer not a string: {p}"
        parts = p.split(":")
        if len(parts) < 2:
            return False, f"Malformed pointer: {p}"
        source_id = parts[0]
        if source_id not in VALID_SOURCES:
            return False, f"Unknown source: {source_id} in {p}"

    return True, "ok"


# ============================================================================
# MERGE STRATEGY
# ============================================================================

def merge_plans(gemini_plan, det_plan, surah, verse):
    """
    Merge Gemini and deterministic plans.
    Gemini pointers come first (higher quality), then unique deterministic ones.
    """
    gemini_pointers = gemini_plan.get("pointers", []) if gemini_plan else []
    det_pointers = det_plan.get("pointers", []) if det_plan else []

    seen = set()
    merged = []
    origin = {}

    # Gemini pointers first
    for p in gemini_pointers:
        if p not in seen and len(merged) < MAX_POINTERS:
            seen.add(p)
            merged.append(p)
            origin[p] = "both" if p in det_pointers else "gemini"

    # Then unique deterministic pointers
    for p in det_pointers:
        if p not in seen and len(merged) < MAX_POINTERS:
            seen.add(p)
            merged.append(p)
            origin[p] = "deterministic"

    # Mark pointers that appear in both
    for p in merged:
        if p in gemini_pointers and p in det_pointers and origin[p] != "both":
            origin[p] = "both"

    reasoning = ""
    if gemini_plan and gemini_plan.get("reasoning"):
        reasoning = gemini_plan["reasoning"]
    elif det_plan and det_plan.get("reasoning"):
        reasoning = det_plan["reasoning"]

    return {
        "pointers": merged,
        "reasoning": reasoning,
        "origin": origin,
    }


# ============================================================================
# MAIN PROCESSING
# ============================================================================

async def process_verse(session, semaphore, token_holder, verse_info,
                        ibn_kathir, al_qurtubi, verse_map, results, stats,
                        verbose=False):
    """Process a single verse with semaphore-controlled concurrency."""
    surah, verse, surah_name = verse_info
    key = f"{surah}:{verse}"

    # Skip if already processed
    if key in results:
        return

    async with semaphore:
        # Gather verse data
        ik_json = ibn_kathir.get(key)
        q_json = al_qurtubi.get(key)
        vm_refs = verse_map.get(key, [])

        # Get deterministic plan (always available, pure Python)
        verse_text = ""
        ik_summary = ""
        if ik_json:
            verse_text = ik_json.get("verse_text", "")
            topics = ik_json.get("topics", [])
            if topics:
                ik_summary = " ".join(
                    t.get("topic_header", "") + " " + (t.get("commentary", "") or "")[:200]
                    for t in topics[:3]
                )[:500]

        det_plan = plan_scholarly_retrieval_deterministic(
            surah, verse, None, verse_text[:300], ik_summary
        )

        # Call Gemini with full context
        prompt = build_batch_planning_prompt(
            surah, verse, surah_name, ik_json, q_json, vm_refs
        )

        gemini_plan = await call_gemini(session, prompt, token_holder["token"], verse_key=key)

        if gemini_plan:
            is_valid, reason = validate_plan(gemini_plan, surah, verse)
            if is_valid:
                stats["gemini_success"] += 1
            else:
                if verbose:
                    print(f"  {key}: Gemini plan invalid ({reason})")
                stats["validation_fail"] += 1
                gemini_plan = None
        else:
            stats["gemini_fail"] += 1

        if gemini_plan is None:
            stats["deterministic_only"] += 1

        # Merge
        merged = merge_plans(gemini_plan, det_plan, surah, verse)
        results[key] = merged
        stats["success"] += 1
        stats["total_pointers"] += len(merged["pointers"])

        if verbose:
            src = "gemini+det" if gemini_plan else "det-only"
            print(f"\n  {key} ({surah_name}) [{src}]:")
            print(f"    Pointers ({len(merged['pointers'])}):")
            for p in merged["pointers"]:
                origin_tag = merged["origin"].get(p, "?")
                print(f"      [{origin_tag}] {p}")
            print(f"    Reasoning: {merged['reasoning']}")


async def process_all_verses_async(args):
    """Process all verses with parallel Gemini calls."""
    print("=" * 60)
    print(f"PRE-COMPUTE SCHOLARLY PLANS (concurrency={CONCURRENCY})")
    print("=" * 60)

    # Load tafsir sources
    ibn_kathir, al_qurtubi = load_tafsir_sources()
    verse_map = load_verse_map()

    # Get auth token
    print("\nAuthenticating with GCP...")
    token_holder = {"token": get_auth_token()}
    print("  Authenticated successfully")

    # Determine which verses to process
    verses_to_process = []
    for surah_num, info in sorted(QURAN_METADATA.items()):
        for verse_num in range(1, info["verses"] + 1):
            verses_to_process.append((surah_num, verse_num, info["name"]))

    # Apply filters
    if args.surah:
        verses_to_process = [
            (s, v, n) for s, v, n in verses_to_process if s == args.surah
        ]
    elif args.verse:
        s, v = map(int, args.verse.split(":"))
        verses_to_process = [(s, v, QURAN_METADATA[s]["name"])]
    elif args.resume_from:
        s, v = map(int, args.resume_from.split(":"))
        verses_to_process = [
            (si, vi, n) for si, vi, n in verses_to_process
            if si > s or (si == s and vi >= v)
        ]

    if args.dry_run:
        verses_to_process = verses_to_process[:10]

    total = len(verses_to_process)

    # Always load existing progress so --surah / --verse modes merge into it
    results = {}
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, encoding="utf-8") as f:
                existing = json.load(f)
            for key, val in existing.items():
                if key != "_metadata":
                    results[key] = val
            print(f"  Loaded {len(results)} existing results")
        except (json.JSONDecodeError, IOError) as e:
            print(f"  WARNING: Could not load existing results: {e}")

    # Filter out already-processed verses
    remaining = [(s, v, n) for s, v, n in verses_to_process if f"{s}:{v}" not in results]
    print(f"\nProcessing {len(remaining)} verses ({total - len(remaining)} already done)...")

    stats = {
        "success": 0, "gemini_success": 0, "gemini_fail": 0,
        "deterministic_only": 0, "validation_fail": 0, "total_pointers": 0,
    }

    start_time = time.time()
    semaphore = asyncio.Semaphore(CONCURRENCY)
    verbose = args.dry_run or args.verse

    # Process in chunks for progress reporting + incremental saves + token refresh
    chunk_size = SAVE_EVERY
    connector = aiohttp.TCPConnector(limit=CONCURRENCY + 5, limit_per_host=CONCURRENCY + 5)
    async with aiohttp.ClientSession(connector=connector) as session:
        for chunk_start in range(0, len(remaining), chunk_size):
            chunk = remaining[chunk_start : chunk_start + chunk_size]

            # Refresh token periodically
            if chunk_start > 0 and chunk_start % TOKEN_REFRESH_INTERVAL == 0:
                try:
                    token_holder["token"] = get_auth_token()
                    print("  Refreshed auth token")
                except Exception as e:
                    print(f"  WARNING: Token refresh failed: {e}")

            # Fire all requests in this chunk concurrently
            tasks = [
                process_verse(
                    session, semaphore, token_holder, v_info,
                    ibn_kathir, al_qurtubi, verse_map, results, stats,
                    verbose=verbose,
                )
                for v_info in chunk
            ]
            await asyncio.gather(*tasks)

            # Progress
            done = chunk_start + len(chunk)
            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed > 0 else 0
            eta = (len(remaining) - done) / rate if rate > 0 else 0
            gemini_pct = stats["gemini_success"] * 100 // max(stats["success"], 1)
            print(f"  [{done}/{len(remaining)}] {rate:.1f} v/s | "
                  f"ETA {eta/60:.1f}m | gemini={gemini_pct}% | "
                  f"fail={stats['gemini_fail']} val_fail={stats['validation_fail']}")

            # Save incrementally
            if not args.dry_run and done % SAVE_EVERY == 0:
                _save_output(results, stats, total)

    # Final save
    if not args.dry_run:
        _save_output(results, stats, total)

    # Print summary
    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"COMPLETE: {stats['success']}/{len(remaining)} verses in {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"  Gemini success:    {stats['gemini_success']}")
    print(f"  Gemini failed:     {stats['gemini_fail']}")
    print(f"  Validation failed: {stats['validation_fail']}")
    print(f"  Deterministic-only:{stats['deterministic_only']}")
    print(f"  Total pointers:    {stats['total_pointers']}")
    print(f"  Avg pointers/verse:{stats['total_pointers']/max(stats['success'],1):.1f}")
    print(f"  Throughput:        {stats['success']/max(elapsed,1):.1f} verses/sec")
    if not args.dry_run:
        print(f"\nOutput: {OUTPUT_FILE}")
    print("=" * 60)


def _save_output(results, stats, total):
    """Save results to output file with metadata."""
    output = {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": GEMINI_MODEL_ID,
            "total_verses": total,
            "successful": stats["success"],
            "gemini_success": stats["gemini_success"],
            "deterministic_only": stats["deterministic_only"],
            "failed": stats["gemini_fail"] + stats["validation_fail"],
            "version": "1.0",
        }
    }
    output.update(results)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=None, separators=(",", ":"))

    # Also save human-readable version for debugging
    debug_file = OUTPUT_FILE.with_suffix(".debug.json")
    with open(debug_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


# ============================================================================
# CLI
# ============================================================================

def main():
    global CONCURRENCY
    parser = argparse.ArgumentParser(
        description="Pre-compute scholarly plans for all Quran verses"
    )
    parser.add_argument(
        "--surah", type=int, help="Process only this surah number (1-114)"
    )
    parser.add_argument(
        "--verse", type=str, help="Process a single verse (e.g., 2:255)"
    )
    parser.add_argument(
        "--resume-from", type=str,
        help="Resume from surah:verse (e.g., 50:1)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Process only first 10 verses, print detailed output"
    )
    parser.add_argument(
        "--concurrency", type=int, default=CONCURRENCY,
        help=f"Number of parallel requests (default: {CONCURRENCY})"
    )
    args = parser.parse_args()
    CONCURRENCY = args.concurrency

    asyncio.run(process_all_verses_async(args))


if __name__ == "__main__":
    main()
