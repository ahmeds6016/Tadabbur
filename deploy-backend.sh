#!/bin/bash

# ============================================================================
# Tafsir Simplified Backend Deployment Script
# ============================================================================

set -e  # Exit on error

echo "🚀 Starting Tafsir Simplified Backend Deployment..."
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="tafsir-simplified"
SERVICE_NAME="tafsir-backend"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Step 1: Check if gcloud is authenticated
echo -e "\n${YELLOW}[1/5] Checking gcloud authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Not authenticated. Running gcloud auth login...${NC}"
    gcloud auth login
fi
echo -e "${GREEN}✓ Authenticated${NC}"

# Step 2: Set project
echo -e "\n${YELLOW}[2/5] Setting GCP project to ${PROJECT_ID}...${NC}"
gcloud config set project ${PROJECT_ID}
echo -e "${GREEN}✓ Project set${NC}"

# Step 3: Build Docker image
echo -e "\n${YELLOW}[3/5] Building Docker image from backend/...${NC}"
cd backend
gcloud builds submit --tag ${IMAGE_NAME} .
echo -e "${GREEN}✓ Image built: ${IMAGE_NAME}${NC}"

# Step 4: Deploy to Cloud Run
echo -e "\n${YELLOW}[4/5] Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars "FIREBASE_PROJECT=tafsir-simplified-6b262" \
  --set-env-vars "GCP_INFRASTRUCTURE_PROJECT=tafsir-simplified" \
  --set-env-vars "GCP_LOCATION=us-central1" \
  --set-env-vars "GEMINI_MODEL_ID=gemini-2.0-flash" \
  --set-env-vars "INDEX_ENDPOINT_ID=3478417184655409152" \
  --set-env-vars "DEPLOYED_INDEX_ID=deployed_tafsir_sliding_1760263278167" \
  --set-env-vars "VECTOR_INDEX_ID=5746296256385253376" \
  --set-env-vars "GCS_BUCKET_NAME=tafsir-simplified-sources" \
  --set-env-vars "FIREBASE_SECRET_FULL_PATH=projects/612616741510/secrets/firebase-admin-key/versions/latest"

echo -e "${GREEN}✓ Deployed successfully!${NC}"

# Step 5: Get service URL and test
echo -e "\n${YELLOW}[5/5] Testing deployment...${NC}"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')
echo -e "Service URL: ${GREEN}${SERVICE_URL}${NC}"

echo -e "\nTesting health endpoint..."
HEALTH_RESPONSE=$(curl -s "${SERVICE_URL}/health")
echo "Health check response: ${HEALTH_RESPONSE}"

echo -e "\nTesting new endpoints (should return 401, not 404)..."
echo -n "  - /query-history: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/query-history")
if [ "$HTTP_CODE" == "401" ]; then
    echo -e "${GREEN}✓ OK (401 Unauthorized - endpoint exists)${NC}"
elif [ "$HTTP_CODE" == "404" ]; then
    echo -e "${RED}✗ FAIL (404 Not Found - endpoint missing)${NC}"
else
    echo -e "${YELLOW}? Unexpected status: ${HTTP_CODE}${NC}"
fi

echo -n "  - /saved-searches: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/saved-searches")
if [ "$HTTP_CODE" == "401" ]; then
    echo -e "${GREEN}✓ OK (401 Unauthorized - endpoint exists)${NC}"
elif [ "$HTTP_CODE" == "404" ]; then
    echo -e "${RED}✗ FAIL (404 Not Found - endpoint missing)${NC}"
else
    echo -e "${YELLOW}? Unexpected status: ${HTTP_CODE}${NC}"
fi

echo -n "  - /annotations/user: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/annotations/user")
if [ "$HTTP_CODE" == "401" ]; then
    echo -e "${GREEN}✓ OK (401 Unauthorized - endpoint exists)${NC}"
elif [ "$HTTP_CODE" == "404" ]; then
    echo -e "${RED}✗ FAIL (404 Not Found - endpoint missing)${NC}"
else
    echo -e "${YELLOW}? Unexpected status: ${HTTP_CODE}${NC}"
fi

echo -e "\n${GREEN}=================================================="
echo "🎉 Deployment Complete!"
echo "==================================================${NC}"
echo -e "Service URL: ${SERVICE_URL}"
echo ""
echo "Next steps:"
echo "1. Test frontend at: https://tafsir-frontend-612616741510.us-central1.run.app/"
echo "2. Try query history: Search something, then go to /history"
echo "3. Try saved searches: Save an answer, then go to /saved"
echo "4. Try annotations: Add a note to a verse"
echo ""
echo "Monitor logs:"
echo "  gcloud run services logs read ${SERVICE_NAME} --region ${REGION} --limit 50"
