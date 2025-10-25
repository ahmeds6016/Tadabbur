# Dynamic Source Weighting - Complete Explanation

**Last Updated:** 2025-10-16
**Commit:** 60f49fd

---

## 🎯 THE PROBLEM WE'RE SOLVING

Your app has **TWO tafsir sources** with **DIFFERENT coverage**:

| Source | Coverage | Percentage |
|--------|----------|------------|
| **Ibn Kathir** | All 114 Surahs | 100% |
| **al-Qurtubi** | Surahs 1-4 only (up to 4:22) | ~3.5% |

**Question:** When a user asks "Year of Grief" (not in Surahs 1-4), should we waste time looking in al-Qurtubi?

**Answer:** NO! We should dynamically adjust based on what content actually exists.

---

## 📊 HOW DYNAMIC WEIGHTING WORKS

### Step-by-Step for Query: "Context of Year of Grief"

#### **Step 1: Vector Search** (Lines 1637-1644)
```python
# Search for 25 nearest neighbors
neighbors_result = index_endpoint.find_neighbors(
    deployed_index_id=DEPLOYED_INDEX_ID,
    queries=[query_embedding],
    num_neighbors=25
)

# Filter by distance < 0.6 (only relevant chunks)
retrieved_chunks = retrieve_chunks_from_neighbors(neighbors_result[0], distance_threshold=0.6)
```

**Result:**
```python
retrieved_chunks = [
    {'source': 'Ibn Kathir', 'distance': 0.35, 'text': '...'},
    {'source': 'Ibn Kathir', 'distance': 0.38, 'text': '...'},
    {'source': 'Ibn Kathir', 'distance': 0.41, 'text': '...'},
    # ... 12 more Ibn Kathir chunks
    # 0 al-Qurtubi chunks (content not in Surahs 1-4)
]
```

#### **Step 2: Separate by Source** (Lines 1683-1684)
```python
ibn_kathir_retrieved = [c for c in retrieved_chunks if c['source'] == 'Ibn Kathir']
# Result: 15 chunks

qurtubi_retrieved = [c for c in retrieved_chunks if c['source'] == 'al-Qurtubi']
# Result: 0 chunks
```

#### **Step 3: Calculate Dynamic Weights** (Lines 1687-1717)
```python
if len(qurtubi_retrieved) == 0:
    # al-Qurtubi has NO relevant chunks
    weights = {'Ibn Kathir': 1.0, 'al-Qurtubi': 0.0}
    print("Dynamic weights: al-Qurtubi has no chunks → Ibn Kathir 100%")
```

**Explanation:**
- Vector search found 0 chunks from al-Qurtubi
- This means "Year of Grief" content is NOT in Surahs 1-4
- Automatically use Ibn Kathir 100%

#### **Step 4: Select Chunks Based on Weights** (Lines 1722-1735)
```python
for source_name, chunks in source_chunks.items():
    weight = weights.get(source_name, 0.5)

    # For Ibn Kathir (weight = 1.0):
    num_chunks = max(3, int(1.0 * 12)) = 12 chunks

    # For al-Qurtubi (weight = 0.0):
    num_chunks = max(3, int(0.0 * 12)) = 3 chunks (minimum)
    # But there are 0 chunks available, so takes 0
```

**Final Result:** Sends 12 Ibn Kathir chunks to AI ✅

---

## 🔄 DECISION TREE

```
Query arrives
    │
    ├─ Vector Search (25 neighbors, filter by distance < 0.6)
    │
    ├─ Separate by Source
    │   ├─ Ibn Kathir: N chunks
    │   └─ al-Qurtubi: M chunks
    │
    ├─ Calculate Weights:
    │   │
    │   ├─ Case 1: M = 0 (no al-Qurtubi chunks)
    │   │   └─ Weights: Ibn Kathir 100%, al-Qurtubi 0%
    │   │      Reason: Content not in Surahs 1-4
    │   │
    │   ├─ Case 2: N = 0 (no Ibn Kathir chunks)
    │   │   └─ Weights: Ibn Kathir 0%, al-Qurtubi 100%
    │   │      Reason: Unlikely, but handle gracefully
    │   │
    │   └─ Case 3: Both have chunks
    │       │
    │       ├─ Compare average distances:
    │       │   avg_dist_IK = sum(distances) / N
    │       │   avg_dist_Q = sum(distances) / M
    │       │
    │       ├─ If |avg_dist_IK - avg_dist_Q| < 0.1:
    │       │   └─ Weights: 50% / 50%
    │       │      Reason: Both sources equally good
    │       │
    │       ├─ Else if avg_dist_IK < avg_dist_Q:
    │       │   └─ Weights: 70% / 30%
    │       │      Reason: Ibn Kathir has better matches
    │       │
    │       └─ Else:
    │           └─ Weights: 30% / 70%
    │              Reason: al-Qurtubi has better matches
    │
    └─ Apply Weights → Select final chunks → Send to AI
```

---

## 📈 EXAMPLES WITH ACTUAL NUMBERS

### Example 1: "Year of Grief" (Historical Query)

**Vector Search Returns:**
| Source | # Chunks | Avg Distance |
|--------|----------|--------------|
| Ibn Kathir | 15 | 0.38 |
| al-Qurtubi | 0 | N/A |

**Dynamic Weighting Decision:**
```
len(qurtubi_retrieved) == 0
→ weights = {'Ibn Kathir': 1.0, 'al-Qurtubi': 0.0}
```

**Chunks Sent to AI:**
- Ibn Kathir: `int(1.0 × 12)` = **12 chunks** ✅
- al-Qurtubi: `int(0.0 × 12)` = **0 chunks** (none available anyway)

**AI Response:** Provides detailed historical context about Year of Grief ✅

---

### Example 2: "Explain Ayat al-Kursi" (2:255)

**Vector Search Returns:**
| Source | # Chunks | Avg Distance |
|--------|----------|--------------|
| Ibn Kathir | 12 | 0.25 |
| al-Qurtubi | 10 | 0.27 |

**Dynamic Weighting Decision:**
```
Both have chunks
avg_dist_IK = 0.25
avg_dist_Q = 0.27
difference = |0.25 - 0.27| = 0.02 < 0.1
→ weights = {'Ibn Kathir': 0.5, 'al-Qurtubi': 0.5}  # Similar quality
```

**Chunks Sent to AI:**
- Ibn Kathir: `int(0.5 × 10)` = **5 chunks**
- al-Qurtubi: `int(0.5 × 10)` = **5 chunks**
- **Total:** 10 chunks (balanced mix)

**AI Response:** Synthesizes both classical tafsir perspectives ✅

---

### Example 3: "Historical context of Surah Al-Fatihah" (Surah 1)

**Vector Search Returns:**
| Source | # Chunks | Avg Distance |
|--------|----------|--------------|
| Ibn Kathir | 8 | 0.40 |
| al-Qurtubi | 11 | 0.30 |

**Dynamic Weighting Decision:**
```
Both have chunks
avg_dist_IK = 0.40
avg_dist_Q = 0.30
difference = |0.40 - 0.30| = 0.10 (not < 0.1, so not "similar")
avg_dist_Q < avg_dist_IK (0.30 < 0.40)
→ weights = {'Ibn Kathir': 0.3, 'al-Qurtubi': 0.7}  # al-Qurtubi better
```

**Chunks Sent to AI:**
- Ibn Kathir: `int(0.3 × 12)` = **3 chunks**
- al-Qurtubi: `int(0.7 × 12)` = **8 chunks**
- **Total:** 11 chunks (favors al-Qurtubi)

**AI Response:** Rich historical context from al-Qurtubi's detailed commentary ✅

---

### Example 4: "What is patience in adversity?" (Thematic Query)

**Vector Search Returns:**
| Source | # Chunks | Avg Distance |
|--------|----------|--------------|
| Ibn Kathir | 18 | 0.35 |
| al-Qurtubi | 3 | 0.55 |

**Dynamic Weighting Decision:**
```
Both have chunks
avg_dist_IK = 0.35
avg_dist_Q = 0.55
difference = |0.35 - 0.55| = 0.20 > 0.1
avg_dist_IK < avg_dist_Q (0.35 < 0.55)
→ weights = {'Ibn Kathir': 0.7, 'al-Qurtubi': 0.3}  # Ibn Kathir better
```

**Chunks Sent to AI:**
- Ibn Kathir: `int(0.7 × 15)` = **10 chunks** (for thematic, uses 15 as multiplier)
- al-Qurtubi: `int(0.3 × 15)` = **4 chunks**
- **Total:** 14 chunks (favors Ibn Kathir)

**AI Response:** Comprehensive thematic analysis from Ibn Kathir's complete coverage ✅

---

## 🎛️ THE THRESHOLDS EXPLAINED

### Distance Threshold (0.6)
```python
distance_threshold = 0.6  # Line 1644
```

**What it means:**
- Vector search returns chunks with semantic distance from 0.0 (identical) to 1.0 (completely different)
- We only keep chunks with `distance < 0.6` (moderately relevant or better)
- Rejects chunks with `distance ≥ 0.6` (too irrelevant)

**Example:**
```
Chunk A: distance = 0.25  ✅ KEEP (highly relevant)
Chunk B: distance = 0.55  ✅ KEEP (moderately relevant)
Chunk C: distance = 0.75  ❌ REJECT (too irrelevant)
```

### Similarity Threshold (0.1)
```python
if distance_diff < 0.1:  # Line 1704
```

**What it means:**
- When comparing average distances between sources, if difference is < 0.1, consider them "similar quality"
- Use 50/50 balanced mix

**Example:**
```
Ibn Kathir avg: 0.35
al-Qurtubi avg: 0.38
Difference: 0.03 < 0.1  → Use 50/50 ✅

Ibn Kathir avg: 0.30
al-Qurtubi avg: 0.45
Difference: 0.15 > 0.1  → Favor better source (70/30) ✅
```

---

## 🔍 WHY THIS IS BETTER THAN KEYWORD-BASED

### ❌ Keyword Approach (Rejected)
```python
# BAD: Guessing based on keywords
if 'fatiha' in query or 'baqarah' in query:
    weights = {'Ibn Kathir': 0.5, 'al-Qurtubi': 0.5}
else:
    weights = {'Ibn Kathir': 0.8, 'al-Qurtubi': 0.2}
```

**Problems:**
1. What if user asks "patience" and relevant content is in both Surah 2 AND Surah 10?
2. Have to maintain huge keyword list
3. Doesn't account for actual content availability
4. Brittle - breaks with different phrasings

### ✅ Vector Search-Based (Current)
```python
# GOOD: Let the data tell us
qurtubi_chunks = [chunks from vector search]
if len(qurtubi_chunks) == 0:
    weights = {'Ibn Kathir': 1.0, 'al-Qurtubi': 0.0}
```

**Benefits:**
1. Adapts automatically to what content exists
2. No keyword lists to maintain
3. Works for ANY query phrasing
4. Self-correcting based on actual semantic similarity

---

## 🚀 APPLIES TO ALL THREE APPROACHES

The dynamic weighting logic is **UNIVERSAL** - applies to:

1. **`approach='tafsir'`** - Classical verse-by-verse commentary
2. **`approach='thematic'`** - Thematic/conceptual connections
3. **`approach='historical'`** - Historical context and events

**No special cases needed!** The vector search results automatically determine the best source mix.

---

## 📝 CODE LOCATION

**File:** `backend/app.py`
**Function:** `perform_diversified_rag_search()`
**Lines:** 1678-1717 (dynamic weighting logic)

---

## 🧪 HOW TO TEST

After deployment, test these queries and check logs for weight decisions:

```bash
# Should see: "Ibn Kathir 100%" (no al-Qurtubi chunks)
curl -X POST .../tafsir -d '{"query": "Year of Grief", "approach": "historical"}'

# Should see: "50%/50%" (both sources have similar quality)
curl -X POST .../tafsir -d '{"query": "2:255"}'

# Should see: "30%/70%" (al-Qurtubi better for Surah 1)
curl -X POST .../tafsir -d '{"query": "Context of Surah 1"}'
```

Look for log lines like:
```
📊 Dynamic weights: al-Qurtubi has no chunks → Ibn Kathir 100%
📊 Dynamic weights: Similar quality (IK:0.25, Q:0.27) → 50%/50%
📊 Dynamic weights: Q better (Q:0.30 < IK:0.40) → 30%/70%
```

---

**END OF DOCUMENT**
