# Tadabbur (تدبّر)

An AI-powered Qur'anic reflection app that brings classical tafsir scholarship to life through personalized, accessible explanations. Named after the Qur'anic concept of deep reflection (4:82, 47:24).

## Features

### Core Tafsir Engine
- **Verse-by-verse tafsir** — Select any verse or verse range via surah/verse dropdown and receive AI-generated tafsir explanations
- **Multi-source scholarly content** — Ibn Kathir, Al-Qurtubi, Asbab Al-Nuzul, Thematic Commentary, Ihya Ulum Al-Din, Madarij Al-Salikin, and Riyad Al-Saliheen
- **Adaptive personas** — Choose from 6 learning personas (Curious Explorer, Practicing Muslim, Scholar, Parent/Educator, Spiritual Seeker, New Muslim) that tailor explanation depth and tone
- **Deterministic scholarly pipeline** — Pure keyword matching for reliable source retrieval (no LLM routing)
- **Tabbed response view** — Verses (Arabic + English), Tafsir Explanations, Cross-References, Lessons & Practical Applications, Summary, and Hadith references

### Daily Verse & Streaks
- **Daily Verse** — Curated pool of verses, one per day, displayed on the homepage
- **Streaks** — Track daily engagement with current and longest streak

### Reading Plans
- **Reading Plans** — Structured journeys through the Qur'an with daily verse assignments
- **Progress tracking** — Day-by-day completion with "Study Verse" and "Complete Day" actions
- **Browse & start** — Filter plans by category, view descriptions, and activate

### Reflections (Annotations)
- **5 reflection types** — Insight, Question, Application, Dua/Prayer, and Connection
- **Inline capture** — Add reflections while viewing tafsir via floating button
- **Tags** — Organize reflections with custom tags
- **Search & filter** — Filter by type, tag, or keyword across all reflections
- **Dedicated reflections page** — Browse, search, and manage all saved reflections

### Progress & Badges
- **114-Surah Progress Map** — Visual grid showing exploration progress across the entire Qur'an (6,236 verses)
- **Color-coded tiles** — Gray (unexplored) through gold (100% complete) with glow effects
- **Badges** — Awarded automatically as milestones are reached

### Iman Journal
- **Daily journal entries** — Log spiritual states, behaviors, and reflections
- **Heart states** — Quick emotional check-ins with AI-generated responses
- **Heart notes** — Short-form spiritual journaling with history view
- **Struggles tracking** — Declare personal challenges and receive Qur'anic guidance, set goals, track progress
- **Weekly digests** — AI-summarized patterns from journal entries
- **Correlations & insights** — Connections between struggles and daily factors
- **Heart patterns** — Visual trends in emotional/spiritual data
- **Scrupulosity safeguards** — Gentle messaging for users showing signs of spiritual anxiety

### Save & Share
- **Save tafsir responses** — Bookmark answers and organize into custom folders
- **Share links** — Generate public shareable links for any tafsir response with view counts
- **Query history** — Browse and re-run past searches (up to 50 recent)

### Guest Browsing
- **Explore without signing up** — Guest users can search tafsir and view daily verse
- **Soft sign-up nudge** — After 3 queries, a gentle prompt to create an account
- **Full access on sign-up** — Journal, reflections, saved answers, and progress tracking require authentication

### Navigation & Accessibility
- **Responsive layout** — Bottom nav on mobile, collapsible sidebar on desktop
- **Keyboard shortcuts** — Alt+H (Home), Alt+R (Plans), Alt+S (Saved), Alt+J (Journal), Alt+N (Reflections), Alt+P (Progress)
- **Dark mode** — System-aware theme support
- **iOS support** — Native wrapper via Capacitor

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
│   ├── app/           # Pages (home, progress, journal, plans, saved, etc.)
│   ├── app/components/# React components
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
