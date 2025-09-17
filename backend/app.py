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
from google.cloud import secretmanager

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
    raise ValueError("CRITICAL STARTUP ERROR: Missing required env vars")

# --- App Initialization ---
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000",
                                         "https://tafsir-frontend-612616741510.us-central1.run.app"]}}, supports_credentials=True)

TAFSIR_CHUNKS = {}

# --- Placeholder Functions ---
def load_chunks_from_gcs():
    pass  # TODO: Implement loading JSON chunks from GCS

def initialize_firebase():
    pass  # TODO: Initialize Firebase app and credentials

def firebase_auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # TODO: Implement Firebase auth verification
        return f(*args, **kwargs)
    return wrapper

def build_adaptive_prompt(user_profile, payload):
    # TODO: Build system_instruction and user_prompt
    return "SYSTEM_INSTRUCTION_PLACEHOLDER", "USER_PROMPT_PLACEHOLDER"

def expand_query(query: str, token: str) -> str:
    # TODO: Implement query expansion logic
    return query

# --- Initialize Services ---
initialize_firebase()
load_chunks_from_gcs()
vertexai.init(project=PROJECT_ID, location=LOCATION)
db = firestore.client()

# --- Endpoints ---
@app.route("/get_profile", methods=["GET"])
def get_profile():
    return jsonify({"message": "GET profile placeholder"}), 200

@app.route("/set_profile", methods=["POST"])
def set_profile():
    return jsonify({"message": "SET profile placeholder"}), 200

@app.route("/tafsir", methods=["POST"])
@firebase_auth_required
def tafsir_handler():
    payload = request.get_json()
    query = payload.get("query")
    if not query:
        return jsonify({"error": "Query is missing"}), 400

    try:
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        token = credentials.token

        expanded_query = expand_query(query, token)

        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        query_embedding = model.get_embeddings([expanded_query])[0].values

        endpoint_resource_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_resource_name)

        neighbors_result = index_endpoint.find_neighbors(queries=[query_embedding], num_neighbors=5)

        context_texts = [TAFSIR_CHUNKS.get(neighbor.id, '') for neighbor in neighbors_result[0]]
        context_string = "\n\n".join(filter(None, context_texts))

        if not context_string:
            return jsonify({"error": "Could not find relevant passages in our library for your query."}), 404

        uid = getattr(request, "user", {}).get('uid', 'anonymous')
        user_doc = db.collection('users').document(uid).get()
        user_profile = user_doc.to_dict() if user_doc.exists else {}

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

        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

        body = {
            "contents": [{"role": "user", "parts": [{"text": final_prompt_for_llm}]}],
            "generation_config": {"response_mime_type": "application/json", "temperature": 0.2, "maxOutputTokens": 4096},
        }

        print("RAG: Sending final request to Gemini...")
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

# --- Run App ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
