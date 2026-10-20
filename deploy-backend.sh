#!/bin/bash
# Claude-owned execution. reflection-encryption-key must exist before deployment.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="tafsir-backend"
SOURCE_DIR="backend"
MEMORY="2Gi"
CPU="2"
TIMEOUT="300"
DEPLOY_ARGS=(
  --set-env-vars "FIREBASE_PROJECT=tafsir-simplified-6b262,GCP_INFRASTRUCTURE_PROJECT=tafsir-simplified,GCP_LOCATION=us-central1,GEMINI_API_LOCATION=global,GEMINI_MODEL_ID=gemini-3.8-flash,GEMINI_LITE_MODEL_ID=gemini-3.5-flash-lite,GCS_BUCKET_NAME=tafsir-simplified-sources,FIREBASE_SECRET_FULL_PATH=projects/612616741510/secrets/firebase-sa-key/versions/latest"
  --set-secrets "ADMIN_SECRET=admin-secret:latest,REFLECTION_ENCRYPTION_SECRET=reflection-encryption-key:latest"
)
source "${SCRIPT_DIR}/scripts/deploy-common.sh" "$@"
