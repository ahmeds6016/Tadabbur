#!/bin/bash

# ============================================================================
# Tafsir Simplified Frontend Deployment Script
# ============================================================================

set -e  # Exit on error

echo "🚀 Starting Tafsir Simplified Frontend Deployment..."
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="tafsir-simplified"
SERVICE_NAME="tafsir-frontend"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Step 1: Check if gcloud is authenticated
echo -e "\n${YELLOW}[1/4] Checking gcloud authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Not authenticated. Running gcloud auth login...${NC}"
    gcloud auth login
fi
echo -e "${GREEN}✓ Authenticated${NC}"

# Step 2: Set project
echo -e "\n${YELLOW}[2/4] Setting GCP project to ${PROJECT_ID}...${NC}"
gcloud config set project ${PROJECT_ID}
echo -e "${GREEN}✓ Project set${NC}"

# Step 3: Build Docker image
echo -e "\n${YELLOW}[3/4] Building Docker image from frontend/...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/frontend"
gcloud builds submit --tag ${IMAGE_NAME} .
echo -e "${GREEN}✓ Image built: ${IMAGE_NAME}${NC}"

# Step 4: Deploy to Cloud Run
echo -e "\n${YELLOW}[4/4] Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 10

echo -e "${GREEN}✓ Deployed successfully!${NC}"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')
echo -e "\n${GREEN}=================================================="
echo "🎉 Frontend Deployment Complete!"
echo "==================================================${NC}"
echo -e "Service URL: ${GREEN}${SERVICE_URL}${NC}"
echo ""
echo "Next steps:"
echo "1. Visit: ${SERVICE_URL}"
echo "2. Test query suggestions - they should be visible by default now!"
echo "3. Test annotations with surah names (e.g., 'An-Naba')"
echo "4. Verify onboarding messages rotate with Arabic greetings"
echo ""
echo "Monitor logs:"
echo "  gcloud run services logs read ${SERVICE_NAME} --region ${REGION} --limit 50"
echo ""
