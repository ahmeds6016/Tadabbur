import os
import json
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.auth
from google.auth.transport.requests import Request as GoogleRequest
import requests
import firebase_admin
from firebase_admin import credentials, auth, firestore
import traceback
import vertexai
from vertexai.language_models import TextEmbeddingModel
from google.cloud import aiplatform
from google.cloud import storage

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "tafsir-simplified")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-2.0-flash")
FIREBASE_SECRET_FULL_PATH = os.environ.get("FIREBASE_SECRET_FULL_PATH")
INDEX_ENDPOINT_ID = os.environ.get("INDEX_ENDPOINT_ID")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")
GCS_CHUNKS_PATH = 'jalalayn_chunks.json'

# --- Startup Validation ---
if not FIREBASE_SECRET_FULL_PATH or not INDEX_ENDPOINT_ID or not GCS_BUCKET_NAME:
    raise ValueError("CRITICAL STARTUP ERROR: Missing required env vars (FIREBASE_SECRET_FULL_PATH, INDEX_ENDPOINT_ID, GCS_BUCKET_NAME)")

# --- App Initialization ---
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# (Global variable and initialization functions remain the same)
TAFSIR_CHUNKS = {}
# ... [initialize_firebase, load_chunks_from_gcs, etc.] ...

# --- NEW: Restored Complex Adaptive Prompt Engineering ---
def build_adaptive_prompt(user_profile, payload):
    level = user_profile.get('level', 'beginner')
    focus = user_profile.get('focus', 'practical') # Default to practical
    verbosity = user_profile.get('verbosity', 'medium') # Default to medium
    
    query = payload.get("query", "")
    approach = payload.get("approach", "tafsir")

    # Base instruction
    system_instruction = f"""
    You are 'Tafsir Simplified', a specialized AI assistant for Qur'anic studies.
    You MUST ALWAYS return a single, valid JSON object that strictly follows the required schema.
    Your RAG context is from Tafsir al-Jalalayn.
    USER PROFILE: Knowledge Level='{level}', Focus='{focus}', Verbosity='{verbosity}'.
    USER APPROACH: '{approach}'.
    """

    # Add level-specific instructions
    if level == 'beginner':
        system_instruction += "\n--- BEGINNER INSTRUCTIONS --- Explain concepts simply. Focus on core lessons. Define Arabic terms."
    elif level == 'intermediate':
        system_instruction += "\n--- INTERMEDIATE INSTRUCTIONS --- Provide more detailed explanations, citing sources clearly. Introduce some scholarly terms."
    elif level == 'advanced':
        system_instruction += "\n--- ADVANCED INSTRUCTIONS --- Include nuanced linguistic analysis, compare opinions where possible, and use Arabic terminology."

    # Add focus-specific instructions
    if focus == 'linguistic':
        system_instruction += "\n--- FOCUS: LINGUISTIC --- Emphasize balagha (rhetoric), i'rab (grammar), and the etymology of key terms."
    elif focus == 'comparative':
         system_instruction += "\n--- FOCUS: COMPARATIVE --- Where the context allows, briefly mention how other mufassireen might approach this topic."
    # 'practical' and 'thematic' focuses are handled by the main prompt

    # Add verbosity-specific instructions
    if verbosity == 'short':
        system_instruction += "\n--- VERBOSITY: SHORT --- Keep all explanations concise and to the point, aiming for a summary."
    elif verbosity == 'detailed':
        system_instruction += "\n--- VERBOSITY: DETAILED --- Provide comprehensive and in-depth explanations for all points."
    
    final_user_prompt = f"USER QUERY: '{query}'. Generate the JSON response now."
    return system_instruction, final_user_prompt


# --- API Routes ---
@app.route("/set_profile", methods=["POST"])
@firebase_auth_required
def set_profile():
    uid = request.user['uid']
    data = request.get_json()
    # Now accepts the full profile
    profile_data = {
        'level': data.get('level'),
        'focus': data.get('focus'),
        'verbosity': data.get('verbosity'),
    }
    # Basic validation
    if not all(profile_data.values()):
        return jsonify({"error": "Missing profile data"}), 400
    try:
        db.collection('users').document(uid).set(profile_data, merge=True)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": "Could not update profile", "details": str(e)}), 500

@app.route("/tafsir", methods=["POST"])
@firebase_auth_required
def tafsir_handler():
    payload = request.get_json()
    query = payload.get("query")
    if not query: return jsonify({"error": "Query is missing"}), 400

    try:
        # Get user profile to pass to the prompt builder
        uid = request.user['uid']
        user_doc = db.collection('users').document(uid).get()
        user_profile = user_doc.to_dict() if user_doc.exists else {}

        # The RAG part remains the same (search and retrieve)
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        query_embedding = model.get_embeddings([query])[0].values
        
        endpoint_resource_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_resource_name)
        
        neighbors_result = index_endpoint.find_neighbors(queries=[query_embedding], num_neighbors=5)
        
        context_texts = [TAFSIR_CHUNKS.get(neighbor.id, '') for neighbor in neighbors_result[0]]
        context_string = "\n\n".join(filter(None, context_texts))
        
        if not context_string:
            return jsonify({"error": "Could not find relevant passages in our library for your query."}), 404

        # --- USE THE RESTORED ADAPTIVE PROMPT BUILDER ---
        system_instruction, user_prompt = build_adaptive_prompt(user_profile, payload)

        final_prompt_for_llm = f"""
        {system_instruction}
        
        Based ONLY on the following context, fulfill the user's request.
        
        CONTEXT:
        ---
        {context_string}
        ---

        {user_prompt}
        """
        
        # (The final Gemini call logic remains the same)
        # ... [Full Gemini call, parsing, and error handling logic] ...
        
    except Exception as e:
        # ... [Error handling] ...

# (The rest of the file, including /get_profile, initialize_firebase, etc. remains the same)
