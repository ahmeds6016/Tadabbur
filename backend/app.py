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
from google.cloud import secretmanager

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-1.5-flash-001")
# This variable will now hold the FULL path to the secret
FIREBASE_SECRET_FULL_PATH = os.environ.get("FIREBASE_SECRET_FULL_PATH") 

# --- App Initialization ---
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# --- Firebase Initialization (Simplified) ---
def initialize_firebase():
    """Initializes Firebase Admin SDK from a full secret path."""
    try:
        if not FIREBASE_SECRET_FULL_PATH:
            raise ValueError("FIREBASE_SECRET_FULL_PATH environment variable not set.")

        print(f"Attempting to access secret at: {FIREBASE_SECRET_FULL_PATH}")
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(name=FIREBASE_SECRET_FULL_PATH)

        secret_payload = response.payload.data.decode("UTF-8")
        cred_json = json.loads(secret_payload)
        
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred)
        print("Firebase App Initialized successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR initializing Firebase: {e}")
        raise

initialize_firebase()
db = firestore.client()

# --- Authentication Decorator ---
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

# --- Prompt Engineering ---
def build_adaptive_prompt(user_profile, payload):
    user_level = user_profile.get('level', 'beginner')
    query = payload.get("query", "")
    approach = payload.get("approach", "tafsir")

    system_instruction = """
    You are 'Tafsir Simplified', a specialized AI assistant for Qur'anic studies.
    You MUST ALWAYS return a single, valid JSON object and nothing else.
    Your knowledge sources are: Saheeh International, Ibn Kathir, Al-Qurtubi, Al-Jalalayn, and Al-Tabari.
    The JSON output must strictly follow the required schema.
    """

    if user_level == 'beginner':
        system_instruction += """
        --- BEGINNER INSTRUCTIONS ---
        Explain all concepts in simple, clear English. Avoid complex theological jargon.
        Focus on the primary lesson and practical application for daily life.
        Define any Arabic terms used.
        """
    elif user_level == 'advanced':
        system_instruction += """
        --- ADVANCED INSTRUCTIONS ---
        Include nuanced linguistic analysis (balagha) where relevant.
        Provide comparisons between the opinions of different mufassiren.
        Reference original Arabic terminology extensively.
        """
    user_prompt = f"User Level: '{user_level}'. Approach: '{approach}'. Query: '{query}'. Generate the JSON response now."
    return system_instruction, user_prompt

# --- API Routes ---
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
        system_prompt, user_prompt = build_adaptive_prompt(user_profile, payload)
        
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = GoogleRequest()
        credentials.refresh(auth_req)
        token = credentials.token

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        VERTEX_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{GEMINI_MODEL_ID}:generateContent"

        body = {
            "system_instruction": {"parts": {"text": system_prompt}},
            "contents": {"role": "user", "parts": {"text": user_prompt}},
            "generation_config": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            },
        }
        response = requests.post(VERTEX_ENDPOINT, headers=headers, json=body, timeout=90)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return jsonify({"error": "An error occurred", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


