'use client';
import { useState, useEffect, useRef, useMemo } from 'react';

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

// Max verses per query
const MAX_VERSE_RANGE = 10;

// All quick select options - will be randomized
const ALL_QUICK_SELECTS = [
  { query: '2:255', label: 'Ayatul Kursi' },
  { query: '1:1-7', label: 'Al-Fatihah' },
  { query: '112:1-4', label: 'Al-Ikhlas' },
  { query: '55:1-13', label: 'Ar-Rahman' },
  { query: '36:1-12', label: 'Ya-Sin' },
  { query: '67:1-5', label: 'Al-Mulk' },
  { query: '31:12-19', label: "Luqman's Advice" },
  { query: '49:11-13', label: 'Brotherhood' },
  { query: '17:23-24', label: 'Parents' },
  { query: '12:1-6', label: 'Yusuf' },
  { query: '18:9-16', label: 'Cave Companions' },
  { query: '28:7-13', label: 'Baby Musa' },
];

export default function SurahVersePicker({ onSelect, initialSurah = null, initialVerse = null }) {
  const [selectedSurah, setSelectedSurah] = useState(initialSurah);
  const [startVerse, setStartVerse] = useState(initialVerse || '');
  const [endVerse, setEndVerse] = useState('');
  const [isRangeMode, setIsRangeMode] = useState(false);
  const [surahSearch, setSurahSearch] = useState('');
  const [showSurahDropdown, setShowSurahDropdown] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const dropdownRef = useRef(null);
  const inputRef = useRef(null);

  // Randomize 3 quick selects on mount
  const randomQuickSelects = useMemo(() => {
    const shuffled = [...ALL_QUICK_SELECTS].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, 3);
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowSurahDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter surahs based on search
  const filteredSurahs = SURAHS.filter(surah => {
    const search = surahSearch.toLowerCase();
    return (
      surah.number.toString().includes(search) ||
      surah.name.toLowerCase().includes(search) ||
      surah.englishName.toLowerCase().includes(search)
    );
  });

  const maxVerses = selectedSurah ? SURAHS.find(s => s.number === selectedSurah)?.verseCount || 0 : 0;

  const handleSurahSelect = (surah) => {
    setSelectedSurah(surah.number);
    setSurahSearch(`${surah.number}. ${surah.name}`);
    setShowSurahDropdown(false);
    setStartVerse('');
    setEndVerse('');
    setValidationError('');
  };

  const handleStartVerseChange = (value) => {
    if (value === '' || /^\d*$/.test(value)) {
      setStartVerse(value);
      setValidationError('');
    }
  };

  const handleEndVerseChange = (value) => {
    if (value === '' || /^\d*$/.test(value)) {
      setEndVerse(value);
      setValidationError('');
    }
  };

  const handleStartVerseBlur = () => {
    if (!startVerse) return;
    const num = parseInt(startVerse);
    if (isNaN(num) || num < 1) {
      setStartVerse('1');
    } else if (num > maxVerses) {
      setStartVerse(maxVerses.toString());
    }
  };

  const handleEndVerseBlur = () => {
    if (!endVerse) return;
    const num = parseInt(endVerse);
    const start = parseInt(startVerse) || 1;
    if (isNaN(num) || num < start) {
      setEndVerse(start.toString());
    } else if (num > maxVerses) {
      setEndVerse(maxVerses.toString());
    }
    if (num - start + 1 > MAX_VERSE_RANGE) {
      setValidationError(`Max ${MAX_VERSE_RANGE} verses. Range will be limited.`);
    }
  };

  const validateAndApply = () => {
    if (!selectedSurah) {
      setValidationError('Please select a surah');
      return;
    }
    if (!startVerse) {
      setValidationError('Please enter a verse number');
      return;
    }
    const start = parseInt(startVerse);
    if (start < 1 || start > maxVerses) {
      setValidationError(`Verse must be between 1 and ${maxVerses}`);
      return;
    }
    if (isRangeMode) {
      if (!endVerse) {
        setValidationError('Please enter an end verse');
        return;
      }
      let end = parseInt(endVerse);
      if (isNaN(end) || end < start) {
        setValidationError('End verse must be >= start verse');
        return;
      }
      if (end > maxVerses) end = maxVerses;
      if (end - start + 1 > MAX_VERSE_RANGE) {
        end = start + MAX_VERSE_RANGE - 1;
        if (end > maxVerses) end = maxVerses;
      }
      onSelect(`${selectedSurah}:${start}-${end}`);
    } else {
      onSelect(`${selectedSurah}:${start}`);
    }
  };

  const handleQuickSelect = (item) => {
    onSelect(item.query);
  };

  return (
    <div className="surah-verse-picker" style={{
      background: 'white',
      borderRadius: '12px',
      border: '1px solid var(--border-light, #e5e7eb)',
      padding: '12px',
      marginBottom: '12px'
    }}>
      {/* Quick Select Row - 3 horizontal buttons */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '8px'
      }}>
        {randomQuickSelects.map((item, index) => (
          <button
            key={index}
            type="button"
            onClick={() => handleQuickSelect(item)}
            style={{
              padding: '8px 6px',
              background: 'var(--cream, #faf6f0)',
              border: '1px solid var(--border-light, #e5e7eb)',
              borderRadius: '8px',
              fontSize: '0.8rem',
              color: 'var(--primary-teal, #0d9488)',
              cursor: 'pointer',
              fontWeight: '500',
              textAlign: 'center',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Expandable Browse Section */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          width: '100%',
          marginTop: '8px',
          padding: '8px 12px',
          background: 'transparent',
          border: '1px dashed var(--border-light, #e5e7eb)',
          borderRadius: '8px',
          fontSize: '0.8rem',
          color: '#666',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px'
        }}
      >
        {isExpanded ? '▲ Hide' : '▼ Browse by Surah & Verse'}
      </button>

      {isExpanded && (
        <div style={{ marginTop: '12px' }}>
          {/* Surah Selector */}
          <div style={{ marginBottom: '10px' }} ref={dropdownRef}>
            <div style={{ position: 'relative' }}>
              <input
                ref={inputRef}
                type="text"
                value={surahSearch}
                onChange={(e) => {
                  setSurahSearch(e.target.value);
                  setShowSurahDropdown(true);
                  if (!e.target.value) setSelectedSurah(null);
                }}
                onFocus={() => setShowSurahDropdown(true)}
                placeholder="Search surah..."
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid var(--border-light, #e5e7eb)',
                  borderRadius: '8px',
                  fontSize: '0.9rem',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
              {showSurahDropdown && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  right: 0,
                  maxHeight: 'min(200px, 40vh)',
                  overflowY: 'auto',
                  background: 'white',
                  border: '1px solid var(--border-light, #e5e7eb)',
                  borderTop: 'none',
                  borderRadius: '0 0 8px 8px',
                  zIndex: 100,
                  boxShadow: '0 4px 6px rgba(0, 0, 0, 0.07)'
                }}>
                  {filteredSurahs.slice(0, 20).map(surah => (
                    <div
                      key={surah.number}
                      onClick={() => handleSurahSelect(surah)}
                      style={{
                        padding: '8px 12px',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        borderBottom: '1px solid #f0f0f0',
                        display: 'flex',
                        justifyContent: 'space-between'
                      }}
                    >
                      <span><b>{surah.number}.</b> {surah.name}</span>
                      <span style={{ color: '#999', fontSize: '0.75rem' }}>{surah.verseCount}v</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Verse Selection */}
          {selectedSurah && (
            <div style={{ marginBottom: '10px' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '6px'
              }}>
                <input
                  type="number"
                  min="1"
                  max={maxVerses}
                  value={startVerse}
                  onChange={(e) => handleStartVerseChange(e.target.value)}
                  onBlur={handleStartVerseBlur}
                  placeholder={`Verse (1-${maxVerses})`}
                  style={{
                    flex: 1,
                    padding: '8px 10px',
                    border: '1px solid var(--border-light, #e5e7eb)',
                    borderRadius: '6px',
                    fontSize: '0.9rem',
                    outline: 'none'
                  }}
                />
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.8rem',
                  color: '#666'
                }}>
                  <input
                    type="checkbox"
                    checked={isRangeMode}
                    onChange={(e) => {
                      setIsRangeMode(e.target.checked);
                      if (!e.target.checked) {
                        setEndVerse('');
                        setValidationError('');
                      }
                    }}
                  />
                  Range
                </label>
                {isRangeMode && (
                  <input
                    type="number"
                    min={parseInt(startVerse) || 1}
                    max={maxVerses}
                    value={endVerse}
                    onChange={(e) => handleEndVerseChange(e.target.value)}
                    onBlur={handleEndVerseBlur}
                    placeholder="End"
                    style={{
                      width: '70px',
                      padding: '8px 10px',
                      border: '1px solid var(--border-light, #e5e7eb)',
                      borderRadius: '6px',
                      fontSize: '0.9rem',
                      outline: 'none'
                    }}
                  />
                )}
              </div>
            </div>
          )}

          {/* Validation Error */}
          {validationError && (
            <div style={{
              padding: '6px 10px',
              background: 'rgba(239, 68, 68, 0.1)',
              borderRadius: '6px',
              marginBottom: '8px',
              fontSize: '0.8rem',
              color: '#dc2626'
            }}>
              {validationError}
            </div>
          )}

          {/* Apply Button */}
          <button
            type="button"
            onClick={validateAndApply}
            disabled={!selectedSurah}
            style={{
              width: '100%',
              padding: '10px',
              background: selectedSurah ? 'var(--primary-teal, #0d9488)' : '#e5e7eb',
              color: selectedSurah ? 'white' : '#9ca3af',
              border: 'none',
              borderRadius: '8px',
              fontSize: '0.9rem',
              fontWeight: '600',
              cursor: selectedSurah ? 'pointer' : 'not-allowed'
            }}
          >
            {selectedSurah && startVerse
              ? `Get ${selectedSurah}:${startVerse}${isRangeMode && endVerse ? `-${endVerse}` : ''}`
              : 'Select Surah & Verse'}
          </button>
        </div>
      )}
    </div>
  );
}

export { SURAHS };
