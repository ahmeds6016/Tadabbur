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
5. **Frontend: `res.json()` before `res.ok`** (frontend/app/page.js:1277 vs :1286) —
   users see raw `Unexpected token '<' …` / `Failed to fetch` when backend errors.
   Parse defensively and show one friendly message. Also add a global backend-down
   banner instead of 31 empty catch blocks rendering empty states.

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
