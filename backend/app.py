import os
import json
import re
import traceback
import time
import hashlib
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta

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

# --- Configuration (UPDATED for cross-project setup) ---
# Firebase project (Auth, Firestore, Users, Quran texts)
FIREBASE_PROJECT = os.environ.get("FIREBASE_PROJECT", "tafsir-simplified-6b262")
# GCP infrastructure project (Vertex AI, GCS, Cloud Run)
GCP_INFRASTRUCTURE_PROJECT = os.environ.get("GCP_INFRASTRUCTURE_PROJECT", "tafsir-simplified")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-2.0-flash")
FIREBASE_SECRET_FULL_PATH = os.environ.get("FIREBASE_SECRET_FULL_PATH")
INDEX_ENDPOINT_ID = os.environ.get("INDEX_ENDPOINT_ID")
DEPLOYED_INDEX_ID = os.environ.get("DEPLOYED_INDEX_ID")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

# Multi-source chunk file paths (for RAG)
GCS_JALALAYN_PATH = 'jalalayn_chunks.json'
GCS_QURTUBI_PATH = 'qurtubi_chunks.json'
GCS_IBN_KATHIR_PATH = 'ibn_kathir_chunks.json'

# --- Startup Validation (Fail Fast) ---
if not FIREBASE_SECRET_FULL_PATH or not INDEX_ENDPOINT_ID or not DEPLOYED_INDEX_ID or not GCS_BUCKET_NAME:
    raise ValueError("CRITICAL STARTUP ERROR: Missing required RAG environment variables")

# Global variables - UPDATED for dual database setup
users_db = None     # Firebase Admin SDK -> (default) database for users/auth
quran_db = None     # Google Cloud client -> tafsir-db database for Quran texts
TAFSIR_CHUNKS = {}
RESPONSE_CACHE = {}  # In-memory cache
USER_RATE_LIMITS = defaultdict(list)  # Rate limiting
ANALYTICS = defaultdict(int)  # Usage analytics

# --- NEW: Complete Quran Metadata for Verse Validation ---
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
    "legal": {"al-Qurtubi": 0.5, "Ibn Kathir": 0.3, "al-Jalalayn": 0.2},
    "historical": {"Ibn Kathir": 0.5, "al-Qurtubi": 0.3, "al-Jalalayn": 0.2},
    "concise": {"al-Jalalayn": 0.5, "al-Qurtubi": 0.3, "Ibn Kathir": 0.2},
    "default": {"al-Jalalayn": 0.33, "al-Qurtubi": 0.33, "Ibn Kathir": 0.34}
}

# --- NEW: Query Normalization Functions ---
def validate_verse_reference(surah, verse):
    """Validate that surah and verse numbers are within valid ranges"""
    if surah not in QURAN_METADATA:
        return False, f"Invalid Surah: {surah}. The Quran has 114 Surahs."
    
    max_verses = QURAN_METADATA[surah]["verses"]
    if not (1 <= verse <= max_verses):
        surah_name = QURAN_METADATA[surah]["name"]
        return False, f"Invalid verse: {verse}. Surah {surah} ('{surah_name}') only has {max_verses} verses."
    
    return True, "Valid reference"

def normalize_verse_reference(query):
    """
    Normalize different verse reference formats to standard (surah, verse) tuple
    Returns (surah_num, verse_num) if verse reference detected, None otherwise
    """
    query_clean = re.sub(r'^(verse|ayat|ayah)\s+', '', query.lower().strip())
    
    # Pattern 1: "2:255", "2 : 255"
    pattern1 = re.match(r'^(\d+)\s*:\s*(\d+)$', query_clean)
    if pattern1:
        surah, verse = int(pattern1.group(1)), int(pattern1.group(2))
        is_valid, msg = validate_verse_reference(surah, verse)
        if is_valid:
            return (surah, verse)
    
    # Pattern 2: "Surah 2 verse 255", "Al-Baqarah verse 255"
    pattern2 = re.search(r'(?:surah\s+)?(?:al-)?(\w+)\s+(?:verse|ayat|ayah)\s+(\d+)', query_clean)
    if pattern2:
        surah_name = pattern2.group(1).lower()
        verse_num = int(pattern2.group(2))
        
        # Try to find surah by name
        for name, surah_num in SURAHS_BY_NAME.items():
            if surah_name in name or name in surah_name:
                is_valid, msg = validate_verse_reference(surah_num, verse_num)
                if is_valid:
                    return (surah_num, verse_num)
    
    # Pattern 3: "surah 2 ayat 255" or similar
    pattern3 = re.search(r'surah\s+(\d+).*?(\d+)', query_clean)
    if pattern3:
        surah, verse = int(pattern3.group(1)), int(pattern3.group(2))
        is_valid, msg = validate_verse_reference(surah, verse)
        if is_valid:
            return (surah, verse)
    
    return None

# --- NEW: Firestore Verse Lookup (UPDATED for dual database) ---
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

def classify_query_type(query):
    """Classify query to determine source weighting"""
    legal_keywords = ["halal", "haram", "ruling", "law", "jurisprudence", "legal", "permissible"]
    historical_keywords = ["story", "history", "Prophet", "Moses", "Jesus", "Abraham", "battle"]
    concise_keywords = ["brief", "short", "quick", "summary", "simple"]
    
    query_lower = query.lower()
    
    if any(keyword in query_lower for keyword in legal_keywords):
        return "legal"
    elif any(keyword in query_lower for keyword in historical_keywords):
        return "historical"
    elif any(keyword in query_lower for keyword in concise_keywords):
        return "concise"
    else:
        return "default"

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
        required_fields = ["verses", "tafsir_explanations", "lessons_practical_applications"]
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

# --- Data Loading & Firebase Initialization (UPDATED for dual database) ---
def load_chunks_from_gcs():
    """Load chunks from all three tafsir sources"""
    global TAFSIR_CHUNKS
    try:
        storage_client = storage.Client(project=GCP_INFRASTRUCTURE_PROJECT)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        
        # Define all source files
        chunk_files = [
            (GCS_JALALAYN_PATH, "al-Jalalayn"),
            (GCS_QURTUBI_PATH, "al-Qurtubi"), 
            (GCS_IBN_KATHIR_PATH, "Ibn Kathir")
        ]
        
        total_chunks = 0
        
        for file_path, source_name in chunk_files:
            try:
                print(f"INFO: Loading {source_name} chunks from gs://{GCS_BUCKET_NAME}/{file_path}")
                blob = bucket.blob(file_path)
                
                if not blob.exists():
                    print(f"WARNING: {file_path} not found, skipping {source_name}")
                    continue
                
                contents = blob.download_as_string()
                chunks_list = json.loads(contents)
                
                # Convert list to dictionary with source-specific IDs that match vector index format
                source_chunks = 0
                for i, chunk in enumerate(chunks_list):
                    # Create unique IDs that match the existing vector index format
                    if source_name == "al-Jalalayn":
                        # Keep existing format (it works with vector index)
                        datapoint_id = f"jalalayn_page_{chunk.get('page_number', i)}_{i}"
                    elif source_name == "al-Qurtubi":
                        # Match vector index format: qurtubi_vol_X_page_Y_Z
                        vol = chunk.get('volume', 1)
                        page = chunk.get('page_number', i)
                        datapoint_id = f"qurtubi_vol_{vol}_page_{page}_{i}"
                    elif source_name == "Ibn Kathir":
                        # Apply +1463 offset to match vector index numbering
                        page = chunk.get('page_number', i)
                        chunk_idx = chunk.get('chunk_index_on_page', i)
                        adjusted_page = page + 1463
                        adjusted_chunk_idx = chunk_idx + 1463
                        datapoint_id = f"ibn_kathir_page_{adjusted_page}_{adjusted_chunk_idx}"
                    
                    TAFSIR_CHUNKS[datapoint_id] = chunk.get('text', '')
                    source_chunks += 1
                
                print(f"INFO: Loaded {source_chunks} chunks from {source_name}")
                total_chunks += source_chunks
                
            except Exception as e:
                print(f"ERROR loading {source_name}: {type(e).__name__} - {e}")
                continue
        
        print(f"INFO: Successfully loaded {total_chunks} total chunks from all sources")
        
        if total_chunks == 0:
            raise RuntimeError("CRITICAL: No chunks loaded from any source")
        
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR loading chunks: {type(e).__name__} - {e}")
        raise

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
        # This connects to the (default) database automatically
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred, {'projectId': FIREBASE_PROJECT})
        users_db = firestore.client()  # (default) database
        
        print(f"INFO: Firebase Admin SDK initialized for project '{FIREBASE_PROJECT}'")
        print(f"INFO: User profiles database connected: (default)")
        
        # 2. Initialize Google Cloud Firestore client for Quran texts
        # This can connect to specific databases like 'tafsir-db'
        quran_db = gcp_firestore.Client(
            project=FIREBASE_PROJECT,
            database='tafsir-db'
        )
        
        print(f"INFO: Quran texts database connected: tafsir-db")
        
        # 3. Test both connections
        try:
            # Test user database
            users_collections = list(users_db.collections())
            print(f"INFO: Users database verified - found {len(users_collections)} collections")
            
            # Test Quran database  
            quran_collections = list(quran_db.collections())
            print(f"INFO: Quran database verified - found {len(quran_collections)} collections")
            
        except Exception as e:
            print(f"WARNING: Database verification failed: {e}")
            
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR in initialize_firebase: {type(e).__name__} - {e}")
        raise

# Initialize services on startup (fail fast if any critical component fails)
initialize_firebase()
load_chunks_from_gcs()
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
You are helping expand a query to search Islamic tafsir (Quranic commentary) texts from multiple classical sources including Tafsir al-Jalalayn, al-Qurtubi, and Ibn Kathir.

Original query: "{query}"

Expand this query by adding relevant Islamic terms, Arabic concepts, Quranic themes, and related theological concepts that would help find relevant tafsir passages from these classical commentaries. Consider:
- Related Arabic terminology
- Connected Quranic verses or themes  
- Islamic jurisprudence concepts (especially for al-Qurtubi)
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

# --- Enhanced Multi-Source RAG Functions ---
def perform_diversified_rag_search(query, expanded_query, embedding_model, index_endpoint, query_type="default"):
    """Enhanced RAG with source weighting based on query type"""
    
    # Step 1: Single expanded query (maintains semantic relevance)
    query_embedding = embedding_model.get_embeddings([expanded_query], output_dimensionality=1024)[0].values
    
    # Step 2: Retrieve larger pool of candidates (25 chunks for better diversity)
    neighbors_result = index_endpoint.find_neighbors(
        deployed_index_id=DEPLOYED_INDEX_ID,
        queries=[query_embedding],
        num_neighbors=25  # Increased for better source coverage
    )
    
    # Step 3: Intelligent source diversification with weighting
    source_chunks = {
        'al-Jalalayn': [],
        'al-Qurtubi': [],
        'Ibn Kathir': []
    }
    
    # Categorize all retrieved chunks by source
    for neighbor in neighbors_result[0]:
        chunk_id = neighbor.id
        chunk_text = TAFSIR_CHUNKS.get(chunk_id, '')
        distance = neighbor.distance
        
        if not chunk_text:
            continue
            
        chunk_data = {
            'text': chunk_text,
            'distance': distance,
            'chunk_id': chunk_id
        }
        
        if chunk_id.startswith('jalalayn'):
            source_chunks['al-Jalalayn'].append(chunk_data)
        elif chunk_id.startswith('qurtubi'):
            source_chunks['al-Qurtubi'].append(chunk_data)
        elif chunk_id.startswith('ibn_kathir'):
            source_chunks['Ibn Kathir'].append(chunk_data)
    
    # Step 4: Weighted selection based on query type
    weights = SOURCE_WEIGHTS.get(query_type, SOURCE_WEIGHTS["default"])
    selected_chunks = []
    context_by_source = {}
    
    for source_name, chunks in source_chunks.items():
        if chunks:
            # Sort by distance (most relevant first)
            sorted_chunks = sorted(chunks, key=lambda x: x['distance'])
            
            # Apply weighting - take more chunks from preferred sources
            weight = weights.get(source_name, 0.33)
            num_chunks = max(2, int(weight * 10))  # 2-5 chunks based on weight
            
            top_chunks = sorted_chunks[:num_chunks]
            selected_chunks.extend(top_chunks)
            context_by_source[source_name] = [chunk['text'] for chunk in top_chunks]
        else:
            # Mark source as having no relevant content
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
            # Include placeholder for sources with no content
            section = f"--- {source_name.upper()} ---\n[No highly relevant passages found]"
            context_sections.append(section)
    
    return "\n\n" + "\n\n".join(context_sections)

def build_enhanced_prompt(query, context_by_source, user_profile, arabic_text=None, cross_refs=None, query_type="default", verse_data=None):
    """Enhanced prompt with Arabic text, cross-references, and verse data integration"""
    structured_context = build_structured_context(context_by_source, arabic_text, cross_refs)
    
    # Add verse information if available
    verse_info = ""
    if verse_data:
        verse_info = f"""
--- VERSE DETAILS ---
Surah: {verse_data['surah_number']} ({verse_data['surah_name']})
Verse: {verse_data['verse_number']}
Arabic: {verse_data['arabic']}
English Translation: {verse_data['english']}
Transliteration: {verse_data['transliteration']}
"""
    
    prompt = f"""You are an expert Islamic scholar providing Quranic commentary (tafsir) analysis.

QUERY: "{query}"
QUERY TYPE: {query_type}

{verse_info}

CONTEXT FROM CLASSICAL TAFSIR SOURCES:
{structured_context}

CRITICAL INSTRUCTIONS - ENHANCED SCHOLARLY APPROACH:
1. **Source Authority**: Consider source expertise - al-Qurtubi for legal matters, Ibn Kathir for historical context, al-Jalalayn for concise explanations
2. **Arabic Integration**: If Arabic text is provided, reference it appropriately in explanations
3. **Cross-References**: If related verses are provided, mention relevant connections
4. **Quality Over Balance**: Emphasize sources with substantial relevant content while acknowledging all available sources
5. **Scholarly Integrity**: Never fabricate content - acknowledge when sources have limited relevant material
6. User preference: {user_profile.get('knowledge_level', 'intermediate')} level, {user_profile.get('verbosity', 'balanced')} detail

ENHANCED JSON FORMAT:
{{
    "verses": [
        {{"surah": "string", "verse_number": "string", "text_saheeh_international": "string", "arabic_text": "{arabic_text or verse_data.get('arabic', 'Not available') if verse_data else 'Not available'}"}}
    ],
    "tafsir_explanations": [
        {{"source": "al-Jalalayn", "explanation": "Detailed explanation with source expertise consideration"}},
        {{"source": "al-Qurtubi", "explanation": "Detailed explanation emphasizing legal/jurisprudential aspects when relevant"}},
        {{"source": "Ibn Kathir", "explanation": "Detailed explanation emphasizing historical context and hadith when relevant"}}
    ],
    "cross_references": [
        {{"verse": "string", "relevance": "brief explanation of connection"}}
    ],
    "lessons_practical_applications": [
        {{"point": "Key lesson 1"}}, {{"point": "Key lesson 2"}}, {{"point": "Key lesson 3"}}
    ],
    "summary": "Synthesis reflecting scholarly depth and source expertise"
}}

SCHOLARLY PRINCIPLE: Provide authentic, well-attributed commentary that respects each source's scholarly strengths."""
    
    return prompt

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

# --- API Routes ---
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
        # Check if user is admin (implement your admin check logic)
        user_email = request.user.get('email', '')
        if not user_email.endswith('@yourdomain.com'):  # Replace with your admin domain
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
    """Get user's learning profile from (default) database"""
    uid = request.user["uid"]
    try:
        user_doc = users_db.collection("users").document(uid).get()
        if user_doc.exists:
            return jsonify(user_doc.to_dict()), 200
        return jsonify({"error": "Profile not found"}), 404
    except Exception as e:
        print(f"ERROR in /get_profile: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/set_profile", methods=["POST"])
@firebase_auth_required  
def set_profile():
    """Set or update user's learning profile in (default) database"""
    uid = request.user["uid"]
    data = request.get_json()
    
    level = data.get("level")
    focus = data.get("focus", "practical")
    verbosity = data.get("verbosity", "medium")

    # Validate profile data
    if level not in ["casual", "beginner", "intermediate", "advanced"]:
        return jsonify({"error": "Invalid level. Must be: casual, beginner, intermediate, or advanced"}), 400
    if focus not in ["practical", "linguistic", "comparative", "thematic"]:
        return jsonify({"error": "Invalid focus. Must be: practical, linguistic, comparative, or thematic"}), 400
    if verbosity not in ["short", "medium", "detailed"]:
        return jsonify({"error": "Invalid verbosity. Must be: short, medium, or detailed"}), 400

    try:
        profile_data = {
            "level": level,
            "focus": focus, 
            "verbosity": verbosity
        }
        users_db.collection("users").document(uid).set(profile_data, merge=True)
        return jsonify({
            "status": "success", 
            "uid": uid,
            "profile": profile_data
        }), 200
    except Exception as e:
        print(f"ERROR in /set_profile: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/verse/<int:surah>/<int:verse>", methods=["GET"])
def get_specific_verse(surah, verse):
    """Direct endpoint for verse lookup"""
    try:
        # Validate verse reference
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

@app.route("/tafsir", methods=["POST"])
@firebase_auth_required
@handle_errors
def tafsir_handler():
    """Enhanced tafsir endpoint with verse lookup + tafsir commentary integration"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        user_id = request.user.get('uid')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Rate limiting check
        if is_rate_limited(user_id):
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
        
        # Analytics tracking
        ANALYTICS[query] += 1
        
        # Get user profile for personalization
        user_profile = get_user_profile(user_id)
        
        # Check cache first
        cache_key = get_cache_key(query, user_profile)
        if cache_key in RESPONSE_CACHE:
            print(f"Cache hit for query: {query}")
            return jsonify(RESPONSE_CACHE[cache_key]), 200
        
        # NEW: Check if this is a verse reference query
        verse_ref = normalize_verse_reference(query)
        verse_data = None
        arabic_text = None
        
        if verse_ref:
            # Direct verse query - get translation data
            surah_num, verse_num = verse_ref
            verse_data = get_verse_from_firestore(surah_num, verse_num)
            if not verse_data:
                return jsonify({'error': f'Verse {surah_num}:{verse_num} not found'}), 404
            
            # Extract Arabic text for RAG context
            arabic_text = get_arabic_text_from_verse_data(verse_data)
            
            # Modify query for RAG search to focus on this specific verse
            rag_query = f"Surah {surah_num} verse {verse_num} {query}"
        else:
            # Thematic query - use original query for RAG
            rag_query = query
        
        # Classify query type for source weighting
        query_type = classify_query_type(rag_query)
        
        # Get cross-references
        cross_refs = get_cross_references(rag_query)
        
        # Get authentication token for Vertex AI
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        token = credentials.token

        # RAG Step 1: Expand the query for better semantic matching
        print(f"RAG: Processing query: '{rag_query}' (type: {query_type})")
        expanded_query = expand_query(rag_query, token)

        # RAG Step 2: Initialize models
        embedding_model = TextEmbeddingModel.from_pretrained("gemini-embedding-001")
        endpoint_resource_name = f"projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_resource_name)
        
        # RAG Step 3: Perform enhanced diversified search
        selected_chunks, context_by_source = perform_diversified_rag_search(
            rag_query, expanded_query, embedding_model, index_endpoint, query_type
        )
        
        # Debug logging
        print(f"Original Query: {query}")
        print(f"RAG Query: {rag_query} | Type: {query_type}")
        print(f"Verse Reference: {verse_ref}")
        print(f"Sources with content: {[s for s, c in context_by_source.items() if c]}")
        print(f"Total chunks retrieved: {len(selected_chunks)}")
        for source, chunks in context_by_source.items():
            print(f"{source}: {len(chunks)} chunks")
        if arabic_text:
            print(f"Arabic text included: {arabic_text[:50]}...")
        if cross_refs:
            print(f"Cross-references: {cross_refs}")
        
        # RAG Step 4: Build enhanced prompt with verse data integration
        prompt = build_enhanced_prompt(rag_query, context_by_source, user_profile, arabic_text, cross_refs, query_type, verse_data)
        
        # RAG Step 5: Generate response with Gemini
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

        # Parse and validate response
        raw_response = response.json()
        if "candidates" in raw_response and raw_response["candidates"]:
            try:
                generated_text = raw_response["candidates"][0]["content"]["parts"][0]["text"]
                final_json = json.loads(generated_text)
                
                # NEW: Enhance response with verse data if available
                if verse_data:
                    # Update the verses field with actual verse data
                    final_json["verses"] = [{
                        "surah": verse_data['surah_name'],
                        "verse_number": str(verse_data['verse_number']),
                        "text_saheeh_international": verse_data['english'],
                        "arabic_text": verse_data['arabic']
                    }]
                    
                    # Add query type indicator
                    final_json["query_type"] = "direct_verse"
                    final_json["verse_reference"] = f"{verse_data['surah_number']}:{verse_data['verse_number']}"
                else:
                    final_json["query_type"] = "thematic"
                
                # Validate response quality
                is_valid, validation_msg = validate_response(final_json)
                if not is_valid:
                    print(f"Response validation failed: {validation_msg}")
                    # Don't cache invalid responses
                    return jsonify({"error": "Generated response did not meet quality standards. Please try again."}), 500
                
                # Cache successful response (in production, use Redis with TTL)
                RESPONSE_CACHE[cache_key] = final_json
                
                # Clean cache if it gets too large (basic memory management)
                if len(RESPONSE_CACHE) > 1000:
                    # Remove oldest 20% of entries
                    keys_to_remove = list(RESPONSE_CACHE.keys())[:200]
                    for key in keys_to_remove:
                        del RESPONSE_CACHE[key]
                
                return jsonify(final_json), 200
                
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"ERROR parsing Gemini response: {type(e).__name__} - {e}")
                print(f"Raw response: {raw_response}")
                return jsonify({"error": "Failed to parse AI response"}), 500
        else:
            print(f"ERROR: Unexpected response structure: {raw_response}")
            return jsonify({"error": "AI service returned empty or blocked response"}), 500

    except requests.exceptions.Timeout:
        return jsonify({"error": "AI service timed out"}), 504
    except requests.exceptions.HTTPError as http_err:
        return jsonify({"error": f"HTTP error: {http_err}", "details": http_err.response.text}), http_err.response.status_code
    except Exception as e:
        print(f"CRITICAL ERROR in /tafsir RAG pipeline: {type(e).__name__} - {e}")
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500

# --- Health Check ---
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "chunks_loaded": len(TAFSIR_CHUNKS),
        "cache_size": len(RESPONSE_CACHE),
        "firebase_project": FIREBASE_PROJECT,
        "infrastructure_project": GCP_INFRASTRUCTURE_PROJECT
    }), 200

# --- Debug Endpoints ---
@app.route('/debug-sources', methods=['GET'])
def debug_sources():
    """Debug endpoint to see what sources are actually in the vector index"""
    try:
        # Test with multiple queries to get a good sample
        test_queries = ["Allah", "Quran", "verse", "surah", "Prophet", "Islam"]
        all_sources = set()
        source_counts = {}
        sample_texts = {}
        
        # Get authentication token for Vertex AI
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        token = credentials.token
        
        # Initialize models
        embedding_model = TextEmbeddingModel.from_pretrained("gemini-embedding-001")
        endpoint_resource_name = f"projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_resource_name)
        
        for query in test_queries:
            try:
                # Get embedding and search
                query_embedding = embedding_model.get_embeddings([query], output_dimensionality=1024)[0].values
                neighbors_result = index_endpoint.find_neighbors(
                    deployed_index_id=DEPLOYED_INDEX_ID,
                    queries=[query_embedding],
                    num_neighbors=10
                )
                
                print(f"DEBUG: Query '{query}' returned {len(neighbors_result[0])} results")
                
                for neighbor in neighbors_result[0]:
                    chunk_id = neighbor.id
                    chunk_text = TAFSIR_CHUNKS.get(chunk_id, '')
                    
                    # Determine source from chunk_id
                    if chunk_id.startswith('jalalayn'):
                        source = 'Tafsir al-Jalalayn'
                    elif chunk_id.startswith('qurtubi'):
                        source = 'Tafsir al-Qurtubi'
                    elif chunk_id.startswith('ibn_kathir'):
                        source = 'Tafsir Ibn Kathir'
                    else:
                        source = 'Unknown'
                    
                    all_sources.add(source)
                    source_counts[source] = source_counts.get(source, 0) + 1
                    
                    # Store a sample text for each source
                    if source not in sample_texts:
                        sample_texts[source] = {
                            'text_preview': chunk_text[:150] if chunk_text else 'No text found',
                            'chunk_id': chunk_id
                        }
                        
            except Exception as e:
                print(f"Error with query '{query}': {str(e)}")
                continue
        
        return jsonify({
            "status": "success",
            "total_unique_sources": len(all_sources),
            "sources_found": list(all_sources),
            "source_distribution": source_counts,
            "sample_data": sample_texts,
            "vector_index_total_count": len(TAFSIR_CHUNKS),
            "chunks_by_source": {
                "jalalayn_chunks": len([k for k in TAFSIR_CHUNKS.keys() if k.startswith('jalalayn')]),
                "qurtubi_chunks": len([k for k in TAFSIR_CHUNKS.keys() if k.startswith('qurtubi')]),
                "ibn_kathir_chunks": len([k for k in TAFSIR_CHUNKS.keys() if k.startswith('ibn_kathir')])
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/debug-id-match', methods=['GET'])
def debug_id_match():
    """Test specific chunk IDs from the debug output"""
    # Test specific chunk IDs from the debug output
    test_cases = {
        "jalalayn_works": {
            "chunk_id": "jalalayn_page_49_46",
            "text_exists": "jalalayn_page_49_46" in TAFSIR_CHUNKS,
            "text_preview": TAFSIR_CHUNKS.get("jalalayn_page_49_46", "NOT_FOUND")[:100]
        },
        "ibn_kathir_test": {
            "chunk_id": "ibn_kathir_page_1464_1463", 
            "text_exists": "ibn_kathir_page_1464_1463" in TAFSIR_CHUNKS,
            "text_preview": TAFSIR_CHUNKS.get("ibn_kathir_page_1464_1463", "NOT_FOUND")[:100]
        },
        "qurtubi_test": {
            "chunk_id": "qurtubi_vol_3_page_415_1664",
            "text_exists": "qurtubi_vol_3_page_415_1664" in TAFSIR_CHUNKS, 
            "text_preview": TAFSIR_CHUNKS.get("qurtubi_vol_3_page_415_1664", "NOT_FOUND")[:100]
        }
    }
    
    # Also show what IDs are actually being generated for each source
    sample_generated_ids = {
        "jalalayn_ids": [k for k in TAFSIR_CHUNKS.keys() if k.startswith('jalalayn')][:3],
        "qurtubi_ids": [k for k in TAFSIR_CHUNKS.keys() if k.startswith('qurtubi')][:3], 
        "ibn_kathir_ids": [k for k in TAFSIR_CHUNKS.keys() if k.startswith('ibn_kathir')][:3]
    }
    
    return jsonify({
        "test_cases": test_cases,
        "sample_generated_ids": sample_generated_ids
    })

# --- Main ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host="0.0.0.0", port=port)
