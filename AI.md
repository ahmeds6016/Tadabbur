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
progress map, badges, save/share, guest mode.

## Architecture (verified 2026-08-01)

```
Next.js 15 frontend (Cloud Run: tafsir-frontend, us-central1)
        │  fetch ${BACKEND_URL}/...  (frontend/app/lib/config.js:7)
        ▼
Flask backend — backend/app.py, ~10,200 lines, 83 routes
(Cloud Run: tafsir-backend, project tafsir-simplified, us-central1)
        │
        ├── Firestore project tafsir-simplified-6b262  ← Firebase Auth + user data
        │     ├── DB "(default)": users/*, annotations, shared_content, feedback
        │     └── DB "tafsir-db": quran_texts (verse text!), tafsir_cache, popular_queries
        ├── GCS bucket tafsir-simplified-sources — 8 tafsir JSON blobs loaded at startup
        ├── Secret Manager — firebase-sa-key (service account for the 6b262 project)
        └── Vertex AI (project tafsir-simplified) — Gemini via RAW REST calls
              (no SDK at runtime; hand-rolled requests.post per call site)
```

**Two GCP projects — do not confuse them:**
- `tafsir-simplified` — infra: Cloud Run, Cloud Build, GCS, Secret Manager, Vertex AI.
- `tafsir-simplified-6b262` — Firebase: Auth, both Firestore DBs. **Must have billing
  linked** or every verse lookup 403s and the app reports "Verse not found".

**Retrieval is deterministic, no vector search.** `_precomputed_scholarly_plans.json`
(offline Gemini-generated plans, ~61% verse coverage) + keyword routing tables in
`backend/services/source_service.py` + in-memory dict `VERSE_METADATA["{source}:{s}:{v}"]`.
The vector-search env vars and docstrings are legacy; the index is not called anywhere.

### The hot path: POST /tafsir (app.py:6671)

parse → verse-ref extraction (app.py:1000) → rate limit (in-memory) → cache check
(memory + Firestore) → verse text from Firestore `tafsir-db` (app.py:1264) → tafsir from
in-memory dicts (app.py:2321) → scholarly excerpts (source_service.py) → prompt build
(app.py:3376) → **Gemini REST call (app.py:7044-7103)** → JSON extraction (app.py:2879)
→ post-filters → cache write + gamification.

### Gemini model configuration — single source of truth

| Where | Value | Status |
|---|---|---|
| Cloud Run env `GEMINI_MODEL_ID` | `gemini-2.5-flash` | **what production runs** |
| `app.py:110` default | `gemini-2.5-flash` | matches |
| `deploy-backend.sh` | `gemini-2.5-flash` | fixed 2026-08-01 (was retired `gemini-2.0-flash`) |
| `app.py:8811`, `app.py:9970` | `gemini-2.5-flash-lite` **hardcoded** | make env-configurable when migrating |
| `config/settings.py:44` | `gemini-2.0-pro` | DEAD CODE — ignore |

**Model deadline: `gemini-2.5-flash` retires Oct 16–20, 2026.** Migration target:
`gemini-3.6-flash` (GA on Vertex) and `gemini-3.5-flash-lite` for the two -lite call
sites. This is a planned, tested migration — see HANDOFF.md P1. Do not bump the model
string casually: the tafsir prompt demands strict JSON and output-format drift between
model generations must be regression-tested (`backend/tests/test_live_pipeline.py`).

## Conventions & constraints

- **Backend is a monolith on purpose (for now).** Don't start an incremental rewrite
  inside `app.py`'s dead siblings (`app_optimized.py`, `config/settings.py`,
  `services/cache_service.py`, etc. are an abandoned rewrite — treat as deletable, not
  as a foundation).
- **Frontend state = local useState + raw fetch.** `app/context/AppContext.jsx` and
  `app/services/tafsirApi.{js,ts}` are dead (never mounted/imported). Either adopt them
  deliberately in one PR or delete them — don't half-use.
- Personas (backend keys): `new_revert, curious_explorer, practicing_muslim, student,
  advanced_learner`.
- Cache invalidation: bump `SCHOLARLY_PIPELINE_VERSION` (app.py:159) when the response
  shape or pipeline changes; Firestore cache entries have NO TTL.
- Deploys: `./deploy-backend.sh` / `./deploy-frontend.sh` (gcloud builds submit + run
  deploy). No CI/CD; deploys are manual from a workstation with gcloud auth.
- Windows dev machine; repo path `c:\Users\us88832\Desktop\tadabbur`.

## Decisions

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
