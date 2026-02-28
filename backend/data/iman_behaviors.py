"""
Iman Index — Behavior catalog and category definitions.

Each behavior has:
- id: Unique identifier (snake_case)
- category: One of 6 categories
- label: Human-readable display name
- input_type: binary | scale_5 | minutes | hours | count | count_inv
- default_on: Whether included in initial tracked set
"""

# ---------------------------------------------------------------------------
# Categories (6) — ordered by Islamic priority (base_weight descending)
# ---------------------------------------------------------------------------

IMAN_CATEGORIES = {
    "fard": {
        "label": "Obligatory Worship",
        "base_weight": 0.30,
        "icon": "mosque",
        "color": "#0D9488",
    },
    "tawbah": {
        "label": "Guarding & Repentance",
        "base_weight": 0.20,
        "icon": "shield",
        "color": "#8B5CF6",
    },
    "quran": {
        "label": "Quranic Engagement",
        "base_weight": 0.20,
        "icon": "book-open",
        "color": "#2563EB",
    },
    "nafl": {
        "label": "Voluntary Worship",
        "base_weight": 0.12,
        "icon": "star",
        "color": "#D97706",
    },
    "character": {
        "label": "Character & Social",
        "base_weight": 0.10,
        "icon": "heart",
        "color": "#EC4899",
    },
    "stewardship": {
        "label": "Body & Health",
        "base_weight": 0.08,
        "icon": "activity",
        "color": "#059669",
    },
}

# Base weights as a flat dict for computation
BASE_WEIGHTS = {cid: cat["base_weight"] for cid, cat in IMAN_CATEGORIES.items()}

# ---------------------------------------------------------------------------
# Behaviors (27 total, 14 default ON)
# ---------------------------------------------------------------------------

IMAN_BEHAVIORS = [
    # --- fard (obligatory) ---
    {"id": "fajr_prayer",       "category": "fard",       "label": "Fajr Prayer",        "input_type": "binary",    "default_on": True},
    {"id": "dhuhr_prayer",      "category": "fard",       "label": "Dhuhr Prayer",       "input_type": "binary",    "default_on": True},
    {"id": "asr_prayer",        "category": "fard",       "label": "Asr Prayer",         "input_type": "binary",    "default_on": True},
    {"id": "maghrib_prayer",    "category": "fard",       "label": "Maghrib Prayer",     "input_type": "binary",    "default_on": True},
    {"id": "isha_prayer",       "category": "fard",       "label": "Isha Prayer",        "input_type": "binary",    "default_on": True},
    {"id": "masjid_attendance", "category": "fard",       "label": "Masjid Attendance",  "input_type": "binary",    "default_on": False},
    {"id": "fasting",           "category": "fard",       "label": "Fasting",            "input_type": "binary",    "default_on": False},
    # --- tawbah (guarding & repentance) ---
    {"id": "avoided_sins",      "category": "tawbah",     "label": "Avoided Known Sins", "input_type": "scale_5",   "default_on": True},
    {"id": "tawbah_moment",     "category": "tawbah",     "label": "Sought Forgiveness", "input_type": "binary",    "default_on": True},
    {"id": "lowering_gaze",     "category": "tawbah",     "label": "Lowering Gaze",      "input_type": "scale_5",   "default_on": False},
    {"id": "device_discipline", "category": "tawbah",     "label": "Device Discipline",  "input_type": "scale_5",   "default_on": False},
    # --- quran ---
    {"id": "quran_minutes",     "category": "quran",      "label": "Quran Recitation",   "input_type": "minutes",   "default_on": True},
    {"id": "tadabbur_session",  "category": "quran",      "label": "Tadabbur Session",   "input_type": "binary",    "default_on": True},
    {"id": "quran_memorization","category": "quran",      "label": "Memorization",       "input_type": "minutes",   "default_on": False},
    # --- nafl (voluntary) ---
    {"id": "sunnah_prayers",    "category": "nafl",       "label": "Sunnah Prayers",     "input_type": "count",     "default_on": True},
    {"id": "tahajjud",          "category": "nafl",       "label": "Tahajjud / Qiyam",   "input_type": "binary",    "default_on": False},
    {"id": "dhikr_minutes",     "category": "nafl",       "label": "Dhikr",              "input_type": "minutes",   "default_on": True},
    {"id": "dua_moments",       "category": "nafl",       "label": "Dua Moments",        "input_type": "count",     "default_on": True},
    {"id": "charity",           "category": "nafl",       "label": "Charity / Sadaqah",  "input_type": "binary",    "default_on": False},
    # --- character ---
    {"id": "gratitude_entry",   "category": "character",  "label": "Gratitude Practice", "input_type": "binary",    "default_on": True},
    {"id": "kindness_act",      "category": "character",  "label": "Act of Kindness",    "input_type": "binary",    "default_on": False},
    {"id": "forgiveness",       "category": "character",  "label": "Forgiveness",        "input_type": "binary",    "default_on": False},
    {"id": "family_rights",     "category": "character",  "label": "Family Rights",      "input_type": "scale_5",   "default_on": False},
    {"id": "tongue_control",    "category": "character",  "label": "Guarded Speech",     "input_type": "scale_5",   "default_on": False},
    # --- stewardship ---
    {"id": "sleep_hours",       "category": "stewardship","label": "Sleep Duration",     "input_type": "hours",     "default_on": True},
    {"id": "exercise",          "category": "stewardship","label": "Physical Activity",  "input_type": "binary",    "default_on": False},
    {"id": "healthy_eating",    "category": "stewardship","label": "Mindful Eating",     "input_type": "binary",    "default_on": False},
]

# Quick lookups
BEHAVIOR_MAP = {b["id"]: b for b in IMAN_BEHAVIORS}
DEFAULT_BEHAVIORS = [b for b in IMAN_BEHAVIORS if b["default_on"]]
ALL_BEHAVIOR_IDS = {b["id"] for b in IMAN_BEHAVIORS}

# Heart note types
HEART_NOTE_TYPES = [
    "gratitude", "dua", "tawbah", "connection", "reflection", "quran_insight",
]

# Heart state options (opt-in daily mood)
HEART_STATES = [
    "grateful", "peaceful", "anxious", "struggling",
    "hopeful", "spiritually_dry", "content",
]
