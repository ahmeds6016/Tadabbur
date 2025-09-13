import os
import json
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, auth, firestore
from google.cloud import secretmanager
import google.auth
from google.auth.transport.requests import Request as GoogleRequest
import requests

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-1.5-flash-001")
FIREBASE_SECRET_SHORT_NAME = os.environ.get("FIREBASE_SECRET_NAME")

# --- Flask App ---
app = Flask(__name__)
# Allow requests from all origins (or restrict to your frontend URL)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- Firebase Initialization ---
def initialize_firebase():
    try:
        client = secretmanager.SecretManagerServiceClient()
        full_secret_name = f"projects/{PROJECT_ID}/secrets/{FIREBASE_SECRET_SHORT_NAME}/versions/latest"
        response = client.access_secret_version(name=full_secret_name)
        secret_payload = response.payload.data.decode("UTF-8")
        cred_json = json.loads(secret_payload)
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred)
        print("Firebase App Initialized successfully.")
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        raise

initialize_firebase()
db = firestore.client()

# --- Firebase Auth Decorator ---
def firebase_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
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

# --- API Endpoints ---
@app.route("/set_profile", methods=["POST"])
@firebase_auth_required
def set_profile():
    uid = request.user['uid']
    data = request.get_json()
    level = data.get('level')
    if level not in ['beginner', 'intermediate', 'advanced']:
        return jsonify({"error": "Invalid level specified"}), 400
    try:
        user_ref = db.collection('users').document(uid)
        user_ref.set({'level': level}, merge=True)
        return jsonify({"status": "success", "uid": uid, "level": level}), 200
    except Exception as e:
        return jsonify({"error": "Could not update profile", "details": str(e)}), 500

@app.route("/tafsir", methods=["POST"])
@firebase_auth_required
def tafsir_handler():
    uid = request.user['uid']
    payload = request.get_json()
    try:
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()
        user_profile = user_doc.to_dict() if user_doc.exists else {}

        # Build prompt for Gemini AI
        user_level = user_profile.get('level', 'beginner')
        query = payload.get("query", "")
        approach = payload.get("approach", "tafsir")
        system_instruction = f"User Level: {user_level}, Approach: {approach}, Query: {query}"

        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        token = credentials.token

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"
        body = {
            "system_instruction": {"parts": {"text": system_instruction}},
            "contents": {"role": "user", "parts": {"text": query}},
            "generation_config": {"response_mime_type": "application/json", "temperature": 0.2, "maxOutputTokens": 2048},
        }

        response = requests.post(VERTEX_ENDPOINT, headers=headers, json=body, timeout=90)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return jsonify({"error": "An error occurred", "details": str(e)}), 500

# --- Run App ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
