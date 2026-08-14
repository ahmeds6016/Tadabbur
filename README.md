# Tadabbur (تدبّر)

Tadabbur is an AI-assisted Qur'an study app that helps readers understand verses
through classical tafsir and turn that understanding into personal reflection. Its name
comes from the Qur'anic call to deep reflection (4:82, 47:24).

## What readers can do

- Study any verse or supported range with Arabic, translation, and commentary grounded
  in Ibn Kathir, al-Qurtubi (through 4:22), Asbab al-Nuzul, thematic commentary, Ihya
  Ulum al-Din, Madarij al-Salikin, and Riyad al-Salihin.
- See a deterministic "Sources used for this answer" panel, including a neutral notice
  when al-Qurtubi is unavailable in the local corpus.
- Choose one of five learning approaches: New Revert, Curious Explorer, Practicing
  Muslim, Student, or Advanced Learner.
- Read verse-specific reflection questions as a guest; signing in is required only to
  save a reflection.
- Start from eight curated theme chips and continue through up to three related-verse
  recommendations after each answer.
- Save answers, organize them into folders, and create public share links. Shared pages
  are server snapshots of version-matched cached answers—not caller-supplied content.
- Follow reading plans, mark days complete, track verses studied and reflections, and
  earn gentle activity streaks and badges.
- Use the responsive mobile/desktop UI, system dark mode, keyboard navigation, and the
  Capacitor iOS wrapper.

Hadith text is validated against the supplied source excerpts before an answer can be
cached or displayed. The Iman Journal backend remains in the repository, but its
frontend experience is suspended and is not part of the shipped navigation.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, Capacitor 8 |
| Backend | Flask 3, Python 3.11, Gunicorn |
| AI | Gemini 3.6 Flash + Gemini 3.5 Flash Lite on Vertex AI's global endpoint (**canary-gated; not merged/deployed until validation passes**) |
| Data | Firebase Auth; two Firestore databases; Cloud Storage source corpus |
| Cache | Firestore tafsir cache, 90-day TTL, invalidated by scholarly pipeline version |
| Infra | Google Cloud Run, Cloud Build, Secret Manager, Cloud Monitoring |

Production is currently on pipeline `14.0`. The canary-gated model branch changes the
generated-content pipeline to `15.0`; see [AI.md](AI.md) and [HANDOFF.md](HANDOFF.md)
for the current merge/deploy gate.

## Repository map

```text
frontend/
  app/                         Next.js routes and local-state UI
  app/components/              Shared UI, source coverage, themes, recommendations
  ios/                         Capacitor iOS wrapper
backend/
  app.py                       Flask application and API routes
  services/source_service.py   Deterministic scholarly planning and coverage
  services/hadith_validation.py Source-grounded hadith validation
  services/persona_prompt_service.py Persona learning contracts
  data/indexes/                Precomputed plans and local scholarly indexes
deploy-backend.sh              Backend Cloud Build + Cloud Run flags
deploy-frontend.sh             Frontend Cloud Build + Cloud Run flags
```

Architecture, GCP project ownership, cache rules, and model configuration are documented
in [AI.md](AI.md). Current work and production revisions live in
[HANDOFF.md](HANDOFF.md).

## Local development

Prerequisites: Node.js 20+, Python 3.11+, and npm. Full backend startup also requires
Google Cloud application credentials plus the configured Firestore, Storage, and Secret
Manager resources; the offline tests do not.

```powershell
py -3 -m pip install -r backend/requirements.txt
py -3 -m pip install pytest
py -3 -m pytest backend/tests -q
```

For frontend development, explicitly point Next.js at the intended backend so local work
does not use the production fallback:

```powershell
Set-Content frontend/.env.local 'NEXT_PUBLIC_BACKEND_URL=http://localhost:8080'
Set-Location frontend
npm install
npm run dev
```

Run `npm run build` before handing off frontend changes.

## Deployment

Deployments are manual and owner-approved. The canonical build and Cloud Run flags are
in `deploy-backend.sh` and `deploy-frontend.sh`:

```bash
./deploy-backend.sh
./deploy-frontend.sh
```

On the current Windows workstation, the `gcloud` shim fails when these scripts are run
from Git Bash because it resolves the Microsoft Store Python stub. Use the scripts as the
source of truth, but run their `gcloud builds submit` and `gcloud run deploy` commands
from PowerShell. Never deploy a model flip until the canary procedure in [AI.md](AI.md)
passes.

## License

All rights reserved.
