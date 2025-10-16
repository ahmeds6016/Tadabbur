# Structural Fixes Required - Line-by-Line Analysis

**Date:** 2025-10-16
**Status:** CRITICAL - Affects reliability of all semantic/historical queries

---

## ROOT CAUSE SUMMARY

The app has **3 critical structural flaws** in the RAG pipeline that cause unreliable results:

1. **No semantic relevance filtering** - Retrieves chunks regardless of distance
2. **Wrong source prioritization** - Prioritizes al-Qurtubi (limited coverage) for historical queries
3. **No fallback mechanisms** - When semantic search fails, there's no keyword fallback

**Result:** Queries like "Year of Grief" return empty results even though content may exist in Ibn Kathir.

---

## CRITICAL FIX #1: Add Distance Threshold Filtering

### Current Code (Lines 1644, 1677)
```python
retrieved_chunks = retrieve_chunks_from_neighbors(neighbors_result[0])
# ...
sorted_chunks = sorted(chunks, key=lambda x: x['distance'])
# NO THRESHOLD CHECK - ALL chunks go to AI
```

### Problem
- Returns top-N chunks **regardless of semantic relevance**
- Chunk with distance 0.9 (completely irrelevant) treated same as distance 0.2 (highly relevant)
- AI receives garbage → says "material does not contain"

### Fix Required

**File:** `backend/app.py`
**Function:** `retrieve_chunks_from_neighbors` (Lines 1353-1386)
**Add parameter:** `distance_threshold=0.6`

```python
def retrieve_chunks_from_neighbors(neighbors, distance_threshold=0.6):
    """
    Retrieve chunks from vector search neighbors with relevance filtering

    Args:
        neighbors: List of neighbor results from vector index
        distance_threshold: Max distance to consider (0.0-1.0, lower = more similar)
                          Default 0.6 = moderately relevant
    """
    retrieved = []
    filtered_count = 0

    for neighbor in neighbors:
        # CRITICAL: Filter by distance BEFORE adding to results
        if neighbor.distance > distance_threshold:
            filtered_count += 1
            continue  # Skip irrelevant chunks

        neighbor_id = str(neighbor.id)

        # Handle sliding window segment IDs (existing logic)
        base_id = neighbor_id
        if '_' in neighbor_id:
            parts = neighbor_id.rsplit('_', 1)
            if len(parts) == 2 and parts[1].isdigit():
                base_id = parts[0]

        chunk_text = TAFSIR_CHUNKS.get(base_id, '')
        source = CHUNK_SOURCE_MAP.get(base_id, 'Unknown')

        if chunk_text:
            retrieved.append({
                'id': neighbor_id,
                'text': chunk_text,
                'source': source,
                'distance': neighbor.distance,  # Keep for debugging
                'verse_metadata': VERSE_METADATA.get(base_id, {})
            })
        else:
            print(f"WARNING: Chunk not found for ID: {neighbor_id} (base: {base_id})")

    # Log filtering stats
    total = len(neighbors)
    kept = len(retrieved)
    print(f"   Vector search: {total} neighbors → {kept} relevant (filtered {filtered_count}, threshold={distance_threshold})")

    if kept == 0 and total > 0:
        closest_dist = min(n.distance for n in neighbors)
        print(f"   ⚠️  No chunks below threshold! Closest match: distance={closest_dist:.3f}")
        print(f"   💡 Consider: keyword fallback or lower threshold")

    return retrieved
```

**Impact:** Prevents irrelevant chunks from reaching AI, reduces false negatives

---

## CRITICAL FIX #2: Fix Source Weighting for Historical Queries

### Current Code (Lines 1663-1665)
```python
if approach == 'historical':
    # Historical: prioritize al-Qurtubi (known for historical context)
    weights = {'Ibn Kathir': 0.4, 'al-Qurtubi': 0.6}  # WRONG!
```

### Problem
- Al-Qurtubi only covers **Surahs 1-4** (3.5% of Quran)
- Most historical events (battles, Year of Grief, etc.) are in **later Meccan/Medinan surahs**
- Year of Grief = Year 10 of Prophethood (Surah 9-10+ period)
- **Al-Qurtubi has ZERO content about this**

### Fix Required

**File:** `backend/app.py`
**Lines:** 1663-1669

```python
# Adjust weights based on approach
if approach == 'historical':
    # FIXED: Ibn Kathir has complete coverage (all 114 surahs)
    # Al-Qurtubi only covers Surahs 1-4 (most historical events are in later surahs)
    # Prioritize Ibn Kathir for historical queries
    weights = {'Ibn Kathir': 0.75, 'al-Qurtubi': 0.25}
elif approach == 'thematic':
    # Thematic: balance both sources equally
    weights = {'Ibn Kathir': 0.5, 'al-Qurtubi': 0.5}
elif approach == 'tafsir':
    # Classical tafsir: slight preference for Ibn Kathir (complete coverage)
    weights = {'Ibn Kathir': 0.6, 'al-Qurtubi': 0.4}
# Default: equal weights
```

**Alternative (Better):** Dynamic weighting based on verse coverage:

```python
def get_dynamic_weights(approach, query, verse_ref=None):
    """
    Calculate source weights dynamically based on coverage
    """
    # Check if query is likely in al-Qurtubi's range (Surahs 1-4)
    if verse_ref:
        surah, _ = verse_ref
        if surah > 4:
            # Outside al-Qurtubi coverage
            return {'Ibn Kathir': 1.0, 'al-Qurtubi': 0.0}

    # For semantic queries, check if keywords suggest early or late surahs
    if approach == 'historical':
        # Most historical events are in Medinan period (later surahs)
        early_meccan_keywords = ['creation', 'adam', 'noah', 'abraham', 'fatiha']
        if any(kw in query.lower() for kw in early_meccan_keywords):
            # Might be in Surahs 1-4
            return {'Ibn Kathir': 0.6, 'al-Qurtubi': 0.4}
        else:
            # Likely later surahs
            return {'Ibn Kathir': 0.8, 'al-Qurtubi': 0.2}

    elif approach == 'thematic':
        return {'Ibn Kathir': 0.5, 'al-Qurtubi': 0.5}

    else:  # tafsir
        return {'Ibn Kathir': 0.6, 'al-Qurtubi': 0.4}
```

**Impact:** Routes historical queries to the right source (Ibn Kathir)

---

## CRITICAL FIX #3: Fix Multi-Verse Metadata Storage

### Current Code (Lines 1010-1012)
```python
if isinstance(verse_num, list) and verse_num:
    # For multi-verse entries, store under first verse
    verse_num = verse_num[0]  # BUG: Only stores under FIRST verse
```

### Problem
When tafsir commentary spans verses 1-3:
- Stored only as: `"ibn-kathir:2:1"`
- Lookups for `"ibn-kathir:2:2"` and `"ibn-kathir:2:3"` fail
- User queries for verses 2-3 return "no content" even though it exists

### Fix Required

**File:** `backend/app.py`
**Lines:** 1010-1122 (in `load_chunks_from_verse_files_enhanced`)

```python
# Handle multi-verse entries (store under ALL verses in range)
verse_numbers = verse.get('verse_numbers', [])
if not verse_numbers:
    verse_numbers = [verse.get('verse_number')]

if isinstance(verse_numbers, int):
    verse_numbers = [verse_numbers]
elif not isinstance(verse_numbers, list):
    print(f"WARNING: Invalid verse_numbers format: {verse_numbers}")
    continue

# Store metadata under EACH verse in the range
for verse_num in verse_numbers:
    chunk_id = f"{source}:{surah}:{verse_num}"

    # Build full text (existing logic)
    chunk_parts = []
    if verse_text:
        chunk_parts.append(f"Verse {verse_num}: {verse_text}")

    # ... rest of chunk building logic ...

    full_text = " ".join(chunk_parts)

    # Store in both dictionaries
    TAFSIR_CHUNKS[chunk_id] = full_text
    CHUNK_SOURCE_MAP[chunk_id] = "Ibn Kathir" if source == "ibn-kathir" else "al-Qurtubi"

    # Store metadata with all verse numbers preserved
    VERSE_METADATA[chunk_id] = {
        'surah': surah,
        'verse_number': verse_num,  # Individual verse
        'verse_numbers': verse_numbers,  # Full range
        'source': source,
        'verse_text': verse_text,
        'topics': topics,
        'commentary': verse.get('commentary'),
        # ... rest of metadata ...
    }
```

**Impact:** Fixes direct lookups for all verses in multi-verse commentary

---

## HIGH PRIORITY FIX #4: Add Hybrid Fallback Search

### Problem
When semantic search returns no relevant results (all chunks above threshold), query fails completely. No fallback to keyword search.

### Fix Required

**File:** `backend/app.py`
**New function after line 1696:**

```python
def hybrid_search_fallback(query, semantic_chunks, distance_threshold=0.6):
    """
    Fallback to keyword search when semantic search fails

    Args:
        query: Original user query
        semantic_chunks: Results from semantic search
        distance_threshold: Threshold used for semantic search

    Returns:
        Additional chunks from keyword search, or empty list
    """
    # Check if semantic search was successful
    relevant_semantic = [c for c in semantic_chunks if c['distance'] < distance_threshold]

    if len(relevant_semantic) >= 5:
        # Semantic search worked fine
        return []

    print(f"⚠️  Semantic search weak ({len(relevant_semantic)} relevant chunks), trying keyword fallback")

    # Extract keywords from query
    import re
    # Remove stop words
    stop_words = {'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'about', 'what', 'when', 'where', 'why', 'how'}
    words = re.findall(r'\b\w+\b', query.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 3]

    print(f"   Keywords: {keywords}")

    # Search for chunks containing keywords
    keyword_matches = []
    for chunk_id, chunk_text in TAFSIR_CHUNKS.items():
        chunk_lower = chunk_text.lower()

        # Count keyword matches
        score = sum(1 for kw in keywords if kw in chunk_lower)

        if score > 0:
            source = CHUNK_SOURCE_MAP.get(chunk_id, 'Unknown')
            keyword_matches.append({
                'id': chunk_id,
                'text': chunk_text,
                'source': source,
                'distance': 1.0 - (score / len(keywords)),  # Pseudo-distance (lower = better)
                'verse_metadata': VERSE_METADATA.get(chunk_id, {}),
                'keyword_score': score
            })

    # Sort by keyword score (descending)
    keyword_matches.sort(key=lambda x: x['keyword_score'], reverse=True)

    # Take top 10
    top_keyword_matches = keyword_matches[:10]

    print(f"   Keyword fallback found {len(top_keyword_matches)} matches")

    return top_keyword_matches
```

**Usage in `perform_diversified_rag_search` (after line 1644):**

```python
# Step 3: Retrieve chunks using new function that handles segment IDs
retrieved_chunks = retrieve_chunks_from_neighbors(neighbors_result[0], distance_threshold=0.6)

# NEW: Hybrid fallback if semantic search weak
if len(retrieved_chunks) < 5:
    fallback_chunks = hybrid_search_fallback(query, retrieved_chunks, distance_threshold=0.6)
    retrieved_chunks.extend(fallback_chunks)
    print(f"   Added {len(fallback_chunks)} chunks from keyword fallback")
```

**Impact:** Catches cases where semantic embeddings don't match but keywords do

---

## MEDIUM PRIORITY FIX #5: Cache Embedding Model

### Current Code (Line 3463)
```python
embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
```

### Problem
Creates new embedding model instance **on every request** - slow!

### Fix Required

**File:** `backend/app.py`
**Lines:** 103-105 (add to globals)

```python
# Global variables
users_db = None
quran_db = None
embedding_model_instance = None  # NEW: Cache embedding model
TAFSIR_CHUNKS = {}
# ...
```

**Lines:** 3463-3465 (replace)

```python
# Initialize models (cached)
global embedding_model_instance
if embedding_model_instance is None:
    embedding_model_instance = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)

embedding_model = embedding_model_instance  # Reuse cached instance

endpoint_resource_name = f"projects/{GCP_INFRASTRUCTURE_PROJECT}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"
index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_resource_name)
```

**Impact:** Reduces latency by ~500ms per query

---

## MEDIUM PRIORITY FIX #6: Add Pre-Flight Content Check

### Problem
Runs expensive RAG pipeline even when query terms don't exist anywhere in corpus

### Fix Required

**File:** `backend/app.py`
**New function after line 1721:**

```python
def preflight_content_check(query, approach='tafsir'):
    """
    Quick check if query terms exist in corpus before running full RAG

    Returns:
        dict with 'should_proceed', 'message', 'suggestion'
    """
    import re

    # Extract keywords
    stop_words = {'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'about', 'what', 'when', 'where', 'why', 'how', 'is', 'are', 'was', 'were'}
    words = re.findall(r'\b\w+\b', query.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 3]

    if len(keywords) == 0:
        return {'should_proceed': True}  # Can't check with no keywords

    # Count chunks containing ANY keyword
    matches = 0
    for text in TAFSIR_CHUNKS.values():
        if any(kw in text.lower() for kw in keywords):
            matches += 1
            if matches >= 5:  # Early exit
                break

    if matches < 3:
        return {
            'should_proceed': False,
            'message': f"Found only {matches} passages mentioning your query terms. Results may be limited.",
            'suggestion': "Try rephrasing with different keywords, asking about related concepts, or using a broader thematic approach.",
            'keyword_count': len(keywords),
            'match_count': matches
        }

    return {'should_proceed': True, 'match_count': matches}
```

**Usage in Route 3 (after line 3447):**

```python
# Pre-flight content check
check = preflight_content_check(rag_query, approach)
if not check['should_proceed']:
    print(f"⚠️  Pre-flight check: {check['message']}")
    # Could return warning to user, or proceed anyway with warning
    # For now, log but continue
```

**Impact:** Warns users when content likely doesn't exist

---

## DEPLOYMENT PRIORITY

### MUST DEPLOY IMMEDIATELY (P0)
These are already committed but NOT deployed:
1. ✅ Fix indentation error (commit d1a613c)
2. ✅ Fix UnboundLocalError for verse variable (commit d3b3c78)
3. ✅ Fix unsafe nested dictionary access (commit d3b3c78)
4. ✅ Add thread-safe cache management (commit d3b3c78)

**ACTION REQUIRED:** Run `./deploy-backend.sh` NOW

### IMPLEMENT NEXT (P1) - Today
5. ⬜ Add distance threshold filtering (Fix #1)
6. ⬜ Fix source weighting for historical queries (Fix #2)
7. ⬜ Fix multi-verse metadata storage (Fix #3)

### IMPLEMENT SOON (P2) - This Week
8. ⬜ Add hybrid keyword fallback (Fix #4)
9. ⬜ Cache embedding model (Fix #5)
10. ⬜ Add pre-flight content check (Fix #6)

---

## TESTING PLAN

After implementing fixes, test with these queries:

### Historical Queries (should improve significantly)
- ✅ "Context of Year of Grief" → Should find Ibn Kathir commentary
- ✅ "Battle of Badr background" → Should find Surah 8 commentary
- ✅ "Treaty of Hudaybiyyah" → Should find Surah 48 commentary

### Verse Lookup Queries (should work reliably)
- ✅ "2:255" → Should return Ayat al-Kursi tafsir
- ✅ "93:1-7" → Should return full range from both sources

### Edge Cases (should handle gracefully)
- ✅ "Context of Surah 50" → al-Qurtubi not available, should use Ibn Kathir only
- ✅ "Hadith about Surah 112" → Should find relevant content if it exists

---

## MONITORING METRICS TO ADD

```python
# Add to Route 3 (after line 3472)
SEARCH_QUALITY_METRICS = {
    'total_queries': 0,
    'semantic_success': 0,  # Chunks found below threshold
    'semantic_failure': 0,  # No relevant chunks
    'fallback_triggered': 0,  # Keyword fallback used
    'avg_chunk_distance': [],  # Track relevance quality
    'empty_results': 0  # AI says "no content"
}

# After vector search
relevant_chunks = [c for c in selected_chunks if c['distance'] < 0.6]
SEARCH_QUALITY_METRICS['total_queries'] += 1

if len(relevant_chunks) > 0:
    SEARCH_QUALITY_METRICS['semantic_success'] += 1
    avg_dist = sum(c['distance'] for c in relevant_chunks) / len(relevant_chunks)
    SEARCH_QUALITY_METRICS['avg_chunk_distance'].append(avg_dist)
else:
    SEARCH_QUALITY_METRICS['semantic_failure'] += 1
```

Add to `/health` endpoint to surface metrics.

---

**END OF DOCUMENT**
