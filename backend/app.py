import os
import json
import traceback
import requests
from functools import wraps
from flask import Flask, request, jsonify

# Optional Firebase imports
import firebase_admin
from firebase_admin import credentials, auth, firestore
from google.cloud import secretmanager

app = Flask(__name__)

# --- Firebase Initialization ---
FIREBASE_SECRET_FULL_PATH = os.environ.get("FIREBASE_SECRET_FULL_PATH")

def initialize_firebase():
    """Initializes Firebase Admin SDK from a full secret path."""
    if not FIREBASE_SECRET_FULL_PATH:
        print("INFO: No Firebase secret provided; skipping Firebase initialization.")
        return
    try:
        client = secretmanager.SecretManagerServiceClient()
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
db = firestore.client() if firebase_admin._apps else None

# --- Authentication Decorator ---
def firebase_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not firebase_admin._apps:
            return jsonify({"error": "Firebase not initialized"}), 500

        id_token = request.headers.get('Authorization', '').split('Bearer ')[-1]
        if not id_token:
            return jsonify({"error": "Authorization token is missing"}), 401
        try:
            decoded_token = auth.verify_id_token(id_token)
            request.user = decoded_token
        except Exception as e:
            return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401
        return f(*args, **kwargs)
    return decorated_function

# --- Example RAG/Gemini Endpoint ---
@app.route("/tafsir", methods=["POST"])
# Uncomment if you want Firebase auth
# @firebase_auth_required
def tafsir():
    try:
        data = request.get_json()
        user_prompt = data.get("prompt", "")
        if not user_prompt:
            return jsonify({"error": "Prompt missing"}), 400

        PROJECT_ID = os.environ.get("PROJECT_ID")
        LOCATION = os.environ.get("LOCATION", "us-central1")
        GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID")
        token = os.environ.get("GCP_ACCESS_TOKEN")  # or use google.auth.default()

        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

        body = {
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generation_config": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 4096
            },
        }

        print("RAG: Sending request to Gemini...")
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
        return jsonify({"error": "Internal error in RAG pipeline"}), 500

# --- Optional Local Dev EntryPoint ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
