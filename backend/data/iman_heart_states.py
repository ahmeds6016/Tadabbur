"""
Heart State Catalog — 7 spiritually-rooted emotional states with tailored responses.

Each state maps to a Quranic verse, scholarly pointers (Ihya, Madarij, Riyad),
a spiritual insight, and a recommended action. Pointers are resolved at request
time via resolve_scholarly_pointers() for live scholarly excerpts.
"""

HEART_STATE_CATALOG = [
    {
        "id": "grateful",
        "label": "Grateful",
        "arabic": "shukr",
        "icon": "sun",
        "color": "#059669",
        "verse": {
            "surah": 14,
            "verse": 7,
            "text": "If you are grateful, I will surely increase you; but if you deny, indeed, My punishment is severe.",
        },
        "scholarly_pointers": [
            "ihya:vol=4:ch=2:sec=0",
        ],
        "insight": (
            "Gratitude is not just feeling — Al-Ghazali teaches it has three pillars: "
            "knowledge (recognizing the blessing), state (the joy that arises from it), "
            "and action (using the blessing in obedience to the Giver)."
        ),
        "action": (
            "Name three specific blessings from today. "
            "Say 'Alhamdulillah' for each one, slowly and with presence."
        ),
    },
    {
        "id": "anxious",
        "label": "Anxious",
        "arabic": "qalaq",
        "icon": "wind",
        "color": "#d97706",
        "verse": {
            "surah": 65,
            "verse": 3,
            "text": "And whoever relies upon Allah — then He is sufficient for him.",
        },
        "scholarly_pointers": [
            "ihya:vol=4:ch=5:sec=0",
            "madarij:vol=2:station=trusting_reliance:sub=0",
        ],
        "insight": (
            "Anxiety often means the heart is carrying what belongs to Allah. "
            "Tawakkul is not passivity — it is active surrender: doing your part, "
            "then entrusting the outcome to the One who holds all outcomes."
        ),
        "action": (
            "Perform wudu slowly. Recite Ayat al-Kursi. "
            "Then say: 'HasbiyAllahu wa ni'mal wakeel' — "
            "Allah is sufficient for me, and He is the best Disposer of affairs."
        ),
    },
    {
        "id": "grieving",
        "label": "Grieving",
        "arabic": "huzn",
        "icon": "cloud-rain",
        "color": "#64748b",
        "verse": {
            "surah": 94,
            "verse": 5,
            "text": "Verily, with hardship comes ease. Verily, with hardship comes ease.",
        },
        "scholarly_pointers": [
            "madarij:vol=2:station=grief:sub=0",
            "riyad:book=1:ch=3:hadith=0",
        ],
        "insight": (
            "Ibn Qayyim distinguishes between grief that paralyzes and grief that purifies. "
            "The latter draws you closer to Allah — it is a sign that your heart is alive "
            "and yearning for what is beyond this world."
        ),
        "action": (
            "Let yourself feel. Then open your hands and make dua — "
            "even if you have no words, the tears are enough. "
            "The Prophet \u2e0e wept for his son Ibrahim, and it was mercy."
        ),
    },
    {
        "id": "spiritually_dry",
        "label": "Spiritually Dry",
        "arabic": "qasawah",
        "icon": "droplets",
        "color": "#94a3b8",
        "verse": {
            "surah": 57,
            "verse": 16,
            "text": "Has the time not come for those who have believed that their hearts should become humbly submissive at the remembrance of Allah?",
        },
        "scholarly_pointers": [
            "ihya:vol=3:ch=1:sec=0",
            "madarij:vol=1:station=awakening:sub=0",
        ],
        "insight": (
            "Spiritual dryness is itself a form of awareness. "
            "The fact that you notice the distance means your heart still remembers closeness. "
            "Ibn Qayyim calls this the station of awakening — the first step back."
        ),
        "action": (
            "Don't try to force a spiritual high. Read one verse slowly. Let it sit. "
            "The rain comes when Allah wills — your task is to keep the soil turned."
        ),
    },
    {
        "id": "joyful",
        "label": "Joyful",
        "arabic": "farah",
        "icon": "sparkles",
        "color": "#0d9488",
        "verse": {
            "surah": 10,
            "verse": 58,
            "text": "Say: In the bounty of Allah and in His mercy — in that let them rejoice; it is better than what they accumulate.",
        },
        "scholarly_pointers": [
            "ihya:vol=4:ch=2:sec=0",
        ],
        "insight": (
            "Joy is a blessing that carries responsibility. "
            "Al-Ghazali warns: don't let ease make you forget the Giver. "
            "True joy is when the heart rejoices in Allah's mercy, not merely in the gift."
        ),
        "action": (
            "Capture this moment in a Heart Note. "
            "Share the joy through sadaqah — generosity in joy multiplies it."
        ),
    },
    {
        "id": "seeking_guidance",
        "label": "Seeking Guidance",
        "arabic": "istikhara",
        "icon": "compass",
        "color": "#2563eb",
        "verse": {
            "surah": 2,
            "verse": 186,
            "text": "And when My servants ask you concerning Me — indeed I am near. I respond to the invocation of the supplicant when he calls upon Me.",
        },
        "scholarly_pointers": [
            "ihya:vol=4:ch=8:sec=0",
            "riyad:book=1:ch=15:hadith=0",
        ],
        "insight": (
            "Seeking guidance is itself guided. The one who turns to Allah for direction "
            "has already taken the first step. Al-Ghazali teaches that introspection "
            "before action is itself an act of worship."
        ),
        "action": (
            "Pray istikhara. Then take a step — tawakkul means trusting the outcome "
            "to Allah after you have done your part. The answer may come as a feeling, "
            "a door opening, or a quiet certainty."
        ),
    },
    {
        "id": "remorseful",
        "label": "Remorseful",
        "arabic": "nadam",
        "icon": "heart-handshake",
        "color": "#8b5cf6",
        "verse": {
            "surah": 39,
            "verse": 53,
            "text": "Say: O My servants who have transgressed against themselves, do not despair of the mercy of Allah. Indeed, Allah forgives all sins.",
        },
        "scholarly_pointers": [
            "ihya:vol=4:ch=1:sec=0",
            "madarij:vol=1:station=repentance:sub=0",
        ],
        "insight": (
            "The Prophet \u2e0e said: 'Remorse is repentance.' "
            "The pain you feel is the door opening, not closing. "
            "Ibn Qayyim teaches that true tawbah is immediate — not delayed until tomorrow."
        ),
        "action": (
            "Make wudu. Pray two raka'at of tawbah. Then let go — "
            "Allah's forgiveness is greater than any sin. "
            "Move forward with the intention to be better, not the burden of what was."
        ),
    },
]

HEART_STATE_MAP = {s["id"]: s for s in HEART_STATE_CATALOG}
ALL_HEART_STATE_IDS = [s["id"] for s in HEART_STATE_CATALOG]
