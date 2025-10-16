#!/bin/bash

# Firestore Composite Index Creation Script
# This script creates the required composite indexes for the Tafsir app

echo "Creating Firestore composite indexes for annotations..."

# Check if we're in the right project
CURRENT_PROJECT=$(gcloud config get-value project)
echo "Current GCP Project: $CURRENT_PROJECT"

if [ "$CURRENT_PROJECT" != "tafsir-simplified-6b262" ] && [ "$CURRENT_PROJECT" != "tafsir-simplified" ]; then
    echo "WARNING: You may not be in the correct project."
    echo "Run: gcloud config set project tafsir-simplified-6b262"
fi

# Method 1: Deploy using Firebase CLI (Recommended)
echo ""
echo "Method 1: Using Firebase CLI to deploy indexes..."

# Create firestore.indexes.json if it doesn't exist
cat > firestore.indexes.json << EOF
{
  "indexes": [
    {
      "collectionGroup": "annotations",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "surah",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "verse",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "createdAt",
          "order": "DESCENDING"
        }
      ]
    },
    {
      "collectionGroup": "saved_searches",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "folder",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "savedAt",
          "order": "DESCENDING"
        }
      ]
    }
  ],
  "fieldOverrides": []
}
EOF

echo ""
echo "firestore.indexes.json file has been created successfully!"
echo ""
echo "Now run ONE of these commands to deploy the indexes:"
echo ""
echo "Option A: Deploy with Firebase CLI (if Firebase is initialized):"
echo "  firebase deploy --only firestore:indexes --project tafsir-simplified-6b262"
echo ""
echo "Option B: Initialize Firebase first, then deploy:"
echo "  firebase init firestore"
echo "  firebase deploy --only firestore:indexes --project tafsir-simplified-6b262"
echo ""
echo "Option C: Manual creation via Firebase Console:"
echo "  1. Go to https://console.firebase.google.com/project/tafsir-simplified-6b262/firestore/indexes"
echo "  2. Click 'Add Index'"
echo "  3. Collection: annotations"
echo "  4. Fields: surah (Ascending), verse (Ascending), createdAt (Descending)"
echo "  5. Query scope: Collection"
echo "  6. Click 'Create'"
echo ""
echo "Note: Index creation typically takes 5-10 minutes to complete."
echo "You can monitor progress in the Firebase Console."