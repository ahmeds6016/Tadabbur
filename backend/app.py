import os
import json
import traceback
from functools import wraps

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

# Global variable for in-memory cache
TAFSIR_CHUNKS = {}

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
                
                # Convert list to dictionary with source-specific IDs
                source_chunks = 0
                for i, chunk in enumerate(chunks_list):
                    # Create unique IDs that include source information
                    if source_name == "al-Jalalayn":
                        datapoint_id = f"jalalayn_page_{chunk.get('page_number', i)}_{i}"
                    elif source_name == "al-Qurtubi":
                        datapoint_id = f"qurtubi_page_{chunk.get('page_number', i)}_{i}"
                    elif source_name == "Ibn Kathir":
                        datapoint_id = f"ibn_kathir_page_{chunk.get('page_number', i)}_{chunk.get('chunk_index_on_page', i)}"
                    
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

# --- Prompt Builder ---
def build_adaptive_prompt(user_profile, payload):
    """Build adaptive prompt based on user profile and preferences"""
    level = user_profile.get("level", "beginner")
    focus = user_profile.get("focus", "practical")
    verbosity = user_profile.get("verbosity", "medium")
    query = payload.get("query", "")
    approach = payload.get("approach", "tafsir")

    system_instruction = f"""
You are 'Tafsir Simplified', a specialized AI assistant for Qur'anic studies.
You have access to three major classical tafsir sources:
- Tafsir al-Jalalayn (concise, essential interpretations)
- Tafsir al-Qurtubi (juridical focus, legal rulings)
- Tafsir Ibn Kathir (detailed commentary with hadith references)

You MUST base your answer on the provided CONTEXT from these classical sources.
You MUST ALWAYS return a single, valid JSON object and nothing else.

USER PROFILE: Knowledge Level='{level}', Focus='{focus}', Verbosity='{verbosity}'.
USER APPROACH: '{approach}'.

JSON Schema:
{{
  "verses": [{{"surah": "string", "verse_number": "string", "text_saheeh_international": "string"}}],
  "tafsir_explanations": [{{"source": "string", "explanation": "string"}}],
  "hadith_refs": [{{"reference": "string", "grade": "string", "text_short": "string"}}],
  "lessons_practical_applications": [{{"point": "string"}}]
}}

When citing explanations, indicate the source (al-Jalalayn, al-Qurtubi, or Ibn Kathir) in the "source" field.
"""

    # Level-specific instructions
    if level == "casual":
        system_instruction += "Keep explanations short, simple, and practical for everyday Muslims.\n"
    elif level == "beginner":
        system_instruction += "Explain concepts in simple English with clear definitions of Arabic terms. Avoid complex theological discussions.\n"
    elif level == "intermediate":
        system_instruction += "Include brief linguistic notes and moderate theological depth. Explain key Arabic terms and their significance.\n"
    elif level == "advanced":
        system_instruction += "Provide full linguistic and theological nuance with detailed scholarly analysis. Include Arabic terminology and comparative perspectives between the three sources.\n"

    # Focus-specific instructions
    if focus == "practical":
        system_instruction += "Emphasize lessons and practical applications for daily Muslim life, especially from al-Jalalayn.\n"
    elif focus == "linguistic":
        system_instruction += "Emphasize Arabic grammar, word roots, rhetorical devices from all sources, especially detailed linguistic analysis.\n"
    elif focus == "comparative":
        system_instruction += "Compare different interpretations between al-Jalalayn, al-Qurtubi, and Ibn Kathir. Highlight areas of consensus or difference.\n"
    elif focus == "thematic":
        system_instruction += "Connect verses to broader Quranic themes and cross-reference related passages across all three sources.\n"

    # Verbosity-specific instructions
    if verbosity == "short":
        system_instruction += "Keep responses concise and to the point.\n"
    elif verbosity == "medium":
        system_instruction += "Provide balanced detail without overwhelming information.\n"
    elif verbosity == "detailed":
        system_instruction += "Provide comprehensive analysis with examples, context, and thorough explanations from multiple sources.\n"

    user_prompt = f"USER QUERY: '{query}'. Generate the JSON response now based on the provided context from the classical tafsir sources."
    return system_instruction, user_prompt

# --- API Routes ---
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
def tafsir_handler():
    """Main tafsir endpoint with RAG pipeline"""
    payload = request.get_json()
    query = payload.get("query")
    
    if not query:
        return jsonify({"error": "Query is missing"}), 400

    try:
        # Get authentication token for Vertex AI
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        token = credentials.token

        # RAG Step 1: Expand the query for better semantic matching
        print(f"RAG: Processing query: '{query}'")
        expanded_query = expand_query(query, token)

        # RAG Step 2: Generate embedding for the expanded query
        # FIXED: Specify output_dimensionality=1024 to match your vector database
        print("RAG: Generating query embedding...")
        embedding_model = TextEmbeddingModel.from_pretrained("gemini-embedding-001")
        query_embedding = embedding_model.get_embeddings([expanded_query], output_dimensionality=1024)[0].values

        # RAG Step 3: Search the vector index
        print("RAG: Searching vector index...")
        endpoint_resource_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_resource_name)
        
        neighbors_result = index_endpoint.find_neighbors(
            deployed_index_id=DEPLOYED_INDEX_ID,
            queries=[query_embedding], 
            num_neighbors=5
        )

        # RAG Step 4: Retrieve relevant context from chunks
        print("RAG: Retrieving context from chunks...")
        context_texts = []
        for neighbor in neighbors_result[0]:
            chunk_text = TAFSIR_CHUNKS.get(neighbor.id, '')
            if chunk_text:
                context_texts.append(chunk_text)
        
        context_string = "\n\n---\n\n".join(context_texts)
        
        if not context_string:
            return jsonify({"error": "Could not find relevant passages in the classical tafsir sources for your query."}), 404

        # RAG Step 5: Get user profile and build adaptive prompt
        uid = request.user["uid"]
        user_doc = db.collection("users").document(uid).get()
        user_profile = user_doc.to_dict() if user_doc.exists else {}

        system_instruction, user_prompt = build_adaptive_prompt(user_profile, payload)
        
        # RAG Step 6: Create final prompt with retrieved context
        final_prompt = f"""
{system_instruction}

Based on the following context from classical tafsir sources (al-Jalalayn, al-Qurtubi, and Ibn Kathir), respond to the user's request:

CONTEXT:
{context_string}

{user_prompt}
"""

        # RAG Step 7: Generate final response using Gemini
        print("RAG: Generating final response...")
        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"
        
        body = {
            "contents": [{"role": "user", "parts": [{"text": final_prompt}]}],
            "generation_config": {
                "response_mime_type": "application/json", 
                "temperature": 0.2, 
                "maxOutputTokens": 4096
            },
        }

        response = requests.post(
            VERTEX_ENDPOINT,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=120
        )
        response.raise_for_status()

        # Parse and return response
        raw_response = response.json()
        if "candidates" in raw_response and raw_response["candidates"]:
            try:
                generated_text = raw_response["candidates"][0]["content"]["parts"][0]["text"]
                final_json = json.loads(generated_text)
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
        return jsonify({"error": "An internal error occurred in the RAG pipeline"}), 500

# --- Health Check ---
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "firebase_initialized": len(firebase_admin._apps) > 0,
        "chunks_loaded": len(TAFSIR_CHUNKS) > 0,
        "total_chunks": len(TAFSIR_CHUNKS),
        "sources": "al-Jalalayn, al-Qurtubi, Ibn Kathir",
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "index_endpoint_id": INDEX_ENDPOINT_ID,
        "deployed_index_id": DEPLOYED_INDEX_ID
    }
    return jsonify(status), 200

# --- Cloud Run Entry Point ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
