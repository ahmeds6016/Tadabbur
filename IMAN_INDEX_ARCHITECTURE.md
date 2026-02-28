# Iman Index — Spiritual Analytics Engine Architecture

## System Overview

A WHOOP-style spiritual companion engine that combines:
- **WHOOP**: Continuous tracking → correlation analysis → AI coaching → trend scoring
- **Atomic Habits**: Identity-based formation → micro-behaviors → systems over goals → consistency
- **Ihya Ulum al-Din**: Muhasaba (self-accounting) → Mujahada (striving) → Tazkiyah (purification)
- **Madarij al-Salikin**: Progressive spiritual stations → self-reckoning → growth through stages
- **Quranic Tadabbur**: Deep reflection → behavioral transformation → living the Quran

The Iman Index is NOT a gamified point system. It is:
- **Personalized**: baseline-relative to each user
- **Trend-driven**: trajectory matters more than raw score
- **Non-comparative**: no leaderboards, no social scores
- **Non-public**: visible only to the user
- **Grounded in ikhlas**: sincerity safeguards at every layer

---

## System Architecture (Layered Modules)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                          │
│  Daily Journal UI │ Heart Notes │ Dashboard │ Coaching │ Struggles  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              LAYER 7: SAFEGUARDS & CONSTRAINTS                │  │
│  │  Anti-Riya │ Anti-Scrupulosity │ Humility Cues │ Privacy     │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▲                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              LAYER 6: ADAPTIVE COACHING                       │  │
│  │  Weekly Digest │ Micro-Adjustments │ Correlation Insights     │  │
│  │  Gemini 2.5 Flash narrative generation                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▲                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              LAYER 5: IMAN INDEX ENGINE                       │  │
│  │  Baseline Normalization │ 3-Pillar Scoring │ Weight Recalib   │  │
│  │  Trajectory Detection │ Strain/Recovery │ Plateau Detection   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▲                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              LAYER 4: AI CORRELATION & INSIGHT                │  │
│  │  Cross-behavior patterns │ Behavioral clustering              │  │
│  │  Scholarly source mapping │ Trend shift detection             │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▲                                      │
│  ┌───────────────────────────┬───────────────────────────────────┐  │
│  │  LAYER 3: SPIRITUAL STATE │  LAYER 3b: HEART NOTES           │  │
│  │  Islamic Calendar         │  Quick spiritual capture          │  │
│  │  Time-of-Day Awareness    │  Emotional pattern detection      │  │
│  │  Emotional Context        │  Gratitude/Dua/Tawbah logging    │  │
│  └───────────────────────────┴───────────────────────────────────┘  │
│                              ▲                                      │
│  ┌───────────────────────────┬───────────────────────────────────┐  │
│  │  LAYER 2: IDENTITY &      │  LAYER 2b: STRUGGLE FRAMEWORK   │  │
│  │  INTENTION                 │  Scholarly source querying       │  │
│  │  Identity statements       │  Structured action plans        │  │
│  │  Micro-behavior scaffold   │  Habit anchors & measurement    │  │
│  │  Habit stacking            │  Progressive deepening          │  │
│  └───────────────────────────┴───────────────────────────────────┘  │
│                              ▲                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              LAYER 1: BEHAVIORAL LOGGING                      │  │
│  │  Daily behavior journal │ Multi-category tracking             │  │
│  │  Binary + continuous + scaled inputs                          │  │
│  │  Encrypted at-rest │ Firestore persistence                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▲                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              EXISTING TADABBUR PLATFORM                       │  │
│  │  Firestore │ Gemini 2.5 Flash │ Scholarly Indexes (9.5MB)    │  │
│  │  5 Personas │ 36 Reading Plans │ 12 Collections │ 39 Badges  │  │
│  │  Annotations │ Streaks │ Progress Tracking │ Daily Verse      │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                        DATA PERSISTENCE                             │
│  Firestore (users/{uid}/iman_engine/...)                           │
│  Encrypted behavioral logs │ Computed baselines │ Weekly digests    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Firestore Data Model

### New Collections (under existing `users/{uid}/`)

```
users/{uid}/
│
├── [EXISTING FIELDS - unchanged]
│   ├── persona, knowledge_level, learning_goal, first_name
│   ├── streak_current, streak_longest, streak_last_date
│   ├── explored_verses, stats_cache, badges_earned
│   ├── active_plans, collection_progress
│   └── daily_verse_count, created_at
│
├── iman_config/                          ◄── ENGINE CONFIGURATION
│   └── settings (single document)
│       ├── tracked_behaviors: [           ◄── User's active behavior set
│       │   {
│       │     "id": "fajr_prayer",
│       │     "category": "fard",
│       │     "label": "Fajr Prayer",
│       │     "input_type": "binary",     // binary | scale_5 | minutes | count
│       │     "weight_override": null,     // null = use category default
│       │     "active": true,
│       │     "added_at": "2026-02-28T..."
│       │   },
│       │   ...
│       │ ]
│       ├── identity_statements: [         ◄── Atomic Habits identity layer
│       │   {
│       │     "id": "ist_001",
│       │     "statement": "I am someone who prays before sleeping",
│       │     "source_type": "hadith",
│       │     "source_ref": "The Prophet ﷺ would not sleep until...",
│       │     "linked_behaviors": ["witr_prayer", "night_adhkar"],
│       │     "created_at": "2026-02-28T...",
│       │     "reinforcement_count": 0     // incremented when linked behaviors logged
│       │   },
│       │   ...
│       │ ]
│       ├── active_struggles: [            ◄── User's declared struggles
│       │   {
│       │     "id": "str_001",
│       │     "label": "anger",
│       │     "keywords": ["anger", "ghadab", "wrath"],
│       │     "scholarly_plan_id": "sp_anger_001",
│       │     "linked_behaviors": ["anger_incidents", "wudu_response"],
│       │     "started_at": "2026-02-28T...",
│       │     "status": "active"           // active | paused | resolved
│       │   }
│       │ ]
│       ├── baseline_period_start: "2026-02-28T..."
│       ├── baseline_established: false    ◄── true after 14-day calibration
│       ├── onboarding_complete: false
│       └── engine_version: "1.0"
│
├── iman_daily_logs/                       ◄── DAILY BEHAVIORAL DATA
│   └── {YYYY-MM-DD} (one document per day)
│       ├── behaviors: {                   ◄── All logged behaviors for this day
│       │     "fajr_prayer":      { "value": 1, "logged_at": "2026-02-28T05:15:00Z" },
│       │     "dhuhr_prayer":     { "value": 1, "logged_at": "2026-02-28T12:35:00Z" },
│       │     "asr_prayer":       { "value": 1, "logged_at": "2026-02-28T15:50:00Z" },
│       │     "maghrib_prayer":   { "value": 1, "logged_at": "2026-02-28T18:10:00Z" },
│       │     "isha_prayer":      { "value": 1, "logged_at": "2026-02-28T19:45:00Z" },
│       │     "masjid_attendance":{ "value": 1, "logged_at": "2026-02-28T05:15:00Z" },
│       │     "quran_minutes":    { "value": 25, "logged_at": "2026-02-28T06:00:00Z" },
│       │     "dhikr_minutes":    { "value": 10, "logged_at": "2026-02-28T05:30:00Z" },
│       │     "tahajjud":         { "value": 0 },
│       │     "sunnah_prayers":   { "value": 3, "logged_at": "..." },  // count of sunnah sets
│       │     "charity":          { "value": 1 },   // binary: gave today
│       │     "lowering_gaze":    { "value": 4, "logged_at": "..." },  // 1-5 self-report
│       │     "avoided_sins":     { "value": 4, "logged_at": "..." },  // 1-5 self-report
│       │     "device_discipline":{ "value": 3, "logged_at": "..." },  // 1-5 self-report
│       │     "sleep_hours":      { "value": 7.0, "logged_at": "..." },
│       │     "fasting":          { "value": 0 },    // binary
│       │     "exercise":         { "value": 1 },    // binary
│       │     "anger_incidents":  { "value": 1 },    // count (struggle-linked)
│       │     "wudu_response":    { "value": 1 }     // binary (struggle-linked)
│       │   }
│       ├── heart_state: "grateful"        ◄── Optional emotional context
│       ├── heart_notes: [                 ◄── Quick spiritual captures
│       │     {
│       │       "type": "gratitude",       // gratitude | dua | tawbah | connection | reflection
│       │       "text": "Grateful for the peace after Fajr today",
│       │       "timestamp": "2026-02-28T05:20:00Z"
│       │     },
│       │     {
│       │       "type": "dua",
│       │       "text": "Ya Allah grant me sabr with my family",
│       │       "timestamp": "2026-02-28T14:30:00Z"
│       │     }
│       │   ]
│       ├── intention_score: 4             ◄── 1-5 self-reported sincerity (optional)
│       ├── day_summary: null              ◄── Populated by AI at end of day (optional)
│       └── logged_at: "2026-02-28T22:00:00Z"
│
├── iman_baselines/                        ◄── COMPUTED BASELINES (per category)
│   └── current (single document)
│       ├── fard: {
│       │     "median": 0.85,
│       │     "mean": 0.82,
│       │     "std_dev": 0.12,
│       │     "mad": 0.08,              // median absolute deviation
│       │     "p95": 1.0,               // 95th percentile (for continuous normalization)
│       │     "sample_size": 30,
│       │     "updated_at": "2026-02-28T...",
│       │     "history": [               // last 6 recalibration snapshots
│       │       { "date": "2026-01-28", "median": 0.78, "std_dev": 0.15 },
│       │       { "date": "2026-02-28", "median": 0.85, "std_dev": 0.12 }
│       │     ]
│       │   }
│       ├── tawbah: { ... same structure ... }
│       ├── quran: { ... }
│       ├── nafl: { ... }
│       ├── character: { ... }
│       ├── stewardship: { ... }
│       ├── last_recalibration: "2026-02-28T..."
│       └── recalibration_count: 2
│
├── iman_trajectory/                       ◄── COMPUTED INDEX HISTORY
│   └── current (single document)
│       ├── current_state: "ascending"     // ascending | steady | recalibrating
│       ├── volatility_state: "stable"     // stable | dynamic | turbulent
│       ├── composite_display: "Ascending & Stable"
│       ├── trend_slope: 0.18              // 14-day linear regression slope
│       ├── volatility_cv: 0.07            // coefficient of variation
│       ├── strain_recovery_ratio: 1.2     // current strain/recovery balance
│       ├── daily_scores: [                // rolling 90-day window
│       │     { "date": "2026-02-28", "composite": 0.72, "strain": 0.65, "recovery": 0.80 },
│       │     { "date": "2026-02-27", "composite": 0.68, ... },
│       │     ...
│       │   ]
│       ├── category_scores: {             // current 7-day category breakdown
│       │     "fard":        { "performance": 0.8, "consistency": 0.9, "trajectory": 0.3, "composite": 0.71 },
│       │     "tawbah":      { "performance": 0.5, "consistency": 0.6, "trajectory": 0.7, "composite": 0.58 },
│       │     "quran":       { "performance": 0.6, "consistency": 0.8, "trajectory": 0.2, "composite": 0.57 },
│       │     "nafl":        { "performance": 0.3, "consistency": 0.4, "trajectory": 0.5, "composite": 0.38 },
│       │     "character":   { "performance": 0.7, "consistency": 0.7, "trajectory": 0.1, "composite": 0.54 },
│       │     "stewardship": { "performance": 0.6, "consistency": 0.5, "trajectory": 0.0, "composite": 0.38 }
│       │   }
│       ├── active_weights: {              // current personalized weights
│       │     "fard": 0.30, "tawbah": 0.22, "quran": 0.20,
│       │     "nafl": 0.10, "character": 0.10, "stewardship": 0.08
│       │   }
│       ├── plateau_detected: false
│       ├── plateau_days: 0
│       ├── growth_edges: ["nafl", "stewardship"]  // categories with most room to grow
│       └── updated_at: "2026-02-28T..."
│
├── iman_weekly_digests/                   ◄── AI-GENERATED WEEKLY COACHING
│   └── {YYYY-Www} (e.g., "2026-W09")
│       ├── narrative: "This week you showed remarkable..."  (Gemini-generated)
│       ├── trajectory_summary: "ascending"
│       ├── top_correlations: [
│       │     { "behavior_a": "sleep_hours", "behavior_b": "fajr_prayer",
│       │       "correlation": 0.78, "direction": "positive",
│       │       "insight": "When you sleep before 11pm, your Fajr consistency rises to 95%" }
│       │   ]
│       ├── strengths: [
│       │     "Your dhikr practice has been unwavering — 10+ minutes every day this week"
│       │   ]
│       ├── gentle_nudges: [
│       │     "Your Quran time dipped from 25 to 12 minutes mid-week. Even 5 minutes of quality tadabbur counts."
│       │   ]
│       ├── identity_reinforcements: [
│       │     { "statement": "I am someone who prays before sleeping",
│       │       "evidence": "You logged witr prayer 6 out of 7 days — that IS who you are." }
│       │   ]
│       ├── struggle_progress: [
│       │     { "struggle": "anger", "insight": "Anger incidents dropped from 4 to 2 this week. Your wudu-response habit is working." }
│       │   ]
│       ├── verse_prescription: {          // Verse for the coming week
│       │     "surah": 3, "verse": 200,
│       │     "reason": "Your patience journey deepens. This verse crowns the concept of sabr."
│       │   }
│       ├── scholarly_connection: {        // One scholarly insight tied to their week
│       │     "source": "ihya",
│       │     "pointer": "ihya:vol=4:ch=2:sec=0",
│       │     "excerpt": "Al-Ghazali writes: 'Patience is not merely endurance...'"
│       │   }
│       ├── humility_cue: "Remember: Allah sees what no metric can capture. Your sincerity is between you and Him."
│       └── generated_at: "2026-02-28T..."
│
├── iman_struggle_plans/                   ◄── GENERATED STRUGGLE ACTION PLANS
│   └── {struggle_id}
│       ├── label: "anger"
│       ├── scholarly_sources_used: [
│       │     "ihya:vol=3:ch=5",           // ANGER, HATRED AND ENVY
│       │     "ihya:vol=4:ch=2",           // PATIENCE AND GRATEFULNESS (antidote)
│       │     "madarij:vol=2:station=patience",
│       │     "riyad:book=1:ch=3"          // About Patience
│       │   ]
│       ├── mindset_shift: "Al-Ghazali teaches that anger is not..."
│       ├── action_framework: {
│       │     "week_1": { "focus": "Recognize triggers", "actions": [...], "verse": [3, 134] },
│       │     "week_2": { "focus": "Prophetic pause", "actions": [...], "verse": [41, 34] },
│       │     "week_3": { "focus": "Replace with dhikr", "actions": [...], "verse": [7, 199] },
│       │     "week_4": { "focus": "Practice hilm", "actions": [...], "verse": [42, 37] }
│       │   }
│       ├── environmental_adjustments: [
│       │     "Identify your top 3 anger triggers this week",
│       │     "Place a visible reminder near your workspace: 'La taghdab' (Don't be angry)"
│       │   ]
│       ├── habit_anchors: [
│       │     { "cue": "After I feel anger rising", "routine": "make wudu", "source": "hadith" },
│       │     { "cue": "If standing when angry", "routine": "sit down. If sitting, lie down.", "source": "Abu Dawud" }
│       │   ]
│       ├── reflection_verses: [
│       │     { "surah": 3, "verse": 134, "prompt": "What does 'restraining anger' look like in your daily life?" },
│       │     { "surah": 41, "verse": 34, "prompt": "Can you recall a time repelling harshness with gentleness transformed a situation?" },
│       │     { "surah": 42, "verse": 37, "prompt": "What is the difference between suppressing anger and truly forgiving?" },
│       │     { "surah": 7, "verse": 199, "prompt": "How does 'taking the way of forgiveness' apply to your closest relationships?" }
│       │   ]
│       ├── weekly_journal_prompts: [
│       │     "What triggered me this week and how did I respond?",
│       │     "What would the Prophet ﷺ have done in my most difficult moment?",
│       │     "Al-Ghazali says anger's root is often unmet expectations. What expectations drove my anger?"
│       │   ]
│       ├── linked_behaviors: ["anger_incidents", "wudu_response", "forgiveness_practice"]
│       ├── progress_log: [
│       │     { "week": 1, "reflection": "Identified 3 triggers...", "behavior_summary": {...} }
│       │   ]
│       ├── generated_at: "2026-02-28T..."
│       └── status: "active"
│
└── [EXISTING subcollections - unchanged]
    ├── annotations/{annotation_id}
    ├── query_history/{history_id}
    └── saved_searches/{search_id}
```

### Behavior Categories & Default Behaviors

```
┌──────────────────────────────────────────────────────────────────────────┐
│ CATEGORY: fard (Obligatory Worship)                    Base Weight: 0.30│
│ Islamic Basis: "The most beloved deeds to Allah are the obligatory"     │
├──────────────────────────────────────────────────────────────────────────┤
│ Behavior ID        │ Label              │ Input Type │ Default │ Notes  │
│────────────────────│────────────────────│────────────│─────────│────────│
│ fajr_prayer        │ Fajr Prayer        │ binary     │ ON      │        │
│ dhuhr_prayer       │ Dhuhr Prayer       │ binary     │ ON      │        │
│ asr_prayer         │ Asr Prayer         │ binary     │ ON      │        │
│ maghrib_prayer     │ Maghrib Prayer     │ binary     │ ON      │        │
│ isha_prayer        │ Isha Prayer        │ binary     │ ON      │        │
│ masjid_attendance  │ Masjid Attendance  │ binary     │ OFF     │ opt-in │
│ fasting            │ Fasting            │ binary     │ OFF     │seasonal│
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ CATEGORY: tawbah (Sin Avoidance & Repentance)          Base Weight: 0.20│
│ Islamic Basis: "Leave that which makes you doubt for that which doesn't"│
├──────────────────────────────────────────────────────────────────────────┤
│ lowering_gaze      │ Lowering Gaze      │ scale_5    │ OFF     │ opt-in │
│ avoided_sins       │ Avoided Known Sins │ scale_5    │ ON      │        │
│ device_discipline  │ Device Discipline  │ scale_5    │ OFF     │ opt-in │
│ tawbah_moment      │ Sought Forgiveness │ binary     │ ON      │        │
│ anger_incidents    │ Anger Incidents    │ count_inv  │ OFF     │struggle│
└──────────────────────────────────────────────────────────────────────────┘
  * count_inv = inverse count (fewer = better)

┌──────────────────────────────────────────────────────────────────────────┐
│ CATEGORY: quran (Quranic Engagement)                   Base Weight: 0.20│
│ Islamic Basis: "The best of you are those who learn the Quran"          │
├──────────────────────────────────────────────────────────────────────────┤
│ quran_minutes      │ Quran Recitation   │ minutes    │ ON      │        │
│ tadabbur_session   │ Tadabbur (Reflect) │ binary     │ ON      │app-link│
│ quran_memorization │ Memorization       │ minutes    │ OFF     │ opt-in │
└──────────────────────────────────────────────────────────────────────────┘
  * tadabbur_session auto-detected from existing app usage

┌──────────────────────────────────────────────────────────────────────────┐
│ CATEGORY: nafl (Voluntary Worship)                     Base Weight: 0.12│
│ Islamic Basis: "My servant draws near through nafl until I love him"    │
├──────────────────────────────────────────────────────────────────────────┤
│ sunnah_prayers     │ Sunnah Prayers     │ count      │ ON      │ 0-12   │
│ tahajjud           │ Tahajjud/Qiyam     │ binary     │ OFF     │ opt-in │
│ dhikr_minutes      │ Dhikr              │ minutes    │ ON      │        │
│ dua_moments        │ Dua Moments        │ count      │ ON      │        │
│ charity            │ Charity/Sadaqah    │ binary     │ OFF     │ opt-in │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ CATEGORY: character (Character & Social)               Base Weight: 0.10│
│ Islamic Basis: "The best among you are those best in character"         │
├──────────────────────────────────────────────────────────────────────────┤
│ gratitude_entry    │ Gratitude Practice │ binary     │ ON      │        │
│ kindness_act       │ Act of Kindness    │ binary     │ OFF     │ opt-in │
│ forgiveness        │ Forgiveness        │ binary     │ OFF     │ opt-in │
│ family_rights      │ Family Rights      │ scale_5    │ OFF     │ opt-in │
│ tongue_control     │ Guarded Speech     │ scale_5    │ OFF     │ opt-in │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ CATEGORY: stewardship (Physical & Mental Health)       Base Weight: 0.08│
│ Islamic Basis: "Your body has a right over you"                         │
├──────────────────────────────────────────────────────────────────────────┤
│ sleep_hours        │ Sleep Duration     │ hours      │ ON      │ 0-12   │
│ exercise           │ Physical Activity  │ binary     │ OFF     │ opt-in │
│ healthy_eating     │ Mindful Eating     │ binary     │ OFF     │ opt-in │
└──────────────────────────────────────────────────────────────────────────┘
```

### Input Type Normalization Rules

```
binary     → 0 or 1 (direct)
scale_5    → value / 5.0 → [0, 1]
minutes    → min(value / P95_personal, 1.0)
hours      → gaussian_score(value, optimal=7.5, sigma=1.5) → [0, 1]
count      → min(value / P95_personal, 1.0)
count_inv  → max(1 - (value / P95_personal), 0.0)   ◄── fewer = better
```

---

## LAYER 5: Iman Index Mathematical Engine

### Design Principles

1. **Trajectory > Raw Score**: The user never sees a number. They see direction.
2. **Consistency > Intensity**: 5 minutes of dhikr daily > 60 minutes once a week.
3. **Baseline-Relative**: Everything is measured against the user's own history.
4. **Anti-Inflation**: As habits lock in, they contribute less. Growth edges matter more.
5. **Spiritual Strain/Recovery**: Mirrors WHOOP's insight that you can't push 100% every day.

### Islamic Theological Grounding

The mathematical design maps to Al-Ghazali's Muhasaba framework from Ihya Vol 4 Ch 8:

```
Musharata  (Setting conditions)    →  Identity statements + behavior selection
Muraqaba   (Watchfulness)          →  Daily behavioral logging
Muhasaba   (Self-accounting)       →  Iman Index computation
Mu'aqaba   (Self-discipline)       →  Coaching nudges for gaps
Mujahada   (Striving)              →  Growth edge identification
Mu'ataba   (Gentle self-reproach)  →  Recalibration, not punishment
```

Ibn Qayyim's Madarij framework maps to the trajectory states:

```
Awakening (yaqazah)        →  First 14 days (calibration period)
Insight (basirah)          →  Correlation detection ("I see patterns")
Self-Reckoning (muhasabah) →  Weekly digest review
Repentance (tawbah)        →  Recalibrating state (returning, not failing)
Patience (sabr)            →  Steady state (maintaining, not stagnating)
Gratitude (shukr)          →  Ascending state (growing with thankfulness)
```

### Step 1: Behavior Normalization

For each behavior `b` logged on day `t`:

```
Given:
  x_b(t) = raw logged value of behavior b on day t
  type_b = input type of behavior b (binary, scale_5, minutes, hours, count, count_inv)

Normalize to [0, 1]:

  if type_b == "binary":
      x̂_b(t) = x_b(t)                                    // already 0 or 1

  if type_b == "scale_5":
      x̂_b(t) = x_b(t) / 5.0

  if type_b == "minutes" or type_b == "count":
      P95_b = 95th percentile of user's last 30 values for behavior b
      x̂_b(t) = min(x_b(t) / max(P95_b, 1), 1.0)         // cap at 1.0, avoid /0

  if type_b == "hours":
      // Gaussian scoring — optimal sleep is ~7.5h, too little or too much is suboptimal
      x̂_b(t) = exp(-0.5 * ((x_b(t) - 7.5) / 1.5)²)      // bell curve centered at 7.5

  if type_b == "count_inv":
      P95_b = 95th percentile of user's last 30 values for behavior b
      x̂_b(t) = max(1.0 - (x_b(t) / max(P95_b, 1)), 0.0) // fewer = better
```

### Step 2: Category Aggregation

For each category `c` on day `t`:

```
Let B_c = set of all active behaviors in category c
Let n_c = |B_c| (number of active behaviors in category)

daily_c(t) = (1/n_c) * Σ x̂_b(t)  for all b ∈ B_c

Range: [0, 1] where 0 = nothing logged, 1 = all behaviors at personal ceiling
```

**Missing data handling:**
```
If behavior b was not logged on day t:
  - Binary/scale behaviors: x̂_b(t) = 0  (conservative — assume not done)
  - Minutes/count behaviors: x̂_b(t) = 0
  - Hours (sleep): EXCLUDE from average (don't penalize for not logging sleep)

If a day has zero logged behaviors:
  - Mark day as "unlogged" — exclude from rolling calculations
  - Do NOT treat as 0 (avoids punishing users for not opening the app)
  - After 3 consecutive unlogged days, include as 0 (prevents gaming by not logging bad days)
```

### Step 3: Baseline Computation

**Initial Calibration (Days 1-14):**

During the first 14 days, no index is shown. The system collects data silently.

```
After day 14:
  For each category c:
    μ_c = median(daily_c(t) for t in [day 1 ... day 14])
    σ_c = MAD(daily_c(t) for t in [day 1 ... day 14])
        where MAD = median absolute deviation = median(|daily_c(t) - μ_c|)
    P95_c = 95th percentile of daily_c(t) values

  Store in iman_baselines/current
  Set baseline_established = true
```

**Why median + MAD instead of mean + std_dev:**
- Robust to outliers (one amazing day shouldn't inflate baseline)
- Better represents "typical" behavior
- MAD is the Islamic "middle path" (wasatiyyah) of statistics

**Rolling Recalibration (every 30 days):**

```
On recalibration day:
  For each category c:
    recent_median = median(daily_c(t) for t in last 30 days)
    recent_mad = MAD(daily_c(t) for t in last 30 days)

    μ_c_new = 0.7 * μ_c_old + 0.3 * recent_median    // EMA: gradual shift
    σ_c_new = 0.7 * σ_c_old + 0.3 * recent_mad

  Log recalibration snapshot to baseline history
```

**Why this matters:**
- A user who prayed 3/5 prayers initially has baseline μ_fard ≈ 0.6
- After 2 months of 5/5, recalibrated baseline shifts to μ_fard ≈ 0.85
- Now 5/5 is "steady", not "ascending" — they need to deepen (masjid, khushu) to grow
- THIS prevents score inflation and forces continuous growth

### Step 4: The Three Pillars

For each category `c`, compute three independent dimensions over a 7-day window `W = [t-6 ... t]`:

**Pillar 1 — Relative Performance (P_c):**
How far above or below your own baseline.

```
P_c = (mean(daily_c(t) for t in W) - μ_c) / max(σ_c, 0.10)

Clamp to [-2.0, 2.0], then rescale:
P_c_scaled = P_c / 2.0  →  range [-1, 1]

Interpretation:
  +1.0 = performing 2+ standard deviations above your baseline (exceptional week)
   0.0 = performing at your baseline (maintaining)
  -1.0 = performing 2+ standard deviations below baseline (significant dip)
```

**Pillar 2 — Consistency (K_c):**
How stable your practice is, day to day. This is the Atomic Habits pillar.

```
mean_W = mean(daily_c(t) for t in W)
std_W  = std(daily_c(t) for t in W)

K_c = 1.0 - (std_W / max(mean_W, 0.10))

Clamp to [0, 1]

Interpretation:
  1.0 = perfectly consistent (same level every day)
  0.5 = moderate variation
  0.0 = wildly inconsistent (feast-or-famine pattern)

Special case: if mean_W < 0.05 (barely practicing):
  K_c = 0.0  // don't reward "consistency" of doing nothing
```

**Islamic grounding:**
> "The most beloved deeds to Allah are the most consistent, even if small." — Bukhari
>
> This pillar mathematically encodes this hadith. A user who prays all 5 prayers
> every day (K=0.95) scores higher on consistency than one who prays all 5 on
> weekends but misses 2 on weekdays (K=0.60), even if their weekly total is similar.

**Pillar 3 — Trajectory (T_c):**
Which direction are you heading? Uses 14-day window for more stable trend.

```
W_long = [t-13 ... t]  (14-day window)
values = [daily_c(t) for t in W_long]
days   = [0, 1, 2, ..., 13]

T_c = pearson_correlation(days, values)

Range: [-1, 1]

Interpretation:
  +1.0 = perfectly upward trend over 14 days
   0.0 = flat / no directional trend
  -1.0 = perfectly downward trend over 14 days
```

**Why Pearson correlation instead of linear regression slope:**
- Normalized to [-1, 1] regardless of absolute values
- A user going from 0.1 → 0.3 and a user going from 0.7 → 0.9 both get similar T_c
- This ensures trajectory rewards RELATIVE growth, not absolute level

### Step 5: Category Composite Score

```
S_c = α * P_c_scaled + β * K_c + γ * T_c

Where:
  α = 0.25  (relative performance)
  β = 0.45  (consistency — weighted HIGHEST)
  γ = 0.30  (trajectory)

Range: approximately [-0.55, 1.0]
  Theoretical max: 0.25(1) + 0.45(1) + 0.30(1) = 1.0
  Theoretical min: 0.25(-1) + 0.45(0) + 0.30(-1) = -0.55
```

**Why consistency is weighted highest (β = 0.45):**
1. Islamic: "Most beloved deeds... most consistent" (Bukhari)
2. Behavioral science: Identity is formed through repetition, not intensity (Atomic Habits)
3. WHOOP insight: Recovery/consistency predicts performance better than peak effort
4. Anti-gaming: Can't game consistency — you either show up every day or you don't

### Step 6: Personalized Category Weights

**Base Weights (Islamic priority order):**

```
W = {
  "fard":        0.30,   // Obligatory — highest by Shariah consensus
  "tawbah":      0.20,   // Sin avoidance — "leaving haram is the first obligation"
  "quran":       0.20,   // Quranic engagement — core of this app's mission
  "nafl":        0.12,   // Voluntary worship
  "character":   0.10,   // Character & social
  "stewardship": 0.08    // Physical health
}
Sum = 1.00
```

**Weight Recalibration Rule (Anti-Inflation):**

```
For each category c:
  If K_c > 0.85 for 30 consecutive days:
    // This behavior is "locked in" — it's become habit, not growth
    w_c_adjusted = w_c * 0.80  // reduce weight by 20%
    freed_weight = w_c * 0.20

    // Redistribute freed weight to growth edges (lowest-K categories)
    growth_edges = categories sorted by K_c ascending, excluding locked-in categories
    for edge in growth_edges:
      w_edge += freed_weight / len(growth_edges)

  Constraint: No category weight can drop below 50% of its base weight
    w_c_adjusted >= w_c_base * 0.50

  Constraint: No category weight can exceed 150% of its base weight
    w_c_adjusted <= w_c_base * 1.50
```

**Example:**
```
User has been praying 5/5 consistently for 2 months (K_fard = 0.95):
  w_fard: 0.30 → 0.24 (reduced by 20%)
  Freed: 0.06
  Growth edges: nafl (K=0.40), character (K=0.35)
  w_nafl: 0.12 → 0.15 (+0.03)
  w_character: 0.10 → 0.13 (+0.03)

Now the index rewards them for growing their nafl and character practice,
not just maintaining what's already established.
```

**Why this matters theologically:**
- Prevents a user from "coasting" on established fard practice while neglecting character
- Mirrors the Islamic concept of ihsan (excellence) — once fard is solid, grow into nafl
- Reflects the hadith qudsi: "My servant draws near through obligatory... then through voluntary..."
- The progression IS the sunnah: master obligations → deepen voluntary → refine character

### Step 7: Composite Iman Index

```
I(t) = Σ (w_c * S_c)  for all categories c

Where w_c = current adjusted weight for category c (after recalibration)

Raw range: approximately [-0.55, 1.0]
```

**Display Transformation (sigmoid normalization):**

```
I_normalized(t) = 100 / (1 + e^(-3.0 * I(t)))

Range: [0, 100] (asymptotic — never truly reaches 0 or 100)
Center: I(t)=0 maps to 50 (performing at baseline = middle)
```

### ⚠️ THE USER NEVER SEES THIS NUMBER.

The numeric score exists only for internal computation. What the user sees:

### Step 8: User-Facing Display

**Trajectory State** (from 14-day slope of I_normalized):

```
slope = linear_regression_slope(I_normalized over last 14 days)

if slope > 0.3:     state = "Ascending"       arrow = ↗   color = #2D8A6E (teal)
if 0.05 < slope ≤ 0.3: state = "Gently Rising" arrow = ↗   color = #4AA88A
if -0.1 ≤ slope ≤ 0.05: state = "Steady"       arrow = →   color = #B8860B (gold)
if slope < -0.1:    state = "Recalibrating"   arrow = ↻   color = #8B7355 (warm brown)
```

**Note: There is NO "declining" state.** The word "recalibrating" is intentional:
- Spiritual lows are part of every journey
- The Prophet ﷺ said: "Iman increases and decreases"
- Ibn Qayyim writes in Madarij: "The heart has cycles of expansion (bast) and contraction (qabd)"
- The goal is awareness and return, not perpetual ascent

**Volatility State** (coefficient of variation of daily I_normalized over 14 days):

```
CV = std(I_normalized over 14 days) / mean(I_normalized over 14 days)

if CV < 0.08:      volatility = "Stable"
if 0.08 ≤ CV ≤ 0.20: volatility = "Dynamic"
if CV > 0.20:      volatility = "Turbulent"
```

**Combined Display Matrix:**

```
┌──────────────────┬────────────────────────────────────────────────────────┐
│ State            │ Meaning & Coaching Tone                               │
├──────────────────┼────────────────────────────────────────────────────────┤
│ Ascending &      │ Strong growth with consistency. "Your practice is     │
│ Stable           │ deepening beautifully. The scholars call this         │
│                  │ istiqamah — steadfastness on the path."               │
├──────────────────┼────────────────────────────────────────────────────────┤
│ Ascending &      │ Growing but inconsistently. "Your highs are getting   │
│ Dynamic          │ higher — now let's make them more consistent.         │
│                  │ Small daily acts compound more than weekly bursts."    │
├──────────────────┼────────────────────────────────────────────────────────┤
│ Steady &         │ Maintained discipline. THIS IS GOOD — not plateau.    │
│ Stable           │ "Istiqamah is itself a rank. The Prophet ﷺ said:     │
│                  │ 'Say I believe in Allah, then be steadfast.'"         │
├──────────────────┼────────────────────────────────────────────────────────┤
│ Steady &         │ Maintaining but with variation. "Some days are fuller │
│ Dynamic          │ than others — that's human. Your consistency is in    │
│                  │ the returning, not in perfection."                    │
├──────────────────┼────────────────────────────────────────────────────────┤
│ Recalibrating &  │ Going through a test. "Ibn Qayyim writes: 'The       │
│ Stable           │ contraction of the heart (qabd) often precedes        │
│                  │ expansion (bast).' This may be that moment."          │
├──────────────────┼────────────────────────────────────────────────────────┤
│ Recalibrating &  │ Turbulent period. "Even the Prophet's companions     │
│ Turbulent        │ experienced fluctuations. Hanzalah said 'Hanzalah    │
│                  │ has become a hypocrite!' and the Prophet ﷺ replied:  │
│                  │ 'If you were always as you are with me, the angels   │
│                  │ would shake your hands.'"                             │
└──────────────────┴────────────────────────────────────────────────────────┘
```

### Step 9: Growth Decay & Plateau Detection

**Growth Decay (prevents indefinite high scores):**

```
For each category c:
  days_above = consecutive days where S_c > 0.70

  if days_above > 60:
    decay_factor = 1.0 - (0.005 * (days_above - 60))
    decay_factor = max(decay_factor, 0.70)    // floor: 30% max decay
    S_c_decayed = S_c * decay_factor

Rationale:
  - After 60 days of high performance, the behavior is established
  - Without decay, the index stagnates at "high" with no motivation to grow
  - Decay gently pushes: "This is great — now what's your next edge?"
  - 0.5% per day past 60 means full decay (30%) at day 120 (4 months)
```

**Plateau Detection:**

```
plateau_slope_threshold = 0.02
plateau_duration_threshold = 21  // days

if |slope of I_normalized| < plateau_slope_threshold for 21 consecutive days:
    plateau_detected = true

Coaching response:
  - "You've been steady for 3 weeks. Steadiness is strength — but if you feel
     called to grow, here are your edges:"
  - Show growth_edges (categories with lowest consistency)
  - Suggest: new behaviors, deeper engagement, or struggle work
  - NEVER frame plateau as failure
```

### Step 10: Spiritual Strain & Recovery Model

Inspired by WHOOP's core insight: you can't train at 100% every day. The heart needs both mujahada (striving) and sakina (tranquility).

**Al-Ghazali's Ihya parallel:** The nafs needs both riyada (discipline) and ghidha (nourishment). Too much discipline without nourishment → spiritual burnout. Too much nourishment without discipline → complacency.

**Spiritual Strain (daily):**

```
strain(t) = Σ (attempt_weight_b * difficulty_factor_b)  for all attempted behaviors on day t

Where:
  attempt_weight_b:
    - binary behavior attempted:     1.0
    - scale_5 behavior logged:       value / 5.0
    - minutes/count behavior logged: min(value / P95, 1.0)

  difficulty_factor_b:
    - behavior linked to active struggle: 1.5x  (struggling behaviors are harder)
    - behavior with K_c < 0.30 (inconsistent): 1.3x  (new/hard behaviors)
    - all other behaviors: 1.0x

Normalize: strain_normalized(t) = strain(t) / max_possible_strain
Range: [0, 1]
```

**Spiritual Recovery (daily):**

```
recovery(t) =
    0.25 * (heart_notes_count(t) > 0)     +   // Spiritual journaling
    0.25 * (quran_engagement(t) > 0)       +   // Quran time (any amount)
    0.20 * (dhikr_minutes(t) > 0)          +   // Dhikr / remembrance
    0.15 * gaussian(sleep_hours(t), 7.5, 1.5) + // Physical rest
    0.15 * (reflection_written(t))              // Deep reflection/tadabbur

Range: [0, 1]
```

**Strain-Recovery Ratio:**

```
SR_ratio(t) = mean(strain over 7 days) / max(mean(recovery over 7 days), 0.1)

Interpretation:
  SR < 0.8:   "Restorative Phase" — more recovery than strain
              "You're in a restful season. Beautiful — rest is worship.
               This is the perfect time to deepen one practice rather than add new ones."

  0.8 ≤ SR ≤ 1.3:  "Balanced" — healthy strain-recovery equilibrium
              "Your effort and nourishment are balanced.
               Al-Ghazali calls this i'tidal — the equilibrium of the heart."

  SR > 1.3:   "High Strain" — pushing hard without enough recovery
              "You're striving intensely — mashAllah. But the Prophet ﷺ said:
               'This religion is ease, and no one overburdens himself in religion
               except that it overcomes him.' (Bukhari)
               Consider: more dhikr, more sleep, or a day of gentle practice."

  SR > 2.0 for 7+ days:  "Burnout Risk" — urgent coaching intervention
              "Your heart needs nourishment. The Prophet ﷺ told Abdullah ibn Amr
               — who was fasting every day and praying all night — 'Your body has
               a right over you, your eyes have a right over you, and your family
               has a right over you.' Please rest."
```

**Visual Representation:**

```
The user sees a simple two-bar indicator:

  Strain:   ████████░░  (80%)
  Recovery: ██████░░░░  (60%)

  Status: "Consider more rest — your spirit needs nourishment alongside effort"

No numbers shown — just relative bars and a one-line insight.
```

---

## LAYER 1: Behavioral Logging (WHOOP-Style Journal)

### Design Philosophy

WHOOP's journal doesn't just track — it **correlates**. The user logs sleep, strain, alcohol, caffeine → WHOOP shows "When you avoid alcohol, your recovery is 23% higher."

Our spiritual equivalent: User logs prayers, Quran time, sleep, sin avoidance, dhikr → system shows "When you do dhikr before bed, your Fajr consistency rises by 40%."

The journal is NOT a checklist. It's a **data source for insight**.

### Journal Entry Flow (Minimal Friction)

```
┌─────────────────────────────────────────────────┐
│           Evening Muhasaba                       │
│           "How was your day with Allah?"         │
│                                                  │
│  ☪ Prayers                                       │
│  [✓] Fajr  [✓] Dhuhr  [✓] Asr  [✓] Maghrib    │
│  [✓] Isha  [ ] Masjid                           │
│                                                  │
│  📖 Quran & Dhikr                               │
│  Quran:  [====15min====]  Dhikr: [==5min==]     │
│  [ ] Tadabbur session (auto-detected from app)   │
│                                                  │
│  🛡 Guarding                                     │
│  Avoided sins:     ○ ○ ○ ● ○  (4/5)            │
│  Device discipline: ○ ○ ● ○ ○  (3/5)            │
│  [ ] Sought forgiveness today                    │
│                                                  │
│  💪 Voluntary                                    │
│  Sunnah prayers: [3]  [ ] Tahajjud  [ ] Charity │
│  Dua moments: [2]                                │
│                                                  │
│  🌱 Character                                    │
│  [ ] Gratitude entry  [ ] Act of kindness        │
│                                                  │
│  😴 Body                                         │
│  Sleep: [===7.0h===]  [ ] Exercise               │
│                                                  │
│  💚 How is your heart? (optional)                │
│  [Grateful] [Anxious] [Peaceful] [Struggling]   │
│                                                  │
│  📝 Heart Note (optional):                       │
│  [                                          ]    │
│                                                  │
│             [Save & Reflect]                     │
└─────────────────────────────────────────────────┘
```

### Key Design Decisions

**1. One-Screen Logging (< 90 seconds)**
- WHOOP's journal takes ~60 seconds. Ours must be similar.
- Default behaviors pre-selected based on user's tracked set
- Sliders for minutes, taps for binary, 5-dot scale for subjective
- No typing required (Heart Note is optional free-text)

**2. Smart Defaults & Auto-Detection**
- `tadabbur_session`: Auto-detected from existing app usage (user opened tafsir today)
- `quran_minutes`: Can sync with Quran apps via future API (or manual)
- `fajr_prayer`: If user opened app before 7am, pre-check Fajr
- Prayer times: Use location-based prayer time APIs for time-awareness

**3. Partial Logging Accepted**
- User can log just prayers and skip everything else
- Missing fields are NOT penalized (see missing data handling in Step 2)
- The system adapts to whatever the user provides

**4. Encryption**
- All behavioral data encrypted at-rest using existing per-user Fernet encryption
- Same HMAC-SHA256 key derivation as current annotation encryption
- Behavioral logs are MORE sensitive than annotations — they reveal daily habits

### Correlation Detection Engine

After 21+ days of data, begin detecting correlations.

**Method: Sliding Pearson Correlation (30-day rolling window)**

```
For each pair (behavior_a, behavior_b) where both have 21+ data points:
    r = pearson_correlation(x̂_a over last 30 days, x̂_b over last 30 days)
    p = p-value of correlation

    if |r| > 0.40 and p < 0.05:
        // Significant correlation detected
        store as { behavior_a, behavior_b, r, p, direction, window }
```

**Cross-Category Correlations (most insightful):**

```
Prioritize correlations that cross categories:
  stewardship × fard:    "Sleep hours ↔ Fajr prayer"
  tawbah × character:    "Device discipline ↔ Tongue control"
  nafl × quran:          "Dhikr minutes ↔ Quran engagement"
  quran × tawbah:        "Tadabbur sessions ↔ Sin avoidance"
  stewardship × nafl:    "Sleep quality ↔ Tahajjud consistency"
```

**Insight Generation Template (for AI coaching):**

```
When correlation detected (r > 0.40):
  Positive: "When you {behavior_a_high}, your {behavior_b} tends to be {higher/better}.
             This week: {behavior_a} was logged {X} days → {behavior_b} averaged {Y}."

  Negative: "On days when you {behavior_a_low}, your {behavior_b} tends to dip.
             This isn't judgment — it's awareness. What might help?"

Examples:
  "When you sleep 7+ hours, your Fajr consistency is 92%. Below 6 hours, it drops to 45%."
  "Days with 10+ minutes of dhikr correlate with higher 'avoided sins' scores (r=0.62)."
  "Your Quran engagement is highest on days you also exercise. The body-spirit connection is real."
```

### Behavioral Clustering (Pattern Recognition)

After 30+ days, cluster days into behavioral archetypes:

```
Method: K-means clustering on daily behavior vectors (k=3 to 5)

Typical clusters that emerge:
  Cluster A: "Peak Days"     — high across all categories (prayers + Quran + dhikr + good sleep)
  Cluster B: "Fard Days"     — prayers consistent but low nafl/character
  Cluster C: "Struggle Days" — low fard, low tawbah, high strain
  Cluster D: "Recovery Days" — moderate fard, high quran/dhikr, good sleep

Insight: "Your 'Peak Days' (Cluster A) share three traits: 7+ hours sleep,
          morning dhikr, and Quran before Dhuhr. Can you replicate those conditions?"
```

### Trend Shift Detection

Detect when a user's behavior pattern meaningfully changes:

```
Method: CUSUM (Cumulative Sum Control Chart) on category daily scores

For each category c:
  S_high(t) = max(0, S_high(t-1) + daily_c(t) - (μ_c + k))
  S_low(t)  = max(0, S_low(t-1) + (μ_c - k) - daily_c(t))

  where k = 0.5 * σ_c  (slack parameter)
  threshold h = 4 * σ_c

  if S_high(t) > h: Upward shift detected in category c
  if S_low(t) > h:  Downward shift detected in category c

Coaching on shift detection:
  Upward: "Something changed in your {category} practice over the last {n} days.
           Your consistency jumped. What shifted? Can you sustain it?"

  Downward: "Your {category} practice has shifted down recently.
             This isn't failure — it's information. What changed in your life?
             Can we adjust your tracked behaviors to match your current capacity?"
```

---

## LAYER 2: Identity & Intention (Atomic Habits × Islam)

### Core Framework

James Clear's identity model: "Every action is a vote for the type of person you wish to become."

Al-Ghazali's parallel from Ihya Vol 3 Ch 2 (Good Conduct): "Character (khulq) is acquired through repeated action. You become patient by practicing patience."

Ibn Qayyim's parallel from Madarij: "The stations are not merely understood — they are inhabited through practice."

### Identity Statement System

**Structure:**
```
{
  "id": "ist_001",
  "statement": "I am someone who turns to Allah when stressed",
  "source_type": "quran",                    // quran | hadith | scholar
  "source_ref": "And when My servants ask you about Me, I am near (2:186)",
  "micro_behavior": "When I feel stress, I say 'HasbiyAllahu wa ni'mal wakeel' 3 times",
  "habit_stack": "After I feel stress rising → I pause → I make dhikr → then I respond",
  "linked_behaviors": ["dua_moments", "dhikr_minutes"],
  "reinforcement_count": 0,                  // incremented when linked behaviors logged
  "created_at": "2026-02-28T..."
}
```

**Pre-Built Identity Templates (user selects or customizes):**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Category: Prayer & Worship                                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│ "I am someone who never misses a prayer"                                        │
│  Source: "Guard strictly the prayers, especially the middle prayer" (2:238)     │
│  Micro: Set alarm 5 min before each prayer time                                │
│  Stack: After adhan → I stop what I'm doing → I make wudu → I pray            │
│  Linked: fajr_prayer, dhuhr_prayer, asr_prayer, maghrib_prayer, isha_prayer    │
├─────────────────────────────────────────────────────────────────────────────────┤
│ "I am someone who stands in the last third of the night"                        │
│  Source: "Is one who worships during the night, prostrating and standing..." (39:9)│
│  Micro: Set alarm 30 min before Fajr. Even 2 raka'at counts.                  │
│  Stack: After alarm → I make wudu → I pray 2 raka'at → I make dua             │
│  Linked: tahajjud                                                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Category: Sin Avoidance & Tawbah                                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│ "I am someone who guards my gaze"                                               │
│  Source: "Tell the believing men to lower their gaze" (24:30)                  │
│  Micro: When temptation appears, immediately look away and say istighfar       │
│  Stack: After I see something → I look down → I say Astaghfirullah → I move on│
│  Linked: lowering_gaze, device_discipline                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│ "I am someone who controls my tongue"                                           │
│  Source: "Whoever believes in Allah and the Last Day, let him speak good or     │
│           remain silent" (Bukhari)                                              │
│  Micro: Before speaking, pause. Ask: Is it true? Is it kind? Is it necessary? │
│  Stack: After I want to comment → I pause 3 seconds → I filter → I speak/stay  │
│  Linked: tongue_control                                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Category: Spiritual Connection                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ "I am someone who turns to Allah when stressed"                                 │
│  Source: "And when My servants ask you about Me, I am near" (2:186)            │
│  Micro: When stressed, say 'HasbiyAllahu wa ni'mal wakeel' 3 times            │
│  Stack: After I feel stress → I pause → I make dhikr → then I respond          │
│  Linked: dua_moments, dhikr_minutes                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│ "I am someone who begins and ends the day with Allah"                           │
│  Source: Morning/evening adhkar of the Prophet ﷺ                               │
│  Micro: 5 minutes of morning adhkar after Fajr, 5 minutes before sleep         │
│  Stack: After Fajr prayer → I stay seated → I recite adhkar                    │
│  Linked: dhikr_minutes, sunnah_prayers                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Category: Character & Growth                                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│ "I am someone who is grateful before complaining"                               │
│  Source: "If you are grateful, I will increase you" (14:7)                     │
│  Micro: Write one gratitude entry before bed                                   │
│  Stack: After I lay down → I think of 3 blessings → I say Alhamdulillah       │
│  Linked: gratitude_entry                                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│ "I am someone who gives, even when it's small"                                  │
│  Source: "Protect yourself from the Fire, even with half a date" (Bukhari)     │
│  Micro: Set aside any amount daily — even $1 counts                            │
│  Stack: After I buy coffee → I donate the same amount digitally                │
│  Linked: charity                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Identity Reinforcement Logic

The AI tracks how consistently the user's ACTIONS align with their STATED IDENTITY.

```
For each identity statement ist:
  linked_consistency = mean(K_b for all b in ist.linked_behaviors)
  reinforcement_days = count of days where ALL linked behaviors were positive

  // Reinforcement levels (inspired by Atomic Habits "votes" concept)
  if reinforcement_days >= 30 consecutive:
    level = "embodied"
    message = "This is no longer something you do — it's who you ARE.
               {ist.statement} — the evidence is undeniable."

  if 14 ≤ reinforcement_days < 30:
    level = "strengthening"
    message = "{reinforcement_days} days of living '{ist.statement}'.
               Each day is a vote for this identity. Keep voting."

  if 7 ≤ reinforcement_days < 14:
    level = "forming"
    message = "A week of '{ist.statement}'. The habit is taking root.
               The Prophet ﷺ said the most beloved deeds are the most consistent."

  if reinforcement_days < 7:
    level = "planting"
    message = "You've planted the seed of '{ist.statement}'.
               Every small act waters it. Be patient with yourself."
```

**Inconsistency Detection (Gentle, Never Shaming):**

```
If user has identity "I am someone who never misses a prayer"
but K_fard < 0.50 for 14 days:

  // Do NOT say: "You're not living up to your identity"
  // Instead:

  "Your identity — '{ist.statement}' — is beautiful.
   Life sometimes creates gaps between who we want to be and where we are.
   That gap isn't failure — it's the space where growth happens.

   Would you like to:
   (a) Adjust this identity to something more achievable right now?
   (b) Add a micro-behavior to make it easier?
   (c) Keep it as your north star and be patient with the journey?"
```

**Habit Stacking Engine:**

```
Format: "After [CURRENT HABIT], I will [NEW BEHAVIOR]"

The system suggests stacks based on:
  1. User's strongest behaviors (anchors)
  2. User's weakest behaviors (targets)
  3. Natural temporal proximity

Example auto-suggestions:
  If user consistently prays Fajr but struggles with Quran:
    "After Fajr prayer → stay on your musalla → read 1 page of Quran"

  If user sleeps well but misses adhkar:
    "After setting your alarm → recite 3 evening adhkar before closing your eyes"

  If user does dhikr but forgets charity:
    "After your morning dhikr → transfer $1 to your charity fund"
```

---

## LAYER 2b: Struggle-Based Action Framework Generator

### Input → Scholarly Query → Structured Plan

When user declares: **"I struggle with anger"**

### Phase 1: Scholarly Source Resolution

```
Input: "anger"
Keywords extracted: ["anger", "ghadab", "wrath", "angry"]

Query existing routing tables:
  _IHYA_ROUTING match:
    {"anger", "envy", "hatred", "jealousy", "hasad"} → ihya:vol=3:ch=5:sec=0
    (ANGER, HATRED AND ENVY — the problem)

    Also fetch antidote:
    {"patience", "sabr"} → ihya:vol=4:ch=2:sec=0
    (PATIENCE AND GRATEFULNESS — the cure)

  _MADARIJ_ROUTING match:
    {"patience", "sabr", "patient", "steadfast"} → madarij:vol=2:station=patience:sub=0

  _RIYAD_ROUTING match:
    {"patience", "sabr"} → riyad:book=1:ch=3:hadith=0
    (About Patience)

  _topic_map.json match:
    "anger" → [
      { "source": "ihya_ulum_al_din", "pointer": "ihya → vol:3 → ch:5", "title": "ANGER, HATRED AND ENVY" }
    ]

Verses from Quran (hardcoded anger-related verse map):
  3:134  — "Those who restrain anger and pardon people"
  41:34  — "Repel evil with that which is better"
  42:37  — "Those who avoid major sins and when angry, they forgive"
  7:199  — "Take the way of forgiveness and enjoin good"
  3:159  — "By mercy of Allah you were lenient with them"
  16:126 — "If you punish, punish proportionately. But patience is better."
```

### Phase 2: Content Extraction

Resolve each pointer to actual content:

```
ihya:vol=3:ch=5 → Load backend/data/indexes/ihya_ulum_al_din/vol_3.json, chapter 5
  Extract: Key principles, Quranic references, practical advice

madarij:vol=2:station=patience → Load madarij_al_salikin/vol_2.json, station "patience"
  Extract: Station description, spiritual progression, Quranic basis

riyad:book=1:ch=3 → Load riyad_al_saliheen/book_01_ch_003.json
  Extract: Relevant hadith about patience and anger management
```

### Phase 3: Plan Generation (Gemini 2.5 Flash)

**Prompt template for struggle plan generation:**

```
You are a wise Islamic scholar-counselor creating a personalized action plan.

STRUGGLE: {struggle_label}
USER PROFILE: {persona} ({knowledge_level})

SCHOLARLY SOURCES AVAILABLE:
---
[Ihya Vol 3 Ch 5 excerpt — anger section]
[Ihya Vol 4 Ch 2 excerpt — patience section]
[Madarij patience station excerpt]
[Riyad hadith on patience]
---

RELEVANT QURAN VERSES:
3:134, 41:34, 42:37, 7:199, 3:159, 16:126

Generate a 4-week structured action plan with these EXACT sections:

1. MINDSET SHIFT (2-3 paragraphs from scholarly sources)
   - Root cause analysis from Ihya
   - Reframing from Madarij
   - Prophetic example from Riyad

2. WEEKLY ACTION FRAMEWORK (4 weeks, progressive)
   Week 1: Awareness (recognize the pattern)
   Week 2: Intervention (prophetic responses)
   Week 3: Replacement (new habit formation)
   Week 4: Deepening (spiritual transformation)
   Each week: focus area, 2-3 specific actions, one Quranic verse, one hadith

3. ENVIRONMENTAL ADJUSTMENTS (3-5 practical changes)

4. HABIT ANCHORS (3 if-then rules in habit stacking format)
   Format: "After [trigger], I will [response]"
   Each grounded in Prophetic sunnah

5. REFLECTION VERSES (4 verses with tadabbur prompts)
   Each prompt must be specific to anger, not generic

6. WEEKLY JOURNAL PROMPTS (4 prompts, one per week)
   Progressive: awareness → intervention → reflection → transformation

CONSTRAINTS:
- Vocabulary: {persona_vocabulary}
- Tone: compassionate, never legalistic, never shaming
- All claims grounded in provided scholarly sources
- Practical and actionable, not theoretical
```

### Phase 4: Behavior Linking

```
For struggle "anger":
  Auto-create tracked behaviors:
    - anger_incidents (count_inv): "How many times did anger overtake you today?"
    - wudu_response (binary): "Did you make wudu when angry?"
    - forgiveness_practice (binary): "Did you consciously choose to forgive someone?"
    - patience_verse (binary): "Did you read/recite your patience verse?"

  Link to existing behaviors:
    - dhikr_minutes (already tracked): dhikr is the primary prophetic anger remedy
    - sleep_hours (already tracked): sleep deprivation is a known anger trigger

  Feed into Iman Index:
    - anger_incidents → tawbah category (count_inv — fewer = better)
    - wudu_response → tawbah category (binary)
    - forgiveness_practice → character category (binary)
```

### Struggle Resolution & Progression

```
After 30 days:
  Evaluate:
    - anger_incidents trend (declining?)
    - wudu_response consistency (increasing?)
    - forgiveness_practice adoption (forming?)

  If positive trend:
    "Your anger incidents have declined 60% over 30 days. Your wudu-response
     habit is becoming second nature (logged 22 of 30 days). Al-Ghazali writes:
     'The fire of anger is quenched by the water of wudu and the water of knowledge.'
     You're living both.

     Ready for Phase 2? We can shift focus from anger management to proactive hilm
     (forbearance) — the positive virtue that replaces the void anger leaves."

  If struggling:
    "Anger is one of the hardest struggles. The Prophet ﷺ was asked for advice
     and repeated three times: 'Don't be angry.' The repetition itself tells us
     this requires persistence.

     Let's adjust your plan:
     - Would a different trigger response help? (currently: wudu)
     - Is there an environmental change we haven't tried?
     - Would you like to revisit Al-Ghazali's root-cause analysis?"
```

### Pre-Indexed Struggle → Source Mapping

```python
STRUGGLE_SOURCE_MAP = {
    "anger": {
        "problem": ["ihya:vol=3:ch=5"],
        "antidote": ["ihya:vol=4:ch=2", "madarij:vol=2:station=patience"],
        "hadith": ["riyad:book=1:ch=3"],
        "verses": [(3,134), (41,34), (42,37), (7,199), (3,159)],
        "behaviors": ["anger_incidents:count_inv", "wudu_response:binary", "forgiveness_practice:binary"]
    },
    "lowering_gaze": {
        "problem": ["ihya:vol=3:ch=3"],          # GREED FOR FOOD SEXUAL PASSION
        "antidote": ["ihya:vol=4:ch=3", "madarij:vol=2:station=fear"],
        "hadith": ["riyad:book=1:ch=6"],          # Taqwa
        "verses": [(24,30), (24,31), (33,35), (17,32), (23,5)],
        "behaviors": ["lowering_gaze:scale_5", "device_discipline:scale_5"]
    },
    "prayer_consistency": {
        "problem": ["ihya:vol=3:ch=6"],           # ATTACHMENT OF THE WORLD
        "antidote": ["ihya:vol=1:ch=4"],          # PRAYER
        "hadith": ["riyad:book=1:ch=1"],          # Sincerity
        "verses": [(2,238), (4,103), (29,45), (20,14), (19,59)],
        "behaviors": ["fajr_prayer:binary", "masjid_attendance:binary"]
    },
    "pride": {
        "problem": ["ihya:vol=3:ch=9"],           # PRIDE AND SELF-PRAISE
        "antidote": ["madarij:vol=2:station=humility", "ihya:vol=4:ch=4"],
        "hadith": ["riyad:book=1:ch=5"],
        "verses": [(31,18), (17,37), (28,76), (4,36), (57,23)],
        "behaviors": ["gratitude_entry:binary", "kindness_act:binary"]
    },
    "backbiting": {
        "problem": ["ihya:vol=3:ch=4"],           # HARMS OF TONGUE
        "antidote": ["ihya:vol=4:ch=1", "madarij:vol=1:station=repentance"],
        "hadith": ["riyad:book=1:ch=4"],          # Truthfulness
        "verses": [(49,12), (104,1), (68,11), (24,19), (33,70)],
        "behaviors": ["tongue_control:scale_5", "tawbah_moment:binary"]
    },
    "greed_materialism": {
        "problem": ["ihya:vol=3:ch=7"],           # LOVE FOR WEALTH
        "antidote": ["ihya:vol=4:ch=4", "madarij:vol=2:station=joyful_contentment"],
        "hadith": ["riyad:book=1:ch=6"],          # Piety
        "verses": [(102,1), (3,14), (57,20), (9,34), (64,15)],
        "behaviors": ["charity:binary", "gratitude_entry:binary"]
    },
    "spiritual_dryness": {
        "problem": ["ihya:vol=3:ch=1"],           # SOUL AND ITS ATTRIBUTES
        "antidote": ["ihya:vol=4:ch=6", "madarij:vol=1:station=awakening"],
        "hadith": ["riyad:book=1:ch=2"],          # Repentance
        "verses": [(13,28), (39,22), (57,16), (2,186), (50,16)],
        "behaviors": ["quran_minutes:minutes", "dhikr_minutes:minutes", "heart_notes:count"]
    },
    "anxiety": {
        "problem": ["ihya:vol=3:ch=1"],
        "antidote": ["ihya:vol=4:ch=5", "madarij:vol=2:station=trusting_reliance"],
        "hadith": ["riyad:book=1:ch=3"],
        "verses": [(94,5), (2,286), (65,3), (3,173), (39,53)],
        "behaviors": ["dua_moments:count", "dhikr_minutes:minutes", "sleep_hours:hours"]
    },
    "laziness": {
        "problem": ["ihya:vol=3:ch=6"],           # ATTACHMENT OF THE WORLD
        "antidote": ["madarij:vol=1:station=purpose", "ihya:vol=4:ch=7"],
        "hadith": ["riyad:book=1:ch=1"],
        "verses": [(9,38), (62,9), (3,200), (29,69), (53,39)],
        "behaviors": ["exercise:binary", "sunnah_prayers:count", "quran_minutes:minutes"]
    },
    "hypocrisy_showing_off": {
        "problem": ["ihya:vol=3:ch=8"],           # LOVE OF POWER AND SHOW
        "antidote": ["ihya:vol=4:ch=7", "madarij:vol=1:station=insight"],
        "hadith": ["riyad:book=1:ch=1"],          # Sincerity (niyyah)
        "verses": [(4,142), (107,4), (2,264), (18,110), (98,5)],
        "behaviors": ["tawbah_moment:binary"]
    }
}
```

---

## LAYER 3: Spiritual State Awareness

### A. Islamic Calendar Integration

The app must be aware of the Islamic calendar to shift its entire posture — not just verse selection, but coaching tone, behavior expectations, and recommendations.

**Calendar Events & System Behavior:**

```
┌──────────────────────┬──────────────────────────────────────────────────────────────┐
│ PERIOD               │ SYSTEM BEHAVIOR                                              │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ Ramadan (full month) │ • Enable fasting behavior (auto-ON)                          │
│                      │ • Add tarawih tracking behavior                              │
│                      │ • Shift daily verse pool to fasting/taqwa/Quran verses       │
│                      │ • Coaching tone: intensified spiritual focus                  │
│                      │ • Strain threshold raised: high strain is EXPECTED            │
│                      │ • Recovery emphasis: "iftar nourishes body and soul"          │
│                      │ • Suggest ramadan_30 reading plan                             │
│                      │ • Weekly digest references Ihya Vol 1 Ch 6 (FASTING)         │
│                      │ • Last 10 nights: special mode — tahajjud/i'tikaf tracking   │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ Dhul Hijjah 1-10     │ • Emphasize first 10 days as "best days of the year"         │
│                      │ • Shift verses to Ibrahim/sacrifice/hajj themes              │
│                      │ • Add extra fasting behavior suggestion (especially Day 9)   │
│                      │ • Dhikr emphasis: "Days in which good deeds are most beloved" │
│                      │ • Coaching references sacrifice, submission, tawakkul         │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ Muharram / Ashura    │ • Suggest fasting on 9th & 10th                              │
│                      │ • Verses on perseverance, Musa's story                       │
│                      │ • Reflection on new Islamic year: "Where are you headed?"    │
│                      │ • Coaching: annual muhasaba (self-accounting)                │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ Rajab & Sha'ban      │ • Pre-Ramadan preparation mode                               │
│                      │ • Suggest ramadan_prep_7 reading plan                         │
│                      │ • "The Prophet ﷺ fasted most in Sha'ban" — fasting emphasis  │
│                      │ • Gradual intensity increase toward Ramadan readiness        │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ Every Friday         │ • Surah Al-Kahf recommendation                               │
│                      │ • Weekly Spiritual Digest generated & delivered               │
│                      │ • Special salawat/dua emphasis                               │
│                      │ • Coaching: "The best day the sun rises on" (Muslim)         │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ White Days           │ • Suggest fasting (13th, 14th, 15th of lunar month)          │
│ (Ayyam al-Bid)      │ • "The Prophet ﷺ used to fast three days every month"        │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ Monday & Thursday    │ • Highlight sunnah fasting opportunity                        │
│                      │ • "Deeds are presented on Monday and Thursday" (Tirmidhi)    │
└──────────────────────┴──────────────────────────────────────────────────────────────┘
```

**Implementation:**
```python
# Use Hijri calendar library (e.g., hijri-converter)
from hijri_converter import Hijri, Gregorian

def get_islamic_context(date):
    hijri = Gregorian(date.year, date.month, date.day).to_hijri()

    context = {
        "hijri_date": f"{hijri.day} {hijri.month_name()} {hijri.year}",
        "is_ramadan": hijri.month == 9,
        "is_dhul_hijjah_10": hijri.month == 12 and hijri.day <= 10,
        "is_muharram": hijri.month == 1,
        "is_ashura": hijri.month == 1 and hijri.day in [9, 10],
        "is_rajab": hijri.month == 7,
        "is_shaban": hijri.month == 8,
        "is_white_day": hijri.day in [13, 14, 15],
        "is_friday": date.weekday() == 4,
        "is_monday": date.weekday() == 0,
        "is_thursday": date.weekday() == 3,
        "ramadan_night": hijri.month == 9 and hijri.day >= 21,  # last 10 nights
    }
    return context
```

### B. Time-of-Day Awareness

```
┌──────────────┬────────────────────────────────────────────────────────────┐
│ TIME WINDOW  │ SPIRITUAL POSTURE                                          │
├──────────────┼────────────────────────────────────────────────────────────┤
│ Pre-Fajr     │ "The quiet before dawn. You're awake when most sleep."     │
│ (4am-Fajr)   │ Verses: Night prayer, closeness to Allah, tahajjud         │
│              │ Tone: Intimate, hushed, sacred                             │
│              │ Ihya ref: Vol 1 Ch 9 (ZIKR AND INVOCATIONS)               │
├──────────────┼────────────────────────────────────────────────────────────┤
│ Post-Fajr    │ "A new day — a new chance from Allah."                     │
│ (Fajr-9am)   │ Verses: New beginnings, morning adhkar, provision          │
│              │ Tone: Fresh, hopeful, energizing                           │
│              │ Quran: Morning recitation emphasis                         │
├──────────────┼────────────────────────────────────────────────────────────┤
│ Midday       │ "The world pulls — stay anchored."                         │
│ (9am-Asr)    │ Verses: Patience in daily life, halal earning, steadfast   │
│              │ Tone: Grounding, steadying                                 │
│              │ Ihya ref: Vol 2 (worldly usages)                           │
├──────────────┼────────────────────────────────────────────────────────────┤
│ Evening      │ "The day is ending. What did it hold?"                     │
│ (Maghrib-    │ Verses: Gratitude, reflection, evening adhkar              │
│  Isha)       │ Tone: Reflective, grateful, gentle                        │
│              │ Action: Evening muhasaba journal prompt                    │
├──────────────┼────────────────────────────────────────────────────────────┤
│ Late Night   │ "The world is quiet. You and Allah."                       │
│ (After Isha) │ Verses: Tawbah, hope, mercy, night of Qadr               │
│              │ Tone: Deeply personal, intimate                            │
│              │ Madarij ref: Station of grief, fear, hope                  │
└──────────────┴────────────────────────────────────────────────────────────┘
```

### C. Emotional Context (Opt-In Heart States)

```
User selects: "How is your heart today?"

┌──────────────┬────────────────────────────────────────────────────────────────┐
│ HEART STATE  │ SYSTEM RESPONSE                                                │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Grateful     │ Verse: 14:7 — "If you are grateful, I will increase you"      │
│ (shukr)      │ Scholar: Ihya Vol 4 Ch 2 (gratitude section)                  │
│              │ Insight: "Gratitude is not just feeling — Al-Ghazali says it   │
│              │  has three pillars: knowledge, state, and action."             │
│              │ Action: "Write what you're grateful for in a Heart Note."      │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Anxious      │ Verse: 65:3 — "Whoever relies on Allah, He is sufficient"     │
│ (qalaq)      │ Scholar: Ihya Vol 4 Ch 5 (TAUHID AND TAWAKKAL)               │
│              │ Madarij: Station of trusting reliance                          │
│              │ Insight: "Anxiety often means we're carrying what belongs to   │
│              │  Allah. Tawakkul is not passivity — it's active surrender."    │
│              │ Action: "Name your worry, then say: HasbiyAllahu wa ni'mal     │
│              │  wakeel. Write it down and release it."                        │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Grieving     │ Verse: 94:5-6 — "Verily, with hardship comes ease"           │
│ (huzn)       │ Scholar: Madarij Vol 2, Station of Grief                      │
│              │ Insight: "Ibn Qayyim distinguishes between grief that          │
│              │  paralyzes and grief that purifies. The latter draws you       │
│              │  closer to Allah."                                             │
│              │ Action: "Let yourself feel. Then open your hands and make      │
│              │  dua — even if you have no words, the tears are enough."       │
│              │ Riyad: Hadith on the Prophet ﷺ weeping for his son Ibrahim    │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Spiritually  │ Verse: 57:16 — "Has the time not come for believers' hearts   │
│ Dry          │  to be humbled by Allah's remembrance?"                        │
│ (qasawah)    │ Scholar: Ihya Vol 3 Ch 1 (SOUL AND ITS ATTRIBUTES)           │
│              │ Madarij: Station of Awakening                                  │
│              │ Insight: "Spiritual dryness is itself a form of awareness.     │
│              │  The fact that you notice the distance means your heart        │
│              │  still remembers closeness."                                   │
│              │ Action: "Don't try to force a spiritual high. Read one verse   │
│              │  slowly. Let it sit. The rain comes when Allah wills."         │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Joyful       │ Verse: 10:58 — "In the bounty of Allah and His mercy, in     │
│ (farah)      │  that let them rejoice"                                        │
│              │ Scholar: Ihya Vol 4 Ch 2 (gratitude section)                  │
│              │ Insight: "Joy is a blessing that carries responsibility.       │
│              │  Al-Ghazali warns: don't let ease make you forget the Giver." │
│              │ Action: "Capture this moment in a Heart Note. Share the joy    │
│              │  through sadaqah — generosity in joy multiplies it."           │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Seeking      │ Verse: 2:186 — "When My servants ask about Me, I am near"    │
│ Guidance     │ Scholar: Ihya Vol 4 Ch 8 (MEDITATION AND INTROSPECTION)       │
│ (istikhara)  │ Insight: "Seeking guidance is itself guided. The one who      │
│              │  turns to Allah for direction has already taken the first      │
│              │  step."                                                        │
│              │ Action: "Pray istikhara. Then take a step — tawakkul means    │
│              │  trusting the outcome to Allah after you've done your part."   │
│              │ Riyad: Hadith on istikhara dua                                │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Remorseful   │ Verse: 39:53 — "Despair not of the mercy of Allah"           │
│ (nadam)      │ Scholar: Ihya Vol 4 Ch 1 (TAUBA / REPENTANCE)               │
│              │ Madarij: Station of Repentance                                │
│              │ Insight: "The Prophet ﷺ said: 'Remorse IS repentance.'        │
│              │  The pain you feel is the door opening, not closing."          │
│              │ Action: "Make wudu. Pray 2 raka'at of tawbah. Then let go —   │
│              │  Allah's forgiveness is greater than any sin."                 │
└──────────────┴────────────────────────────────────────────────────────────────┘
```

### D. Heart Notes System (Layer 3b)

**Quick Spiritual Capture — Minimal Friction:**

```
Types (one-tap selection):
  🤲  Making dua        → auto-tag: "dua"
  🌙  Night reflection   → auto-tag: "qiyam", "night"
  💚  Moment of connection → auto-tag: "connection"
  🙏  Seeking forgiveness → auto-tag: "tawbah", "istighfar"
  ☀️  Gratitude          → auto-tag: "shukr"
  📖  Quran insight      → auto-tag: "quran", "tadabbur"

Optional free-text: max 280 chars (tweet-length — keep it quick)

Storage: Encrypted, appended to daily log's heart_notes array
```

**Pattern Detection from Heart Notes:**

```
After 14+ days of Heart Notes:

Temporal Patterns:
  "Your gratitude entries peak on Fridays and after Fajr — a beautiful rhythm."
  "Your dua moments are concentrated in late evening — you seek Allah most when the world quiets."
  "Tawbah entries cluster on Monday mornings — that's powerful self-awareness."

Emotional Arcs:
  "This week: 3 gratitude notes, 2 connection moments, 1 tawbah.
   Last week: 4 tawbah entries, 1 anxiety-related dua.
   Your heart is shifting from heaviness toward lightness. SubhanAllah."

Correlation with Behaviors:
  "Days with Heart Notes show 25% higher overall behavioral scores.
   The act of capturing a spiritual moment may itself be an act of worship."
```

---

## LAYER 6: AI Coaching Layer

### Weekly Spiritual Digest (Generated Every Friday)

**Input Data for Gemini:**

```python
digest_context = {
    "user_profile": { "persona", "knowledge_level", "learning_goal" },
    "week_behaviors": {
        # 7 days of daily_c(t) per category
        "fard": [0.8, 1.0, 1.0, 0.6, 1.0, 0.8, 1.0],
        "tawbah": [0.6, 0.7, 0.5, 0.8, 0.7, 0.6, 0.7],
        # ... all categories
    },
    "trajectory": "ascending",
    "volatility": "stable",
    "top_correlations": [
        {"a": "sleep_hours", "b": "fajr_prayer", "r": 0.78, "insight": "..."}
    ],
    "identity_statements": [
        {"statement": "...", "reinforcement_days": 12, "level": "forming"}
    ],
    "active_struggles": [
        {"label": "anger", "trend": "improving", "incidents_this_week": 2, "last_week": 4}
    ],
    "heart_notes_summary": {
        "count": 5, "types": {"gratitude": 3, "dua": 1, "tawbah": 1},
        "temporal_pattern": "most entries after Fajr"
    },
    "islamic_context": {
        "hijri_date": "3 Sha'ban 1447",
        "is_friday": True,
        "upcoming": "Ramadan in 27 days"
    },
    "exploration_this_week": {
        "verses_explored": 8,
        "reflections_written": 3,
        "scholarly_sources_engaged": ["ihya:vol=4:ch=2"]
    },
    "strain_recovery": {
        "avg_strain": 0.65,
        "avg_recovery": 0.72,
        "ratio": 0.90,
        "status": "balanced"
    }
}
```

**Gemini Prompt for Weekly Digest:**

```
You are a wise, gentle spiritual companion. You speak like a caring mentor
who has been walking beside this person all week. You are NOT a robot,
NOT a preacher, NOT a judge.

Generate a weekly spiritual digest based on this data.
Persona: {persona_name} ({knowledge_level})

STRUCTURE (follow exactly):

1. OPENING (2 sentences)
   - Warm, personal greeting referencing specific data from their week
   - Must reference something SPECIFIC they did, not generic

2. THIS WEEK'S STORY (3-4 sentences)
   - Narrative arc of their week using behavioral data
   - Highlight the most notable pattern or shift
   - Reference Islamic calendar context if relevant

3. WHAT I NOTICED (2-3 bullet points)
   - One strength they showed (with data evidence)
   - One correlation insight (behavioral pattern)
   - One area of gentle attention (never phrased as failure)

4. YOUR IDENTITY IS FORMING (1-2 sentences)
   - Reference their active identity statements
   - Show evidence from their behavior data
   - Reinforcement, not judgment

5. STRUGGLE UPDATE (if active struggles, 1-2 sentences)
   - Progress narrative (trend-based, not absolute)
   - One scholarly reference tied to their specific struggle

6. A VERSE TO CARRY (1 verse + 1 sentence of personal connection)
   - Must be relevant to their week's themes
   - Explain WHY this verse connects to THEIR specific experience

7. HUMILITY CLOSE (1 sentence)
   - Rotate between: "Allah knows what metrics cannot measure",
     "The unseen is vaster than what we track",
     "Your sincerity is between you and Allah alone"

CONSTRAINTS:
- Max 300 words total
- Never use the word "score" or "index" or "metric"
- Never compare to other users
- Never use "you should" — use "you might consider" or "what if"
- Vocabulary: {persona_vocabulary}
- If trajectory is "recalibrating": lead with compassion, not prescription
- If strain > recovery for 5+ days: emphasize rest, not effort
- Always end with the humility close
```

**Example Generated Digest:**

```
Assalamu alaykum. This was a week of quiet strength.

You showed up for all five prayers on 5 out of 7 days — and on the two days
you missed Asr, you still prayed the other four. That's not failure; that's a
human being in the middle of life.

What I noticed:
• Your dhikr practice was the most consistent thing this week — 10+ minutes
  every single day. That steadiness is rare and beautiful.
• When you slept 7+ hours, your Fajr was 100%. Below 6 hours, it dropped to
  50%. Your body and spirit are deeply connected.
• Your Quran time dipped mid-week. Even 5 minutes of tadabbur counts — it's
  the connection that matters, not the minutes.

Your identity — "I am someone who begins the day with Allah" — has 12 days of
evidence now. You're not just doing morning dhikr; you're becoming someone who
does morning dhikr. There's a difference.

Your anger work is progressing: 2 incidents this week, down from 4. You used
your wudu-response 3 times. Al-Ghazali writes that the water of wudu and the
water of patience together extinguish the fire of anger.

Carry this verse with you: "And those who strive for Us — We will surely guide
them to Our ways" (29:69). You ARE striving. The guidance is already at work.

What lies beyond our awareness belongs to Allah alone.
```

### Micro-Adjustment Suggestions

Beyond weekly digests, the coaching layer makes small, timely suggestions:

```
Trigger: User has logged 5+ days of data this week
Logic: Identify ONE micro-adjustment with highest potential impact

Examples:

  If sleep_hours < 6 and fajr_consistency < 50%:
    "Quick thought: your Fajr and sleep are closely linked. What if you
     moved bedtime 30 minutes earlier this week? Just 30 minutes."

  If dhikr_minutes > 0 every day but quran_minutes == 0 for 3 days:
    "You never miss dhikr — mashAllah. What if you added just 3 minutes
     of Quran right after? Your dhikr momentum could carry into recitation."

  If charity never logged but gratitude_entry consistent:
    "Your gratitude practice is beautiful. What if you let that gratitude
     flow outward? Even $1 of sadaqah turns gratitude into action."

  If all behaviors high but heart_notes count == 0:
    "Your actions are strong. But how's your heart? A quick Heart Note —
     even one word — helps you stay connected to the WHY behind the WHAT."
```

### Correlation Insight Delivery

```
Format: Simple, human-readable insight cards

"When you {do X}, your {Y} improves by {Z}%."

Rules:
  - Only surface correlations with |r| > 0.40 and p < 0.05
  - Max 1 correlation per week (don't overwhelm)
  - Prioritize cross-category correlations (more surprising/useful)
  - Frame as observation, not prescription
  - Always end with: "This is a pattern, not a rule. You know yourself best."
```

---

## LAYER 7: Safeguards & Theological Constraints

### This is the most important layer. Without it, the entire system becomes spiritually dangerous.

### A. Theological Risks & Mitigations

**Risk 1: Riya (Showing Off)**
The Ihya dedicates Vol 3 Ch 8 to this exact danger — tracking worship can breed self-consciousness before creation rather than consciousness of the Creator.

```
Mitigations:
  1. Score is NEVER public, NEVER shareable, NEVER on a leaderboard
  2. No social features connected to the Iman Index
  3. Periodic riya reminder (random, 1 in 10 journal sessions):
     "Reminder: This is between you and Allah alone. The Prophet ﷺ said:
      'The thing I fear most for my ummah is minor shirk — showing off.'
      (Ahmad). If tracking helps your sincerity, continue. If it breeds
      self-admiration, step back. Only you know."
  4. Export/share is NEVER offered for behavioral data
  5. No "achievement" notifications for behavioral streaks
     (different from existing Tadabbur badges which are exploration-based)
```

**Risk 2: Reducing Iman to Metrics**
Iman in Islamic theology is belief, speech, and action — it increases and decreases but encompasses the unseen (ghayb) dimension that no metric can capture.

```
Mitigations:
  1. PERMANENT header on dashboard: "A mirror, not a measure"
  2. The score is HIDDEN — only trajectory and qualitative states shown
  3. Weekly digest always ends with humility cue
  4. Onboarding disclaimer:
     "Iman is vast — it encompasses your belief, your heart, your actions,
      and dimensions only Allah can see. This tool tracks the visible actions
      you choose to monitor. It cannot measure the state of your heart,
      the sincerity of your intention, or your standing with Allah.
      Use it as a mirror for self-reflection, not as a verdict on your faith."
  5. "Allah Knows Best" badge — appears randomly, replacing the trajectory
     display for one session. Forces the user to sit with uncertainty.
```

**Risk 3: False Spiritual Confidence**
A user who sees "Ascending" might develop ujb (self-amazement).

```
Mitigations:
  1. Growth decay (Step 9): High scores naturally decay, preventing stagnation
  2. Baseline recalibration: As you improve, your baseline shifts up.
     "Ascending" requires continuous growth, not just maintaining.
  3. Random "Humility Reset" — once per month, instead of the trajectory:
     "Today, the Prophet ﷺ reminds you: 'None of you will enter Paradise
      by their deeds alone.' The trajectory is paused. Just be with Allah."
  4. When ascending for 30+ days, coaching includes:
     "Al-Ghazali warns in Ihya: 'Self-satisfaction is a poison sweeter
      than any sin.' Your growth is real — but it's a gift, not an
      achievement. Say: Alhamdulillah, this is from my Lord."
```

**Risk 4: Despair During "Recalibrating"**
A declining trajectory could trigger spiritual despair (ya's), which is itself a major sin.

```
Mitigations:
  1. The word "declining" is NEVER used. "Recalibrating" implies return, not fall.
  2. Coaching during recalibrating phase is WARM and SCRIPTURAL:
     - "The Prophet ﷺ said: 'Every son of Adam sins, and the best of sinners
        are those who repent.' (Tirmidhi)"
     - "Ibn Qayyim writes: 'The descent of the heart (qabd) is not punishment —
        it is preparation for the next ascent (bast).'"
  3. Recalibrating for 14+ days triggers special mode:
     - Temporarily hide trajectory indicator entirely
     - Replace with: "Your journey continues. Allah is closer than your jugular vein."
     - Reduce journal to just 3 behaviors (fard prayers + Quran + one nafl)
     - Coach: "Let's simplify. When the heart is heavy, do the minimum with
       maximum presence. Quality over quantity."
  4. Emergency override: If user selects "Grieving" or "Spiritually Dry"
     heart state for 7+ consecutive days:
     - Disable Iman Index entirely
     - Show only: "Your Lord has not forsaken you, nor has He become displeased. (93:3)"
     - Offer: "Would you like to pause tracking and just be? This tool should
       serve you, not burden you."
```

### B. Psychological Safeguards

**Risk 5: Scrupulosity (Waswasah / Religious OCD)**

Some users may become obsessively detailed in tracking, treating every minor slip as catastrophic.

```
Detection signals:
  - Logging 5+ times per day (re-editing entries)
  - Intention score always 1/5 (persistent self-condemnation)
  - All heart notes are tawbah/forgiveness type
  - Extremely high strain with extremely low self-assessment

Mitigations:
  1. If logging frequency > 3x per day for 5 days:
     "You're being very thorough — but gentleness with yourself is worship too.
      The Prophet ﷺ said: 'This religion is ease.' Log once in the evening.
      Trust that Allah sees your day even when you don't record it."

  2. If intention_score is always 1/5 for 14 days:
     "Being aware of shortcomings is a SIGN of sincerity, not evidence of failure.
      The fact that you care about your intention this deeply shows a living heart.
      Al-Ghazali writes: 'The one who worries about riya has already escaped
      the worst of it.'"

  3. If all heart notes are tawbah for 7+ days:
     "Your tawbah is beautiful — and Allah accepts it immediately. But He also
      wants you to experience His other names: Ar-Rahman, Al-Wadud, Al-Latif.
      Today, try a gratitude note instead. Let mercy balance repentance."

  4. Hard limit: Maximum 1 journal edit per day after initial submission
```

**Risk 6: Guilt Spirals**

Missing a day or breaking a streak could trigger excessive guilt.

```
Mitigations:
  1. Missing a day uses language: "Rest days are part of the journey.
     The Prophet ﷺ rested. You're human — that's by design."

  2. Streak breaks are NEVER highlighted. No "you broke your streak!" message.
     Instead: "Welcome back. Where would you like to pick up?"

  3. After 3+ missed days, returning user sees:
     "The best part of falling is the getting back up. You're here now.
      That's what matters. Shall we start gentle?"
     + Reduced journal (3 behaviors only for re-entry)

  4. The Iman Index does NOT tank after missed days:
     - Unlogged days are excluded for first 3 days (not counted as zero)
     - Only after 3+ consecutive unlogged days do they count as zero
     - Trajectory uses 14-day windows — one bad week doesn't erase a good month
```

**Risk 7: Burnout from Overcommitment**

User activates all 25 behaviors, tracks 10 struggles, writes 5 Heart Notes daily.

```
Mitigations:
  1. Onboarding limits:
     - Start with max 8 behaviors (fard + 3 optional)
     - Must track for 14 days before adding more
     - Max 3 active struggles at a time

  2. Strain/Recovery system (Layer 5) monitors burnout:
     - SR ratio > 2.0 for 7 days triggers intervention
     - Coach: "You're pushing beyond what sustains. What if we removed
       one tracked behavior this week? Depth over breadth."

  3. "Less is More" principle enforced:
     - When adding a new behavior: "Adding more can dilute focus.
       Are you sure you want to track this? Quality > quantity."
     - Quarterly review prompt: "You're tracking {N} behaviors.
       Which 3 have the most spiritual impact? Consider focusing there."

  4. Maximum tracked behaviors: 15 (hard cap)
     - Beyond this: "The Prophet ﷺ said: 'Take on only what you can sustain.'
       Let's focus on what matters most."
```

### C. Gamification Safeguards

```
  1. NO points, NO levels, NO ranks, NO leaderboards
  2. NO comparison to other users — ever
  3. Streaks are tracked but de-emphasized:
     - Streak count shown only on request, not as a prominent feature
     - Breaking a streak has NO negative consequence in the Index
     - "The streak is a tool, not a goal. If it helps, use it. If it pressures, ignore it."
  4. NO "compete with yourself" framing
     - Not "beat your best week" — instead "deepen your practice"
  5. Achievement language is spiritual, not competitive:
     - Not "Level Up!" — instead "A new station on your path"
     - Not "Personal Best!" — instead "A moment of growth, by Allah's grace"
```

### D. Data Privacy Safeguards

```
  1. All behavioral data encrypted at-rest (Fernet, same as annotations)
  2. Behavioral logs are MORE sensitive than annotations:
     - Prayer habits, sin avoidance, emotional states — this is deeply personal
     - Encryption key: HMAC-SHA256(IMAN_ENCRYPTION_SECRET, uid) — separate from annotation key
  3. NO behavioral data in analytics pipeline
  4. NO aggregate behavioral data collection (even anonymized)
  5. Complete data deletion on request:
     - "Delete my spiritual data" → wipe all iman_* subcollections
     - Confirmation required: "This will delete all your behavioral logs,
       baselines, digests, and struggle plans. This cannot be undone."
  6. NO third-party data sharing — ever
  7. Data export available in encrypted format only (user holds the key)
  8. Session timeout: behavioral dashboard requires re-authentication after 15 min
```

### E. Theological Review Board (Future)

```
For production deployment:
  - All AI-generated coaching narratives should be reviewed by qualified scholars
  - Pre-approved phrase bank for sensitive topics (tawbah, qadr, sin)
  - Scholarly advisory board for edge cases
  - User reporting mechanism for inappropriate AI responses
  - Regular audit of generated content for theological accuracy
```

---

## UX FLOWS

### Daily Flow (Evening Muhasaba — Primary Touchpoint)

```
┌─────────────────────────────────────────────────────────────────┐
│                    DAILY FLOW (~90 seconds)                      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. OPEN APP (any time)                                    │   │
│  │    → Time-aware greeting (Layer 3B)                       │   │
│  │    → Daily verse from existing system                     │   │
│  │    → If active reading plan: "Day N awaits"               │   │
│  │    → If unfinished thread: gentle nudge                   │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 ▼                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. USE TADABBUR (existing tafsir flow — unchanged)        │   │
│  │    → Explore verses, read tafsir, write annotations       │   │
│  │    → Auto-detect: tadabbur_session = true for the day     │   │
│  │    → Auto-detect: quran_minutes from session duration     │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 ▼                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 3. HEART NOTE (any time, zero friction)                   │   │
│  │    → Floating button: tap → select type → optional text   │   │
│  │    → Auto-logged to daily_logs with timestamp             │   │
│  │    → No interruption to current flow                      │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 ▼                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 4. EVENING MUHASABA (notification at Maghrib+1hr)         │   │
│  │    → Journal screen: log today's behaviors (<90 sec)      │   │
│  │    → Optional: heart state selection                      │   │
│  │    → Optional: intention self-report (1-5)                │   │
│  │    → Save → immediate feedback:                           │   │
│  │      "Logged. [trajectory arrow] [qualitative state]"     │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 ▼                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 5. POST-LOG INSIGHT (if available, <15 seconds)           │   │
│  │    → One micro-insight if correlation detected            │   │
│  │    → Or: identity reinforcement message                   │   │
│  │    → Or: struggle progress update                         │   │
│  │    → Or: nothing (don't force content)                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Total daily touchpoints: 1-3 (journal is the only "required")  │
│  Total daily time: 90 seconds (journal) + existing app usage    │
└─────────────────────────────────────────────────────────────────┘
```

### Weekly Flow (Jumu'ah — Reflection Touchpoint)

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEEKLY FLOW (every Friday)                    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. FRIDAY NOTIFICATION (after Jumu'ah)                    │   │
│  │    "Your weekly spiritual digest is ready."               │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 ▼                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. WEEKLY DIGEST SCREEN                                   │   │
│  │    ┌───────────────────────────────────────────────┐      │   │
│  │    │  "A mirror, not a measure"                     │      │   │
│  │    │                                                │      │   │
│  │    │  Trajectory: ↗ Ascending & Stable              │      │   │
│  │    │                                                │      │   │
│  │    │  ┌─ Strain ████████░░ ─┐                       │      │   │
│  │    │  └─ Recovery █████████░ ┘  Balanced             │      │   │
│  │    │                                                │      │   │
│  │    │  [AI Narrative — 300 words]                     │      │   │
│  │    │                                                │      │   │
│  │    │  This Week's Insight:                          │      │   │
│  │    │  "Sleep 7+h → Fajr 95%. < 6h → Fajr 45%"      │      │   │
│  │    │                                                │      │   │
│  │    │  Identity Check:                               │      │   │
│  │    │  "I begin the day with Allah" — 12 days strong │      │   │
│  │    │                                                │      │   │
│  │    │  Verse to Carry: 29:69                         │      │   │
│  │    │  "Those who strive for Us..."                  │      │   │
│  │    │                                                │      │   │
│  │    │  ─ Allah knows what metrics cannot measure ─   │      │   │
│  │    └───────────────────────────────────────────────┘      │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 ▼                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 3. OPTIONAL ACTIONS                                       │   │
│  │    → Review/adjust tracked behaviors                      │   │
│  │    → Read the prescribed verse (links to Tadabbur)        │   │
│  │    → Explore the scholarly connection (links to source)    │   │
│  │    → Write a reflection on the week                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Behind the scenes (Friday computation):                         │
│  → Compute weekly category scores                               │
│  → Run correlation analysis (30-day window)                     │
│  → Detect trend shifts (CUSUM)                                  │
│  → Generate digest via Gemini                                   │
│  → Check baseline recalibration (if 30-day mark)                │
│  → Check weight recalibration (if locked-in categories)         │
│  → Store digest in iman_weekly_digests/{week_id}                │
└─────────────────────────────────────────────────────────────────┘
```

### Monthly Flow (Deep Reflection)

```
┌─────────────────────────────────────────────────────────────────┐
│                    MONTHLY FLOW (1st of each month)              │
│                                                                  │
│  1. MONTHLY REFLECTION PROMPT                                    │
│     "A month has passed. Let's look at the bigger picture."      │
│                                                                  │
│  2. MONTHLY REPORT (Gemini-generated, deeper than weekly)        │
│     → Theme evolution: "What topics occupied your heart?"         │
│     → Category trend lines (30-day view per category)            │
│     → Baseline recalibration notice:                             │
│       "Your baseline shifted up. What was once growth is now     │
│        your normal. MashAllah — that's how transformation works."│
│     → Struggle plan progress (if active)                         │
│     → Reading plan progress                                      │
│     → Heart Notes pattern analysis                               │
│     → "Your Tadabbur Story" narrative excerpt                    │
│                                                                  │
│  3. RECALIBRATION                                                │
│     → Baselines updated (EMA: 0.7 old + 0.3 new)                │
│     → Weights rechecked for locked-in categories                 │
│     → Growth edges re-identified                                 │
│     → Plateau check (21-day flat detection)                      │
│                                                                  │
│  4. QUARTERLY REVIEW (every 3 months)                            │
│     → Full "Your Tadabbur Story" narrative                       │
│     → Persona upgrade suggestion if warranted                    │
│     → Behavior set review: "Are you tracking the right things?"  │
│     → Struggle resolution check: "Is this still your struggle?"  │
└─────────────────────────────────────────────────────────────────┘
```

### Seasonal Flow (Islamic Calendar Events)

```
┌─────────────────────────────────────────────────────────────────┐
│               SEASONAL FLOW (Islamic Calendar)                   │
│                                                                  │
│  RAMADAN (30 days):                                              │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Day 1: "Ramadan Mubarak" special onboarding               │  │
│  │  → Auto-enable fasting behavior                            │  │
│  │  → Suggest tarawih tracking                                │  │
│  │  → Shift daily verse pool to Ramadan verses                │  │
│  │  → Suggest ramadan_30 plan (if not already active)         │  │
│  │  → Adjust strain expectations: high strain is expected     │  │
│  │                                                            │  │
│  │ Daily: Ramadan-specific journal additions                  │  │
│  │  → "How was your fast today?" (quality, not just binary)   │  │
│  │  → Tarawih attendance                                      │  │
│  │  → Quran khatmah progress (optional page/juz tracker)      │  │
│  │  → Iftar charity                                           │  │
│  │                                                            │  │
│  │ Last 10 Nights: Intensified mode                           │  │
│  │  → Tahajjud/Qiyam emphasis                                 │  │
│  │  → Laylat al-Qadr awareness                                │  │
│  │  → "The Prophet would tighten his belt, stay up            │  │
│  │     through the night, and wake his family"                 │  │
│  │                                                            │  │
│  │ Eid: Special digest — "Your Ramadan Journey"               │  │
│  │  → Full month narrative summary                            │  │
│  │  → "How to carry Ramadan forward"                          │  │
│  │  → Transition guidance (post-Ramadan is a known dip)       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  POST-RAMADAN (Shawwal):                                         │
│  → Anticipate the "Ramadan drop" — coach proactively            │
│  → "The real test isn't Ramadan — it's what comes after."        │
│  → Suggest 6 days of Shawwal fasting                             │
│  → Reduce behavior expectations temporarily (gentle re-entry)    │
│  → If trajectory dips: "This is normal. Every Ramadan graduate   │
│    experiences this. The habits you built are still in you."     │
│                                                                  │
│  DHUL HIJJAH 1-10:                                               │
│  → "The best days of the year" mode                              │
│  → Emphasize: fasting (esp Day 9), dhikr, charity, takbeer      │
│  → Verse pool: Ibrahim, sacrifice, submission, Hajj              │
│  → Day 10 (Eid al-Adha): "What are you willing to sacrifice      │
│    for Allah? Not a sheep — a habit, an attachment, a fear."     │
└─────────────────────────────────────────────────────────────────┘
```

### Onboarding Flow (First Time Setup)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ONBOARDING FLOW                               │
│                                                                  │
│  SCREEN 1: INTRODUCTION                                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  "Tadabbur's Spiritual Companion"                          │  │
│  │                                                            │  │
│  │  This is a private space for self-reflection.              │  │
│  │                                                            │  │
│  │  It is NOT a score. NOT a judgment. NOT a competition.     │  │
│  │                                                            │  │
│  │  It is a mirror — to help you see patterns in your own     │  │
│  │  journey and grow at YOUR pace, relative to YOUR baseline. │  │
│  │                                                            │  │
│  │  "Take account of yourselves before you are taken to       │  │
│  │   account." — Umar ibn al-Khattab                          │  │
│  │                                                            │  │
│  │  Iman cannot be reduced to metrics. What you track here    │  │
│  │  is the visible dimension of your practice. The rest       │  │
│  │  belongs to Allah alone.                                   │  │
│  │                                                            │  │
│  │                    [Begin Setup]                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  SCREEN 2: SELECT BEHAVIORS (checkboxes, defaults pre-set)       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  "What would you like to be mindful of?"                   │  │
│  │                                                            │  │
│  │  Prayer (required for fard):                               │  │
│  │  [x] 5 daily prayers   [ ] Masjid attendance              │  │
│  │                                                            │  │
│  │  Quran:                                                    │  │
│  │  [x] Quran recitation  [x] Tadabbur session (auto)        │  │
│  │                                                            │  │
│  │  Guarding:                                                 │  │
│  │  [x] Avoided sins      [x] Sought forgiveness             │  │
│  │  [ ] Lowering gaze     [ ] Device discipline              │  │
│  │                                                            │  │
│  │  Voluntary:                                                │  │
│  │  [x] Sunnah prayers    [x] Dhikr    [ ] Tahajjud         │  │
│  │                                                            │  │
│  │  Character:                                                │  │
│  │  [x] Gratitude entry   [ ] Act of kindness                │  │
│  │                                                            │  │
│  │  Body:                                                     │  │
│  │  [x] Sleep duration    [ ] Exercise                       │  │
│  │                                                            │  │
│  │  Start with 6-10. Add more after 14 days.                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  SCREEN 3: SET IDENTITY (select 1-3 statements)                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  "Who do you want to become?"                              │  │
│  │                                                            │  │
│  │  [Identity template cards — grouped by category]           │  │
│  │                                                            │  │
│  │  Or write your own:                                        │  │
│  │  "I am someone who ________________________________"       │  │
│  │                                                            │  │
│  │  Start with 1-2. These evolve over time.                  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  SCREEN 4: DECLARE STRUGGLES (optional)                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  "What are you working on?"                                │  │
│  │                                                            │  │
│  │  [ ] Anger         [ ] Lowering gaze    [ ] Prayer        │  │
│  │  [ ] Pride         [ ] Backbiting       [ ] Laziness      │  │
│  │  [ ] Materialism   [ ] Anxiety          [ ] Dryness       │  │
│  │                                                            │  │
│  │  We'll create a plan from Ihya, Madarij, and Riyad.       │  │
│  │                                                            │  │
│  │  [Skip for now]          [Continue with struggles]         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  SCREEN 5: CALIBRATION PERIOD                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  "Your journey begins with 14 days of honest logging."     │  │
│  │                                                            │  │
│  │  Don't try to be perfect. This establishes YOUR baseline.  │  │
│  │  After 14 days, your Spiritual Companion activates.        │  │
│  │                                                            │  │
│  │                    [Start Day 1]                            │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Adaptive Persona Progression

### Spiritual Maturity Detection (Internal — Never Shown)

```
Maturity Dimensions (computed from Iman Index + existing Tadabbur data):

1. BREADTH = (surahs_touched / 114) * 0.4 + (total_verses / 6236) * 0.6

2. DEPTH = (
     scholarly_source_engagements * 0.3 +
     avg_reflection_length_norm * 0.2 +
     verse_revisit_ratio * 0.3 +
     question_type_reflection_ratio * 0.2
   )

3. CONSISTENCY = (
     K_fard * 0.4 +
     streak_longest / 90 * 0.3 +
     journal_logging_rate * 0.3
   )

4. CURIOSITY = (
     unique_struggles * 0.3 +
     theme_diversity * 0.3 +
     source_diversity * 0.4
   )

5. INTEGRATION = (
     application_reflections * 0.4 +
     heart_notes_frequency * 0.3 +
     behavior_improvement_trends * 0.3
   )
```

### Persona Upgrade Thresholds

```
new_revert (composite > 0.35 for 4 weeks)        → curious_explorer
curious_explorer (composite > 0.50 for 4 weeks)   → practicing_muslim
practicing_muslim (composite > 0.65 for 4 weeks)  → student
student (composite > 0.80 for 4 weeks)            → advanced_learner
```

Upgrade is ALWAYS an invitation, never forced. User can decline or revert at any time.

### Regression Awareness

```
After 30+ days inactive:
  → Hide trajectory. Show: "Welcome back. Your journey is always here."
  → Reduce journal to 3 behaviors for re-entry week
  → Recalibrate baseline after 14 days of re-engagement

Explicit persona downgrade:
  → Respect immediately. "Sometimes we need gentleness, not depth."
  → No re-upgrade suggestion for 60 days

Engagement drops 50%+ for 14 days:
  → "Life has seasons. Would you like to simplify?"
  → Offer essentials mode: 5 prayers + 1 nafl only
```

---

## Integration with Existing Tadabbur Systems

### What Stays Unchanged
- All existing pages, components, flows
- Existing badges, streaks, collections, reading plans
- Tafsir generation, scholarly pipeline, annotations

### New Backend Endpoints

```
POST   /iman/setup               → Initialize config
GET    /iman/config              → Get behaviors, identities, struggles
PUT    /iman/config              → Update config

POST   /iman/log                 → Submit daily behavioral log
GET    /iman/log/{date}          → Get specific day's log
GET    /iman/logs?from=&to=      → Get date range

GET    /iman/trajectory          → Current state + display data
GET    /iman/baselines           → Current baselines

GET    /iman/digest/latest       → Most recent weekly digest
POST   /iman/digest/generate     → Trigger generation

POST   /iman/struggle            → Declare struggle (triggers plan)
GET    /iman/struggles           → List all struggles

POST   /iman/heart-note          → Quick capture
GET    /iman/heart-notes         → Date range query

GET    /iman/correlations        → Significant correlations
GET    /iman/identity            → Statements + reinforcement data

DELETE /iman/data                → Delete ALL iman data (privacy)
```

### Auto-Detection Integration

```
Existing app usage auto-populates behavioral log:
  - tadabbur_session: true if user opened /tafsir today
  - quran_minutes: estimated from session duration
  - reflection_written: true if annotation created today

Struggle plans link to existing scholarly source pipeline.
Weekly digest verse links to existing /tafsir flow.
```

---

## What Makes This Revolutionary

1. **First spirituality app treating growth scientifically** — correlation detection, trend analysis, baseline normalization applied to spiritual development

2. **Grounded in 1,000 years of Islamic scholarship** — struggle maps link to Ihya Vol 3 (problems) and Vol 4 (solutions), Madarij stations, Riyad hadith. Pre-indexed, deterministic.

3. **Measures trajectory, not achievement** — like WHOOP shows recovery trends, not "fitness scores"

4. **Theological safeguards as architectural foundation** — anti-riya, anti-scrupulosity, hidden scores, humility resets, despair prevention

5. **Connects inner and outer dimensions** — Heart Notes (feelings) + Behavioral Logs (actions) woven into AI narrative honoring both

6. **Identity-based transformation, not checkbox tracking** — "Are you becoming someone who prays?" not "Did you pray?"

---

## Keeping It Spiritually Deep, Not Productivity-Driven

```
LANGUAGE:
  Never "optimize" → always "deepen"
  Never "underperforming" → always "your growth edge"
  Never "score" → always "trajectory" or "direction"

FRAMING:
  Always relationship (user ↔ Allah), never performance
  The app is a mirror, not a judge

SCHOLARLY ANCHORING:
  Every coaching message references Al-Ghazali, Ibn Qayyim, or Al-Nawawi
  Not generic self-help. Not pop psychology.

SILENCE:
  Sometimes the best coaching is: "This week, just be."

MYSTERY:
  Preserve the ghayb dimension: "Allah sees what we cannot measure"
  The score is hidden because iman IS partly hidden

THE OFF BUTTON:
  Users can pause the entire engine anytime
  "Just use Tadabbur for Quran reflection? That's beautiful on its own."
```

## Data Flow

```
User logs behavior (Layer 1)
    │
    ▼
Normalize & categorize ──► Store encrypted in Firestore
    │
    ▼
Check identity alignment (Layer 2) ──► Reinforce or gently nudge
    │
    ▼
Apply spiritual context (Layer 3) ──► Calendar, time, emotional state
    │
    ▼
Detect correlations (Layer 4) ──► "Sleep ↔ Fajr", "Dhikr ↔ Anxiety relief"
    │
    ▼
Compute Iman Index (Layer 5) ──► Baseline-relative, 3-pillar scoring
    │
    ▼
Generate coaching narrative (Layer 6) ──► Gemini weekly digest
    │
    ▼
Apply safeguards (Layer 7) ──► Humility cues, anti-riya, anti-scrupulosity
    │
    ▼
Present to user ──► Trajectory arrow, qualitative state, narrative
```
