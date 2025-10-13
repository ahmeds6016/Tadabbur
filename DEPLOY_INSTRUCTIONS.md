# Backend Deployment Instructions

## Option 1: Automated Script (Recommended)

Run the automated deployment script:

```bash
cd /workspaces/tafsir-simplified-app
./deploy-backend.sh
```

This will:
1. Authenticate with gcloud
2. Build Docker image
3. Deploy to Cloud Run
4. Test all endpoints
5. Show service URL

---

## Option 2: Manual Deployment (Step-by-Step)

### Prerequisites
- Google Cloud SDK installed
- Authenticated with gcloud
- Access to project `tafsir-simplified`

### Steps

#### 1. Authenticate and Set Project
```bash
gcloud auth login
gcloud config set project tafsir-simplified
```

#### 2. Navigate to Backend Directory
```bash
cd /workspaces/tafsir-simplified-app/backend
```

#### 3. Build Docker Image
```bash
gcloud builds submit --tag gcr.io/tafsir-simplified/tafsir-backend
```

This will:
- Read `Dockerfile`
- Build the image
- Push to Google Container Registry
- Take ~2-3 minutes

#### 4. Deploy to Cloud Run
```bash
gcloud run deploy tafsir-backend \
  --image gcr.io/tafsir-simplified/tafsir-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars FIREBASE_PROJECT=tafsir-simplified-6b262,GCP_INFRASTRUCTURE_PROJECT=tafsir-simplified,GCP_LOCATION=us-central1,GEMINI_MODEL_ID=gemini-2.0-flash,INDEX_ENDPOINT_ID=3478417184655409152,DEPLOYED_INDEX_ID=deployed_tafsir_sliding_1760263278167,VECTOR_INDEX_ID=5746296256385253376,GCS_BUCKET_NAME=tafsir-simplified-sources,FIREBASE_SECRET_FULL_PATH=projects/612616741510/secrets/firebase-admin-key/versions/latest
```

When prompted, confirm:
- Service name: `tafsir-backend`
- Region: `us-central1`
- Allow unauthenticated: `Yes`

#### 5. Get Service URL
```bash
gcloud run services describe tafsir-backend --region us-central1 --format 'value(status.url)'
```

Should output: `https://tafsir-backend-612616741510.us-central1.run.app`

---

## Option 3: Cloud Console (GUI)

### Via Google Cloud Console

1. Go to: https://console.cloud.google.com/run?project=tafsir-simplified

2. Find `tafsir-backend` service

3. Click **"EDIT & DEPLOY NEW REVISION"**

4. Under "Container image URL", click **"SELECT"**

5. Click **"Cloud Build"** tab

6. Repository: Select your repo or enter:
   ```
   /workspaces/tafsir-simplified-app/backend
   ```

7. Branch: `main`

8. Build type: `Dockerfile`

9. Click **"BUILD"**

10. Once built, click **"DEPLOY"**

11. Wait ~2-3 minutes for deployment

---

## Verification

After deployment, test the endpoints:

### Test 1: Health Check (Should return 200)
```bash
curl https://tafsir-backend-612616741510.us-central1.run.app/health
```

Expected: JSON with `status: "healthy"`, `chunks_loaded`, etc.

### Test 2: New Endpoints (Should return 401, NOT 404)
```bash
# Query History
curl -i https://tafsir-backend-612616741510.us-central1.run.app/query-history

# Saved Searches
curl -i https://tafsir-backend-612616741510.us-central1.run.app/saved-searches

# Annotations
curl -i https://tafsir-backend-612616741510.us-central1.run.app/annotations/user
```

**Expected Response:**
```
HTTP/2 401
content-type: application/json
...
{"error": "Unauthorized"}
```

**If you see 404:** Deployment failed, old code still running

**If you see 401:** ✅ Success! Endpoint exists, just needs auth token

### Test 3: End-to-End Frontend Test

1. Go to: https://tafsir-frontend-612616741510.us-central1.run.app/

2. Sign in

3. Search for "2:255"

4. Go to `/history` - should see your search

5. Click "⭐ Save this Answer"

6. Go to `/saved` - should see saved answer

7. Click "📝 Add Note" on verse

8. Add annotation and save

9. Refresh page - annotation should persist

---

## Troubleshooting

### Error: "The user does not have permission to access project"
```bash
gcloud auth login
gcloud auth application-default login
```

### Error: "Service account does not have permission"
```bash
# Grant necessary permissions to Cloud Run service account
gcloud projects add-iam-policy-binding tafsir-simplified \
  --member="serviceAccount:612616741510-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Error: Build fails
```bash
# Check Dockerfile exists
ls -la /workspaces/tafsir-simplified-app/backend/Dockerfile

# Check requirements.txt exists
ls -la /workspaces/tafsir-simplified-app/backend/requirements.txt
```

### Deployment succeeds but endpoints still 404
- Check logs: `gcloud run services logs read tafsir-backend --region us-central1 --limit 50`
- Look for startup errors
- Verify app.py has the new routes (search for `@app.route("/query-history")`)

### Deployment takes too long
- Normal build time: 2-3 minutes
- If > 5 minutes, check Cloud Build logs: https://console.cloud.google.com/cloud-build/builds

---

## Rollback (If Needed)

If deployment breaks something:

### List Previous Revisions
```bash
gcloud run revisions list --service tafsir-backend --region us-central1
```

### Rollback to Previous Revision
```bash
# Replace PREVIOUS_REVISION with revision name from list above
gcloud run services update-traffic tafsir-backend \
  --to-revisions PREVIOUS_REVISION=100 \
  --region us-central1
```

---

## Monitoring

### View Logs
```bash
# Last 50 lines
gcloud run services logs read tafsir-backend --region us-central1 --limit 50

# Live tail
gcloud run services logs tail tafsir-backend --region us-central1
```

### View Metrics
Go to: https://console.cloud.google.com/run/detail/us-central1/tafsir-backend/metrics

Monitor:
- Request count
- Request latency
- Error rate
- Container CPU/memory usage

---

## Environment Variables (Current Configuration)

```bash
FIREBASE_PROJECT=tafsir-simplified-6b262
GCP_INFRASTRUCTURE_PROJECT=tafsir-simplified
GCP_LOCATION=us-central1
GEMINI_MODEL_ID=gemini-2.0-flash
INDEX_ENDPOINT_ID=3478417184655409152
DEPLOYED_INDEX_ID=deployed_tafsir_sliding_1760263278167
VECTOR_INDEX_ID=5746296256385253376
GCS_BUCKET_NAME=tafsir-simplified-sources
FIREBASE_SECRET_FULL_PATH=projects/612616741510/secrets/firebase-admin-key/versions/latest
```

To update env vars:
```bash
gcloud run services update tafsir-backend \
  --region us-central1 \
  --set-env-vars NEW_VAR=value
```

---

## Post-Deployment Checklist

- [ ] Backend deployed successfully
- [ ] Health check returns 200
- [ ] /query-history returns 401 (not 404)
- [ ] /saved-searches returns 401 (not 404)
- [ ] /annotations/user returns 401 (not 404)
- [ ] Frontend can save query history
- [ ] Frontend can save answers
- [ ] Frontend can create annotations
- [ ] No errors in Cloud Run logs
- [ ] Response times < 5 seconds

---

## Need Help?

If stuck, check:
1. Cloud Run logs: https://console.cloud.google.com/run/detail/us-central1/tafsir-backend/logs
2. Cloud Build history: https://console.cloud.google.com/cloud-build/builds
3. Service details: https://console.cloud.google.com/run/detail/us-central1/tafsir-backend/metrics

Common issues:
- **404 errors:** Old code still deployed
- **500 errors:** Check startup logs for missing env vars
- **Timeout:** Increase `--timeout` value
- **OOM:** Increase `--memory` value
