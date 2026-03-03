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
        "goals": {
            0: {
                "daily": [
                    {"id": "pc_d0_1", "text": "Pray one salah with full attention today", "type": "action"},
                    {"id": "pc_d0_2", "text": "Make wudu slowly and mindfully", "type": "mindfulness"},
                    {"id": "pc_d0_3", "text": "Say SubhanAllah 10 times after one prayer", "type": "dhikr"},
                ],
                "weekly": {"id": "pc_w0", "text": "Protect Fajr for 7 consecutive days"},
            },
            1: {
                "daily": [
                    {"id": "pc_d1_1", "text": "Arrive 1 minute early for your anchor prayer", "type": "action"},
                    {"id": "pc_d1_2", "text": "Pray sunnah before or after your anchor prayer", "type": "action"},
                    {"id": "pc_d1_3", "text": "Make dhikr after your anchor prayer", "type": "dhikr"},
                ],
                "weekly": {"id": "pc_w1", "text": "Pray in congregation at least once this week"},
            },
            2: {
                "daily": [
                    {"id": "pc_d2_1", "text": "Anchor a second prayer — protect it fully", "type": "action"},
                    {"id": "pc_d2_2", "text": "Pray one prayer in congregation today", "type": "action"},
                    {"id": "pc_d2_3", "text": "Read the meaning of a surah you pray", "type": "knowledge"},
                ],
                "weekly": {"id": "pc_w2", "text": "All five prayers on time for 5 out of 7 days"},
            },
            3: {
                "daily": [
                    {"id": "pc_d3_1", "text": "All five prayers on time today", "type": "action"},
                    {"id": "pc_d3_2", "text": "Focus on one khushu technique in salah", "type": "mindfulness"},
                    {"id": "pc_d3_3", "text": "Pray one sunnah prayer today", "type": "action"},
                ],
                "weekly": {"id": "pc_w3", "text": "Maintain all five on time for the full week"},
            },
        },
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
        "goals": {
            0: {
                "daily": [
                    {"id": "am_d0_1", "text": "Notice one body signal before anger today", "type": "awareness"},
                    {"id": "am_d0_2", "text": "Practice silence when you feel annoyed", "type": "action"},
                    {"id": "am_d0_3", "text": "Make dua when triggered instead of reacting", "type": "dua"},
                ],
                "weekly": {"id": "am_w0", "text": "Journal three anger triggers you noticed this week"},
            },
            1: {
                "daily": [
                    {"id": "am_d1_1", "text": "Make wudu when you feel angry", "type": "action"},
                    {"id": "am_d1_2", "text": "Change position (sit or lie down) when angry", "type": "action"},
                    {"id": "am_d1_3", "text": "Write down one anger trigger today", "type": "reflection"},
                ],
                "weekly": {"id": "am_w1", "text": "Practice the Prophetic pause in 3 anger moments this week"},
            },
            2: {
                "daily": [
                    {"id": "am_d2_1", "text": "Respond with hilm (forbearance) once today", "type": "action"},
                    {"id": "am_d2_2", "text": "Forgive one small thing someone did", "type": "character"},
                    {"id": "am_d2_3", "text": "Make dua for someone who angered you", "type": "dua"},
                ],
                "weekly": {"id": "am_w2", "text": "Go a full day without raising your voice"},
            },
            3: {
                "daily": [
                    {"id": "am_d3_1", "text": "Transform one anger moment into dua", "type": "action"},
                    {"id": "am_d3_2", "text": "Teach patience by example today", "type": "character"},
                    {"id": "am_d3_3", "text": "Reflect on the hilm of the Prophet (pbuh)", "type": "reflection"},
                ],
                "weekly": {"id": "am_w3", "text": "Complete a full week responding to anger with patience"},
            },
        },
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
        "goals": {
            0: {
                "daily": [
                    {"id": "lg_d0_1", "text": "Notice when and where the gaze slips today", "type": "awareness"},
                    {"id": "lg_d0_2", "text": "Set one device boundary (e.g., time limit)", "type": "action"},
                    {"id": "lg_d0_3", "text": "Do dhikr when the urge arises", "type": "dhikr"},
                ],
                "weekly": {"id": "lg_w0", "text": "Identify your top 3 trigger times or places"},
            },
            1: {
                "daily": [
                    {"id": "lg_d1_1", "text": "Adjust one routine to reduce a trigger", "type": "action"},
                    {"id": "lg_d1_2", "text": "Use a content blocker or screen time limit", "type": "action"},
                    {"id": "lg_d1_3", "text": "Replace 5 min of screen time with reading", "type": "action"},
                ],
                "weekly": {"id": "lg_w1", "text": "Keep your phone out of the bedroom for 5 nights"},
            },
            2: {
                "daily": [
                    {"id": "lg_d2_1", "text": "Redirect an urge to physical movement or dhikr", "type": "action"},
                    {"id": "lg_d2_2", "text": "Keep the phone out of the bedroom tonight", "type": "action"},
                    {"id": "lg_d2_3", "text": "Read one page of Quran instead of scrolling", "type": "action"},
                ],
                "weekly": {"id": "lg_w2", "text": "Complete 3 days with no gaze slips"},
            },
            3: {
                "daily": [
                    {"id": "lg_d3_1", "text": "Celebrate one moment of self-mastery", "type": "mindfulness"},
                    {"id": "lg_d3_2", "text": "Fill freed time with beneficial knowledge", "type": "knowledge"},
                    {"id": "lg_d3_3", "text": "Help or advise someone who struggles similarly", "type": "character"},
                ],
                "weekly": {"id": "lg_w3", "text": "Maintain your gaze discipline for the full week"},
            },
        },
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
        "goals": {
            0: {
                "daily": [
                    {"id": "qd_d0_1", "text": "Open the mushaf for 1 minute today", "type": "action"},
                    {"id": "qd_d0_2", "text": "Listen to 1 page of recitation", "type": "action"},
                    {"id": "qd_d0_3", "text": "Read 1 ayah with its translation", "type": "knowledge"},
                ],
                "weekly": {"id": "qd_w0", "text": "Open the Quran on 5 out of 7 days"},
            },
            1: {
                "daily": [
                    {"id": "qd_d1_1", "text": "Read 5 ayat with their meaning", "type": "action"},
                    {"id": "qd_d1_2", "text": "Listen to tafsir of 1 ayah", "type": "knowledge"},
                    {"id": "qd_d1_3", "text": "Write one reflection on what you read", "type": "reflection"},
                ],
                "weekly": {"id": "qd_w1", "text": "Complete one full page of Quran with reflection"},
            },
            2: {
                "daily": [
                    {"id": "qd_d2_1", "text": "Read 1 page of Quran daily", "type": "action"},
                    {"id": "qd_d2_2", "text": "Memorize 1 short ayah", "type": "action"},
                    {"id": "qd_d2_3", "text": "Discuss an ayah with someone", "type": "action"},
                ],
                "weekly": {"id": "qd_w2", "text": "Read Quran every day this week"},
            },
            3: {
                "daily": [
                    {"id": "qd_d3_1", "text": "Complete your daily page of Quran", "type": "action"},
                    {"id": "qd_d3_2", "text": "Teach someone an ayah you love", "type": "character"},
                    {"id": "qd_d3_3", "text": "Make dua using words from the Quran", "type": "dua"},
                ],
                "weekly": {"id": "qd_w3", "text": "Study one full surah in depth this week"},
            },
        },
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
        "goals": {
            0: {
                "daily": [
                    {"id": "sd_d0_1", "text": "Accept this season without guilt — say Alhamdulillah", "type": "mindfulness"},
                    {"id": "sd_d0_2", "text": "Simplify to one act of worship done with presence", "type": "action"},
                    {"id": "sd_d0_3", "text": "Sit in nature and make dhikr for 2 minutes", "type": "dhikr"},
                ],
                "weekly": {"id": "sd_w0", "text": "Write a letter to yourself about how you feel spiritually"},
            },
            1: {
                "daily": [
                    {"id": "sd_d1_1", "text": "Be near someone who reminds you of Allah", "type": "action"},
                    {"id": "sd_d1_2", "text": "Listen to a short lecture or reminder", "type": "knowledge"},
                    {"id": "sd_d1_3", "text": "Make one heartfelt dua — even one word", "type": "dua"},
                ],
                "weekly": {"id": "sd_w1", "text": "Attend one gathering of remembrance or knowledge"},
            },
            2: {
                "daily": [
                    {"id": "sd_d2_1", "text": "Visit the masjid even briefly today", "type": "action"},
                    {"id": "sd_d2_2", "text": "Do one act of service for someone", "type": "character"},
                    {"id": "sd_d2_3", "text": "Read about a companion who faced spiritual difficulty", "type": "knowledge"},
                ],
                "weekly": {"id": "sd_w2", "text": "Pray tahajjud once this week — even 2 rakaat"},
            },
            3: {
                "daily": [
                    {"id": "sd_d3_1", "text": "Trust the return — the heart that seeks Allah is found", "type": "mindfulness"},
                    {"id": "sd_d3_2", "text": "Share your experience to help someone else", "type": "character"},
                    {"id": "sd_d3_3", "text": "Increase your gratitude practice today", "type": "action"},
                ],
                "weekly": {"id": "sd_w3", "text": "Complete the week with daily dhikr and one act of worship done with love"},
            },
        },
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
        "goals": {
            0: {
                "daily": [
                    {"id": "tc_d0_1", "text": "Pause before speaking once today", "type": "awareness"},
                    {"id": "tc_d0_2", "text": "Notice one gossip impulse and hold back", "type": "awareness"},
                    {"id": "tc_d0_3", "text": "Make istighfar after a speech slip", "type": "dhikr"},
                ],
                "weekly": {"id": "tc_w0", "text": "Go one full day without idle talk or gossip"},
            },
            1: {
                "daily": [
                    {"id": "tc_d1_1", "text": "Apply the sieve: is it true, kind, necessary?", "type": "mindfulness"},
                    {"id": "tc_d1_2", "text": "Replace one gossip impulse with dua for the person", "type": "dua"},
                    {"id": "tc_d1_3", "text": "Practice 10 minutes of intentional silence", "type": "action"},
                ],
                "weekly": {"id": "tc_w1", "text": "Avoid backbiting for 3 consecutive days"},
            },
            2: {
                "daily": [
                    {"id": "tc_d2_1", "text": "Fill silence with dhikr instead of small talk", "type": "dhikr"},
                    {"id": "tc_d2_2", "text": "Compliment someone genuinely today", "type": "character"},
                    {"id": "tc_d2_3", "text": "Avoid one negative conversation", "type": "action"},
                ],
                "weekly": {"id": "tc_w2", "text": "Complete 5 days of mindful speech this week"},
            },
            3: {
                "daily": [
                    {"id": "tc_d3_1", "text": "Let your speech be a garden — speak only good", "type": "mindfulness"},
                    {"id": "tc_d3_2", "text": "Thank someone you usually don't acknowledge", "type": "character"},
                    {"id": "tc_d3_3", "text": "Reflect on the weight of words in the akhira", "type": "reflection"},
                ],
                "weekly": {"id": "tc_w3", "text": "Guard your tongue for the full week"},
            },
        },
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
        "goals": {
            0: {
                "daily": [
                    {"id": "wa_d0_1", "text": "Notice what occupies your thoughts most today", "type": "awareness"},
                    {"id": "wa_d0_2", "text": "Write 3 blessings you are grateful for", "type": "reflection"},
                    {"id": "wa_d0_3", "text": "Give a small amount in charity today", "type": "action"},
                ],
                "weekly": {"id": "wa_w0", "text": "Give away one item you feel attached to"},
            },
            1: {
                "daily": [
                    {"id": "wa_d1_1", "text": "Fast from one luxury today (e.g., coffee, dessert)", "type": "action"},
                    {"id": "wa_d1_2", "text": "Make shukr for 5 specific blessings", "type": "reflection"},
                    {"id": "wa_d1_3", "text": "Give something — time, money, or kindness", "type": "action"},
                ],
                "weekly": {"id": "wa_w1", "text": "Spend one day without a non-essential purchase"},
            },
            2: {
                "daily": [
                    {"id": "wa_d2_1", "text": "Use a blessing as a bridge to gratitude", "type": "mindfulness"},
                    {"id": "wa_d2_2", "text": "Volunteer your time, not just money", "type": "action"},
                    {"id": "wa_d2_3", "text": "Reflect on a sahabi who gave everything", "type": "knowledge"},
                ],
                "weekly": {"id": "wa_w2", "text": "Give charity 3 times this week"},
            },
            3: {
                "daily": [
                    {"id": "wa_d3_1", "text": "Hold dunya in the hand, not the heart", "type": "mindfulness"},
                    {"id": "wa_d3_2", "text": "Mentor someone in practicing gratitude", "type": "character"},
                    {"id": "wa_d3_3", "text": "Live simply in one area today", "type": "action"},
                ],
                "weekly": {"id": "wa_w3", "text": "Complete the week with daily charity or gratitude practice"},
            },
        },
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
        "goals": {
            0: {
                "daily": [
                    {"id": "pa_d0_1", "text": "Notice where you compare yourself to others", "type": "awareness"},
                    {"id": "pa_d0_2", "text": "Remember your origin — you came from dust", "type": "reflection"},
                    {"id": "pa_d0_3", "text": "Say SubhanAllah at something greater than you", "type": "dhikr"},
                ],
                "weekly": {"id": "pa_w0", "text": "Do one anonymous act of service this week"},
            },
            1: {
                "daily": [
                    {"id": "pa_d1_1", "text": "Serve someone anonymously today", "type": "action"},
                    {"id": "pa_d1_2", "text": "Ask forgiveness from someone", "type": "character"},
                    {"id": "pa_d1_3", "text": "Sit on the floor for a meal today", "type": "action"},
                ],
                "weekly": {"id": "pa_w1", "text": "Apologize to someone you wronged recently"},
            },
            2: {
                "daily": [
                    {"id": "pa_d2_1", "text": "Praise someone sincerely today", "type": "character"},
                    {"id": "pa_d2_2", "text": "Admit being wrong about something", "type": "character"},
                    {"id": "pa_d2_3", "text": "Learn from someone younger or less experienced", "type": "knowledge"},
                ],
                "weekly": {"id": "pa_w2", "text": "Complete 3 acts of humble service this week"},
            },
            3: {
                "daily": [
                    {"id": "pa_d3_1", "text": "Empty the cup — seek knowledge with humility", "type": "mindfulness"},
                    {"id": "pa_d3_2", "text": "Thank your teachers and mentors", "type": "character"},
                    {"id": "pa_d3_3", "text": "Walk with softness and gentleness", "type": "mindfulness"},
                ],
                "weekly": {"id": "pa_w3", "text": "Live the week with humility as your compass"},
            },
        },
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
        "goals": {
            0: {
                "daily": [
                    {"id": "lp_d0_1", "text": "Do one small good deed right now", "type": "action"},
                    {"id": "lp_d0_2", "text": "Set alarm 5 minutes before Fajr", "type": "action"},
                    {"id": "lp_d0_3", "text": "Move your body for 5 minutes", "type": "action"},
                ],
                "weekly": {"id": "lp_w0", "text": "Pray Fajr on time for 3 days this week"},
            },
            1: {
                "daily": [
                    {"id": "lp_d1_1", "text": "Win the morning — Fajr on time", "type": "action"},
                    {"id": "lp_d1_2", "text": "Stack one act after Fajr (dhikr, Quran, walk)", "type": "action"},
                    {"id": "lp_d1_3", "text": "Prepare for tomorrow tonight", "type": "action"},
                ],
                "weekly": {"id": "lp_w1", "text": "Fajr on time for 5 out of 7 days"},
            },
            2: {
                "daily": [
                    {"id": "lp_d2_1", "text": "Complete 3 good deeds before noon", "type": "action"},
                    {"id": "lp_d2_2", "text": "Exercise for 20 minutes", "type": "action"},
                    {"id": "lp_d2_3", "text": "Read 1 page of beneficial knowledge", "type": "knowledge"},
                ],
                "weekly": {"id": "lp_w2", "text": "Build a 5-day streak of morning routine"},
            },
            3: {
                "daily": [
                    {"id": "lp_d3_1", "text": "Protect your full daily routine", "type": "action"},
                    {"id": "lp_d3_2", "text": "Teach someone a productive habit", "type": "character"},
                    {"id": "lp_d3_3", "text": "Reflect on the gift of time", "type": "reflection"},
                ],
                "weekly": {"id": "lp_w3", "text": "Maintain your routine for the full week"},
            },
        },
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
        "goals": {
            0: {
                "daily": [
                    {"id": "rc_d0_1", "text": "Make tawbah right now — the door is always open", "type": "action"},
                    {"id": "rc_d0_2", "text": "Write down one trigger that leads to the fall", "type": "reflection"},
                    {"id": "rc_d0_3", "text": "Make dua for strength against this sin", "type": "dua"},
                ],
                "weekly": {"id": "rc_w0", "text": "Identify your complete trigger chain (what leads to what)"},
            },
            1: {
                "daily": [
                    {"id": "rc_d1_1", "text": "Break one link in the trigger chain today", "type": "action"},
                    {"id": "rc_d1_2", "text": "Replace one bad habit with a good one", "type": "action"},
                    {"id": "rc_d1_3", "text": "Read about Allah's mercy and forgiveness", "type": "knowledge"},
                ],
                "weekly": {"id": "rc_w1", "text": "Go 3 consecutive days without falling"},
            },
            2: {
                "daily": [
                    {"id": "rc_d2_1", "text": "Distance yourself from one means of sin", "type": "action"},
                    {"id": "rc_d2_2", "text": "Increase worship during a vulnerable time", "type": "action"},
                    {"id": "rc_d2_3", "text": "Confide in a trusted friend or mentor", "type": "action"},
                ],
                "weekly": {"id": "rc_w2", "text": "Build 5 days of resistance this week"},
            },
            3: {
                "daily": [
                    {"id": "rc_d3_1", "text": "Trust His mercy — each return is sincere", "type": "mindfulness"},
                    {"id": "rc_d3_2", "text": "The cycle is jihad al-nafs — honor the fight", "type": "reflection"},
                    {"id": "rc_d3_3", "text": "Help someone else who struggles with repentance", "type": "character"},
                ],
                "weekly": {"id": "rc_w3", "text": "Complete the week trusting in Allah's mercy"},
            },
        },
    },
]

# ── Lookup helpers ────────────────────────────────────────────────────
STRUGGLE_MAP = {s["id"]: s for s in STRUGGLE_CATALOG}
ALL_STRUGGLE_IDS = [s["id"] for s in STRUGGLE_CATALOG]
