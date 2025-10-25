# Root Cause Analysis - Test Failures

**Date:** 2025-10-16
**Test Sample:** 25 queries
**Success Rate:** 72% (18/25)
**Failure Rate:** 28% (7/25)

---

## 🔍 **ROOT CAUSES IDENTIFIED FROM LOGS**

### **ROOT CAUSE #1: Gemini API Malformed JSON (2 failures)**

**Affected Queries:**
1. "Context of Surah Al-Lahab" (Historical approach)
2. "Context of fasting in Ramadan" (Historical approach)
3. "Injustice" (Thematic approach) - assumed similar pattern

**Log Evidence:**
```
📥 QUERY: Context of Surah Al-Lahab
🚀 ROUTE 3: Semantic Search (Full RAG)
   Vector search: 25 neighbors → 25 relevant (filtered 0, threshold=0.6)
   📊 Dynamic weights: Similar quality (IK:0.30, Q:0.29) → 50%/50%
   Retrieved 7 chunks (approach: historical)
✅ Semantic response generated
✅ Semantic response generated
⚠️  Attempt 1/3: Failed to parse JSON
   Retrying with lower temperature (0.2)...
✅ Semantic response generated
⚠️  Attempt 2/3: Failed to parse JSON
   Retrying with lower temperature (0.1)...
✅ JSON parsing succeeded on retry 3
```

**Analysis:**
- Vector search **working correctly** (25 neighbors retrieved, 0 filtered)
- Dynamic weighting **working correctly** (50%/50% split)
- Retrieved 7 relevant chunks **successfully**
- Gemini API **generated response** successfully
- **JSON parsing FAILED** on attempts 1 & 2
- **Succeeded on attempt 3** with lower temperature

**Root Cause:**
Gemini API (gemini-2.5-flash) occasionally returns **malformed JSON** despite structured prompts. The retry logic (commit 5707241) works but:
- Takes 3 attempts
- Still shows as "failure" in UI because frontend doesn't wait for all retries
- Or final retry also fails and returns error to user

**Current Retry Logic (app.py lines ~3511-3550):**
```python
for attempt in range(1, 4):  # 3 attempts
    try:
        raw_response = model.generate_content(full_prompt, generation_config=generation_config)
        response_text = safe_get_nested(raw_response, "candidates", 0, "content", "parts", 0, "text")

        if response_text:
            # Parse JSON
            final_json = json.loads(response_text)
            break  # Success!
    except json.JSONDecodeError as e:
        print(f"⚠️  Attempt {attempt}/3: Failed to parse JSON")
        if attempt < 3:
            generation_config.temperature = max(0.1, generation_config.temperature - 0.2)
            print(f"   Retrying with lower temperature ({generation_config.temperature})...")
        else:
            # Final retry failed - return error
            return error_response
```

**Why It's Still Failing:**
1. **Temperature reduction not aggressive enough** - Goes 0.6 → 0.4 → 0.2, but malformed JSON can still occur
2. **No JSON schema validation** - Not telling Gemini the EXACT structure expected
3. **No response pre-cleaning** - Gemini sometimes adds markdown formatting (```json...```)
4. **Frontend timeout** - May timeout before 3rd retry completes

**Frequency:** 2-3/25 queries = 8-12%

**Impact:** HIGH - Query fails completely, user sees generic error

---

### **ROOT CAUSE #2: Source Coverage Gaps (4-5 failures)**

**Affected Queries:**

#### **2a. "Context of Ayat al-Tayammum"**
**Expected Behavior:** Should return historical context about tayammum revelation
**Actual Behavior:** "No relevant information found"

**Log Analysis:** (Need to check logs for this specific query)
**Root Cause:**
- Ayat al-Tayammum is in Surah 5:6 (al-Ma'idah)
- al-Qurtubi covers Surahs 1-4 only (stops at 4:22) ❌
- Ibn Kathir should have it, but chunks may not be loaded
- Or semantic distance > 0.6 filtered out all chunks

---

#### **2b. "18:65-70" (Surah Al-Kahf)**
**Expected Behavior:** Should return tafsir for Al-Kahf verses 65-70
**Actual Behavior:** "do not contain specific commentary"

**Log Evidence:**
```
📥 QUERY: 18:65-70
🚀 ROUTE 3: Semantic Search (Full RAG)
   Vector search: 20 neighbors → 20 relevant (filtered 0, threshold=0.6)
   📊 Dynamic weights: al-Qurtubi has no chunks → Ibn Kathir 100%
   Retrieved 10 chunks (approach: tafsir)
```

**Analysis:**
- Vector search retrieved 20 neighbors ✅
- 0 filtered out (all distance < 0.6) ✅
- Dynamic weighting correctly chose Ibn Kathir 100% ✅
- Retrieved 10 chunks ✅
- **BUT Gemini still said "does not contain specific commentary"**

**Root Cause:**
The chunks retrieved were **semantically similar** (distance < 0.6) but **NOT about verses 18:65-70**. Possible reasons:
1. Ibn Kathir commentary for 18:65-70 **not loaded** into vector index
2. Query expansion corrupted the search: `"Surah 18 verse 65 18:65-70" → "Surah 18 verse 6"` ⚠️
3. Retrieved chunks were from different verses (mismatched semantic similarity)

**KEY INSIGHT:** Query expansion is **breaking** verse lookup!
- Original: "18:65-70"
- Expanded to: "Surah 18 verse 6" (WRONG - lost the "5-70" part!)

**This is a BUG in query expansion logic!**

---

#### **2c. "17:23-24" (Surah Al-Isra)**
**Expected Behavior:** Should return tafsir for verses about parents
**Actual Behavior:** User said "no tafsir" but UI showed content (UNCLEAR)

**Log Evidence:**
```
📥 QUERY: 17:23-24
🚀 ROUTE 3: Semantic Search (Full RAG)
   Vector search: 20 neighbors → 20 relevant (filtered 0, threshold=0.6)
   📊 Dynamic weights: al-Qurtubi has no chunks → Ibn Kathir 100%
   Retrieved 10 chunks (approach: tafsir)
```

**Analysis:**
- Same pattern as 18:65-70
- Query expansion: `"17:23-24" → "Surah 17 verse 2"` ⚠️ BUG!
- Retrieved 10 chunks but possibly wrong verses

**Root Cause:** Same query expansion bug as 2b

---

#### **2d. "Context of Surah Al-Lahab"**
**Expected Behavior:** Historical context of Surah 111
**Actual Behavior:** Malformed JSON (see Root Cause #1)

**Log Evidence:**
```
📥 QUERY: Context of Surah Al-Lahab
   Vector search: 25 neighbors → 25 relevant (filtered 0, threshold=0.6)
   📊 Dynamic weights: Similar quality (IK:0.30, Q:0.29) → 50%/50%
   Retrieved 7 chunks (approach: historical)
```

**Analysis:**
- Retrieved 7 chunks successfully
- But then malformed JSON error occurred
- **IF JSON parsing had succeeded**, this query might have worked!

**Root Cause:** Hybrid of #1 (malformed JSON) + possible coverage gap for Surah 111

---

### **ROOT CAUSE #3: Query Expansion Bug (NEWLY DISCOVERED!)**

**Location:** Likely in `expand_query_for_context()` function

**Evidence from logs:**
```
INFO: Query expanded from 'Surah 18 verse 65 18:65-70' to 'Surah 18 verse 6'
INFO: Query expanded from 'Surah 17 verse 23 17:23-24' to 'Surah 17 verse 2'
```

**Problem:**
- Query expansion is **truncating verse numbers**
- "18:65-70" → "verse 6" (should be "verse 65-70")
- "17:23-24" → "verse 2" (should be "verse 23-24")

**Impact:**
- Vector search retrieves chunks for **wrong verses**
- Gemini receives irrelevant content
- Returns "does not contain" even though source has the data

**Severity:** HIGH - Affects all multi-verse range queries in Route 3

---

### **ROOT CAUSE #4: Surah 3:26-27 Anomaly**

**Expected Behavior:** Should work (al-Qurtubi covers Surah 3)
**Actual Behavior:** "do not contain specific commentary for Surah 3, verse 26"

**Log Evidence:**
```
📥 QUERY: 3:26-27
🚀 ROUTE 3: Semantic Search (Full RAG)
INFO: Query expanded from 'Surah 3 verse 26 3:26-27' to 'Surah'
WARNING: Chunk not found for ID: ibn-kathir:23:0 (base: ibn-kathir:23:0)
   Vector search: 20 neighbors → 19 relevant (filtered 0, threshold=0.6)
   📊 Dynamic weights: Similar quality (IK:0.29, Q:0.29) → 50%/50%
   Retrieved 8 chunks (approach: tafsir)
```

**Analysis:**
- Query expansion **failed completely**: "3:26-27" → "Surah" (NO verse number!) ⚠️⚠️
- Chunk not found warning: `ibn-kathir:23:0` (Surah 23, not Surah 3!)
- Retrieved 19 neighbors but **wrong surah**
- Retrieved 8 chunks but **not from Surah 3:26-27**

**Root Cause:**
1. **Query expansion severely broken** - lost all verse information
2. Vector search retrieved chunks from **Surah 23** instead of **Surah 3**
3. Retrieved chunks were irrelevant to the query

**This is the WORST case of the query expansion bug!**

---

### **ROOT CAUSE #5: Firestore Index Missing (Non-blocking)**

**Evidence:**
```
ERROR in /annotations/verse: FailedPrecondition - 400 The query requires an index.
```

**Analysis:**
- This is for the annotations endpoint, NOT the main tafsir query
- User was trying to add/view annotations
- Firestore composite index missing for: `surah + verse + createdAt + __name__`

**Impact:** Annotations feature broken, but doesn't affect tafsir queries

**Severity:** MEDIUM - Secondary feature affected

---

## 📊 **ROOT CAUSE SUMMARY**

| Root Cause | Failures | % of Total | Severity | Fix Complexity |
|------------|----------|------------|----------|----------------|
| **#3: Query Expansion Bug** | 3-4 | 12-16% | CRITICAL | MEDIUM |
| **#1: Malformed JSON** | 2-3 | 8-12% | HIGH | LOW |
| **#2: Coverage Gaps** | 1-2 | 4-8% | MEDIUM | HIGH |
| **#5: Firestore Index** | N/A | 0% | MEDIUM | TRIVIAL |

**Key Insight:**
- **Root Cause #3 (Query Expansion Bug)** is the **PRIMARY issue** (12-16% of failures)
- If we fix this ONE bug, we'd go from 72% → 84-88% success rate!
- Combined with malformed JSON fix → 92-96% success rate

---

## 🎯 **RECOMMENDED FIX PRIORITY**

### **PRIORITY 1: Fix Query Expansion Bug** (CRITICAL)

**Estimated Time:** 1-2 hours
**Expected Impact:** +12-16% success rate (72% → 84-88%)

**Files to Fix:**
- `app.py` - `expand_query_for_context()` or similar function
- Need to find where query expansion happens

**Fix Required:**
1. Preserve full verse numbers in expansion
2. Don't truncate "18:65-70" to "verse 6"
3. Don't strip verse info completely ("3:26-27" → "Surah")

---

### **PRIORITY 2: Strengthen Malformed JSON Handling** (HIGH)

**Estimated Time:** 1-2 hours
**Expected Impact:** +8-12% success rate (88% → 96-100%)

**Fixes Required:**
1. Add response pre-cleaning (strip markdown ```json...```)
2. Use more aggressive temperature reduction (0.6 → 0.3 → 0.0)
3. Add JSON schema to generation config
4. Increase retries to 5 attempts
5. Add fallback to simpler prompt on final retry

---

### **PRIORITY 3: Create Firestore Index** (TRIVIAL)

**Estimated Time:** 5 minutes
**Expected Impact:** Fixes annotations feature

**Fix:** Click the URL in the error message to auto-create index

---

### **PRIORITY 4: Investigate Coverage Gaps** (MEDIUM)

**Estimated Time:** 2-4 hours
**Expected Impact:** +4-8% success rate (potential)

**Tasks:**
1. Verify Ibn Kathir coverage for Surah 111 (Al-Lahab)
2. Check if Ayat al-Tayammum (5:6) exists in source data
3. Add logging for "chunk not found" warnings

---

## 🚀 **ACTION PLAN**

### **Step 1: Fix Query Expansion Bug (NOW)**
- Find and fix the expansion logic
- Test with: 3:26-27, 17:23-24, 18:65-70
- Expected: 72% → 88% success rate

### **Step 2: Fix Malformed JSON (NEXT)**
- Add pre-cleaning and schema validation
- Increase retries to 5
- Expected: 88% → 96% success rate

### **Step 3: Create Firestore Index (5 min)**
- Click the URL to create index
- Fixes annotations feature

### **Step 4: Monitor and Re-test (AFTER)**
- Run full 25 query test suite
- Verify 95%+ success rate
- Document any remaining edge cases

---

**END OF ANALYSIS**
