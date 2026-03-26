# Tadabbur (تدبّر)

An AI-powered Qur'anic reflection app that brings classical tafsir scholarship to life through personalized, accessible explanations. Named after the Qur'anic concept of deep reflection (4:82, 47:24).

## Features

### Core Tafsir Engine
- **Multi-source scholarly tafsir** — Ibn Kathir, Al-Qurtubi, Asbab Al-Nuzul, Thematic Commentary, Ihya Ulum Al-Din, Madarij Al-Salikin, and Riyad Al-Saliheen
- **Adaptive explanations** — Personalized to the reader's knowledge level and persona
- **3-tier query routing** — Metadata queries → direct verse lookup → semantic RAG search
- **Deterministic scholarly pipeline** — Pure keyword matching for reliable source retrieval (no LLM routing)

### Engagement & Growth
- **Daily Verse** — Curated pool of 69 verses, one per day
- **Streaks** — Track daily engagement with current and longest streak
- **13 Badges** — Awarded automatically as milestones are reached
- **12 Themed Collections** — Grouped verses by topic (patience, gratitude, etc.)
- **5 Reading Plans** — Structured journeys through the Qur'an with progress tracking
- **114-Surah Progress Map** — Visual exploration tracker across the entire Qur'an

### Journaling & Self-Reflection
- **Iman journal** — Track daily behaviors and heart states
- **Struggles catalog** — Identify and work through personal challenges with Qur'anic guidance
- **AI-generated reflections** — Contextual prompts tied to each tafsir response
- **Daily digests & insights** — Gemini-summarized personal growth patterns

### User Features
- Firebase authentication (email/password)
- Annotations with tags and search
- Saved searches and folders
- Dark mode
- Mobile-responsive with iOS support via Capacitor

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, Capacitor 8 |
| Backend | Flask 3.0, Python 3.11, Gunicorn |
| AI | Google Gemini 2.5 Flash (Vertex AI) |
| Database | Cloud Firestore (7-day response cache) |
| Auth | Firebase Authentication |
| Infra | Google Cloud Run, Cloud Build, Cloud Storage, Secret Manager |

## Project Structure

```
├── frontend/          # Next.js app
│   ├── src/app/       # Pages (tafsir, progress, journal, collections, etc.)
│   ├── src/components/# React components
│   └── ios/           # Capacitor iOS project
├── backend/
│   ├── app.py         # Flask app + API endpoints
│   ├── services/      # Scholarly source service, deterministic planner
│   ├── data/
│   │   ├── indexes/   # Precomputed scholarly indexes (~560 files)
│   │   └── tafsir_sources/ # Source JSON data
│   └── Dockerfile     # Python 3.11-slim container
└── cloudbuild.yaml    # GCP Cloud Build config
```

## Getting Started

### Prerequisites
- Node.js 20+
- Python 3.11+
- Google Cloud project with Vertex AI, Firestore, and Firebase enabled

### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:3000` and the backend on `http://localhost:8080`.

## Deployment

The app deploys to Google Cloud Run via Cloud Build:

```bash
gcloud builds submit --config cloudbuild.yaml
```

## License

All rights reserved.
