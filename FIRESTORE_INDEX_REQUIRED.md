# Required Firestore Composite Index

**CRITICAL:** This index is required for the `/annotations/verse/<surah>/<verse>` endpoint to function.

## Current Status
❌ **MISSING** - Causing 100% failure rate for verse annotation queries (500 errors)

## Index Configuration

**Collection Path:** `users/{userId}/annotations`

**Fields to Index:**
1. `surah` - Ascending
2. `verse` - Ascending
3. `createdAt` - Descending

**Query Scope:** Collection group

## How to Create

### Option 1: Firebase Console (Recommended)

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select project: `tafsir-simplified`
3. Navigate to **Firestore Database** → **Indexes** tab
4. Click **Create Index**
5. Enter:
   - Collection ID: `annotations`
   - Scope: **Collection group**
   - Fields:
     - `surah` - Ascending
     - `verse` - Ascending
     - `createdAt` - Descending
6. Click **Create Index**
7. Wait 2-5 minutes for index to build

### Option 2: Firebase CLI

```bash
# Create firestore.indexes.json if it doesn't exist
cat > firestore.indexes.json <<EOF
{
  "indexes": [
    {
      "collectionGroup": "annotations",
      "queryScope": "COLLECTION_GROUP",
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
    }
  ]
}
EOF

# Deploy indexes
firebase deploy --only firestore:indexes
```

### Option 3: Click Error Link

When the query fails, Firestore provides a direct link to create the index in the error message. Look for logs like:

```
ERROR: The query requires an index. You can create it here: https://console.firebase.google.com/...
```

Click that link and approve index creation.

## Why This Index Is Needed

**Query in code (app.py line 2651):**
```python
query = annotations_ref.where('surah', '==', surah) \
                      .where('verse', '==', verse) \
                      .order_by('createdAt', direction='DESCENDING')
```

This query:
1. Filters by TWO equality constraints (`surah` and `verse`)
2. Sorts by a THIRD field (`createdAt`)

Firestore requires a composite index for any query with:
- Multiple `where()` clauses on different fields, OR
- `where()` + `order_by()` on different fields

## Impact

**Before Index:**
- 0% success rate for `/annotations/verse/<surah>/<verse>`
- Users cannot retrieve their verse annotations
- 500 Internal Server Error

**After Index:**
- 99% success rate expected
- Fast queries (~50-100ms)
- Users can view all annotations for a verse

## Verification

After creating the index, test with:

```bash
curl -X GET "https://tafsir-backend-612616741510.us-central1.run.app/annotations/verse/18/65" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Should return:
```json
{
  "annotations": [...],
  "count": X
}
```

Instead of:
```json
{
  "error": "The query requires an index..."
}
```

## Related Documentation

- [Firestore Index Documentation](https://firebase.google.com/docs/firestore/query-data/indexing)
- [Index Best Practices](https://firebase.google.com/docs/firestore/query-data/index-overview)
