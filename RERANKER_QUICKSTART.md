# Reranker System - Quick Start Guide

## 🚀 Installation (2 minutes)

### Step 1: Install Dependencies

```bash
pip install sentence-transformers
```

That's it! The reranker models will download automatically on first startup.

### Step 2: Verify Installation

Start your backend and check the logs:

```bash
python backend/app.py
```

Look for this output:

```
======================================================================
🔄 INITIALIZING RERANKER SYSTEM (Setup 1: Retriever-Reranker)
======================================================================

📥 Attempting to load: jina-reranker-v2-base-multilingual
   Description: Primary: Multilingual (Arabic+English), 8192 token context
   Max length: 8192 tokens

✅ SUCCESS: Reranker loaded in 8.43s
   Model: jina-reranker-v2-base-multilingual
   Test score: 0.7234
   Default threshold: 0.0
   Status: Ready for production use
======================================================================
```

### Step 3: Check Health Status

```bash
curl http://localhost:5000/health
```

Look for:

```json
{
  "reranker": {
    "enabled": true,
    "model": "jina-reranker-v2-base-multilingual",
    "status": "active",
    "calls": 0,
    "avg_latency_ms": 0.0
  }
}
```

---

## 🧪 Testing

### Quick Test Queries

Run these queries through your frontend or API to verify reranking:

#### Test 1: Semantic Nuance
```json
{
  "query": "patience in adversity in Quran",
  "approach": "semantic"
}
```

**Expected behavior:**
- Should retrieve 50 candidates
- Rerank to ~20 final chunks
- Top verses: 2:153, 2:155, 3:200, 16:126
- Log should show rerank scores around 0.5-0.9

#### Test 2: Negation Handling
```json
{
  "query": "lack of patience in Quran",
  "approach": "semantic"
}
```

**Expected behavior:**
- Should find verses about impatience/hastiness
- Should NOT return general patience verses
- Reranker should correctly distinguish opposites

#### Test 3: Arabic + English Mixed
```json
{
  "query": "sabr and tawakkul",
  "approach": "semantic"
}
```

**Expected behavior:**
- Should handle both Arabic terms
- Jina multilingual model should score both highly

#### Test 4: Historical Context
```json
{
  "query": "Battle of Badr revelation context",
  "approach": "semantic"
}
```

**Expected behavior:**
- Should find verses from Surah 3 (Aal-E-Imran) and 8 (Al-Anfal)
- Reranker should prioritize historical context mentions

### Check Logs

After each query, check the backend logs for this output:

```
🔍 STAGE 1: Vector Retrieval (High Recall)
   Query: patience in adversity in Quran
   Approach: semantic
   Candidates to retrieve: 50 (increased for reranking)
   ✅ Vector search returned: 50 neighbors
   Retrieved: 47 chunks for reranking

✨ STAGE 2: CrossEncoder Reranking (High Precision)
   ✨ Reranker: 47 → 32 relevant → 20 final
      Model: jina-reranker-v2-base-multilingual
      Threshold: -0.50
      Top score: 0.874
      Latency: 143.2ms

📊 STAGE 3: Dynamic Source Weighting
   ✅ Dynamic weights: IK better (IK:0.76 > Q:0.58) → 70%/30%
   Final distribution: IK=14, Q=6
```

**What to look for:**
- ✅ Stage 2 should show reranker is active
- ✅ Top score should be >0.5 for relevant queries
- ✅ Latency should be 100-200ms
- ✅ Final distribution should make sense for query

---

## 📊 Monitoring

### View Reranker Statistics

```bash
curl http://localhost:5000/reranker-stats
```

**What to monitor:**

```json
{
  "performance": {
    "total_calls": 1234,
    "avg_latency_ms": 147.3,
    "fallback_to_distance_count": 0  // Should be 0 if working properly
  }
}
```

**Red flags:**
- ❌ `fallback_to_distance_count` > 10% of total calls
- ❌ `avg_latency_ms` > 300ms
- ❌ `status` != "active"

---

## 🐛 Troubleshooting

### Problem: Reranker shows "disabled"

**Solution:**
```bash
# Check if sentence-transformers is installed
pip list | grep sentence-transformers

# If not installed, install it
pip install sentence-transformers

# Restart backend
```

### Problem: Model download fails

**Symptoms:**
```
⚠️ FAILED to load jina-reranker-v2-base-multilingual
   Error: HTTPError: 403 Client Error
```

**Solution:**
```bash
# Try manually downloading
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('jinaai/jina-reranker-v2-base-multilingual')"

# If that fails, check internet connection and try fallback model
# System will automatically use ms-marco fallback
```

### Problem: High fallback_to_distance_count

**Symptoms:**
```json
{
  "fallback_to_distance_count": 123  // Should be near 0
}
```

**Possible causes:**
1. Memory pressure (model being unloaded)
2. Thread contention
3. Extremely long chunks

**Solutions:**
```bash
# Check available memory
free -h

# Check chunk lengths in logs
grep "chunk length" backend.log

# Restart backend to clear memory
```

### Problem: Queries seem less accurate

**Check:**
1. Verify correct model loaded: `curl /reranker-stats`
2. Check rerank scores in logs (should be >0.3 for relevant)
3. Compare with old system using distance-based filtering

**Calibrate thresholds:**
```python
# In app.py, adjust thresholds if needed
RERANKER_MODELS = [
    {
        "name": "jina-reranker-v2-base-multilingual",
        "default_threshold": 0.0,  # Try -0.5 if too strict, +0.2 if too lenient
    }
]
```

---

## 📈 Performance Expectations

### Normal Operation

| Metric | Expected Value |
|--------|---------------|
| **Reranker latency** | 100-200ms |
| **Total query time** | 1.5-2.5s |
| **Fallback rate** | <1% |
| **Top rerank scores** | 0.5-0.9 for relevant queries |
| **Bottom rerank scores** | -2.0 to 0.0 for irrelevant |

### Rerank Score Distribution

**Jina model (scores [0, 1]):**
- **Highly relevant**: 0.7-0.9
- **Relevant**: 0.3-0.7
- **Marginally relevant**: 0.0-0.3
- **Irrelevant**: <0.0

**MS-MARCO fallback (scores [-10, 10]):**
- **Highly relevant**: 3.0-8.0
- **Relevant**: 0.0-3.0
- **Marginally relevant**: -2.0-0.0
- **Irrelevant**: <-2.0

---

## ✅ Success Checklist

After installation, verify:

- [ ] `/health` shows `"reranker.status": "active"`
- [ ] `/reranker-stats` shows Jina model loaded
- [ ] Test query shows 3-stage log output
- [ ] Top rerank scores are reasonable (>0.5)
- [ ] Latency is acceptable (<200ms for reranking)
- [ ] Fallback count is low (<1%)
- [ ] Query results are more accurate than before

---

## 🎯 Next Steps

1. **Run 50-100 diverse queries** to test robustness
2. **Monitor `/reranker-stats`** to track performance
3. **Calibrate thresholds** if score distribution is off
4. **Compare with old system** to validate improvements
5. **Document any edge cases** for future optimization

---

## 🆘 Need Help?

Check the full documentation:
- **[RERANKER_IMPLEMENTATION.md](RERANKER_IMPLEMENTATION.md)** - Complete technical details
- **[UNIFIED_ROADMAP.md](UNIFIED_ROADMAP.md)** - Overall system architecture

Or check the logs for detailed debug output!
