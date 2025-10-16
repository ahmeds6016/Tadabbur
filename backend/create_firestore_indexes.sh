#!/bin/bash

# Firestore Composite Index Creation Script
# This script creates the required composite indexes for the Tafsir app

echo "Creating Firestore composite indexes for annotations..."

# Index for verse annotations query
# Pattern: where(surah==X).where(verse==Y).orderBy(createdAt, DESC)
gcloud firestore indexes create \
  --collection-group="annotations" \
  --field-config field-path=surah,order=ASCENDING \
  --field-config field-path=verse,order=ASCENDING \
  --field-config field-path=createdAt,order=DESCENDING \
  --project=tafsir-simplified-6b262

# Index for saved searches with folder filter
# Pattern: where(folder==X).orderBy(savedAt, DESC)
gcloud firestore indexes create \
  --collection-group="saved_searches" \
  --field-config field-path=folder,order=ASCENDING \
  --field-config field-path=savedAt,order=DESCENDING \
  --project=tafsir-simplified-6b262

echo "Index creation commands submitted. Check the Firebase console for status."
echo "Note: Index creation may take several minutes to complete."

# Alternative: Using firebase.json for index deployment
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
echo "Alternative method: Deploy indexes using Firebase CLI:"
echo "  firebase deploy --only firestore:indexes"
echo ""
echo "The firestore.indexes.json file has been created for this purpose."