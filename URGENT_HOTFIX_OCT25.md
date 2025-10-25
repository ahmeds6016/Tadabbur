# URGENT HOTFIX - October 25, 2024

## Critical Issues Addressed

### 1. 🔴 **CRITICAL: Token Indexing Error**
**Error Found:**
```
Token indices sequence length is longer than the specified maximum sequence length for this model (2340 > 1024)
Token indices sequence length is longer than the specified maximum sequence length for this model (2471 > 1024)
```

**Root Cause:**
The tokenizer was trying to encode entire 18K token documents at once, exceeding its internal 1024 token buffer limit.

**Fix Applied:**
- Pre-chunk documents before tokenization to avoid buffer overflow
- Process documents in safe-sized chunks (8KB characters)
- Tokenize each chunk separately, then create sliding windows

### 2. 🔴 **CRITICAL: 5+ Minute Query Latency**
**Issue:**
Queries taking over 5 minutes, sometimes not returning at all.

**Root Cause:**
- No timeout protection in reranking
- Processing 40-50 chunks with up to 30+ windows each
- Potential for 1500+ reranking operations per query

**Fixes Applied:**
- Added 60-second timeout for reranking (configurable)
- Limited to 30 windows per chunk maximum
- Added timeout fallback scoring
- Enhanced logging to track actual timing

### 3. 🟡 **User Onboarding Delay**
**Issue:**
Long delay between sign-out and persona selection screen for new users.

**Analysis:**
- User profile creation appears normal
- Likely related to overall system performance issues
- Should improve with reranking optimizations

## Code Changes

### File: backend/app.py

#### 1. Fixed Sliding Window Tokenization (lines 1632-1669)
```python
# CRITICAL FIX: Pre-chunk document to avoid tokenizer limit exceeded error
# First, do a rough character-based chunking to get manageable pieces
chars_per_token_estimate = 4
safe_chunk_size = max_total_tokens * chars_per_token_estimate * 2  # 2x safety margin

# If document is too long, pre-chunk it
if len(document) > safe_chunk_size:
    # Process document in safe-sized chunks...
```

#### 2. Added Timeout Protection (lines 1774-1801)
```python
MAX_RERANKING_TIME = 60  # Maximum 60 seconds for reranking
MAX_WINDOWS_PER_CHUNK = 30  # Limit windows per chunk

# Check timeout during processing
if time.time() - start_time > MAX_RERANKING_TIME:
    print(f"   ⚠️  Reranking timeout after {chunk_idx}/{len(chunks)} chunks")
    # Fall back to distance-based scoring for remaining chunks
```

#### 3. Enhanced Monitoring (lines 1906-1923)
```python
# Track timing for performance analysis
print(f"   ⏱️  RERANKER TIMING: {latency_ms:.0f}ms for {len(chunks)} chunks")

# Log warning for slow reranking
if latency_ms > 10000:  # More than 10 seconds
    print(f"   ⚠️  SLOW RERANKING: {latency_ms:.0f}ms")
```

## Testing Recommendations

1. **Monitor Reranking Times**
   ```bash
   # Watch for timing logs
   gcloud logging read "RERANKER TIMING" --project=tafsir-simplified --limit=50
   ```

2. **Check for Token Errors**
   ```bash
   # Should see NO more token indexing errors
   gcloud logging read "Token indices sequence length" --project=tafsir-simplified --limit=10
   ```

3. **Analyze Performance Metrics**
   ```bash
   curl https://tafsir-backend.run.app/reranker-stats | jq '.'
   ```

## Deployment Steps

1. **Test locally first** (if possible):
   ```bash
   cd backend
   python app.py
   # Run test queries
   ```

2. **Deploy to production**:
   ```bash
   cd backend
   gcloud run deploy tafsir-backend \
     --source . \
     --region us-central1 \
     --project tafsir-simplified
   ```

3. **Monitor logs immediately**:
   ```bash
   gcloud logging tail --project=tafsir-simplified
   ```

## Performance Tuning

After collecting timing data from production:

1. **Analyze median reranking time**:
   - Look for "RERANKER TIMING" logs
   - Calculate median time
   - Update MAX_RERANKING_TIME accordingly

2. **Optimize if needed**:
   - Consider reducing RERANKER_CONFIG chunks from 40/50 to 30/40
   - Adjust MAX_WINDOWS_PER_CHUNK based on actual usage
   - Consider implementing chunk pre-filtering

## Success Metrics

- ✅ No more token indexing errors
- ✅ Query response times < 10 seconds (target: < 5 seconds)
- ✅ No timeout errors in logs
- ✅ User onboarding flows complete normally

## Rollback Plan

If issues persist:
1. Set RERANKER_MODEL = None to disable reranking entirely
2. System will fall back to distance-based filtering
3. Re-deploy previous version if necessary

## Notes

- The 60-second timeout is conservative and can be reduced based on metrics
- The 30-window limit per chunk may need adjustment based on actual chunk sizes
- Consider implementing request-level caching to avoid reranking identical queries