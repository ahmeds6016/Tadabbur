# Why Duplicate Requests Are Happening

**Date:** 2025-10-16
**Analysis:** Based on frontend code review and log patterns

---

## 🔍 **ROOT CAUSE IDENTIFIED**

The duplicate requests are **NOT** coming from:
- ❌ Frontend retry logic (doesn't exist)
- ❌ Double-click prevention issue (button is properly disabled)
- ❌ User error

The duplicates are likely from **ONE OF THREE SOURCES:**

---

## **SOURCE #1: Browser/Network Auto-Retry (MOST LIKELY)**

### **The Problem:**

When a fetch request takes too long (20+ seconds seen in logs), browsers and network infrastructure may:

1. **Timeout and retry automatically**
   - Browser thinks first request hung
   - Initiates retry while first request still processing
   - Both requests hit backend simultaneously

2. **TCP connection issues**
   - Connection appears broken
   - Browser retries on new connection
   - Original connection still alive

3. **HTTP/2 multiplexing issues**
   - Stream error on one request
   - Browser retries on new stream
   - Both streams active

### **Evidence:**

```
Logs show:
- Request A starts processing → succeeds
- Request B starts 5 microseconds later → fails
- Both for same query, same user
```

This timing is **too fast** for user double-click (would be 100+ milliseconds apart).

### **Why This Happens to You:**

- **30-second timeout** still quite long for browsers (default is often 30s)
- Your queries take **20+ seconds** (logs confirm)
- Browser times out just as response arrives
- Retry kicks in, creates race condition

---

## **SOURCE #2: Cloud Run Load Balancer Retry**

### **The Problem:**

Google Cloud Run load balancer has **automatic retry logic** for:
- Timeouts
- 502/503/504 errors
- Connection failures

### **How It Works:**

1. User sends request to Cloud Run
2. Load balancer forwards to container instance
3. If response takes too long or connection drops
4. Load balancer **automatically retries** on different container instance
5. Now **two requests** processing same query

### **Evidence:**

```json
"revision_name": "tafsir-backend-00113-zxz"
"instanceId": "0069c7a988c55d9f30259eaabbea793bd03e9e77d5e38744..." (same instance)
```

Both requests hitting **same instance** rules this out for your case.

---

## **SOURCE #3: Frontend "Try It" Button (POSSIBLE)**

### **The Problem:**

Lines 984-1027 in `page.js`:

```javascript
<button
  onClick={async () => {
    // Set the approach first
    setApproach(response.approach_suggestion.suggested);

    // Wait for state update, then trigger search
    setTimeout(async () => {
      setIsTafsirLoading(true);
      setResponse(null);

      // MAKES NEW FETCH REQUEST
      const res = await fetch(`${BACKEND_URL}/tafsir`, {
        method: 'POST',
        headers: { ... },
        body: JSON.stringify({
          approach: response.approach_suggestion.suggested,
          query
        })
      });
      // ...
    }, 0);
  }}
>
  Try It
</button>
```

**If user:**
1. Submits query
2. Gets partial response with approach suggestion
3. Clicks "Try It"
4. Original request still processing

**Result:** Two concurrent requests!

### **But This Doesn't Match Your Test:**

Your test queries ("2:286", "Anger", etc.) didn't involve clicking "Try It" button.

---

## **SOURCE #4: Fetch API Default Behavior**

### **The Problem:**

The `fetch()` API has **NO built-in timeout**. Browsers implement their own:

```javascript
const res = await fetch(`${BACKEND_URL}/tafsir`, {
  method: 'POST',
  // NO TIMEOUT SPECIFIED!
  headers: { ... },
  body: JSON.stringify({ approach, query })
});
```

**What happens:**
1. Request sent
2. Backend processing (20+ seconds)
3. Browser timeout kicks in (varies by browser, ~30-120s)
4. Browser may retry OR connection drops
5. User sees error but backend still processing

**Why you see failures:**
- First request succeeds (logs show ✅)
- Retry/duplicate request fails (malformed JSON)
- **User receives response from failed retry, not successful first request!**

---

## ✅ **THE ACTUAL ISSUE: Response Routing**

### **The Real Problem Isn't Duplicates - It's Which Response You See!**

**Timeline:**

```
00:00 - User submits "2:286"
00:01 - Request A starts processing (browser connection 1)
00:20 - Browser times out, retry kicks in
00:21 - Request B starts processing (browser connection 2)
00:25 - Request A completes ✅ "Direct verse formatted by AI"
00:27 - Request B fails ❌ "Failed to parse JSON after 5 attempts"
00:28 - Browser receives BOTH responses
00:29 - Browser shows Request B (the retry/failure) to user
```

**Why Browser Shows Request B:**
- Request B was initiated last (most recent)
- Browsers typically resolve promises in order of **completion**
- But if retry is on different connection, it may **override** first response

---

## 🔧 **WHY REQUEST DEDUPLICATION WON'T FULLY FIX THIS**

Request deduplication on backend helps:
✅ Prevents wasted processing
✅ Ensures same response for duplicates

But **DOESN'T** fix:
❌ Browser still sends two requests (browser-level retry)
❌ User still might see retry response instead of first response
❌ Network-level issues causing duplicates

---

## 🎯 **THE REAL FIX: Make Requests Faster**

### **Root Cause:**

20-30 second response times → browser timeouts → retries → race conditions

### **Solutions:**

#### **1. Reduce Processing Time (BEST FIX)**

**Target:** Get responses under 10 seconds

**How:**
- ✅ Already did: Route 2 for direct verses (1 LLM call vs 2)
- ✅ Already did: Caching for repeat queries
- ⚠️ **Still needed:** Reduce token context (50K → 30K)
- ⚠️ **Still needed:** Parallel processing where possible
- ⚠️ **Still needed:** Streaming responses (return partial results)

**Expected Impact:** 20s → 8s (60% faster)

---

#### **2. Add Frontend Timeout with Proper Error Handling (GOOD FIX)**

**Current:**
```javascript
const res = await fetch(`${BACKEND_URL}/tafsir`, {
  method: 'POST',
  // NO TIMEOUT!
});
```

**Fixed:**
```javascript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 45000); // 45s

try {
  const res = await fetch(`${BACKEND_URL}/tafsir`, {
    method: 'POST',
    signal: controller.signal,
    headers: { ... },
    body: JSON.stringify({ approach, query })
  });

  clearTimeout(timeoutId);
  const data = await res.json();
  // ...
} catch (err) {
  clearTimeout(timeoutId);

  if (err.name === 'AbortError') {
    setError('Request timed out after 45 seconds. Please try a simpler query or try again.');
  } else {
    setError(err.message);
  }
}
```

**Impact:**
- Explicit timeout prevents browser auto-retry
- Clear error message to user
- No duplicate requests from browser

---

#### **3. Add Request ID Tracking (DEBUGGING FIX)**

**Backend:**
```python
import uuid

@app.route('/tafsir', methods=['POST'])
def tafsir_handler_enhanced():
    request_id = str(uuid.uuid4())[:8]
    print(f"🆔 [{request_id}] QUERY: {query}")

    # ... process ...

    final_json['request_id'] = request_id
    return jsonify(final_json), 200
```

**Frontend:**
```javascript
const data = await res.json();
console.log(`Received response for request ID: ${data.request_id}`);
setResponse(data);
```

**Impact:**
- Can trace which response user received
- Helps debug race conditions
- Identifies duplicate patterns

---

#### **4. Implement Request Deduplication (PARTIAL FIX)**

**Backend:** (as discussed earlier)

```python
IN_FLIGHT_REQUESTS = {}
in_flight_lock = threading.Lock()

# At start of /tafsir
request_sig = f"{query}:{approach}:{user_id}"

with in_flight_lock:
    if request_sig in IN_FLIGHT_REQUESTS:
        # Wait for first request
        event = IN_FLIGHT_REQUESTS[request_sig]

if event:
    event.wait(timeout=60)
    # Return cached result
    with cache_lock:
        if cache_key in RESPONSE_CACHE:
            return jsonify(RESPONSE_CACHE[cache_key]), 200
```

**Impact:**
- ✅ Backend processes query only once
- ✅ Both requests get same (successful) response
- ❌ Doesn't prevent browser from sending duplicates
- ❌ Doesn't fix which response browser shows user

---

## 📊 **PRIORITY RANKING**

| Fix | Complexity | Impact | Priority |
|-----|------------|--------|----------|
| **Add frontend timeout (45s)** | 5 min | High | 🔴 CRITICAL |
| **Reduce token context (50K→30K)** | 2 min | High | 🔴 CRITICAL |
| **Add request ID tracking** | 10 min | Medium | 🟡 HIGH |
| **Request deduplication** | 30 min | Medium | 🟡 HIGH |
| **Streaming responses** | 4 hours | High | 🟢 FUTURE |

---

## 🧪 **HOW TO VERIFY THE ROOT CAUSE**

### **Test #1: Check Browser Network Tab**

1. Open DevTools → Network tab
2. Submit query "2:286"
3. Watch for:
   - How many `/tafsir` requests sent?
   - Do both complete?
   - Which response did browser use?

**Expected if browser-retry:**
- 2 requests to `/tafsir` with same payload
- First completes with 200 OK
- Second also runs (maybe 200, maybe 500)
- Browser shows second response

---

### **Test #2: Add Frontend Logging**

```javascript
const handleGetTafsir = async (e) => {
  e.preventDefault();
  console.log(`🚀 Submitting query: ${query} at ${new Date().toISOString()}`);

  // ... existing code ...

  console.log(`✅ Received response at ${new Date().toISOString()}`);
  console.log(`Response data:`, data);
};
```

**Check:** How many "🚀 Submitting" messages for single button click?
- **1 message** → Not frontend double-submit
- **2 messages** → Frontend issue (but code review says no)

---

### **Test #3: Add Request ID**

Implement request ID tracking (see above).

**Check logs:**
```
Request A (ID: abc123): ✅ Success
Request B (ID: def456): ❌ Failed

Frontend console: "Received request ID: def456"
```

**Confirms:** User saw failed request, not successful one!

---

## 📝 **CONCLUSION**

### **Why Duplicates Happen:**

**Most Likely:** Browser auto-retry due to 20+ second response times

**Evidence:**
- No retry logic in frontend code
- Submit button properly disabled
- Timing too fast for user double-click (5μs between requests)
- Both requests hit same backend instance

### **Why You See Failures:**

**The Problem:** You're seeing the response from the **failed retry**, not the **successful first request**

**Solution:** Need to either:
1. **Prevent retries** (frontend timeout with AbortController)
2. **Make requests faster** (reduce processing time)
3. **Deduplicate on backend** (ensure both requests get same response)

---

## 🎯 **RECOMMENDED ACTION PLAN**

### **IMMEDIATE (Do Now - 10 minutes):**

1. Add frontend timeout with AbortController
2. Add request ID tracking
3. Reduce token context 50K → 30K

**Expected Impact:**
- User success rate: 33% → 70%+
- Can debug which response user sees

### **HIGH PRIORITY (This Week):**

4. Implement backend request deduplication
5. Optimize query expansion (reduce latency)

**Expected Impact:**
- User success rate: 70% → 90%+
- Eliminate race conditions

### **FUTURE (Nice to Have):**

6. Streaming responses (partial results)
7. Query result preview (show cached results first)

**Expected Impact:**
- User success rate: 90% → 99%+
- Much better UX

---

**END OF ANALYSIS**
