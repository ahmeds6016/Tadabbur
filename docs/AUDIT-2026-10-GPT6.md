# Tadabbur independent audit — 2026-10-17

## 1. Executive summary

1. Audited main `7a0f3f15f26f447a0878339211ce61d9ca590447`, including `2271020`, on `codex/audit-gpt6`; findings only.
2. October 17 live metadata confirms backend `00273-dpr` and frontend `00308-vbm`, both 100% latest; friendly errors are already deployed.
3. The audit records 34 findings: 1 P0, 11 P1, 22 P2 and 0 P3; all are confirmed within the stated evidence limits.
4. Top risk: the hadith validator can retain unsupported attribution in free-text fields after downgrading its collection label.
5. Top risk: unsanitized model HTML executes same-origin iframe JavaScript in the actual installed frontend stack.
6. Top risk: neither Firestore database has managed backup schedules, retained regional backups or PITR enabled.
7. User-record routes consistently derive their tenant from the verified UID; no cross-user backend IDOR was found.
8. Offline verification passed 457 backend tests, 11 frontend tests and all 14 build pages; dependency advisories and a server-import error remain.
9. Address LOG-01 and SEC-01/02 before the next routine content release; prioritize the remaining P1 work and block iOS distribution on SEC-04/PRIV-02/04.
10. Only three permitted public GETs were made; deployed rules and the actual guest proxy identity remain unverified.

## 2. Scorecard

| Dimension | Rating | Reason |
|---|---|---|
| A. Security and vulnerabilities | Weak | Required auth and tenant paths are sound, but unsafe model rendering and abuse/dependency gaps remain. |
| B. Logic and correctness | Critical | A reproduced hadith-attribution bypass breaches the central content trust promise; parsing and cache identity also fail. |
| C. Performance | Adequate | Caching and deterministic retrieval are effective at current load; synchronous read fanout and capacity settings need work. |
| D. Error handling and resilience | Weak | Bounded retries work, but incomplete output, dependency errors and stale async state still escape the intended contracts. |
| E. Privacy and data | Weak | Client access is constrained, but application encryption, erasure and first-party disclosure are incomplete. |
| F. Reliability, operations and cost | Weak | Alerts and current traffic are healthy; backups/PITR are absent and deployment scripts can misreport success. |
| G. Maintainability and tests | Adequate | The offline suite is useful and green, with concrete missing boundary tests rather than an architectural need to rewrite. |

## 3. Ranked findings table

Severity follows the requested P0–P3 scale. Likelihood and impact are separate in each detail. “Confirmed” means reproduced offline or unambiguous code/configuration; it does not imply exploitation was observed in production. Effort is S/M/L and includes the focused regression check. Findings known but still open in HANDOFF are retained; resolved historical defects are not reopened without current evidence.

| ID | Title | Severity | Status | Effort | Area |
|---|---|---|---|---|---|
| LOG-01 | Hadith downgrade can still display unsupported attribution and wording | P0 | Confirmed | M | B |
| SEC-01 | Raw commentary HTML executes same-origin iframe script | P1 | Confirmed | S | A |
| SEC-02 | Reader instructions and canonical verse requests share public cache identity | P1 | Confirmed | S | A |
| OPS-01 | Neither Firestore database has scheduled backups or PITR | P1 | Confirmed | M | F |
| SEC-03 | Abuse controls do not cap paid work or public Firestore amplification | P1 | Confirmed | M | A |
| SEC-04 | Dependency audit finds vulnerable image caching and native-origin code | P1 | Confirmed | M | A |
| ERR-02 | A parsed JSON object is cached without checking the answer contract | P1 | Confirmed | M | D |
| ERR-03 | Late account-bound fetches can display the previous reader’s data | P1 | Confirmed | M | D |
| PRIV-01 | Production reflection encryption silently falls back to clear application fields | P1 | Confirmed | M | E |
| PRIV-02 | Account deletion is absent and the existing Iman erasure misses two collections | P1 | Confirmed | L | E |
| OPS-02 | Deploy scripts can declare success while traffic still serves an older revision | P1 | Confirmed | M | F |
| LOG-02 | Named and slash ranges collide with single-verse cache documents | P1 | Confirmed | S | B |
| LOG-03 | Named verse shortcuts override explicit verses and invalid ranges degrade to singles | P2 | Confirmed | S | B |
| LOG-04 | Cache fallback discards the requested persona and learning level | P2 | Confirmed | S | B |
| LOG-05 | Cache lifecycle omits read-time expiry and pipeline identity in keys | P2 | Confirmed | S | B |
| LOG-06 | Concurrent progress writes lose a studied verse | P2 | Confirmed | M | B |
| LOG-07 | Reading-plan retries can rewind the current day and accept fractional days | P2 | Confirmed | S | B |
| LOG-08 | Several advertised badges cannot be earned through normal activity | P2 | Confirmed | S | B |
| LOG-09 | Iman struggle goals always subtract naive and aware timestamps | P2 | Confirmed | S | B |
| LOG-10 | Iman trajectory recomputation freezes on the oldest 90 logs | P2 | Confirmed | S | B |
| LOG-11 | A reflection can retain the share link of the previously studied verse | P2 | Confirmed | S | B |
| PERF-01 | Badge checks read up to 1,001 full annotations repeatedly on the study path | P2 | Confirmed | M | C |
| PERF-02 | Reader list APIs fetch unbounded full documents and catalog pages repeat verse reads | P2 | Confirmed | M | C |
| PERF-03 | Cloud Run accepts 80 concurrent requests for eight Gunicorn threads | P2 | Confirmed | S | C |
| ERR-01 | Firestore outages are reported as missing verses or empty successful content | P2 | Confirmed | S | D |
| ERR-04 | An aborted search can clear a newer request’s timer and loading state | P2 | Confirmed | S | D |
| ERR-05 | Firebase reCAPTCHA initialization runs during server import and drops a rejection | P2 | Confirmed | S | D |
| ERR-06 | Saved/history load failures still look like genuinely empty accounts | P2 | Confirmed | S | D |
| SEC-05 | 69 route handlers return raw exception strings to API callers | P2 | Confirmed | S | A |
| SEC-06 | The live frontend can be framed and has no CSP containment | P2 | Confirmed | S | A |
| PRIV-03 | Reader text and feedback identifiers enter unredacted operational logs | P2 | Confirmed | S | E |
| PRIV-04 | No Tadabbur privacy notice explains collected data and model processing | P2 | Confirmed | M | E |
| OPS-03 | Frontend build/runtime dependency installation is not reproducible | P2 | Confirmed | S | F |
| MAINT-01 | Passing tests leave the main trust and ownership boundaries unexercised | P2 | Confirmed | M | G |

## 4. Detailed findings

### LOG-01 — Hadith downgrade can still display unsupported attribution and wording

**P0 · Confirmed · Effort M · Area B**

**Likelihood:** Medium: requires erroneous model fields; the validator accepts them deterministically.

**Impact:** Wrong religious attribution can be displayed and shared for the cache lifetime.

**Evidence**

`backend/services/hadith_validation.py:192`:

```
        collection, narrator, attribution = _reference_parts(item)
        if collection and not _collection_is_supported(collection, source_tokens, matched_start):
            # The wording itself is verified verbatim against the supplied
            # sources — only the collection label could not be tied to this
            # wording. Keep the hadith but strip the unverified label rather
            # than losing grounded content (downgrade, not drop).
            item["_downgraded_collection"] = collection
            collection = ""

        if not attribution:
            attribution = "As cited in the supplied source excerpts"

```

`backend/services/hadith_validation.py:146`:

```
    if attribution:
        parts.append(attribution)
```

`frontend/app/page.js:3169` displays the normalized reference directly:

```
                            {h.reference}
```

**Failure and reproduction/proof:** Using the existing 2:255 Ahmad fixture, set the structured collection to Sahih Muslim, narrator to a synthetic incorrect name, and attribution to `Sahih Muslim 999999`. The collection is stripped, but the returned display reference is `narrated by Synthetic incorrect narrator; Sahih Muslim 999999`. Neither narrator nor attribution is grounded. Separately, a 100-word exact source plus three unsupported trailing words is accepted at a 0.967 shingle ratio. The 80% aggregate match is not full containment. Appendix probes reproduce both. This is a demonstrated hole in the current trust boundary, not a claim that the previously corrected production 2:255 document regressed.

**Minimal fix:** Build display attribution only from trusted matched source metadata; discard model-authored locators, narrators and grades unless verified. Require the complete normalized quote to be supported by a single source span, or display only an exact supported span. Preserve downgrade-not-drop for the supported wording. Bump the scholarly pipeline and review old shared/saved snapshots separately.

**Offline regression/acceptance:** Extend the existing Ahmad/Muslim golden test with the attribution-field bypass, a wrong narrator, altered endings and stitched excerpts. No unsupported label may appear anywhere in kept fields; authentic hyphenated labels must still survive.

### SEC-01 — Raw commentary HTML executes same-origin iframe script

**P1 · Confirmed · Effort S · Area A**

**Likelihood:** Medium: a model/cache response must contain hostile HTML; execution after rendering is reproduced.

**Impact:** An affected reader’s Firebase session and private reflections are exposed to same-origin script.

**Evidence**

`frontend/app/page.js:3096`:

```
                <ReactMarkdown remarkPlugins={[remarkBreaks]} rehypePlugins={[rehypeRaw]}>
                  {tafsir.explanation}
                </ReactMarkdown>
```

`backend/utils/text_cleaning.py:29`:

```
    text = re.sub(r'</?(?:span|div|p|font|center|u|s|mark|small|big|sub|sup|blockquote|ul|ol|li|table|tr|td|th)(?:\s[^>]*)?>', '', text, flags=re.IGNORECASE)

    return text
```

**Failure and reproduction/proof:** An iframe with `srcdoc="<script>parent.document.body.dataset.auditIframe=1</script>"` survives the real backend filter. In Chrome 155, the installed React 19.1.2 / react-markdown 9.1.0 / rehype-raw 7.0.0 stack sets the parent marker to 1. The frame has no sandbox. Direct script insertion was inert in this client-render test, inline onerror was removed, and javascript: links became empty hrefs; those protections do not stop srcdoc. Styles, remote frames/images and forms also survive. No production payload or live model injection was attempted. P1 reflects that model/cache delivery is a precondition; the rendering primitive itself is confirmed.

**Minimal fix:** Remove rehypeRaw from this renderer, matching the shared page. If HTML is indispensable, use an explicit sanitization schema rejecting frames, srcdoc, scripts, styles, forms and unapproved resource URLs. Address the shared-cache input boundary in SEC-02 as well.

**Offline regression/acceptance:** Render malicious commentary after the actual backend normalization in a browser fixture. Assert no iframe/form/style/script, no parent marker and no remote resource load. Test both fresh and cached-answer rendering.

### SEC-02 — Reader instructions and canonical verse requests share public cache identity

**P1 · Confirmed · Effort S · Area A**

**Likelihood:** Medium: a miss lets a reader influence the shared answer; actual model obedience remains untested.

**Impact:** A private question or injected instruction can alter content later served to unrelated readers.

**Evidence**

`backend/app.py:3004`:

```
USER QUERY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"{query}"

```

`backend/app.py:3648`:

```
def normalize_verse_query(query: str) -> str:
    """
    Normalize verse queries for better cache matching.
    Examples:
    - "2:3" -> "2:3"
    - "surah 2 verse 3" -> "2:3"
    - "Al-Baqarah 3" -> "2:3"
    - "2:3-5" -> "2:3-5"
    """
    query_lower = query.lower().strip()

    # Extract verse reference if present
    verse_ref = extract_verse_reference_enhanced(query)
    if verse_ref:
        surah, start_verse = verse_ref
        # Check if it's a range
        range_match = re.search(r'(\d+)[:\s]+(\d+)\s*[-–]\s*(\d+)', query)
        if range_match:
            return f"{surah}:{start_verse}-{range_match.group(3)}"
```

**Failure and reproduction/proof:** `2:255` and `2:255 extra instructions` produce the same Firestore cache key, while the complete second query is inserted into Gemini’s sole user-role prompt. A first cache-missing request can therefore write a query-specific answer into the public verse cache. Existing hits can also answer a different natural-language question with the first writer’s content. Hadith validation and canonical verse replacement restrict only part of the output; commentary, summary and other prose remain model-written. This confirms the boundary mismatch, not a particular live jailbreak.

**Minimal fix:** Pass only the validated canonical verse/range to the shared tafsir prompt and deterministic retrieval. If arbitrary questions remain supported, give them a separate, explicitly scoped cache identity and treat their text as data. Do not rely on another prompt instruction to fix a cache identity mismatch.

**Offline regression/acceptance:** Compare canonical and suffixed requests using the real parser, prompt and cache helpers. Reader text must either be absent from the shared prompt or have a distinct non-shared key. Stub Gemini to return a marker and prove another reader cannot retrieve it under the canonical request.

### OPS-01 — Neither Firestore database has scheduled backups or PITR

**P1 · Confirmed · Effort M · Area F**

**Likelihood:** Low-frequency operational event; recovery protection is absent now.

**Impact:** Deletion or corruption of private journals and progress can outlast the available recovery window.

**Evidence**

`backend/app.py:8001`:

```
            docs = user_ref.collection(sub).stream()
            for doc in docs:
                doc.reference.delete()
                count += 1
            deleted_counts[sub] = count
```

**Failure and reproduction/proof:** Read-only Cloud metadata returned empty backup schedules for `(default)` and `tafsir-db`, no backups in us-central1, `POINT_IN_TIME_RECOVERY_DISABLED`, `versionRetentionPeriod: 3600s`, and database delete protection disabled on both. Commands and results are in the appendix. This proves no managed scheduled backup/PITR in the inspected databases/region; external exports were not inventoried. Application deletion routes, including private-data erasure at app.py:7980, establish why recoverability matters.

**Minimal fix:** Configure owner-reviewed retention/backups and PITR for private data, enable database deletion protection, document restore ownership and recovery objectives, and exercise a restore into a disposable database. Keep the cache’s cheaper recovery policy separate from irreplaceable private notes.

**Offline regression/acceptance:** An offline configuration check can verify the desired database policies, but cannot prove recoverability. Acceptance also requires read-only metadata verification and a separately authorized restore drill; this audit performs neither mutations nor a restore.

### SEC-03 — Abuse controls do not cap paid work or public Firestore amplification

**P1 · Confirmed · Effort M · Area A**

**Likelihood:** Medium under intentional abuse; ordinary traffic is tiny.

**Impact:** Unexpected Vertex/Firestore spend, shared guest denial, and growing process memory.

**Evidence**

`backend/app.py:1404`:

```
def is_rate_limited(user_id, limit=150, window_hours=1):
    """Check if user is rate limited (150 requests per hour per user)"""
    now = datetime.now()
    window_start = now - timedelta(hours=window_hours)

    # Clean old entries
    USER_RATE_LIMITS[user_id] = [
        timestamp for timestamp in USER_RATE_LIMITS[user_id]
        if timestamp > window_start
    ]

    # Check limit
    if len(USER_RATE_LIMITS[user_id]) >= limit:
        return True

    # Add current request
    USER_RATE_LIMITS[user_id].append(now)
    return False





```

`backend/app.py:3885`:

```
        total_cached = len(cache_collection.limit(10000).get())

        # Get hit counts and sizes
        total_hits = 0
        total_size = 0
        total_tokens_saved = 0
        cache_by_persona = defaultdict(int)

        for doc in cache_collection.limit(500).stream():
```

`backend/app.py:6476`:

```
        ANALYTICS[query] += 1
```

**Failure and reproduction/proof:** Only tafsir, topics and share creation have application rate checks. The limiter is process-local; tafsir/share call its read-filter-append sequence without the topic route’s lock. Keys are never globally evicted, and ANALYTICS keeps every raw query variant. Public `/cache/lookup` bypasses generation limits and updates cache hit counters; `/cache/analytics` can read up to 10,000 + 500 + 10 documents per call; `/cache/popular` has no upper clamp. Any authenticated account can repeatedly call paid feedback or the suspended Iman APIs; clearing its digest cache enables regeneration. With one stable guest key and instance, 10 allowed tafsir requests/hour means up to 20 Vertex attempts/hour, 240 requests/480 attempts in 24 hours. Ten independent instance buckets multiply that to 100/200 per hour and 2,400/4,800 per day. These are conditional steady-state envelopes, not hard global ceilings: restarts, races and additional identities invalidate them. Topics shares the guest/UID bucket with tafsir and makes at most one lite call per allowed request; it does not add another ten. No application-wide daily/spend cutoff exists. Cloud Run max-instances limits concurrent capacity, not total spend. Exact production REMOTE_ADDR grouping is unverified (section 6).

**Minimal fix:** Protect operational cache analytics/popular routes with admin auth or cheap bounded aggregates; bound public lookup. Use durable per-identity quotas plus a small global generation budget, apply them to every paid route, and reserve quota atomically before the call. Gate suspended Iman generation until needed. Cap/expire process counters and normalize analytics keys. Establish the trusted proxy chain before deriving guest identities; do not blindly trust the leftmost X-Forwarded-For value.

**Offline regression/acceptance:** Offline fake-clock/concurrent quota tests must cover two instances, shared topic/tafsir budgets, paid feedback/Iman routes, counter expiry and public cache-route authorization/read counts. Stub outbound calls and assert budget exhaustion prevents them. Billing budgets/quota verification remains a cloud acceptance check.

### SEC-04 — Dependency audit finds vulnerable image caching and native-origin code

**P1 · Confirmed · Effort M · Area A**

**Likelihood:** Medium for a shipped iOS build following a crafted link; web exposure differs by advisory.

**Impact:** Same-origin/native-capability compromise on affected iOS builds; possible web DoS/cache integrity issues.

**Evidence**

`frontend/ios/App/CapApp-SPM/Package.swift:14`:

```
        .package(url: "https://github.com/ionic-team/capacitor-swift-pm.git", exact: "8.1.0"),
        .package(name: "CapacitorSplashScreen", path: "../../../node_modules/@capacitor/splash-screen"),
        .package(name: "CapacitorStatusBar", path: "../../../node_modules/@capacitor/status-bar")
```

`frontend/package.json:22`:

```
    "next": "^15.5.12",
    "react": "19.1.2",
    "react-dom": "19.1.2",
    "react-markdown": "^9.0.0",
    "rehype-raw": "^7.0.0",
```

`backend/requirements.txt:1`:

```
Flask==3.0.3
flask-cors==4.0.0
requests==2.32.3
google-auth==2.30.0
gunicorn==22.0.0
firebase-admin==6.5.0
cryptography==49.0.0
google-cloud-secret-manager==2.19.0
google-cloud-firestore==2.18.0
google-cloud-storage==2.16.0
```

**Failure and reproduction/proof:** npm reports 14 production dependency packages (5 critical, 8 high, 1 moderate). Capacitor iOS and the checked-in Swift package are 8.1.0, affected by the vendor’s internal HTTP proxy origin bypass; the model Markdown can supply relative links, which is the advisory’s delivery precondition. A physical-device exploit was not run; applicability of the exact remote-server URL configuration must be settled on a disposable native test build. The public next/image handler and writable image cache are present (Logo.tsx uses an optimized PNG); the image-cache growth advisory has a current code path. Server upgrade proxy handling is also present even without application-defined WebSocket code, so its advisory cannot be dismissed on that basis; Cloud Run ingress exploitability remains unverified. The appendix assesses every reported high/critical npm advisory, including several that lack a reachable call path here. In particular, the built Server Action manifest has zero actions and the installed handler rejects before decoding, so the Server Function advisories are not simply counted as exploitable because the app uses App Router. pip-audit reports 20 entries across five packages, deduplicating to 10 advisory identities, with no demonstrated remote exploit in the Flask application. This is not a blanket claim of web RCE.

**Minimal fix:** Update to vendor-patched compatible releases and lock the resulting graph in a dedicated dependency session. Re-sync and rebuild iOS, verifying its Swift pin as well as npm. Evaluate all advisory preconditions rather than running a blind audit fix. Obtain the deployed image dependency inventory because the Docker install process can drift (OPS-03).

**Offline regression/acceptance:** Repeat both audits on the final lock/requirements, run the existing suites/build and an isolated native navigation regression rejecting the internal interceptor path. The appendix provides applicability decisions and vendor links; no attack should be run against production.

### ERR-02 — A parsed JSON object is cached without checking the answer contract

**P1 · Confirmed · Effort M · Area D**

**Likelihood:** Medium with malformed, truncated or instruction-diverted model output.

**Impact:** A verse can acquire an incomplete answer that persists and is shared as a successful response.

**Evidence**

`backend/app.py:6924`:

```
                if final_json.get('metadata', {}).get('extraction_error'):
                    if attempt < max_retries - 1:
                        logger.warning(
                            "GEMINI_RETRY_MALFORMED verse=%s",
                            f"{surah}:{start_verse}" + (f"-{end_verse}" if end_verse != start_verse else ""),
                        )
                        continue
                    logger.error("Gemini returned malformed JSON; refusing to cache fallback response")
                    perf_metrics['stages']['post_processing'] = (time.time() - stage_start) * 1000
                    return tafsir_response({
                        "error": "AI returned a malformed response. Please try again."
                    }, 502)

```

`backend/app.py:9232`:

```
        if not digest_data:
            return jsonify({"error": "Could not parse digest response"}), 502

```

**Failure and reproduction/proof:** The real tafsir handler, executed through the existing offline fixture with Gemini returning `{"unrelated":"no commentary"}`, returns 200 and calls store_tafsir_cache once with no tafsir_explanations. Valid JSON is not a valid answer. Empty commentary can also result after source filtering. MAX_TOKENS is accepted, and JSON repair can turn a truncated prefix into a cacheable object. Iman digest/insight/correlation paths only check truthiness after the shared extractor, so its truthy extraction-error fallback can become cached empty fields. These are distinct from the fixed main-route rejection of the extraction_error fallback, which still passes its regression tests.

**Minimal fix:** Validate the minimal post-filter response contract and required field types before display/cache; reject incomplete/truncated answers using the existing two-attempt budget. Make every Iman model path explicitly reject extraction_error and invalid shape. Retain canonical verse replacement and grounded hadith processing.

**Offline regression/acceptance:** Stub model outputs with an unrelated object, wrong field types, empty explanations, partial MAX_TOKENS JSON, and the extractor fallback on each active paid path. Require a friendly 502 and zero cache writes. A valid no-hadith answer must remain valid.

### ERR-03 — Late account-bound fetches can display the previous reader’s data

**P1 · Confirmed · Effort M · Area D**

**Likelihood:** Low to medium: overlapping requests and an account switch on one browser are required.

**Impact:** Saved answers, annotations or a previous profile can appear in another account’s session.

**Evidence**

`frontend/app/saved/page.js:20`:

```
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        await Promise.all([fetchSaved(currentUser), fetchFolders(currentUser)]);
      }
      setIsLoading(false);
    });
    return () => unsubscribe();
  }, []);
```

`frontend/app/saved/page.js:44`:

```
        setSaved(data.saved || []);
      }
```

`frontend/app/page.js:97`:

```
  const fetchUserProfile = async (currentUser) => {
    if (!currentUser) return;
    try {
      const token = await currentUser.getIdToken();
      const response = await fetch(`${BACKEND_URL}/get_profile`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      reportBackendSuccess();
      if (!response.ok) throw new Error('Network error fetching profile');
      const data = await response.json();
      if (data?.is_new_user) {
        // New user — no profile yet, will proceed to onboarding
        return;
      }
      if (data?.level || data?.persona) {
        setUserProfile(data);
      }
    } catch (err) {
      if (err instanceof TypeError) reportBackendFailure();
      // No saved profile, will proceed to onboarding
```

**Failure and reproduction/proof:** Precise trace: account A starts a slow saved-answer request; auth changes to B; B’s request resolves; A’s request then resolves and unconditionally calls setSaved. The callback has no captured UID/current-UID check, abort or request generation guard. The same pattern exists in profile loading and other reader-data screens. Firestore server isolation is intact; this is client state crossing an authentication transition. Component unmount cleanup unsubscribes auth, but does not cancel an already running request. A two-minute check is the quoted callback and unconditional setter.

**Minimal fix:** Clear account-bound state immediately on every auth change, cancel outstanding reads, and accept results only when the initiating UID and request generation still match. Apply the same guard to profile loading. Keep the existing local-state/raw-fetch architecture.

**Offline regression/acceptance:** Use deferred mocked fetches: A starts, B starts, B resolves, A resolves. Assert only B’s profile/answers/notes are displayed, and signing out leaves no reader data. Also test getIdToken rejection and unmount.

### PRIV-01 — Production reflection encryption silently falls back to clear application fields

**P1 · Confirmed · Effort M · Area E**

**Likelihood:** Certain storage behavior; disclosure requires access to server-side records or their exports.

**Impact:** Sensitive reflections, highlights and Iman journal text are readable in Firestore document fields.

**Evidence**

`backend/app.py:246`:

```
def _get_user_fernet(uid: str) -> Optional[Fernet]:
    """Derive a per-user Fernet key from UID + server secret via HMAC-SHA256."""
    if not REFLECTION_ENCRYPTION_SECRET:
        return None
    # HMAC-SHA256 produces 32 bytes → base64-encode for Fernet (which needs 32 url-safe base64 bytes)
```

`backend/app.py:262`:

```
def _encrypt_text(text: str, uid: str) -> str:
    """Encrypt text for storage. Returns original text if encryption is not configured."""
    if not text:
        return text
    f = _get_user_fernet(uid)
    if not f:
        return text
    return f.encrypt(text.encode('utf-8')).decode('utf-8')


```

**Failure and reproduction/proof:** Cloud Run env-name inspection confirms REFLECTION_ENCRYPTION_SECRET is absent from revision 00273-dpr. The deployment script also omits it. The actual encrypt helper returns the original string in the offline probe. Annotation content/highlights and Iman fields call this helper, so newly written values are clear to the application/database reader. No private production record was read. This does not mean Google’s underlying disk encryption is disabled, nor that Firebase clients can read these records.

**Minimal fix:** Configure and preserve a dedicated Secret Manager key through deployment; make the intended production encryption policy explicit instead of silently degrading. Inventory plaintext fields and backfill with update preconditions, a format/key version and rollback plan. Preserve access to the key for recovery. Query context, tags, behavior values and feedback also need an explicit classification; merely setting this secret does not encrypt all personal data.

**Offline regression/acceptance:** Mock configured and missing keys, inspect serialized writes, and test legacy plaintext reads plus safe backfill/retry. Assert new protected fields never equal the input when production policy requires encryption. Do not test using real private reflections.

### PRIV-02 — Account deletion is absent and the existing Iman erasure misses two collections

**P1 · Confirmed · Effort L · Area E**

**Likelihood:** Certain for anyone requesting complete account erasure.

**Impact:** People cannot remove their full account; purported Iman deletion leaves derived private records.

**Evidence**

`frontend/app/page.js:9`:

```
  createUserWithEmailAndPassword,
```

`backend/app.py:7992`:

```
        subcollections = [
            "iman_config", "iman_daily_logs", "iman_baselines",
            "iman_trajectory", "iman_struggles", "iman_weekly_digests",
            "iman_daily_insights",
        ]

```

`backend/app.py:8525`:

```
                .collection("iman_correlation_narratives").document(today_str)
```

**Failure and reproduction/proof:** There is no account-deletion route, Firebase delete_user call or in-app deletion control. The only broad deletion API lists seven Iman subcollections but omits iman_correlation_narratives and iman_struggle_goals, both written elsewhere. The complete deletion inventory appears in the appendix. Shared content/cache original queries and feedback are outside users/{uid}, and shares currently have no owner UID for locating them. [Apple requires an in-app account-deletion initiation path for apps that support account creation](https://developer.apple.com/help/app-review/guideline-reference/5-1-1-account-deletion).

**Minimal fix:** Implement a reauthenticated, explicit deletion flow with an idempotent resumable backend job: enumerate all subcollections, handle feedback and attributable shared/query metadata, then remove Auth and browser account state. Include the two omitted Iman collections immediately. Define a transparent retention/anonymization policy for public scholarly snapshots and operational logs.

**Offline regression/acceptance:** Seed a Firestore emulator with every collection in the appendix, including nested descendants, and fake Firebase Auth. Interrupt/retry deletion; require no other user to be touched and no sensitive record to remain. Verify the visible in-app entry point. No production deletion is authorized here.

### OPS-02 — Deploy scripts can declare success while traffic still serves an older revision

**P1 · Confirmed · Effort M · Area F**

**Likelihood:** Medium whenever a no-traffic canary has pinned a revision, a documented recurring precondition.

**Impact:** A security/content fix can remain undeployed or a manual to-latest step can select the wrong canary.

**Evidence**

`deploy-backend.sh:46`:

```
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
```

`deploy-backend.sh:73`:

```
HEALTH_RESPONSE=$(curl -s "${SERVICE_URL}/health")
echo "Health check response: ${HEALTH_RESPONSE}"

```

**Failure and reproduction/proof:** The scripts deploy and then check the stable service URL, without proving that traffic reaches the built revision. AI.md and the top handoff document the October incident where the new revision got 0% and latestReadyRevisionName selected an older canary. Current read-only service metadata is safe: both services are 100% latest, with no canary tag in the traffic list. The latent script defect remains and the current health check would pass against the previous revision.

**Minimal fix:** Record the revision returned by deploy and verify its image digest/readiness and exact traffic assignment before reporting success. Preserve intentional no-traffic canaries. For a reviewed switch, use an explicit revision name and verify before normalizing latest; never infer a switch from an old service health response.

**Offline regression/acceptance:** Stub gcloud responses for latest traffic, pinned old traffic, and a retired new revision with another canary reported latestReady. The script must fail with a clear concrete diagnosis if its intended production revision has no traffic. No deploy is needed to review this script fix.

### LOG-02 — Named and slash ranges collide with single-verse cache documents

**P1 · Confirmed · Effort S · Area B**

**Likelihood:** Medium for supported non-picker formats; every collision is deterministic.

**Impact:** Readers receive a single-verse answer for a range, or a range for a later single-verse request.

**Evidence**

`backend/app.py:3664`:

```
        range_match = re.search(r'(\d+)[:\s]+(\d+)\s*[-–]\s*(\d+)', query)
        if range_match:
            return f"{surah}:{start_verse}-{range_match.group(3)}"
        return f"{surah}:{start_verse}"

```

**Failure and reproduction/proof:** Actual parser output: `Al-Baqarah 1-3` and `2/1-3` both extract range (2,1,3), but normalize_verse_query returns `2:1` for each. Their Firestore cache key equals the single-verse key. The main handler returns a cache hit before rebuilding canonical requested verses, so either writer can contaminate the other request shape. The same normalizer underlies lookup and share creation.

**Minimal fix:** Construct one cache query from the validated extracted surah/start/end tuple for every supported syntax; do not independently parse ranges with the narrower cache regex. Bump the pipeline/cache namespace and isolate old colliding documents.

**Offline regression/acceptance:** Table-test numeric/colon/slash/dot/named ranges and single verses through actual normalization, lookup and share helpers. Equal canonical ranges must have equal keys; a single verse and a multi-verse range must never collide.

### LOG-03 — Named verse shortcuts override explicit verses and invalid ranges degrade to singles

**P2 · Confirmed · Effort S · Area B**

**Likelihood:** Medium for named input; high certainty for reproduced inputs.

**Impact:** A reader’s explicit verse/range selection can be silently changed.

**Evidence**

`backend/app.py:1083`:

```
    # Strategy 1: Named verses
    for name, ref in NAMED_VERSES.items():
        if name in query_normalized:
            return ref
```

`backend/app.py:1241`:

```
    # Strategy 3: If no range found, check for single verse and return as range
    verse_ref = extract_verse_reference_enhanced(query)
    if verse_ref:
        surah, verse = verse_ref
        return (surah, verse, verse)

    return None
```

**Failure and reproduction/proof:** The real helpers parse `Al-Fatihah 7` as (1,1), because the substring named-verse shortcut fatiha runs before explicit surah/verse parsing. `2:280-999` and reversed `2:10-1` fail range validation and then fall through to the valid start verse. Numeric Arabic-Indic `٢:٢٥٥` works, and invalid surah 115 or verse zero are rejected. Mixed text containing a reference is accepted by design; ambiguity with multiple references is not diagnosed.

**Minimal fix:** Give explicit validated references precedence over named shortcuts. When range syntax is present, reject an invalid endpoint/order instead of silently returning a singleton. Reject or clarify ambiguous multiple references.

**Offline regression/acceptance:** Pure parser tests for explicit Al-Fatihah 7, named shortcuts alone, reversed/out-of-range endpoints, Arabic numerals and multiple references. Assert exact range or a validation result, never a silent fallback.

### LOG-04 — Cache fallback discards the requested persona and learning level

**P2 · Confirmed · Effort S · Area B**

**Likelihood:** High whenever a matching persona document is absent but the default exists.

**Impact:** A beginner/new revert or advanced learner receives another learning contract.

**Evidence**

`backend/app.py:3746`:

```
        # If no cache found with user profile, try with default profile as fallback
        if user_profile and any(user_profile.values()):
            logger.info("No cache found with user profile, trying default profile fallback...")
            default_profile = {
                'persona': 'practicing_muslim',
                'knowledge_level': 'intermediate',
                'learning_goal': 'balanced',
                'include_arabic': True
            }
            default_cache_info = get_firestore_cache_key(query, default_profile, approach)
            default_cache_key = default_cache_info['cache_key']

            if default_cache_key != cache_key:  # Only try if different
                logger.info("Looking for default cache with key: %s...", default_cache_key[:16])
                default_cache_ref = quran_db.collection('tafsir_cache').document(default_cache_key)
```

**Failure and reproduction/proof:** The helper retries practicing_muslim/intermediate/balanced for every nonempty profile. The offline fake Firestore probe requests curious_explorer/beginner, misses, and receives the practicing-Muslim marker. Fresh persona prompt contracts are therefore bypassed by normal cache hits. Missing signed-in profiles resolve to {}, also selecting the default; actual guest construction remains correctly curious_explorer/beginner.

**Minimal fix:** Require a full match on answer-affecting profile fields. Remove cross-persona fallback or constrain a documented migration fallback to truly equivalent profiles. Choose an explicit default for missing/partial signed-in profiles.

**Offline regression/acceptance:** Seed only a default-profile cache; requesting each different persona must miss and build its own contract. Cover missing/partial profiles and confirm repeated guest requests still use the guest key.

### LOG-05 — Cache lifecycle omits read-time expiry and pipeline identity in keys

**P2 · Confirmed · Effort S · Area B**

**Likelihood:** Certain on an expired-but-not-yet-deleted document or concurrent canary version.

**Impact:** Answers exceed 90 days; canaries overwrite production cache entries and force paid regeneration.

**Evidence**

`backend/app.py:3692`:

```
        'cache_key': hashlib.md5(f"{normalized_query}_{approach}_{json.dumps(profile_key, sort_keys=True)}".encode()).hexdigest()
```

`backend/app.py:3717`:

```
            cached_version = cache_data.get('version', '1.0')
            if cached_version != SCHOLARLY_PIPELINE_VERSION:
                logger.info(
                    "Cache STALE (version %s != %s) for key %s... — regenerating",
                    cached_version,
                    SCHOLARLY_PIPELINE_VERSION,
                    cache_key[:8],
                )
                return None

            # Increment hit count
```

`backend/app.py:6595`:

```
            if cache_key in RESPONSE_CACHE:
                perf_metrics['stages']['cache_check'] = (time.time() - stage_start) * 1000
                logger.info("Memory cache hit for query (approach: %s)", approach)
                logger.info(
                    "PERFORMANCE: Memory cache hit in %.0fms",
```

**Failure and reproduction/proof:** A fake current-version document with expires_at in 2000 is returned and its hit counter updated. Neither primary nor default Firestore reads compare expiry. Memory entries have no timestamp/expiry, so TTL deletion of the Firestore document can expose an indefinitely old memory fallback. Changing SCHOLARLY_PIPELINE_VERSION leaves the cache key unchanged; the documented canary overwrite is reproducible as key equality. The version read gate itself works and prevents cross-version serving.

**Minimal fix:** Include the pipeline version in both persistent and memory key namespaces and enforce expiry in each read path. Keep the existing Firestore TTL for physical cleanup. Use a bounded migration strategy that does not fall back across incompatible versions.

**Offline regression/acceptance:** Fake-clock tests: expired direct/default/memory hits miss; future entries hit; versions coexist without overwriting; both keys are stable for equivalent query/profile input.

### LOG-06 — Concurrent progress writes lose a studied verse

**P2 · Confirmed · Effort M · Area B**

**Likelihood:** Medium with two tabs or overlapping plan/search activity.

**Impact:** Exploration totals and badges omit real study activity.

**Evidence**

`backend/app.py:4414`:

```
        existing = set(explored.get(surah_key, []))
        new_verses = [v for v in verses if v not in existing]

        if not new_verses:
            return  # Already tracked

        updated_list = sorted(existing | set(new_verses))
        explored[surah_key] = updated_list

        # Count totals
        total = sum(len(v) for v in explored.values())
        total_surahs = len(explored)

        user_ref.set({
            "explored_verses": explored,
            "stats_cache": {
                "total_explored_verses": total,
                "total_explored_surahs": total_surahs,
            }
        }, merge=True)
    except Exception as e:
        print(f"WARNING: Failed to track explored verse: {e}")

```

**Failure and reproduction/proof:** Two actual _track_explored_verse calls read the same empty fake user snapshot, one for 2:1 and one for 2:2. With a barrier before writes, the final same-surah array contains only one verse and total_explored_verses is 1. merge=True does not atomically union arrays or recompute counters. Similar read-modify-write patterns occur in plans, collections and Iman heart-note arrays; the reproduced result here is the progress loss, not an active private-note deletion test.

**Minimal fix:** Use a Firestore transaction for the affected user map/counter update, or atomic ArrayUnion plus a consistent count strategy. Make plan/collection updates transactional too; preserve idempotency for repeated completed work.

**Offline regression/acceptance:** Run two requests against the same mocked/emulated snapshot and require both verses and an accurate total. Repeat each event and require no increment. Add the analogous overlapping array-update cases before changing Iman.

### LOG-07 — Reading-plan retries can rewind the current day and accept fractional days

**P2 · Confirmed · Effort S · Area B**

**Likelihood:** Medium for stale tab/retry; crafted fractional input is also accepted.

**Impact:** Plan navigation regresses; malformed progress can be saved before a 500 response.

**Evidence**

`backend/app.py:5333`:

```
            day_num = data.get("day")
            if not day_num or day_num < 1 or day_num > plan["duration_days"]:
                return jsonify({"error": "Invalid day number"}), 400

```

`backend/app.py:5354`:

```
            next_day = min(day_num + 1, plan["duration_days"])
            is_complete = len(completed) >= plan["duration_days"]

```

**Failure and reproduction/proof:** After completing days 1 and 2, current_day is 3. Reposting complete_day for day 1 leaves the completion set unchanged but unconditionally sets next_day/current_day to 2. An input day of 1.5 passes numeric range checks, is added to completed_days and persisted; indexing plan[days][day_num - 1] then raises because the index is not an integer. No transaction or operation id prevents these partial states.

**Minimal fix:** Require an integer day (excluding bool), keep repeated completions idempotent, and derive the next incomplete day from the completion set. Validate everything before a transactional write.

**Offline regression/acceptance:** Replay a completed earlier day, submit days out of order, and send fractional/string/bool values. A retry must not rewind or write; invalid inputs must return 400 with no side effects.

### LOG-08 — Several advertised badges cannot be earned through normal activity

**P2 · Confirmed · Effort S · Area B**

**Likelihood:** Certain after the relevant thresholds/preconditions.

**Impact:** Achievements remain missing despite qualifying study or reflection.

**Evidence**

`backend/app.py:4873`:

```
            ann_limit = 1001 if "reflect_500" not in earned else 51
            ann_query = users_db.collection("users").document(uid).collection("annotations").limit(ann_limit)
            annotation_count = sum(1 for _ in ann_query.stream())
```

`backend/app.py:4840`:

```
    "reflect_1000": {"name": "Spiritual Journalist", "description": "Wrote 1,000 reflections", "icon": "book", "category": "reflection", "tier": "diamond", "threshold": 1000},
```

`backend/app.py:4920`:

```
        daily_verse_count = data.get("daily_verse_count", 0)

        # First week check
        created_at = data.get("created_at")
        first_week_active = False
        if created_at:
```

**Failure and reproduction/proof:** Once reflect_500 exists, annotation counting is capped at 51, so subsequent growth cannot satisfy reflect_1000. Repository-wide references show daily_verse_count and _comeback_detected are read but never updated; set_profile does not establish the created_at needed for first_week. These are persisted badge definitions with missing event inputs, not a proposal to redesign motivation.

**Minimal fix:** Use a consistent reflection count/aggregate, and either wire the explicit daily-study/comeback/creation events or stop advertising unreachable badges until they exist. Do not infer spirituality from journal content.

**Offline regression/acceptance:** Progress from 499 through 500 to 1,000 reflections and verify the final award. Simulate daily study, a qualifying return gap, and a newly created profile using fake dates; each displayed badge must have a reachable event path.

### LOG-09 — Iman struggle goals always subtract naive and aware timestamps

**P2 · Confirmed · Effort S · Area B**

**Likelihood:** Certain for an existing declared struggle with a valid timestamp.

**Impact:** The live goals API returns 500 for normal records; the UI is currently suspended.

**Evidence**

`backend/app.py:9712`:

```
            start = datetime.fromisoformat(declared_at.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, AttributeError):
            start = now
        days_active = max(0, (now - start).days)
        current_phase = min(days_active // 7, 3)
```

**Failure and reproduction/proof:** The route makes start naive with replace(tzinfo=None), while now is timezone-aware UTC, then subtracts them. The offline expression raises `can’t subtract offset-naive and offset-aware datetimes`. Weekly-goal lc parsed with strptime is also naive before subtraction. Normal declaration writes an aware ISO timestamp, so this is a regular path, not malformed stored data.

**Minimal fix:** Keep all arithmetic aware in UTC, assigning UTC only for legacy naive timestamps, and compare dates where only calendar days matter. Do not mix stripping timezone information with aware now.

**Offline regression/acceptance:** Invoke the extracted route with normal declaration/completion records and fake UTC now. Cover aware, legacy naive and invalid dates plus the weekly reset path; require 200 and the expected phase.

### LOG-10 — Iman trajectory recomputation freezes on the oldest 90 logs

**P2 · Confirmed · Effort S · Area B**

**Likelihood:** Certain after more than 90 distinct daily documents.

**Impact:** New activity stops influencing trajectory/baselines and can produce misleading guidance.

**Evidence**

`backend/app.py:8139`:

```
        # Fetch all logs for trajectory computation (last 90 days)
        logs_query = (
            users_db.collection("users").document(uid)
            .collection("iman_daily_logs")
            .order_by("date")
            .limit(90)
        )
        all_logs = [doc.to_dict() for doc in logs_query.stream()]
```

**Failure and reproduction/proof:** The query orders date ascending and applies limit(90), with no cutoff. Day 91 still selects days 1–90, despite its comment saying last 90 days. Other Iman readers use descending order or date cutoffs, so derived screens can disagree. This remains reachable by direct authenticated API calls despite suspension of the UI.

**Minimal fix:** Fetch the latest 90 valid daily records in descending order, then reverse for chronological pure logic, or apply an explicit bounded date window. Reject unintended future dates consistently.

**Offline regression/acceptance:** Seed 91 dated fake logs with a materially different newest value. Recompute and assert the oldest is excluded and newest included, with all pure trajectory functions receiving chronological input.

### LOG-11 — A reflection can retain the share link of the previously studied verse

**P2 · Confirmed · Effort S · Area B**

**Likelihood:** High after creating a reflection on one answer and moving to another in the same app mount.

**Impact:** A saved reflection opens an unrelated answer instead of its original context.

**Evidence**

`frontend/app/page.js:1446`:

```
    if (currentShareId) return currentShareId;

    // Prevent duplicate requests
    if (pendingShareRequest.current) {
      return pendingShareRequest.current;
    }
```

`frontend/app/components/AnnotationForm.jsx:96`:

```
      if (shareId) body.share_id = shareId;
```

**Failure and reproduction/proof:** currentShareId is initialized once and set after share creation, but has no reset on query/result change. Trace: create reflection/share A; study B; open reflection; ensureShareId returns A immediately; AnnotationForm persists A’s ID alongside B’s query context. A pending share can likewise resolve after changing answers. A repository search finds no setCurrentShareId(null) after initialization.

**Minimal fix:** Associate share state and its pending promise with the canonical answer/profile identity. Clear it on a new answer and discard a late result belonging to an old answer.

**Offline regression/acceptance:** Mock shares A and B in sequence, including a deferred A response. The B annotation must carry B’s share ID or no ID, never A’s.

### PERF-01 — Badge checks read up to 1,001 full annotations repeatedly on the study path

**P2 · Confirmed · Effort M · Area C**

**Likelihood:** High for established signed-in readers with many notes.

**Impact:** Slow cache hits, repeated private-document reads and unnecessary Firestore billing.

**Evidence**

`backend/app.py:4874`:

```
            ann_query = users_db.collection("users").document(uid).collection("annotations").limit(ann_limit)
            annotation_count = sum(1 for _ in ann_query.stream())
        except Exception:
```

`frontend/app/page.js:1389`:

```
        // Update streak on successful search
        updateStreak();
        // Save to query history
```

**Failure and reproduction/proof:** Every authenticated tafsir hit/fresh response invokes _check_and_award_badges; the UI then POSTs /streak, which invokes it again, including when the day was already recorded only if its path advances (the same-day short circuit skips the second check). Each applicable check streams up to 1,001 full annotations to count them, plus user document reads. This work is synchronous despite _track_explored_verse describing itself as fire-and-forget. The read fanout can dominate a normally ~126 ms Firestore cache hit for a mature reader.

**Minimal fix:** Use a maintained or aggregate annotation count, skip badge families whose thresholds cannot change, and avoid redundant checks for one study event. Keep badge work bounded and preserve idempotent progress.

**Offline regression/acceptance:** Count fake Firestore reads with 0, 500 and 1,000 annotations on a cached study and first/same-day streak update. The response should require a small constant read count and still award the correct boundary badges.

### PERF-02 — Reader list APIs fetch unbounded full documents and catalog pages repeat verse reads

**P2 · Confirmed · Effort M · Area C**

**Likelihood:** Medium as a reader’s saved corpus grows; public catalog fanout occurs on every detail fetch.

**Impact:** Growing memory/response size and latency; a list refresh can download every saved full answer.

**Evidence**

`backend/app.py:5478`:

```
            query = saved_ref.order_by('savedAt', direction='DESCENDING')

        saved = []
        for doc in query.stream():
            data = doc.to_dict()
```

`backend/app.py:5994`:

```
        for doc in annotations_ref.stream():
            data = doc.to_dict()
            # Decrypt content before searching
            decrypted_content = _decrypt_text(data.get('content', ''), uid)
            content_lower = decrypted_content.lower()
```

`backend/app.py:5165`:

```
    for day in plan["days"]:
        surah, verse_num = day["verse"]
        verse_data = get_verse_from_firestore(surah, verse_num)
        surah_name = QURAN_METADATA.get(surah, {}).get("name", f"Surah {surah}")
```

**Failure and reproduction/proof:** Saved answers and folders stream all owned records; the answer list includes fullResponse even though its cards need metadata. Annotation search/tags scan all notes. Iman heart-note history accepts unbounded days; some date-cutoff queries also lack a document limit and allow future logs. Reading-plan/collection detail fetches a whole surah document once per verse/day instead of once per distinct surah. These are real code-path costs, not load-test measurements or a claim of a currently slow small account.

**Minimal fix:** Paginate saved/history/search metadata, fetch a full saved answer on demand, use aggregates/projections for counts/tags where useful, and bound Iman ranges. Memoize or batch canonical verse reads by surah within catalog responses.

**Offline regression/acceptance:** Seed large fake collections and count documents/bytes/reads. Page size must cap the response, cursors must preserve ordering, and a plan must read each distinct surah document at most once per request.

### PERF-03 — Cloud Run accepts 80 concurrent requests for eight Gunicorn threads

**P2 · Confirmed · Effort S · Area C**

**Likelihood:** Low at current traffic; medium during a burst or abuse.

**Impact:** Requests can wait behind long Gemini calls and exceed the intentional 180-second frontend deadline.

**Evidence**

`backend/Dockerfile:13`:

```
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 300 app:app"]
```

**Failure and reproduction/proof:** Cloud Run metadata sets containerConcurrency=80, while the backend has one worker and eight threads. At a simplified uniform 27-second generation duration, 80 requests assigned to one instance form ten service batches, with the last finishing around 270 seconds before other I/O. Autoscaling may distribute a burst, so this is a capacity mismatch argument, not a measured production tail. The observed memory p99 near 13% of 2 GiB does not show a current memory bottleneck.

**Minimal fix:** Set and validate Cloud Run concurrency in relation to the existing eight-thread capacity, then measure the target with mocked slow generation in an isolated environment. Keep min-instances=0 and the 180-second reader timeout as the recorded decisions; changing them is not this finding.

**Offline regression/acceptance:** Use a fake slow upstream and local concurrency instrumentation without cloud clients or paid calls. Verify accepted work begins within the chosen queue budget; inspect deployment configuration to ensure the intended concurrency is explicit.

### ERR-01 — Firestore outages are reported as missing verses or empty successful content

**P2 · Confirmed · Effort S · Area D**

**Likelihood:** Medium during billing, IAM or transient dependency failure.

**Impact:** Readers are told valid scripture is absent; process-only health can stay healthy.

**Evidence**

`backend/app.py:1359`:

```
        print(f"Error fetching verse {surah_num}:{verse_num} from Firestore: {e}")
    return None
```

`backend/app.py:4289`:

```
        arabic_text = verse_data.get("arabic", "") if verse_data else ""
        english_text = verse_data.get("english", "") if verse_data else ""
```

`backend/app.py:7035`:

```
def health_check_enhanced():
    """Health check with system status"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "metadata_entries": len(VERSE_METADATA),
        "cache_size": len(RESPONSE_CACHE),
```

**Failure and reproduction/proof:** get_verse_from_firestore catches all exceptions and returns None. /verse and /tafsir then return 404 for a valid reference, while /daily-verse returns 200 with empty Arabic/English. /health checks process dictionaries only, not the failing dependency. This is the still-present error-classification mechanism behind the historical billing outage, not a claim that billing is currently broken. The PermissionDenied alert is enabled, but it does not correct the reader-facing response.

**Minimal fix:** Distinguish an absent canonical record from a dependency error and return a retryable 503 with generic reader copy for the latter. Make readiness limitations explicit, or maintain a cheap last-known dependency/readiness signal without a paid generation.

**Offline regression/acceptance:** Mock PermissionDenied, deadline exceeded and a genuinely missing document. The first two must not become 404/empty 200; the genuine absence can. Test the corresponding frontend recovery copy.

### ERR-04 — An aborted search can clear a newer request’s timer and loading state

**P2 · Confirmed · Effort S · Area D**

**Likelihood:** Medium with Cancel followed quickly by a new selection.

**Impact:** A new search loses its timeout/loading indicator, and stale results can replace current work.

**Evidence**

`frontend/app/page.js:1268`:

```
  const handleCancelSearch = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsTafsirLoading(false);
    setVersePreview(null);
    setError('');
    // Keep query intact - don't clear it!
  };

```

`frontend/app/page.js:1412`:

```
      // Clear the timeout when request completes
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
        searchTimeoutRef.current = null;
      }
      setIsTafsirLoading(false);
    }
  };
```

**Failure and reproduction/proof:** Search A is aborted; before its rejection/finally runs, search B replaces the shared controller and timeout refs. A’s finally clears searchTimeoutRef.current (now B’s timer) and sets loading false. The fetch itself also uses the shared controller after awaiting getIdToken, so A can accidentally attach to B’s controller. The preview path has an identity guard; the main response/finally path does not. An auth transition/unmount likewise has no search cleanup.

**Minimal fix:** Capture a controller, timer and request generation in each invocation. Only the current request may update UI state or clear its own timer. Cancel on unmount/account change and guard token resolution before issuing fetch.

**Offline regression/acceptance:** Use deferred token/fetch promises: cancel A, start B, then settle A. B must retain its own timeout/loading state and only B may render. Test timeout, cancel and unmount separately.

### ERR-05 — Firebase reCAPTCHA initialization runs during server import and drops a rejection

**P2 · Confirmed · Effort S · Area D**

**Likelihood:** Certain build-side I/O; the error depends on network/configuration.

**Impact:** Noisy builds and unhandled promise failures; future build behavior can turn the warning into failure.

**Evidence**

`frontend/app/lib/firebase.js:11`:

```
const auth = getAuth(app);
initializeRecaptchaConfig(auth);

```

**Failure and reproduction/proof:** The local Next 15.5.12 build completes all 14 pages but logs auth/network-request-failed from server chunk 434. With all fetches stubbed before loading the installed Firebase modules, an enabled synthetic reCAPTCHA config makes initializeRecaptchaConfig resolve, then its internal unawaited verifier emits `ReferenceError: window is not defined` at @firebase/auth/dist/node-esm/totp-13844f55.js:3371. This reproduces the documented Cloud Build symptom even on Node 24 and identifies a concrete source, without querying production Auth. The ordinary build’s SDK configuration lookup was network-blocked; it was not a sign-in or account-creation test.

**Minimal fix:** Initialize reCAPTCHA only in the browser lifecycle and handle initialization/verifier failure. Keep the shared Firebase app/auth singleton, but avoid calling browser verification at module import on the server.

**Offline regression/acceptance:** Import/build with an enabled mocked reCAPTCHA config and no window; require no unhandled rejection and no network call during server rendering. Verify browser sign-in still initializes the protection.

### ERR-06 — Saved/history load failures still look like genuinely empty accounts

**P2 · Confirmed · Effort S · Area D**

**Likelihood:** Medium on expiry, 5xx or connection failure.

**Impact:** Readers see “no saved work” rather than an actionable failure or sign-in recovery.

**Evidence**

`frontend/app/saved/page.js:44`:

```
        setSaved(data.saved || []);
      }
    } catch (err) {
      if (err instanceof TypeError) reportBackendFailure();
      // Fetch failed — non-critical
    }
  };
```

`frontend/app/history/page.js:41`:

```
      // History fetch failed — non-critical
    }
```

**Failure and reproduction/proof:** fetchSaved only handles res.ok; a 401/500 leaves the initial empty list with no load error, and its catch calls the health reporter only for TypeError. History behaves similarly. reportBackendSuccess is invoked before checking HTTP success in several callers, so HTTP outages can even clear the global backend warning. The new ErrorNotice is used for deletion errors on these screens, not the initial-load failure. Route ErrorBoundary cannot catch async fetch errors that are swallowed.

**Minimal fix:** Add explicit load error state and retry/re-auth actions to reader-data lists, using the new errors helper. Mark backend success only for the intended successful/known reachable states, and distinguish empty data from unavailable data.

**Offline regression/acceptance:** Mock 401, 500, non-JSON and network failures for saved/history/folders. Require a visible calm message and recovery action, with an empty-state message only after a successful empty response.

### SEC-05 — 69 route handlers return raw exception strings to API callers

**P2 · Confirmed · Effort S · Area A**

**Likelihood:** High when malformed input or a dependency error reaches a broad catch.

**Impact:** Internal project/resource names, query/index details, paths or upstream exception text can leak.

**Evidence**

`backend/app.py:2240`:

```
            return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401
```

`backend/app.py:3970`:

```
        print(f"ERROR in /get_profile: {type(e).__name__} - {e}")
        return jsonify({"error": str(e)}), 500
```

**Failure and reproduction/proof:** AST inventory counts 69 explicit route handlers containing an error: str(e) response, including the nested annotation GET. Auth-required adds details: str(e) on token verification failure. Examples of potentially exposed exceptions are Firestore index-precondition messages with project/index URLs, billing/IAM resource errors, Python type errors and Google API diagnostics. Exact production message contents were not elicited. The shipped UI calls profile, streak/progress, plans, history/saved, annotation, share and feedback routes in that set. lib/errors.js now hides 5xx bodies from those readers; direct API callers still receive them. The main tafsir generic catch itself does not disclose str(e).

**Minimal fix:** Return stable error codes and generic messages at the API boundary while logging diagnostic context server-side with a request correlation ID. Explicitly validate request types so caller errors become 400, not internal exceptions. Do not weaken the new frontend error mapping.

**Offline regression/acceptance:** Inject a synthetic exception carrying a fake project/path/token marker into representative public and protected routes and auth verification. Assert the HTTP body never contains the marker and the server log retains a safe correlation trail.

### SEC-06 — The live frontend can be framed and has no CSP containment

**P2 · Confirmed · Effort S · Area A**

**Likelihood:** Medium if an attacker hosts a deceptive framing page.

**Impact:** Clickjacking of account/reflection controls; no browser containment for the raw-HTML defect.

**Evidence**

`frontend/next.config.mjs:4`:

```
  async headers() {
    return [
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
        ],
      },
    ];
  },
};

```

**Failure and reproduction/proof:** The one live homepage GET returns neither CSP/frame-ancestors nor X-Frame-Options, HSTS or Referrer-Policy. Backend health also lacks those headers. The Next configuration defines only Service-Worker-Allowed for sw.js. Frame embedding therefore has no application-supplied prohibition; no framing attack was performed. Missing HSTS is recorded as a header fact, not proof of an HTTP downgrade exploit on the HTTPS-only run.app deployment.

**Minimal fix:** Set a tested frontend frame-ancestors policy (and compatible X-Frame-Options), a CSP that constrains script/frame/form/resource sources, and an explicit Referrer-Policy. Handle Next/Firebase/reCAPTCHA requirements deliberately; removing raw HTML is still the primary SEC-01 fix. Add transport headers where appropriate to the serving domain.

**Offline regression/acceptance:** Inspect local response headers and render a harmless cross-origin framing fixture. Assert it is blocked, while normal script loading, Firebase verification and expected external links still work.

### PRIV-03 — Reader text and feedback identifiers enter unredacted operational logs

**P2 · Confirmed · Effort S · Area E**

**Likelihood:** High whenever the corresponding route logs a request/feedback item.

**Impact:** Personal queries or feedback persist outside reflection encryption and user-deletion paths.

**Evidence**

`backend/app.py:6611`:

```
        print(f"[TAFSIR] query={query} approach={approach}")
```

`backend/app.py:9948`:

```
        print(f"[FEEDBACK] {feedback_type} from {uid[:8]}...: {message[:80]}")
```

`backend/app.py:10059`:

```
                print(f"[FEEDBACK] Summary (logged):\n{email_body}")
        else:
```

**Failure and reproduction/proof:** Tafsir logs the complete accepted raw query, which can contain a private concern after a verse. Feedback logs a UID prefix plus the first 80 characters; SMTP failure/unconfigured summary code logs the full email summary, whose items include email. No private log records were downloaded for this audit; filtered REQUEST_METRIC/GEMINI_USAGE lines contain canonical verse references and counts. Reflection encryption does not cover these sinks, and there is no account-log erasure integration or documented log retention in the repo.

**Minimal fix:** Log canonical verse, status and correlation IDs instead of raw reader text. Redact feedback body/email from routine and failure logs. Set/document operational retention and access controls, including what can and cannot be erased.

**Offline regression/acceptance:** Pass synthetic email/unique text markers through tafsir/feedback and mocked SMTP failure. Capture logs and assert no private marker appears, while status and useful diagnostics remain.

### PRIV-04 — No Tadabbur privacy notice explains collected data and model processing

**P2 · Confirmed · Effort M · Area E**

**Likelihood:** Certain for a reader looking for a first-party policy.

**Impact:** People cannot understand retention, deletion or how reflections/feedback are sent to services; iOS submission is blocked.

**Evidence**

`frontend/app/components/RecaptchaAttribution.jsx:5`:

```
      <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Privacy Policy</a>
      {' '}and{' '}
      <a href="https://policies.google.com/terms" target="_blank" rel="noopener noreferrer">Terms of Service</a>
```

**Failure and reproduction/proof:** Route/file inventory has no privacy policy page or first-party policy link; the visible privacy link belongs to Google’s reCAPTCHA terms. The backend sends journal heart notes into Gemini digest/insight prompts and feedback into Gemini (and optionally GitHub/SMTP); private data also persists in Firebase and logs. [Apple’s privacy guideline requires an accessible privacy policy](https://developer.apple.com/app-store/review/guidelines/#privacy). This is a concrete missing product disclosure, not a claim about any particular jurisdiction’s legal liability.

**Minimal fix:** Publish an accurate first-party privacy policy linked from auth/settings and the app listing, covering the appendix inventory, model processing, optional feedback destinations, retention, public shares and deletion/contact routes. Verify operational settings before making promises.

**Offline regression/acceptance:** Check first-party policy links and every material collection/processing destination against the inventory. Require a reachable policy page without authentication and clear account-deletion instructions.

### OPS-03 — Frontend build/runtime dependency installation is not reproducible

**P2 · Confirmed · Effort S · Area F**

**Likelihood:** Medium on a new dependency release or clean image build.

**Impact:** The deployed runtime can differ from the audited lockfile and the Next version that built its artifacts.

**Evidence**

`frontend/Dockerfile:5`:

```
RUN npm install
COPY . .
RUN npm run build

```

`frontend/Dockerfile:15`:

```
RUN npm install next react react-dom --production
```

**Failure and reproduction/proof:** Builder uses npm install instead of a frozen clean install; runtime then explicitly installs next/react/react-dom again from the copied manifest/lock. That command can change the dependency graph rather than reproduce the audited graph. Backend direct dependencies are pinned, but transitive packages and both base image tags also resolve over time. No deployed container SBOM was fetched, so advisory reachability in the exact running image is not inferred from local package-lock alone. The normal gcloud upload manifests exclude local secrets/settings; direct docker builds have weaker ignore coverage.

**Minimal fix:** Use npm ci with the reviewed lockfile in both stages (or copy the necessary reviewed runtime artifacts/dependencies), ensure the runtime Next version matches the builder, and record the deployed image digest/dependency inventory. Add direct-Docker ignore coverage for local env/venv files without changing the approved deployment architecture.

**Offline regression/acceptance:** Build twice from a clean disposable context with the same manifests and compare installed versions/lock checksums; compare builder/runtime Next/React versions. Confirm both gcloud and direct-Docker contexts omit local settings and credential files.

### MAINT-01 — Passing tests leave the main trust and ownership boundaries unexercised

**P2 · Confirmed · Effort M · Area G**

**Likelihood:** High confidence from suite inventory and reproduced escapes.

**Impact:** Auth/cache/share regressions can pass the complete offline suite.

**Evidence**

`backend/tests/test_tafsir_retry.py:51`:

```
        node.decorator_list = []

```

`backend/tests/test_tafsir_retry.py:80`:

```
        "get_cached_tafsir_response": lambda *args: None,
        "get_verse_from_firestore": lambda *args: verse,
        "get_verse_metadata_direct": lambda *args, **kwargs: [
```

**Failure and reproduction/proof:** 457 backend tests and 11 frontend tests pass. They cover valuable pure logic, topic contracts, hadith labels and bounded retries. The principal tafsir route fixture strips decorators and mocks cache/parsing/grounding; it cannot detect IDOR/auth failures, the real cache normalization/TTL/fallback defects or the HTML trust boundary. No offline route test exercises actual share creation/GET ownership assumptions or required/admin/debug/cron denial boundaries. The topic harness does retain optional auth and test its authenticated/guest happy paths and shared rate bucket; that useful coverage does not cover the missing denial cases. Most Iman tests target pure services, explaining why the live goals route’s timezone error remained green. This finding concerns named boundary gaps tied to reproduced failures, not a request to rewrite the monolith.

**Minimal fix:** Add small isolated boundary fixtures retaining real decorators, parsers, cache and share helpers with fake clients. Add the browser/raw-HTML and account-transition regressions specified above. Preserve the existing pure suite and live/paid harness separation.

**Offline regression/acceptance:** Require offline tests that fail on SEC-01, LOG-01/02/05, ERR-02/03 and auth/IDOR denials before implementing their fixes. Never import production-initializing app.py or run the paid golden harness as part of offline tests.

## 5. Verified safe

Evidence below is scoped to the audited commit and October 17 observations. It is not an assertion that a later deploy has the same configuration.

- **Backend tenant isolation:** app.py:5549,5930,5965,8231,8936,9304,9561,9772 derive document parents from request.user[uid]. Every personal ID route stays under users/{verified UID}; supplying another reader’s annotation/search/log/goal ID cannot change that parent. The annotation-by-verse GET applies firebase_auth_required inside handle_get (5596), so its missing outer decorator is not an auth bypass.
- **Token verification:** app.py:2230–2259 delegates signature/project/expiry verification to Firebase Admin. Required auth fails without a token; optional auth degrades invalid tokens to a guest only on public endpoints. This does not claim revocation checking: check_revoked is not requested.
- **Admin/debug gates:** app.py:2261–2297 fails closed when ADMIN_SECRET is unset, compares UTF-8 bytes with hmac.compare_digest, and hides debug routes unless DEBUG_ROUTES=1. No admin secret was opened and no live admin/debug requests were made.
- **Feedback cron:** app.py:9976–9989 refuses an unset cron secret and compares a provided secret in constant time. The deployed env-name list lacks FEEDBACK_CRON_SECRET, so this currently disables the endpoint rather than leaving it public.
- **Share creation boundary:** app.py:7378–7417 snapshots only a current-version server cache response and ignores a caller-provided response. It has a separate 20/hour process bucket; no personal annotation text is read by share creation. Old share GET/version behavior remains a lead, not a blanket safety claim.
- **Closed topic vocabulary:** services/topic_service.py:83–106 rejects extra fields, unknown names, duplicated topics, boolean/non-finite/out-of-range confidence and model-supplied references; canonical refs are attached only from the editorial index. Route tests cover malicious/invalid output and failures.
- **Memory response capacity:** app.py:7002–7007 inserts under cache_lock and trims the first 200 keys whenever RESPONSE_CACHE exceeds 1,000 entries. It is bounded by count, unlike USER_RATE_LIMITS/ANALYTICS key retention; per-entry age is still LOG-05.
- **Bounded topic cache:** app.py:6260–6283 locks access, expires entries and limits them to 256. It stores normalized learner text in process memory, not Firestore. Fallback returns eight zero-confidence browse suggestions and makes no tafsir generation.
- **Guest profile repair remains intact:** app.py:6481–6488 creates curious_explorer/beginner; the later profile refresh at 6734 runs only if user_id is truthy. This is not the August guest-profile overwrite regression. Cross-persona fallback is separately LOG-04.
- **Requested scripture is canonical on fresh responses:** app.py:1803–1883 builds the main verses array from Firestore verse data and replaces model translations/Arabic before fresh display/cache. Wrong query/cache identity is separately reported; this finding does not accuse the model of controlling the canonical fresh verse fields.
- **Range budget is consistent:** app.py:6427–6465 and 4245–4261 both use compute_max_end_verse with ABSOLUTE_MAX_VERSES=10. The public GET for 2:1 returned maxEnd=6; SurahVersePicker.jsx:404–459 consumes that endpoint. Six is the dynamic budget, ten the safety cap. The old help copy still says five; that copy is stale, not an actual picker/backend budget disagreement.
- **Hadith safeguards that still work:** services/hadith_validation.py drops absent wording/non-object items, does not validate a collection from a name appearing only after a quote, and accepts the new hyphen variants. All existing integrity tests pass; LOG-01 targets fields/partial wording those tests do not exercise.
- **Malformed extraction fallback is rejected on main tafsir:** app.py:6912–6925 checks metadata.extraction_error, and the actual offline handler tests prove two malformed attempts return 502 with zero caches written. Non-object output is rejected; a single-element object array is unwrapped. ERR-02 concerns missing schema validation after that protection.
- **Main model retry budget:** app.py:6810–6877 shares two total attempts between timeout, 429, 503 and malformed output, with explicit timeout=120. The tests prove no third attempt and a 242-second maximum sum of these network timeouts plus backoff. Credential refresh, SDK operations, thread queueing and post-processing are additional time, so 242 is not an end-to-end guarantee.
- **No invented “missing timeout” finding:** Every direct Vertex requests.post has an explicit timeout (20/120/20/15/60/30/15 by topic/tafsir/correlation/guidance/digest/insight/feedback paths; debug is gated). GitHub posting has timeout=10. Firestore, GCS and credential refresh have SDK default timeouts/retries rather than explicit per-request deadlines; their worst-case composition was not measured.
- **Main/cache recommendations:** app.py:6531–6560 rebuilds deterministic recommendations and source spelling at serve time on the tafsir cache branches. Cache-hit progress/badge callbacks still execute, unlike the resolved August omission. Share GET does not re-run that path and is treated separately.
- **New error mapping:** frontend/app/lib/errors.js never returns arbitrary err.message, ignores raw 5xx bodies, maps Firebase codes, preserves only constrained 4xx explanations, and gives the same bad-credential/reset result for unknown accounts. All seven error-helper tests pass. This is a display boundary, not a replacement for server redaction.
- **ErrorNotice and render recovery:** ErrorNotice.jsx renders message as a React text child, forwards its ref and has an optional button; it has no raw HTML sink. app/error.js covers route render failures; ErrorBoundary.jsx hides diagnostics in production. Async failures remain the caller’s responsibility (ERR-03/04/06).
- **Other rendering and links:** The only two ReactMarkdown render sites are main commentary and shared/[id]/page.js:167; the shared site does not enable raw HTML. There is no dangerouslySetInnerHTML in app code. History/saved/reflection route queries use encodeURIComponent or validated numeric refs; nav links are static. Button innerHTML assignments use constants or the button’s original static markup. Markdown still allows ordinary external links/images, so this is not a claim that all model URLs are trustworthy.
- **Service worker:** public/sw.js:29–33 returns from fetch without respondWith or CacheStorage operations. It does not cache authenticated responses. App search persistence uses sessionStorage for 30 minutes; onboarding state is keyed by UID. Browser Auth persistence remains Firebase-managed.
- **CORS:** app.py:108–118 allows only localhost:3000 and the stable production frontend origin, uses explicit methods/headers and exposes only the timing/cache headers. No wildcard or dead Vercel origin remains. CORS is not treated as an authorization or cost barrier.
- **Public Firebase config:** frontend/app/lib/config.js contains web API/project/app identifiers, not an Admin service-account key. App code imports Firebase Auth, not client Firestore/Storage writes. Repository firestore.rules denies all client access; deployed rules were not accessible for comparison.
- **Cloud Build secret exclusions:** gcloud meta list-files-for-upload from backend and frontend returned 628 and 94 files respectively, with zero .env*, venv, run-local.sh, golden-results, node_modules/.next or secret paths in the filtered manifests. git ls-files found no tracked .env*, secret/*, secrets/*, .pem/.key/.p12 files. No secret contents or git history secret scan was performed; direct-Docker contexts remain OPS-03.
- **Existing indexes:** Read-only Firestore index metadata shows READY composite indexes for saved_searches(folder ASC, savedAt DESC) and annotations(surah ASC, verse ASC, createdAt DESC), matching the shipped folder and verse/batch annotation query shapes. There is no evidence for a missing-index finding on those paths.
- **Startup fail-fast floor:** app.py:1690–1697 raises if no chunks load, and initialize_firebase re-raises critical initialization failures. GCS source downloads use seven threads for eight files; startup then precomputes verse budgets. Individual file failures can still degrade partial corpus coverage; no all-empty “healthy startup” defect is asserted.
- **Current capacity and traffic:** Read-only metadata shows backend 2 CPU/2 GiB, timeout 300, max 10, one worker/eight threads; frontend 1 CPU/1 GiB. Both October 17 traffic lists are 100% latest. Memory daily p99 was about 10–13%, not evidence of current OOM pressure. Min-instances=0 and the deliberate monolith/local-state design are respected.
- **Monitoring exists:** The enabled October 17 policies cover >5 backend 5xx in 300 seconds, PermissionDenied logging, and multi-region /health failure for 900 seconds. The uptime check uses /health, 900-second period and 60-second timeout. Notification channel delivery was not tested; /health does not prove end-to-end dependencies.
- **Useful tests and build:** The 457-test backend suite includes pure scholarly routing, persona contracts, token budgeting, hadith validation, text cleanup, topic strictness and bounded retries. Frontend tests cover error copy and topic UI. The 14-page build succeeds; the server-import warning is documented in ERR-05. No change of architecture is needed to preserve these strengths.

## 6. Leads you could not verify

| Lead | What is known | Exactly what settles it |
|---|---|---|
| Cloud Run REMOTE_ADDR and guest sharing | Gunicorn receives the socket peer; app.py never wraps ProxyFix or reads a trusted forwarded chain. Flask documents that a proxied app needs explicit proxy handling. A fixed proxy peer would merge guest buckets; scaling/restarts already split buckets. No spoofable-header bypass is proven because this code ignores X-Forwarded-For. | Read an existing access log that actually records Gunicorn peer/forwarded values and correlate a permitted health request, or instrument an isolated staging revision and make two harmless GETs from different clients. Establish trusted hop count before any ProxyFix change. Do not infer Flask remote_addr from Cloud Logging httpRequest.remoteIp: they are different observations. [Flask proxy guidance](https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/) supports the boundary distinction, not a particular Cloud Run IP. |
| Deployed Firestore rules, both databases | backend/firestore.rules is deny-all and app clients use Auth only. The rules releases metadata GET returned 403. | With rules read access, GET the Firebase Rules releases, locate the default and named-database releases, fetch their referenced rulesets and compare source/hash with backend/firestore.rules. No client attack or write is needed. |
| Provider-wide budgets/quotas | The app has no global generation/spend cutoff. gcloud billing budgets list failed because billingbudgets.googleapis.com is disabled for the querying project. | Use the billing console/authorized read API to inspect budgets and automation, and read Vertex/Firestore quota overrides and actual expenditure. Do not enable an API or change a budget merely to complete this audit. A notification budget alone is not a spend stop. |
| Exact deployed dependency graph | Local lockfile/requirements audit is complete; the Docker install process can resolve a different runtime graph. | Read an existing image SBOM or export the installed package manifests from the already built image in a disposable, network-blocked environment and compare versions/digests. No production endpoint attack is necessary. |
| Native-origin advisory in this remote-URL shell | npm and checked-in Swift both pin affected Capacitor 8.1.0; default top-level external navigation is handed to the system browser, no wildcard allowNavigation is configured, and cleartext is false. None of that proves the internal proxy path safe. | On a disposable iOS simulator/device build, verify a synthetic allowed-link/internal-interceptor case with no real account, then re-sync a patched native runtime and confirm it is blocked. Also inspect subframe navigation and native bridge access. This audit did not run cap sync or open/sign an iOS build. |
| Next upgrade-proxy SSRF and uncertain RSC/cache advisory preconditions at Cloud Run ingress | The vendor’s self-hosted Node upgrade branch exists in the audited dependency. It does not require an app-defined WebSocket endpoint. No exploit request was sent. App Router is present, but Server Actions are absent. | Reproduce vendor cases only on a disposable local container with every outbound destination replaced by loopback/stubs; separately inspect Cloud Run ingress normalization in a staging service. Classify each advisory using the matrix below and the exact image graph. |
| Old public shares and saved snapshots after a content-integrity fix | create_share stores pipeline_version, but GET /share/<id> serves its snapshot without a version gate or hadith revalidation; saved fullResponse is also independent of the current shared cache. | Inventory snapshot versions through metadata-only reads, then review specifically outdated public religious content in a controlled offline export. Decide whether to revoke/rebuild affected snapshots. Do not GET production shares as a supposedly pure read: it increments view_count. |
| Actual private record encryption/backfill and retention | Missing encryption configuration proves new helper writes are clear application fields. No user records were read, and no log retention or historic export inventory was fetched. | Use synthetic records or an owner-approved minimal administrative inventory to classify old formats, then inspect retention settings and exports. Validate a migration on disposable data before proposing it for real journals. |
| Streak timezone contract | Streak days are UTC (app.py:4341–4342); the UI formats dates locally and profiles do not store a timezone. Same-UTC-day repeats are idempotent. | Product owner chooses UTC versus reader-local day semantics. An offline clock test at 00:00 UTC/19:00 Chicago in October settles whether implementation matches that chosen contract. This audit does not call an undocumented local-time promise a confirmed defect. |
| Partial GCS source loss and startup/tail deadlines | Individual downloads can fail while other chunks let startup succeed. SDK calls use defaults/retries; credentials are refreshed per generation. | In an isolated mocked startup, fail one required source segment and inspect readiness/coverage; inspect installed SDK deadline defaults and capture staged timing under a fake slow upstream. No production object removal, load test or paid generation is needed. |
| External backups, alert delivery and regional failover | No managed backups/PITR were found in the two regional DBs; alerts exist and deployment is single-region. | Inventory pre-existing export jobs/buckets without reading private payloads, review alert channel verification/history, and execute an authorized disposable restore/failover exercise. Absence of an external export is not assumed from the managed-backup result. |

## 7. Proposed fix sessions

Each unit is a reviewable implementation branch. Owner approval for any cloud mutation, content invalidation or native distribution belongs to its fix/deploy session; this audit makes none. The original monolith, raw fetch/local state, deterministic retrieval, min-instances=0 and 180-second frontend abort remain design constraints.

| Order / branch | Findings and files | Acceptance criteria | Deploy needed |
|---|---|---|---|
| 1. `codex/audit-content-boundaries` | LOG-01/02/03/04/05, SEC-01/02, ERR-02; backend/app.py, services/hadith_validation.py, existing parser/cache/hadith tests; frontend/app/page.js | No unverified attribution or partial quote survives; no executable model HTML; canonical query/range/profile/version/expiry contracts hold; incomplete model JSON never caches; use the existing retry budget. Bump the scholarly pipeline and prepare a reviewed old snapshot/cache policy. | Backend + frontend |
| 2. `codex/audit-abuse-dependencies` | SEC-03/04/05/06, OPS-03; app.py gates/quotas/errors, requirements.txt, package manifests/lock, Dockerfiles/ignore files, next.config.mjs, iOS native pin/config | Bound all paid/public expensive work; redact API errors; lock and triage patched dependencies; reviewed security headers; builder/runtime match; verify native interceptor fix before distribution. Offline authorization, quota and URL regressions pass. | Backend + frontend; separate iOS rebuild |
| 3. `codex/audit-private-data-recovery` | PRIV-01/02/03/04, OPS-01; app.py encryption/deletion/logging, deploy-backend.sh, settings/auth/privacy UI, operations runbook/config | Synthetic protected writes encrypt; complete resumable deletion covers the inventory and the two missed Iman collections; no private markers in logs; first-party policy exists; owner-reviewed key/retention/backups/PITR and a disposable restore drill are documented. | Backend + frontend + separately approved cloud configuration |
| 4. `codex/audit-client-resilience` | ERR-01/03/04/05/06, LOG-11; app.py dependency error boundary; frontend/lib/firebase.js, page.js, saved/history/annotations readers, existing ErrorNotice/helper | Late A-account results never appear for B; cancel/restart cannot clear B’s timer; no server reCAPTCHA side effect; failed lists have retry/re-auth UI; reflection shares track the current answer; outages are not missing scripture. | Backend + frontend |
| 5. `codex/audit-progress-and-reads` | LOG-06/07/08/09/10, PERF-01/02/03; app.py progress/plan/badge/Iman routes, frontend list fetches, deploy-backend.sh concurrency | Transaction/idempotency tests preserve concurrent progress; invalid/replayed plan days cannot corrupt/rewind; reachable badges; aware date math; latest 90 logs; bounded metadata pagination/read counts; queue budget validated with a fake upstream. Suspended Iman routes remain gated until their acceptance checks pass. | Backend + frontend |
| 6. `codex/audit-deploy-verification` | OPS-02, MAINT-01; deployment scripts, focused offline boundary harnesses, AI.md/HANDOFF operational instructions | Mocked pinned/retired/canary traffic cases cannot report success incorrectly; intended revision/image/traffic is checked explicitly; retain real auth/cache/share boundaries in tests. No monolith rewrite, live golden calls or automatic production switch. | None for scripts/tests; apply procedure at next approved deployment |

**Release recommendation:** prioritize the P0 attribution bypass and the executable-render/shared-input boundaries before another routine content release. Fixing an emergency security problem should not wait for the whole table. P1 backup/encryption/erasure/abuse/client-account/deploy issues each need an owned session. No App Store submission until the affected native runtime, account deletion and privacy policy are resolved. No evidence here requires reversing the recorded min-instance or frontend-abort decisions.

## 8. Appendix

### Scope, dates and execution boundaries

- Requested filename/date is retained. Repository, tool runs and cloud/public observations below were collected on October 17, 2026; report completion was resumed on October 20. Baseline stayed `7a0f3f15f26f447a0878339211ce61d9ca590447` and source files were unchanged. Dependency feeds are an October 17 snapshot; several primary advisory descriptions were rechecked October 20. Cloud state was not silently re-dated as current.
- Orientation followed the requested order: git pull (already current), AI.md, top five HANDOFF session entries, prior audit, then quality review. No AGENTS.md was found at the repository or parent levels. No agents were spawned. No skill was necessary for a Markdown/code audit.
- No application, dependency, rules, deployment or runtime setting was edited. Only this report and the new HANDOFF log entry are committed. Generated build/test files stayed ignored; scratch fixtures/audit environments were under /tmp.
- No secret file, Secret Manager payload or private production document was opened. Existing CLI authentication was used internally for authorized metadata GETs; no credential value is saved in this report.
- Exactly three explicit production public GETs: frontend `/`, backend `/health`, backend `/range-limit?surah=2&start=1`. No `/tafsir`, `/cache/*`, `/debug/*`, user-data API, share GET, production Auth attempt, email/issue creation, gcloud mutation, corpus mutation, deploy, load test or paid golden harness was invoked. The allowed Next build made a failing SDK reCAPTCHA configuration lookup during prerender; ERR-05 records that side effect. Synthetic renderer/SSR probes used local content/stubbed SDK responses.

### Route inventory — all 84 explicit Flask handlers

`U` = Firebase required, guest 401, signed-in reader’s own UID subtree only; another reader’s record ID cannot select its parent. `O` = optional Firebase on public functionality, guest allowed and signed-in profile used. `P` = public, guest/signed-in have the same public/static access. `A` = admin secret required, ordinary reader credentials do not authorize it; unset configuration 503. `D` = debug gate plus admin secret, normally 404. `C` = cron secret checked inside the handler, unset 503/wrong 403. `U+domain` additionally requires configured ADMIN_DOMAIN email suffix. No personal route accepts a caller-supplied UID.

Limits are per process and precede cache hits. `shared 10/150 h` means the same guest/UID bucket for topics and tafsir; `share 20 h` is separate. `—` means no application rate limit, not that the endpoint is cost-free. HEAD is implicit for GET and Flask provides automatic OPTIONS; its implicit static-file route is not an additional application handler and no app static payload was audited. Body shape/size/type validation is incomplete where noted; there is no global MAX_CONTENT_LENGTH.

| Method | Path (app.py definition line) | Auth / guest and other-reader reach | Rate | Input validation / state access |
|---|---|---|---|---|
| GET | `/suggestions` (3320) | O | — | Normalizes approach against a small vocabulary; profile from verified UID; static suggestion bank. |
| GET | `/analytics` (3374) | U+domain | — | ADMIN_DOMAIN must be configured and match email suffix; process aggregates contain raw query keys. |
| POST | `/cache/lookup` (3396) | P | — | Nonempty stripped query; caller supplies arbitrary profile/approach; no length/schema cap; public cache response plus hit-counter update. |
| POST | `/cache/store` (3439) | A | — | Requires nonempty query and response; administrative arbitrary cache document write. |
| GET | `/cache/analytics` (3468) | P | — | No parameters; up to 10,000 + 500 + 10 document reads. |
| GET | `/cache/popular` (3486) | P | — | Integer limit defaults 20 without upper/lower clamp; optional persona filter. |
| POST | `/cache/prewarm` (3523) | A | — | Administrative query/profile list; uses existing generation/cache path; no public access. |
| POST | `/cache/invalidate` (3575) | A | — | Administrative invalidation type/confirm/filter checks; can delete all cache documents. |
| POST | `/export/<format_type>` (3933) | U | — | Format allowlist markdown/json and nonempty response_data; user-supplied export only, no other-user fetch. |
| GET | `/get_profile` (3961) | U | — | No input; users/{UID} profile only. |
| POST | `/set_profile` (3979) | U | — | Persona/goal/knowledge enums, legacy level/focus/verbosity enums; first_name trimmed to 30; partial/empty profiles permitted. |
| GET | `/personas` (4106) | P | — | Static persona definitions. |
| GET | `/range-limit` (4223) | P | — | Integer surah/start, canonical bounds; dynamic budget plus hard 10 cap; fallback response on exceptions. |
| GET | `/daily-verse` (4276) | P | — | No input; deterministic UTC date pool and canonical Firestore lookup; may return empty text after lookup failure. |
| GET | `/streak` (4313) | U | — | No input; own stored streak. |
| POST | `/streak` (4337) | U | — | No body; UTC-day comparison, sequential same-day short circuit; own read/merge write and badges. |
| GET | `/progress` (4440) | U | — | No input; own explored map and derived totals. |
| GET | `/collections` (4668) | P | — | Static catalog metadata. |
| GET | `/collections/<collection_id>` (4685) | P | — | Static collection ID must exist; canonical verse lookup per listed entry. |
| GET | `/collections/<collection_id>/progress` (4716) | U | — | Static collection ID; own map. |
| GET | `/collections/progress` (4742) | U | — | Own map combined with static catalog. |
| POST | `/collections/<collection_id>/progress` (4770) | U | — | Static collection ID + nonempty verse_key; no membership/type check on that key; own map merge. |
| GET | `/badges` (5003) | U | — | Own earned map combined with static definitions. |
| GET | `/reading-plans` (5141) | P | — | Static plan catalog. |
| GET | `/reading-plans/<plan_id>` (5158) | P | — | Static plan ID must exist; canonical text per day. |
| GET | `/reading-plans/active` (5193) | U | — | Own map with legacy migration in response; static catalog lookup. |
| GET | `/reading-plans/<plan_id>/progress` (5248) | U | — | Plan ID selects only own active-plan map; static metadata if known. |
| POST | `/reading-plans/<plan_id>/progress` (5296) | U | — | Static plan ID/action; numeric day range but no integer type; own map then progress/badge side effects. |
| GET | `/query-history` (5394) | U | — | Integer limit capped at 200, no positive floor; own ordered subcollection. |
| POST | `/query-history` (5432) | U | — | Nonempty query only; no length/enum/schema cap for history payload; own new doc. |
| GET | `/saved-searches` (5466) | U | — | Optional folder; own unbounded ordered stream including fullResponse. |
| POST | `/saved-searches` (5508) | U | — | Nonempty query only; caller metadata/fullResponse stored only in own new doc; no validation as server-generated content. |
| DELETE | `/saved-searches/<search_id>` (5549) | U | — | ID is resolved under own saved_searches; delete is idempotent even if another UID has that ID. |
| GET | `/saved-searches/folders` (5565) | U | — | Own unbounded saved-search stream and counts. |
| GET | `/annotations/verse/<path:surah>/<verse>` (5593) | U | — | Nested required auth; numeric/name surah and verse format/bounds; query under own annotations. |
| GET | `/annotations/verses` (5683) | U | — | Required integer surah/from/to, ordered endpoints; span check permits 21 inclusive verses despite “20” message; own query. |
| GET | `/annotations/user` (5748) | U | — | Limit capped at 500, no positive floor; optional tag/type applied after limited own stream. |
| POST | `/annotations` (5823) | U | — | Nonempty content; verse bounds or section/highlight fields depending on type; enums/lengths/tags not fully validated; encrypt helper then own doc. |
| PUT | `/annotations/<annotation_id>` (5930) | U | — | Own doc existence; editable fields selected explicitly; lengths/types/tag enum not validated. |
| DELETE | `/annotations/<annotation_id>` (5965) | U | — | ID under own annotations only; idempotent delete. |
| GET | `/annotations/search` (5981) | U | — | Nonempty q or tag; scans/decrypts own notes; no pagination. |
| GET | `/annotations/tags` (6033) | U | — | Scans own annotations; no pagination. |
| GET | `/verse/<int:surah>/<int:verse>` (6054) | P | — | Typed URL integers plus canonical surah/verse bounds; public source text. |
| GET | `/metadata-types` (6074) | P | — | Static type metadata. |
| GET | `/metadata/<int:surah>/<int:verse>` (6174) | P | — | Canonical bounds and metadata type enum; optional source filter; public corpus only. |
| POST | `/topics/resolve` (6240) | O | shared 10/150 h | JSON object with nonblank string text <=500; strict closed output schema and static verse refs; bounded 256-entry cache. |
| POST | `/tafsir` (6290) | O | shared 10/150 h | Nonempty query <=500, approach normalized; reference/range/dynamic budget checks; JSON/string types incomplete; optional profile, shared cache and study side effects. |
| GET | `/health` (7035) | P | — | No input; process metadata only; no live dependency check. |
| GET | `/debug/range-map` (7060) | D | — | Gate then corpus/budget diagnostics. |
| GET | `/debug/test/<path:query>` (7076) | D | — | Gate then path query parsed into diagnostics and paid generation; full debug trace is not public. |
| GET | `/debug/verse-metadata/<surah>/<verse>` (7284) | D | — | Gate; surah name/number and verse parsing/lookup diagnostics. |
| POST | `/share` (7347) | O | share 20 h | Nonempty string-coerced query; approach normalized; cache current-version lookup; no arbitrary response body accepted; public snapshot write. |
| GET | `/share/<share_id>` (7429) | P | — | Public share ID lookup; no owner/version gate; increments view_count, so GET is not write-free. |
| GET | `/names` (7671) | P | — | Optional name/catalog query filters; local/public catalog, no personal record lookup. |
| POST | `/iman/setup` (7711) | U | — | Behavior cap/minimum and helper validation; known struggle IDs; own config and optional struggle records. |
| GET | `/iman/config` (7802) | U | — | Own config and active struggles; static categories/behaviors. |
| PUT | `/iman/config` (7858) | U | — | Nonempty behavior ID list, known IDs, cap and existing setup; own config update. |
| GET | `/iman/catalog` (7926) | U | — | Static behavior/struggle catalog; auth still required. |
| DELETE | `/iman/data` (7980) | U | — | Exact DELETE_ALL_IMAN_DATA confirmation; own seven subcollections only; omits two written Iman collections. |
| POST | `/iman/clear-digest-cache` (8022) | U | — | No body validation needed; deletes own insight/digest docs without rate limit. |
| POST | `/iman/log` (8041) | U | — | Date format, behavior values and heart note/state helpers; permits arbitrary date age/future, missing heart_notes defaults to []; own writes/recompute/invalidation. |
| GET | `/iman/log/<date_str>` (8231) | U | — | Date string used as own document ID, no calendar validation; decrypted note/reflection fields. |
| GET | `/iman/logs` (8262) | U | — | Optional lexicographic from/to filters; ascending limit 90; heart note text redacted but other own fields returned. |
| GET | `/iman/trajectory` (8299) | U | — | Own trajectory/config and date-filtered logs; no explicit query limit. |
| POST | `/iman/heart-note` (8349) | U | — | Type/text validated by helper; today UTC; own read/append/write array. |
| GET | `/iman/heart-state/<state_id>/response` (8405) | U | — | Known static state ID; scholarly pointers only, UID scoped logging. |
| GET | `/iman/heart-patterns` (8450) | U | — | Own config, latest 30 own logs; pure pattern functions. |
| GET | `/iman/correlations` (8487) | U | — | Own config/logs; daily cache under UID; may generate paid narrative on GET and update shown-correlations. |
| GET | `/iman/safeguards/status` (8611) | U | — | Own logs/config/trajectory; static/pure safeguard processing. |
| POST | `/iman/struggle` (8736) | U | — | Known struggle ID; own declared record; paid summary helper and optional config behavior additions. |
| GET | `/iman/struggles` (8857) | U | — | Own declared struggles + latest 30 logs; known static struggle catalog. |
| PUT | `/iman/struggle/<struggle_id>` (8936) | U | — | Known struggle ID and own doc existence; action defaults resolve but lacks strict action enum. |
| GET | `/iman/struggle/<struggle_id>/guidance` (8974) | U | — | Known struggle ID and own declaration required; cached or paid summary on GET. |
| POST | `/iman/digest/generate` (9046) | U | — | Monday UTC/minimum four recent logs; optional week_start/week_end and parsed week; own cached or paid digest. Date range is not fully constrained. |
| GET | `/iman/digest/latest` (9279) | U | — | Own latest digest, decrypted fields. |
| GET | `/iman/digest/<week_id>` (9304) | U | — | week_id selects own digest only; no format validation. |
| GET | `/iman/daily-insight/<date_str>` (9372) | U | — | Calendar date validation and own log existence; cached or paid generation on GET. |
| PUT | `/iman/heart-note/<date_str>/<int:index>` (9561) | U | — | Today UTC only; own log/index bounds; note-type/text validation; rewrites array. |
| DELETE | `/iman/heart-note/<date_str>/<int:index>` (9601) | U | — | Today UTC only; own log/index bounds; rewrites array. |
| GET | `/iman/heart-notes` (9632) | U | — | Integer days without upper clamp; optional type/q; own cutoff stream/decryption. |
| GET | `/iman/struggle/<struggle_id>/goals` (9686) | U | — | Known struggle, own existing unresolved declaration; naive/aware date failure before normal response. |
| POST | `/iman/struggle/<struggle_id>/goal/complete` (9772) | U | — | Known struggle and nonempty goal_id; no catalog-membership/declaration check for goal_id; own completion map only. |
| POST | `/feedback` (9914) | U | — | Known feedback type and string message 1–2000; paid enrichment; global feedback doc tagged with verified UID/email; optional issue/email integrations. |
| POST | `/feedback/daily-summary` (9969) | C | — | Constant-time cron-secret check; last-24h feedback; optional SMTP, full-text logging fallback. |

**Ownership conclusion:** static plan/collection/state IDs reference public catalogs; private progress/struggles/logs/digests/heart-note indexes are always resolved under the token UID. Public share IDs intentionally identify public snapshots. No backend endpoint was found that uses a reader-supplied UID to read/write another reader’s private record. Client account-transition races (ERR-03) are a separate trust boundary. The Iman APIs remain live and authenticated despite their UI being suspended; GET correlations/guidance/daily-insight can perform paid work and writes.

### Personal data, retention and deletion inventory

This is a code-derived inventory, not a dump of production records. Locations are Firebase project tafsir-simplified-6b262 unless stated otherwise. “No retention” means no application TTL/purge mechanism found; it does not describe uninspected provider backups/log settings.

| Location | Data / processing | Retention found | Complete deletion action |
|---|---|---|---|
| Firebase Auth | UID, email/password identity, display name and auth/session metadata; browser Firebase persistence | Until account deletion/provider policy; no app deletion flow | Reauthenticate, revoke sessions, delete Auth identity, clear UID-bound browser state |
| `(default)/users/{uid}` | First name/profile/persona/learning goal, explored verse map/stats, streak dates/counts, badges, collection and active-plan maps | No application expiry | Delete document after processing all descendants; document deletion alone does not recursively delete them |
| `users/{uid}/query_history/*` | Raw queries, approach/persona, success flag, timestamps | Read limit 200 is not storage retention | Delete all pages of records |
| `users/{uid}/saved_searches/*` | Query, folder/title/snippet, full answer snapshot, timestamps | No TTL | Delete all records, not just current folder/page |
| `users/{uid}/annotations/*` | Verse/section/general/highlight reflections, content, highlighted text, tags, context, linked verses/share IDs, timestamps/isPrivate | No TTL; individual delete exists; encrypt helper currently identity in production | Delete all records, including general/highlight items lacking a verse |
| `users/{uid}/iman_config/*` | Tracked behaviors, setup state, shown correlations | No TTL | Recursive delete |
| `users/{uid}/iman_daily_logs/*` | Date, worship/behavior values, heart state, heart notes, struggle reflections | Limit(90) is a read limit, not storage deletion | Delete every date and any descendants |
| `users/{uid}/iman_baselines/*`, `iman_trajectory/*` | Derived scores/baselines/history | No TTL | Delete both |
| `users/{uid}/iman_struggles/*` | Declared/resolved struggles, guidance/summary, dates | No TTL | Delete all records |
| `users/{uid}/iman_weekly_digests/*`, `iman_daily_insights/*` | Model-written private summaries/selected verse and context summaries; heart-note text sent to Vertex when generating | No TTL | Delete both; clarify provider processing retention in policy |
| `users/{uid}/iman_correlation_narratives/*` | Derived private narrative/key insight | No TTL; missed by /iman/data | Include explicitly in Iman and account erasure |
| `users/{uid}/iman_struggle_goals/*` | Goal IDs and completion-date arrays | No TTL; missed by /iman/data | Include explicitly in Iman and account erasure |
| `(default)/feedback/*` | Verified UID/email, raw feedback, enriched title/body/labels, optional issue URL | No TTL | Query by UID, delete/anonymize under the disclosed policy; consider already exported copies |
| `tafsir-db/tafsir_cache/*` | Shared answer, profile dimensions, original raw query, normalized reference, model/pipeline metadata | expires_at +90d and TTL recorded in AI.md; reader checks are LOG-05 | Shared scholarly answer can be retained only under a defined policy; remove private raw query text, and track provenance if removal is promised |
| `tafsir-db/popular_queries/*` | Canonical query/persona/count/times | No TTL | Usually aggregate/public scholarship, but classify before promising erasure |
| `tafsir-db/shared_content/*` | Public original query and immutable answer snapshot, version/date/view count | No TTL/revocation route; no creator UID | Add provenance if attributable erasure/revocation is promised; define retained anonymous scholarly snapshots |
| `tafsir-db/quran_texts/*`, GCS source bucket | Public canonical scripture/classical source material | Corpus lifetime | Not personal data; no user erasure needed |
| Cloud Logging, infrastructure project | Raw tafsir query, feedback text/UID prefix/summary emails, canonical usage metrics | Log-bucket retention not inspected | Redact at source; document operational retention/access and any erasure limits |
| Optional GitHub/SMTP integrations | Feedback is sent to Vertex, optional enriched issues to configured repo, summaries to email | Production env list has no feedback token/SMTP/cron settings; external historic copies not inspected | Define export/retention/removal behavior before enabling, and disclose it |
| Browser state | Firebase Auth IndexedDB/local storage; onboarding UID state; 30-minute sessionStorage answer/query | Auth/provider; onboarding no expiry; answer 30-minute application age check | Clear account-bound state on sign-out/deletion and prevent late async repopulation |

No in-app Plus/payment implementation or entitlement enforcement was identified in the audited routes; “accounts” here means Firebase email/password accounts. External billing/subscription records, if any, were not available and must be added before a deletion promise covers them.

### Exact offline commands, versions and outputs

Version observations on October 17:

```text
system python3: Python 3.14.7
backend/venv/bin/python: Python 3.11.16
backend/venv pytest: 9.1.1
node: v24.19.0
npm: 11.17.0
/tmp/tadabbur-audit-venv/bin/python: Python 3.14.7
pip-audit: 2.10.1
Google Cloud SDK: 581.0.0
Chrome: 155.0.8059.80
installed frontend: next 15.5.12, react/react-dom 19.1.2,
react-markdown 9.1.0, rehype-raw 7.0.0
```

```sh
git pull
git merge-base --is-ancestor 2271020 HEAD
backend/venv/bin/python -m pytest backend/tests -q
node --test frontend/tests/*.test.*
(cd frontend && npm run build > /tmp/tadabbur-build.log 2>&1)
(cd frontend && npm audit --omit=dev --json > /tmp/tadabbur-npm-audit.json)
python3 -m venv /tmp/tadabbur-audit-venv
/tmp/tadabbur-audit-venv/bin/python -m pip install pip-audit
/tmp/tadabbur-audit-venv/bin/python -m pip_audit -r backend/requirements.txt   --format json --output /tmp/tadabbur-pip-audit.json
```

No requirements were installed into the repository venv for the audit; pip-audit’s resolver/audit environment was outside it. Its resolution on Python 3.14 is not a production container SBOM for Python 3.11. Both dependency scans queried advisory services. The first npm attempt hit restricted-network ENOTFOUND; the permitted rerun succeeded and exited 1 because advisories were found. The initial git pull was filesystem-blocked, then the approved retry returned “Already up to date.” A later optional GitHub advisory metadata command did not execute because approval review timed out; primary vendor web pages supplied the relevant checks instead.

```text
pytest: 457 passed in 2.28s; exit 0
node --test: 11 tests, 11 pass, 0 fail/cancelled/skipped; exit 0
Next build: compiled; all 14/14 pages generated; exit 0
  emitted FirebaseError auth/network-request-failed from server chunk 434
  / route: 118 kB, First Load JS 303 kB; shared JS 102 kB
npm audit: 14 affected production packages
  info 0, low 0, moderate 1, high 8, critical 5; exit 1
pip-audit: Found 20 known vulnerabilities in 5 packages; exit 1
  duplicate aliases/advisory records reduce to 10 unique identities below
```

The build’s 303 kB first-load JS is measured, not automatically a defect at this traffic level. page.js is 3,478 lines and app.py 10,074 at the baseline. The results subtree re-renders as its parent’s local state changes; no CPU profile demonstrates that it dominates the ~27-second generation time. The local build does not prove Node 20 image behavior, but the independent stubbed Firebase probe establishes the window-access source.

### Dependency findings and per-advisory reachability

The npm metadata contains advisories of differing severities under each package’s maximum severity. The matrix includes **every individual high/critical advisory reported by npm**, without treating build-only transitive dependencies as remotely exposed services. Advisory links point to the record carrying its precise range/fix information. “No app path found” is scoped to this code and audited graph; “Suspected” requires the indicated isolated runtime check. No audit fix or dependency update was run.

| Package / actual affected lock nodes | npm maximum | Present code path / limitation |
|---|---|---|
| @capacitor/ios 8.1.0 | critical | Affected iOS/Swift runtime 8.1.0; links from model Markdown provide a delivery surface. Exact remote-URL shell interception needs disposable native verification. |
| @grpc/grpc-js 1.9.15 | high | Transitive Firebase Node capability; app uses browser Auth only and runs no gRPC server or untrusted peer. No app path to the listed server/peer handling found. |
| @protobufjs/utf8 1.1.0 | moderate | Transitive serialization; no user-selected descriptor/schema or direct decoder in app code. |
| @xmldom/xmldom 0.8.11 | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| glob/node_modules/brace-expansion 5.0.2 | high | Actual vulnerable node is glob/node_modules/brace-expansion 5.0.2, not the root 1.1.12. CLI filesystem patterns, not reader-controlled HTTP input. |
| glob/node_modules/minimatch 10.2.0 | high | Actual vulnerable node is glob/node_modules/minimatch 10.2.0, not root 3.1.2. CLI/local patterns; no HTTP pattern interface. |
| nanoid 3.3.11 | high | No direct app call; transitive fixed-size generation. No reader-controlled size/custom alphabet path found. |
| next 15.5.12 | critical | Built-in public server/image optimizer and App Router present; no Server Actions, middleware, rewrites, i18n, custom server, Cache Components or CSP nonces configured. See individual cases. |
| postcss 8.4.31 | high | Build-time app CSS, no reader CSS compiler/source-map parser. User-controlled raw style tags are the separate SEC-01 sink, not PostCSS compilation. |
| protobufjs 7.5.4 | critical | No client Firestore import, schema upload or direct protobuf reflection/codegen path. Browser Auth does not accept user-created protobuf descriptors. |
| sharp 0.34.3 | high | next/image optimizes the fixed local PNG logo. No remotePatterns or AVIF upload/source found; untrusted decoder inputs not demonstrated. Image-cache resource growth is separate. |
| source-map-js 1.2.1 | high | Build tooling consumes trusted generated/local maps; no source-map upload HTTP endpoint. |
| tar 7.5.7 | critical | Capacitor CLI/package tooling, no reader-supplied archive extraction route. Audit labels package critical; that does not establish backend archive execution. |
| websocket-driver 0.7.4 | critical | Firebase includes WebSocket capabilities transitively, but app uses Auth only and has no websocket-driver server/untrusted frame interface. Next’s separate upgrade-proxy advisory still needs review. |

| Advisory (individual high/critical) | Package | Severity | Applicability in this code |
|---|---|---|---|
| [GHSA-rvm3-566m-v7fv: Capacitor Android and iOS: remote content can be loaded at the app origin via the internal HTTP proxy path](https://github.com/advisories/GHSA-rvm3-566m-v7fv) | @capacitor/ios | critical | Affected iOS/Swift runtime 8.1.0; links from model Markdown provide a delivery surface. Exact remote-URL shell interception needs disposable native verification. |
| [GHSA-5375-pq7m-f5r2: @grpc/grpc-js: A malformed request can cause a server crash](https://github.com/advisories/GHSA-5375-pq7m-f5r2) | @grpc/grpc-js | high | Transitive Firebase Node capability; app uses browser Auth only and runs no gRPC server or untrusted peer. No app path to the listed server/peer handling found. |
| [GHSA-99f4-grh7-6pcq: @grpc/grpc-js: An incoming malformed compressed message can cause a client or server crash](https://github.com/advisories/GHSA-99f4-grh7-6pcq) | @grpc/grpc-js | high | Transitive Firebase Node capability; app uses browser Auth only and runs no gRPC server or untrusted peer. No app path to the listed server/peer handling found. |
| [GHSA-m9gg-hp2v-232j: @grpc/grpc-js: In certain configurations, getAuthContext can return unauthorized certificates as though they were authorized](https://github.com/advisories/GHSA-m9gg-hp2v-232j) | @grpc/grpc-js | high | Transitive Firebase Node capability; app uses browser Auth only and runs no gRPC server or untrusted peer. No app path to the listed server/peer handling found. |
| [GHSA-wh4c-j3r5-mjhp: xmldom: XML injection via unsafe CDATA serialization allows attacker-controlled markup insertion](https://github.com/advisories/GHSA-wh4c-j3r5-mjhp) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-2v35-w6hq-6mfw: xmldom: Uncontrolled recursion in XML serialization leads to DoS](https://github.com/advisories/GHSA-2v35-w6hq-6mfw) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-f6ww-3ggp-fr8h: xmldom has XML injection through unvalidated DocumentType serialization](https://github.com/advisories/GHSA-f6ww-3ggp-fr8h) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-x6wf-f3px-wcqx: xmldom has XML node injection through unvalidated processing instruction serialization](https://github.com/advisories/GHSA-x6wf-f3px-wcqx) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-j759-j44w-7fr8: xmldom has XML node injection through unvalidated comment serialization](https://github.com/advisories/GHSA-j759-j44w-7fr8) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-w2rr-34g9-rvrj: xmldom: Element name injection via createElement() bypasses requireWellFormed](https://github.com/advisories/GHSA-w2rr-34g9-rvrj) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-4w3w-2rp5-g8jm: xmldom: Attribute name injection via setAttribute() bypasses requireWellFormed](https://github.com/advisories/GHSA-4w3w-2rp5-g8jm) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-c7q8-3ch8-vqpv: xmldom: Processing Instruction Target Injection Bypasses requireWellFormed](https://github.com/advisories/GHSA-c7q8-3ch8-vqpv) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-27p8-2357-5qqv: xmldom: DocType `name` Injection Bypasses requireWellFormed](https://github.com/advisories/GHSA-27p8-2357-5qqv) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-8344-3jmq-59r6: xmldom: Quadratic-time attribute deduplication](https://github.com/advisories/GHSA-8344-3jmq-59r6) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-x4fp-j954-r2f4: xmldom: End-tag Whitespace-Trim Regex ReDoS — quadratic backtracking in the 0.8.x end-tag parser](https://github.com/advisories/GHSA-x4fp-j954-r2f4) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-965w-775f-mr7g: xmldom: Quadratic-memory consumption](https://github.com/advisories/GHSA-965w-775f-mr7g) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-93r5-fhx6-vmg9: xmldom: Quadratic-time parsing via the malformed-input recovery path — `parseElementStartPart` re-scan and `normalize()` adjacent-text merge](https://github.com/advisories/GHSA-93r5-fhx6-vmg9) | @xmldom/xmldom | high | Capacitor CLI consumes checked-in native XML at build/sync time. No XML upload/parser HTTP endpoint. |
| [GHSA-3jxr-9vmj-r5cp: brace-expansion: DoS via exponential-time expansion of consecutive non-expanding {} groups](https://github.com/advisories/GHSA-3jxr-9vmj-r5cp) | brace-expansion | high | Actual vulnerable node is glob/node_modules/brace-expansion 5.0.2, not the root 1.1.12. CLI filesystem patterns, not reader-controlled HTTP input. |
| [GHSA-mh99-v99m-4gvg: brace-expansion: DoS via unbounded expansion length causing an out-of-memory process crash](https://github.com/advisories/GHSA-mh99-v99m-4gvg) | brace-expansion | high | Actual vulnerable node is glob/node_modules/brace-expansion 5.0.2, not the root 1.1.12. CLI filesystem patterns, not reader-controlled HTTP input. |
| [GHSA-rgw5-rvv9-x895: brace-expansion: DoS via unbounded intermediate arrays, bypassing the CVE-2026-14257 mitigation](https://github.com/advisories/GHSA-rgw5-rvv9-x895) | brace-expansion | high | Actual vulnerable node is glob/node_modules/brace-expansion 5.0.2, not the root 1.1.12. CLI filesystem patterns, not reader-controlled HTTP input. |
| [GHSA-qhr7-859c-m2p7: brace-expansion: DoS via uncontrolled recursion on nested brace groups causing stack exhaustion](https://github.com/advisories/GHSA-qhr7-859c-m2p7) | brace-expansion | high | Actual vulnerable node is glob/node_modules/brace-expansion 5.0.2, not the root 1.1.12. CLI filesystem patterns, not reader-controlled HTTP input. |
| [GHSA-6j4f-fj2g-mc7p: brace-expansion: DoS via uncontrolled recursion in parseCommaParts causing stack exhaustion](https://github.com/advisories/GHSA-6j4f-fj2g-mc7p) | brace-expansion | high | Actual vulnerable node is glob/node_modules/brace-expansion 5.0.2, not the root 1.1.12. CLI filesystem patterns, not reader-controlled HTTP input. |
| [GHSA-3ppc-4f35-3m26: minimatch has a ReDoS via repeated wildcards with non-matching literal in pattern](https://github.com/advisories/GHSA-3ppc-4f35-3m26) | minimatch | high | Actual vulnerable node is glob/node_modules/minimatch 10.2.0, not root 3.1.2. CLI/local patterns; no HTTP pattern interface. |
| [GHSA-7r86-cg39-jmmj: minimatch has ReDoS: matchOne() combinatorial backtracking via multiple non-adjacent GLOBSTAR segments](https://github.com/advisories/GHSA-7r86-cg39-jmmj) | minimatch | high | Actual vulnerable node is glob/node_modules/minimatch 10.2.0, not root 3.1.2. CLI/local patterns; no HTTP pattern interface. |
| [GHSA-23c5-xmqv-rm74: minimatch ReDoS: nested *() extglobs generate catastrophically backtracking regular expressions](https://github.com/advisories/GHSA-23c5-xmqv-rm74) | minimatch | high | Actual vulnerable node is glob/node_modules/minimatch 10.2.0, not root 3.1.2. CLI/local patterns; no HTTP pattern interface. |
| [GHSA-28wg-ghj8-5hjv: nanoid: non-secure generators can loop indefinitely with negative size](https://github.com/advisories/GHSA-28wg-ghj8-5hjv) | nanoid | high | No direct app call; transitive fixed-size generation. No reader-controlled size/custom alphabet path found. |
| [GHSA-2v37-7h3g-55p8: nanoid: custom generators can loop indefinitely when size is zero](https://github.com/advisories/GHSA-2v37-7h3g-55p8) | nanoid | high | No direct app call; transitive fixed-size generation. No reader-controlled size/custom alphabet path found. |
| [GHSA-xwg4-73v4-xw9w: nanoid: Integer Overflow or Wraparound](https://github.com/advisories/GHSA-xwg4-73v4-xw9w) | nanoid | high | No direct app call; transitive fixed-size generation. No reader-controlled size/custom alphabet path found. |
| [GHSA-q4gf-8mx6-v5v3: Next.js has a Denial of Service with Server Components](https://github.com/advisories/GHSA-q4gf-8mx6-v5v3) | next | high | No Server Actions: node/edge manifests are empty and action handler exits before decode. No current app action endpoint. |
| [GHSA-8h8q-6873-q5fj: Next.js Vulnerable to Denial of Service with Server Components](https://github.com/advisories/GHSA-8h8q-6873-q5fj) | next | high | No Server Actions: same early rejection; do not infer exploitability from App Router alone. |
| [GHSA-26hh-7cqf-hhc6: Next.js has a Middleware / Proxy bypass in App Router applications via segment-prefetch routes - Incomplete Fix Follow-Up](https://github.com/advisories/GHSA-26hh-7cqf-hhc6) | next | high | No app middleware/proxy auth layer to bypass; Firebase authorization is in the separate backend. |
| [GHSA-mg66-mrh9-m8jx: Next.js vulnerable to Denial of Service via connection exhaustion in applications using Cache Components](https://github.com/advisories/GHSA-mg66-mrh9-m8jx) | next | high | Cache Components not enabled; named feature precondition absent. |
| [GHSA-c4j6-fc7j-m34r: Next.js vulnerable to server-side request forgery in applications using WebSocket upgrades](https://github.com/advisories/GHSA-c4j6-fc7j-m34r) | next | high | Vendor covers built-in self-hosted Node upgrade handling, which is present even with no app WebSocket code. Cloud Run ingress exploitability Suspected; isolated/staging check required. |
| [GHSA-492v-c6pp-mqqv: Next.js has a Middleware / Proxy bypass through dynamic route parameter injection](https://github.com/advisories/GHSA-492v-c6pp-mqqv) | next | high | No app middleware/proxy security gate to bypass. |
| [GHSA-267c-6grr-h53f: Next.js has a Middleware / Proxy bypass in App Router applications via segment-prefetch routes](https://github.com/advisories/GHSA-267c-6grr-h53f) | next | high | No app middleware/proxy security gate to bypass. |
| [GHSA-36qx-fr4f-26g5: Next.js has a Middleware / Proxy bypass in Pages Router applications using i18n](https://github.com/advisories/GHSA-36qx-fr4f-26g5) | next | high | No Pages Router/i18n configuration. |
| [GHSA-m99w-x7hq-7vfj: Next.js: Denial of Service in App Router using Server Actions](https://github.com/advisories/GHSA-m99w-x7hq-7vfj) | next | high | No Server Actions in built manifest; named action endpoint absent. |
| [GHSA-89xv-2m56-2m9x: Next.js: Server-Side Request Forgery in Server Actions on custom servers](https://github.com/advisories/GHSA-89xv-2m56-2m9x) | next | high | No custom Next server or Server Actions. |
| [GHSA-p9j2-gv94-2wf4: Next.js: Server-Side Request Forgery in rewrites via attacker-controlled destination hostname](https://github.com/advisories/GHSA-p9j2-gv94-2wf4) | next | high | No configured rewrites. |
| [GHSA-p293-qw3h-jr36: Next.js: Unauthenticated Remote Code Execution on windows-hosted servers](https://github.com/advisories/GHSA-p293-qw3h-jr36) | next | critical | Production Docker runtime is Linux, not Windows. |
| [GHSA-2xp9-vwfh-vxw4: Next.js: Unauthenticated Remote Code Execution in Image Optimization API when AVIF files are used](https://github.com/advisories/GHSA-2xp9-vwfh-vxw4) | next | critical | AVIF decoding path not demonstrated: fixed local PNGs, no AVIF files/upload or allowed external source. No blanket web RCE claim. |
| [GHSA-6g55-p6wh-862q: PostCSS: Arbitrary file read and information disclosure via attacker-controlled sourceMappingURL in CSS comments](https://github.com/advisories/GHSA-6g55-p6wh-862q) | postcss | high | Build-time app CSS, no reader CSS compiler/source-map parser. User-controlled raw style tags are the separate SEC-01 sink, not PostCSS compilation. |
| [GHSA-r28c-9q8g-f849: PostCSS: Path Traversal in Previous Source Map Auto-Loading (sourceMappingURL) leads to Arbitrary .map File Disclosure](https://github.com/advisories/GHSA-r28c-9q8g-f849) | postcss | high | Build-time app CSS, no reader CSS compiler/source-map parser. User-controlled raw style tags are the separate SEC-01 sink, not PostCSS compilation. |
| [GHSA-xq3m-2v4x-88gg: Arbitrary code execution in protobufjs](https://github.com/advisories/GHSA-xq3m-2v4x-88gg) | protobufjs | critical | No client Firestore import, schema upload or direct protobuf reflection/codegen path. Browser Auth does not accept user-created protobuf descriptors. |
| [GHSA-66ff-xgx4-vchm: protobuf.js: Code injection through bytes field defaults in generated toObject code](https://github.com/advisories/GHSA-66ff-xgx4-vchm) | protobufjs | high | No client Firestore import, schema upload or direct protobuf reflection/codegen path. Browser Auth does not accept user-created protobuf descriptors. |
| [GHSA-75px-5xx7-5xc7: protobuf.js: Code generation gadget after prototype pollution](https://github.com/advisories/GHSA-75px-5xx7-5xc7) | protobufjs | high | No client Firestore import, schema upload or direct protobuf reflection/codegen path. Browser Auth does not accept user-created protobuf descriptors. |
| [GHSA-jvwf-75h9-cwgg: protobuf.js: Process-wide denial of service through unsafe option paths](https://github.com/advisories/GHSA-jvwf-75h9-cwgg) | protobufjs | high | No client Firestore import, schema upload or direct protobuf reflection/codegen path. Browser Auth does not accept user-created protobuf descriptors. |
| [GHSA-685m-2w69-288q: protobuf.js: Denial of service through unbounded protobuf recursion](https://github.com/advisories/GHSA-685m-2w69-288q) | protobufjs | high | No client Firestore import, schema upload or direct protobuf reflection/codegen path. Browser Auth does not accept user-created protobuf descriptors. |
| [GHSA-wcpc-wj8m-hjx6: protobufjs: Denial of service through unbounded Any expansion during JSON conversion](https://github.com/advisories/GHSA-wcpc-wj8m-hjx6) | protobufjs | high | No client Firestore import, schema upload or direct protobuf reflection/codegen path. Browser Auth does not accept user-created protobuf descriptors. |
| [GHSA-f88m-g3jw-g9cj: sharp inherited vulnerabilities in libvips: CVE-2026-33327, CVE-2026-33328, CVE-2026-35590, CVE-2026-35591](https://github.com/advisories/GHSA-f88m-g3jw-g9cj) | sharp | high | next/image optimizes the fixed local PNG logo. No remotePatterns or AVIF upload/source found; untrusted decoder inputs not demonstrated. Image-cache resource growth is separate. |
| [GHSA-rgj7-g3m4-5g8c: sharp: Vulnerabilities in libheif: GHSA-g89c-p67h-r497 and GHSA-2jg2-4ch7-h545](https://github.com/advisories/GHSA-rgj7-g3m4-5g8c) | sharp | high | next/image optimizes the fixed local PNG logo. No remotePatterns or AVIF upload/source found; untrusted decoder inputs not demonstrated. Image-cache resource growth is separate. |
| [GHSA-wq5f-xc86-pv6w: sharp : Vulnerability in librsvg dependency CVE-2026-96889](https://github.com/advisories/GHSA-wq5f-xc86-pv6w) | sharp | high | next/image optimizes the fixed local PNG logo. No remotePatterns or AVIF upload/source found; untrusted decoder inputs not demonstrated. Image-cache resource growth is separate. |
| [GHSA-68fv-2mgg-jv7q: source-map-js allows event-loop denial of service through indexed source-map section offsets](https://github.com/advisories/GHSA-68fv-2mgg-jv7q) | source-map-js | high | Build tooling consumes trusted generated/local maps; no source-map upload HTTP endpoint. |
| [GHSA-83g3-92jg-28cx: Arbitrary File Read/Write via Hardlink Target Escape Through Symlink Chain in node-tar Extraction](https://github.com/advisories/GHSA-83g3-92jg-28cx) | tar | high | Capacitor CLI/package tooling, no reader-supplied archive extraction route. Audit labels package critical; that does not establish backend archive execution. |
| [GHSA-qffp-2rhf-9h96: tar has Hardlink Path Traversal via Drive-Relative Linkpath](https://github.com/advisories/GHSA-qffp-2rhf-9h96) | tar | high | Capacitor CLI/package tooling, no reader-supplied archive extraction route. Audit labels package critical; that does not establish backend archive execution. |
| [GHSA-9ppj-qmqm-q256: node-tar Symlink Path Traversal via Drive-Relative Linkpath](https://github.com/advisories/GHSA-9ppj-qmqm-q256) | tar | high | Capacitor CLI/package tooling, no reader-supplied archive extraction route. Audit labels package critical; that does not establish backend archive execution. |
| [GHSA-23hp-3jrh-7fpw: node-tar: Decompression/parse DoS via unlimited input](https://github.com/advisories/GHSA-23hp-3jrh-7fpw) | tar | critical | Capacitor CLI/package tooling, no reader-supplied archive extraction route. Audit labels package critical; that does not establish backend archive execution. |
| [GHSA-8x88-c5mf-7j5w: node-tar: Negative tar entry size causes infinite loop in archive replace](https://github.com/advisories/GHSA-8x88-c5mf-7j5w) | tar | high | Capacitor CLI/package tooling, no reader-supplied archive extraction route. Audit labels package critical; that does not establish backend archive execution. |
| [GHSA-r292-9mhp-454m: node-tar: Uncontrolled recursion in mapHas/filesFilter allows uncatchable stack-overflow DoS via crafted long-path tar with member selection](https://github.com/advisories/GHSA-r292-9mhp-454m) | tar | high | Capacitor CLI/package tooling, no reader-supplied archive extraction route. Audit labels package critical; that does not establish backend archive execution. |
| [GHSA-xv26-6w52-cph6: websocket-driver: Message corruption via abuse of protocol length headers](https://github.com/advisories/GHSA-xv26-6w52-cph6) | websocket-driver | critical | Firebase includes WebSocket capabilities transitively, but app uses Auth only and has no websocket-driver server/untrusted frame interface. Next’s separate upgrade-proxy advisory still needs review. |

No user-managed Server Action manifest key is reproduced here; the generated manifest was inspected only to establish empty node/edge action maps. Patched version ranges must be verified when implementing the dependency session because feeds and compatible releases move. In particular, the [Capacitor vendor advisory](https://github.com/ionic-team/capacitor/security/advisories/GHSA-rvm3-566m-v7fv) requires a patched native rebuild, not only a web deployment. The [Next AVIF advisory](https://github.com/vercel/next.js/security/advisories/GHSA-2xp9-vwfh-vxw4) concerns decoder input, while its [upgrade-proxy advisory](https://github.com/vercel/next.js/security/advisories/GHSA-c4j6-fc7j-m34r) concerns the built-in self-hosted server. They have different preconditions.

pip-audit details below retain every unique advisory, including low/moderate cases, because the JSON output has no severity field. All high/critical paths are therefore included rather than guessed from package names. Duplicate PYSEC/GHSA/CVE aliases are counted once in this table.

| Resolved requirement/dependency | Advisory | Fixed versions reported | Concrete reachability assessment |
|---|---|---|---|
| flask 3.0.3 | [PYSEC-2026-2151 / GHSA-68rp-wp8r-4726](https://github.com/advisories/GHSA-68rp-wp8r-4726) | 3.1.3 | Flask session membership/Vary behavior: app uses Firebase bearer tokens and never imports/accesses Flask session. Named cookie-session caching path absent. |
| flask-cors 4.0.0 | [PYSEC-2024-271 / GHSA-84pr-m4jr-85g5](https://github.com/advisories/GHSA-84pr-m4jr-85g5) | 4.0.1 | Debug log injection: production env list has no FLASK_DEBUG; app logs INFO. Debug-specific precondition absent in observed revision. |
| flask-cors 4.0.0 | [PYSEC-2024-71 / GHSA-hxwh-jpp2-84pm](https://github.com/advisories/GHSA-hxwh-jpp2-84pm) | 4.0.2 | Private-network CORS default: this app is a public Cloud Run service, not a private-network target, and uses explicit origin allowlist. No private-network exposure demonstrated. |
| flask-cors 4.0.0 | [PYSEC-2026-1385 / GHSA-8vgw-p6qm-5gr7](https://github.com/advisories/GHSA-8vgw-p6qm-5gr7) | 6.0.0 | CORS path normalization: a single /* rule applies uniformly, with no more restrictive path rule to bypass. No current differential-path policy found. |
| flask-cors 4.0.0 | [PYSEC-2026-1383 / GHSA-43qf-4rqw-9q2g](https://github.com/advisories/GHSA-43qf-4rqw-9q2g) | 6.0.0 | CORS case-insensitive matching: same uniform policy; no path-specific access policy. Server auth remains independent. |
| flask-cors 4.0.0 | [PYSEC-2026-1384 / GHSA-7rxf-gvfg-47g4](https://github.com/advisories/GHSA-7rxf-gvfg-47g4) | 6.0.0 | CORS regex priority: only one resource rule, so no competing permissive/sensitive path policies. |
| requests 2.32.3 | [PYSEC-2026-1872 / GHSA-9hjg-9r4m-mvj7](https://github.com/advisories/GHSA-9hjg-9r4m-mvj7) | 2.32.4 | Requests .netrc leak: outbound URLs are fixed server configuration/Vertex/GitHub targets, not reader-provided URL fetches. No crafted URL path demonstrated. |
| requests 2.32.3 | [PYSEC-2026-2275 / GHSA-gc5v-m9x4-r6x2](https://github.com/advisories/GHSA-gc5v-m9x4-r6x2) | 2.33.0 | extract_zipped_paths local temporary-file issue: no direct app use; standard HTTP usage alone is not the described path. |
| cryptography 49.0.0 | [PYSEC-2026-3552 / GHSA-g6cj-pr64-35w5](https://github.com/advisories/GHSA-g6cj-pr64-35w5) | 50.0.0 | PKCS7 decrypt oracle: app uses Fernet, not attacker-supplied PKCS7 EnvelopedData decryption. Named cryptographic operation absent. |
| protobuf 4.25.9 | [PYSEC-2026-1805 / GHSA-7gcm-g887-7qv7](https://github.com/advisories/GHSA-7gcm-g887-7qv7) | 5.29.6, 6.33.5 | Nested protobuf Any/ParseDict: no user-provided protobuf descriptor/Any decoding route. Google API SDK transport use is not proof of this input path. |

The Python audit result is actionable dependency debt, but none of these advisory-specific remote exploit paths was demonstrated in this application. This does not excuse the separate raw exception disclosure, missing quotas or HTML rendering defects, which are app code.

### Read-only cloud commands and observations

The following are the actual command shapes used (JSON was selected/summarized before display to omit credential/env values):

```sh
gcloud run services describe tafsir-backend --region=us-central1 --project=tafsir-simplified --format=json
gcloud run services describe tafsir-frontend --region=us-central1 --project=tafsir-simplified --format=json
gcloud firestore databases describe --database='(default)' --project=tafsir-simplified-6b262 --format=json
gcloud firestore databases describe --database=tafsir-db --project=tafsir-simplified-6b262 --format=json
gcloud firestore backups schedules list --database='(default)' --project=tafsir-simplified-6b262 --format=json
gcloud firestore backups schedules list --database=tafsir-db --project=tafsir-simplified-6b262 --format=json
gcloud firestore backups list --location=us-central1 --project=tafsir-simplified-6b262 --format=json
gcloud billing budgets list --billing-account=0152F9-4F49EC-74C075 --format=json
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="tafsir-backend" AND (textPayload:"REQUEST_METRIC" OR textPayload:"GEMINI_USAGE")' --project=tafsir-simplified --freshness=30d --limit=200 --format=json
(cd backend && gcloud meta list-files-for-upload)
(cd frontend && gcloud meta list-files-for-upload)
```

Metadata-only HTTPS GETs, authorized using an existing CLI token internally (never printed/saved), read:

- `firebaserules.googleapis.com/v1/projects/tafsir-simplified-6b262/releases` → 403; no ruleset content available.
- `monitoring.googleapis.com/v3/projects/tafsir-simplified/alertPolicies` → three enabled policies described above.
- `monitoring.googleapis.com/v3/projects/tafsir-simplified/uptimeCheckConfigs` → backend health check described above.
- `firestore.googleapis.com/v1/projects/tafsir-simplified-6b262/databases/(default)/collectionGroups/-/indexes` → two READY indexes described above.
- Monitoring `timeSeries` for `run.googleapis.com/container/memory/utilizations`, filtered to backend, last seven days, 86400-second alignment, ALIGN_PERCENTILE_99 → observed revision daily values about 0.0999–0.1299. These are histogram/period p99 summaries, not maximum heap/RSS measurements or proof under concurrency.

```text
backend: 00273-dpr, 100% latest, 2 CPU/2Gi, timeout 300,
  containerConcurrency 80, maxScale 10, no minScale annotation
  env names: FIREBASE_PROJECT, GCP_INFRASTRUCTURE_PROJECT, GCP_LOCATION,
  GEMINI_API_LOCATION, GEMINI_MODEL_ID, GEMINI_LITE_MODEL_ID, GCS_BUCKET_NAME,
  FIREBASE_SECRET_FULL_PATH, ADMIN_SECRET
  REFLECTION_ENCRYPTION_SECRET absent
frontend: 00308-vbm, 100% latest, 1 CPU/1Gi, timeout 60, concurrency 80
both Firestore DBs: us-central1; PITR disabled; retention 3600s;
  DELETE_PROTECTION_DISABLED
backup schedules: (default)=[], tafsir-db=[]
retained managed backups in us-central1: []
budget query: SERVICE_DISABLED, billingbudgets.googleapis.com; no API enabled
```

The current backend’s nine env names match the intended deployed model setup; values were not exported wholesale. ADMIN_SECRET is a secret reference, not a value accessed by this audit.

| Revision / successful tafsir status | Sample n | Median server time | Maximum | Interpretation |
|---|---:|---:|---:|---|
| 00273-dpr, miss (3.8 production) | 2 | 28.193 s | 29.515 s | Tiny fresh sample; consistent with handoff, not an organic-traffic distribution |
| 00273-dpr, hit-firestore | 6 | 126 ms | 153 ms | Shared cache is effective |
| 00275-dap, miss (3.8 canary) | 6 | 27.204 s | 44.192 s | Existing canary data, no new generation |
| 00271-l8f, miss (3.6 previous) | 12 | 21.592 s | 26.890 s | Different verses/conditions; not a controlled speed benchmark |

Representative existing usage lines:

```text
GEMINI_USAGE verse=94:5 model=gemini-3.8-flash prompt_tokens=7636 candidate_tokens=1219 total_tokens=10681
GEMINI_USAGE verse=2:255 model=gemini-3.8-flash prompt_tokens=14400 candidate_tokens=2026 total_tokens=19438
```

**Hot-path breakdown supported by code:** parse/range/budget and rate check; profile read; Firestore cache direct/default read and hit update before memory fallback; canonical verse/metadata retrieval; deterministic scholarly planning and local pointer resolution; prompt assembly; credential refresh and one/two Gemini HTTP attempts; extraction/hadith/source filters; deterministic recommendations/canonical verse replacement; memory/Firestore cache writes; authenticated progress and badge reads/writes. Server-Timing names include request_parsing, user_profile, cache_check, classification, verse_lookup, scholarly_retrieval, prompt_build, gemini, post_processing, total. Existing REQUEST_METRIC lines supply totals, not individual stage durations; no fresh Server-Timing request was triggered just to fill this table. Cache write and badge time are folded into post_processing. GCS corpus loading/precomputation occurs at startup, outside these request stages. No exact per-stage timing or cold-start percentile is invented.

Public GET results, all October 17 and HTTP 200:

```text
frontend /: x-nextjs-cache=HIT; cache-control=s-maxage=31536000;
  no CSP, X-Frame-Options, HSTS or Referrer-Policy header
backend /health: status healthy, metadata_entries 6720, memory cache_size 2;
  no CSP, X-Frame-Options, HSTS or Referrer-Policy header
backend /range-limit?surah=2&start=1: {"maxEnd":6,"surahMax":286}
```

The frontend cached HTML is the public shell: reader data is fetched with bearer auth client-side. The service worker is network-only. No authenticated response caching was observed or exercised. Backend private responses have no explicit Cache-Control policy in application code; the audit did not find a configured intermediary caching bearer-auth responses, so it does not assert cross-user HTTP cache leakage from header absence alone.

### Offline reproduction outputs and portable fixtures

The scratch code probe AST-compiled the real functions without decorators/startup and used only fake Firestore/Vertex clients. It did not import app.py or initialize Google clients. The existing route retry fixture likewise stubs all paid/storage I/O.

```text
PARSER
'2:1-3' ref= (2, 1) range= (2, 1, 3) normalized= 2:1-3
'Al-Baqarah 1-3' ref= (2, 1) range= (2, 1, 3) normalized= 2:1
'2/1-3' ref= (2, 1) range= (2, 1, 3) normalized= 2:1
'2:280-999' ref= (2, 280) range= (2, 280, 280) normalized= 2:280-999
'2:10-1' ref= (2, 10) range= (2, 10, 10) normalized= 2:10-1
'٢:٢٥٥' ref= (2, 255) range= (2, 255, 255) normalized= 2:255
'2:255 extra instructions' ref= (2, 255) range= (2, 255, 255) normalized= 2:255
'Al-Fatihah 7' ref= (1, 1) range= (1, 1, 1) normalized= 1:1
'115:1' ref= None range= None normalized= 115:1
'2:0' ref= None range= None normalized= 2:0
KEY_COLLISION_RAW_QUERY True
KEY_COLLISION_NAMED_RANGE True
KEY_COLLISION_PIPELINE True
EXPIRED_CACHE_RETURNED {'marker': 'expired'}
WRONG_PERSONA_FALLBACK {'marker': 'practicing-muslim'}
UNCONFIGURED_ENCRYPTION_IDENTITY True
HADITH_UNSUPPORTED_ATTRIBUTION_SURVIVES narrated by Synthetic incorrect narrator; Sahih Muslim 999999 collection= ''
HADITH_UNSUPPORTED_ENDING_KEPT True match_ratio= 0.967391304347826
CONCURRENT_PROGRESS_FINAL {'explored_verses': {'2': [1]}, 'stats_cache': {'total_explored_verses': 1, 'total_explored_surahs': 1}}
SCHEMALESS_RESPONSE_CACHED 200 cache_writes= 1 tafsir= None
NONSTRING_QUERY_STATUS 500
IMAN_GOALS_DATE_ERROR can't subtract offset-naive and offset-aware datetimes
ROUTE_COUNT 84 RAW_ERROR_ROUTES 69
HTML_SURVIVES_BACKEND_FILTER True
```

The full self-contained scratch probe can be reproduced by saving this fenced script outside the repository and running `backend/venv/bin/python /tmp/tadabbur-code-probes.py` from the repository root. It changes only fake in-memory objects and /tmp output files.

<details><summary>Offline function/route probe</summary>

```python
import ast,json,re,hashlib,logging,sys,threading,copy,importlib.util
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import defaultdict
from typing import Optional,Tuple,Dict,Any,List
from types import SimpleNamespace
from unittest.mock import Mock
from flask import Flask,request,jsonify
from cryptography.fernet import Fernet

root=Path.cwd();path=root/'backend/app.py';source=path.read_text();tree=ast.parse(source)
sys.path.insert(0,str(root/'backend'))
ns=dict(globals());ns['logger']=logging.getLogger('audit');ns['_single_line_log']=str
for n in tree.body:
 if isinstance(n,ast.Assign):
  for target in n.targets:
   if isinstance(target,ast.Name) and target.id in {'QURAN_METADATA','NAMED_VERSES','SURAH_NAME_ALIASES'}:ns[target.id]=ast.literal_eval(n.value)
ns['SURAHS_BY_NAME']={v['name'].lower():k for k,v in ns['QURAN_METADATA'].items()}
def add(*names):
 nodes=[copy.deepcopy(n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 for n in nodes:n.decorator_list=[]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
add('normalize_query_text','extract_verse_reference_enhanced','extract_verse_range','surah_name_to_number','validate_verse_reference','normalize_verse_query','get_firestore_cache_key','get_cached_tafsir_response','_track_explored_verse','update_plan_progress','_encrypt_text','_get_user_fernet')
print('PARSER')
for q in ['2:1-3','Al-Baqarah 1-3','2/1-3','2:280-999','2:10-1','٢:٢٥٥','2:255 extra instructions','Al-Fatihah 7','115:1','2:0']:
 print(repr(q),'ref=',ns['extract_verse_reference_enhanced'](q),'range=',ns['extract_verse_range'](q),'normalized=',ns['normalize_verse_query'](q))
profile={'persona':'curious_explorer','knowledge_level':'beginner'}
k=lambda q:ns['get_firestore_cache_key'](q,profile)['cache_key']
print('KEY_COLLISION_RAW_QUERY',k('2:255')==k('2:255 extra instructions'))
print('KEY_COLLISION_NAMED_RANGE',k('Al-Baqarah 1-3')==k('2:1'))
ns['SCHOLARLY_PIPELINE_VERSION']='16.0'
a=k('2:255');ns['SCHOLARLY_PIPELINE_VERSION']='17.0';print('KEY_COLLISION_PIPELINE',a==k('2:255'));ns['SCHOLARLY_PIPELINE_VERSION']='16.0'
# Static fake Firestore documents. Never initialize cloud clients.
class Doc:
 def __init__(self,data=None):self.data=data;self.exists=data is not None
 def to_dict(self):return copy.deepcopy(self.data)
class Ref:
 def __init__(self,data=None):self.data=data;self.updates=[]
 def get(self):return Doc(self.data)
 def update(self,x):self.updates.append(x)
expired=Ref({'version':'16.0','expires_at':datetime(2000,1,1,tzinfo=timezone.utc),'response':{'marker':'expired'}})
ns['quran_db']=Mock();ns['quran_db'].collection.return_value.document.return_value=expired;ns['firestore']=SimpleNamespace(Increment=lambda x:x)
print('EXPIRED_CACHE_RETURNED',ns['get_cached_tafsir_response']('2:255',profile))
ns['quran_db'].collection.return_value.document.side_effect=[Ref(),Ref({'version':'16.0','response':{'marker':'practicing-muslim'}})]
print('WRONG_PERSONA_FALLBACK',ns['get_cached_tafsir_response']('2:255',profile))
ns['REFLECTION_ENCRYPTION_SECRET']='';print('UNCONFIGURED_ENCRYPTION_IDENTITY',ns['_encrypt_text']('synthetic private reflection','synthetic-uid')=='synthetic private reflection')
from services.hadith_validation import validate_hadith_items,_normalize_tokens,_text_match
wording='By Him in Whose Hand is my soul, this verse has a tongue and two lips with which it praises the King beside the leg of the Throne.'
context='Imam Ahmad recorded the following wording from Ubayy ibn Kab: '+wording+' Muslim also collected the report, but did not include this additional wording.'
kept,dropped=validate_hadith_items([{'reference':{'collection':'Sahih Muslim','narrator':'Synthetic incorrect narrator','attribution':'Sahih Muslim 999999'},'text':wording}],context)
print('HADITH_UNSUPPORTED_ATTRIBUTION_SURVIVES',kept[0]['reference'],'collection=',repr(kept[0]['collection']))
base=' '.join('word'+str(i) for i in range(100));altered=base+' synthetic unsupported ending'
print('HADITH_UNSUPPORTED_ENDING_KEPT',bool(validate_hadith_items([{'text':altered}],base)[0]),'match_ratio=',_text_match(_normalize_tokens(altered),_normalize_tokens(base))[2])
# Two actual progress functions reading the same snapshot, then merging writes.
barrier=threading.Barrier(2);stored={}
class ConcurrentRef:
 def get(self):
  snap=Doc(copy.deepcopy(stored));barrier.wait(timeout=2);return snap
 def set(self,data,merge=False):stored.update(copy.deepcopy(data))
ns['users_db']=Mock();ns['users_db'].collection.return_value.document.return_value=ConcurrentRef()
threads=[threading.Thread(target=ns['_track_explored_verse'],args=('synthetic',2,v)) for v in (1,2)]
for t in threads:t.start()
for t in threads:t.join()
print('CONCURRENT_PROGRESS_FINAL',stored)
# Existing offline route fixture compiles actual tafsir handler with all I/O replaced.
spec=importlib.util.spec_from_file_location('audit_retry',root/'backend/tests/test_tafsir_retry.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
import pytest
with pytest.MonkeyPatch.context() as monkeypatch:
 env=mod.route_env.__wrapped__(monkeypatch)
 env.post.side_effect=[mod.gemini_response(json.dumps({'unrelated':'no commentary'}))]
 response=env.client.post('/tafsir',json={'query':'2:255'})
 print('SCHEMALESS_RESPONSE_CACHED',response.status_code,'cache_writes=',env.store.call_count,'tafsir=',response.get_json().get('tafsir_explanations'))
 response=env.client.post('/tafsir',json={'query':12})
 print('NONSTRING_QUERY_STATUS',response.status_code)
# Date arithmetic from actual Iman handler.
try:datetime.now(timezone.utc)-datetime.fromisoformat('2026-10-17T12:00:00+00:00').replace(tzinfo=None)
except TypeError as e:print('IMAN_GOALS_DATE_ERROR',str(e))
# Inventory and exact count of raw str(e) route responses.
routes=[];leaks=[]
for n in tree.body:
 if not isinstance(n,ast.FunctionDef):continue
 route=[d for d in n.decorator_list if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.func.attr=='route']
 if not route:continue
 d=route[0];p=ast.literal_eval(d.args[0]);methods=next((ast.literal_eval(k.value) for k in d.keywords if k.arg=='methods'),['GET'])
 decorators=[ast.unparse(x) for x in n.decorator_list[1:]]
 if n.name=='get_verse_annotations':decorators=['firebase_auth_required (nested handle_get)']
 text=ast.get_source_segment(source,n)
 if re.search(r'"error": str\(e\)|\x27error\x27: str\(e\)',text):leaks.append(p+' '+','.join(methods))
 routes.append({'path':p,'methods':methods,'line':n.lineno,'name':n.name,'auth':decorators})
print('ROUTE_COUNT',len(routes),'RAW_ERROR_ROUTES',len(leaks))
open('/tmp/tadabbur-route-inventory.json','w').write(json.dumps(routes,indent=2));open('/tmp/tadabbur-leaky-routes.json','w').write(json.dumps(leaks,indent=2))
from utils.text_cleaning import normalize_html_to_markdown,sanitize_heading_format
ns.update(normalize_html_to_markdown=normalize_html_to_markdown,sanitize_heading_format=sanitize_heading_format)
add('filter_unavailable_sources','sanitize_explanation_text','sanitize_unavailability_text')
payload='<iframe srcdoc="<script>parent.document.body.dataset.auditIframe=1</script>"></iframe>'
x=ns['filter_unavailable_sources']({'tafsir_explanations':[{'source':'Ibn Kathir','explanation':payload}]})
print('HTML_SURVIVES_BACKEND_FILTER',x['tafsir_explanations'][0]['explanation']==payload)

```

</details>

Renderer checks used the exact installed libraries, not a generic Markdown sanitizer model. A standalone Node render produced these results:

| Synthetic input | Actual rendered behavior |
|---|---|
| img onerror | onerror removed; remote image URL retained |
| javascript: link | href becomes empty |
| script element | Element is emitted; script did not execute after createRoot in the browser fixture |
| iframe srcdoc containing a parent marker script | srcDoc retained; unsandboxed frame executes parent script |
| style | CSS retained |
| form with external HTTPS action/password field | Form/action/input retained |
| iframe with external HTTPS src | Frame retained |

A local browser fixture bundled React createRoot + ReactMarkdown + rehypeRaw using Next’s installed webpack, then ran:

```sh
'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'   --headless --disable-gpu --no-first-run   --user-data-dir=/tmp/tadabbur-audit-chrome --dump-dom   --virtual-time-budget=1500 file:///tmp/tadabbur-html-browser/index.html
```

The DOM result was `body data-audit-iframe="1"` and `{"iframe":"1","script":"0"}`. The fixture contains synthetic markers only. The [react-markdown maintainers explicitly distinguish its safe default from plugin behavior and recommend sanitization for untrusted plugin output](https://github.com/remarkjs/react-markdown#security).

Minimal browser entry (resolve the imports from this repo’s node_modules and bundle to a /tmp fixture with `<div id="root"></div>`):

```js
import React from 'react';
import {createRoot} from 'react-dom/client';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
const text = '<iframe srcdoc="<script>parent.document.body.dataset.auditIframe=1</script>"></iframe>';
createRoot(document.getElementById('root')).render(
  React.createElement(ReactMarkdown, {rehypePlugins: [rehypeRaw]}, text)
);
```

SSR diagnostic with synthetic Firebase config (no production account/API key or network response): stub global fetch **before dynamically importing Firebase**, return an enabled EMAIL_PASSWORD_PROVIDER reCAPTCHA config, create a synthetic app/auth, then call initializeRecaptchaConfig. Observed output:

```text
CONFIG_PROMISE_RESOLVED
UNHANDLED ReferenceError window is not defined
  @firebase/auth/dist/node-esm/totp-13844f55.js:3371:51
```

The first scratch attempt used an incorrect module path and was corrected. A later attempt stubbed fetch after static imports, so the SDK had already captured its provider and emitted a network failure for a synthetic app; it was interrupted and replaced with the correctly ordered, fully stubbed probe above. Neither attempt used a real account or invoked a production application API. Failed harness setup is not counted as an application finding.

### Summary counts and skipped work

Counts assign each finding once to its primary dimension; shared consequences are not double-counted.

| Dimension | Rating | P0 | P1 | P2 | P3 |
|---|---|---:|---:|---:|---:|
| A. Security | Weak | 0 | 4 | 2 | 0 |
| B. Logic | Critical | 1 | 1 | 9 | 0 |
| C. Performance | Adequate | 0 | 0 | 3 | 0 |
| D. Errors | Weak | 0 | 2 | 4 | 0 |
| E. Privacy | Weak | 0 | 2 | 2 | 0 |
| F. Operations | Weak | 0 | 2 | 1 | 0 |
| G. Maintainability | Adequate | 0 | 0 | 1 | 0 |
| Total | | 1 | 11 | 22 | 0 |

Skipped/unavailable checks and reasons:

- Production attacks, paid generation, load/auth tests, account creation and mutating APIs: prohibited by the task; offline fakes/code proof were used.
- Local backend startup and paid golden/live harnesses: avoided because they initialize production clients or call paid Vertex; offline suite/probes sufficed.
- Secret payloads, secret files, private user documents and private log bodies: prohibited/unnecessary; encryption conclusions come from config names and actual helper behavior.
- Deployed rule contents: metadata GET returned 403; exact follow-up is in section 6.
- Billing budget/quota enforcement: budget API disabled; no service activation/configuration was authorized or performed.
- Exact container SBOM and clean Node 20 Docker rebuild: not retrieved/run; current graph audit and synthetic SSR reproduction are distinguished from deployed-image claims.
- Physical iOS/Capacitor sync, native interception exploit, signing/App Store submission and external-link device behavior: no native build/device action was taken; use a disposable build as specified in section 6.
- Authenticated browser/account-switch reproduction: not attempted on production; ERR-03 is an unambiguous deferred-response code trace with a specified offline test.
- Existing shared snapshot versions/content and external exports/log retention: no user-linked data was read and share GET mutates view counters; metadata-only follow-up remains.
- Fresh Server-Timing breakdown, load/cold-start stress, notification delivery, restore and failover: not measured actively; existing totals/configuration are reported with sample sizes and the needed isolated checks.
- Full repository history secret scan, native binary/static analysis and corpus-wide scholarly/source verification: outside the inspected working-tree/application boundary; no claim of exhaustive secret-history or religious-corpus validation is made.
