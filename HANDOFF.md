# HANDOFF.md — Living handoff between Claude (architect) and GPT 5.6 (main coder)

> Update this file at the end of every working session: what changed, what's verified,
> what's next. Newest entries on top. Architecture & conventions: see `AI.md`.
> Full audit: `docs/AUDIT-2026-08-01.md`.

## Current status (2026-08-29, Claude)

**Everything through Session 7 is MERGED and DEPLOYED.** Production: backend
`tafsir-backend-00269-z5h` (Gemini 3.6, global endpoint, pipeline 15.1) + frontend
`tafsir-frontend-00305-q78`. Verified 2026-08-29: every `codex/*` and `canary/*` branch
tip is an ancestor of `origin/main` (28/28 merged, zero unmerged), so the queue below now
records deployed revisions instead of "awaiting review/deploy". Dev environment moved to
macOS 2026-08-28 (see session log). Open work lives in the 2026-08-29 session entry.

### Historical record — 2026-08-01 outage & recovery

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
4. **Gunicorn/Cloud Run timeout mismatch** — **✅ DEPLOYED 2026-08-01 (merged via `8f36ce2`; rev `tafsir-backend-00260-m9l`)**:
   Gunicorn now uses timeout 300 and `${PORT:-8080}`; the main Gemini call permits two
   total attempts. Worst network budget is `120s + 2s + 120s = 242s`, leaving about
   58 seconds inside the Gunicorn/Cloud Run limit for application overhead.
5. **Frontend: defensive `/tafsir` error handling** — **✅ DEPLOYED 2026-08-01 (merged `8f36ce2`; rev `tafsir-frontend-00302-8ls`)**:
   non-success responses are checked before parsing, JSON backend errors (including
   P1.2's 502) are preserved, non-JSON failures get a status-based message, and fetch
   `TypeError` failures get a friendly connection message. Existing 429 and timeout
   messages are unchanged. The global backend-down banner
   (`codex/s7-backend-banner`) ✅ DEPLOYED 2026-08-14 in `tafsir-frontend-00305-q78`.

### P1-Q — product quality (promoted from docs/QUALITY-REVIEW-2026-08-03.md; Claude-verified)
Q1. **✅ DEPLOYED & P0 VERIFIED IN PROD 2026-08-13 — hadith citation integrity**
    (`codex/q1-hadith-integrity`; rev `tafsir-backend-00262-82w`, pipeline 13.0 cache flush). Review finding 1 was **verified live by Claude**:
    cached 2:255 attributes the Ahmad-version "tongue and two lips" wording to Sahih
    Muslim; Muslim 810 ends at the congratulation). Fix: structured hadith fields
    (collection, canonical ID, grade, exact excerpt, source pointer), containment
    validation against the supplied source excerpts before render/cache, drop+log on
    failure, golden test for 2:255. Requires `SCHOLARLY_PIPELINE_VERSION` bump —
    which auto-invalidates ALL old cached responses, including the bad one.
Q2. **✅ DEPLOYED 2026-08-13 — Guest reflection visibility**
    (`codex/q2-4-quick-wins`; rev `tafsir-frontend-00303-9b6`, incl. `onGuestSignUp` fixup `56c1832`). Removed the `user`
    gate; guests see the question and a “Sign in to save your reflection” CTA.
Q3. **✅ DEPLOYED 2026-08-13 — Cache-hit progress/badges**
    (`codex/q2-4-quick-wins`; rev `tafsir-backend-00262-82w`). Existing idempotent
    set/merge tracking and badge checks now run on authenticated cache hits.
Q4. **✅ DEPLOYED & VERIFIED 2026-08-13 — Timing + cache-status headers**
    (`codex/q2-4-quick-wins`; rev `tafsir-backend-00262-82w`; live + CORS-exposed). `Server-Timing` and
    `X-Cache-Status` now cover every handler path without changing response bodies.
Q5. **✅ DEPLOYED & VERIFIED 2026-08-13 — `/share` integrity**
    (`codex/s6-share`; revs `tafsir-backend-00263-5wb` + `tafsir-frontend-00304-9qr`; live 409-unviewed check passed). Share creation
    now snapshots only a current-version server cache record, rate-limits creation,
    and the public shared page no longer renders raw HTML.
Q6. **✅ DEPLOYED & VERIFIED 2026-08-13 — source-coverage contract**
    (`codex/s6-coverage`; revs 00263/00304; live 2:255 + 30:54 Qurtubi-notice checks passed). Every verse
    answer now carries deterministic classical/additional-source coverage, including
    old cache hits; the UI renders a compact source panel and neutral corpus notice.
Q7. **✅ DEPLOYED 2026-08-13 — verse-first loading + accessibility**
    (`codex/s6-progressive-a11y`; rev `tafsir-frontend-00304-9qr`; covers review finding 11). The canonical
    start verse now renders while commentary loads, with accessible picker labels,
    live status announcements, focus transitions, and Arabic language metadata.
Q8. **✅ DEPLOYED & VERIFIED 2026-08-13 — Continue reflecting recommendations**
    (`codex/s6-recommendations`; revs 00263/00304; 3 recommendations confirmed in live 2:255).
    Deterministic follow-on verses now reach fresh and cached answers and render as
    a three-card continuation path.
Q9. **✅ DEPLOYED & VERIFIED 2026-08-13 — Persona learning contracts**
    (`codex/s6-personas`; rev 00263, pipeline 14.0 cache flush; meaning-first contract visible live). All five personas now
    receive distinct learning behavior plus shared meaning-first and verse-specific
    reflection requirements. Pipeline version is `14.0`.
Q10. **✅ DEPLOYED 2026-08-13 — Curated theme entry point**
    (`codex/s6-themes`; rev `tafsir-frontend-00304-9qr`). The home search surface now
    offers eight editorial themes that lead directly into ordinary verse queries.
Q11+ Review-doc remainders: finding 11 (a11y naming) shipped inside Q7's unit; finding 13
    (output/cache tuning) = the token-cap experiment, now measurable via GEMINI_USAGE — open.
Q12. **✅ DEPLOYED 2026-08-13 — Study-centered streaks and progress**
    (`codex/s6-streaks`; revs 00263/00304). Reflection saves and
    completed reading-plan days now count as daily learning activity; the progress
    page leads with verses studied and reflections written.
Q14. **✅ DEPLOYED 2026-08-13 — Reliability quick wins**
    (`codex/s6-reliability`; revs 00263/00304). The feedback
    cron fails closed without its secret, corrupt onboarding state self-recovers,
    and route render failures show a retry boundary.

### P2 — planned work
6. **✅ DEPLOYED & CANARY-VALIDATED 2026-08-14 — Gemini 3.6 flip**
   (`codex/s7-model-flip` via `canary/s7-flip` + fixes `5127bf4`/`7d19dd1`; rev
   `tafsir-backend-00269-z5h`, pipeline 15.1; `GEMINI_USAGE model=gemini-3.6-flash` in prod logs): defaults and deploy
   configuration now use `gemini-3.6-flash`, `gemini-3.5-flash-lite`, and the required
   global Vertex endpoint. All live call sites share multipart response extraction and
   thinking-safe output budgets; pipeline version is `15.0`.
7. **✅ DEPLOYED 2026-08-13 — Dead code purge**
   (`codex/s6-purge` merged as `11d946c`; revs 00263/00304): removed the unreachable optimized-backend tree, audited
   dead `app.py` helpers and SDK/dependencies, and the re-verified orphaned frontend
   context/API/components/demo/test surface. `RecommendationBar` and
   `ReflectionDetailPanel` remain because Session 6 made/confirmed them live.
8. **✅ DEPLOYED 2026-08-13 — Pin `cryptography`**
   (`codex/p2b-hygiene` + fixup `a6ce590`; rev `tafsir-backend-00262-82w`): explicit `49.0.0` pin
   matches the version the production image resolver installs under pyOpenSSL 26.3.0.
9. **Dockerfile PORT — promoted into P1.4**. The separate option to use `--workers 2`
   on the second CPU remains unimplemented and must be evaluated independently.
10. **✅ DEPLOYED 2026-08-13 — Frontend Suspense boundary**
    (`codex/p2c-suspense`; rev `tafsir-frontend-00303-9b6`): `useSearchParams()` now
    lives in a minimal inner component beneath `<Suspense>`.
11. **✅ DEPLOYED 2026-08-13 (code) — Vercel/Capacitor cleanup**
    (`codex/p2d-capacitor-cors`; revs 00262/00303). **Still open: `npx cap sync ios` +
    a real-device test have never been run against the new config** (needs Xcode on the Mac):
    `capacitor.config.ts` now points the iOS shell at the stable project-number Cloud
    Run frontend URL, and backend CORS no longer permits the dead Vercel origin.
12. **✅ DEPLOYED & VERIFIED 2026-08-13 — Firestore cache TTL field**
    (`codex/s6-coverage`; rev 00263; live v14 doc carried `expires_at`=+90d): new cache documents receive an
    `expires_at` timestamp 90 days after creation. Claude already enabled the TTL policy.
13. **✅ DEPLOYED & VERIFIED 2026-08-14 — Runtime logging + request metrics**
    (`codex/s7-observability`; rev `tafsir-backend-00269-z5h`; REQUEST_METRIC lines flowing): emoji diagnostics now
    use the configured logger, and `/tafsir`/`/share` emit one duration/status/cache line.
    Cloud Monitoring 5xx and permission-denied alerts were already enabled by Claude.
14. **✅ DEPLOYED 2026-08-13 — Verse-range startup hygiene**
    (`codex/p2b-hygiene`; rev `tafsir-backend-00262-82w`): removed the missing-file
    load branch; startup now directly precomputes from the already-loaded tafsir chunks.
15. **✅ DONE 2026-08-13 — Green offline backend suite**
    (`codex/s7-green-tests`; in rev 00269; 379 green re-verified on macOS 2026-08-28): all 378 tests pass
    locally with no skips; UTF-8 scholarly loaders and stale test contracts were fixed.

## Session log

### 2026-09-19 — Codex: Session 9 Unit 1 — Iman retry consistency

- **Branch:** `codex/s9-iman-retry`; **implementation commit:** `2a61719`.
  Changed only the two falsey-Response conditions in `iman_generate_digest` and
  `iman_get_daily_insight` to `response is not None`; no handler restructuring.
- **Verification:** `python3 -m pytest backend/tests -q -W error::DeprecationWarning`
  in `backend/venv` from repo root → **397 passed, 0 skips, 0 warnings**.
  All **51 backend Python files compile**; `git diff --check` clean.
  Four AST-extracted handler tests use real requests.Response objects: each
  429→200 sequence retries exactly once; a third-attempt 503 raises HTTPError,
  which the existing handler catches and returns as 502, without a fourth call
  or a cache write. This preserves the actual terminal behavior.
- **Next:** Claude review; backend-only deploy when separately authorized.
  No deploy, gcloud, secrets, paid calls, dependencies, or pipeline changes.
  Unit 2 is now Ahmed-approved and will be developed separately from `main`
  on `codex/s8-topics`, keeping the reviews independent.

### 2026-09-19 — Claude: Session 8 Unit 1 reviewed, merged, DEPLOYED & VERIFIED

- **Live: backend `tafsir-backend-00270-9fr`** (merge `3d0983a` of `codex/s8-hygiene`).
  Pipeline stays **15.1** — no cache flush, response shape unchanged. Frontend
  untouched (`tafsir-frontend-00305-q78` still current).
- **Review: approved, zero fixups.** Every claim was re-verified independently rather
  than taken on trust:
  * 393 passed under `-W error::DeprecationWarning` (stricter than Codex's
    `-W always` run — proves zero deprecation warnings, not merely that they were
    displayed). Zero `utcnow()` remain repo-wide; all 50 backend files compile;
    `perf_probe.py` collects no tests; git preserved the rename history.
  * Retry control flow traced by indentation rather than from the diff: `break` sits
    at loop-body level (not inside `if generated_text:`), `attempt < max_retries - 1`
    yields exactly one retry, and no path reaches the post-loop code with
    `generated_text` or `final_json` unbound. Budget holds: at most 2 Gemini calls,
    240s (the malformed path deliberately does not sleep).
  * `datetime.now(timezone.utc).replace(tzinfo=None)` preserves naive arithmetic
    against `start` on the following line. Confirmed `timezone` resolves from the
    module-level import at `iman_service.py:11` despite the function-local
    `from datetime import datetime` shadow — the main NameError candidate, and clean.
  * The new `test_tafsir_retry.py` AST-extracts the real `tafsir_handler_enhanced`
    from `app.py` and runs it against a faked namespace, so it tests the shipping
    function rather than a copy. It encodes the P1.4 budget as an assertion
    (`sum(timeouts) + sum(sleeps) <= 242`) and covers the case worth demanding:
    a network failure *after* a malformed response must not get a third attempt.
- **Undeclared but correct behavior change, flagged for the record:** the
  `if response` → `if response is not None` fix at `app.py:6746` is a genuine bug
  fix. `requests.Response.__bool__` returns `status < 400`, so a 429/503 response was
  falsey, `status_code` became 500, and **the 429/503 retry branches were dead code**.
  They now actually execute. Verified empirically. Low risk (still inside the
  two-attempt budget), but it activates a path that had never run in production.
- **KNOWN REMAINING BUG (follow-up, deliberately not widened into this unit):** the
  identical `if response else 500` remains at `app.py:9115` and `app.py:9412`
  (`iman_generate_digest`, `iman_get_daily_insight`), so their 429/503 retry branches
  are still dead. Both sit in the Iman Journal surface, which README documents as
  suspended from shipped navigation — no user impact today, but the codebase is now
  inconsistent. One-line fix each; queue for the next backend unit.
- **Deploy hygiene — both Session 6/7 failure modes explicitly checked and clear:**
  `status.traffic` is 100% on `00270-9fr` with `latestRevision: true` (NOT pinned —
  the Session 7 trap), and the new revision carries the complete env set plus the
  `ADMIN_SECRET` secret ref (the 00261 partial-env incident did not recur).
  **Rollback target: `tafsir-backend-00269-z5h`.**
- **Live verification (all pass):** `/health` healthy (6,720 metadata entries);
  `/daily-verse` returns Arabic; `/tafsir` 2:255 → 200 in 0.58s `hit-firestore`;
  admin lockdown intact after the rebuild (403 without secret, 404 on debug routes).
  **Fresh generation 93:5 → 200 in 17.2s, `X-Cache-Status: miss`**, gemini stage
  16.7s, 1 hadith + 3 recommendations, `extraction_error: None` — this is the
  meaningful check, since a cache hit never touches the restructured parse-inside-loop
  code. Logs confirm **exactly one** `GEMINI_USAGE verse=93:5
  model=gemini-3.6-flash` line (no accidental double-call), no
  `GEMINI_RETRY_MALFORMED` (first response was valid), no errors.
- **Observability caveat:** a malformed response now emits TWO `GEMINI_USAGE` lines
  for one user request. That is accurate — two calls genuinely occur — but the
  token-cap experiment (finding 13) must dedupe per request when it reads this data.
- **BLOCKED — `git push` fails: no GitHub credentials on this Mac.** `main` is 5
  commits ahead of `origin/main` and the merge is local only. `osxkeychain` is
  configured but empty; no SSH keys, and `gh` 2.98.0 was installed to make this a
  one-liner. Ahmed runs `gh auth login` (or adds a PAT), then
  `git push origin main codex/s8-hygiene`. **The deployed image was built from local
  source via Cloud Build, so production is running reviewed code that does not yet
  exist on origin — push soon to close that gap.**
- **Next:** push once authenticated; fix the two Iman `if response` sites; Unit 2
  (`codex/s8-topics`, free-text topic discovery) remains GATED on Ahmed.

### 2026-09-19 — Codex: Session 8 Unit 1 hygiene + bounded malformed-output retry

- **Branch:** `codex/s8-hygiene`. **Implementation commit:** `1bb38d2`
  (`fix: share Gemini retry budget with malformed output recovery`). Based on the
  clean local `main` at `eff769a`; `git pull` reported already up to date. The two
  pre-existing local main commits were preserved. **Not deployed.**
- **Hygiene:** deleted obsolete `backend/test_heading_format.py` without porting
  its assertions; moved the live load script to `backend/scripts/perf_probe.py`,
  preserving its executable body and `__main__` entry. Its module docstring now
  states that requests are live/paid and require ad hoc `pip install aiohttp`.
  `backend/test_verse_extraction.py` and production requirements are unchanged.
- **UTC compatibility:** replaced all five remaining `datetime.utcnow()` call
  sites (one service call and four test fixtures) with `datetime.now(timezone.utc)`.
  Stripped tzinfo to retain naive UTC comparisons and the fixtures' existing
  `isoformat() + "Z"` strings. No stored timestamp formats changed.
- **Resilience:** main `/tafsir` extraction now runs inside the existing two-attempt
  loop. A first extraction fallback consumes the second slot and logs
  `GEMINI_RETRY_MALFORMED verse=<ref>`; another fallback returns the existing 502
  without memory or Firestore cache writes. Network failures and malformed output
  cannot stack a third call: at most two 120s calls and one 2s network backoff
  (242s). Each received Gemini response retains its `GEMINI_USAGE` log.
  Corrected the adjacent HTTP status check to use `response is not None`, since
  requests' 429/503 responses are falsey and otherwise bypass their retry branches.
  Terminal network statuses retain their existing handling. `/debug/test` remains
  single-attempt; pipeline version stays **15.1** and response shape is unchanged.
- **Verification:** from repo root with `backend/venv` activated,
  `python3 -m pytest backend/tests -q -W always::DeprecationWarning` →
  **393 passed (379 + 14), 0 skipped, 0 warnings**. New offline tests execute the
  actual route/parser function definitions with cloud startup excluded and external
  services faked: malformed→valid success/cache/logging, malformed→malformed 502/no
  cache, timeout/429/503 mixed sequences sharing the attempt budget, first-attempt
  success, safety response, and debug single-attempt behavior. All **50 backend
  Python files compile**; AST scan finds zero `utcnow()` calls; `git diff --check`
  passes. Probe body and debug handler verified unchanged.
- **Next:** Claude review, then a **backend-only deploy** when authorized. No deploy,
  gcloud command, secret access, live/paid probe, or new dependency was used.
  **Unit 2 remains GATED and was not started.**

### 2026-08-29 — Claude: queue reconciled to reality, prod health check green, Session 8 proposed

- **Environment:** first working session from the macOS machine (migration recorded
  below, 2026-08-28). gcloud authenticated as ahmedsheik123@gmail.com, project
  `tafsir-simplified`. CLI quirk: the Homebrew gcloud cannot self-install the `alpha`
  component non-interactively, so `gcloud alpha monitoring …` prints an install prompt
  and no data — use the Monitoring REST API with `gcloud auth print-access-token`
  instead (that is how the alert-policy state below was verified).
- **Task queue reconciled.** Cross-checked every queue item against `git log`
  (28/28 `codex/*` + `canary/*` branch tips are ancestors of `origin/main`, zero
  unmerged) and the three merge/deploy session entries. Every P1, P1-Q, and P2 item
  that said "CODE COMPLETE — awaiting review/deploy" actually shipped in revisions
  00260/00262/00263/00269 (backend) and 00302–00305 (frontend); statuses now record
  those revisions. Genuinely still open after reconciliation: P2.9's `--workers 2`
  evaluation, P2.11's iOS `cap sync` + device test, min-instances decision,
  token-cap experiment (finding 13), free-text topic discovery (finding 10),
  Firestore rules review, and the migration cleanup batch (stale root test files,
  `aiohttp`, `datetime.utcnow()` warnings).
- **Prod health check (read-only) — ALL GREEN:**
  - Backend serving `tafsir-backend-00269-z5h` = latestCreated = latestReady,
    traffic `latestRevision: true` at 100% — **no silent pinning** (Session 7's ops
    gotcha is not recurring). Frontend `tafsir-frontend-00305-q78`, same. No deploys
    since Session 7.
  - Serving env confirmed: `gemini-3.6-flash` / `gemini-3.5-flash-lite`,
    `GEMINI_API_LOCATION=global`.
  - Live smoke: `/health` healthy; 2:255 → 200 in 0.8s `hit-firestore`; uncached
    58:12 → 200 in 32.2s `miss` (gemini phase 31.4s), clean structured JSON, 1
    grounded hadith, 4 recommendations, `GEMINI_USAGE model=gemini-3.6-flash
    prompt_tokens=8971 candidate_tokens=1488`.
  - 5xx since Aug 14: **10 total, 9 of them Session 7's own Aug-14 canary probing.
    The single organic 5xx (Aug 20 03:15) is the P1.2 guard working**: Gemini emitted
    12 tokens of non-JSON ("An error occurred while evaluating…"), the handler logged
    "refusing to cache fallback response", returned 502 without caching, and the next
    request (6:14) generated cleanly. Neither alert policy fired (threshold >5/5min);
    both policies verified enabled with the email channel via REST.
  - Hadith telemetry: all 11 `HADITH_INTEGRITY_DROP` events are from the Aug-14
    canary windows — **zero organic drops since 15.1**. `HADITH_COLLECTION_DOWNGRADE`
    fired 4× organically in 15 days (25:74, 40:17, 1:1, 58:12) — the
    downgrade-not-drop design working at low frequency.
  - **Traffic reality: ~7 organic `/tafsir` requests in 15 days** (9 REQUEST_METRIC
    lines post-canary; 2 are this health check), on 3 active days. Frontend ~200
    raw 200s spread across the fortnight. Latency: fresh 17.8–32.0s (median ~20s),
    hits ~0.5s. Both services cold-start from zero instances (observed: 6.3s first
    frontend byte).
  - Token data (6 generations): prompts 8.5–10.3K (one 21.1K outlier on 1:1 —
    richest corpus), candidates 1.2–1.7K against the 65,536 main budget.
  - Billing: BOTH projects linked and enabled on `0152F9-4F49EC-74C075` — the July
    outage cause has not recurred. Vertex vector-index inventory was already
    confirmed empty 2026-08-13. With 6 paid generations in 15 days and
    min-instances=0, spend is effectively pennies; exact dollar figures are not
    CLI-exposed (console check optional).
- **Session 8 proposal (awaiting Ahmed's pick; no implementation started):**
  - **8a — min-instances decision + uptime check** (Claude, XS, no code deploy).
    Data says keep `min-instances=0`: always-on capacity would cost real money to
    erase cold starts almost nobody hits. Add a Cloud Monitoring uptime check on
    `/health` → email, closing the July-outage detection gap (user-report latency).
  - **8b — iOS shell on the Mac** (Ahmed + Claude, M). `npx cap sync ios`, simulator
    run, then device test. Blocked on Windows for months; the Mac migration finally
    unblocks it, and it is the distribution path. Needs Ahmed: Xcode install + Apple ID.
  - **8c — Firestore security-rules review** (Claude audit, S). `backend/firestore.rules`
    has never been Claude-audited against actual client usage; verify what the deployed
    rules in `tafsir-simplified-6b262` actually are and whether client SDK paths can
    bypass the backend.
  - **8d — hygiene + resilience batch** (GPT 5.6, S): delete/replace stale
    `backend/test_heading_format.py`; resolve `backend/test_performance.py` /
    `aiohttp`; fix 10 `datetime.utcnow()` deprecations; add ONE bounded retry on
    malformed Gemini output before the 502 (the only organic prod defect in 2 weeks).
  - **8e — free-text topic discovery** (finding 10, L; GPT 5.6 after Claude
    architecture spec; Ahmed gate). The largest remaining product gap and the most
    likely to make the app shareable; at ~0 traffic, product motion beats infra tuning.
  - Deferred deliberately: token-cap experiment (piggyback the env change on the next
    canary/deploy; candidates ≤1.7K vs 65K budget is pure headroom, and the canary
    procedure costs 12 paid requests — poor value standalone), and P2.9 `--workers 2`
    (meaningless at current traffic).
- **Recommendation to Ahmed:** start with 8b (iOS) as the session centerpiece with
  8a+8c as same-day Claude quick items; queue 8d for GPT 5.6 in parallel; green-light
  the 8e spec if product growth is the goal this month.
- **Ahmed approved ("proceed as you see fit") — Claude items EXECUTED same session:**
  - **8a DONE.** min-instances stays 0 — decision + measured basis recorded in AI.md.
    Created uptime check `tadabbur-backend-health-8GuGMv_lpPY` (`/health`, 900s period,
    60s timeout so cold starts don't false-alarm) and alert policy
    `3972331784810525302` ("/health failing from multiple regions": 2+ checkers
    failing 15+ min → Ahmed's email channel, with a runbook note pointing at billing
    first per 2026 history). Verified live: all 5 checker regions returning
    `check_passed=true`. Three alert policies now enabled in total.
  - **8c DONE (audit + repo fix; prod rules deploy PENDING Ahmed's OK).** Deployed
    rules fetched via the Rules API (needs `x-goog-user-project` header on this
    workstation): `tafsir-db` = deny-all (correct, untouched since 2025-09-21);
    `(default)` = authed users can read/write their OWN `users/{uid}` doc
    (2025-09-13), everything else deny-by-default. **No exploitable hole** — the one
    LOW finding is self-profile writes (fake streaks/badges, corrupt own fields).
    Frontend verified to use `firebase/auth` ONLY (zero client Firestore usage), so
    `backend/firestore.rules` was rewritten to the deny-all target state with the
    audit record and deploy instructions inline. Repo file previously matched
    NEITHER deployed ruleset and referenced nonexistent collections.
    **DEPLOYED 2026-09-19 (Ahmed: "deploy the rules").** Pushed via the Firebase
    Rules REST API (`releases.patch` with a wrapped `{"release": {...}}` body —
    note PUT 404s, PATCH is the working method, and every call needs the
    `x-goog-user-project` header on this workstation). New ruleset
    `f1362022-03d4-4ef5-8bb0-660ec68caa5d` is live on release `cloud.firestore`;
    `tafsir-db` untouched (already deny-all since 2025-09-21). Both databases are
    now deny-all to client SDKs. **ROLLBACK:** repoint release `cloud.firestore`
    at ruleset `d973c40a-60cc-44fe-828f-d4c27778ec55`. Pre-deploy re-verification
    found exactly `firebase/app` (init) + `firebase/auth` (8 call sites) and zero
    Firestore imports anywhere in the repo; the iOS shell carries no native
    Firebase SDK. Post-deploy production smoke test PASSED: `/health` healthy,
    `/daily-verse` returned Arabic text, `POST /tafsir` 2:255 → 200 in 0.62s
    `hit-firestore` with hadith + recommendations intact, frontend 200 — the
    backend's Admin SDK bypasses rules as expected.
  - **8b SIMULATOR-VERIFIED 2026-09-05 (Xcode 26.6 installed by Ahmed; Claude drove
    the rest).** The iOS project is pure SPM (`CapApp-SPM`, no Podfile → CocoaPods
    NOT needed). `capacitor.config.ts` loads the production URL, so `webDir: 'out'`
    is a sync-time placeholder; created a gitignored stub `frontend/out/index.html`
    and `npx cap sync ios` SUCCEEDED (splash-screen + status-bar plugins registered
    in Package.swift; no tracked files changed). Then on 09-05: SPM resolved,
    **`xcodebuild` BUILD SUCCEEDED** for the iPhone 17 / iOS 26.5 simulator,
    installed + launched, and a screenshot confirms the live production app
    rendering correctly in the shell (welcome screen, guest CTA, Firebase Auth
    reCAPTCHA badge, safe-area/notch respected, brand background). Two findings:
    1. **Bundle-ID mismatch — RESOLVED 2026-09-05 (Ahmed: "take care of both"):**
       `capacitor.config.ts` declared `appId: com.tadabbur.app` but the Xcode
       project built `PRODUCT_BUNDLE_IDENTIFIER = com.tafsirsimplified.app`
       (discovered when launching by the config ID failed). No `DEVELOPMENT_TEAM`
       was configured, so there was zero signing/App Store history and the rename
       was free. Both Debug and Release now build `com.tadabbur.app`; grep confirms
       zero remaining `tafsirsimplified` references under `frontend/ios/`
       (`Info.plist` inherits the variable). Rebuilt, old app uninstalled from the
       simulator, new app installed + launched under `com.tadabbur.app`,
       screenshot-verified identical rendering. **Register exactly
       `com.tadabbur.app` as the App ID when the Apple Developer step comes.**
    2. `xcode-select` globally still points at CLT; Claude worked via per-command
       `DEVELOPER_DIR` (sudo needs a password only Ahmed can type). Ahmed runs once:
       `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer`.
    Remaining Ahmed-only: the physical-device test (Xcode → Signing & Capabilities →
    add Apple ID team → plug in iPhone → trust → Run). Simulator left booted.
    Working tree now also carries `frontend/ios/App/App.xcodeproj/project.pbxproj`
    (the two-line bundle-ID alignment) awaiting commit.
  - **8d + 8e specs WRITTEN** into `docs/PROMPT-GPT56.md` as the Session 8 prompt:
    Unit 1 `codex/s8-hygiene` (stale test deletion, `test_performance.py` →
    `scripts/perf_probe.py`, `utcnow()` migration, ONE bounded malformed-output
    retry reusing the second attempt slot within the 242s budget) is ready to hand
    to Codex now; Unit 2 `codex/s8-topics` (deterministic topic discovery, lite
    model closed-set mapping, no vector search) is GATED on Ahmed's explicit go.
  - Still pending Ahmed: physical-device test + bundle-ID decision (8b), OK to
    deploy the tightened default-DB rules (8c), go/no-go on Unit 2 (8e), and the
    commit of this session's working-tree changes (AI.md, HANDOFF.md,
    backend/firestore.rules, docs/PROMPT-GPT56.md, frontend/package-lock.json).
    No code deploys happened; monitoring config was the only cloud change, per the
    approved 8a scope.

### 2026-08-28 — Claude: workstation migration Windows → macOS (MacBook Air, Apple Silicon)

- **New machine.** Development moved off the Windows box (`c:\Users\us88832\Desktop\tadabbur`)
  to macOS 26.6.2 / arm64. Repo now lives at `/Users/ahmeds/Desktop/Tadabbur`.
- **The manual folder copy was incomplete — re-cloned.** The copied folder held only 7
  loose top-level files (AI.md, HANDOFF.md, README.md, cloudbuild.yaml, deploy-backend.sh,
  deploy-frontend.sh, and `gitignore` with the leading dot stripped). No `.git/`, and none
  of `backend/`, `frontend/`, `docs/`, `secret/`. Confirmed by checksum that all 7 were
  byte-identical to `7bbcc15` once CRLF was stripped, so **no local work was lost**.
  Re-cloned from origin; the partial copy is preserved at
  `~/Desktop/Tadabbur-incomplete-copy-backup`.
- **Git verified:** on `main`, working tree clean, `HEAD == origin/main == 7bbcc15`.
  No phantom CRLF modifications — the fresh clone checked out LF. Set
  `core.autocrlf=input` globally (Mac-appropriate); nothing was committed to fix endings.
- **Toolchain:** Homebrew 6.0.19 and Apple git 2.50.1 were already present. Installed
  Node 24.19.0 LTS + npm 11.17.0 (note: plain `brew install node` pulls Node 26 *Current*,
  so it was replaced with `node@24`), Python 3.11.16, and Google Cloud SDK 581.0.0.
- **Dependencies rebuilt from scratch:** new `backend/venv` (all of requirements.txt +
  pytest 9.1.1); `npm install` in `frontend/` clean. No Windows junk to delete — the fresh
  clone had zero `node_modules`, `.next`, `__pycache__`, `.pytest_cache`, venv, or
  `desktop.ini`/`Zone.Identifier` files. Execute bits on the shell scripts came across
  correctly from git.
- **Verified green on macOS:**
  - `pytest backend/tests` → **379 passed** (matches the Session 7 clean signal)
  - `backend/test_verse_extraction.py` (a `__main__` script, not pytest) → 14 passed
  - `npm run build` → all 14 routes compiled, no errors
  - `npm run dev` → ready in 557ms; `/`, `/progress`, `/saved`, `/plans`, `/names` all 200,
    Arabic renders correctly
  - the startup env check at `app.py:164` passes with the new local env file
- **Pre-existing failures found (NOT caused by the migration):**
  - `backend/test_heading_format.py` — 2 of 3 cases fail. The file asserts the old
    `**Title**` → `## Title` behaviour that `utils/text_cleaning.py` deliberately dropped
    in `c7e2511`. It is superseded by `backend/tests/test_text_cleaning.py` (50 cases,
    all green). It also cannot be collected from the repo root — its `from utils...`
    import needs `backend/` as cwd. Should be updated or deleted.
  - `backend/test_performance.py` — cannot be collected: `import aiohttp`, which is not
    in `requirements.txt`.
- **`secret/admin-secret.txt` was lost in the copy, then RESTORED 2026-08-29.** Being
  gitignored, it was not recoverable from origin, so it was re-pulled from Secret Manager
  (`admin-secret` version 2 — the current `latest`; v1 still carries the trailing `\r`
  from Windows openssl and must not be used):

  ```bash
  gcloud secrets versions access latest --secret=admin-secret \
    --project=tafsir-simplified | tr -d '\r\n' > secret/admin-secret.txt
  chmod 600 secret/admin-secret.txt
  ```

  Verified: 64 bytes, no stray CR/LF, sha1 matches the Secret Manager payload exactly,
  mode `600`, ignored by `.gitignore:61` and absent from `git status`. Auth confirmed on a
  scratch instance (port 8081, so the running dev server was untouched): all three
  cache-mutation routes return **403** with a deliberately wrong header — 403 rather than
  503 is what proves `ADMIN_SECRET` is loaded (`app.py:2255`) — and `/debug/range-map`
  returns 404 with `DEBUG_ROUTES` unset. This reproduces the P1.1 posture recorded above.
  The correct secret was deliberately never sent to a cache-mutation route: the local
  backend writes to the same Firestore as production, so a successful `/cache/invalidate`
  would wipe the live tafsir cache.
- **gcloud authenticated — backend verified live on macOS (2026-08-28 17:03).** Ahmed ran
  `gcloud auth login` and `gcloud auth application-default login` as
  ahmedsheik123@gmail.com, plus `gcloud config set project tafsir-simplified`.
  `./backend/run-local.sh` then booted cleanly: Firebase Admin SDK initialized for
  `tafsir-simplified-6b262`, both Firestore DBs connected (`(default)` 2 collections,
  `tafsir-db` 4 collections), all 8 GCS source blobs loaded (2,638 verses → 2,590 flat
  chunks / 6,720 metadata entries; Ibn Kathir 2,146, al-Qurtubi 492), token budgets
  precomputed for 114 surahs / 6,236 verses. The AI.md verification checklist was run
  against `localhost:8080`:
  - `/health` → `status: healthy`, 6,720 metadata entries
  - `/daily-verse` → real verse returned, so the Firestore + billing path is healthy
    (none of the 2026-07 "Verse not found" 403 behaviour)
  - `/personas` → 5 personas
  - `POST /tafsir {"query":"2:255","persona":"curious_explorer"}` → **200 in 0.44s**,
    `X-Cache-Status: hit-firestore` (served from the live prod cache — no Gemini call and
    no spend), `Server-Timing` present, body carrying grounded hadith, `source_coverage`
    with additional sources, `recommendations`, `reflection_prompt`, and
    `extraction_error: None`. The Session 6/7 feature set is intact from this machine.
  - CORS preflight and a GET from `Origin: http://localhost:3000` both return
    `Access-Control-Allow-Origin: http://localhost:3000`, so the browser path from the
    local frontend to the local backend is open.
- **ADC quota project set.** `gcloud auth application-default login` warned
  `Cannot find a quota project to add to ADC`, which risks spurious "quota exceeded" /
  "API not enabled" errors. Fixed with
  `gcloud auth application-default set-quota-project tafsir-simplified`. The backend was
  already running when this was applied, so restart it to clear the in-process
  `UserWarning`.
- **New gitignored local-dev env loading:** `backend/.env.local` carries the backend
  environment — only `FIREBASE_SECRET_FULL_PATH` is genuinely required by the `:164`
  check; every other variable has a safe default in `app.py`. `backend/run-local.sh`
  sources it, injects `ADMIN_SECRET` from `secret/admin-secret.txt` (stripping any
  trailing `\r`, per the P1.1 Windows-openssl note), and starts Flask; it is excluded via
  `.git/info/exclude` so the tracked `.gitignore` stays untouched. It runs Flask with
  `--debug` and forwards extra flags, so `./backend/run-local.sh --no-reload` skips the
  reloader's second corpus load (8 GCS downloads, ~5s) when that startup cost is not wanted. `frontend/.env.local`
  sets `NEXT_PUBLIC_BACKEND_URL=http://localhost:8080` so local work never falls back to
  production — verified baked into the built chunks.
- **Left uncommitted:** `frontend/package-lock.json` (978 insertions) — expected platform
  churn, `@img/sharp-win32-x64` → `@img/sharp-darwin-arm64` and the Next.js SWC binaries.
  Per instruction nothing was committed or pushed, and no deploy script was run. Note that
  `package-lock.json` is listed in `.gitignore` but is already tracked, so that ignore
  rule has no effect on it.
- **macOS differences worth folding into the docs:** the `py -3` / PowerShell invocations
  throughout AI.md and README.md are Windows-only — on this machine use
  `backend/venv/bin/python -m pytest backend/tests -q` and `source backend/venv/bin/activate`.
  `timeout(1)` does not exist on macOS (`brew install coreutils` gives `gtimeout`).
  npm 11 now gates package install scripts: the `sharp`, `protobufjs`, `@firebase/util`
  and `unrs-resolver` postinstalls were skipped, and the production build succeeds anyway.
  The Git-Bash/gcloud-shim workaround described in AI.md and README.md no longer applies —
  the deploy scripts can run directly in zsh once auth is in place.
- **Next:** no blockers remain. The one unverified item is the browser round trip — open
  `http://localhost:3000` with the backend running and confirm the backend-down banner
  stays clear and a verse query renders. It is the only thing not checkable from the
  shell, since the frontend's fetches execute in the browser; everything upstream of it
  (bundled backend URL, CORS for `localhost:3000`, backend 200s) is confirmed.
  Worth queuing separately: delete or update the two stale root-level test files, and
  decide whether `aiohttp` belongs in `requirements.txt` or `test_performance.py` should
  go.

### 2026-08-14 — Claude: Session 7 reviewed, merged, DEPLOYED — **GEMINI 3.6 LIVE**
- **Production: backend `tafsir-backend-00269-z5h` (Gemini 3.6, global endpoint,
  pipeline 15.1) + frontend `tafsir-frontend-00305-q78` (backend-down banner).**
  Confirmed in prod logs: `GEMINI_USAGE model=gemini-3.6-flash`; fresh 18:10 in
  15.3s (faster than 2.5); miss → hit-firestore round trip; REQUEST_METRIC lines
  flowing; 379 offline tests green on main.
- Units 2-5 approved unchanged. Unit 1 approved after canary iteration — TWO
  Claude fixes were required, found only because the canary gate exists:
  1. **Downgrade-not-drop for hadith collection labels** — 3.6 names collections
     diligently; Ibn Kathir names them >24 tokens before the wording, so the
     validator dropped grounded hadith wholesale (canary 2:255 served ZERO
     hadith). Verified text now survives with the unverifiable label stripped
     (`HADITH_COLLECTION_DOWNGRADE` logged). Pipeline bumped 15.0 → 15.1 so the
     hadith-less canary cache docs are never served.
  2. **Array-wrapped JSON guard** — 3.6 wrapped the 112:1-4 range response in a
     JSON array; `.get` on a list crashed the handler (500). Single-element
     object arrays are unwrapped; other non-objects return the no-cache 502.
- Golden regression final: all content scenarios pass (first-run failures were
  the two fixes above + harness proxy-context/token false-positives + my own
  guest rate limit at requests 11-12).
- **Ops gotcha discovered:** traffic had been PINNED to revision 00263-5wb (a
  leftover from earlier canary36 probing), silently absorbing deploys — my
  units-2/3 deploy wasn't actually serving until
  `update-traffic --to-latest`. **Always check `status.traffic` after deploying
  to a service that has ever used tags/pins.** Stale canary/canary36 tags removed.
- Model migration COMPLETE ~2 months before the Oct 16 shutdown. AI.md truth
  table updated. Remaining known work: iOS cap-sync/device test, min-instances
  decision, token-cap experiment (now measurable via GEMINI_USAGE data),
  free-text topic discovery (L), Firestore rules review.

### 2026-08-13 — GPT 5.6: Session 7 Unit 1 — Gemini 3.6 code-side flip
- **Branch/commit:** `codex/s7-model-flip` / `Prepare Gemini 3.6 global model flip`.
- **Endpoint/model contract:** added `GEMINI_API_LOCATION=global` and one shared URL
  builder. Main tafsir, guarded debug generation, correlations, guidance summaries,
  weekly digests, daily insights, and feedback enrichment all use it; `GCP_LOCATION`
  remains unchanged for Firestore/GCS. App/deploy defaults now select 3.6 Flash and
  3.5 Flash Lite, and pipeline `14.0` becomes `15.0`.
- **Thinking compatibility:** correlations/feedback budgets are now 4,096; guidance,
  digest, and insight budgets are 8,192; the main 65,536 budget is unchanged. Every
  Gemini consumer concatenates all non-thought text parts, preserving text parts that
  also carry `thoughtSignature` metadata.
- **Scripts/harness:** `test_live_pipeline.py` and `precompute_scholarly_plans.py` use
  the new model/global defaults and multipart extraction. The golden 2:255 heuristic
  now recognizes fatigue/tiring language from Claude's valid canary response.
- **Old-model grep judgment:** no executable/configuration `gemini-2.5` or `gemini-2.0`
  hits remain. The precomputed-plan `_metadata.model` is immutable generation history;
  `docs/AUDIT-2026-08-01.md` and `docs/PROMPT-GPT56.md` are historical records; older
  HANDOFF entries describe their then-current changes; AI.md's 2026-08-01 decision
  records the pre-migration safety rule. All were deliberately retained.
- **Verified:** changed Python files compile; URL/extraction harness covers global and
  regional hosts, thought skipping, `thoughtSignature`, and multipart concatenation;
  hadith/persona tests pass 7; golden CLI help and `git diff --check` pass. No paid/live
  generation, deploy, GCP, traffic shift, or secret access was performed.
- **Gate:** Claude decides merge/deploy only after the separate no-traffic canary passes.

### 2026-08-13 — GPT 5.6: Session 7 Unit 2 — green backend tests
- **Branch/commit:** `codex/s7-green-tests` / `Make backend test suite deterministic`.
- **Reproduction:** untouched main produced the documented 337 passed / 41 failed.
  Classification found no credential/network, missing-repo-data, or post-purge dead-code
  failures, so no live-test gates, skips, or test deletions were warranted.
- **Root causes/fixes:** 35 scholarly failures were Windows CP-1252 reads of present UTF-8
  JSON, fixed by explicit encoding on all eight loaders. Two routing tests now bypass the
  complete precomputed-plan overlay so they exercise their claimed deterministic paths.
  One fixed-date struggle test and the old 14-behavior default assertion were updated to
  the current clock/minimal-five-prayer contract.
- **Token constants:** history commit `c7e2511` introduced the 2,500 fixed-output reserve
  and 10-verse cap. Tests now follow `config/token_budget.py`, the runtime source of truth:
  input-side components total 27,500 and `ABSOLUTE_MAX_VERSES` is 10; constants were not
  changed.
- **Verified:** `py -3 -m pytest backend/tests -q` exits 0 with **378 passed, 0 skipped,
  10 warnings** in 1.73s; changed Python files compile and `git diff --check` passes.
  The warnings are pre-existing `datetime.utcnow()` deprecations, not hidden failures.
- **Not run:** no GCP/network/live tests, deploy, credentials, or secrets were used.

### 2026-08-13 — GPT 5.6: Session 7 Unit 3 — logger and request metrics
- **Branch/commits:** `codex/s7-observability`; `7a48fda` (`Route runtime diagnostics
  through logging`) plus `Log tafsir and share request metrics`.
- **Commit 1:** replaced every emoji `print` in live `app.py` code with severity-matched
  `logger.info/warning/error` calls, preserving message content without emoji. Raw prompt,
  response, traceback, and parse-context values escape line breaks so one call remains one
  Cloud Logging entry. Startup/non-emoji prints remain; structured `GEMINI_USAGE` and
  `HADITH_INTEGRITY_DROP` log statements are unchanged.
- **Commit 2:** one timer hook stores the start on Flask `g`; one `after_request` hook
  emits `REQUEST_METRIC method=… path=… status=… duration_ms=… cache_status=…` for exact
  `/tafsir` and `/share` paths only. `/health`, shared-link reads, and other routes remain
  noise-free; tafsir's existing perf clock reuses the same start.
- **Verified:** app compiles; a focused hook harness confirms health suppression, one line
  per observed request, cache-header capture, and `none` fallback; grep finds zero emoji
  prints. A disposable combined Unit 2 + Unit 3 worktree passed the full suite: **378
  passed, 0 skipped, 10 existing warnings**; the worktree was removed afterward.
- **Not verified:** exact deployed Cloud Logging rendering/latency. No live calls, deploy,
  GCP access, credentials, or secrets were used.

### 2026-08-13 — GPT 5.6: Session 7 Unit 4 — global backend status banner
- **Branch/commit:** `codex/s7-backend-banner` / `Surface repeated backend outages`.
- **Shared signal/UI:** added a dependency-free module-level failure window and listener
  set plus one layout-mounted client banner. Two fetch rejections within 30 seconds show
  the slim dismissible polite live region; any later HTTP response clears failures,
  auto-hides the banner, and rearms dismissal for a future outage.
- **Scoped wiring:** only profile, daily verse, streak GET, tafsir submit, saved-search
  list, reading-plan catalog, and annotation list report health. A resolved HTTP response
  reports success regardless of status; only fetch `TypeError` counts as unreachable, so
  4xx/5xx, JSON parsing, auth, cancellation, and existing UI error behavior are unchanged.
- **Verified:** a deterministic module harness covers one-vs-two failures, 30-second
  expiry, success reset, and subscription transitions; import/call-site trace confirms all
  seven paths and the single layout mount; `npm run build` exits 0 with all 14 routes.
  The known trailing non-fatal `window is not defined` diagnostic remains.
- **Not verified:** deployed outage/devtools-offline behavior and visual interaction.
  No backend changes, live calls, deploy, GCP access, credentials, or secrets were used.

### 2026-08-13 — GPT 5.6: Session 7 Unit 5 — documentation truth-up
- **Branch/commit:** `codex/s7-docs-truth` / `Refresh documentation after Sessions 5–7`.
- `README.md` now describes the five live personas, guest-visible reflection prompts,
  recommendations, editorial themes, source coverage, suspended Iman UI, and safe shares.
- Its stack/deployment sections now distinguish production pipeline 14.0 from the
  canary-gated Gemini 3/global-endpoint pipeline 15.0 and document the 90-day TTL.
- `AI.md` now maps hadith validation, cache-backed shares, coverage, TTL, alerts, the
  offline suites, and Claude's paid no-traffic golden-canary procedure.
- `docs/AUDIT-2026-08-01.md` remains historical, with a preamble marking P1, Q1–Q7,
  and the Session 6 purge resolved so those findings are not reopened from stale lines.
- **Corrected stale claims:** six personas → five; seven-day cache → 90-day TTL;
  approximately 61% planned coverage → 6,236 plans (6,170 Gemini + 66 deterministic).
- **Code cross-check:** main has 83 Flask routes, pipeline 14.0, TTL writes, coverage,
  grounded hadith validation, cache-backed shares, eight themes, and recommendations.
- Unit 1's branch was separately inspected for 3.6/3.5/global/pipeline-15 values; docs
  explicitly preserve the canary gate rather than presenting those values as deployed.
- **Verified:** docs-only diff, local Markdown links, and every changed factual claim
  against code/config or the precomputed-plan metadata. No code, tests, live calls, or deploy.

### 2026-08-13 — Claude: Session 6 (all 10 units) reviewed, merged, DEPLOYED & VERIFIED
- **Live: backend `tafsir-backend-00263-5wb` + frontend `tafsir-frontend-00304-9qr`.**
  Pipeline 14.0 flushed the 13.0 cache on deploy.
- Review: approved all ten units, ZERO fixups needed this time (prop plumbing and
  pin choices were clean — the session-5 lessons landed). Independently verified:
  persona/hadith tests pass (11 total), `is_rate_limited` signature supports the
  share limiter, purge left zero code references to deleted modules, frontend
  builds, and the full backend suite shows IDENTICAL 41 pre-existing failures on
  main and on the session-6 tree — no regressions (those 41 are env/data-dependent
  + 2 stale constant tests; queued as cleanup).
- Live verification (all pass):
  * Fresh 2:255 under 14.0: miss → 38s; `source_coverage` present (Qurtubi=true,
    no notice needed), 3 `recommendations`, hadith attribution still clean, and
    the reflection prompt is anchored in the verse's own imagery ("does not tire
    Him") — persona meaning-first contract visibly working.
  * 30:54 (post-Qurtubi): `al_qurtubi: false` + notice "Al-Qurtubi is not
    available in this corpus for this verse." + per-source retrieval methods.
  * Share: POST /share for cached 2:255 → share_id, GET → 200; unviewed 48:29 →
    409 "View the verse first". Caller-supplied response bodies are dead.
  * New v14 cache doc carries `expires_at` = +90d (2026-11-12) — the TTL policy
    enabled on 2026-08-13 will reap old docs server-side.
- Remaining queue: Gemini 3.6 flip (Claude, via canary + `golden_regression.py`,
  before mid-Oct); fix 2 stale token-budget constant tests; env/data-dependent
  test suite cleanup; P2.13 logger/metrics remainder; review finding 10's L-sized
  free-text theme search (future).

### 2026-08-13 — GPT 5.6: Session 6 Unit 10 — dead-code purge
- **Branch/commit:** `codex/s6-purge` / `Purge unreachable legacy code`, branched from
  local-only `codex/s6-integration` after merging Units 1–9 in order.
- **Backend deletion:** removed `app_optimized.py`, its exclusive config/model/service
  tree, the migration script, and all audit §6 `app.py` functions after confirming zero
  callers. Also removed four helper functions plus global state used only by that dead cluster.
  The vestigial Vertex SDK import/init had no runtime consumer or required side effect, so
  its two packages were removed with redis/pydantic/pydantic-settings; `cryptography==49.0.0`
  and all live Google Cloud libraries remain.
- **Frontend deletion:** removed the unused `AppContext`, duplicate tafsir API clients,
  25 re-verified orphan components/styles, `/logo-demo`, and the standalone test with no
  runner. `RecommendationBar` is live from Unit 4 and `ReflectionDetailPanel` is imported
  by annotations, so both were deliberately retained.
- **Scope proof:** code-only import/reference scans found no callers of deleted modules,
  components, or `app.py` functions. Unit 9 has a separate script-local function also
  named `validate_response`; it is live and unrelated to the removed Flask helper.
- **Verified:** `py_compile` passed for all 50 remaining backend Python files;
  `npm run build` exited 0 and generated 14 routes (the known trailing `window is not
  defined` diagnostic remains); `git diff --check` and final zero-reference scans pass.
- **Pytest:** the requested hadith + persona + token-budget run completed with 35 passed
  and 2 failed. Both failures are inherited from the integration base: current constants
  total 27,500 versus the test's expected 30,000, and cap ranges at 10 verses versus the
  test's expected 5. Unit 10 changes neither test nor implementation, so this deletion-only
  branch does not repair that separate mismatch.
- **Not run/deployed:** no live API probes, GCP access, secrets, deployment, or browser
  interaction tests. Production cleanup requires backend rebuild and frontend deploy by
  Claude/Ahmed after review.

### 2026-08-13 — GPT 5.6: Session 6 Unit 9 — Golden canary harness
- **Branch/commit:** `codex/s6-golden-harness` / `Add live golden regression harness`.
- **Harness:** `backend/tests/golden_regression.py` sends the fixed six-query set
  (`1:5`, `2:255`, `4:23`, `6:57`, `93:3`, `112:1-4`) for curious-explorer and
  student, prints a pass/fail table, and saves timestamped raw JSON envelopes.
- **Invariants:** valid object JSON; required keys; exactly three lessons; non-empty
  tafsir explanations; source coverage; cache-status header; length, generic-phrase,
  and verse-token reflection checks; all returned hadith accepted by the existing
  validator against the response’s non-empty textual fields.
- **Persona/rate-limit honesty:** the handler derives authenticated personas from
  saved profiles and forces guests to curious-explorer, so separate optional
  `--persona-token` values support a genuine two-persona run and avoid the 10/hour
  guest ceiling for 12 calls. The script warns clearly when tokens are absent.
- **Canary procedure:** top-level documentation covers production baseline,
  no-traffic 3.6/3.5-lite canary, raw comparison, approval, traffic shift, and a
  conditional pipeline bump. No model configuration was changed.
- **Verified:** `py -3 -m py_compile backend/tests/golden_regression.py`, `--help`,
  invariant/call-site trace, and `git diff --check`. Per instruction, the 12 paid
  live requests were not run; no deploy, secret, or model change occurred.

### 2026-08-13 — GPT 5.6: Session 6 Unit 8 — Explore a theme
- **Branch/commit:** `codex/s6-themes` / `Add curated theme exploration`.
- **Catalog:** exported eight curated themes from the picker’s quick-select catalog:
  Patience, Gratitude, Forgiveness, Grief & Hope, Trust in Allah, Prayer, Family,
  and Justice. Added four missing singular quick-select references (`93:3`, `21:83`,
  `20:14`, `29:45`) so grief/hope and prayer have clear editorial entry points.
- **Experience:** choosing a theme reveals three or four verse cards under the
  explicit “Editorial suggestions” label. Each card has a one-line description and
  selection runs the same hidden-form tafsir query path as the existing picker.
- **Scope/verified:** no free-text semantic search, backend, model, or pipeline change.
  Verified all eight catalog IDs and absence of model/semantic additions by grep,
  `git diff --check`, and `npm run build` (exit 0). The known trailing `window is not
  defined` diagnostic remains. No browser interaction test or deploy was performed.

### 2026-08-13 — GPT 5.6: Session 6 Unit 7 — Persona learning contracts
- **Branch/commit:** `codex/s6-personas` / `Define testable persona learning contracts`.
- **Prompt behavior:** `build_enhanced_prompt` now embeds a pure, testable contract:
  revert terminology/action simplicity; explorer context and inquiry; practicing
  worship/character application; student attributed comparison with verse locators;
  advanced rhetoric, disagreements, evidence strength, and uncertainty.
- **Universal quality bar:** every persona must answer the verse’s meaning in the
  first two explanation sentences and derive its reflection question from a concrete
  verse-specific tension, image, contrast, or command. JSON shape is unchanged.
- **Cache/version:** `SCHOLARLY_PIPELINE_VERSION` changed exactly once from `13.0`
  to `14.0`, intentionally invalidating generated-content caches on deploy. No model
  values or hadith instructions changed.
- **Verified:** `py -3 -m py_compile` for app/service/test, version grep, `git diff
  --check`, and `py -3 -m pytest tests/test_persona_prompts.py
  tests/test_hadith_integrity.py -q` (7 passed). Offline only; no generation or deploy.

### 2026-08-13 — GPT 5.6: Session 6 Unit 6 — Study-centered streaks
- **Branch/commit:** `codex/s6-streaks` / `Reward study in learning streaks`.
- **Activity paths:** the existing idempotent streak update runs after the shared
  annotation-save success callback and after a reading-plan `complete_day` response
  succeeds. A streak failure remains non-blocking and cannot undo saved study work.
- **Progress copy:** “Your Quran Learning” now leads with verses studied and
  reflections written from the existing `/progress` and `/annotations/user` data;
  percentage context remains visible and the existing `/streak` count is secondary.
  No spiritual score, quality judgment, or new backend metric was introduced.
- **Verified:** success-path trace for all annotation modes and plan-day completion,
  `git diff --check`, and `npm run build` (exit 0). The known trailing `window is not
  defined` diagnostic remains. No browser interaction test or deploy was performed.

### 2026-08-13 — GPT 5.6: Session 6 Unit 5 — Reliability batch
- **Branch/commit:** `codex/s6-reliability` / `Harden reliability failure paths`.
- **Backend:** `/feedback/daily-summary` now returns 503 when
  `FEEDBACK_CRON_SECRET` is unset and uses constant-time comparison for a configured
  secret, mirroring the existing admin endpoint fail-closed boundary.
- **Frontend:** malformed onboarding JSON is removed and state resets to the shared
  first-run default; `app/error.js` catches route rendering failures and offers a
  friendly “Try again” action through Next.js `reset`.
- **Verified:** `py -3 -m py_compile backend/app.py`, failure-path code trace,
  `git diff --check`, and `npm run build` (exit 0). The known post-build `window is
  not defined` diagnostic remains. No browser localStorage corruption test, live
  endpoint probe, or deploy was performed.

### 2026-08-13 — GPT 5.6: Session 6 Unit 4 — Continue reflecting
- **Branch/commit:** `codex/s6-recommendations` / `Deliver continue-reflecting recommendations`.
- **Backend:** removed the unused user dependency from the deterministic helper,
  attached recommendations before both fresh cache writes, and computes the field
  for old Firestore/memory hits plus direct fallback responses. Guest requests are
  safe because recommendation inputs are response content and local catalogs only.
- **Frontend:** revived `RecommendationBar.jsx` as a null-guarded, maximum-three
  “Continue reflecting” card row; each valid verse card shows a one-line reason and
  runs the normal query flow when selected.
- **Verified:** `py -3 -m py_compile backend/app.py`, response-path trace for fresh,
  Firestore, memory, and fallback success paths, `git diff --check`, and `npm run
  build` (exit 0). The known trailing `window is not defined` diagnostic remains
  after the successful Next.js build. No live probes or deploys were performed.

### 2026-08-13 — GPT 5.6: Session 6 Unit 3 — progressive loading and accessibility
- **Branch/commit:** `codex/s6-progressive-a11y` /
  `Show the verse before commentary`.
- **Progressive path:** submit starts public `GET /verse/<surah>/<start>` before any
  auth-token wait while `/tafsir` proceeds with the same abort signal. Success renders
  Arabic, translation, reference, and the existing commentary skeleton; range previews
  identify the full requested range while showing its start verse.
- **Fallback/cancel:** preview HTTP/network failure is silent and preserves the old
  spinner. User cancel, timeout, retry, defensive response parsing, and history paths
  remain intact; stale preview responses are rejected by controller identity.
- **Accessibility:** the Surah select has a visible label; from/to selects have names
  and a `fieldset`/`legend`. Loading and result regions announce politely; focus moves
  to the verse preview, completed answer, clarification, or error/warning as appropriate.
- **Arabic:** main, progressive, and shared verse text now use `lang="ar" dir="rtl"`.
  `TafsirSkeleton` accepts an optional null-safe display prop so the known verse is not
  replaced by a duplicate verse skeleton.
- **Verified:** `npm run build` exits 0 and generates all 15 routes; selector, endpoint,
  language, live-region, controller, and focus code traces pass; `git diff --check`
  passes. The known trailing non-fatal `window is not defined` print remains.
- **Not run:** browser timing, keyboard, VoiceOver/NVDA, or mobile-device tests. No
  backend changes, live probes, deploy, GCP, or secrets access; frontend deploy required.

### 2026-08-13 — GPT 5.6: Session 6 Unit 1 — `/share` integrity
- **Branch/commit:** `codex/s6-share` / `Secure shared tafsir snapshots`.
- **Backend:** `POST /share` accepts only query/approach, applies optional auth,
  mirrors `/tafsir` profile and approach handling, and reads through the existing
  versioned cache helper including its default-profile fallback. A miss returns the
  requested 409; stored snapshots add pipeline version and normalized query metadata.
- **Abuse boundary:** share creation is limited to 20/hour per authenticated user or
  guest IP using the existing process-local limiter; arbitrary client response data
  is never stored.
- **Frontend:** both call sites send only query/approach and support optional guest
  authorization. The public shared route no longer enables `rehype-raw`.
- **Scope trace:** the main results view still uses `rehype-raw` for generated tafsir
  markup and was deliberately left unchanged; GET `/share/<id>` keeps its old shape.
- **Verified:** `py -3 -m py_compile backend/app.py`, `npm run build`, call-site
  searches, and `git diff --check` pass. The known trailing non-fatal
  `ReferenceError: window is not defined` remains after the successful build.
- **Not run:** Firestore/auth HTTP tests or live probes; no deploy, GCP, secrets, or
  guest-rate-limit calls were made. Claude should deploy backend and frontend after merge.

### 2026-08-13 — GPT 5.6: Session 6 Unit 2 — coverage, TTL, and usage telemetry
- **Branch/commit:** `codex/s6-coverage` / `Expose deterministic source coverage`.
- **Coverage contract:** planner pointers now record `verse_plan`, `keyword`, or
  `surah_overview` provenance. Resolved badges produce `source_coverage` before
  generation; current and older cache hits reconstruct it from the same local plan
  inventory. Al-Qurtubi availability follows the exact 4:22 corpus boundary.
- **Frontend:** a null-guarded “Sources used for this answer” panel folds in classical
  and additional source names and shows a neutral Al-Qurtubi limitation notice.
- **Cache/telemetry:** every newly stored cache document expires 90 days after its
  creation timestamp. Each successful fresh main Gemini response logs prompt,
  candidate, and total token counts from `usageMetadata`; maxOutputTokens is unchanged.
- **Plan inventory:** recount found 6,236 plans: 6,170 with Gemini-origin pointers and
  66 deterministic-only fallbacks. Only `_metadata` changed; all plan entries compare
  byte-for-data equal after JSON parsing. The temporary recount script was removed.
- **Verified:** backend files compile; coverage/boundary assertions pass; frontend
  `npm run build` succeeds with the known trailing non-fatal `window` diagnostic;
  `git diff --check` passes. Scholarly tests pass 73 with two unrelated existing
  assertions deselected (precomputed-plan cap/reasoning expectations).
- **Environment note:** the first Windows run also hit the existing CP-1252 loader
  issue; UTF-8 mode matches production and reaches the results above.
- **Not run:** backend startup, Firestore TTL deletion, HTTP/live, or token-log checks.
  No deploy, GCP, secrets, or guest API calls. Pipeline remains 13.0 per Session 6 rules.

### 2026-08-13 — Claude: gcloud-side P2 items done; session 6 prompt issued
- **Firestore TTL enabled** on `tafsir_cache.expires_at` (DB `tafsir-db`, project
  tafsir-simplified-6b262). No-op until Session 6 Unit 2 ships the `expires_at`
  field (created_at + 90d); then old docs age out server-side.
- **Idle vector-search check: CLEAN** — zero Vertex AI indexes and zero index
  endpoints exist in tafsir-simplified/us-central1. No idle billing; the old env
  IDs were pure leftovers (already removed from deploy script on 2026-08-01).
- **Monitoring alerts live** (project tafsir-simplified, email channel →
  ahmedsheik123@gmail.com, channel 12754084532587087780):
  1. "Tadabbur backend 5xx errors" — >5 5xx responses in 5 min (policy
     9839969195041220396).
  2. "Tadabbur backend PermissionDenied (billing/IAM breakage)" — any occurrence
     of the log-based metric `backend_permission_denied` (policy
     5263098835948754037). This alarm would have caught the July billing outage
     within minutes instead of a week.
  P2.13 remaining scope (logger cleanup, request metrics) stays queued.
- Session 6 mega prompt (Q5-Q7, findings 6/9-14, model-flip harness, purge) added
  to docs/PROMPT-GPT56.md and pushed.

### 2026-08-13 — Claude: all six units reviewed, merged, DEPLOYED & VERIFIED
- **Backend `tafsir-backend-00262-82w` + frontend `tafsir-frontend-00303-9b6` are
  live with Q1–Q4 and P2-A/B/C/D.** Q1–Q4 and P2 items 10/11 above: treat status
  as DEPLOYED.
- Review: approved all six branches with two fixups committed by Claude:
  (1) `onGuestSignUp` was referenced in `EnhancedResultsDisplay` but never passed
  as a prop — guest reflection CTA would have thrown ReferenceError (56c1832);
  (2) cryptography pin 50.0.0 → 49.0.0 (pip backtracks to 49.0.0 under pyopenssl
  26.3.0; 50.0.0 would fail the image build) (a6ce590).
- Independently re-ran the Q1 golden tests (4 passed) and compile checks on the
  merged tree before deploying.
- **P0 VERIFIED FIXED IN PRODUCTION:** pipeline 13.0 flushed the old cache; fresh
  2:255 (31s, X-Cache-Status: miss) now cites all hadith as "As cited in Ibn
  Kathir's tafsir of this verse" with no Sahih-Muslim misattribution; repeat query
  → hit-firestore in 0.3s. Server-Timing + X-Cache-Status live and CORS-exposed.
  No HADITH_INTEGRITY_DROP events logged — model followed the new contract.
- **Deploy incident (self-inflicted, resolved):** first deploy used
  `--set-env-vars` with only the new var, which REPLACES the whole env set —
  revision 00261 shipped with missing env vars (its readiness probe passed
  because gunicorn's master binds the port before workers import the app).
  Redeployed within minutes with the full set (00262). **Lesson recorded: always
  use `--update-env-vars` for incremental changes, and the full-set deploy
  command from deploy-backend.sh otherwise.**
- Remaining queue: Q5 (/share validation), Q6 (coverage contract), Q7
  (progressive loading), review findings 6/9-14, P2.6 model flip (Oct deadline),
  P2.7 dead-code purge, P2.12-14 gcloud-side items (TTL, monitoring — Claude).

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

### 2026-08-13 — GPT 5.6: P2-A Gemini lite model environment prep
- **Branch/commit:** `codex/p2a-model-env-prep` / `Make Gemini lite model configurable`.
- **Changed:** added `GEMINI_LITE_MODEL_ID` beside `GEMINI_MODEL_ID`, defaulting to `gemini-2.5-flash-lite`; the guidance summarizer and feedback enricher now interpolate it into their Vertex endpoints.
- **Deploy config:** `deploy-backend.sh` passes `GEMINI_LITE_MODEL_ID=gemini-2.5-flash-lite`, preserving today's behavior in both default and explicit deploy configuration.
- **Unchanged:** `GEMINI_MODEL_ID` remains `gemini-2.5-flash`; no model was flipped and no pipeline-version bump was made.
- **Verified:** `py -3 -m py_compile backend/app.py` and `git diff --check` pass; trace finds zero hardcoded lite endpoint call sites and exactly two `GEMINI_LITE_MODEL_ID` consumers.
- **Not run:** backend startup or live model calls because the change is configuration plumbing only and undeployed. No live API, deploy, gcloud, Firestore, billing, or secrets access performed.
- **Next:** Claude merges in sequence; the 3.6/3.5 model flip remains a later deploy-time task with live golden-response regression testing.

### 2026-08-13 — GPT 5.6: P2-B dependency and range-map hygiene
- **Branch/commit:** `codex/p2b-hygiene` / `Pin crypto and simplify range budget startup`.
- **Dependency:** added only `cryptography==50.0.0`. A clean dry-run of the existing requirements resolves Firebase Admin 6.5.0 → PyJWT[crypto] and Google Auth's pyOpenSSL extra to cryptography 50.0.0; its Python 3.11 `manylinux_2_34_x86_64` wheel was downloaded successfully.
- **Range map investigation:** `backend/scripts/generate_range_map.py` and `export_range_map()` exist, but the generator downloads seven authoritative tafsir files from GCS and requires cloud credentials. Local source data is incomplete, so generating a trustworthy artifact is not possible under this session's no-GCP rule.
- **Changed:** removed `load_range_map()` from app startup plus the inaccurate static “ground-truth” comments. The existing `precompute_verse_budgets(TAFSIR_CHUNKS, QURAN_METADATA)` path is now the sole startup behavior; no fabricated JSON was committed.
- **Verified:** `py -3 -m py_compile` passes for app, token-budget service, and generator; 25 non-constant token-budget tests pass; `git diff --check` passes.
- **Known pre-existing tests:** the full token-budget file is 28 passed/2 failed because `TestBudgetConstants` still expects `ABSOLUTE_MAX_VERSES == 5` (runtime is 10) and old component totals of 30,000 (runtime sum is 27,500). This branch does not change those constants or tests.
- **Not run:** backend startup or GCS generation. No live API, deploy, gcloud, GCS/Firestore, billing, or secrets access performed.
- **Deployment:** backend image rebuild is required after merge; runtime behavior remains the same fallback computation that already ran on every startup.
- **Claude review fixup:** cryptography pin corrected 50.0.0 → 49.0.0 — the last
  production image build backtracked to 49.0.0 (pyopenssl 26.3.0 constraint), so
  pinning 50.0.0 would have failed the Docker build.

### 2026-08-13 — GPT 5.6: P2-C frontend Suspense boundary
- **Branch/commit:** `codex/p2c-suspense` / `Wrap search params in Suspense`.
- **Changed:** added a small `MainApp` wrapper with `<Suspense fallback={<TafsirSkeleton />}>`; the existing 3,000-line component body moved only by name to `MainAppContent`, where `useSearchParams()` remains.
- **Scope:** no state, effects, props, navigation behavior, or component sections were refactored.
- **Verified:** `npm run build` exits 0 after compiling, lint/type checks, and generation of all 15 pages; `git diff --check` passes. Static trace confirms the only `useSearchParams()` call is under the new boundary.
- **Known print unchanged:** the pre-existing trailing `ReferenceError: window is not defined` still appears after the successful route summary and does not change the exit code.
- **Not run:** browser/device interaction tests because this is an undeployed build-safety change. No live API, deploy, gcloud, Firestore, billing, or secrets access performed.
- **Deployment:** include this branch in the single final frontend deploy after ordered merges.

### 2026-08-13 — GPT 5.6: P2-D iOS/Capacitor and CORS cleanup
- **Branch/commit:** `codex/p2d-capacitor-cors` /
  `Point iOS shell at live frontend`, branched directly from updated `main`.
- **Changed:** `frontend/capacitor.config.ts` now sends the iOS WebView to the stable
  project-number Cloud Run frontend URL instead of the dead Vercel deployment.
- **Changed:** removed the dead Vercel origin from `backend/app.py` CORS and documented
  that the allowlist must contain only currently live frontend origins.
- **Verified:** `py -3 -m py_compile backend/app.py`, `npm run build`, and
  `git diff --check` pass; the build still prints the known non-fatal trailing
  `ReferenceError: window is not defined` after successfully generating all 15 pages.
- **Scope:** no `ios/` changes, Capacitor sync, device test, deploy, or GCP access.
- **Deployment:** Claude/Ahmed should deploy backend and frontend after merge; the
  remote-URL-only Capacitor config change does not require an `ios/` sync in this task.

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
