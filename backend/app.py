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

# --- NEW: Startup Validation (Your excellent suggestion) ---
if not FIREBASE_SECRET_FULL_PATH or not INDEX_ENDPOINT_ID or not GCS_BUCKET_NAME:
    raise ValueError("CRITICAL STARTUP ERROR: Missing one or more required environment variables (FIREBASE_SECRET_FULL_PATH, INDEX_ENDPOINT_ID, GCS_BUCKET_NAME)")

# --- App Initialization ---
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# (The rest of the file is the same as the last version, but with the tafsir_handler completed)
# ...

@app.route("/tafsir", methods=["POST"])
@firebase_auth_required
def tafsir_handler():
    """Handles tafsir requests using the RAG pipeline."""
    payload = request.get_json()
    query = payload.get("query")
    if not query:
        return jsonify({"error": "Query is missing"}), 400

    try:
        # --- RAG Step 1 & 2: Get Query Embedding and Find Neighbors ---
        print("RAG: Generating embedding for user query...")
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        query_embedding = model.get_embeddings([query])[0].values

        print("RAG: Searching Vector Search index...")
        endpoint_resource_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_resource_name)
        
        neighbors_result = index_endpoint.find_neighbors(
            queries=[query_embedding],
            num_neighbors=5
        )

        # --- RAG Step 3: Retrieve Full Text for Neighbors ---
        print("RAG: Retrieving text for relevant chunks...")
        context_texts = []
        if neighbors_result and neighbors_result[0]:
            for neighbor in neighbors_result[0]:
                if neighbor.id in TAFSIR_CHUNKS:
                    context_texts.append(TAFSIR_CHUNKS[neighbor.id])
        
        if not context_texts:
            return jsonify({"error": "Could not find relevant passages in our library for your query."}), 404

        context_string = "\n\n".join(context_texts)

        # --- RAG Step 4: Augment Prompt for the Final Gemini Call ---
        print("RAG: Augmenting prompt for final generation...")
        final_prompt = f"""
        Based ONLY on the following context from Tafsir al-Jalalayn, provide a comprehensive, structured answer for the user's query.
        The answer MUST be in a valid JSON format. If the context does not contain the answer, return a JSON object with an "error" key.
        
        CONTEXT:
        ---
        {context_string}
        ---

        USER'S QUERY:
        {query}

        REQUIRED JSON OUTPUT FORMAT:
        {{
          "verses": [{{"surah": "string", "verse_number": "string", "text_saheeh_international": "string"}}],
          "tafsir_explanations": [{{"source": "Tafsir al-Jalalayn", "explanation": "string"}}],
          "lessons_practical_applications": [{{"point": "string"}}]
        }}
        """
        
        # --- NEW: Step 5 - The Completed Gemini Call ---
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        token = credentials.token

        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

        body = {
            "contents": [{"role": "user", "parts": [{"text": final_prompt}]}],
            "generation_config": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 4096,
            },
        }

        print("RAG: Sending final request to Gemini...")
        response = requests.post(
            VERTEX_ENDPOINT,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=120
        )
        response.raise_for_status()
        
        # (The robust parsing logic remains the same)
        raw_response = response.json()
        if ( "candidates" in raw_response and len(raw_response["candidates"]) > 0 ):
             clean_text = raw_response["candidates"][0]["content"]["parts"][0]["text"]
             return jsonify(json.loads(clean_text)), 200
        else:
             print(f"ERROR: Unexpected AI response structure: {raw_response}")
             return jsonify({"error": "Unexpected response structure from AI service."}), 500

    except Exception as e:
        # (The detailed error handling also remains)
        print(f"CRITICAL ERROR in /tafsir RAG pipeline: {type(e).__name__} - {e}")
        traceback.print_exc()
        return jsonify({"error": "An internal error occurred in the RAG pipeline."}), 500

# (The rest of the file, including /get_profile, /set_profile, etc., remains unchanged)

# ... [Full code for initialize_firebase, load_chunks_from_gcs, decorators, etc. as in the last full version] ...
