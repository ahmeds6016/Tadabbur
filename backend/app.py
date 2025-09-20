import os
import json
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

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "tafsir-simplified")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-2.0-flash")
FIREBASE_SECRET_FULL_PATH = os.environ.get("FIREBASE_SECRET_FULL_PATH")
INDEX_ENDPOINT_ID = os.environ.get("INDEX_ENDPOINT_ID")
DEPLOYED_INDEX_ID = os.environ.get("DEPLOYED_INDEX_ID")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

# Multi-source chunk file paths
GCS_JALALAYN_PATH = 'jalalayn_chunks.json'
GCS_QURTUBI_PATH = 'qurtubi_chunks.json'
GCS_IBN_KATHIR_PATH = 'ibn_kathir_chunks.json'

# --- Startup Validation (Fail Fast) ---
if not FIREBASE_SECRET_FULL_PATH or not INDEX_ENDPOINT_ID or not DEPLOYED_INDEX_ID or not GCS_BUCKET_NAME:
    raise ValueError("CRITICAL STARTUP ERROR: Missing required RAG environment variables")

# Global variables
TAFSIR_CHUNKS = {}
RESPONSE_CACHE = {}  # In-memory cache
USER_RATE_LIMITS = defaultdict(list)  # Rate limiting
ANALYTICS = defaultdict(int)  # Usage analytics

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

# Arabic text samples (in production, this would be from a database)
ARABIC_TEXTS = {
    "2:255": "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ",
    "1:1": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
}

# Source authority weights by query type
SOURCE_WEIGHTS = {
    "legal": {"al-Qurtubi": 0.5, "Ibn Kathir": 0.3, "al-Jalalayn": 0.2},
    "historical": {"Ibn Kathir": 0.5, "al-Qurtubi": 0.3, "al-Jalalayn": 0.2},
    "concise": {"al-Jalalayn": 0.5, "al-Qurtubi": 0.3, "Ibn Kathir": 0.2},
    "default": {"al-Jalalayn": 0.33, "al-Qurtubi": 0.33, "Ibn Kathir": 0.34}
}

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

def get_arabic_text(query):
    """Get Arabic text if available"""
    for verse_ref, arabic in ARABIC_TEXTS.items():
        if verse_ref in query:
            return arabic
    return None

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

# --- Data Loading & Firebase Initialization ---
def load_chunks_from_gcs():
    """Load chunks from all three tafsir sources"""
    global TAFSIR_CHUNKS
    try:
        storage_client = storage.Client()
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
                        # FIXED: Apply +1463 offset to match vector index numbering
                        # Vector index expects ibn_kathir_page_1464_1463 format
                        # Your chunks are sequential paragraphs numbered 1, 2, 3...
                        page = chunk.get('page_number', i)  # Sequential paragraph number
                        chunk_idx = chunk.get('chunk_index_on_page', i)  # Usually 0
                        
                        # Apply offset: paragraph 1 -> page 1464, paragraph 2 -> page 1465, etc.
                        adjusted_page = page + 1463
                        adjusted_chunk_idx = chunk_idx + 1463  # Also adjust chunk index
                        
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
    """Initialize Firebase Admin SDK"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(name=FIREBASE_SECRET_FULL_PATH)
        secret_payload = response.payload.data.decode("UTF-8")
        cred_json = json.loads(secret_payload)
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred)
        print("INFO: Firebase App Initialized successfully")
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR in initialize_firebase: {type(e).__name__} - {e}")
        raise

# Initialize services on startup (fail fast if any critical component fails)
initialize_firebase()
load_chunks_from_gcs()
vertexai.init(project=PROJECT_ID, location=LOCATION)
db = firestore.client()

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
        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"
        
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
def perform_diversified_rag_search(query, expand_query, embedding_model, index_endpoint, query_type="default"):
    """
    Enhanced RAG with source weighting based on query type
    """
    
    # Step 1: Single expanded query (maintains semantic relevance)
    query_embedding = embedding_model.get_embeddings([expand_query], output_dimensionality=1024)[0].values
    
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
    """
    Build enhanced context blocks with Arabic text and cross-references
    """
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

def build_enhanced_prompt(query, context_by_source, user_profile, arabic_text=None, cross_refs=None, query_type="default"):
    """
    Enhanced prompt with Arabic text, cross-references, and source weighting
    """
    structured_context = build_structured_context(context_by_source, arabic_text, cross_refs)
    
    # Assess content quality and depth for each source
    source_quality = {}
    for source, chunks in context_by_source.items():
        if chunks:
            total_content = ' '.join(chunks)
            source_quality[source] = len(total_content)
        else:
            source_quality[source] = 0
    
    prompt = f"""You are an expert Islamic scholar providing Quranic commentary (tafsir) analysis.

QUERY: "{query}"
QUERY TYPE: {query_type}

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
        {{"surah": "string", "verse_number": "string", "text_saheeh_international": "string", "arabic_text": "{arabic_text or 'Not available'}"}}
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
    """Get user profile from Firestore"""
    try:
        if not user_id:
            return {}
        user_doc = db.collection("users").document(user_id).get()
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
    """Get user's learning profile"""
    uid = request.user["uid"]
    try:
        user_doc = db.collection("users").document(uid).get()
        if user_doc.exists:
            return jsonify(user_doc.to_dict()), 200
        return jsonify({"error": "Profile not found"}), 404
    except Exception as e:
        print(f"ERROR in /get_profile: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/set_profile", methods=["POST"])
@firebase_auth_required  
def set_profile():
    """Set or update user's learning profile"""
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
        db.collection("users").document(uid).set(profile_data, merge=True)
        return jsonify({
            "status": "success", 
            "uid": uid,
            "profile": profile_data
        }), 200
    except Exception as e:
        print(f"ERROR in /set_profile: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/tafsir", methods=["POST"])
@firebase_auth_required
@handle_errors
def tafsir_handler():
    """Enhanced tafsir endpoint with caching, rate limiting, and quality validation"""
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
        
        # Classify query type for source weighting
        query_type = classify_query_type(query)
        
        # Get Arabic text and cross-references
        arabic_text = get_arabic_text(query)
        cross_refs = get_cross_references(query)
        
        # Get authentication token for Vertex AI
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        token = credentials.token

        # RAG Step 1: Expand the query for better semantic matching
        print(f"RAG: Processing query: '{query}' (type: {query_type})")
        expanded_query = expand_query(query, token)

        # RAG Step 2: Initialize models
        embedding_model = TextEmbeddingModel.from_pretrained("gemini-embedding-001")
        endpoint_resource_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_resource_name)
        
        # RAG Step 3: Perform enhanced diversified search
        selected_chunks, context_by_source = perform_diversified_rag_search(
            query, expanded_query, embedding_model, index_endpoint, query_type
        )
        
        # Debug logging
        print(f"Query: {query} | Type: {query_type}")
        print(f"Sources with content: {[s for s, c in context_by_source.items() if c]}")
        print(f"Total chunks retrieved: {len(selected_chunks)}")
        for source, chunks in context_by_source.items():
            print(f"{source}: {len(chunks)} chunks")
        if arabic_text:
            print(f"Arabic text included: {arabic_text[:50]}...")
        if cross_refs:
            print(f"Cross-references: {cross_refs}")
        
        # RAG Step 4: Build enhanced prompt
        prompt = build_enhanced_prompt(query, context_by_source, user_profile, arabic_text, cross_refs, query_type)
        
        # RAG Step 5: Generate response with Gemini
        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"
        
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
        "cache_size": len(RESPONSE_CACHE)
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
        endpoint_resource_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
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

@app.route('/debug-large-sample', methods=['GET'])
def debug_large_sample():
    """Get larger sample of loaded chunk IDs and check pattern matching"""
    try:
        # Show samples of what we loaded vs what vector index expects
        loaded_samples = {}
        for source in ['jalalayn', 'qurtubi', 'ibn_kathir']:
            source_keys = [k for k in TAFSIR_CHUNKS.keys() if k.startswith(source)]
            loaded_samples[f"{source}_loaded"] = source_keys[:15]  # Show 15 samples each
            
        # Test some specific patterns that might exist in vector index
        test_patterns = {
            "qurtubi_vol_1_tests": [
                f"qurtubi_vol_1_page_{i}_{j}" for i in range(1, 20) for j in range(0, 3)
            ][:10],
            "qurtubi_vol_2_tests": [
                f"qurtubi_vol_2_page_{i}_{j}" for i in range(1, 20) for j in range(0, 3) 
            ][:10],
            "ibn_kathir_high_page_tests": [
                f"ibn_kathir_page_{i}_{j}" for i in range(1400, 1470) for j in range(0, 5)
            ][:15]
        }
        
        # Check which test patterns exist in our loaded chunks
        pattern_matches = {}
        for pattern_name, test_ids in test_patterns.items():
            matches = [tid for tid in test_ids if tid in TAFSIR_CHUNKS]
            pattern_matches[pattern_name] = {
                "matches_found": len(matches),
                "sample_matches": matches[:5],
                "total_tested": len(test_ids)
            }
        
        # Also check actual data from chunk files to understand structure
        sample_metadata = {}
        for source in ['jalalayn', 'qurtubi', 'ibn_kathir']:
            source_keys = [k for k in TAFSIR_CHUNKS.keys() if k.startswith(source)]
            if source_keys:
                sample_key = source_keys[0]
                # Try to extract metadata from key structure
                parts = sample_key.split('_')
                sample_metadata[source] = {
                    "sample_key": sample_key,
                    "key_parts": parts,
                    "total_chunks": len(source_keys)
                }
        
        return jsonify({
            "loaded_samples": loaded_samples,
            "pattern_test_results": pattern_matches,
            "metadata_analysis": sample_metadata,
            "total_chunks_loaded": len(TAFSIR_CHUNKS)
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

# --- Main ---
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
