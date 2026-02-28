"""
Iman Index — Behavior catalog and category definitions.

Each behavior has:
- id: Unique identifier (snake_case)
- category: One of 6 categories
- label: Human-readable display name
- input_type: binary | scale_5 | minutes | hours | count | count_inv
- default_on: Whether included in initial tracked set
- practice_group: Groups related behaviors for UI display
- scale_labels: (scale_5 only) Endpoint labels for the 1-5 scale
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
# Practice Groups — UI grouping for related behaviors within a category
# ---------------------------------------------------------------------------

PRACTICE_GROUPS = {
    "daily_prayers":    {"label": "Daily Prayers",              "category": "fard"},
    "prayer_quality":   {"label": "Prayer Quality",             "category": "fard"},
    "masjid":           {"label": "Masjid",                     "category": "fard"},
    "fasting":          {"label": "Fasting",                    "category": "fard"},
    "sin_awareness":    {"label": "Sin Awareness",              "category": "tawbah"},
    "gaze_screen":      {"label": "Gaze & Screen",              "category": "tawbah"},
    "quran_reading":    {"label": "Quran Reading",              "category": "quran"},
    "quran_reflection": {"label": "Reflection & Memorization",  "category": "quran"},
    "sunnah":           {"label": "Sunnah Prayers",             "category": "nafl"},
    "tahajjud":         {"label": "Night Prayer",               "category": "nafl"},
    "dhikr":            {"label": "Dhikr & Adhkar",             "category": "nafl"},
    "dua":              {"label": "Dua",                        "category": "nafl"},
    "charity":          {"label": "Charity",                    "category": "nafl"},
    "gratitude":        {"label": "Gratitude",                  "category": "character"},
    "kindness":         {"label": "Kindness",                   "category": "character"},
    "forgiveness":      {"label": "Forgiveness",                "category": "character"},
    "family":           {"label": "Family",                     "category": "character"},
    "speech":           {"label": "Speech",                     "category": "character"},
    "sleep":            {"label": "Sleep",                      "category": "stewardship"},
    "exercise":         {"label": "Exercise",                   "category": "stewardship"},
    "nutrition":        {"label": "Nutrition",                  "category": "stewardship"},
}

# ---------------------------------------------------------------------------
# Behaviors (39 total, 14 default ON)
# ---------------------------------------------------------------------------

IMAN_BEHAVIORS = [
    # --- fard (obligatory) --- Daily Prayers group
    {"id": "fajr_prayer",          "category": "fard",       "label": "Fajr Prayer",          "input_type": "binary",    "default_on": True,  "practice_group": "daily_prayers"},
    {"id": "dhuhr_prayer",         "category": "fard",       "label": "Dhuhr Prayer",         "input_type": "binary",    "default_on": True,  "practice_group": "daily_prayers"},
    {"id": "asr_prayer",           "category": "fard",       "label": "Asr Prayer",           "input_type": "binary",    "default_on": True,  "practice_group": "daily_prayers"},
    {"id": "maghrib_prayer",       "category": "fard",       "label": "Maghrib Prayer",       "input_type": "binary",    "default_on": True,  "practice_group": "daily_prayers"},
    {"id": "isha_prayer",          "category": "fard",       "label": "Isha Prayer",          "input_type": "binary",    "default_on": True,  "practice_group": "daily_prayers"},
    # --- fard --- Prayer Quality group (optional dimensions)
    {"id": "prayer_on_time",       "category": "fard",       "label": "Prayers On Time",      "input_type": "scale_5",   "default_on": False, "practice_group": "prayer_quality",
     "scale_labels": {"1": "Few on time", "3": "Some on time", "5": "All on time"}},
    {"id": "prayer_khushu",        "category": "fard",       "label": "Khushu' (Focus)",      "input_type": "scale_5",   "default_on": False, "practice_group": "prayer_quality",
     "scale_labels": {"1": "Very distracted", "3": "Moderate focus", "5": "Deep presence"}},
    {"id": "prayer_congregation",  "category": "fard",       "label": "In Congregation",      "input_type": "count",     "default_on": False, "practice_group": "prayer_quality"},
    # --- fard --- Other
    {"id": "masjid_attendance",    "category": "fard",       "label": "Masjid Attendance",    "input_type": "binary",    "default_on": False, "practice_group": "masjid"},
    {"id": "fasting",              "category": "fard",       "label": "Fasting",              "input_type": "binary",    "default_on": False, "practice_group": "fasting"},

    # --- tawbah (guarding & repentance) --- Sin Awareness group
    {"id": "avoided_sins",         "category": "tawbah",     "label": "Avoided Known Sins",   "input_type": "scale_5",   "default_on": True,  "practice_group": "sin_awareness",
     "scale_labels": {"1": "Major struggle", "3": "Moderate", "5": "Strong guard"}},
    {"id": "tawbah_moment",        "category": "tawbah",     "label": "Sought Forgiveness",   "input_type": "binary",    "default_on": True,  "practice_group": "sin_awareness"},
    {"id": "urge_resistance",      "category": "tawbah",     "label": "Urge Resistance",      "input_type": "scale_5",   "default_on": False, "practice_group": "sin_awareness",
     "scale_labels": {"1": "Weak resistance", "3": "Moderate", "5": "Strong resistance"}},
    {"id": "sin_slip",             "category": "tawbah",     "label": "Slip Occurred",        "input_type": "count_inv", "default_on": False, "practice_group": "sin_awareness"},
    # --- tawbah --- Gaze & Screen group
    {"id": "lowering_gaze",        "category": "tawbah",     "label": "Lowering Gaze",        "input_type": "scale_5",   "default_on": False, "practice_group": "gaze_screen",
     "scale_labels": {"1": "Many slips", "3": "Some lapses", "5": "Well guarded"}},
    {"id": "device_discipline",    "category": "tawbah",     "label": "Device Discipline",    "input_type": "scale_5",   "default_on": False, "practice_group": "gaze_screen",
     "scale_labels": {"1": "Excessive use", "3": "Some control", "5": "Disciplined"}},

    # --- quran --- Quran Reading group
    {"id": "quran_minutes",        "category": "quran",      "label": "Quran Recitation",     "input_type": "minutes",   "default_on": True,  "practice_group": "quran_reading"},
    {"id": "quran_pages",          "category": "quran",      "label": "Pages Read",           "input_type": "count",     "default_on": False, "practice_group": "quran_reading"},
    {"id": "quran_surahs",         "category": "quran",      "label": "Surahs Completed",     "input_type": "count",     "default_on": False, "practice_group": "quran_reading"},
    {"id": "quran_ayat",           "category": "quran",      "label": "Ayat Read",            "input_type": "count",     "default_on": False, "practice_group": "quran_reading"},
    # --- quran --- Reflection & Memorization group
    {"id": "tadabbur_session",     "category": "quran",      "label": "Tadabbur Session",     "input_type": "binary",    "default_on": True,  "practice_group": "quran_reflection"},
    {"id": "tadabbur_quality",     "category": "quran",      "label": "Reflection Quality",   "input_type": "scale_5",   "default_on": False, "practice_group": "quran_reflection",
     "scale_labels": {"1": "Surface reading", "3": "Some reflection", "5": "Deep pondering"}},
    {"id": "quran_memorization",   "category": "quran",      "label": "Memorization",         "input_type": "minutes",   "default_on": False, "practice_group": "quran_reflection"},

    # --- nafl (voluntary) --- Sunnah group
    {"id": "sunnah_prayers",       "category": "nafl",       "label": "Sunnah Prayers",       "input_type": "count",     "default_on": True,  "practice_group": "sunnah"},
    {"id": "sunnah_prayers_done",  "category": "nafl",       "label": "Prayed Sunnah",        "input_type": "binary",    "default_on": False, "practice_group": "sunnah"},
    # --- nafl --- Night Prayer
    {"id": "tahajjud",             "category": "nafl",       "label": "Tahajjud / Qiyam",     "input_type": "binary",    "default_on": False, "practice_group": "tahajjud"},
    # --- nafl --- Dhikr group
    {"id": "dhikr_minutes",        "category": "nafl",       "label": "Dhikr",                "input_type": "minutes",   "default_on": True,  "practice_group": "dhikr"},
    {"id": "adhkar_set",           "category": "nafl",       "label": "Adhkar Set Completed", "input_type": "binary",    "default_on": False, "practice_group": "dhikr"},
    # --- nafl --- Dua group
    {"id": "dua_moments",          "category": "nafl",       "label": "Dua Moments",          "input_type": "count",     "default_on": True,  "practice_group": "dua"},
    {"id": "dua_made",             "category": "nafl",       "label": "Made Dua",             "input_type": "binary",    "default_on": False, "practice_group": "dua"},
    # --- nafl --- Charity
    {"id": "charity",              "category": "nafl",       "label": "Charity / Sadaqah",    "input_type": "binary",    "default_on": False, "practice_group": "charity"},

    # --- character ---
    {"id": "gratitude_entry",      "category": "character",  "label": "Gratitude Practice",   "input_type": "binary",    "default_on": True,  "practice_group": "gratitude"},
    {"id": "kindness_act",         "category": "character",  "label": "Act of Kindness",      "input_type": "binary",    "default_on": False, "practice_group": "kindness"},
    {"id": "forgiveness",          "category": "character",  "label": "Forgiveness",          "input_type": "binary",    "default_on": False, "practice_group": "forgiveness"},
    {"id": "family_rights",        "category": "character",  "label": "Family Rights",        "input_type": "scale_5",   "default_on": False, "practice_group": "family",
     "scale_labels": {"1": "Neglected", "3": "Some effort", "5": "Fulfilled well"}},
    {"id": "tongue_control",       "category": "character",  "label": "Guarded Speech",       "input_type": "scale_5",   "default_on": False, "practice_group": "speech",
     "scale_labels": {"1": "Many slips", "3": "Some control", "5": "Well guarded"}},

    # --- stewardship ---
    {"id": "sleep_hours",          "category": "stewardship","label": "Sleep Duration",       "input_type": "hours",     "default_on": True,  "practice_group": "sleep"},
    {"id": "exercise",             "category": "stewardship","label": "Physical Activity",    "input_type": "binary",    "default_on": False, "practice_group": "exercise"},
    {"id": "healthy_eating",       "category": "stewardship","label": "Mindful Eating",       "input_type": "binary",    "default_on": False, "practice_group": "nutrition"},
]

# Quick lookups
BEHAVIOR_MAP = {b["id"]: b for b in IMAN_BEHAVIORS}
DEFAULT_BEHAVIORS = [b for b in IMAN_BEHAVIORS if b["default_on"]]
ALL_BEHAVIOR_IDS = {b["id"] for b in IMAN_BEHAVIORS}

# Heart note types
HEART_NOTE_TYPES = [
    "gratitude", "dua", "tawbah", "connection", "reflection", "quran_insight",
]

# Heart state options (opt-in daily mood) — aligned with scholarly catalog
HEART_STATES = [
    "grateful", "anxious", "grieving", "spiritually_dry",
    "joyful", "seeking_guidance", "remorseful",
]
