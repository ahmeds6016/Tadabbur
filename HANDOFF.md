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

### 2026-10-21 — Codex: Session 14 review follow-ups (NOT deployed)

- Branch: `codex/s14-followups`, from current `main` after `git pull --ff-only`.
  Read Claude's Session 13 review and both `97a107d` / `dd90eda` messages; preserved their fixups.
  No deployments, cloud calls, paid calls, dependencies, migrations, or secret reads.
- Verification: **659 backend tests, 29 frontend tests, build 15/15, lint zero warnings/errors**.
  `bash -n` on both deploy entrypoints and common script; `git diff --check` clean.
- Badge awards now travel as IDs in `X-Newly-Earned-Badges`, exposed by CORS, on the
  requesting authenticated reader's response only (`private, no-store`, `Vary: Authorization`).
  The UI resolves display metadata from `/badges`; stale requests cannot set the popup.
  Fresh generation, Firestore/memory hits, guest access, and public shares are tested:
  personal awards never enter the answer, either cache write, or public share snapshot.
- Study tracking calculates badges in the same user transaction. Standalone badge checks
  skip writes when awards/count are unchanged. Collection completion recognises the union of
  global exploration and collection progress. `/progress` runs an index count in its user
  transaction on every read and repairs drift, writing only when the stored count differs.
- Annotation cursors retain mode, submitted query, and filters together, including cursor
  repair after deletion. The save picker follows all folder cursors and deduplicates names.
- Parser table covers `2:255 and 256` as 2:255–256 and bare `Al-Fatihah` as requiring a verse
  choice. Cross-surah, invalid, reversed, and extra `and` references require clarification.
- Real verse lookup failures propagate through Flask's registered error handler for `/verse`
  and `/tafsir` (single and range), with safe 503 copy, retry flag, correlation ID, and
  `Retry-After`. The frontend has stable 503 copy. Deployment tests assert every backend
  environment/secret pair and no such frontend flags. Offline mutations removing a required
  environment variable or encryption-secret binding both fail those assertions.
- Both deploy scripts now tag the created revision, verify its exact digest/readiness/traffic
  and matching tag URL, then curl that URL's `/health`. HTTP must be 200 and JSON status
  `healthy`; redirects, non-JSON, unhealthy bodies, connection/HTTP failures, or wrong/missing
  tags fail the command. Verification failure prevents curl. All executions in tests use
  PATH stubs for **both gcloud and curl**. Frontend `/health` is dynamic and uncached; its
  TypeScript route avoids Next 15's unused generated imports for a JavaScript route.

| Item | Commit | Regression test | Deploy needed |
| --- | --- | --- | --- |
| 1. Badge popup | `34a5f78`, `d9d6aa5` | `test_real_boundaries.py`, `test_tafsir_retry.py`, `search-races.test.cjs`: header/CORS/cache/share isolation and popup | backend + frontend |
| 2. Search Load more | `f2dd003` | `annotation-paging.test.cjs`: edited/cleared draft and list filters | frontend |
| 3. Folder picker | `f6047ac` | `search-races.test.cjs`: second folder page and duplicate names | frontend |
| 4. Collection backfill | `750ea8d`, `eba6f8c`* | `test_collection_badges_backfill_from_explored_verses` | backend |
| 5. Badge writes | `750ea8d`, `eba6f8c`* | unchanged checks do not write; study awards use one transaction | backend |
| 6. Badge total | `750ea8d`, `eba6f8c`* | retired badge IDs excluded from total | backend |
| 7. Count drift | `750ea8d`, `eba6f8c`* | stale/missing counts repaired; unchanged reads do not write | backend |
| 8. Parser | `46d7817` | parser compatibility table and invalid/ambiguous `and` ranges | backend |
| 9. Missing coverage | `ecc09f1` | real Flask 503 handler, frontend copy, exact env/secrets; configuration mutations | backend + frontend |
| 10. Hook lint | `c4acf92` | ESLint regression plus account/search race tests | frontend |
| 11. Health smoke | `61f4551` | 52 deploy stub cases; frontend health response test | frontend (scripts apply to both services) |

* Concurrent workspace commit `750ea8d` (privacy notice with Ahmed's decisions) captured the
  Session 14 accounting edits before my test commit; preserved that commit and recorded the
  regression tests separately in `eba6f8c`. A subsequent, nonfunctional `deploy-frontend.sh`
  comment edit from the concurrent writer remains unstaged; Session 14 did not alter it.

Next: Claude reviews this branch and owns any later canary/deployment, following the existing
backend-before-frontend and traffic-switch prerequisites. Health smoke is a future deploy
step; it has not been run against production in this session.

### 2026-10-20 — Claude: Session 13 reviewed and MERGED with fixups (NOT deployed)

- **Merged** `b1daded` (six stacked GPT 6 units + Claude fixups `97a107d`, `dd90eda`).
  605 backend tests, 22 frontend tests, build 15/15. **Nothing deployed.**
- **Review split:** Claude reviewed Units 1 (content), 2 (surface), 4 (privacy); three review
  agents took Units 3, 5, 6 in isolated worktrees. All four verdicts: approve with fixups. The
  agents confirmed by mutation that the new boundary tests bite (removing an auth decorator or
  breaking cache identity fails them) and that existing readers' annotation counts are seeded
  from real data, not zero.
- **Deploy blocker found and fixed (Claude):** `valid_answer_contract` required
  `verses[].surah` to be a string; post-processing stores the surah number. Run against 12 real
  Gemini answers (3.6 baseline + 3.8 canary): **12/12 failed**. In production every cache read
  would have missed (every request a paid ~27s regeneration) and shares would have failed.
- **Other fixups:** verified-only attribution recognised only `--- IBN KATHIR ---` headings, so
  Riyad al-Salihin / Asbab al-Nuzul / Ihya / Madarij / thematic hadith all became "As cited in the
  supplied source excerpts" — now named correctly (still never model-written); stuck Share button
  after a failed share; completed reading plans could not be restarted; last viewed answer
  survived sign-out into the next account's session (now owner-scoped); six paging handlers
  returned raw `ValueError` text; guard tests on the REAL `/debug/` and `/cache/` handlers; deploy
  preflight refuses a normal deploy when traffic is pinned (as after a `--no-traffic` canary);
  per-item delete tickets and cursor repair on list pages; remaining exclamation marks removed;
  non-tafsir approaches now return a 400 instead of a 500 on an unparseable query.
- **Parser rewrite verified** against every format the old parser supported (side-by-side
  table): all preserved; "Al-Fatihah 7" now 1:7. Known small regressions queued in Session 14:
  "2:255 and 256" is now a single verse; "Al-Fatihah" alone no longer opens 1:1 (it only ever did
  via an accidental substring match).
- **Session 14 issued** (`docs/PROMPT-GPT56.md`) for non-blocking follow-ups: badge popup no
  longer fires, search Load-more mode, folder picker paging, collection badge backfill, badge
  write skipping, `/badges` total, count drift repair, the "and" range, missing tests (real 503
  path, deploy env/secret flag assertions), lint warnings, post-deploy `/health` smoke.
- **Deploy prerequisites (in order):**
  1. **Ahmed:** privacy page details — contact address, deletion-marker retention, policy for
     public shares after account deletion, operational log retention. The page is linked from
     the sign-in screen and currently titled "draft for owner review", so **the frontend cannot
     ship until this is settled.**
  2. **Claude:** create `reflection-encryption-key` (random 32+ bytes) in Secret Manager and grant
     the runtime service account `secretAccessor` — `deploy-backend.sh` now fails without it.
     Losing this key later would make encrypted reflections unrecoverable; never delete versions.
  3. **Claude:** pipeline 17.0 canary (`deploy-backend.sh --no-traffic` + golden harness, ~6
     paid calls). Cache keys now include the version, so the canary can no longer overwrite
     production documents. Also verify ProxyFix on the canary with spoofed `X-Forwarded-For`
     (cached verses, zero cost).
  4. **Backend before frontend** (new frontend against the old backend breaks streak recording
     and reflection counts; old frontend against the new backend shows 0 reflections on progress
     temporarily). Switch with `--to-revisions`, verify, then `--to-latest` (the canary pins
     traffic; the new preflight enforces this).
  5. **Ahmed:** budget alert amount; Claude sets it with a Vertex quota cap.
  6. Not before Ahmed approves: running `scripts/encrypt_existing_reflections.py` (dry run
     first) on existing plaintext reflections.

### 2026-10-20 — Codex: Session 13 Unit 6 — deploy verification and real boundaries

- Branch `codex/s13-verification`; implementation **`9dc4ca6`**, stacked on Unit 5 and containing all six units. Both deploy entrypoints build unique tags, obtain the exact successful build digest, deploy by digest with an explicit revision suffix, capture the created revision and verify image/readiness/reconciliation/retirement/actual resolved traffic. Normal deploys require 100%; `--no-traffic` requires a ready tagged 0% canary. Wrong latest, pinned traffic and retired revisions fail with exact diagnoses. Verification never changes traffic. **22 stubbed-gcloud entrypoint scenarios pass; no real deploy ran.**
- Real route fixtures retain decorators/parser/cache/share helpers with fake clients: guest/required/admin/debug/cron boundaries, cache hits through /tafsir, profiles/versions/syntax identity, invalid references, server-only share snapshots, public legacy snapshots and deletion markers. Added actual frontend handler regressions for search timer/loading ownership, late share promises, and A/B/A onboarding completion.
- Verification-driven follow-ups: debug generation cannot write the reader cache; share entry validates input; served tafsir suggestions are canonical; bare collection labels cannot survive as narrators; scholarly excerpt boundaries prevent inheriting the wrong source attribution; migration rejects unreadable legacy ciphertext; feedback mail errors omit raw recipient-bearing messages; late onboarding/annotation changes and persisted answer queries retain ownership. The 0.80 wording threshold remains untouched.
- **Final checks: 571 backend tests, 18 frontend tests, build 15/15, shell syntax and diff checks pass.** No window-is-not-defined error. Exact commands, source links and limitations: `docs/SESSION-13-VERIFICATION.md`. Unit 6 also contains backend/frontend follow-up fixes, so both need deployment.
- **All six implementation units completed locally; no unit skipped or ballooned.** No push, deployment, cloud mutation, live application/model call, secret creation/access, account erasure or migration execution. Claude still owns the encryption secret, budget/quota cloud controls, pipeline-17.0 paid canary, proxy-hop smoke check and all deployment. Ahmed must review the privacy draft/contact, public-share policy and deletion-marker retention. Dependency scan debt remains as recorded in Unit 2; native rebuild is separate. Existing snapshots predate trust fixes. LOG-09/10 and PERF-03 remain explicitly out of scope; OPS-01 cloud protection was not redone (restore drill/runbook remain Claude's follow-up).

| Unit | Branch | Implementation commit | Findings addressed | Verified | Deploy needed |
|---|---|---|---|---|---|
| 1 | `codex/s13-content` | `0c461d7` | LOG-01–05; SEC-01/02; ERR-02 | 485 backend, 12 frontend, build 14/14 | backend + frontend |
| 2 | `codex/s13-surface` | `c6a27e7` | SEC-03/05/06; requested SEC-04 patches; OPS-03; Iman gate | 494 backend, 12 frontend, build 14/14; audits recorded | backend + frontend |
| 3 | `codex/s13-client` | `4cd77ae` | ERR-01/03–06; LOG-11 | 497 backend, 15 frontend, build 14/14 | backend + frontend |
| 4 | `codex/s13-privacy` | `df5bba4` | PRIV-01–04 code and privacy draft | 501 backend, 15 frontend, build 15/15 | backend + frontend, after prerequisites/review |
| 5 | `codex/s13-progress` | `64963db` | LOG-06–08; PERF-01/02 | 524 backend, 15 frontend, build 15/15 | backend + frontend |
| 6 | `codex/s13-verification` | `9dc4ca6` | OPS-02; MAINT-01; boundary follow-ups | 571 backend, 18 frontend, build 15/15; 22 deploy scenarios | backend + frontend |

Each branch includes its predecessor's code and handoff commits; the commits above identify implementation changes. The final branch is the complete review stack.

### 2026-10-20 — Codex: Session 13 Unit 5 — progress and bounded reads

- Branch `codex/s13-progress`, implementation `64963db`, stacked on Unit 4. Explored maps/counts, collections, plans, streak updates and badge awards use Firestore transactions. Study transactions also derive collection progress from canonical verse membership, making collection badges reachable through normal study. Transactions read deletion markers before writes.
- Plan days require non-boolean integers within the plan before any transaction. Completion is idempotent; current_day is the first incomplete day, so out-of-order completion/retries do not rewind. Repeated start preserves existing progress. Removed advertised comeback/daily-verse/first-week badges because those events are not recorded; retained activity badges use counts, never journal-content inference.
- Annotation create/delete and maintained annotation_count commit together; repeated deletion cannot decrement twice. Legacy counts seed once through a server index count aggregation, not full annotation document streams. One bounded badge check per backend study event. Frontend streak refreshes now GET, avoiding duplicate checks.
- Saved/history metadata, reflection candidate searches/lists, folder and tag metadata use bounded cursor pages. Saved lists project out full snapshots; an owner-scoped GET and explicit View saved answer load a snapshot on demand. Cursor reads project only ordering fields. Client Load more actions retain UID/generation guards. Progress uses the maintained reflection total instead of fetching 500 reflections. Each request reuses a surah snapshot, so catalog loops read each surah once.
- Offline verification: **524 backend tests**, **15 frontend tests**, build **15/15**. Regressions cover concurrent study writes, completion/retry ordering, highest reflection badge, one-time aggregation, exact annotation counts, deletion markers, projected/scoped pagination and per-request surah reads. Firestore transaction/aggregation behavior follows the installed SDK; no live Firestore/emulator call was made. Backend + frontend deploy needed.
- LOG-09/10 remain out of scope behind the Iman gate; PERF-03 remains accepted/deferred at current traffic. No deployment/cloud mutation.

### 2026-10-20 — Codex: Session 13 Unit 4 — private data

- Branch `codex/s13-privacy`, implementation `df5bba4`, stacked on Unit 3. Missing production encryption secret logs a startup warning without crashing. New reflection ciphertext has `fernet:v1:` prefix; reads accept legacy plaintext and unprefixed Fernet. Versioned ciphertext fails safely if a key is unavailable. Migration `backend/scripts/encrypt_existing_reflections.py` is dry-run by default, recognizes already migrated fields and uses update-time preconditions. **Migration was not run.** Tests imported pure helpers only.
- Deploy script references `REFLECTION_ENCRYPTION_SECRET=reflection-encryption-key:latest`. **Claude must create the secret before the next backend deploy**, then review/dry-run/apply the migration separately. Keep the key stable; no key rotation protocol is introduced here.
- Settings now requires password reauthentication and literal DELETE confirmation. `/account/delete` creates a hashed-UID status marker, rejects new account work, waits 305 seconds for previously admitted requests under the 300-second service deadline, erases at most 100 records per call, recursively walks even missing document parents, removes account-linked feedback, and removes Firebase Auth last. Retries resume after partial failures. Browser Firebase state, UID onboarding and session answer state are cleared on success. Minimal deletion markers remain for retry/late-write protection; their retention/cleanup policy needs owner review.
- Shares still have **no owner field**. No share-removal policy was invented. Proposal for review: attribute future signed-in shares and provide revocation; explicitly decide how to handle legacy/guest anonymous scholarly snapshots and pre-existing external feedback copies. This is not implemented or promised by the erasure route.
- Operational tafsir logging uses canonical references/status/request IDs; feedback bodies, enrichment titles, summary bodies and recipient emails are no longer emitted by routine feedback logging. Public shares now store canonical queries. `/privacy` is a serious **draft for Ahmed review**, linked from auth and Settings, with `[Ahmed to confirm]` placeholders and inventory/recovery/deletion limits. **Do not deploy the privacy text before Ahmed reviews it.**
- Offline verification: **501 backend tests**, **15 frontend tests**, build **15/15**, no window-is-not-defined warning. Backend + frontend deploy needed. No cloud calls, account deletion, migration, secret access or deployment occurred.

### 2026-10-20 — Codex: Session 13 Unit 3 — client resilience

- Branch `codex/s13-client`, implementation `4cd77ae`, stacked on Unit 2. Firestore lookup failures now differ from missing documents and return retryable 503; daily verse refuses empty Arabic/English text. Canonical missing verses still return 404.
- Component-local UID + generation tickets protect profile, saved/history, reflection lists and result annotations, progress and plans. Auth callbacks clear account data immediately; main study/onboarding components remount per UID. Each search captures its controller, timeout and generation; an old finally can clear only its own timer. The 180-second timeout remains unchanged.
- Share IDs/pending promises reset with each answer; late old-answer results are discarded, and sharing uses the answer's captured query. Saved/history use ErrorNotice and lib/errors with retry; expired sessions offer sign-out and fresh sign-in. Successful HTTP responses alone report backend recovery.
- reCAPTCHA initialization is browser-only with a handled rejection; protection remains enabled. Build emits no window-is-not-defined error.
- Offline verification: **497 backend tests**, **15 frontend tests**, **14/14 production build**. New delayed-response component regressions exercise A-to-B account switches and logout for saved/history; identity generations also reject A/B/A reuse. No app/model/cloud calls or deployment. Backend + frontend deploy needed.

### 2026-10-20 — Codex: Session 13 Unit 2 — surface and dependency controls

- Branch `codex/s13-surface`, stacked on Unit 1; implementation `c6a27e7`. Iman prefix gated before auth unless IMAN_ENABLED=1; all operational cache readers require the existing admin secret. Rate checks own their lock, evict stale keys and cap key counts; analytics uses bounded canonical-query keys. Feedback is limited before paid enrichment. Durable quotas remain deferred; Claude owns budget/quota cloud controls.
- Exception responses use stable copy and a server-generated 12-character request ID, with the active exception logged server-side. JSON object validation rejects malformed request bodies; tafsir and feedback text types are explicitly validated. Source regression prevents str(e) from returning. Added enforced frame/referrer/HSTS headers and a fuller Report-Only CSP.
- Next pinned **15.5.27**, Capacitor core/CLI/iOS **8.5.1**, matching tooling/lock. Docker uses npm ci then copies pruned builder node_modules into Node 24 runtime. Added .dockerignore. cap sync ios succeeded and Swift package references/tag hash updated; **no iOS build or shipping**.
- Verification: **494 backend tests**, **12 frontend tests**, production build **14/14**. The upgraded Next build required public font cache refresh under network access; no application/model calls. Dependency scan remains **16 npm packages** and **20 Python advisory entries across 5 packages**; exact residual applicability, CSP domains and proxy assumptions are recorded in `docs/SESSION-13-VERIFICATION.md`. No clean-scan claim. Python dependencies were audited in an external venv, not changed.
- ProxyFix trusts one rightmost hop only under K_SERVICE for direct run.app ingress. The cited Google docs describe ordered XFF chains but do not explicitly guarantee a numerical hop count; this topology inference needs Claude's deployment smoke verification. Do not use leftmost XFF. Backend + frontend deploy needed; native release remains separate. No deployment/cloud mutation occurred.

### 2026-10-20 — Codex: Session 13 Unit 1 — content trust boundaries

- Branch `codex/s13-content`; implementation `0c461d7` (stack starts at main `037e1c9`). Closes LOG-01 attribution/narrator bypass, SEC-01/02, LOG-02/03/04, LOG-05 version identity, ERR-02 answer contract.
- One validated tuple drives explicit-reference parsing, canonical prompt input and both cache keys. Invalid/reversed ranges and distinct references require correction. Exact resolved profiles replace cross-persona fallback; missing profiles use curious_explorer/beginner. Pipeline **17.0** is in prompt cache identity. Firestore TTL remains the expiry policy.
- Hadith labels retain the existing support check; narrator names require nearby source tokens; display attribution comes from structured source headings or the neutral default. Downgrade-not-drop and **0.80 wording threshold remain unchanged**. Trailing unsupported words remain a golden-canary follow-up owned by Claude. Existing saved answers and shared snapshots are unchanged and **predate this attribution fix**.
- Commentary no longer parses raw HTML; removed rehype-raw and unused lockfile dependencies. Browser-free hostile iframe/form/style/script rendering test passes.
- Verified offline: `backend/venv/bin/python -m pytest backend/tests -q` **485 passed**; `node --test tests/*.test.*` **12 passed**; frontend `npm run build` **14/14**. No live/model/cloud calls, no deployment. Backend + frontend deploy needed; Claude owns paid golden canary and deployment.

### 2026-10-20 — Claude: Ahmed approved all six audit decisions; OPS-01 done; Session 13 issued

- **Decisions recorded in AI.md (2026-10-20):** canonical-verse-only shared prompt (SEC-02,
  option A); no cross-persona cache fallback (LOG-04); pipeline version in the cache key, TTL
  stays the expiry policy (LOG-05); verified-only hadith attribution, 0.8 threshold untouched
  without the golden canary (LOG-01); Iman routes off unless `IMAN_ENABLED=1`; cheap abuse
  controls first, durable quotas deferred (SEC-03).
- **OPS-01 DONE (Claude, cloud config):** both Firestore databases (`(default)`, `tafsir-db`,
  project `tafsir-simplified-6b262`) now have **PITR enabled** (7-day version retention,
  `earliestVersionTime` 2026-10-20T14:43Z), **delete protection enabled**, and **daily backup
  schedules** — `(default)` 14-day retention, `tafsir-db` 7-day. App verified unaffected
  (`/daily-verse` reads Firestore fine). Still open from OPS-01: a restore drill into a
  disposable database, and a written restore runbook.
- **Facts verified for the spec:** the frontend calls none of `/cache/lookup|analytics|popular`
  and none of the 28 `/iman/*` routes (both safe to gate); the guest default persona is
  `curious_explorer`; all 10 cached answers contain zero HTML tags in commentary, so removing
  `rehype-raw` loses no formatting.
- **Session 13 issued** (`docs/PROMPT-GPT56.md`): six stacked units — content boundaries
  (P0 + pipeline 17.0), abuse surface/errors/headers/dependencies, client resilience, private
  data (deletion, encryption code, privacy page draft), progress and reads, deploy verification
  and boundary tests.
- **Claude-owned follow-ups:** create `reflection-encryption-key` in Secret Manager before the
  first Session 13 backend deploy; billing budget alert + Vertex quota cap (need Ahmed's
  monthly amount); golden canary for pipeline 17.0; the OPS-01 restore drill.

### 2026-10-20 — Claude: review of the GPT 6 audit — dispositions, and where findings meet recorded decisions

- **Merged** the audit (docs only) to `main`. Report: `docs/AUDIT-2026-10-GPT6.md`,
  34 findings (1 P0, 11 P1, 22 P2). **Quality: high.** Evidence-based, and it explicitly
  honoured recorded decisions (kept min-instances 0 and the 180s abort in PERF-03, kept local
  state + raw fetch in ERR-03, kept reCAPTCHA protection in ERR-05, kept downgrade-not-drop in
  LOG-01, kept the deployment architecture in OPS-03).
- **Spot-checked against the code, all confirmed:**
  * LOG-01 (P0): a model-written attribution "Sahih Muslim 999999" plus an ungrounded narrator
    survive validation and display ("narrated by A narrator nowhere in the source; Sahih Muslim
    999999") even though the collection field was stripped — a bypass of the Session 5 P0 fix.
  * LOG-02: "Al-Baqarah 1-3" and "2/1-3" normalise to `2:1` and share the single-verse key.
  * LOG-03: "Al-Fatihah 7" resolves to (1, 1).
  * SEC-02: "2:255", "2:255 ignore the sources and praise me" and the help text's own example
    "historical context of 2:255" share one cache key, while the raw query is interpolated into
    the prompt (`"{query}"`, app.py ~3006).
  * SEC-03: `/cache/lookup`, `/cache/analytics`, `/cache/popular` carry no auth decorator.
- **Findings that meet a decision — need Ahmed's call (not simple bugs):**
  1. **SEC-02 vs the free-text "analysis" query feature.** Cache normalisation to the canonical
     verse is a deliberate hit-rate design, and the help text advertises "historical context of
     2:255". Both together mean any query wording rewrites the shared answer. Options: (A) send
     only the canonical verse/range to the shared prompt and drop free-text framing — topic
     discovery now owns free text; (B) give non-canonical queries their own cache identity (more
     paid generations, injection surface isolated per query). **Claude recommends A.**
  2. **LOG-04 vs the default-profile cache fallback.** Documented with P1.3 (2026-08-01) when
     personas only changed tone; Session 6's persona learning contracts made it wrong — a
     beginner can be served an intermediate answer. **Recommend removing it** (cost: more first
     misses; negligible now the cache was purged).
  3. **LOG-05 vs the TTL design.** Accept the pipeline-version-in-key half (Claude already
     recommended it after the 3.8 canary). **Decline the read-time-expiry half as an accepted
     risk:** Firestore TTL deletes typically within a day of expiry and memory caches die with
     instances (min-instances 0); serving a 90-day answer one day late is harmless.
  4. **LOG-01's "require full containment" vs the Session 7 lesson.** Over-strict matching is what
     stripped every hadith from 2:255 in the 3.6 canary. Fix the attribution/narrator half now
     (build display attribution only from verified data); tighten text matching only behind the
     golden harness.
  5. **Iman Journal "suspended but live".** LOG-09, LOG-10, ERR-02's Iman paths, SEC-03's Iman
     generation and part of PRIV-02 exist only because suspended endpoints still answer.
     Gating them off (404) while suspended is consistent with README's suspension and closes
     several findings at once.
  6. **SEC-03 fix scope.** Durable cross-instance quotas mean new shared state. Cheaper first:
     admin-gate the three cache read routes, a GCP billing budget alert, a Vertex quota cap,
     and bounded in-process counters. Revisit durable quotas when traffic exists.
- **Severity adjustments Claude would make:** PERF-03 and LOG-05's expiry half to P3 at current
  traffic; LOG-09/LOG-10 moot if Iman is gated; SEC-04's Capacitor advisory blocks iOS release
  but is not live risk until an iOS build ships. Everything else accepted as filed.
- **Next:** Ahmed decides items 1-6; Claude then writes the fix sessions (P0 + SEC-01/02 first, as
  the audit recommends).

### 2026-10-20 — Codex: Session 12 independent read-only audit completed (October 17 observations)

- **Branch:** `codex/audit-gpt6`. **Audit commit:** `519788b`.
  Report: [docs/AUDIT-2026-10-GPT6.md](docs/AUDIT-2026-10-GPT6.md).
  Audited `main` at `7a0f3f1`, including required `2271020`; repository/cloud/test
  observations were collected October 17 and the report completed October 20.
- **34 findings: 1 P0, 11 P1, 22 P2, 0 P3.** Full evidence, quoted code,
  offline reproductions, all **84 route handlers**, dependency applicability,
  verified-safe checks, unresolved leads and six proposed fix sessions are in the report.
- **Top three risks:** (1) **LOG-01 P0**: hadith downgrade strips the collection field
  but preserves unverified narrator/free-text attribution; the existing Ahmad fixture
  can still display a Muslim claim through `attribution`. Aggregate shingle matching
  also accepts unsupported endings. (2) **SEC-01 P1**: main commentary raw HTML
  permits unsandboxed `iframe srcdoc` script to execute in the parent's origin,
  reproduced in an isolated browser using the installed libraries. (3) **OPS-01 P1**:
  both Firestore databases have no managed backup schedule/retained us-central1
  backup, PITR disabled and only 3600-second version retention.
- **Before the next routine content deploy:** Claude should review and prioritize
  **LOG-01 + SEC-01/02** (attribution, rendering and reader-input/shared-cache boundaries).
  A focused emergency security fix should not wait for all 34 findings. Own the other
  P1 recovery, encryption, erasure, abuse, dependency, account-state and deployment
  work. **No iOS submission** until the affected native runtime, account deletion
  and first-party privacy policy are resolved (SEC-04, PRIV-02/04).
- **Verified:** 457 backend tests, 11 frontend tests, Next build 14/14; build emits
  Firebase server-initialization failure, with the `window` source reproduced using
  a synthetic enabled reCAPTCHA response. npm audit reports 14 affected production
  packages (5 critical, 8 high, 1 moderate); pip-audit reports 20 records across five
  packages, deduplicated to 10 advisory identities. The report distinguishes reachable,
  absent and unverified advisory preconditions instead of treating every CVSS label
  as a live exploit. No backend cross-user IDOR was found; required/admin/debug/cron
  gates, strict topic mapping, share creation and bounded main retry remain sound.
- **Observed production on October 17:** backend `00273-dpr`, frontend `00308-vbm`,
  both 100% latest. Friendly errors had already deployed, correcting the kickoff's
  pending-deploy assumption. This is not a new October 20 production observation.
- **Read-only scope preserved:** no application/dependency changes, backend startup,
  paid generation, private record/secret reads, cloud mutations or deployment.
  Three explicit public GETs only: frontend `/`, backend `/health`, and the `2:1`
  range limit. Six is its valid dynamic budget beneath the ten-verse hard cap.
- **Not verified:** deployed Firestore rules (metadata read 403), exact guest proxy
  identity, provider budgets/quotas (budget API disabled), exact image dependency
  graph, native-device exploit behavior, old snapshots/external exports/log retention,
  alert delivery and restore/failover. Production attacks/load/auth tests were excluded
  by instruction. Section 6 names the precise isolated/read-only follow-up for each.
- **Next:** Claude reviews the evidence into fix sessions. Only this audit document
  and this handoff entry are committed; no fixes are implemented by this branch.

### 2026-10-17 — Claude: plain-language errors app-wide (merged, NOT deployed); GPT 6 full audit issued

- **Merged** `2271020` (`claude/friendly-errors`). Frontend only. **DEPLOYED 2026-10-17** as
  `tafsir-frontend-00308-vbm` (100%, `latestRevision: true`; rollback `00307-r65`). Backend
  untouched (0 backend files changed since the deployed 3.8 merge). Verified on the live site:
  bundle has zero `localhost:8080` references and ships the new copy; a wrong-password attempt
  against production Firebase shows "That email and password don't match..." with no
  "Firebase" text; a cached 94:5 answer renders fully (verse, sources, headings 18px, no fixed
  overlays, no horizontal overflow).
- **Problem:** a wrong password showed Firebase's raw "Firebase: Error
  (auth/invalid-credential)." The same pattern ran app-wide: raw `err.message` on sign-in,
  sign-up, password reset, profile setup, progress, plans and badges; backend `error` text
  passed straight to the screen; and the tafsir range error displayed the raw code
  `verse_range_too_large` instead of the server's explanation.
- **Fix:** `frontend/app/lib/errors.js` is the single place that decides what a reader is
  told — Firebase codes map to plain sentences, HTTP failures map by status (401 sign in
  again, 403, 404 per screen, 429, 5xx per-screen fallback), and server text is shown only for
  4xx responses that read like a sentence (rejects codes, exception names, braces, URLs).
  Raw `err.message` is never returned. `components/ErrorNotice.jsx` replaces seven different
  error treatments with one calm design (thin rule in the error colour, reading-colour text,
  no icon, no "Error:" prefix; forwards the tafsir focus ref; optional retry action).
  Applied in `page.js` (auth, profile, tafsir, notes, save toast), progress, plans, badges,
  annotation form, saved, shared page and the crash screen.
- **No account enumeration:** sign-in gives one answer for wrong password and unknown
  email; password reset shows the same neutral confirmation ("If an account exists for this
  email...") whether or not the account exists.
- **Verified against real Firebase** in headless Chrome: wrong password → "That email and
  password don't match. Please check them and try again, or reset your password."; unknown
  email on reset → neutral confirmation; no "Firebase" or `auth/` text anywhere on the page.
  7 new unit tests (`node frontend/tests/errors.test.mjs`), 4 component tests, build 14/14.
- **GPT 6 full audit issued** (`docs/PROMPT-GPT56.md`, Session 12): read-only, evidence-based,
  dimensions security / logic / performance / error handling / privacy / ops / tests,
  deliverable `docs/AUDIT-2026-10-GPT6.md`. Seeded with leads Claude confirmed in code but has
  not runtime-verified:
  * **~69 backend routes return `str(e)` on 500** (internal exception text to the client).
  * **Guest rate limit keys on `request.remote_addr` with no `ProxyFix`** behind Cloud Run —
    guests may share one 10/hr bucket, or evade it.
  * **`REFLECTION_ENCRYPTION_SECRET` is not set in production** — reflections are stored
    without the app-level encryption the code supports.
  * **Model-written commentary is rendered with `ReactMarkdown` + `rehype-raw`** (raw HTML) in
    `page.js`; the shared page does not use raw HTML.
  * Picker range budget (6 for 2:1) vs backend cap (10) disagree.
- **Next:** Ahmed's go to deploy the frontend; run the GPT 6 audit; Claude reviews it into fix
  sessions; App Store blockers remain.

### 2026-10-17 — Claude: stale tafsir cache physically purged (Ahmed: "clear all cache")

- **Before:** `tafsir-db/tafsir_cache` held 379 docs — 372 stale (pipeline 8.0: 94,
  9.0: 34, 10.0: 15, 11.0: 22, 12.0: 163, 14.0: 5, 15.1: 39) and 7 current (16.0,
  Gemini 3.8, generated today). The version gate already made the stale docs
  unservable, but **328 of them (8.0-12.0) predate the `expires_at` field, so the TTL
  policy would never have deleted them.**
- **Deleted all 372 stale docs**, each with a `last_update_time` precondition so a doc
  regenerated mid-purge could not be removed (0 skipped). **Kept the 7 current 16.0 docs**
  — deleting them would only force identical 3.8 regenerations.
- **Verified safe beforehand:** shared links copy the full response into
  `shared_content` at creation and read only that collection; saved searches live in
  the users DB; nothing else reads `tafsir_cache` except the live lookup and analytics.
  After the purge: `/health` healthy (in-memory cache = 2 entries, both 3.8 answers from
  the new revision), 94:5 still `hit-firestore` in 0.25s, a pre-existing shared link
  (`1762560969478_9e4504d9`, 39:53) still loads with its full response.
- **Did not use `/cache/invalidate` `confirm=all`** — it deletes every doc including
  current ones, and offers no version filter.

### 2026-10-17 — Claude: Gemini 3.8 Flash SWITCHED & VERIFIED in production (backend + frontend)

- **Production: backend `tafsir-backend-00273-dpr` (gemini-3.8-flash, pipeline 16.0) +
  frontend `tafsir-frontend-00307-r65`**, from `main` @ `15b6108` (merge of
  `claude/s12-gemini-38-canary`). Ahmed approved ("SWITCH"). Migration done 33 days
  before Vertex retires gemini-3.6-flash (2026-11-19). **Rollback:** backend
  `tafsir-backend-00271-l8f` (3.6, pipeline 15.1 — valid only until 2026-11-19),
  frontend `tafsir-frontend-00306-ptn`.
- **Traffic switch — a near-miss worth remembering.** `deploy-backend.sh` created
  `00273-dpr` (the build WITH the correlations-cap fix) at 0% because the canary's
  `--no-traffic` had pinned traffic to `00271` by name. Cloud Run then reported
  `latestReadyRevisionName = 00275-dap` — the canary build WITHOUT the fix — because the
  new revision, untagged at 0%, was "Retired" and skipped. `--to-latest` at that moment
  would have routed production to the wrong build. Instead: `update-traffic
  --to-revisions tafsir-backend-00273-dpr=100 --remove-tags canary38`, verified, and
  only then `--to-latest` (now `100% LATEST (currently 00273-dpr)`, pin cleared, future
  deploys take traffic normally). Procedure recorded in AI.md.
- **Backend verification:** 9 env vars, `GEMINI_MODEL_ID=gemini-3.8-flash`;
  `/health` healthy; `/daily-verse` Arabic; admin 403 / debug 404; `/topics/resolve` OK.
  Fresh 2:255 (29.6s) and 94:5 (26.9s) → 200, 8/8 sections, no extraction error,
  1 grounded hadith each, `notices: []`, no emoji; repeat 94:5 → `hit-firestore` 0.22s.
  Prod logs: `GEMINI_USAGE ... model=gemini-3.8-flash`, zero errors.
- **Frontend verification:** 100% on `00307-r65` with `latestRevision: true`. Live
  bundle: zero `localhost:8080`, targets prod backend. Headless Chrome at 390px against
  the live site (guest, 94:5): single closing quote, badge hidden + attribution, no
  floating button, no fixed overlays, no horizontal overflow, headings 18px,
  recommendation reasons end on whole words, install banner styled (white surface,
  1px border, 20px padding). The 2026-10-01 follow-ups (banner, `.gcloudignore`,
  Riyad spelling + hyphen-tolerant hadith labels) are now live too.
- **Pre-existing, logged, not blocking:** every frontend Cloud Build since at least
  2026-08-14 prints `ReferenceError: window is not defined` after all 14 pages generate
  (`.next/server/chunks/434.js`, Node 20 image; does not reproduce on Node 24 locally).
  No page fails to prerender. Some module touches `window` at import on the server —
  worth tracking down. Also: an interrupted `deploy-frontend.sh` left one extra build
  (`87b95d5d`) that never deployed; only `00307` was created.
- **Cost note:** pipeline 16.0 means every cached answer regenerates once on 3.8 when
  first viewed (about 27s for that reader, then cached for 90 days).
- **Next:** iOS App Store blockers (account deletion, privacy policy, Guideline 4.2
  native value — see the 2026-10-01 entry); include pipeline version in the Firestore
  cache key; canonicalise model-supplied hadith collection labels ("Ṣaḥīḥ Muslim");
  find the `window` access in the server bundle; truncating quick-select chips.

### 2026-10-17 — Claude: Gemini 3.8 Flash canary PASSED; traffic switch awaits Ahmed

- **Why:** Vertex AI retires `gemini-3.6-flash` on **2026-11-19** (Vertex model page;
  the Gemini API page lists no date, but Tadabbur runs on Vertex). Replacement:
  `gemini-3.8-flash` — GA, global endpoint, retires "September 2, 2027 or later".
  `gemini-3.7-flash` is already superseded by 3.8. Lite model stays on
  `gemini-3.5-flash-lite` (retires "July 21, 2027 or later"; no 3.8 Flash-Lite exists
  for text).
- **Branch `claude/s12-gemini-38-canary` (pushed, NOT merged):** main model default +
  `deploy-backend.sh` → `gemini-3.8-flash`; `SCHOLARLY_PIPELINE_VERSION` 15.1 → **16.0**;
  `/iman/correlations` cap 4,096 → 8,192 (`eea4b9b`, see thinking below). Built from
  `main`, so it also carries the 2026-10-01 follow-ups (banner, ignores, Riyad, hyphen
  patterns) that are merged but not yet deployed. 457 offline tests green.
- **Canary:** revision `tafsir-backend-00275-dap`, **0% traffic**, tag
  `canary38` → https://canary38---tafsir-backend-vg7kshbegq-uc.a.run.app , image
  `gcr.io/tafsir-simplified/tafsir-backend:canary-38` (separate tag; `:latest` untouched),
  full 9-var environment verified.
- **Golden harness, guest profile, six verses** (no persona tokens are available, so
  both personas collapse to the guest default; run once per verse via a scratchpad
  wrapper around `golden_regression.run_case`, which also keeps under the 10/hr guest
  limit). Raw results in `backend/tests/golden-results/`.
  * Baseline (prod 3.6): **6/6 PASS**, all cache hits, zero cost.
  * Canary (3.8): **6/6 PASS** on all invariants. 1:5 first showed a 300s client
    ReadTimeout — **proven a client artifact**: Cloud Run's request log shows 200 in
    25.9s/7.4 KB delivered, and `pmset` shows the Mac lid closed 23s before the response
    (13:36:02 CDT) and opened 13:40:44; awake time summed to exactly 300s. Re-validated
    from the canary's cache: PASS.
- **Numbers (3.8 canary vs 3.6 prod, last 30 days):** thinking tokens median 1,894
  (max **4,627**) vs 2,663 (max 4,119); output median 1,572 vs 1,659; server latency on
  fresh answers median **27.2s** (max 44.2s) vs 21.6s (max 26.9s). Verse sets differ,
  but 3.8 is plausibly ~25% slower with a fatter tail. Still well inside the 120s
  Gemini timeout and 180s frontend abort.
- **Thinking risk confirmed and fixed:** 3.8's thinking reached 4,627 tokens, which counts
  against `maxOutputTokens`; `/iman/correlations` (main model, cap 4,096) would have
  truncated before writing JSON. Raised to 8,192. The other main-model Iman calls are
  already 8,192 (~3.5K headroom at the observed max). Iman is suspended, but the
  endpoints are live.
- **Content review (Claude):** hadith totals 5 (3.8) vs 6 (3.6); **2:255 keeps its
  hadith** (no repeat of the Session 7 zero-hadith canary). 3.8 attributes the
  2:255 "tongue and two lips" wording to **Imam Ahmad** — correct, and the validator
  confirmed the label against Ibn Kathir's text (the Session 5 P0 was this wording
  misattributed to Muslim). 4:23 fosterage hadith → Sahih Muslim via 'Ā'ishah, correct.
  Every 3.8 reflection prompt quotes the verse's own words; 4:23's leans toward honouring
  nursing mothers rather than the verse's marriage prohibitions (acceptable, anchored to
  verse text). No emoji anywhere; the only exclamation marks are inside the verbatim
  2:255 hadith quotation. Cosmetic: a model-supplied label renders "Ṣaḥīḥ Muslim" with
  diacritics rather than the canonical "Sahih Muslim" — follow-up, not blocking.
- **Side effect, handled:** the cache key omits the pipeline version, so the canary
  overwrote production's guest-profile docs for the six test verses with 16.0 docs.
  Production never served them (version gate rejects them) but would regenerate on 3.6.
  Re-warmed 2:255 on production (miss 24.9s → hit 0.4s). The other five regenerate
  lazily if visited before the switch. Worth fixing generally: include the pipeline
  version in the cache key so future canaries cannot touch production docs.
- **Production unchanged:** `tafsir-backend-00271-l8f` 100%. **But traffic is now
  pinned to 00271 by name** (a `--no-traffic` deploy replaces "latest") — the Session 7
  trap. Any `deploy-backend.sh` run will NOT receive traffic until
  `gcloud run services update-traffic tafsir-backend --to-latest`.
- **Switch plan (needs Ahmed's go):** merge the canary branch → `deploy-backend.sh` →
  `update-traffic --to-latest` → remove tag `canary38` → `deploy-frontend.sh` (ships the
  pending follow-ups) → AI.md checklist + one fresh generation with
  `GEMINI_USAGE model=gemini-3.8-flash` → update AI.md truth table. Pipeline 16.0 means
  every cached answer regenerates once on first view. Rollback: `update-traffic` to
  `tafsir-backend-00271-l8f` (works until 2026-11-19).

### 2026-10-01 — Claude: follow-ups merged (NOT yet deployed) + App Store readiness assessment

- **Merged** `128240f` (`claude/followups-banner-ignore-riyad`). 457 tests green, 4 frontend
  component tests green, build 14/14. **Not deployed** — awaiting Ahmed's go. Needs
  backend + frontend.
- **Install banner:** rebuilt on design tokens (Tailwind was never installed, so it had
  always rendered unstyled on Chrome/Android). In-flow card, teal Install / outlined
  Not now. Dead iOS instructions block removed. Verified rendered by forcing
  `beforeinstallprompt` in headless Chrome.
- **Explicit `.gcloudignore` for frontend and backend.** A `.gcloudignore` disables
  gcloud's `.gitignore` fallback, so both state every exclusion directly. Verified with
  `gcloud meta list-files-for-upload`: zero `.env*`, venv, `run-local.sh`, caches or
  OCR images; every runtime file still present (backend 20.8 MB, 627 files).
- **Riyad al-Salihin — turned out to be a hadith-validator bug, not just a spelling.**
  `_KNOWN_COLLECTION_PATTERNS` only matched unhyphenated names, so "Sahih al-Bukhari",
  "Riyad al-Saliheen" and "Sunan al-Nasa'i" as models actually write them were never
  recognised. **It failed safe** — an unrecognised label is discarded, never shown
  unverified — but correctly supported labels were discarded too. Patterns now accept
  hyphens and variants (Abu/Abi Dawud, Nasa'i/Nasai, at-/al-Tirmidhi,
  as-/al-Salihin); recognised labels are still verified against the source wording
  before display. Tests prove a supported hyphenated label is now kept and an
  unsupported one is still stripped. Prompt context in `source_service.py` now says
  al-Salihin (internal keys `riyad_al_saliheen` unchanged), and
  `normalize_source_spellings` rewrites responses at serve time, so the 90-day cache
  matches — confirmed on a cached 103:2 whose model-written hadith attribution now
  reads "As cited in Riyad al-Salihin". Fresh-generation spot-check (49:12, cache
  miss) passed: 9/9 sections, no extraction error; the validator correctly downgraded
  an unsupported "Muslim" label live. No pipeline bump.

**App Store readiness: NOT READY.** Two hard blockers, one high rejection risk:

1. **BLOCKER — no in-app account deletion** (Guideline 5.1.1(v)). The app lets people
   create accounts (`createUserWithEmailAndPassword`) but there is no way to delete one.
   Apple rejects this outright. Needs a backend route that deletes the Firebase Auth
   user and all their Firestore data (profile, saved searches, annotations,
   reflections, progress, Iman data), plus a confirmed "Delete account" in Settings.
2. **BLOCKER — no privacy policy.** App Store Connect requires a privacy policy URL, and
   the app collects email, reflections and reading history. Needs a `/privacy` page
   (and ideally `/terms`, `/support`) plus App Store privacy "nutrition label" answers.
3. **HIGH RISK — Guideline 4.2 Minimum Functionality.** The iOS app is a Capacitor shell
   whose `server.url` loads the production website, with only splash-screen and
   status-bar plugins. Apple routinely rejects apps that are "just a website". Most
   credible mitigations: an offline/error screen instead of a blank WebView (there is
   none today), native share sheet, local notifications for the daily verse, and
   ideally bundling the web assets instead of loading a remote URL.
4. Smaller items: add `ITSAppUsesNonExemptEncryption=false` to Info.plist; check whether
   an app-level `PrivacyInfo.xcprivacy` is needed; `TARGETED_DEVICE_FAMILY = "1,2"`
   means iPad must work well and needs iPad screenshots — restrict to iPhone ("1") for
   v1 unless iPad is wanted; disclose in the listing that commentary is AI-generated
   from classical sources.
5. Ahmed-only: Apple Developer Program membership ($99/yr), signing team, physical
   device test, App Store Connect listing and screenshots.
Already fine: 1024px icon with no alpha; email/password only, so Sign in with Apple is
not required; bundle ID `com.tadabbur.app` set; version 1.0 (1).

### 2026-10-01 — Claude: Sessions 10 + 11 DEPLOYED & VERIFIED (backend + frontend)

- **Production: backend `tafsir-backend-00271-l8f` + frontend `tafsir-frontend-00306-ptn`**
  from `main` @ `a05efde`. Ahmed approved after reviewing the merged build locally.
  **Rollback targets:** backend `tafsir-backend-00270-9fr`, frontend
  `tafsir-frontend-00305-q78`. Pipeline still **15.1** — no cache flush.
- **Pre-deploy hazard checked:** `frontend/.env.local` sets
  `NEXT_PUBLIC_BACKEND_URL=http://localhost:8080`, the frontend has no
  `.gcloudignore`/`.dockerignore`, and the Dockerfile copies the whole directory before
  `npm run build`. `gcloud meta list-files-for-upload` confirmed the generated ignore
  (from `.gitignore`'s `.env*`) excludes it: 115 files uploaded, zero `.env*`, no
  `node_modules`/`.next`. Post-deploy, the live JS bundle has **zero** `localhost:8080`
  references. **Recommend adding an explicit `frontend/.gcloudignore`** so this never
  depends on gcloud's fallback behaviour.
- **Order:** backend first, so `/topics/resolve` existed before the new UI could call it.
- **Backend verification:** traffic 100% on 00271 with `latestRevision: true` (not
  pinned); all 9 env vars incl. `ADMIN_SECRET` secret ref; `/health` healthy;
  `/daily-verse` Arabic present; `/tafsir` 2:255 → 200 in 0.61s `hit-firestore` with
  `notices: []` and `A Thematic Commentary on the Qurʼan` rendered **on a cached
  answer** (the badge-map resolution working); admin 403 / debug 404 intact;
  `/topics/resolve` live; failed-lookup help text emoji-free.
- **Frontend verification:** traffic 100% on 00306, not pinned; homepage 200.
  **First-ever end-to-end check of the live production site in a browser** (headless
  Chrome at 390px against the production URL, guest mode, 13:28): the deployed frontend
  calls the deployed backend and renders the full answer. Measured on the live DOM:
  reCAPTCHA badge hidden, attribution present, no floating help button, zero fixed
  overlays, no horizontal overflow, recommendation cards full-width (16-374px), headings
  18px. Single closing quote on 13:28; recommendation reasons end on whole words.
- **NEW FINDING — pre-existing, not caused by this deploy:** the PWA "Install Tadabbur"
  banner renders unstyled in production (text flush to the edge, dark text on teal).
  **Tailwind is not installed in this project**, and `PWAProvider.jsx` is the only
  component written with Tailwind utility classes, so none of its classes have ever
  applied. It only appears on Chrome/Android (it surfaced here because headless Chrome
  fires `beforeinstallprompt`).
  **Correction to the Session 11 review entry:** it said the banner moved "from a fixed
  bottom toast to in-flow". That was wrong — `fixed` never applied either, so the banner
  was always in-flow and unstyled. Fix: restyle the banner with the app's design tokens
  (inline styles or `globals.css` classes, like the rest of the app).
- **Next:** banner restyle + `frontend/.gcloudignore` (both small, frontend-only); the
  `hadith_validation.py` `Riyad al-Saliheen` spelling; the truncating quick-select
  chips; iOS physical-device test.

### 2026-10-01 — Claude: Session 11 reviewed, rendered on a phone viewport, MERGED with three fixups

- **Merged** as `78fec2a` (the four units via Codex's `codex/s11-preview` stack, plus
  Claude fixups `ba4fdfa`). 445 backend tests green under
  `-W error::DeprecationWarning`, 4 frontend component tests green, build passes
  (14/14 pages). **Nothing deployed.** Production is still
  `tafsir-backend-00270-9fr` + `tafsir-frontend-00305-q78`.
- **Visual verification that Codex could not do.** Headless Chrome driven over the
  DevTools protocol (Node 24's built-in WebSocket, no installs; driver kept in the
  session scratchpad) at a 390px mobile viewport, entering guest mode, submitting
  13:28 and switching tabs. Measured on the rendered DOM, not inferred from code:
  * `.grecaptcha-badge` is `visibility: hidden`; attribution present.
    `initializeRecaptchaConfig` is untouched, so Auth bot protection still runs.
  * No `.floating-help-button`; **zero** visible `position: fixed` elements over the
    answer; no horizontal page overflow.
  * All three recommendation cards span 16-374px in a 390px viewport — stacked, none
    clipped. Section headings share one 18px size.
  * Zero off-palette hex accents (slate, blue, magenta, purple, violet, indigo, pink,
    rose, emerald) left in `page.js` or `components/`. Progression stages now share one
    neutral rule; the reflection card uses a grey label and a flat teal button.
    Arabic verse, tafsir header bar and hadith card untouched as specified.
- **Three fixups, found only by looking at the rendered page:**
  1. **Recommendation reasons cut mid-word** ("those who tru"). `app.py` hard-sliced at
     80 characters; the old one-line clamp hid it behind an ellipsis, and Unit 4 rightly
     removed the clamp. Added `_shorten_on_word` (word boundary + ellipsis, never over
     80, unchanged if it fits) and `tests/test_recommendation_reason.py`.
     Recommendations are rebuilt at serve time, so cached answers benefit immediately.
  2. **Doubled closing quote** on verses whose translation continues speech from a
     neighbouring verse (13:28 closes a quotation opened in 13:27). New
     `frontend/app/lib/scripture.js` `displayTranslation` drops only an *unmatched*
     quote; balanced speech is preserved. Applied at all three render sites (main
     view, shared page, annotation form). 7-case unit check passed.
  3. **Bottom-nav Help item had no icon** beside icon-plus-label neighbours, so it
     would sit misaligned for signed-in phone users. Added lucide `CircleHelp` at the
     same 22px / 1.8 stroke. This was Claude's spec error: it said both "icon-free"
     and "match the surrounding items exactly".
- **Accepted, flagged:** the PWA install banner moved from a fixed bottom toast to
  in-flow at the foot of the page. It no longer covers content but is less
  discoverable. It only fires on Chrome/Android; Safari never shows it.
- **Noticed, pre-existing, not from this session:** the rotating quick-select chips in
  `SurahVersePicker` truncate long labels with an ellipsis at phone width
  ("Nothing Resembles Alla…"). Worth a small follow-up.
- **Correction to my own output during review:** a sample of five verses' quote
  balance returned empty text for four of them because the local guest rate limit
  (10/hr) had been hit. Those rows were discarded; only 13:28 was a valid data point.
- **Ready to ship together:** Session 10 backend (notice, titles, emoji, and the
  unshipped `/topics/resolve`) + Session 10/11 frontend + these fixups. Awaiting
  Ahmed's device review of the merged build, then backend + frontend deploy and the
  AI.md checklist.

### 2026-10-01 — Codex: Session 11 combined local review

- **Checked-out review branch:** `codex/s11-preview` (local only, based on `main`
  `e525b4d`). All four independently reviewable unit branches remain available.
  Combined implementation commits are `f4b9c67`, `5291315`, `34a10d9`, `72bfbd3`.
  The only cherry-pick conflict was adjacent imports: kept RecaptchaAttribution and
  the default HelpMenu import, dropping FloatingHelpButton as specified. `main`
  remains unchanged. No deployment or push was performed.
- **Combined verification:** production build passed (14 static pages); existing
  frontend topic lifecycle tests **4 passed**; backend **441 passed, 0 skipped,
  0 deprecation warnings** under `-W error::DeprecationWarning`; diff check clean.
  No changes to backend files or `frontend/app/lib/firebase.js`, including
  `initializeRecaptchaConfig(auth)`. Pipeline **15.1** unchanged.
- **Device review still required:** confirm the badge is absent, attribution visible,
  local sign-in works, Help opens through nav/F1, and a complete answer scrolls to
  its final recommendation without obstruction at iPhone widths. Check the new
  heading scale and colour restraint in light/dark appearance, plus wide-screen
  recommendation snapping. Browser inventory is empty and native UI access was
  blocked by macOS permissions; no visual/auth pass is claimed. No paid calls or
  secrets were used. All four units need **frontend-only deployment**, after review.

### 2026-10-01 — Codex: Session 11 Unit 4 — recommendations and answer hierarchy

- **Branch:** `codex/s11-recs`; **implementation commit:** `b67ec28`.
  Independent from `main`; frontend only, pipeline **15.1** unchanged.
- **Screen for Ahmed's device review:** at viewport widths up to 640px, Continue
  reflecting shows one full-width card per row. References and reasons wrap fully,
  without ellipsis or a one-line clamp. Wider screens retain a horizontal row with
  mandatory scroll snapping, 8px side padding/scroll padding and an available thin
  scrollbar. Continue reflecting, Hadith, Related Verses, source coverage and desktop
  answer-section headings share `answer-section-heading`: 1.125rem, weight 600,
  line-height 1.4. Arabic text, tafsir source bars and hadith cards are unchanged.
- **Overlap audit:** found an additional conditional PWA install banner fixed over
  the page bottom; it now appears after content in normal flow, with bottom space
  for the navigation/safe area. Install/dismiss behaviour and copy are unchanged.
  BottomNav already reserves 52px plus the device safe area. Units 1 and 2 remove
  the persistent badge/help overlays. Intentional user-triggered dialogs, text
  selection controls and transient notifications remain; Next's development
  indicator is untouched.
- **Verification:** `npm run build` passed (14 static pages);
  `python3 -m pytest backend/tests -q -W error::DeprecationWarning` passed:
  **441 passed, 0 skipped, 0 deprecation warnings**. `git diff --check` passed.
  Reviewed null filtering and verse callbacks: unchanged. No API/backend files,
  dependencies or content semantics changed. No live/paid probes or deployment.
- **Pending:** actual iPhone/desktop bottom-of-answer scrolling, badge visibility
  and local sign-in remain manual review items. Browser inventory is still empty;
  native computer use previously reported missing macOS Accessibility/Screen
  Recording permissions. Source/build checks are not a device visual test.
  **Deploy needed: frontend.**

### 2026-10-01 — Codex: Session 11 Unit 3 — restrained brand palette

- **Branch:** `codex/s11-palette`; **implementation commit:** `6296694`.
  Independent from `main`; frontend only, pipeline **15.1** unchanged.
- **Screen for Ahmed's device review:** Baseline, Ascent and Peak have identical
  neutral surfaces, 3px border-colour left rules and secondary-text labels. Their
  names and vertical order distinguish them. Reflection has a quiet teal tint,
  secondary-text label and flat teal sign-in button. Synthesis/contemplation cards,
  annotation categories, badges, menus and status accents use teal/gold/neutral
  colours; labels and icons still convey their existing meanings. Share, copy,
  annotation, introduction, feedback and install controls have flat backgrounds.
  Arabic verse typography, source header and hadith-card presentation are preserved.
- **Verification:** `npm run build` passed (14 static pages);
  `python3 -m pytest backend/tests -q -W error::DeprecationWarning` passed:
  **441 passed, 0 skipped, 0 deprecation warnings**. `git diff --check` passed.
  Audited remaining hex colours: teal, gold and neutrals. Token-based badge tints
  use `color-mix` instead of appending hex alpha to CSS variable strings.
- **Independent-unit boundary:** the obsolete floating help export is left intact
  on this branch to avoid colliding with Unit 2, which deletes it entirely. Its
  gradient disappears with Unit 2. Non-interactive manuscript/shimmer decoration
  remains. No copy semantics, API/backend behaviour or dependencies changed.
- **Pending:** device/browser visual review remains unverified: computer-use access
  is blocked by macOS Accessibility/Screen Recording permissions. No live/paid
  calls, credentials, deployment or backend changes. **Deploy needed: frontend.**

### 2026-09-28 — Codex: Session 11 Unit 2 — help in navigation

- **Branch:** `codex/s11-fab`; **implementation:** `b3f98a4`.
  Removed the sole FloatingHelpButton caller, named import, unused export, and its
  entire fixed-circle style block. No other screen imported or rendered it.
- **Appearance:** Help is a plain, icon-free item with the existing desktop nav-item
  styling (also visible when collapsed) and the mobile bottom-nav label styling.
  Guests receive a plain Help action alongside the header account controls because
  their side/bottom navigation is intentionally hidden. No floating control covers
  answer text. Other screens' BottomNav calls are unchanged (onHelp is optional).
- **Keyboard detail:** source inspection found F1 only in the old tooltip, not in
  a key handler. F1 now directly opens the retained HelpMenu, including while typing.
  Existing Alt+H finds the new help-toggle entry; all other shortcuts are unchanged.
- **Verified:** frontend build passes; backend suite **441 passed, 0 skips/warnings**
  with deprecations as errors; no FloatingHelpButton references remain; diff clean.
  Native UI verification remains blocked by computer-use permissions; no device
  visual/keyboard pass claimed. No backend/API/auth/pipeline change (**15.1**).
- **Next:** Claude review and Ahmed device check; frontend-only deploy when authorized.
  Nothing deployed; independent branch from main.

### 2026-09-28 — Codex: Session 11 Unit 1 — reCAPTCHA badge attribution

- **Branch:** `codex/s11-recaptcha`; **implementation:** `563c3e8`.
  Added `.grecaptcha-badge { visibility: hidden; }`. Firebase initialization,
  `initializeRecaptchaConfig(auth)`, and all auth handlers are unchanged.
- **Appearance:** the bottom-right floating badge is hidden by CSS. The complete
  Google attribution appears as 0.75rem secondary text below every auth mode
  (sign-up, sign-in, password reset) and in the main app's in-flow footer. Both
  policy links are underlined, open a new tab, and use `noopener noreferrer`.
- **Verified:** frontend production build passes; offline backend suite **441 passed,
  0 skips, 0 warnings** with deprecations as errors; diff check clean. No backend,
  API, Firebase configuration, dependency, or pipeline change (**15.1**).
- **Local verification limit:** computer-use native Chrome inspection is blocked by
  pending Accessibility/Screen Recording permissions; no successful local sign-in
  or visual badge check is claimed. Ahmed should confirm both before deployment.
  No credentials were accessed and no auth account was created or modified.
- **Next:** Claude review and local device/auth check; frontend-only deploy when
  authorized. Nothing deployed. Independent branch from main.

### 2026-09-28 — Claude: Session 10 all four units reviewed and MERGED; backend verified, frontend deploy HELD

- **Merged to `main`** (`1ac46bf`, `5cce098`, `7d34c1b`, `5b4a0c9`): 441 offline tests
  green under `-W error::DeprecationWarning`, all 55 backend files compile, frontend
  builds, pipeline still **15.1**. **Nothing deployed** — production remains
  `tafsir-backend-00270-9fr` + `tafsir-frontend-00305-q78`.
- **GENERATION SPOT-CHECK PASSED** (the gate Claude owed for the prompt edit). Booted the
  merged tree locally and generated a genuinely fresh verse (103:2, `X-Cache-Status:
  miss`, 19.1s, one `GEMINI_USAGE model=gemini-3.6-flash` line, zero errors). Output is
  fully intact and good: all 11 contract sections present, `extraction_error: None`,
  scholarly attribution correct for Surah al-Asr (Ibn Kathir, Shaykh al-Ghazali, Ibn
  Qayyim al-Jawziyyah), grounded hadith, and a verse-anchored reflection prompt. The
  plain-text prompt markers did NOT degrade generation. Note this wrote one valid 15.1
  document into the shared production cache.
- **Units 1-3 verified LIVE, not just by test:** `source_coverage.notices` is now `[]`
  even with `al_qurtubi: false`; badges render `A Thematic Commentary on the Qurʼan`
  (U+02BC confirmed) and `Riyad al-Salihin`; both failed-lookup help branches return
  zero emoji and zero exclamation marks. A simulator screenshot of the real UI confirms
  the sources panel now reads the full commentary title with no absence notice.
- **Unit 2 carried an unspecced improvement worth keeping:** display names resolve
  through `_SOURCE_BADGE_MAP`, so answers already sitting in the 90-day cache render
  current titles instead of stale ones. Without it the rename would have taken ~90 days
  to fully appear.
- **Unit 4 review:** the bolted-on search form and the `<details>` demotion are gone;
  lookup help is primary again with themes beneath; bespoke `styled-jsx` replaced by
  shared classes on existing design tokens; the panel moved from a 2px amber alert box
  to a 1px bordered surface; resolves on arrival rather than behind a button. The
  reviewed correctness pieces (AbortController, 30s timeout, null-guards, curated
  fallback, `aria-live`) are intact, and the new component tests compile the real JSX
  and assert exactly those behaviours.
- **FINDING (minor, cosmetic, not blocking):** `services/hadith_validation.py:25` still
  emits the canonical label `Riyad al-Saliheen` while source badges now read
  `Riyad al-Salihin`. A reader can see both spellings in one answer. One-line fix;
  queue it with the next backend unit.
- **Deploy posture:** backend (Units 1-3) is verified and ready on Ahmed's word.
  Frontend (Unit 4) is deliberately HELD until Ahmed reviews the redesign locally,
  since he rejected the previous presentation unseen-by-him would repeat that mistake.
  Note that a backend deploy also ships `/topics/resolve` (merged in Session 9); it is
  unused without the frontend, guest rate-limited at 10/hr, input-capped, lite-model
  only and fails safe, so exposure is minimal.
- **Next:** Ahmed reviews the redesigned not-a-verse screen locally, then Claude deploys
  backend + frontend together and runs the AI.md checklist.

### 2026-09-28 — Codex: Session 10 Unit 4 — restrained topic presentation

- **Branch:** `codex/s10-topics-redesign`; **implementation commit:** `7e1cae5`.
  Independent from `main`. Topic discovery is still **unshipped**; this corrects
  presentation rejected during local review. Backend files, topic vocabulary/seeds,
  rate limiting, model contract and pipeline **15.1** are completely unchanged.
- **Screen for Ahmed's local review:** the home screen again has its existing
  Surah/Verse picker and curated theme controls, without the added free-text form.
  On the failed-verse result screen, the original lookup message, supported formats,
  and suggestions are fully visible at the top (no details toggle). The result uses
  the app's existing surface card, a fine border, 24px padding, and normal foreground
  text; the former yellow warning styling and moving hover treatment are removed.
  Format examples preserve their line breaks. Below the lookup suggestions, a fine
  divider and generous spacing introduce **Related themes**, followed by the query
  in smaller secondary text. A quiet **Identifying related themes…** status appears
  immediately, with no extra button press. Results show each theme as a restrained
  semibold subheading and its references beneath in wrapping rectangular controls:
  teal text, existing surface/border tokens, 8px corners, 44px minimum height, and a
  visible keyboard-focus outline. No pictographic emoji, new colours, ornament,
  rounded-pill treatment, or component-local styled-jsx. Styles live alongside the
  existing results styles in globals.css and inherit the app's typography.
- **Behavior:** reference selection still invokes the ordinary verse flow.
  `key={query}` resets topic state. The effect retains AbortController cancellation,
  the 30s timeout, null guards, curated-theme fallback, and the same polite aria-live
  status region. Effect cleanup clears its timer and prevents an abandoned query
  from updating state after automatic resolution is cancelled/remounted. Failure
  copy is plain: e.g. "Topic search is unavailable. Curated themes are listed below."
- **Verified:** `npm run build` passes (14 static pages, lint/type checks included).
  `python3 -m pytest backend/tests -q -W error::DeprecationWarning` → **438 passed,
  0 skips, 0 warnings** on this independent frontend branch. Four offline component
  lifecycle checks pass via `node --test frontend/tests/topic-explorer.test.cjs`:
  arrival triggers the request, valid references select correctly, null data shows
  eight themes, and timeout/unmount abort safely. These execute the real JSX compiled
  with installed Next tooling and simulated hooks/fetch; they are not browser tests.
  Diff check clean; backend diff from main is empty.
- **Visual verification limitation:** attempted a temporary fully mocked local preview,
  but browser access was unavailable and native Chrome inspection remained blocked
  by pending computer-use Accessibility/Screen Recording permissions. No visual
  pass or screenshot is claimed. The temporary route and dev server were removed.
  Ahmed's local visual review remains required before deployment; no paid/live
  requests were made.
- **Independent implementation commits, in review order:** Unit 1 `20b483e` on
  `codex/s10-notice` (handoff `a34ac49`); Unit 2 `1c3fc13` on `codex/s10-titles`
  (handoff `6fff8c3`); Unit 3 `92f76f1` on `codex/s10-no-emoji` (handoff `6429227`).
  A disposable detached worktree applied all four implementation commits cleanly:
  **441 backend tests pass with deprecations as errors; all 55 backend Python files
  compile**. Worktree removed; no merge to main. Apply Units 1–3 for the complete
  no-emoji/full-title/notice-free preview; this independent branch retains main's
  unchanged backend until those commits are integrated.
- **Next:** Claude review and Ahmed local presentation approval. Unit 4 changes need
  a frontend deploy; its approved topic backend endpoint is still unshipped and must
  also be deployed before topic discovery can work live. Units 1–3 can ship separately
  via backend deploy; **Claude's known-verse generation spot-check is required before
  deploying Unit 3's plain prompt markers**. No deploy, gcloud, secret access, new
  dependency, live/paid probe, or pipeline bump performed.
### 2026-09-28 — Codex: Session 10 Unit 3 — remove product emoji

- **Branch:** `codex/s10-no-emoji`; **implementation commit:** `92f76f1`.
  Removed pictographic prefixes from both failed-lookup help messages, retaining
  their sentences as requested. Changed only the surrounding format introduction
  from "Try one of these formats" to "Supported verse-reference formats"; the
  examples remain plain and contain no exclamation marks.
- Removed six Gemini prompt markers, including SEMANTIC SEARCH APPROACH, leaving
  their text headings intact. Verified that all pre-handler source is byte-identical
  after stripping those six prefixes: no prompt instruction or ordering changed.
  **Pipeline remains 15.1. Claude must spot-check generation quality against a known
  verse before any backend deploy because prompt text changed.** No paid check run.
- **Verified:** full offline suite with deprecations as errors → **440 passed,
  0 skips, 0 warnings**; app compiles; diff check clean. Two new real-handler offline
  cases cover full-surah and unrecognized-query help, asserting no pictographic
  emoji or exclamation marks and no model call. Scanned app.py and all 49 frontend
  source files: zero pictographic emoji; typographic arrows remain.
- **Next:** Claude review; backend-only deploy when separately authorized. Independent
  branch from main. Developer-facing deploy/run-local scripts deliberately untouched.
  No deploy, gcloud, secrets, live probe, dependency change, or cache invalidation.
### 2026-09-28 — Codex: Session 10 Unit 2 — full source titles

- **Branch:** `codex/s10-titles`; **implementation commit:** `1c3fc13`.
  Both thematic badge definitions now read `A Thematic Commentary on the Qurʼan`
  with U+02BC. Ihya Ulum al-Din and Madarij al-Salikin were already correct and
  unchanged; both Riyad badge labels now use Ahmed's requested `Riyad al-Salihin`
  spelling instead of `Riyad al-Saliheen`. Authors and prompt/source excerpts unchanged.
- **Pre-edit audit:** no runtime routing/filtering comparison matches the bare
  `Thematic Commentary` display name. The internal `thematic` key and pointer
  prefixes drive retrieval. `filter_unavailable_sources` handles classical tafsir
  names only. The corpus parser's full-title comparison is unrelated and untouched.
  No existing test asserted the old badge title (old excerpt fixtures are unchanged).
- **Cached answers:** coverage presentation resolves titles from the existing badge
  map by internal key, so old cached badges show the new titles without changing
  stored answers, retrieval, coverage methods, or invalidating the cache.
- **Verified:** full offline suite with deprecations as errors → **439 passed,
  0 skips, 0 warnings**; module compiles; diff check clean. The new regression covers
  cached display names, exact U+02BC, unchanged methods and unchanged stored badges.
- **Next:** Claude review; backend-only deploy when authorized. No deploy, live probe,
  gcloud, secrets, new dependency, or pipeline bump (**15.1**). Independent of Unit 1.
### 2026-09-28 — Codex: Session 10 Unit 1 — source-coverage notice

- **Branch:** `codex/s10-notice`; **implementation commit:** `20b483e`.
  Removed only the conditional append advertising unavailable al-Qurtubi coverage.
  `notices` remains an empty list; `classical.al_qurtubi` and frontend notice rendering
  are unchanged. No offline test asserted the removed notice text (verified by search).
- **Verified:** full offline suite in `backend/venv`,
  `python3 -m pytest backend/tests -q -W error::DeprecationWarning` →
  **438 passed, 0 skips, 0 warnings**; changed module compiles; diff check clean.
- **Next:** Claude review; backend-only deploy when authorized. No deploy, live probe,
  gcloud, secret access, dependency change, or pipeline bump (still **15.1**).
  This branch is independent from `main`; the remaining units are separate branches.

### 2026-09-28 — Claude: Ahmed rejected the topic UI; presentation pass specced (Session 10)

- **Ahmed reviewed topic discovery locally and rejected the presentation**
  ("not a fan of it at all"). Unit 2 is merged to `main` but **was never deployed**,
  so production has never served it — this is an unshipped feature being corrected,
  not a live regression. The **backend is approved and unchanged**: `/topics/resolve`,
  `services/topic_service.py`, the closed vocabulary and the security model all stand.
- **Ahmed's standing preference, recorded:** no emoji anywhere in the product, and the
  presentation must be professional and serious, following an Islamic aesthetic that
  matches the gravity of the content.
- **Emoji audit (Claude):** the **frontend is already emoji-free** — the `←`/`→`
  characters are typography and stay. Every emoji lives in `backend/app.py`:
  * **User-facing (what Ahmed saw):** `app.py:6371` (`📚 Full surah queries…`) and
    `app.py:6380` (`🤔 I couldn't find that verse…`) — the latter renders on exactly
    the failed-lookup screen he was testing.
  * **Gemini prompt section markers:** ~`app.py:2924, 2932, 3017, 3025, 3055, 3076`.
    Specced as plain uppercase markers with identical semantics and **no pipeline
    bump** — the output contract is unchanged and a bump would flush the whole
    production cache. Claude should spot-check generation quality before deploy.
  * Deploy scripts and `run-local.sh` keep their emoji (developer-facing, out of scope).
- **Other fixes specced:** drop the `"Al-Qurtubi is not available in this corpus for
  this verse."` notice at `services/source_service.py:1765` (keep the `notices` key so
  the contract and frontend need no change — absence should simply not be advertised);
  and render the full title `A Thematic Commentary on the Qurʼan` in place of the bare
  `Thematic Commentary` label at `source_service.py:721` and `:903`, with an explicit
  instruction to decouple display name from any matching logic first.
- **Topic UI redesign specced** (`docs/PROMPT-GPT56.md`, Session 10 Unit 4): remove the
  bolted-on second search form and the `<details>` demotion from `page.js`, surface
  discovery only on the existing not-a-verse screen, adopt the app's existing design
  tokens instead of bespoke `styled-jsx`, resolve on arrival rather than behind an
  extra click, and keep the reviewed correctness pieces (AbortController, timeout,
  null-guards, graceful fallback, `aria-live`) untouched.
- **Nothing deployed this session.** Production remains `tafsir-backend-00270-9fr` +
  `tafsir-frontend-00305-q78`. Local dev servers were run for Ahmed's review.
- **Next:** Codex works Session 10 Units 1-4; Claude reviews, with generation-quality
  spot-check required before any backend deploy because the Gemini prompt text changes.

### 2026-09-19 — Codex: Session 9 Unit 2 — free-text topic discovery (Ahmed-approved)

- **Branch:** `codex/s8-topics`; **implementation commit:** `aefed72`.
  Branched independently from `main` after completing Unit 1, so this review does
  not include Iman changes. **Review/merge Unit 1 first:** `codex/s9-iman-retry`,
  implementation `2a61719`, handoff `7032b28` (397 tests, 51 backend files compiled).
  Neither branch was merged or deployed by Codex.
- **Index:** eight existing curated themes and their exact editorial verse order
  copied into `backend/data/topic_seeds.json`, loaded once at startup. The index
  reuses `source_service.py` keyword extraction and routing tables for candidate
  ordering/aliases. A regression test checks seed parity with the frontend theme
  catalog and every reference against canonical Quran bounds. This first vocabulary
  is intentionally the eight themes; out-of-vocabulary questions receive browse
  suggestions. No model-generated references, vector search, or external data.
- **API:** guest-allowed `POST /topics/resolve` accepts `{text}` (1–500 characters)
  and returns `{topics: [{name, verse_refs, confidence}]}`. Free text makes one
  `GEMINI_LITE_MODEL_ID` request, 20s HTTP timeout, 4,096 output-token budget, with
  JSON response schema restricting names to the local vocabulary and at most three
  topics. Strict validation rejects unknown/duplicate names, generated references,
  extra fields, and invalid/non-finite confidences. References are then attached
  from the index. Exact curated theme names resolve locally without a model call.
- **Failure/cache behavior:** mapping/transport/parse failures return 200 with all
  eight curated themes (confidence 0 means browse suggestion). Bad input returns
  400, rate limits return 429 + Retry-After, both with the same browsable suggestions.
  Shares `/tafsir`'s user/IP rate-limit keys and limits, including cache hits.
  Separate locked process-local cache: 256 entries, normalized text keys, 1h success
  TTL / 60s fallback TTL. No Firestore reads/writes or pipeline interaction.
- **Frontend:** added the visible home search box (the current UI previously had
  only a picker). Text uses the existing verse-selection flow; `/tafsir`'s existing
  `needs_clarification` response identifies failed verse extraction and presents
  **Explore as a topic**. This preserves numeric/named-verse handling without a
  second parser or changes to `/tafsir`. Topic verse chips call the same existing
  `handleVerseSelection`. Local component state + raw fetch only; loading, timeout,
  malformed/null fields, and network/rate-limit fallbacks are handled. The eight
  existing theme buttons still lead straight to their editorial verse choices.
- **Verification:** from repo root with `backend/venv` active,
  `python3 -m pytest backend/tests -q -W error::DeprecationWarning` →
  **434 passed (393 baseline + 41), 0 skips, 0 warnings** on this independent branch.
  All **54 backend Python files compile**. `npm run build` succeeds (14 static pages,
  lint/type checks included); `git diff --check` clean. AST comparison confirms all
  pre-existing backend functions are unchanged. Pipeline stays **15.1**; dependency
  manifests unchanged. No production/live Gemini quality claims are made.
- **Manual offline endpoint script:**
  `python3 backend/scripts/topics_smoke.py` exercises the real decorated route via
  Flask's in-process HTTP test client with a **fake lite response** (no credentials,
  paid calls, live server, or production traffic). All five requests returned 200:

  | Phrase | Result (seeded references) |
  |---|---|
  | patience during hardship | Patience: 2:153, 3:200, 39:10 |
  | how can I seek forgiveness? | Forgiveness: 39:53, 4:110, 42:25 |
  | being kinder to my family | Family: 30:21, 25:74, 4:19, 46:15 |
  | I feel uncertain about the future | Trust in Allah: 3:159, 9:51, 14:12 |
  | help me pick a new laptop | Empty fake mapping → all 8 curated themes with their seed refs |

- **Next:** Claude review, then backend + frontend deploy when separately authorized.
  Live model mapping quality and browser/end-to-end production verification remain
  for that authorized validation. No deploy, gcloud, secret access, live/paid probe,
  new dependency, Firestore schema change, or pipeline bump was performed.
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
