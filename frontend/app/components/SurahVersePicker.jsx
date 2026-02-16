'use client';
import { useState, useMemo, useEffect } from 'react';
import { BACKEND_URL } from '../lib/config';

// Complete list of all 114 surahs with their verse counts
const SURAHS = [
  { number: 1, name: 'Al-Fatihah', englishName: 'The Opening', verseCount: 7 },
  { number: 2, name: 'Al-Baqarah', englishName: 'The Cow', verseCount: 286 },
  { number: 3, name: 'Ali Imran', englishName: 'Family of Imran', verseCount: 200 },
  { number: 4, name: 'An-Nisa', englishName: 'The Women', verseCount: 176 },
  { number: 5, name: "Al-Ma'idah", englishName: 'The Table Spread', verseCount: 120 },
  { number: 6, name: "Al-An'am", englishName: 'The Cattle', verseCount: 165 },
  { number: 7, name: "Al-A'raf", englishName: 'The Heights', verseCount: 206 },
  { number: 8, name: 'Al-Anfal', englishName: 'The Spoils of War', verseCount: 75 },
  { number: 9, name: 'At-Tawbah', englishName: 'The Repentance', verseCount: 129 },
  { number: 10, name: 'Yunus', englishName: 'Jonah', verseCount: 109 },
  { number: 11, name: 'Hud', englishName: 'Hud', verseCount: 123 },
  { number: 12, name: 'Yusuf', englishName: 'Joseph', verseCount: 111 },
  { number: 13, name: "Ar-Ra'd", englishName: 'The Thunder', verseCount: 43 },
  { number: 14, name: 'Ibrahim', englishName: 'Abraham', verseCount: 52 },
  { number: 15, name: 'Al-Hijr', englishName: 'The Rocky Tract', verseCount: 99 },
  { number: 16, name: 'An-Nahl', englishName: 'The Bee', verseCount: 128 },
  { number: 17, name: 'Al-Isra', englishName: 'The Night Journey', verseCount: 111 },
  { number: 18, name: 'Al-Kahf', englishName: 'The Cave', verseCount: 110 },
  { number: 19, name: 'Maryam', englishName: 'Mary', verseCount: 98 },
  { number: 20, name: 'Ta-Ha', englishName: 'Ta-Ha', verseCount: 135 },
  { number: 21, name: 'Al-Anbya', englishName: 'The Prophets', verseCount: 112 },
  { number: 22, name: 'Al-Hajj', englishName: 'The Pilgrimage', verseCount: 78 },
  { number: 23, name: "Al-Mu'minun", englishName: 'The Believers', verseCount: 118 },
  { number: 24, name: 'An-Nur', englishName: 'The Light', verseCount: 64 },
  { number: 25, name: 'Al-Furqan', englishName: 'The Criterion', verseCount: 77 },
  { number: 26, name: "Ash-Shu'ara", englishName: 'The Poets', verseCount: 227 },
  { number: 27, name: 'An-Naml', englishName: 'The Ant', verseCount: 93 },
  { number: 28, name: 'Al-Qasas', englishName: 'The Stories', verseCount: 88 },
  { number: 29, name: "Al-'Ankabut", englishName: 'The Spider', verseCount: 69 },
  { number: 30, name: 'Ar-Rum', englishName: 'The Romans', verseCount: 60 },
  { number: 31, name: 'Luqman', englishName: 'Luqman', verseCount: 34 },
  { number: 32, name: 'As-Sajdah', englishName: 'The Prostration', verseCount: 30 },
  { number: 33, name: 'Al-Ahzab', englishName: 'The Confederates', verseCount: 73 },
  { number: 34, name: 'Saba', englishName: 'Sheba', verseCount: 54 },
  { number: 35, name: 'Fatir', englishName: 'Originator', verseCount: 45 },
  { number: 36, name: 'Ya-Sin', englishName: 'Ya-Sin', verseCount: 83 },
  { number: 37, name: 'As-Saffat', englishName: 'Those in Ranks', verseCount: 182 },
  { number: 38, name: 'Sad', englishName: 'Sad', verseCount: 88 },
  { number: 39, name: 'Az-Zumar', englishName: 'The Crowds', verseCount: 75 },
  { number: 40, name: 'Ghafir', englishName: 'The Forgiver', verseCount: 85 },
  { number: 41, name: 'Fussilat', englishName: 'Explained in Detail', verseCount: 54 },
  { number: 42, name: 'Ash-Shura', englishName: 'The Consultation', verseCount: 53 },
  { number: 43, name: 'Az-Zukhruf', englishName: 'The Gold Adornments', verseCount: 89 },
  { number: 44, name: 'Ad-Dukhan', englishName: 'The Smoke', verseCount: 59 },
  { number: 45, name: 'Al-Jathiyah', englishName: 'The Crouching', verseCount: 37 },
  { number: 46, name: 'Al-Ahqaf', englishName: 'The Wind-Curved Sandhills', verseCount: 35 },
  { number: 47, name: 'Muhammad', englishName: 'Muhammad', verseCount: 38 },
  { number: 48, name: 'Al-Fath', englishName: 'The Victory', verseCount: 29 },
  { number: 49, name: 'Al-Hujurat', englishName: 'The Rooms', verseCount: 18 },
  { number: 50, name: 'Qaf', englishName: 'Qaf', verseCount: 45 },
  { number: 51, name: 'Adh-Dhariyat', englishName: 'The Winnowing Winds', verseCount: 60 },
  { number: 52, name: 'At-Tur', englishName: 'The Mount', verseCount: 49 },
  { number: 53, name: 'An-Najm', englishName: 'The Star', verseCount: 62 },
  { number: 54, name: 'Al-Qamar', englishName: 'The Moon', verseCount: 55 },
  { number: 55, name: 'Ar-Rahman', englishName: 'The Beneficent', verseCount: 78 },
  { number: 56, name: "Al-Waqi'ah", englishName: 'The Inevitable', verseCount: 96 },
  { number: 57, name: 'Al-Hadid', englishName: 'The Iron', verseCount: 29 },
  { number: 58, name: 'Al-Mujadila', englishName: 'The Pleading Woman', verseCount: 22 },
  { number: 59, name: 'Al-Hashr', englishName: 'The Exile', verseCount: 24 },
  { number: 60, name: 'Al-Mumtahanah', englishName: 'She That is Examined', verseCount: 13 },
  { number: 61, name: 'As-Saff', englishName: 'The Ranks', verseCount: 14 },
  { number: 62, name: "Al-Jumu'ah", englishName: 'The Congregation', verseCount: 11 },
  { number: 63, name: 'Al-Munafiqun', englishName: 'The Hypocrites', verseCount: 11 },
  { number: 64, name: 'At-Taghabun', englishName: 'The Mutual Disillusion', verseCount: 18 },
  { number: 65, name: 'At-Talaq', englishName: 'The Divorce', verseCount: 12 },
  { number: 66, name: 'At-Tahrim', englishName: 'The Prohibition', verseCount: 12 },
  { number: 67, name: 'Al-Mulk', englishName: 'The Sovereignty', verseCount: 30 },
  { number: 68, name: 'Al-Qalam', englishName: 'The Pen', verseCount: 52 },
  { number: 69, name: 'Al-Haqqah', englishName: 'The Reality', verseCount: 52 },
  { number: 70, name: "Al-Ma'arij", englishName: 'The Ascending Stairways', verseCount: 44 },
  { number: 71, name: 'Nuh', englishName: 'Noah', verseCount: 28 },
  { number: 72, name: 'Al-Jinn', englishName: 'The Jinn', verseCount: 28 },
  { number: 73, name: 'Al-Muzzammil', englishName: 'The Enshrouded One', verseCount: 20 },
  { number: 74, name: 'Al-Muddaththir', englishName: 'The Cloaked One', verseCount: 56 },
  { number: 75, name: 'Al-Qiyamah', englishName: 'The Resurrection', verseCount: 40 },
  { number: 76, name: 'Al-Insan', englishName: 'The Human', verseCount: 31 },
  { number: 77, name: 'Al-Mursalat', englishName: 'The Emissaries', verseCount: 50 },
  { number: 78, name: 'An-Naba', englishName: 'The Tidings', verseCount: 40 },
  { number: 79, name: "An-Nazi'at", englishName: 'Those Who Drag Forth', verseCount: 46 },
  { number: 80, name: 'Abasa', englishName: 'He Frowned', verseCount: 42 },
  { number: 81, name: 'At-Takwir', englishName: 'The Overthrowing', verseCount: 29 },
  { number: 82, name: 'Al-Infitar', englishName: 'The Cleaving', verseCount: 19 },
  { number: 83, name: 'Al-Mutaffifin', englishName: 'The Defrauding', verseCount: 36 },
  { number: 84, name: 'Al-Inshiqaq', englishName: 'The Sundering', verseCount: 25 },
  { number: 85, name: 'Al-Buruj', englishName: 'The Mansions of the Stars', verseCount: 22 },
  { number: 86, name: 'At-Tariq', englishName: 'The Night Comer', verseCount: 17 },
  { number: 87, name: "Al-A'la", englishName: 'The Most High', verseCount: 19 },
  { number: 88, name: 'Al-Ghashiyah', englishName: 'The Overwhelming', verseCount: 26 },
  { number: 89, name: 'Al-Fajr', englishName: 'The Dawn', verseCount: 30 },
  { number: 90, name: 'Al-Balad', englishName: 'The City', verseCount: 20 },
  { number: 91, name: 'Ash-Shams', englishName: 'The Sun', verseCount: 15 },
  { number: 92, name: 'Al-Layl', englishName: 'The Night', verseCount: 21 },
  { number: 93, name: 'Ad-Duhaa', englishName: 'The Morning Hours', verseCount: 11 },
  { number: 94, name: 'Ash-Sharh', englishName: 'The Relief', verseCount: 8 },
  { number: 95, name: 'At-Tin', englishName: 'The Fig', verseCount: 8 },
  { number: 96, name: "Al-'Alaq", englishName: 'The Clot', verseCount: 19 },
  { number: 97, name: 'Al-Qadr', englishName: 'The Power', verseCount: 5 },
  { number: 98, name: 'Al-Bayyinah', englishName: 'The Clear Proof', verseCount: 8 },
  { number: 99, name: 'Az-Zalzalah', englishName: 'The Earthquake', verseCount: 8 },
  { number: 100, name: "Al-'Adiyat", englishName: 'The Courser', verseCount: 11 },
  { number: 101, name: "Al-Qari'ah", englishName: 'The Calamity', verseCount: 11 },
  { number: 102, name: 'At-Takathur', englishName: 'The Rivalry in World Increase', verseCount: 8 },
  { number: 103, name: "Al-'Asr", englishName: 'The Declining Day', verseCount: 3 },
  { number: 104, name: 'Al-Humazah', englishName: 'The Traducer', verseCount: 9 },
  { number: 105, name: 'Al-Fil', englishName: 'The Elephant', verseCount: 5 },
  { number: 106, name: 'Quraysh', englishName: 'Quraysh', verseCount: 4 },
  { number: 107, name: "Al-Ma'un", englishName: 'The Small Kindnesses', verseCount: 7 },
  { number: 108, name: 'Al-Kawthar', englishName: 'The Abundance', verseCount: 3 },
  { number: 109, name: 'Al-Kafirun', englishName: 'The Disbelievers', verseCount: 6 },
  { number: 110, name: 'An-Nasr', englishName: 'The Divine Support', verseCount: 3 },
  { number: 111, name: 'Al-Masad', englishName: 'The Palm Fiber', verseCount: 5 },
  { number: 112, name: 'Al-Ikhlas', englishName: 'The Sincerity', verseCount: 4 },
  { number: 113, name: 'Al-Falaq', englishName: 'The Daybreak', verseCount: 5 },
  { number: 114, name: 'An-Nas', englishName: 'The Mankind', verseCount: 6 }
];

// Max verses per query (matches backend ABSOLUTE_MAX_VERSES)
const MAX_VERSE_RANGE = 5;

// 120+ commonly referenced Quranic verses — randomized on each visit
const ALL_QUICK_SELECTS = [
  // Core essentials
  { query: '1:1-7', label: 'The Mother of the Quran' },
  { query: '2:255', label: 'The Throne Verse' },
  { query: '112:1-4', label: 'A Third of the Quran' },
  { query: '113:1-5', label: 'Refuge from Outer Evil' },
  { query: '114:1-6', label: 'Refuge from Inner Evil' },
  { query: '36:1-5', label: 'The Heart of the Quran' },
  { query: '55:1-5', label: 'The Lord of Majesty' },
  { query: '67:1-5', label: 'Protector from the Grave' },
  { query: '56:1-7', label: 'The Three Groups' },
  { query: '78:1-5', label: 'The Great Questioning' },

  // Tawbah & mercy
  { query: '39:53', label: 'The Most Hopeful Verse' },
  { query: '2:186', label: 'Divine Nearness' },
  { query: '40:60', label: 'Promise of Answered Dua' },
  { query: '3:135', label: 'Immediate Return to Allah' },
  { query: '4:110', label: 'The Door of Tawbah' },
  { query: '11:90', label: "Shu'ayb's Call to Mercy" },
  { query: '66:8', label: 'Sincere Repentance' },
  { query: '25:70', label: 'Sins Become Good Deeds' },
  { query: '42:25', label: 'The One Who Pardons' },

  // Patience & trials
  { query: '2:153', label: 'The Command of Sabr' },
  { query: '2:155-157', label: 'Promise to the Tested' },
  { query: '94:5-6', label: 'Ease After Hardship' },
  { query: '65:2-3', label: 'The Tawakkul Covenant' },
  { query: '29:2-3', label: 'The Purpose of Trials' },
  { query: '3:200', label: 'Persevere Together' },
  { query: '39:10', label: 'Boundless Reward of Sabr' },
  { query: '12:87', label: "Ya'qub's Hope" },
  { query: '21:83-84', label: "Ayyub's Cry to His Lord" },

  // Tawakkul & reliance
  { query: '3:159', label: 'Trust in Allah' },
  { query: '9:51', label: 'The Verse of Qadr' },
  { query: '8:2-4', label: 'Marks of True Iman' },
  { query: '14:12', label: 'The Prophets\' Trust' },
  { query: '33:3', label: 'Allah as Sole Protector' },
  { query: '64:13', label: 'Sufficiency of Allah' },

  // Guidance & knowledge
  { query: '2:2-5', label: 'Opening of Al-Baqarah' },
  { query: '20:114', label: 'Dua for Knowledge' },
  { query: '96:1-5', label: 'The First Revelation' },
  { query: '39:9', label: 'Those Who Know' },
  { query: '35:28', label: 'True Khashyah' },
  { query: '58:11', label: 'Elevated in Ranks' },
  { query: '3:7', label: 'Muhkam & Mutashabih' },
  { query: '16:43', label: 'Ask People of Knowledge' },

  // Character & conduct
  { query: '17:23-24', label: 'The Rights of Parents' },
  { query: '31:12-19', label: "Luqman's Counsels" },
  { query: '49:11-13', label: 'Etiquette of Believers' },
  { query: '49:6', label: 'The Verse of Verification' },
  { query: '3:134', label: 'Restraining Anger' },
  { query: '25:63-67', label: "'Ibad ar-Rahman" },
  { query: '25:72', label: 'Avoiding False Witness' },
  { query: '33:70', label: 'Command of Truthful Speech' },
  { query: '16:90', label: 'Justice & Kindness' },
  { query: '4:135', label: 'Standing for Justice' },
  { query: '5:8', label: 'Just Even to Enemies' },
  { query: '41:34', label: 'Repel Evil with Good' },
  { query: '24:27', label: 'Adab of Permission' },
  { query: '2:263', label: 'A Kind Word' },
  { query: '17:36', label: 'Follow with Knowledge' },
  { query: '49:12', label: 'Prohibition of Backbiting' },

  // Gratitude & dhikr
  { query: '14:7', label: 'The Law of Shukr' },
  { query: '2:152', label: 'Remember Me' },
  { query: '33:41-42', label: 'Abundant Dhikr' },
  { query: '13:28', label: 'Hearts at Rest' },
  { query: '76:3', label: 'The Gift of Choice' },
  { query: '31:12', label: "Luqman's Gratitude" },

  // Prophetic stories
  { query: '12:1-5', label: "Yusuf's Dream" },
  { query: '12:86-87', label: "Ya'qub's Hope" },
  { query: '18:9-13', label: 'Sleepers of the Cave' },
  { query: '18:60-65', label: 'Musa & Al-Khidr' },
  { query: '28:7-9', label: 'Rescue of Baby Musa' },
  { query: '19:16-21', label: 'Maryam & the Angel' },
  { query: '21:87-88', label: "Yunus's Cry" },
  { query: '38:41-44', label: "Ayyub's Healing" },
  { query: '27:15-19', label: 'Sulayman & the Ant' },
  { query: '2:260', label: "Ibrahim's Certainty" },
  { query: '37:102-107', label: "Ibrahim's Sacrifice" },
  { query: '20:25-28', label: "Musa's Dua" },
  { query: '3:38-41', label: "Zakariyya's Prayer" },
  { query: '12:30-33', label: "Yusuf's Chastity" },
  { query: '20:9-14', label: 'The Burning Bush' },

  // Dua & supplication
  { query: '2:201', label: 'The Most Recited Dua' },
  { query: '3:8', label: 'Dua for a Firm Heart' },
  { query: '23:118', label: 'The Seal of Mercy' },
  { query: '7:23', label: "Adam's Repentance" },
  { query: '2:286', label: 'No Unbearable Burden' },
  { query: '3:26-27', label: 'Sovereignty of Allah' },
  { query: '14:40-41', label: "Ibrahim's Dua" },
  { query: '25:74', label: 'Righteous Family Dua' },

  // Tawheed & nature of Allah
  { query: '59:22-24', label: 'Names of Al-Hashr' },
  { query: '24:35', label: 'The Verse of Light' },
  { query: '57:3', label: 'The First & the Last' },
  { query: '42:11', label: 'Nothing Is Like Him' },
  { query: '6:103', label: 'Beyond All Vision' },
  { query: '2:115', label: 'Wherever You Turn' },
  { query: '50:16', label: 'Closer Than Jugular' },
  { query: '35:15', label: 'Allah Needs None' },

  // Afterlife & accountability
  { query: '99:1-8', label: "Earth's Testimony" },
  { query: '82:1-5', label: 'The Shattering Sky' },
  { query: '81:1-7', label: 'When Sun Is Folded' },
  { query: '101:1-5', label: 'The Striking Hour' },
  { query: '23:99-100', label: 'The Regret at Death' },
  { query: '102:1-8', label: 'Distracted by Piling Up' },
  { query: '3:185', label: 'Every Soul Tastes Death' },
  { query: '18:49', label: 'Book That Misses Nothing' },
  { query: '17:13-14', label: 'Read Your Own Record' },

  // Women & family
  { query: '4:1', label: 'Created from One Soul' },
  { query: '30:21', label: 'Love & Mercy' },
  { query: '66:11', label: "Pharaoh's Believing Wife" },
  { query: '3:35-37', label: "Hannah's Dedication" },
  { query: '46:15', label: 'Rights of the Mother' },
  { query: '4:19', label: 'Treat Wives with Kindness' },

  // Wealth & charity
  { query: '2:261', label: 'Charity Multiplied' },
  { query: '2:274', label: 'Give in Secret & Open' },
  { query: '57:7', label: 'Spend from His Trust' },
  { query: '63:9', label: "Wealth Won't Distract" },
  { query: '9:34-35', label: 'Warning Against Hoarding' },
  { query: '28:77', label: 'Seek the Hereafter' },

  // Nature & signs
  { query: '3:190-191', label: 'Signs in Creation' },
  { query: '51:47-49', label: 'The Expanding Heavens' },
  { query: '21:30', label: 'Every Life from Water' },
  { query: '16:68-69', label: 'Revelation to the Bee' },
  { query: '6:95', label: 'Splitter of Seed' },
  { query: '30:22', label: 'Diversity as a Sign' },

  // Short powerful surahs
  { query: '103:1-3', label: "Shafi'i's Sufficient Surah" },
  { query: '108:1-3', label: 'Al-Kawthar' },
  { query: '107:1-7', label: 'Neglect of Kindness' },
  { query: '104:1-4', label: 'The Scandal-Monger' },
  { query: '105:1-5', label: 'The Army of Abraha' },
  { query: '109:1-6', label: 'Declaration of Tawheed' },
  { query: '110:1-3', label: 'The Final Surah' },
];

export default function SurahVersePicker({ onSelect, initialSurah = null, initialVerse = null, externalSurah = null, externalVerse = null }) {
  const [selectedSurah, setSelectedSurah] = useState(initialSurah || '');
  const [startVerse, setStartVerse] = useState(initialVerse || '');
  const [endVerse, setEndVerse] = useState('');

  // Sync dropdown when navigating via cross-reference click
  useEffect(() => {
    if (externalSurah) {
      setSelectedSurah(String(externalSurah));
      setStartVerse(externalVerse ? String(externalVerse) : '');
      setEndVerse('');
    }
  }, [externalSurah, externalVerse]);

  // Randomize 3 quick selects on mount
  const randomQuickSelects = useMemo(() => {
    const shuffled = [...ALL_QUICK_SELECTS].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, 3);
  }, []);

  // Get verse count for selected surah
  const maxVerses = selectedSurah ? SURAHS.find(s => s.number === parseInt(selectedSurah))?.verseCount || 0 : 0;

  // Dynamic range limit from backend token budget
  const [dynamicMaxEnd, setDynamicMaxEnd] = useState(null);

  useEffect(() => {
    if (!selectedSurah || !startVerse) {
      setDynamicMaxEnd(null);
      return;
    }
    let cancelled = false;
    fetch(`${BACKEND_URL}/range-limit?surah=${selectedSurah}&start=${startVerse}`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (!cancelled && data) setDynamicMaxEnd(data.maxEnd);
      })
      .catch(() => {
        if (!cancelled) setDynamicMaxEnd(null);
      });
    return () => { cancelled = true; };
  }, [selectedSurah, startVerse]);

  // Clamp endVerse if it now exceeds the dynamic limit
  useEffect(() => {
    if (dynamicMaxEnd !== null && endVerse && parseInt(endVerse) > dynamicMaxEnd) {
      setEndVerse(String(dynamicMaxEnd));
    }
  }, [dynamicMaxEnd, endVerse]);

  // Generate verse options array
  const verseOptions = useMemo(() => {
    if (!maxVerses) return [];
    return Array.from({ length: maxVerses }, (_, i) => i + 1);
  }, [maxVerses]);

  // Generate end verse options — use dynamic limit when available, static fallback otherwise
  const endVerseOptions = useMemo(() => {
    if (!startVerse || !maxVerses) return [];
    const start = parseInt(startVerse);
    const staticMax = Math.min(start + MAX_VERSE_RANGE - 1, maxVerses);
    const effectiveMax = dynamicMaxEnd !== null
      ? Math.min(dynamicMaxEnd, maxVerses)
      : staticMax;
    return Array.from({ length: effectiveMax - start + 1 }, (_, i) => start + i);
  }, [startVerse, maxVerses, dynamicMaxEnd]);

  // Whether the dynamic limit is tighter than the static 10-verse cap
  const isDynamicallyLimited = useMemo(() => {
    if (!startVerse || !maxVerses || dynamicMaxEnd === null) return false;
    const start = parseInt(startVerse);
    const staticMax = Math.min(start + MAX_VERSE_RANGE - 1, maxVerses);
    return dynamicMaxEnd < staticMax;
  }, [startVerse, maxVerses, dynamicMaxEnd]);

  const handleSurahChange = (e) => {
    const value = e.target.value;
    setSelectedSurah(value);
    setStartVerse('');
    setEndVerse('');
  };

  const handleStartVerseChange = (e) => {
    const value = e.target.value;
    setStartVerse(value);
    setEndVerse('');
  };

  const handleEndVerseChange = (e) => {
    setEndVerse(e.target.value);
  };

  const handleApply = () => {
    if (!selectedSurah || !startVerse) return;

    const end = endVerse || startVerse;
    if (parseInt(end) > parseInt(startVerse)) {
      onSelect(`${selectedSurah}:${startVerse}-${end}`);
    } else {
      onSelect(`${selectedSurah}:${startVerse}`);
    }
  };

  const handleQuickSelect = (item) => {
    onSelect(item.query);
  };

  const canApply = selectedSurah && startVerse;

  // Shared select styles
  const selectStyle = {
    padding: '10px 14px',
    border: '1px solid var(--border-light, #e5e7eb)',
    borderRadius: '8px',
    fontSize: '16px',
    background: 'white',
    color: '#333',
    outline: 'none',
    cursor: 'pointer',
    appearance: 'none',
    WebkitAppearance: 'none',
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 12px center',
    paddingRight: '36px'
  };

  return (
    <div style={{
      background: 'white',
      borderRadius: '10px',
      padding: '12px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      marginBottom: '16px'
    }}>
      {/* Quick Select Buttons */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '8px',
        marginBottom: '16px'
      }}>
        {randomQuickSelects.map((item, index) => (
          <button
            key={index}
            type="button"
            onClick={() => handleQuickSelect(item)}
            style={{
              padding: '6px 5px',
              background: 'white',
              border: '1px solid var(--primary-teal, #0d9488)',
              borderRadius: '8px',
              fontSize: '0.68rem',
              lineHeight: '1.3',
              color: 'var(--primary-teal, #0d9488)',
              cursor: 'pointer',
              fontWeight: '600',
              textAlign: 'center',
              transition: 'all 0.2s ease',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--primary-teal, #0d9488)';
              e.currentTarget.style.color = 'white';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'white';
              e.currentTarget.style.color = 'var(--primary-teal, #0d9488)';
            }}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Surah Dropdown */}
      <div style={{ marginBottom: '12px' }}>
        <select
          value={selectedSurah}
          onChange={handleSurahChange}
          style={{ ...selectStyle, width: '100%', fontWeight: '500' }}
        >
          <option value="">Select Surah</option>
          {SURAHS.map(surah => (
            <option key={surah.number} value={surah.number}>
              {surah.number}. {surah.name}
            </option>
          ))}
        </select>
      </div>

      {/* Verse Dropdowns - Only show when surah is selected */}
      {selectedSurah && (
        <>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr auto 1fr',
            gap: '10px',
            alignItems: 'center',
            marginBottom: '12px'
          }}>
            {/* Start Verse */}
            <select
              value={startVerse}
              onChange={handleStartVerseChange}
              style={selectStyle}
            >
              <option value="">From</option>
              {verseOptions.map(v => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>

            {/* Separator */}
            <span style={{
              color: 'var(--text-muted, #6b7280)',
              fontSize: '0.9rem',
              fontWeight: '500'
            }}>—</span>

            {/* End Verse */}
            <select
              value={endVerse || startVerse}
              onChange={handleEndVerseChange}
              style={selectStyle}
              disabled={!startVerse}
            >
              <option value="">To</option>
              {startVerse && endVerseOptions.map(v => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </div>

          {/* Range limit info */}
          {isDynamicallyLimited && (
            <div style={{
              fontSize: '0.78rem',
              color: 'var(--text-muted, #6b7280)',
              marginBottom: '10px',
              padding: '6px 10px',
              background: 'rgba(13, 148, 136, 0.06)',
              borderRadius: '6px',
              borderLeft: '3px solid var(--primary-teal, #0d9488)',
              lineHeight: '1.4',
            }}>
              Range limited to {dynamicMaxEnd - parseInt(startVerse) + 1} verse{dynamicMaxEnd - parseInt(startVerse) + 1 !== 1 ? 's' : ''} based on verse length and included scholarly commentary.
            </div>
          )}

          {/* Apply Button */}
          <button
            type="button"
            onClick={handleApply}
            disabled={!canApply}
            style={{
              width: '100%',
              padding: '12px',
              background: canApply ? 'var(--primary-teal, #0d9488)' : '#cbd5e0',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '0.95rem',
              fontWeight: '600',
              cursor: canApply ? 'pointer' : 'not-allowed',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => {
              if (canApply) {
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 4px 8px rgba(13, 148, 136, 0.3)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            {canApply
              ? `Get ${selectedSurah}:${startVerse}${(endVerse || startVerse) !== startVerse && parseInt(endVerse || startVerse) > parseInt(startVerse) ? `-${endVerse}` : ''}`
              : 'Select Surah & Verse'}
          </button>
        </>
      )}
    </div>
  );
}

export { SURAHS };
