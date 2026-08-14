# HANDOFF.md — Living handoff between Claude (architect) and GPT 5.6 (main coder)

> Update this file at the end of every working session: what changed, what's verified,
> what's next. Newest entries on top. Architecture & conventions: see `AI.md`.
> Full audit: `docs/AUDIT-2026-08-01.md`.

## Current status (2026-08-01, Claude)

**✅ RESOLVED 2026-08-01 ~18:45 UTC — app is back up.** Billing relinked to
`tafsir-simplified-6b262` (freed a slot by unlinking `tafsir-sandbox` per Ahmed's
instruction; billing account allows max 3 linked projects). Verified live:
`POST /tafsir` 2:255 → 200 (cache hit) and 67:2 → 200 in 17.5s (fresh Gemini
generation, clean structured JSON, no extraction fallback). Historical record of
the outage below.

**App was DOWN July 25 – Aug 1; root cause identified and fixed.**

- Both Cloud Run services are healthy and serving (`tafsir-backend`, `tafsir-frontend`,
  project `tafsir-simplified`, us-central1).
- Every tafsir query fails with `"Verse X not found"` because verse text lives in
  Firestore (project `tafsir-simplified-6b262`, DB `tafsir-db`) and that project has
  **no billing account linked** → all Firestore calls return
  `403 This API method requires billing to be enabled`.
- **It is NOT the Gemini model.** `gemini-2.5-flash` (deployed) works until Oct 16–20,
  2026. The user's report of "model deprecated" was a reasonable but wrong guess.

### ⚡ P0 — the one command that brings the app back (human must run/approve)

```bash
gcloud billing projects link tafsir-simplified-6b262 --billing-account=0152F9-4F49EC-74C075
```

Then verify (see checklist in AI.md). No redeploy needed — the running containers will
start succeeding as soon as billing propagates (minutes).

Cause identified from audit logs: `DisableResourceBilling` on 2026-07-25T20:22Z by
ahmedsheik123@gmail.com — ~3 min after the "Life OS" project was created on the same
billing account. Likely the billing account's linked-project quota forced an unlink
(or it was unlinked manually during Life OS setup). If the link command fails with a
quota error, either request a quota increase on the billing account or unlink an
unused project (candidates: synapse-demo-471205, vertical-karma-471205-j1).

## Task queue (priority order)

### P0 — recovery ✅ DONE 2026-08-01
- [x] Link billing — done (unlinked tafsir-sandbox to free the 3-project quota slot,
      linked tafsir-simplified-6b262; Ahmed approved)
- [x] Verify end-to-end: `/tafsir` 2:255 → 200 cached; 67:2 → 200 fresh generation
      with clean structured JSON. Auth-path endpoints not yet spot-checked from a
      signed-in client — worth one manual smoke test in the browser.

### P1 — do next (high value, low risk)
1. **Lock down unauthenticated destructive/costly endpoints** (backend/app.py) —
   **✅ DEPLOYED & VERIFIED 2026-08-01 (revision tafsir-backend-00258-q55)**:
   without secret → 403 on all 3 cache-mutation routes; debug routes → 404; with
   correct `X-Admin-Secret` → auth passes (400 validation, nothing executed);
   `/tafsir` unaffected. Secret: `admin-secret` v2 in Secret Manager
   (tafsir-simplified), local copy in gitignored `secret/admin-secret.txt`.
   (v1 had a trailing `\r` from Windows openssl — superseded; use v2+.)
   Original finding for the record:
   - `POST /cache/invalidate` (:4058) — anyone can wipe the whole tafsir cache
   - `POST /cache/store` (:3924) — cache poisoning into responses served to all users
   - `POST /cache/prewarm` (:4007) — free LLM spend for anyone
   - `GET /debug/test/<query>` (:7229), `/debug/range-map`, `/debug/verse-metadata` —
     unmetered 65K-token generation + dumps full prompts to logs
   - Suggested: require a shared admin secret header (env `ADMIN_SECRET` via Secret
     Manager) or `@firebase_auth_required` + owner-UID allowlist; return 404 for
     debug routes when env `DEBUG_ROUTES != "1"`.
2. **Fix silent cache poisoning on malformed LLM output** — **✅ DEPLOYED 2026-08-01
   in revision `tafsir-backend-00259-zj6`; code-path verified**:
   the fallback
   dict from `extract_json_from_response` (:3026-3034) is always truthy, so the
   `if not final_json` guard never fires and garbage gets cached forever (memory +
   Firestore). Check `metadata.extraction_error` instead (the `/debug/test` handler
   at :7406 already does this correctly) and return 502 without caching.
3. **Fix guest cache key mismatch** — **✅ DEPLOYED & VERIFIED 2026-08-01 in revision
   `tafsir-backend-00259-zj6`**:
   `user_profile = get_user_profile(None)` returned `{}` for guests, overwriting the
   guest default profile before prompt construction and the Firestore cache write.
   Fixed by refreshing the profile only when `user_id` is truthy.
   **Audit correction:** the in-memory cache key is computed before the overwrite, and
   Firestore lookup retries with the default `practicing_muslim/intermediate` profile
   after a guest-key miss (app.py:4269-4303). Therefore old mis-keyed documents can be
   served via fallback, and not every repeated guest query necessarily incurred an LLM
   call. No old documents were migrated or deleted.
4. **Gunicorn/Cloud Run timeout mismatch** — **CODE COMPLETE 2026-08-01 on
   `codex/p1-4-timeout-stack` (`2f0c4a3`); awaiting review/image rebuild/deploy**:
   Gunicorn now uses timeout 300 and `${PORT:-8080}`; the main Gemini call permits two
   total attempts. Worst network budget is `120s + 2s + 120s = 242s`, leaving about
   58 seconds inside the Gunicorn/Cloud Run limit for application overhead.
5. **Frontend: defensive `/tafsir` error handling** — **CODE COMPLETE 2026-08-01 on
   `codex/p1-5-tafsir-errors` (`58df38d`); awaiting review/frontend deploy**:
   non-success responses are checked before parsing, JSON backend errors (including
   P1.2's 502) are preserved, non-JSON failures get a status-based message, and fetch
   `TypeError` failures get a friendly connection message. Existing 429 and timeout
   messages are unchanged. The global backend-down banner remains a separate future task.

### P1-Q — product quality (promoted from docs/QUALITY-REVIEW-2026-08-03.md; Claude-verified)
Q1. **✅ CODE COMPLETE 2026-08-13 — P0 hadith citation integrity**
    (`codex/q1-hadith-integrity`; awaiting review/backend deploy). Review finding 1 was **verified live by Claude**:
    cached 2:255 attributes the Ahmad-version "tongue and two lips" wording to Sahih
    Muslim; Muslim 810 ends at the congratulation). Fix: structured hadith fields
    (collection, canonical ID, grade, exact excerpt, source pointer), containment
    validation against the supplied source excerpts before render/cache, drop+log on
    failure, golden test for 2:255. Requires `SCHOLARLY_PIPELINE_VERSION` bump —
    which auto-invalidates ALL old cached responses, including the bad one.
Q2. **✅ CODE COMPLETE 2026-08-13 — Guest reflection visibility**
    (`codex/q2-4-quick-wins`; awaiting review/frontend deploy). Removed the `user`
    gate; guests see the question and a “Sign in to save your reflection” CTA.
Q3. **✅ CODE COMPLETE 2026-08-13 — Cache-hit progress/badges**
    (`codex/q2-4-quick-wins`; awaiting review/backend deploy). Existing idempotent
    set/merge tracking and badge checks now run on authenticated cache hits.
Q4. **✅ CODE COMPLETE 2026-08-13 — Timing + cache-status headers**
    (`codex/q2-4-quick-wins`; awaiting review/backend deploy). `Server-Timing` and
    `X-Cache-Status` now cover every handler path without changing response bodies.
Q5. **/share validation** (finding 4): server-side shares only from verified
    response/cache records; schema+sanitize if client snapshots stay.
Q6. **Source-coverage contract** (finding 5): deterministic coverage object +
    "Sources used" UI panel; regenerate stale plan metadata in CI.
Q7. **Verse-first progressive loading** (finding 8): show Arabic+translation
    immediately, skeleton for commentary. After Q4 measurements.
Q8+ Remaining findings (6, 9-14) stay in the review doc; promote after the above.

### P2 — planned work
6. **Gemini migration (deadline mid-Oct 2026)**: `gemini-2.5-flash` → `gemini-3.6-flash`,
   and the two hardcoded `gemini-2.5-flash-lite` sites (app.py:8811, :9970) →
   `gemini-3.5-flash-lite` via a new env var. Steps: make -lite sites env-driven; run
   `backend/tests/test_live_pipeline.py` against 3.6-flash; check JSON-format compliance
   & token limits; deploy with env var flip (no code change needed for the main model);
   bump `SCHOLARLY_PIPELINE_VERSION` if response quality/shape shifts.
7. **Dead code purge** (~2,000 backend + ~4,000 frontend lines): `app_optimized.py` tree
   (+ redis/pydantic deps), dead functions listed in the audit §6, frontend
   `AppContext.jsx`, `tafsirApi.{js,ts}`, 20+ orphaned Iman-journal components,
   `/logo-demo`. One PR, pure deletion, no behavior change.
8. **Add `cryptography` to requirements.txt** (imported at app.py:14, currently only a
   transitive dep — a resolver change breaks startup).
9. **Dockerfile PORT — promoted into P1.4**. The separate option to use `--workers 2`
   on the second CPU remains unimplemented and must be evaluated independently.
10. **Frontend build risk**: `useSearchParams()` without a `<Suspense>` boundary
    (app/page.js:877) — breaks/deopts `next build` on Next 15. Wrap it.
11. **Vercel/Capacitor cleanup**: `tafsir-simplified-app.vercel.app` is 404 (dead), but
    `capacitor.config.ts:11` points the iOS shell at it → iOS app is broken. Point it at
    the Cloud Run frontend URL or resurrect the Vercel deploy; remove the dead origin
    from backend CORS (app.py:98) accordingly.
12. **Firestore cache TTL**: `tafsir_cache` has no TTL and no eviction — enable
    Firestore TTL policy on a `expires_at` field or accept unbounded growth.
13. **Observability**: replace emoji `print()` with the configured `logger`; add basic
    request metrics; set up a Cloud Monitoring alert on 4xx/5xx spikes and on Firestore
    PERMISSION_DENIED (this outage went unnoticed in logs for days).
14. **Repo hygiene**: `verse_range_map.json` referenced at app.py:2649 doesn't exist in
    repo (fallback path always taken) — either ship it or delete the load path.

## Session log

### 2026-08-13 — GPT 5.6: Q1 hadith citation integrity
- **Branch/commit:** `codex/q1-hadith-integrity` / `Document source-grounded hadith validation`.
- **Changed:** `build_enhanced_prompt` now requires structured collection/narrator/in-corpus attribution and verbatim source wording; nested lesson anchors may no longer introduce unvalidated hadith.
- **Validation:** added the pure `services/hadith_validation.py` validator. Normalized 12-word shingles require an 80% match (short 4–11 word items require exact containment); named collections must occur in the 24 words preceding the matched wording, deliberately preferring a safe false negative over a misattribution.
- **Pipeline:** `/tafsir` validates against the exact tafsir + scholarly context supplied to the prompt before post-processing or either cache write, returns an empty list if all items fail, and logs verse/reference/reason for each drop. Kept items retain a display-string `reference` plus additive `collection`, `narrator`, and `attribution` fields.
- **P0 regression:** the fixture where Ahmad's 2:255 “tongue and two lips” wording is labeled Sahih Muslim is dropped because Muslim is not the preceding attribution; verbatim, absent, and empty cases are also covered.
- **Version:** `SCHOLARLY_PIPELINE_VERSION` 12.0 → 13.0, deliberately making all old Firestore cache documents stale on deployment, including the bad 2:255 response.
- **Verified:** `py -3 -m pytest backend/tests/test_hadith_integrity.py -q` (4 passed), `py -3 -m py_compile` for the app/validator/test, and `git diff --check` all pass. Code trace confirms validation precedes filtering and caches.
- **Not run:** full backend startup or HTTP/live tests because these changes are undeployed and startup requires GCP-backed configuration. No live API, deploy, gcloud, Firestore, billing, or secrets access performed.
- **Deployment:** Claude/Ahmed must review, merge, rebuild, and deploy the backend; the version bump will cause regeneration and normal LLM cost as stale verses are requested.

### 2026-08-13 — GPT 5.6: Q2–Q4 quality quick wins
- **Branch/commit:** `codex/q2-4-quick-wins` / `Ship product quality quick wins`.
- **Q2:** guests now see the generated reflection question. The action remains auth-gated: signed-in users open the annotation flow; guests see “Sign in to save your reflection” and return to auth.
- **Q3:** both Firestore-hit paths and the memory-hit path now run `_track_explored_verse` plus `_check_and_award_badges` for authenticated users. The memory lock is released first. Tracking is sequentially idempotent: stored verses become a set and already-tracked verses return without a write; earned badge IDs are also skipped.
- **Q4:** all 21 returns inside `/tafsir` use one `make_response` helper with `X-Cache-Status` (`hit-firestore`, `hit-memory`, or `miss`) and `Server-Timing`; the body/cache object remains unchanged. Added measured classification, verse lookup, scholarly retrieval, prompt, Gemini, post-processing, and total durations.
- **CORS:** `Server-Timing` and `X-Cache-Status` are listed in `expose_headers`, allowing browser JavaScript to inspect them.
- **Verified:** `py -3 -m py_compile backend/app.py` passes; static handler trace finds 21 wrapped and zero legacy `jsonify` returns; `git diff --check` passes.
- **Frontend:** `npm run build` exits 0, compiling and generating all 15 pages. The pre-existing trailing `ReferenceError: window is not defined` still prints after the successful route summary.
- **Not run:** backend startup/HTTP or authenticated Firestore tests because the changes are undeployed and local startup needs GCP-backed configuration. No live API, deploy, gcloud, Firestore, billing, or secrets access performed.
- No pipeline-version bump: response bodies and cache schema are unchanged. Claude should merge after Q1, then include this backend/frontend work in the final consolidated deploys.

### 2026-08-03 — Claude: Phase 2 review validated; P0 confirmed; findings promoted
- Independently verified the P0: fetched live cached 2:255 — first hadith reads
  "Sahih Muslim, narrated by Ubayy bin Ka'b" and includes the "tongue and two lips"
  clause; external sources confirm Muslim 810 ends at the congratulation (the longer
  wording is Ahmad's, exactly as Ibn Kathir distinguishes). Finding stands.
- Spot-verified findings 2 (page.js:3081 guest gating) and 7 (perf_metrics never
  attached). Review quality is high; corrections to my kickoff assumptions (plan
  file now covers all 6,236 verse keys; perf_metrics absent from responses) accepted
  — docs/AUDIT-2026-08-01.md §retrieval numbers are superseded on those points.
- Merged `codex/phase2-quality-review` → main (63b1d33), pushed. Promoted findings
  into new **P1-Q** queue section above (Q1 hadith integrity first; its pipeline-
  version bump conveniently flushes every previously cached response).
- Decision: do NOT hand-purge the bad 2:255 cache doc now — regeneration without the
  validation layer could reproduce the same mislabeling; Q1 + version bump is the
  correct remediation and invalidates everything at once.
- Next: GPT session 4B (P2-A..D engineering batch, already scripted) can run
  anytime; Q1 needs a dedicated session prompt (Claude to write when Ahmed says go).

### 2026-08-13 — GPT 5.6: Phase 2 product-lens quality review
- **Branch:** `codex/phase2-quality-review`; analysis/docs only, with no product code, deploy, gcloud, Firestore, billing, or secrets changes.
- **Deliverable:** added `docs/QUALITY-REVIEW-2026-08-03.md`, ranking 14 findings by impact per effort with evidence and concrete prompt examples.
- **P0:** live 2:255 combined an Ahmad-only addition into a report labeled Sahih Muslim; priority is canonical hadith retrieval/validation plus cached-answer audit.
- **Core UX:** guests are currently denied the generated reflection question; showing it is the highest-value small tadabbur improvement.
- **Coverage:** the plan file now has all 6,236 verse keys, but stale metadata, deterministic fallback, hidden badges, and silently removed al-Qurtubi gaps make coverage opaque.
- **Performance:** long probes took 16.475–28.183s and warm repeats 0.200–0.491s; production omits the `perf_metrics` that code initializes, so stage attribution is not yet possible.
- **Learning loop:** cache hits bypass explored-verse/badge tracking, and generated recommendations are added after cache writes and have no mounted frontend consumer.
- **Verification:** stayed within four conservatively counted potentially uncached generations; traced backend/frontend paths and ran `git diff --check`; browser/device audit was unavailable.
- **Next:** Claude reviews religious-source and architecture findings; Ahmed prioritizes, then selected items are promoted into the task queue before any implementation.

### 2026-08-01 (night) — Claude: P1.4 + P1.5 reviewed, merged, deployed — **P1 COMPLETE**
- Reviewed PRs #32/#33: approved, no changes. P1.4's `sh -c "exec gunicorn …"` is the
  right pattern (env expansion, gunicorn stays PID 1); 242s worst case < 300s checks
  out. P1.5 preserves the 429/timeout branches exactly.
- Merged both to `main` (8f36ce2), rebuilt both images, deployed
  **tafsir-backend-00260-m9l** (readiness pass proves the new CMD/PORT binding works)
  and **tafsir-frontend-00302-8ls** (first frontend redeploy under new workflow).
- Verified live: health 200; cached tafsir 0.4s; fresh 31:18 generation 19.7s;
  admin lockdown intact after rebuild (403 no-secret, 404 debug); frontend 200.
  P1.5's error UX is code-trace-verified (would need forced backend failure to see).
- **DECISION (accepted, recorded in AI.md):** frontend abort stays at 180s even though
  backend worst case is 242s — a >3-min spinner is worse UX than "try again", and the
  backend completes + caches anyway, so a retry after timeout hits cache instantly.
- P2.9's PORT half is done (shipped with P1.4); remaining P2.9 = consider --workers 2.
- **All five P1 tasks are now deployed. Next up: GPT 5.6 Phase 2 product-lens audit**
  (see kickoff prompt §Phase 2 in docs/PROMPT-GPT56.md) or P2 items per Ahmed's pick.

### 2026-08-01 — GPT 5.6: P1.4 timeout-stack alignment
- **Branch/commit:** `codex/p1-4-timeout-stack` / `2f0c4a3`
  (`Align backend timeout budget`), branched directly from updated `main`.
- **Changed:** `backend/Dockerfile` — Gunicorn timeout 120 → 300; bind now expands
  `${PORT:-8080}` through `sh -c`, with `exec` preserving direct signal delivery.
  Worker/thread counts remain exactly 1/8. `backend/app.py` — main Gemini attempts
  reduced from four to two without restructuring the existing timeout/429/503 paths.
- **Budget:** two 120-second request attempts plus the only intervening backoff of
  2 seconds = 242 seconds worst case, leaving about 58 seconds under both 300-second
  Gunicorn and Cloud Run limits for retrieval, prompt construction, parsing, and response.
- **Verified:** `py -3 -m py_compile backend/app.py` and `git diff --check` pass; traced
  timeout, 429, and 503 branches to confirm their existing terminal behavior remains.
  **Not run:** Docker image build/container startup (Docker and local `sh` unavailable),
  full backend startup, or HTTP tests. No deploy or GCP access performed.
- No `SCHOLARLY_PIPELINE_VERSION` bump: response shape/pipeline is unchanged.
- **Deployment:** requires a backend image rebuild and manual deploy by Claude/Ahmed.
  **Next:** publish the P1.4 draft PR, then branch P1.5 directly from updated `main`.

### 2026-08-01 — GPT 5.6: P1.5 `/tafsir` frontend errors
- **Branch/commit:** `codex/p1-5-tafsir-errors` / `58df38d`
  (`Handle tafsir request failures`), branched directly from updated `main`, independently
  of P1.4.
- **Changed:** `frontend/app/page.js` only for application code — the main `/tafsir`
  handler now checks `res.ok` before JSON parsing. On failure it preserves the existing
  429 warning, otherwise parses a backend `error` inside a guarded block and falls back
  to `The server had a problem (<status>). Please try again in a moment.` Network
  `TypeError` failures map to `Can't reach the server — check your connection and try
  again.` Existing abort/timeout handling and failed-query history behavior remain.
- **Code trace:** P1.2's JSON 502 message flows through the guarded error parse and is
  shown verbatim; HTML/non-JSON 502/503/504 bodies use the status fallback; fetch
  rejection uses the connection message; successful responses parse exactly once.
- **Verified:** full `npm run lint` passes. `npm run build` exits 0 after compiling,
  type-checking, and generating all 15 pages, but prints a trailing
  `ReferenceError: window is not defined` after the route summary; left untouched as an
  unrelated existing issue. `git diff --check` passes.
- **Dependency caveat:** initial `npm ci` failed because the checked-in lockfile is
  already missing optional Sharp/resolver packages required by `package.json`.
  Verification used `npm install --no-package-lock`; no package or lockfile changes were
  made. No dependencies were added or upgraded in the PR.
- **Not run:** browser-level forced 502/503/network-disconnect tests. No deploy or GCP
  access performed. P1.5 requires a manual frontend deploy by Claude/Ahmed after merge.
- **Residual timeout mismatch (not changed):** the frontend abort timer remains 180
  seconds (page.js:1248), while P1.4's bounded backend worst case is 242 seconds. The UI
  can therefore abort before the backend's terminal retry response. Aligning that timer
  was outside both scoped fixes and should be explicitly prioritized or accepted.
- **P1.4:** draft PR #32 is open separately. **Next:** publish the P1.5 draft PR for
  Claude review.

### 2026-08-01 (late) — Claude: P1.2 + P1.3 reviewed, merged, deployed
- Reviewed PRs #30/#31: both minimal and correctly placed. Verified GPT's audit
  correction is accurate (Firestore default-profile fallback read exists at
  app.py:4269-4303 — so pre-fix guest queries could hit stale wrong-persona docs
  rather than always paying for an LLM call). Approved both.
- Merged to `main` (85bf12d; HANDOFF session-log conflict resolved keeping both
  entries), built image sha256:30046f62…, deployed revision
  **tafsir-backend-00259-zj6**.
- Verified live: guest double-query on uncached 30:54 → first 200 in 23.1s (fresh
  generation), second 200 in 0.10s (cache hit) on the new revision. Confirmed via
  direct Firestore query: exactly one cache doc for 30:54, profile
  `curious_explorer/beginner` (the guest key), created at the exact completion
  time of the first test request → guest writes and reads are now symmetric.
  P1.2 is code-trace-verified only (cannot trigger malformed Gemini output on
  demand).
- Log-reading gotcha recorded: Cloud Run stdout logs lag ingestion by minutes —
  match request timestamps (httpRequest logs) before attributing stdout lines to
  a test.

### 2026-08-01 — GPT 5.6: P1.2 malformed-response cache guard
- **Branch/commit:** `codex/p1-2-extraction-guard` / `85c0b72`
  (`Reject malformed tafsir responses`), branched from updated `main` after P1.1 was
  merged and deployed.
- **Changed:** `backend/app.py` only for application code — `/tafsir` now checks
  `metadata.extraction_error` immediately after extraction and returns a clean 502
  before post-processing or either cache write. The existing falsy-result guard remains.
- **MAX_TOKENS trace:** `MAX_TOKENS` is accepted at app.py:7153, then generated text is
  extracted at :7161 and parsed at :7164. A truncated response that reaches the
  extraction fallback now returns at :7173-7177, before memory caching at :7212,
  Firestore caching at :7219, and progress side effects at :7221. Prompt line numbers
  had drifted from the audit; behavior matched the report.
- **Verified:** `py -3 -m py_compile backend/app.py` and `git diff --check` pass; the
  handler path was traced directly as described above. **Not run:** full local backend
  or HTTP tests, because runtime dependencies and GCP-backed startup configuration are
  unavailable locally. No deploy or GCP access performed.
- No `SCHOLARLY_PIPELINE_VERSION` bump: successful response shape/pipeline is unchanged.
- **Next:** publish the P1.2 draft PR, then branch P1.3 from updated `main` and preserve
  the guest default profile through prompt construction and cache writes.

### 2026-08-01 — GPT 5.6: P1.3 guest profile preservation
- **Branch/commit:** `codex/p1-3-guest-profile` / `53634e9`
  (`Preserve guest tafsir profile`), branched directly from updated `main` as a separate
  PR from P1.2.
- **Changed:** `backend/app.py` only for application code — the later profile refresh is
  now guarded by `if user_id`, so guests retain `curious_explorer` / `beginner` for the
  prompt, persona limits, and new Firestore cache writes. Signed-in behavior is unchanged.
- **Path trace:** guest defaults are set at app.py:6892-6896 and used for Firestore read
  at :6906 and the memory key at :6927; the new guard at :7057 preserves them through
  prompt construction at :7080, persona handling at :7188, memory storage under the
  already-computed key at :7207, and Firestore storage at :7214.
- **Audit correction:** the memory cache was already symmetric because its key was
  computed before the clobber. Firestore also has a default-profile fallback at
  app.py:4269-4303, so old mis-keyed documents are not guaranteed to be unread and can
  prevent some repeat LLM calls. The scoped fix still corrects persona selection and all
  newly generated Firestore keys. No cache migration/deletion was performed.
- **Verified:** `py -3 -m py_compile backend/app.py` and `git diff --check` pass; the
  guest and signed-in paths were traced directly as described above. **Not run:** full
  local backend or HTTP tests, because runtime dependencies and GCP-backed startup
  configuration are unavailable locally. No deploy or GCP access performed.
- No `SCHOLARLY_PIPELINE_VERSION` bump: response shape is unchanged.
- **P1.2:** draft PR #30 is open separately. **Next:** publish the P1.3 draft PR for
  Claude review; deployment remains Ahmed's manual step after approval/merge.

### 2026-08-01 (evening) — Claude: P1.1 merged, deployed, verified
- Merged `codex/p1-1-admin-endpoints` → `main` (66db496); pushed all branches.
- Created `admin-secret` in Secret Manager (v2 is the good one; v1 had a trailing
  CR from Windows openssl output), granted accessor to the runtime SA, mounted via
  `--set-secrets` (now also in deploy-backend.sh).
- Built + deployed revisions 00257/00258. Verified live: 403 without secret on
  cache mutation routes, 404 on debug routes, auth passes with secret, `/tafsir`
  2:255 → 200. Cloud Run `--timeout 300` confirmed in the deploy flags.
- NOTE for whoever runs deploys: `deploy-backend.sh` does NOT work from Git Bash on
  this machine (gcloud needs Python; the bash shim hits the MS Store stub). Run the
  `gcloud builds submit` + `gcloud run deploy` steps in PowerShell instead.
- **GPT 5.6: P1.1 is fully closed. Proceed to P1.2** (cache-poisoning guard),
  branch from updated `main`.

### 2026-08-01 — Claude (architect): P1.1 review — APPROVED
- Reviewed `codex/p1-1-admin-endpoints` (bca7bdb, +47 lines app.py only). Verified:
  constant-time compare (`hmac.compare_digest`), fail-closed 503 when `ADMIN_SECRET`
  unset (`logger` confirmed defined at app.py:23), debug routes 404-hidden unless
  `DEBUG_ROUTES=1`, correct decorator order under `@app.route`, all 6 target routes
  covered, read-only cache routes intentionally left public, no response-shape change
  (no pipeline-version bump needed). No changes requested.
- **Changed:** `deploy-backend.sh` — added `--set-secrets "ADMIN_SECRET=admin-secret:latest"`.
- Deploy prerequisites for Ahmed (before merging + deploying this branch):
  1. Create the secret in the infra project (generate a long random value):
     `gcloud secrets create admin-secret --data-file=- --project tafsir-simplified`
  2. Grant the Cloud Run runtime service account access:
     `gcloud secrets add-iam-policy-binding admin-secret --project tafsir-simplified
      --member serviceAccount:612616741510-compute@developer.gserviceaccount.com
      --role roles/secretmanager.secretAccessor`
  3. Leave `DEBUG_ROUTES` unset in production.
  Note: deploying WITHOUT the secret is still safe — admin routes fail closed (503).
- GPT 5.6: proceed to P1.2 (cache-poisoning guard), branch from `main` or stack on
  the P1.1 branch if merge is pending — note which in your session entry.

### 2026-08-01 — GPT 5.6: P1.1 admin endpoint lockdown
- Created branch `codex/p1-1-admin-endpoints` from `main`; preserved Claude's existing
  uncommitted `deploy-backend.sh`, `AI.md`, `HANDOFF.md`, and `docs/` work.
- **Changed:** `backend/app.py` — added constant-time `X-Admin-Secret` validation backed
  by `ADMIN_SECRET`; protected `POST /cache/store`, `/cache/prewarm`, and
  `/cache/invalidate`; made all three `/debug/*` routes return 404 unless
  `DEBUG_ROUTES=1`, with the same admin-secret requirement when enabled.
- **Caller compatibility:** no in-repo callers use the six protected routes.
  `/feedback/daily-summary` was deliberately left unchanged and retains its separate
  `X-Cron-Secret` contract. Any external cache-prewarm scheduler must add
  `X-Admin-Secret`.
- **Verified locally without GCP access:** `py -3 -m py_compile backend/app.py` passes;
  an AST-loaded guard harness verified missing server config → 503, missing/wrong
  header → 403, matching header → 200, debug disabled → 404, and all six decorator
  placements. `git diff --check` passes apart from the pre-existing LF/CRLF warning.
- **Untested:** full backend startup and HTTP smoke tests (local dependencies and GCP
  credentials are not configured). Ahmed must create/configure a Secret Manager value
  as Cloud Run env `ADMIN_SECRET`, then manually deploy and run the `AI.md` checklist.
  Leave `DEBUG_ROUTES` unset in production. No `SCHOLARLY_PIPELINE_VERSION` bump: the
  tafsir response shape and pipeline are unchanged.
- **Next:** P1.2 — reject malformed Gemini extraction fallbacks before either cache
  tier is written.

### 2026-08-01 (later) — Claude: outage resolved
- Billing state now: linked = `tafsir-simplified`, `tafsir-simplified-6b262`,
  `life-os-prod-8832`; unlinked = `tafsir-sandbox` (freed the quota slot; was the only
  other linked project — remaining projects were never linked). Sandbox will lose any
  billable resources until relinked; it appeared inactive.
- App verified recovered (cache hit + fresh Gemini generation both 200).

### 2026-08-01 — Claude (architect): takeover audit
- Cloned repo fresh to `c:\Users\us88832\Desktop\tadabbur`; full cloud + code audit.
- Root-caused outage to unlinked billing on `tafsir-simplified-6b262` (Firestore 403s
  since at least 2026-07-29 per Cloud Run logs). Gemini model NOT the cause.
- Verified live: `/health` 200, `/personas` 200, `/daily-verse` 200 (in-memory data),
  `POST /tafsir` → `"Verse not found"` (Firestore-backed), Vercel frontend 404 (dead).
- Confirmed model timeline: 2.5-flash retires 2026-10-16/20; `gemini-3.6-flash` is the
  GA migration target; `gemini-2.0-flash` (old deploy-script pin) already retired.
- **Changed files:** `deploy-backend.sh` (model pin `gemini-2.0-flash` → `gemini-2.5-flash`;
  removed 3 dead vector-search env vars). **Created:** `AI.md`, `HANDOFF.md`,
  `docs/AUDIT-2026-08-01.md`. Nothing committed/pushed yet; nothing redeployed.
