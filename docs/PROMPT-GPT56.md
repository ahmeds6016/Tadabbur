# Prompts for GPT 5.6

## Session 13 prompt (2026-10-20) — fix the GPT 6 audit: six stacked units

---

You are GPT 6, now main coder for Tadabbur (Claude = architect/reviewer, Ahmed = owner).
`git pull`, then read `AI.md` (especially the **2026-10-20 decisions**, which settle six
questions your audit raised), the top two `HANDOFF.md` entries (Claude's review of your
audit), and your own `docs/AUDIT-2026-10-GPT6.md`. Finding IDs below refer to that report;
its evidence and reproductions are your starting point.

**State:** production backend `tafsir-backend-00273-dpr` (gemini-3.8-flash, pipeline
`16.0`), frontend `tafsir-frontend-00308-vbm`. Offline baseline: 457 backend tests,
11 frontend tests, build 14/14. macOS: `python3`, venv `backend/venv`.

**Already done by Claude — do not redo:** OPS-01 (both Firestore databases now have PITR,
delete protection and daily backups).

**Claude-owned, out of scope for you:** creating the `REFLECTION_ENCRYPTION_SECRET` secret,
the billing budget alert and Vertex quota cap, the golden canary (paid), every deploy, and
any cloud mutation. Where your code needs one of these, write the code and say so in
HANDOFF.

**Branching — stacked, so app.py merges cleanly:** Unit 1 branches from `main`; each later
unit branches from the previous unit's tip. One commit series per unit, a HANDOFF entry per
unit. Work in order. If a unit balloons, stop it, record why, continue with the next.

### Unit 1 — content trust boundaries (`codex/s13-content`) — LOG-01, SEC-01, SEC-02, LOG-02, LOG-03, LOG-04, LOG-05, ERR-02

The P0 and everything that decides what readers see for a verse. Backend + frontend.

1. **LOG-01 (decision 4).** Display attribution is built only from verified data. A
   collection label survives only via the existing `_collection_is_supported` check; a
   narrator survives only if its name tokens appear in the source near the matched wording;
   model-written `attribution` text is never displayed — derive it server-side from the
   source excerpt the wording matched (e.g. "As cited in Ibn Kathir's tafsir of this
   verse"), else the existing neutral default. Strip any collection name found inside
   narrator or attribution text. **Keep downgrade-not-drop. Do NOT change the 0.8 wording
   threshold** — record the trailing-words finding as a follow-up for the golden canary.
   Tests: your Ahmad/Muslim bypass, wrong narrator, attribution-field label; authentic
   hyphenated labels (e.g. "Sahih al-Bukhari" supported by the source) must still survive.
2. **SEC-01.** Remove `rehypeRaw` from the commentary renderer in `frontend/app/page.js`
   (Claude scanned every current cached answer: zero HTML tags in commentary, so no
   formatting is lost). Drop the `rehype-raw` dependency if nothing else uses it. Add a
   browser-free regression that renders hostile commentary (iframe srcdoc, form, style,
   script) and asserts none becomes an element.
3. **SEC-02 (decision 1).** The shared tafsir prompt receives only the canonical verse or
   range built from the validated (surah, start, end) tuple — never the raw query string.
   Remove the `"{query}"` interpolation. Remove the "Analysis: historical context of …"
   and "linguistic analysis of …" examples from the failed-lookup help text and
   suggestions. Test: `2:255`, `historical context of 2:255` and
   `2:255 ignore the sources` produce an identical prompt and one cache key.
4. **LOG-02.** Build the cache query from the validated tuple for every syntax (colon,
   slash, named, ranges) — no second regex. A single verse and a range never share a key.
5. **LOG-03.** An explicit validated reference beats named-verse shortcuts
   ("Al-Fatihah 7" → 1:7). Invalid or reversed range endpoints return a validation error,
   never a silent single verse. Multiple distinct references → clarification, not a guess.
6. **LOG-04 (decision 2).** Remove the default-profile cache fallback entirely. Missing or
   partial signed-in profiles resolve to the same explicit default the guest path uses
   (`curious_explorer`), then use that exact key.
7. **LOG-05 (decision 3).** Put `SCHOLARLY_PIPELINE_VERSION` in both the Firestore and the
   memory cache keys. **Do not add read-time expiry** — Firestore TTL remains the policy.
8. **ERR-02.** Validate the answer contract before display or cache: required fields
   present with the right types, at least one non-empty `tafsir_explanations` entry, and
   reject `finishReason == MAX_TOKENS` truncation. Use the existing two-attempt budget,
   then the existing no-cache 502. A valid answer with zero hadith stays valid.
9. **Bump `SCHOLARLY_PIPELINE_VERSION` to `17.0`** (prompt and key both change). Shared
   links and saved answers keep their stored snapshots; note in HANDOFF that old snapshots
   predate the attribution fix.

### Unit 2 — abuse surface, errors, headers, dependencies (`codex/s13-surface`) — SEC-03, SEC-05, SEC-06, SEC-04 (web), OPS-03, Iman gating

1. **Iman (decision 5).** All 28 `/iman/*` routes return 404 unless env `IMAN_ENABLED=1`,
   mirroring `debug_route_required`. The frontend calls none of them (verified).
2. **SEC-03 (decision 6, cheap path).** `admin_secret_required` on `/cache/lookup`,
   `/cache/analytics`, `/cache/popular` (the frontend calls none of them — verified). Bound
   `USER_RATE_LIMITS` and `ANALYTICS` (evict stale keys, cap size) and take the lock on every
   rate-limit check. Derive the guest identity from the trusted Cloud Run proxy hop
   (Werkzeug `ProxyFix` with the correct `x_for` count — justify the count from Cloud Run's
   documented `X-Forwarded-For` behaviour in HANDOFF; never trust the leftmost value).
   Apply the rate limit to `/feedback`. No durable cross-instance quota system.
3. **SEC-05.** Replace every `jsonify({"error": str(e)})` and the auth `"details": str(e)`
   with a stable generic message plus a short request ID; log the exception server-side with
   that ID. Caller mistakes become 400s through explicit validation. Add a test that scans
   app.py so `str(e)` cannot return to a response body.
4. **SEC-06.** Frontend: `X-Frame-Options: DENY`, `Content-Security-Policy:
   frame-ancestors 'none'`, `Referrer-Policy: strict-origin-when-cross-origin`, HSTS — via
   `next.config.mjs` headers. A fuller script/connect CSP ships as
   **`Content-Security-Policy-Report-Only`** only, so Firebase Auth and reCAPTCHA cannot
   break; list the domains it allows.
5. **SEC-04 (web) + OPS-03.** Move Next to the patched 15.x release and Capacitor to the
   patched release named in your appendix; regenerate the lockfile. Dockerfile: `npm ci` in
   the builder; the runtime stage reuses the builder's pruned `node_modules` instead of a
   second unpinned install, so runtime Next equals build Next. Add `frontend/.dockerignore`.
   Run `npx cap sync ios` and update `Package.resolved`; do not build or ship iOS.
   Re-run `npm audit --omit=dev` and `pip-audit` and record what remains and why.

### Unit 3 — client resilience (`codex/s13-client`) — ERR-01, ERR-03, ERR-04, ERR-05, ERR-06, LOG-11

1. **ERR-01.** `get_verse_from_firestore` distinguishes "no such verse" from a dependency
   failure; the latter returns a retryable 503 with the generic reader copy, never "Verse
   not found". `/daily-verse` must not return 200 with empty text.
2. **ERR-03.** Clear account-bound state on every auth change; accept a response only if
   the initiating UID and a request generation still match (profile, saved, history,
   annotations, progress, plans). Keep raw fetch + local state (AI.md).
3. **ERR-04.** Each search captures its own controller, timer and generation; only the
   current request may update loading/error state or clear its own timer.
4. **ERR-05.** Call `initializeRecaptchaConfig` only in the browser (client effect or a
   `typeof window` guard) and handle its rejection. **Keep reCAPTCHA** (AI.md). The build
   must no longer print `window is not defined`.
5. **ERR-06.** Saved and history screens show a load error with retry (and re-auth on
   401) using `lib/errors.js` and `ErrorNotice`; an empty list means genuinely empty.
   `reportBackendSuccess` only after a successful response.
6. **LOG-11.** Share state belongs to the current answer: reset it on a new answer and
   discard late results for an old one.

### Unit 4 — private data (`codex/s13-privacy`) — PRIV-01, PRIV-02, PRIV-03, PRIV-04

1. **PRIV-01.** Make encryption policy explicit: if `REFLECTION_ENCRYPTION_SECRET` is
   absent in production, log a startup warning (do not crash). Reads must accept legacy
   plaintext and new ciphertext (version-prefix the ciphertext). Write
   `backend/scripts/encrypt_existing_reflections.py` — idempotent, update preconditions,
   dry-run by default — but **do not run it**. Add the secret reference to
   `deploy-backend.sh` (`--set-secrets REFLECTION_ENCRYPTION_SECRET=reflection-encryption-key:latest`)
   and note in HANDOFF that Claude must create that secret before the next backend deploy.
2. **PRIV-02.** Account deletion: a reauthenticated "Delete account" in Settings with a
   clear confirmation, backed by an idempotent, resumable backend route that deletes every
   collection in your appendix inventory (including `iman_correlation_narratives` and
   `iman_struggle_goals`), removes the Firebase Auth user last, and clears browser state.
   Shares have no owner field today — record that and propose a policy; do not invent one.
3. **PRIV-03.** Log canonical verse, status and request ID, never raw query text or
   feedback bodies; redact email from feedback logs.
4. **PRIV-04.** Draft `/privacy` (Next route) from your appendix inventory: what is
   collected, model processing (Vertex AI), storage, retention, deletion, shares, contact.
   Serious plain tone, no emoji. Mark contact details `[Ahmed to confirm]` — Claude will
   not deploy it until Ahmed reviews the text. Link it from the auth screen and Settings.

### Unit 5 — progress and reads (`codex/s13-progress`) — LOG-06, LOG-07, LOG-08, PERF-01, PERF-02

1. **LOG-06.** Transactions (or ArrayUnion plus a consistent count) for explored verses,
   plans and collections.
2. **LOG-07.** Integer days only, idempotent completion, next day derived from the
   completion set, validate before a transactional write.
3. **LOG-08.** Make every advertised badge reachable, or stop advertising the ones whose
   events do not exist yet. No spirituality inferred from journal content.
4. **PERF-01.** One bounded badge check per study event, using a maintained annotation
   count instead of streaming up to 1,001 documents.
5. **PERF-02.** Paginate saved/history/search metadata; fetch a full saved answer on
   demand; read each surah once per catalog response.
6. LOG-09, LOG-10 and PERF-03 are **out of scope**: Iman is gated in Unit 2 and PERF-03 is P3
   at current traffic.

### Unit 6 — deploy verification and boundary tests (`codex/s13-verification`) — OPS-02, MAINT-01

1. **OPS-02.** Both deploy scripts capture the revision they created, then verify its image
   digest, readiness and actual traffic share; fail loudly with the exact diagnosis if
   production does not serve it (pinned traffic, retired revision, a canary reported as
   latest). Keep intentional no-traffic canaries possible via a flag. Test with stubbed
   `gcloud`.
2. **MAINT-01.** Boundary fixtures that keep the real decorators, parser, cache and share
   helpers with fake clients: guest/required/admin/debug/cron denial, share ownership
   assumptions, cache identity across syntaxes and profiles.

### Global rules
Short plan → implement → verify → HANDOFF entry per unit with branch + commit. No deploys,
no gcloud mutations, no secrets, no paid or live calls, no new runtime dependencies beyond
the patched upgrades in Unit 2. Keep AI.md conventions: monolith, raw fetch + local state,
deterministic retrieval. Ahmed's tone rules for any reader copy: no emoji, no exclamation
marks, serious and respectful. Line numbers drift — trust the code. Full offline suite and
`npm run build` green after every unit. Finish with the summary table
(unit | branch | commit | findings closed | verified | deploy-needed backend/frontend/none),
plus anything skipped and why.

---

## Session 12 prompt (2026-10-17) — FULL READ-ONLY AUDIT by GPT 6: security, vulnerabilities, logic, performance, error handling, privacy, reliability

---

You are GPT 6, acting as **independent auditor** for Tadabbur (Claude = architect/reviewer,
Ahmed = owner). This session produces **findings, not fixes**. Claude will review your
report and turn it into fix sessions.

### 0. Orientation (do this first)

`git pull`, then read, in order: `AI.md` (architecture, decisions, conventions, the model
table), the top five entries of `HANDOFF.md`, `docs/AUDIT-2026-08-01.md` (Claude's earlier
audit — its resolved items are history; only re-raise one if you can show it regressed), and
`docs/QUALITY-REVIEW-2026-08-03.md`. Audit `main` at or after commit `2271020`.

**What Tadabbur is:** an AI-assisted Qur'an study app. A reader picks a verse or range; the
Flask backend assembles classical tafsir excerpts (Ibn Kathir, al-Qurtubi to 4:22, Ihya,
Madarij, Riyad al-Salihin, A Thematic Commentary on the Qurʼan), Gemini writes a
persona-tailored explanation, hadith are validated against the supplied source text before
display or caching, and answers are cached in Firestore for 90 days. Plus accounts, guest mode,
saved answers, reflections/annotations, reading plans, streaks, badges, share links, topic
discovery, and a Capacitor iOS shell.

**Production right now:** backend Cloud Run `tafsir-backend-00273-dpr` (project
`tafsir-simplified`, us-central1), `gemini-3.8-flash` + `gemini-3.5-flash-lite` on the Vertex
global endpoint, scholarly pipeline `16.0`; frontend `tafsir-frontend-00307-r65` (Next.js 15,
React 19). Firebase project `tafsir-simplified-6b262`: Auth plus Firestore databases
`(default)` (user data) and `tafsir-db` (verse text, `tafsir_cache`, `shared_content`). Both
databases have deny-all client rules; the frontend uses Firebase Auth only and all data goes
through the backend's Admin SDK. **Note:** `main` contains a frontend error-handling change
(`frontend/app/lib/errors.js`, `components/ErrorNotice.jsx`) that is merged but not yet deployed
— audit it as code that is about to ship. Traffic is tiny (~1-2 organic requests a day), so
weigh risk by exploitability and harm, not by current volume.

### 1. Hard rules

- **Read-only.** No code changes, no refactors, no dependency changes. Your only commits are
  the audit document and a `HANDOFF.md` session-log entry, on branch `codex/audit-gpt6`.
- **Production is off-limits for active testing.** No fuzzing, load tests, auth attacks,
  account creation, or requests to admin or cache-mutation routes against the live URLs. At
  most a handful of `GET /health` and other read-only public GETs to confirm a header or
  behaviour, and say so in the report when you do.
- **The local backend is not a sandbox.** `./backend/run-local.sh` talks to the PRODUCTION
  Firestore and to PAID Gemini. Running it is allowed for observing behaviour, but: never
  call `/cache/*` or `/debug/*` routes, never trigger fresh `/tafsir` generations for
  uncached verses (each costs money and writes the shared production cache), and never
  write user data. Prefer code reading plus the offline suite.
- No gcloud mutations, no secret access (`secret/admin-secret.txt` stays unread), no deploys.
- Offline tooling is fine: `python3 -m pytest backend/tests -q` (venv `backend/venv`),
  `node frontend/tests/*.test.*`, `npm run build`, `npm audit --omit=dev`, and `pip-audit`
  run from a throwaway venv OUTSIDE the repo against `backend/requirements.txt`. Record exact
  commands and versions.
- Ahmed's standing rules apply to any copy you propose: no emoji, no exclamation marks,
  serious and respectful tone suited to scriptural content.
- Decisions recorded in `AI.md` (deliberate monolith, raw fetch plus local state, no vector
  search, min-instances 0, 180s frontend abort) are not findings by themselves. You may flag a
  concrete risk they create, with evidence, but do not recommend reversing them on taste.

### 2. Evidence standard

Every finding needs **evidence a reviewer can check in two minutes**: `path:line`, the exact
code, and either a reproduction (offline test, local request, or a precise request/response
trace) or a clear argument from the code. Mark each finding **Confirmed** (reproduced or
unambiguous from code) or **Suspected** (plausible, needs a runtime check — say what check).
No speculative "best practice" items without a concrete failure mode in THIS codebase.
Line numbers drift — quote the code. If you check something and it is fine, record it in the
"Verified safe" section; that list matters as much as the findings.

Severity: **P0** exploitable now or causes data loss / wrong scripture attribution shown to
readers; **P1** serious but needs a precondition, or a likely production failure; **P2**
real defect with limited blast radius; **P3** hygiene. Give likelihood and impact separately,
plus effort **S/M/L**.

### 3. Scope — audit every dimension

**A. Security and vulnerabilities**
- Every route in `backend/app.py`: list method, path, auth (`@firebase_auth_required`,
  `@firebase_auth_optional`, `admin_secret_required`, `debug_route_required`, or none), rate
  limit, input validation, and what a guest, a signed-in reader, and another reader's ID can
  reach. Hunt specifically for **IDOR**: any route taking an ID (annotation, saved search,
  share, plan, reflection, heart note) that does not prove the record belongs to the caller.
- Token verification paths, admin-secret handling, CORS allowlist, debug-route gating, the
  feedback cron secret, the suspended-but-live Iman Journal endpoints.
- **Prompt injection:** how reader-supplied text (the `/tafsir` query, topic text, reflection
  text) reaches Gemini prompts; whether model output can change control flow, cache contents
  served to others, or rendered markup.
- **XSS / unsafe rendering:** the frontend renders model-written commentary with
  `ReactMarkdown` plus `rehype-raw` (raw HTML enabled) — see the `tafsir_explanations`
  render in `frontend/app/page.js`. Determine what HTML a model (or a cached/shared answer)
  could inject and what React 19 / react-markdown actually let through. Check every other
  `ReactMarkdown`, `dangerouslySetInnerHTML`, and `href` built from data.
- **Information disclosure:** about 69 backend routes return `jsonify({"error": str(e)})`
  on 500, and the token-verification failure returns `"details": str(e)`. Quantify what can
  leak (project IDs, paths, Firestore/Google exception text) and which routes the shipped UI
  calls.
- Rate limiting: in-memory, per instance, keyed by `request.remote_addr` with **no
  `ProxyFix`** behind Cloud Run's front end. Establish what `remote_addr` actually is on Cloud
  Run (code, docs, or one harmless observation) and whether guests therefore share one bucket,
  can evade the limit, or both. Also check memory growth of the rate-limit and response-cache
  dictionaries.
- Cost abuse: how many paid Gemini generations an anonymous actor can trigger per hour and
  per day, and whether anything caps total spend.
- Secrets and config in the repo and Docker images (`.gcloudignore`, `.dockerignore`), the
  public Firebase web config (expected public — confirm nothing more sensitive ships), Secret
  Manager usage.
- Dependency vulnerabilities: `npm audit --omit=dev` and `pip-audit`; for each high/critical,
  state whether the vulnerable code path is actually reachable here.
- Security headers on the frontend (CSP, HSTS, X-Frame-Options/frame-ancestors,
  Referrer-Policy) and backend; the Capacitor iOS shell (`capacitor.config.ts` loads the
  production URL — navigation allowlist, external links); the service worker (`public/sw.js`)
  — can it cache authenticated responses?
- Firestore rules as deployed vs `backend/firestore.rules`, and whether any client path could
  still write data.

**B. Logic and correctness**
- Verse-reference parsing (numeric, named surahs, ranges, out-of-range verses, Arabic
  numerals, mixed input), the range budget (the picker said "limited to 6 verses" for 2:1
  while the backend capped at 10 — find which is authoritative and whether they disagree).
- Cache correctness: key composition (the key omits the pipeline version — a canary overwrote
  production docs during the 3.8 migration), guest-key vs default-profile fallback, version
  gate, TTL, `/share` snapshots, recommendations rebuilt at serve time.
- Hadith validation (`services/hadith_validation.py`): false negatives (real hadith dropped)
  and false positives (unsupported attribution kept), the downgrade-not-drop path, the
  hyphen-tolerant collection patterns added on 2026-10-01.
- Streaks, badges, progress and reading plans: timezone handling (naive UTC), double
  counting, idempotency, concurrent requests.
- Topic discovery: closed-vocabulary enforcement, fallback paths.
- Persona handling: guest default profile vs signed-in profile, missing or partial profiles.

**C. Performance**
- `/tafsir` end to end: ~27s median on fresh answers under 3.8; break it down from
  `Server-Timing` and `REQUEST_METRIC`/`GEMINI_USAGE` logs if you can read them (read-only),
  otherwise from code. Startup cost (GCS corpus loads, precomputed budgets), cold starts with
  min-instances 0, Gunicorn 1 worker / 8 threads, memory headroom at 2 GiB.
- Firestore access patterns: N+1 reads, unbounded queries (`.stream()` without limits),
  missing indexes, reads on hot paths.
- Frontend: bundle size (first-load JS ~303 kB on `/`), the ~3,000-line `page.js` and its
  re-render behaviour, images, caching headers, the build-time
  `ReferenceError: window is not defined` (server chunk, every Cloud Build since August).

**D. Error handling and resilience**
- Backend: bare or broad `except` blocks that swallow failures, missing timeouts on outbound
  calls (Vertex, Firestore, GCS), partial-failure states (answer generated but cache write
  failed, progress written twice), retry behaviour (the bounded malformed-output retry and
  the 429/503 retry paths), logging hygiene (is reader text or PII logged?).
- Frontend: review the new `lib/errors.js` and `ErrorNotice` critically — any path that can
  still show raw error text, any state that strands a reader with no way forward, unhandled
  promise rejections, `ErrorBoundary` coverage, auth-state edge cases (expired token mid-
  session, sign-out during a request).

**E. Privacy and data**
- Inventory personal data stored (email, display name, reflections, query history, saved
  answers, Iman data) with location and retention. **Reflection encryption:** the backend
  supports encrypting reflections, but `REFLECTION_ENCRYPTION_SECRET` is not set in the
  production revision or `deploy-backend.sh` — confirm what is actually stored and assess.
- There is no in-app account deletion (also an App Store blocker); map every collection a
  deletion would need to cover.

**F. Reliability, operations and cost**
- Deploy scripts and their traps (documented in AI.md: `--no-traffic` pinning, retired
  revisions skipped by `--to-latest`, cache-key overwrite by canaries), Firestore backups
  (do any exist?), single region, alert coverage (5xx, PermissionDenied, `/health` uptime),
  spend controls on Vertex and Firestore.

**G. Maintainability and tests**
- Test coverage of the paths that matter most (auth, `/tafsir`, hadith validation, cache,
  share); critical paths with no offline test; dead code; duplicated logic. Keep this section
  short and concrete.

### 4. Deliverable

Write `docs/AUDIT-2026-10-GPT6.md` with exactly these sections:

1. **Executive summary** — 10 lines: overall posture, the three most important risks, and
   whether anything needs action before the next deploy.
2. **Scorecard** — one row per dimension A-G: rating (Strong / Adequate / Weak / Critical)
   and a one-sentence reason.
3. **Ranked findings table** — ID (`SEC-01`, `LOG-01`, `PERF-01`, `ERR-01`, `PRIV-01`,
   `OPS-01`, `MAINT-01`), title, severity, Confirmed/Suspected, effort, area.
4. **Detailed findings** — per finding: evidence (path:line plus the quoted code), what goes
   wrong and for whom, reproduction or proof, recommended fix (specific, minimal, consistent
   with AI.md conventions), the offline test that would prove the fix, and effort.
5. **Verified safe** — everything you checked and found sound, with one line of evidence each.
6. **Leads you could not verify** — and exactly what check would settle each.
7. **Proposed fix sessions** — group findings into 3-6 implementable units (branch name,
   files, acceptance criteria, deploy needed: backend/frontend/none), P0/P1 first.
8. **Appendix** — route inventory table, tool outputs (`npm audit`, `pip-audit`, test
   runs) with commands and versions.

Then add a `HANDOFF.md` session-log entry: branch, commit, counts by severity, the top three
risks, anything that should block the next deploy. Finish with a summary table (dimension |
rating | P0 | P1 | P2 | P3) and a list of anything you skipped and why.

---

## Session 11 prompt (2026-09-28) — visual coherence pass: kill the reCAPTCHA badge, the floating FAB, and the colour chaos

---

You are GPT 5.6/6, main coder for Tadabbur (Claude = architect/reviewer, Ahmed =
owner). `git pull` and read the top entries of `HANDOFF.md`.

**State:** Session 10 (Units 1-4) is merged on `main`; backend is verified but **not yet
deployed**, frontend deploy is held. Pipeline **15.1**, 441 offline tests green. macOS:
`python3`, venv at `backend/venv`.

**This session is FRONTEND-ONLY and purely visual.** Ahmed reviewed the real answer
screen on an iPhone and called the layout "unorganized". His words also: the captcha
symbol in the bottom corner "looks funny, please remove", and — standing rule — **no
emoji anywhere, professional and serious, Islamic aesthetic matching the gravity of the
content**. Do not change any backend behaviour, API shape, or copy semantics.

Claude inspected three device screenshots and traced every issue to source. Work the
units in order; they are independent commits.

### Unit 1 — remove the reCAPTCHA badge, correctly (branch `codex/s11-recaptcha`)

The floating Google reCAPTCHA badge sits bottom-right and overlaps the "Continue
reflecting" cards. It is injected because `app/lib/firebase.js:12` calls
`initializeRecaptchaConfig(auth)`.

**Do NOT delete `initializeRecaptchaConfig`.** It enables Firebase Auth bot protection;
removing it weakens sign-up/sign-in security. Remove only the *visual badge*:

1. Hide the badge in `app/globals.css`:
   `.grecaptcha-badge { visibility: hidden; }`
2. **Google's Terms require attribution when the badge is hidden.** Add small,
   unobtrusive footer text wherever the auth/sign-in surface lives (and the app footer
   if there is one), using `--color-text-secondary` at ~0.75rem:
   "This site is protected by reCAPTCHA and the Google
   [Privacy Policy](https://policies.google.com/privacy) and
   [Terms of Service](https://policies.google.com/terms) apply."
   Links open in a new tab with `rel="noopener noreferrer"`.
3. Confirm the badge is gone and auth still works locally.

### Unit 2 — remove the floating help button (branch `codex/s11-fab`)

`FloatingHelpButton` (`app/components/HelpMenu.jsx:1040-1068`) renders a
`position: fixed` 44px circle at `bottom: 24px; right: 16px` with
`background: linear-gradient(135deg, var(--primary-teal) 0%, var(--gold) 100%)`. In
Ahmed's screenshots it **covers body text mid-sentence** and sits on top of the
recommendation cards. The teal-to-gold gradient also matches nothing else in the app.

1. Remove the `<FloatingHelpButton />` render at `app/page.js:2298` and its import at
   `app/page.js:24`. **Keep `HelpMenu` itself** and keep the F1 keyboard shortcut.
2. Give help a non-overlapping entry point: add a plain text/icon-free "Help" item to
   the existing navigation (see `DesktopNav.jsx` and the mobile nav) that calls
   `setHelpMenuOpen(true)`. Match the surrounding nav items exactly — no gradient, no
   circle, no badge.
3. Delete the now-unused `FloatingHelpButton` export and its `styled-jsx` block.
4. Check no other screen relied on that button.

### Unit 3 — one restrained colour system (branch `codex/s11-palette`)

This is the main cause of "unorganized". The answer screen currently shows **six**
unrelated accent families: brand teal, gold/amber, slate, blue, magenta, and purple.
For Qur'anic commentary this reads arbitrary and unserious.

Available brand tokens (`app/globals.css`): `--primary-teal`, `--primary-teal-dark`,
`--primary-teal-light`, `--gold`, `--gold-text`, `--gold-light`, `--foreground`,
`--color-text-secondary`, `--color-border`, `--color-surface`.

1. **Progression cards** — `app/page.js` ~3368-3415, the baseline/ascent/peak blocks
   currently hardcode slate `#94a3b8`, blue `#3b82f6`, magenta `#d946ef` as
   `borderLeft` + label colour + 8%-alpha background. Replace all three with a single
   restrained treatment: the SAME neutral `--color-border` left rule and
   `--color-text-secondary` label on every step, distinguishing the three stages by
   **label text and vertical order alone**, not by hue. If a visual gradient of
   emphasis is wanted, use increasing left-rule weight or `--primary-teal` tints only —
   never three unrelated hues.
2. **Reflection card** — `app/page.js` ~3228-3262 hardcodes purple `#7c3aed` for the
   "REFLECTION" label and `linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)` for the
   "Sign in to save your reflection" button. Re-tone to the brand: label in
   `--color-text-secondary` or `--primary-teal-dark`, button in flat `--primary-teal`
   (no gradient), matching the app's other primary buttons.
3. Sweep `app/page.js` and `app/components/*` for any other hardcoded hex accent that is
   not teal/gold/neutral and bring it into the token set. **Do not restyle the Arabic
   verse display, the tafsir source header bar, or the hadith card** — those already
   read correctly; only remove off-palette colour.
4. No new colours, no gradients on interactive elements.

### Unit 4 — fix the clipped "Continue reflecting" row (branch `codex/s11-recs`)

In the screenshots the second recommendation card is cut off at the viewport edge with
text truncated mid-word and no affordance showing the row scrolls.
`app/components/RecommendationBar.jsx` uses `display: flex; overflow-x: auto;` with
`flex-shrink: 0; max-width: 220px` children.

1. On narrow viewports (max-width ~640px) **stack the cards into a single column**
   instead of a horizontal scroller, so nothing is ever clipped. Keep the horizontal
   row on wider screens if it looks right there.
2. If you keep any horizontal scroller, add `scroll-snap-type: x mandatory` with
   `scroll-snap-align: start` on the cards, and side padding so the last card can rest
   fully on screen.
3. Ensure page content is not obscured by anything `position: fixed` — after Units 1
   and 2 there should be nothing left overlapping, so verify by scrolling to the very
   bottom of a full answer.
4. **Heading consistency:** "Continue reflecting" renders at a noticeably different size
   and weight from the neighbouring "Hadith" heading. Make section headings within the
   answer view share one class and one type scale.

### Not a bug — do not "fix" this
The dark circular **"N" badge at bottom-left is the Next.js dev-tools indicator**. It
appears only in `npm run dev` and is absent from production builds. Leave it alone.

### Global rules
Per unit: short plan → implement → verify → HANDOFF session-log entry with branch +
commit. `npm run build` must pass and the backend suite must stay green (you should not
be touching it). No deploys, no gcloud, no secrets, no new dependencies, no backend or
API changes, no pipeline bump, no emoji. Describe in your HANDOFF entry what each screen
looks like after the change, since Ahmed reviews on a device before any deploy. Finish
with the summary table (unit | branch | commit | verified | deploy-needed
backend/frontend/none).

---

## Session 10 prompt (2026-09-28) — presentation pass: drop the corpus notice, full source titles, zero emoji, and REDESIGN topic discovery

---

You are GPT 5.6/6, main coder for Tadabbur (Claude = architect/reviewer, Ahmed =
owner). `git pull` and read the top entries of `HANDOFF.md`.

**State:** `main` is at the Session 9 merges. Backend `tafsir-backend-00270-9fr` is
live; **topic discovery (Unit 2) is merged but was NEVER DEPLOYED** — Ahmed reviewed
it locally and rejected the presentation. Production has never served it, so you are
correcting an unshipped feature, not fixing a live regression. Pipeline stays **15.1**.
Baseline: 438 offline tests green, zero deprecation warnings. macOS: `python3`, venv
at `backend/venv`.

**Ahmed's direction, verbatim in substance:** the current topic UI is not acceptable;
the presentation must be *professional, serious, and follow an Islamic aesthetic that
matches the gravity of the content*. **He does not want emoji anywhere.** Treat
restraint as the design goal: typography, hierarchy and spacing carry the design — not
decoration, not novelty, not playful copy.

Four units. Units 1-3 are small and independent; do them first and keep them in
separate commits so they can ship without waiting on Unit 4.

### Unit 1 — remove the al-Qurtubi absence notice (branch `codex/s10-notice`)

`backend/services/source_service.py:1765` appends
`"Al-Qurtubi is not available in this corpus for this verse."` to `notices`. Ahmed
does not want absence advertised to readers — the panel should state what *was* used,
nothing more.

1. Delete that append. **Keep the `notices` key** in the `source_coverage` contract
   (it stays an empty list) so the response shape and the frontend's
   `(source_coverage.notices || []).map(...)` in `frontend/app/page.js` need no change.
   Do not remove the frontend rendering — a future notice type may use it.
2. The `classical.al_qurtubi: false` flag stays as-is; the badge simply does not render.
3. Verify no offline test asserts that notice text (there is none today, but check).

### Unit 2 — full scholarly source titles (branch `codex/s10-titles`)

The coverage panel shows the bare label `Thematic Commentary`. Ahmed wants the real
title. In `backend/services/source_service.py`, the display name is set at **line 721**
and **line 903** as `"name": "Thematic Commentary"`.

1. Change the display name to exactly: `A Thematic Commentary on the Qurʼan`
   (note U+02BC MODIFIER LETTER APOSTROPHE in `Qurʼan`, matching Ahmed's request).
2. **Before changing it, grep for code that compares against the string
   `"Thematic Commentary"`** (routing, filtering, `filter_unavailable_sources`, plan
   pointers, tests). If any logic matches on the display name, decouple it: keep the
   internal key `thematic` for logic and change only what is rendered. Do not let a
   display rename alter retrieval behavior.
3. Check the other additional sources render their proper titles too — `Ihya Ulum
   al-Din`, `Madarij al-Salikin`, `Riyad al-Salihin` — and leave them alone if already
   correct. Do not invent new attributions.
4. Update any offline test asserting the old display string.

### Unit 3 — remove every emoji (branch `codex/s10-no-emoji`)

Audit result (Claude, 2026-09-28): the **frontend is already emoji-free** — the arrows
(`←`, `→`) are typography, keep them. All emoji live in `backend/app.py`:

1. **User-facing, highest priority — these are what Ahmed saw:**
   - `app.py:6371` — `'📚 Full surah queries are not currently supported.'`
   - `app.py:6380` — `'🤔 I couldn\'t find that verse. Let me help you format it correctly.'`
   Remove the emoji, keep the sentences. Also re-read the surrounding `help_text` /
   `example_suggestions` copy and make the tone plain and respectful — no exclamation
   marks, no chattiness. This is the screen a reader hits when a lookup fails.
2. **Gemini prompt section markers** at approximately `app.py:2924, 2932, 3017, 3025,
   3055, 3076` (`📖 TAFSIR-BASED APPROACH`, `⚠️ NOTE`, `✅ ENHANCE CLARITY`,
   `❌ PRESERVE ACCURACY`, `🚨 STRICT VERSE LIMIT`). Replace each with a plain uppercase
   text marker carrying identical meaning (e.g. `NOTE:`, `ENHANCE CLARITY:`,
   `PRESERVE ACCURACY:`, `STRICT VERSE LIMIT:`). **Change nothing else about the prompt
   — no rewording of instructions, no reordering.** The semantics must be identical.
   **Do NOT bump `SCHOLARLY_PIPELINE_VERSION`:** the output contract is unchanged and a
   bump would invalidate the entire production cache. Flag it in your HANDOFF entry so
   Claude can spot-check generation quality against a known verse before deploy.
3. **Out of scope:** `deploy-backend.sh`, `deploy-frontend.sh`, `backend/run-local.sh`
   are developer-facing; leave their emoji alone unless Ahmed says otherwise.
4. Add a small offline test asserting no pictographic emoji appear in the user-facing
   help messages, so this cannot regress.

### Unit 4 — REDESIGN topic discovery (branch `codex/s10-topics-redesign`)

Keep the entire backend: `/topics/resolve`, `services/topic_service.py`, the closed
vocabulary, and the seed data are all approved and verified — **do not touch the
backend contract or the security model** (the model must never supply a verse
reference). This unit is presentation only.

What is wrong with the current frontend (Claude's review):

- `frontend/app/page.js` bolts a **second search form** onto the home screen with
  inline styles that match nothing else in the app. Ahmed does not want a new primary
  affordance competing with the existing Surah/Verse picker.
- The existing "verse not found" content was wrapped in a raw `<details>` toggle
  labelled "Looking for a verse reference instead?" — a crude demotion of working UI.
- `TopicExplorer.jsx` ships its own ad-hoc `styled-jsx` block instead of the app's
  existing design language, and requires an extra "Explore as a topic" button press.

Redesign requirements:

1. **Remove the bolted-on `<form id="home-search">`** from `page.js` and **remove the
   `<details>` wrapper**, restoring that content to its previous structure. Revert those
   two edits cleanly.
2. Surface topic discovery **only where it is already relevant**: the existing
   not-a-verse result screen. It should read as a calm, scholarly continuation of that
   screen, not a second product bolted on.
3. **Use the app's existing design tokens and component idioms** (`--primary-teal`,
   `--color-surface`, `--color-border`, `--foreground`, existing card/badge/chip
   patterns — look at `ThemeExplorer` and the source-coverage panel and match them).
   No bespoke `styled-jsx` visual language, no new colors, no rounded-pill novelty
   that the rest of the app does not use.
4. **Tone and typography:** no emoji, no exclamation marks, no coaching voice. Serious,
   plain, respectful copy. Prefer a clear heading, generous whitespace, and restrained
   type scale. Verse references should be presented with the dignity the rest of the
   app gives them.
5. **Reduce friction:** do not require a separate "Explore as a topic" click if the
   screen is already a failed verse lookup — resolve on arrival, with a quiet loading
   state. Keep the AbortController, the 30s timeout, the null-guarding, the graceful
   fallback to curated themes, and the `aria-live` status region exactly as they are;
   those were reviewed and are correct.
6. Keep `key={query}`-style remounting semantics so state resets per query.
7. **Verify:** `npm run build`; offline backend suite still 438+ green; and describe
   in your HANDOFF entry exactly what the redesigned screen looks like, since Ahmed
   will review it locally before any deploy.

### Global rules
Per unit: short plan → implement → verify → HANDOFF session-log entry with branch +
commit. No deploys, no gcloud, no secrets, no live/paid probes, no drive-by refactors,
no new dependencies, no pipeline bump. Line numbers drift — trust the code. Finish with
the summary table (unit | branch | commit | verified | deploy-needed
backend/frontend/none), plus anything skipped and why.

---

## Session 9 prompt (2026-09-19) — Iman retry-branch fix + free-text topic discovery (Unit 2 UNGATED)

---

You are GPT 5.6/6, main coder for Tadabbur (Claude = architect/reviewer, Ahmed =
owner). First: `git pull` and read the top entry of `HANDOFF.md`.

**State:** Session 8 Unit 1 is merged and DEPLOYED — backend
`tafsir-backend-00270-9fr` (merge `3d0983a`), frontend `tafsir-frontend-00305-q78`,
pipeline **15.1** (unchanged; do not bump). Offline baseline is **393 tests green**
with zero deprecation warnings — keep it that way. Workstation is macOS: use
`python3` / zsh and the venv at `backend/venv`
(`source backend/venv/bin/activate`). Traffic is still tiny (~7 organic /tafsir
requests per fortnight), so favor correctness and clarity over premature tuning.

Two units, one branch each, worked IN ORDER. Unit 1 is small and should land first
so Unit 2's review is not mixed with unrelated changes.

### Unit 1 — finish the falsey-Response retry fix (branch `codex/s9-iman-retry`)

Claude's Session 8 review found that Unit 1's `response is not None` fix was applied
to the main `/tafsir` path only. The identical latent bug remains in two places:
`app.py:9115` (`iman_generate_digest`) and `app.py:9412` (`iman_get_daily_insight`),
both still `status_code = response.status_code if response else 500`.

`requests.Response.__bool__` returns `status_code < 400`, so a 429 or 503 response is
falsey, `status_code` collapses to 500, and the `if status_code in (429, 503) and
attempt < max_retries - 1` branch never fires — those retries are dead code today.

1. Change both sites to `response is not None`, matching `app.py:6746`. Nothing else
   in those handlers changes — no restructuring, no moving parsing into the loop.
   These are Iman Journal handlers on a surface README documents as suspended, so
   the fix is for consistency and future correctness, not a user-facing bug.
2. Add an offline test asserting that, for each of those two handlers, a 429 first
   response triggers exactly one retry and a 503-on-last-attempt still raises. Follow
   the existing harness style in `backend/tests/test_tafsir_retry.py` (AST-extract the
   real handler, fake the namespace) rather than inventing a second pattern.
3. Verify: full suite green from repo root
   (`python3 -m pytest backend/tests -q -W error::DeprecationWarning`), backend
   compiles. Backend-only deploy.

### Unit 2 — free-text topic discovery (branch `codex/s8-topics`) — review finding 10

**Ahmed has greenlit this.** It is the largest remaining product gap: today a learner
who types "patience during hardship" gets nothing useful, because the app only
understands verse references. Scope contract (Claude reviews against this):

- **Goal:** a learner types a life question (or taps a theme) and lands in the
  ordinary verse-answer flow. Topic → verses must be deterministic and grounded;
  **the LLM never invents verse references.**
- **Retrieval spine (no vector search — AI.md convention):** reuse
  `services/source_service.py` keyword routing plus the curated-theme machinery from
  `codex/s6-themes` as the candidate generator. Build a small topic→verse index at
  startup from existing local data (theme seed lists + keyword maps). No new external
  data sources, no new dependencies.
- **LLM role (lite model only):** `GEMINI_LITE_MODEL_ID` maps free text → up to 3
  candidate topics drawn from OUR index vocabulary — a closed set, JSON-schema
  output, and anything outside the vocabulary is rejected rather than passed through.
  On mapping failure, respond with the 8 curated themes as suggestions; never an
  error dead-end. Output budget 4,096, consistent with the Session 7 thinking-safe
  budgets.
- **Endpoint:** `POST /topics/resolve` `{text}` → `{topics: [{name, verse_refs (from
  the index), confidence}]}`. Guest-allowed, same in-memory rate-limiting family as
  `/tafsir`, response cached in memory. No Firestore writes, no pipeline interaction.
- **Frontend:** the home search box detects non-verse queries (reuse the existing
  verse-ref extraction's failure path) and offers "Explore as a topic" → calls
  `/topics/resolve` → renders verse chips that feed the EXISTING query flow. No new
  state layer (AI.md convention: local `useState` + raw fetch). Null-guard every
  field that may be absent.
- **Out of scope:** no changes to `/tafsir`, no pipeline bump, no new dependencies,
  no Firestore schema changes.
- **Verify:** offline tests for the index build and closed-set mapping validation
  (fake the lite call — do NOT make live paid calls); `npm run build`; and a manual
  script hitting `/topics/resolve` with 5 sample phrases, with the results documented
  in your HANDOFF entry.

### Global rules
Per unit: short plan → implement → verify → HANDOFF session-log entry with branch +
commit. No deploys, no gcloud, no secrets, no live/paid probes, no drive-by
refactors, no new dependencies. Line numbers drift — trust the code. Finish with the
summary table (unit | branch | commit | verified | deploy-needed
backend/frontend/none), plus anything skipped and why.

---

## Session 8 prompt (2026-08-29) — hygiene + resilience batch, and the gated topic-discovery feature

---

You are GPT 5.6, main coder for Tadabbur (Claude = architect/reviewer, Ahmed =
owner). First: `git pull` and read the top two entries of `HANDOFF.md`. Session 7
is DEPLOYED and canary-validated: backend `tafsir-backend-00269-z5h` (Gemini 3.6,
global endpoint, pipeline 15.1), frontend `tafsir-frontend-00305-q78`. Development
moved to a macOS workstation — commands in older prompts written as `py -3` /
PowerShell are now `python3` / zsh; the backend venv lives at `backend/venv`. Two
weeks of production telemetry exist (REQUEST_METRIC + GEMINI_USAGE): traffic is
tiny (~7 organic /tafsir requests in 15 days), fresh generations run 17.8–32s with
candidates ≤1.7K tokens, and exactly ONE organic defect occurred — Gemini emitted
12 tokens of non-JSON and the P1.2 guard correctly 502'd without caching. Unit 1
is approved to start now. Unit 2 is GATED — do not start it unless Ahmed has
said go in HANDOFF or in your prompt.

### Unit 1 — hygiene + resilience batch (branch `codex/s8-hygiene`)

1. **Delete `backend/test_heading_format.py`.** It asserts the pre-`c7e2511`
   `**Title**` → `## Title` behavior that `utils/text_cleaning.py` deliberately
   dropped, and it cannot even be collected from the repo root (`from utils...`
   needs `backend/` as cwd). It is fully superseded by
   `backend/tests/test_text_cleaning.py` (50 green cases). Do not port anything.
2. **Resolve `backend/test_performance.py`.** It imports `aiohttp` (not in
   `requirements.txt`) and is a live load-generation script against a deployed
   URL, not an offline test. Move it to `backend/scripts/perf_probe.py` with its
   `if __name__ == "__main__"` entry intact and a module docstring stating it is
   live/paid and needs `pip install aiohttp` ad hoc. Do NOT add aiohttp to
   `requirements.txt` (production imports nothing from it).
   `backend/test_verse_extraction.py` is a fine `__main__` script — leave it.
3. **Replace all `datetime.utcnow()` calls** (10 deprecation warnings in the
   suite) with `datetime.now(timezone.utc)`. Preserve stored-format compatibility
   EXACTLY: where the old value was naive and is serialized/compared (Firestore
   fields, isoformat strings, cache timestamps), strip tzinfo or format
   identically so documents written before and after the change compare cleanly.
   Add no new formats.
4. **One bounded retry on malformed Gemini output** in the main `/tafsir` path:
   when `extract_json_from_response` yields `metadata.extraction_error` (the
   fallback dict), make exactly ONE additional Gemini attempt before returning
   the existing no-cache 502. Constraints: total attempts across network retries
   AND this retry stay within the 242s worst-case budget from P1.4 (do not stack
   a new full 120s attempt on top of two existing ones — reuse the second
   attempt slot: i.e., at most 2 total Gemini calls per request, where a
   malformed FIRST response consumes the retry that a network failure would
   have). Log `GEMINI_RETRY_MALFORMED verse=<ref>` on the retry, and keep the
   502-without-caching behavior when the retry also fails. The `/debug/test`
   handler keeps its current single-attempt behavior. Add an offline test that
   fakes a malformed-then-valid response pair and asserts: one retry, success
   cached, log line emitted; and malformed-malformed → 502, nothing cached.
5. **Verify:** full suite green from repo root (`python3 -m pytest backend/tests -q`
   with the venv active — expect 379 + your new tests, 0 skips), zero
   `DeprecationWarning: datetime.datetime.utcnow` lines in the run, backend
   compiles. No pipeline bump — response shape is unchanged.

### Unit 2 — free-text topic discovery (branch `codex/s8-topics`) — finding 10

**SUPERSEDED — ungated 2026-09-19; issued in the Session 9 prompt above.**
Scope contract (Claude will review against this):

- **Goal:** a learner can type "patience during hardship" (or tap a theme) and
  land in the ordinary verse-answer flow. Topic → verses must be deterministic
  and grounded; the LLM never invents verse references.
- **Retrieval spine (no vector search — AI.md convention):** reuse
  `services/source_service.py` keyword routing + the curated-theme machinery
  from `codex/s6-themes` as the candidate generator. Build a small topic→verse
  index at startup from existing local data (theme seed lists + keyword maps);
  no new external data sources.
- **LLM role (lite model only):** `GEMINI_LITE_MODEL_ID` maps free text → up to
  3 candidate topics from OUR index vocabulary (closed set, JSON-schema output,
  reject anything outside the vocabulary). On mapping failure → respond with the
  8 curated themes as suggestions, never an error dead-end. Cap the lite call's
  output budget consistent with Session 7 thinking-safe budgets (4,096).
- **Endpoint:** `POST /topics/resolve` {text} → {topics: [{name, verse_refs
  (from index), confidence}]} with the same in-memory rate limiting family as
  `/tafsir`, guest-allowed, response cached in memory (no Firestore writes, no
  pipeline interaction).
- **Frontend:** the home search box detects non-verse queries (reuse the
  existing verse-ref extraction's failure path) and offers "Explore as a topic"
  → calls `/topics/resolve` → renders verse chips that feed the EXISTING query
  flow. No new state layer (AI.md convention: local useState + raw fetch).
- **Out of scope:** no changes to `/tafsir`, no pipeline bump, no new
  dependencies, no Firestore schema changes.
- **Verify:** offline tests for the index build + closed-set mapping validation
  (fake the lite call); `npm run build`; manual script hitting `/topics/resolve`
  with 5 sample phrases documented in the HANDOFF entry.

### Global rules
Per unit: short plan → implement → verify → HANDOFF session-log entry with
branch + commit. No deploys, no gcloud, no secrets, no drive-by refactors, no
new dependencies. Line numbers drift — trust the code. Frontend: null-guard any
field that may be absent. Finish with the summary table
(unit | branch | commit | verified | deploy-needed backend/frontend/none),
plus anything skipped and why.

---

## Session 7 prompt (2026-08-13, tonight) — MEGA ONE-SHOT: model flip w/ canary fixes + green tests + observability + banner + docs truth-up

---

You are GPT 5.6, main coder for Tadabbur (Claude = architect/reviewer, Ahmed =
owner). First: `git pull` and read `HANDOFF.md` top entry. Session 6 (all ten
units) is DEPLOYED and verified live: backend `tafsir-backend-00263-5wb`,
frontend `tafsir-frontend-00304-9qr`, pipeline 14.0, coverage/recommendations/
share/persona contracts all confirmed working in production. Your work needed
ZERO review fixups. This session: FIVE units, one branch each, all from `main`,
worked IN ORDER — this is everything left in the queue that is code-side, in one
shot, including the fixes Claude's Gemini 3.6 canary just discovered. While you
work, Claude is IN PARALLEL finishing the canary validation with your
`golden_regression.py` harness — Unit 1 is the code half of that flip and Claude
merges it ONLY after the canary passes, so keep it exactly scoped. If any unit
balloons: stop it, record why in HANDOFF, move to the next.

### Unit 1 — the Gemini 3.6 flip PR (branch `codex/s7-model-flip`)
Code-side changes only; NO deploys, and Claude decides when this merges:

**CANARY FINDING (Claude, 2026-08-13 late): the endpoint must change too.**
Claude's no-traffic canary proved `gemini-3.6-flash` returns 404 on the regional
endpoint (`us-central1-aiplatform.googleapis.com/...locations/us-central1/...`)
but WORKS on the global endpoint
(`aiplatform.googleapis.com/...locations/global/...`) — verified with a live
generateContent call. Therefore Unit 1 must ALSO:
- Introduce `GEMINI_API_LOCATION` env (default `"global"`). Build every live
  Gemini endpoint URL from it: host = `aiplatform.googleapis.com` when value is
  `global`, else `{value}-aiplatform.googleapis.com`; path location segment =
  the value. Apply to ALL live call sites (main tafsir, correlations, guidance
  summarizer, digest, daily insight, feedback enricher) — a small shared helper
  `vertex_generate_url(model_id)` is warranted; do not otherwise touch the call
  sites. Firestore/GCS/`GCP_LOCATION` usage stays untouched.
- Gemini 3.x are THINKING models: thoughts consume `maxOutputTokens`. Claude's
  probe with maxOutputTokens=10 returned empty parts. The main call (65536) is
  safe; the small-budget sites are not — raise correlations 1024→4096,
  feedback enricher 1024→4096, guidance summarizer 2048→8192, weekly digest
  4096→8192, daily insight 2048→8192. Also make response-text extraction
  tolerant of multi-part candidates (concatenate `parts[].text`, skipping
  thought parts) wherever it currently assumes `parts[0].text` — Claude's probe
  showed parts can carry `thoughtSignature` metadata.
- Optional, allowed: loosen `golden_regression.py`'s "verse-linked token"
  reflection heuristic — it false-positived on a good 2:255 prompt anchored in
  the verse's meaning ("does not tire Him") rather than a literal token.
- `backend/app.py`: `GEMINI_MODEL_ID` default `"gemini-2.5-flash"` →
  `"gemini-3.6-flash"`; `GEMINI_LITE_MODEL_ID` default `"gemini-2.5-flash-lite"`
  → `"gemini-3.5-flash-lite"`. Update the stale comment on the GEMINI_MODEL_ID
  line (it still talks about the 2.0→2.5 upgrade).
- `deploy-backend.sh`: same two value changes.
- `SCHOLARLY_PIPELINE_VERSION` "14.0" → "15.0" (a model change is a material
  content change; the bump flushes mixed-model cache on deploy).
- Update `AI.md`'s model-config truth table to the new values, marked
  "pending canary validation (Claude, tonight)".
- Grep the whole repo for any remaining `gemini-2.5` / `gemini-2.0` strings and
  report every hit with your judgment (docs/metadata references stay; the
  `_precomputed_scholarly_plans.json` `_metadata.model` value is HISTORY — do
  not touch it; `precompute_scholarly_plans.py` and `test_live_pipeline.py`
  defaults should flip).

### Unit 2 — make `pytest backend/tests` green (branch `codex/s7-green-tests`)
Current state: 337 passed / 41 failed, identical on main — all pre-existing.
Goal: a clean signal, honestly.
- The 2 stale constant tests (`TestBudgetConstants`): read
  `config/token_budget.py` and the git history of the constants; the RUNTIME
  values (27,500 component sum, ABSOLUTE_MAX_VERSES=10) are the deliberate
  current behavior — update the test expectations to match, with a comment
  naming the values' source of truth. Do NOT change the constants.
- The remaining ~39 failures: triage each into (a) needs GCS/GCP credentials or
  network, (b) needs data files not in the repo, (c) tests dead code that no
  longer exists post-purge, (d) genuinely broken assertion worth fixing.
  For (a)/(b): add `pytest.mark.skipif` with a precise reason string (e.g.
  "requires GCS credentials; run in cloud env") — prefer an env-var gate
  (`RUN_LIVE_TESTS=1`) over deletion. For (c): delete the test with a note.
  For (d): fix it. End state: `py -3 -m pytest backend/tests -q` exits 0
  locally with a skip count, and the skip reasons are greppable.
- Add the final pass/skip counts to HANDOFF.

### Unit 3 — logger + request metrics cleanup (branch `codex/s7-observability`)
P2.13 remainder. Mechanical but large — do it in two commits for reviewability:
- Commit 1: replace the emoji `print(...)` calls in `backend/app.py` (and the
  live services) with `logger.info/warning/error(...)` preserving message
  content minus emojis; keep messages single-line (Cloud Logging treats each
  line as an entry). Module-level prints during startup may stay prints if
  logger isn't configured yet at that point — check order. Do not change any
  logic, and leave the structured `GEMINI_USAGE` / `HADITH_INTEGRITY_DROP`
  logger lines exactly as they are.
- Commit 2: add one `@app.after_request` hook emitting a single structured
  request log line for /tafsir and /share only: method, path, status,
  duration_ms (reuse the perf_start already in the handler via `g` or an
  equivalent — simplest correct mechanism you can find), X-Cache-Status if set.
  Skip /health (noise).
- Verify: py_compile, the (now green) test suite, and grep-proof there are no
  remaining emoji prints in app.py. State honestly that log-output formatting
  can only be fully confirmed after deploy.

### Unit 4 — global backend-down banner (branch `codex/s7-backend-banner`)
The last deferred piece of P1.5. Today, when the backend is unreachable, 31
empty catch blocks make every page render its empty state — "backend down" is
indistinguishable from "you have no data".
- Add ONE tiny shared module (e.g. `app/lib/backendHealth.js`): a function
  `reportBackendFailure()` / `reportBackendSuccess()` and a subscribable flag
  (module-level state + listener set is fine; NO new dependencies, NO context
  refactor — AppContext stays dead/deleted).
- A thin `<BackendStatusBanner />` mounted once in `app/layout.js`: when ≥2
  failures within 30s and no success since, show a slim dismissible banner
  "Can't reach the server — some content may be unavailable. Retrying…"; auto-
  hide on the next reported success. Style consistent with existing toasts;
  polite live region (aria) per the Session 6 accessibility conventions.
- Wire ONLY the highest-traffic call sites to report success/failure: the
  /tafsir submit path, daily-verse, streak, profile fetch, saved-searches list,
  plans list, annotations list. Do NOT touch the other catch blocks' behavior —
  one added report call per site, everything else identical.
- Verify with `npm run build` exit 0 + trace; note honestly that live behavior
  needs a deployed backend outage (or devtools offline) to fully confirm.

### Unit 5 — docs truth-up (branch `codex/s7-docs-truth`)
The public docs still describe the pre-takeover app. Pure documentation; no
code. Update:
- `README.md`: tech-stack table (model → the Unit 1 values, marked "canary-
  gated"; cache → "Firestore cache, 90-day TTL, version-invalidated" — the
  "7-day response cache" claim is false), feature list (guest reflections,
  Continue-reflecting cards, theme chips, source-coverage panel now exist;
  Iman Journal stays listed as suspended), deployment section (deploy scripts +
  the PowerShell note from HANDOFF), and remove/repair anything else you can
  prove stale against the code.
- `AI.md`: refresh the architecture map bullets that Session 5/6 changed
  (hadith validation module, share-by-cache-key, coverage object, pipeline
  version now 14.0→15.0-pending, TTL field, monitoring alerts exist), and add
  a "Testing" section: how to run the offline suites and how Claude runs
  `golden_regression.py` against a canary.
- `docs/AUDIT-2026-08-01.md`: add a short "Status as of 2026-08-13" preamble
  noting which audit sections are now RESOLVED (P1 all, Q1-Q7, purge) so a
  future reader doesn't re-discover fixed issues. Do not rewrite history below
  the preamble.
- Cross-check every claim you write against the code, not against memory or
  HANDOFF prose; where they disagree, the code wins and note the discrepancy.

### Global rules
Per unit: short plan → implement → verify → HANDOFF session-log entry with
branch + commit. No deploys, no gcloud, no secrets, no drive-by refactors, no
new dependencies. Line numbers drift — trust the code. Frontend: null-guard any
field that may be absent. Finish with the summary table
(unit | branch | commit | verified | deploy-needed backend/frontend/none),
plus anything skipped and why.

---

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
