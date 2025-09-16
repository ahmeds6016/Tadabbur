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

TAFSIR_CHUNKS = {}

def load_chunks_from_gcs():
    global TAFSIR_CHUNKS
    try:
        print(f"INFO: Loading chunks from gs://{GCS_BUCKET_NAME}/{GCS_CHUNKS_PATH}")
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(GCS_CHUNKS_PATH)
        contents = blob.download_as_string()
        chunks_list = json.loads(contents)
        for i, chunk in enumerate(chunks_list):
            datapoint_id = f"jalalayn_page_{chunk['page_number']}_{i}"
            TAFSIR_CHUNKS[datapoint_id] = chunk['text']
        print(f"INFO: Successfully loaded {len(TAFSIR_CHUNKS)} chunks into memory.")
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR loading chunks: {type(e).__name__} - {e}")
        raise

def initialize_firebase():
    try:
        client = storage.Client()
        response = client.access_secret_version(name=FIREBASE_SECRET_FULL_PATH)
        secret_payload = response.payload.data.decode("UTF-8")
        cred_json = json.loads(secret_payload)
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred)
        print("INFO: Firebase App Initialized successfully.")
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR in initialize_firebase: {type(e).__name__} - {e}")
        raise

initialize_firebase()
load_chunks_from_gcs()
vertexai.init(project=PROJECT_ID, location=LOCATION)
db = firestore.client()

def firebase_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        id_token = request.headers.get('Authorization', '').split('Bearer ')[-1]
        if not id_token: return jsonify({"error": "Authorization token is missing"}), 401
        try:
            request.user = auth.verify_id_token(id_token)
        except Exception as e:
            return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401
        return f(*args, **kwargs)
    return decorated_function

def build_adaptive_prompt(user_profile, payload):
    level = user_profile.get('level', 'beginner')
    focus = user_profile.get('focus', 'practical')
    verbosity = user_profile.get('verbosity', 'medium')
    query = payload.get("query", "")
    approach = payload.get("approach", "tafsir")

    system_instruction = f"You are 'Tafsir Simplified', a specialized AI assistant. You MUST ALWAYS return a single, valid JSON object. Your RAG context is from Tafsir al-Jalalayn. USER PROFILE: Knowledge Level='{level}', Focus='{focus}', Verbosity='{verbosity}'. USER APPROACH: '{approach}'."
    if level == 'beginner': system_instruction += "\n--- BEGINNER INSTRUCTIONS --- Explain simply. Focus on core lessons. Define Arabic terms."
    elif level == 'intermediate': system_instruction += "\n--- INTERMEDIATE INSTRUCTIONS --- Provide more detail, citing sources. Introduce scholarly terms."
    elif level == 'advanced': system_instruction += "\n--- ADVANCED INSTRUCTIONS --- Include linguistic analysis, compare opinions, use Arabic terminology."
    if focus == 'linguistic': system_instruction += "\n--- FOCUS: LINGUISTIC --- Emphasize balagha, i'rab, and etymology."
    elif focus == 'comparative': system_instruction += "\n--- FOCUS: COMPARATIVE --- Where context allows, mention other mufassireen."
    if verbosity == 'short': system_instruction += "\n--- VERBOSITY: SHORT --- Keep explanations concise."
    elif verbosity == 'detailed': system_instruction += "\n--- VERBOSITY: DETAILED --- Provide comprehensive explanations."
    
    final_user_prompt = f"USER QUERY: '{query}'. Generate the JSON response now."
    return system_instruction, final_user_prompt

@app.route("/get_profile", methods=["GET"])
@firebase_auth_required
def get_profile():
    uid = request.user['uid']
    try:
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists: return jsonify(user_doc.to_dict()), 200
        else: return jsonify({"error": "Profile not found"}), 404
    except Exception as e:
        print(f"ERROR in /get_profile: {e}")
        return jsonify({"error": "Could not retrieve profile"}), 500

@app.route("/set_profile", methods=["POST"])
@firebase_auth_required
def set_profile():
    uid = request.user['uid']
    data = request.get_json()
    profile_data = {'level': data.get('level'), 'focus': data.get('focus'), 'verbosity': data.get('verbosity')}
    if not all(profile_data.values()): return jsonify({"error": "Missing profile data"}), 400
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
        uid = request.user['uid']
        user_doc = db.collection('users').document(uid).get()
        user_profile = user_doc.to_dict() if user_doc.exists else {}

        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        query_embedding = model.get_embeddings([query])[0].values
        
        endpoint_resource_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_resource_name)
        
        neighbors_result = index_endpoint.find_neighbors(queries=[query_embedding], num_neighbors=5)
        
        context_texts = [TAFSIR_CHUNKS.get(neighbor.id, '') for neighbor in neighbors_result[0]]
        context_string = "\n\n".join(filter(None, context_texts))
        
        if not context_string: return jsonify({"error": "Could not find relevant passages."}), 404

        system_instruction, user_prompt = build_adaptive_prompt(user_profile, payload)
        final_prompt_for_llm = f"{system_instruction}\n\nBased ONLY on the following context, fulfill the user's request.\n\nCONTEXT:\n---\n{context_string}\n---\n\n{user_prompt}"
        
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        token = credentials.token
        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"
        
        body = {
            "contents": [{"role": "user", "parts": [{"text": final_prompt_for_llm}]}],
            "generation_config": {"response_mime_type": "application/json", "temperature": 0.2, "maxOutputTokens": 4096},
        }

        response = requests.post(VERTEX_ENDPOINT, headers={"Authorization": f"Bearer {token}"}, json=body, timeout=120)
        response.raise_for_status()
        
        raw_response = response.json()
        if "candidates" in raw_response and len(raw_response["candidates"]) > 0:
             clean_text = raw_response["candidates"][0]["content"]["parts"][0]["text"]
             return jsonify(json.loads(clean_text)), 200
        else:
             print(f"ERROR: Unexpected AI response structure: {raw_response}")
             return jsonify({"error": "Unexpected response structure from AI service."}), 500

    except Exception as e:
        print(f"CRITICAL ERROR in /tafsir RAG pipeline: {type(e).__name__} - {e}")
        traceback.print_exc()
        return jsonify({"error": "An internal error occurred in the RAG pipeline."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
