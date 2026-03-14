import os
import json
import re
import traceback
import time
import hashlib
import base64
import threading
import logging
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional, Dict, List, Any
from cryptography.fernet import Fernet

# Configure logging - use INFO in production, DEBUG for development
log_level = logging.DEBUG if os.environ.get('FLASK_DEBUG') else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from flask import Flask, request, jsonify
from flask_cors import CORS

import requests
import google.auth
from google.auth.transport.requests import Request as GoogleRequest

import firebase_admin
from firebase_admin import credentials, auth, firestore
from google.cloud import secretmanager
from google.cloud import firestore as gcp_firestore
from google.cloud.firestore import FieldFilter  # For new query syntax

# Imports for Vertex AI
import vertexai
from google.cloud import storage
from utils.text_cleaning import sanitize_heading_format, normalize_html_to_markdown
from services.source_service import (
    get_relevant_scholarly_context,
    extract_topic_keywords_from_query,
    get_scholarly_sources_metadata,
    build_scholarly_planning_prompt,
    resolve_scholarly_pointers,
    format_scholarly_excerpts_for_prompt,
    plan_scholarly_retrieval_deterministic,
)
from data.reading_plans import READING_PLANS
from data.iman_behaviors import (
    IMAN_CATEGORIES,
    IMAN_BEHAVIORS,
    BEHAVIOR_MAP,
    DEFAULT_BEHAVIORS,
    ALL_BEHAVIOR_IDS,
    HEART_NOTE_TYPES,
    HEART_STATES,
)
from data.iman_struggles import STRUGGLE_CATALOG, STRUGGLE_MAP, ALL_STRUGGLE_IDS
from data.iman_heart_states import HEART_STATE_MAP, ALL_HEART_STATE_IDS
from services.iman_service import (
    validate_behavior_value,
    validate_heart_note,
    validate_heart_state,
    build_default_config,
    get_tracked_behavior_ids,
    aggregate_category_scores,
    compute_baselines,
    recompute_trajectory,
    check_behavior_cap,
    should_show_anti_riya_reminder,
    get_recalibrating_comfort,
    get_welcome_back_message,
    compute_struggle_progress,
    prepare_digest_context,
    build_digest_prompt,
    prepare_daily_insight_context,
    build_daily_insight_prompt,
    compute_heart_note_patterns,
    compute_behavior_correlations,
    select_weekly_insight,
    compute_strain_recovery,
    compute_strain_trend,
    compute_safeguard_status,
    build_correlation_narrative_prompt,
    HEART_NOTE_LIMITS,
    MAX_TRACKED_BEHAVIORS,
    ENGINE_VERSION,
)

# --- App Initialization ---
app = Flask(__name__)
CORS(app, resources={r"/*": {
    "origins": [
        "http://localhost:3000",
        "https://tafsir-frontend-612616741510.us-central1.run.app"
    ]
}}, supports_credentials=True, max_age=86400)

# --- Configuration (UPDATED for new sliding window vector index) ---
# Firebase project (Auth, Firestore, Users, Quran texts)
FIREBASE_PROJECT = os.environ.get("FIREBASE_PROJECT", "tafsir-simplified-6b262")
# GCP infrastructure project (Vertex AI, GCS, Cloud Run)
GCP_INFRASTRUCTURE_PROJECT = os.environ.get("GCP_INFRASTRUCTURE_PROJECT", "tafsir-simplified")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-2.5-flash")  # Upgraded: 65K output tokens (vs 8K in 2.0) - eliminates truncation-based malformed JSON
FIREBASE_SECRET_FULL_PATH = os.environ.get("FIREBASE_SECRET_FULL_PATH")
REFLECTION_ENCRYPTION_SECRET = os.environ.get("REFLECTION_ENCRYPTION_SECRET", "")

GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "tafsir-simplified-sources")

# Verse limit per response — uniform across all personas.
# Dynamic: computed per-request by compute_max_end_verse(). This default
# is only used when precomputation hasn't run or as a prompt fallback.
VERSE_LIMIT_DEFAULT = 10

# Source coverage information
# Ibn Kathir: Complete Quran (114 Surahs)
# Al-Qurtubi: Surahs 1-4 (up to Surah 4, Verse 22)

# --- Startup Validation (Fail Fast) ---
if not FIREBASE_SECRET_FULL_PATH or not GCS_BUCKET_NAME:
    raise ValueError("CRITICAL STARTUP ERROR: Missing required environment variables")

# --- Helper Functions ---
def safe_get_nested(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely access nested dictionary keys without raising KeyError.

    Usage:
        safe_get_nested(response, "candidates", 0, "content", "parts", 0, "text")
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, (list, tuple)) and isinstance(key, int):
            try:
                current = current[key]
            except (IndexError, TypeError):
                return default
        else:
            return default

        if current is None:
            return default
    return current

# Global variables - UPDATED for dual database setup
users_db = None      # Firebase Admin SDK -> (default) database for users/auth
quran_db = None      # Google Cloud client -> tafsir-db database for Quran texts
TAFSIR_CHUNKS = {}   # Flattened text for direct verse lookup
VERSE_METADATA = {}  # Structured metadata for direct queries
RESPONSE_CACHE = {}  # In-memory cache
SCHOLARLY_PIPELINE_VERSION = "12.0"  # Bump: pre-computed scholarly plans (eliminates runtime Gemini planning call)
USER_RATE_LIMITS = defaultdict(list)  # Rate limiting
ANALYTICS = defaultdict(int)  # Usage analytics

# Thread safety locks
cache_lock = threading.Lock()
rate_limit_lock = threading.Lock()
analytics_lock = threading.Lock()

# ============================================================================
# REFLECTION ENCRYPTION (at-rest encryption for user reflections)
# ============================================================================

def _get_user_fernet(uid: str) -> Optional[Fernet]:
    """Derive a per-user Fernet key from UID + server secret via HMAC-SHA256."""
    if not REFLECTION_ENCRYPTION_SECRET:
        return None
    # HMAC-SHA256 produces 32 bytes → base64-encode for Fernet (which needs 32 url-safe base64 bytes)
    import hmac
    dk = hmac.new(
        REFLECTION_ENCRYPTION_SECRET.encode('utf-8'),
        uid.encode('utf-8'),
        hashlib.sha256
    ).digest()
    # Fernet requires a 32-byte url-safe base64-encoded key
    fernet_key = base64.urlsafe_b64encode(dk)
    return Fernet(fernet_key)


def _encrypt_text(text: str, uid: str) -> str:
    """Encrypt text for storage. Returns original text if encryption is not configured."""
    if not text:
        return text
    f = _get_user_fernet(uid)
    if not f:
        return text
    return f.encrypt(text.encode('utf-8')).decode('utf-8')


def _decrypt_text(token: str, uid: str) -> str:
    """Decrypt text from storage. Returns original text if decryption fails or is not configured."""
    if not token:
        return token
    f = _get_user_fernet(uid)
    if not f:
        return token
    try:
        return f.decrypt(token.encode('utf-8')).decode('utf-8')
    except Exception:
        # Data was stored before encryption was enabled — return as-is
        return token


# ============================================================================
# NEW: PERSONA SYSTEM FOR ADAPTIVE RESPONSES
# ============================================================================

# Consolidated persona system (5 personas)
# All personas use academic_prose format for consistent parsing
PERSONAS = {
    "new_revert": {
        "name": "New Revert",
        "tone": "warm, encouraging, patient",
        "vocabulary": "simple, everyday",
        "include_hadith": False,
        "scholarly_debates": False,
        "format_style": "academic_prose"
    },
    "curious_explorer": {
        "name": "Curious Explorer",
        "tone": "warm, reflective, inviting",
        "vocabulary": "accessible",
        "include_hadith": True,
        "scholarly_debates": False,
        "format_style": "academic_prose"
    },
    "practicing_muslim": {
        "name": "Practicing Muslim",
        "tone": "respectful, balanced",
        "vocabulary": "moderate",
        "include_hadith": True,
        "scholarly_debates": True,
        "format_style": "academic_prose"
    },
    "student": {
        "name": "Islamic Studies Student",
        "tone": "educational, comprehensive",
        "vocabulary": "academic",
        "include_hadith": True,
        "scholarly_debates": True,
        "format_style": "academic_prose"
    },
    "advanced_learner": {
        "name": "Advanced Learner",
        "tone": "academic, precise",
        "vocabulary": "advanced, technical",
        "include_hadith": True,
        "scholarly_debates": True,
        "format_style": "academic_prose"
    }
}

# --- Complete Quran Metadata for Verse Validation ---
QURAN_METADATA = {
    1: {"name": "Al-Fatihah", "verses": 7}, 2: {"name": "Al-Baqarah", "verses": 286}, 3: {"name": "Aal-E-Imran", "verses": 200},
    4: {"name": "An-Nisa", "verses": 176}, 5: {"name": "Al-Ma'idah", "verses": 120}, 6: {"name": "Al-An'am", "verses": 165},
    7: {"name": "Al-A'raf", "verses": 206}, 8: {"name": "Al-Anfal", "verses": 75}, 9: {"name": "At-Tawbah", "verses": 129},
    10: {"name": "Yunus", "verses": 109}, 11: {"name": "Hud", "verses": 123}, 12: {"name": "Yusuf", "verses": 111},
    13: {"name": "Ar-Ra'd", "verses": 43}, 14: {"name": "Ibrahim", "verses": 52}, 15: {"name": "Al-Hijr", "verses": 99},
    16: {"name": "An-Nahl", "verses": 128}, 17: {"name": "Al-Isra", "verses": 111}, 18: {"name": "Al-Kahf", "verses": 110},
    19: {"name": "Maryam", "verses": 98}, 20: {"name": "Taha", "verses": 135}, 21: {"name": "Al-Anbya", "verses": 112},
    22: {"name": "Al-Hajj", "verses": 78}, 23: {"name": "Al-Mu'minun", "verses": 118}, 24: {"name": "An-Nur", "verses": 64},
    25: {"name": "Al-Furqan", "verses": 77}, 26: {"name": "Ash-Shu'ara", "verses": 227}, 27: {"name": "An-Naml", "verses": 93},
    28: {"name": "Al-Qasas", "verses": 88}, 29: {"name": "Al-Ankabut", "verses": 69}, 30: {"name": "Ar-Rum", "verses": 60},
    31: {"name": "Luqman", "verses": 34}, 32: {"name": "As-Sajdah", "verses": 30}, 33: {"name": "Al-Ahzab", "verses": 73},
    34: {"name": "Saba", "verses": 54}, 35: {"name": "Fatir", "verses": 45}, 36: {"name": "Ya-Sin", "verses": 83},
    37: {"name": "As-Saffat", "verses": 182}, 38: {"name": "Sad", "verses": 88}, 39: {"name": "Az-Zumar", "verses": 75},
    40: {"name": "Ghafir", "verses": 85}, 41: {"name": "Fussilat", "verses": 54}, 42: {"name": "Ash-Shuraa", "verses": 53},
    43: {"name": "Az-Zukhruf", "verses": 89}, 44: {"name": "Ad-Dukhan", "verses": 59}, 45: {"name": "Al-Jathiyah", "verses": 37},
    46: {"name": "Al-Ahqaf", "verses": 35}, 47: {"name": "Muhammad", "verses": 38}, 48: {"name": "Al-Fath", "verses": 29},
    49: {"name": "Al-Hujurat", "verses": 18}, 50: {"name": "Qaf", "verses": 45}, 51: {"name": "Adh-Dhariyat", "verses": 60},
    52: {"name": "At-Tur", "verses": 49}, 53: {"name": "An-Najm", "verses": 62}, 54: {"name": "Al-Qamar", "verses": 55},
    55: {"name": "Ar-Rahman", "verses": 78}, 56: {"name": "Al-Waqi'ah", "verses": 96}, 57: {"name": "Al-Hadid", "verses": 29},
    58: {"name": "Al-Mujadila", "verses": 22}, 59: {"name": "Al-Hashr", "verses": 24}, 60: {"name": "Al-Mumtahanah", "verses": 13},
    61: {"name": "As-Saf", "verses": 14}, 62: {"name": "Al-Jumu'ah", "verses": 11}, 63: {"name": "Al-Munafiqun", "verses": 11},
    64: {"name": "At-Taghabun", "verses": 18}, 65: {"name": "At-Talaq", "verses": 12}, 66: {"name": "At-Tahrim", "verses": 12},
    67: {"name": "Al-Mulk", "verses": 30}, 68: {"name": "Al-Qalam", "verses": 52}, 69: {"name": "Al-Haqqah", "verses": 52},
    70: {"name": "Al-Ma'arij", "verses": 44}, 71: {"name": "Nuh", "verses": 28}, 72: {"name": "Al-Jinn", "verses": 28},
    73: {"name": "Al-Muzzammil", "verses": 20}, 74: {"name": "Al-Muddaththir", "verses": 56}, 75: {"name": "Al-Qiyamah", "verses": 40},
    76: {"name": "Al-Insan", "verses": 31}, 77: {"name": "Al-Mursalat", "verses": 50}, 78: {"name": "An-Naba", "verses": 40},
    79: {"name": "An-Nazi'at", "verses": 46}, 80: {"name": "Abasa", "verses": 42}, 81: {"name": "At-Takwir", "verses": 29},
    82: {"name": "Al-Infitar", "verses": 19}, 83: {"name": "Al-Mutaffifin", "verses": 36}, 84: {"name": "Al-Inshiqaq", "verses": 25},
    85: {"name": "Al-Buruj", "verses": 22}, 86: {"name": "At-Tariq", "verses": 17}, 87: {"name": "Al-A'la", "verses": 19},
    88: {"name": "Al-Ghashiyah", "verses": 26}, 89: {"name": "Al-Fajr", "verses": 30}, 90: {"name": "Al-Balad", "verses": 20},
    91: {"name": "Ash-Shams", "verses": 15}, 92: {"name": "Al-Layl", "verses": 21}, 93: {"name": "Ad-Duhaa", "verses": 11},
    94: {"name": "Ash-Sharh", "verses": 8}, 95: {"name": "At-Tin", "verses": 8}, 96: {"name": "Al-Alaq", "verses": 19},
    97: {"name": "Al-Qadr", "verses": 5}, 98: {"name": "Al-Bayyinah", "verses": 8}, 99: {"name": "Az-Zalzalah", "verses": 8},
    100: {"name": "Al-Adiyat", "verses": 11}, 101: {"name": "Al-Qari'ah", "verses": 11}, 102: {"name": "At-Takathur", "verses": 8},
    103: {"name": "Al-Asr", "verses": 3}, 104: {"name": "Al-Humazah", "verses": 9}, 105: {"name": "Al-Fil", "verses": 5},
    106: {"name": "Quraysh", "verses": 4}, 107: {"name": "Al-Ma'un", "verses": 7}, 108: {"name": "Al-Kawthar", "verses": 3},
    109: {"name": "Al-Kafirun", "verses": 6}, 110: {"name": "An-Nasr", "verses": 3}, 111: {"name": "Al-Masad", "verses": 5},
    112: {"name": "Al-Ikhlas", "verses": 4}, 113: {"name": "Al-Falaq", "verses": 5}, 114: {"name": "An-Nas", "verses": 6}
}

SURAHS_BY_NAME = {info["name"].lower(): num for num, info in QURAN_METADATA.items()}

# SURAH_NAME_ALIASES: Handle common misspellings and variations
SURAH_NAME_ALIASES = {
    # Common misspellings and variations
    'fatiha': 'al-fatihah',
    'fatihah': 'al-fatihah',
    'al-fatiha': 'al-fatihah',
    'opening': 'al-fatihah',

    'baqara': 'al-baqarah',
    'baqarah': 'al-baqarah',
    'cow': 'al-baqarah',
    'the cow': 'al-baqarah',

    'imran': 'ali imran',
    'al-imran': 'ali imran',
    'aal imran': 'ali imran',
    'aal-imran': 'ali imran',
    'family of imran': 'ali imran',

    'nisa': 'an-nisa',
    'women': 'an-nisa',
    'the women': 'an-nisa',

    'maida': 'al-ma\'idah',
    'maidah': 'al-ma\'idah',
    'table': 'al-ma\'idah',
    'table spread': 'al-ma\'idah',

    'anam': 'al-an\'am',
    'cattle': 'al-an\'am',
    'livestock': 'al-an\'am',

    'araf': 'al-a\'raf',
    'heights': 'al-a\'raf',

    'anfal': 'al-anfal',
    'spoils': 'al-anfal',
    'spoils of war': 'al-anfal',

    'tawba': 'at-tawbah',
    'taubah': 'at-tawbah',
    'repentance': 'at-tawbah',
    'baraat': 'at-tawbah',

    'yunus': 'yunus',
    'jonah': 'yunus',

    'hud': 'hud',

    'yusuf': 'yusuf',
    'joseph': 'yusuf',

    'rad': 'ar-ra\'d',
    'thunder': 'ar-ra\'d',

    'ibrahim': 'ibrahim',
    'abraham': 'ibrahim',

    'hijr': 'al-hijr',
    'rocky tract': 'al-hijr',

    'nahl': 'an-nahl',
    'bee': 'an-nahl',
    'bees': 'an-nahl',

    'isra': 'al-isra',
    'night journey': 'al-isra',
    'bani israel': 'al-isra',
    'children of israel': 'al-isra',

    'kahf': 'al-kahf',
    'cave': 'al-kahf',

    'maryam': 'maryam',
    'mary': 'maryam',

    'taha': 'ta-ha',

    'anbiya': 'al-anbya',
    'prophets': 'al-anbya',

    'hajj': 'al-hajj',
    'pilgrimage': 'al-hajj',

    'muminun': 'al-mu\'minun',
    'believers': 'al-mu\'minun',

    'nur': 'an-nur',
    'light': 'an-nur',

    'furqan': 'al-furqan',
    'criterion': 'al-furqan',

    'shuara': 'ash-shu\'ara',
    'poets': 'ash-shu\'ara',

    'naml': 'an-naml',
    'ant': 'an-naml',
    'ants': 'an-naml',

    'qasas': 'al-qasas',
    'stories': 'al-qasas',
    'narration': 'al-qasas',

    'ankabut': 'al-\'ankabut',
    'spider': 'al-\'ankabut',

    'rum': 'ar-rum',
    'romans': 'ar-rum',
    'rome': 'ar-rum',

    'luqman': 'luqman',

    'sajda': 'as-sajdah',
    'sajdah': 'as-sajdah',
    'prostration': 'as-sajdah',

    'ahzab': 'al-ahzab',
    'confederates': 'al-ahzab',
    'clans': 'al-ahzab',

    'saba': 'saba',
    'sheba': 'saba',

    'fatir': 'fatir',
    'originator': 'fatir',
    'creator': 'fatir',

    'yasin': 'ya-sin',
    'yaseen': 'ya-sin',

    'saffat': 'as-saffat',
    'ranks': 'as-saffat',

    'sad': 'sad',

    'zumar': 'az-zumar',
    'groups': 'az-zumar',
    'crowds': 'az-zumar',

    'ghafir': 'ghafir',
    'forgiver': 'ghafir',
    'mumin': 'ghafir',
    'believer': 'ghafir',

    'fussilat': 'fussilat',
    'explained': 'fussilat',
    'ha mim': 'fussilat',

    'shura': 'ash-shura',
    'consultation': 'ash-shura',

    'zukhruf': 'az-zukhruf',
    'ornaments': 'az-zukhruf',
    'gold': 'az-zukhruf',

    'dukhan': 'ad-dukhan',
    'smoke': 'ad-dukhan',

    'jathiya': 'al-jathiyah',
    'jathiyah': 'al-jathiyah',
    'kneeling': 'al-jathiyah',

    'ahqaf': 'al-ahqaf',
    'dunes': 'al-ahqaf',

    'muhammad': 'muhammad',
    'qital': 'muhammad',
    'fighting': 'muhammad',

    'fath': 'al-fath',
    'victory': 'al-fath',
    'conquest': 'al-fath',

    'hujurat': 'al-hujurat',
    'rooms': 'al-hujurat',
    'chambers': 'al-hujurat',

    'qaf': 'qaf',

    'dhariyat': 'adh-dhariyat',
    'winds': 'adh-dhariyat',

    'tur': 'at-tur',
    'mount': 'at-tur',

    'najm': 'an-najm',
    'star': 'an-najm',

    'qamar': 'al-qamar',
    'moon': 'al-qamar',

    'rahman': 'ar-rahman',
    'merciful': 'ar-rahman',
    'beneficent': 'ar-rahman',

    'waqiah': 'al-waqi\'ah',
    'event': 'al-waqi\'ah',
    'inevitable': 'al-waqi\'ah',

    'hadid': 'al-hadid',
    'iron': 'al-hadid',

    'mujadila': 'al-mujadila',
    'mujadilah': 'al-mujadila',
    'disputation': 'al-mujadila',

    'hashr': 'al-hashr',
    'gathering': 'al-hashr',
    'exile': 'al-hashr',

    'mumtahina': 'al-mumtahanah',
    'mumtahanah': 'al-mumtahanah',
    'examined': 'al-mumtahanah',

    'saff': 'as-saff',
    'row': 'as-saff',
    'ranks': 'as-saff',

    'jumuah': 'al-jumu\'ah',
    'friday': 'al-jumu\'ah',
    'congregation': 'al-jumu\'ah',

    'munafiqun': 'al-munafiqun',
    'hypocrites': 'al-munafiqun',

    'taghabun': 'at-taghabun',
    'loss and gain': 'at-taghabun',

    'talaq': 'at-talaq',
    'divorce': 'at-talaq',

    'tahrim': 'at-tahrim',
    'prohibition': 'at-tahrim',

    'mulk': 'al-mulk',
    'dominion': 'al-mulk',
    'sovereignty': 'al-mulk',

    'qalam': 'al-qalam',
    'pen': 'al-qalam',

    'haqqah': 'al-haqqah',
    'reality': 'al-haqqah',
    'inevitable': 'al-haqqah',

    'maarij': 'al-ma\'arij',
    'ascending': 'al-ma\'arij',

    'nuh': 'nuh',
    'noah': 'nuh',

    'jinn': 'al-jinn',

    'muzzammil': 'al-muzzammil',
    'wrapped': 'al-muzzammil',
    'enshrouded': 'al-muzzammil',

    'muddathir': 'al-muddaththir',
    'muddaththir': 'al-muddaththir',
    'cloaked': 'al-muddaththir',

    'qiyama': 'al-qiyamah',
    'qiyamah': 'al-qiyamah',
    'resurrection': 'al-qiyamah',

    'insan': 'al-insan',
    'dahr': 'al-insan',
    'man': 'al-insan',
    'time': 'al-insan',

    'mursalat': 'al-mursalat',
    'sent forth': 'al-mursalat',

    'naba': 'an-naba',
    'tidings': 'an-naba',
    'announcement': 'an-naba',

    'naziat': 'an-nazi\'at',
    'pluckers': 'an-nazi\'at',

    'abasa': '\'abasa',
    'frowned': '\'abasa',

    'takwir': 'at-takwir',
    'folding': 'at-takwir',

    'infitar': 'al-infitar',
    'cleaving': 'al-infitar',

    'mutaffifin': 'al-mutaffifin',
    'defrauders': 'al-mutaffifin',

    'inshiqaq': 'al-inshiqaq',
    'splitting': 'al-inshiqaq',

    'buruj': 'al-buruj',
    'constellations': 'al-buruj',

    'tariq': 'at-tariq',
    'nightcomer': 'at-tariq',

    'ala': 'al-a\'la',
    'most high': 'al-a\'la',

    'ghashiya': 'al-ghashiyah',
    'ghashiyah': 'al-ghashiyah',
    'overwhelming': 'al-ghashiyah',

    'fajr': 'al-fajr',
    'dawn': 'al-fajr',

    'balad': 'al-balad',
    'city': 'al-balad',

    'shams': 'ash-shams',
    'sun': 'ash-shams',

    'layl': 'al-layl',
    'lail': 'al-layl',
    'night': 'al-layl',

    'duha': 'ad-duha',
    'forenoon': 'ad-duha',
    'morning': 'ad-duha',

    'sharh': 'ash-sharh',
    'inshirah': 'ash-sharh',
    'expansion': 'ash-sharh',

    'tin': 'at-tin',
    'fig': 'at-tin',

    'alaq': 'al-\'alaq',
    'clot': 'al-\'alaq',
    'clinging': 'al-\'alaq',

    'qadr': 'al-qadr',
    'power': 'al-qadr',
    'decree': 'al-qadr',

    'bayyina': 'al-bayyinah',
    'bayyinah': 'al-bayyinah',
    'evidence': 'al-bayyinah',

    'zalzalah': 'az-zalzalah',
    'zalzala': 'az-zalzalah',
    'earthquake': 'az-zalzalah',

    'adiyat': 'al-\'adiyat',
    'chargers': 'al-\'adiyat',

    'qariah': 'al-qari\'ah',
    'calamity': 'al-qari\'ah',

    'takathur': 'at-takathur',
    'competition': 'at-takathur',

    'asr': 'al-\'asr',
    'time': 'al-\'asr',
    'epoch': 'al-\'asr',

    'humazah': 'al-humazah',
    'slanderer': 'al-humazah',

    'fil': 'al-fil',
    'feel': 'al-fil',
    'elephant': 'al-fil',

    'quraysh': 'quraysh',
    'quraish': 'quraysh',

    'maun': 'al-ma\'un',
    'assistance': 'al-ma\'un',

    'kawthar': 'al-kawthar',
    'kauther': 'al-kawthar',
    'abundance': 'al-kawthar',

    'kafirun': 'al-kafirun',
    'disbelievers': 'al-kafirun',

    'nasr': 'an-nasr',
    'help': 'an-nasr',
    'victory': 'an-nasr',

    'masad': 'al-masad',
    'lahab': 'al-masad',
    'palm fiber': 'al-masad',

    'ikhlas': 'al-ikhlas',
    'sincerity': 'al-ikhlas',
    'purity': 'al-ikhlas',

    'falaq': 'al-falaq',
    'daybreak': 'al-falaq',

    'nas': 'an-nas',
    'mankind': 'an-nas',
    'people': 'an-nas',
}

# Apply aliases to create expanded SURAHS_BY_NAME
SURAHS_BY_NAME_WITH_ALIASES = dict(SURAHS_BY_NAME)
for alias, actual_name in SURAH_NAME_ALIASES.items():
    if actual_name in SURAHS_BY_NAME:
        SURAHS_BY_NAME_WITH_ALIASES[alias] = SURAHS_BY_NAME[actual_name]

# Update the main dictionary to include aliases
SURAHS_BY_NAME.update(SURAHS_BY_NAME_WITH_ALIASES)

# Persona-specific query suggestions
# Each persona gets relevant suggestions based on their knowledge level and needs
# Import persona-specific suggestions
from persona_suggestions import PERSONA_SUGGESTIONS, DEFAULT_SUGGESTIONS

# Legacy QUERY_SUGGESTIONS_BANK for backwards compatibility
QUERY_SUGGESTIONS_BANK = {
    "tafsir": [
        # Direct verse references - Key verses from your organization
        "1:1-7",  # Al-Fatihah: praise, guidance, mercy
        "2:255",  # Ayatul Kursi
        "2:256",  # No compulsion in religion
        "2:282",  # Accountability in transactions
        "2:286",  # No soul burdened beyond capacity
        "3:190-200",  # Reflecting on creation and signs
        "4:1",  # Humanity from a single soul
        "17:23-24",  # Parents' rights and respect
        "18:65-82",  # Khidr and Musa story
        "24:35",  # Allah as Light
        "30:21",  # Marriage, love, and mercy
        "36:1-7",  # Ya-Sin opening
        "39:53",  # Allah's boundless mercy
        "93:1-11",  # Ad-Duha: comfort and reassurance
        "112:1-4",  # Al-Ikhlas: Allah's oneness

        # Direct tafsir requests
        "Explain Surah Al-Fatihah",
        "Commentary on Ayatul Kursi",
        "Meaning of Surah Al-Ikhlas",
        "Tafsir of verse 39:53 about Allah's mercy",
        "Explain verse 2:256 about religious freedom",

        # Metadata-specific queries for tafsir approach
        "What hadith are mentioned in verse 2:255?",
        "Linguistic analysis of Ayatul Kursi",
        "Cross references for verse 30:21",
        "Legal rulings from verse 2:282 about debt",
        "Scholar opinions on verse 2:256",
        "Ibn Kathir's commentary on verse 39:53",
        "Al-Qurtubi's legal analysis of verse 2:282",
        "Grammatical structure of verse 1:5",
        "Prophetic narrations about Surah Al-Fatihah"
    ],
    "explore": [
        # 1. Mercy, Forgiveness, and Hope
        "Allah's boundless mercy and forgiveness",
        "How does the Quran describe Allah's mercy?",
        "Verses about repentance and forgiveness",
        "Finding hope in difficult times",
        "Allah loves those who repent",

        # 2. Reflection and Signs of Allah
        "Signs of Allah in creation",
        "Reflecting on the natural world",
        "Universe as evidence of Allah's power",
        "Signs in night and day alternation",

        # 3. Guidance, Care, and Protection
        "How does Allah guide and protect believers?",
        "Seeking knowledge and guidance",
        "Allah's straight path",
        "Divine protection and care",

        # 4. Creation, Life, and Human Responsibility
        "Stages of human creation",
        "Everything created in pairs",
        "Human responsibility and stewardship",
        "Purpose of life according to Quran",

        # 5. Family, Social Ethics, and Relationships
        "Parents' rights in Islam",
        "Marriage as mercy and harmony",
        "Justice and kindness to neighbors",
        "Family ethics in the Quran",
        "Social responsibility and equality",

        # 6. Knowledge, Wisdom, and Accountability
        "Elevation through knowledge",
        "Avoiding assumptions and judging with evidence",
        "Accountability in transactions",
        "Knowledge vs mere hearing",

        # 7. Prophets, Stories, and Lessons
        "Story of Prophet Yusuf and patience",
        "Prophet Ibrahim's trials",
        "Maryam and Isa's miraculous birth",
        "Creation of Adam and Iblis' arrogance",
        "Prophet Musa and Khidr's journey",

        # 8. Themes and Concepts
        "What does the Quran say about patience?",
        "Concept of Tawakkul (trust in Allah)",
        "Dealing with anxiety and hardship",
        "Charity and its spiritual rewards",
        "Overcoming envy and jealousy",
        "Warnings against pride and arrogance",
        "Description of Paradise",

        # Metadata exploration queries
        "Which verses have the most hadith narrations?",
        "Linguistic miracles in the Quran",
        "Legal principles from Quranic verses",
        "Verses with multiple interpretations",
        "Differences between Al-Qurtubi and Ibn Kathir",
        "Most cited verses by classical scholars",
        "Rhetorical devices in Meccan surahs"
    ]
}

# Keep "semantic" as an alias for "explore" for backwards compatibility
QUERY_SUGGESTIONS_BANK["semantic"] = QUERY_SUGGESTIONS_BANK["explore"]

# Legacy format for backwards compatibility
QUERY_SUGGESTIONS = (
    QUERY_SUGGESTIONS_BANK["tafsir"] +
    QUERY_SUGGESTIONS_BANK["semantic"]
)

# Verse cross-references database (simplified)
VERSE_CROSS_REFS = {
    "2:255": ["2:256", "7:180", "59:23", "112:1-4"],
    "1:1": ["113:1", "114:1", "17:110", "96:1"],
    "charity": ["2:261-274", "9:60", "57:7", "63:10"],
    "prayer": ["2:43", "4:103", "20:14", "62:9-10"]
}

# Source authority weights by query type
SOURCE_WEIGHTS = {
    "legal": {"al-Qurtubi": 0.6, "Ibn Kathir": 0.4},
    "historical": {"Ibn Kathir": 0.6, "al-Qurtubi": 0.4},
    "concise": {"al-Qurtubi": 0.5, "Ibn Kathir": 0.5},
    "default": {"Ibn Kathir": 0.5, "al-Qurtubi": 0.5}
}

# ============================================================================
# NEW: ENHANCED QUERY CLASSIFICATION SYSTEM
# ============================================================================

# Named verses mapping (common references) - EXPANDED
NAMED_VERSES = {
    # Ayat al-Kursi variations
    'ayat al-kursi': (2, 255),
    'ayat al kursi': (2, 255),
    'ayah al-kursi': (2, 255),
    'ayah al kursi': (2, 255),
    'ayatul kursi': (2, 255),
    'throne verse': (2, 255),
    'verse of the throne': (2, 255),
    'greatest verse': (2, 255),

    # Light verse variations
    'light verse': (24, 35),
    'verse of light': (24, 35),
    'ayat an-nur': (24, 35),
    'ayah an-nur': (24, 35),
    'ayat al-nur': (24, 35),
    'ayah al-nur': (24, 35),
    'ayatul nur': (24, 35),

    # Financial/Legal verses
    'debt verse': (2, 282),
    'longest verse': (2, 282),  # It's the longest verse in the Quran
    'verse of debt': (2, 282),
    'riba verse': (2, 275),
    'usury verse': (2, 275),
    'inheritance verse': (4, 11),
    'verse of inheritance': (4, 11),

    # Opening and closing
    'bismillah': (1, 1),
    'basmala': (1, 1),
    'fatiha': (1, 1),
    'al-fatiha': (1, 1),
    'opening': (1, 1),
    'last verse': (110, 3),  # Last verse of last complete surah
    'verse of refuge': (113, 1),  # Al-Falaq
    'verse of mankind': (114, 1),  # An-Nas

    # Verses about specific topics
    'hijab verse': (24, 31),
    'veil verse': (24, 31),
    'modesty verse': (24, 31),
    'sword verse': (9, 5),
    'verse of the sword': (9, 5),
    'patience verse': (2, 153),
    'verse of patience': (2, 153),

    # Verses about prophets
    'verse of jesus': (3, 45),
    'verse of mary': (3, 42),
    'verse of moses': (28, 7),
    'verse of abraham': (2, 124),
    'verse of noah': (71, 1),

    # Important theological verses
    'tawhid verse': (112, 1),
    'verse of oneness': (112, 1),
    'no compulsion verse': (2, 256),
    'verse of no compulsion': (2, 256),
    'freedom of religion': (2, 256),

    # Verses about worship
    'qibla verse': (2, 144),
    'verse of qibla': (2, 144),
    'fasting verse': (2, 183),
    'verse of fasting': (2, 183),
    'hajj verse': (3, 97),
    'verse of hajj': (3, 97),
    'zakat verse': (2, 43),
    'verse of zakat': (2, 43),

    # Night journey
    'isra verse': (17, 1),
    'night journey verse': (17, 1),
    'verse of night journey': (17, 1),

    # End times
    'verse of the hour': (7, 187),
    'judgment verse': (82, 1),
    'verse of judgment': (82, 1),

    # Miracles and signs
    'spider verse': (29, 41),
    'verse of spider': (29, 41),
    'bee verse': (16, 68),
    'verse of bee': (16, 68),
    'ant verse': (27, 18),
    'verse of ant': (27, 18),
}

def normalize_query_text(query: str) -> str:
    """Normalize query for comprehensive pattern matching"""
    query = query.lower().strip()

    # Normalize apostrophes (curly quotes to straight quotes)
    query = query.replace("'", "'").replace("'", "'").replace("`", "'")

    # PHASE 1: Strip natural language prefixes (do this first)
    natural_prefixes = [
        r'^(show me|give me|tell me about|tell me|explain|what is|what does|what are)\s+',
        r'^(i want to read|i want to see|i want|please show|please|can you show|can you)\s+',
        r'^(display|get|fetch|find|search for|look up|lookup)\s+',
    ]
    for prefix in natural_prefixes:
        query = re.sub(prefix, '', query, flags=re.IGNORECASE)

    # PHASE 2: Comprehensive word replacements
    replacements = {
        # Surah variations
        r'\bsura\b': 'surah',
        r'\bsurat\b': 'surah',
        r'\bsoorah\b': 'surah',
        r'\bchapter\b': 'surah',
        r'\bch\b\.?(?=\s*\d)': 'surah',  # ch2 or ch. 2 -> surah 2

        # Verse variations
        r'\bayat\b': 'ayah',
        r'\bayaat\b': 'ayah',
        r'\baya\b': 'ayah',
        r'\bayet\b': 'ayah',  # Turkish variant
        r'\bverses\b': 'verse',
        r'\bayahs\b': 'ayah',
        r'\bv\.?(?=\s*\d)': 'verse',  # v255 or v. 255 -> verse 255

        # Range connectors (normalize to hyphen)
        r'\s+to\s+': '-',
        r'\s+through\s+': '-',
        r'\s+till\s+': '-',
        r'\s+until\s+': '-',
        r'\s+thru\s+': '-',
        r'\s+and\s+': '-',  # for "255 and 256" -> "255-256"

        # Other normalizations
        'cited by': 'cited',
        'mentions': 'mentioned',

        # Remove trailing punctuation
        r'[.!?]+$': '',
    }
    for pattern, replacement in replacements.items():
        query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)

    return query.strip()

def extract_verse_reference_enhanced(query: str) -> Optional[Tuple[int, int]]:
    """
    Extract verse reference using multiple strategies.
    Returns (surah, start_verse) for single verses or verse ranges.
    NOTE: For ranges like 3:190-191, returns (3, 190) - the first verse.
    Use extract_verse_range() to get full range details.
    """
    query_normalized = normalize_query_text(query)

    # Strategy 1: Named verses
    for name, ref in NAMED_VERSES.items():
        if name in query_normalized:
            return ref

    # Strategy 2: Numeric patterns (including ranges and various separators)
    patterns = [
        # Colon patterns
        r'\b(\d{1,3}):(\d{1,3})(?:-\d{1,3})?\b',  # 2:255 or 2:255-256
        r'\b(\d{1,3})\s*:\s*(\d{1,3})(?:\s*-\s*\d{1,3})?\b',  # 2 : 255 or 2 : 255 - 256

        # Period and dot patterns
        r'\b(\d{1,3})\.(\d{1,3})(?:-\d{1,3})?\b',  # 2.255 or 2.255-256
        r'\b(\d{1,3})\s*\.\s*(\d{1,3})(?:\s*-\s*\d{1,3})?\b',  # 2 . 255

        # Slash patterns
        r'\b(\d{1,3})/(\d{1,3})(?:-\d{1,3})?\b',  # 2/255

        # Explicit surah/verse patterns
        r'surah\s+(\d{1,3})\s+(?:verse|ayah|ayat|verses?)\s+(\d{1,3})',  # surah 2 verse 255
        r's(\d{1,3})v(\d{1,3})\b',  # s2v255 (abbreviated)
        r'ch(?:apter)?\s*(\d{1,3})\s*v(?:erse)?\s*(\d{1,3})',  # ch2v255 or chapter 2 verse 255

        # Reversed patterns (verse X of surah Y)
        r'(?:verse|ayah|ayat)\s+(\d{1,3})\s+(?:of|from|in)\s+surah\s+(\d{1,3})',  # verse 255 of surah 2
    ]

    for pattern in patterns:
        match = re.search(pattern, query_normalized)
        if match:
            try:
                # Handle reversed pattern (last pattern has verse first, surah second)
                if 'of|from|in' in pattern:
                    verse = int(match.group(1))
                    surah = int(match.group(2))
                else:
                    surah = int(match.group(1))
                    verse = int(match.group(2))

                is_valid, _ = validate_verse_reference(surah, verse)
                if is_valid:
                    return (surah, verse)
            except (ValueError, IndexError):
                continue

    # Strategy 3: Surah name patterns with various formats
    for surah_name, surah_num in sorted(SURAHS_BY_NAME.items(), key=lambda x: len(x[0]), reverse=True):
        if surah_name in query_normalized:
            # Multiple patterns for surah name + verse
            patterns = [
                # Standard patterns
                rf'{re.escape(surah_name)}[^\d]*(\d{{1,3}})',  # Al-Baqarah 255
                rf'{re.escape(surah_name)}[,\s]+(?:verse|ayah|ayat|v\.?)\s*(\d{{1,3}})',  # Al-Baqarah, verse 255

                # Comma-separated pattern (the one that was failing)
                rf'{re.escape(surah_name)}\s*,\s*(?:verse|ayah|ayat|v\.?)?\s*(\d{{1,3}})',  # Al-Baqarah, 255 or Al-Baqarah, Verse 6

                # Reversed patterns
                rf'(?:verse|ayah|ayat|v\.?)\s+(\d{{1,3}})\s+(?:of|from|in)\s+{re.escape(surah_name)}',  # verse 255 of Al-Baqarah
                rf'(\d{{1,3}})\s+(?:of|from|in)\s+{re.escape(surah_name)}',  # 255 of Al-Baqarah

                # Parenthetical patterns
                rf'{re.escape(surah_name)}\s*\((\d{{1,3}})\)',  # Al-Baqarah (255)
                rf'{re.escape(surah_name)}\s*\[(\d{{1,3}})\]',  # Al-Baqarah [255]
            ]

            for pattern in patterns:
                match = re.search(pattern, query_normalized)
                if match:
                    try:
                        verse_num = int(match.group(1))
                        is_valid, _ = validate_verse_reference(surah_num, verse_num)
                        if is_valid:
                            return (surah_num, verse_num)
                    except (ValueError, IndexError):
                        continue

    return None

def extract_verse_range(query: str) -> Optional[Tuple[int, int, int]]:
    """
    Extract verse RANGE from query.
    Returns (surah, start_verse, end_verse) or None.
    Examples: "3:190-191" -> (3, 190, 191), "2:255" -> (2, 255, 255)
              "As-Sajdah 1-9" -> (32, 1, 9), "Surah Al-Baqarah verse 255-257" -> (2, 255, 257)
    """
    query_normalized = normalize_query_text(query)

    # Strategy 1: Surah name + verse range (e.g., "As-Sajdah 1-9", "Surah Al-Baqarah verse 1-5")
    # Sort by length (longest first) to avoid substring matching issues
    for surah_name, surah_num in sorted(SURAHS_BY_NAME.items(), key=lambda x: len(x[0]), reverse=True):
        if surah_name in query_normalized:
            # Try various patterns for verse ranges with surah names
            patterns = [
                # Standard range patterns
                rf'{re.escape(surah_name)}[^\d]*(\d{{1,3}})\s*-\s*(\d{{1,3}})',  # "As-Sajdah 1-9"
                rf'{re.escape(surah_name)}[^\d]*verse[s]?\s+(\d{{1,3}})\s*-\s*(\d{{1,3}})',  # "As-Sajdah verse 1-9"
                rf'{re.escape(surah_name)}[^\d]*ayah[s]?\s+(\d{{1,3}})\s*-\s*(\d{{1,3}})',  # "As-Sajdah ayah 1-9"

                # Comma-separated ranges
                rf'{re.escape(surah_name)}\s*,\s*(?:verse[s]?|ayah[s]?)?\s*(\d{{1,3}})\s*-\s*(\d{{1,3}})',  # "As-Sajdah, verses 1-9"

                # Reversed patterns with ranges
                rf'verse[s]?\s+(\d{{1,3}})\s*-\s*(\d{{1,3}})\s+(?:of|from|in)\s+{re.escape(surah_name)}',  # "verses 1-9 of As-Sajdah"
                rf'ayah[s]?\s+(\d{{1,3}})\s*-\s*(\d{{1,3}})\s+(?:of|from|in)\s+{re.escape(surah_name)}',  # "ayahs 1-9 from As-Sajdah"
            ]

            for pattern in patterns:
                match = re.search(pattern, query_normalized)
                if match:
                    try:
                        start_verse = int(match.group(1))
                        end_verse = int(match.group(2))

                        # Validate both verses
                        is_valid_start, _ = validate_verse_reference(surah_num, start_verse)
                        is_valid_end, _ = validate_verse_reference(surah_num, end_verse)

                        if is_valid_start and is_valid_end and start_verse <= end_verse:
                            return (surah_num, start_verse, end_verse)
                    except (ValueError, IndexError):
                        continue

    # Strategy 2: Numeric patterns with various separators
    range_patterns = [
        # Colon patterns
        r'\b(\d{1,3}):(\d{1,3})-(\d{1,3})\b',  # 3:190-191
        r'\b(\d{1,3})\s*:\s*(\d{1,3})\s*-\s*(\d{1,3})\b',  # 3 : 190 - 191

        # Period/dot patterns
        r'\b(\d{1,3})\.(\d{1,3})-(\d{1,3})\b',  # 3.190-191
        r'\b(\d{1,3})\s*\.\s*(\d{1,3})\s*-\s*(\d{1,3})\b',  # 3 . 190 - 191

        # Slash patterns
        r'\b(\d{1,3})/(\d{1,3})-(\d{1,3})\b',  # 3/190-191

        # Explicit surah/verse range patterns
        r'surah\s+(\d{1,3})\s+(?:verse[s]?|ayah[s]?)\s+(\d{1,3})\s*-\s*(\d{1,3})',  # surah 3 verses 190-191
        r'ch(?:apter)?\s*(\d{1,3})\s*v(?:erse[s]?)?\s*(\d{1,3})\s*-\s*(\d{1,3})',  # ch3v190-191 or chapter 3 verses 190-191
    ]

    for range_pattern in range_patterns:
        match = re.search(range_pattern, query_normalized)
        if match:
            try:
                surah = int(match.group(1))
                start_verse = int(match.group(2))
                end_verse = int(match.group(3))

                # Validate both verses
                is_valid_start, _ = validate_verse_reference(surah, start_verse)
                is_valid_end, _ = validate_verse_reference(surah, end_verse)

                if is_valid_start and is_valid_end and start_verse <= end_verse:
                    return (surah, start_verse, end_verse)
            except (ValueError, IndexError):
                continue

    # Strategy 3: If no range found, check for single verse and return as range
    verse_ref = extract_verse_reference_enhanced(query)
    if verse_ref:
        surah, verse = verse_ref
        return (surah, verse, verse)

    return None

def classify_query_enhanced(query: str) -> Dict[str, Any]:
    """
    Query classification — extracts verse reference from query.

    Returns dict with:
    - query_type: 'direct_verse' (only route)
    - confidence: 0.0-1.0
    - verse_ref: (surah, verse) or None
    """
    query_normalized = normalize_query_text(query)
    verse_ref = extract_verse_reference_enhanced(query)

    if verse_ref:
        verse_range = extract_verse_range(query)
        if verse_range:
            return {'query_type': 'direct_verse', 'confidence': 0.95, 'verse_ref': verse_ref}

        if re.fullmatch(r'\d{1,3}:\d{1,3}(?:-\d{1,3})?', query_normalized.strip()):
            return {'query_type': 'direct_verse', 'confidence': 0.95, 'verse_ref': verse_ref}

        if any(name in query_normalized for name in NAMED_VERSES.keys()):
            return {'query_type': 'direct_verse', 'confidence': 0.9, 'verse_ref': verse_ref}

        return {'query_type': 'direct_verse', 'confidence': 0.7, 'verse_ref': verse_ref}

    # No verse reference — should not happen (frontend validates)
    return {'query_type': 'direct_verse', 'confidence': 0.0, 'verse_ref': None}


# --- Query Normalization Functions ---
def surah_name_to_number(surah_input):
    """
    Convert surah name or number to integer surah number.
    Returns (surah_number, error_message) tuple.
    """
    # If already a number, validate and return
    if isinstance(surah_input, int):
        if surah_input in QURAN_METADATA:
            return surah_input, None
        else:
            return None, f"Invalid Surah number: {surah_input}. The Quran has 114 Surahs."

    # Try to convert string to int
    if isinstance(surah_input, str):
        # Try direct number conversion
        try:
            surah_num = int(surah_input)
            if surah_num in QURAN_METADATA:
                return surah_num, None
            else:
                return None, f"Invalid Surah number: {surah_num}. The Quran has 114 Surahs."
        except ValueError:
            # Not a number, search by name
            surah_input_lower = surah_input.lower().strip()
            for num, data in QURAN_METADATA.items():
                if data["name"].lower() == surah_input_lower:
                    return num, None
            return None, f"Invalid Surah name: '{surah_input}'. Could not find matching surah."

    return None, f"Invalid Surah input type: {type(surah_input)}. Expected string or integer."


def validate_verse_reference(surah, verse):
    """
    Validate that surah and verse numbers are within valid ranges.
    Surah can be either a number or surah name.
    """
    # Convert surah name to number if needed
    surah_num, error = surah_name_to_number(surah)
    if error:
        return False, error

    # Convert verse to int if string
    if isinstance(verse, str):
        try:
            verse = int(verse)
        except ValueError:
            return False, f"Invalid verse number: '{verse}'. Expected integer."

    # Validate verse range
    max_verses = QURAN_METADATA[surah_num]["verses"]
    if not (1 <= verse <= max_verses):
        surah_name = QURAN_METADATA[surah_num]["name"]
        return False, f"Invalid verse: {verse}. Surah {surah_num} ('{surah_name}') only has {max_verses} verses."

    return True, "Valid reference"


# --- Firestore Verse Lookup ---
def get_verse_from_firestore(surah_num, verse_num):
    """Retrieve verse text from tafsir-db database"""
    try:
        doc_ref = quran_db.collection('quran_texts').document(f'surah_{surah_num}')
        doc = doc_ref.get()

        if doc.exists:
            verses = doc.to_dict().get('verses', {})
            verse_data = verses.get(str(verse_num))

            if verse_data:
                return {
                    'surah_number': surah_num,
                    'verse_number': verse_num,
                    'surah_name': QURAN_METADATA[surah_num]["name"],
                    'arabic': verse_data.get('arabic', ''),
                    'english': verse_data.get('en_sahih', ''),
                    'transliteration': verse_data.get('en_transliteration', '')
                }

    except Exception as e:
        print(f"Error fetching verse {surah_num}:{verse_num} from Firestore: {e}")
    return None

def get_verses_range_from_firestore(surah_num, start_verse, end_verse):
    """Retrieve multiple verses from tafsir-db database"""
    try:
        doc_ref = quran_db.collection('quran_texts').document(f'surah_{surah_num}')
        doc = doc_ref.get()

        if doc.exists:
            verses_dict = doc.to_dict().get('verses', {})
            surah_name = QURAN_METADATA[surah_num]["name"]

            result = []
            for v in range(start_verse, end_verse + 1):
                verse_data = verses_dict.get(str(v))
                if verse_data:
                    result.append({
                        'surah_number': surah_num,
                        'verse_number': v,
                        'surah_name': surah_name,
                        'arabic': verse_data.get('arabic', ''),
                        'english': verse_data.get('en_sahih', ''),
                        'transliteration': verse_data.get('en_transliteration', '')
                    })
            return result if result else None

        return None
    except Exception as e:
        print(f"Firestore lookup error: {e}")
        return None

def get_arabic_text_from_verse_data(verse_data):
    """Extract Arabic text for use in RAG context"""
    if verse_data and verse_data.get('arabic'):
        return verse_data['arabic']
    return None

# --- Utility Functions ---
def get_cache_key(query, user_profile, approach="tafsir"):
    """Generate cache key for response (includes approach for distinct caching)"""
    cache_data = f"{query}_{approach}_{json.dumps(user_profile, sort_keys=True)}"
    return hashlib.md5(cache_data.encode()).hexdigest()

def detect_query_intent(query: str) -> dict:
    """
    Detect the nature of the query to suggest optimal approach.

    Returns: {
        'suggested_approach': 'tafsir'|'thematic'|'historical'|None,
        'confidence': 'high'|'medium'|'low',
        'reason': 'explanation string'
    }
    """
    query_lower = query.lower()

    # ========================================================================
    # HISTORICAL INTENT PATTERNS - Comprehensive detection for revelation
    # context, timeline, events, and progressive revelation
    # ========================================================================
    historical_patterns = [
        # Revelation context (Why/When/Where/How was it revealed?)
        r'\b(why.*reveal|when.*reveal|where.*reveal|how.*reveal|who.*reveal)\b',
        r'\b(asbab|sabab.*nuzul|circumstances.*revelation|context.*revelation)\b',
        r'\b(occasion.*revelation|reason.*reveal|cause.*reveal)\b',
        r'\bسبب النزول\b',  # Arabic: reason for revelation

        # Historical events, battles, and incidents
        r'\b(battle|war|expedition|raid|ghazwa|sariyya|campaign|conflict)\b',
        r'\b(battle of|war of|expedition to|raid on)\b',
        r'\b(badr|uhud|khandaq|trench|tabuk|hunayn|khaybar)\b',
        r'\b(event|incident|occurrence|happening|situation|episode)\b',
        r'\b(story of|tale of|account of|narrative|biography)\b',
        r'\b(at the time|during|in the period|in the era|in the days)\b',

        # Timeline, progression, and change over time
        r'\b(becoming|became|turned into|transformed|evolved|converted)\b',
        r'\b(when did.*command|when was.*ordain|when did.*prescrib)\b',
        r'\b(when did.*prohibit|when did.*ban|when did.*forbid)\b',
        r'\b(gradual|progressive|stages|phases|steps|step by step|evolution)\b',
        r'\b(first.*then|initially|originally|at first|in the beginning)\b',
        r'\b(later|eventually|finally|ultimately|in the end)\b',
        r'\b(before.*after|prior to|following|subsequent|preceding)\b',
        r'\b(changed from|change.*over time|transition|shift|development)\b',
        r'\b(three stages|four stages|progressive revelation|gradual revelation)\b',

        # Commandment and prohibition timing
        r'\b(when.*(mandatory|obligatory|ordained|prescribed|required|compulsory))\b',
        r'\b(when.*(fard|wajib|sunnah|mustahabb|mandub))\b',
        r'\b(when.*(forbidden|prohibited|haram|banned|impermissible|unlawful))\b',
        r'\b(when.*(makruh|disliked|discouraged))\b',
        r'\b((mandatory|obligatory|ordained|prescribed|required).*when)\b',
        r'\b((forbidden|prohibited|haram|banned).*when)\b',
        r'\b(made (mandatory|compulsory|obligatory|forbidden|prohibited))\b',

        # Historical context and background
        r'\b(historical|history|historically|historic)\b',
        r'\b(context|background|setting|circumstances|situation|conditions)\b',
        r'\b(chronology|timeline|sequence|order of events|succession)\b',
        r'\b(makki|madani|meccan|medinan|makkah|madinah)\b',
        r'\b(early islam|pre-islamic|jahiliyyah|jahiliyya|ignorance)\b',

        # Specific historical periods and migrations
        r'\b(hijra|hijrah|migration|emigration|exodus)\b',
        r'\b(before hijra|after hijra|pre-hijra|post-hijra)\b',
        r'\b(year of.*elephant|year of.*grief|year of.*delegation)\b',

        # People and companions (historical figures)
        r'\b(companion|sahabi|sahabah|sahaba)\b',
        r'\b(prophet.*life|prophetic.*biography|seerah|sirah|sira)\b',
        r'\b(abu bakr|umar|uthman|ali|khadijah|aisha)\b',
        r'\b(muhajirun|ansar|emigrants|helpers)\b',

        # Specific commandments with timeline implications
        r'\b((prayer|salah|salat|namaz).*(ordained|commanded|prescribed))\b',
        r'\b((fasting|sawm|siyam).*(ordained|commanded|prescribed))\b',
        r'\b((hijab|veil|covering).*(ordained|commanded|prescribed))\b',
        r'\b((alcohol|wine|khamr).*(forbidden|prohibited|banned))\b',
        r'\b((usury|riba|interest).*(forbidden|prohibited|banned))\b'
    ]

    # ========================================================================
    # THEMATIC INTENT PATTERNS - Comprehensive detection for cross-verse
    # concepts, holistic understanding, and topic exploration
    # ========================================================================
    thematic_patterns = [
        # Cross-reference and multi-verse indicators
        r'\b(across.*surah|across.*chapter|across.*quran)\b',
        r'\b(throughout.*quran|throughout.*book|throughout.*scripture)\b',
        r'\b(all.*verse|all.*ayah|all.*ayat|every.*verse)\b',
        r'\b(different.*surah|multiple.*surah|various.*chapter|several.*surah)\b',
        r'\b(verses about|ayat about|ayahs about|passages about)\b',
        r'\b(everywhere.*quran|wherever.*quran|anywhere.*quran)\b',

        # Conceptual inquiry (What does Quran/Islam say?)
        r'\b(what.*quran.*(say|teach|mention|state|describe|explain))\b',
        r'\b(what.*islam.*(say|teach|mention|state|describe|explain))\b',
        r'\b(what.*allah.*(say|command|decree|ordain))\b',
        r'\b(how.*quran.*(describe|view|portray|depict|present))\b',
        r'\b(how.*islam.*(view|regard|consider|treat))\b',
        r'\b(does.*quran.*(mention|talk about|discuss|address))\b',
        r'\b(does.*islam.*(allow|permit|forbid|prohibit))\b',

        # Teaching and guidance
        r'\b(quran.*teach|islam.*teach|islamic.*teaching|quranic.*teaching)\b',
        r'\b(quran.*guidance|islamic.*guidance|divine.*guidance)\b',
        r'\b(quran.*perspective|islamic.*perspective|quranic.*view)\b',
        r'\b(according to.*(quran|islam|sharia|shariah))\b',
        r'\b(in.*(quran|islam|islamic.*view))\b',

        # Thematic analysis terms
        r'\b(theme|concept|topic|subject|idea|notion)\b',
        r'\b(holistic|comprehensive|complete|full|entire|total)\b',
        r'\b(overview|summary|general.*understanding|overall|broad)\b',
        r'\b(all instances|all mentions|all references|all occurrences)\b',
        r'\b(collect|compilation|collection|gathering)\b',

        # Pattern and relationship seeking
        r'\b(pattern|recurring|repeated|repetition|recurrence)\b',
        r'\b(common|consistent|constant|uniform)\b',
        r'\b(connection|relationship|link|correlation|association)\b',
        r'\b(compare|comparison|contrast|difference|similarity)\b',
        r'\b(related.*verse|connected.*verse|similar.*verse|parallel)\b',

        # Conceptual development
        r'\b(evolution.*concept|development.*idea|progression.*theme)\b',
        r'\b(concept of|idea of|notion of|principle of)\b',
        r'\b(understanding|comprehension|grasp|meaning)\b',

        # Significance and importance
        r'\b(significance|importance|value|worth|merit)\b',
        r'\b(role|function|purpose|objective|goal)\b',
        r'\b(principle|guideline|rule|law|regulation)\b',

        # Virtues and qualities (thematic topics)
        r'\b(virtue|quality|attribute|characteristic|trait)\b',
        r'\b(concept of.*(justice|mercy|patience|charity|compassion))\b',
        r'\b(concept of.*(prayer|fasting|pilgrimage|zakat|hajj))\b',
        r'\b(concept of.*(faith|belief|iman|taqwa|piety))\b',

        # Islamic concepts and topics
        r'\b(islam.*say about|quran.*mention.*about|verses.*(discuss|address))\b',
        r'\b(islamic.*(view|stance|position|ruling) on)\b',
        r'\b(quranic.*(concept|teaching|principle|view))\b',

        # Broad exploratory questions
        r'\b(explain|elaborate|clarify|elucidate)\b',
        r'\b(tell me about|inform me about|educate me about)\b',
        r'\b(learn about|study|understand|explore)\b',

        # Multiple aspects and dimensions
        r'\b(aspect|dimension|facet|angle|perspective)\b',
        r'\b(different.*view|various.*aspect|multiple.*dimension)\b'
    ]

    # ========================================================================
    # TAFSIR/VERSE-SPECIFIC PATTERNS - For detailed classical commentary
    # ========================================================================
    tafsir_patterns = [
        # Specific verse analysis
        r'\b(explain|meaning|tafsir|commentary|interpretation) (of|for).*\d+:\d+\b',
        r'\b(what does|what is).*(verse|ayah|ayat).*mean\b',
        r'\b(deeper|detailed|thorough|in-depth).*(meaning|understanding|analysis)\b',

        # Classical commentary focus
        r'\b(ibn kathir|qurtubi|tabari|jalalayn|al-jalalayn)\b',
        r'\b(classical.*scholar|traditional.*scholar|early.*scholar)\b',
        r'\b(arabic.*meaning|linguistic|grammar|etymology)\b',
        r'\b(word by word|phrase by phrase|detailed.*explanation)\b',

        # Specific surah/verse focus (not asking "what does Quran say" but focused analysis)
        r'\b(surah|sura).*(verse|ayah).*(mean|explain|teach|say)\b',
        r'\b(verse|ayah).*(about|regarding|concerning).*(specific|particular)\b'
    ]

    # Priority 1: Check for historical keywords (timeline, revelation context, events)
    if any(re.search(pattern, query_lower) for pattern in historical_patterns):
        return {
            'suggested_approach': 'tafsir',  # Deep tafsir can handle historical context
            'confidence': 'high',
            'reason': 'Your query asks about revelation context or historical events - include a verse reference for best results'
        }

    # Priority 2: Check for thematic keywords (cross-verse concepts, holistic understanding)
    if any(re.search(pattern, query_lower) for pattern in thematic_patterns):
        return {
            'suggested_approach': 'tafsir',  # Deep tafsir handles thematic queries with verse references
            'confidence': 'high',
            'reason': 'Your query explores a concept - include a verse reference for detailed commentary'
        }

    # Priority 3: Check for tafsir-specific patterns (detailed commentary, classical scholars)
    if any(re.search(pattern, query_lower) for pattern in tafsir_patterns):
        return {
            'suggested_approach': 'tafsir',
            'confidence': 'high',
            'reason': 'Your query seeks detailed classical commentary or verse-specific analysis'
        }

    # Priority 4: Check for verse reference (tafsir suitable)
    verse_ref = extract_verse_reference_enhanced(query)
    if verse_ref:
        return {
            'suggested_approach': 'tafsir',
            'confidence': 'medium',
            'reason': 'Your query references a specific verse - classical commentary may help'
        }

    # Default: unclear intent, no suggestion (user's chosen approach is fine)
    return {
        'suggested_approach': None,
        'confidence': 'low',
        'reason': None
    }

def is_rate_limited(user_id, limit=150, window_hours=1):
    """Check if user is rate limited (150 requests per hour per user)"""
    now = datetime.now()
    window_start = now - timedelta(hours=window_hours)

    # Clean old entries
    USER_RATE_LIMITS[user_id] = [
        timestamp for timestamp in USER_RATE_LIMITS[user_id]
        if timestamp > window_start
    ]

    # Check limit
    if len(USER_RATE_LIMITS[user_id]) >= limit:
        return True

    # Add current request
    USER_RATE_LIMITS[user_id].append(now)
    return False

def get_cross_references(query):
    """Get cross-references for the query"""
    query_lower = query.lower()
    for key, refs in VERSE_CROSS_REFS.items():
        if key in query_lower or any(ref in query_lower for ref in refs):
            return refs
    return []


def extract_verse_references_from_text(text):
    """Extract verse references from tafsir text (e.g., '31:12', 'Surah Luqman 31:12')"""
    import re
    verse_refs = []

    # Pattern 1: Direct references like "31:12" or "(31:12)"
    pattern1 = r'\b(\d{1,3}):(\d{1,3})\b'
    matches1 = re.findall(pattern1, text)
    for surah, verse in matches1:
        verse_refs.append(f"{surah}:{verse}")

    # Pattern 2: Named references like "Surah Luqman 31:12" or "An-Nahl 16:114"
    pattern2 = r'(?:Surah\s+)?(?:Al-)?[A-Za-z-]+\s+(\d{1,3}):(\d{1,3})'
    matches2 = re.findall(pattern2, text)
    for surah, verse in matches2:
        verse_refs.append(f"{surah}:{verse}")

    # Remove duplicates while preserving order
    seen = set()
    unique_refs = []
    for ref in verse_refs:
        if ref not in seen:
            seen.add(ref)
            unique_refs.append(ref)

    return unique_refs


def fetch_arabic_for_referenced_verses(tafsir_explanations, main_verses):
    """Fetch Arabic text for verses mentioned in tafsir but not in main verses"""
    all_referenced_verses = []
    main_verse_refs = {f"{v.get('surah_number', '')}:{v.get('verse_number', '')}"
                       for v in main_verses if v.get('surah_number') and v.get('verse_number')}

    # Extract verse references from all tafsir explanations
    for explanation in tafsir_explanations:
        text = explanation.get('explanation', '')
        refs = extract_verse_references_from_text(text)

        for ref in refs:
            # Skip if this is already in main verses
            if ref in main_verse_refs:
                continue

            try:
                parts = ref.split(':')
                if len(parts) == 2:
                    surah_num = int(parts[0])
                    verse_num = int(parts[1])

                    # Fetch the verse data
                    verse_data = get_verse_from_firestore(surah_num, verse_num)
                    if verse_data:
                        all_referenced_verses.append({
                            'surah_number': surah_num,
                            'verse_number': verse_num,
                            'arabic_text': verse_data.get('arabic', ''),
                            'text_saheeh_international': verse_data.get('en_sahih', ''),
                            'reference': ref,
                            'is_supplementary': True  # Mark as supplementary verse
                        })
            except (ValueError, IndexError) as e:
                print(f"Warning: Could not fetch verse {ref}: {e}")
                continue

    return all_referenced_verses

def validate_response(response_data):
    """Validate response quality and ensure all sections are present"""
    try:
        # Check ALL required fields for proper formatting
        required_fields = [
            "verses",
            "tafsir_explanations",
            "cross_references",
            "lessons_practical_applications",
            "summary"
        ]

        missing_fields = [field for field in required_fields if field not in response_data]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"

        # Validate verses section
        verses = response_data.get("verses", [])
        if not verses:
            return False, "No verses provided"

        for verse in verses:
            if not verse.get("arabic_text") or not verse.get("text_saheeh_international"):
                return False, "Verses missing Arabic or English text"

        # Check if at least one tafsir explanation has substantial content
        explanations = response_data.get("tafsir_explanations", [])
        if len(explanations) != 2:
            return False, "Must have exactly 2 tafsir sources (al-Qurtubi and Ibn Kathir)"

        substantial_explanations = [
            exp for exp in explanations
            if len(exp.get("explanation", "")) > 50 and
            "Limited relevant content" not in exp.get("explanation", "")
        ]

        if len(substantial_explanations) == 0:
            return False, "No substantial explanations found"

        # Validate lessons section
        lessons = response_data.get("lessons_practical_applications", [])
        if len(lessons) < 2:
            return False, "Must have at least 2 practical lessons"

        # Validate summary
        summary = response_data.get("summary", "")
        if len(summary) < 50:
            return False, "Summary too short or missing"

        return True, "Valid response"
    except Exception as e:
        return False, f"Validation error: {e}"


def format_response_with_headers(response_data):
    """Add clear section headers to response for better UI display"""
    formatted_response = response_data.copy()

    # Add section headers as metadata
    formatted_response['section_headers'] = {
        'summary': '📚 Summary',
        'verses': '📖 Verses',
        'tafsir': '📝 Classical Commentary',
        'cross_references': '🔗 Related Verses',
        'lessons': '💡 Lessons & Applications'
    }

    # Ensure proper formatting of each section
    if 'summary' in formatted_response and not formatted_response['summary']:
        formatted_response['summary'] = "Summary not available for this query."

    # Ensure cross_references is always a list
    if 'cross_references' not in formatted_response:
        formatted_response['cross_references'] = []

    # Ensure lessons have proper structure
    if 'lessons_practical_applications' in formatted_response:
        lessons = formatted_response['lessons_practical_applications']
        if lessons and isinstance(lessons, list):
            # Ensure each lesson has a 'point' key
            formatted_lessons = []
            for lesson in lessons:
                if isinstance(lesson, dict) and 'point' in lesson:
                    formatted_lessons.append(lesson)
                elif isinstance(lesson, str):
                    formatted_lessons.append({'point': lesson})
            formatted_response['lessons_practical_applications'] = formatted_lessons

    return formatted_response

# ============================================================================
# NEW: PROFILE HELPER FUNCTION (Suggestion 2)
# ============================================================================

def determine_knowledge_level(persona: str, provided_level: Optional[str]) -> Tuple[str, bool]:
    """
    Smart logic for knowledge_level based on persona.
    
    Returns: (knowledge_level, is_deterministic)
    - is_deterministic=True means level was auto-set by persona
    - is_deterministic=False means level came from user input
    """
    # Deterministic personas - auto-set knowledge_level
    deterministic = {
        "advanced_learner": "advanced",
        "student": "advanced",
        "new_revert": "beginner"
    }
    
    if persona in deterministic:
        return deterministic[persona], True
    
    # Variable personas - require provided_level
    if not provided_level:
        return None, False
    
    # Validate provided level
    if provided_level not in ["beginner", "intermediate", "advanced"]:
        return None, False
    
    return provided_level, False

# --- REPLACED: Enhanced Data Loading with Dual Storage ---
def load_chunks_from_verse_files_enhanced():
    """
    Enhanced loader: Store BOTH flattened text AND structured metadata.
    This replaces your existing load_chunks_from_verse_files function.
    """
    global TAFSIR_CHUNKS, VERSE_METADATA

    try:
        print(f"INFO: Initializing enhanced dual-storage system")
        storage_client = storage.Client(project=GCP_INFRASTRUCTURE_PROJECT)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)

        source_files = [
            ("processed/ibnkathir-Fatiha-Tawbah_fixed.json", "ibn-kathir"),
            ("processed/ibnkathir-Yunus-Ankabut_FINAL_fixed.json", "ibn-kathir"),
            ("processed/ibnkathir-Rum-Nas_FINAL_fixed.json", "ibn-kathir"),
            ("processed/al-Qurtubi_Fatiha.json", "al-qurtubi"),
            ("processed/al-Qurtubi Vol. 1_FINAL_fixed.json", "al-qurtubi"),
            ("processed/al-Qurtubi Vol. 2_FINAL_fixed.json", "al-qurtubi"),
            ("processed/al-Qurtubi Vol. 3_fixed.json", "al-qurtubi"),
            ("processed/al-Qurtubi Vol. 4_FINAL_fixed.json", "al-qurtubi")
        ]

        all_verses = []
        source_counts = {"ibn-kathir": 0, "al-qurtubi": 0}

        def _load_one_file(file_path, source):
            """Load a single GCS file and return (verses, source, file_path) or None."""
            try:
                blob = bucket.blob(file_path)
                if not blob.exists():
                    print(f"WARNING: File not found: {file_path}")
                    return None
                contents = blob.download_as_text()
                data = json.loads(contents)
                verses = data.get('verses', [])
                for verse in verses:
                    verse['_source'] = source
                return (verses, source, file_path)
            except Exception as e:
                print(f"ERROR loading {file_path}: {e}")
                return None

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=7) as executor:
            futures = [executor.submit(_load_one_file, fp, src) for fp, src in source_files]
            for future in futures:
                result = future.result()
                if result:
                    verses, source, file_path = result
                    all_verses.extend(verses)
                    source_counts[source] += len(verses)
                    print(f"INFO: Loaded {len(verses)} verses from {file_path}")

        print(f"INFO: Total verses loaded: {len(all_verses)}")

        # Process verses with dual storage
        for verse in all_verses:
            surah = verse.get('surah')
            verse_num = verse.get('verse_number') or verse.get('verse_numbers')
            source = verse.get('_source', 'unknown')

            if surah is None:
                continue

            # Handle verse numbers (single, list, or STRING RANGE like "183-184")
            verse_numbers_list = []
            if isinstance(verse_num, str) and '-' in verse_num:
                # CRITICAL FIX: Handle string ranges like "183-184"
                try:
                    parts = verse_num.split('-')
                    start_v = int(parts[0])
                    end_v = int(parts[1])
                    verse_numbers_list = list(range(start_v, end_v + 1))
                    verse_num = start_v  # Use first verse for chunk_id
                    print(f"INFO: Processing range {surah}:{verse_num} (string format '{verse.get('verse_number')}')")
                except (ValueError, IndexError) as e:
                    print(f"WARNING: Could not parse verse_number '{verse_num}': {e}")
                    continue
            elif isinstance(verse_num, list):
                if verse_num:
                    # Handle list format: [183, 184]
                    verse_numbers_list = verse_num
                    verse_num = verse_num[0]  # Use first for chunk_id
                else:
                    # Empty list [] — no verse number available, skip
                    continue
            elif verse_num is None:
                verse_num = 0
                verse_numbers_list = [0]
            elif isinstance(verse_num, (int, float)):
                # Handle single integer/float
                verse_num = int(verse_num)
                verse_numbers_list = [verse_num]
            else:
                # Handle any other format
                try:
                    verse_num = int(verse_num)
                    verse_numbers_list = [verse_num]
                except (ValueError, TypeError):
                    print(f"WARNING: Unexpected verse_number format: {verse_num} (type: {type(verse_num)})")
                    continue

            verse_text = verse.get('verse_text', '')
            topics = verse.get('topics', [])

            # Build flattened text for embeddings (EXISTING LOGIC)
            chunk_parts = []
            if verse_text:
                chunk_parts.append(verse_text)

            # Al-Qurtubi structure
            if verse.get('commentary') and not topics:
                chunk_parts.append(verse['commentary'])
                if verse.get('phrase_analysis'):
                    for phrase in verse['phrase_analysis']:
                        if isinstance(phrase, str):
                            chunk_parts.append(phrase)
                if verse.get('scholar_citations'):
                    for citation in verse['scholar_citations']:
                        if isinstance(citation, str):
                            chunk_parts.append(citation)

            # Ibn Kathir structure
            if topics:
                for topic in topics:
                    if topic.get('topic_header'):
                        chunk_parts.append(topic['topic_header'])
                    if topic.get('commentary'):
                        chunk_parts.append(topic['commentary'])
                    if topic.get('phrase_analysis'):
                        for phrase in topic['phrase_analysis']:
                            if isinstance(phrase, dict):
                                if phrase.get('phrase'):
                                    chunk_parts.append(phrase['phrase'])
                                if phrase.get('analysis'):
                                    chunk_parts.append(phrase['analysis'])

            full_text = " ".join(chunk_parts)
            chunk_id = f"{source}:{surah}:{verse_num}"

            if full_text.strip():
                # STORAGE 1: Flattened text for direct chunk lookup
                TAFSIR_CHUNKS[chunk_id] = full_text

                # STORAGE 2: Structured metadata for direct queries
                # Extract metadata from BOTH structures (Al-Qurtubi flat + Ibn Kathir nested)

                # Initialize aggregated metadata lists
                all_hadith = []
                all_scholar_citations = []
                all_phrase_analysis = []
                all_cross_refs = []
                all_historical_context = []
                all_linguistic_analysis = []
                all_legal_rulings = []

                # Extract from verse level (Al-Qurtubi style)
                if verse.get('hadith_references'):
                    all_hadith.extend(verse['hadith_references'])
                if verse.get('scholar_citations'):
                    all_scholar_citations.extend(verse['scholar_citations'])
                if verse.get('phrase_analysis'):
                    all_phrase_analysis.extend(verse['phrase_analysis'])
                if verse.get('cross_references'):
                    all_cross_refs.extend(verse['cross_references'])
                if verse.get('historical_context'):
                    all_historical_context.extend(verse['historical_context'])
                if verse.get('linguistic_analysis'):
                    all_linguistic_analysis.extend(verse['linguistic_analysis'])
                if verse.get('legal_rulings'):
                    all_legal_rulings.extend(verse['legal_rulings'])

                # Extract from topics (Ibn Kathir style)
                if topics:
                    for topic in topics:
                        if isinstance(topic, dict):
                            if topic.get('hadith_references'):
                                all_hadith.extend(topic['hadith_references'])
                            if topic.get('scholar_citations'):
                                all_scholar_citations.extend(topic['scholar_citations'])
                            if topic.get('phrase_analysis'):
                                all_phrase_analysis.extend(topic['phrase_analysis'])
                            if topic.get('cross_references'):
                                all_cross_refs.extend(topic['cross_references'])
                            if topic.get('historical_context'):
                                all_historical_context.extend(topic['historical_context'])
                            if topic.get('linguistic_analysis'):
                                all_linguistic_analysis.extend(topic['linguistic_analysis'])
                            if topic.get('legal_rulings'):
                                all_legal_rulings.extend(topic['legal_rulings'])

                # CRITICAL FIX: Store metadata under ALL verses in the range
                metadata_entry = {
                    'surah': surah,
                    'verse_number': verse_num,
                    'source': source,
                    'verse_text': verse_text,
                    'topics': topics,  # Keep original topics structure
                    'commentary': verse.get('commentary'),
                    # Aggregated metadata from BOTH structures
                    'phrase_analysis': all_phrase_analysis,
                    'scholar_citations': all_scholar_citations,
                    'hadith_references': all_hadith,
                    'cross_references': all_cross_refs,
                    'historical_context': all_historical_context,
                    'linguistic_analysis': all_linguistic_analysis,
                    'legal_rulings': all_legal_rulings,
                    'verse_numbers': verse.get('verse_numbers'),
                }

                # Store under the primary chunk_id (for backward compatibility)
                VERSE_METADATA[chunk_id] = metadata_entry

                # ALSO store under each individual verse in the range
                for individual_verse in verse_numbers_list:
                    individual_chunk_id = f"{source}:{surah}:{individual_verse}"
                    if individual_chunk_id != chunk_id:  # Avoid duplicate
                        VERSE_METADATA[individual_chunk_id] = metadata_entry.copy()

        print(f"INFO: Dual storage complete:")
        print(f"  - Flat chunks: {len(TAFSIR_CHUNKS)}")
        print(f"  - Structured metadata: {len(VERSE_METADATA)}")
        print(f"  - Ibn Kathir: {source_counts['ibn-kathir']} verses")
        print(f"  - al-Qurtubi: {source_counts['al-qurtubi']} verses")

        if len(TAFSIR_CHUNKS) == 0:
            raise RuntimeError("CRITICAL: No chunks loaded")

    except Exception as e:
        print(f"CRITICAL ERROR loading chunks: {e}")
        raise


# --- Response Filtering Functions ---
def sanitize_explanation_text(text):
    """
    Clean up LLM output that sometimes has excessive indentation.
    Fixes issues like:
        **Header**
        Paragraph text with 8 spaces...
    """
    if not text:
        return text

    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        # Remove excessive leading whitespace (more than 4 spaces is considered excessive)
        # Keep 0-4 spaces for legitimate indentation (like nested lists)
        stripped = line.lstrip()
        leading_spaces = len(line) - len(stripped)

        if leading_spaces > 4:
            # Reduce to max 4 spaces
            line = '    ' + stripped if stripped else ''

        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)

def enforce_persona_verse_limit(response_json: Dict, persona_name: str, requested_verses: Optional[List[Tuple[int, int]]] = None, dynamic_limit: Optional[int] = None) -> Tuple[Dict, bool, int, int]:
    """
    Enforce verse limits while prioritizing explicitly requested verses.
    Uses dynamic_limit (from token budget) when provided, else VERSE_LIMIT_DEFAULT.

    Returns a tuple of:
        (response_json, trimmed_flag, original_count, final_count)
    """
    if not response_json or not isinstance(response_json, dict):
        return response_json, False, 0, 0

    verses = response_json.get('verses')
    if not verses or not isinstance(verses, list):
        return response_json, False, 0, 0

    original_count = len(verses)
    verse_limit = dynamic_limit if dynamic_limit else VERSE_LIMIT_DEFAULT

    requested_set = set()
    if requested_verses:
        for surah, verse in requested_verses:
            try:
                requested_set.add((int(surah), int(verse)))
            except (TypeError, ValueError):
                continue

    def normalize_verse_id(entry: Dict) -> Optional[Tuple[int, int]]:
        surah_val = entry.get('surah') or entry.get('surah_number')
        verse_val = entry.get('verse_number') or entry.get('verse')
        try:
            return int(surah_val), int(str(verse_val).split(':')[-1])
        except (TypeError, ValueError):
            return None

    prioritized = []
    others = []
    seen = set()

    for verse_entry in verses:
        verse_id = normalize_verse_id(verse_entry)

        if verse_id:
            if verse_id in seen:
                continue  # Deduplicate identical verse entries
            seen.add(verse_id)

            if requested_set and verse_id in requested_set:
                prioritized.append(verse_entry)
            else:
                others.append(verse_entry)
        else:
            # Keep unrecognized structures at the end (rare)
            others.append(verse_entry)

    # Always honor all explicitly requested verses, even if they exceed the persona limit
    allowed_count = max(verse_limit, len(prioritized))
    remaining_slots = max(0, allowed_count - len(prioritized))

    limited_verses = prioritized + others[:remaining_slots]
    trimmed = len(limited_verses) < original_count

    response_json['verses'] = limited_verses
    final_count = len(limited_verses)

    return response_json, trimmed, original_count, final_count

def normalize_verse_id(entry: Dict) -> Optional[Tuple[int, int]]:
    """Extract (surah, verse) tuple from a verse entry dict."""
    try:
        surah_val = entry.get('surah') or entry.get('surah_number')
        verse_val = entry.get('verse_number') or entry.get('verse')
        if isinstance(verse_val, str) and ':' in verse_val:
            verse_val = verse_val.split(':')[-1]
        return int(surah_val), int(verse_val)
    except (TypeError, ValueError, AttributeError):
        return None

def build_requested_verse_objects(requested_data: Any) -> List[Dict]:
    """
    Build normalized verse objects for the main verses array using requested verse data.
    """
    if not requested_data:
        return []

    data_list = requested_data if isinstance(requested_data, list) else [requested_data]
    normalized = []

    for data in data_list:
        try:
            surah_num = data.get('surah_number') or data.get('surah')
            verse_num = data.get('verse_number') or data.get('verse')
            if isinstance(verse_num, str) and ':' in verse_num:
                verse_num = verse_num.split(':')[-1]

            normalized.append({
                "surah": int(surah_num) if surah_num is not None else None,
                "surah_name": data.get('surah_name') or data.get('surahName'),
                "verse_number": str(verse_num) if verse_num is not None else None,
                "text_saheeh_international": data.get('english') or data.get('text_saheeh_international'),
                "arabic_text": data.get('arabic') or data.get('arabic_text')
            })
        except (TypeError, ValueError, AttributeError):
            continue

    # Filter out incomplete entries (missing surah or verse)
    normalized = [
        v for v in normalized
        if v.get("surah") is not None and v.get("verse_number") is not None
    ]

    return normalized

def keep_requested_verses_primary(response_json: Dict, requested_data: Any, requested_verses: Optional[List[Tuple[int, int]]] = None) -> Dict:
    """
    Ensure the main `verses` array only contains the explicitly requested verse(s).
    Any extra verses get moved into `cross_references`.
    """
    if not response_json or not isinstance(response_json, dict):
        return response_json

    # Establish requested set from explicit list or requested_data
    requested_set = set()
    if requested_verses:
        for surah, verse in requested_verses:
            try:
                requested_set.add((int(surah), int(verse)))
            except (TypeError, ValueError):
                continue
    elif requested_data:
        data_list = requested_data if isinstance(requested_data, list) else [requested_data]
        for data in data_list:
            verse_id = normalize_verse_id(data)
            if verse_id:
                requested_set.add(verse_id)

    # Move non-requested verses into cross references
    current_verses = response_json.get('verses', [])
    extra_refs = []
    for verse_entry in current_verses:
        verse_id = normalize_verse_id(verse_entry)
        if verse_id and requested_set and verse_id not in requested_set:
            extra_refs.append(f"{verse_id[0]}:{verse_id[1]}")

    cross_refs = response_json.get('cross_references') or []
    if not isinstance(cross_refs, list):
        cross_refs = [cross_refs]

    for ref in extra_refs:
        if ref not in cross_refs:
            cross_refs.append(ref)

    response_json['cross_references'] = cross_refs

    requested_objects = build_requested_verse_objects(requested_data)
    if requested_objects:
        response_json['verses'] = requested_objects

    return response_json

def sanitize_unavailability_text(text):
    """
    Remove mentions of source unavailability from response text.
    This prevents user-facing messages like "Al-Qurtubi's tafsir is not available for this verse."

    Returns: Cleaned text with unavailability mentions removed
    """
    if not text:
        return text

    # Patterns that indicate source unavailability (case-insensitive)
    unavailability_patterns = [
        # Direct unavailability statements
        r"al-Qurtubi'?s?\s+(?:tafsir|commentary|comprehensive tafsir).*?(?:is\s+)?not\s+available.*?(?:\.|;|$)",
        r"(?:tafsir|commentary)\s+(?:is\s+)?not\s+available\s+for\s+(?:this\s+)?verse.*?(?:\.|;|$)",
        r"(?:is\s+)?not\s+available\s+for\s+(?:Surah|this\s+verse|verses?\s+beyond).*?(?:\.|;|$)",
        # Scope/coverage limitations
        r"(?:is\s+)?beyond\s+(?:the\s+)?scope.*?(?:\.|;|$)",
        r"(?:only\s+)?covers?\s+(?:only\s+)?Surahs?\s+1-?4.*?(?:\.|;|$)",
        r"available\s+(?:only\s+)?for\s+Surahs?\s+1-?4.*?(?:therefore|so|thus).*?(?:\.|;|$)",
        r"limited\s+to\s+Surahs?\s+1-?4.*?(?:\.|;|$)",
        r"does\s+not\s+cover\s+(?:this\s+)?(?:verse|surah|passage).*?(?:\.|;|$)",
        # Source material limitations
        r"(?:the\s+)?(?:provided\s+)?source\s+material.*?does\s+not\s+contain.*?(?:\.|;|$)",
        r"(?:no|insufficient)\s+(?:tafsir|commentary)\s+(?:is\s+)?available.*?(?:\.|;|$)",
    ]

    cleaned = text
    for pattern in unavailability_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)

    # Clean up resulting artifacts
    # Remove multiple consecutive spaces (but NOT newlines - preserve paragraph breaks)
    cleaned = re.sub(r'[^\S\n]{2,}', ' ', cleaned)  # Match 2+ whitespace except newlines
    # Remove orphaned punctuation at start of sentences
    cleaned = re.sub(r'^\s*[,;:]\s*', '', cleaned)
    cleaned = re.sub(r'\.\s*[,;:]\s*', '. ', cleaned)
    # Remove empty parentheses or brackets
    cleaned = re.sub(r'\(\s*\)', '', cleaned)
    cleaned = re.sub(r'\[\s*\]', '', cleaned)
    # Clean up double periods
    cleaned = re.sub(r'\.{2,}', '.', cleaned)
    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()

    return cleaned if cleaned else text

def filter_unavailable_sources(response_json):
    """
    Remove tafsir sources from response where content is unavailable.
    Checks for patterns like 'not available', 'is not available for',
    'does not cover', 'only covers Surahs 1-4', etc.

    ALSO removes any sources that aren't al-Qurtubi or Ibn Kathir
    (e.g., "General Scholarly Analysis" sometimes added by Gemini).

    Returns: Modified response_json with unavailable sources removed
    """
    if not response_json or 'tafsir_explanations' not in response_json:
        return response_json

    # ONLY these two classical sources are allowed
    approved_sources = ['al-qurtubi', 'ibn kathir']

    unavailability_patterns = [
        r'not available',
        r'is not available',
        r'commentary.*not available',
        r'tafsir.*not available',
        r'does not cover',
        r'only covers surahs? 1-4',
        r'covers only surahs? 1-4',
        r'commentary covers only',
        r'limited to surahs? 1-4',
        r'unavailable',
        r'provided source material.*does not contain'
    ]

    original_explanations = response_json.get('tafsir_explanations', [])
    filtered_explanations = []

    for explanation in original_explanations:
        source_name = explanation.get('source', '').lower()
        explanation_text = explanation.get('explanation', '').lower()

        # Check if source is from approved list (al-Qurtubi or Ibn Kathir ONLY)
        is_approved_source = any(
            approved in source_name
            for approved in approved_sources
        )

        # Check if explanation indicates unavailability
        is_unavailable = any(
            re.search(pattern, explanation_text, re.IGNORECASE)
            for pattern in unavailability_patterns
        )

        # Only include if:
        # 1. Source is from approved list (al-Qurtubi or Ibn Kathir)
        # 2. Content is actually available (not "not available" message)
        # 3. Explanation has actual content
        if is_approved_source and not is_unavailable and explanation_text.strip():
            # Sanitize the explanation text: HTML→markdown, fix indentation, fix heading format
            original_text = explanation.get('explanation', '')
            sanitized = normalize_html_to_markdown(original_text)
            sanitized = sanitize_explanation_text(sanitized)
            sanitized = sanitize_heading_format(sanitized)

            explanation['explanation'] = sanitized
            filtered_explanations.append(explanation)

    # Update response with filtered explanations
    if filtered_explanations:
        response_json['tafsir_explanations'] = filtered_explanations
    else:
        # If no sources available, set to empty list
        response_json['tafsir_explanations'] = []

    # Also sanitize other text fields that might have indentation and heading format issues
    if response_json.get('summary'):
        sanitized_summary = normalize_html_to_markdown(response_json['summary'])
        sanitized_summary = sanitize_explanation_text(sanitized_summary)
        sanitized_summary = sanitize_heading_format(sanitized_summary)
        # Remove any unavailability messages from summary
        response_json['summary'] = sanitize_unavailability_text(sanitized_summary)

    if response_json.get('key_points'):
        response_json['key_points'] = [
            sanitize_unavailability_text(sanitize_heading_format(sanitize_explanation_text(normalize_html_to_markdown(point))))
            if isinstance(point, str) else point
            for point in response_json['key_points']
        ]

    # Sanitize unavailability text from each tafsir explanation
    for explanation in response_json.get('tafsir_explanations', []):
        if explanation.get('explanation'):
            explanation['explanation'] = sanitize_unavailability_text(explanation['explanation'])

    return response_json


# --- NEW: Direct Metadata Retrieval Functions ---
def get_verse_metadata_direct(surah: int, verse: int, source_pref: Optional[str] = None, end_verse: Optional[int] = None) -> List[Dict]:
    """
    Direct lookup of verse metadata (no vector search).
    Supports verse ranges when end_verse is provided.

    Args:
        surah: Surah number
        verse: Starting verse number
        source_pref: 'ibn-kathir', 'al-qurtubi', or None (both)
        end_verse: Optional ending verse number for ranges

    Returns:
        List of metadata dicts from matching sources
    """
    results = []
    sources_to_check = [source_pref] if source_pref else ['ibn-kathir', 'al-qurtubi']

    # Determine verse range
    start_verse = verse
    last_verse = end_verse if end_verse else verse

    for source in sources_to_check:
        # Collect metadata for all verses in range
        range_metadata = []
        for v in range(start_verse, last_verse + 1):
            chunk_id = f"{source}:{surah}:{v}"
            metadata = VERSE_METADATA.get(chunk_id)

            if metadata:
                range_metadata.append({
                    'verse_number': v,
                    'metadata': metadata
                })

        if range_metadata:
            results.append({
                'chunk_id': f"{source}:{surah}:{start_verse}-{last_verse}" if end_verse else f"{source}:{surah}:{verse}",
                'source': "Ibn Kathir" if source == "ibn-kathir" else "al-Qurtubi",
                'verses': range_metadata,
                'metadata': range_metadata[0]['metadata'] if len(range_metadata) == 1 else None  # For backwards compatibility
            })

    return results

def format_metadata_response(verse_ref: Tuple[int, int], metadata_type: str,
                             verse_metadata_list: List[Dict]) -> Dict:
    """Format metadata into structured response"""
    surah, verse = verse_ref

    response = {
        "query_type": "direct_metadata",
        "verse_reference": f"{surah}:{verse}",
        "surah_name": QURAN_METADATA[surah]["name"],
        "metadata_type": metadata_type,
        "sources": []
    }

    for item in verse_metadata_list:
        source_name = item['source']
        metadata = item['metadata']

        source_data = {
            "source": source_name,
            "verse_text": metadata.get('verse_text', '')
        }

        # Add requested metadata
        if metadata_type == 'hadith':
            source_data['hadith_references'] = metadata.get('hadith_references', [])
        elif metadata_type == 'scholar_citations':
            source_data['scholar_citations'] = metadata.get('scholar_citations', [])
        elif metadata_type == 'phrase_analysis':
            source_data['phrase_analysis'] = metadata.get('phrase_analysis', [])
        elif metadata_type == 'topics':
            source_data['topics'] = metadata.get('topics', [])
        elif metadata_type == 'cross_references':
            source_data['cross_references'] = metadata.get('cross_references', [])
        elif metadata_type == 'historical_context':
            source_data['historical_context'] = metadata.get('historical_context', [])
        elif metadata_type == 'legal_rulings':
            source_data['legal_rulings'] = metadata.get('legal_rulings', [])
        else:  # 'all'
            source_data.update({
                'topics': metadata.get('topics', []),
                'hadith_references': metadata.get('hadith_references', []),
                'scholar_citations': metadata.get('scholar_citations', []),
                'phrase_analysis': metadata.get('phrase_analysis', []),
                'cross_references': metadata.get('cross_references', []),
                'historical_context': metadata.get('historical_context', []),
                'legal_rulings': metadata.get('legal_rulings', [])
            })

        response['sources'].append(source_data)

    return response

def build_direct_verse_response(verse_data: Dict, verse_metadata_list: List[Dict]) -> Dict:
    """Build comprehensive response for direct verse queries"""
    response = {
        "query_type": "direct_verse",
        "verse_reference": f"{verse_data['surah_number']}:{verse_data['verse_number']}",
        "verses": [{
            "surah": verse_data['surah_number'],  # Use surah_number for annotations
            "surah_name": verse_data['surah_name'],
            "verse_number": str(verse_data['verse_number']),
            "text_saheeh_international": verse_data['english'],
            "arabic_text": verse_data['arabic']
        }],
        "tafsir_explanations": [],
        "metadata_summary": {}
    }

    for item in verse_metadata_list:
        source_name = item['source']
        metadata = item['metadata']

        # Build explanation from topics/commentary
        explanation_parts = []

        if metadata.get('topics'):
            for topic in metadata['topics']:
                if isinstance(topic, dict):
                    if topic.get('topic_header'):
                        explanation_parts.append(f"**{topic['topic_header']}**\n")
                    if topic.get('commentary'):
                        explanation_parts.append(topic['commentary'])
        elif metadata.get('commentary'):
            explanation_parts.append(metadata['commentary'])

        response['tafsir_explanations'].append({
            "source": source_name,
            "explanation": sanitize_heading_format("\n\n".join(explanation_parts)) if explanation_parts else "No detailed commentary available"
        })

        # Add metadata summary
        response['metadata_summary'][source_name] = {
            'hadith_count': len(metadata.get('hadith_references', [])),
            'has_scholar_citations': bool(metadata.get('scholar_citations')),
            'has_phrase_analysis': bool(metadata.get('phrase_analysis')),
            'topic_count': len(metadata.get('topics', [])),
            'cross_references': metadata.get('cross_references', [])
        }

    return response


# ============================================================================
# LLM-ORCHESTRATED DIRECT RETRIEVAL (No Vector Search RAG)
# ============================================================================

# Analytics logging for missing tafsir
MISSING_TAFSIR_LOG = []

def is_valid_verse_reference(surah, verse):
    """
    Validate verse reference exists in Quran using QURAN_METADATA

    Returns: (is_valid: bool, error_message: str)
    """
    if not (1 <= surah <= 114):
        return False, f"Invalid surah {surah} (must be 1-114)"

    max_verses = QURAN_METADATA.get(surah, {}).get('verses', 0)
    if not (1 <= verse <= max_verses):
        return False, f"Invalid verse {verse} for Surah {surah} (max: {max_verses})"

    return True, ""

def normalize_source_key(source):
    """
    Normalize source name to standardized key format
    Handles: "Ibn Kathir", "ibn kathir", "Al-Qurtubi", etc.
    """
    normalized = source.lower().strip()
    normalized = normalized.replace("'", '')  # Remove apostrophes
    normalized = normalized.replace(' ', '-')  # Spaces to hyphens

    # Standardize variations
    mappings = {
        'ibn-kathir': 'ibn-kathir',
        'ibnkathir': 'ibn-kathir',
        'kathir': 'ibn-kathir',
        'al-qurtubi': 'al-qurtubi',
        'qurtubi': 'al-qurtubi',
        'alqurtubi': 'al-qurtubi'
    }

    return mappings.get(normalized, normalized)

def log_missing_tafsir(source, surah, verse):
    """Log missing tafsir for analytics"""
    global MISSING_TAFSIR_LOG
    MISSING_TAFSIR_LOG.append({
        'timestamp': time.time(),
        'source': source,
        'surah': surah,
        'verse': verse
    })

    # Keep only last 100 entries
    if len(MISSING_TAFSIR_LOG) > 100:
        MISSING_TAFSIR_LOG.pop(0)

def fuzzy_lookup_tafsir(source_key, surah, verse):
    """
    Fuzzy fallback: Look for sliding window segments
    Example: ibn-kathir:2:222_0, ibn-kathir:2:222_1
    """
    chunks = []
    segment_idx = 0
    max_segments = 10

    while segment_idx < max_segments:
        segment_key = f"{source_key}:{surah}:{verse}_{segment_idx}"
        chunk_text = TAFSIR_CHUNKS.get(segment_key)

        if chunk_text:
            chunks.append({
                'text': chunk_text,
                'source': source_key,
                'surah': surah,
                'verse': verse,
                'chunk_id': segment_key,
                'distance': 0.0,
                'retrieval_method': 'fuzzy_segment_match'
            })
            segment_idx += 1
        else:
            break

    return chunks

def get_tafsir_for_verse(surah, verse, sources=['Ibn Kathir']):
    """
    Direct lookup of tafsir chunks with normalization and fuzzy fallback

    Args:
        surah: Surah number (1-114)
        verse: Verse number
        sources: List of tafsir sources

    Returns:
        list: Tafsir chunks
    """
    chunks = []

    for source in sources:
        # Al-Qurtubi constraint
        if source == 'Al-Qurtubi' and (surah > 4 or (surah == 4 and verse > 22)):
            continue

        # Normalize source name
        source_key = normalize_source_key(source)
        chunk_key = f"{source_key}:{surah}:{verse}"

        # Primary lookup
        chunk_text = TAFSIR_CHUNKS.get(chunk_key)

        if chunk_text:
            chunks.append({
                'text': chunk_text,
                'source': source,
                'surah': surah,
                'verse': verse,
                'chunk_id': chunk_key,
                'distance': 0.0,
                'retrieval_method': 'direct_lookup'
            })
        else:
            # Fuzzy fallback: Check for segments
            fuzzy_chunks = fuzzy_lookup_tafsir(source_key, surah, verse)
            if fuzzy_chunks:
                chunks.extend(fuzzy_chunks)
            else:
                log_missing_tafsir(source, surah, verse)

    return chunks

def initialize_firebase():
    """Initialize dual database connections"""
    global users_db, quran_db

    try:
        # Get service account credentials from Secret Manager
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(name=FIREBASE_SECRET_FULL_PATH)
        secret_payload = response.payload.data.decode("UTF-8")
        cred_json = json.loads(secret_payload)

        # 1. Initialize Firebase Admin SDK for auth and user profiles
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred, {'projectId': FIREBASE_PROJECT})
        users_db = firestore.client()

        print(f"INFO: Firebase Admin SDK initialized for project '{FIREBASE_PROJECT}'")
        print(f"INFO: User profiles database connected: (default)")

        # 2. Initialize Google Cloud Firestore client for Quran texts
        quran_db = gcp_firestore.Client(
            project=FIREBASE_PROJECT,
            database='tafsir-db'
        )

        print(f"INFO: Quran texts database connected: tafsir-db")

        # 3. Test both connections
        try:
            users_collections = list(users_db.collections())
            print(f"INFO: Users database verified - found {len(users_collections)} collections")

            quran_collections = list(quran_db.collections())
            print(f"INFO: Quran database verified - found {len(quran_collections)} collections")

        except Exception as e:
            print(f"WARNING: Database verification failed: {e}")

    except Exception as e:
        print(f"CRITICAL STARTUP ERROR in initialize_firebase: {type(e).__name__} - {e}")
        raise

# Initialize services on startup (fail fast if any critical component fails)
initialize_firebase()
load_chunks_from_verse_files_enhanced() # UPDATED CALL

# Load the static verse range map (ground-truth validated with full payload:
# prompt template + verse text + tafsir chunks + scholarly sources + output allocation).
# Falls back to in-memory precomputation if the static map is missing.
from services.token_budget_service import load_range_map, precompute_verse_budgets
if not load_range_map():
    print("WARNING: Static range map not found — falling back to in-memory precomputation")
    precompute_verse_budgets(TAFSIR_CHUNKS, QURAN_METADATA)
else:
    print("INFO: Loaded ground-truth verse range map from data/verse_range_map.json")

vertexai.init(project=GCP_INFRASTRUCTURE_PROJECT, location=LOCATION)

# --- Firebase Auth Decorator ---
def firebase_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        id_token = request.headers.get("Authorization", "").split("Bearer ")[-1]
        if not id_token:
            return jsonify({"error": "Authorization token is missing"}), 401
        try:
            decoded_token = auth.verify_id_token(id_token)
            request.user = decoded_token
        except Exception as e:
            return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401
        return f(*args, **kwargs)
    return decorated_function

def firebase_auth_optional(f):
    """Optional auth - sets request.user if token is valid, but doesn't require it"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        id_token = request.headers.get("Authorization", "").split("Bearer ")[-1]
        if id_token:
            try:
                decoded_token = auth.verify_id_token(id_token)
                request.user = decoded_token
            except Exception:
                # Token invalid or expired, but that's OK for optional auth
                request.user = None
        else:
            request.user = None
        return f(*args, **kwargs)
    return decorated_function

# --- Comprehensive Error Handler Decorator ---
def handle_errors(f):
    """
    Comprehensive error handling wrapper for API endpoints.
    Catches and properly formats various types of errors.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except auth.InvalidIdTokenError as e:
            return jsonify({
                "error": "Authentication failed",
                "type": "auth_error",
                "details": str(e)
            }), 401
        except auth.ExpiredIdTokenError as e:
            return jsonify({
                "error": "Authentication token expired",
                "type": "token_expired",
                "details": "Please sign in again"
            }), 401
        except gcp_firestore.DocumentNotFoundError as e:
            return jsonify({
                "error": "Resource not found",
                "type": "not_found",
                "details": str(e)
            }), 404
        except requests.Timeout as e:
            return jsonify({
                "error": "Service timeout",
                "type": "timeout",
                "details": "The AI service is taking longer than expected. Please try again.",
                "retry": True
            }), 503
        except requests.HTTPError as e:
            error_code = e.response.status_code if hasattr(e, 'response') else 500
            return jsonify({
                "error": "External service error",
                "type": "http_error",
                "details": str(e),
                "status_code": error_code
            }), 502
        except json.JSONDecodeError as e:
            return jsonify({
                "error": "Invalid response format",
                "type": "parse_error",
                "details": "The AI response could not be parsed. Please try rephrasing your query."
            }), 500
        except ValueError as e:
            return jsonify({
                "error": "Invalid input",
                "type": "validation_error",
                "details": str(e)
            }), 400
        except Exception as e:
            # Log the full error for debugging
            print(f"❌ Unhandled error in {f.__name__}: {type(e).__name__} - {e}")
            traceback.print_exc()

            # Return generic error to client
            return jsonify({
                "error": "An unexpected error occurred",
                "type": "internal_error",
                "details": "The request could not be completed. Please try again later."
            }), 500

    return wrapper

# --- JSON Extraction Helper ---
def fix_malformed_json(text: str) -> str:
    """
    Comprehensive JSON cleanup for malformed Gemini responses.
    Handles:
    1. Unescaped quotes inside string values
    2. Trailing commas before closing braces/brackets
    3. Invalid control characters (unescaped newlines, tabs, carriage returns)
    4. Unicode issues (BOM, zero-width spaces)
    5. Smart quotes and other typography
    """
    import re

    # Step 1: Remove BOM and invisible characters
    text = text.lstrip('\ufeff\u200b\u200c\u200d\ufeff')

    # Step 2: Replace smart quotes with regular quotes (if any slipped through)
    text = text.replace('\u201c', '"').replace('\u201d', '"')  # " "
    text = text.replace('\u2018', "'").replace('\u2019', "'")  # ' '

    # Step 3: Remove trailing commas before closing braces/brackets
    text = re.sub(r',(\s*[}\]])', r'\1', text)

    # Step 4: Fix unescaped quotes and control characters in JSON string values
    # We need to identify string values and escape:
    # - Unescaped quotes
    # - Control characters (newlines, tabs, carriage returns)

    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(text):
        char = text[i]

        # Handle escape sequences
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == '\\':
            result.append(char)
            escape_next = True
            i += 1
            continue

        # Handle double quotes
        if char == '"':
            if not in_string:
                # Starting a string
                in_string = True
                result.append(char)
                i += 1
                continue
            else:
                # Possibly ending a string - check what comes after
                # Look ahead to find next non-whitespace character
                next_idx = i + 1
                while next_idx < len(text) and text[next_idx] in ' \t\n\r':
                    next_idx += 1

                next_char = text[next_idx] if next_idx < len(text) else None

                # If followed by ,, }, ], or end of text, this closes the string
                if next_char is None or next_char in ',}]':
                    in_string = False
                    result.append(char)
                    i += 1
                    continue
                elif next_char == ':':
                    # Colon could be JSON key separator OR part of text like "Ababil": Ibn...
                    # Check if colon is followed by a JSON value start: ", {, [, digit, true, false, null
                    colon_idx = next_idx + 1
                    while colon_idx < len(text) and text[colon_idx] in ' \t\n\r':
                        colon_idx += 1
                    after_colon = text[colon_idx] if colon_idx < len(text) else None

                    # If after colon we have a JSON value start, this quote ends the string (it's a key)
                    if after_colon in '"{[0123456789tfn-':
                        in_string = False
                        result.append(char)
                        i += 1
                        continue
                    else:
                        # Colon followed by text (e.g., "Ababil": Ibn) - escape the quote
                        result.append('\\')
                        result.append(char)
                        i += 1
                        continue
                else:
                    # This is an unescaped quote in the middle - escape it!
                    result.append('\\')
                    result.append(char)
                    i += 1
                    continue

        # Handle control characters INSIDE strings only
        if in_string:
            if char == '\n':
                result.append('\\n')
                i += 1
                continue
            elif char == '\r':
                result.append('\\r')
                i += 1
                continue
            elif char == '\t':
                result.append('\\t')
                i += 1
                continue

        # Normal character
        result.append(char)
        i += 1

    return ''.join(result)


def extract_json_from_response(text: str) -> Optional[dict]:
    """
    Enhanced robust JSON extraction from Gemini responses.
    Handles:
    - Direct JSON
    - JSON wrapped in markdown code blocks
    - JSON embedded in text
    - Malformed JSON with common issues (unescaped quotes, trailing commas, etc.)
    - Truncated responses
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # Try 1: Direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"⚠️ Initial JSON parse failed at position {e.pos}: {e.msg}")

        # If it looks like a quote/comma/control character issue, try comprehensive fix
        if any(keyword in str(e.msg) for keyword in ["Expecting ','", "Expecting ':'", "Unterminated string", "Invalid control character"]):
            print(f"⚠️ Attempting comprehensive JSON cleanup...")
            try:
                fixed_text = fix_malformed_json(text)
                result = json.loads(fixed_text)
                print(f"✅ Successfully cleaned and parsed malformed JSON!")
                return result
            except json.JSONDecodeError as e2:
                print(f"⚠️ Cleanup failed at position {e2.pos}: {e2.msg}")
                if e2.pos < len(fixed_text):
                    context_start = max(0, e2.pos - 100)
                    context_end = min(len(fixed_text), e2.pos + 100)
                    print(f"⚠️ Error context: ...{fixed_text[context_start:e2.pos]}<<<HERE>>>{fixed_text[e2.pos:context_end]}...")
                # Continue to other methods below
            except Exception as ex:
                print(f"⚠️ Unexpected error during cleanup: {str(ex)}")

        # Continue with original fallback logic
        pass

    # Try 2: Extract from markdown code blocks
    json_pattern = r'```(?:json)?\s*(.*?)\s*```'
    matches = re.findall(json_pattern, text, re.DOTALL)
    for match in matches:
        try:
            # Clean common JSON issues
            cleaned = match.strip()
            # Remove trailing commas before closing braces/brackets
            cleaned = re.sub(r',\s*}', '}', cleaned)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            continue

    # Try 3: Find JSON object using improved brace matching
    try:
        # Look for opening brace and find matching closing brace
        start_idx = text.find('{')
        if start_idx != -1:
            brace_count = 0
            end_idx = start_idx
            in_string = False
            escape_next = False

            for i in range(start_idx, len(text)):
                char = text[i]

                if escape_next:
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break

            json_str = text[start_idx:end_idx+1]
            # Clean common issues
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try 4: Last resort - find first { to last }
    try:
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = text[start_idx:end_idx+1]
            # Clean common issues
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Try 5: Fallback - create minimal valid response
    print(f"⚠️ JSON extraction failed, using fallback response")
    print(f"⚠️ Response length: {len(text)} chars")

    # Check for common JSON issues
    has_opening_brace = text.strip().startswith('{')
    has_closing_brace = text.strip().endswith('}')
    brace_count = text.count('{') - text.count('}')

    print(f"⚠️ JSON structure check: starts_with_brace={has_opening_brace}, ends_with_brace={has_closing_brace}, brace_imbalance={brace_count}")

    # LOG RESPONSE (truncated for large responses)
    if len(text) > 2000:
        print(f"⚠️ === FIRST 1000 CHARS OF GEMINI RESPONSE ===")
        print(text[:1000])
        print(f"⚠️ === (TRUNCATED - TOTAL LENGTH: {len(text)} chars) ===")
    else:
        print("⚠️ === COMPLETE GEMINI RESPONSE ===")
        print(text)
        print("⚠️ === END RESPONSE ===")

    # If response looks like it might be valid JSON that's just very long, try one more parse
    if has_opening_brace and has_closing_brace and brace_count == 0:
        print(f"⚠️ Response structure looks valid, attempting final JSON parse...")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"⚠️ Final parse failed at position {e.pos}: {e.msg}")

            # Show context around the exact error
            if e.pos < len(text):
                context_start = max(0, e.pos - 150)
                context_end = min(len(text), e.pos + 150)
                print(f"⚠️ Error context (150 chars before/after pos {e.pos}):")
                print(text[context_start:e.pos] + " <<<ERROR_HERE>>> " + text[e.pos:context_end])

    return {
        "response": text[:500] if len(text) > 500 else text,
        "sources": [],
        "verses": [],
        "metadata": {
            "extraction_error": True,
            "fallback_used": True
        }
    }

# --- Token Counting Helper ---
def count_tokens_approximate(text: str) -> int:
    """
    Rough token count estimation.
    Rule of thumb: ~4 characters = 1 token
    """
    if not text:
        return 0
    return len(text) // 4

def truncate_context_if_needed(context: str, max_tokens: int = 50000) -> str:
    """
    Truncate context to fit within Gemini token limits.
    Gemini 2.5 Flash: 1M input + 65K output
    Conservative limit of 50K tokens (typical queries: 6K-25K, max realistic: 40K)
    Ensures fast processing and lower costs while handling all realistic query scenarios
    """
    current_tokens = count_tokens_approximate(context)

    if current_tokens <= max_tokens:
        return context

    print(f"⚠️ Context too large ({current_tokens} tokens), truncating to {max_tokens} tokens")

    # Calculate truncation ratio
    truncation_ratio = max_tokens / current_tokens
    truncated_length = int(len(context) * truncation_ratio)

    # Truncate and add notice
    return context[:truncated_length] + "\n\n[Note: Context truncated due to length. Results may be incomplete.]"

# --- Query Expansion ---
def sanitize_source_text_for_prompt(text):
    """Replace double quotes with single quotes in source text before embedding in prompts.

    This prevents Gemini from echoing unescaped double quotes into JSON string
    values, which causes 'Expecting , delimiter' parse errors. The scholarly
    source texts (Ibn Kathir, al-Qurtubi, Ihya, etc.) contain abundant double
    quotes from scholar speech patterns like: Ibn Jarir said, "The Arabs..."
    """
    if not text:
        return text
    return text.replace('"', "'")


def build_structured_context(context_by_source, arabic_text=None, cross_refs=None):
    """Build enhanced context blocks with Arabic text and cross-references"""
    context_sections = []

    # Add Arabic text if available
    if arabic_text:
        context_sections.append(f"--- ARABIC TEXT ---\n{arabic_text}\n")

    # Add cross-references if available
    if cross_refs:
        refs_text = ", ".join(cross_refs)
        context_sections.append(f"--- RELATED VERSES ---\n{refs_text}\n")

    # Add source content (sanitize to prevent malformed JSON from Gemini)
    for source_name, chunks in context_by_source.items():
        if chunks:
            section = f"--- {source_name.upper()} ---\n"
            section += "\n\n".join(sanitize_source_text_for_prompt(c) for c in chunks)
            context_sections.append(section)
        else:
            section = f"--- {source_name.upper()} ---\n[No highly relevant passages found]"
            context_sections.append(section)

    return "\n\n" + "\n\n".join(context_sections)

# ============================================================================
# SCHOLARLY SOURCE CONTEXT HELPER
# ============================================================================

def _get_scholarly_context_for_prompt(query, verse_data=None):
    """Extract surah/verse info from verse_data and fetch scholarly context."""
    try:
        surah_number = None
        verse_start = None
        verse_end = None

        if verse_data:
            if isinstance(verse_data, list) and len(verse_data) > 0:
                surah_number = verse_data[0].get('surah_number')
                verse_start = verse_data[0].get('verse_number')
                verse_end = verse_data[-1].get('verse_number')
            elif isinstance(verse_data, dict):
                surah_number = verse_data.get('surah_number')
                verse_start = verse_data.get('verse_number')

        # Also extract topic keywords from query for topic-based retrieval
        topic_keywords = extract_topic_keywords_from_query(query)

        ctx = get_relevant_scholarly_context(
            surah_number=surah_number,
            verse_start=verse_start,
            verse_end=verse_end,
            topic_keywords=topic_keywords,
        )
        return ctx
    except Exception as e:
        print(f"⚠️ Scholarly source retrieval error (non-fatal): {e}")
        return ""


def _get_scholarly_sources_metadata(query, verse_data=None):
    """Get metadata about which scholarly sources were used for this query."""
    try:
        surah_number = None
        verse_start = None
        verse_end = None

        if verse_data:
            if isinstance(verse_data, list) and len(verse_data) > 0:
                surah_number = verse_data[0].get('surah_number')
                verse_start = verse_data[0].get('verse_number')
                verse_end = verse_data[-1].get('verse_number')
            elif isinstance(verse_data, dict):
                surah_number = verse_data.get('surah_number')
                verse_start = verse_data.get('verse_number')

        topic_keywords = extract_topic_keywords_from_query(query)

        return get_scholarly_sources_metadata(
            surah_number=surah_number,
            verse_start=verse_start,
            verse_end=verse_end,
            topic_keywords=topic_keywords,
        )
    except Exception as e:
        print(f"⚠️ Scholarly sources metadata error (non-fatal): {e}")
        return []


# ============================================================================
# TWO-STAGE SCHOLARLY RETRIEVAL: Plan → Fetch → Answer
# ============================================================================

def plan_scholarly_retrieval(planning_prompt):
    """
    Call Gemini to generate a scholarly retrieval plan.
    Returns a dict with 'pointers' list, or None on failure.
    Includes retry logic for 429/503/timeout (matching generation call pattern).
    """
    import re as _re
    plan_start = time.time()
    print(f"  [SCHOLARLY-PLAN] Starting planning call ({len(planning_prompt)} char prompt)")

    try:
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        token = credentials.token

        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

        body = {
            "contents": [{"role": "user", "parts": [{"text": planning_prompt}]}],
            "generation_config": {
                "response_mime_type": "application/json",
                "temperature": 0.05,
                "top_k": 10,
                "top_p": 0.8,
                "maxOutputTokens": 8192,
            },
        }

        # Retry logic matching the generation call pattern
        max_retries = 3
        response = None
        for attempt in range(max_retries):
            retry_delay = 2 ** (attempt + 1)  # 2s, 4s, 8s
            try:
                api_start = time.time()
                response = requests.post(
                    VERTEX_ENDPOINT,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=body,
                    timeout=60,
                )
                api_duration = time.time() - api_start
                print(f"  [SCHOLARLY-PLAN] Gemini responded: HTTP {response.status_code} in {api_duration:.2f}s (attempt {attempt+1})")

                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        print(f"  [SCHOLARLY-PLAN] Rate limited (429), retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    print(f"  [SCHOLARLY-PLAN] Rate limited after {max_retries} attempts")
                    return None

                if response.status_code == 503:
                    if attempt < max_retries - 1:
                        print(f"  [SCHOLARLY-PLAN] Service unavailable (503), retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    print(f"  [SCHOLARLY-PLAN] Service unavailable after {max_retries} attempts")
                    return None

                response.raise_for_status()
                break  # Success

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"  [SCHOLARLY-PLAN] Timeout on attempt {attempt+1}, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                print(f"  [SCHOLARLY-PLAN] TIMEOUT after {max_retries} attempts ({(time.time()-plan_start)*1000:.0f}ms total)")
                return None

            except requests.exceptions.HTTPError as he:
                print(f"  [SCHOLARLY-PLAN] HTTP ERROR: {he}")
                return None

        if not response or response.status_code != 200:
            return None

        raw_response = response.json()
        generated_text = safe_get_nested(raw_response, "candidates", 0, "content", "parts", 0, "text")
        finish_reason = safe_get_nested(raw_response, "candidates", 0, "finishReason")
        print(f"  [SCHOLARLY-PLAN] finishReason={finish_reason}")

        if not generated_text:
            safety_ratings = safe_get_nested(raw_response, "candidates", 0, "safetyRatings")
            print(f"  [SCHOLARLY-PLAN] Empty response! finishReason={finish_reason}, safety={safety_ratings}")
            return None

        print(f"  [SCHOLARLY-PLAN] Generated: {len(generated_text)} chars — {generated_text[:200]}")

        try:
            plan = json.loads(generated_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown fences
            match = _re.search(r'\{[\s\S]*\}', generated_text)
            if match:
                plan = json.loads(match.group())
            else:
                print(f"  [SCHOLARLY-PLAN] JSON parse failed, text: {generated_text[:300]}")
                return None

        pointers = plan.get("pointers", [])
        reasoning = plan.get("reasoning", "")
        print(f"  [SCHOLARLY-PLAN] SUCCESS: {len(pointers)} pointers in {(time.time()-plan_start)*1000:.0f}ms — {reasoning}")
        for p in pointers:
            print(f"    -> {p}")
        return plan

    except Exception as e:
        print(f"  [SCHOLARLY-PLAN] EXCEPTION: {type(e).__name__}: {str(e)[:200]}")
        return None


def _get_scholarly_context_two_stage(query, verse_data, context_by_source):
    """
    Scholarly retrieval: pre-computed plans + deterministic keyword matching.

    Uses pre-computed Gemini plans (generated offline with full tafsir context)
    merged with keyword routing and verse-map discovery. No runtime API calls.

    Returns (scholarly_ctx_string, badges_list, pipeline_info).
    """
    start = time.time()
    print(f"\n  [SCHOLARLY] === Starting scholarly retrieval ===")

    def _fallback(reason):
        print(f"  [SCHOLARLY] FALLBACK: {reason}")
        ctx = _get_scholarly_context_for_prompt(query, verse_data)
        badges = _get_scholarly_sources_metadata(query, verse_data)
        return ctx, badges, f"fallback: {reason}"

    try:
        # Extract verse info
        surah_number = None
        verse_start = None
        verse_end = None
        verse_text = ""

        if verse_data:
            if isinstance(verse_data, list) and len(verse_data) > 0:
                surah_number = verse_data[0].get('surah_number')
                verse_start = verse_data[0].get('verse_number')
                verse_end = verse_data[-1].get('verse_number')
                verse_text = verse_data[0].get('english', '') or verse_data[0].get('text_saheeh_international', '') or ''
            elif isinstance(verse_data, dict):
                surah_number = verse_data.get('surah_number')
                verse_start = verse_data.get('verse_number')
                verse_text = verse_data.get('english', '') or verse_data.get('text_saheeh_international', '') or ''

        if not surah_number or not verse_start:
            return _fallback(f"No verse info (surah={surah_number}, verse={verse_start})")

        # Extract Ibn Kathir summary from context_by_source
        ibn_kathir_summary = ""
        if context_by_source:
            for key in context_by_source:
                if "ibn kathir" in key.lower() or "ibn_kathir" in key.lower():
                    texts = context_by_source[key]
                    if texts and isinstance(texts, list):
                        ibn_kathir_summary = str(texts[0])[:500]
                    elif isinstance(texts, str):
                        ibn_kathir_summary = texts[:500]
                    break

        # --- Single call: deterministic planner (now includes pre-computed plans) ---
        plan = plan_scholarly_retrieval_deterministic(
            surah_number, verse_start, verse_end,
            verse_text[:300], ibn_kathir_summary
        )
        pointers = plan["pointers"]
        print(f"  [SCHOLARLY] Plan: {len(pointers)} pointers — {plan['reasoning']}")

        for p in pointers:
            print(f"    -> {p}")

        # --- Resolve pointers ---
        resolved = resolve_scholarly_pointers(pointers)

        if not resolved["excerpts"]:
            return _fallback(f"All {len(pointers)} pointers resolved to empty")

        # Format for generation prompt
        scholarly_ctx = format_scholarly_excerpts_for_prompt(resolved)
        badges = resolved["sources_used"]

        duration = (time.time() - start) * 1000
        pipeline_info = f"precomputed: {len(resolved['excerpts'])} excerpts, {len(badges)} badges in {duration:.0f}ms"
        print(f"  [SCHOLARLY] SUCCESS: {pipeline_info}")
        print(f"  [SCHOLARLY] Badges: {[b['key'] for b in badges]}")
        return scholarly_ctx, badges, pipeline_info

    except Exception as e:
        print(f"  [SCHOLARLY] EXCEPTION: {type(e).__name__}: {str(e)[:300]}")
        traceback.print_exc()
        return _fallback(f"Exception: {type(e).__name__}: {str(e)[:200]}")


# ============================================================================
# UPDATED: PERSONA-ADAPTIVE CLARITY-ENHANCED PROMPT WITH NEW PROFILE DATA
# ============================================================================

def build_enhanced_prompt(query, context_by_source, user_profile, arabic_text=None, cross_refs=None, query_type="default", verse_data=None, approach="tafsir", scholarly_context="", verse_limit=None):
    """
    ENHANCED VERSION: Gemini as Scholarly Editor with Persona-Adaptive Formatting
    UPDATED: Now includes learning_goal, knowledge_level, and refined formatting rules
    NEW: Approach-based instructions (tafsir/thematic/historical)

    Gives Gemini explicit instructions to:
    1. Fix grammar/clarity while preserving accuracy
    2. Adapt content FORMAT to user persona (bullets for beginners, prose for scholars)
    3. Use verse translations from backend (not generate them)
    4. Adapt depth and focus based on learning_goal and knowledge_level
    5. Emphasize different aspects based on approach (tafsir/thematic/historical)
    """
    structured_context = build_structured_context(context_by_source, arabic_text, cross_refs)

    # Dynamic verse limit — computed from token budget, falls back to default
    VERSE_LIMIT = verse_limit if verse_limit else VERSE_LIMIT_DEFAULT

    # Get persona configuration
    persona_name = user_profile.get('persona', 'practicing_muslim')
    if persona_name not in PERSONAS:
        persona_name = 'practicing_muslim'  # Fallback to default

    persona = PERSONAS[persona_name]
    format_style = persona.get('format_style', 'balanced')

    # NEW: Get knowledge_level from profile (Suggestion 1)
    knowledge_level = user_profile.get('knowledge_level', 'intermediate')

    # NEW: Get learning_goal and create goal_instruction
    learning_goal = user_profile.get('learning_goal', 'balanced')

    goal_instructions = {
        'application': "Focus on practical applications and how to apply these teachings in daily life. Emphasize actionable takeaways and real-world relevance.",
        'understanding': "Focus on deep comprehension and scholarly context. Emphasize theological depth, historical background, and scholarly interpretation.",
        'balanced': "Balance practical applications with scholarly understanding. Provide both actionable insights and theological depth."
    }

    goal_instruction = goal_instructions.get(learning_goal, goal_instructions['balanced'])

    # NEW: Approach-specific instructions (MERGED: historical + thematic → semantic)
    approach_instructions = {
        'tafsir': """
📖 TAFSIR-BASED APPROACH:
Focus on CLASSICAL COMMENTARY and verse-by-verse analysis.
- Emphasize what classical scholars (Ibn Kathir, al-Qurtubi) said about specific verses
- Provide linguistic analysis and word meanings where relevant
- Deep dive into the interpretation of individual verses or small verse sets
- Prioritize scholarly precision and detailed explanation
        """,
        'semantic': """
🔍 SEMANTIC SEARCH APPROACH:
Focus on COMPREHENSIVE EXPLORATION of themes, events, and concepts.
- For THEMATIC queries: Identify verses across different surahs that relate to the same theme, extract patterns and principles
- For HISTORICAL queries: Emphasize asbab al-nuzul, chronological context, and how events illuminate meaning
- For EVENT queries: Connect verses to specific battles, treaties, or incidents with timeline
- Group content by sub-topics or themes rather than verse-by-verse
- Show connections and relationships across different verses and contexts
- Present a holistic view of how the Quran addresses this topic or event
        """
    }

    approach_instruction = approach_instructions.get(approach, approach_instructions['tafsir'])

    # Add verse information if available (handles both single verse and list of verses)
    verse_info = ""
    if verse_data:
        if isinstance(verse_data, list):
            # Multiple verses in a range
            verse_info = "\n--- VERSE DETAILS (PROVIDED BY BACKEND) ---\n"
            verse_info += f"Surah: {verse_data[0]['surah_number']} ({verse_data[0]['surah_name']})\n"
            verse_info += f"Verse Range: {verse_data[0]['verse_number']}-{verse_data[-1]['verse_number']}\n\n"

            for v in verse_data:
                verse_info += f"**Verse {v['verse_number']}:**\n"
                verse_info += f"Arabic: {v['arabic']}\n"
                verse_info += f"English Translation (Saheeh International): {v['english']}\n"
                verse_info += f"Transliteration: {v['transliteration']}\n\n"

            verse_info += "IMPORTANT: These verse texts are already provided by our backend.\n"
            verse_info += "You do NOT need to provide verse translations - focus on explaining the TAFSIR (commentary).\n"
        else:
            # Single verse
            verse_info = f"""
--- VERSE DETAILS (PROVIDED BY BACKEND) ---
Surah: {verse_data['surah_number']} ({verse_data['surah_name']})
Verse: {verse_data['verse_number']}
Arabic: {verse_data['arabic']}
English Translation (Saheeh International): {verse_data['english']}
Transliteration: {verse_data['transliteration']}

IMPORTANT: These verse texts are already provided by our backend.
You do NOT need to provide verse translations - focus on explaining the TAFSIR (commentary).
"""

    # Build the clarity-enhanced, persona-adaptive prompt
    prompt = f"""You are a SCHOLARLY EDITOR for an Islamic learning platform, transforming classical tafsir into clear, polished explanations for modern readers.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER PROFILE: {persona['name']} ({knowledge_level.title()} Level)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Tone: {persona['tone']}
• Vocabulary: {persona['vocabulary']}
• Knowledge Level: {knowledge_level}
• Learning Goal: {learning_goal}
• Include hadith: {'Yes' if persona['include_hadith'] else 'No - avoid hadith references'}
• Scholarly debates: {'Yes' if persona['scholarly_debates'] else 'No - avoid scholarly disagreements'}
• Format style: {format_style}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEARNING GOAL INSTRUCTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{goal_instruction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPROACH-SPECIFIC INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{approach_instruction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER QUERY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"{query}"

Query Type: {query_type}
Approach: {approach.upper()}
{verse_info}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE MATERIAL (Classical Tafsir - May Have Issues)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{structured_context}

⚠️ NOTE: This source material comes from JSON-structured classical tafsir texts.
It may contain grammar errors, typos, run-on sentences, missing punctuation, and awkward phrasing from translation/OCR.
{scholarly_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR ROLE AS SCHOLARLY EDITOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ ENHANCE CLARITY (Your Primary Job):
1. **Fix Grammar & Structure**
   • Correct grammatical errors
   • Fix run-on sentences and fragments
   • Add proper punctuation and capitalization
   • Improve sentence flow and transitions

2. **Improve Readability**
   • Break complex sentences into simpler ones
   • Use clear paragraph structure
   • Add helpful transitions between ideas
   • Make connections between concepts explicit
   • Organize information logically

3. **Clarify Terminology**
   • Define Islamic terms appropriately for the user's level ({persona['vocabulary']})
   • Use consistent transliteration
   • Add brief explanations where needed
   • Make implicit references explicit

4. **Adapt to User Profile**
   • Match vocabulary to user's level ({persona['vocabulary']})
   • Use appropriate tone ({persona['tone']})
   • Follow the learning goal: {learning_goal}
   • Adjust depth to knowledge level: {knowledge_level}

5. **Content Guidelines Based on Profile**
   • Hadith references: {'INCLUDE hadith citations when relevant' if persona['include_hadith'] else 'AVOID hadith references - omit or minimize them'}
   • Scholarly debates: {'INCLUDE different scholarly opinions when relevant' if persona['scholarly_debates'] else 'AVOID scholarly disagreements - present unified explanations'}

❌ PRESERVE ACCURACY (Never Compromise):
1. **Never Alter Scholarly Content**
   • Do NOT change the meaning of tafsir
   • Do NOT add interpretations not in source
   • Do NOT omit important scholarly details
   • Do NOT change theological positions

2. **Keep Attributions Exact**
   • Scholar names MUST remain exact (Ibn Kathir, al-Qurtubi)
   • Hadith narrators MUST be preserved exactly
   • Do NOT reassign opinions to different scholars

3. **Sacred Text Unchanged**
   • Verse translations are provided by backend - DO NOT generate them
   • Arabic Quranic text stays EXACTLY as provided
   • Do NOT paraphrase verse translations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERSE LIMITS - CRITICAL FOR PERFORMANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚨 STRICT VERSE LIMIT: Maximum {VERSE_LIMIT} verses per response.

IMPORTANT: Even if more verses are provided in the source material, you MUST:
1. Select only the MOST RELEVANT verses that directly answer the query
2. Stay WITHIN the {VERSE_LIMIT}-verse limit
3. Prioritize quality over quantity
4. For broad queries, focus on the most foundational or representative verses

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE FORMAT - STANDARDIZED STRUCTURE (ALL PERSONAS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL: Return valid JSON with CONSISTENT formatting across ALL personas.

UNIVERSAL FORMAT RULES (applies to ALL personas):
- Use SHORT PARAGRAPH format (2-4 sentences per paragraph)
- Use **Bolded Sub-Headers** before each paragraph for scannability
- NO bullet points (no •, -, or numbered lists)
- NO emojis anywhere in the response
- Vocabulary adapts to persona level, but structure remains consistent
- Scholarly citations integrated naturally where appropriate

STANDARD EXAMPLE (all personas follow this structure):
"**Theological Significance**
Ayat al-Kursi (2:255) represents a comprehensive theological statement regarding divine attributes. This verse contains a concentrated exposition of tawhid (divine oneness) in the Quran.

**Divine Attributes**
The verse presents both positive attributes (al-Hayy, al-Qayyum) and negative attributes (no slumber, no fatigue) to establish Allah's absolute transcendence. It moves systematically from Allah's essence to His knowledge to His power.

**Practical Application**
The Prophet (peace be upon him) taught that reciting this verse provides spiritual protection. Many Muslims incorporate it into their daily remembrance, especially before sleep.

**Key Insight**
This verse reminds us that Allah's care never ceases. When we feel alone, we can find comfort in knowing He is always aware and present."

VOCABULARY ADAPTATION BY PERSONA:
- Beginner personas (new_revert, curious_explorer): Use simple, everyday language while maintaining paragraph structure
- Intermediate personas (practicing_muslim): Use moderate vocabulary with some Arabic terms explained
- Advanced personas (student, advanced_learner): Use technical terminology and scholarly citations

JSON Structure (verse text ALREADY provided by backend - you focus on tafsir):

CRITICAL VERSE SELECTION RULES:
• Maximum verses: {VERSE_LIMIT} verses
• Include ONLY the most directly relevant verses to the query
• If more verses are provided in source material, SELECT and PRIORITIZE based on relevance
• Better to have fewer highly relevant verses than many tangentially related ones

CRITICAL: The tafsir_explanations array MUST contain EXACTLY TWO sources and NO MORE:
1. al-Qurtubi
2. Ibn Kathir

DO NOT add any additional sources to tafsir_explanations like "General Scholarly Analysis", "Additional Commentary", or any other source names.
ONLY use the source material provided above for tafsir_explanations. DO NOT generate additional explanations from your own knowledge.

However, USE the Additional Scholarly Sources (if provided above) EXTENSIVELY to create deeply layered responses:
- The "lessons_practical_applications" section MUST integrate scholarly sources by name ("Imam al-Ghazali explains...", "Ibn al-Qayyim describes...")
- The "hadith" section should use hadith excerpts from Riyad al-Saliheen when provided
- The "summary" section must connect classical tafsir with spiritual insights from scholarly sources
- NEVER cite granular section names (e.g., "Section: SECRETS OF MARRIAGE"). Instead, cite naturally: "Imam al-Ghazali, in Ihya Ulum al-Din, discusses..."

{{
    "verses": [
        {{
            "surah": "Surah name (from verse_data)",
            "verse_number": "verse number (from verse_data)",
            "text_saheeh_international": "English translation (from verse_data)",
            "arabic_text": "Arabic text (from verse_data)"
        }}
        // LIMIT: Maximum {VERSE_LIMIT} verses
    ],

    "tafsir_explanations": [
        {{
            "source": "al-Qurtubi",
            "explanation": "Use short paragraphs (2-4 sentences) with **bolded sub-headers**. NO bullets, NO emojis. Fix all grammar, improve clarity, preserve accuracy. If verse beyond Surah 4:22, state: 'Al-Qurtubi's tafsir is not available for this verse.'"
        }},
        {{
            "source": "Ibn Kathir",
            "explanation": "Use short paragraphs (2-4 sentences) with **bolded sub-headers**. NO bullets, NO emojis. Fix all grammar, improve clarity, preserve accuracy."
        }}
    ],

    "cross_references": [
        {{
            "verse": "Related verse reference (e.g., '2:256')",
            "relevance": "Brief, clear explanation"
        }}
    ],

    "hadith": [
        {{
            "reference": "Source attribution (e.g., 'Sahih Bukhari 1234' or 'Riyad al-Saliheen, Imam al-Nawawi'). NEVER include section/chapter names like 'Section: X'.",
            "text": "The hadith text or a scholarly excerpt. If from Riyad al-Saliheen data, use the provided text. Cite naturally: 'Imam al-Ghazali, in Ihya Ulum al-Din, discusses...' — NOT 'Section: SECRETS OF MARRIAGE'.",
            "relevance": "How this connects to the verse. Weave in the scholarly perspective — why this teaching matters for the verse's message."
        }}
    ],

    "lessons_practical_applications": [
        {{
            "point": "Lesson title (Synthesis)",
            "type": "synthesis",
            "body": "A rich narrative paragraph that synthesizes the scholarly sources with the verse's themes. Reference scholars by name naturally: 'Imam al-Ghazali argues that...', 'The thematic structure of this Surah suggests...', 'Ibn al-Qayyim explains that...'. This should feel like a continuation of the scholarly tradition — authoritative and illuminating, NOT preachy or generic."
        }},
        {{
            "point": "Lesson title (Contemplation)",
            "type": "contemplation",
            "core_principle": "A concise statement of the ethical/spiritual principle derived from the verse.",
            "contemplation": "A deep, probing question that forces genuine self-reflection. Example: 'If you stripped away all human witnesses to your good deeds, what would remain of your motivation?'",
            "prophetic_anchor": "A short hadith or scholarly quote that answers or deepens the contemplation."
        }},
        {{
            "point": "Lesson title (Progression)",
            "type": "progression",
            "baseline": "The Baseline — what is required at the Shariah level. The external, foundational obligation or understanding.",
            "ascent": "The Ascent — how to refine the intention at the Tariqah level. The psychological and spiritual refinement, drawing from Ihya or Madarij.",
            "peak": "The Peak — the state of the heart once the lesson is mastered at the Haqiqah level. The transformed worldview and spiritual station."
        }}
    ],

    "summary": "A concise scholarly synthesis (4-6 sentences). Connect the classical tafsir (Ibn Kathir/al-Qurtubi) with spiritual insights from the scholarly sources. This is NOT a blurb — it should demonstrate how the verse sits within the broader Islamic intellectual tradition. Reference specific scholars and their contributions to understanding this verse.",

    "reflection_prompt": "A single, deeply personal question (1-2 sentences) that invites the reader to reflect on how THIS SPECIFIC verse applies to their life today. The question must be unique to the verse's content — reference the verse's themes, imagery, or commands directly. Examples: For a verse about charity, ask about generosity in the reader's daily life. For a verse about patience, ask about a current trial they face. NEVER use generic prompts like 'How does this verse apply to your life?' — always tie it to the verse's specific message. The tone should be warm, introspective, and non-judgmental."
}}

FORMATTING RULES (ALL PERSONAS):
- Use short paragraphs (2-4 sentences each) with **bolded sub-headers**
- NO bullet points, NO numbered lists, NO emojis
- NEVER use single asterisks for italics (*word*). Use only double asterisks for **bold headers**.
- Vocabulary complexity adapts to persona, structure stays consistent
- When citing scholarly sources, cite naturally by scholar name — NEVER cite section/chapter numbers (e.g., say "Imam al-Ghazali, in Ihya Ulum al-Din, explains..." NOT "Ihya Ulum al-Din, Section: SECRETS OF MARRIAGE")

IMPORTANT: Always use **Bold Header** format for sub-headers (e.g., **Divine Will and Human Diversity**). NEVER use *single asterisks* anywhere.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL REMINDERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **ENFORCE VERSE LIMITS** - MAXIMUM {VERSE_LIMIT} verses. Select only the MOST relevant ones.
2. **CONSISTENT FORMAT** - ALL personas use short paragraphs with **bolded sub-headers**. NO bullets, NO emojis.
3. **You are an EDITOR, not an author** - Polish what's there, don't create new interpretations
4. **PRESERVE ACCURACY** - Never change meanings, attributions, or theological positions
5. **ENHANCE CLARITY** - Fix grammar, improve structure, make readable
6. **CITE ACCURATELY** - Keep all scholar names exactly as provided (Ibn Kathir, al-Qurtubi)
7. **VERSES FROM BACKEND** - Don't try to provide translations, they're already in verse_data
8. **BE HELPFUL** - Make the response answer the user's query directly and clearly
9. **NEVER FABRICATE** - If insufficient source material, acknowledge limitations
10. **FOLLOW CONTENT GUIDELINES** - {'Include hadith' if persona['include_hadith'] else 'Avoid hadith'}, {'include scholarly debates' if persona['scholarly_debates'] else 'avoid scholarly disagreements'}
11. **MATCH LEARNING GOAL** - {goal_instruction}
12. **NO SINGLE ASTERISKS** - NEVER use *italic* formatting. Only use **bold** for headers.
13. **NATURAL CITATIONS** - Say "Imam al-Ghazali explains..." not "Ihya Ulum al-Din, Section: X"
14. **LESSONS TRILOGY** - Each response MUST have exactly 3 lessons: one synthesis, one contemplation, one progression
15. **RICH SUMMARY** - Summary is a scholarly synthesis (4-6 sentences), NOT a 2-sentence blurb
16. **REFLECTION PROMPT** - The reflection_prompt MUST be specific to this verse's content. Reference the verse's themes/imagery directly. NEVER generic.

Current persona: **{persona_name}** ({knowledge_level} level)
Apply formatting: Short paragraphs with **bolded sub-headers**. NO bullets. NO emojis. NO single asterisks. Vocabulary adapted to {persona_name} level.

Begin your persona-adapted, clarity-enhanced response now.
"""

    return prompt

# ============================================================================
# END OF UPDATED PROMPT FUNCTION
# ============================================================================

def get_user_profile(user_id):
    """Get user profile from (default) database"""
    try:
        if not user_id:
            return {}
        user_doc = users_db.collection("users").document(user_id).get()
        return user_doc.to_dict() if user_doc.exists else {}
    except Exception as e:
        print(f"WARNING: Could not get user profile: {e}")
        return {}

def format_for_export(response_data, format_type='markdown'):
    """Format response data for export"""
    if format_type == 'json':
        return json.dumps(response_data, indent=2, ensure_ascii=False)

    # Markdown format
    content = "# Tafsir Response\n\n"

    # Verses
    if response_data.get('verses'):
        content += "## Relevant Verses\n\n"
        for verse in response_data['verses']:
            # Handle both old (surah) and new (surah_number) field names
            surah = verse.get('surah_number') or verse.get('surah')
            verse_num = verse.get('verse_number')
            arabic = verse.get('arabic') or verse.get('arabic_text')
            english = verse.get('english') or verse.get('text_saheeh_international')

            if arabic and arabic != 'Not available':
                content += f"**Surah {surah}, Verse {verse_num}**\n\n"
                content += f"{arabic}\n\n"
                content += f"*{english}*\n\n"
            else:
                content += f"**Surah {surah}, Verse {verse_num}**\n\n"
                content += f"*{english}*\n\n"

    # Tafsir explanations
    if response_data.get('tafsir_explanations'):
        content += "## Tafsir Explanations\n\n"
        for tafsir in response_data['tafsir_explanations']:
            content += f"### {tafsir['source']}\n\n"
            content += f"{tafsir['explanation']}\n\n"

    # Cross-references
    if response_data.get('cross_references'):
        content += "## Related Verses\n\n"
        for ref in response_data['cross_references']:
            content += f"- **{ref['verse']}**: {ref['relevance']}\n"
        content += "\n"

    # Lessons
    if response_data.get('lessons_practical_applications'):
        content += "## Lessons & Practical Applications\n\n"
        for lesson in response_data['lessons_practical_applications']:
            content += f"- {lesson['point']}\n"
        content += "\n"

    # Summary
    if response_data.get('summary'):
        content += "## Summary\n\n"
        content += f"{response_data['summary']}\n\n"

    content += "---\n*Generated by Tadabbur*"
    return content

# ============================================================================
# API ROUTES
# ============================================================================

@app.route("/suggestions", methods=["GET"])
@firebase_auth_optional
def get_suggestions():
    """Get persona-specific randomized query suggestions"""
    import random

    # Get user's persona (default to practicing_muslim if not set)
    try:
        user_id = getattr(request, 'user', {}).get('uid', None)
        if user_id:
            user_profile = get_user_profile(user_id)
            persona = user_profile.get('persona', 'practicing_muslim') if user_profile else 'practicing_muslim'
        else:
            persona = 'practicing_muslim'
    except Exception:
        persona = 'practicing_muslim'

    # Get persona-specific suggestions
    persona_bank = PERSONA_SUGGESTIONS.get(persona, DEFAULT_SUGGESTIONS)

    # Get current approach from query parameter (if provided by frontend)
    current_approach = request.args.get('approach', 'explore').lower()

    # Normalize approach (historical/thematic/semantic -> explore)
    if current_approach in ['historical', 'thematic', 'semantic']:
        current_approach = 'explore'  # Use user-friendly name
    elif current_approach not in ['tafsir', 'explore']:
        current_approach = 'explore'  # Default to explore

    # Select suggestions from persona-specific bank
    # More tafsir suggestions (8) since they're shorter, fewer explore (6) since they're detailed
    tafsir_suggestions = random.sample(
        persona_bank["tafsir"],
        min(8, len(persona_bank["tafsir"]))
    )
    explore_suggestions = random.sample(
        persona_bank["explore"],
        min(6, len(persona_bank["explore"]))
    )

    # Create suggestion objects with user-friendly approach labels
    all_suggestions = (
        [{"query": s, "approach": "tafsir", "type": "verse"} for s in tafsir_suggestions] +
        [{"query": s, "approach": "explore", "type": "concept"} for s in explore_suggestions]
    )
    random.shuffle(all_suggestions)

    return jsonify({
        "suggestions": all_suggestions,
        "persona": persona,
        "total_bank_size": len(persona_bank["tafsir"]) + len(persona_bank["explore"]),
        "current_approach": current_approach
    }), 200

@app.route("/analytics", methods=["GET"])
@firebase_auth_required
def get_analytics():
    """Get usage analytics (admin only)"""
    try:
        user_email = request.user.get('email', '')
        admin_domain = os.environ.get('ADMIN_DOMAIN', '')
        if not admin_domain or not user_email.endswith(f'@{admin_domain}'):
            return jsonify({"error": "Unauthorized"}), 403

        return jsonify({
            "total_queries": sum(ANALYTICS.values()),
            "popular_queries": dict(sorted(ANALYTICS.items(), key=lambda x: x[1], reverse=True)[:10]),
            "active_users": len(USER_RATE_LIMITS),
            "cache_hit_rate": len(RESPONSE_CACHE) / max(sum(ANALYTICS.values()), 1)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# TAFSIR CACHING SYSTEM - Dedicated Endpoints
# ============================================================================

@app.route("/cache/lookup", methods=["POST"])
def cache_lookup():
    """
    Check if a tafsir query is cached.
    Returns cached response if available.
    """
    try:
        data = request.json
        query = data.get('query', '').strip()
        user_profile = data.get('user_profile', {})
        approach = data.get('approach', 'tafsir')

        if not query:
            return jsonify({'cached': False, 'error': 'Query required'}), 400

        # Normalize the query for better matching
        normalized_query = normalize_verse_query(query)

        # Check Firestore cache
        cached_response = get_cached_tafsir_response(query, user_profile, approach)

        if cached_response:
            return jsonify({
                'cached': True,
                'response': cached_response,
                'cache_info': {
                    'normalized_query': normalized_query,
                    'source': 'firestore',
                    'persona': user_profile.get('persona', 'unknown')
                }
            }), 200
        else:
            return jsonify({
                'cached': False,
                'normalized_query': normalized_query,
                'message': 'No cache found'
            }), 200

    except Exception as e:
        print(f"❌ Cache lookup error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/cache/store", methods=["POST"])
def cache_store():
    """
    Store a tafsir response in cache.
    Called after AI generation for future reuse.
    """
    try:
        data = request.json
        query = data.get('query', '').strip()
        user_profile = data.get('user_profile', {})
        response = data.get('response', {})
        approach = data.get('approach', 'tafsir')

        if not query or not response:
            return jsonify({'error': 'Query and response required'}), 400

        # Store in Firestore cache
        store_tafsir_cache(query, user_profile, response, approach)

        return jsonify({
            'success': True,
            'message': 'Response cached successfully',
            'normalized_query': normalize_verse_query(query)
        }), 200

    except Exception as e:
        print(f"❌ Cache store error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/cache/analytics", methods=["GET"])
def cache_analytics():
    """
    Get comprehensive cache analytics and statistics.
    """
    try:
        analytics = get_cache_analytics()

        return jsonify({
            'success': True,
            'analytics': analytics,
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        print(f"❌ Cache analytics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/cache/popular", methods=["GET"])
def get_popular_queries():
    """
    Get most popular queries for cache pre-warming.
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        persona = request.args.get('persona', None)

        query = quran_db.collection('popular_queries').order_by('count', direction=firestore.Query.DESCENDING)

        if persona:
            query = query.where('persona', '==', persona)

        query = query.limit(limit)

        popular = []
        for doc in query.stream():
            data = doc.to_dict()
            popular.append({
                'query': data.get('query'),
                'count': data.get('count'),
                'persona': data.get('persona'),
                'last_queried': data.get('last_queried').isoformat() if data.get('last_queried') else None
            })

        return jsonify({
            'success': True,
            'popular_queries': popular,
            'total': len(popular)
        }), 200

    except Exception as e:
        print(f"❌ Popular queries error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/cache/prewarm", methods=["POST"])
def prewarm_cache():
    """
    Pre-generate cache for popular or specified queries.
    This can be called by a scheduled job or manually.
    """
    try:
        data = request.json
        queries = data.get('queries', [])
        personas = data.get('personas', ['practicing_muslim', 'advanced_learner', 'new_revert'])

        if not queries:
            # Get top popular queries if none specified
            pop_docs = quran_db.collection('popular_queries').order_by('count', direction=firestore.Query.DESCENDING).limit(10).stream()
            queries = [doc.to_dict().get('query') for doc in pop_docs]

        results = []
        for query in queries:
            for persona in personas:
                # Check if already cached
                profile = {
                    'persona': persona,
                    'knowledge_level': 'intermediate',
                    'learning_goal': 'balanced'
                }

                cached = get_cached_tafsir_response(query, profile, 'tafsir')
                if cached:
                    results.append({
                        'query': query,
                        'persona': persona,
                        'status': 'already_cached'
                    })
                else:
                    results.append({
                        'query': query,
                        'persona': persona,
                        'status': 'queued_for_generation'
                    })
                    # TODO: Queue for background generation

        return jsonify({
            'success': True,
            'results': results,
            'message': f'Pre-warming {len(results)} query-persona combinations'
        }), 200

    except Exception as e:
        print(f"❌ Cache pre-warm error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/cache/invalidate", methods=["POST"])
def invalidate_cache():
    """
    Invalidate cache entries based on criteria.
    Useful when tafsir database is updated.
    """
    try:
        data = request.json
        invalidate_type = data.get('type', 'all')  # all, query, persona, age

        if invalidate_type == 'query':
            query = data.get('query')
            if not query:
                return jsonify({'error': 'Query required for query-based invalidation'}), 400

            normalized = normalize_verse_query(query)
            # Delete all cache entries for this query
            cache_docs = quran_db.collection('tafsir_cache').where('query_normalized', '==', normalized).stream()
            count = 0
            for doc in cache_docs:
                doc.reference.delete()
                count += 1

            return jsonify({
                'success': True,
                'message': f'Invalidated {count} cache entries for query: {normalized}'
            }), 200

        elif invalidate_type == 'age':
            # Invalidate entries older than X hours
            max_age_hours = data.get('max_age_hours', 24)
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            cache_docs = quran_db.collection('tafsir_cache').where('created_at', '<', cutoff_time).stream()
            count = 0
            for doc in cache_docs:
                doc.reference.delete()
                count += 1

            return jsonify({
                'success': True,
                'message': f'Invalidated {count} cache entries older than {max_age_hours} hours'
            }), 200

        elif invalidate_type == 'all':
            # Clear entire cache (use with caution!)
            if not data.get('confirm', False):
                return jsonify({'error': 'Confirmation required to clear all cache'}), 400

            # Clear Firestore cache
            cache_docs = quran_db.collection('tafsir_cache').stream()
            firestore_count = 0
            for doc in cache_docs:
                doc.reference.delete()
                firestore_count += 1

            # Clear in-memory cache
            with cache_lock:
                memory_count = len(RESPONSE_CACHE)
                RESPONSE_CACHE.clear()

            return jsonify({
                'success': True,
                'message': f'Cleared entire cache (Firestore: {firestore_count}, Memory: {memory_count} entries)'
            }), 200

        else:
            return jsonify({'error': f'Unknown invalidation type: {invalidate_type}'}), 400

    except Exception as e:
        print(f"❌ Cache invalidation error: {e}")
        return jsonify({'error': str(e)}), 500

# Cache utility functions (to be added before the endpoints)
def normalize_verse_query(query: str) -> str:
    """
    Normalize verse queries for better cache matching.
    Examples:
    - "2:3" -> "2:3"
    - "surah 2 verse 3" -> "2:3"
    - "Al-Baqarah 3" -> "2:3"
    - "2:3-5" -> "2:3-5"
    """
    query_lower = query.lower().strip()

    # Extract verse reference if present
    verse_ref = extract_verse_reference_enhanced(query)
    if verse_ref:
        surah, start_verse = verse_ref
        # Check if it's a range
        range_match = re.search(r'(\d+)[:\s]+(\d+)\s*[-–]\s*(\d+)', query)
        if range_match:
            return f"{surah}:{start_verse}-{range_match.group(3)}"
        return f"{surah}:{start_verse}"

    return query_lower

def get_firestore_cache_key(query: str, user_profile: dict, approach: str = "tafsir") -> dict:
    """
    Generate a structured cache key for Firestore storage.
    Returns dict with normalized components for better querying.
    """
    normalized_query = normalize_verse_query(query)

    # Extract key profile attributes that affect response
    profile_key = {
        'persona': user_profile.get('persona', 'practicing_muslim'),
        'knowledge_level': user_profile.get('knowledge_level', 'intermediate'),
        'learning_goal': user_profile.get('learning_goal', 'balanced'),
        'include_arabic': user_profile.get('include_arabic', True),
    }

    return {
        'query_normalized': normalized_query,
        'query_original': query,
        'approach': approach,
        'profile_hash': hashlib.md5(json.dumps(profile_key, sort_keys=True).encode()).hexdigest(),
        'profile_details': profile_key,
        'cache_key': hashlib.md5(f"{normalized_query}_{approach}_{json.dumps(profile_key, sort_keys=True)}".encode()).hexdigest()
    }

def get_cached_tafsir_response(query: str, user_profile: dict, approach: str = "tafsir") -> Optional[dict]:
    """
    Retrieve cached tafsir response from Firestore.
    Returns cached response or None if not found/expired.
    """
    try:
        cache_info = get_firestore_cache_key(query, user_profile, approach)
        cache_key = cache_info['cache_key']

        # Debug logging for cache key
        print(f"🔍 Looking for cache with key: {cache_key[:16]}...")
        print(f"   Query: {cache_info['query_normalized']}")
        print(f"   Profile: persona={cache_info['profile_details'].get('persona')}, level={cache_info['profile_details'].get('knowledge_level')}")

        # Try Firestore first
        cache_ref = quran_db.collection('tafsir_cache').document(cache_key)
        cache_doc = cache_ref.get()

        if cache_doc.exists:
            cache_data = cache_doc.to_dict()

            # Check pipeline version — reject old cache entries from before two-stage scholarly pipeline
            cached_version = cache_data.get('version', '1.0')
            if cached_version != SCHOLARLY_PIPELINE_VERSION:
                print(f"💾 Cache STALE (version {cached_version} != {SCHOLARLY_PIPELINE_VERSION}) for key {cache_key[:8]}... — regenerating")
                return None

            # Increment hit count
            cache_ref.update({
                'hit_count': firestore.Increment(1),
                'last_accessed': datetime.now(timezone.utc)
            })

            print(f"💾 Firestore cache HIT for query: {cache_info['query_normalized']}")
            print(f"   Profile: {cache_info['profile_details']}")
            print(f"   Hit count: {cache_data.get('hit_count', 0) + 1}")

            # Decompress response if compressed
            response_data = cache_data.get('response')
            if cache_data.get('compressed', False) and response_data:
                import gzip
                import base64
                response_data = json.loads(gzip.decompress(base64.b64decode(response_data)))

            return response_data

        # If no cache found with user profile, try with default profile as fallback
        if user_profile and any(user_profile.values()):
            print(f"💾 No cache found with user profile, trying default profile fallback...")
            default_profile = {
                'persona': 'practicing_muslim',
                'knowledge_level': 'intermediate',
                'learning_goal': 'balanced',
                'include_arabic': True
            }
            default_cache_info = get_firestore_cache_key(query, default_profile, approach)
            default_cache_key = default_cache_info['cache_key']

            if default_cache_key != cache_key:  # Only try if different
                print(f"🔍 Looking for default cache with key: {default_cache_key[:16]}...")
                default_cache_ref = quran_db.collection('tafsir_cache').document(default_cache_key)
                default_cache_doc = default_cache_ref.get()

                if default_cache_doc.exists:
                    cache_data = default_cache_doc.to_dict()

                    # Check pipeline version
                    cached_version = cache_data.get('version', '1.0')
                    if cached_version != SCHOLARLY_PIPELINE_VERSION:
                        return None

                    print(f"💾 Using DEFAULT cached response")

                    # Decompress if needed
                    response_data = cache_data.get('response')
                    if cache_data.get('compressed', False) and response_data:
                        import gzip
                        import base64
                        response_data = json.loads(gzip.decompress(base64.b64decode(response_data)))

                    return response_data

    except Exception as e:
        import traceback
        print(f"⚠️ Cache retrieval error: {e}")
        print(f"Traceback: {traceback.format_exc()}")

    return None

def store_tafsir_cache(query: str, user_profile: dict, response: dict, approach: str = "tafsir"):
    """
    Store tafsir response in Firestore cache with compression and metadata.
    """
    try:
        cache_info = get_firestore_cache_key(query, user_profile, approach)
        cache_key = cache_info['cache_key']

        # Compress large responses
        response_str = json.dumps(response)
        compressed = False
        stored_response = response

        if len(response_str) > 10000:  # Compress if > 10KB
            import gzip
            import base64
            compressed_data = gzip.compress(response_str.encode())
            stored_response = base64.b64encode(compressed_data).decode()
            compressed = True
            print(f"   Compressed response: {len(response_str)} -> {len(stored_response)} bytes")

        # Store in Firestore with metadata
        cache_doc = {
            'cache_key': cache_key,
            'query_normalized': cache_info['query_normalized'],
            'query_original': query,
            'approach': approach,
            'profile': cache_info['profile_details'],
            'response': stored_response,
            'compressed': compressed,
            'created_at': datetime.now(timezone.utc),
            'last_accessed': datetime.now(timezone.utc),
            'hit_count': 0,
            'response_size': len(response_str),
            'version': SCHOLARLY_PIPELINE_VERSION,  # Auto-invalidates old cache on pipeline upgrades
            'tokens_saved': count_tokens_approximate(response.get('response', ''))
        }

        # Extract verse info for analytics
        verse_ref = extract_verse_reference_enhanced(query)
        if verse_ref:
            cache_doc['surah'] = verse_ref[0]
            cache_doc['verse'] = verse_ref[1]

        quran_db.collection('tafsir_cache').document(cache_key).set(cache_doc)

        print(f"💾 STORING cache for: {cache_info['query_normalized']}")
        print(f"   Cache key: {cache_key[:16]}...")
        print(f"   Profile: persona={cache_info['profile_details'].get('persona')}, level={cache_info['profile_details'].get('knowledge_level')}")
        print(f"   Approach: {approach}")
        print(f"   Size: {len(response_str)} bytes (compressed: {compressed})")

        # Track popular queries for pre-warming
        track_popular_query(cache_info['query_normalized'], cache_info['profile_details'])

    except Exception as e:
        print(f"⚠️ Cache storage error: {e}")

def track_popular_query(normalized_query: str, profile: dict):
    """
    Track popular queries for cache pre-warming.
    """
    try:
        # Create a popularity key combining query and persona
        popularity_key = f"{normalized_query}_{profile.get('persona', 'default')}"

        pop_ref = quran_db.collection('popular_queries').document(popularity_key)
        pop_doc = pop_ref.get()

        if pop_doc.exists:
            pop_ref.update({
                'count': firestore.Increment(1),
                'last_queried': datetime.now()
            })
        else:
            pop_ref.set({
                'query': normalized_query,
                'persona': profile.get('persona'),
                'count': 1,
                'created_at': datetime.now(),
                'last_queried': datetime.now()
            })
    except Exception as e:
        print(f"⚠️ Popular query tracking error: {e}")

def get_cache_analytics() -> dict:
    """
    Get comprehensive cache analytics.
    """
    try:
        # Get cache stats from Firestore
        cache_collection = quran_db.collection('tafsir_cache')

        # Total cached responses
        total_cached = len(cache_collection.limit(10000).get())

        # Get hit counts and sizes
        total_hits = 0
        total_size = 0
        total_tokens_saved = 0
        cache_by_persona = defaultdict(int)

        for doc in cache_collection.limit(500).stream():
            data = doc.to_dict()
            total_hits += data.get('hit_count', 0)
            total_size += data.get('response_size', 0)
            total_tokens_saved += data.get('tokens_saved', 0) * data.get('hit_count', 0)
            persona = data.get('profile', {}).get('persona', 'unknown')
            cache_by_persona[persona] += 1

        # Get popular queries
        popular_queries = []
        pop_collection = quran_db.collection('popular_queries').order_by('count', direction=firestore.Query.DESCENDING).limit(10)
        for doc in pop_collection.stream():
            data = doc.to_dict()
            popular_queries.append({
                'query': data.get('query'),
                'count': data.get('count'),
                'persona': data.get('persona')
            })

        # Calculate cost savings (rough estimate)
        # Gemini pricing: ~$0.00025 per 1K input tokens, ~$0.001 per 1K output tokens
        estimated_cost_saved = (total_tokens_saved / 1000) * 0.001

        return {
            'total_cached_responses': total_cached,
            'total_cache_hits': total_hits,
            'total_cache_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_by_persona': dict(cache_by_persona),
            'popular_queries': popular_queries,
            'total_tokens_saved': total_tokens_saved,
            'estimated_cost_saved': f"${estimated_cost_saved:.2f}",
            'average_hit_rate': round(total_hits / max(total_cached, 1), 2)
        }

    except Exception as e:
        print(f"⚠️ Cache analytics error: {e}")
        return {}

@app.route("/export/<format_type>", methods=["POST"])
@firebase_auth_required
def export_response(format_type):
    """Export response in specified format"""
    try:
        if format_type not in ['markdown', 'json']:
            return jsonify({"error": "Invalid format. Use 'markdown' or 'json'"}), 400

        data = request.get_json()
        response_data = data.get('response_data')

        if not response_data:
            return jsonify({"error": "No response data provided"}), 400

        content = format_for_export(response_data, format_type)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tafsir_response_{timestamp}.{format_type if format_type != 'markdown' else 'md'}"

        return jsonify({
            "content": content,
            "filename": filename,
            "format": format_type
        }), 200

    except Exception as e:
        print(f"ERROR in export: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/get_profile", methods=["GET"])
@firebase_auth_required
def get_profile():
    """Get user's learning profile"""
    uid = request.user["uid"]
    try:
        user_doc = users_db.collection("users").document(uid).get()
        if user_doc.exists:
            return jsonify(user_doc.to_dict()), 200
        return jsonify({"profile": None, "is_new_user": True}), 200
    except Exception as e:
        print(f"ERROR in /get_profile: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# UPDATED: /set_profile ENDPOINT WITH SMART LOGIC (Suggestions 2 & 3)
# ============================================================================

@app.route("/set_profile", methods=["POST"])
@firebase_auth_required
def set_profile():
    """
    Set or update user's learning profile with smart knowledge_level handling.
    
    NEW LOGIC:
    - Deterministic personas (advanced_learner, student, new_revert) auto-set knowledge_level
    - Variable personas require knowledge_level from client
    - learning_goal is required for all personas
    """
    uid = request.user["uid"]
    data = request.get_json()

    # Support both old and new profile systems
    level = data.get("level")  # OLD SYSTEM
    focus = data.get("focus", "practical")  # OLD SYSTEM
    verbosity = data.get("verbosity", "medium")  # OLD SYSTEM
    
    # NEW SYSTEM
    persona = data.get("persona")
    provided_knowledge_level = data.get("knowledge_level")
    learning_goal = data.get("learning_goal")
    first_name = data.get("first_name")

    try:
        profile_data = {}

        # OLD SYSTEM (backwards compatibility)
        if level:
            if level not in ["casual", "beginner", "intermediate", "advanced"]:
                return jsonify({"error": "Invalid level"}), 400
            if focus not in ["practical", "linguistic", "comparative", "thematic"]:
                return jsonify({"error": "Invalid focus"}), 400
            if verbosity not in ["short", "medium", "detailed"]:
                return jsonify({"error": "Invalid verbosity"}), 400
            
            profile_data["level"] = level
            profile_data["focus"] = focus
            profile_data["verbosity"] = verbosity

        # NEW SYSTEM (persona-based)
        if persona:
            # Validate persona
            if persona not in PERSONAS:
                return jsonify({
                    "error": "Invalid persona",
                    "available_personas": list(PERSONAS.keys()),
                    "description": "Choose from: new_revert, curious_explorer, practicing_muslim, student, advanced_learner"
                }), 400
            
            # Validate learning_goal
            if not learning_goal:
                return jsonify({
                    "error": "learning_goal is required",
                    "valid_options": ["application", "understanding", "balanced"],
                    "descriptions": {
                        "application": "Focus on practical everyday use and actionable insights",
                        "understanding": "Focus on deep scholarly comprehension and theological depth",
                        "balanced": "Mix of both practical and scholarly approaches"
                    }
                }), 400
            
            if learning_goal not in ["application", "understanding", "balanced"]:
                return jsonify({
                    "error": "Invalid learning_goal",
                    "valid_options": ["application", "understanding", "balanced"],
                    "descriptions": {
                        "application": "Focus on practical everyday use and actionable insights",
                        "understanding": "Focus on deep scholarly comprehension and theological depth",
                        "balanced": "Mix of both practical and scholarly approaches"
                    }
                }), 400
            
            # Smart knowledge_level determination using helper function
            knowledge_level, is_deterministic = determine_knowledge_level(persona, provided_knowledge_level)
            
            if knowledge_level is None:
                # Variable persona without valid knowledge_level
                return jsonify({
                    "error": "knowledge_level is required for this persona",
                    "persona": persona,
                    "valid_options": ["beginner", "intermediate", "advanced"],
                    "descriptions": {
                        "beginner": "New to Islamic studies, need foundational explanations",
                        "intermediate": "Have basic Islamic knowledge, want deeper understanding",
                        "advanced": "Strong Islamic background, ready for scholarly depth"
                    },
                    "note": f"The persona '{persona}' allows flexible knowledge levels. Please specify your level."
                }), 400
            
            # All validations passed - save profile
            profile_data["persona"] = persona
            profile_data["knowledge_level"] = knowledge_level
            profile_data["learning_goal"] = learning_goal
            
            # Log whether level was auto-set or user-provided
            if is_deterministic:
                print(f"INFO: Auto-set knowledge_level='{knowledge_level}' for persona='{persona}'")
            else:
                print(f"INFO: User-provided knowledge_level='{knowledge_level}' for persona='{persona}'")

        # Store first_name if provided
        if first_name and isinstance(first_name, str):
            cleaned = first_name.strip()[:30]
            if cleaned:
                profile_data["first_name"] = cleaned

        # Save to Firestore
        users_db.collection("users").document(uid).set(profile_data, merge=True)
        
        response_data = {
            "status": "success",
            "uid": uid,
            "profile": profile_data
        }
        
        # Add helpful message if knowledge_level was auto-set
        if persona and is_deterministic:
            response_data["note"] = f"Knowledge level automatically set to '{knowledge_level}' based on persona '{persona}'"
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"ERROR in /set_profile: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

# NEW: Persona endpoints
@app.route("/personas", methods=["GET"])
def list_personas():
    """List available user personas with detailed information"""
    persona_info = {}

    for name, config in PERSONAS.items():
        # Determine if this persona has deterministic knowledge_level
        deterministic_level = None
        if name in ["advanced_learner", "student"]:
            deterministic_level = "advanced"
        elif name == "new_revert":
            deterministic_level = "beginner"
        
        persona_info[name] = {
            'name': config['name'],
            'description': f"{config['tone']} | Format: {config['format_style']}",
            'tone': config['tone'],
            'vocabulary': config['vocabulary'],
            'format_style': config['format_style'],
            'include_hadith': config['include_hadith'],
            'scholarly_debates': config['scholarly_debates'],
            'knowledge_level': deterministic_level if deterministic_level else "variable (user chooses)",
            'requires_knowledge_level_input': deterministic_level is None
        }

    return jsonify({
        'personas': persona_info,
        'count': len(persona_info),
        'knowledge_levels': {
            'beginner': 'New to Islamic studies, need foundational explanations',
            'intermediate': 'Have basic Islamic knowledge, want deeper understanding',
            'advanced': 'Strong Islamic background, ready for scholarly depth'
        },
        'learning_goals': {
            'application': 'Focus on practical everyday use and actionable insights',
            'understanding': 'Focus on deep scholarly comprehension and theological depth',
            'balanced': 'Mix of both practical and scholarly approaches'
        }
    }), 200

# ============================================================================
# DAILY VERSE ENDPOINT
# ============================================================================

# Curated list of impactful, universally resonant verses for daily rotation
# Format: (surah_number, verse_number, brief_theme)
DAILY_VERSE_POOL = [
    (1, 1, "The Opening"),
    (2, 152, "Remember Allah"),
    (2, 155, "Patience through trials"),
    (2, 186, "Allah is near"),
    (2, 197, "Best provision is taqwa"),
    (2, 216, "Hidden good in hardship"),
    (2, 255, "Ayat al-Kursi"),
    (2, 261, "Charity multiplied"),
    (2, 286, "Allah does not burden"),
    (3, 26, "Sovereignty belongs to Allah"),
    (3, 139, "Do not grieve"),
    (3, 159, "Mercy and consultation"),
    (3, 185, "Every soul shall taste death"),
    (3, 200, "Patience and perseverance"),
    (4, 36, "Worship Allah and be kind"),
    (5, 8, "Stand firm for justice"),
    (6, 59, "Keys of the unseen"),
    (6, 162, "Prayer and sacrifice for Allah"),
    (7, 56, "Mercy of Allah is near"),
    (7, 199, "Forgiveness and kindness"),
    (8, 2, "Hearts tremble at Allah's mention"),
    (9, 51, "Nothing befalls except what Allah decrees"),
    (10, 62, "Friends of Allah have no fear"),
    (11, 6, "Every creature's provision is from Allah"),
    (12, 86, "Complaining only to Allah"),
    (13, 11, "Change begins within"),
    (13, 28, "Hearts find rest in remembrance"),
    (14, 7, "Gratitude increases blessings"),
    (16, 90, "Justice, kindness, and generosity"),
    (16, 97, "Good life through faith"),
    (17, 23, "Honor your parents"),
    (17, 80, "Prayer for true entrance"),
    (18, 10, "Youth of the cave"),
    (18, 46, "Good deeds are lasting"),
    (20, 114, "Increase me in knowledge"),
    (21, 87, "Dua of Yunus"),
    (23, 1, "Success of the believers"),
    (24, 35, "Light upon light"),
    (25, 63, "Servants of the Most Merciful"),
    (29, 69, "Striving in Allah's way"),
    (31, 17, "Patience in adversity"),
    (33, 21, "Prophet as best example"),
    (33, 41, "Remember Allah abundantly"),
    (35, 5, "Life of this world is delusion"),
    (36, 58, "Peace — a word from the Lord"),
    (39, 10, "Reward for those who do good"),
    (39, 53, "Despair not of Allah's mercy"),
    (40, 60, "Call upon Me, I will respond"),
    (41, 34, "Repel evil with good"),
    (42, 30, "Afflictions from your own deeds"),
    (49, 10, "Believers are brothers"),
    (49, 13, "Most noble is most righteous"),
    (50, 16, "Closer than the jugular vein"),
    (51, 56, "Created to worship"),
    (55, 13, "Which blessings will you deny"),
    (57, 4, "Allah is with you wherever you are"),
    (59, 22, "Beautiful names of Allah"),
    (64, 16, "Fear Allah as much as you can"),
    (65, 3, "Allah provides from unexpected sources"),
    (67, 2, "Created life as a test"),
    (73, 8, "Devote yourself to Allah"),
    (87, 14, "Successful is the one who purifies"),
    (89, 27, "O tranquil soul"),
    (93, 5, "Your Lord will give you"),
    (94, 5, "With hardship comes ease"),
    (103, 1, "Time and loss"),
    (112, 1, "Say: He is Allah, the One"),
]


@app.route("/range-limit", methods=["GET"])
def get_range_limit():
    """
    Dropdown guardrail: return the precomputed maximum end verse for a given
    surah + start verse.  Uses actual tafsir chunk sizes measured at startup —
    no heuristics, no per-request computation.

    Query params:
        surah (int): Surah number (1-114)
        start (int): Starting verse number

    Returns:
        {"maxEnd": int, "surahMax": int}
    """
    from services.token_budget_service import compute_max_end_verse
    from config.token_budget import ABSOLUTE_MAX_VERSES

    try:
        surah = request.args.get("surah", type=int)
        start = request.args.get("start", type=int)

        if not surah or not start:
            return jsonify({"error": "Missing required params: surah, start"}), 400

        if surah not in QURAN_METADATA:
            return jsonify({"error": f"Invalid surah: {surah}"}), 400

        surah_max = QURAN_METADATA[surah]["verses"]

        if start < 1 or start > surah_max:
            return jsonify({"error": f"Invalid start verse: {start}"}), 400

        # Precomputed lookup — O(1) dict access
        max_end, _ = compute_max_end_verse(surah, start, surah_max)

        # Hard cap as safety net (should already be enforced by precomputation)
        hard_max = min(start + ABSOLUTE_MAX_VERSES - 1, surah_max)
        effective_max = min(max_end, hard_max)

        return jsonify({"maxEnd": effective_max, "surahMax": surah_max}), 200

    except Exception as e:
        print(f"[RANGE-LIMIT] Error: {e}")
        # Graceful fallback: return the existing hard limit
        try:
            s_max = QURAN_METADATA.get(surah, {}).get("verses", 0) if surah else 0
            fallback = min(start + 4, s_max) if surah and start and s_max else 5
        except Exception:
            s_max = 0
            fallback = 5
        return jsonify({"maxEnd": fallback, "surahMax": s_max}), 200


@app.route("/daily-verse", methods=["GET"])
def get_daily_verse():
    """Return a verse of the day — deterministic, same for all users on a given date."""
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # Deterministic index: hash the date, mod by pool size
        idx = int(hashlib.md5(today.encode()).hexdigest(), 16) % len(DAILY_VERSE_POOL)
        surah, verse_num, theme = DAILY_VERSE_POOL[idx]

        surah_meta = QURAN_METADATA.get(surah, {})
        surah_name = surah_meta.get("name", f"Surah {surah}")

        # Fetch verse text from Firestore
        verse_data = get_verse_from_firestore(surah, verse_num)
        arabic_text = verse_data.get("arabic", "") if verse_data else ""
        english_text = verse_data.get("english", "") if verse_data else ""

        return jsonify({
            "surah": surah,
            "verse": verse_num,
            "surah_name": surah_name,
            "theme": theme,
            "arabic_text": arabic_text,
            "english_text": english_text,
            "date": today
        }), 200

    except Exception as e:
        print(f"ERROR in /daily-verse: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# STREAK PERSISTENCE ENDPOINTS
# ============================================================================

@app.route("/streak", methods=["GET"])
@firebase_auth_required
def get_streak():
    """Get user's streak data from Firestore."""
    uid = request.user["uid"]
    try:
        user_doc = users_db.collection("users").document(uid).get()
        if user_doc.exists:
            data = user_doc.to_dict()
            return jsonify({
                "current_streak": data.get("streak_current", 0),
                "longest_streak": data.get("streak_longest", 0),
                "last_activity_date": data.get("streak_last_date", None),
            }), 200
        return jsonify({
            "current_streak": 0,
            "longest_streak": 0,
            "last_activity_date": None,
        }), 200
    except Exception as e:
        print(f"ERROR in GET /streak: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/streak", methods=["POST"])
@firebase_auth_required
def update_streak():
    """Record activity and update streak. Called when user makes a reflection or searches a verse."""
    uid = request.user["uid"]
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

        user_ref = users_db.collection("users").document(uid)
        user_doc = user_ref.get()
        data = user_doc.to_dict() if user_doc.exists else {}

        last_date = data.get("streak_last_date", None)
        current = data.get("streak_current", 0)
        longest = data.get("streak_longest", 0)

        if last_date == today:
            # Already recorded today — no change
            return jsonify({
                "current_streak": current,
                "longest_streak": longest,
                "last_activity_date": today,
                "changed": False,
            }), 200

        if last_date == yesterday:
            # Consecutive day — extend streak
            current += 1
        else:
            # Streak broken or first activity — start fresh
            current = 1

        longest = max(longest, current)

        user_ref.set({
            "streak_current": current,
            "streak_longest": longest,
            "streak_last_date": today,
        }, merge=True)

        # Check for newly earned badges after streak update
        newly_earned = []
        try:
            newly_earned = _check_and_award_badges(uid)
        except Exception as badge_err:
            print(f"[BADGES] Error checking badges after streak: {badge_err}")

        return jsonify({
            "current_streak": current,
            "longest_streak": longest,
            "last_activity_date": today,
            "changed": True,
            "newly_earned_badges": newly_earned,
        }), 200

    except Exception as e:
        print(f"ERROR in POST /streak: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# VERSE EXPLORATION TRACKING
# ============================================================================

def _track_explored_verse(uid, surah, start_verse, end_verse=None):
    """Track which verses a user has explored. Non-blocking, fire-and-forget."""
    try:
        if not uid:
            return
        end = end_verse or start_verse
        verses = list(range(start_verse, end + 1))
        surah_key = str(surah)

        user_ref = users_db.collection("users").document(uid)
        user_doc = user_ref.get()
        data = user_doc.to_dict() if user_doc.exists else {}

        explored = data.get("explored_verses", {})
        existing = set(explored.get(surah_key, []))
        new_verses = [v for v in verses if v not in existing]

        if not new_verses:
            return  # Already tracked

        updated_list = sorted(existing | set(new_verses))
        explored[surah_key] = updated_list

        # Count totals
        total = sum(len(v) for v in explored.values())
        total_surahs = len(explored)

        user_ref.set({
            "explored_verses": explored,
            "stats_cache": {
                "total_explored_verses": total,
                "total_explored_surahs": total_surahs,
            }
        }, merge=True)
    except Exception as e:
        print(f"WARNING: Failed to track explored verse: {e}")


@app.route("/progress", methods=["GET"])
@firebase_auth_required
def get_progress():
    """Get user's Quran exploration progress."""
    uid = request.user["uid"]
    try:
        user_doc = users_db.collection("users").document(uid).get()
        data = user_doc.to_dict() if user_doc.exists else {}
        explored = data.get("explored_verses", {})

        total_explored = sum(len(v) for v in explored.values())
        total_verses = sum(s["verses"] for s in QURAN_METADATA.values())

        surahs = []
        for num, meta in QURAN_METADATA.items():
            explored_list = explored.get(str(num), [])
            surahs.append({
                "number": num,
                "name": meta["name"],
                "total_verses": meta["verses"],
                "explored_count": len(explored_list),
                "explored_verses": explored_list,
            })

        return jsonify({
            "total_explored": total_explored,
            "total_verses": total_verses,
            "percentage": round(total_explored / total_verses * 100, 1) if total_verses else 0,
            "total_surahs_touched": len(explored),
            "surahs": surahs,
        }), 200
    except Exception as e:
        print(f"ERROR in GET /progress: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# THEMED VERSE COLLECTIONS
# ============================================================================

THEMED_COLLECTIONS = [
    {
        "id": "patience",
        "title": "Patience & Perseverance",
        "description": "How the Quran teaches steadfastness through trials and gratitude in ease",
        "category": "Spiritual Growth",
        "icon": "mountain",
        "scholarly_sources": ["ihya", "madarij", "riyad"],
        "verses": [
            (2, 155, "Tested through loss"),
            (2, 216, "Hidden good in hardship"),
            (2, 286, "Allah does not burden beyond capacity"),
            (3, 200, "Patience and perseverance"),
            (31, 17, "Patience in adversity"),
            (39, 10, "Reward for those who do good"),
            (94, 5, "With hardship comes ease"),
        ],
    },
    {
        "id": "trust",
        "title": "Trust in Allah",
        "description": "Surrender, reliance, and finding peace in divine decree",
        "category": "Spiritual Growth",
        "icon": "shield",
        "scholarly_sources": ["ihya", "madarij"],
        "verses": [
            (3, 159, "Mercy and consultation"),
            (9, 51, "Nothing befalls except what Allah decrees"),
            (11, 6, "Every creature's provision is from Allah"),
            (57, 4, "Allah is with you wherever you are"),
            (65, 3, "Allah provides from unexpected sources"),
            (64, 16, "Fear Allah as much as you can"),
        ],
    },
    {
        "id": "mercy",
        "title": "Mercy & Forgiveness",
        "description": "The boundless mercy of Allah and the path to forgiveness",
        "category": "Spiritual Growth",
        "icon": "heart",
        "scholarly_sources": ["ihya", "riyad"],
        "verses": [
            (7, 56, "Mercy of Allah is near"),
            (7, 199, "Forgiveness and kindness"),
            (39, 53, "Despair not of Allah's mercy"),
            (40, 60, "Call upon Me, I will respond"),
            (41, 34, "Repel evil with good"),
            (42, 30, "Afflictions from your own deeds"),
        ],
    },
    {
        "id": "gratitude",
        "title": "Gratitude & Blessings",
        "description": "Recognizing and giving thanks for Allah's countless favors",
        "category": "Faith & Worship",
        "icon": "sun",
        "scholarly_sources": ["ihya"],
        "verses": [
            (2, 152, "Remember Allah"),
            (14, 7, "Gratitude increases blessings"),
            (16, 97, "Good life through faith"),
            (55, 13, "Which blessings will you deny"),
            (93, 5, "Your Lord will give you"),
        ],
    },
    {
        "id": "knowledge",
        "title": "Knowledge & Learning",
        "description": "The sacred duty to seek knowledge and understanding",
        "category": "Character & Conduct",
        "icon": "book",
        "scholarly_sources": ["ihya", "riyad"],
        "verses": [
            (20, 114, "Increase me in knowledge"),
            (96, 1, "Read in the name of your Lord"),
            (2, 269, "Wisdom is immense good"),
            (58, 11, "Allah raises those with knowledge"),
        ],
    },
    {
        "id": "remembrance",
        "title": "The Heart & Remembrance",
        "description": "Finding tranquility through the remembrance of Allah",
        "category": "Faith & Worship",
        "icon": "sparkle",
        "scholarly_sources": ["ihya", "madarij"],
        "verses": [
            (2, 152, "Remember Me, I will remember you"),
            (8, 2, "Hearts tremble at Allah's mention"),
            (13, 28, "Hearts find rest in remembrance"),
            (33, 41, "Remember Allah abundantly"),
            (50, 16, "Closer than the jugular vein"),
            (73, 8, "Devote yourself to Allah"),
        ],
    },
    {
        "id": "family",
        "title": "Family & Community",
        "description": "Rights of parents, neighbors, and building a just society",
        "category": "Life Guidance",
        "icon": "users",
        "scholarly_sources": ["riyad"],
        "verses": [
            (4, 36, "Worship Allah and be kind"),
            (17, 23, "Honor your parents"),
            (49, 10, "Believers are brothers"),
            (49, 13, "Most noble is most righteous"),
        ],
    },
    {
        "id": "justice",
        "title": "Justice & Righteousness",
        "description": "Standing firm for truth, equity, and moral excellence",
        "category": "Character & Conduct",
        "icon": "scale",
        "scholarly_sources": ["riyad", "ihya"],
        "verses": [
            (5, 8, "Stand firm for justice"),
            (16, 90, "Justice, kindness, and generosity"),
            (4, 135, "Stand firm for justice even against yourselves"),
        ],
    },
    {
        "id": "hereafter",
        "title": "Death & the Hereafter",
        "description": "Preparing the soul for the journey beyond this world",
        "category": "Spiritual Growth",
        "icon": "hourglass",
        "scholarly_sources": ["ihya", "riyad"],
        "verses": [
            (3, 185, "Every soul shall taste death"),
            (35, 5, "Life of this world is delusion"),
            (67, 2, "Created life as a test"),
            (89, 27, "O tranquil soul"),
        ],
    },
    {
        "id": "repentance",
        "title": "Repentance & Return",
        "description": "The door of tawbah is always open — returning to Allah",
        "category": "Spiritual Growth",
        "icon": "refresh",
        "scholarly_sources": ["ihya", "madarij", "riyad"],
        "verses": [
            (25, 63, "Servants of the Most Merciful"),
            (39, 53, "Despair not of Allah's mercy"),
            (66, 8, "Sincere repentance"),
            (2, 222, "Allah loves those who repent"),
        ],
    },
    {
        "id": "worship",
        "title": "Worship & Devotion",
        "description": "The essence of prayer, fasting, and devotion to Allah",
        "category": "Faith & Worship",
        "icon": "moon",
        "scholarly_sources": ["ihya"],
        "verses": [
            (2, 186, "Allah is near"),
            (6, 162, "Prayer and sacrifice for Allah"),
            (23, 1, "Success of the believers"),
            (51, 56, "Created to worship"),
            (87, 14, "Successful is the one who purifies"),
        ],
    },
    {
        "id": "charity",
        "title": "Charity & Generosity",
        "description": "The rewards of giving and caring for those in need",
        "category": "Character & Conduct",
        "icon": "gift",
        "scholarly_sources": ["ihya", "riyad"],
        "verses": [
            (2, 261, "Charity multiplied"),
            (2, 267, "Spend from what you love"),
            (3, 92, "You will not attain righteousness until you spend"),
            (57, 18, "Charity is a beautiful loan"),
        ],
    },
]

# Pre-build lookup: verse → collection IDs
_VERSE_TO_COLLECTIONS = {}
for _col in THEMED_COLLECTIONS:
    for _s, _v, _t in _col["verses"]:
        _key = f"{_s}:{_v}"
        _VERSE_TO_COLLECTIONS.setdefault(_key, []).append(_col["id"])


@app.route("/collections", methods=["GET"])
def list_collections():
    """List all themed verse collections (metadata only)."""
    result = []
    for col in THEMED_COLLECTIONS:
        result.append({
            "id": col["id"],
            "title": col["title"],
            "description": col["description"],
            "category": col["category"],
            "icon": col["icon"],
            "verse_count": len(col["verses"]),
            "scholarly_sources": col["scholarly_sources"],
        })
    return jsonify({"collections": result}), 200


@app.route("/collections/<collection_id>", methods=["GET"])
def get_collection(collection_id):
    """Get full collection with verse text."""
    col = next((c for c in THEMED_COLLECTIONS if c["id"] == collection_id), None)
    if not col:
        return jsonify({"error": "Collection not found"}), 404

    verses = []
    for surah, verse_num, theme in col["verses"]:
        verse_data = get_verse_from_firestore(surah, verse_num)
        surah_name = QURAN_METADATA.get(surah, {}).get("name", f"Surah {surah}")
        verses.append({
            "surah": surah,
            "verse": verse_num,
            "surah_name": surah_name,
            "theme": theme,
            "arabic_text": verse_data.get("arabic", "") if verse_data else "",
            "english_text": verse_data.get("english", "") if verse_data else "",
        })

    return jsonify({
        "id": col["id"],
        "title": col["title"],
        "description": col["description"],
        "category": col["category"],
        "verses": verses,
        "scholarly_sources": col["scholarly_sources"],
    }), 200


@app.route("/collections/<collection_id>/progress", methods=["GET"])
@firebase_auth_required
def get_collection_progress(collection_id):
    """Get user's progress for a collection."""
    uid = request.user["uid"]
    col = next((c for c in THEMED_COLLECTIONS if c["id"] == collection_id), None)
    if not col:
        return jsonify({"error": "Collection not found"}), 404

    try:
        user_doc = users_db.collection("users").document(uid).get()
        data = user_doc.to_dict() if user_doc.exists else {}
        progress = data.get("collection_progress", {}).get(collection_id, {})
        explored = progress.get("explored", [])

        return jsonify({
            "collection_id": collection_id,
            "explored": explored,
            "completed_count": len(explored),
            "total_count": len(col["verses"]),
            "percentage": round(len(explored) / len(col["verses"]) * 100) if col["verses"] else 0,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/collections/progress", methods=["GET"])
@firebase_auth_required
def get_all_collection_progress():
    """Get user's progress for all collections in a single request."""
    uid = request.user["uid"]
    try:
        user_doc = users_db.collection("users").document(uid).get()
        data = user_doc.to_dict() if user_doc.exists else {}
        all_progress = data.get("collection_progress", {})

        result = {}
        for col in THEMED_COLLECTIONS:
            cid = col["id"]
            progress = all_progress.get(cid, {})
            explored = progress.get("explored", [])
            result[cid] = {
                "collection_id": cid,
                "explored": explored,
                "completed_count": len(explored),
                "total_count": len(col["verses"]),
                "percentage": round(len(explored) / len(col["verses"]) * 100) if col["verses"] else 0,
            }

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/collections/<collection_id>/progress", methods=["POST"])
@firebase_auth_required
def update_collection_progress(collection_id):
    """Mark a verse as explored in a collection."""
    uid = request.user["uid"]
    col = next((c for c in THEMED_COLLECTIONS if c["id"] == collection_id), None)
    if not col:
        return jsonify({"error": "Collection not found"}), 404

    data = request.get_json() or {}
    verse_key = data.get("verse_key")  # e.g., "2:155"
    if not verse_key:
        return jsonify({"error": "verse_key required"}), 400

    try:
        user_ref = users_db.collection("users").document(uid)
        user_doc = user_ref.get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        collection_progress = user_data.get("collection_progress", {})
        col_data = collection_progress.get(collection_id, {"explored": [], "started_at": datetime.now(timezone.utc).isoformat()})

        if verse_key not in col_data["explored"]:
            col_data["explored"].append(verse_key)

        collection_progress[collection_id] = col_data
        user_ref.set({"collection_progress": collection_progress}, merge=True)

        return jsonify({
            "collection_id": collection_id,
            "explored": col_data["explored"],
            "completed_count": len(col_data["explored"]),
            "total_count": len(col["verses"]),
            "is_complete": len(col_data["explored"]) >= len(col["verses"]),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ACHIEVEMENT / BADGE SYSTEM
# ============================================================================

BADGE_DEFINITIONS = {
    # ── Consistency (Streaks) ──
    "streak_3": {"name": "Getting Started", "description": "Maintained a 3-day learning streak", "icon": "fire", "category": "consistency", "tier": "bronze", "threshold": 3},
    "streak_7": {"name": "Week of Wisdom", "description": "7 consecutive days of engagement", "icon": "calendar", "category": "consistency", "tier": "silver", "threshold": 7},
    "streak_14": {"name": "Fortnight of Focus", "description": "14 consecutive days of engagement", "icon": "calendar-check", "category": "consistency", "tier": "silver", "threshold": 14},
    "streak_30": {"name": "Month of Devotion", "description": "30-day learning streak", "icon": "crown", "category": "consistency", "tier": "gold", "threshold": 30},
    "streak_90": {"name": "Quarter of Commitment", "description": "90-day learning streak", "icon": "trophy", "category": "consistency", "tier": "gold", "threshold": 90},
    "streak_180": {"name": "Half-Year Dedication", "description": "180-day learning streak", "icon": "gem", "category": "consistency", "tier": "platinum", "threshold": 180},
    "streak_365": {"name": "Year of Transformation", "description": "365-day learning streak", "icon": "sun", "category": "consistency", "tier": "diamond", "threshold": 365},
    "comeback_7": {"name": "The Return", "description": "Returned after 7+ days away and completed 3 consecutive days", "icon": "refresh", "category": "consistency", "tier": "silver", "threshold": 3},

    # ── Exploration (Breadth) ──
    "explore_10": {"name": "Curious Mind", "description": "Explored 10 unique verses", "icon": "search", "category": "exploration", "tier": "bronze", "threshold": 10},
    "explore_50": {"name": "Seeker of Knowledge", "description": "Explored 50 unique verses", "icon": "book-open", "category": "exploration", "tier": "silver", "threshold": 50},
    "explore_100": {"name": "Deep Diver", "description": "Explored 100 unique verses", "icon": "compass", "category": "exploration", "tier": "silver", "threshold": 100},
    "explore_250": {"name": "Devoted Reader", "description": "Explored 250 unique verses", "icon": "library", "category": "exploration", "tier": "gold", "threshold": 250},
    "explore_500": {"name": "Quranic Scholar", "description": "Explored 500 unique verses", "icon": "graduation", "category": "exploration", "tier": "gold", "threshold": 500},
    "explore_1000": {"name": "Huffadh's Path", "description": "Explored 1,000 unique verses", "icon": "award", "category": "exploration", "tier": "platinum", "threshold": 1000},
    "surahs_10": {"name": "Surah Explorer", "description": "Explored verses from 10 different surahs", "icon": "globe", "category": "exploration", "tier": "bronze", "threshold": 10},
    "surahs_30": {"name": "Surah Voyager", "description": "Explored verses from 30 different surahs", "icon": "map", "category": "exploration", "tier": "silver", "threshold": 30},
    "surahs_50": {"name": "Quran Traveler", "description": "Explored verses from 50 different surahs", "icon": "rocket", "category": "exploration", "tier": "gold", "threshold": 50},
    "surahs_114": {"name": "Complete Journey", "description": "Explored verses from all 114 surahs", "icon": "flag", "category": "exploration", "tier": "diamond", "threshold": 114},

    # ── Reflection (Depth) ──
    "reflect_1": {"name": "First Reflection", "description": "Wrote your first reflection", "icon": "pen", "category": "reflection", "tier": "bronze", "threshold": 1},
    "reflect_10": {"name": "Thoughtful Heart", "description": "Wrote 10 reflections", "icon": "heart", "category": "reflection", "tier": "silver", "threshold": 10},
    "reflect_50": {"name": "Reflection Master", "description": "Wrote 50 reflections", "icon": "brain", "category": "reflection", "tier": "gold", "threshold": 50},
    "reflect_100": {"name": "Contemplative Soul", "description": "Wrote 100 reflections", "icon": "feather", "category": "reflection", "tier": "gold", "threshold": 100},
    "reflect_250": {"name": "Deep Thinker", "description": "Wrote 250 reflections", "icon": "lamp", "category": "reflection", "tier": "platinum", "threshold": 250},
    "reflect_500": {"name": "Voice of Tadabbur", "description": "Wrote 500 reflections", "icon": "scroll", "category": "reflection", "tier": "platinum", "threshold": 500},
    "reflect_1000": {"name": "Spiritual Journalist", "description": "Wrote 1,000 reflections", "icon": "book", "category": "reflection", "tier": "diamond", "threshold": 1000},

    # ── Completion (Plans & Collections) ──
    "plan_complete": {"name": "Journey Complete", "description": "Finished a reading plan", "icon": "star", "category": "completion", "tier": "bronze", "threshold": 1},
    "plan_3": {"name": "Triple Journey", "description": "Completed 3 reading plans", "icon": "stars", "category": "completion", "tier": "silver", "threshold": 3},
    "plan_7": {"name": "Seasoned Traveler", "description": "Completed 7 reading plans", "icon": "mountain", "category": "completion", "tier": "gold", "threshold": 7},
    "plan_all": {"name": "Master of Plans", "description": "Completed all available reading plans", "icon": "crown", "category": "completion", "tier": "diamond", "threshold": -1},
    "collection_complete": {"name": "Collection Complete", "description": "Completed a themed verse collection", "icon": "book", "category": "completion", "tier": "bronze", "threshold": 1},
    "collection_3": {"name": "Collection Builder", "description": "Completed 3 themed collections", "icon": "archive", "category": "completion", "tier": "silver", "threshold": 3},
    "collection_all": {"name": "Complete Scholar", "description": "Completed all 12 themed collections", "icon": "library", "category": "completion", "tier": "gold", "threshold": 12},

    # ── Special & Seasonal ──
    "ramadan_plan": {"name": "Ramadan Completer", "description": "Completed the Ramadan Essentials plan", "icon": "moon", "category": "special", "tier": "gold", "threshold": 1},
    "daily_verse_7": {"name": "Daily Verse Devotee", "description": "Studied the daily verse 7 times", "icon": "sunrise", "category": "special", "tier": "silver", "threshold": 7},
    "first_week": {"name": "Welcome", "description": "Active during your first 7 days", "icon": "hand-wave", "category": "special", "tier": "bronze", "threshold": 1},
}


def _check_and_award_badges(uid):
    """Check all badge conditions and award any newly earned badges. Returns list of newly earned."""
    try:
        user_doc = users_db.collection("users").document(uid).get()
        data = user_doc.to_dict() if user_doc.exists else {}

        earned = data.get("badges_earned", {})
        stats = data.get("stats_cache", {})
        streak_current = data.get("streak_current", 0)
        streak_longest = data.get("streak_longest", 0)
        total_verses = stats.get("total_explored_verses", 0)
        total_surahs = stats.get("total_explored_surahs", 0)

        # Count annotations (raise limit for higher-tier badges)
        try:
            ann_limit = 1001 if "reflect_500" not in earned else 51
            ann_query = users_db.collection("users").document(uid).collection("annotations").limit(ann_limit)
            annotation_count = sum(1 for _ in ann_query.stream())
        except Exception:
            annotation_count = 0

        # Count completed collections
        collection_progress = data.get("collection_progress", {})
        completed_collections = sum(
            1 for cid, cp in collection_progress.items()
            if len(cp.get("explored", [])) >= len(next((c["verses"] for c in THEMED_COLLECTIONS if c["id"] == cid), []))
        )

        # Count completed plans (support both old single and new multi-plan format)
        active_plans = data.get("active_plans", {})
        old_plan = data.get("active_plan", {})
        completed_plans = sum(1 for p in active_plans.values() if p.get("completed_at"))
        if old_plan.get("completed_at") and old_plan.get("plan_id") not in active_plans:
            completed_plans += 1

        # Check for comeback streak (7+ day gap then 3 consecutive days)
        streak_last_date = data.get("streak_last_date")
        is_comeback = False
        if streak_last_date and streak_current >= 3:
            try:
                from datetime import date as dt_date
                if isinstance(streak_last_date, str):
                    last = dt_date.fromisoformat(streak_last_date)
                else:
                    last = streak_last_date
                # Check if there was a gap of 7+ days before current streak started
                gap_start = datetime.now(timezone.utc).date() - timedelta(days=streak_current)
                if hasattr(last, 'date'):
                    last = last.date()
                # This is approximate — comeback detected if user had a long gap
                # We store a flag when we detect it
                is_comeback = data.get("_comeback_detected", False)
            except Exception:
                pass

        # Check for Ramadan plan completion
        ramadan_completed = any(
            p.get("plan_id") == "ramadan_30" and p.get("completed_at")
            for p in list(active_plans.values()) + ([old_plan] if old_plan else [])
        )

        # Daily verse study count
        daily_verse_count = data.get("daily_verse_count", 0)

        # First week check
        created_at = data.get("created_at")
        first_week_active = False
        if created_at:
            try:
                if isinstance(created_at, str):
                    created_dt = datetime.fromisoformat(created_at)
                else:
                    created_dt = created_at
                days_since_signup = (datetime.now(timezone.utc) - created_dt).days
                first_week_active = days_since_signup <= 7 and streak_current >= 1
            except Exception:
                pass

        newly_earned = []
        best_streak = max(streak_current, streak_longest)

        checks = {
            # Consistency
            "streak_3": best_streak >= 3,
            "streak_7": best_streak >= 7,
            "streak_14": best_streak >= 14,
            "streak_30": best_streak >= 30,
            "streak_90": best_streak >= 90,
            "streak_180": best_streak >= 180,
            "streak_365": best_streak >= 365,
            "comeback_7": is_comeback,
            # Exploration
            "explore_10": total_verses >= 10,
            "explore_50": total_verses >= 50,
            "explore_100": total_verses >= 100,
            "explore_250": total_verses >= 250,
            "explore_500": total_verses >= 500,
            "explore_1000": total_verses >= 1000,
            "surahs_10": total_surahs >= 10,
            "surahs_30": total_surahs >= 30,
            "surahs_50": total_surahs >= 50,
            "surahs_114": total_surahs >= 114,
            # Reflection
            "reflect_1": annotation_count >= 1,
            "reflect_10": annotation_count >= 10,
            "reflect_50": annotation_count >= 50,
            "reflect_100": annotation_count >= 100,
            "reflect_250": annotation_count >= 250,
            "reflect_500": annotation_count >= 500,
            "reflect_1000": annotation_count >= 1000,
            # Completion
            "collection_complete": completed_collections >= 1,
            "collection_3": completed_collections >= 3,
            "collection_all": completed_collections >= len(THEMED_COLLECTIONS),
            "plan_complete": completed_plans >= 1,
            "plan_3": completed_plans >= 3,
            "plan_7": completed_plans >= 7,
            "plan_all": completed_plans >= len(READING_PLANS),
            # Special
            "ramadan_plan": ramadan_completed,
            "daily_verse_7": daily_verse_count >= 7,
            "first_week": first_week_active,
        }

        for badge_id, condition in checks.items():
            if condition and badge_id not in earned:
                earned[badge_id] = {"earned_at": datetime.now(timezone.utc).isoformat()}
                newly_earned.append({
                    "id": badge_id,
                    **BADGE_DEFINITIONS[badge_id]
                })

        if newly_earned:
            users_db.collection("users").document(uid).set(
                {"badges_earned": earned}, merge=True
            )

        return newly_earned
    except Exception as e:
        print(f"WARNING: Badge check failed: {e}")
        return []


@app.route("/badges", methods=["GET"])
@firebase_auth_required
def get_badges():
    """Get all badge definitions with user's earned status."""
    uid = request.user["uid"]
    try:
        user_doc = users_db.collection("users").document(uid).get()
        data = user_doc.to_dict() if user_doc.exists else {}
        earned = data.get("badges_earned", {})

        badges = []
        for badge_id, defn in BADGE_DEFINITIONS.items():
            badge = {
                "id": badge_id,
                **defn,
                "earned": badge_id in earned,
                "earned_at": earned[badge_id]["earned_at"] if badge_id in earned else None,
            }
            badges.append(badge)

        return jsonify({
            "badges": badges,
            "total_earned": len(earned),
            "total_available": len(BADGE_DEFINITIONS),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PERSONALIZED RECOMMENDATIONS
# ============================================================================

def _generate_recommendations(surah, verse, final_json, user_id=None):
    """Generate deterministic verse recommendations based on cross-refs and themes."""
    recs = []
    seen = {f"{surah}:{verse}"}

    # 1. Cross-references from the response
    for ref in final_json.get("cross_references", [])[:3]:
        ref_str = ref.get("verse", "")
        match = re.match(r"(\d+):(\d+)", ref_str)
        if match and ref_str not in seen:
            s, v = int(match.group(1)), int(match.group(2))
            sname = QURAN_METADATA.get(s, {}).get("name", f"Surah {s}")
            recs.append({"surah": s, "verse": v, "surah_name": sname,
                         "reason": ref.get("relevance", "Related verse")[:80]})
            seen.add(ref_str)

    # 2. Collection-based: if this verse is in a themed collection, suggest next verse
    verse_key = f"{surah}:{verse}"
    col_ids = _VERSE_TO_COLLECTIONS.get(verse_key, [])
    for cid in col_ids[:1]:
        col = next((c for c in THEMED_COLLECTIONS if c["id"] == cid), None)
        if col:
            for s, v, theme in col["verses"]:
                vk = f"{s}:{v}"
                if vk not in seen:
                    sname = QURAN_METADATA.get(s, {}).get("name", f"Surah {s}")
                    recs.append({"surah": s, "verse": v, "surah_name": sname,
                                 "reason": f"From '{col['title']}' collection"})
                    seen.add(vk)
                    break

    # 3. Theme-based from verse map
    from services.source_service import _load_unified_verse_map
    verse_map = _load_unified_verse_map()
    refs = verse_map.get(verse_key, [])
    source_chapters = set()
    for ref in refs:
        src = ref.get("source", "")
        if src == "ihya_ulum_al_din":
            source_chapters.add(("ihya", ref.get("volume"), ref.get("chapter")))
        elif src == "riyad_al_saliheen":
            source_chapters.add(("riyad", ref.get("book"), ref.get("chapter")))

    if source_chapters and len(recs) < 5:
        for map_key, map_refs in list(verse_map.items())[:500]:
            if map_key in seen or len(recs) >= 5:
                break
            for mr in map_refs:
                src = mr.get("source", "")
                ch_key = None
                if src == "ihya_ulum_al_din":
                    ch_key = ("ihya", mr.get("volume"), mr.get("chapter"))
                elif src == "riyad_al_saliheen":
                    ch_key = ("riyad", mr.get("book"), mr.get("chapter"))
                if ch_key and ch_key in source_chapters and map_key not in seen:
                    parts = map_key.split(":")
                    if len(parts) == 2:
                        s, v = int(parts[0]), int(parts[1])
                        sname = QURAN_METADATA.get(s, {}).get("name", f"Surah {s}")
                        recs.append({"surah": s, "verse": v, "surah_name": sname,
                                     "reason": "Shares scholarly theme"})
                        seen.add(map_key)
                        break

    return recs[:5]


# ============================================================================
# READING PLANS (imported from data.reading_plans — 36 enhanced plans)
# ============================================================================
# READING_PLANS imported at top of file via: from data.reading_plans import READING_PLANS



@app.route("/reading-plans", methods=["GET"])
def list_reading_plans():
    """List all available reading plans (metadata only)."""
    result = []
    for plan in READING_PLANS:
        result.append({
            "id": plan["id"],
            "title": plan["title"],
            "description": plan["description"],
            "duration_days": plan["duration_days"],
            "category": plan["category"],
            "difficulty": plan.get("difficulty", "beginner"),
            "tags": plan.get("tags", []),
        })
    return jsonify({"plans": result}), 200


@app.route("/reading-plans/<plan_id>", methods=["GET"])
def get_reading_plan(plan_id):
    """Get full reading plan with verse text for each day."""
    plan = next((p for p in READING_PLANS if p["id"] == plan_id), None)
    if not plan:
        return jsonify({"error": "Plan not found"}), 404

    days = []
    for day in plan["days"]:
        surah, verse_num = day["verse"]
        verse_data = get_verse_from_firestore(surah, verse_num)
        surah_name = QURAN_METADATA.get(surah, {}).get("name", f"Surah {surah}")
        days.append({
            **day,
            "surah_name": surah_name,
            "arabic_text": verse_data.get("arabic", "") if verse_data else "",
            "english_text": verse_data.get("english", "") if verse_data else "",
        })

    return jsonify({
        "id": plan["id"],
        "title": plan["title"],
        "description": plan["description"],
        "overview": plan.get("overview", ""),
        "outcomes": plan.get("outcomes", []),
        "duration_days": plan["duration_days"],
        "category": plan["category"],
        "difficulty": plan.get("difficulty", "beginner"),
        "next_recommended": plan.get("next_recommended", ""),
        "tags": plan.get("tags", []),
        "days": days,
    }), 200


@app.route("/reading-plans/active", methods=["GET"])
@firebase_auth_required
def get_all_active_plans():
    """Get all active plans for the user."""
    uid = request.user["uid"]
    try:
        user_doc = users_db.collection("users").document(uid).get()
        data = user_doc.to_dict() if user_doc.exists else {}

        # Support both old single active_plan and new active_plans dict
        active_plans = data.get("active_plans", {})
        # Migrate old format if present
        old_plan = data.get("active_plan", {})
        if old_plan and old_plan.get("plan_id") and old_plan["plan_id"] not in active_plans:
            active_plans[old_plan["plan_id"]] = old_plan

        results = []
        for pid, plan_data in active_plans.items():
            plan = next((p for p in READING_PLANS if p["id"] == pid), None)
            if not plan:
                continue
            current_day = plan_data.get("current_day", 1)
            today_verse = None
            if 1 <= current_day <= len(plan["days"]):
                day_data = plan["days"][current_day - 1]
                surah, verse_num = day_data["verse"]
                surah_name = QURAN_METADATA.get(surah, {}).get("name", f"Surah {surah}")
                today_verse = {
                    "surah": surah,
                    "verse": verse_num,
                    "surah_name": surah_name,
                    "title": day_data.get("title", ""),
                    "prompt": day_data.get("prompt", ""),
                }
            completed_days = plan_data.get("completed_days", [])
            is_complete = len(completed_days) >= plan["duration_days"]
            results.append({
                "active": not is_complete,
                "plan_id": pid,
                "title": plan["title"],
                "description": plan["description"],
                "duration_days": plan["duration_days"],
                "category": plan["category"],
                "current_day": current_day,
                "completed_days": completed_days,
                "started_at": plan_data.get("started_at"),
                "completed_at": plan_data.get("completed_at"),
                "today_verse": today_verse,
            })

        return jsonify({"plans": results}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reading-plans/<plan_id>/progress", methods=["GET"])
@firebase_auth_required
def get_plan_progress(plan_id):
    """Get user's progress on a reading plan."""
    uid = request.user["uid"]
    try:
        user_doc = users_db.collection("users").document(uid).get()
        data = user_doc.to_dict() if user_doc.exists else {}

        # Check new active_plans dict first, fall back to old active_plan
        active_plans = data.get("active_plans", {})
        plan_progress = active_plans.get(plan_id)
        if not plan_progress:
            old_plan = data.get("active_plan", {})
            if old_plan.get("plan_id") == plan_id:
                plan_progress = old_plan
        if not plan_progress:
            return jsonify({"active": False, "plan_id": plan_id}), 200

        # Look up today's verse from the plan data
        plan = next((p for p in READING_PLANS if p["id"] == plan_id), None)
        current_day = plan_progress.get("current_day", 1)
        today_verse = None
        if plan and 1 <= current_day <= len(plan["days"]):
            day_data = plan["days"][current_day - 1]
            surah, verse_num = day_data["verse"]
            surah_name = QURAN_METADATA.get(surah, {}).get("name", f"Surah {surah}")
            today_verse = {
                "surah": surah,
                "verse": verse_num,
                "surah_name": surah_name,
                "title": day_data.get("title", ""),
                "prompt": day_data.get("prompt", ""),
            }

        return jsonify({
            "active": True,
            "plan_id": plan_id,
            "current_day": current_day,
            "completed_days": plan_progress.get("completed_days", []),
            "started_at": plan_progress.get("started_at"),
            "completed_at": plan_progress.get("completed_at"),
            "today_verse": today_verse,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reading-plans/<plan_id>/progress", methods=["POST"])
@firebase_auth_required
def update_plan_progress(plan_id):
    """Start a plan or complete a day."""
    uid = request.user["uid"]
    plan = next((p for p in READING_PLANS if p["id"] == plan_id), None)
    if not plan:
        return jsonify({"error": "Plan not found"}), 404

    data = request.get_json() or {}
    action = data.get("action")  # "start" or "complete_day"

    try:
        user_ref = users_db.collection("users").document(uid)

        if action == "start":
            # Read current active_plans dict
            user_doc = user_ref.get()
            user_data = user_doc.to_dict() if user_doc.exists else {}
            active_plans = user_data.get("active_plans", {})

            # Migrate old single active_plan if present
            old_plan = user_data.get("active_plan", {})
            if old_plan and old_plan.get("plan_id") and old_plan["plan_id"] not in active_plans:
                active_plans[old_plan["plan_id"]] = old_plan

            # Add the new plan (or restart it)
            active_plans[plan_id] = {
                "plan_id": plan_id,
                "current_day": 1,
                "completed_days": [],
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": None,
            }

            user_ref.set({"active_plans": active_plans}, merge=True)
            return jsonify({"status": "started", "plan_id": plan_id, "current_day": 1}), 200

        elif action == "complete_day":
            day_num = data.get("day")
            if not day_num or day_num < 1 or day_num > plan["duration_days"]:
                return jsonify({"error": "Invalid day number"}), 400

            user_doc = user_ref.get()
            user_data = user_doc.to_dict() if user_doc.exists else {}
            active_plans = user_data.get("active_plans", {})

            # Migrate old format
            old_plan = user_data.get("active_plan", {})
            if old_plan and old_plan.get("plan_id") and old_plan["plan_id"] not in active_plans:
                active_plans[old_plan["plan_id"]] = old_plan

            active = active_plans.get(plan_id)
            if not active:
                return jsonify({"error": "This plan is not active"}), 400

            completed = active.get("completed_days", [])
            if day_num not in completed:
                completed.append(day_num)

            next_day = min(day_num + 1, plan["duration_days"])
            is_complete = len(completed) >= plan["duration_days"]

            active_plans[plan_id] = {
                "plan_id": plan_id,
                "current_day": next_day,
                "completed_days": completed,
                "started_at": active.get("started_at"),
                "completed_at": datetime.now(timezone.utc).isoformat() if is_complete else None,
            }

            user_ref.set({"active_plans": active_plans}, merge=True)

            # Track the verse as explored
            verse_info = plan["days"][day_num - 1]["verse"]
            _track_explored_verse(uid, verse_info[0], verse_info[1])

            # Check badges
            newly_earned = _check_and_award_badges(uid)

            return jsonify({
                "status": "completed" if is_complete else "day_complete",
                "day": day_num,
                "current_day": next_day,
                "completed_days": completed,
                "is_complete": is_complete,
                "newly_earned_badges": newly_earned,
            }), 200

        return jsonify({"error": "Invalid action. Use 'start' or 'complete_day'"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# QUERY HISTORY & SAVED SEARCHES ENDPOINTS
# ============================================================================

@app.route("/query-history", methods=["GET"])
@firebase_auth_required
def get_query_history():
    """Get user's recent query history"""
    try:
        uid = request.user['uid']
        try:
            limit = min(int(request.args.get('limit', 50)), 200)  # Cap at 200
        except (ValueError, TypeError):
            limit = 50

        history_ref = users_db.collection('users').document(uid).collection('query_history')
        query = history_ref.order_by('timestamp', direction='DESCENDING').limit(limit)

        history = []
        for doc in query.stream():
            data = doc.to_dict()
            # Convert Firestore timestamp to serializable format
            timestamp = data.get('timestamp', '')
            if timestamp and hasattr(timestamp, 'timestamp'):
                # Convert to seconds since epoch for JavaScript
                timestamp = {'seconds': int(timestamp.timestamp())}

            history.append({
                'id': doc.id,
                'query': data.get('query', ''),
                'approach': data.get('approach', 'tafsir'),
                'persona': data.get('persona', ''),
                'timestamp': timestamp,
                'hasResult': data.get('hasResult', False)
            })

        return jsonify({'history': history, 'count': len(history)}), 200

    except Exception as e:
        print(f"ERROR in /query-history: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/query-history", methods=["POST"])
@firebase_auth_required
def save_query_to_history():
    """Save a query to user's history"""
    try:
        uid = request.user['uid']
        data = request.get_json()

        query_text = data.get('query', '')
        approach = data.get('approach', 'tafsir')
        persona = data.get('persona', '')
        has_result = data.get('hasResult', True)

        if not query_text:
            return jsonify({"error": "Query text is required"}), 400

        history_ref = users_db.collection('users').document(uid).collection('query_history')

        # Add to history
        doc_ref = history_ref.document()
        doc_ref.set({
            'query': query_text,
            'approach': approach,
            'persona': persona,
            'hasResult': has_result,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        return jsonify({'success': True, 'id': doc_ref.id}), 201

    except Exception as e:
        print(f"ERROR in POST /query-history: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/saved-searches", methods=["GET"])
@firebase_auth_required
def get_saved_searches():
    """Get user's saved searches/answers"""
    try:
        uid = request.user['uid']
        folder = request.args.get('folder', None)

        saved_ref = users_db.collection('users').document(uid).collection('saved_searches')

        if folder:
            # Updated to use FieldFilter (new Firestore syntax)
            query = saved_ref.where(filter=FieldFilter('folder', '==', folder)).order_by('savedAt', direction='DESCENDING')
        else:
            query = saved_ref.order_by('savedAt', direction='DESCENDING')

        saved = []
        for doc in query.stream():
            data = doc.to_dict()
            # Convert Firestore timestamp to serializable format
            savedAt = data.get('savedAt', '')
            if savedAt and hasattr(savedAt, 'timestamp'):
                # Convert to seconds since epoch for JavaScript
                savedAt = {'seconds': int(savedAt.timestamp())}

            saved.append({
                'id': doc.id,
                'query': data.get('query', ''),
                'approach': data.get('approach', 'tafsir'),
                'folder': data.get('folder', 'Uncategorized'),
                'title': data.get('title', data.get('query', '')[:50]),
                'savedAt': savedAt,
                'responseSnippet': data.get('responseSnippet', ''),
                'fullResponse': data.get('fullResponse')  # Include full response for "View Full Answer"
            })

        return jsonify({'saved': saved, 'count': len(saved)}), 200

    except Exception as e:
        print(f"ERROR in /saved-searches: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/saved-searches", methods=["POST"])
@firebase_auth_required
def save_search():
    """Save a search/answer for later"""
    try:
        uid = request.user['uid']
        data = request.get_json()

        query_text = data.get('query', '')
        approach = data.get('approach', 'tafsir')
        folder = data.get('folder', 'Uncategorized')
        title = data.get('title', query_text[:50])
        response_snippet = data.get('responseSnippet', '')
        full_response = data.get('fullResponse', None)  # Optional: store full response

        if not query_text:
            return jsonify({"error": "Query text is required"}), 400

        saved_ref = users_db.collection('users').document(uid).collection('saved_searches')

        doc_ref = saved_ref.document()
        save_data = {
            'query': query_text,
            'approach': approach,
            'folder': folder,
            'title': title,
            'responseSnippet': response_snippet,
            'savedAt': firestore.SERVER_TIMESTAMP
        }

        if full_response:
            save_data['fullResponse'] = full_response

        doc_ref.set(save_data)

        return jsonify({'success': True, 'id': doc_ref.id}), 201

    except Exception as e:
        print(f"ERROR in POST /saved-searches: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/saved-searches/<search_id>", methods=["DELETE"])
@firebase_auth_required
def delete_saved_search(search_id):
    """Delete a saved search"""
    try:
        uid = request.user['uid']

        doc_ref = users_db.collection('users').document(uid).collection('saved_searches').document(search_id)
        doc_ref.delete()

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"ERROR in DELETE /saved-searches: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/saved-searches/folders", methods=["GET"])
@firebase_auth_required
def get_folders():
    """Get list of all folders with counts"""
    try:
        uid = request.user['uid']

        saved_ref = users_db.collection('users').document(uid).collection('saved_searches')

        # Get all saved searches and group by folder
        folders = {}
        for doc in saved_ref.stream():
            data = doc.to_dict()
            folder = data.get('folder', 'Uncategorized')
            folders[folder] = folders.get(folder, 0) + 1

        folder_list = [{'name': name, 'count': count} for name, count in folders.items()]
        folder_list.sort(key=lambda x: x['name'])

        return jsonify({'folders': folder_list, 'totalFolders': len(folder_list)}), 200

    except Exception as e:
        print(f"ERROR in /saved-searches/folders: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# VERSE-LEVEL ANNOTATIONS ENDPOINTS
# ============================================================================

@app.route("/annotations/verse/<path:surah>/<verse>", methods=["GET", "OPTIONS"])
def get_verse_annotations(surah, verse):
    """Get all annotations for a specific verse"""
    # Handle CORS preflight request
    if request.method == "OPTIONS":
        return "", 200

    # Apply authentication for GET requests
    @firebase_auth_required
    def handle_get():
        try:
            uid = request.user['uid']

            # Parse surah - could be number or name
            try:
                # Check if surah is a number
                if surah.isdigit():
                    surah_num = int(surah)
                else:
                    # Handle URL-encoded surah names (e.g., "Al-Baqarah" or "Ali%20'Imran")
                    import urllib.parse
                    surah_decoded = urllib.parse.unquote(surah)
                    # Map surah name to number
                    surah_num = SURAHS_BY_NAME.get(surah_decoded.lower())
                    if not surah_num:
                        # Try with various formats
                        surah_normalized = surah_decoded.replace("'", "").replace("-", " ").lower()
                        for name, num in SURAHS_BY_NAME.items():
                            if name.replace("'", "").replace("-", " ") == surah_normalized:
                                surah_num = num
                                break

                    if not surah_num:
                        return jsonify({"error": f"Invalid surah: {surah}"}), 400

                # Parse verse (handle "2:94" format if present)
                verse_str = str(verse)
                if ':' in verse_str:
                    verse_str = verse_str.split(':')[-1]
                verse_num = int(verse_str)

                # Validate verse reference
                if surah_num not in QURAN_METADATA:
                    return jsonify({"error": f"Invalid surah number: {surah_num}"}), 400
                if verse_num < 1 or verse_num > QURAN_METADATA[surah_num]["verses"]:
                    return jsonify({"error": f"Invalid verse number: {verse_num} for surah {surah_num}"}), 400

            except ValueError:
                return jsonify({"error": "Invalid verse reference format"}), 400

            annotations_ref = users_db.collection('users').document(uid).collection('annotations')
            # Updated to use FieldFilter (new Firestore syntax) - requires composite index
            # Use surah_num and verse_num (integers) for the query
            query = annotations_ref.where(filter=FieldFilter('surah', '==', surah_num)) \
                                  .where(filter=FieldFilter('verse', '==', verse_num)) \
                                  .order_by('createdAt', direction='DESCENDING')

            annotations = []
            for doc in query.stream():
                data = doc.to_dict()

                # Convert Firestore timestamp to serializable format
                created_at = data.get('createdAt')
                if created_at and hasattr(created_at, 'timestamp'):
                    created_at = {'seconds': int(created_at.timestamp())}

                updated_at = data.get('updatedAt')
                if updated_at and hasattr(updated_at, 'timestamp'):
                    updated_at = {'seconds': int(updated_at.timestamp())}

                annotations.append({
                    'id': doc.id,
                    'surah': data.get('surah'),
                    'verse': data.get('verse'),
                    'type': data.get('type', 'personal_insight'),
                    'content': _decrypt_text(data.get('content', ''), uid),
                    'tags': data.get('tags', []),
                    'linkedVerses': data.get('linkedVerses', []),
                    'createdAt': created_at,
                    'updatedAt': updated_at,
                    'isPrivate': data.get('isPrivate', True)
                })

            return jsonify({'annotations': annotations, 'count': len(annotations)}), 200

        except Exception as e:
            print(f"ERROR in /annotations/verse: {type(e).__name__} - {e}")
            return jsonify({"error": str(e)}), 500

    # Call the inner function for GET requests
    return handle_get()


@app.route("/annotations/verses", methods=["GET"])
@firebase_auth_required
def get_batch_verse_annotations():
    """Get annotations for multiple verses in a single request.
    Query params: surah (int), from_verse (int), to_verse (int)
    """
    try:
        uid = request.user['uid']
        surah_num = request.args.get('surah', type=int)
        from_verse = request.args.get('from_verse', type=int)
        to_verse = request.args.get('to_verse', type=int)

        if not all([surah_num, from_verse, to_verse]):
            return jsonify({"error": "surah, from_verse, and to_verse are required"}), 400
        if to_verse < from_verse:
            return jsonify({"error": "to_verse must be >= from_verse"}), 400
        if to_verse - from_verse > 20:
            return jsonify({"error": "Maximum 20 verses per batch request"}), 400
        if surah_num not in QURAN_METADATA:
            return jsonify({"error": f"Invalid surah number: {surah_num}"}), 400

        annotations_ref = users_db.collection('users').document(uid).collection('annotations')
        query = annotations_ref.where(filter=FieldFilter('surah', '==', surah_num)) \
                              .where(filter=FieldFilter('verse', '>=', from_verse)) \
                              .where(filter=FieldFilter('verse', '<=', to_verse)) \
                              .order_by('verse') \
                              .order_by('createdAt', direction='DESCENDING')

        result = {}
        for v in range(from_verse, to_verse + 1):
            result[str(v)] = []

        for doc in query.stream():
            data = doc.to_dict()
            verse_key = str(data.get('verse', 0))

            created_at = data.get('createdAt')
            if created_at and hasattr(created_at, 'timestamp'):
                created_at = {'seconds': int(created_at.timestamp())}
            updated_at = data.get('updatedAt')
            if updated_at and hasattr(updated_at, 'timestamp'):
                updated_at = {'seconds': int(updated_at.timestamp())}

            if verse_key in result:
                result[verse_key].append({
                    'id': doc.id,
                    'surah': data.get('surah'),
                    'verse': data.get('verse'),
                    'type': data.get('type', 'personal_insight'),
                    'content': _decrypt_text(data.get('content', ''), uid),
                    'tags': data.get('tags', []),
                    'linkedVerses': data.get('linkedVerses', []),
                    'createdAt': created_at,
                    'updatedAt': updated_at,
                    'isPrivate': data.get('isPrivate', True)
                })

        total = sum(len(v) for v in result.values())
        return jsonify({'annotations': result, 'count': total, 'surah': surah_num}), 200

    except Exception as e:
        print(f"ERROR in /annotations/verses: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/annotations/user", methods=["GET"])
@firebase_auth_required
def get_user_annotations():
    """Get all annotations for user with optional filters"""
    try:
        uid = request.user['uid']
        tag = request.args.get('tag')
        annotation_type = request.args.get('type')
        try:
            limit = min(int(request.args.get('limit', 100)), 500)  # Cap at 500
        except (ValueError, TypeError):
            limit = 100

        annotations_ref = users_db.collection('users').document(uid).collection('annotations')
        query = annotations_ref.order_by('createdAt', direction='DESCENDING').limit(limit)

        annotations = []
        for doc in query.stream():
            data = doc.to_dict()

            # Apply filters
            if tag and tag not in data.get('tags', []):
                continue
            if annotation_type and data.get('type') != annotation_type:
                continue

            # Convert Firestore timestamp to serializable format
            created_at = data.get('createdAt')
            if created_at and hasattr(created_at, 'timestamp'):
                created_at = {'seconds': int(created_at.timestamp())}

            updated_at = data.get('updatedAt')
            if updated_at and hasattr(updated_at, 'timestamp'):
                updated_at = {'seconds': int(updated_at.timestamp())}

            annotation_obj = {
                'id': doc.id,
                'type': data.get('type', 'personal_insight'),
                'content': _decrypt_text(data.get('content', ''), uid),
                'tags': data.get('tags', []),
                'createdAt': created_at,
                'updatedAt': updated_at,
                'reflection_type': data.get('reflection_type', 'verse'),
                'share_id': data.get('share_id')
            }

            # Add verse-specific fields
            if data.get('surah') and data.get('verse'):
                annotation_obj['surah'] = data.get('surah')
                annotation_obj['verse'] = data.get('verse')
                annotation_obj['verseRef'] = f"{data.get('surah')}:{data.get('verse')}"
                annotation_obj['linkedVerses'] = data.get('linkedVerses', [])

            # Add section-specific fields
            if data.get('section_name'):
                annotation_obj['section_name'] = data.get('section_name')
                annotation_obj['query_context'] = data.get('query_context', '')

            # Add general reflection fields
            if data.get('reflection_type') == 'general':
                annotation_obj['query_context'] = data.get('query_context', '')

            # Add highlight reflection fields
            if data.get('highlighted_text'):
                annotation_obj['highlighted_text'] = _decrypt_text(data.get('highlighted_text'), uid)
                annotation_obj['query_context'] = data.get('query_context', '')

            annotations.append(annotation_obj)

        return jsonify({'annotations': annotations, 'count': len(annotations)}), 200

    except Exception as e:
        print(f"ERROR in /annotations/user: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/annotations", methods=["POST"])
@firebase_auth_required
def create_annotation():
    """Create a new annotation - supports verse, section, general, and highlight reflections"""
    try:
        uid = request.user['uid']
        data = request.get_json()

        # Get common fields
        annotation_type = data.get('type', 'personal_insight')
        content = data.get('content', '')
        tags = data.get('tags', [])
        reflection_type = data.get('reflection_type', 'verse')  # verse, section, general, highlight

        if not content:
            return jsonify({"error": "Content is required"}), 400

        annotations_ref = users_db.collection('users').document(uid).collection('annotations')
        doc_ref = annotations_ref.document()

        # Encrypt sensitive content before storage
        encrypted_content = _encrypt_text(content, uid)

        # Base annotation data
        annotation_data = {
            'type': annotation_type,
            'content': encrypted_content,
            'tags': tags,
            'reflection_type': reflection_type,
            'isPrivate': data.get('isPrivate', True),
            'createdAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }

        # Store share_id to link back to original response
        if data.get('share_id'):
            annotation_data['share_id'] = data.get('share_id')

        # Handle verse-specific reflections
        if reflection_type == 'verse':
            surah = data.get('surah')
            verse = data.get('verse')

            if not surah or not verse:
                return jsonify({"error": "Surah and verse are required for verse reflections"}), 400

            # Convert surah name to number if needed
            surah_num, error = surah_name_to_number(surah)
            if error:
                return jsonify({"error": error}), 400

            # Convert verse to int if string
            if isinstance(verse, str):
                try:
                    verse = int(verse)
                except ValueError:
                    return jsonify({"error": f"Invalid verse number: '{verse}'"}), 400

            # Validate verse reference
            is_valid, msg = validate_verse_reference(surah_num, verse)
            if not is_valid:
                return jsonify({"error": msg}), 400

            annotation_data['surah'] = surah_num
            annotation_data['verse'] = verse
            annotation_data['linkedVerses'] = data.get('linkedVerses', [])

        # Handle section-specific reflections
        elif reflection_type == 'section':
            section_name = data.get('section_name')
            if not section_name:
                return jsonify({"error": "Section name is required for section reflections"}), 400
            annotation_data['section_name'] = section_name
            annotation_data['query_context'] = data.get('query_context', '')

        # Handle general reflections
        elif reflection_type == 'general':
            annotation_data['query_context'] = data.get('query_context', '')

        # Handle highlighted text reflections
        elif reflection_type == 'highlight':
            highlighted_text = data.get('highlighted_text')
            if not highlighted_text:
                return jsonify({"error": "Highlighted text is required for highlight reflections"}), 400
            annotation_data['highlighted_text'] = _encrypt_text(highlighted_text, uid)
            annotation_data['query_context'] = data.get('query_context', '')

        doc_ref.set(annotation_data)

        # Check for newly earned badges after annotation creation
        newly_earned = []
        try:
            newly_earned = _check_and_award_badges(uid)
        except Exception as badge_err:
            print(f"[BADGES] Error checking badges after annotation: {badge_err}")

        return jsonify({
            'success': True,
            'id': doc_ref.id,
            'newly_earned_badges': newly_earned,
        }), 201

    except Exception as e:
        print(f"ERROR in POST /annotations: {type(e).__name__} - {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/annotations/<annotation_id>", methods=["PUT"])
@firebase_auth_required
def update_annotation(annotation_id):
    """Update an existing annotation"""
    try:
        uid = request.user['uid']
        data = request.get_json()

        doc_ref = users_db.collection('users').document(uid).collection('annotations').document(annotation_id)

        # Check if annotation exists
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({"error": "Annotation not found"}), 404

        # Update fields
        update_data = {'updatedAt': firestore.SERVER_TIMESTAMP}

        if 'content' in data:
            update_data['content'] = _encrypt_text(data['content'], uid)
        if 'tags' in data:
            update_data['tags'] = data['tags']
        if 'linkedVerses' in data:
            update_data['linkedVerses'] = data['linkedVerses']
        if 'type' in data:
            update_data['type'] = data['type']

        doc_ref.update(update_data)

        return jsonify({'success': True, 'id': annotation_id}), 200

    except Exception as e:
        print(f"ERROR in PUT /annotations: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/annotations/<annotation_id>", methods=["DELETE"])
@firebase_auth_required
def delete_annotation(annotation_id):
    """Delete an annotation"""
    try:
        uid = request.user['uid']

        doc_ref = users_db.collection('users').document(uid).collection('annotations').document(annotation_id)
        doc_ref.delete()

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"ERROR in DELETE /annotations: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/annotations/search", methods=["GET"])
@firebase_auth_required
def search_annotations():
    """Search annotations by text content"""
    try:
        uid = request.user['uid']
        query_text = request.args.get('q', '').lower()
        tag = request.args.get('tag')

        if not query_text and not tag:
            return jsonify({"error": "Query text or tag required"}), 400

        annotations_ref = users_db.collection('users').document(uid).collection('annotations')

        results = []
        for doc in annotations_ref.stream():
            data = doc.to_dict()
            # Decrypt content before searching
            decrypted_content = _decrypt_text(data.get('content', ''), uid)
            content_lower = decrypted_content.lower()

            # Text search
            if query_text and query_text in content_lower:
                match = True
            elif tag and tag in data.get('tags', []):
                match = True
            else:
                match = False

            if match:
                # Convert Firestore timestamp to serializable format
                created_at = data.get('createdAt')
                if created_at and hasattr(created_at, 'timestamp'):
                    created_at = {'seconds': int(created_at.timestamp())}

                results.append({
                    'id': doc.id,
                    'surah': data.get('surah'),
                    'verse': data.get('verse'),
                    'verseRef': f"{data.get('surah')}:{data.get('verse')}",
                    'type': data.get('type'),
                    'content': decrypted_content,
                    'tags': data.get('tags', []),
                    'createdAt': created_at
                })

        return jsonify({'results': results, 'count': len(results)}), 200

    except Exception as e:
        print(f"ERROR in /annotations/search: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/annotations/tags", methods=["GET"])
@firebase_auth_required
def get_all_tags():
    """Get all unique tags used by user"""
    try:
        uid = request.user['uid']

        annotations_ref = users_db.collection('users').document(uid).collection('annotations')

        tags = set()
        for doc in annotations_ref.stream():
            data = doc.to_dict()
            tags.update(data.get('tags', []))

        tag_list = sorted(list(tags))

        return jsonify({'tags': tag_list, 'count': len(tag_list)}), 200

    except Exception as e:
        print(f"ERROR in /annotations/tags: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/verse/<int:surah>/<int:verse>", methods=["GET"])
def get_specific_verse(surah, verse):
    """Direct endpoint for verse lookup"""
    try:
        is_valid, msg = validate_verse_reference(surah, verse)
        if not is_valid:
            return jsonify({"error": "Invalid verse reference", "message": msg}), 400

        verse_data = get_verse_from_firestore(surah, verse)
        if verse_data:
            return jsonify(verse_data)
        else:
            return jsonify({'error': f'Verse {surah}:{verse} not found'}), 404
    except Exception as e:
        print(f"Error in verse lookup: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# NEW: METADATA ENDPOINTS
# ============================================================================
@app.route("/metadata-types", methods=["GET"])
def get_metadata_types():
    """
    Return available metadata types and example queries.
    Helps users understand what they can ask for.
    """
    return jsonify({
        "metadata_types": {
            "hadith": {
                "field": "hadith_references",
                "description": "Prophetic traditions and hadith citations",
                "example_queries": [
                    "hadith in 2:255",
                    "show me narrations for 16:91",
                    "what did the prophet say about 3:34",
                    "prophetic traditions in verse 2:180"
                ]
            },
            "scholar_citations": {
                "field": "scholar_citations",
                "description": "Classical scholar opinions and citations",
                "example_queries": [
                    "scholars cited for 3:34",
                    "who mentioned 2:255",
                    "scholar opinions on 16:91",
                    "what did mujahid say about 2:137",
                    "commentator views on 3:34"
                ]
            },
            "phrase_analysis": {
                "field": "phrase_analysis",
                "description": "Word-by-word and phrase-by-phrase breakdown",
                "example_queries": [
                    "phrase analysis of 2:255",
                    "word breakdown for 3:34",
                    "what does each phrase mean in 16:91",
                    "phrase-by-phrase explanation of 2:180"
                ]
            },
            "topics": {
                "field": "topics",
                "description": "Main themes and subjects discussed",
                "example_queries": [
                    "topics in 2:255",
                    "what themes are covered in 16:91",
                    "main points of 3:34",
                    "subjects discussed in 2:180"
                ]
            },
            "cross_references": {
                "field": "cross_references",
                "description": "Related verses and connections",
                "example_queries": [
                    "related verses to 2:255",
                    "similar verses like 3:34",
                    "cross references for 16:91",
                    "other verses about same topic as 2:180"
                ]
            },
            "historical_context": {
                "field": "historical_context",
                "description": "Historical background and revelation circumstances",
                "example_queries": [
                    "historical context of 16:91",
                    "when was 2:255 revealed",
                    "background of 3:34",
                    "why was 2:180 revealed",
                    "occasion of revelation for 16:91"
                ]
            },
            "linguistic_analysis": {
                "field": "linguistic_analysis",
                "description": "Arabic grammar, roots, and linguistic structure",
                "example_queries": [
                    "linguistic analysis of 2:140",
                    "arabic grammar in 3:34",
                    "root words in 2:255",
                    "etymology of terms in 16:91"
                ]
            },
            "legal_rulings": {
                "field": "legal_rulings",
                "description": "Islamic jurisprudence and legal implications",
                "example_queries": [
                    "legal rulings in 2:180",
                    "fiqh of 3:34",
                    "what is halal/haram in 16:91",
                    "jurisprudence related to 2:255"
                ]
            }
        },
        "general_tips": [
            "You can use natural language - we'll understand variations",
            "Combine verse reference with metadata type: 'hadith in 2:255'",
            "Use plural or singular forms - both work",
            "Try synonyms - 'scholars cited', 'scholars mentioned', 'who said' all work",
            "For all metadata: 'everything about 2:255' or just '2:255'"
        ]
    }), 200

@app.route("/metadata/<int:surah>/<int:verse>", methods=["GET"])
def get_verse_metadata_endpoint(surah, verse):
    """
    Direct metadata endpoint - returns structured data instantly.

    Query params:
    - type: hadith | scholar_citations | phrase_analysis | topics |
            cross_references | historical_context | linguistic_analysis |
            legal_rulings | all (default: all)
    - source: ibn-kathir | al-qurtubi (default: both)

    Examples:
    - /metadata/2/255?type=hadith
    - /metadata/16/91?type=historical_context&source=ibn-kathir
    - /metadata/2/137?type=linguistic_analysis
    """
    try:
        # Validate verse reference
        is_valid, msg = validate_verse_reference(surah, verse)
        if not is_valid:
            return jsonify({"error": msg}), 400

        # Get query params
        metadata_type = request.args.get('type', 'all')
        source_pref = request.args.get('source', None)

        # Validate metadata type
        valid_types = ['hadith', 'scholar_citations', 'phrase_analysis', 'topics',
                       'cross_references', 'historical_context', 'linguistic_analysis',
                       'legal_rulings', 'all']
        if metadata_type not in valid_types:
            return jsonify({"error": f"Invalid type. Must be one of: {', '.join(valid_types)}"}), 400

        # Direct lookup
        verse_metadata_list = get_verse_metadata_direct(surah, verse, source_pref)

        if not verse_metadata_list:
            return jsonify({
                'error': f'Verse {surah}:{verse} not found in tafsir sources'
            }), 404

        # Format response
        response = format_metadata_response((surah, verse), metadata_type, verse_metadata_list)

        return jsonify(response), 200

    except Exception as e:
        print(f"Error in metadata lookup: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# REPLACED: ENHANCED /tafsir ENDPOINT WITH HYBRID ROUTING
# ============================================================================
@app.route("/tafsir", methods=["POST"])
@firebase_auth_required
@handle_errors
def tafsir_handler_enhanced():
    """
    HYBRID tafsir endpoint with 3-tier intelligent routing + approach-based customization:

    APPROACHES (Simplified):
    - tafsir: Classical verse-by-verse commentary (default)
    - explore/semantic: Themes, events, and concepts (merged historical + thematic)
      * Frontend sends 'explore', backend maps to 'semantic' internally
      * Legacy 'historical' or 'thematic' also map to 'semantic'

    ROUTES:
    1. METADATA QUERIES (e.g., "hadith in 2:255")
       - Direct lookup (~50ms)
       - AI formats response with persona (1 LLM call)
       - Total: ~1-2s, 50% cheaper than full RAG

    2. DIRECT VERSE QUERIES (e.g., "2:255", "ayat al kursi")
       - Direct lookup (~50ms)
       - AI formats tafsir with persona (1 LLM call)
       - Total: ~1-2s, 50% cheaper than full RAG

    3. SEMANTIC QUERIES (e.g., "patience", "Battle of Badr", "migration to Madinah")
       - RAG pipeline (NO expansion for semantic to avoid garbage):
         * Vector search (30 neighbors, 15 chunks)
         * Context building
         * AI generation (1 LLM call)
       - Total: ~2-3s, 1 LLM call (faster without expansion!)

    Routes 1 & 2 skip expensive RAG but keep AI quality & persona adaptation!
    """
    try:
        # Initialize performance tracking
        perf_start = time.time()
        perf_metrics = {
            'total_start': perf_start,
            'stages': {},
            'route': None,
            'approach': None,
            'chunks_retrieved': 0,
            'windows_processed': 0,
            'llm_calls': 0
        }

        # Request parsing
        stage_start = time.time()
        data = request.get_json()
        query = data.get('query', '').strip()
        approach = data.get('approach', 'tafsir').strip()  # NEW: Get approach parameter
        user_id = request.user.get('uid')
        perf_metrics['stages']['request_parsing'] = (time.time() - stage_start) * 1000

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        # Input validation: cap query length to prevent abuse
        if len(query) > 500:
            return jsonify({'error': 'Query too long. Please keep your query under 500 characters.'}), 400

        # Normalize approach — all queries route through direct verse lookup
        if approach != 'tafsir':
            approach = 'tafsir'

        perf_metrics['approach'] = approach

        # TAFSIR MODE VALIDATION - Help user format query correctly
        if approach == 'tafsir':
            verse_ref = extract_verse_reference_enhanced(query)
            if not verse_ref:
                # Try to help user fix their query with fuzzy matching
                query_lower = query.lower()
                has_number = bool(re.search(r'\d+', query))

                # Extract potential surah name from query
                suggestions = []

                # Try fuzzy matching surah names
                query_words = query_lower.split()
                for word in query_words:
                    if len(word) > 3:  # Only check words longer than 3 chars
                        for surah_name, surah_num in SURAHS_BY_NAME.items():
                            # Simple similarity: check if word is similar to surah name
                            if word in surah_name or surah_name.replace('-', '') in word or word.replace('-', '') in surah_name:
                                # Extract verse number if present
                                verse_match = re.search(r'\d+', query)
                                if verse_match:
                                    verse_num = verse_match.group()
                                    suggestions.append(f"{surah_num}:{verse_num}")
                                    suggestions.append(f"Surah {QURAN_METADATA[surah_num]['name']} verse {verse_num}")
                                break

                # Remove duplicates while preserving order
                suggestions = list(dict.fromkeys(suggestions[:4]))  # Limit to 4 suggestions

                # Check if this looks like a full surah query (e.g., "Surah 67" without verse)
                surah_only_match = re.match(r'^(?:surah\s+)?(\d{1,3})$', query.strip().lower())
                if surah_only_match or re.match(r'^surah\s+\d{1,3}$', query.strip().lower()):
                    help_message = '📚 Full surah queries are not currently supported.'
                    help_text = 'Please specify a verse or verse range (max 5 verses):\n• Single verse: "67:1"\n• Verse range: "67:1-5"\n• Analysis: "historical context of 67:1"'
                    example_suggestions = [
                        '67:1 (First verse)',
                        '67:1-5 (First 5 verses)',
                        '67:15-24 (Middle section)',
                        'linguistic analysis of 67:1'
                    ] if not suggestions else suggestions
                else:
                    help_message = '🤔 I couldn\'t find that verse. Let me help you format it correctly.'
                    help_text = 'Try one of these formats:\n• Numeric: "2:255"\n• Named: "Surah Al-Baqarah verse 255"\n• Range: "2:255-257" (max 5 verses)\n• Analysis: "historical context of 2:255"'
                    example_suggestions = [
                        '2:255 (Ayatul Kursi)',
                        'Surah Al-Fatihah verse 1',
                        '3:190-194',
                        'linguistic analysis of 2:255'
                    ] if not suggestions else suggestions

                response_data = {
                    'needs_clarification': True,
                    'original_query': query,
                    'message': help_message,
                    'suggestions': example_suggestions,
                    'help_text': help_text
                }

                return jsonify(response_data), 200  # Return 200, not error

        # VERSE RANGE VALIDATION - Block overly large ranges
        verse_range = extract_verse_range(query)
        if verse_range:
            surah, start_verse, end_verse = verse_range
            verse_count = end_verse - start_verse + 1

            # Dynamic budget enforcement — prevent oversized prompts
            from services.token_budget_service import compute_max_end_verse
            from config.token_budget import ABSOLUTE_MAX_VERSES

            # Hard cap from budget config (safety net)
            if verse_count > ABSOLUTE_MAX_VERSES:
                return jsonify({
                    'error': 'verse_range_too_large',
                    'message': f'Please narrow your range to {ABSOLUTE_MAX_VERSES} verses or less.\n\nYou requested {verse_count} verses ({surah}:{start_verse}-{end_verse}).',
                    'requested_verses': verse_count,
                    'max_verses': ABSOLUTE_MAX_VERSES,
                    'suggestions': [
                        f'{surah}:{start_verse}-{min(start_verse + ABSOLUTE_MAX_VERSES - 1, end_verse)}'
                    ]
                }), 400
            surah_max = QURAN_METADATA.get(surah, {}).get("verses", 0)
            if surah_max:
                budget_max_end, _meta = compute_max_end_verse(surah, start_verse, surah_max)
                if end_verse > budget_max_end:
                    safe_count = budget_max_end - start_verse + 1
                    return jsonify({
                        'error': 'verse_range_too_large',
                        'message': f'The verses {surah}:{start_verse}-{end_verse} contain extensive commentary that exceeds response limits.\n\nPlease narrow your range to {safe_count} verse{"s" if safe_count != 1 else ""} or fewer from this starting point.\n\nSuggested range:\n- {surah}:{start_verse}-{budget_max_end}',
                        'requested_verses': verse_count,
                        'max_verses': safe_count,
                        'suggestions': [
                            f'{surah}:{start_verse}-{budget_max_end}'
                        ]
                    }), 400

        # Rate limiting
        if is_rate_limited(user_id):
            resp = jsonify({'error': 'You have reached your query limit. Please wait a moment before trying again.'})
            resp.headers['Retry-After'] = '60'
            return resp, 429

        # Analytics
        ANALYTICS[query] += 1

        # Get user profile for caching
        stage_start = time.time()
        user_profile = get_user_profile(user_id)
        perf_metrics['stages']['user_profile'] = (time.time() - stage_start) * 1000

        # Check cache BEFORE any processing (applies to ALL routes)
        stage_start = time.time()

        # For tafsir queries with verse references, check Firestore cache first
        if approach == 'tafsir' and extract_verse_reference_enhanced(query):
            firestore_cached = get_cached_tafsir_response(query, user_profile, approach)
            if firestore_cached:
                perf_metrics['stages']['cache_check'] = (time.time() - stage_start) * 1000
                print(f"💾 FIRESTORE cache hit for tafsir query")
                print(f"   ⏱️  PERFORMANCE: Firestore cache hit in {perf_metrics['stages']['cache_check']:.0f}ms")
                # Apply sanitization to cached responses (ensures line breaks in headings)
                firestore_cached = filter_unavailable_sources(firestore_cached)
                return jsonify(firestore_cached), 200

        # For semantic/explore queries, also check Firestore cache
        elif approach == 'semantic':  # Remember: explore was normalized to semantic
            firestore_cached = get_cached_tafsir_response(query, user_profile, approach)
            if firestore_cached:
                perf_metrics['stages']['cache_check'] = (time.time() - stage_start) * 1000
                print(f"💾 FIRESTORE cache hit for explore/semantic query")
                print(f"   ⏱️  PERFORMANCE: Firestore cache hit in {perf_metrics['stages']['cache_check']:.0f}ms")
                # Apply sanitization to cached responses (ensures line breaks in headings)
                firestore_cached = filter_unavailable_sources(firestore_cached)
                return jsonify(firestore_cached), 200

        # Check in-memory cache as fallback
        cache_key = get_cache_key(query, user_profile, approach)
        with cache_lock:
            if cache_key in RESPONSE_CACHE:
                perf_metrics['stages']['cache_check'] = (time.time() - stage_start) * 1000
                print(f"💾 Memory cache hit for query (approach: {approach})")
                print(f"   ⏱️  PERFORMANCE: Memory cache hit in {perf_metrics['stages']['cache_check']:.0f}ms")
                # Apply sanitization to cached responses (ensures line breaks in headings)
                cached_response = filter_unavailable_sources(RESPONSE_CACHE[cache_key].copy())
                return jsonify(cached_response), 200
        perf_metrics['stages']['cache_check'] = (time.time() - stage_start) * 1000

        print(f"[TAFSIR] query={query} approach={approach}")

        # CLASSIFICATION
        classification = classify_query_enhanced(query)
        verse_ref = classification['verse_ref']
        confidence = classification['confidence']

        if verse_ref:
            print(f"🎯 Verse: {verse_ref[0]}:{verse_ref[1]} (confidence: {confidence:.0%})")
        verse_range = extract_verse_range(query)
        if verse_range:
            print(f"   📖 Verse Range: {verse_range[0]}:{verse_range[1]}-{verse_range[2]}")

        # ===================================================================
        # DIRECT VERSE QUERY (Direct lookup → AI formatting)
        # ===================================================================
        if not verse_ref:
            return jsonify({"error": "No verse reference found in query"}), 400

        # Check if query contains a verse range
        verse_range = extract_verse_range(query)
        if verse_range:
            surah, start_verse, end_verse = verse_range
            verse = start_verse
        else:
            surah, verse = verse_ref
            start_verse = verse
            end_verse = verse

        # Validate verse range against surah limits
        if surah in QURAN_METADATA:
            max_verse = QURAN_METADATA[surah]["verses"]
            if end_verse > max_verse:
                print(f"⚠️  Verse range {surah}:{start_verse}-{end_verse} exceeds surah limit ({max_verse} verses)")
                end_verse = max_verse
            if start_verse > max_verse:
                return jsonify({
                    "error": f"Invalid verse reference: Surah {surah} only has {max_verse} verses"
                }), 400

        # Get verse text(s) from Firestore
        if start_verse != end_verse:
            verses_data_list = get_verses_range_from_firestore(surah, start_verse, end_verse)
            verse_data = verses_data_list[0] if verses_data_list else None
            verses_for_ai = verses_data_list
        else:
            verses_data_list = None
            verse_data = get_verse_from_firestore(surah, start_verse)
            verses_for_ai = verse_data

        if not verse_data:
            return jsonify({"error": f"Verse {surah}:{start_verse} not found"}), 404

        print(f"✅ Firestore: {verse_data.get('surah_number')}:{verse_data.get('verse_number')} ({verse_data.get('surah_name')})")

        # Get metadata via direct lookup (with range support)
        verse_metadata_list = get_verse_metadata_direct(surah, start_verse, end_verse=end_verse if start_verse != end_verse else None)

        # Build context from direct lookup
        context_by_source = {}

        if not verse_metadata_list:
            print(f"⚠️  No tafsir found for {surah}:{start_verse}" + (f"-{end_verse}" if start_verse != end_verse else ""))

        if verse_metadata_list:
            for item in verse_metadata_list:
                source_name = item['source']

                # Handle verse ranges (new structure) or single verse (backwards compatible)
                verses_data = item.get('verses', [])
                if not verses_data and item.get('metadata'):
                    verses_data = [{'verse_number': start_verse, 'metadata': item['metadata']}]

                context_parts = []

                for verse_info in verses_data:
                    metadata = verse_info['metadata']
                    verse_num = verse_info.get('verse_number', start_verse)

                    if len(verses_data) > 1:
                        context_parts.append(f"\n**Verse {verse_num}:**\n")

                    # Topics (Ibn Kathir style)
                    if metadata.get('topics'):
                        for topic in metadata['topics']:
                            if isinstance(topic, dict):
                                if topic.get('topic_header'):
                                    context_parts.append(f"**{topic['topic_header']}**")
                                if topic.get('commentary'):
                                    context_parts.append(topic['commentary'])

                                if topic.get('phrase_analysis'):
                                    for phrase in topic['phrase_analysis']:
                                        if isinstance(phrase, dict):
                                            if phrase.get('phrase'):
                                                context_parts.append(f"Phrase: {phrase['phrase']}")
                                            if phrase.get('analysis'):
                                                context_parts.append(f"Analysis: {phrase['analysis']}")

                                if topic.get('hadith_references'):
                                    context_parts.append(f"Hadith: {topic['hadith_references']}")

                    # Commentary (al-Qurtubi style)
                    elif metadata.get('commentary'):
                        context_parts.append(metadata['commentary'])

                        if metadata.get('phrase_analysis'):
                            for phrase in metadata['phrase_analysis']:
                                if isinstance(phrase, str):
                                    context_parts.append(phrase)

                        if metadata.get('scholar_citations'):
                            for citation in metadata['scholar_citations']:
                                if isinstance(citation, str):
                                    context_parts.append(citation)

                context_by_source[source_name] = ["\n\n".join(context_parts)] if context_parts else []

        # Get user profile for persona
        user_profile = get_user_profile(user_id)

        # Build prompt for AI formatting
        arabic_text = get_arabic_text_from_verse_data(verse_data)

        cross_refs = []
        if verse_metadata_list:
            first_item = verse_metadata_list[0]
            if first_item.get('verses'):
                cross_refs = first_item['verses'][0]['metadata'].get('cross_references', [])
            elif first_item.get('metadata'):
                cross_refs = first_item['metadata'].get('cross_references', [])

        scholarly_ctx, scholarly_badges, scholarly_pipeline = _get_scholarly_context_two_stage(query, verses_for_ai, context_by_source)

        # Compute dynamic verse limit from token budget
        from services.token_budget_service import compute_max_end_verse as _compute_max_end
        surah_max_v = QURAN_METADATA.get(surah, {}).get("verses", 286)
        dynamic_max_end, _ = _compute_max_end(surah, start_verse, surah_max_v)
        dynamic_verse_limit = dynamic_max_end - start_verse + 1
        print(f"   📊 Dynamic verse limit for {surah}:{start_verse}: {dynamic_verse_limit} verses")

        prompt = build_enhanced_prompt(query, context_by_source, user_profile,
                                     arabic_text, cross_refs, 'direct_verse', verses_for_ai, approach, scholarly_ctx,
                                     verse_limit=dynamic_verse_limit)

        if isinstance(verses_for_ai, list):
            print(f"🔍 Calling Gemini with {len(verses_for_ai)} verses: {verses_for_ai[0].get('surah_number')}:{verses_for_ai[0].get('verse_number')}-{verses_for_ai[-1].get('verse_number')}")
        else:
            print(f"🔍 Calling Gemini with single verse: {verses_for_ai.get('surah_number')}:{verses_for_ai.get('verse_number')}")

        # Get auth token
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        token = credentials.token

        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generation_config": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 65536
            },
        }

        # Retry with exponential backoff
        max_retries = 4

        for attempt in range(max_retries):
            retry_delay = 2 ** (attempt + 1)
            try:
                response = requests.post(
                    VERTEX_ENDPOINT,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=body,
                    timeout=120
                )
                response.raise_for_status()
                break
            except requests.Timeout:
                if attempt == max_retries - 1:
                    return jsonify({
                        "error": "AI service timeout",
                        "retry": True,
                        "error_type": "timeout"
                    }), 503
                print(f"⚠️ Retry {attempt + 1}/{max_retries} in {retry_delay}s...")
                time.sleep(retry_delay)
            except requests.HTTPError as e:
                status_code = response.status_code if response else 500
                if status_code == 429:
                    if attempt == max_retries - 1:
                        return jsonify({
                            "error": "AI service is busy. Please wait a moment and try again.",
                            "retry": True,
                            "error_type": "rate_limit",
                            "retry_after": 30
                        }), 429
                    print(f"⚠️ Rate limited (429), retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                if status_code == 503:
                    if attempt == max_retries - 1:
                        raise
                    print(f"⚠️ Service unavailable, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                raise

        # Parse response
        raw_response = response.json()

        finish_reason = safe_get_nested(raw_response, "candidates", 0, "finishReason")
        if finish_reason and finish_reason not in ("STOP", "MAX_TOKENS"):
            print(f"⚠️ Gemini finishReason: {finish_reason}")
            if finish_reason == "SAFETY":
                return jsonify({
                    "error": "The AI could not generate a response for this query. Please try rephrasing.",
                    "error_type": "content_blocked"
                }), 400

        generated_text = safe_get_nested(raw_response, "candidates", 0, "content", "parts", 0, "text")

        if generated_text:
            final_json = extract_json_from_response(generated_text)

            if not final_json:
                print(f"❌ Failed to extract JSON from Gemini response")
                return jsonify({
                    "error": "AI returned malformed response",
                    "error_type": "json_parse_error"
                }), 500

            final_json["query_type"] = "direct_verse"
            final_json["verse_reference"] = f"{surah}:{verse}"

            final_json = filter_unavailable_sources(final_json)

            final_json["scholarly_sources"] = scholarly_badges
            final_json["_scholarly_pipeline"] = scholarly_pipeline

            final_json = keep_requested_verses_primary(
                final_json,
                verses_for_ai,
                requested_verses=[(surah, v) for v in range(start_verse, end_verse + 1)]
            )

            persona_name = user_profile.get('persona', 'practicing_muslim')
            requested_range = [(surah, v) for v in range(start_verse, end_verse + 1)]
            final_json, trimmed, original_count, final_count = enforce_persona_verse_limit(
                final_json,
                persona_name,
                requested_verses=requested_range,
                dynamic_limit=dynamic_verse_limit
            )
            if trimmed:
                print(f"   ℹ️  Trimmed verses to {final_count}/{original_count} for persona {persona_name}")

            verse_count = len(final_json.get('verses', []))
            if verse_count > dynamic_verse_limit:
                print(f"   ⚠️  VERSE LIMIT EXCEEDED: {verse_count}/{dynamic_verse_limit}")
            else:
                print(f"   ✅ Verse count: {verse_count}/{dynamic_verse_limit}")

            # Cache the response
            with cache_lock:
                RESPONSE_CACHE[cache_key] = final_json
                if len(RESPONSE_CACHE) > 1000:
                    keys_to_remove = list(RESPONSE_CACHE.keys())[:200]
                    for key in keys_to_remove:
                        RESPONSE_CACHE.pop(key, None)

            if approach == 'tafsir':
                store_tafsir_cache(query, user_profile, final_json, approach)

            if user_id:
                _track_explored_verse(user_id, surah, start_verse, end_verse)
                _check_and_award_badges(user_id)
            final_json["recommendations"] = _generate_recommendations(surah, start_verse, final_json, user_id)

            print(f"✅ Formatted by AI from {len(verse_metadata_list)} source(s)")
            return jsonify(final_json), 200
        else:
            response = build_direct_verse_response(verse_data, verse_metadata_list)
            return jsonify(response), 200

    except requests.exceptions.Timeout:
        return jsonify({"error": "AI service timed out"}), 504
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500


@app.route("/health", methods=["GET"])
def health_check_enhanced():
    """Health check with system status"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "metadata_entries": len(VERSE_METADATA),
        "cache_size": len(RESPONSE_CACHE),
        "query_routes": {
            "direct_verse": {
                "description": "Direct lookup + AI formatting",
                "example": "2:255",
                "llm_calls": 1
            }
        },
        "personas_available": list(PERSONAS.keys()),
        "source_coverage": {
            "Ibn Kathir": "Complete Quran (114 Surahs)",
            "al-Qurtubi": "Surahs 1-4 (up to 4:22)"
        }
    }), 200



@app.route("/debug/range-map", methods=["GET"])
def debug_range_map():
    """View the static verse range map info and optionally re-export it."""
    from services.token_budget_service import get_range_map_info, export_range_map
    try:
        info = get_range_map_info()
        action = request.args.get("action")
        if action == "export":
            path = export_range_map()
            info["exported_to"] = path
        return jsonify(info), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/debug/test/<path:query>", methods=["GET"])
def debug_query(query):
    """
    REAL EXECUTION with step-by-step logging
    Actually runs the query through the full processing pipeline
    """
    import urllib.parse
    import time
    query = urllib.parse.unquote(query)

    approach = "tafsir"  # Default approach

    trace = {
        "timestamp": datetime.now().isoformat(),
        "original_query": query,
        "approach": approach,
        "processing_steps": [],
        "timings": {},
        "actual_execution": True
    }

    step_timings = {}

    def log_step(step_name, details=None):
        """Helper to log each processing step with timing"""
        step_start = time.time()
        step = {
            "step": step_name,
            "timestamp": datetime.now().isoformat()
        }
        if details:
            step.update(details)
        trace["processing_steps"].append(step)
        return step

    def log_timing(step_name, duration):
        """Log timing for a step"""
        step_timings[step_name] = f"{duration:.3f}s"

    try:
        overall_start = time.time()

        # STEP 1: Initial Setup
        step_start = time.time()
        log_step("1. Initial Setup", {
            "query": query,
            "approach": approach,
            "user_id": "debug_user"
        })
        log_timing("1. Initial Setup", time.time() - step_start)

        # STEP 2: Cache Check
        step_start = time.time()
        user_profile = {"persona": "practicing_muslim"}  # Default profile
        cache_key = get_cache_key(query, user_profile, approach)
        cache_hit = cache_key in RESPONSE_CACHE

        log_step("2. Cache Check", {
            "cache_key_hash": hashlib.md5(cache_key.encode()).hexdigest()[:16],
            "cache_hit": cache_hit,
            "cache_size": len(RESPONSE_CACHE)
        })
        log_timing("2. Cache Check", time.time() - step_start)

        if cache_hit:
            log_step("CACHE HIT - Returning cached response", {
                "note": "No further processing needed"
            })
            trace["timings"] = step_timings
            trace["timings"]["total"] = f"{time.time() - overall_start:.3f}s"
            trace["response"] = RESPONSE_CACHE[cache_key]
            return jsonify(trace), 200

        # STEP 3: Query Classification
        step_start = time.time()
        classification = classify_query_enhanced(query)
        verse_ref = classification['verse_ref']

        log_step("3. Query Classification", {
            "verse_ref": f"{verse_ref[0]}:{verse_ref[1]}" if verse_ref else None,
            "confidence": f"{classification['confidence']:.0%}"
        })
        log_timing("3. Query Classification", time.time() - step_start)

        if not verse_ref:
            trace["error"] = "No verse reference found"
            return jsonify(trace), 400

        # DIRECT VERSE QUERY
        surah, verse = verse_ref
        verse_range = extract_verse_range(query)

        step_start = time.time()
        is_valid, msg = validate_verse_reference(surah, verse)
        log_step("4. Verse Validation", {"surah": surah, "verse": verse, "is_valid": is_valid})
        log_timing("4. Verse Validation", time.time() - step_start)

        if not is_valid:
            trace["error"] = msg
            return jsonify(trace), 400

        # Get tafsir
        step_start = time.time()
        if verse_range and verse_range[1] != verse_range[2]:
            start_verse, end_verse = verse_range[1], verse_range[2]
            verse_metadata_list = get_verse_metadata_direct(surah, start_verse, end_verse)
        else:
            verse_metadata_list = get_verse_metadata_direct(surah, verse)
        log_timing("5. Fetch Tafsir", time.time() - step_start)

        if not verse_metadata_list:
            trace["error"] = f"No tafsir found for {surah}:{verse}"
            trace["timings"] = step_timings
            return jsonify(trace), 404

        # Build context
        step_start = time.time()
        context_by_source = {}
        for item in verse_metadata_list:
            source_name = item['source']
            metadata = item['metadata']
            if metadata.get('commentary'):
                context_by_source[source_name] = [metadata['commentary']]
        log_timing("6. Build Context", time.time() - step_start)

        # Fetch verse from Firestore
        step_start = time.time()
        verse_data = get_verse_from_firestore(surah, verse)
        log_timing("7. Fetch Verse", time.time() - step_start)

        # Build prompt
        step_start = time.time()
        arabic_text = get_arabic_text_from_verse_data(verse_data) if verse_data else None
        scholarly_ctx, scholarly_badges, scholarly_pipeline = _get_scholarly_context_two_stage(query, verse_data, context_by_source)
        prompt = build_enhanced_prompt(query, context_by_source, user_profile,
                                     arabic_text, None, 'direct_verse', verse_data, approach, scholarly_ctx)

        print("🔵 === COMPLETE PROMPT TO GEMINI ===")
        print(prompt)
        print("🔵 === END COMPLETE PROMPT ===")

        log_step("8. Build AI Prompt", {"prompt_length": len(prompt), "num_sources": len(context_by_source)})
        log_timing("8. Build Prompt", time.time() - step_start)

        # Call Gemini
        step_start = time.time()
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        credentials.refresh(google.auth.transport.requests.Request())

        gemini_url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/us-central1/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generation_config": {"temperature": 0.3, "maxOutputTokens": 65536},
        }

        response = requests.post(
            gemini_url,
            headers={"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"},
            json=body,
            timeout=120
        )

        gemini_duration = time.time() - step_start
        log_step("9. Gemini Response", {"status_code": response.status_code, "duration": f"{gemini_duration:.3f}s"})
        log_timing("9. Gemini API Call", gemini_duration)

        if response.ok:
            result = response.json()
            generated_text = result['candidates'][0]['content']['parts'][0]['text']

            print("🟢 === COMPLETE GEMINI RESPONSE ===")
            print(generated_text)
            print("🟢 === END COMPLETE RESPONSE ===")

            final_json = extract_json_from_response(generated_text)

            if not final_json or final_json.get('metadata', {}).get('extraction_error'):
                trace["error"] = "Failed to parse AI response"
                return jsonify(trace), 500

            final_json["sources"] = list(context_by_source.keys())
            final_json["scholarly_sources"] = scholarly_badges
            final_json["_scholarly_pipeline"] = scholarly_pipeline

            with cache_lock:
                RESPONSE_CACHE[cache_key] = final_json

            trace["response"] = final_json
            trace["timings"] = step_timings
            trace["timings"]["total"] = f"{time.time() - overall_start:.3f}s"
            return jsonify(trace), 200
        else:
            trace["error"] = f"Gemini API error: {response.status_code}"
            return jsonify(trace), 500

    except Exception as e:
        log_step("CRITICAL ERROR", {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        })
        trace["error"] = str(e)
        trace["timings"] = step_timings
        return jsonify(trace), 500

@app.route("/debug/verse-metadata/<surah>/<verse>", methods=["GET"])
def check_verse_metadata(surah, verse):
    """
    Check what metadata exists for a specific verse
    Usage: /debug/verse-metadata/2/183
    """
    try:
        surah = int(surah)
        verse = int(verse)

        result = {
            "query": f"{surah}:{verse}",
            "metadata_store_stats": {
                "total_verses": len(VERSE_METADATA),
                "total_chunks": len(TAFSIR_CHUNKS)
            },
            "lookups": {}
        }

        # Check both sources
        for source in ['ibn-kathir', 'al-qurtubi']:
            chunk_id = f"{source}:{surah}:{verse}"

            # Check VERSE_METADATA
            metadata = VERSE_METADATA.get(chunk_id)

            # Check TAFSIR_CHUNKS
            chunk_text = TAFSIR_CHUNKS.get(chunk_id)

            result["lookups"][source] = {
                "chunk_id": chunk_id,
                "in_verse_metadata": metadata is not None,
                "in_tafsir_chunks": chunk_text is not None,
                "metadata_keys": list(metadata.keys()) if metadata else None,
                "chunk_text_length": len(chunk_text) if chunk_text else 0,
                "has_commentary": metadata.get('commentary') is not None if metadata else False,
                "commentary_length": len(metadata.get('commentary') or '') if metadata else 0
            }

        # Sample surrounding verses
        result["surrounding_verses"] = {}
        for v in range(max(1, verse - 2), verse + 3):
            ibn_id = f"ibn-kathir:{surah}:{v}"
            qur_id = f"al-qurtubi:{surah}:{v}"
            result["surrounding_verses"][f"{surah}:{v}"] = {
                "ibn-kathir": ibn_id in VERSE_METADATA,
                "al-qurtubi": qur_id in VERSE_METADATA
            }

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }), 500

# ============================================================================
# SHAREABLE LINKS
# ============================================================================

@app.route('/share', methods=['POST'])
def create_share():
    """
    Create a shareable link for a tafsir response.
    Request body: {
        "query": str,
        "approach": str,
        "response": dict (the tafsir response data)
    }
    Returns: { "share_id": str, "share_url": str }
    """
    try:
        data = request.get_json()
        query = data.get('query', '')
        approach = data.get('approach', 'tafsir')
        response = data.get('response', {})

        if not query or not response:
            return jsonify({"error": "Query and response are required"}), 400

        # Generate a unique share ID using timestamp and hash
        timestamp = int(time.time() * 1000)
        content_hash = hashlib.sha256(f"{query}{json.dumps(response)}".encode()).hexdigest()[:8]
        share_id = f"{timestamp}_{content_hash}"

        # Create the shared content document
        share_doc = {
            "share_id": share_id,
            "query": query,
            "approach": approach,
            "response": response,
            "created_at": firestore.SERVER_TIMESTAMP,
            "view_count": 0
        }

        # Save to Firestore in quran_db (public collection)
        quran_db.collection('shared_content').document(share_id).set(share_doc)

        # Return the share ID and full URL
        share_url = f"/shared/{share_id}"

        return jsonify({
            "share_id": share_id,
            "share_url": share_url
        }), 201

    except Exception as e:
        print(f"Error creating share: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/share/<share_id>', methods=['GET'])
def get_shared_content(share_id):
    """
    Retrieve shared content by ID.
    Returns the original query, approach, and response data.
    """
    try:
        # Get the shared content from Firestore
        doc_ref = quran_db.collection('shared_content').document(share_id)
        doc = doc_ref.get()

        if not doc.exists:
            return jsonify({"error": "Shared content not found"}), 404

        share_data = doc.to_dict()

        # Increment view count
        doc_ref.update({"view_count": firestore.Increment(1)})

        # Return the shared content
        return jsonify({
            "query": share_data.get('query'),
            "approach": share_data.get('approach'),
            "response": share_data.get('response'),
            "created_at": share_data.get('created_at'),
            "view_count": share_data.get('view_count', 0) + 1
        }), 200

    except Exception as e:
        print(f"Error retrieving shared content: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ============================================================================
# MUSLIM NAME DICTIONARY
# ============================================================================

MUSLIM_NAMES = {
    "male": [
        {"name": "Muhammad", "arabic": "محمد", "meaning": "Praised, commendable", "origin": "Prophetic", "quranic": True, "reference": "47:2"},
        {"name": "Ahmad", "arabic": "أحمد", "meaning": "Most praised, most commendable", "origin": "Prophetic", "quranic": True, "reference": "61:6"},
        {"name": "Ibrahim", "arabic": "إبراهيم", "meaning": "Father of many nations", "origin": "Prophetic", "quranic": True, "reference": "2:124"},
        {"name": "Yusuf", "arabic": "يوسف", "meaning": "God increases, adds", "origin": "Prophetic", "quranic": True, "reference": "12:4"},
        {"name": "Adam", "arabic": "آدم", "meaning": "Made from earth, the first human", "origin": "Prophetic", "quranic": True, "reference": "2:31"},
        {"name": "Isa", "arabic": "عيسى", "meaning": "God is salvation", "origin": "Prophetic", "quranic": True, "reference": "3:45"},
        {"name": "Musa", "arabic": "موسى", "meaning": "Drawn from the water", "origin": "Prophetic", "quranic": True, "reference": "20:9"},
        {"name": "Nuh", "arabic": "نوح", "meaning": "Rest, comfort", "origin": "Prophetic", "quranic": True, "reference": "71:1"},
        {"name": "Dawud", "arabic": "داود", "meaning": "Beloved", "origin": "Prophetic", "quranic": True, "reference": "38:17"},
        {"name": "Sulayman", "arabic": "سليمان", "meaning": "Man of peace", "origin": "Prophetic", "quranic": True, "reference": "27:15"},
        {"name": "Ismail", "arabic": "إسماعيل", "meaning": "God hears", "origin": "Prophetic", "quranic": True, "reference": "2:125"},
        {"name": "Ishaq", "arabic": "إسحاق", "meaning": "He laughs, joy", "origin": "Prophetic", "quranic": True, "reference": "37:112"},
        {"name": "Yaqub", "arabic": "يعقوب", "meaning": "Supplanter, follower", "origin": "Prophetic", "quranic": True, "reference": "2:132"},
        {"name": "Ayyub", "arabic": "أيوب", "meaning": "The patient one, returning to God", "origin": "Prophetic", "quranic": True, "reference": "21:83"},
        {"name": "Yunus", "arabic": "يونس", "meaning": "Dove", "origin": "Prophetic", "quranic": True, "reference": "10:98"},
        {"name": "Idris", "arabic": "إدريس", "meaning": "Studious, learned", "origin": "Prophetic", "quranic": True, "reference": "19:56"},
        {"name": "Harun", "arabic": "هارون", "meaning": "Mountaineer, exalted", "origin": "Prophetic", "quranic": True, "reference": "20:30"},
        {"name": "Zakariya", "arabic": "زكريا", "meaning": "God remembers", "origin": "Prophetic", "quranic": True, "reference": "19:2"},
        {"name": "Yahya", "arabic": "يحيى", "meaning": "God gives life", "origin": "Prophetic", "quranic": True, "reference": "19:7"},
        {"name": "Ilyas", "arabic": "إلياس", "meaning": "The Lord is my God", "origin": "Prophetic", "quranic": True, "reference": "37:123"},
        {"name": "Omar", "arabic": "عمر", "meaning": "Long-lived, flourishing", "origin": "Companion", "quranic": False},
        {"name": "Ali", "arabic": "علي", "meaning": "Exalted, noble, sublime", "origin": "Companion", "quranic": False},
        {"name": "Uthman", "arabic": "عثمان", "meaning": "Young bustard (a bird), wise", "origin": "Companion", "quranic": False},
        {"name": "Abu Bakr", "arabic": "أبو بكر", "meaning": "Father of the young camel", "origin": "Companion", "quranic": False},
        {"name": "Khalid", "arabic": "خالد", "meaning": "Eternal, immortal", "origin": "Companion", "quranic": False},
        {"name": "Hamza", "arabic": "حمزة", "meaning": "Lion, strong, steadfast", "origin": "Companion", "quranic": False},
        {"name": "Bilal", "arabic": "بلال", "meaning": "Moisture, freshness, the caller to prayer", "origin": "Companion", "quranic": False},
        {"name": "Salman", "arabic": "سلمان", "meaning": "Safe, peaceful", "origin": "Companion", "quranic": False},
        {"name": "Zaid", "arabic": "زيد", "meaning": "Growth, abundance", "origin": "Companion", "quranic": True, "reference": "33:37"},
        {"name": "Talha", "arabic": "طلحة", "meaning": "A kind of tree, fruitful", "origin": "Companion", "quranic": False},
        {"name": "Imran", "arabic": "عمران", "meaning": "Prosperity, long-lived", "origin": "Quranic", "quranic": True, "reference": "3:33"},
        {"name": "Luqman", "arabic": "لقمان", "meaning": "Wise man", "origin": "Quranic", "quranic": True, "reference": "31:12"},
        {"name": "Dhul-Kifl", "arabic": "ذو الكفل", "meaning": "Possessor of the double portion", "origin": "Quranic", "quranic": True, "reference": "21:85"},
        {"name": "Rahman", "arabic": "رحمن", "meaning": "The Most Merciful (divine attribute)", "origin": "Divine Attribute", "quranic": True, "reference": "55:1"},
        {"name": "Rahim", "arabic": "رحيم", "meaning": "The Most Compassionate", "origin": "Divine Attribute", "quranic": True, "reference": "1:1"},
        {"name": "Kareem", "arabic": "كريم", "meaning": "Generous, noble", "origin": "Divine Attribute", "quranic": True, "reference": "82:6"},
        {"name": "Aziz", "arabic": "عزيز", "meaning": "Mighty, powerful, beloved", "origin": "Divine Attribute", "quranic": True, "reference": "59:23"},
        {"name": "Hakeem", "arabic": "حكيم", "meaning": "Wise, judicious", "origin": "Divine Attribute", "quranic": True, "reference": "2:32"},
        {"name": "Latif", "arabic": "لطيف", "meaning": "Gentle, subtle, kind", "origin": "Divine Attribute", "quranic": True, "reference": "6:103"},
        {"name": "Rashid", "arabic": "راشد", "meaning": "Rightly guided", "origin": "Arabic", "quranic": False},
        {"name": "Tariq", "arabic": "طارق", "meaning": "Morning star, he who knocks at the door", "origin": "Quranic", "quranic": True, "reference": "86:1"},
        {"name": "Faisal", "arabic": "فيصل", "meaning": "Decisive, resolute judge", "origin": "Arabic", "quranic": False},
        {"name": "Hassan", "arabic": "حسن", "meaning": "Beautiful, handsome, good", "origin": "Prophetic Family", "quranic": False},
        {"name": "Hussain", "arabic": "حسين", "meaning": "Beautiful, handsome (diminutive)", "origin": "Prophetic Family", "quranic": False},
        {"name": "Jamal", "arabic": "جمال", "meaning": "Beauty, grace", "origin": "Arabic", "quranic": False},
        {"name": "Samir", "arabic": "سمير", "meaning": "Entertaining companion, friend", "origin": "Arabic", "quranic": False},
        {"name": "Nasir", "arabic": "ناصر", "meaning": "Helper, supporter, protector", "origin": "Arabic", "quranic": False},
        {"name": "Mansur", "arabic": "منصور", "meaning": "Victorious, divinely aided", "origin": "Arabic", "quranic": False},
        {"name": "Saeed", "arabic": "سعيد", "meaning": "Happy, fortunate, blessed", "origin": "Quranic", "quranic": True, "reference": "11:108"},
        {"name": "Muadh", "arabic": "معاذ", "meaning": "Protected, sheltered by God", "origin": "Companion", "quranic": False},
        {"name": "Amir", "arabic": "أمير", "meaning": "Prince, commander, leader", "origin": "Arabic", "quranic": False},
        {"name": "Nabil", "arabic": "نبيل", "meaning": "Noble, distinguished", "origin": "Arabic", "quranic": False},
        {"name": "Rayan", "arabic": "ريان", "meaning": "Gate of Paradise for those who fast, lush", "origin": "Islamic", "quranic": False},
        {"name": "Zain", "arabic": "زين", "meaning": "Beauty, grace, adornment", "origin": "Arabic", "quranic": False},
        {"name": "Yaser", "arabic": "ياسر", "meaning": "Wealthy, prosperous, easy", "origin": "Companion", "quranic": False},
        {"name": "Sami", "arabic": "سامي", "meaning": "Elevated, sublime, exalted", "origin": "Arabic", "quranic": False},
        {"name": "Noor", "arabic": "نور", "meaning": "Light, radiance", "origin": "Quranic", "quranic": True, "reference": "24:35"},
        {"name": "Hadi", "arabic": "هادي", "meaning": "Guide, leader to righteousness", "origin": "Divine Attribute", "quranic": True, "reference": "22:54"},
        {"name": "Basim", "arabic": "باسم", "meaning": "Smiling, cheerful", "origin": "Arabic", "quranic": False},
        {"name": "Farid", "arabic": "فريد", "meaning": "Unique, precious, incomparable", "origin": "Arabic", "quranic": False},
        {"name": "Idrees", "arabic": "إدريس", "meaning": "Studious, interpreter", "origin": "Prophetic", "quranic": True, "reference": "19:56"},
        {"name": "Junaid", "arabic": "جنيد", "meaning": "Young warrior, soldier", "origin": "Arabic", "quranic": False},
        {"name": "Kamil", "arabic": "كامل", "meaning": "Perfect, complete", "origin": "Arabic", "quranic": False},
        {"name": "Majid", "arabic": "ماجد", "meaning": "Glorious, noble, magnificent", "origin": "Divine Attribute", "quranic": True, "reference": "85:15"},
        {"name": "Nasser", "arabic": "ناصر", "meaning": "Supporter, helper", "origin": "Arabic", "quranic": False},
        {"name": "Qasim", "arabic": "قاسم", "meaning": "Distributer, divider", "origin": "Prophetic Family", "quranic": False},
        {"name": "Rafi", "arabic": "رفيع", "meaning": "High, exalted, sublime", "origin": "Arabic", "quranic": False},
        {"name": "Sadiq", "arabic": "صادق", "meaning": "Truthful, honest, sincere", "origin": "Arabic", "quranic": False},
        {"name": "Taha", "arabic": "طه", "meaning": "Quranic letters opening Surah Taha", "origin": "Quranic", "quranic": True, "reference": "20:1"},
        {"name": "Yaseen", "arabic": "يس", "meaning": "Quranic letters, 'Heart of the Quran'", "origin": "Quranic", "quranic": True, "reference": "36:1"},
        {"name": "Waqar", "arabic": "وقار", "meaning": "Dignity, poise, self-respect", "origin": "Arabic", "quranic": False},
        {"name": "Usman", "arabic": "عثمان", "meaning": "The chosen one, wise", "origin": "Companion", "quranic": False},
        {"name": "Shakir", "arabic": "شاكر", "meaning": "Grateful, thankful", "origin": "Quranic", "quranic": True, "reference": "2:158"},
        {"name": "Rafiq", "arabic": "رفيق", "meaning": "Gentle companion, kind friend", "origin": "Arabic", "quranic": False},
        {"name": "Naeem", "arabic": "نعيم", "meaning": "Comfort, bliss, paradise", "origin": "Quranic", "quranic": True, "reference": "5:65"},
        {"name": "Mumin", "arabic": "مؤمن", "meaning": "Believer, faithful one", "origin": "Quranic", "quranic": True, "reference": "40:28"},
        {"name": "Labib", "arabic": "لبيب", "meaning": "Intelligent, sensible", "origin": "Arabic", "quranic": False},
        {"name": "Ihsan", "arabic": "إحسان", "meaning": "Excellence, perfection in worship", "origin": "Islamic", "quranic": False},
        {"name": "Ghazi", "arabic": "غازي", "meaning": "Conqueror, warrior", "origin": "Arabic", "quranic": False},
        {"name": "Furqan", "arabic": "فرقان", "meaning": "Criterion between right and wrong", "origin": "Quranic", "quranic": True, "reference": "25:1"},
        {"name": "Ehsan", "arabic": "احسان", "meaning": "Benevolence, charity, compassion", "origin": "Islamic", "quranic": False},
        {"name": "Danish", "arabic": "دانش", "meaning": "Knowledge, wisdom, learning", "origin": "Persian-Islamic", "quranic": False},
        {"name": "Burhan", "arabic": "برهان", "meaning": "Proof, evidence, clear argument", "origin": "Quranic", "quranic": True, "reference": "4:174"},
        {"name": "Asad", "arabic": "أسد", "meaning": "Lion, brave, courageous", "origin": "Arabic", "quranic": False},
        {"name": "Anas", "arabic": "أنس", "meaning": "Friendliness, affection, love", "origin": "Companion", "quranic": False},
        {"name": "Muaz", "arabic": "معاذ", "meaning": "Refuge, protected", "origin": "Companion", "quranic": False},
        {"name": "Mikail", "arabic": "ميكائيل", "meaning": "Angel Mikail, who is like God", "origin": "Angelic", "quranic": True, "reference": "2:98"},
        {"name": "Jibreel", "arabic": "جبريل", "meaning": "Angel Gabriel, strength of God", "origin": "Angelic", "quranic": True, "reference": "2:97"},
        {"name": "Sufyan", "arabic": "سفيان", "meaning": "Moving swiftly, lightning", "origin": "Companion", "quranic": False},
        {"name": "Marwan", "arabic": "مروان", "meaning": "A type of fragrant stone, solid", "origin": "Arabic", "quranic": False},
        {"name": "Hashim", "arabic": "هاشم", "meaning": "Crusher, generous provider", "origin": "Prophetic Ancestry", "quranic": False},
        {"name": "Abdullah", "arabic": "عبدالله", "meaning": "Servant of Allah", "origin": "Islamic", "quranic": True, "reference": "72:19"},
        {"name": "Abdulrahman", "arabic": "عبدالرحمن", "meaning": "Servant of the Most Merciful", "origin": "Islamic", "quranic": False},
        {"name": "Abdelkarim", "arabic": "عبدالكريم", "meaning": "Servant of the Most Generous", "origin": "Islamic", "quranic": False},
        {"name": "Tawfiq", "arabic": "توفيق", "meaning": "Divine guidance, success from God", "origin": "Arabic", "quranic": False},
        {"name": "Shafi", "arabic": "شافي", "meaning": "Healer, one who cures", "origin": "Arabic", "quranic": False},
        {"name": "Rayhan", "arabic": "ريحان", "meaning": "Sweet basil, fragrance of Paradise", "origin": "Quranic", "quranic": True, "reference": "55:12"},
        {"name": "Owais", "arabic": "أويس", "meaning": "Little wolf, gifted", "origin": "Historical", "quranic": False},
        {"name": "Muneeb", "arabic": "منيب", "meaning": "One who turns to God in repentance", "origin": "Quranic", "quranic": True, "reference": "50:33"},
    ],
    "female": [
        {"name": "Maryam", "arabic": "مريم", "meaning": "Beloved, star of the sea, exalted", "origin": "Quranic", "quranic": True, "reference": "3:36"},
        {"name": "Aisha", "arabic": "عائشة", "meaning": "Living, prosperous, alive", "origin": "Prophetic Family", "quranic": False},
        {"name": "Fatimah", "arabic": "فاطمة", "meaning": "One who abstains, weaned", "origin": "Prophetic Family", "quranic": False},
        {"name": "Khadijah", "arabic": "خديجة", "meaning": "Born prematurely, trustworthy", "origin": "Prophetic Family", "quranic": False},
        {"name": "Zainab", "arabic": "زينب", "meaning": "Fragrant flower, father's precious jewel", "origin": "Prophetic Family", "quranic": False},
        {"name": "Hawa", "arabic": "حواء", "meaning": "Eve, life-giver, mother of humanity", "origin": "Prophetic", "quranic": False},
        {"name": "Asiya", "arabic": "آسية", "meaning": "One who heals, pillar of strength", "origin": "Quranic Figure", "quranic": False},
        {"name": "Sarah", "arabic": "سارة", "meaning": "Princess, noble woman, pure", "origin": "Prophetic Family", "quranic": False},
        {"name": "Hajar", "arabic": "هاجر", "meaning": "Emigrant, flight to God", "origin": "Prophetic Family", "quranic": False},
        {"name": "Ruqayyah", "arabic": "رقية", "meaning": "Rise, ascent, enchantment", "origin": "Prophetic Family", "quranic": False},
        {"name": "Sumayya", "arabic": "سمية", "meaning": "High, exalted — first martyr in Islam", "origin": "Companion", "quranic": False},
        {"name": "Hafsa", "arabic": "حفصة", "meaning": "Young lioness, gatherer", "origin": "Prophetic Family", "quranic": False},
        {"name": "Umm Kulthum", "arabic": "أم كلثوم", "meaning": "Mother of the chubby-cheeked one", "origin": "Prophetic Family", "quranic": False},
        {"name": "Nusaybah", "arabic": "نسيبة", "meaning": "Noble lineage — warrior companion", "origin": "Companion", "quranic": False},
        {"name": "Safiyyah", "arabic": "صفية", "meaning": "Pure, sincere, best friend", "origin": "Prophetic Family", "quranic": False},
        {"name": "Jannah", "arabic": "جنة", "meaning": "Paradise, garden", "origin": "Quranic", "quranic": True, "reference": "2:35"},
        {"name": "Noor", "arabic": "نور", "meaning": "Light, divine radiance", "origin": "Quranic", "quranic": True, "reference": "24:35"},
        {"name": "Iman", "arabic": "إيمان", "meaning": "Faith, belief", "origin": "Islamic", "quranic": True, "reference": "49:14"},
        {"name": "Amina", "arabic": "آمنة", "meaning": "Trustworthy, faithful, secure", "origin": "Prophetic Family", "quranic": False},
        {"name": "Rahma", "arabic": "رحمة", "meaning": "Mercy, compassion", "origin": "Quranic", "quranic": True, "reference": "21:107"},
        {"name": "Sakina", "arabic": "سكينة", "meaning": "Tranquility, divine peace", "origin": "Quranic", "quranic": True, "reference": "2:248"},
        {"name": "Layla", "arabic": "ليلى", "meaning": "Night, dark beauty, intoxicating", "origin": "Arabic", "quranic": False},
        {"name": "Yasmin", "arabic": "ياسمين", "meaning": "Jasmine flower, symbol of grace", "origin": "Persian-Islamic", "quranic": False},
        {"name": "Amira", "arabic": "أميرة", "meaning": "Princess, leader, prosperous", "origin": "Arabic", "quranic": False},
        {"name": "Hana", "arabic": "هناء", "meaning": "Happiness, bliss, felicity", "origin": "Arabic", "quranic": False},
        {"name": "Dina", "arabic": "دينة", "meaning": "Faith, obedience, devotion", "origin": "Arabic", "quranic": False},
        {"name": "Salma", "arabic": "سلمى", "meaning": "Peaceful, safe, secure", "origin": "Arabic", "quranic": False},
        {"name": "Zahra", "arabic": "زهراء", "meaning": "Radiant, luminous, flower", "origin": "Prophetic Family", "quranic": False},
        {"name": "Naima", "arabic": "نعيمة", "meaning": "Blissful, living in comfort", "origin": "Arabic", "quranic": False},
        {"name": "Huda", "arabic": "هدى", "meaning": "Guidance, right path", "origin": "Quranic", "quranic": True, "reference": "2:2"},
        {"name": "Sabira", "arabic": "صابرة", "meaning": "Patient, enduring with grace", "origin": "Islamic", "quranic": False},
        {"name": "Barakah", "arabic": "بركة", "meaning": "Blessing, abundance", "origin": "Islamic", "quranic": False},
        {"name": "Amal", "arabic": "أمل", "meaning": "Hope, aspiration, expectation", "origin": "Arabic", "quranic": False},
        {"name": "Samira", "arabic": "سميرة", "meaning": "Entertaining companion, night conversationalist", "origin": "Arabic", "quranic": False},
        {"name": "Nasreen", "arabic": "نسرين", "meaning": "Wild rose, sweetbrier", "origin": "Persian-Islamic", "quranic": False},
        {"name": "Farida", "arabic": "فريدة", "meaning": "Unique, precious, rare gem", "origin": "Arabic", "quranic": False},
        {"name": "Malika", "arabic": "ملكة", "meaning": "Queen, sovereign", "origin": "Arabic", "quranic": False},
        {"name": "Jamila", "arabic": "جميلة", "meaning": "Beautiful, elegant, graceful", "origin": "Arabic", "quranic": False},
        {"name": "Karima", "arabic": "كريمة", "meaning": "Generous, noble, precious", "origin": "Arabic", "quranic": False},
        {"name": "Latifa", "arabic": "لطيفة", "meaning": "Gentle, kind, subtle", "origin": "Arabic", "quranic": False},
        {"name": "Marwa", "arabic": "مروة", "meaning": "A hill in Makkah, flint stone", "origin": "Quranic", "quranic": True, "reference": "2:158"},
        {"name": "Safa", "arabic": "صفا", "meaning": "A hill in Makkah, pure, clear", "origin": "Quranic", "quranic": True, "reference": "2:158"},
        {"name": "Taqwa", "arabic": "تقوى", "meaning": "God-consciousness, piety", "origin": "Quranic", "quranic": True, "reference": "2:197"},
        {"name": "Baraka", "arabic": "بركة", "meaning": "Blessing, sacred gift", "origin": "Islamic", "quranic": False},
        {"name": "Rania", "arabic": "رانية", "meaning": "Gazing, queenly", "origin": "Arabic", "quranic": False},
        {"name": "Lubna", "arabic": "لبنى", "meaning": "A tree with sweet sap, softness", "origin": "Arabic", "quranic": False},
        {"name": "Inaya", "arabic": "عناية", "meaning": "Care, concern, divine providence", "origin": "Arabic", "quranic": False},
        {"name": "Duaa", "arabic": "دعاء", "meaning": "Supplication, prayer to God", "origin": "Islamic", "quranic": True, "reference": "2:186"},
        {"name": "Shifa", "arabic": "شفاء", "meaning": "Healing, cure, remedy", "origin": "Quranic", "quranic": True, "reference": "10:57"},
        {"name": "Isra", "arabic": "إسراء", "meaning": "Night journey (of the Prophet)", "origin": "Quranic", "quranic": True, "reference": "17:1"},
        {"name": "Tasneem", "arabic": "تسنيم", "meaning": "A fountain in Paradise", "origin": "Quranic", "quranic": True, "reference": "83:27"},
        {"name": "Salsabil", "arabic": "سلسبيل", "meaning": "A spring in Paradise, smooth flowing", "origin": "Quranic", "quranic": True, "reference": "76:18"},
        {"name": "Kawther", "arabic": "كوثر", "meaning": "Abundance, a river in Paradise", "origin": "Quranic", "quranic": True, "reference": "108:1"},
        {"name": "Firdaws", "arabic": "فردوس", "meaning": "The highest level of Paradise", "origin": "Quranic", "quranic": True, "reference": "18:107"},
        {"name": "Sidra", "arabic": "سدرة", "meaning": "Lote tree at the boundary of heaven", "origin": "Quranic", "quranic": True, "reference": "53:14"},
        {"name": "Tasnim", "arabic": "تسنيم", "meaning": "Spring of Paradise", "origin": "Quranic", "quranic": True, "reference": "83:27"},
        {"name": "Sundus", "arabic": "سندس", "meaning": "Fine green silk of Paradise", "origin": "Quranic", "quranic": True, "reference": "18:31"},
        {"name": "Abeer", "arabic": "عبير", "meaning": "Fragrance, perfume", "origin": "Arabic", "quranic": False},
        {"name": "Afaf", "arabic": "عفاف", "meaning": "Chastity, purity, modesty", "origin": "Islamic", "quranic": False},
        {"name": "Basma", "arabic": "بسمة", "meaning": "A smile", "origin": "Arabic", "quranic": False},
        {"name": "Dana", "arabic": "دانة", "meaning": "Large pearl, precious gem", "origin": "Arabic", "quranic": False},
        {"name": "Hadiya", "arabic": "هدية", "meaning": "Gift, guide to righteousness", "origin": "Arabic", "quranic": False},
        {"name": "Ihsan", "arabic": "إحسان", "meaning": "Excellence, doing beautiful deeds", "origin": "Islamic", "quranic": False},
        {"name": "Lina", "arabic": "لينة", "meaning": "Tender, young palm tree", "origin": "Quranic", "quranic": True, "reference": "59:5"},
        {"name": "Maha", "arabic": "مها", "meaning": "Wild cow (symbol of beautiful eyes), moon-like", "origin": "Arabic", "quranic": False},
        {"name": "Nadia", "arabic": "نادية", "meaning": "The caller, the generous one", "origin": "Arabic", "quranic": False},
        {"name": "Rabia", "arabic": "رابعة", "meaning": "Spring, fourth (named for Rabia al-Adawiyyah)", "origin": "Historical", "quranic": False},
        {"name": "Sumaiya", "arabic": "سمية", "meaning": "High above, first female martyr", "origin": "Companion", "quranic": False},
        {"name": "Tamara", "arabic": "تمارة", "meaning": "Date palm, date fruit", "origin": "Arabic", "quranic": False},
        {"name": "Wafa", "arabic": "وفاء", "meaning": "Loyalty, faithfulness", "origin": "Arabic", "quranic": False},
        {"name": "Yara", "arabic": "يارة", "meaning": "Small butterfly, friend", "origin": "Arabic", "quranic": False},
        {"name": "Zubaida", "arabic": "زبيدة", "meaning": "Cream of the crop, best portion", "origin": "Historical", "quranic": False},
        {"name": "Anisa", "arabic": "أنيسة", "meaning": "Friendly companion, source of comfort", "origin": "Arabic", "quranic": False},
        {"name": "Bushra", "arabic": "بشرى", "meaning": "Good news, glad tidings", "origin": "Quranic", "quranic": True, "reference": "10:64"},
        {"name": "Ghada", "arabic": "غادة", "meaning": "Graceful, delicate young woman", "origin": "Arabic", "quranic": False},
        {"name": "Hanifa", "arabic": "حنيفة", "meaning": "Upright, true believer", "origin": "Quranic", "quranic": True, "reference": "6:79"},
        {"name": "Lamya", "arabic": "لمياء", "meaning": "Dark-lipped beauty, radiant", "origin": "Arabic", "quranic": False},
        {"name": "Manal", "arabic": "منال", "meaning": "Achievement, attainment", "origin": "Arabic", "quranic": False},
        {"name": "Najwa", "arabic": "نجوى", "meaning": "Whispered conversation, secret talk", "origin": "Quranic", "quranic": True, "reference": "58:7"},
        {"name": "Rawda", "arabic": "روضة", "meaning": "Garden, meadow of paradise", "origin": "Arabic", "quranic": False},
        {"name": "Sahar", "arabic": "سحر", "meaning": "Dawn, early morning", "origin": "Arabic", "quranic": False},
        {"name": "Thuraya", "arabic": "ثريا", "meaning": "Star cluster (Pleiades), chandelier", "origin": "Arabic", "quranic": False},
        {"name": "Wahida", "arabic": "واحدة", "meaning": "Unique, singular, the only one", "origin": "Arabic", "quranic": False},
        {"name": "Zara", "arabic": "زهرة", "meaning": "Flower, blooming, radiance", "origin": "Arabic", "quranic": False},
        {"name": "Asma", "arabic": "أسماء", "meaning": "Supreme, excellent, precious", "origin": "Companion", "quranic": False},
        {"name": "Bilqis", "arabic": "بلقيس", "meaning": "Queen of Sheba, wisdom and power", "origin": "Quranic Figure", "quranic": False},
        {"name": "Daliya", "arabic": "داليا", "meaning": "Grapevine, gentle", "origin": "Arabic", "quranic": False},
        {"name": "Fadila", "arabic": "فاضلة", "meaning": "Virtuous, outstanding, excellent", "origin": "Arabic", "quranic": False},
        {"name": "Ghufran", "arabic": "غفران", "meaning": "Forgiveness, pardon", "origin": "Quranic", "quranic": True, "reference": "2:286"},
        {"name": "Hayat", "arabic": "حياة", "meaning": "Life, existence", "origin": "Quranic", "quranic": True, "reference": "2:179"},
        {"name": "Ibtisam", "arabic": "ابتسام", "meaning": "Smiling, cheerful", "origin": "Arabic", "quranic": False},
        {"name": "Khawla", "arabic": "خولة", "meaning": "Gazelle, female deer", "origin": "Companion", "quranic": False},
        {"name": "Mizan", "arabic": "ميزان", "meaning": "Balance, scale of justice", "origin": "Quranic", "quranic": True, "reference": "55:7"},
        {"name": "Nur Jahan", "arabic": "نور جهان", "meaning": "Light of the world", "origin": "Persian-Islamic", "quranic": False},
        {"name": "Qamar", "arabic": "قمر", "meaning": "Moon, moonlight", "origin": "Quranic", "quranic": True, "reference": "54:1"},
        {"name": "Reem", "arabic": "ريم", "meaning": "White gazelle, gentle beauty", "origin": "Arabic", "quranic": False},
        {"name": "Shahida", "arabic": "شهيدة", "meaning": "Witness, one who testifies to truth", "origin": "Islamic", "quranic": False},
        {"name": "Umama", "arabic": "أمامة", "meaning": "Young mother, three hundred camels", "origin": "Prophetic Family", "quranic": False},
    ],
}


@app.route("/names", methods=["GET"])
def get_muslim_names():
    """Get Muslim name dictionary. Optional query params: gender, search, origin, quranic."""
    gender = request.args.get("gender")  # male, female, or None for both
    search = request.args.get("search", "").lower().strip()
    origin_filter = request.args.get("origin")
    quranic_only = request.args.get("quranic") == "true"

    results = {}
    for g in ["male", "female"]:
        if gender and gender != g:
            continue
        names = MUSLIM_NAMES[g]
        if search:
            names = [n for n in names if search in n["name"].lower() or search in n["meaning"].lower()]
        if origin_filter:
            names = [n for n in names if n["origin"] == origin_filter]
        if quranic_only:
            names = [n for n in names if n.get("quranic")]
        results[g] = names

    # Collect unique origins for filter
    all_origins = set()
    for g in ["male", "female"]:
        for n in MUSLIM_NAMES[g]:
            all_origins.add(n["origin"])

    return jsonify({
        "names": results,
        "total_male": len(MUSLIM_NAMES["male"]),
        "total_female": len(MUSLIM_NAMES["female"]),
        "origins": sorted(all_origins),
    }), 200


# ============================================================================
# IMAN INDEX — Behavioral Logging & Spiritual Companion
# ============================================================================

@app.route("/iman/setup", methods=["POST"])
@firebase_auth_required
def iman_setup():
    """Initialize Iman Index config for a new user.

    Body: {
        behavior_ids: ["fajr_prayer", ...],  # Optional, defaults to DEFAULT_BEHAVIORS
        struggle_ids: ["prayer_consistency"],  # Optional, auto-declares these
        onboarding_complete: true  # Optional, defaults to true
    }
    """
    uid = request.user["uid"]
    try:
        data = request.get_json(silent=True) or {}
        behavior_ids = data.get("behavior_ids")
        struggle_ids = data.get("struggle_ids", [])
        onboarding_done = data.get("onboarding_complete", True)

        # Check if already set up
        config_ref = users_db.collection("users").document(uid).collection("iman_config").document("settings")
        existing = config_ref.get()
        if existing.exists:
            return jsonify({"message": "Already configured", "config": existing.to_dict()}), 200

        # Validate behavior_ids if provided
        if behavior_ids:
            ok, cap_err = check_behavior_cap(behavior_ids)
            if not ok:
                return jsonify({"error": cap_err}), 400
            if len(behavior_ids) < 3:
                return jsonify({"error": "Please select at least 3 behaviors to track."}), 400

        config = build_default_config(behavior_ids)
        config["onboarding_complete"] = onboarding_done
        config_ref.set(config)

        # Auto-declare struggles if provided
        declared_struggles = []
        for sid in struggle_ids:
            if sid not in STRUGGLE_MAP:
                continue
            struggle_ref = (
                users_db.collection("users").document(uid)
                .collection("iman_struggles").document(sid)
            )
            ex = struggle_ref.get()
            if ex.exists and not ex.to_dict().get("resolved_at"):
                continue

            now_str = datetime.now(timezone.utc).isoformat()
            s_config = STRUGGLE_MAP[sid]

            guidance_excerpts = []
            try:
                pointers = s_config.get("scholarly_pointers", [])
                resolved = resolve_scholarly_pointers(pointers)
                for r in resolved.get("excerpts", []):
                    if r.get("text"):
                        guidance_excerpts.append({
                            "source": r.get("source", ""),
                            "title": r.get("title", ""),
                            "text": _encrypt_text(r["text"][:2000], uid),
                        })
            except Exception:
                pass

            doc_data = {
                "struggle_id": sid,
                "declared_at": now_str,
                "resolved_at": None,
                "guidance_excerpts": guidance_excerpts,
                "comfort_verse": s_config.get("comfort_verses", [{}])[0] if s_config.get("comfort_verses") else None,
                "updated_at": now_str,
            }
            struggle_ref.set(doc_data)
            declared_struggles.append(sid)

        print(f"[IMAN] Setup complete for user {uid[:8]}... — {len(config['tracked_behaviors'])} behaviors, {len(declared_struggles)} struggles")
        return jsonify({
            "message": "Iman Index configured",
            "config": config,
            "declared_struggles": declared_struggles,
        }), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"ERROR in POST /iman/setup: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/config", methods=["GET"])
@firebase_auth_required
def iman_get_config():
    """Get user's Iman Index configuration (tracked behaviors, categories)."""
    uid = request.user["uid"]
    try:
        config_ref = users_db.collection("users").document(uid).collection("iman_config").document("settings")
        doc = config_ref.get()
        if not doc.exists:
            return jsonify({"error": "Iman Index not set up. Call POST /iman/setup first."}), 404

        config = doc.to_dict()
        # Enrich with category metadata
        categories = []
        for cat_id, cat_meta in IMAN_CATEGORIES.items():
            categories.append({
                "id": cat_id,
                "label": cat_meta["label"],
                "icon": cat_meta["icon"],
                "color": cat_meta["color"],
                "base_weight": cat_meta["base_weight"],
            })

        return jsonify({
            "config": config,
            "categories": categories,
            "all_behaviors": IMAN_BEHAVIORS,
        }), 200

    except Exception as e:
        print(f"ERROR in GET /iman/config: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/config", methods=["PUT"])
@firebase_auth_required
def iman_update_config():
    """Update tracked behaviors (add/remove/reorder)."""
    uid = request.user["uid"]
    try:
        data = request.get_json(silent=True) or {}
        behavior_ids = data.get("behavior_ids")
        if not behavior_ids or not isinstance(behavior_ids, list):
            return jsonify({"error": "behavior_ids list required"}), 400

        # Validate all IDs
        invalid = [bid for bid in behavior_ids if bid not in BEHAVIOR_MAP]
        if invalid:
            return jsonify({"error": f"Unknown behavior IDs: {invalid}"}), 400

        # Safeguard: enforce behavior cap
        ok, cap_err = check_behavior_cap(behavior_ids)
        if not ok:
            return jsonify({"error": cap_err}), 400

        config_ref = users_db.collection("users").document(uid).collection("iman_config").document("settings")
        doc = config_ref.get()
        if not doc.exists:
            return jsonify({"error": "Iman Index not set up"}), 404

        now = datetime.now(timezone.utc).isoformat()
        tracked = []
        for bid in behavior_ids:
            b = BEHAVIOR_MAP[bid]
            tracked.append({
                "id": b["id"],
                "category": b["category"],
                "label": b["label"],
                "input_type": b["input_type"],
                "weight_override": None,
                "active": True,
                "added_at": now,
            })

        config_ref.update({"tracked_behaviors": tracked})

        print(f"[IMAN] Config updated for {uid[:8]}... — {len(tracked)} behaviors")

        # Return full config (matching GET /iman/config shape)
        updated_config = config_ref.get().to_dict()
        categories = []
        for cat_id, cat_meta in IMAN_CATEGORIES.items():
            categories.append({
                "id": cat_id,
                "label": cat_meta["label"],
                "icon": cat_meta["icon"],
                "color": cat_meta["color"],
                "base_weight": cat_meta["base_weight"],
            })

        return jsonify({
            "message": "Config updated",
            "tracked_count": len(tracked),
            "config": updated_config,
            "categories": categories,
        }), 200

    except Exception as e:
        print(f"ERROR in PUT /iman/config: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/catalog", methods=["GET"])
@firebase_auth_required
def iman_get_catalog():
    """Return full behavior + struggle catalog for onboarding/settings.

    Does NOT require setup. Used to render selectors before config exists.
    """
    try:
        categories = []
        for cat_id, cat_meta in IMAN_CATEGORIES.items():
            categories.append({
                "id": cat_id,
                "label": cat_meta["label"],
                "icon": cat_meta["icon"],
                "color": cat_meta["color"],
                "base_weight": cat_meta["base_weight"],
            })

        behaviors = []
        for b in IMAN_BEHAVIORS:
            behaviors.append({
                "id": b["id"],
                "category": b["category"],
                "label": b["label"],
                "input_type": b["input_type"],
                "default_on": b["default_on"],
            })

        struggles = []
        for s in STRUGGLE_CATALOG:
            struggles.append({
                "id": s["id"],
                "label": s["label"],
                "description": s["description"],
                "icon": s["icon"],
                "color": s["color"],
            })

        return jsonify({
            "categories": categories,
            "behaviors": behaviors,
            "struggles": struggles,
            "defaults": {
                "max_tracked": MAX_TRACKED_BEHAVIORS,
                "default_behavior_ids": [b["id"] for b in DEFAULT_BEHAVIORS],
                "recommended_range": {"min": 3, "max": 10},
            },
        }), 200

    except Exception as e:
        print(f"ERROR in GET /iman/catalog: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/data", methods=["DELETE"])
@firebase_auth_required
def iman_delete_all_data():
    """Permanently delete all Iman Index data for the authenticated user.

    Body: {confirm: "DELETE_ALL_IMAN_DATA"}
    """
    uid = request.user["uid"]
    try:
        data = request.get_json(silent=True) or {}
        if data.get("confirm") != "DELETE_ALL_IMAN_DATA":
            return jsonify({"error": "Confirmation required. Send {confirm: 'DELETE_ALL_IMAN_DATA'}"}), 400

        user_ref = users_db.collection("users").document(uid)
        subcollections = [
            "iman_config", "iman_daily_logs", "iman_baselines",
            "iman_trajectory", "iman_struggles", "iman_weekly_digests",
        ]

        deleted_counts = {}
        for sub in subcollections:
            count = 0
            docs = user_ref.collection(sub).stream()
            for doc in docs:
                doc.reference.delete()
                count += 1
            deleted_counts[sub] = count

        total = sum(deleted_counts.values())
        print(f"[IMAN] Data deleted for {uid[:8]}... — {total} documents across {len(subcollections)} subcollections")
        return jsonify({
            "message": "All Iman Index data deleted",
            "deleted": deleted_counts,
            "total_documents": total,
        }), 200

    except Exception as e:
        print(f"ERROR in DELETE /iman/data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/log", methods=["POST"])
@firebase_auth_required
def iman_submit_log():
    """Submit a daily journal log. Triggers trajectory recomputation.

    Body: {
        date: "YYYY-MM-DD",
        behaviors: {behavior_id: value, ...},
        heart_state: "grateful" (optional),
        heart_notes: [{type: "gratitude", text: "..."}] (optional)
    }
    """
    uid = request.user["uid"]
    try:
        data = request.get_json(silent=True) or {}
        date_str = data.get("date")
        behaviors_raw = data.get("behaviors", {})
        heart_state = data.get("heart_state")
        heart_notes_raw = data.get("heart_notes", [])

        if not date_str:
            return jsonify({"error": "date is required (YYYY-MM-DD)"}), 400

        # Validate date format
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Get config
        config_ref = users_db.collection("users").document(uid).collection("iman_config").document("settings")
        config_doc = config_ref.get()
        if not config_doc.exists:
            return jsonify({"error": "Iman Index not set up"}), 404
        config = config_doc.to_dict()
        tracked_ids = get_tracked_behavior_ids(config)

        # Validate behaviors
        now = datetime.now(timezone.utc).isoformat()
        validated_behaviors = {}
        errors = []
        for bid, val in behaviors_raw.items():
            if bid not in ALL_BEHAVIOR_IDS:
                errors.append(f"Unknown behavior: {bid}")
                continue
            ok, err, coerced = validate_behavior_value(bid, val)
            if not ok:
                errors.append(err)
            else:
                validated_behaviors[bid] = {"value": coerced, "logged_at": now}

        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        # Validate heart state
        if heart_state:
            ok, err = validate_heart_state(heart_state)
            if not ok:
                return jsonify({"error": err}), 400

        # Validate & encrypt heart notes
        encrypted_notes = []
        for note in heart_notes_raw:
            ok, err = validate_heart_note(note.get("type", ""), note.get("text", ""))
            if not ok:
                return jsonify({"error": err}), 400
            encrypted_notes.append({
                "type": note["type"],
                "text": _encrypt_text(note["text"].strip(), uid),
                "created_at": now,
            })

        # Build daily log document
        log_doc = {
            "date": date_str,
            "behaviors": validated_behaviors,
            "heart_state": heart_state,
            "heart_notes": encrypted_notes,
            "updated_at": now,
        }

        # Save to Firestore
        log_ref = users_db.collection("users").document(uid).collection("iman_daily_logs").document(date_str)
        log_ref.set(log_doc, merge=True)

        # Fetch all logs for trajectory computation (last 90 days)
        logs_query = (
            users_db.collection("users").document(uid)
            .collection("iman_daily_logs")
            .order_by("date")
            .limit(90)
        )
        all_logs = [doc.to_dict() for doc in logs_query.stream()]

        # Get current baselines
        baselines_ref = users_db.collection("users").document(uid).collection("iman_baselines").document("current")
        baselines_doc = baselines_ref.get()
        current_baselines = baselines_doc.to_dict() if baselines_doc.exists else None

        # Recompute trajectory
        trajectory, new_baselines = recompute_trajectory(all_logs, config, current_baselines)

        # Save trajectory
        traj_ref = users_db.collection("users").document(uid).collection("iman_trajectory").document("current")
        traj_ref.set(trajectory)

        # Save new baselines if computed
        if new_baselines:
            baselines_ref.set(new_baselines)
            # Mark config as baseline established
            if not config.get("baseline_established"):
                config_ref.update({"baseline_established": True})

        # Safeguards: welcome-back + anti-riya
        welcome_back = None
        if len(all_logs) >= 2:
            prev_date = all_logs[-2].get("date", "")
            if prev_date:
                try:
                    days_gap = (datetime.strptime(date_str, "%Y-%m-%d") - datetime.strptime(prev_date, "%Y-%m-%d")).days
                    welcome_back = get_welcome_back_message(days_gap)
                except ValueError:
                    pass

        # Strain/Recovery + Safeguards + Strain Trend
        tracked_ids = get_tracked_behavior_ids(config)
        sr_data = compute_strain_recovery(all_logs, tracked_ids)
        safeguards = compute_safeguard_status(all_logs, trajectory, sr_data, uid)
        strain_trend = compute_strain_trend(all_logs, tracked_ids)

        # Invalidate cached weekly digest so next view reflects new data
        try:
            log_date = datetime.strptime(date_str, "%Y-%m-%d")
            iso_cal = log_date.isocalendar()
            digest_week_id = f"{iso_cal[0]}-W{iso_cal[1]:02d}"
            digest_ref = (
                users_db.collection("users").document(uid)
                .collection("iman_weekly_digests").document(digest_week_id)
            )
            if digest_ref.get().exists:
                digest_ref.delete()
                print(f"[IMAN] Invalidated digest {digest_week_id} for {uid[:8]}... (new log saved)")
        except Exception as digest_err:
            print(f"[IMAN] Non-critical: failed to invalidate digest: {digest_err}")

        print(f"[IMAN] Log saved for {uid[:8]}... date={date_str} — state={trajectory.get('current_state')}")
        return jsonify({
            "message": "Log saved",
            "date": date_str,
            "trajectory": trajectory,
            "strain_recovery": sr_data,
            "safeguards": safeguards,
            "strain_trend": strain_trend,
            "anti_riya_reminder": should_show_anti_riya_reminder(),
            "welcome_back": welcome_back,
            "digest_invalidated": True,
        }), 200

    except Exception as e:
        print(f"ERROR in POST /iman/log: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/log/<date_str>", methods=["GET"])
@firebase_auth_required
def iman_get_log(date_str):
    """Get a specific day's log (with decrypted heart notes)."""
    uid = request.user["uid"]
    try:
        log_ref = users_db.collection("users").document(uid).collection("iman_daily_logs").document(date_str)
        doc = log_ref.get()
        if not doc.exists:
            return jsonify({"log": None, "date": date_str}), 200

        log = doc.to_dict()

        # Decrypt heart notes for display
        if log.get("heart_notes"):
            for note in log["heart_notes"]:
                note["text"] = _decrypt_text(note.get("text", ""), uid)

        return jsonify({"log": log, "date": date_str}), 200

    except Exception as e:
        print(f"ERROR in GET /iman/log/{date_str}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/logs", methods=["GET"])
@firebase_auth_required
def iman_get_logs():
    """Get logs for a date range. Query params: from, to (YYYY-MM-DD)."""
    uid = request.user["uid"]
    try:
        date_from = request.args.get("from")
        date_to = request.args.get("to")

        query = (
            users_db.collection("users").document(uid)
            .collection("iman_daily_logs")
            .order_by("date")
        )

        if date_from:
            query = query.where(filter=FieldFilter("date", ">=", date_from))
        if date_to:
            query = query.where(filter=FieldFilter("date", "<=", date_to))

        query = query.limit(90)
        logs = []
        for doc in query.stream():
            log = doc.to_dict()
            # Don't decrypt heart notes in bulk listing (privacy + performance)
            if log.get("heart_notes"):
                for note in log["heart_notes"]:
                    note["text"] = "[encrypted]"
            logs.append(log)

        return jsonify({"logs": logs, "count": len(logs)}), 200

    except Exception as e:
        print(f"ERROR in GET /iman/logs: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/trajectory", methods=["GET"])
@firebase_auth_required
def iman_get_trajectory():
    """Get current trajectory state."""
    uid = request.user["uid"]
    try:
        traj_ref = users_db.collection("users").document(uid).collection("iman_trajectory").document("current")
        doc = traj_ref.get()
        if not doc.exists:
            return jsonify({"trajectory": None, "message": "No trajectory data yet. Start logging!"}), 200

        traj = doc.to_dict()

        # Safeguard: comfort mode for extended recalibrating
        recal_days = 0
        if traj.get("current_state") == "recalibrating":
            daily_scores = traj.get("daily_scores", [])
            for score in reversed(daily_scores):
                if score.get("composite", 0.5) < 0.3:
                    recal_days += 1
                else:
                    break
            comfort = get_recalibrating_comfort(recal_days)
            if comfort:
                traj["comfort"] = comfort

        # Compute strain/recovery + safeguards from recent logs
        config_ref = users_db.collection("users").document(uid).collection("iman_config").document("settings")
        config_doc = config_ref.get()
        config = config_doc.to_dict() if config_doc.exists else {}
        tracked_ids = get_tracked_behavior_ids(config)

        logs_ref = users_db.collection("users").document(uid).collection("iman_daily_logs")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        recent_docs = logs_ref.where("date", ">=", cutoff).order_by("date").stream()
        recent_logs = [d.to_dict() for d in recent_docs]

        sr_data = compute_strain_recovery(recent_logs, tracked_ids)
        safeguards = compute_safeguard_status(recent_logs, traj, sr_data, uid, recal_days)

        traj["strain_recovery"] = sr_data
        traj["safeguards"] = safeguards

        return jsonify({"trajectory": traj}), 200

    except Exception as e:
        print(f"ERROR in GET /iman/trajectory: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/heart-note", methods=["POST"])
@firebase_auth_required
def iman_add_heart_note():
    """Quick-capture: append a heart note to today's log.

    Body: {type: "gratitude", text: "Alhamdulillah for..."}
    """
    uid = request.user["uid"]
    try:
        data = request.get_json(silent=True) or {}
        note_type = data.get("type", "")
        note_text = data.get("text", "")

        ok, err = validate_heart_note(note_type, note_text)
        if not ok:
            return jsonify({"error": err}), 400

        now = datetime.now(timezone.utc).isoformat()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        encrypted_note = {
            "type": note_type,
            "text": _encrypt_text(note_text.strip(), uid),
            "created_at": now,
        }

        # Get or create today's log
        log_ref = users_db.collection("users").document(uid).collection("iman_daily_logs").document(today)
        doc = log_ref.get()

        if doc.exists:
            log = doc.to_dict()
            notes = log.get("heart_notes", [])
            notes.append(encrypted_note)
            log_ref.update({"heart_notes": notes, "updated_at": now})
        else:
            log_ref.set({
                "date": today,
                "behaviors": {},
                "heart_state": None,
                "heart_notes": [encrypted_note],
                "updated_at": now,
            })

        print(f"[IMAN] Heart note ({note_type}) added for {uid[:8]}... date={today}")
        return jsonify({"message": "Heart note saved", "date": today}), 200

    except Exception as e:
        print(f"ERROR in POST /iman/heart-note: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Iman — Heart State Responses + Patterns
# ---------------------------------------------------------------------------

@app.route("/iman/heart-state/<state_id>/response", methods=["GET"])
@firebase_auth_required
def iman_heart_state_response(state_id):
    """Get tailored scholarly response for a heart state.

    Returns verse, insight, action, and resolved scholarly excerpts.
    """
    uid = request.user["uid"]
    try:
        if state_id not in HEART_STATE_MAP:
            return jsonify({"error": f"Unknown heart state: {state_id}"}), 400

        config = HEART_STATE_MAP[state_id]

        # Resolve scholarly pointers (live, like struggle guidance)
        pointers = config.get("scholarly_pointers", [])
        guidance_excerpts = []
        try:
            resolved = resolve_scholarly_pointers(pointers)
            for r in resolved.get("excerpts", []):
                if r.get("text"):
                    guidance_excerpts.append({
                        "source": r.get("source", ""),
                        "title": r.get("title", ""),
                        "text": r["text"][:2000],
                    })
        except Exception as re_err:
            print(f"[IMAN] Warning: Could not resolve pointers for heart state {state_id}: {re_err}")

        print(f"[IMAN] Heart state response: {state_id} for {uid[:8]}... ({len(guidance_excerpts)} excerpts)")
        return jsonify({
            "state_id": state_id,
            "label": config["label"],
            "arabic": config["arabic"],
            "verse": config["verse"],
            "insight": config["insight"],
            "action": config["action"],
            "guidance_excerpts": guidance_excerpts,
        }), 200

    except Exception as e:
        print(f"ERROR in GET /iman/heart-state/{state_id}/response: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/heart-patterns", methods=["GET"])
@firebase_auth_required
def iman_heart_patterns():
    """Get detected heart note patterns (temporal, emotional arcs, score correlation)."""
    uid = request.user["uid"]
    try:
        config_ref = users_db.collection("users").document(uid).collection("iman_config").document("settings")
        config_doc = config_ref.get()
        if not config_doc.exists:
            return jsonify({"error": "Iman Index not set up"}), 404
        config = config_doc.to_dict()
        tracked_ids = get_tracked_behavior_ids(config)

        # Fetch daily logs (last 30 days)
        logs_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_daily_logs")
            .order_by("date", direction=firestore.Query.DESCENDING)
            .limit(30)
        )
        daily_logs = [d.to_dict() for d in logs_ref.stream()]
        daily_logs.reverse()

        patterns = compute_heart_note_patterns(daily_logs, tracked_ids, window_days=30)

        print(f"[IMAN] Heart patterns for {uid[:8]}...: {patterns['has_patterns']}")
        return jsonify({"patterns": patterns}), 200

    except Exception as e:
        print(f"ERROR in GET /iman/heart-patterns: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Iman — Correlations & Safeguards Endpoints
# ---------------------------------------------------------------------------

@app.route("/iman/correlations", methods=["GET"])
@firebase_auth_required
def iman_get_correlations():
    """Get behavior correlations and weekly insight for display."""
    uid = request.user["uid"]
    try:
        config_ref = users_db.collection("users").document(uid).collection("iman_config").document("settings")
        config_doc = config_ref.get()
        if not config_doc.exists:
            return jsonify({"error": "Iman Index not set up"}), 404
        config = config_doc.to_dict()
        tracked_ids = get_tracked_behavior_ids(config)

        # Fetch 90 days of logs for correlation window
        logs_ref = users_db.collection("users").document(uid).collection("iman_daily_logs")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
        docs = logs_ref.where("date", ">=", cutoff).order_by("date").stream()
        daily_logs = [d.to_dict() for d in docs]

        correlations = compute_behavior_correlations(daily_logs, tracked_ids, window_days=90)

        # Select weekly insight (avoid repeats)
        previously_shown = config.get("shown_correlations", [])
        weekly_insight = select_weekly_insight(correlations, previously_shown)

        # Persist the newly shown insight to avoid repeats
        if weekly_insight:
            key = f"{weekly_insight['behavior_a']}|{weekly_insight['behavior_b']}"
            if key not in previously_shown:
                updated_shown = previously_shown + [key]
                # Cap at 50 to prevent unbounded growth
                config_ref.update({"shown_correlations": updated_shown[-50:]})

        # Generate Gemini-powered narrative (cached daily)
        narrative_data = None
        if len(correlations) >= 2:
            # Check daily cache
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            narrative_ref = (
                users_db.collection("users").document(uid)
                .collection("iman_correlation_narratives").document(today_str)
            )
            cached_narrative = narrative_ref.get()
            if cached_narrative.exists:
                narrative_data = cached_narrative.to_dict()
                # Decrypt fields
                for field in ["narrative", "key_insight"]:
                    val = narrative_data.get(field)
                    if val:
                        try:
                            narrative_data[field] = _decrypt_text(val, uid)
                        except Exception:
                            pass
            else:
                # Get trajectory and user info for context
                traj_ref = users_db.collection("users").document(uid).collection("iman_trajectory").document("current")
                traj_doc = traj_ref.get()
                traj = traj_doc.to_dict() if traj_doc.exists else {}
                user_doc = users_db.collection("users").document(uid).get()
                user_name = ""
                if user_doc.exists:
                    ud = user_doc.to_dict()
                    user_name = ud.get("displayName", ud.get("display_name", ""))

                narrative_prompt = build_correlation_narrative_prompt(
                    correlations,
                    trajectory_state=traj.get("composite_display", ""),
                    days_logged=traj.get("days_logged", 0),
                    user_name=user_name,
                )
                if narrative_prompt:
                    try:
                        import google.auth
                        from google.auth.transport.requests import Request as GoogleRequest
                        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                        auth_req = GoogleRequest()
                        credentials.refresh(auth_req)

                        vertex_endpoint = (
                            f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/"
                            f"{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/"
                            f"publishers/google/models/{GEMINI_MODEL_ID}:generateContent"
                        )
                        body = {
                            "contents": [{"role": "user", "parts": [{"text": narrative_prompt}]}],
                            "generation_config": {
                                "response_mime_type": "application/json",
                                "temperature": 0.6,
                                "maxOutputTokens": 1024,
                            },
                        }
                        resp = requests.post(
                            vertex_endpoint,
                            headers={"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"},
                            json=body,
                            timeout=20,
                        )
                        if resp.ok:
                            raw = resp.json()
                            gen_text = safe_get_nested(raw, "candidates", 0, "content", "parts", 0, "text")
                            if gen_text:
                                narrative_data = extract_json_from_response(gen_text)
                                if narrative_data:
                                    # Cache (encrypt text fields)
                                    encrypted = {
                                        "narrative": _encrypt_text(str(narrative_data.get("narrative", "")), uid),
                                        "key_insight": _encrypt_text(str(narrative_data.get("key_insight", "")), uid),
                                        "clusters": narrative_data.get("clusters", []),
                                        "generated_at": datetime.now(timezone.utc).isoformat(),
                                    }
                                    narrative_ref.set(encrypted)
                                    print(f"[IMAN] Correlation narrative generated for {uid[:8]}...")
                    except Exception as narr_err:
                        print(f"[IMAN] Narrative generation failed (non-blocking): {narr_err}")

        print(f"[IMAN] Correlations for {uid[:8]}...: {len(correlations)} found")
        return jsonify({
            "correlations": correlations[:5],
            "weekly_insight": weekly_insight,
            "narrative": narrative_data,
        }), 200

    except Exception as e:
        print(f"ERROR in GET /iman/correlations: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/safeguards/status", methods=["GET"])
@firebase_auth_required
def iman_get_safeguard_status():
    """Get current safeguard status for the user."""
    uid = request.user["uid"]
    try:
        # Read trajectory
        traj_ref = users_db.collection("users").document(uid).collection("iman_trajectory").document("current")
        traj_doc = traj_ref.get()
        traj = traj_doc.to_dict() if traj_doc.exists else {"current_state": "calibrating"}

        # Read config for tracked behaviors
        config_ref = users_db.collection("users").document(uid).collection("iman_config").document("settings")
        config_doc = config_ref.get()
        config = config_doc.to_dict() if config_doc.exists else {}
        tracked_ids = get_tracked_behavior_ids(config)

        # Fetch recent logs
        logs_ref = users_db.collection("users").document(uid).collection("iman_daily_logs")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        docs = logs_ref.where("date", ">=", cutoff).order_by("date").stream()
        recent_logs = [d.to_dict() for d in docs]

        sr_data = compute_strain_recovery(recent_logs, tracked_ids)
        safeguards = compute_safeguard_status(recent_logs, traj, sr_data, uid)

        return jsonify({"safeguards": safeguards}), 200

    except Exception as e:
        print(f"ERROR in GET /iman/safeguards/status: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Iman — Struggle Endpoints
# ---------------------------------------------------------------------------


def _summarize_guidance_excerpts(excerpts, struggle_label):
    """Use Gemini to distill raw scholarly text into concise, relevant guidance."""
    if not excerpts:
        return excerpts

    try:
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)

        sources_block = ""
        for i, ex in enumerate(excerpts):
            sources_block += (
                f"\n--- Source {i+1}: {ex.get('source', '')} — {ex.get('title', '')} ---\n"
                f"{ex.get('text', '')}\n"
            )

        prompt = f"""You are a scholarly Islamic studies assistant. A user is working on the struggle: "{struggle_label}".

Below are raw excerpts from classical Islamic texts. They may contain OCR artifacts, mixed scripts, or irrelevant sections.

For EACH source, produce a clean, concise summary (100-150 words) that:
1. Extracts ONLY the content relevant to "{struggle_label}"
2. Removes OCR artifacts, formatting noise, and untranslated Arabic text
3. Preserves the scholarly voice and key teachings
4. Focuses on practical spiritual guidance the reader can apply

{sources_block}

Return valid JSON — an array of objects, one per source, in the same order:
[
  {{"source": "source name", "title": "chapter/section title", "summary": "the clean summary"}}
]

Return ONLY the JSON array, no markdown fences."""

        vertex_endpoint = (
            f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/"
            f"{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/"
            f"publishers/google/models/gemini-2.5-flash-lite:generateContent"
        )

        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generation_config": {
                "response_mime_type": "application/json",
                "temperature": 0.3,
                "maxOutputTokens": 2048,
            },
        }

        response = requests.post(
            vertex_endpoint,
            headers={
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30,
        )

        if response.status_code != 200:
            print(f"[IMAN] Guidance summarization failed: HTTP {response.status_code}")
            return excerpts  # Fall back to raw text

        result = response.json()
        text = (
            result.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        summaries = json.loads(text)
        if not isinstance(summaries, list) or len(summaries) != len(excerpts):
            print(f"[IMAN] Guidance summarization returned unexpected shape")
            return excerpts

        summarized = []
        for i, ex in enumerate(excerpts):
            summarized.append({
                "source": ex.get("source", ""),
                "title": summaries[i].get("title", ex.get("title", "")),
                "text": summaries[i].get("summary", ex.get("text", "")),
            })

        print(f"[IMAN] Guidance summarized for '{struggle_label}': {len(summarized)} excerpts")
        return summarized

    except Exception as e:
        print(f"[IMAN] Guidance summarization error: {e}")
        return excerpts  # Fall back to raw text


@app.route("/iman/struggle", methods=["POST"])
@firebase_auth_required
def iman_declare_struggle():
    """Declare a new struggle. Resolves scholarly pointers for initial guidance.

    Body: {struggle_id: "prayer_consistency"}
    """
    uid = request.user["uid"]
    try:
        data = request.get_json(silent=True) or {}
        struggle_id = data.get("struggle_id", "")

        if struggle_id not in STRUGGLE_MAP:
            return jsonify({"error": f"Unknown struggle: {struggle_id}"}), 400

        struggle_config = STRUGGLE_MAP[struggle_id]

        # Check if already active
        struggle_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_struggles").document(struggle_id)
        )
        existing = struggle_ref.get()
        if existing.exists:
            ex_data = existing.to_dict()
            if not ex_data.get("resolved_at"):
                return jsonify({"error": "This struggle is already active."}), 409

        # Resolve scholarly pointers for initial guidance
        pointers = struggle_config.get("scholarly_pointers", [])
        raw_excerpts = []
        try:
            resolved = resolve_scholarly_pointers(pointers)
            for r in resolved.get("excerpts", []):
                if r.get("text"):
                    raw_excerpts.append({
                        "source": r.get("source", ""),
                        "title": r.get("title", ""),
                        "text": r["text"][:2000],
                    })
        except Exception as re_err:
            print(f"[IMAN] Warning: Could not resolve pointers for {struggle_id}: {re_err}")

        # Summarize raw text with Gemini
        summarized = _summarize_guidance_excerpts(raw_excerpts, struggle_config["label"])

        # Encrypt raw excerpts for Firestore storage
        encrypted_excerpts = []
        for r in raw_excerpts:
            encrypted_excerpts.append({
                "source": r["source"],
                "title": r["title"],
                "text": _encrypt_text(r["text"], uid),
            })

        now = datetime.now(timezone.utc).isoformat()
        doc_data = {
            "struggle_id": struggle_id,
            "declared_at": now,
            "resolved_at": None,
            "guidance_excerpts": encrypted_excerpts,
            "summarized_guidance": summarized,
            "comfort_verse": struggle_config.get("comfort_verses", [{}])[0] if struggle_config.get("comfort_verses") else None,
            "updated_at": now,
        }
        struggle_ref.set(doc_data)

        print(f"[IMAN] Struggle declared: {struggle_id} for {uid[:8]}...")
        return jsonify({
            "message": "Struggle declared",
            "struggle_id": struggle_id,
            "label": struggle_config["label"],
            "phases": struggle_config["phases"],
            "comfort_verse": doc_data["comfort_verse"],
            "guidance_excerpts": summarized,
            "declared_at": now,
        }), 201

    except Exception as e:
        print(f"ERROR in POST /iman/struggle: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/struggles", methods=["GET"])
@firebase_auth_required
def iman_list_struggles():
    """List active struggles with computed progress."""
    uid = request.user["uid"]
    try:
        struggles_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_struggles")
        )
        docs = struggles_ref.stream()

        # Fetch recent daily logs for progress computation
        logs_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_daily_logs")
            .order_by("date", direction=firestore.Query.DESCENDING)
            .limit(30)
        )
        daily_logs = [d.to_dict() for d in logs_ref.stream()]
        daily_logs.reverse()  # Oldest first

        active_struggles = []
        resolved_struggles = []

        for doc in docs:
            s = doc.to_dict()
            sid = s.get("struggle_id", doc.id)

            if sid not in STRUGGLE_MAP:
                continue

            config = STRUGGLE_MAP[sid]

            if s.get("resolved_at"):
                resolved_struggles.append({
                    "struggle_id": sid,
                    "label": config["label"],
                    "icon": config["icon"],
                    "color": config["color"],
                    "declared_at": s.get("declared_at"),
                    "resolved_at": s["resolved_at"],
                })
                continue

            # Compute progress for active struggles
            progress = compute_struggle_progress(
                sid,
                s.get("declared_at", ""),
                daily_logs,
                config,
            )

            # Pick a comfort verse
            verses = config.get("comfort_verses", [])
            comfort = verses[0] if verses else None

            active_struggles.append({
                "struggle_id": sid,
                "label": config["label"],
                "description": config["description"],
                "icon": config["icon"],
                "color": config["color"],
                "declared_at": s.get("declared_at"),
                "progress": progress,
                "comfort_verse": comfort,
                "linked_behaviors": config.get("linked_behaviors", []),
            })

        return jsonify({
            "active": active_struggles,
            "resolved": resolved_struggles,
        }), 200

    except Exception as e:
        print(f"ERROR in GET /iman/struggles: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/struggle/<struggle_id>", methods=["PUT"])
@firebase_auth_required
def iman_update_struggle(struggle_id):
    """Deactivate (resolve/pause) a struggle.

    Body: {action: "resolve"} or {action: "pause"}
    """
    uid = request.user["uid"]
    try:
        if struggle_id not in STRUGGLE_MAP:
            return jsonify({"error": f"Unknown struggle: {struggle_id}"}), 400

        data = request.get_json(silent=True) or {}
        action = data.get("action", "resolve")

        struggle_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_struggles").document(struggle_id)
        )
        doc = struggle_ref.get()
        if not doc.exists:
            return jsonify({"error": "Struggle not found."}), 404

        now = datetime.now(timezone.utc).isoformat()
        struggle_ref.update({
            "resolved_at": now,
            "resolution_type": action,
            "updated_at": now,
        })

        print(f"[IMAN] Struggle {action}: {struggle_id} for {uid[:8]}...")
        return jsonify({"message": f"Struggle {action}d", "struggle_id": struggle_id}), 200

    except Exception as e:
        print(f"ERROR in PUT /iman/struggle/{struggle_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/struggle/<struggle_id>/guidance", methods=["GET"])
@firebase_auth_required
def iman_struggle_guidance(struggle_id):
    """Resolve and summarize scholarly guidance for a declared struggle."""
    uid = request.user["uid"]
    try:
        if struggle_id not in STRUGGLE_MAP:
            return jsonify({"error": f"Unknown struggle: {struggle_id}"}), 400

        config = STRUGGLE_MAP[struggle_id]

        # Check that the user has declared this struggle
        struggle_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_struggles").document(struggle_id)
        )
        doc = struggle_ref.get()
        if not doc.exists:
            return jsonify({"error": "Struggle not declared."}), 404

        doc_data = doc.to_dict()

        # Return cached summarized guidance if available
        if doc_data.get("summarized_guidance"):
            print(f"[IMAN] Returning cached summarized guidance for {struggle_id}")
            return jsonify({
                "struggle_id": struggle_id,
                "label": config["label"],
                "phases": config["phases"],
                "comfort_verses": config.get("comfort_verses", []),
                "guidance_excerpts": doc_data["summarized_guidance"],
            }), 200

        # Resolve scholarly pointers
        pointers = config.get("scholarly_pointers", [])
        guidance_excerpts = []
        try:
            resolved = resolve_scholarly_pointers(pointers)
            for r in resolved.get("excerpts", []):
                if r.get("text"):
                    guidance_excerpts.append({
                        "source": r.get("source", ""),
                        "title": r.get("title", ""),
                        "text": r["text"][:2000],
                    })
        except Exception as re_err:
            print(f"[IMAN] Warning: Could not resolve pointers for {struggle_id}: {re_err}")

        # Summarize with Gemini and cache
        summarized = _summarize_guidance_excerpts(guidance_excerpts, config["label"])
        try:
            struggle_ref.update({"summarized_guidance": summarized})
        except Exception:
            pass  # Non-critical — just serve without caching

        return jsonify({
            "struggle_id": struggle_id,
            "label": config["label"],
            "phases": config["phases"],
            "comfort_verses": config.get("comfort_verses", []),
            "guidance_excerpts": summarized,
        }), 200

    except Exception as e:
        print(f"ERROR in GET /iman/struggle/{struggle_id}/guidance: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Iman — Weekly Digest Endpoints
# ---------------------------------------------------------------------------

@app.route("/iman/digest/generate", methods=["POST"])
@firebase_auth_required
def iman_generate_digest():
    """Generate (or return cached) weekly spiritual digest via Gemini.

    Body: {week_start: "2026-02-23", week_end: "2026-03-01"} (optional, defaults to current week)
    """
    uid = request.user["uid"]
    try:
        data = request.get_json(silent=True) or {}

        # Determine week boundaries
        now = datetime.now(timezone.utc)

        # Weekly digest restriction: Monday only + minimum 4 days logged
        if now.weekday() != 0:  # 0 = Monday
            return jsonify({
                "error": "Weekly digest is available on Mondays only.",
                "restriction": "monday_only",
                "day_of_week": now.strftime("%A"),
            }), 400

        week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        recent_logs_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_daily_logs")
            .where("date", ">=", week_ago)
        )
        recent_count = sum(1 for _ in recent_logs_ref.stream())
        if recent_count < 4:
            return jsonify({
                "error": f"Log at least 4 days this week to unlock your digest ({recent_count}/4 so far).",
                "restriction": "min_days",
                "days_logged": recent_count,
            }), 400

        if data.get("week_start") and data.get("week_end"):
            week_start = data["week_start"]
            week_end = data["week_end"]
        else:
            # Default: Monday-Sunday of current week
            monday = now - timedelta(days=now.weekday())
            sunday = monday + timedelta(days=6)
            week_start = monday.strftime("%Y-%m-%d")
            week_end = sunday.strftime("%Y-%m-%d")

        week_id = f"{week_start[:4]}-W{datetime.strptime(week_start, '%Y-%m-%d').isocalendar()[1]:02d}"

        # Check if digest already exists for this week
        digest_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_weekly_digests").document(week_id)
        )
        existing = digest_ref.get()
        if existing.exists:
            digest = existing.to_dict()
            # Decrypt stored fields
            decrypted = _decrypt_digest(digest, uid)
            return jsonify({"digest": decrypted, "week_id": week_id, "cached": True}), 200

        # Fetch all needed data
        # 1. Config
        config_ref = users_db.collection("users").document(uid).collection("iman_config").document("settings")
        config_doc = config_ref.get()
        config = config_doc.to_dict() if config_doc.exists else build_default_config()

        # 2. Daily logs (90 days for correlations)
        logs_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_daily_logs")
            .order_by("date", direction=firestore.Query.DESCENDING)
            .limit(90)
        )
        daily_logs = [d.to_dict() for d in logs_ref.stream()]
        daily_logs.reverse()

        if not daily_logs:
            return jsonify({"error": "No daily logs yet. Start logging to generate a digest."}), 400

        # 3. Trajectory
        traj_ref = users_db.collection("users").document(uid).collection("iman_trajectory").document("current")
        traj_doc = traj_ref.get()
        trajectory = traj_doc.to_dict() if traj_doc.exists else {}

        # 4. Heart notes from this week (decrypt them)
        heart_notes = []
        for log in daily_logs:
            if week_start <= log.get("date", "") <= week_end:
                for note in log.get("heart_notes", []):
                    try:
                        heart_notes.append({
                            "type": note.get("type", ""),
                            "text": _decrypt_text(note.get("text", ""), uid),
                        })
                    except Exception:
                        heart_notes.append({"type": note.get("type", ""), "text": ""})

        # 5. Active struggles with progress
        struggles_ref = users_db.collection("users").document(uid).collection("iman_struggles")
        active_struggles = []
        for doc in struggles_ref.stream():
            s = doc.to_dict()
            sid = s.get("struggle_id", doc.id)
            if s.get("resolved_at") or sid not in STRUGGLE_MAP:
                continue
            s_config = STRUGGLE_MAP[sid]
            progress = compute_struggle_progress(sid, s.get("declared_at", ""), daily_logs, s_config)
            active_struggles.append({
                "label": s_config["label"],
                "progress": progress,
            })

        # 6. User persona + display name
        user_doc = users_db.collection("users").document(uid).get()
        persona_name = "practicing_muslim"
        user_name = ""
        explored_verses_this_week = []
        if user_doc.exists:
            user_data = user_doc.to_dict()
            persona_name = user_data.get("persona", "practicing_muslim")
            user_name = user_data.get("displayName", user_data.get("display_name", ""))
            # Get explored verses for this week
            explored = user_data.get("explored_verses", {})
            for surah_num, verse_list in explored.items():
                for v in verse_list[-5:]:  # Last 5 per surah
                    explored_verses_this_week.append({"surah": surah_num, "verse": v})
            explored_verses_this_week = explored_verses_this_week[-10:]  # Cap at 10

        # Build context and prompt
        context = prepare_digest_context(
            daily_logs, trajectory, config, heart_notes,
            active_struggles, week_start, week_end,
            user_name=user_name,
            explored_verses_this_week=explored_verses_this_week,
        )
        prompt = build_digest_prompt(context, persona_name)

        # Call Gemini
        import google.auth
        from google.auth.transport.requests import Request as GoogleRequest

        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        gemini_token = credentials.token

        vertex_endpoint = (
            f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/"
            f"{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/"
            f"publishers/google/models/{GEMINI_MODEL_ID}:generateContent"
        )

        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generation_config": {
                "response_mime_type": "application/json",
                "temperature": 0.7,
                "maxOutputTokens": 4096,
            },
        }

        max_retries = 3
        response = None
        for attempt in range(max_retries):
            retry_delay = 2 ** (attempt + 1)
            try:
                response = requests.post(
                    vertex_endpoint,
                    headers={"Authorization": f"Bearer {gemini_token}", "Content-Type": "application/json"},
                    json=body,
                    timeout=60,
                )
                response.raise_for_status()
                break
            except requests.Timeout:
                if attempt == max_retries - 1:
                    return jsonify({"error": "AI service timeout", "retry": True}), 503
                time.sleep(retry_delay)
            except requests.HTTPError:
                status_code = response.status_code if response else 500
                if status_code in (429, 503) and attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return jsonify({"error": "AI service error"}), 502

        raw_response = response.json()
        generated_text = safe_get_nested(raw_response, "candidates", 0, "content", "parts", 0, "text")

        if not generated_text:
            return jsonify({"error": "Empty response from AI service"}), 502

        digest_data = extract_json_from_response(generated_text)
        if not digest_data:
            return jsonify({"error": "Could not parse digest response"}), 502

        # Encrypt sensitive text fields before storing
        encrypted_digest = {}
        text_fields = ["opening", "weekly_story", "strength_noticed", "correlation_insight", "gentle_attention", "closing"]
        for field in text_fields:
            val = digest_data.get(field, "")
            encrypted_digest[field] = _encrypt_text(str(val), uid) if val else ""

        # Handle verse_to_carry separately
        verse = digest_data.get("verse_to_carry", {})
        encrypted_digest["verse_to_carry"] = {
            "surah": verse.get("surah", 0),
            "verse": verse.get("verse", 0),
            "text": _encrypt_text(str(verse.get("text", "")), uid),
            "why": _encrypt_text(str(verse.get("why", "")), uid),
        }

        # Store
        store_doc = {
            **encrypted_digest,
            "week_id": week_id,
            "week_start": week_start,
            "week_end": week_end,
            "generated_at": now.isoformat(),
            "persona": persona_name,
            "context_summary": {
                "days_logged": context["days_logged_this_week"],
                "trajectory_state": context["trajectory_state"],
                "struggles_count": len(active_struggles),
            },
        }
        digest_ref.set(store_doc)

        print(f"[IMAN] Digest generated for {uid[:8]}... week={week_id}")
        return jsonify({"digest": digest_data, "week_id": week_id, "cached": False}), 200

    except Exception as e:
        print(f"ERROR in POST /iman/digest/generate: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/iman/digest/latest", methods=["GET"])
@firebase_auth_required
def iman_digest_latest():
    """Fetch the most recent weekly digest."""
    uid = request.user["uid"]
    try:
        digests_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_weekly_digests")
            .order_by("generated_at", direction=firestore.Query.DESCENDING)
            .limit(1)
        )
        docs = list(digests_ref.stream())
        if not docs:
            return jsonify({"digest": None}), 200

        digest = docs[0].to_dict()
        decrypted = _decrypt_digest(digest, uid)
        return jsonify({"digest": decrypted, "week_id": digest.get("week_id", "")}), 200

    except Exception as e:
        print(f"ERROR in GET /iman/digest/latest: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/digest/<week_id>", methods=["GET"])
@firebase_auth_required
def iman_digest_by_week(week_id):
    """Fetch a specific week's digest."""
    uid = request.user["uid"]
    try:
        digest_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_weekly_digests").document(week_id)
        )
        doc = digest_ref.get()
        if not doc.exists:
            return jsonify({"error": "No digest found for this week."}), 404

        digest = doc.to_dict()
        decrypted = _decrypt_digest(digest, uid)
        return jsonify({"digest": decrypted, "week_id": week_id}), 200

    except Exception as e:
        print(f"ERROR in GET /iman/digest/{week_id}: {e}")
        return jsonify({"error": str(e)}), 500


def _decrypt_digest(digest: dict, uid: str) -> dict:
    """Decrypt all encrypted text fields in a stored digest."""
    text_fields = ["opening", "weekly_story", "strength_noticed", "correlation_insight", "gentle_attention", "closing"]
    result = {}
    for field in text_fields:
        val = digest.get(field, "")
        try:
            result[field] = _decrypt_text(val, uid) if val else ""
        except Exception:
            result[field] = val

    # Decrypt verse_to_carry
    verse = digest.get("verse_to_carry", {})
    if isinstance(verse, dict):
        result["verse_to_carry"] = {
            "surah": verse.get("surah", 0),
            "verse": verse.get("verse", 0),
            "text": "",
            "why": "",
        }
        try:
            result["verse_to_carry"]["text"] = _decrypt_text(verse.get("text", ""), uid)
        except Exception:
            result["verse_to_carry"]["text"] = verse.get("text", "")
        try:
            result["verse_to_carry"]["why"] = _decrypt_text(verse.get("why", ""), uid)
        except Exception:
            result["verse_to_carry"]["why"] = verse.get("why", "")
    else:
        result["verse_to_carry"] = {}

    # Copy non-encrypted metadata
    result["week_id"] = digest.get("week_id", "")
    result["week_start"] = digest.get("week_start", "")
    result["week_end"] = digest.get("week_end", "")
    result["generated_at"] = digest.get("generated_at", "")
    result["context_summary"] = digest.get("context_summary", {})

    return result


# ---------------------------------------------------------------------------
# Iman — Daily Insight (Gemini-powered)
# ---------------------------------------------------------------------------

@app.route("/iman/daily-insight/<date_str>", methods=["GET"])
@firebase_auth_required
def iman_get_daily_insight(date_str):
    """Get Gemini-powered daily insight for a specific date. Cached per date."""
    uid = request.user["uid"]
    try:
        # Validate date
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Check cache
        insight_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_daily_insights").document(date_str)
        )
        existing = insight_ref.get()
        if existing.exists:
            cached = existing.to_dict()
            # Decrypt fields
            decrypted = {}
            for field in ["observation", "correlation", "encouragement", "strain_note"]:
                val = cached.get(field)
                if val:
                    try:
                        decrypted[field] = _decrypt_text(val, uid)
                    except Exception:
                        decrypted[field] = val
                else:
                    decrypted[field] = None
            return jsonify({"insight": decrypted, "date": date_str, "cached": True}), 200

        # Fetch today's log
        log_ref = users_db.collection("users").document(uid).collection("iman_daily_logs").document(date_str)
        log_doc = log_ref.get()
        if not log_doc.exists:
            return jsonify({"error": "No log found for this date."}), 404
        today_log = log_doc.to_dict()

        # Fetch last 7 days of logs
        cutoff = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
        logs_query = (
            users_db.collection("users").document(uid)
            .collection("iman_daily_logs")
            .where("date", ">=", cutoff)
            .where("date", "<=", date_str)
            .order_by("date")
        )
        recent_logs = [d.to_dict() for d in logs_query.stream()]

        # Config
        config_ref = users_db.collection("users").document(uid).collection("iman_config").document("settings")
        config_doc = config_ref.get()
        config = config_doc.to_dict() if config_doc.exists else build_default_config()

        # Trajectory
        traj_ref = users_db.collection("users").document(uid).collection("iman_trajectory").document("current")
        traj_doc = traj_ref.get()
        trajectory = traj_doc.to_dict() if traj_doc.exists else {}

        # Active struggles
        struggles_ref = users_db.collection("users").document(uid).collection("iman_struggles")
        active_struggles = []
        for doc in struggles_ref.stream():
            s = doc.to_dict()
            sid = s.get("struggle_id", doc.id)
            if s.get("resolved_at") or sid not in STRUGGLE_MAP:
                continue
            s_config = STRUGGLE_MAP[sid]
            progress = compute_struggle_progress(sid, s.get("declared_at", ""), recent_logs, s_config)
            active_struggles.append({"label": s_config["label"], "progress": progress})

        # User persona + display name
        user_doc = users_db.collection("users").document(uid).get()
        persona_name = "practicing_muslim"
        user_name = ""
        recent_verses = []
        if user_doc.exists:
            user_data = user_doc.to_dict()
            persona_name = user_data.get("persona", "practicing_muslim")
            user_name = user_data.get("displayName", user_data.get("display_name", ""))
            # Recent explored verses
            explored = user_data.get("explored_verses", {})
            for surah_num, verse_list in explored.items():
                for v in verse_list[-3:]:
                    recent_verses.append({"surah": surah_num, "verse": v})
            recent_verses = recent_verses[-5:]

        # Decrypt today's heart notes for context
        heart_note_texts = []
        for note in today_log.get("heart_notes", []):
            try:
                heart_note_texts.append({
                    "type": note.get("type", ""),
                    "text": _decrypt_text(note.get("text", ""), uid),
                })
            except Exception:
                pass

        # Build context and prompt
        context = prepare_daily_insight_context(
            today_log, recent_logs, trajectory, config, active_struggles,
            user_name=user_name,
            heart_note_texts=heart_note_texts,
            recent_verses_explored=recent_verses,
        )
        prompt = build_daily_insight_prompt(context, persona_name)

        # Call Gemini
        import google.auth
        from google.auth.transport.requests import Request as GoogleRequest
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        gemini_token = credentials.token

        vertex_endpoint = (
            f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/"
            f"{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/"
            f"publishers/google/models/{GEMINI_MODEL_ID}:generateContent"
        )

        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generation_config": {
                "response_mime_type": "application/json",
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            },
        }

        max_retries = 3
        response = None
        for attempt in range(max_retries):
            retry_delay = 2 ** (attempt + 1)
            try:
                response = requests.post(
                    vertex_endpoint,
                    headers={"Authorization": f"Bearer {gemini_token}", "Content-Type": "application/json"},
                    json=body,
                    timeout=30,
                )
                response.raise_for_status()
                break
            except requests.Timeout:
                if attempt == max_retries - 1:
                    return jsonify({"error": "AI service timeout", "retry": True}), 503
                time.sleep(retry_delay)
            except requests.HTTPError:
                status_code = response.status_code if response else 500
                if status_code in (429, 503) and attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return jsonify({"error": "AI service error"}), 502

        raw_response = response.json()
        generated_text = safe_get_nested(raw_response, "candidates", 0, "content", "parts", 0, "text")
        if not generated_text:
            return jsonify({"error": "Empty response from AI service"}), 502

        insight_data = extract_json_from_response(generated_text)
        if not insight_data:
            return jsonify({"error": "Could not parse insight response"}), 502

        # Encrypt and cache
        encrypted = {}
        for field in ["observation", "correlation", "encouragement", "strain_note"]:
            val = insight_data.get(field)
            if val and val != "null" and str(val).lower() != "none":
                encrypted[field] = _encrypt_text(str(val), uid)
            else:
                encrypted[field] = None

        now = datetime.now(timezone.utc).isoformat()
        encrypted["generated_at"] = now
        encrypted["date"] = date_str
        insight_ref.set(encrypted)

        print(f"[IMAN] Daily insight generated for {uid[:8]}... date={date_str}")
        return jsonify({"insight": insight_data, "date": date_str, "cached": False}), 200

    except Exception as e:
        print(f"ERROR in GET /iman/daily-insight/{date_str}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Iman — Heart Note Edit / Delete / History
# ---------------------------------------------------------------------------

@app.route("/iman/heart-note/<date_str>/<int:index>", methods=["PUT"])
@firebase_auth_required
def iman_edit_heart_note(date_str, index):
    """Edit a heart note (same-day only)."""
    uid = request.user["uid"]
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if date_str != today:
            return jsonify({"error": "Can only edit same-day notes"}), 400

        data = request.get_json(silent=True) or {}
        new_text = data.get("text", "")

        log_ref = users_db.collection("users").document(uid).collection("iman_daily_logs").document(date_str)
        doc = log_ref.get()
        if not doc.exists:
            return jsonify({"error": "No log found for this date"}), 404

        log = doc.to_dict()
        notes = log.get("heart_notes", [])
        if index < 0 or index >= len(notes):
            return jsonify({"error": "Invalid note index"}), 400

        note_type = notes[index].get("type", "gratitude")
        ok, err = validate_heart_note(note_type, new_text)
        if not ok:
            return jsonify({"error": err}), 400

        now = datetime.now(timezone.utc).isoformat()
        notes[index]["text"] = _encrypt_text(new_text.strip(), uid)
        notes[index]["edited_at"] = now
        log_ref.update({"heart_notes": notes, "updated_at": now})

        return jsonify({"message": "Heart note updated"}), 200

    except Exception as e:
        print(f"ERROR in PUT /iman/heart-note/{date_str}/{index}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/heart-note/<date_str>/<int:index>", methods=["DELETE"])
@firebase_auth_required
def iman_delete_heart_note(date_str, index):
    """Delete a heart note (same-day only)."""
    uid = request.user["uid"]
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if date_str != today:
            return jsonify({"error": "Can only delete same-day notes"}), 400

        log_ref = users_db.collection("users").document(uid).collection("iman_daily_logs").document(date_str)
        doc = log_ref.get()
        if not doc.exists:
            return jsonify({"error": "No log found for this date"}), 404

        log = doc.to_dict()
        notes = log.get("heart_notes", [])
        if index < 0 or index >= len(notes):
            return jsonify({"error": "Invalid note index"}), 400

        notes.pop(index)
        now = datetime.now(timezone.utc).isoformat()
        log_ref.update({"heart_notes": notes, "updated_at": now})

        return jsonify({"message": "Heart note deleted"}), 200

    except Exception as e:
        print(f"ERROR in DELETE /iman/heart-note/{date_str}/{index}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/heart-notes", methods=["GET"])
@firebase_auth_required
def iman_heart_note_history():
    """Get heart note history with filtering and search."""
    uid = request.user["uid"]
    try:
        days = int(request.args.get("days", 30))
        note_type = request.args.get("type", "")
        search_q = request.args.get("q", "").strip().lower()

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        logs_ref = (
            users_db.collection("users").document(uid)
            .collection("iman_daily_logs")
            .where("date", ">=", cutoff)
            .order_by("date", direction=firestore.Query.DESCENDING)
        )

        all_notes = []
        for doc in logs_ref.stream():
            log = doc.to_dict()
            log_date = log.get("date", "")
            for i, note in enumerate(log.get("heart_notes", [])):
                n_type = note.get("type", "")
                if note_type and n_type != note_type:
                    continue

                try:
                    decrypted_text = _decrypt_text(note.get("text", ""), uid)
                except Exception:
                    decrypted_text = ""

                if search_q and search_q not in decrypted_text.lower():
                    continue

                all_notes.append({
                    "date": log_date,
                    "index": i,
                    "type": n_type,
                    "text": decrypted_text,
                    "created_at": note.get("created_at", ""),
                })

        return jsonify({"notes": all_notes, "total": len(all_notes)}), 200

    except Exception as e:
        print(f"ERROR in GET /iman/heart-notes: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Iman — Struggle Goals
# ---------------------------------------------------------------------------

@app.route("/iman/struggle/<struggle_id>/goals", methods=["GET"])
@firebase_auth_required
def iman_get_struggle_goals(struggle_id):
    """Get active daily + weekly goals for a struggle based on current phase."""
    uid = request.user["uid"]
    try:
        if struggle_id not in STRUGGLE_MAP:
            return jsonify({"error": "Unknown struggle"}), 404

        s_config = STRUGGLE_MAP[struggle_id]
        goals_catalog = s_config.get("goals", {})
        if not goals_catalog:
            return jsonify({"error": "No goals defined for this struggle"}), 404

        # Get struggle doc
        struggle_ref = users_db.collection("users").document(uid).collection("iman_struggles").document(struggle_id)
        struggle_doc = struggle_ref.get()
        if not struggle_doc.exists:
            return jsonify({"error": "Struggle not found"}), 404

        s = struggle_doc.to_dict()
        if s.get("resolved_at"):
            return jsonify({"error": "Struggle is resolved"}), 400

        # Compute current phase
        declared_at = s.get("declared_at", "")
        now = datetime.now(timezone.utc)
        try:
            start = datetime.fromisoformat(declared_at.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, AttributeError):
            start = now
        days_active = max(0, (now - start).days)
        current_phase = min(days_active // 7, 3)

        phase_goals = goals_catalog.get(current_phase, goals_catalog.get(str(current_phase), {}))
        if not phase_goals:
            return jsonify({"daily": [], "weekly": None}), 200

        # Completion tracking
        today = now.strftime("%Y-%m-%d")
        tracking_ref = users_db.collection("users").document(uid).collection("iman_struggle_goals").document(struggle_id)
        tracking_doc = tracking_ref.get()
        completions = tracking_doc.to_dict().get("completions", {}) if tracking_doc.exists else {}

        # Build daily goals
        daily_goals = []
        for goal in phase_goals.get("daily", []):
            goal_dates = completions.get(goal["id"], [])
            daily_goals.append({
                **goal,
                "completed_today": today in goal_dates,
            })

        # Build weekly goal
        weekly_goal = None
        wg = phase_goals.get("weekly")
        if wg:
            wg_dates = completions.get(wg["id"], [])
            # Check if completed in last 7 days
            week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            completed_this_week = any(d >= week_ago for d in wg_dates)
            # Days until reset
            if wg_dates:
                last_completion = max(wg_dates)
                try:
                    lc = datetime.strptime(last_completion, "%Y-%m-%d")
                    days_since = (now - lc).days
                    days_until_reset = max(0, 7 - days_since)
                except ValueError:
                    days_until_reset = 0
            else:
                days_until_reset = 0

            weekly_goal = {
                **wg,
                "completed_this_week": completed_this_week,
                "days_until_reset": days_until_reset,
            }

        return jsonify({"daily": daily_goals, "weekly": weekly_goal, "phase": current_phase}), 200

    except Exception as e:
        print(f"ERROR in GET /iman/struggle/{struggle_id}/goals: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/iman/struggle/<struggle_id>/goal/complete", methods=["POST"])
@firebase_auth_required
def iman_complete_struggle_goal(struggle_id):
    """Mark a struggle goal as completed."""
    uid = request.user["uid"]
    try:
        data = request.get_json(silent=True) or {}
        goal_id = data.get("goal_id", "")
        if not goal_id:
            return jsonify({"error": "goal_id is required"}), 400

        if struggle_id not in STRUGGLE_MAP:
            return jsonify({"error": "Unknown struggle"}), 404

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        tracking_ref = users_db.collection("users").document(uid).collection("iman_struggle_goals").document(struggle_id)
        tracking_doc = tracking_ref.get()
        completions = tracking_doc.to_dict().get("completions", {}) if tracking_doc.exists else {}

        goal_dates = completions.get(goal_id, [])

        # Check if it's a weekly goal (id ends with _w*)
        is_weekly = "_w" in goal_id and goal_id.split("_w")[-1].isdigit()
        if is_weekly:
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
            if any(d >= week_ago for d in goal_dates):
                return jsonify({"error": "Weekly goal already completed this week"}), 400

        if today not in goal_dates:
            goal_dates.append(today)

        completions[goal_id] = goal_dates
        tracking_ref.set({"completions": completions}, merge=True)

        return jsonify({"message": "Goal completed", "goal_id": goal_id, "date": today}), 200

    except Exception as e:
        print(f"ERROR in POST /iman/struggle/{struggle_id}/goal/complete: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# FEEDBACK SYSTEM — Gemini enrichment + GitHub Issues + Daily Email Summary
# ============================================================================

FEEDBACK_GITHUB_REPO = os.environ.get("FEEDBACK_GITHUB_REPO", "ahmeds6016/tafsir-simplified-app")
FEEDBACK_GITHUB_TOKEN = os.environ.get("FEEDBACK_GITHUB_TOKEN", "")
FEEDBACK_SUMMARY_EMAIL = os.environ.get("FEEDBACK_SUMMARY_EMAIL", "")


def _enrich_feedback_with_gemini(feedback_type, raw_message):
    """Use Gemini to clean up and structure user feedback."""
    try:
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(GoogleRequest())

        endpoint = (
            f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/"
            f"{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/"
            f"publishers/google/models/gemini-2.5-flash-lite:generateContent"
        )

        type_labels = {"feature": "feature request", "bug": "bug report", "general": "general feedback"}
        prompt = (
            f"You are a product manager assistant. A user submitted the following {type_labels.get(feedback_type, 'feedback')} "
            f"for a Quran study app called Tadabbur.\n\n"
            f"Raw user message:\n\"{raw_message}\"\n\n"
            f"Return a JSON object with exactly these fields:\n"
            f"- \"title\": A concise, clear title (under 80 chars) suitable for a GitHub issue\n"
            f"- \"body\": A cleaned-up, well-structured version of the feedback (2-4 sentences max). "
            f"Fix grammar and spelling but preserve the user's intent. Do not add information they didn't mention.\n"
            f"- \"labels\": An array of 1-2 relevant labels from this list: "
            f"[\"enhancement\", \"bug\", \"ux\", \"content\", \"performance\", \"mobile\", \"accessibility\"]\n\n"
            f"Return ONLY valid JSON, no markdown fences."
        )

        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generation_config": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
                "maxOutputTokens": 1024,
            },
        }

        resp = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
            json=body,
            timeout=15,
        )

        if resp.status_code == 200:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            enriched = json.loads(text)
            print(f"[FEEDBACK] Gemini enrichment OK — title: {enriched.get('title', '')[:60]}")
            return enriched
        else:
            print(f"[FEEDBACK] Gemini enrichment failed: HTTP {resp.status_code}")
            return None

    except Exception as e:
        print(f"[FEEDBACK] Gemini enrichment error: {e}")
        return None


def _create_github_issue(feedback_type, title, body, labels):
    """Create a GitHub issue from enriched feedback."""
    if not FEEDBACK_GITHUB_TOKEN:
        print("[FEEDBACK] No FEEDBACK_GITHUB_TOKEN set — skipping GitHub issue")
        return None

    try:
        type_label = "enhancement" if feedback_type == "feature" else "bug" if feedback_type == "bug" else "feedback"
        all_labels = list(set([type_label] + (labels or [])))

        issue_body = f"{body}\n\n---\n*Submitted via in-app feedback*"

        resp = requests.post(
            f"https://api.github.com/repos/{FEEDBACK_GITHUB_REPO}/issues",
            headers={
                "Authorization": f"token {FEEDBACK_GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            },
            json={
                "title": title,
                "body": issue_body,
                "labels": all_labels,
            },
            timeout=10,
        )

        if resp.status_code == 201:
            issue_url = resp.json().get("html_url", "")
            print(f"[FEEDBACK] GitHub issue created: {issue_url}")
            return issue_url
        else:
            print(f"[FEEDBACK] GitHub issue creation failed: HTTP {resp.status_code} — {resp.text[:200]}")
            return None

    except Exception as e:
        print(f"[FEEDBACK] GitHub issue error: {e}")
        return None


@app.route("/feedback", methods=["POST"])
@firebase_auth_required
def submit_feedback():
    """Store user feedback in Firestore, enrich with Gemini, create GitHub issue."""
    try:
        uid = request.user["uid"]
        data = request.get_json()

        feedback_type = data.get("type", "general")
        message = (data.get("message") or "").strip()

        if not message:
            return jsonify({"error": "Message is required"}), 400
        if len(message) > 2000:
            return jsonify({"error": "Message must be under 2000 characters"}), 400
        if feedback_type not in ("feature", "bug", "general"):
            return jsonify({"error": "Invalid feedback type"}), 400

        # Enrich with Gemini (non-blocking — failures don't prevent submission)
        enriched = _enrich_feedback_with_gemini(feedback_type, message)

        title = enriched["title"] if enriched else f"[{feedback_type}] {message[:70]}"
        body = enriched["body"] if enriched else message
        labels = enriched.get("labels", []) if enriched else []

        doc = {
            "uid": uid,
            "email": request.user.get("email", ""),
            "type": feedback_type,
            "message": message,
            "enriched_title": title,
            "enriched_body": body,
            "labels": labels,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        _, doc_ref = users_db.collection("feedback").add(doc)
        print(f"[FEEDBACK] {feedback_type} from {uid[:8]}...: {message[:80]}")

        # Create GitHub issue in background thread (don't slow down response)
        def _bg_github(ref):
            issue_url = _create_github_issue(feedback_type, title, body, labels)
            if issue_url:
                try:
                    ref.update({"github_issue_url": issue_url})
                except Exception as e:
                    print(f"[FEEDBACK] Failed to update doc with issue URL: {e}")

        threading.Thread(target=_bg_github, args=(doc_ref,), daemon=True).start()

        return jsonify({"message": "Feedback submitted. Thank you!"}), 200

    except Exception as e:
        print(f"ERROR in POST /feedback: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/feedback/daily-summary", methods=["POST"])
def feedback_daily_summary():
    """
    Generate and email a daily summary of feedback.
    Intended to be called by Cloud Scheduler (no auth — use IAM or a shared secret).
    """
    try:
        # Verify Cloud Scheduler secret (optional, set FEEDBACK_CRON_SECRET env var)
        cron_secret = os.environ.get("FEEDBACK_CRON_SECRET", "")
        if cron_secret:
            provided = request.headers.get("X-Cron-Secret", "")
            if provided != cron_secret:
                return jsonify({"error": "Unauthorized"}), 403

        if not FEEDBACK_SUMMARY_EMAIL:
            return jsonify({"error": "FEEDBACK_SUMMARY_EMAIL not configured"}), 500

        # Get feedback from the last 24 hours
        yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
        docs = (
            users_db.collection("feedback")
            .where(filter=FieldFilter("created_at", ">=", yesterday))
            .order_by("created_at", direction="DESCENDING")
            .get()
        )

        if not docs:
            print("[FEEDBACK] No feedback in last 24h — skipping summary email")
            return jsonify({"message": "No feedback to summarize"}), 200

        items = []
        for doc in docs:
            d = doc.to_dict()
            items.append({
                "type": d.get("type", "general"),
                "title": d.get("enriched_title", d.get("message", "")[:70]),
                "body": d.get("enriched_body", d.get("message", "")),
                "email": d.get("email", "anonymous"),
                "github": d.get("github_issue_url", ""),
            })

        # Build email body
        type_icons = {"feature": "NEW FEATURE", "bug": "BUG REPORT", "general": "GENERAL"}
        lines = [f"Tadabbur Feedback Summary — {len(items)} item(s)\n"]
        lines.append(f"Period: {yesterday.strftime('%Y-%m-%d %H:%M UTC')} to now\n")
        lines.append("=" * 60 + "\n")

        for i, item in enumerate(items, 1):
            lines.append(f"\n{i}. [{type_icons.get(item['type'], 'OTHER')}] {item['title']}")
            lines.append(f"   From: {item['email']}")
            lines.append(f"   {item['body']}")
            if item["github"]:
                lines.append(f"   GitHub: {item['github']}")
            lines.append("")

        email_body = "\n".join(lines)

        # Send via SMTP (Gmail app password or any SMTP provider)
        smtp_email = os.environ.get("FEEDBACK_SMTP_EMAIL", "")
        smtp_password = os.environ.get("FEEDBACK_SMTP_PASSWORD", "")
        smtp_host = os.environ.get("FEEDBACK_SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("FEEDBACK_SMTP_PORT", "587"))

        if smtp_email and smtp_password:
            try:
                import smtplib
                from email.mime.text import MIMEText

                mime_msg = MIMEText(email_body, "plain", "utf-8")
                mime_msg["From"] = smtp_email
                mime_msg["To"] = FEEDBACK_SUMMARY_EMAIL
                mime_msg["Subject"] = (
                    f"Tadabbur Feedback: {len(items)} new item(s) "
                    f"— {datetime.now(timezone.utc).strftime('%b %d')}"
                )

                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_email, smtp_password)
                    server.send_message(mime_msg)

                print(f"[FEEDBACK] Daily summary email sent to {FEEDBACK_SUMMARY_EMAIL}")

            except Exception as mail_err:
                print(f"[FEEDBACK] Email send failed: {mail_err}")
                print(f"[FEEDBACK] Summary (logged):\n{email_body}")
        else:
            print("[FEEDBACK] SMTP not configured — logging summary instead")
            print(f"[FEEDBACK] Summary:\n{email_body}")

        return jsonify({"message": f"Summary generated for {len(items)} items"}), 200

    except Exception as e:
        print(f"ERROR in POST /feedback/daily-summary: {e}")
        return jsonify({"error": str(e)}), 500


# --- Main ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host="0.0.0.0", port=port)
