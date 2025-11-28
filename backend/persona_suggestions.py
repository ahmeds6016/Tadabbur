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

            # Core belief verses
            "2:255",      # Ayatul Kursi - Protection and Allah's attributes
            "2:286",      # No soul burdened beyond capacity
            "39:53",      # Allah's boundless mercy
            "3:190-191",  # Signs in creation
            "13:28",      # Hearts find rest in remembrance
            "16:97",      # Good life for believers
            "20:14",      # Establish prayer for My remembrance
            "33:35",      # Qualities of Muslim men and women
            "49:13",      # Created to know each other
            "2:152",      # Remember Me, I'll remember you

            # Comfort and reassurance
            "93:1-8",     # Ad-Duha - Morning brightness
            "94:1-8",     # Ash-Sharh - Expansion of chest
            "95:1-8",     # At-Tin - Honor of human creation
            "2:153",      # Seek help through patience and prayer
            "65:2-3",     # Allah provides from unexpected sources

            # Simple format requests
            "Surah Al-Fatihah",
            "Surah Al-Ikhlas meaning",
            "Last two verses of Surah Baqarah",
            "Surah Al-Asr explanation"
        ],
        "explore": [
            # Essential practices - question format
            "How do I perform wudu properly?",
            "What are the five daily prayers and their times?",
            "How do Muslims pray step by step?",
            "What should I say during prayer?",
            "What breaks my wudu?",
            "Can I pray in English?",
            "What is the importance of Friday prayer?",

            # Core beliefs - detailed questions
            "What are the five pillars of Islam?",
            "Who is Allah and what are His attributes?",
            "Why do Muslims believe in one God?",
            "What happens after death in Islam?",
            "What is the purpose of life according to Islam?",
            "How does Allah forgive sins?",
            "What if I make mistakes in my prayer?",

            # Daily life guidance
            "What foods are halal and haram?",
            "How should I treat my parents in Islam?",
            "What does Islam say about honesty?",
            "How do I deal with non-Muslim family members?",
            "Can I still celebrate cultural holidays?",
            "What should I do when I feel overwhelmed?",
            "How do I strengthen my faith?",

            # Common concerns
            "Will Allah accept me as a new Muslim?",
            "How do I deal with my past sins?",
            "What if my family doesn't accept my conversion?",
            "How can I find peace through Islam?",
            "What does Islam say about depression and anxiety?",
            "How do I make Islamic friends?",
            "Where can I learn more about Islam?"
        ]
    },

    "revert": {
        "tafsir": [
            # Expanding knowledge
            "1:1-7",      # Al-Fatihah with deeper understanding
            "2:1-5",      # Beginning of Al-Baqarah
            "2:30-39",    # Story of Adam
            "2:255",      # Ayatul Kursi
            "2:256",      # No compulsion in religion
            "2:261-266",  # Charity parables
            "2:285-286",  # Belief and burden verses

            # Important passages
            "3:26-27",    # Allah's sovereignty
            "3:190-195",  # Reflecting on creation
            "4:1",        # Creation from single soul
            "4:36",       # Worship Allah and kindness
            "5:32",       # Saving one life
            "6:151-153",  # Commandments
            "7:31",       # Beautiful appearance at mosque
            "7:156",      # Mercy encompasses everything

            # Relationship and society verses
            "17:23-24",   # Parents' rights
            "30:21",      # Marriage and mercy
            "49:10-13",   # Brotherhood and diversity
            "60:8",       # Justice with non-Muslims

            # Spiritual development
            "23:1-10",    # Qualities of successful believers
            "25:63-70",   # Servants of the Most Merciful
            "29:45",      # Prayer prevents evil
            "33:21",      # Prophet as example
            "39:53-54",   # Never despair of Allah's mercy
            "42:36-43",   # Forgiveness and patience

            # Named passages
            "Surah Ya-Sin verse 1-10",
            "Surah Ar-Rahman verse 1-10",
            "Surah Al-Kahf verse 1-10",
            "Surah Al-Waqiah verse 1-10"
        ],
        "explore": [
            # Deepening faith - detailed questions
            "What is the concept of Tawakkul and how do I practice it?",
            "How does predestination work with free will in Islam?",
            "What are the different names of Allah and their meanings?",
            "How do I balance worldly life with spiritual goals?",
            "What is the spiritual significance of the five daily prayers?",
            "How do I develop khushu (humility) in prayer?",
            "What are the signs of a hypocrite mentioned in Quran?",

            # Stories and lessons from the Quran
            "What lessons can we learn from Prophet Yusuf's story?",
            "How did Prophet Ibrahim discover monotheism?",
            "What is the story of Prophet Musa and Pharaoh?",
            "Why did Prophet Yunus end up in the whale?",
            "What can we learn from the People of the Cave?",
            "What does the Quran say about Prophet Muhammad's character?",
            "What miracles are mentioned in the Quran?",
            "What is the story of Maryam in the Quran?",
            "What does the Quran teach about Prophet Adam's creation?",
            "What lessons are in the story of Prophet Nuh?",

            # Practical Islam
            "How do I perform Istikhara prayer for decisions?",
            "What are the etiquettes of making dua?",
            "When and how should I pay Zakat?",
            "What are the benefits of voluntary fasting?",
            "How do I purify my income and wealth?",
            "What is the importance of Tahajjud prayer?",
            "How can I memorize the Quran effectively?",

            # Social and family life
            "What are the rights and responsibilities in marriage?",
            "How should Muslims raise their children?",
            "What does Islam say about maintaining family ties?",
            "How do I give dawah to my family respectfully?",
            "What is the Islamic view on friendship?",
            "How should neighbors be treated in Islam?",
            "What does Islam say about social justice?",

            # Quranic guidance
            "What does the Quran say about mental health and healing?",
            "How does the Quran guide maintaining Islamic identity?",
            "What does the Quran say about respecting creation?",
            "How does the Quran guide social interactions?"
        ]
    },

    "seeker": {
        "tafsir": [
            # Spiritual and philosophical verses
            "2:164",      # Signs in creation for those who understand
            "2:255",      # Ayatul Kursi - Allah's throne
            "3:190-195",  # Contemplation of creation
            "6:59",       # Keys of the unseen
            "7:54",       # Creation and command
            "10:5-6",     # Signs in celestial bodies
            "13:2-4",     # Signs in nature
            "13:28",      # Hearts find rest in remembrance

            # Divine attributes and presence
            "24:35",      # Allah is the Light verse
            "50:16",      # Closer than jugular vein
            "57:3-6",     # First, Last, Manifest, Hidden
            "59:22-24",   # Beautiful names of Allah
            "2:115",      # Wherever you turn is Allah's face
            "11:61",      # He is near and responsive

            # Soul and spiritual journey
            "16:97",      # Good life for believers
            "17:85",      # Soul is from Allah's command
            "23:12-14",   # Stages of human creation
            "32:7-9",     # Creation and soul breathing
            "39:42",      # Allah takes souls at death and sleep
            "50:16-18",   # Recording angels
            "56:83-87",   # Soul at death
            "89:27-30",   # Content soul returning

            # Wisdom and reflection
            "31:12-19",   # Luqman's wisdom
            "38:29",      # Book of contemplation
            "39:9",       # Are those who know equal to those who don't
            "47:24",      # Do they not ponder the Quran
            "51:20-21",   # Signs within yourselves

            # Passages for meditation
            "Surah Ar-Rahman verse 1-10",
            "Surah Al-Mulk verse 1-10",
            "Surah Ya-Sin verse 1-10",
            "93:1-8",     # Ad-Duha
            "94:1-8"      # Ash-Sharh/Al-Inshirah
        ],
        "explore": [
            # Deep spiritual questions
            "What is the nature of the soul according to the Quran?",
            "How can one achieve inner peace through remembrance of Allah?",
            "What are the stages of spiritual development in Islam?",
            "How does the Quran describe the journey to Allah?",
            "What is the relationship between gratitude and spiritual growth?",
            "How do trials and tribulations purify the soul?",
            "What is the concept of divine love in Islamic spirituality?",

            # Purpose and meaning
            "What is the ultimate purpose of human existence?",
            "How does Islam explain suffering and evil in the world?",
            "What is the meaning of true success according to the Quran?",
            "How does one find their calling in life through Islamic guidance?",
            "What does it mean to be Allah's khalifa on earth?",
            "How can one align their will with divine will?",
            "What is the spiritual significance of free will?",

            # Connection with the Divine
            "What are the different levels of consciousness of Allah?",
            "How can one develop a personal relationship with Allah?",
            "What is the role of meditation and contemplation in Islam?",
            "How do the 99 names of Allah guide spiritual development?",
            "What is the experience of divine presence in prayer?",
            "How does night prayer transform the soul?",
            "What are the signs of Allah's love for a servant?",

            # Nature and creation in the Quran
            "How does the Quran use nature as signs for seekers?",
            "What can we learn from observing the natural world?",
            "What is the spiritual significance of celestial bodies in the Quran?",
            "How does the cycle of life and death point to resurrection?",
            "What do the parables of light and darkness mean in the Quran?",
            "How is water used as a spiritual metaphor in the Quran?",
            "What lessons are in the creation of the heavens and earth?",
            "What does the Quran say about the sun and moon?",
            "How does the Quran describe mountains and their purpose?",
            "What spiritual meanings are in Quranic references to rain?",

            # Wisdom traditions in the Quran
            "What spiritual wisdom did Luqman teach his son?",
            "How do the stories of prophets guide spiritual seekers?",
            "What is the significance of dreams in the Quran?",
            "How does the Quran describe the straight path?",
            "What are the veils between humanity and divine truth?",
            "How can one develop spiritual insight and wisdom?",
            "What does the Quran say about patience and perseverance?",
            "How does the Quran define true success?",
            "What are the characteristics of the righteous in the Quran?"
        ]
    },

    "practicing_muslim": {
        "tafsir": [
            # Key passages
            "2:1-10",     # Opening of Baqarah
            "2:21-29",    # Call to worship
            "2:30-39",    # Story of Adam
            "2:255",      # Ayatul Kursi
            "2:256",      # No compulsion in religion
            "2:284-286",  # Final verses of Baqarah

            # Important verses
            "3:26-27",    # Allah's sovereignty
            "4:1",        # Creation from single soul
            "4:36",       # Worship Allah and kindness
            "5:1-8",      # Contracts and purification
            "6:151-153",  # Commandments
            "9:60",       # Zakat distribution
            "24:27-31",   # Social etiquette
            "30:21",      # Marriage and mercy
            "49:10-13",   # Brotherhood and diversity

            # Spiritual development
            "17:23-24",   # Parents' rights
            "23:1-10",    # Qualities of successful believers
            "25:63-70",   # Servants of the Most Merciful
            "31:12-19",   # Luqman's wisdom
            "33:21",      # Prophet as example
            "39:53-54",   # Never despair of Allah's mercy
            "42:36-43",   # Forgiveness and patience

            # Important passages
            "Surah Al-Kahf verse 1-10",
            "Surah Maryam verse 1-10",
            "Surah As-Sajdah verse 1-9",
            "Surah Al-Hujurat verse 10-13",
            "Surah Al-Hadid verse 1-10",
            "Surah Al-Waqi'ah verse 1-10",

            # Study topics
            "Hadith narrations about verse 2:255",
            "Context of revelation for verse 5:3",
            "Hadith references in verse 4:36",
            "Historical context of verse 2:256",
            "Hadith about verse 49:10",
            "Circumstances of verse 60:8",
            "Scholar interpretations of verse 2:286",
            "Linguistic analysis of verse 1:1-7"
        ],
        "explore": [
            # Jurisprudence and practice
            "What are the conditions that make prayer valid?",
            "How are inheritance shares calculated in Islamic law?",
            "What are the different types of sunnah prayers and their rewards?",
            "When is Zakat obligatory and how is it calculated?",
            "What are the nullifiers of fasting during Ramadan?",
            "How does Islamic law address modern financial instruments?",
            "What are the rules for combining or shortening prayers?",
            "What makes a marriage contract valid in Islam?",

            # Theological understanding
            "How do the different schools of thought differ on key issues?",
            "What is the concept of bid'ah and how is it determined?",
            "How does intercession work on the Day of Judgment?",
            "What are the major and minor signs of the Day of Judgment?",
            "How do angels interact with human beings?",
            "What is the nature of divine decree and human responsibility?",
            "What happens in the grave according to Islamic teachings?",

            # Social and community affairs
            "What are the rights of neighbors in Islamic society?",
            "How should Islamic leadership and governance function?",
            "What are the principles of Islamic business ethics?",
            "How does Islam address social inequality and poverty?",
            "What is the role of the mosque in community development?",
            "How should Muslims engage in interfaith dialogue?",
            "What are the guidelines for giving Islamic advice?",

            # Family and relationships
            "What are the mutual rights of spouses in marriage?",
            "How should divorce proceedings be conducted Islamically?",
            "What are the Islamic guidelines for raising children?",
            "How should inheritance be distributed among heirs?",
            "What are the rules of mahram relationships?",
            "How does Islam view adoption and fostering?",
            "What are the etiquettes of seeking marriage?",

            # Quranic principles
            "How do scholars derive rulings from Quranic verses?",
            "What does the Quran say about justice in society?",
            "How does the Quran guide community leadership?",
            "What are Quranic principles for social responsibility?",
            "What does the Quran say about wealth and charity?",
            "How does the Quran address family responsibilities?",
            "What are Quranic principles for ethical business?",
            "How does the Quran guide conflict resolution?"
        ]
    },

    "teacher": {
        "tafsir": [
            # Pedagogical verses
            "1:1-7",      # Al-Fatihah - layers of meaning
            "2:1-5",      # Characteristics of the guided
            "2:31-33",    # Adam taught names
            "3:7",        # Clear and allegorical verses
            "3:79",       # Teaching scripture and wisdom
            "4:82",       # Pondering the Quran
            "6:105",      # Signs explained for people who know
            "12:1-3",     # Best of stories
            "12:111",     # Lessons in stories
            "14:1-4",     # Book to bring people to light
            "16:43-44",   # Ask people of knowledge
            "16:89",      # Book explaining all things
            "16:125",     # Call with wisdom
            "18:60-69",   # Musa and Khidr - learning journey
            "20:113-114", # Quran in Arabic, seeking knowledge
            "29:43",      # Examples for those who understand
            "30:22",      # Signs for those with knowledge
            "39:9",       # Are those who know equal
            "41:3",       # Book explained in detail
            "47:24",      # Do they not ponder

            # Stories for teaching
            "12:1-10",    # Opening of Surah Yusuf
            "18:1-10",    # Opening of Surah Kahf
            "19:1-10",    # Opening of Surah Maryam
            "20:1-10",    # Opening of Surah Ta-Ha
            "21:51-60",   # Ibrahim and idols
            "28:1-10",    # Opening of Surah Qasas

            # Teaching methods in Quran
            "What are pedagogical methods in the Quran?",
            "How do parables function as teaching tools?",
            "What is the wisdom of gradual revelation?",
            "How do rhetorical questions teach in the Quran?",
            "Historical context of verse 5:3",
            "Hadith explaining verse 31:14",
            "Context of revelation for verse 96:1-5",
            "Historical background of verse 2:256",
            "Hadith about seeking knowledge",
            "Linguistic beauty in verse 55:1-4"
        ],
        "explore": [
            # Educational methodology
            "What teaching methods does the Quran employ?",
            "How are stories used for moral education in the Quran?",
            "What is the progression of revelation on key topics?",
            "How does the Quran address different learning styles?",
            "What are the principles of asking questions in the Quran?",
            "How does repetition function as a teaching tool?",
            "What role do parables play in Quranic pedagogy?",

            # Curriculum development
            "How should Islamic education be structured by age?",
            "What are the essential topics for new Muslim education?",
            "How can Quranic stories be adapted for children?",
            "What is the sequence for teaching Islamic sciences?",
            "How should Arabic be integrated with Quranic studies?",
            "What are effective methods for Quran memorization?",
            "How can critical thinking be developed through Quranic study?",

            # Teaching challenges
            "How does the Quran address controversial topics?",
            "What are Quranic strategies for teaching truth?",
            "How should teachers handle questions about other religions?",
            "What Quranic guidance addresses misconceptions?",
            "How can Quranic stories be made accessible to all learners?",

            # Character development
            "How does the Quran build moral character?",
            "What are the stages of spiritual development for students?",
            "How can teachers model prophetic character?",
            "What methods develop God-consciousness in students?",
            "How should discipline be approached Islamically?",
            "What builds confidence in young Muslims?",
            "How can community service be integrated into learning?",

            # Teaching diverse audiences
            "How to teach Islam to children of mixed-faith families?",
            "What Quranic principles guide accommodating different learners?",
            "How does the Quran address healing and comfort in teaching?",
            "What are the Quran's principles for women's education?",
            "How does the Quran encourage lifelong learning?",
            "What Quranic examples show teaching methods for adults?"
        ]
    },

    "scholar": {
        "tafsir": [
            # Methodological verses
            "2:1",        # Huruf muqatta'at
            "3:7",        # Muhkam and mutashabih
            "4:82",       # Tadabbur and consistency
            "6:114-115",  # Detailed book, perfect words
            "7:52",       # Book with knowledge
            "10:37",      # Cannot be produced by other
            "11:1",       # Verses perfected and detailed
            "15:9",       # Preservation of dhikr
            "16:89",      # Tibyan li kulli shay
            "17:88",      # Inimitability challenge
            "18:109",     # Oceans as ink
            "25:32-33",   # Gradual revelation
            "26:192-195", # Clear Arabic tongue
            "41:41-42",   # Protected book
            "42:7",       # Arabic Quran
            "56:77-79",   # Hidden book, pure touch
            "75:16-19",   # Collection and recitation
            "85:21-22",   # Preserved tablet

            # Legal methodology verses
            "2:106",      # Naskh (abrogation)
            "2:178-179",  # Qisas principles
            "2:185",      # Ease and difficulty
            "2:219",      # Gradual prohibition
            "2:282-283",  # Testimony and documentation
            "4:11-12",    # Inheritance laws detail
            "4:59",       # Sources of authority
            "5:1",        # Fulfill contracts
            "5:3",        # Completion of religion
            "5:48",       # Each community's law
            "16:116",     # Don't declare halal/haram
            "22:78",      # No hardship in religion

            # Hadith references
            "Hadith references in verse 39:73-74",
            "Hadith narrations about verse 17:79",
            "Hadith explaining verse 53:39-42",
            "Hadith about verse 59:9",

            # Divine mercy and forgiveness
            "39:53-54",   # Allah's boundless mercy - no despair
            "25:70",      # Evil deeds replaced with good
            "42:25",      # Accepts repentance and pardons
            "4:110",      # Whoever does evil then seeks forgiveness
            "11:90",      # Seek forgiveness, He is Most Loving
            "15:56",      # Who despairs of Lord's mercy except the lost

            # Divine proximity and response
            "2:186",      # I am near, I respond
            "50:16",      # Closer than jugular vein
            "57:4",       # He is with you wherever you are
            "58:7",       # No secret consultation but He is fourth
            "11:61",      # My Lord is near and responsive
            "34:50",      # If I go astray, I go astray to my own loss

            # Purpose and human condition
            "51:56",      # Created jinn and humans to worship
            "67:1-2",     # Created death and life to test
            "90:4",       # Created human in struggle
            "95:4-6",     # Created in best form
            "103:1-3",    # Time, human is in loss except believers
            "76:2-3",     # Created from drop, We guided the way

            # Justice and wisdom
            "21:47",      # Scales of justice for Day of Judgment
            "99:7-8",     # Atom's weight of good and evil
            "3:185",      # Every soul shall taste death
            "6:160",      # Good deeds multiplied tenfold
            "4:40",       # Allah does not wrong atom's weight
            "10:44",      # Allah wrongs not mankind at all"
        ],
        "explore": [
            # Divine nature and human relationship
            "How does the Quran reconcile divine mercy with divine justice?",
            "What does 'Allah is closer than the jugular vein' mean for spiritual practice?",
            "How do the 99 names reveal different aspects of divine reality?",
            "What is the significance of Allah responding 'I am near' to seekers?",
            "How does the Quran describe the moment of divine encounter?",
            "What does it mean that Allah is 'the Light of the heavens and earth'?",
            "How does divine predestination interact with human free will?",
            "What is the nature of divine love in Quranic theology?",
            "How does the Quran balance transcendence with immanence?",
            "What does it mean that Allah guides whom He wills?",

            # Existential and purpose questions
            "What is the Quranic answer to human suffering and evil?",
            "How does the Quran address the purpose of creation?",
            "What is the significance of being created 'in the best form'?",
            "How does the Quran explain the human capacity for both good and evil?",
            "What is the meaning of being Allah's khalifa on earth?",
            "How does the Quran view the relationship between reason and revelation?",
            "What is the nature of the covenant between Allah and humanity?",
            "How does the Quran define true success and loss?",
            "What is the significance of forgetting our primordial covenant?",
            "How does the Quran address existential anxiety and despair?",

            # Spiritual transformation and heart
            "What does the Quran mean by the 'diseased heart' and its cure?",
            "How does remembrance (dhikr) transform the human soul?",
            "What is the process of tazkiyah (purification) in Quranic spirituality?",
            "How does the Quran describe the expansion of the breast for Islam?",
            "What are the veils between humans and divine reality?",
            "How does gratitude (shukr) relate to increased divine favor?",
            "What is the relationship between tawbah and divine love?",
            "How does the Quran describe spiritual death and revival?",
            "What is the significance of the heart's role in understanding?",
            "How does certainty (yaqin) develop according to the Quran?",

            # Death, afterlife, and ultimate reality
            "How does the Quran describe the experience of death?",
            "What is the nature of the barzakh (intermediate realm)?",
            "How does divine justice manifest on the Day of Judgment?",
            "What does the Quran reveal about the nature of Paradise?",
            "How are the Fire's punishments related to earthly actions?",
            "What is the significance of intercession (shafa'ah) on Judgment Day?",
            "How does the Quran describe the transformation of reality on the Last Day?",
            "What is the meaning of 'meeting with Allah'?",
            "How does the Quran address the fear of death?",
            "What is eternal life according to Quranic teaching?",

            # Knowledge, wisdom, and guidance
            "What is the relationship between 'ilm and hikmah in the Quran?",
            "How does the Quran view the limits of human knowledge?",
            "What is the significance of pondering (tadabbur) over verses?",
            "How does divine guidance differ from human guidance?",
            "What is the role of the fitrah (primordial nature) in recognizing truth?",
            "How does the Quran address doubt and strengthen faith?",
            "What is the nature of wisdom that Allah grants to whom He wills?",
            "How do signs (ayat) in creation lead to certainty?",
            "What is the relationship between knowledge and humility?",
            "How does the Quran distinguish between conjecture and certain knowledge?"
        ]
    },

    "student": {
        "tafsir": [
            # Structured study passages
            "1:1-7",      # Al-Fatihah deep analysis
            "2:1-10",     # Opening of Baqarah
            "2:255",      # Ayatul Kursi study
            "3:1-9",      # Opening of Al-Imran
            "4:1-10",     # Opening themes
            "6:1-10",     # Creation arguments
            "7:1-10",     # Warning and creation
            "10:1-10",    # Signs and revelation
            "12:1-10",    # Opening of Surah Yusuf
            "18:1-10",    # Opening of Surah Kahf
            "19:1-10",    # Opening of Surah Maryam
            "20:1-10",    # Opening of Surah Ta-Ha
            "24:35",      # Light verse analysis
            "31:12-19",   # Luqman's wisdom
            "36:1-10",    # Opening of Ya-Sin
            "55:1-10",    # Opening of Rahman
            "56:1-10",    # Opening of Waqiah
            "67:1-10",    # Opening of Mulk

            # Research topics
            "What is the thematic structure of Surah Baqarah?",
            "How does ring composition work in Surah Yusuf?",
            "What is the chronological order of revelation?",
            "What are Makkan vs Medinan characteristics?",
            "What is the historical context of Surah Anfal?",
            "How do literary devices function in Surah Kahf?",
            "What is the coherence in Surah An-Nisa?",
            "What are rhetorical strategies in Surah Ibrahim?",

            # Analytical studies
            "Compare commentaries on verse 3:7",
            "Analyze different interpretations of verse 4:34",
            "Study variant readings of verse 2:125",
            "Historical context of verse 9:29",
            "Hadith references in verse 2:187",
            "Linguistic features of verse 19:1-11",
            "Legal principles from verse 17:32",
            "Historical background of verse 48:1-3",
            "Scholar consensus on verse 24:31",
            "Rhetorical analysis of verse 14:24-26",
            "Context of revelation for verse 66:1-5",
            "Hadith explaining verse 13:11"
        ],
        "explore": [
            # Research methodologies
            "What are the primary sources for Quranic research?",
            "How to conduct thematic analysis across the Quran?",
            "What databases and tools exist for Quranic studies?",
            "How to write an academic paper on Quranic topics?",
            "What are the citation standards in Islamic studies?",
            "How to evaluate the authenticity of hadith narrations?",
            "What methodologies exist for comparative tafsir?",
            "How to approach manuscript studies?",

            # Core academic topics
            "What is the history of Quran compilation?",
            "How did the science of tajwid develop?",
            "What are the major tafsir works and their methodologies?",
            "How has Quranic exegesis evolved over time?",
            "What are the key debates in Quranic studies?",
            "How do orientalist and traditional approaches differ?",
            "What is the role of isnad in Quranic sciences?",
            "How are pre-Islamic sources used in tafsir?",

            # Interdisciplinary approaches
            "How does linguistics contribute to Quranic understanding?",
            "What can archaeology tell us about Quranic contexts?",
            "How do literary theories apply to Quranic analysis?",
            "What is the relationship between fiqh and Quranic studies?",
            "How does philosophy intersect with Quranic thought?",
            "What psychological insights emerge from Quranic study?",
            "How do sociological methods apply to Quranic texts?",
            "What can anthropology contribute to understanding?",

            # Contemporary scholarship
            "Who are the leading contemporary Quran scholars?",
            "What are recent developments in Quranic studies?",
            "How is technology changing Quranic research?",
            "What are emerging trends in Western academia?",
            "How do Muslim and non-Muslim scholarship interact?",
            "What are the major academic conferences and journals?",
            "What funding opportunities exist for Quranic research?",
            "How to engage with international scholarly community?",

            # Specialized topics
            "What is the Birmingham manuscript's significance?",
            "How do Sanaa manuscripts impact textual history?",
            "What are the debates around orientalist translations?",
            "How reliable are computer-based stylometric analyses?",
            "What is the state of Quranic palaeography?",
            "How do cognitive linguistics apply to Quranic Arabic?",
            "What are the ethical considerations in critical studies?",
            "How to balance faith and academic objectivity?"
        ]
    }
}

# Default fallback for any undefined persona
DEFAULT_SUGGESTIONS = PERSONA_SUGGESTIONS["practicing_muslim"]