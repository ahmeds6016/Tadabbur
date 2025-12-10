# Comprehensive persona-specific query suggestions
# Each persona gets relevant suggestions based on their knowledge level and needs

PERSONA_SUGGESTIONS = {
    "new_revert": {
        "tafsir": [
            # Essential short surahs for prayer
            "1:1-7",      # Al-Fatihah - must know for prayer
            "112:1-4",    # Al-Ikhlas - Oneness of Allah
            "113:1-5",    # Al-Falaq - Seeking protection
            "114:1-6",    # An-Nas - Seeking refuge
            "110:1-3",    # An-Nasr - Divine help
            "109:1-6",    # Al-Kafirun - Religious boundaries
            "108:1-3",    # Al-Kawthar - Abundance
            "107:1-7",    # Al-Ma'un - Small kindnesses
            "105:1-5",    # Al-Fil - The Elephant
            "103:1-3",    # Al-Asr - Time and faith
            "106:1-4",    # Al-Quraish - God's favors
            "111:1-5",    # Al-Masad

            # Core belief verses
            "2:255",      # Ayatul Kursi
            "2:286",      # No soul burdened beyond capacity
            "39:53",      # Allah's boundless mercy
            "13:28",      # Hearts find rest in remembrance
            "49:13",      # Created to know each other
            "2:152",      # Remember Me, I'll remember you

            # Comfort and reassurance
            "93:1-8",     # Ad-Duha
            "94:1-8",     # Ash-Sharh
            "2:153",      # Seek help through patience and prayer

            # Simple format requests
            "Surah Al-Fatihah",
            "Surah Al-Ikhlas meaning",
            "Last two verses of Surah Baqarah"
        ],
        "explore": [
            "How do I perform wudu properly?",
            "What are the five daily prayers and their times?",
            "What are the five pillars of Islam?",
            "Who is Allah and what are His attributes?",
            "What happens after death in Islam?",
            "How does Allah forgive sins?",
            "What foods are halal and haram?",
            "How should I treat my parents in Islam?",
            "Will Allah accept me as a new Muslim?",
            "How do I deal with my past sins?",
            "How can I find peace through Islam?"
        ]
    },

    "revert": {
        "tafsir": [
            "1:1-7", "2:1-5", "2:30-39", "2:255", "2:256",
            "2:261-266", "2:285-286", "3:26-27", "3:190-195",
            "4:1", "4:36", "5:32", "6:151-153", "7:156",
            "17:23-24", "30:21", "49:10-13", "60:8",
            "23:1-10", "25:63-70", "29:45", "33:21",
            "39:53-54", "42:36-43",
            "Surah Ya-Sin verse 1-10",
            "Surah Ar-Rahman verse 1-10",
            "Surah Al-Kahf verse 1-10"
        ],
        "explore": [
            "What is the concept of Tawakkul and how do I practice it?",
            "How does predestination work with free will in Islam?",
            "What lessons can we learn from Prophet Yusuf's story?",
            "How did Prophet Ibrahim discover monotheism?",
            "What can we learn from the People of the Cave?",
            "How do I perform Istikhara prayer for decisions?",
            "What are the etiquettes of making dua?",
            "When and how should I pay Zakat?",
            "What are the rights and responsibilities in marriage?",
            "How should Muslims raise their children?",
            "What does Islam say about social justice?"
        ]
    },

    "seeker": {
        "tafsir": [
            "2:164", "2:255", "3:190-195", "6:59", "7:54",
            "10:5-6", "13:2-4", "13:28", "24:35", "50:16",
            "57:3-6", "59:22-24", "2:115", "11:61",
            "17:85", "23:12-14", "32:7-9", "39:42",
            "56:83-87", "89:27-30", "31:12-19", "38:29",
            "39:9", "47:24", "51:20-21",
            "6:95-96", "55:19-22", "88:17-20",
            "Surah Ar-Rahman verse 1-10",
            "Surah Al-Mulk verse 1-10",
            "93:1-8", "94:1-8"
        ],
        "explore": [
            "What is the nature of the soul according to the Quran?",
            "How can one achieve inner peace through remembrance of Allah?",
            "What are the stages of spiritual development in Islam?",
            "What is the ultimate purpose of human existence?",
            "How does Islam explain suffering and evil in the world?",
            "What does it mean to be Allah's khalifa on earth?",
            "How can one develop a personal relationship with Allah?",
            "What is the role of meditation and contemplation in Islam?",
            "How does the Quran use nature as signs for seekers?",
            "What spiritual wisdom did Luqman teach his son?",
            "What are the veils between humanity and divine truth?"
        ]
    },

    "practicing_muslim": {
        "tafsir": [
            # Key passages
            "2:1-10", "2:21-29", "2:30-39", "2:255", "2:256",
            "2:284-286", "2:155-157", "2:177-179", "2:201-202",

            # Important verses
            "3:8-9", "3:26-27", "4:1", "4:36", "4:58-59",
            "4:136-137", "5:1-8", "5:55-56", "6:54-55",
            "6:151-153", "9:60", "14:7-8", "16:90-91",
            "24:27-31", "30:21", "49:10-13",

            # Spiritual development
            "17:23-24", "17:26-27", "23:1-10", "23:115-116",
            "25:63-65", "31:12-19", "31:18-19", "33:21",
            "39:22-23", "39:53-54", "40:57-60", "42:11-12",

            # Important passages
            "Surah Al-Kahf verse 1-10",
            "Surah Al-Hadid verse 1-10",
            "Surah Al-Waqi'ah verse 1-10",
            "7:142-143", "6:95-96", "55:19-22",

            # Metadata queries - Circumstances of revelation
            "Circumstances of verse 60:8",
            "Circumstances of verse 5:3",
            "Circumstances of verse 2:256",
            "Circumstances of verse 33:53",
            "Circumstances of verse 2:187",
            "Circumstances of verse 2:142",

            # Metadata queries - Legal rulings
            "Legal ruling on 3:97",
            "Legal ruling on 5:6",
            "Legal ruling on 2:275",
            "Legal ruling on 4:11-12",
            "Legal ruling on 2:282",
            "Legal ruling on 2:228",
            "Legal ruling on 2:178",

            # Context and historical background
            "Historical context of verse 9:29",
            "Historical context of verse 3:110",
            "Context of revelation for verse 2:154"
        ],
        "explore": [
            # Theological questions addressed by tafsir
            "How does the Quran reconcile divine mercy with divine justice?",
            "If Allah sealed their hearts in 2:7, are disbelievers forced into disbelief?",
            "What is the Trust (Amanah) that heavens and earth refused but humans accepted?",
            "Why does Allah command worship if He is self-sufficient?",
            "How does Allah's omniscience relate to human free will?",
            "Will intercession be accepted for those who died in disbelief?",
            "What happens to those who never received the message of Islam?",
            # Legal and practical questions
            "What are the conditions that make prayer valid?",
            "How are inheritance shares calculated in Islamic law?",
            "When is Zakat obligatory and how is it calculated?",
            "What makes a marriage contract valid in Islam?",
            "What are the rules of mahram relationships?",
            "Is the running between Safa and Marwa obligatory or voluntary?",
            "What exactly constitutes necessity that permits eating forbidden foods?",
            "What is the waiting period for a divorced woman and why?"
        ]
    },

    "teacher": {
        "tafsir": [
            "1:1-7", "2:1-5", "2:31-33", "3:7", "3:79",
            "4:82", "6:105", "12:1-3", "12:111", "14:1-4",
            "16:43-44", "16:89", "16:125", "18:60-69",
            "20:25-34", "29:43", "39:9", "41:3", "47:24",
            "12:1-10", "18:1-10", "19:1-10", "20:1-10",
            "21:51-60", "28:1-10",
            "What are pedagogical methods in the Quran?",
            "How do parables function as teaching tools?",
            "Historical context of verse 5:3",
            "Context of revelation for verse 96:1-5",
            "Linguistic beauty in verse 55:1-4"
        ],
        "explore": [
            "What teaching methods does the Quran employ?",
            "How are stories used for moral education in the Quran?",
            "What is the progression of revelation on key topics?",
            "How should Islamic education be structured by age?",
            "What are effective methods for Quran memorization?",
            "How does the Quran address controversial topics?",
            "How does the Quran build moral character?",
            "How can teachers model prophetic character?",
            "How to teach Islam to children of mixed-faith families?"
        ]
    },

    "scholar": {
        "tafsir": [
            # Methodological verses
            "2:1", "3:7", "4:82", "6:114-115", "10:37",
            "11:1", "15:9", "16:89", "17:88", "25:32-33",
            "41:41-42", "56:77-79", "75:16-19", "85:21-22",

            # Legal methodology
            "2:106", "2:178-179", "2:185", "2:219",
            "2:282-283", "4:11-12", "4:59", "5:1", "5:3",
            "5:48", "16:116", "22:78",

            # Divine mercy and proximity
            "39:53-54", "25:70", "42:25", "4:110",
            "2:186", "50:16", "57:4", "58:7", "11:61",

            # Purpose and judgment
            "51:56", "67:1-2", "90:4", "95:4-6", "103:1-3",
            "21:47", "99:7-8", "3:185", "6:160",

            # Day of Judgment passages
            "75:1-6", "99:1-8", "101:1-11", "78:31-36",

            # Profound metadata queries
            "Hadith references in verse 39:73-74",
            "Hadith narrations about verse 17:79",
            "Hadith explaining verse 53:39-42",
            "Legal ruling on verse 2:228",
            "Legal ruling on verse 4:3",
            "Circumstances of verse 4:43",
            "Circumstances of verse 2:187",
            "Linguistic analysis of verse 2:255",
            "Rhetorical features of verse 24:35",
            "Variant readings of verse 2:184"
        ],
        "explore": [
            "How does the Quran reconcile divine mercy with divine justice?",
            "What does 'Allah is closer than the jugular vein' mean for spiritual practice?",
            "How do the 99 names reveal different aspects of divine reality?",
            "What is the Quranic answer to human suffering and evil?",
            "What is the meaning of being Allah's khalifa on earth?",
            "What does the Quran mean by the 'diseased heart' and its cure?",
            "How does remembrance (dhikr) transform the human soul?",
            "What is the process of tazkiyah (purification) in Quranic spirituality?",
            "How does the Quran describe the experience of death?",
            "What is the nature of the barzakh (intermediate realm)?",
            "What is the significance of intercession (shafa'ah) on Judgment Day?",
            "What is the relationship between 'ilm and hikmah in the Quran?",
            "How does the Quran view the limits of human knowledge?",
            "What is the role of the fitrah (primordial nature) in recognizing truth?"
        ]
    },

    "student": {
        "tafsir": [
            # Structured study passages
            "1:1-7", "2:1-10", "2:2-4", "2:255", "3:1-9",
            "4:1-10", "6:1-10", "6:97-99", "7:1-10",
            "10:1-10", "11:6-8", "12:1-10", "12:86-87",
            "18:1-10", "19:1-10", "20:1-10", "24:35",
            "31:12-19", "36:1-10", "39:9-10", "55:1-10",
            "56:1-10", "67:1-10", "67:3-4",

            # Thematic passages
            "2:201-202", "16:90-91", "49:11-13",

            # Research topics
            "What is the thematic structure of Surah Baqarah?",
            "How does ring composition work in Surah Yusuf?",
            "What are Makkan vs Medinan characteristics?",

            # Analytical studies with metadata
            "Compare commentaries on verse 3:7",
            "Historical context of verse 9:29",
            "Hadith references in verse 2:187",
            "Legal principles from verse 17:32",
            "Scholar consensus on verse 24:31",
            "Context of revelation for verse 66:1-5",
            "Hadith explaining verse 13:11",
            "Circumstances of verse 2:158",
            "Legal ruling on verse 9:60"
        ],
        "explore": [
            "What are the primary sources for Quranic research?",
            "How to conduct thematic analysis across the Quran?",
            "What is the history of Quran compilation?",
            "What are the major tafsir works and their methodologies?",
            "How has Quranic exegesis evolved over time?",
            "What are the key debates in Quranic studies?",
            "How does linguistics contribute to Quranic understanding?",
            "What can archaeology tell us about Quranic contexts?",
            "Who are the leading contemporary Quran scholars?",
            "What is the Birmingham manuscript's significance?",
            "How to balance faith and academic objectivity?"
        ]
    }
}

# Default fallback for any undefined persona
DEFAULT_SUGGESTIONS = PERSONA_SUGGESTIONS["practicing_muslim"]
