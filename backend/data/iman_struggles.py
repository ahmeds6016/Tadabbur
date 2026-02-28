"""
Iman Struggle Catalog
=====================
10 pre-indexed spiritual struggles mapped to scholarly sources (Ihya, Madarij, Riyad),
comfort verses, linked behaviors for progress tracking, and 4-week phase progressions.

Each struggle's scholarly_pointers use the exact format from source_service.py routing tables.
"""

STRUGGLE_CATALOG = [
    # ── 1. Prayer Consistency ──────────────────────────────────────────
    {
        "id": "prayer_consistency",
        "label": "Prayer Consistency",
        "description": "Struggling to maintain the five daily prayers on time and with presence of heart.",
        "icon": "clock",
        "color": "#0d9488",
        "scholarly_pointers": [
            "ihya:vol=1:ch=4:sec=0",           # Book of Prayer
            "madarij:vol=2:station=devotion:sub=0",
            "riyad:book=1:ch=8:hadith=0",       # Uprightness
        ],
        "comfort_verses": [
            {"surah": 29, "verse": 45, "text": "Indeed, prayer prohibits immorality and wrongdoing, and the remembrance of Allah is greater."},
            {"surah": 2, "verse": 45, "text": "And seek help through patience and prayer; and indeed, it is difficult except for the humbly submissive."},
            {"surah": 20, "verse": 14, "text": "Indeed, I am Allah. There is no deity except Me, so worship Me and establish prayer for My remembrance."},
        ],
        "linked_behaviors": [
            "fajr_prayer", "dhuhr_prayer", "asr_prayer",
            "maghrib_prayer", "isha_prayer", "masjid_attendance",
        ],
        "phases": [
            "Acknowledge: Notice which prayers feel heaviest and why — without judgment.",
            "Anchor: Choose one prayer to protect completely this week. Build around it.",
            "Expand: Add a second anchored prayer. Begin arriving a minute early.",
            "Sustain: All five are becoming habits. Focus now on khushu (presence of heart).",
        ],
    },

    # ── 2. Anger Management ───────────────────────────────────────────
    {
        "id": "anger_management",
        "label": "Anger Management",
        "description": "Working on controlling anger, responding with patience, and choosing gentleness.",
        "icon": "flame",
        "color": "#dc2626",
        "scholarly_pointers": [
            "ihya:vol=3:ch=5:sec=0",           # Anger & Envy
            "madarij:vol=2:station=patience:sub=0",
            "riyad:book=1:ch=3:hadith=0",       # Patience
        ],
        "comfort_verses": [
            {"surah": 3, "verse": 134, "text": "Those who restrain anger and pardon the people — and Allah loves the doers of good."},
            {"surah": 41, "verse": 34, "text": "Repel evil by that which is better; and thereupon the one between you and him was enmity will become as though he was a devoted friend."},
            {"surah": 42, "verse": 43, "text": "And whoever is patient and forgives — indeed, that is of the matters requiring resolve."},
        ],
        "linked_behaviors": ["forgiveness", "kindness_act", "tongue_control"],
        "phases": [
            "Recognize: Notice anger as it rises — the body signals before words come.",
            "Pause: Practice the Prophetic response: silence, wudu, change position.",
            "Reframe: Ask 'What would hilm (forbearance) look like here?'",
            "Transform: Anger becomes a signal for dua, not a trigger for harm.",
        ],
    },

    # ── 3. Lowering the Gaze ─────────────────────────────────────────
    {
        "id": "lowering_gaze",
        "label": "Lowering the Gaze",
        "description": "Guarding the eyes and heart from what does not benefit, especially in a digital world.",
        "icon": "eye-off",
        "color": "#7c3aed",
        "scholarly_pointers": [
            "ihya:vol=3:ch=3:sec=0",           # Greed / Appetites
            "madarij:vol=2:station=scrupulousness:sub=0",
            "riyad:book=1:ch=6:hadith=0",       # Piety (Taqwa)
        ],
        "comfort_verses": [
            {"surah": 24, "verse": 30, "text": "Tell the believing men to lower their gaze and guard their private parts. That is purer for them."},
            {"surah": 7, "verse": 26, "text": "But the garment of righteousness — that is best."},
            {"surah": 23, "verse": 1, "text": "Certainly will the believers have succeeded — they who are during their prayer humbly submissive."},
        ],
        "linked_behaviors": ["lowering_gaze", "device_discipline"],
        "phases": [
            "Awareness: Track when and where the gaze slips — patterns reveal triggers.",
            "Environment: Adjust devices, spaces, and routines to reduce exposure.",
            "Replace: Fill the gap — when the urge arises, redirect to dhikr or movement.",
            "Freedom: The sweetness of self-mastery replaces the pull of distraction.",
        ],
    },

    # ── 4. Quranic Disconnection ─────────────────────────────────────
    {
        "id": "quran_disconnection",
        "label": "Quranic Disconnection",
        "description": "Feeling distant from the Quran — difficulty reading, reflecting, or finding meaning.",
        "icon": "book-open",
        "color": "#2563eb",
        "scholarly_pointers": [
            "ihya:vol=1:ch=8:sec=0",           # Etiquettes of Quran Recitation
            "madarij:vol=1:station=reflection:sub=0",
            "riyad:book=1:ch=9:hadith=0",       # Reflection / Contemplation
        ],
        "comfort_verses": [
            {"surah": 73, "verse": 4, "text": "And recite the Quran with measured recitation."},
            {"surah": 17, "verse": 82, "text": "And We send down of the Quran that which is healing and mercy for the believers."},
            {"surah": 54, "verse": 17, "text": "And We have certainly made the Quran easy for remembrance, so is there any who will remember?"},
        ],
        "linked_behaviors": ["quran_minutes", "tadabbur_session", "quran_memorization"],
        "phases": [
            "Return: Open the mushaf — even one ayah. The door is never locked.",
            "Listen: Let recitation wash over you before you try to study.",
            "Reflect: Pick one verse per day. Sit with its meaning. Write one thought.",
            "Converse: The Quran speaks to you — begin responding with dua and action.",
        ],
    },

    # ── 5. Spiritual Dryness ─────────────────────────────────────────
    {
        "id": "spiritual_dryness",
        "label": "Spiritual Dryness",
        "description": "A season of numbness — worship feels mechanical, dua feels empty, the heart feels distant.",
        "icon": "cloud",
        "color": "#64748b",
        "scholarly_pointers": [
            "ihya:vol=4:ch=3:sec=0",           # Fear & Hope
            "ihya:vol=3:ch=1:sec=0",           # Wonders of the Heart
            "madarij:vol=2:station=grief:sub=0",
            "madarij:vol=1:station=awakening:sub=0",
        ],
        "comfort_verses": [
            {"surah": 94, "verse": 5, "text": "For indeed, with hardship will be ease."},
            {"surah": 39, "verse": 53, "text": "Say: O My servants who have transgressed against themselves, do not despair of the mercy of Allah."},
            {"surah": 2, "verse": 186, "text": "And when My servants ask you concerning Me — indeed I am near. I respond to the invocation of the supplicant when he calls upon Me."},
        ],
        "linked_behaviors": ["dhikr_minutes", "dua_moments", "tahajjud", "sunnah_prayers"],
        "phases": [
            "Accept: Spiritual seasons are real. This is not failure — it is a human experience.",
            "Simplify: Strip back to the essentials. One prayer with full presence beats five rushed.",
            "Seek company: Be near those who remind you of Allah, even if you feel nothing yet.",
            "Trust the return: The heart that seeks Allah is already being sought by Him.",
        ],
    },

    # ── 6. Tongue Control ────────────────────────────────────────────
    {
        "id": "tongue_control",
        "label": "Tongue Control",
        "description": "Guarding speech from gossip, lying, harshness, and idle talk.",
        "icon": "message-circle-off",
        "color": "#ea580c",
        "scholarly_pointers": [
            "ihya:vol=3:ch=4:sec=0",           # Tongue / Speech
            "madarij:vol=2:station=listening:sub=0",
            "riyad:book=1:ch=4:hadith=0",       # Truthfulness
        ],
        "comfort_verses": [
            {"surah": 49, "verse": 12, "text": "O you who have believed, avoid much suspicion... And do not spy or backbite each other."},
            {"surah": 23, "verse": 3, "text": "And they who turn away from ill speech."},
            {"surah": 33, "verse": 70, "text": "O you who have believed, fear Allah and speak words of appropriate justice."},
        ],
        "linked_behaviors": ["tongue_control", "forgiveness", "kindness_act"],
        "phases": [
            "Listen: Before speaking, pause. Notice the impulse behind the words.",
            "Filter: Apply the Prophetic sieve — is it true? Is it kind? Is it necessary?",
            "Replace: Fill silence with dhikr. Replace gossip with dua for the person.",
            "Protect: Your tongue becomes a garden, not a weapon. Guard it with gratitude.",
        ],
    },

    # ── 7. Worldly Attachment ────────────────────────────────────────
    {
        "id": "worldly_attachment",
        "label": "Worldly Attachment",
        "description": "The heart clinging to dunya — wealth, status, comfort — at the expense of the akhira.",
        "icon": "gem",
        "color": "#ca8a04",
        "scholarly_pointers": [
            "ihya:vol=3:ch=7:sec=0",           # Love of Wealth
            "ihya:vol=4:ch=4:sec=0",           # Poverty & Renunciation
            "madarij:vol=2:station=renunciation:sub=0",
            "riyad:book=1:ch=54:hadith=0",      # Renunciation
        ],
        "comfort_verses": [
            {"surah": 57, "verse": 20, "text": "Know that the life of this world is but amusement and diversion and adornment and boasting to one another."},
            {"surah": 28, "verse": 77, "text": "But seek, through that which Allah has given you, the home of the Hereafter; and do not forget your share of the world."},
            {"surah": 3, "verse": 14, "text": "Beautified for people is the love of that which they desire... but Allah has with Him the best return."},
        ],
        "linked_behaviors": ["charity", "gratitude_entry"],
        "phases": [
            "Notice: What occupies your thoughts most? That is what owns your heart.",
            "Loosen: Give something away this week that you feel attached to.",
            "Reorient: Use blessings as bridges to gratitude, not anchors to anxiety.",
            "Balance: Be in the world but not of it. The hand holds dunya; the heart holds Allah.",
        ],
    },

    # ── 8. Pride & Arrogance ─────────────────────────────────────────
    {
        "id": "pride_arrogance",
        "label": "Pride & Arrogance",
        "description": "Subtle or overt kibr — feeling superior, dismissing others, or resisting truth.",
        "icon": "crown",
        "color": "#9333ea",
        "scholarly_pointers": [
            "ihya:vol=3:ch=9:sec=0",           # Pride
            "madarij:vol=2:station=humility:sub=0",
            "riyad:book=1:ch=50:hadith=0",      # Forgiveness / Pardoning
        ],
        "comfort_verses": [
            {"surah": 31, "verse": 18, "text": "And do not turn your cheek in contempt toward people and do not walk through the earth exultantly."},
            {"surah": 25, "verse": 63, "text": "And the servants of the Most Merciful are those who walk upon the earth humbly."},
            {"surah": 4, "verse": 36, "text": "Worship Allah and associate nothing with Him, and to parents do good, and to relatives, orphans, the needy..."},
        ],
        "linked_behaviors": ["kindness_act", "gratitude_entry", "family_rights"],
        "phases": [
            "See it: Pride hides. Notice where you compare, dismiss, or feel 'above' others.",
            "Remember origin: You came from dust. Every blessing is borrowed.",
            "Serve: Do something no one sees — serve someone 'beneath' your status.",
            "Empty the cup: True knowledge begins with knowing how little you know.",
        ],
    },

    # ── 9. Laziness & Procrastination ────────────────────────────────
    {
        "id": "laziness_procrastination",
        "label": "Laziness & Procrastination",
        "description": "Delaying good deeds, struggling to start worship, or feeling spiritually lethargic.",
        "icon": "timer-off",
        "color": "#0284c7",
        "scholarly_pointers": [
            "ihya:vol=4:ch=8:sec=0",           # Self-examination / Meditation
            "ihya:vol=1:ch=3:sec=0",           # Foundations of Worship
            "madarij:vol=1:station=resolve:sub=0",
            "riyad:book=1:ch=11:hadith=0",      # Striving
        ],
        "comfort_verses": [
            {"surah": 3, "verse": 133, "text": "And hasten to forgiveness from your Lord and a garden as wide as the heavens and earth."},
            {"surah": 63, "verse": 10, "text": "And spend from what We have provided you before death approaches one of you."},
            {"surah": 18, "verse": 10, "text": "Our Lord, grant us from Yourself mercy and prepare for us from our affair right guidance."},
        ],
        "linked_behaviors": ["fajr_prayer", "tahajjud", "exercise", "sunnah_prayers"],
        "phases": [
            "Start small: The Prophet (pbuh) said the most beloved deeds are the most consistent, even if small.",
            "Morning anchor: Win the morning — Fajr on time becomes the day's foundation.",
            "Build momentum: Stack one small act on another. Movement creates energy.",
            "Discipline as love: You are not punishing yourself — you are honoring the gift of time.",
        ],
    },

    # ── 10. Repentance Cycle ─────────────────────────────────────────
    {
        "id": "repentance_cycle",
        "label": "The Repentance Cycle",
        "description": "Falling into the same sin, repenting, then falling again — feeling trapped in a loop.",
        "icon": "rotate-ccw",
        "color": "#059669",
        "scholarly_pointers": [
            "ihya:vol=4:ch=1:sec=0",           # Repentance
            "madarij:vol=1:station=repentance:sub=0",
            "madarij:vol=1:station=self_reckoning:sub=0",
            "riyad:book=1:ch=2:hadith=0",       # Repentance
        ],
        "comfort_verses": [
            {"surah": 39, "verse": 53, "text": "Say: O My servants who have transgressed against themselves, do not despair of the mercy of Allah. Indeed, Allah forgives all sins."},
            {"surah": 66, "verse": 8, "text": "O you who have believed, repent to Allah with sincere repentance."},
            {"surah": 11, "verse": 114, "text": "Indeed, good deeds do away with misdeeds. That is a reminder for those who remember."},
        ],
        "linked_behaviors": ["tawbah_moment", "avoided_sins", "dua_moments"],
        "phases": [
            "The door is open: Allah loves the one who keeps returning. Your repentance is never rejected.",
            "Understand triggers: Map the chain — what leads to the fall? Break one link.",
            "Build barriers: Distance yourself from the means of sin, not just the sin itself.",
            "Trust His mercy: Each return to Allah is sincere. The cycle is not failure — it is jihad al-nafs.",
        ],
    },
]

# ── Lookup helpers ────────────────────────────────────────────────────
STRUGGLE_MAP = {s["id"]: s for s in STRUGGLE_CATALOG}
ALL_STRUGGLE_IDS = [s["id"] for s in STRUGGLE_CATALOG]
