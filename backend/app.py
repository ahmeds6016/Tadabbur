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
# *** THIS IS THE CORRECTED LINE ***
# Add your live frontend URL to the list of allowed origins
CORS(app, resources={r"/*": {
    "origins": [
        "http://localhost:3000", 
        "https://tafsir-frontend-612616741510.us-central1.run.app"
    ]
}}, supports_credentials=True)

# (The rest of the file is exactly the same)
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
load_chunks_from_gcs()
vertexai.init(project=PROJECT_ID, location=LOCATION)
db = firestore.client()

# ... (The rest of your endpoints and functions are correct and unchanged) ...
