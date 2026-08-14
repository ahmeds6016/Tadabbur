# Prompts for GPT 5.6

## Session 6 prompt (2026-08-13) — MEGA ONE-SHOT: Q5-Q7, findings 6/9-14, model-flip harness, purge

---

You are GPT 5.6, main coder for Tadabbur (Claude = architect/reviewer, Ahmed =
owner). First: `git pull` and read `HANDOFF.md` (top session entry) and
`docs/QUALITY-REVIEW-2026-08-03.md`. Session 5 shipped: all six units were
approved, merged, and DEPLOYED (backend `tafsir-backend-00262-82w`, frontend
`tafsir-frontend-00303-9b6`). The P0 is verified fixed in production: fresh 2:255
cites hadith as "As cited in Ibn Kathir's tafsir of this verse", no Muslim
misattribution, zero validator drops. Two Claude review fixups to learn from:
(1) your guest CTA referenced `onGuestSignUp` in `EnhancedResultsDisplay` without
passing it as a prop (runtime ReferenceError — builds don't catch undefined
identifiers; always trace prop plumbing end-to-end); (2) `cryptography==50.0.0`
would have failed the image build (pip backtracks to 49.0.0 under pyopenssl) —
pin what the resolver actually installs, verified from build logs.

This is the LONGEST session yet: TEN units. Units 1-9 branch from `main`. Unit 10
(the purge) branches from a local integration branch you create by merging your
own units 1-9 in order (name it `codex/s6-integration`, do not push it as a PR —
it only exists so the purge diff is computed against post-session code). Work the
units IN ORDER; finish one (implement → verify → HANDOFF entry) before the next.
If a unit balloons: stop it, record why, move on. No deploys, no gcloud, no
secrets. Pipeline version: bump `SCHOLARLY_PIPELINE_VERSION` "13.0" → "14.0"
EXACTLY ONCE, in Unit 7 (the only unit that changes generated content). All new
response fields are additive; the frontend must null-guard every one of them
(old cached docs and error paths won't have them).

### Unit 1 — Q5: /share integrity (branch `codex/s6-share`)
- Today `POST /share` (unauthenticated) stores the caller's entire `response`
  dict verbatim and `/shared/[id]` renders it with `rehype-raw` (raw HTML) —
  anyone can publish fabricated "Tadabbur" scholarship, with an XSS path.
- Backend: change `POST /share` to accept `{query, approach}` only. Server
  recomputes the Firestore cache key exactly like /tafsir does for the caller
  (auth profile or guest default, including the default-profile fallback read)
  and snapshots the CACHED response into `shared_content` together with
  `pipeline_version`, `query_normalized`, and `created_at`. If no cache record
  exists → 409 `{"error": "View the verse first, then share it."}` (the share
  button lives on a rendered result, so the cache exists in practice). Keep
  `GET /share/<id>` shape unchanged so old share links keep working.
- Frontend: update the two `POST /share` call sites in `app/page.js` to send
  `{query, approach}`; remove `rehype-raw` from `app/shared/[id]/page.js` ONLY
  (markdown still renders; raw HTML no longer executes). Check whether the main
  results view relies on raw HTML in backend markdown before touching anything
  outside the shared page — report what you find.
- Rate-limit share creation with the existing `is_rate_limited` helper
  (e.g. 20/hour per user-or-IP).

### Unit 2 — Q6: source-coverage contract + cache TTL field + usage logging
(branch `codex/s6-coverage`)
- Backend: build a deterministic `source_coverage` object BEFORE generation and
  attach it (additive) to every /tafsir response, cached or fresh:
  `{classical: {ibn_kathir: true, al_qurtubi: <bool per 4:22 boundary>},
  additional_sources: [{name, method: verse_plan|keyword|surah_overview}],
  notices: ["Al-Qurtubi is not available in this corpus for this verse."]}` —
  derive from the actual retrieval plan (`source_service.py`), not the LLM.
- Frontend: compact "Sources used for this answer" panel rendering that object
  (names + a neutral notice line when a classical tafsir is unavailable). The
  orphaned scholarly badge data (`scholarly_sources`) can be folded in here if
  trivial; do not redesign the results page.
- `store_tafsir_cache`: add `expires_at` = created_at + 90 days to every new
  cache doc (Claude will enable the Firestore TTL policy on that field —
  server-side deletion, no code path needed).
- Log Gemini `usageMetadata` (prompt/candidates token counts) from the main
  generation response as one structured log line per fresh generation
  (finding 13's "measure first" step). Do NOT change maxOutputTokens.
- Correct `_metadata` inside `_precomputed_scholarly_plans.json` to match the
  file's real contents (6,236 keys; recount origins with a small throwaway
  script; commit corrected metadata only, not the script).

### Unit 3 — Q7 + finding 11: verse-first loading + accessibility
(branch `codex/s6-progressive-a11y`)
- On search submit, immediately `GET /verse/<surah>/<verse>` (public, fast) and
  render Arabic + translation + verse reference at once, with the existing
  `TafsirSkeleton` where commentary will appear, while `/tafsir` runs in
  parallel. Ranges: fetch the start verse, label "Loading verses …-…". Keep
  cancel/retry and all existing error handling; if the verse fetch fails, fall
  back to today's spinner behavior silently.
- Accessibility (same UI, so same unit): visible labels or `aria-label` on the
  surah/from/to selects (fieldset+legend for the range pair); loading and
  results containers become polite live regions ("Verse loaded; gathering
  classical commentary" → completion announcement); `lang="ar" dir="rtl"` on
  every Arabic text node (main results + shared page); verify focus lands
  sensibly after submit and after an error.

### Unit 4 — finding 6: deliver "Continue reflecting" (branch `codex/s6-recommendations`)
- `_generate_recommendations` exists but runs only on the fresh path AFTER cache
  writes, so cached responses never carry it. Move/attach it so EVERY successful
  /tafsir response includes `recommendations` (computing before the cache write
  is fine; it's deterministic). Guard for guests (user_id may be None — read the
  function to see what it needs).
- Frontend: render up to 3 "Continue reflecting" cards (verse ref + one-line
  reason, click = run that query). Reuse the card look of related verses; the
  orphaned `RecommendationBar.jsx` may be revived ONLY if it genuinely fits —
  otherwise build inline and leave the orphan for the purge.

### Unit 5 — finding 14: reliability batch (branch `codex/s6-reliability`)
- `/feedback/daily-summary`: fail closed — if `FEEDBACK_CRON_SECRET` is unset,
  return 503 (mirror the ADMIN_SECRET pattern from P1.1).
- `useOnboarding.js`: wrap the localStorage `JSON.parse` in try/catch; on failure
  clear the corrupt key and reset to first-run state.
- Add `frontend/app/error.js` (route error boundary: friendly message + reset
  button) so a render crash no longer blanks the page.

### Unit 6 — finding 12: streaks reward study, not clicks (branch `codex/s6-streaks`)
- Keep the gentle daily streak, but also fire the existing streak update on:
  saving a reflection and completing a reading-plan day (frontend already has
  both success paths; call the same `updateStreak()` there).
- Progress page copy: lead with "verses studied" and "reflections" counts
  (already available from /progress and /annotations data); streak becomes
  secondary. Copy-level change only — no new metrics engine, no scoring of
  spiritual quality (hard product rule).

### Unit 7 — finding 9: persona learning contracts (branch `codex/s6-personas`)
- In `build_enhanced_prompt`, replace the tone/vocabulary-only persona deltas
  with per-persona learning contracts (depth/section behavior may now differ;
  the JSON SCHEMA stays identical):
  * new_revert: meaning first, explain every Arabic term on first use, exactly
    one concrete action, no scholarly debate.
  * curious_explorer: context-first narrative + one open question woven in.
  * practicing_muslim: worship/character application emphasized in lessons.
  * student: named positions with source locators ("Ibn Kathir states…",
    "al-Qurtubi holds…"), comparison encouraged.
  * advanced_learner: Arabic rhetoric notes, scholarly disagreements, evidence
    strength, explicit uncertainty where sources differ.
  * All personas: first two sentences of the explanation must answer "what does
    this verse mean here?" before any scholarly layering; reflection_prompt must
    be built from a verse-specific tension/image/command (the review's 1:5,
    2:255, 93:3 before/after table is your quality bar).
- Do not touch the hadith contract from Q1. **Bump SCHOLARLY_PIPELINE_VERSION
  "13.0" → "14.0" in this unit** (generated content changes; flushes 13.0 cache
  on deploy).
- Add `backend/tests/test_persona_prompts.py` (offline, pure): build prompts for
  2:255 with fixture context for all 5 personas, assert each contract's
  distinguishing instruction text is present and others' are absent.

### Unit 8 — finding 10: theme entry point (branch `codex/s6-themes`)
- Add an "Explore a theme" section to the home/search UI: curated chips
  (Patience, Gratitude, Forgiveness, Grief & Hope, Trust in Allah, Prayer,
  Family, Justice — pull verse lists from the existing quick-select catalog in
  `SurahVersePicker.jsx`; add 2-3 verses per theme where missing, choosing only
  unambiguous, well-known verses). A chip click shows its 2-4 verses with
  one-line editorial descriptions ("Editorial suggestions" label), and picking
  one runs the normal verse query. NO free-text semantic search — that stays a
  future L project.

### Unit 9 — Gemini 3.6 flip harness, NO flip (branch `codex/s6-golden-harness`)
- Write `backend/tests/golden_regression.py`: a SCRIPT (not pytest) that takes
  `--base-url` and hits POST /tafsir for a fixed verse set (1:5, 2:255, 4:23
  [post-Qurtubi], 6:57 [deterministic-only plan], 93:3, 112:1-4 range) across
  2 personas, then asserts structural invariants: valid JSON, required keys,
  exactly 3 lessons, non-empty tafsir_explanations, every hadith item passes
  `validate_hadith_items` against nothing-empty fields, reflection_prompt
  non-generic (length + contains a verse-linked token), `source_coverage`
  present, X-Cache-Status header present. Emits a pass/fail table and saves raw
  JSON responses to a timestamped folder for side-by-side diffing.
- Document at the top: Claude's flip procedure = deploy a NO-TRAFFIC canary
  revision with `GEMINI_MODEL_ID=gemini-3.6-flash` +
  `GEMINI_LITE_MODEL_ID=gemini-3.5-flash-lite`, run this script against the
  canary URL, compare against a baseline run, then shift traffic and bump
  pipeline version if content shifts materially. Do NOT change any model value
  anywhere in this unit.

### Unit 10 — dead-code purge (branch `codex/s6-purge`, from your local
`codex/s6-integration` merge of units 1-9)
- Pure deletion, zero behavior change. Backend: `app_optimized.py`,
  `migrate_to_optimized.py`, `config/settings.py`, `models/*`,
  `services/{verse_service,cache_service,rate_limiter,batch_query_service,
  integration}.py`; dead functions in app.py listed in
  `docs/AUDIT-2026-08-01.md` §6 (verify each has ZERO references beyond its
  `def` before deleting — if anything references one, leave it and note it);
  remove `redis`, `pydantic`, `pydantic-settings` from requirements.txt;
  remove the vestigial `import vertexai`/`vertexai.init` ONLY if you verify
  nothing else needs the SDK import side effects (if in doubt, leave it).
  Frontend: `app/context/AppContext.jsx`, `app/services/tafsirApi.{js,ts}`,
  the orphaned components list from the audit (RE-VERIFY each is still
  unimported AFTER your units 1-9 — you may have revived RecommendationBar in
  Unit 4), `/logo-demo`, the test file with no runner.
- Verify: py_compile, full pytest run (hadith + persona + token-budget tests),
  `npm run build` exit 0, and grep-proof of zero references for every deleted
  symbol, summarized in the PR description.

### Global rules
- Per unit: 2-3 sentence plan → implement → verify (py_compile / pytest /
  npm build / trace) → honest verified-vs-not in HANDOFF.md session log with
  branch + commit. Line numbers drift — trust the code. Match existing style.
- Frontend null-guards for every new response field. No new dependencies
  anywhere. Don't spend the guest rate limit on live probes (changes are
  undeployed; Unit 9's script is run by Claude later, not you).
- Finish with a summary table: unit | branch | commit | verified | deploy
  needed (backend/frontend/both), plus anything you skipped and why.

---

## Session 5 prompt (2026-08-03) — ONE-SHOT: P0 hadith integrity + quality wins + P2 batch

---

You are GPT 5.6, main coder for Tadabbur (Claude = architect/reviewer, Ahmed =
owner). First: `git pull` and read `HANDOFF.md` (P1-Q section + latest session log)
and `docs/QUALITY-REVIEW-2026-08-03.md`. Your Phase 2 review was validated: Claude
independently confirmed the P0 (live 2:255 attributes Ahmad's "tongue and two lips"
wording to Sahih Muslim; Muslim 810 ends at the congratulation) and spot-verified
findings 2 and 7. Your findings are promoted as queue items Q1-Q7.

This is a LONG end-to-end session: SIX branches, in this exact order. Each branch
comes from `main` (Claude merges in order and resolves trivial cross-branch
conflicts). Finish one unit — implement, verify, HANDOFF entry — before starting
the next. If any unit balloons, stop it, write down why, and move on. No deploys,
no gcloud, no secrets, ever.

### Unit 1 — Q1: hadith citation integrity (branch `codex/q1-hadith-integrity`) — THE P0

Design contract (Claude-approved):
1. **Prompt contract** (in `build_enhanced_prompt`, hadith section ~app.py:3699):
   hadith `text` MUST be verbatim (or tightly trimmed) from the source excerpts
   supplied in the prompt context — never from model memory. `reference` becomes
   structured: `collection` (ONLY if the supplied excerpt itself names that
   collection for that wording), `narrator`, and `attribution` (always set to the
   in-corpus source, e.g. "as cited in Ibn Kathir's tafsir of this verse"). If the
   excerpt notes wording differences between collections (as Ibn Kathir does for
   2:255), the model must attribute each wording to the collection the excerpt
   assigns it, or omit `collection`.
2. **Server-side validation** — a NEW PURE FUNCTION `validate_hadith_items(
   hadith_list, source_context_text) -> (kept, dropped)`: for each item, normalize
   both sides (lowercase, strip punctuation/diacritics, collapse whitespace) and
   require a substantial containment match of the hadith text within the supplied
   source context (e.g. a sliding window: ≥80% of the item's 12+-word shingles
   found in the context — pick and document a defensible method). Items failing →
   dropped, with a `print`/logger correctness event including verse ref and the
   rejected reference. Wire it into the /tafsir handler after extraction, BEFORE
   post-processing and caching, passing the same scholarly/tafsir context text the
   prompt was built from. If everything is dropped, return the response with an
   empty hadith list — never fail the whole request over hadith validation.
3. **Version bump**: `SCHOLARLY_PIPELINE_VERSION` "12.0" → "13.0" (this
   auto-invalidates ALL cached responses, including the bad 2:255 — deliberate).
4. **Golden tests**: new `backend/tests/test_hadith_integrity.py`, pure pytest, NO
   GCP/network — fixture-based: (a) the exact composite 2:255 case: an item with
   the "tongue and two lips" wording attributed to Sahih Muslim against a fixture
   context where that wording is attributed to Ahmad → must be dropped or
   re-attributed per your implementation; (b) a legitimate verbatim item → kept;
   (c) an item wholly absent from context → dropped; (d) empty hadith list → OK.
   Design `validate_hadith_items` so these tests run offline.
5. Response SHAPE stays: `hadith` remains a list of objects with at least
   `reference`/`text`/`relevance` keys so the frontend needs no change this unit —
   build `reference` as a display string from the structured parts, and add the
   new structured fields alongside (additive).

### Unit 2 — Q2+Q3+Q4: quality quick-wins (branch `codex/q2-4-quick-wins`)

- **Q2 (frontend)**: `frontend/app/page.js` ~:3081 — remove the `user &&` gate on
  `reflection_prompt` so guests see the question. Keep the save/annotate actions
  auth-gated; for guests render the question plus a sign-in CTA phrased as saving
  the reflection ("Sign in to save your reflection"), not unlocking it.
- **Q3 (backend)**: on the authenticated cache-hit return paths in the /tafsir
  handler (Firestore-hit and memory-hit returns, ~app.py:6904-6935), invoke the
  same `_track_explored_verse` + `_check_and_award_badges` calls the fresh path
  makes (~:7222-7224), guarded by `if user_id`. Confirm by reading
  `_track_explored_verse` that repeat calls for the same verse are idempotent
  (set/merge semantics) and say so in the PR; if they are NOT idempotent, add a
  cheap per-user/verse/day guard.
- **Q4 (backend)**: every /tafsir return path gets headers: `X-Cache-Status:
  hit-firestore | hit-memory | miss` and `Server-Timing` built from the existing
  `perf_metrics['stages']` (e.g. `cache;dur=114, gemini;dur=15800`). Use
  `make_response(jsonify(...))` pattern; do NOT put perf data into the cached
  response object. CORS: check whether `Server-Timing`/`X-Cache-Status` need
  `expose_headers` in the flask-cors config for the frontend to read them — add if
  so.
- No pipeline bump in this unit (Q1 already bumped; response body shape unchanged).

### Unit 3 — P2-A: Gemini migration prep (branch `codex/p2a-model-env-prep`)
Hardcoded `gemini-2.5-flash-lite` sites (2 in app.py) → env `GEMINI_LITE_MODEL_ID`
defaulting to `"gemini-2.5-flash-lite"`, defined next to `GEMINI_MODEL_ID`.
Identical behavior today. Add `GEMINI_LITE_MODEL_ID=gemini-2.5-flash-lite` to
deploy-backend.sh env vars. Do NOT touch `GEMINI_MODEL_ID` or flip any model.

### Unit 4 — P2-B: dependency + data hygiene (branch `codex/p2b-hygiene`)
Add `cryptography` to backend/requirements.txt pinned compatible with
firebase-admin's transitive pull (state version + why). `verse_range_map.json`:
missing from repo, so `load_range_map()` always falls back — either regenerate it
via an existing export helper (check services/token_budget_service.py) and commit
it, or delete the dead load path + misleading comment; state which and why.

### Unit 5 — P2-C: frontend build safety (branch `codex/p2c-suspense`)
Wrap the `useSearchParams()` usage (frontend/app/page.js, inside MainApp) in a
`<Suspense>` boundary — smallest structural change. `npm run build` must exit 0;
note whether the pre-existing trailing `window is not defined` print changes.

### Unit 6 — P2-D: iOS/CORS cleanup (branch `codex/p2d-capacitor-cors`)
`frontend/capacitor.config.ts` → point at
`https://tafsir-frontend-612616741510.us-central1.run.app` (dead Vercel URL out).
backend/app.py CORS origins: remove the dead Vercel origin, add comment that
origins must match live frontends. Don't touch ios/ or run cap sync.

### Global rules
- Per unit: 2-3 sentence plan first, then implement, then verify (py_compile,
  pytest for Unit 1's offline tests, npm build for frontend units, code trace for
  the rest) and record verified-vs-not honestly in HANDOFF.md session log with
  branch + commit.
- Line numbers drift — trust the code. Match existing style. No drive-by
  refactors, no dead-code deletion, no dependency changes beyond Unit 4's single
  pin.
- Live API probing is NOT useful this session (your changes aren't deployed);
  don't spend the guest rate limit.
- Finish with a single summary listing all six branches + commits + what Claude
  must do (merge order, deploy backend once at the end — Unit 1's version bump
  flushes the cache on deploy — and deploy frontend once for Units 2/5/6).

---

## Session 4A prompt (2026-08-03) — Phase 2 product audit — copy the block below

---

You are GPT 5.6, main coder for Tadabbur (Claude = architect/reviewer, Ahmed =
owner). First: `git pull` and read `HANDOFF.md` — ALL FIVE P1 tasks are deployed
and verified (backend revision `tafsir-backend-00260-m9l`, frontend
`tafsir-frontend-00302-8ls`). The app is live and healthy. Your P1.4/P1.5 work was
approved with no changes; your flagged 180s-vs-242s residual was accepted as a
deliberate decision (recorded in AI.md — read it).

This session is **ANALYSIS ONLY — no code changes, no branches**. Execute the
"Phase 2 — your own deep audit, through the product lens" section of
`docs/PROMPT-GPT56.md` (Kickoff prompt, bottom of file). Re-read that section now;
it is your full spec. The north star for every finding: **does this make it easier
for an end user to learn the meaning of the Qur'an and practice tadabbur?**

Additions/clarifications to that spec:
- You cannot access Firestore or gcloud. To inspect REAL responses, call the live
  API directly: `POST https://tafsir-backend-vg7kshbegq-uc.a.run.app/tafsir` with
  `{"query": "1:5", "persona": "curious_explorer"}` (vary verse + persona).
  **Budget: max 8 uncached generations** — guest rate limit is 10/hour per IP and
  each fresh generation costs real money. Prefer likely-cached verses (2:255,
  30:54, 31:18, 67:2 are cached) for structure inspection, and spend your fresh
  budget on persona comparison (same verse, 2-3 personas) since that's finding #1.
- Response `perf_metrics` contains stage timings — use them for the
  time-to-first-insight analysis instead of guessing.
- For coverage honesty (#2): `backend/data/indexes/_precomputed_scholarly_plans.json`
  `_metadata` block + the routing tables in `backend/services/source_service.py`
  are local ground truth; test one verse you can verify has no precomputed plan and
  describe exactly what the user receives.
- Deliverable: `docs/QUALITY-REVIEW-2026-08-03.md` in the format the spec defines
  (user problem → evidence → proposed change → effort S/M/L → expected user
  impact, ranked by impact-per-effort), plus a 10-line summary appended to
  HANDOFF.md's session log. Commit BOTH directly on a branch
  `codex/phase2-quality-review` (docs-only branch; this is the one exception to
  "no branches"). Do NOT implement any finding.

---

## Session 4B prompt (2026-08-03) — P2 engineering batch — copy the block below

---

You are GPT 5.6, main coder for Tadabbur (Claude = architect/reviewer, Ahmed =
owner). First: `git pull` and read `HANDOFF.md` + `AI.md`. All P1 tasks are
deployed. This session: four SMALL engineering PRs, one branch each, in this
order. Stop after each and record it; do not combine them.

**P2-A — Gemini migration prep (code only, no model flip)**
(branch `codex/p2a-model-env-prep`):
- The two hardcoded `gemini-2.5-flash-lite` call sites (search app.py for that
  string — guidance summarizer and feedback enricher) → read from a new env var
  `GEMINI_LITE_MODEL_ID` defaulting to `"gemini-2.5-flash-lite"` , defined next to
  `GEMINI_MODEL_ID` at the top config block. Behavior today must be identical.
- Do NOT change `GEMINI_MODEL_ID` or any model string values. The actual flip to
  `gemini-3.6-flash` / `gemini-3.5-flash-lite` is a later deploy-time step with
  live regression testing (Claude/Ahmed).
- Also update `deploy-backend.sh` to pass `GEMINI_LITE_MODEL_ID=gemini-2.5-flash-lite`.

**P2-B — dependency + data hygiene** (branch `codex/p2b-hygiene`):
- Add `cryptography` to `backend/requirements.txt`, pinned to a version compatible
  with what firebase-admin already pulls transitively (state the version you chose
  and why; do not upgrade anything else).
- `verse_range_map.json`: `load_range_map()` (search app.py) references
  `data/verse_range_map.json`, which does not exist in the repo, so the fallback
  recompute path always runs. Investigate: if the map can be regenerated by an
  existing script/export (check `services/token_budget_service.py` for an export
  helper), generate and commit it; otherwise delete the dead load path and its
  misleading comment, keeping the fallback as the only path. Either way, state
  which you did and why.

**P2-C — frontend build safety** (branch `codex/p2c-suspense`):
- Wrap the `useSearchParams()` usage in `frontend/app/page.js` (~:877, inside
  MainApp) in a `<Suspense>` boundary per Next.js 15 requirements — smallest
  possible structural change; do not refactor the component tree beyond what the
  boundary requires. Verify `npm run build` still exits 0 and note whether the
  pre-existing trailing `window is not defined` print changes (it should not).

**P2-D — iOS/CORS cleanup** (branch `codex/p2d-capacitor-cors`):
- `frontend/capacitor.config.ts:11` points the iOS WebView at
  `https://tafsir-simplified-app.vercel.app` — that deployment is dead (404), so
  the iOS app is broken. Point it at
  `https://tafsir-frontend-612616741510.us-central1.run.app` (the stable
  project-number URL, matching what backend CORS already allows).
- backend/app.py CORS origins: remove the dead Vercel origin. Add a comment noting
  origins must match live frontends only.
- Do not touch the ios/ directory or attempt cap sync.

For each PR: plan in 2-3 sentences, implement, verify what you can (py_compile /
npm build / trace), update HANDOFF.md status + session log, no deploys, no gcloud.
Line numbers drift — trust the code. If any task turns out bigger than it looks
(e.g. the range-map regeneration is complex), stop that task, note why, and move
on to the next.

---

## Session 3 prompt (2026-08-01, after P1.2/P1.3) — copy the block below

---

You are GPT 5.6, main coder for Tadabbur (Claude = architect/reviewer, Ahmed =
owner). Continuation session. First: `git pull` and read `HANDOFF.md` — P1.2 (#30)
and P1.3 (#31) were both approved with no changes, merged to `main`, and deployed
as revision `tafsir-backend-00259-zj6`. P1.3 was verified end-to-end in production
(guest cache doc confirmed under `curious_explorer/beginner` via direct Firestore
query; repeat guest query now hits in ~0.1s). Your audit correction was
independently verified and accepted. P1.2 and P1.3 are closed.

This session: **P1.4 and P1.5** — one branch + PR each.

**P1.4 — timeout stack fix** (branch `codex/p1-4-timeout-stack`, backend only):
- Bug: `backend/Dockerfile` runs gunicorn with `--timeout 120`, but a single main
  Gemini call already has `timeout=120` (requests) and the retry loop (~app.py
  7100-7140 — find `for attempt in range` near the main generateContent call)
  allows 4 attempts with 2/4/8/16s sleeps → worst case far exceeds both gunicorn
  120s and Cloud Run's 300s. Requests that hit even one retry die at the worker
  and the client sees a connection reset instead of the app's 503.
- Fix, two parts:
  1. Dockerfile: `--timeout 300` (match Cloud Run), and while you're in the CMD
     line, bind to `${PORT}` with an 8080 default instead of hardcoded 8080 —
     note the CMD is currently exec-form JSON, which does NOT expand env vars;
     switch to shell form (`CMD gunicorn --bind 0.0.0.0:${PORT:-8080} ...`) or
     keep exec form via `sh -c`. This PORT fix is explicitly authorized here
     (promoted from P2.9); do NOT also change worker/thread counts.
  2. Retry budget: cap the main-call retry loop so worst case fits inside 300s
     with margin — e.g. 2 attempts max (120 + backoff + 120 ≈ 245s) or lower the
     per-attempt `timeout=` so 3 attempts fit. State the arithmetic for your
     chosen budget in the PR/HANDOFF. Keep the existing 429/503 handling
     behavior; do not restructure the loop.
- No response-shape change → no pipeline-version bump.

**P1.5 — frontend /tafsir error handling** (branch `codex/p1-5-tafsir-errors`,
frontend only):
- Bug: `frontend/app/page.js` — in the main search submit handler, `const data =
  await res.json()` runs BEFORE the `res.ok` check (~:1277 vs ~:1286). When the
  backend returns a non-JSON body (Cloud Run 502/503/504 HTML, cold start, error
  pages), users see the raw parser error rendered in the UI, e.g.
  `Unexpected token '<', "<!DOCTYPE"... is not valid JSON`. When the network is
  down they see literally `Failed to fetch`.
- Fix, scoped to the /tafsir call path only:
  1. Check `res.ok` FIRST. On failure, attempt `await res.json()` inside its own
     try/catch to extract a server-provided `error` message; if parsing fails,
     fall back to a friendly generic message keyed off status ("The server had a
     problem (503). Please try again in a moment.").
  2. In the outer catch, map `TypeError` / fetch-rejection to a friendly
     "Can't reach the server — check your connection and try again." Keep the
     existing 429 message and the existing timeout/abort message exactly as is.
  3. Handle the new backend 502 from P1.2 (`{"error": "AI returned a malformed
     response. Please try again."}`) by showing that message.
- Do NOT attempt the global backend-down banner or touch the other ~30 catch
  blocks — that's a separate future task. No new dependencies, no refactor of the
  3,000-line page.js beyond this handler.
- Verification: try `npm run build` in frontend/ if Node is available. KNOWN
  ISSUE: the build may fail on a pre-existing `useSearchParams()`-without-
  Suspense problem (queued as P2.10) — if it does, report that honestly and do
  not fix it in this PR; verify by lint + code trace instead.

For each fix: state your plan in 2-3 sentences first, implement, then list exactly
what you verified vs could not run. Update `HANDOFF.md` (status + Session log with
branches/commits). Do not deploy; do not touch gcloud (deploys are Claude/Ahmed's
step — note P1.4 needs an image rebuild and P1.5 a frontend deploy). No drive-by
refactors; match existing code style. Line numbers drift — trust the code.

---

## Session 2 prompt (2026-08-01, after P1.1) — copy the block below

---

You are GPT 5.6, main coder for Tadabbur (Claude = architect/reviewer, Ahmed =
owner). Continuation session. First: `git pull` and read `HANDOFF.md` — your P1.1
work was reviewed (approved, no changes), merged to `main` (66db496), deployed as
Cloud Run revision `tafsir-backend-00258-q55`, and verified live: 403 without
secret, 404 debug routes, `/tafsir` unaffected. P1.1 is closed.

This session: **P1.2 and P1.3** — two small backend fixes, one branch + PR each,
in `backend/app.py` only. Branch each from updated `main`.

**P1.2 — stop caching malformed LLM output** (branch `codex/p1-2-extraction-guard`):
- Bug: `extract_json_from_response` (~app.py:2879) can never return a falsy value
  for non-empty model text — on total parse failure it returns a fallback dict
  `{"response": text[:500], "sources": [], "verses": [], "metadata":
  {"extraction_error": True, "fallback_used": True}}`. The guard in the /tafsir
  handler (`if not final_json:` ~app.py:7122) is therefore dead, and the fallback
  garbage flows through post-processing and gets written to BOTH caches (in-memory
  ~:7162 and Firestore ~:7169) permanently.
- Fix: in the /tafsir handler, after extraction, check
  `final_json.get('metadata', {}).get('extraction_error')` (the `/debug/test`
  handler ~:7406 already does this — copy that pattern). If set: log it, return
  HTTP 502 with a clean JSON error (`{"error": "AI returned a malformed response.
  Please try again."}`), and do NOT write either cache. Keep the existing
  `if not final_json` check as a belt-and-braces guard.
- Also cover the `MAX_TOKENS` path: finish reason MAX_TOKENS (~:7109) currently
  counts as success and produces truncated JSON that lands in the same fallback.
  Treating extraction_error as fatal covers it — just confirm by tracing the path.
- Response shape unchanged on success → NO pipeline-version bump.

**P1.3 — guest cache key mismatch** (branch `codex/p1-3-guest-profile`):
- Bug: ~app.py:7013 `user_profile = get_user_profile(user_id)` runs for everyone;
  for guests `user_id` is None and `get_user_profile(None)` returns `{}` (~:3735),
  clobbering the guest default profile set earlier (~:6849,
  persona=curious_explorer / knowledge_level=beginner). Consequence: cache READ
  (~:6862) uses the guest defaults but cache WRITE (~:7169) uses `{}` → Firestore
  key defaults (~:4163) to practicing_muslim/intermediate. Guests can never hit
  their own cache; every guest query is a full paid LLM call; prompt persona also
  silently changes.
- Fix: only call `get_user_profile` when `user_id` is truthy — otherwise keep the
  already-set guest profile. One-line guard; touch nothing else.
- After this fix, cached guest entries will be written under the guest-default
  keys. Old orphan docs stay harmlessly unread; do not migrate them.

For each fix: state your plan in 2-3 sentences first, implement, then list exactly
what you verified (at minimum: file compiles; trace the code path by reading it;
you cannot run the backend locally — say so honestly rather than claiming tests
ran). Update `HANDOFF.md` (mark task status, add a Session log entry naming your
branches/commits). Do not deploy; do not touch gcloud; no drive-by refactors; match
existing code style. If anything in the code contradicts the line numbers above
(they can drift), trust the code and note the correction.

---

## Kickoff prompt (2026-08-01, initial) — P1.1

---

You are GPT 5.6, the **main coder** for Tadabbur, an AI-powered Qur'anic reflection app
(Flask backend + Next.js 15 frontend on Google Cloud Run). You work alongside Claude
(Fable 5), who is the **architect/auditor/reviewer**, and Ahmed, the human owner who
approves deploys and anything touching billing/secrets.

## Before writing any code

1. Read `AI.md` at the repo root — architecture map, the two-GCP-project split,
   model config truth table, conventions, decision log. Treat its "Conventions &
   constraints" section as binding.
2. Read `HANDOFF.md` — current status and the prioritized task queue. This is the
   single source of truth for what to work on.
3. Skim `docs/AUDIT-2026-08-01.md` — the evidence base behind every task (exact
   file:line references for each bug).

Repo: https://github.com/ahmeds6016/Tadabbur (local checkout:
`c:\Users\us88832\Desktop\tadabbur`). Backend is one big file, `backend/app.py`
(~10,200 lines, 83 routes) — that's intentional for now; do not restructure it
without an architecture decision recorded in `AI.md`.

## Current state (as of 2026-08-01)

- The July 25–Aug 1 outage (Firestore billing unlink) is RESOLVED. App is live and
  verified: backend `https://tafsir-backend-vg7kshbegq-uc.a.run.app`, frontend
  `https://tafsir-frontend-vg7kshbegq-uc.a.run.app`.
- Production model is `gemini-2.5-flash` (env `GEMINI_MODEL_ID` on Cloud Run). It is
  NOT broken; it retires Oct 16–20, 2026. Migration to `gemini-3.6-flash` is task P2.6
  — do not change model strings outside that task.

## Your assignment: HANDOFF.md P1 tasks, in order

1. **Lock down unauthenticated destructive/costly endpoints** — `/cache/invalidate`,
   `/cache/store`, `/cache/prewarm`, and the three `/debug/*` routes. Follow the
   suggested approach in HANDOFF.md P1.1 (admin secret header via env from Secret
   Manager; debug routes 404 unless `DEBUG_ROUTES=1`).
2. **Fix malformed-LLM-output cache poisoning** — app.py:7122 guard is dead because
   the fallback dict from `extract_json_from_response` is always truthy. Check
   `metadata.extraction_error` (copy the correct pattern from the `/debug/test`
   handler at app.py:7406), return 502, and never cache the fallback.
3. **Fix guest cache key mismatch** — app.py:7013 overwrites the guest profile with
   `{}`; only call `get_user_profile` when `user_id` is truthy. This bug makes every
   guest query a full paid LLM call.
4. **Fix gunicorn timeout** — `backend/Dockerfile` `--timeout 120` → 300 to match
   Cloud Run; cap the Gemini retry loop (app.py:7064-7103) so worst case fits inside.
5. **Frontend error handling** — app/page.js:1277 parses JSON before checking
   `res.ok`; make the /tafsir call parse defensively and show a friendly message for
   non-JSON/network failures.

One PR (or one commit series on a branch) per numbered task — no drive-by refactors,
no dead-code deletion (that's a separate P2 task), no dependency bumps.

## Phase 2 — your own deep audit, through the product lens

After the P1 fixes are merged, do an independent deep pass over the entire app —
bugs, optimizations, and quality gains Claude's audit may have missed. The north
star for EVERY proposal: **does this make it easier for an end user to learn the
meaning of the Qur'an and practice tadabbur (deep reflection)?** Engineering
elegance that doesn't serve that goal goes to the bottom of the list.

Angles to investigate (not exhaustive — add your own):

1. **Tafsir answer quality** — the core product. Read `build_enhanced_prompt`
   (app.py:3376) and real cached responses in Firestore. Are explanations faithful
   to the cited sources? Do the 5 personas actually change depth/tone, or just the
   preamble? Are reflection prompts genuinely reflective or generic? Propose prompt
   improvements with before/after examples for 3 test verses (e.g. 1:5, 2:255, 93:3).
2. **Coverage honesty** — al-Qurtubi stops at 4:22; precomputed scholarly plans
   cover only ~61% of verses. What does a user get on an uncovered verse today?
   Does the UI communicate source coverage or silently degrade? Propose how to
   handle/communicate gaps.
3. **Time-to-first-insight** — fresh generations take ~17s with no streaming and a
   bare loading state. Options to evaluate: streaming responses, prewarming the
   most-read verses (Fatiha, Ayat al-Kursi, Ya-Sin, Ar-Rahman, Al-Mulk, Juz 'Amma)
   via the existing prewarm endpoint once secured, lowering maxOutputTokens (65536
   is far beyond any real response), and a skeleton/progressive UI. Measure first:
   the backend already returns `perf_metrics` stage timings — use them.
4. **The learning loop** — do streaks/badges/progress actually drive understanding,
   or just clicks? Is there a natural "what should I read next?" path? The
   recommendations engine (app.py:5511) exists — is it surfaced anywhere in the UI?
5. **First-run & guest experience** — walk the guest flow end to end. Onboarding
   friction, empty states, the 3-query sign-up nudge, what a confused first-time
   user sees when they type "patience" instead of a verse reference (backend
   currently rejects non-verse queries — is the guidance helpful?).
6. **Arabic & accessibility** — Arabic typography/RTL rendering quality, font
   loading, tashkeel legibility on mobile, screen-reader labels, dark mode contrast.
7. **Trust & correctness** — hadith citations shown without grading, source
   attribution clarity, cross-references accuracy. Anything that could misquote
   scripture or scholarship is a P0-severity quality bug: flag immediately.
8. **Remaining engineering debt** — anything from `docs/AUDIT-2026-08-01.md` §5-§7
   not yet queued, plus whatever you find that it missed.

**Deliverable:** `docs/QUALITY-REVIEW-<date>.md` + a summary appended to HANDOFF.md.
Each finding: *user problem → evidence (file:line, measurement, or screenshot-level
description) → proposed change → effort (S/M/L) → expected user impact*. Rank by
impact-per-effort. Do NOT start building these — Claude reviews the list, Ahmed
prioritizes, then items get promoted into the HANDOFF task queue.

## Rules

- **Never deploy, never touch gcloud/billing/secrets** — flag to Ahmed/Claude when a
  task is ready to deploy. Deploys are manual via `./deploy-backend.sh` /
  `./deploy-frontend.sh`.
- Branch from `main`; do not push to `main` directly.
- If a response's shape changes, bump `SCHOLARLY_PIPELINE_VERSION` (app.py:159) —
  the Firestore cache has no TTL.
- Match the existing code style of whichever file you're in, even where it's ugly.
- Verification after backend changes: run the checklist at the bottom of `AI.md`
  (health, a cached verse, a fresh verse) against a locally running backend or ask
  for a deploy to test against Cloud Run.
- **After every session, update `HANDOFF.md`**: what changed (files + why), what's
  verified vs untested, what's next. Add an entry to the Session log. If you made or
  discovered an architectural decision, propose it as a note for `AI.md` (Claude
  reviews and records decisions).
- If something in the code contradicts the audit docs, trust the code, fix the doc,
  and note the correction in HANDOFF.md.

Start with P1.1. Before coding it, restate your implementation plan in a few
sentences (which routes, which mechanism, how existing legitimate callers — e.g. any
cron hitting `/feedback/daily-summary` — are preserved), then implement.
