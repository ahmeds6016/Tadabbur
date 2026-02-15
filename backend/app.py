import os
import json
import re
import traceback
import time
import hashlib
import threading
import logging
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional, Dict, List, Any

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

# Imports for RAG and Query Expansion
import vertexai
from vertexai.language_models import TextEmbeddingModel
from google.cloud import aiplatform
from google.cloud import storage
from utils.text_cleaning import sanitize_heading_format
from services.source_service import (
    get_relevant_scholarly_context,
    extract_topic_keywords_from_query,
    get_scholarly_sources_metadata,
    build_scholarly_planning_prompt,
    resolve_scholarly_pointers,
    format_scholarly_excerpts_for_prompt,
    plan_scholarly_retrieval_deterministic,
)

# --- App Initialization ---
app = Flask(__name__)
CORS(app, resources={r"/*": {
    "origins": [
        "http://localhost:3000",
        "https://tafsir-frontend-612616741510.us-central1.run.app"
    ]
}}, supports_credentials=True)

# --- Configuration (UPDATED for new sliding window vector index) ---
# Firebase project (Auth, Firestore, Users, Quran texts)
FIREBASE_PROJECT = os.environ.get("FIREBASE_PROJECT", "tafsir-simplified-6b262")
# GCP infrastructure project (Vertex AI, GCS, Cloud Run)
GCP_INFRASTRUCTURE_PROJECT = os.environ.get("GCP_INFRASTRUCTURE_PROJECT", "tafsir-simplified")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-2.5-flash")  # Upgraded: 65K output tokens (vs 8K in 2.0) - eliminates truncation-based malformed JSON
FIREBASE_SECRET_FULL_PATH = os.environ.get("FIREBASE_SECRET_FULL_PATH")

# UPDATED: New sliding window vector index configuration (1536 dimensions)
INDEX_ENDPOINT_ID = os.environ.get("INDEX_ENDPOINT_ID", "3478417184655409152")
DEPLOYED_INDEX_ID = os.environ.get("DEPLOYED_INDEX_ID", "deployed_tafsir_sliding_1760263278167")
VECTOR_INDEX_ID = os.environ.get("VECTOR_INDEX_ID", "5746296256385253376")

GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "tafsir-simplified-sources")

# UPDATED: Embedding configuration to match new index
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 1536  # Changed from 1024 to 1536

# --- RAG CONFIGURATION ---
# Tuned for quality + latency without reranking
RAG_OPTIMIZED_CONFIG = {
    'tafsir': {
        'num_neighbors': 8,           # Retrieve more for better coverage (was 15 for reranking)
        'distance_threshold': 0.7,    # Filter out low-quality matches (cosine similarity)
        'min_chunks': 3,              # Minimum chunks to return
        'max_chunks': 6,              # Maximum chunks to avoid overwhelming
        'deduplicate': True,          # Remove duplicate verse references
    },
    'semantic': {
        'num_neighbors': 10,          # More for exploratory queries
        'distance_threshold': 0.65,   # Slightly more permissive for exploration
        'min_chunks': 3,
        'max_chunks': 8,
        'deduplicate': True,
    }
}

# Verse limit per response — uniform across all personas.
# The dynamic range map (verse_range_map.json) already handles per-verse
# token budgeting.  Persona depth affects content DENSITY, not verse count,
# so a separate persona-based limit is counterproductive.
VERSE_LIMIT = 5

# Source coverage information
# Ibn Kathir: Complete Quran (114 Surahs)
# Al-Qurtubi: Surahs 1-4 (up to Surah 4, Verse 22)

# --- Startup Validation (Fail Fast) ---
if not FIREBASE_SECRET_FULL_PATH or not INDEX_ENDPOINT_ID or not DEPLOYED_INDEX_ID or not GCS_BUCKET_NAME:
    raise ValueError("CRITICAL STARTUP ERROR: Missing required RAG environment variables")

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
TAFSIR_CHUNKS = {}
CHUNK_SOURCE_MAP = {}  # Maps chunk_id to source name
VERSE_METADATA = {}  # NEW: Stores structured metadata for direct queries
RESPONSE_CACHE = {}  # In-memory cache
SCHOLARLY_PIPELINE_VERSION = "8.0"  # Bump: dynamic verse range (30k budget, max 5 verses, per-verse output allocation)
USER_RATE_LIMITS = defaultdict(list)  # Rate limiting
ANALYTICS = defaultdict(int)  # Usage analytics

# Thread safety locks
cache_lock = threading.Lock()
rate_limit_lock = threading.Lock()
analytics_lock = threading.Lock()

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

# Metadata type keywords - COMPREHENSIVE COVERAGE
METADATA_KEYWORDS = {
    'hadith': [
        'hadith', 'narration', 'narrated', 'reported', 'transmitted',
        'prophetic tradition', 'prophet said', 'tradition', 'sunnah',
        'bukhari', 'muslim', 'abu dawud', 'tirmidhi', 'narrator'
    ],
    'scholar_citations': [
        'scholar', 'scholars', 'citation', 'citations', 'cited', 'cite',
        'quotes', 'quoted', 'quote', 'says', 'said', 'according to',
        'opinion', 'opinions', 'view', 'views', 'mentioned', 'mentions',
        'states', 'stated', 'explains', 'explained', 'commentator',
        'commentators', 'interpreter', 'mufassir', 'ulama', 'imam'
    ],
    'phrase_analysis': [
        'phrase', 'phrases', 'analysis', 'analyze', 'linguistic',
        'word', 'words', 'breakdown', 'phrase-by-phrase', 'word-by-word',
        'meaning', 'means', 'interpretation', 'translate', 'translation',
        'explain phrase', 'what does', 'definition'
    ],
    'topics': [
        'topic', 'topics', 'themes', 'theme', 'subject', 'subjects',
        'discusses', 'discuss', 'covers', 'cover', 'about', 'concerning',
        'regarding', 'main points', 'key points', 'summary'
    ],
    'cross_references': [
        'related', 'related verses', 'cross reference', 'cross references',
        'similar verses', 'similar', 'see also', 'connections', 'connected',
        'other verses', 'parallel', 'compare', 'comparison', 'like this',
        'elsewhere', 'same topic'
    ],
    'historical_context': [
        'context', 'historical', 'history', 'background', 'when',
        'why revealed', 'revelation', 'occasion', 'circumstances',
        'situation', 'event', 'happened', 'story', 'narrative',
        'time period', 'era', 'during', 'asbab al-nuzul', 'reason for revelation'
    ],
    'linguistic_analysis': [
        'linguistic', 'language', 'grammar', 'grammatical', 'arabic',
        'root', 'roots', 'etymology', 'meaning', 'derivation', 'derived',
        'structure', 'syntax', 'morphology', 'conjugation', 'verb form',
        'noun', 'particle', 'i\'rab', 'nahw', 'sarf'
    ],
    'legal_rulings': [
        'ruling', 'rulings', 'legal', 'fiqh', 'law', 'laws',
        'halal', 'haram', 'permissible', 'forbidden', 'allowed',
        'prohibited', 'jurisprudence', 'judgment', 'decree', 'fatwa',
        'mandatory', 'obligatory', 'recommended', 'disliked', 'makruh',
        'mubah', 'wajib', 'sunnah', 'mustahabb'
    ]
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

def detect_metadata_type(query: str) -> Optional[str]:
    """Detect which metadata type is requested"""
    query_normalized = normalize_query_text(query)

    for metadata_type, keywords in METADATA_KEYWORDS.items():
        if any(keyword in query_normalized for keyword in keywords):
            return metadata_type

    return None

def classify_query_enhanced(query: str) -> Dict[str, Any]:
    """
    Enhanced query classification with confidence scoring.

    Returns dict with:
    - query_type: 'metadata' | 'direct_verse' | 'semantic'
    - confidence: 0.0-1.0
    - verse_ref: (surah, verse) or None
    - metadata_type: type of metadata or None
    """
    query_normalized = normalize_query_text(query)
    verse_ref = extract_verse_reference_enhanced(query)

    # Check for metadata request
    metadata_type = detect_metadata_type(query)

    # Classification logic
    if verse_ref and metadata_type:
        # Explicit metadata query: "hadith in 2:255"
        return {
            'query_type': 'metadata',
            'confidence': 0.9,
            'verse_ref': verse_ref,
            'metadata_type': metadata_type
        }

    elif verse_ref:
        # Has verse reference, check if it's direct or semantic
        word_count = len(query_normalized.split())

        # CRITICAL FIX: Also check for verse ranges even if not pure numeric
        # This catches "Surah Al-Kahf verse 1-10" type queries
        verse_range = extract_verse_range(query)
        if verse_range:
            # Query has a verse range, classify as direct_verse
            return {
                'query_type': 'direct_verse',
                'confidence': 0.95,
                'verse_ref': verse_ref,
                'metadata_type': None
            }

        # Pure reference like "2:255" or verse range like "2:255-256"
        if re.fullmatch(r'\d{1,3}:\d{1,3}(?:-\d{1,3})?', query_normalized.strip()):
            return {
                'query_type': 'direct_verse',
                'confidence': 0.95,
                'verse_ref': verse_ref,
                'metadata_type': None
            }

        # Named verse like "ayat al kursi"
        if any(name in query_normalized for name in NAMED_VERSES.keys()):
            return {
                'query_type': 'direct_verse',
                'confidence': 0.9,
                'verse_ref': verse_ref,
                'metadata_type': None
            }

        # Short query with verse ref
        if word_count < 10:
            simple_verbs = ['show', 'read', 'give', 'tell', 'display', 'get']
            if any(verb in query_normalized for verb in simple_verbs):
                return {
                    'query_type': 'direct_verse',
                    'confidence': 0.8,
                    'verse_ref': verse_ref,
                    'metadata_type': None
                }

        # Longer query with verse - likely semantic
        return {
            'query_type': 'semantic',
            'confidence': 0.7,
            'verse_ref': verse_ref,
            'metadata_type': None
        }

    # No verse reference - semantic search
    return {
        'query_type': 'semantic',
        'confidence': 1.0,
        'verse_ref': None,
        'metadata_type': None
    }


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
    global TAFSIR_CHUNKS, CHUNK_SOURCE_MAP, VERSE_METADATA

    try:
        print(f"INFO: Initializing enhanced dual-storage system")
        storage_client = storage.Client(project=GCP_INFRASTRUCTURE_PROJECT)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)

        source_files = [
            ("processed/ibnkathir-Fatiha-Tawbah_fixed.json", "ibn-kathir"),
            ("processed/ibnkathir-Yunus-Ankabut_FINAL_fixed.json", "ibn-kathir"),
            ("processed/ibnkathir-Rum-Nas_FINAL_fixed.json", "ibn-kathir"),
            ("processed/al-Qurtubi Vol. 1_FINAL_fixed.json", "al-qurtubi"),
            ("processed/al-Qurtubi Vol. 2_FINAL_fixed.json", "al-qurtubi"),
            ("processed/al-Qurtubi Vol. 3_fixed.json", "al-qurtubi"),
            ("processed/al-Qurtubi Vol. 4_FINAL_fixed.json", "al-qurtubi")
        ]

        all_verses = []
        source_counts = {"ibn-kathir": 0, "al-qurtubi": 0}

        for file_path, source in source_files:
            try:
                blob = bucket.blob(file_path)
                if not blob.exists():
                    print(f"WARNING: File not found: {file_path}")
                    continue

                contents = blob.download_as_text()
                data = json.loads(contents)
                verses = data.get('verses', [])

                for verse in verses:
                    verse['_source'] = source

                all_verses.extend(verses)
                source_counts[source] += len(verses)
                print(f"INFO: Loaded {len(verses)} verses from {file_path}")

            except Exception as e:
                print(f"ERROR loading {file_path}: {e}")
                continue

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
            elif isinstance(verse_num, list) and verse_num:
                # Handle list format: [183, 184]
                verse_numbers_list = verse_num
                verse_num = verse_num[0]  # Use first for chunk_id
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
                # STORAGE 1: Flattened text for vector search (EXISTING)
                TAFSIR_CHUNKS[chunk_id] = full_text
                CHUNK_SOURCE_MAP[chunk_id] = "Ibn Kathir" if source == "ibn-kathir" else "al-Qurtubi"

                # STORAGE 2: Structured metadata for direct queries (NEW)
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

def enforce_persona_verse_limit(response_json: Dict, persona_name: str, requested_verses: Optional[List[Tuple[int, int]]] = None) -> Tuple[Dict, bool, int, int]:
    """
    Enforce persona-specific verse limits while prioritizing explicitly requested verses.

    Returns a tuple of:
        (response_json, trimmed_flag, original_count, final_count)
    """
    if not response_json or not isinstance(response_json, dict):
        return response_json, False, 0, 0

    verses = response_json.get('verses')
    if not verses or not isinstance(verses, list):
        return response_json, False, 0, 0

    original_count = len(verses)
    verse_limit = VERSE_LIMIT

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
            # Sanitize the explanation text to fix excessive indentation and heading format
            original_text = explanation.get('explanation', '')
            sanitized = sanitize_explanation_text(original_text)

            # FIX: Add line breaks BEFORE and AFTER **Bold** subheadings
            if '**' in sanitized:
                import re as regex_module

                original_for_debug = sanitized[:150].replace('\n', '\\n')

                # STEP 0: Normalize heading format - remove spaces after ** and before **
                # LLM sometimes generates "** Heading **" instead of "**Heading**"
                sanitized = regex_module.sub(r'\*\*\s+', '**', sanitized)  # "** Text" -> "**Text"
                sanitized = regex_module.sub(r'\s+\*\*', '**', sanitized)  # "Text **" -> "Text**"

                # STEP 1: Add \n\n AFTER **heading** (before next text)
                # Pattern: **any text** followed by optional whitespace then a letter
                sanitized = regex_module.sub(
                    r'(\*\*[^*]+\*\*)[ \t]*([A-Za-z])',
                    r'\1\n\n\2',
                    sanitized
                )

                # STEP 2: Add \n\n BEFORE **heading** (after punctuation)
                # Pattern: punctuation + optional whitespace + **Capital
                sanitized = regex_module.sub(
                    r'([.?!:;,\)\]\'\"])[ \t]*(\*\*[A-Z])',
                    r'\1\n\n\2',
                    sanitized
                )

                # STEP 3: Also handle existing single \n before/after heading
                sanitized = regex_module.sub(
                    r'(\*\*[^*]+\*\*)\n([A-Za-z])',
                    r'\1\n\n\2',
                    sanitized
                )
                sanitized = regex_module.sub(
                    r'([.?!:;,\)\]\'\"])\n(\*\*[A-Z])',
                    r'\1\n\n\2',
                    sanitized
                )

                # Cleanup: prevent triple+ newlines
                while '\n\n\n' in sanitized:
                    sanitized = sanitized.replace('\n\n\n', '\n\n')

                modified_for_debug = sanitized[:150].replace('\n', '\\n')
                print(f"🔧 HEADING FIX v5: {explanation.get('source', 'unknown')}")
                print(f"   BEFORE: {original_for_debug}")
                print(f"   AFTER:  {modified_for_debug}")

            explanation['explanation'] = sanitized
            filtered_explanations.append(explanation)

    # Update response with filtered explanations
    if filtered_explanations:
        response_json['tafsir_explanations'] = filtered_explanations
        # DEBUG MARKER: This proves the new code is running
        response_json['_debug_heading_fix'] = 'v6_newlines_preserved'
    else:
        # If no sources available, set to empty list
        response_json['tafsir_explanations'] = []

    # Also sanitize other text fields that might have indentation and heading format issues
    if response_json.get('summary'):
        sanitized_summary = sanitize_explanation_text(response_json['summary'])
        sanitized_summary = sanitize_heading_format(sanitized_summary)
        # Remove any unavailability messages from summary
        response_json['summary'] = sanitize_unavailability_text(sanitized_summary)

    if response_json.get('key_points'):
        # Apply indentation and heading format sanitization
        response_json['key_points'] = [
            sanitize_heading_format(sanitize_explanation_text(point)) if isinstance(point, str) else point
            for point in response_json['key_points']
        ]
        # Remove unavailability messages from key points
        response_json['key_points'] = [
            sanitize_unavailability_text(point) if isinstance(point, str) else point
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

DB_SCHEMA_OVERVIEW = """
PRECISE DATABASE STRUCTURE FOR TAFSIR SIMPLIFIED:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. VERSE COLLECTION (Firestore: quran_db)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Primary key: (surah: int 1-114, verse_number: int)
Fields:
  - arabic_text: string (Arabic Quran text)
  - text_saheeh_international: string (English translation)
  - surah_name: string (e.g., "Al-Baqarah")
  - verse_number: int

Access: get_verse_from_firestore(surah, verse)

Example: get_verse_from_firestore(2, 222) returns verse data

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. TAFSIR CHUNKS (In-memory: TAFSIR_CHUNKS dict)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Key format: "{source}:{surah}:{verse}"
  - source: "ibn-kathir" or "al-qurtubi"
  - Examples: "ibn-kathir:2:222", "al-qurtubi:2:187"

Value: string (unstructured tafsir commentary text)
  - Plain text tafsir commentary
  - May mention hadith, scholars, legal rulings within text
  - NOT structured as separate metadata fields

CRITICAL CONSTRAINTS:
- Ibn Kathir: ALL surahs (1-114), ALL verses - COMPLETE COVERAGE
- Al-Qurtubi: ONLY Surahs 1-4, ONLY up to verse 4:22 - LIMITED COVERAGE
  * For verse 4:23+: Al-Qurtubi DOES NOT EXIST
  * For Surahs 5-114: Al-Qurtubi DOES NOT EXIST

Access: TAFSIR_CHUNKS.get(f"ibn-kathir:{surah}:{verse}")

IMPORTANT: Tafsir text is UNSTRUCTURED. Generation LLM extracts:
- Legal rulings, hadith references, scholar citations from text

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. TOPICAL INDEX (Pre-built verse lists)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Topics mapped to verse references:
- patience/sabr: (2,153), (2,155), (2,177), (3,200), (16,127), (39,10)
- marriage: (2,187), (2,221), (2,232), (4,1), (4,19), (4,34), (30,21)
- sexual_ethics: (2,222), (2,223), (4,19), (17,32), (24,30), (24,31)
- prayer/salah: (2,238), (4,103), (20,14), (29,45)
- charity/zakat: (2,43), (2,110), (2,177), (9,60), (24,56)
- justice: (4,58), (4,135), (5,8), (16,90), (57,25)
- fasting: (2,183), (2,184), (2,185), (2,187)
- hajj: (2,196), (2,197), (3,97), (5,95), (22,27)
- wealth: (2,188), (2,275), (4,29), (17,35)
- family: (4,36), (17,23), (17,24), (31,14)
- women_rights: (2,228), (4,19), (4,34), (33,35)
- knowledge: (20,114), (35,28), (39,9), (58,11), (96,1)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RETRIEVAL LIMITS:
- Maximum 5 verses total per response
- Prioritize quality over quantity
- Prefer verses with both Ibn Kathir AND Al-Qurtubi when possible
"""

PLANNING_FEW_SHOT_EXAMPLES = """
EXAMPLE 1 - Specific Verse Query:
Query: "Explain verse 2:255"
{
  "query_intent": "Detailed explanation of Ayat al-Kursi",
  "primary_verses": [{"surah": 2, "verse": 255, "reason": "requested verse"}],
  "contextual_verses": [],
  "tafsir_sources": ["Ibn Kathir", "Al-Qurtubi"],
  "include_cross_references": true
}

EXAMPLE 2 - Fiqh Query:
Query: "what are the prohibitions within lawful marital intercourse"
{
  "query_intent": "Quranic prohibitions in halal intimacy",
  "primary_verses": [
    {"surah": 2, "verse": 222, "reason": "menstruation prohibition"},
    {"surah": 2, "verse": 223, "reason": "lawful boundaries"}
  ],
  "contextual_verses": [
    {"surah": 2, "verse": 187, "reason": "mutual respect"},
    {"surah": 4, "verse": 19, "reason": "no harm principle"}
  ],
  "tafsir_sources": ["Ibn Kathir", "Al-Qurtubi"],
  "include_cross_references": true
}

EXAMPLE 3 - Thematic Query:
Query: "What does Quran say about patience?"
{
  "query_intent": "Quranic guidance on sabr",
  "primary_verses": [
    {"surah": 2, "verse": 153, "reason": "seek help via patience"},
    {"surah": 2, "verse": 155, "reason": "testing believers"}
  ],
  "contextual_verses": [
    {"surah": 3, "verse": 200, "reason": "persevere steadfastly"},
    {"surah": 16, "verse": 127, "reason": "Allah with patient"}
  ],
  "tafsir_sources": ["Ibn Kathir"],
  "include_cross_references": true
}

EXAMPLE 4 - Al-Qurtubi Constraint (CORRECT):
Query: "Explain Surah Al-Maidah verse 1"
{
  "query_intent": "Explanation of Surah 5:1",
  "primary_verses": [{"surah": 5, "verse": 1, "reason": "requested verse"}],
  "contextual_verses": [],
  "tafsir_sources": ["Ibn Kathir"],
  "include_cross_references": true
}
NOTE: Only Ibn Kathir for Surah 5 (beyond Al-Qurtubi coverage)

EXAMPLE 5 - Avoiding Hallucinations:
Query: "Surah Al-Baqarah verse 500"
WRONG: {"primary_verses": [{"surah": 2, "verse": 500}]}
REASON: Al-Baqarah only has 286 verses - this is hallucination!
"""

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

def get_verses_by_topic(topic, max_verses=5):
    """
    Get verses tagged with specific topic

    Args:
        topic: Topic name (e.g., "patience", "marriage")
        max_verses: Maximum verses to return

    Returns:
        list: List of (surah, verse) tuples
    """
    TOPIC_INDEX = {
        'patience': [(2, 153), (2, 155), (2, 177), (3, 200), (16, 127), (39, 10)],
        'sabr': [(2, 153), (2, 155), (2, 177), (3, 200), (16, 127), (39, 10)],
        'marriage': [(2, 187), (2, 221), (2, 232), (4, 1), (4, 19), (30, 21), (4, 34)],
        'sexual_ethics': [(2, 222), (2, 223), (4, 19), (17, 32), (24, 30), (24, 31), (65, 4)],
        'prayer': [(2, 238), (4, 103), (20, 14), (29, 45), (107, 4)],
        'salah': [(2, 238), (4, 103), (20, 14), (29, 45), (107, 4)],
        'charity': [(2, 43), (2, 110), (2, 177), (9, 60), (24, 56), (70, 24)],
        'zakat': [(2, 43), (2, 110), (2, 177), (9, 60), (24, 56), (70, 24)],
        'justice': [(4, 58), (4, 135), (5, 8), (16, 90), (57, 25)],
        'fasting': [(2, 183), (2, 184), (2, 185), (2, 187), (5, 95)],
        'hajj': [(2, 196), (2, 197), (2, 198), (3, 97), (5, 95), (22, 27)],
        'wealth': [(2, 188), (2, 275), (2, 276), (4, 29), (17, 35)],
        'family': [(4, 36), (17, 23), (17, 24), (31, 14), (31, 15)],
        'women': [(2, 228), (4, 19), (4, 34), (33, 35), (49, 13)],
        'women_rights': [(2, 228), (4, 19), (4, 34), (33, 35), (49, 13)],
        'war': [(2, 190), (2, 191), (2, 193), (8, 60), (8, 61), (9, 5)],
        'knowledge': [(20, 114), (35, 28), (39, 9), (58, 11), (96, 1)],
    }

    topic_lower = topic.lower().replace('_', ' ').replace('-', ' ')

    # Try exact match
    verses = TOPIC_INDEX.get(topic_lower, TOPIC_INDEX.get(topic.lower(), []))

    return verses[:max_verses]

def validate_and_sanitize_plan(plan):
    """
    Validate and sanitize LLM's retrieval plan

    - Checks verse references exist
    - Validates Al-Qurtubi constraints
    - Enforces max verse limits
    - Rejects hallucinated verses

    Returns: validated plan dict or None if invalid
    """
    if not plan:
        return None

    validated_primary = []
    for v in plan.get('primary_verses', []):
        surah, verse = v.get('surah'), v.get('verse')
        if not surah or not verse:
            continue

        is_valid, error_msg = is_valid_verse_reference(surah, verse)

        if is_valid:
            validated_primary.append(v)
        else:
            print(f"   ⚠️  Rejected hallucinated verse: {surah}:{verse} - {error_msg}")

    validated_contextual = []
    for v in plan.get('contextual_verses', []):
        surah, verse = v.get('surah'), v.get('verse')
        if not surah or not verse:
            continue

        is_valid, error_msg = is_valid_verse_reference(surah, verse)

        if is_valid:
            validated_contextual.append(v)
        else:
            print(f"   ⚠️  Rejected hallucinated verse: {surah}:{verse} - {error_msg}")

    # If all verses rejected, return None
    if not validated_primary and not validated_contextual:
        print("   ❌ All verses rejected - LLM hallucinated non-existent references")
        return None

    # Enforce max 5 verses (matches ABSOLUTE_MAX_VERSES)
    total_verses = len(validated_primary) + len(validated_contextual)
    if total_verses > 5:
        trim_amount = total_verses - 5
        validated_contextual = validated_contextual[:-trim_amount] if trim_amount < len(validated_contextual) else []

    # Keep both tafsir sources - per-verse filtering happens in get_tafsir_for_verse()
    # Al-Qurtubi will be used for verses in Surahs 1-4:22, Ibn Kathir for all verses
    tafsir_sources = plan.get('tafsir_sources', ['Ibn Kathir'])

    # Always include both sources if Qurtubi was requested - filtering is per-verse
    if 'Al-Qurtubi' in tafsir_sources:
        all_verses = validated_primary + validated_contextual
        qurtubi_eligible = sum(1 for v in all_verses if v['surah'] <= 4 and (v['surah'] < 4 or v['verse'] <= 22))
        if qurtubi_eligible > 0:
            print(f"   📚 Qurtubi available for {qurtubi_eligible}/{len(all_verses)} verses")
        else:
            print("   ℹ️  No verses in Qurtubi range (Surahs 1-4:22), using Ibn Kathir only")

    return {
        'query_intent': plan.get('query_intent', ''),
        'primary_verses': validated_primary,
        'contextual_verses': validated_contextual,
        'tafsir_sources': tafsir_sources,
        'include_cross_references': plan.get('include_cross_references', True)
    }

def llm_plan_direct_retrieval(user_query, approach='explore'):
    """
    Use Gemini 2.5 Flash to create precise retrieval plan
    Ultra-low temperature (0.05) for deterministic, precise planning

    Args:
        user_query: User's natural language question
        approach: 'tafsir' or 'explore'/'semantic'

    Returns:
        dict: Structured retrieval plan or None if failed
    """

    planning_prompt = f"""{DB_SCHEMA_OVERVIEW}

USER QUERY: "{user_query}"
APPROACH: {approach}

TASK: Create MINIMAL, PRECISE retrieval plan.

CRITICAL CONSTRAINTS:
1. Maximum 6-8 verses total (primary + contextual)
2. ONLY verses that DIRECTLY answer query
3. Al-Qurtubi: ONLY if verse in Surahs 1-4 AND verse ≤ 22
4. DO NOT hallucinate - only real verse references
5. Quality > Quantity - fewer high-quality verses better
6. DO NOT over-retrieve

OUTPUT (strict JSON):
{{
  "query_intent": "<max 15 words>",
  "primary_verses": [
    {{"surah": <int>, "verse": <int>, "reason": "<max 10 words>"}}
  ],
  "contextual_verses": [
    {{"surah": <int>, "verse": <int>, "reason": "<max 10 words>"}}
  ],
  "tafsir_sources": ["Ibn Kathir"],
  "include_cross_references": <boolean>
}}

RULES:
- primary_verses: 2-4 MAX directly answering query
- contextual_verses: 2-4 MAX for principles/framework
- Total: 4-8 verses MAX
- Single verse query: ONLY retrieve that verse
- DO NOT add Al-Qurtubi if ANY verse beyond 4:22

{PLANNING_FEW_SHOT_EXAMPLES}

Create plan for: "{user_query}"

REMINDER: Be MINIMAL. Max 8 verses. Quality > Quantity.
"""

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
                "temperature": 0.05,  # Ultra-low for deterministic planning
                "top_k": 10,  # Limit vocabulary
                "top_p": 0.8,  # Focus on probable tokens
                "maxOutputTokens": 2048
            }
        }

        response = requests.post(
            VERTEX_ENDPOINT,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=30
        )
        response.raise_for_status()

        raw_response = response.json()
        generated_text = safe_get_nested(raw_response, "candidates", 0, "content", "parts", 0, "text")

        if not generated_text:
            print(f"   ⚠️  LLM planning returned empty response")
            return None

        plan = json.loads(generated_text)

        print(f"📋 LLM RETRIEVAL PLAN:")
        print(f"   Intent: {plan.get('query_intent', 'N/A')}")
        print(f"   Primary: {len(plan.get('primary_verses', []))} verses")
        print(f"   Contextual: {len(plan.get('contextual_verses', []))} verses")

        return plan

    except Exception as e:
        print(f"   ⚠️  LLM planning failed: {type(e).__name__}: {str(e)}")
        return None

def create_heuristic_fallback_plan(user_query, approach):
    """
    Heuristic fallback when LLM planning fails
    Uses pattern matching and topic detection
    """
    query_lower = user_query.lower()

    # Check for explicit verse reference
    verse_ref = extract_verse_reference_enhanced(user_query)
    if verse_ref:
        surah, verse = verse_ref
        return {
            'query_intent': f'Retrieve verse {surah}:{verse}',
            'primary_verses': [{'surah': surah, 'verse': verse, 'reason': 'explicitly requested'}],
            'contextual_verses': [],
            'tafsir_sources': ['Ibn Kathir', 'Al-Qurtubi'] if surah <= 4 else ['Ibn Kathir'],
            'include_cross_references': True
        }

    # Topic-based heuristic
    topic_keywords = {
        'patience': ['patience', 'sabr', 'persever', 'endur'],
        'marriage': ['marriage', 'spouse', 'wife', 'wives', 'husband', 'marital'],
        'prayer': ['prayer', 'salah', 'salat', 'pray'],
        'charity': ['charity', 'zakat', 'sadaqah', 'give', 'spend'],
    }

    for topic, keywords in topic_keywords.items():
        if any(kw in query_lower for kw in keywords):
            verses = get_verses_by_topic(topic, max_verses=5)
            if verses:
                return {
                    'query_intent': f'Topic query about {topic}',
                    'primary_verses': [{'surah': s, 'verse': v, 'reason': f'{topic} topic'} for s, v in verses[:3]],
                    'contextual_verses': [{'surah': s, 'verse': v, 'reason': f'{topic} related'} for s, v in verses[3:5]],
                    'tafsir_sources': ['Ibn Kathir'],
                    'include_cross_references': True
                }

    return None

def llm_plan_direct_retrieval_with_validation(user_query, approach='explore', max_retries=2):
    """
    LLM planning with retry logic and validation
    """
    for attempt in range(max_retries):
        try:
            plan = llm_plan_direct_retrieval(user_query, approach)

            if not plan:
                continue

            validated_plan = validate_and_sanitize_plan(plan)

            if validated_plan and (validated_plan['primary_verses'] or validated_plan['contextual_verses']):
                return validated_plan
            else:
                print(f"   ⚠️  Plan validation failed, retry {attempt + 1}/{max_retries}")

        except json.JSONDecodeError as e:
            print(f"   ❌ JSON parsing error, retry {attempt + 1}/{max_retries}")
        except Exception as e:
            print(f"   ❌ Planning error: {e}, retry {attempt + 1}/{max_retries}")

    # Heuristic fallback
    print("   🔄 LLM planning failed, using heuristic fallback")
    return create_heuristic_fallback_plan(user_query, approach)

def execute_direct_retrieval(plan):
    """
    Execute direct database lookups based on LLM's plan
    NO vector search - just direct Firestore/dict queries

    Args:
        plan: Validated retrieval plan from LLM

    Returns:
        dict: Retrieved verses, tafsir chunks, metadata
    """
    if not plan:
        return None

    all_verse_data = []
    all_tafsir_chunks = []
    verse_seen = set()

    # 1. Fetch primary verses
    primary_verses = plan.get('primary_verses', [])
    if primary_verses:
        print(f"   🎯 Fetching {len(primary_verses)} primary verses...")
    for v in primary_verses:
        surah, verse = v['surah'], v['verse']
        reason = v.get('reason', '')

        if (surah, verse) in verse_seen:
            continue
        verse_seen.add((surah, verse))

        verse_data = get_verse_from_firestore(surah, verse)
        if verse_data:
            verse_data['retrieval_reason'] = reason
            verse_data['priority'] = 'primary'
            all_verse_data.append(verse_data)

        tafsir_chunks = get_tafsir_for_verse(surah, verse, plan.get('tafsir_sources', ['Ibn Kathir']))
        all_tafsir_chunks.extend(tafsir_chunks)

    # 2. Fetch contextual verses
    contextual_verses = plan.get('contextual_verses', [])
    if contextual_verses:
        print(f"   📚 Fetching {len(contextual_verses)} contextual verses...")
    for v in contextual_verses:
        surah, verse = v['surah'], v['verse']
        reason = v.get('reason', '')

        if (surah, verse) in verse_seen:
            continue
        verse_seen.add((surah, verse))

        verse_data = get_verse_from_firestore(surah, verse)
        if verse_data:
            verse_data['retrieval_reason'] = reason
            verse_data['priority'] = 'contextual'
            all_verse_data.append(verse_data)

        tafsir_chunks = get_tafsir_for_verse(surah, verse, plan.get('tafsir_sources', ['Ibn Kathir']))
        all_tafsir_chunks.extend(tafsir_chunks)

    # 3. Get cross-references if requested
    cross_refs = []
    if plan.get('include_cross_references'):
        for verse in all_verse_data[:5]:
            refs = get_cross_references(f"{verse['surah_number']}:{verse['verse_number']}")
            cross_refs.extend(refs)

    # 4. Organize by source for context building
    context_by_source = {}
    for chunk in all_tafsir_chunks:
        source = chunk.get('source', 'Unknown')
        if source not in context_by_source:
            context_by_source[source] = []
        context_by_source[source].append(chunk['text'])

    print(f"   ✅ Retrieved: {len(all_verse_data)} verses, {len(all_tafsir_chunks)} tafsir chunks (direct DB lookups)")
    if context_by_source:
        print(f"   📊 Sources: {', '.join(context_by_source.keys())}")

    return {
        'verses': all_verse_data,
        'tafsir_chunks': all_tafsir_chunks,
        'context_by_source': context_by_source,
        'cross_references': cross_refs,
        'retrieval_plan': plan
    }

# ============================================================================
# END OF LLM-ORCHESTRATED DIRECT RETRIEVAL
# ============================================================================


def retrieve_chunks_from_neighbors(neighbors, distance_threshold=0.6):
    """
    Retrieve chunks from TAFSIR_CHUNKS based on neighbor IDs with relevance filtering.
    Handles sliding window segment IDs (e.g., ibn-kathir:1:1_0 -> ibn-kathir:1:1)

    Args:
        neighbors: List of neighbor results from vector index
        distance_threshold: Max distance to consider (0.0-1.0, lower = more similar)
                          Default 0.6 = moderately relevant

    Returns list of dicts with chunk info.
    """
    retrieved = []
    filtered_count = 0

    for neighbor in neighbors:
        # CRITICAL FIX: Filter by semantic distance BEFORE adding to results
        if neighbor.distance > distance_threshold:
            filtered_count += 1
            continue  # Skip irrelevant chunks

        neighbor_id = str(neighbor.id)

        # Remove segment suffix if present (e.g., ibn-kathir:1:1_0 -> ibn-kathir:1:1)
        base_id = neighbor_id
        if '_' in neighbor_id:
            parts = neighbor_id.rsplit('_', 1)
            if len(parts) == 2 and parts[1].isdigit():
                base_id = parts[0]

        # Lookup chunk
        chunk_text = TAFSIR_CHUNKS.get(base_id, '')
        source = CHUNK_SOURCE_MAP.get(base_id, 'Unknown')

        if chunk_text:
            retrieved.append({
                'text': chunk_text,
                'distance': neighbor.distance,
                'chunk_id': base_id,
                'source': source
            })
        else:
            # CRITICAL DEBUG: Log what's not matching
            print(f"WARNING: Chunk not found for ID: {neighbor_id} (base: {base_id})")
            print(f"   First 5 TAFSIR_CHUNKS keys: {list(TAFSIR_CHUNKS.keys())[:5]}")
            print(f"   Looking for: '{base_id}' in {len(TAFSIR_CHUNKS)} chunks")

    # Log filtering stats for debugging
    total = len(neighbors)
    kept = len(retrieved)
    if total > 0:
        print(f"   Vector search: {total} neighbors → {kept} relevant (filtered {filtered_count}, threshold={distance_threshold})")
        if kept == 0:
            closest_dist = min(n.distance for n in neighbors) if neighbors else 1.0
            print(f"   ⚠️  No chunks below threshold! Closest match: distance={closest_dist:.3f}")

    return retrieved



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
    import re
    # Pattern for ```json ... ``` or ``` ... ```
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
def expand_query(query: str, token: str, approach: str = "tafsir") -> str:
    """
    Expand user query to better match tafsir content using LLM.
    Now approach-aware: different expansions for tafsir/thematic/historical approaches.
    """
    try:
        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

        # Approach-specific expansion instructions
        approach_guidance = {
            'tafsir': """
Focus on CLASSICAL COMMENTARY while keeping the core concept:
- ALWAYS keep the main concept/term from the original query
- Add related Arabic terms (e.g., "patience" → add "sabr", "sabirun")
- Add relevant Quranic terminology that appears in verses
- Keep expansion broad enough to find foundational verses
- Avoid overly specific classical terms that might miss main verses
Example: "patience" → "patience sabr steadfastness endurance trials perseverance"
NOT: "patience grammatical analysis Ibn Kathir methodology" (too restrictive)
""",
            'thematic': """
Focus on THEMATIC CONNECTIONS that help find verses across different surahs:
- Broader Quranic themes and concepts
- Related topics that appear in multiple surahs
- Patterns and recurring principles
- Multi-verse connections and comparisons
- Holistic conceptual terms
""",
            'historical': """
Focus on HISTORICAL CONTEXT that helps find revelation circumstances:
- Asbab al-nuzul (circumstances of revelation)
- Historical events, battles, and incidents
- Chronological and sequential context
- Names of people, places, and tribes
- Pre-Islamic and early Islamic history
"""
        }

        guidance = approach_guidance.get(approach, approach_guidance['tafsir'])

        expansion_prompt = f"""You are a search query expander for an Islamic knowledge system that searches tafsir (Quranic commentary) from:
- Tafsir Ibn Kathir (complete Quran)
- Tafsir al-Qurtubi (Surahs 1-4)

INPUT QUERY: "{query}"
APPROACH: {approach.upper()}

TASK: Add 5-15 relevant Islamic/Arabic search terms to help find tafsir content.

APPROACH GUIDANCE:
{guidance}

CRITICAL RULES:
1. Keep the ENTIRE original query intact - do not truncate or modify ANY words
2. If query has verse references (e.g., "3:26-27", "Treaty of Hudaybiyyah"), preserve them EXACTLY
3. Add supplementary terms AFTER the original query
4. Total output must be under 200 tokens
5. Return ONLY the expanded query - no explanations, no metadata

OUTPUT FORMAT: [complete original query] + [5-15 supplementary Islamic/Arabic terms]

EXAMPLE:
Input: "patience"
Output: "patience sabr steadfastness endurance trials perseverance sabirun quranic patience Islamic patience reward"

Input: "Context of Treaty of Hudaybiyyah"
Output: "Context of Treaty of Hudaybiyyah sulh hudaybiyah peace treaty Prophet Muhammad Quraysh Mecca pilgrimage umrah year 6 AH companions Umar Surah Al-Fath victory"

Now expand: "{query}"
"""

        body = {
            "contents": [{"role": "user", "parts": [{"text": expansion_prompt}]}],
            "generation_config": {"temperature": 0.2, "maxOutputTokens": 300},
        }

        response = requests.post(
            VERTEX_ENDPOINT,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()

            # Safely extract expanded query from nested response
            expanded = safe_get_nested(result, "candidates", 0, "content", "parts", 0, "text")

            if expanded:
                expanded = expanded.strip()

                # VALIDATION: Prevent truncated or malformed expansions
                original_word_count = len(query.split())
                expanded_word_count = len(expanded.split())

                # Check 1: Expansion should NOT be shorter than original
                if expanded_word_count < original_word_count:
                    print(f"⚠️ REJECTED truncated expansion: '{expanded}'")
                    print(f"   Original had {original_word_count} words, expansion has {expanded_word_count}")
                    print(f"   Using original query: '{query}'")
                    return query

                # Check 2: Original query terms must be preserved
                original_words = set(word.lower() for word in query.split())
                expanded_words = set(word.lower() for word in expanded.split())

                missing_words = original_words - expanded_words
                if missing_words:
                    print(f"⚠️ REJECTED expansion missing original terms: {missing_words}")
                    print(f"   Expansion was: '{expanded}'")
                    print(f"   Using original query: '{query}'")
                    return query

                # Validation passed
                print(f"✅ Query expanded from '{query}' to '{expanded}'")
                return expanded

        print(f"WARNING: Query expansion failed, using original query")
        return query

    except Exception as e:
        print(f"WARNING: Query expansion error: {e}")
        return query

# --- UPDATED: Enhanced Multi-Source RAG Functions with 1536 dimensions ---
def perform_diversified_rag_search(query, expanded_query, embedding_model, index_endpoint, query_type="default", approach="tafsir"):
    """
    Optimized RAG Search with Vector Similarity

    Three-Stage Process:
    ====================
    Stage 1 (Vector Search): Fast vector search with distance filtering
      - Retrieve 8-10 neighbors using cosine similarity
      - Filter by distance threshold (0.7 for tafsir, 0.65 for semantic)
      - Latency: ~150-250ms

    Stage 2 (Deduplication + Capping): Quality optimization
      - Deduplicate by verse reference
      - Cap to configured limits (3-8 chunks)
      - Latency: ~10-20ms

    Stage 3 (Source Weighting): Dynamic source diversification
      - Compare Ibn Kathir vs al-Qurtubi quality scores
      - Apply dynamic weights (50/50, 70/30, or 100/0)
      - Latency: ~5-10ms

    Benefits:
    - Fast and efficient (~200-300ms total)
    - High-quality results through distance-based filtering
    - Balanced source coverage

    Args:
        query: User query text
        expanded_query: Deprecated, kept for compatibility
        embedding_model: Gemini embedding model
        index_endpoint: Vertex AI vector index endpoint
        query_type: Query classification type
        approach: 'tafsir' or 'semantic'

    Returns:
        (selected_chunks, context_by_source) tuple
    """

    # ========================================================================
    # STAGE 1: FAST RETRIEVER (High Recall)
    # ========================================================================
    perf_start = time.time()
    print(f"\n🔍 STAGE 1: Vector Retrieval (High Recall)")

    # Use ORIGINAL query for embedding (not expanded)
    # Reasoning: CrossEncoder will handle semantic matching in Stage 2
    embedding_start = time.time()
    query_embedding = embedding_model.get_embeddings(
        [query],  # CHANGED: Use original query, not expanded
        output_dimensionality=EMBEDDING_DIMENSION
    )[0].values
    embedding_time = (time.time() - embedding_start) * 1000
    print(f"   ⏱️  Query embedding: {embedding_time:.0f}ms")

    # RAG-optimized configuration
    config = RAG_OPTIMIZED_CONFIG.get(approach, RAG_OPTIMIZED_CONFIG['tafsir'])
    num_neighbors = config['num_neighbors']
    print(f"   Mode: OPTIMIZED RAG (neighbors: {num_neighbors}, threshold: {config['distance_threshold']})")

    print(f"   Query: {query[:100]}..." if len(query) > 100 else f"   Query: {query}")
    print(f"   Approach: {approach}")
    print(f"   Embedding dimension: {len(query_embedding)}")

    try:
        vector_start = time.time()
        neighbors_result = index_endpoint.find_neighbors(
            deployed_index_id=DEPLOYED_INDEX_ID,
            queries=[query_embedding],
            num_neighbors=num_neighbors
        )
        vector_time = (time.time() - vector_start) * 1000
        print(f"   ✅ Vector search returned: {len(neighbors_result[0]) if neighbors_result else 0} neighbors in {vector_time:.0f}ms")
    except Exception as e:
        print(f"   ❌ Vector search failed: {e}")
        neighbors_result = [[]]

    # Retrieve chunks with distance-based filtering
    retrieval_start = time.time()
    distance_threshold = config['distance_threshold']
    retrieved_chunks = retrieve_chunks_from_neighbors(
        neighbors_result[0],
        distance_threshold=distance_threshold
    )
    print(f"   Retrieved: {len(retrieved_chunks)} chunks (filtered by distance >= {distance_threshold}) in {(time.time() - retrieval_start) * 1000:.0f}ms")

    print(f"   ⏱️  STAGE 1 TOTAL: {(time.time() - perf_start) * 1000:.0f}ms")

    # ========================================================================
    # STAGE 2: RAG OPTIMIZATION (Deduplication + Capping)
    # ========================================================================
    stage2_start = time.time()
    print(f"\n✨ STAGE 2: RAG Optimization (Deduplication + Capping)")

    # Deduplicate by verse reference
    if config.get('deduplicate', False):
        seen_verses = set()
        deduplicated = []
        for chunk in retrieved_chunks:
            verse_key = f"{chunk.get('surah', '')}:{chunk.get('verse', '')}"
            if verse_key not in seen_verses:
                seen_verses.add(verse_key)
                deduplicated.append(chunk)
        print(f"   Deduplicated: {len(retrieved_chunks)} → {len(deduplicated)} chunks")
        retrieved_chunks = deduplicated

    # Cap to max_chunks
    max_chunks = config.get('max_chunks', 8)
    min_chunks = config.get('min_chunks', 3)

    if len(retrieved_chunks) > max_chunks:
        final_chunks = retrieved_chunks[:max_chunks]
        print(f"   Capped to max: {max_chunks} chunks")
    elif len(retrieved_chunks) < min_chunks:
        final_chunks = retrieved_chunks
        print(f"   ⚠️  Only {len(retrieved_chunks)} chunks (min: {min_chunks})")
    else:
        final_chunks = retrieved_chunks
        print(f"   Using all {len(retrieved_chunks)} chunks")

    print(f"   ⏱️  STAGE 2 TOTAL: {(time.time() - stage2_start) * 1000:.0f}ms")

    # ========================================================================
    # STAGE 3: SOURCE DIVERSIFICATION (Distance-Based Weighting)
    # ========================================================================
    print(f"\n📊 STAGE 3: Dynamic Source Weighting")

    # Categorize final chunks by source
    source_chunks = {
        'Ibn Kathir': [],
        'al-Qurtubi': []
    }

    for chunk in final_chunks:
        source = chunk['source']
        if source in source_chunks:
            source_chunks[source].append(chunk)

    # Separate chunks by source for analysis
    ibn_kathir_chunks = [c for c in final_chunks if c['source'] == 'Ibn Kathir']
    qurtubi_chunks = [c for c in final_chunks if c['source'] == 'al-Qurtubi']

    # Calculate dynamic weights based on distance scores
    if len(qurtubi_chunks) == 0:
        # al-Qurtubi has NO relevant chunks (content not in Surahs 1-4)
        weights = {'Ibn Kathir': 1.0, 'al-Qurtubi': 0.0}
        print(f"   ✅ Dynamic weights: al-Qurtubi has no chunks → Ibn Kathir 100%")

    elif len(ibn_kathir_chunks) == 0:
        # Ibn Kathir has NO relevant chunks (unlikely, but handle it)
        weights = {'Ibn Kathir': 0.0, 'al-Qurtubi': 1.0}
        print(f"   ✅ Dynamic weights: Ibn Kathir has no chunks → al-Qurtubi 100%")

    else:
        # BOTH sources have chunks - compare distance scores (higher is better)
        avg_score_ik = sum(c.get('distance', 0) for c in ibn_kathir_chunks) / len(ibn_kathir_chunks)
        avg_score_q = sum(c.get('distance', 0) for c in qurtubi_chunks) / len(qurtubi_chunks)
        score_diff = abs(avg_score_ik - avg_score_q)
        similarity_threshold = 0.05  # 5% difference in cosine similarity
        metric_name = "distance"

        if score_diff < similarity_threshold:
            # Scores similar → Use 50/50 balanced mix
            weights = {'Ibn Kathir': 0.5, 'al-Qurtubi': 0.5}
            print(f"   ✅ Dynamic weights: Similar quality (IK:{avg_score_ik:.2f}, Q:{avg_score_q:.2f} {metric_name}) → 50%/50%")

        elif avg_score_ik > avg_score_q:
            # Ibn Kathir has better matches → Favor it 70/30
            weights = {'Ibn Kathir': 0.7, 'al-Qurtubi': 0.3}
            print(f"   ✅ Dynamic weights: IK better (IK:{avg_score_ik:.2f} > Q:{avg_score_q:.2f} {metric_name}) → 70%/30%")

        else:
            # al-Qurtubi has better matches → Favor it 30/70
            weights = {'Ibn Kathir': 0.3, 'al-Qurtubi': 0.7}
            print(f"   ✅ Dynamic weights: Q better (Q:{avg_score_q:.2f} > IK:{avg_score_ik:.2f} {metric_name}) → 30%/70%")

    # Build final context by source
    context_by_source = {}
    for source_name, chunks in source_chunks.items():
        if chunks:
            # Extract text for context
            context_by_source[source_name] = [chunk['text'] for chunk in chunks]
        else:
            context_by_source[source_name] = []

    print(f"   Final distribution: IK={len(source_chunks['Ibn Kathir'])}, Q={len(source_chunks['al-Qurtubi'])}")

    return final_chunks, context_by_source

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

    # Add source content
    for source_name, chunks in context_by_source.items():
        if chunks:
            section = f"--- {source_name.upper()} ---\n"
            section += "\n\n".join(chunks)
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
    Two-stage scholarly retrieval: deterministic baseline + Gemini enrichment.

    1. Deterministic keyword matcher runs instantly (guaranteed baseline)
    2. Gemini planning call runs with retries (catches nuanced connections)
    3. Results are MERGED: union of pointers, deduplicated, capped at 7

    Returns (scholarly_ctx_string, badges_list, pipeline_info).
    """
    start = time.time()
    print(f"\n  [SCHOLARLY-2STAGE] === Starting two-stage scholarly retrieval ===")

    def _fallback(reason):
        print(f"  [SCHOLARLY-2STAGE] FALLBACK: {reason}")
        ctx = _get_scholarly_context_for_prompt(query, verse_data)
        badges = _get_scholarly_sources_metadata(query, verse_data)
        return ctx, badges, f"single_stage_fallback: {reason}"

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

        # --- Stage 1: Deterministic baseline (instant, guaranteed) ---
        det_plan = plan_scholarly_retrieval_deterministic(
            surah_number, verse_start, verse_end,
            verse_text[:300], ibn_kathir_summary
        )
        det_pointers = det_plan["pointers"]
        print(f"  [SCHOLARLY-2STAGE] Deterministic: {len(det_pointers)} pointers — {det_plan['reasoning']}")

        # --- Stage 2: Gemini enrichment (API call with retries) ---
        gemini_pointers = []
        gemini_status = "skipped"
        try:
            planning_prompt = build_scholarly_planning_prompt(
                surah_number, verse_start, verse_end,
                verse_text[:300], ibn_kathir_summary, query
            )
            gemini_plan = plan_scholarly_retrieval(planning_prompt)
            if gemini_plan and gemini_plan.get("pointers"):
                gemini_pointers = gemini_plan["pointers"]
                gemini_status = f"ok: {len(gemini_pointers)} pointers"
                print(f"  [SCHOLARLY-2STAGE] Gemini: {len(gemini_pointers)} pointers — {gemini_plan.get('reasoning', '')}")
            else:
                gemini_status = "empty_response"
                print(f"  [SCHOLARLY-2STAGE] Gemini: returned no pointers")
        except Exception as ge:
            gemini_status = f"error: {type(ge).__name__}"
            print(f"  [SCHOLARLY-2STAGE] Gemini error: {type(ge).__name__}: {str(ge)[:200]}")

        # --- Merge: union of pointers, deduplicated, capped at 10 ---
        seen = set()
        merged_pointers = []
        for p in det_pointers + gemini_pointers:
            if p not in seen and len(merged_pointers) < 10:
                seen.add(p)
                merged_pointers.append(p)

        print(f"  [SCHOLARLY-2STAGE] Merged: {len(merged_pointers)} pointers (det={len(det_pointers)}, gemini={len(gemini_pointers)}, unique={len(seen)})")
        for p in merged_pointers:
            src = "both" if p in det_pointers and p in gemini_pointers else ("det" if p in det_pointers else "gemini")
            print(f"    -> [{src}] {p}")

        # --- Resolve merged pointers ---
        resolved = resolve_scholarly_pointers(merged_pointers)

        if not resolved["excerpts"]:
            return _fallback(f"All {len(merged_pointers)} merged pointers resolved to empty")

        # Format for generation prompt
        scholarly_ctx = format_scholarly_excerpts_for_prompt(resolved)
        badges = resolved["sources_used"]

        duration = (time.time() - start) * 1000
        pipeline_info = f"two_stage: {len(resolved['excerpts'])} excerpts, {len(badges)} badges in {duration:.0f}ms (gemini={gemini_status})"
        print(f"  [SCHOLARLY-2STAGE] SUCCESS: {pipeline_info}")
        print(f"  [SCHOLARLY-2STAGE] Badges: {[b['key'] for b in badges]}")
        return scholarly_ctx, badges, pipeline_info

    except Exception as e:
        print(f"  [SCHOLARLY-2STAGE] EXCEPTION: {type(e).__name__}: {str(e)[:300]}")
        traceback.print_exc()
        return _fallback(f"Exception: {type(e).__name__}: {str(e)[:200]}")


# ============================================================================
# UPDATED: PERSONA-ADAPTIVE CLARITY-ENHANCED PROMPT WITH NEW PROFILE DATA
# ============================================================================

def build_enhanced_prompt(query, context_by_source, user_profile, arabic_text=None, cross_refs=None, query_type="default", verse_data=None, approach="tafsir", scholarly_context=""):
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

    content += "---\n*Generated by Tafsir Simplified*"
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

            # Check if cache is still valid (7 days TTL for tafsir)
            created_at = cache_data.get('created_at')
            if created_at:
                age_days = (datetime.now(timezone.utc) - created_at).total_seconds() / 86400
                if age_days > 7:  # Cache expired after 7 days
                    print(f"💾 Cache expired for key {cache_key[:8]}... (age: {age_days:.1f} days)")
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
                    created_at = cache_data.get('created_at')
                    if created_at:
                        age_days = (datetime.now(timezone.utc) - created_at).total_seconds() / 86400
                        if age_days <= 7:
                            print(f"💾 Using DEFAULT cached response (age: {age_days:.1f} days)")

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
        return jsonify({"error": "Profile not found"}), 404
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
    "streak_3": {"name": "Getting Started", "description": "Maintained a 3-day learning streak", "icon": "fire", "category": "streak", "threshold": 3},
    "streak_7": {"name": "Week of Wisdom", "description": "7 consecutive days of engagement", "icon": "calendar", "category": "streak", "threshold": 7},
    "streak_30": {"name": "Month of Devotion", "description": "30-day learning streak", "icon": "crown", "category": "streak", "threshold": 30},
    "explore_10": {"name": "Curious Mind", "description": "Explored 10 unique verses", "icon": "search", "category": "exploration", "threshold": 10},
    "explore_100": {"name": "Deep Diver", "description": "Explored 100 unique verses", "icon": "compass", "category": "exploration", "threshold": 100},
    "explore_500": {"name": "Quranic Scholar", "description": "Explored 500 unique verses", "icon": "graduation", "category": "exploration", "threshold": 500},
    "surahs_10": {"name": "Surah Explorer", "description": "Explored verses from 10 different surahs", "icon": "globe", "category": "exploration", "threshold": 10},
    "surahs_50": {"name": "Quran Traveler", "description": "Explored verses from 50 different surahs", "icon": "rocket", "category": "exploration", "threshold": 50},
    "reflect_1": {"name": "First Reflection", "description": "Wrote your first reflection", "icon": "pen", "category": "reflection", "threshold": 1},
    "reflect_10": {"name": "Thoughtful Heart", "description": "Wrote 10 reflections", "icon": "heart", "category": "reflection", "threshold": 10},
    "reflect_50": {"name": "Reflection Master", "description": "Wrote 50 reflections", "icon": "brain", "category": "reflection", "threshold": 50},
    "collection_complete": {"name": "Collection Complete", "description": "Completed a themed verse collection", "icon": "book", "category": "special", "threshold": 1},
    "plan_complete": {"name": "Journey Complete", "description": "Finished a reading plan", "icon": "star", "category": "special", "threshold": 1},
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

        # Count annotations
        try:
            ann_query = users_db.collection("users").document(uid).collection("annotations").limit(51)
            annotation_count = sum(1 for _ in ann_query.stream())
        except Exception:
            annotation_count = 0

        # Count completed collections
        collection_progress = data.get("collection_progress", {})
        completed_collections = sum(
            1 for cid, cp in collection_progress.items()
            if len(cp.get("explored", [])) >= len(next((c["verses"] for c in THEMED_COLLECTIONS if c["id"] == cid), []))
        )

        # Count completed plans
        active_plan = data.get("active_plan", {})
        completed_plans = 1 if active_plan.get("completed_at") else 0

        newly_earned = []
        best_streak = max(streak_current, streak_longest)

        checks = {
            "streak_3": best_streak >= 3,
            "streak_7": best_streak >= 7,
            "streak_30": best_streak >= 30,
            "explore_10": total_verses >= 10,
            "explore_100": total_verses >= 100,
            "explore_500": total_verses >= 500,
            "surahs_10": total_surahs >= 10,
            "surahs_50": total_surahs >= 50,
            "reflect_1": annotation_count >= 1,
            "reflect_10": annotation_count >= 10,
            "reflect_50": annotation_count >= 50,
            "collection_complete": completed_collections >= 1,
            "plan_complete": completed_plans >= 1,
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
# READING PLANS
# ============================================================================

READING_PLANS = [
    {
        "id": "patience_7",
        "title": "7-Day Patience Journey",
        "description": "Explore how the Quran teaches patience through hardship, gratitude, and trust in Allah's plan",
        "duration_days": 7,
        "category": "Spiritual Growth",
        "days": [
            {"day": 1, "title": "The Promise of Patience", "verse": [2, 155], "prompt": "What trial in your life right now could be a hidden blessing?"},
            {"day": 2, "title": "Hidden Wisdom", "verse": [2, 216], "prompt": "Think of a past difficulty that turned out to be good for you."},
            {"day": 3, "title": "No Soul Overburdened", "verse": [2, 286], "prompt": "What burden feels heavy today? How does knowing Allah's promise change that?"},
            {"day": 4, "title": "Persevere and Excel", "verse": [3, 200], "prompt": "Where in your life do you need more steadfastness?"},
            {"day": 5, "title": "Patience in Action", "verse": [31, 17], "prompt": "How can you practice active patience — not just enduring, but growing?"},
            {"day": 6, "title": "Reward Beyond Measure", "verse": [39, 10], "prompt": "What goodness are you investing in that you haven't seen the reward for yet?"},
            {"day": 7, "title": "Ease After Hardship", "verse": [94, 5], "prompt": "Reflect on your journey this week. How has your understanding of patience deepened?"},
        ],
    },
    {
        "id": "spiritual_stations",
        "title": "Spiritual Stations",
        "description": "A 14-day journey through the stations of the soul, inspired by Ibn al-Qayyim's Madarij al-Salikin",
        "duration_days": 14,
        "category": "Spiritual Growth",
        "days": [
            {"day": 1, "title": "Awakening", "verse": [6, 122], "prompt": "What moment first awakened your spiritual curiosity?"},
            {"day": 2, "title": "Insight", "verse": [24, 35], "prompt": "Where do you see Allah's light in your daily life?"},
            {"day": 3, "title": "Purpose", "verse": [51, 56], "prompt": "How does the purpose of creation shape your priorities?"},
            {"day": 4, "title": "Resolve", "verse": [29, 69], "prompt": "What spiritual goal requires more determination from you?"},
            {"day": 5, "title": "Repentance", "verse": [39, 53], "prompt": "What would it feel like to truly let go of past mistakes?"},
            {"day": 6, "title": "Remembrance", "verse": [13, 28], "prompt": "When during your day do you feel closest to Allah?"},
            {"day": 7, "title": "Fear & Awe", "verse": [8, 2], "prompt": "What does healthy reverence for Allah look like in your life?"},
            {"day": 8, "title": "Hope", "verse": [7, 56], "prompt": "What hope sustains you through difficult moments?"},
            {"day": 9, "title": "Devotion", "verse": [6, 162], "prompt": "How can your daily routines become acts of devotion?"},
            {"day": 10, "title": "Trust", "verse": [65, 3], "prompt": "What are you struggling to trust Allah with right now?"},
            {"day": 11, "title": "Patience", "verse": [2, 155], "prompt": "How has this journey changed your relationship with difficulty?"},
            {"day": 12, "title": "Gratitude", "verse": [14, 7], "prompt": "Name three blessings you usually overlook."},
            {"day": 13, "title": "Submission", "verse": [3, 159], "prompt": "What does true surrender to Allah mean for you today?"},
            {"day": 14, "title": "Contentment", "verse": [89, 27], "prompt": "Reflect on your 14-day journey. What station resonated most deeply?"},
        ],
    },
    {
        "id": "ramadan_30",
        "title": "Ramadan Essentials",
        "description": "30 days of verses covering fasting, charity, night prayer, and spiritual renewal",
        "duration_days": 30,
        "category": "Seasonal",
        "days": [
            {"day": 1, "title": "Fasting Prescribed", "verse": [2, 183], "prompt": "What intention are you setting for this month of fasting?"},
            {"day": 2, "title": "Month of Quran", "verse": [2, 185], "prompt": "How will you deepen your relationship with the Quran this month?"},
            {"day": 3, "title": "Dua is Heard", "verse": [2, 186], "prompt": "What is the one dua you want to focus on this Ramadan?"},
            {"day": 4, "title": "Charity Multiplied", "verse": [2, 261], "prompt": "Who in your community could benefit from your generosity?"},
            {"day": 5, "title": "Taqwa", "verse": [2, 197], "prompt": "How is fasting building your God-consciousness?"},
            {"day": 6, "title": "Night Prayer", "verse": [73, 8], "prompt": "What would it mean to devote even a few minutes of the night to Allah?"},
            {"day": 7, "title": "Gratitude", "verse": [14, 7], "prompt": "What blessing has fasting helped you appreciate?"},
            {"day": 8, "title": "Patience", "verse": [2, 155], "prompt": "What is fasting teaching you about self-control?"},
            {"day": 9, "title": "Remembrance", "verse": [33, 41], "prompt": "How can you increase your dhikr throughout the day?"},
            {"day": 10, "title": "Forgiveness", "verse": [39, 53], "prompt": "Is there someone you need to forgive — including yourself?"},
            {"day": 11, "title": "Brotherhood", "verse": [49, 10], "prompt": "How can you strengthen a bond with a fellow believer today?"},
            {"day": 12, "title": "Honoring Parents", "verse": [17, 23], "prompt": "What can you do for your parents today?"},
            {"day": 13, "title": "Purification", "verse": [87, 14], "prompt": "What habit or thought pattern do you want to purify this month?"},
            {"day": 14, "title": "Justice", "verse": [5, 8], "prompt": "Where can you stand up for fairness in your daily life?"},
            {"day": 15, "title": "Midpoint Reflection", "verse": [13, 28], "prompt": "Halfway through — how has your heart changed?"},
            {"day": 16, "title": "Provision", "verse": [11, 6], "prompt": "How does trusting Allah's provision change your relationship with money?"},
            {"day": 17, "title": "Laylat al-Qadr", "verse": [97, 1], "prompt": "What would you ask for in a night worth a thousand months?"},
            {"day": 18, "title": "Sincerity", "verse": [112, 1], "prompt": "How can you make your worship more sincere?"},
            {"day": 19, "title": "The Unseen", "verse": [2, 3], "prompt": "What does believing in the unseen mean practically?"},
            {"day": 20, "title": "Success", "verse": [23, 1], "prompt": "What does true success look like beyond worldly measures?"},
            {"day": 21, "title": "Allah's Names", "verse": [59, 22], "prompt": "Which name of Allah speaks to you most right now?"},
            {"day": 22, "title": "Best Example", "verse": [33, 21], "prompt": "Which quality of the Prophet do you most want to embody?"},
            {"day": 23, "title": "Inner Change", "verse": [13, 11], "prompt": "What one internal change would transform your life?"},
            {"day": 24, "title": "Trust", "verse": [9, 51], "prompt": "What would full trust in Allah's decree look like?"},
            {"day": 25, "title": "Knowledge", "verse": [20, 114], "prompt": "What have you learned this Ramadan that surprised you?"},
            {"day": 26, "title": "Ease", "verse": [94, 5], "prompt": "Where has Allah brought you ease that you didn't expect?"},
            {"day": 27, "title": "Light", "verse": [24, 35], "prompt": "How is your spiritual light growing this month?"},
            {"day": 28, "title": "Return", "verse": [2, 156], "prompt": "How does remembering our return to Allah shape your priorities?"},
            {"day": 29, "title": "Mercy", "verse": [7, 56], "prompt": "How can you be a vessel of Allah's mercy to others?"},
            {"day": 30, "title": "Farewell", "verse": [3, 200], "prompt": "As Ramadan ends, what commitment will you carry forward?"},
        ],
    },
    {
        "id": "prophets_10",
        "title": "Stories of the Prophets",
        "description": "10 days exploring the lives and lessons of the prophets mentioned in the Quran",
        "duration_days": 10,
        "category": "Knowledge",
        "days": [
            {"day": 1, "title": "Adam — The First Human", "verse": [2, 30], "prompt": "What does being Allah's khalifah (steward) on earth mean for your daily choices?"},
            {"day": 2, "title": "Nuh — Steadfastness", "verse": [11, 36], "prompt": "When have you held firm to truth despite others doubting you?"},
            {"day": 3, "title": "Ibrahim — Surrender", "verse": [2, 131], "prompt": "What would it mean to submit to Allah as completely as Ibrahim?"},
            {"day": 4, "title": "Yusuf — Beauty Through Trial", "verse": [12, 86], "prompt": "How do you maintain hope when life feels unjust?"},
            {"day": 5, "title": "Musa — Courage", "verse": [20, 25], "prompt": "What daunting task are you being called to undertake?"},
            {"day": 6, "title": "Dawud — Gratitude in Power", "verse": [34, 10], "prompt": "How do you use your strengths in gratitude to Allah?"},
            {"day": 7, "title": "Sulayman — Wisdom", "verse": [27, 19], "prompt": "How does gratitude for blessings shape the way you lead and serve?"},
            {"day": 8, "title": "Yunus — Repentance in Darkness", "verse": [21, 87], "prompt": "When have you called out to Allah from a dark place?"},
            {"day": 9, "title": "Isa — The Word of God", "verse": [3, 45], "prompt": "What does the miraculous nature of Isa teach about Allah's power?"},
            {"day": 10, "title": "Muhammad — Mercy to All", "verse": [33, 21], "prompt": "How can you embody the prophetic example in your relationships?"},
        ],
    },
    {
        "id": "foundations_7",
        "title": "Foundations of Faith",
        "description": "7 days exploring the core pillars of Islamic belief through the Quran",
        "duration_days": 7,
        "category": "Knowledge",
        "days": [
            {"day": 1, "title": "Tawhid — Oneness of Allah", "verse": [112, 1], "prompt": "How does believing in One God simplify your life?"},
            {"day": 2, "title": "Angels — Unseen Servants", "verse": [2, 285], "prompt": "How does knowing angels surround you affect your behavior?"},
            {"day": 3, "title": "Divine Books — Guidance Revealed", "verse": [2, 2], "prompt": "What role does the Quran play in your daily decisions?"},
            {"day": 4, "title": "Messengers — Examples to Follow", "verse": [33, 21], "prompt": "Which prophetic quality do you most want to develop?"},
            {"day": 5, "title": "The Last Day — Accountability", "verse": [3, 185], "prompt": "If today were your last, what would you change?"},
            {"day": 6, "title": "Divine Decree — Trusting the Plan", "verse": [9, 51], "prompt": "What aspect of your life do you need to surrender to Allah's qadr?"},
            {"day": 7, "title": "Ihsan — Excellence in Faith", "verse": [2, 112], "prompt": "What does it mean to worship Allah as though you see Him?"},
        ],
    },
]


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
        "duration_days": plan["duration_days"],
        "category": plan["category"],
        "days": days,
    }), 200


@app.route("/reading-plans/<plan_id>/progress", methods=["GET"])
@firebase_auth_required
def get_plan_progress(plan_id):
    """Get user's progress on a reading plan."""
    uid = request.user["uid"]
    try:
        user_doc = users_db.collection("users").document(uid).get()
        data = user_doc.to_dict() if user_doc.exists else {}
        active_plan = data.get("active_plan", {})

        if active_plan.get("plan_id") != plan_id:
            return jsonify({"active": False, "plan_id": plan_id}), 200

        # Look up today's verse from the plan data
        plan = next((p for p in READING_PLANS if p["id"] == plan_id), None)
        current_day = active_plan.get("current_day", 1)
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
                "reflection": day_data.get("reflection", ""),
            }

        return jsonify({
            "active": True,
            "plan_id": plan_id,
            "current_day": current_day,
            "completed_days": active_plan.get("completed_days", []),
            "started_at": active_plan.get("started_at"),
            "completed_at": active_plan.get("completed_at"),
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
            user_ref.set({
                "active_plan": {
                    "plan_id": plan_id,
                    "current_day": 1,
                    "completed_days": [],
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "completed_at": None,
                }
            }, merge=True)
            return jsonify({"status": "started", "plan_id": plan_id, "current_day": 1}), 200

        elif action == "complete_day":
            day_num = data.get("day")
            if not day_num or day_num < 1 or day_num > plan["duration_days"]:
                return jsonify({"error": "Invalid day number"}), 400

            user_doc = user_ref.get()
            user_data = user_doc.to_dict() if user_doc.exists else {}
            active = user_data.get("active_plan", {})

            if active.get("plan_id") != plan_id:
                return jsonify({"error": "This plan is not active"}), 400

            completed = active.get("completed_days", [])
            if day_num not in completed:
                completed.append(day_num)

            next_day = min(day_num + 1, plan["duration_days"])
            is_complete = len(completed) >= plan["duration_days"]

            update_data = {
                "active_plan": {
                    "plan_id": plan_id,
                    "current_day": next_day,
                    "completed_days": completed,
                    "started_at": active.get("started_at"),
                    "completed_at": datetime.now(timezone.utc).isoformat() if is_complete else None,
                }
            }
            user_ref.set(update_data, merge=True)

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
                    'content': data.get('content', ''),
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
                'content': data.get('content', ''),
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
                annotation_obj['highlighted_text'] = data.get('highlighted_text')
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

        # Base annotation data
        annotation_data = {
            'type': annotation_type,
            'content': content,
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
            annotation_data['highlighted_text'] = highlighted_text
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
            update_data['content'] = data['content']
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
            content = data.get('content', '').lower()

            # Text search
            if query_text and query_text in content:
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
                    'content': data.get('content'),
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

        # Validate and normalize approach FIRST (before validation)
        # MERGE: historical + thematic + explore → semantic (same underlying mechanism)
        if approach in ['historical', 'thematic', 'explore']:
            original_approach = data.get('approach')
            approach = 'semantic'  # Internal routing uses 'semantic'
            print(f"📍 Normalized approach: {original_approach} → semantic")
        elif approach not in ['tafsir', 'semantic']:
            approach = 'tafsir'  # Default fallback

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

            # Hard cap: maximum 5 verses per query (matches ABSOLUTE_MAX_VERSES)
            if verse_count > 5:
                return jsonify({
                    'error': 'verse_range_too_large',
                    'message': f'Please narrow your range to 5 verses or less.\n\nYou requested {verse_count} verses ({surah}:{start_verse}-{end_verse}).\n\nTry smaller ranges like:\n- {surah}:{start_verse}-{start_verse+4}',
                    'requested_verses': verse_count,
                    'max_verses': 5,
                    'suggestions': [
                        f'{surah}:{start_verse}-{min(start_verse+4, end_verse)}'
                    ]
                }), 400

            # Dynamic budget enforcement — prevent oversized prompts
            from services.token_budget_service import compute_max_end_verse
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

        print(f"\n{'='*70}")
        print(f"📥 QUERY: {query}")
        print(f"🎯 APPROACH: {approach.upper()}")
        print(f"{'='*70}")

        # ENHANCED CLASSIFICATION
        classification = classify_query_enhanced(query)
        query_type = classification['query_type']
        confidence = classification['confidence']
        verse_ref = classification['verse_ref']
        metadata_type = classification['metadata_type']

        print(f"🎯 Type: {query_type} (confidence: {confidence:.0%})")
        if verse_ref:
            print(f"   Verse: {verse_ref[0]}:{verse_ref[1]}")
        # Add logging for verse ranges
        verse_range = extract_verse_range(query)
        if verse_range:
            print(f"   📖 Verse Range Detected: {verse_range[0]}:{verse_range[1]}-{verse_range[2]}")
        if metadata_type:
            print(f"   Metadata: {metadata_type}")

        # ===================================================================
        # ROUTE 1: METADATA QUERY (Direct lookup → AI formatting)
        # ===================================================================
        if query_type == 'metadata' and verse_ref:
            print("🚀 ROUTE 1: Direct Metadata Lookup → AI Formatting")

            surah, verse = verse_ref

            # Validate
            is_valid, msg = validate_verse_reference(surah, verse)
            if not is_valid:
                return jsonify({'error': msg}), 400

            # Direct lookup
            verse_metadata_list = get_verse_metadata_direct(surah, verse)

            if not verse_metadata_list:
                print(f"⚠️  No metadata found, falling back to semantic search")
                query_type = 'semantic'  # Fallback
            else:
                # Get verse text from Firestore
                verse_data = get_verse_from_firestore(surah, verse)

                # Build targeted context from direct lookup
                context_by_source = {}
                for item in verse_metadata_list:
                    source_name = item['source']
                    metadata = item['metadata']

                    # Extract the specific metadata requested
                    context_parts = []

                    if metadata_type == 'hadith' or metadata_type == 'all':
                        hadith_refs = metadata.get('hadith_references', [])
                        if hadith_refs:
                            context_parts.append(f"HADITH REFERENCES:\n" + "\n".join(str(h) for h in hadith_refs))

                    if metadata_type == 'scholar_citations' or metadata_type == 'all':
                        citations = metadata.get('scholar_citations', [])
                        if citations:
                            context_parts.append(f"SCHOLAR CITATIONS:\n" + "\n".join(str(c) for c in citations))

                    if metadata_type == 'phrase_analysis' or metadata_type == 'all':
                        phrases = metadata.get('phrase_analysis', [])
                        if phrases:
                            phrase_text = []
                            for p in phrases:
                                if isinstance(p, dict):
                                    phrase_text.append(f"{p.get('phrase', '')}: {p.get('analysis', '')}")
                                else:
                                    phrase_text.append(str(p))
                            context_parts.append(f"PHRASE ANALYSIS:\n" + "\n".join(phrase_text))

                    if metadata_type == 'topics' or metadata_type == 'all':
                        topics = metadata.get('topics', [])
                        if topics:
                            topic_text = []
                            for t in topics:
                                if isinstance(t, dict):
                                    if t.get('topic_header'):
                                        topic_text.append(f"**{t['topic_header']}**")
                                    if t.get('commentary'):
                                        topic_text.append(t['commentary'])
                            context_parts.append(f"TOPICS:\n" + "\n".join(topic_text))

                    if metadata_type == 'cross_references' or metadata_type == 'all':
                        cross_refs = metadata.get('cross_references', [])
                        if cross_refs:
                            context_parts.append(f"RELATED VERSES:\n" + ", ".join(cross_refs))

                    if metadata_type == 'historical_context' or metadata_type == 'all':
                        historical = metadata.get('historical_context', [])
                        if historical:
                            historical_text = []
                            for h in historical:
                                if isinstance(h, dict):
                                    historical_text.append(str(h))
                                else:
                                    historical_text.append(h)
                            context_parts.append(f"HISTORICAL CONTEXT:\n" + "\n".join(historical_text))

                    if metadata_type == 'linguistic_analysis' or metadata_type == 'all':
                        linguistic = metadata.get('linguistic_analysis', [])
                        if linguistic:
                            linguistic_text = []
                            for l in linguistic:
                                if isinstance(l, dict):
                                    linguistic_text.append(str(l))
                                else:
                                    linguistic_text.append(l)
                            context_parts.append(f"LINGUISTIC ANALYSIS:\n" + "\n".join(linguistic_text))

                    if metadata_type == 'legal_rulings' or metadata_type == 'all':
                        legal = metadata.get('legal_rulings', [])
                        if legal:
                            legal_text = []
                            for lr in legal:
                                if isinstance(lr, dict):
                                    legal_text.append(str(lr))
                                else:
                                    legal_text.append(lr)
                            context_parts.append(f"LEGAL RULINGS:\n" + "\n".join(legal_text))

                    # Add commentary if no specific metadata found
                    if not context_parts and metadata.get('commentary'):
                        context_parts.append(metadata['commentary'])

                    context_by_source[source_name] = ["\n\n".join(context_parts)] if context_parts else []

                # Get user profile for persona
                user_profile = get_user_profile(user_id)

                # Build prompt for AI formatting (skip RAG, use direct context)
                arabic_text = get_arabic_text_from_verse_data(verse_data) if verse_data else None
                scholarly_ctx, scholarly_badges, scholarly_pipeline = _get_scholarly_context_two_stage(query, verse_data, context_by_source)
                prompt = build_enhanced_prompt(query, context_by_source, user_profile,
                                             arabic_text, None, 'metadata', verse_data, approach, scholarly_ctx)

                # Get auth token
                credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                auth_req = GoogleRequest()
                credentials.refresh(auth_req)
                token = credentials.token

                # Generate AI-formatted response
                VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

                body = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generation_config": {
                        "response_mime_type": "application/json",
                        "temperature": 0.2,
                        "maxOutputTokens": 65536  # Increased from 8192 to prevent truncation of detailed responses
                    },
                }

                # Add retry logic for Gemini API calls with exponential backoff for rate limits
                max_retries = 4  # More retries for rate limiting
                response = None

                for attempt in range(max_retries):
                    # Exponential backoff: 2s, 4s, 8s, 16s
                    retry_delay = 2 ** (attempt + 1)
                    try:
                        response = requests.post(
                            VERTEX_ENDPOINT,
                            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                            json=body,
                            timeout=120  # Increased from 30s to match Gemini's actual response times
                        )
                        response.raise_for_status()
                        break  # Success, exit retry loop
                    except requests.Timeout:
                        if attempt == max_retries - 1:
                            print(f"❌ Gemini API timeout after {max_retries} attempts")
                            return jsonify({
                                "error": "AI service timeout. Please try again or simplify your query.",
                                "retry": True,
                                "error_type": "timeout"
                            }), 503
                        print(f"⚠️ Gemini timeout on attempt {attempt + 1}, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                    except requests.HTTPError as e:
                        status_code = response.status_code if response else 500
                        # Handle rate limiting (429) with exponential backoff
                        if status_code == 429:
                            if attempt == max_retries - 1:
                                print(f"❌ Gemini API rate limited after {max_retries} attempts")
                                return jsonify({
                                    "error": "AI service is busy. Please wait a moment and try again.",
                                    "retry": True,
                                    "error_type": "rate_limit",
                                    "retry_after": 30
                                }), 429
                            print(f"⚠️ Gemini rate limited (429), retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue
                        # Handle service unavailable (503)
                        if status_code == 503:
                            if attempt == max_retries - 1:
                                raise
                            print(f"⚠️ Gemini service unavailable, retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue
                        # For other errors, raise immediately
                        raise

                # Parse response
                raw_response = response.json()

                # Safely extract generated text from nested response
                generated_text = safe_get_nested(raw_response, "candidates", 0, "content", "parts", 0, "text")

                if generated_text:
                    final_json = extract_json_from_response(generated_text)

                    if not final_json:
                        print(f"❌ Failed to extract JSON from Gemini response (Route 1)")
                        print(f"Response preview: {generated_text[:500]}...")
                        return jsonify({
                            "error": "AI returned malformed response",
                            "details": "The AI response could not be parsed as JSON. Try rephrasing your query or making it more specific.",
                            "error_type": "json_parse_error"
                        }), 500

                    final_json["query_type"] = "direct_metadata"
                    final_json["verse_reference"] = f"{surah}:{verse}"

                    # Filter out unavailable sources before caching and returning
                    final_json = filter_unavailable_sources(final_json)

                    # Add scholarly source attribution metadata (from two-stage resolver)
                    final_json["scholarly_sources"] = scholarly_badges
                    final_json["_scholarly_pipeline"] = scholarly_pipeline

                    # Keep only requested verse(s) in main list; move extras to cross references
                    final_json = keep_requested_verses_primary(
                        final_json,
                        verse_data,
                        requested_verses=[(surah, verse)]
                    )

                    persona_name = user_profile.get('persona', 'practicing_muslim')
                    final_json, trimmed, original_count, final_count = enforce_persona_verse_limit(
                        final_json,
                        persona_name,
                        requested_verses=[(surah, verse)]
                    )
                    if trimmed:
                        print(f"   ℹ️  Trimmed verses to {final_count}/{original_count} for persona {persona_name}")

                    # Log verse count for monitoring
                    verse_count = len(final_json.get('verses', []))
                    verse_limit = VERSE_LIMIT
                    if verse_count > verse_limit:
                        print(f"   ⚠️  VERSE LIMIT EXCEEDED: {verse_count} verses returned (limit: {verse_limit})")
                    else:
                        print(f"   ✅ Verse count: {verse_count}/{verse_limit}")

                    # Cache the response (Route 1)
                    with cache_lock:
                        RESPONSE_CACHE[cache_key] = final_json
                        if len(RESPONSE_CACHE) > 1000:
                            # Prune oldest 20% of cache
                            keys_to_remove = list(RESPONSE_CACHE.keys())[:200]
                            for key in keys_to_remove:
                                RESPONSE_CACHE.pop(key, None)

                    # Store in Firestore cache for tafsir queries with verse references
                    if approach == 'tafsir' and extract_verse_reference_enhanced(query):
                        store_tafsir_cache(query, user_profile, final_json, approach)
                        print(f"💾 Stored tafsir response in Firestore cache")

                    # Track explored verse and generate recommendations
                    if user_id:
                        _track_explored_verse(user_id, surah, verse)
                        _check_and_award_badges(user_id)
                    final_json["recommendations"] = _generate_recommendations(surah, verse, final_json, user_id)

                    print(f"✅ Metadata formatted by AI from {len(verse_metadata_list)} source(s)")
                    return jsonify(final_json), 200
                else:
                    # Fallback to structured response
                    print(f"⚠️  Gemini response structure unexpected, using fallback")
                    response = format_metadata_response(verse_ref, metadata_type or 'all', verse_metadata_list)
                    return jsonify(response), 200

        # ===================================================================
        # ROUTE 2: DIRECT VERSE QUERY (Direct lookup → AI formatting)
        # ===================================================================
        if query_type == 'direct_verse' and verse_ref:
            print("🚀 ROUTE 2: Direct Verse Query → AI Formatting")

            # Check if query contains a verse range
            verse_range = extract_verse_range(query)
            if verse_range:
                surah, start_verse, end_verse = verse_range
                verse = start_verse  # For verse_reference formatting
                print(f"   Detected verse range: {surah}:{start_verse}-{end_verse}")
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
                # Fetch all verses in the range
                verses_data_list = get_verses_range_from_firestore(surah, start_verse, end_verse)
                # CRITICAL FIX: Use all verses, not just the first one
                verse_data = verses_data_list[0] if verses_data_list else None  # Only for validation
                verses_for_ai = verses_data_list  # Pass ALL verses to AI
            else:
                # Single verse - use existing function
                verses_data_list = None
                verse_data = get_verse_from_firestore(surah, start_verse)
                verses_for_ai = verse_data  # Single verse

            if not verse_data:
                print(f"⚠️  Verse(s) not found in Firestore, trying semantic search")
                query_type = 'semantic'  # Fallback
            else:
                # CRITICAL LOGGING: Verify we're getting the correct verse data
                print(f"✅ Firestore returned: Surah {verse_data.get('surah_number')}, Verse {verse_data.get('verse_number')}, Name: {verse_data.get('surah_name')}")
                print(f"   English preview: {verse_data.get('english', '')[:100]}...")
                if verse_data.get('surah_number') != surah or verse_data.get('verse_number') != start_verse:
                    print(f"❌❌❌ MISMATCH! Requested {surah}:{start_verse} but got {verse_data.get('surah_number')}:{verse_data.get('verse_number')}")

                # Get metadata via direct lookup (with range support)
                verse_metadata_list = get_verse_metadata_direct(surah, start_verse, end_verse=end_verse if start_verse != end_verse else None)

                if not verse_metadata_list:
                    print(f"⚠️  No tafsir found for {surah}:{start_verse}" + (f"-{end_verse}" if start_verse != end_verse else ""))
                    print(f"⚠️  Trying semantic search as fallback")
                    query_type = 'semantic'  # Fallback
                else:
                    # Build context from direct lookup (handles both single verses and ranges)
                    context_by_source = {}

                    for item in verse_metadata_list:
                        source_name = item['source']

                        # Handle verse ranges (new structure) or single verse (backwards compatible)
                        verses_data = item.get('verses', [])
                        if not verses_data and item.get('metadata'):
                            # Backwards compatibility: single verse
                            verses_data = [{'verse_number': start_verse, 'metadata': item['metadata']}]

                        # Extract comprehensive tafsir from all verses in range
                        context_parts = []

                        for verse_info in verses_data:
                            metadata = verse_info['metadata']
                            verse_num = verse_info.get('verse_number', start_verse)

                            # Add verse marker for ranges
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

                                        # Add phrase analysis from topics
                                        if topic.get('phrase_analysis'):
                                            for phrase in topic['phrase_analysis']:
                                                if isinstance(phrase, dict):
                                                    if phrase.get('phrase'):
                                                        context_parts.append(f"Phrase: {phrase['phrase']}")
                                                    if phrase.get('analysis'):
                                                        context_parts.append(f"Analysis: {phrase['analysis']}")

                                        # Add hadith from topics
                                        if topic.get('hadith_references'):
                                            context_parts.append(f"Hadith: {topic['hadith_references']}")

                            # Commentary (al-Qurtubi style)
                            elif metadata.get('commentary'):
                                context_parts.append(metadata['commentary'])

                                # Add phrase analysis
                                if metadata.get('phrase_analysis'):
                                    for phrase in metadata['phrase_analysis']:
                                        if isinstance(phrase, str):
                                            context_parts.append(phrase)

                                # Add scholar citations
                                if metadata.get('scholar_citations'):
                                    for citation in metadata['scholar_citations']:
                                        if isinstance(citation, str):
                                            context_parts.append(citation)

                        context_by_source[source_name] = ["\n\n".join(context_parts)] if context_parts else []

                    # Get user profile for persona
                    user_profile = get_user_profile(user_id)

                    # Build prompt for AI formatting (skip RAG, use direct context)
                    arabic_text = get_arabic_text_from_verse_data(verse_data)

                    # Get cross refs from first verse's metadata
                    cross_refs = []
                    if verse_metadata_list:
                        first_item = verse_metadata_list[0]
                        if first_item.get('verses'):
                            cross_refs = first_item['verses'][0]['metadata'].get('cross_references', [])
                        elif first_item.get('metadata'):
                            cross_refs = first_item['metadata'].get('cross_references', [])

                    # CRITICAL FIX: Pass correct verse data to prompt
                    scholarly_ctx, scholarly_badges, scholarly_pipeline = _get_scholarly_context_two_stage(query, verses_for_ai, context_by_source)
                    prompt = build_enhanced_prompt(query, context_by_source, user_profile,
                                                 arabic_text, cross_refs, 'direct_verse', verses_for_ai, approach, scholarly_ctx)

                    # CRITICAL LOGGING: Verify verse_data being passed to Gemini
                    if isinstance(verses_for_ai, list):
                        print(f"🔍 About to call Gemini with {len(verses_for_ai)} verses: {verses_for_ai[0].get('surah_number')}:{verses_for_ai[0].get('verse_number')}-{verses_for_ai[-1].get('verse_number')} ({verses_for_ai[0].get('surah_name')})")
                    else:
                        print(f"🔍 About to call Gemini with single verse: {verses_for_ai.get('surah_number')}:{verses_for_ai.get('verse_number')} ({verses_for_ai.get('surah_name')})")

                    # Get auth token
                    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                    auth_req = GoogleRequest()
                    credentials.refresh(auth_req)
                    token = credentials.token

                    # Generate AI-formatted response
                    VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

                    body = {
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "generation_config": {
                            "response_mime_type": "application/json",
                            "temperature": 0.2,
                            "maxOutputTokens": 65536  # Increased from 8192 to prevent truncation of detailed tafsir responses
                        },
                    }

                    # Add retry logic for Gemini API calls with exponential backoff for rate limits
                    max_retries = 4  # More retries for rate limiting

                    for attempt in range(max_retries):
                        # Exponential backoff: 2s, 4s, 8s, 16s
                        retry_delay = 2 ** (attempt + 1)
                        try:
                            response = requests.post(
                                VERTEX_ENDPOINT,
                                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                                json=body,
                                timeout=120  # Increased to match Gemini's actual response times
                            )
                            response.raise_for_status()
                            break  # Success
                        except requests.Timeout:
                            if attempt == max_retries - 1:
                                print(f"❌ Gemini timeout in Route 2 after {max_retries} attempts")
                                return jsonify({
                                    "error": "AI service timeout",
                                    "retry": True,
                                    "error_type": "timeout"
                                }), 503
                            print(f"⚠️ Retry {attempt + 1}/{max_retries} in {retry_delay}s...")
                            time.sleep(retry_delay)
                        except requests.HTTPError as e:
                            status_code = response.status_code if response else 500
                            # Handle rate limiting (429) with exponential backoff
                            if status_code == 429:
                                if attempt == max_retries - 1:
                                    print(f"❌ Gemini API rate limited after {max_retries} attempts")
                                    return jsonify({
                                        "error": "AI service is busy. Please wait a moment and try again.",
                                        "retry": True,
                                        "error_type": "rate_limit",
                                        "retry_after": 30
                                    }), 429
                                print(f"⚠️ Gemini rate limited (429), retrying in {retry_delay}s...")
                                time.sleep(retry_delay)
                                continue
                            # Handle service unavailable (503)
                            if status_code == 503:
                                if attempt == max_retries - 1:
                                    raise
                                print(f"⚠️ Gemini service unavailable, retrying in {retry_delay}s...")
                                time.sleep(retry_delay)
                                continue
                            # For other errors, raise immediately
                            raise

                    # Parse response
                    raw_response = response.json()

                    # Check finish reason to understand why generation stopped
                    finish_reason = safe_get_nested(raw_response, "candidates", 0, "finishReason")
                    if finish_reason and finish_reason not in ("STOP", "MAX_TOKENS"):
                        print(f"⚠️ Gemini finishReason: {finish_reason} — response may be blocked or incomplete")
                        if finish_reason == "SAFETY":
                            return jsonify({
                                "error": "The AI could not generate a response for this query. Please try rephrasing.",
                                "error_type": "content_blocked"
                            }), 400

                    # Safely extract generated text from nested response
                    generated_text = safe_get_nested(raw_response, "candidates", 0, "content", "parts", 0, "text")

                    if generated_text:
                        final_json = extract_json_from_response(generated_text)

                        if not final_json:
                            print(f"❌ Failed to extract JSON from Gemini response")
                            print(f"Response preview: {generated_text[:500]}...")
                            return jsonify({
                                "error": "AI returned malformed response",
                                "details": "The AI response could not be parsed as JSON. Try rephrasing your query or making it more specific.",
                                "error_type": "json_parse_error"
                            }), 500
                        final_json["query_type"] = "direct_verse"
                        final_json["verse_reference"] = f"{surah}:{verse}"

                        # Filter out unavailable sources before caching and returning
                        final_json = filter_unavailable_sources(final_json)

                        # Add scholarly source attribution metadata (from two-stage resolver)
                        final_json["scholarly_sources"] = scholarly_badges
                        final_json["_scholarly_pipeline"] = scholarly_pipeline

                        # Keep only requested verse(s) in main list; move extras to cross references
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
                            requested_verses=requested_range
                        )
                        if trimmed:
                            print(f"   ℹ️  Trimmed verses to {final_count}/{original_count} for persona {persona_name}")

                        # Log verse count for monitoring
                        verse_count = len(final_json.get('verses', []))
                        verse_limit = VERSE_LIMIT
                        if verse_count > verse_limit:
                            print(f"   ⚠️  VERSE LIMIT EXCEEDED: {verse_count} verses returned (limit: {verse_limit})")
                        else:
                            print(f"   ✅ Verse count: {verse_count}/{verse_limit}")

                        # Cache the response (Route 2)
                        with cache_lock:
                            RESPONSE_CACHE[cache_key] = final_json
                            if len(RESPONSE_CACHE) > 1000:
                                # Prune oldest 20% of cache
                                keys_to_remove = list(RESPONSE_CACHE.keys())[:200]
                                for key in keys_to_remove:
                                    RESPONSE_CACHE.pop(key, None)

                        # Store in Firestore cache for tafsir queries
                        if approach == 'tafsir':
                            store_tafsir_cache(query, user_profile, final_json, approach)
                            print(f"💾 Stored direct verse response in Firestore cache")

                        # Track explored verse and generate recommendations
                        if user_id:
                            _track_explored_verse(user_id, surah, start_verse, end_verse)
                            _check_and_award_badges(user_id)
                        final_json["recommendations"] = _generate_recommendations(surah, start_verse, final_json, user_id)

                        print(f"✅ Direct verse formatted by AI from {len(verse_metadata_list)} source(s)")
                        return jsonify(final_json), 200
                    else:
                        # Fallback to structured response
                        print(f"⚠️  Gemini response structure unexpected, using fallback")
                        response = build_direct_verse_response(verse_data, verse_metadata_list)
                        return jsonify(response), 200

        # ===================================================================
        # ROUTE 3: LLM-ORCHESTRATED DIRECT RETRIEVAL (No Vector Search)
        # ===================================================================
        if query_type == 'semantic':
            print("🚀 ROUTE 3: LLM-Orchestrated Direct Retrieval")

            # NOTE: user_profile and cache_key already set at top of function
            # No need to check cache again - already checked above

            # Get auth token (needed for both LLM planning and generation)
            credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            auth_req = GoogleRequest()
            credentials.refresh(auth_req)
            token = credentials.token

            # ================================================================
            # STEP 1: LLM Planning - What to Retrieve
            # ================================================================
            stage_start = time.time()
            retrieval_plan = llm_plan_direct_retrieval_with_validation(query, approach, max_retries=2)
            perf_metrics['stages']['llm_planning'] = (time.time() - stage_start) * 1000

            retrieved_data = None
            context_by_source = {}
            verse_data = None
            arabic_text = None
            cross_refs = []

            if retrieval_plan:
                # ================================================================
                # STEP 2: Execute Direct DB Retrieval
                # ================================================================
                stage_start = time.time()
                retrieved_data = execute_direct_retrieval(retrieval_plan)
                perf_metrics['stages']['direct_retrieval'] = (time.time() - stage_start) * 1000

                if retrieved_data and len(retrieved_data.get('verses', [])) > 0:
                    # Success: Use LLM-planned retrieval
                    context_by_source = retrieved_data['context_by_source']
                    cross_refs = retrieved_data.get('cross_references', [])

                    # Get verse data for ALL verses (not just first)
                    if retrieved_data['verses']:
                        # Pass all verses to prompt builder for complete Arabic text
                        verse_data = retrieved_data['verses']
                        # Keep first verse's arabic for backward compatibility
                        arabic_text = retrieved_data['verses'][0].get('arabic')

                    print(f"   ✅ LLM-orchestrated retrieval: {len(retrieved_data['verses'])} verses, {len(retrieved_data.get('tafsir_chunks', []))} chunks")
                    print(f"   ⏱️  Planning: {perf_metrics['stages']['llm_planning']:.0f}ms, Retrieval: {perf_metrics['stages']['direct_retrieval']:.0f}ms")
                else:
                    # LLM plan retrieved nothing - fallback to vector search
                    print("   ⚠️  LLM-orchestrated retrieval returned no results, falling back to vector search")
                    retrieval_plan = None

            if not retrieval_plan or not retrieved_data:
                # ================================================================
                # FALLBACK: Vector Search RAG (if LLM planning fails)
                # ================================================================
                print("   🔄 Fallback: Using vector search RAG")

                # Prepare query
                if verse_ref:
                    surah_num, verse_num = verse_ref
                    verse_data = get_verse_from_firestore(surah_num, verse_num)
                    if verse_data:
                        arabic_text = get_arabic_text_from_verse_data(verse_data)
                else:
                    verse_data = None
                    arabic_text = None

                rag_query = query
                rag_query_type = "default"
                cross_refs = get_cross_references(rag_query)

                # Initialize vector search models
                stage_start = time.time()
                embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
                endpoint_resource_name = f"projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
                index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_resource_name)
                perf_metrics['stages']['model_init'] = (time.time() - stage_start) * 1000

                # Vector search
                stage_start = time.time()
                selected_chunks, context_by_source = perform_diversified_rag_search(
                    rag_query, rag_query, embedding_model, index_endpoint, rag_query_type, approach
                )
                perf_metrics['stages']['rag_search'] = (time.time() - stage_start) * 1000
                perf_metrics['chunks_retrieved'] = len(selected_chunks)

                print(f"   Retrieved {len(selected_chunks)} chunks (fallback RAG) in {perf_metrics['stages']['rag_search']:.0f}ms")

            # ================================================================
            # STEP 3: Build Prompt and Generate Response
            # ================================================================
            # Build prompt (approach-aware)
            stage_start = time.time()
            rag_query_type = "default"
            scholarly_ctx, scholarly_badges, scholarly_pipeline = _get_scholarly_context_two_stage(query, verse_data, context_by_source)
            prompt = build_enhanced_prompt(query, context_by_source, user_profile,
                                         arabic_text, cross_refs, rag_query_type, verse_data, approach, scholarly_ctx)
            perf_metrics['stages']['prompt_building'] = (time.time() - stage_start) * 1000

            # Truncate prompt if needed to fit token limits (50K max - typical: 6K-25K)
            stage_start = time.time()
            prompt = truncate_context_if_needed(prompt, max_tokens=50000)
            perf_metrics['stages']['prompt_truncation'] = (time.time() - stage_start) * 1000

            # Generate response with retry logic for malformed JSON
            VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

            max_retries = 5  # INCREASED from 3 to 5 for better reliability
            final_json = None
            generated_text = None

            llm_start = time.time()
            for json_attempt in range(max_retries):
                # Progressive temperature reduction on retries (0.3 → 0.1, never 0.0 to avoid robotic responses)
                temperature = max(0.1, round(0.3 - (json_attempt * 0.05), 2))

                body = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generation_config": {
                        "response_mime_type": "application/json",
                        "temperature": temperature,
                        "maxOutputTokens": 65536  # Gemini 2.5 Flash supports up to 65K output tokens (vs 8K in 2.0)
                    },
                }

                try:
                    # Add retry logic for HTTP-level Gemini API calls with exponential backoff
                    max_http_retries = 4  # More retries for rate limiting

                    for http_attempt in range(max_http_retries):
                        # Exponential backoff: 2s, 4s, 8s, 16s
                        retry_delay = 2 ** (http_attempt + 1)
                        try:
                            response = requests.post(
                                VERTEX_ENDPOINT,
                                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                                json=body,
                                timeout=120  # Increased to match Gemini's actual response times
                            )
                            response.raise_for_status()
                            break  # Success
                        except requests.Timeout:
                            if http_attempt == max_http_retries - 1:
                                print(f"❌ Gemini HTTP timeout after {max_http_retries} attempts")
                                return jsonify({
                                    "error": "AI service timeout",
                                    "retry": True,
                                    "error_type": "timeout"
                                }), 503
                            print(f"⚠️ HTTP retry {http_attempt + 1}/{max_http_retries} in {retry_delay}s...")
                            time.sleep(retry_delay)
                        except requests.HTTPError as e:
                            status_code = response.status_code if response else 500
                            # Handle rate limiting (429) with exponential backoff
                            if status_code == 429:
                                if http_attempt == max_http_retries - 1:
                                    print(f"❌ Gemini API rate limited after {max_http_retries} attempts")
                                    return jsonify({
                                        "error": "AI service is busy. Please wait a moment and try again.",
                                        "retry": True,
                                        "error_type": "rate_limit",
                                        "retry_after": 30
                                    }), 429
                                print(f"⚠️ Gemini rate limited (429), retrying in {retry_delay}s...")
                                time.sleep(retry_delay)
                                continue
                            # Handle service unavailable (503)
                            if status_code == 503:
                                if http_attempt == max_http_retries - 1:
                                    raise
                                print(f"⚠️ Gemini service unavailable, retrying in {retry_delay}s...")
                                time.sleep(retry_delay)
                                continue
                            # For other errors, raise immediately
                            raise

                    # Parse response
                    raw_response = response.json()

                    # Check finish reason to understand why generation stopped
                    finish_reason = safe_get_nested(raw_response, "candidates", 0, "finishReason")
                    if finish_reason and finish_reason not in ("STOP", "MAX_TOKENS"):
                        print(f"⚠️ Gemini finishReason: {finish_reason} — response may be blocked or incomplete")
                        if finish_reason == "SAFETY":
                            return jsonify({
                                "error": "The AI could not generate a response for this query. Please try rephrasing.",
                                "error_type": "content_blocked"
                            }), 400

                    # Safely extract generated text from nested response
                    generated_text = safe_get_nested(raw_response, "candidates", 0, "content", "parts", 0, "text")

                    if generated_text:
                        final_json = extract_json_from_response(generated_text)

                        if final_json:
                            if json_attempt > 0:
                                print(f"✅ JSON parsing succeeded on retry {json_attempt + 1}")
                            break  # Success!
                        else:
                            print(f"⚠️  JSON attempt {json_attempt + 1}/{max_retries}: Failed to parse JSON")
                            if json_attempt < max_retries - 1:
                                print(f"   Retrying with lower temperature ({temperature})...")
                                time.sleep(0.5)  # Brief pause before retry
                    else:
                        print(f"⚠️  JSON attempt {json_attempt + 1}/{max_retries}: Empty or malformed response from Gemini")
                        if json_attempt < max_retries - 1:
                            time.sleep(0.5)

                except requests.exceptions.Timeout:
                    print(f"⚠️  JSON attempt {json_attempt + 1}/{max_retries}: Timeout")
                    if json_attempt < max_retries - 1:
                        time.sleep(1)
                except Exception as e:
                    print(f"⚠️  JSON attempt {json_attempt + 1}/{max_retries}: Error - {e}")
                    if json_attempt < max_retries - 1:
                        time.sleep(0.5)

            # Check if we got valid JSON after retries
            if not final_json:
                print(f"❌ Failed to extract JSON after {max_retries} attempts (Route 3)")
                if generated_text:
                    print(f"Last response preview: {generated_text[:500]}...")
                return jsonify({
                    "error": "AI returned malformed response",
                    "details": f"The AI response could not be parsed as JSON after {max_retries} attempts. This may be due to query complexity or temporary service issues.",
                    "suggestion": "Try rephrasing your query, making it more specific, or try again in a moment.",
                    "error_type": "json_parse_error"
                }), 500

            # Continue with valid JSON
            try:
                # Enhance with verse data
                if verse_data:
                    # verse_data can be a list (from LLM retrieval) or a single dict (from fallback)
                    if isinstance(verse_data, list):
                        # LLM-orchestrated retrieval: verse_data is already a list of verse dicts
                        final_json["verses"] = [{
                            "surah": v.get('surah_number') or v.get('surah'),
                            "surah_name": v.get('surah_name', ''),
                            "verse_number": str(v.get('verse_number') or v.get('verse', '')),
                            "text_saheeh_international": v.get('english', ''),
                            "arabic_text": v.get('arabic', '')
                        } for v in verse_data]
                    else:
                        # Single verse dict (from fallback path)
                        final_json["verses"] = [{
                            "surah": verse_data['surah_number'],
                            "surah_name": verse_data['surah_name'],
                            "verse_number": str(verse_data['verse_number']),
                            "text_saheeh_international": verse_data['english'],
                            "arabic_text": verse_data['arabic']
                        }]
                    final_json["query_type"] = "semantic_with_verse"
                else:
                    final_json["query_type"] = "thematic"

                # Validate
                is_valid, validation_msg = validate_response(final_json)
                if not is_valid:
                    print(f"⚠️  Validation failed: {validation_msg}")
                    print(f"⚠️  Response keys: {list(final_json.keys())}")
                    print(f"⚠️  Has tafsir_explanations: {'tafsir_explanations' in final_json}")
                    if 'tafsir_explanations' in final_json:
                        explanations = final_json.get('tafsir_explanations', [])
                        print(f"⚠️  Number of explanations: {len(explanations)}")
                        for i, exp in enumerate(explanations[:3]):  # Show first 3
                            exp_text = exp.get('explanation', '')
                            print(f"⚠️  Explanation {i+1} length: {len(exp_text)}, preview: {exp_text[:100]}")
                    print(f"⚠️  Has metadata.extraction_error: {final_json.get('metadata', {}).get('extraction_error')}")
                    return jsonify({"error": "Response quality not met"}), 500

                # Add approach suggestion if user might benefit from different approach
                intent = detect_query_intent(query)
                if intent['suggested_approach'] and intent['suggested_approach'] != approach and intent['confidence'] == 'high':
                    final_json['approach_suggestion'] = {
                        'suggested': intent['suggested_approach'],
                        'reason': intent['reason'],
                        'current': approach
                    }
                    print(f"💡 Suggesting {intent['suggested_approach']} approach (current: {approach})")

                # Filter out unavailable sources before caching and returning
                final_json = filter_unavailable_sources(final_json)

                # Add scholarly source attribution metadata (from two-stage resolver)
                final_json["scholarly_sources"] = scholarly_badges
                final_json["_scholarly_pipeline"] = scholarly_pipeline

                # Keep only requested verse(s) in main list; move extras to cross references
                final_json = keep_requested_verses_primary(
                    final_json,
                    verse_data,
                    requested_verses=[(verse_ref[0], verse_ref[1])] if verse_ref else None
                )

                persona_name = user_profile.get('persona', 'practicing_muslim')
                requested_list = [(verse_ref[0], verse_ref[1])] if verse_ref else None
                final_json, trimmed, original_count, final_count = enforce_persona_verse_limit(
                    final_json,
                    persona_name,
                    requested_verses=requested_list
                )
                if trimmed:
                    print(f"   ℹ️  Trimmed verses to {final_count}/{original_count} for persona {persona_name}")

                # Log verse count for monitoring
                verse_count = len(final_json.get('verses', []))
                verse_limit = VERSE_LIMIT
                if verse_count > verse_limit:
                    print(f"   ⚠️  VERSE LIMIT EXCEEDED: {verse_count} verses returned (limit: {verse_limit})")
                    perf_metrics['verse_limit_exceeded'] = True
                else:
                    print(f"   ✅ Verse count: {verse_count}/{verse_limit}")
                perf_metrics['verse_count'] = verse_count

                # Cache with thread safety (in-memory)
                with cache_lock:
                    RESPONSE_CACHE[cache_key] = final_json
                    if len(RESPONSE_CACHE) > 1000:
                        keys_to_remove = list(RESPONSE_CACHE.keys())[:200]
                        for key in keys_to_remove:
                            RESPONSE_CACHE.pop(key, None)  # Use pop to avoid KeyError

                # Store semantic/explore response in Firestore for long-term caching
                if approach == 'semantic':
                    print(f"💾 Storing semantic/explore query to Firestore cache...")
                    store_tafsir_cache(query, user_profile, final_json, approach)

                # Performance summary
                perf_metrics['stages']['llm_generation'] = (time.time() - llm_start) * 1000
                perf_metrics['llm_calls'] = json_attempt + 1
                total_time = (time.time() - perf_metrics['total_start']) * 1000

                print(f"\n{'='*70}")
                print(f"⏱️  PERFORMANCE SUMMARY - ROUTE 3 (Semantic Search)")
                print(f"{'='*70}")
                print(f"Total Request Time: {total_time:.0f}ms")
                print(f"\nStage Breakdown:")
                for stage, timing in perf_metrics['stages'].items():
                    print(f"  • {stage}: {timing:.0f}ms ({timing/total_time*100:.1f}%)")
                print(f"\nMetrics:")
                print(f"  • Chunks retrieved: {perf_metrics['chunks_retrieved']}")
                print(f"  • LLM calls: {perf_metrics['llm_calls']}")
                print(f"  • Verses returned: {perf_metrics.get('verse_count', 0)}")
                if perf_metrics.get('verse_limit_exceeded'):
                    print(f"  • ⚠️  VERSE LIMIT EXCEEDED")
                print(f"  • Route: Semantic Search (Full RAG)")
                print(f"  • Approach: {perf_metrics['approach']}")
                print(f"{'='*70}")

                print(f"✅ Semantic response generated in {total_time:.0f}ms")
                return jsonify(final_json), 200

            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"❌ Response structure error: {type(e).__name__} - {e}")
                if 'generated_text' in locals():
                    print(f"Response preview: {generated_text[:500]}...")
                return jsonify({
                    "error": "AI returned unexpected response format",
                    "details": "The response structure didn't match our expected format. This may be due to query complexity.",
                    "suggestion": "Try simplifying your query or breaking it into smaller parts.",
                    "error_type": "structure_error"
                }), 500

    except requests.exceptions.Timeout:
        return jsonify({"error": "AI service timed out"}), 504
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500


# --- REPLACED: Health Check ---
@app.route("/health", methods=["GET"])
def health_check_enhanced():
    """Enhanced health check with hybrid system status"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "chunks_loaded": len(TAFSIR_CHUNKS),
        "metadata_entries": len(VERSE_METADATA),
        "cache_size": len(RESPONSE_CACHE),
        "system_type": "RAG-optimized",
        "query_routes": {
            "metadata": {
                "description": "Direct lookup + AI formatting",
                "example": "hadith in 2:255",
                "avg_time": "1-2s",
                "llm_calls": 1
            },
            "direct_verse": {
                "description": "Direct lookup + AI formatting",
                "example": "2:255",
                "avg_time": "1-2s",
                "llm_calls": 1
            },
            "semantic": {
                "description": "Full RAG pipeline",
                "example": "explain charity",
                "avg_time": "3-5s",
                "llm_calls": 2
            }
        },
        "personas_available": list(PERSONAS.keys()),
        "source_coverage": {
            "Ibn Kathir": "Complete Quran (114 Surahs)",
            "al-Qurtubi": "Surahs 1-4 (up to 4:22)"
        }
    }), 200



# --- Debug Endpoint ---
@app.route('/debug-index', methods=['GET'])
def debug_index():
    """Debug endpoint to verify index configuration"""
    try:
        # Count chunks by source using the mapping
        ibn_kathir_count = sum(1 for source in CHUNK_SOURCE_MAP.values() if source == 'Ibn Kathir')
        qurtubi_count = sum(1 for source in CHUNK_SOURCE_MAP.values() if source == 'al-Qurtubi')

        # Sample IDs from each source
        ibn_kathir_samples = [k for k, v in CHUNK_SOURCE_MAP.items() if v == 'Ibn Kathir'][:5]
        qurtubi_samples = [k for k, v in CHUNK_SOURCE_MAP.items() if v == 'al-Qurtubi'][:5]

        # Sample text previews
        ibn_kathir_text = {k: TAFSIR_CHUNKS[k][:200] + '...' for k in ibn_kathir_samples if k in TAFSIR_CHUNKS}
        qurtubi_text = {k: TAFSIR_CHUNKS[k][:200] + '...' for k in qurtubi_samples if k in TAFSIR_CHUNKS}

        return jsonify({
            "status": "success",
            "configuration": {
                "index_endpoint_id": INDEX_ENDPOINT_ID,
                "deployed_index_id": DEPLOYED_INDEX_ID,
                "vector_index_id": VECTOR_INDEX_ID,
                "embedding_model": EMBEDDING_MODEL,
                "embedding_dimension": EMBEDDING_DIMENSION
            },
            "chunks_loaded": {
                "total": len(TAFSIR_CHUNKS),
                "ibn_kathir": ibn_kathir_count,
                "al_qurtubi": qurtubi_count
            },
            "personas_available": list(PERSONAS.keys()),
            "source_coverage": {
                "Ibn Kathir": "Complete Quran (all 114 Surahs)",
                "al-Qurtubi": "Surahs 1-4 only (up to Surah 4:22)"
            },
            "sample_ids": {
                "ibn_kathir": ibn_kathir_samples,
                "al_qurtubi": qurtubi_samples
            },
            "sample_text_previews": {
                "ibn_kathir": ibn_kathir_text,
                "al_qurtubi": qurtubi_text
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

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
        query_type = classification['query_type']
        confidence = classification['confidence']
        verse_ref = classification['verse_ref']
        metadata_type = classification['metadata_type']

        log_step("3. Query Classification", {
            "query_type": query_type,
            "confidence": f"{confidence:.0%}",
            "verse_ref": f"{verse_ref[0]}:{verse_ref[1]}" if verse_ref else None,
            "metadata_type": metadata_type
        })
        log_timing("3. Query Classification", time.time() - step_start)

        # STEP 4: Verse Range Extraction
        if verse_ref:
            step_start = time.time()
            verse_range = extract_verse_range(query)
            log_step("4. Verse Range Extraction", {
                "has_range": verse_range is not None,
                "range": f"{verse_range[0]}:{verse_range[1]}-{verse_range[2]}" if verse_range else None,
                "is_multi_verse": verse_range and verse_range[1] != verse_range[2] if verse_range else False
            })
            log_timing("4. Verse Range Extraction", time.time() - step_start)

        # STEP 5: Route Determination
        if query_type == 'metadata' and verse_ref:
            route = "ROUTE 1: Metadata Query (Direct lookup → AI formatting)"
        elif query_type == 'direct_verse' and verse_ref:
            route = "ROUTE 2: Direct Verse Query (Direct lookup → AI formatting)"
        else:
            route = "ROUTE 3: Semantic Search (Full RAG pipeline)"

        log_step("5. Route Determination", {
            "route": route,
            "will_use_vector_search": "ROUTE 3" in route
        })

        # ===================================================================
        # ROUTE 1: METADATA QUERY
        # ===================================================================
        if query_type == 'metadata' and verse_ref:
            log_step("ROUTE 1 EXECUTION START", {"route": "Metadata Query"})

            surah, verse = verse_ref

            # Validation
            step_start = time.time()
            is_valid, msg = validate_verse_reference(surah, verse)
            log_step("6. Verse Validation", {
                "surah": surah,
                "verse": verse,
                "is_valid": is_valid,
                "message": msg if not is_valid else "Valid"
            })
            log_timing("6. Verse Validation", time.time() - step_start)

            if not is_valid:
                trace["error"] = msg
                return jsonify(trace), 400

            # Direct metadata lookup
            step_start = time.time()
            verse_metadata_list = get_verse_metadata_direct(surah, verse)
            log_step("7. Direct Metadata Lookup", {
                "found_metadata": bool(verse_metadata_list),
                "num_sources": len(verse_metadata_list) if verse_metadata_list else 0,
                "sources": [item['source'] for item in verse_metadata_list] if verse_metadata_list else []
            })
            log_timing("7. Direct Metadata Lookup", time.time() - step_start)

            if not verse_metadata_list:
                log_step("FALLBACK TO ROUTE 3", {
                    "reason": "No metadata found in direct lookup"
                })
                query_type = 'semantic'  # Will fall through to ROUTE 3
            else:
                # Get verse data
                step_start = time.time()
                verse_data = get_verse_from_firestore(surah, verse)
                log_step("8. Fetch Verse from Firestore", {
                    "has_verse_data": bool(verse_data),
                    "arabic_text_length": len(verse_data.get('text', '')) if verse_data else 0
                })
                log_timing("8. Fetch Verse from Firestore", time.time() - step_start)

                # Build context (simplified for debug)
                step_start = time.time()
                context_by_source = {}
                for item in verse_metadata_list:
                    source_name = item['source']
                    metadata = item['metadata']
                    context_parts = []

                    # Extract metadata based on type
                    if metadata_type in ['hadith', 'all']:
                        hadith_refs = metadata.get('hadith_references', [])
                        if hadith_refs:
                            context_parts.append(f"HADITH: {len(hadith_refs)} references")

                    if metadata.get('commentary'):
                        context_parts.append(f"Commentary: {len(metadata['commentary'])} chars")

                    context_by_source[source_name] = context_parts

                log_step("9. Build Context from Metadata", {
                    "sources_with_context": len(context_by_source),
                    "context_summary": context_by_source
                })
                log_timing("9. Build Context", time.time() - step_start)

                # Build prompt
                step_start = time.time()
                arabic_text = get_arabic_text_from_verse_data(verse_data) if verse_data else None
                scholarly_ctx, scholarly_badges, scholarly_pipeline = _get_scholarly_context_two_stage(query, verse_data, context_by_source)
                prompt = build_enhanced_prompt(query, context_by_source, user_profile,
                                             arabic_text, None, 'metadata', verse_data, approach, scholarly_ctx)

                # LOG COMPLETE PROMPT
                print("🔵 === COMPLETE PROMPT TO GEMINI ===")
                print(prompt)
                print("🔵 === END COMPLETE PROMPT ===")

                log_step("10. Build AI Prompt", {
                    "prompt_length": len(prompt),
                    "has_arabic": bool(arabic_text),
                    "persona": user_profile.get('persona')
                })
                log_timing("10. Build AI Prompt", time.time() - step_start)

                # Call Gemini
                step_start = time.time()
                log_step("11. Calling Gemini API", {
                    "model": "{GEMINI_MODEL_ID}",
                    "temperature": 0.3,
                    "timeout": 120
                })

                credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                credentials.refresh(google.auth.transport.requests.Request())

                gemini_url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/us-central1/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

                body = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generation_config": {"temperature": 0.3, "maxOutputTokens": 65536},
                }

                response = requests.post(
                    gemini_url,
                    headers={
                        "Authorization": f"Bearer {credentials.token}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=120
                )

                gemini_duration = time.time() - step_start

                log_step("12. Gemini Response", {
                    "status_code": response.status_code,
                    "duration": f"{gemini_duration:.3f}s",
                    "response_length": len(response.text) if response.ok else 0
                })
                log_timing("11. Gemini API Call", gemini_duration)

                if response.ok:
                    result = response.json()
                    generated_text = result['candidates'][0]['content']['parts'][0]['text']

                    # LOG COMPLETE GEMINI RESPONSE
                    print("🟢 === COMPLETE GEMINI RESPONSE ===")
                    print(generated_text)
                    print("🟢 === END COMPLETE RESPONSE ===")

                    # CRITICAL FIX: Parse JSON from Gemini response
                    final_json = extract_json_from_response(generated_text)

                    if not final_json or final_json.get('metadata', {}).get('extraction_error'):
                        log_step("ERROR: JSON Extraction Failed", {
                            "has_extraction_error": bool(final_json and final_json.get('metadata', {}).get('extraction_error')),
                            "response_preview": generated_text[:500]
                        })
                        trace["error"] = "Failed to parse AI response"
                        return jsonify(trace), 500

                    # Add route and sources to response
                    final_json["route"] = "ROUTE 1"
                    if "sources" not in final_json:
                        final_json["sources"] = list(context_by_source.keys())
                    final_json["scholarly_sources"] = scholarly_badges
                    final_json["_scholarly_pipeline"] = scholarly_pipeline

                    # Cache it
                    with cache_lock:
                        RESPONSE_CACHE[cache_key] = final_json

                    trace["response"] = final_json
                    trace["timings"] = step_timings
                    trace["timings"]["total"] = f"{time.time() - overall_start:.3f}s"

                    log_step("ROUTE 1 COMPLETE", {
                        "has_verses": bool(final_json.get("verses")),
                        "has_tafsir": bool(final_json.get("tafsir_explanations")),
                        "cached": True
                    })

                    return jsonify(trace), 200
                else:
                    log_step("ERROR: Gemini API Failed", {
                        "status": response.status_code,
                        "error": response.text[:500]
                    })
                    trace["error"] = f"Gemini API error: {response.status_code}"
                    return jsonify(trace), 500

        # ===================================================================
        # ROUTE 2: DIRECT VERSE QUERY
        # ===================================================================
        if query_type == 'direct_verse' and verse_ref:
            log_step("ROUTE 2 EXECUTION START", {"route": "Direct Verse Query"})

            surah, verse = verse_ref
            verse_range = extract_verse_range(query)

            # Validation
            step_start = time.time()
            is_valid, msg = validate_verse_reference(surah, verse)
            log_step("6. Verse Validation", {
                "surah": surah,
                "verse": verse,
                "is_valid": is_valid
            })
            log_timing("6. Verse Validation", time.time() - step_start)

            if not is_valid:
                trace["error"] = msg
                return jsonify(trace), 400

            # Get tafsir for verse/range
            step_start = time.time()
            if verse_range and verse_range[1] != verse_range[2]:
                start_verse = verse_range[1]
                end_verse = verse_range[2]
                verse_metadata_list = get_verse_metadata_direct(surah, start_verse, end_verse)
                log_step("7. Fetch Verse Range Tafsir", {
                    "range": f"{surah}:{start_verse}-{end_verse}",
                    "num_verses": end_verse - start_verse + 1,
                    "num_sources": len(verse_metadata_list) if verse_metadata_list else 0
                })
            else:
                verse_metadata_list = get_verse_metadata_direct(surah, verse)
                log_step("7. Fetch Single Verse Tafsir", {
                    "verse": f"{surah}:{verse}",
                    "num_sources": len(verse_metadata_list) if verse_metadata_list else 0
                })

            log_timing("7. Fetch Tafsir", time.time() - step_start)

            if not verse_metadata_list:
                log_step("FALLBACK TO ROUTE 3", {
                    "reason": "No tafsir found in direct lookup"
                })
                query_type = 'semantic'  # Fall through to ROUTE 3
            else:
                # Build context from tafsir
                step_start = time.time()
                context_by_source = {}
                for item in verse_metadata_list:
                    source_name = item['source']
                    metadata = item['metadata']
                    if metadata.get('commentary'):
                        context_by_source[source_name] = [metadata['commentary']]

                log_step("8. Build Context from Tafsir", {
                    "num_sources": len(context_by_source),
                    "sources": list(context_by_source.keys()),
                    "total_commentary_chars": sum(len(c[0]) for c in context_by_source.values())
                })
                log_timing("8. Build Context", time.time() - step_start)

                # Get verse data from Firestore
                step_start = time.time()
                if verse_range and verse_range[1] != verse_range[2]:
                    # For range, get all verses
                    verse_data = get_verse_from_firestore(surah, verse_range[1])
                    log_step("9. Fetch Verse from Firestore", {
                        "verse_range": f"{surah}:{verse_range[1]}-{verse_range[2]}",
                        "has_verse_data": bool(verse_data)
                    })
                else:
                    verse_data = get_verse_from_firestore(surah, verse)
                    log_step("9. Fetch Verse from Firestore", {
                        "verse": f"{surah}:{verse}",
                        "has_verse_data": bool(verse_data),
                        "arabic_text_length": len(verse_data.get('text', '')) if verse_data else 0
                    })
                log_timing("9. Fetch Verse from Firestore", time.time() - step_start)

                # Build prompt
                step_start = time.time()
                arabic_text = get_arabic_text_from_verse_data(verse_data) if verse_data else None
                scholarly_ctx, scholarly_badges, scholarly_pipeline = _get_scholarly_context_two_stage(query, verse_data, context_by_source)
                prompt = build_enhanced_prompt(query, context_by_source, user_profile,
                                             arabic_text, None, 'direct_verse', verse_data, approach, scholarly_ctx)

                # LOG COMPLETE PROMPT
                print("🔵 === COMPLETE PROMPT TO GEMINI ===")
                print(prompt)
                print("🔵 === END COMPLETE PROMPT ===")

                log_step("10. Build AI Prompt", {
                    "prompt_length": len(prompt),
                    "has_arabic": bool(arabic_text),
                    "persona": user_profile.get('persona'),
                    "num_sources": len(context_by_source)
                })
                log_timing("10. Build AI Prompt", time.time() - step_start)

                # Call Gemini
                step_start = time.time()
                log_step("11. Calling Gemini API", {
                    "model": "{GEMINI_MODEL_ID}",
                    "temperature": 0.3,
                    "timeout": 120
                })

                credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                credentials.refresh(google.auth.transport.requests.Request())

                gemini_url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/us-central1/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

                body = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generation_config": {"temperature": 0.3, "maxOutputTokens": 65536},
                }

                response = requests.post(
                    gemini_url,
                    headers={
                        "Authorization": f"Bearer {credentials.token}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=120
                )

                gemini_duration = time.time() - step_start

                log_step("12. Gemini Response", {
                    "status_code": response.status_code,
                    "duration": f"{gemini_duration:.3f}s",
                    "response_length": len(response.text) if response.ok else 0
                })
                log_timing("11. Gemini API Call", gemini_duration)

                if response.ok:
                    result = response.json()
                    generated_text = result['candidates'][0]['content']['parts'][0]['text']

                    # LOG COMPLETE GEMINI RESPONSE
                    print("🟢 === COMPLETE GEMINI RESPONSE ===")
                    print(generated_text)
                    print("🟢 === END COMPLETE RESPONSE ===")

                    # CRITICAL FIX: Parse JSON from Gemini response
                    final_json = extract_json_from_response(generated_text)

                    if not final_json or final_json.get('metadata', {}).get('extraction_error'):
                        log_step("ERROR: JSON Extraction Failed", {
                            "has_extraction_error": bool(final_json and final_json.get('metadata', {}).get('extraction_error')),
                            "response_preview": generated_text[:500]
                        })
                        trace["error"] = "Failed to parse AI response"
                        return jsonify(trace), 500

                    # Add route and sources to response
                    final_json["route"] = "ROUTE 2"
                    if "sources" not in final_json:
                        final_json["sources"] = list(context_by_source.keys())
                    final_json["scholarly_sources"] = scholarly_badges
                    final_json["_scholarly_pipeline"] = scholarly_pipeline

                    # Cache it
                    with cache_lock:
                        RESPONSE_CACHE[cache_key] = final_json

                    trace["response"] = final_json
                    trace["timings"] = step_timings
                    trace["timings"]["total"] = f"{time.time() - overall_start:.3f}s"

                    log_step("ROUTE 2 COMPLETE", {
                        "has_verses": bool(final_json.get("verses")),
                        "has_tafsir": bool(final_json.get("tafsir_explanations")),
                        "cached": True
                    })

                    return jsonify(trace), 200
                else:
                    log_step("ERROR: Gemini API Failed", {
                        "status": response.status_code,
                        "error": response.text[:500]
                    })
                    trace["error"] = f"Gemini API error: {response.status_code}"
                    return jsonify(trace), 500

        # ===================================================================
        # ROUTE 3: SEMANTIC SEARCH
        # ===================================================================
        if query_type == 'semantic':
            log_step("ROUTE 3 EXECUTION START", {"route": "Semantic Search (Full RAG)"})

            # Get auth token for query expansion
            step_start = time.time()
            credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            credentials.refresh(google.auth.transport.requests.Request())
            token = credentials.token

            # Query Expansion
            log_step("6. Query Expansion", {
                "original_query": query,
                "status": "calling Gemini for expansion..."
            })

            expanded_query = expand_query(query, token, approach)

            log_step("6b. Query Expansion Result", {
                "original": query,
                "expanded": expanded_query,
                "expansion_added": len(expanded_query) - len(query)
            })
            log_timing("6. Query Expansion", time.time() - step_start)

            # Generate Embedding
            step_start = time.time()
            log_step("7. Generate Embedding", {
                "query": expanded_query,
                "model": EMBEDDING_MODEL,
                "dimension": EMBEDDING_DIMENSION
            })

            from vertexai.language_models import TextEmbeddingModel
            model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
            embeddings = model.get_embeddings([expanded_query], output_dimensionality=EMBEDDING_DIMENSION)
            query_embedding = embeddings[0].values

            log_step("7b. Embedding Generated", {
                "dimension": len(query_embedding),
                "first_5_values": query_embedding[:5]
            })
            log_timing("7. Generate Embedding", time.time() - step_start)

            # Vector Search
            step_start = time.time()
            log_step("8. Vector Search", {
                "index_endpoint": INDEX_ENDPOINT_ID,
                "deployed_index": DEPLOYED_INDEX_ID,
                "num_neighbors": 20
            })

            endpoint_name = f"projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
            index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_name)

            vector_response = index_endpoint.find_neighbors(
                deployed_index_id=DEPLOYED_INDEX_ID,
                queries=[query_embedding],
                num_neighbors=20
            )

            neighbors = vector_response[0] if vector_response else []

            log_step("8b. Vector Search Results", {
                "num_results": len(neighbors),
                "top_5_ids": [n.id for n in neighbors[:5]],
                "top_5_distances": [f"{n.distance:.4f}" for n in neighbors[:5]]
            })
            log_timing("8. Vector Search", time.time() - step_start)

            # Fetch chunks from Firestore
            step_start = time.time()
            log_step("9. Fetch Chunks from Firestore", {
                "chunk_ids": [n.id for n in neighbors[:5]]
            })

            chunks_by_source = {}
            for neighbor in neighbors:
                chunk_doc = quran_db.collection('tafsir_chunks').document(neighbor.id).get()
                if chunk_doc.exists:
                    chunk_data = chunk_doc.to_dict()
                    source = chunk_data.get('source', 'Unknown')
                    if source not in chunks_by_source:
                        chunks_by_source[source] = []
                    chunks_by_source[source].append(chunk_data.get('text', ''))

            log_step("9b. Chunks Retrieved", {
                "num_sources": len(chunks_by_source),
                "sources": list(chunks_by_source.keys()),
                "total_chunks": sum(len(chunks) for chunks in chunks_by_source.values())
            })
            log_timing("9. Fetch Chunks", time.time() - step_start)

            # Build prompt and call Gemini
            step_start = time.time()
            scholarly_ctx, scholarly_badges, scholarly_pipeline = _get_scholarly_context_two_stage(query, None, chunks_by_source)
            prompt = build_enhanced_prompt(query, chunks_by_source, user_profile,
                                         None, None, 'semantic', None, approach, scholarly_ctx)

            log_step("10. Build AI Prompt", {
                "prompt_length": len(prompt),
                "num_sources": len(chunks_by_source)
            })
            log_timing("10. Build Prompt", time.time() - step_start)

            # Gemini call
            step_start = time.time()
            log_step("11. Calling Gemini API", {
                "model": "{GEMINI_MODEL_ID}"
            })

            credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            credentials.refresh(google.auth.transport.requests.Request())

            gemini_url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/us-central1/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

            body = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generation_config": {"temperature": 0.3, "maxOutputTokens": 65536},
            }

            response = requests.post(
                gemini_url,
                headers={
                    "Authorization": f"Bearer {credentials.token}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=120
            )

            gemini_duration = time.time() - step_start

            log_step("12. Gemini Response", {
                "status_code": response.status_code,
                "duration": f"{gemini_duration:.3f}s"
            })
            log_timing("11. Gemini API", gemini_duration)

            if response.ok:
                result = response.json()
                answer = result['candidates'][0]['content']['parts'][0]['text']

                final_response = {
                    "answer": answer,
                    "sources": list(chunks_by_source.keys()),
                    "route": "ROUTE 3",
                    "num_chunks": sum(len(chunks) for chunks in chunks_by_source.values()),
                    "scholarly_sources": scholarly_badges,
                    "_scholarly_pipeline": scholarly_pipeline,
                }

                # Track exploration + badges for Route 3 (if verse ref available)
                if user_id:
                    try:
                        vr = extract_verse_range(query) or extract_verse_reference_enhanced(query)
                        if vr and len(vr) >= 2:
                            s, sv = int(vr[0]), int(vr[1])
                            ev = int(vr[2]) if len(vr) >= 3 else sv
                            _track_explored_verse(user_id, s, sv, ev)
                            _check_and_award_badges(user_id)
                    except Exception as track_err:
                        print(f"[TRACKING] Route 3 tracking error: {track_err}")

                # Cache it
                with cache_lock:
                    RESPONSE_CACHE[cache_key] = final_response

                trace["response"] = final_response
                trace["timings"] = step_timings
                trace["timings"]["total"] = f"{time.time() - overall_start:.3f}s"

                log_step("ROUTE 3 COMPLETE", {
                    "answer_length": len(answer),
                    "cached": True
                })

                return jsonify(trace), 200
            else:
                log_step("ERROR: Gemini API Failed", {
                    "status": response.status_code,
                    "error": response.text[:500]
                })
                trace["error"] = f"Gemini API error: {response.status_code}"
                return jsonify(trace), 500

        # Should not reach here
        trace["error"] = "No route matched"
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

@app.route("/debug/vector-test", methods=["GET"])
def test_vector_search():
    """Test vector search directly without auth"""
    try:
        from vertexai.language_models import TextEmbeddingModel

        # Initialize
        model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
        endpoint_name = f"projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_name)

        # Generate embedding for test query
        test_query = "Allah mercy compassion"
        embeddings = model.get_embeddings([test_query], output_dimensionality=EMBEDDING_DIMENSION)
        query_embedding = embeddings[0].values

        # Perform vector search
        result = index_endpoint.find_neighbors(
            deployed_index_id=DEPLOYED_INDEX_ID,
            queries=[query_embedding],
            num_neighbors=5
        )

        # Process results
        neighbors = result[0] if result else []

        response = {
            "test_query": test_query,
            "embedding_dim": len(query_embedding),
            "neighbors_found": len(neighbors),
            "neighbors": []
        }

        # Check each neighbor
        for i, neighbor in enumerate(neighbors[:5]):
            neighbor_id = str(neighbor.id)
            base_id = neighbor_id
            if '_' in neighbor_id:
                parts = neighbor_id.rsplit('_', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    base_id = parts[0]

            chunk_exists = base_id in TAFSIR_CHUNKS

            response["neighbors"].append({
                "index": i,
                "vector_id": neighbor_id,
                "base_id": base_id,
                "distance": neighbor.distance,
                "chunk_exists": chunk_exists,
                "chunk_preview": TAFSIR_CHUNKS.get(base_id, "NOT FOUND")[:100] if chunk_exists else None
            })

        # Show sample of actual chunk keys
        response["sample_chunk_keys"] = list(TAFSIR_CHUNKS.keys())[:10]
        response["chunk_key_pattern"] = "Format of keys in TAFSIR_CHUNKS"

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

@app.route("/debug/vector-diagnosis", methods=["GET"])
def diagnose_vector_index():
    """Emergency diagnostic endpoint to check why vector search is failing"""
    try:
        diagnosis = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "INDEX_ENDPOINT_ID": INDEX_ENDPOINT_ID,
                "DEPLOYED_INDEX_ID": DEPLOYED_INDEX_ID,
                "EMBEDDING_DIMENSION": EMBEDDING_DIMENSION,
                "EMBEDDING_MODEL": EMBEDDING_MODEL,
                "GCP_PROJECT": GCP_INFRASTRUCTURE_PROJECT
            },
            "tests": {}
        }

        # Test 1: Check embedding generation
        try:
            from vertexai.language_models import TextEmbeddingModel
            model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
            test_emb = model.get_embeddings(["test"], output_dimensionality=EMBEDDING_DIMENSION)
            actual_dim = len(test_emb[0].values)

            diagnosis["tests"]["embedding"] = {
                "success": True,
                "expected_dim": EMBEDDING_DIMENSION,
                "actual_dim": actual_dim,
                "match": actual_dim == EMBEDDING_DIMENSION
            }
        except Exception as e:
            diagnosis["tests"]["embedding"] = {
                "success": False,
                "error": str(e)
            }

        # Test 2: Check index connectivity and search
        try:
            endpoint_name = f"projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
            index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_name)

            # Test 3: Perform test search
            test_embedding = model.get_embeddings(["Allah"], output_dimensionality=EMBEDDING_DIMENSION)[0].values
            result = index_endpoint.find_neighbors(
                deployed_index_id=DEPLOYED_INDEX_ID,
                queries=[test_embedding],
                num_neighbors=5
            )

            num_found = len(result[0]) if result and result[0] else 0

            diagnosis["tests"]["vector_search"] = {
                "success": True,
                "neighbors_found": num_found,
                "index_populated": num_found > 0,
                "endpoint_name": endpoint_name
            }

            if num_found == 0:
                diagnosis["critical_issue"] = "INDEX_EMPTY_OR_MISCONFIGURED"

        except Exception as e:
            diagnosis["tests"]["vector_search"] = {
                "success": False,
                "error": str(e)[:500]  # Truncate long errors
            }
            diagnosis["critical_issue"] = "INDEX_CONNECTION_FAILED"

        # Test 4: Check local chunks
        diagnosis["tests"]["local_chunks"] = {
            "total_loaded": len(TAFSIR_CHUNKS),
            "sources": {
                "Ibn Kathir": sum(1 for v in CHUNK_SOURCE_MAP.values() if v == "Ibn Kathir"),
                "al-Qurtubi": sum(1 for v in CHUNK_SOURCE_MAP.values() if v == "al-Qurtubi")
            },
            "metadata_loaded": len(VERSE_METADATA)
        }

        # Determine root cause
        if diagnosis["tests"].get("embedding", {}).get("match") == False:
            diagnosis["root_cause"] = "EMBEDDING_DIMENSION_MISMATCH"
            diagnosis["fix"] = "Index expects different embedding dimension than model produces"
            diagnosis["action_required"] = "Rebuild index with correct embedding dimension or use matching model"
        elif diagnosis.get("critical_issue") == "INDEX_EMPTY_OR_MISCONFIGURED":
            diagnosis["root_cause"] = "INDEX_NOT_POPULATED"
            diagnosis["fix"] = "Vector index has no data or wrong IDs configured"
            diagnosis["action_required"] = "Check if index is populated or verify INDEX_ENDPOINT_ID and DEPLOYED_INDEX_ID"
        elif diagnosis.get("critical_issue") == "INDEX_CONNECTION_FAILED":
            diagnosis["root_cause"] = "WRONG_INDEX_IDS"
            diagnosis["fix"] = "Cannot connect to index endpoint"
            diagnosis["action_required"] = "Verify INDEX_ENDPOINT_ID exists in project"
        else:
            diagnosis["root_cause"] = "SYSTEM_OPERATIONAL"
            diagnosis["fix"] = "No issues detected"

        return jsonify(diagnosis), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__,
            "critical": True
        }), 500

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

# --- Main ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host="0.0.0.0", port=port)
