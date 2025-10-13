import os
import json
import re
import traceback
import time
import hashlib
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, List, Any

from flask import Flask, request, jsonify
from flask_cors import CORS

import requests
import google.auth
from google.auth.transport.requests import Request as GoogleRequest

import firebase_admin
from firebase_admin import credentials, auth, firestore
from google.cloud import secretmanager
from google.cloud import firestore as gcp_firestore

# Imports for RAG and Query Expansion
import vertexai
from vertexai.language_models import TextEmbeddingModel
from google.cloud import aiplatform
from google.cloud import storage

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
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-2.0-flash")
FIREBASE_SECRET_FULL_PATH = os.environ.get("FIREBASE_SECRET_FULL_PATH")

# UPDATED: New sliding window vector index configuration (1536 dimensions)
INDEX_ENDPOINT_ID = os.environ.get("INDEX_ENDPOINT_ID", "3478417184655409152")
DEPLOYED_INDEX_ID = os.environ.get("DEPLOYED_INDEX_ID", "deployed_tafsir_sliding_1760263278167")
VECTOR_INDEX_ID = os.environ.get("VECTOR_INDEX_ID", "5746296256385253376")

GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "tafsir-simplified-sources")

# UPDATED: Embedding configuration to match new index
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 1536  # Changed from 1024 to 1536

# Source coverage information
# Ibn Kathir: Complete Quran (114 Surahs)
# Al-Qurtubi: Surahs 1-4 (up to Surah 4, Verse 22)

# --- Startup Validation (Fail Fast) ---
if not FIREBASE_SECRET_FULL_PATH or not INDEX_ENDPOINT_ID or not DEPLOYED_INDEX_ID or not GCS_BUCKET_NAME:
    raise ValueError("CRITICAL STARTUP ERROR: Missing required RAG environment variables")

# Global variables - UPDATED for dual database setup
users_db = None      # Firebase Admin SDK -> (default) database for users/auth
quran_db = None      # Google Cloud client -> tafsir-db database for Quran texts
TAFSIR_CHUNKS = {}
CHUNK_SOURCE_MAP = {}  # Maps chunk_id to source name
VERSE_METADATA = {}  # NEW: Stores structured metadata for direct queries
RESPONSE_CACHE = {}  # In-memory cache
USER_RATE_LIMITS = defaultdict(list)  # Rate limiting
ANALYTICS = defaultdict(int)  # Usage analytics

# ============================================================================
# NEW: PERSONA SYSTEM FOR ADAPTIVE RESPONSES
# ============================================================================

# Comprehensive persona system (7 personas) - UPDATED: removed response_length
PERSONAS = {
    "new_revert": {
        "name": "New Revert",
        "tone": "warm, encouraging, patient",
        "vocabulary": "simple, everyday",
        "include_hadith": False,
        "scholarly_debates": False,
        "format_style": "bullets_emojis"  # Bullets + emojis
    },
    "revert": {
        "name": "Revert Muslim (1-5 years)",
        "tone": "supportive, informative",
        "vocabulary": "moderate",
        "include_hadith": True,
        "scholarly_debates": False,
        "format_style": "bullets_emojis"
    },
    "seeker": {
        "name": "Spiritual Seeker",
        "tone": "warm, reflective",
        "vocabulary": "accessible",
        "include_hadith": True,
        "scholarly_debates": False,
        "format_style": "bullets_emojis"
    },
    "practicing_muslim": {
        "name": "Practicing Muslim",
        "tone": "respectful, balanced",
        "vocabulary": "moderate",
        "include_hadith": True,
        "scholarly_debates": True,
        "format_style": "balanced"  # Mix of paragraphs + bullets
    },
    "teacher": {
        "name": "Teacher/Imam/Educator",
        "tone": "pedagogical, clear",
        "vocabulary": "accessible",
        "include_hadith": True,
        "scholarly_debates": True,
        "format_style": "balanced"
    },
    "scholar": {
        "name": "Scholar/Advanced Student",
        "tone": "academic, precise",
        "vocabulary": "advanced, technical",
        "include_hadith": True,
        "scholarly_debates": True,
        "format_style": "academic_prose"  # Dense prose, no bullets
    },
    "student": {
        "name": "Islamic Studies Student",
        "tone": "educational, comprehensive",
        "vocabulary": "academic",
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

# Popular query suggestions
QUERY_SUGGESTIONS = [
    "2:255", "Ayat al-Kursi", "1:1", "Fatiha", "charity", "prayer", "jihad",
    "taqwa", "patience", "forgiveness", "Day of Judgment", "paradise",
    "mercy of Allah", "guidance", "faith", "gratitude", "justice"
]

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

# Named verses mapping (common references)
NAMED_VERSES = {
    'ayat al-kursi': (2, 255),
    'ayatul kursi': (2, 255),
    'throne verse': (2, 255),
    'verse of the throne': (2, 255),
    'light verse': (24, 35),
    'ayat an-nur': (24, 35),
    'debt verse': (2, 282),
    'bismillah': (1, 1),
    'basmala': (1, 1),
    'fatiha': (1, 1),
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
    """Normalize query for better matching"""
    query = query.lower().strip()
    replacements = {
        'sura': 'surah', 'ayat': 'ayah', 'verses': 'verse',
        'cited by': 'cited', 'mentions': 'mentioned'
    }
    for old, new in replacements.items():
        query = query.replace(old, new)
    return query

def extract_verse_reference_enhanced(query: str) -> Optional[Tuple[int, int]]:
    """
    Extract verse reference using multiple strategies.
    Returns (surah, verse) or None.
    """
    query_normalized = normalize_query_text(query)

    # Strategy 1: Named verses
    for name, ref in NAMED_VERSES.items():
        if name in query_normalized:
            return ref

    # Strategy 2: Numeric patterns
    patterns = [
        r'\b(\d{1,3}):(\d{1,3})\b',  # 2:255
        r'\b(\d{1,3})\s*:\s*(\d{1,3})\b',  # 2 : 255
        r'surah\s+(\d{1,3})\s+(?:verse|ayah|ayat)\s+(\d{1,3})',  # surah 2 verse 255
    ]

    for pattern in patterns:
        match = re.search(pattern, query_normalized)
        if match:
            try:
                surah = int(match.group(1))
                verse = int(match.group(2))
                is_valid, _ = validate_verse_reference(surah, verse)
                if is_valid:
                    return (surah, verse)
            except (ValueError, IndexError):
                continue

    # Strategy 3: Surah name + number
    for surah_name, surah_num in SURAHS_BY_NAME.items():
        if surah_name in query_normalized:
            pattern = rf'{re.escape(surah_name)}[^\d]*(\d{{1,3}})'
            match = re.search(pattern, query_normalized)
            if match:
                verse_num = int(match.group(1))
                is_valid, _ = validate_verse_reference(surah_num, verse_num)
                if is_valid:
                    return (surah_num, verse_num)

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

        # Pure reference like "2:255"
        if re.fullmatch(r'\d{1,3}:\d{1,3}', query_normalized.strip()):
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
def validate_verse_reference(surah, verse):
    """Validate that surah and verse numbers are within valid ranges"""
    if surah not in QURAN_METADATA:
        return False, f"Invalid Surah: {surah}. The Quran has 114 Surahs."

    max_verses = QURAN_METADATA[surah]["verses"]
    if not (1 <= verse <= max_verses):
        surah_name = QURAN_METADATA[surah]["name"]
        return False, f"Invalid verse: {verse}. Surah {surah} ('{surah_name}') only has {max_verses} verses."

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
def get_cache_key(query, user_profile):
    """Generate cache key for response"""
    cache_data = f"{query}_{json.dumps(user_profile, sort_keys=True)}"
    return hashlib.md5(cache_data.encode()).hexdigest()

def is_rate_limited(user_id, limit=50, window_hours=1):
    """Check if user is rate limited"""
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

def validate_response(response_data):
    """Validate response quality"""
    try:
        required_fields = ["tafsir_explanations", "lessons_practical_applications"]
        if not all(field in response_data for field in required_fields):
            return False, "Missing required fields"

        # Check if at least one tafsir explanation has substantial content
        explanations = response_data.get("tafsir_explanations", [])
        substantial_explanations = [
            exp for exp in explanations
            if len(exp.get("explanation", "")) > 50 and
            "Limited relevant content" not in exp.get("explanation", "")
        ]

        if len(substantial_explanations) == 0:
            return False, "No substantial explanations found"

        return True, "Valid response"
    except Exception as e:
        return False, f"Validation error: {e}"

# --- Error Handler ---
def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(f"ERROR in {f.__name__}: {type(e).__name__} - {e}")
            traceback.print_exc()
            return jsonify({'error': 'Internal server error'}), 500
    return decorated_function

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
        "scholar": "advanced",
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

            # Handle verse numbers (single or list)
            if isinstance(verse_num, list) and verse_num:
                # For multi-verse entries, store under first verse
                verse_num = verse_num[0]
            elif verse_num is None:
                verse_num = 0

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

                VERSE_METADATA[chunk_id] = {
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


# --- NEW: Direct Metadata Retrieval Functions ---
def get_verse_metadata_direct(surah: int, verse: int, source_pref: Optional[str] = None) -> List[Dict]:
    """
    Direct lookup of verse metadata (no vector search).

    Args:
        surah: Surah number
        verse: Verse number
        source_pref: 'ibn-kathir', 'al-qurtubi', or None (both)

    Returns:
        List of metadata dicts from matching sources
    """
    results = []
    sources_to_check = [source_pref] if source_pref else ['ibn-kathir', 'al-qurtubi']

    for source in sources_to_check:
        chunk_id = f"{source}:{surah}:{verse}"
        metadata = VERSE_METADATA.get(chunk_id)

        if metadata:
            results.append({
                'chunk_id': chunk_id,
                'source': "Ibn Kathir" if source == "ibn-kathir" else "al-Qurtubi",
                'metadata': metadata
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
            "surah": verse_data['surah_name'],
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
            "explanation": "\n\n".join(explanation_parts) if explanation_parts else "No detailed commentary available"
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


def retrieve_chunks_from_neighbors(neighbors):
    """
    Retrieve chunks from TAFSIR_CHUNKS based on neighbor IDs.
    Handles sliding window segment IDs (e.g., ibn-kathir:1:1_0 -> ibn-kathir:1:1)

    Returns list of dicts with chunk info.
    """
    retrieved = []

    for neighbor in neighbors:
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
            print(f"WARNING: Chunk not found for ID: {neighbor_id} (base: {base_id})")

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

# --- Query Expansion ---
def expand_query(query: str, token: str) -> str:
    """Expand user query to better match tafsir content using LLM"""
    try:
        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

        expansion_prompt = f"""
You are helping expand a query to search Islamic tafsir (Quranic commentary) texts from classical sources:
- Tafsir Ibn Kathir (complete Quran coverage)
- Tafsir al-Qurtubi (Surahs 1-4, up to verse 4:22)

Original query: "{query}"

Expand this query by adding relevant Islamic terms, Arabic concepts, Quranic themes, and related theological concepts that would help find relevant tafsir passages. Consider:
- Related Arabic terminology
- Connected Quranic verses or themes
- Islamic jurisprudence concepts (especially for al-Qurtubi on early Surahs)
- Historical context and hadith references (especially for Ibn Kathir)
- Theological implications

Keep the expansion concise but comprehensive. Return only the expanded query text, nothing else.
"""

        body = {
            "contents": [{"role": "user", "parts": [{"text": expansion_prompt}]}],
            "generation_config": {"temperature": 0.3, "maxOutputTokens": 200},
        }

        response = requests.post(
            VERTEX_ENDPOINT,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and result["candidates"]:
                expanded = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                print(f"INFO: Query expanded from '{query}' to '{expanded}'")
                return expanded

        print(f"WARNING: Query expansion failed, using original query")
        return query

    except Exception as e:
        print(f"WARNING: Query expansion error: {e}")
        return query

# --- UPDATED: Enhanced Multi-Source RAG Functions with 1536 dimensions ---
def perform_diversified_rag_search(query, expanded_query, embedding_model, index_endpoint, query_type="default"):
    """Enhanced RAG with source weighting - UPDATED for 1536 dimensions and sliding window IDs"""

    # Step 1: Generate query embedding with correct dimension
    query_embedding = embedding_model.get_embeddings(
        [expanded_query],
        output_dimensionality=EMBEDDING_DIMENSION
    )[0].values

    # Step 2: Retrieve larger pool of candidates (20 chunks for better diversity)
    neighbors_result = index_endpoint.find_neighbors(
        deployed_index_id=DEPLOYED_INDEX_ID,
        queries=[query_embedding],
        num_neighbors=20
    )

    # Step 3: Retrieve chunks using new function that handles segment IDs
    retrieved_chunks = retrieve_chunks_from_neighbors(neighbors_result[0])

    # Step 4: Intelligent source diversification with weighting
    source_chunks = {
        'Ibn Kathir': [],
        'al-Qurtubi': []
    }

    # Categorize all retrieved chunks by source
    for chunk in retrieved_chunks:
        source = chunk['source']
        if source in source_chunks:
            source_chunks[source].append(chunk)

    # Step 5: Weighted selection based on query type
    # CLASSIFY FOR RAG
    rag_query_type = "default" # Placeholder for old logic, now handled by main handler
    weights = SOURCE_WEIGHTS.get(rag_query_type, SOURCE_WEIGHTS["default"])
    selected_chunks = []
    context_by_source = {}

    for source_name, chunks in source_chunks.items():
        if chunks:
            # Sort by distance (most relevant first)
            sorted_chunks = sorted(chunks, key=lambda x: x['distance'])

            # Apply weighting
            weight = weights.get(source_name, 0.5)
            num_chunks = max(2, int(weight * 10))

            top_chunks = sorted_chunks[:num_chunks]
            selected_chunks.extend(top_chunks)
            context_by_source[source_name] = [chunk['text'] for chunk in top_chunks]
        else:
            context_by_source[source_name] = []

    return selected_chunks, context_by_source

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
# UPDATED: PERSONA-ADAPTIVE CLARITY-ENHANCED PROMPT WITH NEW PROFILE DATA
# ============================================================================

def build_enhanced_prompt(query, context_by_source, user_profile, arabic_text=None, cross_refs=None, query_type="default", verse_data=None):
    """
    ENHANCED VERSION: Gemini as Scholarly Editor with Persona-Adaptive Formatting
    UPDATED: Now includes learning_goal, knowledge_level, and refined formatting rules

    Gives Gemini explicit instructions to:
    1. Fix grammar/clarity while preserving accuracy
    2. Adapt content FORMAT to user persona (bullets for beginners, prose for scholars)
    3. Use verse translations from backend (not generate them)
    4. Adapt depth and focus based on learning_goal and knowledge_level
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

    # Add verse information if available
    verse_info = ""
    if verse_data:
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
USER QUERY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"{query}"

Query Type: {query_type}
{verse_info}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE MATERIAL (Classical Tafsir - May Have Issues)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{structured_context}

⚠️ NOTE: This source material comes from JSON-structured classical tafsir texts.
It may contain grammar errors, typos, run-on sentences, missing punctuation, and awkward phrasing from translation/OCR.

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
RESPONSE FORMAT - PERSONA-ADAPTIVE CONTENT STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL: Return valid JSON, but ADAPT THE CONTENT FORMAT based on user persona:

📱 FOR BEGINNER PERSONAS (new_revert, revert, seeker) - Format: {format_style}
   Use VISUAL, SCANNABLE format with:
   • Short bullet points (use • character for bullets)
   • Clear section headers with MINIMAL emoji use (ONE emoji in main headers ONLY, ZERO in body text)
   • Short sentences (10-15 words max)
   • Encouraging language (avoid excessive emoji decoration)
   • Visual breaks between concepts

   Example for beginner (UPDATED - minimal emojis):
   "🌟 **Key Point: Allah Never Sleeps**

   This verse (Ayat al-Kursi) teaches us that:
   • Allah is always awake and aware
   • He never gets tired or needs rest
   • He protects us 24/7

   **What This Means for You:**
   When you feel alone or scared, remember Allah is always there watching over you.

   **Quick Tip:**
   Many Muslims say this verse before sleeping for protection. You can too!"

📚 FOR INTERMEDIATE PERSONAS (practicing_muslim, teacher) - Format: {format_style}
   Use BALANCED format with:
   • Mix of short paragraphs (3-5 sentences) and bullet points
   • Clear subheadings (use **Bold** for headers)
   • NO emojis
   • Some detail but not overwhelming
   • Practical focus

   Example for intermediate:
   "**Overview of Ayat al-Kursi**

   This verse is considered one of the greatest in the Quran. It describes Allah's attributes of absolute power and perfect knowledge.

   **Key Themes:**
   • Divine sovereignty - Allah's throne extends over all creation
   • Perfect attributes - Al-Hayy (Ever-Living) and Al-Qayyum (Self-Sustaining)
   • Effortless preservation - Maintaining the universe requires no effort from Allah

   **Practical Application:**
   The Prophet ﷺ taught that reciting this verse provides spiritual protection. Many Muslims incorporate it into their daily dhikr, especially before sleep."

🎓 FOR ADVANCED/SCHOLAR PERSONAS (scholar, student) - Format: {format_style}
   Use SHORT PARAGRAPH format with:
   • Short, focused paragraphs (2-4 sentences each)
   • **Bolded sub-headers** before each paragraph for scannability
   • Technical terminology appropriate for advanced students
   • Scholarly citations integrated naturally
   • Debates and nuances discussed
   • NO bullet points or emojis

   Example for scholar (UPDATED - short paragraphs with sub-headers):
   "**Theological Significance**
   Ayat al-Kursi (2:255) represents a comprehensive theological statement regarding divine attributes. Classical exegetes have identified this verse as containing the most concentrated exposition of tawhid in the Quran.

   **Ibn Kathir's Interpretation**
   Ibn Kathir (d. 774 AH) notes in his tafsir that the verse systematically presents both positive attributes (al-Hayy, al-Qayyum) and negative attributes (no slumber, no fatigue) to establish Allah's absolute transcendence. He emphasizes the pedagogical structure of moving from Allah's essence to His knowledge to His power.

   **Al-Qurtubi's Jurisprudential Perspective**
   Al-Qurtubi approaches the verse differently, extracting legal implications from each phrase. He discusses the controversy regarding the nature of the Kursi, presenting three interpretive schools: those who equate it with knowledge, those who see it as a physical entity beneath the Throne, and those who consider it metaphorical.

   **Scholarly Debates**
   The controversy regarding the nature of the Kursi has been extensively discussed by medieval scholars. The Ash'ari school tends toward metaphorical interpretation, while the Hanbali school maintains a more literal reading while affirming tanzih (transcendence)."

JSON Structure (verse text ALREADY provided by backend - you focus on tafsir):

{{
    "verses": [
        {{
            "surah": "Surah name (from verse_data)",
            "verse_number": "verse number (from verse_data)",
            "text_saheeh_international": "English translation (from verse_data)",
            "arabic_text": "Arabic text (from verse_data)"
        }}
    ],

    "tafsir_explanations": [
        {{
            "source": "al-Qurtubi",
            "explanation": "FORMAT BASED ON PERSONA: Bullets + MINIMAL emojis for beginners ({format_style}), balanced with NO emojis for intermediate, short paragraphs with sub-headers for scholars. Fix all grammar, improve clarity, preserve accuracy. If verse beyond Surah 4:22, state: 'Al-Qurtubi's tafsir is not available for this verse.'"
        }},
        {{
            "source": "Ibn Kathir",
            "explanation": "FORMAT BASED ON PERSONA: Bullets + MINIMAL emojis for beginners ({format_style}), balanced with NO emojis for intermediate, short paragraphs with sub-headers for scholars. Fix all grammar, improve clarity, preserve accuracy."
        }}
    ],

    "cross_references": [
        {{
            "verse": "Related verse reference (e.g., '2:256')",
            "relevance": "Brief, clear explanation"
        }}
    ],

    "lessons_practical_applications": [
        {{"point": "Clear, actionable takeaway 1"}},
        {{"point": "Clear, actionable takeaway 2"}},
        {{"point": "Clear, actionable takeaway 3"}}
    ],

    "summary": "2-3 sentences directly answering the query"
}}

FORMATTING DECISION:
• If persona = new_revert, revert, or seeker → Use bullets (•), ONE emoji in main headers ONLY, short sentences
• If persona = practicing_muslim or teacher → Use balanced: **bold headers**, short paragraphs + some bullets, NO emojis
• If persona = scholar or student → Use short paragraphs (2-4 sentences) with **bolded sub-headers**, NO bullets, NO emojis

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE COVERAGE (Important Context)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **Ibn Kathir**: Complete Quran (all 114 Surahs)
• **al-Qurtubi**: Surahs 1-4 only (up to Surah 4:22)

If query is about verses beyond Surah 4:22, explain that al-Qurtubi's commentary is not available.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL REMINDERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **ADAPT FORMAT TO PERSONA** - Beginners get bullets + MINIMAL emojis, scholars get short paragraphs with sub-headers
2. **You are an EDITOR, not an author** - Polish what's there, don't create new interpretations
3. **PRESERVE ACCURACY** - Never change meanings, attributions, or theological positions
4. **ENHANCE CLARITY** - Fix grammar, improve structure, make readable
5. **CITE ACCURATELY** - Keep all scholar names exactly as provided (Ibn Kathir, al-Qurtubi)
6. **VERSES FROM BACKEND** - Don't try to provide translations, they're already in verse_data
7. **BE HELPFUL** - Make the response answer the user's query directly and clearly
8. **NEVER FABRICATE** - If insufficient source material, acknowledge limitations
9. **FOLLOW CONTENT GUIDELINES** - {'Include hadith' if persona['include_hadith'] else 'Avoid hadith'}, {'include scholarly debates' if persona['scholarly_debates'] else 'avoid scholarly disagreements'}
10. **MATCH LEARNING GOAL** - {goal_instruction}

Current persona: **{persona_name}** ({knowledge_level} level)
Apply formatting rules for: {'BEGINNER (bullets + MINIMAL emojis)' if format_style == 'bullets_emojis' else 'INTERMEDIATE (balanced, NO emojis)' if format_style == 'balanced' else 'SCHOLAR (short paragraphs with sub-headers, NO bullets)'}

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
            if verse.get('arabic_text') and verse['arabic_text'] != 'Not available':
                content += f"**{verse['surah']}, Verse {verse['verse_number']}**\n\n"
                content += f"{verse['arabic_text']}\n\n"
                content += f"*{verse['text_saheeh_international']}*\n\n"
            else:
                content += f"**{verse['surah']}, Verse {verse['verse_number']}**\n\n"
                content += f"*{verse['text_saheeh_international']}*\n\n"

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
def get_suggestions():
    """Get query suggestions"""
    return jsonify({
        "suggestions": QUERY_SUGGESTIONS,
        "popular_topics": ["2:255", "charity", "prayer", "forgiveness", "patience"],
        "verse_examples": ["1:1", "2:255", "112:1-4", "113:1", "114:1"]
    }), 200

@app.route("/analytics", methods=["GET"])
@firebase_auth_required
def get_analytics():
    """Get usage analytics (admin only)"""
    try:
        user_email = request.user.get('email', '')
        if not user_email.endswith('@yourdomain.com'): # Replace with your admin domain
            return jsonify({"error": "Unauthorized"}), 403

        return jsonify({
            "total_queries": sum(ANALYTICS.values()),
            "popular_queries": dict(sorted(ANALYTICS.items(), key=lambda x: x[1], reverse=True)[:10]),
            "active_users": len(USER_RATE_LIMITS),
            "cache_hit_rate": len(RESPONSE_CACHE) / max(sum(ANALYTICS.values()), 1)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    - Deterministic personas (scholar, student, new_revert) auto-set knowledge_level
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
                    "description": "Choose from: new_revert, revert, seeker, practicing_muslim, teacher, scholar, student"
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
        if name in ["scholar", "student"]:
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
# QUERY HISTORY & SAVED SEARCHES ENDPOINTS
# ============================================================================

@app.route("/query-history", methods=["GET"])
@require_auth
def get_query_history():
    """Get user's recent query history"""
    try:
        uid = request.uid
        limit = int(request.args.get('limit', 50))

        history_ref = users_db.collection('users').document(uid).collection('query_history')
        query = history_ref.order_by('timestamp', direction='DESCENDING').limit(limit)

        history = []
        for doc in query.stream():
            data = doc.to_dict()
            history.append({
                'id': doc.id,
                'query': data.get('query', ''),
                'approach': data.get('approach', 'tafsir'),
                'persona': data.get('persona', ''),
                'timestamp': data.get('timestamp', ''),
                'hasResult': data.get('hasResult', False)
            })

        return jsonify({'history': history, 'count': len(history)}), 200

    except Exception as e:
        print(f"ERROR in /query-history: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/query-history", methods=["POST"])
@require_auth
def save_query_to_history():
    """Save a query to user's history"""
    try:
        uid = request.uid
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
@require_auth
def get_saved_searches():
    """Get user's saved searches/answers"""
    try:
        uid = request.uid
        folder = request.args.get('folder', None)

        saved_ref = users_db.collection('users').document(uid).collection('saved_searches')

        if folder:
            query = saved_ref.where('folder', '==', folder).order_by('savedAt', direction='DESCENDING')
        else:
            query = saved_ref.order_by('savedAt', direction='DESCENDING')

        saved = []
        for doc in query.stream():
            data = doc.to_dict()
            saved.append({
                'id': doc.id,
                'query': data.get('query', ''),
                'approach': data.get('approach', 'tafsir'),
                'folder': data.get('folder', 'Uncategorized'),
                'title': data.get('title', data.get('query', '')[:50]),
                'savedAt': data.get('savedAt', ''),
                'responseSnippet': data.get('responseSnippet', '')
            })

        return jsonify({'saved': saved, 'count': len(saved)}), 200

    except Exception as e:
        print(f"ERROR in /saved-searches: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/saved-searches", methods=["POST"])
@require_auth
def save_search():
    """Save a search/answer for later"""
    try:
        uid = request.uid
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
@require_auth
def delete_saved_search(search_id):
    """Delete a saved search"""
    try:
        uid = request.uid

        doc_ref = users_db.collection('users').document(uid).collection('saved_searches').document(search_id)
        doc_ref.delete()

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"ERROR in DELETE /saved-searches: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/saved-searches/folders", methods=["GET"])
@require_auth
def get_folders():
    """Get list of all folders with counts"""
    try:
        uid = request.uid

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

@app.route("/annotations/verse/<int:surah>/<int:verse>", methods=["GET"])
@require_auth
def get_verse_annotations(surah, verse):
    """Get all annotations for a specific verse"""
    try:
        uid = request.uid

        annotations_ref = users_db.collection('users').document(uid).collection('annotations')
        query = annotations_ref.where('surah', '==', surah).where('verse', '==', verse).order_by('createdAt', direction='DESCENDING')

        annotations = []
        for doc in query.stream():
            data = doc.to_dict()
            annotations.append({
                'id': doc.id,
                'surah': data.get('surah'),
                'verse': data.get('verse'),
                'type': data.get('type', 'personal_insight'),
                'content': data.get('content', ''),
                'tags': data.get('tags', []),
                'linkedVerses': data.get('linkedVerses', []),
                'createdAt': data.get('createdAt'),
                'updatedAt': data.get('updatedAt'),
                'isPrivate': data.get('isPrivate', True)
            })

        return jsonify({'annotations': annotations, 'count': len(annotations)}), 200

    except Exception as e:
        print(f"ERROR in /annotations/verse: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/annotations/user", methods=["GET"])
@require_auth
def get_user_annotations():
    """Get all annotations for user with optional filters"""
    try:
        uid = request.uid
        tag = request.args.get('tag')
        annotation_type = request.args.get('type')
        limit = int(request.args.get('limit', 100))

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

            annotations.append({
                'id': doc.id,
                'surah': data.get('surah'),
                'verse': data.get('verse'),
                'verseRef': f"{data.get('surah')}:{data.get('verse')}",
                'type': data.get('type', 'personal_insight'),
                'content': data.get('content', ''),
                'tags': data.get('tags', []),
                'linkedVerses': data.get('linkedVerses', []),
                'createdAt': data.get('createdAt'),
                'updatedAt': data.get('updatedAt')
            })

        return jsonify({'annotations': annotations, 'count': len(annotations)}), 200

    except Exception as e:
        print(f"ERROR in /annotations/user: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/annotations", methods=["POST"])
@require_auth
def create_annotation():
    """Create a new annotation"""
    try:
        uid = request.uid
        data = request.get_json()

        surah = data.get('surah')
        verse = data.get('verse')
        annotation_type = data.get('type', 'personal_insight')
        content = data.get('content', '')
        tags = data.get('tags', [])
        linked_verses = data.get('linkedVerses', [])

        if not surah or not verse:
            return jsonify({"error": "Surah and verse are required"}), 400

        if not content:
            return jsonify({"error": "Content is required"}), 400

        # Validate verse reference
        is_valid, msg = validate_verse_reference(surah, verse)
        if not is_valid:
            return jsonify({"error": msg}), 400

        annotations_ref = users_db.collection('users').document(uid).collection('annotations')
        doc_ref = annotations_ref.document()

        annotation_data = {
            'surah': surah,
            'verse': verse,
            'type': annotation_type,
            'content': content,
            'tags': tags,
            'linkedVerses': linked_verses,
            'isPrivate': data.get('isPrivate', True),
            'createdAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }

        doc_ref.set(annotation_data)

        return jsonify({
            'success': True,
            'id': doc_ref.id,
            'annotation': annotation_data
        }), 201

    except Exception as e:
        print(f"ERROR in POST /annotations: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/annotations/<annotation_id>", methods=["PUT"])
@require_auth
def update_annotation(annotation_id):
    """Update an existing annotation"""
    try:
        uid = request.uid
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
@require_auth
def delete_annotation(annotation_id):
    """Delete an annotation"""
    try:
        uid = request.uid

        doc_ref = users_db.collection('users').document(uid).collection('annotations').document(annotation_id)
        doc_ref.delete()

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"ERROR in DELETE /annotations: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/annotations/search", methods=["GET"])
@require_auth
def search_annotations():
    """Search annotations by text content"""
    try:
        uid = request.uid
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
                results.append({
                    'id': doc.id,
                    'surah': data.get('surah'),
                    'verse': data.get('verse'),
                    'verseRef': f"{data.get('surah')}:{data.get('verse')}",
                    'type': data.get('type'),
                    'content': data.get('content'),
                    'tags': data.get('tags', []),
                    'createdAt': data.get('createdAt')
                })

        return jsonify({'results': results, 'count': len(results)}), 200

    except Exception as e:
        print(f"ERROR in /annotations/search: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/annotations/tags", methods=["GET"])
@require_auth
def get_all_tags():
    """Get all unique tags used by user"""
    try:
        uid = request.uid

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
    HYBRID tafsir endpoint with 3-tier intelligent routing:

    1. METADATA QUERIES (e.g., "hadith in 2:255")
       - Direct lookup (~50ms)
       - AI formats response with persona (1 LLM call)
       - Total: ~1-2s, 50% cheaper than full RAG

    2. DIRECT VERSE QUERIES (e.g., "2:255", "ayat al kursi")
       - Direct lookup (~50ms)
       - AI formats tafsir with persona (1 LLM call)
       - Total: ~1-2s, 50% cheaper than full RAG

    3. SEMANTIC QUERIES (e.g., "explain charity")
       - Full RAG pipeline:
         * Query expansion (1 LLM call)
         * Vector search
         * Context building
         * AI generation (1 LLM call)
       - Total: ~3-5s, 2 LLM calls

    Routes 1 & 2 skip expensive RAG but keep AI quality & persona adaptation!
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        user_id = request.user.get('uid')

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        # Rate limiting
        if is_rate_limited(user_id):
            return jsonify({'error': 'Rate limit exceeded'}), 429

        # Analytics
        ANALYTICS[query] += 1

        print(f"\n{'='*70}")
        print(f"📥 QUERY: {query}")
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
                prompt = build_enhanced_prompt(query, context_by_source, user_profile,
                                             arabic_text, None, 'metadata', verse_data)

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
                        "maxOutputTokens": 8192
                    },
                }

                response = requests.post(
                    VERTEX_ENDPOINT,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=body,
                    timeout=120
                )
                response.raise_for_status()

                # Parse response
                raw_response = response.json()
                if "candidates" in raw_response and raw_response["candidates"]:
                    generated_text = raw_response["candidates"][0]["content"]["parts"][0]["text"]
                    final_json = json.loads(generated_text)
                    final_json["query_type"] = "direct_metadata"
                    final_json["verse_reference"] = f"{surah}:{verse}"

                    print(f"✅ Metadata formatted by AI from {len(verse_metadata_list)} source(s)")
                    return jsonify(final_json), 200
                else:
                    # Fallback to structured response
                    response = format_metadata_response(verse_ref, metadata_type or 'all', verse_metadata_list)
                    return jsonify(response), 200

        # ===================================================================
        # ROUTE 2: DIRECT VERSE QUERY (Direct lookup → AI formatting)
        # ===================================================================
        if query_type == 'direct_verse' and verse_ref:
            print("🚀 ROUTE 2: Direct Verse Query → AI Formatting")

            surah, verse = verse_ref

            # Get verse text from Firestore
            verse_data = get_verse_from_firestore(surah, verse)
            if not verse_data:
                print(f"⚠️  Verse not found in Firestore, trying semantic search")
                query_type = 'semantic'  # Fallback
            else:
                # Get metadata via direct lookup
                verse_metadata_list = get_verse_metadata_direct(surah, verse)

                if not verse_metadata_list:
                    print(f"⚠️  No tafsir found, trying semantic search")
                    query_type = 'semantic'  # Fallback
                else:
                    # Build context from direct lookup
                    context_by_source = {}

                    for item in verse_metadata_list:
                        source_name = item['source']
                        metadata = item['metadata']

                        # Extract comprehensive tafsir
                        context_parts = []

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
                    cross_refs = verse_metadata_list[0]['metadata'].get('cross_references', []) if verse_metadata_list else []

                    prompt = build_enhanced_prompt(query, context_by_source, user_profile,
                                                 arabic_text, cross_refs, 'direct_verse', verse_data)

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
                            "maxOutputTokens": 8192
                        },
                    }

                    response = requests.post(
                        VERTEX_ENDPOINT,
                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                        json=body,
                        timeout=120
                    )
                    response.raise_for_status()

                    # Parse response
                    raw_response = response.json()
                    if "candidates" in raw_response and raw_response["candidates"]:
                        generated_text = raw_response["candidates"][0]["content"]["parts"][0]["text"]
                        final_json = json.loads(generated_text)
                        final_json["query_type"] = "direct_verse"
                        final_json["verse_reference"] = f"{surah}:{verse}"

                        print(f"✅ Direct verse formatted by AI from {len(verse_metadata_list)} source(s)")
                        return jsonify(final_json), 200
                    else:
                        # Fallback to structured response
                        response = build_direct_verse_response(verse_data, verse_metadata_list)
                        return jsonify(response), 200

        # ===================================================================
        # ROUTE 3: SEMANTIC SEARCH (Full RAG pipeline)
        # ===================================================================
        if query_type == 'semantic':
            print("🚀 ROUTE 3: Semantic Search (Full RAG)")

            # Get user profile
            user_profile = get_user_profile(user_id)

            # Check cache
            cache_key = get_cache_key(query, user_profile)
            if cache_key in RESPONSE_CACHE:
                print(f"💾 Cache hit")
                return jsonify(RESPONSE_CACHE[cache_key]), 200

            # Prepare query
            if verse_ref:
                surah_num, verse_num = verse_ref
                verse_data = get_verse_from_firestore(surah_num, verse_num)
                if verse_data:
                    arabic_text = get_arabic_text_from_verse_data(verse_data)
                    rag_query = f"Surah {surah_num} verse {verse_num} {query}"
                else:
                    rag_query = query
                    verse_data = None
                    arabic_text = None
            else:
                rag_query = query
                verse_data = None
                arabic_text = None

            # Classify for RAG
            rag_query_type = "default" # Simplified; classification is now primary
            cross_refs = get_cross_references(rag_query)

            # Get auth token
            credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            auth_req = GoogleRequest()
            credentials.refresh(auth_req)
            token = credentials.token

            # Query expansion
            expanded_query = expand_query(rag_query, token)

            # Initialize models
            embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
            endpoint_resource_name = f"projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
            index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_resource_name)

            # Perform search
            selected_chunks, context_by_source = perform_diversified_rag_search(
                rag_query, expanded_query, embedding_model, index_endpoint, rag_query_type
            )

            print(f"   Retrieved {len(selected_chunks)} chunks")

            # Build prompt
            prompt = build_enhanced_prompt(rag_query, context_by_source, user_profile,
                                         arabic_text, cross_refs, rag_query_type, verse_data)

            # Generate response
            VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

            body = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generation_config": {
                    "response_mime_type": "application/json",
                    "temperature": 0.2,
                    "maxOutputTokens": 8192
                },
            }

            response = requests.post(
                VERTEX_ENDPOINT,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body,
                timeout=120
            )
            response.raise_for_status()

            # Parse response
            raw_response = response.json()
            if "candidates" in raw_response and raw_response["candidates"]:
                try:
                    generated_text = raw_response["candidates"][0]["content"]["parts"][0]["text"]
                    final_json = json.loads(generated_text)

                    # Enhance with verse data
                    if verse_data:
                        final_json["verses"] = [{
                            "surah": verse_data['surah_name'],
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
                        return jsonify({"error": "Response quality not met"}), 500

                    # Cache
                    RESPONSE_CACHE[cache_key] = final_json
                    if len(RESPONSE_CACHE) > 1000:
                        keys_to_remove = list(RESPONSE_CACHE.keys())[:200]
                        for key in keys_to_remove:
                            del RESPONSE_CACHE[key]

                    print(f"✅ Semantic response generated")
                    return jsonify(final_json), 200

                except (KeyError, IndexError, json.JSONDecodeError) as e:
                    print(f"ERROR parsing response: {e}")
                    return jsonify({"error": "Failed to parse AI response"}), 500
            else:
                return jsonify({"error": "AI returned empty response"}), 500

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
        "system_type": "hybrid",
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

# --- Main ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host="0.0.0.0", port=port)
