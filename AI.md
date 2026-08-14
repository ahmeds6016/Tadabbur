# AI.md — AI Collaboration Guide for Tadabbur

> Read this first. This file is the shared brain for the AI team working on Tadabbur.
> **Roles:** Claude (Fable 5) = architect / auditor / reviewer. GPT 5.6 = main coder.
> The human owner is Ahmed (ahmeds6016 on GitHub, ahmedsheik123@gmail.com on GCP).
>
> **Protocol:** Before coding, read `HANDOFF.md` (current state + task queue). After any
> meaningful change, update `HANDOFF.md` (what changed, what's verified, what's next).
> Architectural decisions get recorded here under "Decisions". Full audit findings live
> in `docs/AUDIT-2026-08-01.md`.

## What Tadabbur is

AI-powered Qur'anic reflection app: user picks a verse (or range), backend assembles
classical tafsir excerpts (Ibn Kathir complete; al-Qurtubi through 4:22; Ihya, Madarij,
Riyad al-Salihin via keyword routing) and has Gemini generate a persona-tailored
explanation. Plus: daily verse, streaks, reading plans, reflections/annotations,
progress map, badges, save/share, guest mode, curated themes, and follow-on verse
recommendations. Hadith items are source-grounded before caching/display.

## Architecture (verified 2026-08-13)

```
Next.js 15 frontend (Cloud Run: tafsir-frontend, us-central1)
        │  fetch ${BACKEND_URL}/...  (frontend/app/lib/config.js:7)
        ▼
Flask backend — backend/app.py, ~9,800 lines, 83 routes
(Cloud Run: tafsir-backend, project tafsir-simplified, us-central1)
        │
        ├── Firestore project tafsir-simplified-6b262  ← Firebase Auth + user data
        │     ├── DB "(default)": users/*, annotations, saved searches, feedback
        │     └── DB "tafsir-db": quran_texts, tafsir_cache, popular_queries, shared_content
        ├── GCS bucket tafsir-simplified-sources — 8 tafsir JSON blobs loaded at startup
        ├── Secret Manager — firebase-sa-key (service account for the 6b262 project)
        └── Vertex AI (project tafsir-simplified) — Gemini via raw REST calls
              (global endpoint on the canary-gated Gemini 3 branch)
```

**Two GCP projects — do not confuse them:**
- `tafsir-simplified` — infra: Cloud Run, Cloud Build, GCS, Secret Manager, Vertex AI.
- `tafsir-simplified-6b262` — Firebase: Auth, both Firestore DBs. **Must have billing
  linked** or every verse lookup 403s and the app reports "Verse not found".

**Retrieval is deterministic, no vector search.** `_precomputed_scholarly_plans.json`
contains all 6,236 verse keys (6,170 Gemini-origin plans and 66 deterministic-only
fallbacks). Keyword routing in `backend/services/source_service.py` remains the fallback;
the same service constructs the additive `source_coverage` contract shown by the UI.

**Trust boundaries:** `backend/services/hadith_validation.py` drops hadith text that is
not grounded in the supplied corpus excerpts. `POST /share` accepts only query/approach
and snapshots a current-version server cache record; public pages never store or render a
caller-provided tafsir response.

### The hot path: POST /tafsir

parse → verse-ref extraction → in-memory rate limit → memory/Firestore cache → verse text
from Firestore `tafsir-db` → local tafsir/scholarly retrieval → deterministic coverage →
persona prompt → Gemini REST generation → JSON extraction → hadith grounding → post-filters
→ 90-day/versioned cache write → progress/badge side effects.

### Gemini model configuration — single source of truth

| Where | Value | Status |
|---|---|---|
| Production (rev tafsir-backend-00269-z5h) | `gemini-3.6-flash` / `gemini-3.5-flash-lite`, `GEMINI_API_LOCATION=global`, pipeline `15.1` | **DEPLOYED & canary-validated 2026-08-14** (`GEMINI_USAGE model=gemini-3.6-flash` confirmed in prod logs) |
| app.py defaults + deploy-backend.sh | same values | in sync with production |
| Retired | `gemini-2.5-flash` (shutdown Oct 16-20, 2026) | migration complete ~2 months ahead of deadline |

Migration notes (2026-08-14): 3.6 requires the global endpoint (404 on regional);
thinking tokens eat small maxOutputTokens budgets (all raised); 3.6 sometimes wraps
the response object in a JSON array (handler unwraps single-element arrays, 502s
other non-objects); unverifiable hadith collection labels are now DOWNGRADED
(label stripped, grounded text kept) instead of dropped — see
`services/hadith_validation.py`. Pipeline 15.1 skipped 15.0 because early canary
runs cached hadith-less 15.0 docs. Any future model change: same procedure —
no-traffic canary + `golden_regression.py`, never flip from docs alone.

## Conventions & constraints

- **Backend is a monolith on purpose (for now).** The abandoned optimized-backend tree
  was purged in Session 6; do not recreate an incremental sibling architecture without
  an approved decision.
- **Frontend state = local useState + raw fetch.** The unused AppContext/duplicate API
  clients were purged. Add a shared state layer only through a deliberate architecture
  decision, not one call site at a time.
- Personas (backend keys): `new_revert, curious_explorer, practicing_muslim, student,
  advanced_learner`.
- Cache invalidation: bump `SCHOLARLY_PIPELINE_VERSION` when generated content or the
  response pipeline materially changes. New Firestore cache documents set `expires_at`
  to creation + 90 days; the Firestore TTL policy deletes them server-side.
- Deploys: `./deploy-backend.sh` / `./deploy-frontend.sh` (gcloud builds submit + run
  deploy). No CI/CD; deploys are manual from a workstation with gcloud auth.
- Windows dev machine; repo path `c:\Users\us88832\Desktop\tadabbur`.

## Testing

Run the complete offline backend suite from the repository root:

```powershell
py -3 -m pytest backend/tests -q
```

`codex/s7-green-tests` establishes the clean local signal: 378 passed, 0 skipped, with
10 known `datetime.utcnow()` deprecation warnings. Frontend changes must pass:

```powershell
Set-Location frontend
npm run build
```

The Gemini migration harness is intentionally live and paid. Claude's canary procedure:

1. Run `backend/tests/golden_regression.py` against the current production URL for a
   timestamped baseline.
2. Deploy a **no-traffic** revision with `GEMINI_API_LOCATION=global`,
   `GEMINI_MODEL_ID=gemini-3.6-flash`, and
   `GEMINI_LITE_MODEL_ID=gemini-3.5-flash-lite`.
3. Run the harness against the canary URL with bearer tokens for users configured as
   `curious_explorer` and `student`:

   ```powershell
   py -3 backend/tests/golden_regression.py --base-url https://CANARY_URL `
     --persona-token curious_explorer=TOKEN_ONE `
     --persona-token student=TOKEN_TWO
   ```

4. Compare the saved raw baseline/canary folders and structural table. Shift traffic
   only after content review and approval. The harness makes 12 paid requests; never run
   it casually or without the rate-limit/credential plan.

## Operations and monitoring

- Firestore TTL is enabled on `tafsir_cache.expires_at` in database `tafsir-db`.
- Cloud Monitoring alerts exist for backend 5xx bursts (>5 in five minutes) and any
  logged backend `PermissionDenied`, with Ahmed's email channel configured.
- Deploys remain manual through `deploy-backend.sh` / `deploy-frontend.sh`. On the
  current Windows workstation, run the scripts' underlying gcloud commands in PowerShell;
  the Git Bash gcloud shim resolves a broken Microsoft Store Python stub.

## Decisions

- **2026-08-01 (Claude):** Frontend /tafsir abort timer stays at 180s although the
  backend's bounded worst case is 242s (P1.4). Rationale: a >3-minute spinner is
  worse UX than a "took too long, try again" message, and the backend request
  completes and caches server-side regardless — a user retry after the timeout gets
  an instant cache hit. Revisit only if timeout complaints show up in feedback.

- **2026-08-01 (Claude):** Root cause of the July/Aug 2026 outage = billing unlinked from
  `tafsir-simplified-6b262`, NOT model deprecation. Fix = relink billing account
  `0152F9-4F49EC-74C075`. Keep `gemini-2.5-flash` until a deliberate, tested migration
  to `gemini-3.6-flash` (before Oct 16, 2026).
- **2026-08-01 (Claude):** Removed dead vector-search env vars from `deploy-backend.sh`
  (`INDEX_ENDPOINT_ID`, `DEPLOYED_INDEX_ID`, `VECTOR_INDEX_ID`) — read by zero lines of
  code. If a Matching Engine index/endpoint still exists in `tafsir-simplified`, it is
  billable idle cost and should be deleted from the console after confirmation.
- **2026-08-01 (Claude):** Security posture of unauthenticated cache/debug endpoints is
  the top post-recovery priority (see HANDOFF P1) — `/cache/invalidate` allows anyone to
  wipe the tafsir cache; `/cache/store` allows cache poisoning; `/debug/test/<q>` gives
  unmetered LLM generation.

## Verification checklist (run after any backend deploy)

```bash
BASE=https://tafsir-backend-vg7kshbegq-uc.a.run.app
curl -s $BASE/health                          # expect status healthy
curl -s -X POST $BASE/tafsir -H "Content-Type: application/json" \
     -d '{"query":"2:255","persona":"curious_explorer"}'   # expect JSON tafsir, not "Verse not found"
curl -s $BASE/daily-verse                     # expect a verse
```
Logs: `gcloud run services logs read tafsir-backend --region us-central1 --project tafsir-simplified --limit 50`
