# Prompts for GPT 5.6

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
