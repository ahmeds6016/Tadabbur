'use client';
import { useState, useEffect } from 'react';
import { getAuth, onAuthStateChanged } from 'firebase/auth';
import { initializeApp, getApps } from 'firebase/app';
import Link from 'next/link';

const firebaseConfig = {
  apiKey: "AIzaSyBKPuVvuJC1bTUsZsZkiMHRoBRRqF6YqVU",
  authDomain: "tafsir-simplified-6b262.firebaseapp.com",
  projectId: "tafsir-simplified-6b262",
  storageBucket: "tafsir-simplified-6b262.appspot.com",
  messagingSenderId: "69730898944",
  appId: "1:69730898944:web:ee2cbeee72be8d856474e5",
  measurementId: "G-7RZD1G66YH"
};

const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
const auth = getAuth(app);

const BACKEND_URL = 'https://tafsir-backend-612616741510.us-central1.run.app';

const ANNOTATION_TYPE_CONFIG = {
  personal_insight: { icon: '💡', label: 'Insight', color: '#0D9488' },
  question: { icon: '❓', label: 'Question', color: '#8B5CF6' },
  application: { icon: '✅', label: 'Application', color: '#059669' },
  memory: { icon: '💭', label: 'Memory', color: '#3B82F6' },
  connection: { icon: '🔗', label: 'Connection', color: '#D97706' },
  dua: { icon: '🤲', label: 'Dua/Prayer', color: '#10B981' },
  gratitude: { icon: '🙏', label: 'Gratitude', color: '#F59E0B' },
  reminder: { icon: '⏰', label: 'Reminder', color: '#EF4444' },
  story: { icon: '📚', label: 'Story', color: '#6366F1' },
  linguistic: { icon: '📝', label: 'Linguistic', color: '#84CC16' },
  historical: { icon: '📜', label: 'Historical', color: '#A78BFA' },
  scientific: { icon: '🔬', label: 'Scientific', color: '#06B6D4' },
  personal_experience: { icon: '💭', label: 'Experience', color: '#EC4899' },
  teaching_point: { icon: '👨‍🏫', label: 'Teaching', color: '#F97316' },
  warning: { icon: '⚠️', label: 'Warning', color: '#DC2626' },
  goal: { icon: '🎯', label: 'Goal', color: '#059669' },
  contemplation: { icon: '🤔', label: 'Contemplation', color: '#7C3AED' }
};

// Helper function to get config for any type (including custom ones)
const getTypeConfig = (type) => {
  if (ANNOTATION_TYPE_CONFIG[type]) {
    return ANNOTATION_TYPE_CONFIG[type];
  }
  // For custom types, use default styling
  return {
    icon: '✨',
    label: type ? type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, ' ') : 'Custom',
    color: '#6B7280'
  };
};

// Reflection Calendar Component
function ReflectionCalendar({ annotations }) {
  const today = new Date();
  const currentMonth = today.getMonth();
  const currentYear = today.getFullYear();

  // Create activity map for the calendar
  const activityMap = new Map();
  annotations.forEach(annotation => {
    if (annotation.createdAt?.seconds) {
      const date = new Date(annotation.createdAt.seconds * 1000);
      const dateKey = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
      activityMap.set(dateKey, (activityMap.get(dateKey) || 0) + 1);
    }
  });

  // Generate calendar days
  const firstDay = new Date(currentYear, currentMonth, 1).getDay();
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
  const days = [];

  // Add empty cells for days before month starts
  for (let i = 0; i < firstDay; i++) {
    days.push(null);
  }

  // Add days of the month
  for (let day = 1; day <= daysInMonth; day++) {
    days.push(day);
  }

  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];

  return (
    <div>
      <h3 style={{
        textAlign: 'center',
        marginBottom: '20px',
        color: 'var(--foreground)',
        fontSize: '1.2rem'
      }}>
        {monthNames[currentMonth]} {currentYear}
      </h3>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        gap: '4px',
        marginBottom: '16px'
      }}>
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
          <div
            key={day}
            style={{
              textAlign: 'center',
              fontSize: '0.75rem',
              fontWeight: '700',
              color: '#666',
              padding: '8px 0'
            }}
          >
            {day}
          </div>
        ))}

        {days.map((day, index) => {
          const dateKey = day ? `${currentYear}-${currentMonth}-${day}` : null;
          const count = dateKey ? activityMap.get(dateKey) || 0 : 0;
          const isToday = day === today.getDate();

          // Color intensity based on number of reflections
          const getBackgroundColor = () => {
            if (!day) return 'transparent';
            if (count === 0) return '#f3f4f6';
            if (count === 1) return 'rgba(13, 148, 136, 0.2)';
            if (count === 2) return 'rgba(13, 148, 136, 0.4)';
            if (count === 3) return 'rgba(13, 148, 136, 0.6)';
            return 'rgba(13, 148, 136, 0.8)';
          };

          return (
            <div
              key={index}
              style={{
                aspectRatio: '1',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                background: getBackgroundColor(),
                borderRadius: '8px',
                border: isToday ? '2px solid var(--gold)' : '1px solid #e5e7eb',
                cursor: day ? 'pointer' : 'default',
                position: 'relative',
                transition: 'all 0.3s ease'
              }}
              title={count > 0 ? `${count} reflection${count > 1 ? 's' : ''}` : ''}
            >
              {day && (
                <>
                  <div style={{
                    fontSize: '0.9rem',
                    fontWeight: isToday ? '700' : '500',
                    color: count > 2 ? 'white' : 'var(--foreground)'
                  }}>
                    {day}
                  </div>
                  {count > 0 && (
                    <div style={{
                      fontSize: '0.65rem',
                      fontWeight: '600',
                      color: count > 2 ? 'white' : 'var(--primary-teal)',
                      marginTop: '2px'
                    }}>
                      {count}
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '16px',
        marginTop: '20px',
        fontSize: '0.85rem'
      }}>
        <span style={{ color: '#666' }}>Less</span>
        {[0, 1, 2, 3, 4].map(level => (
          <div
            key={level}
            style={{
              width: '20px',
              height: '20px',
              borderRadius: '4px',
              background: level === 0 ? '#f3f4f6' :
                `rgba(13, 148, 136, ${level * 0.2})`,
              border: '1px solid #e5e7eb'
            }}
          />
        ))}
        <span style={{ color: '#666' }}>More</span>
      </div>
    </div>
  );
}

export default function MyReflectionsPage() {
  const [user, setUser] = useState(null);
  const [annotations, setAnnotations] = useState([]);
  const [allTags, setAllTags] = useState([]);
  const [selectedTag, setSelectedTag] = useState(null);
  const [selectedType, setSelectedType] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  const [sortBy, setSortBy] = useState('newest');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [showStats, setShowStats] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [selectedTags, setSelectedTags] = useState([]);
  const [showCalendar, setShowCalendar] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        await Promise.all([fetchAnnotations(currentUser), fetchTags(currentUser)]);
      }
      setIsLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const fetchAnnotations = async (currentUser, tag = null, type = null) => {
    try {
      const token = await currentUser.getIdToken();
      let url = `${BACKEND_URL}/annotations/user?limit=100`;
      if (tag) url += `&tag=${encodeURIComponent(tag)}`;
      if (type) url += `&type=${type}`;

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setAnnotations(data.annotations || []);
      }
    } catch (err) {
      console.error('Failed to fetch annotations:', err);
    }
  };

  const fetchTags = async (currentUser) => {
    try {
      const token = await currentUser.getIdToken();
      const res = await fetch(`${BACKEND_URL}/annotations/tags`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setAllTags(data.tags || []);
      }
    } catch (err) {
      console.error('Failed to fetch tags:', err);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/annotations/search?q=${encodeURIComponent(searchQuery)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setAnnotations(data.results || []);
      }
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  const handleTagFilter = (tag) => {
    setSelectedTag(tag);
    setSelectedType(null);
    fetchAnnotations(user, tag, null);
  };

  const handleTypeFilter = (type) => {
    setSelectedType(type);
    setSelectedTag(null);
    fetchAnnotations(user, null, type);
  };

  const handleClearFilters = () => {
    setSelectedTag(null);
    setSelectedType(null);
    setSearchQuery('');
    fetchAnnotations(user);
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return 'Recently';
    try {
      const date = new Date(timestamp.seconds * 1000);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Recently';
    }
  };

  // Sort annotations based on selected criteria
  const sortAnnotations = (annotationsList) => {
    const sorted = [...annotationsList];
    switch(sortBy) {
      case 'newest':
        return sorted.sort((a, b) => (b.createdAt?.seconds || 0) - (a.createdAt?.seconds || 0));
      case 'oldest':
        return sorted.sort((a, b) => (a.createdAt?.seconds || 0) - (b.createdAt?.seconds || 0));
      case 'surah':
        return sorted.sort((a, b) => {
          if (a.surah === b.surah) return a.verse - b.verse;
          return a.surah - b.surah;
        });
      case 'type':
        return sorted.sort((a, b) => (a.type || '').localeCompare(b.type || ''));
      default:
        return sorted;
    }
  };

  // Filter by date range
  const filterByDateRange = (annotationsList) => {
    if (!dateRange.start && !dateRange.end) return annotationsList;

    return annotationsList.filter(annotation => {
      if (!annotation.createdAt?.seconds) return false;
      const annotationDate = new Date(annotation.createdAt.seconds * 1000);

      if (dateRange.start) {
        const startDate = new Date(dateRange.start);
        if (annotationDate < startDate) return false;
      }

      if (dateRange.end) {
        const endDate = new Date(dateRange.end);
        endDate.setHours(23, 59, 59, 999); // Include full day
        if (annotationDate > endDate) return false;
      }

      return true;
    });
  };


  // Calculate comprehensive statistics
  const calculateStats = () => {
    const stats = {
      totalReflections: annotations.length,
      byType: {},
      bySurah: {},
      byMonth: {},
      byDayOfWeek: {},
      topTags: {},
      recentDays: 0,
      averageLength: 0,
      longestStreak: 0,
      currentStreak: 0,
      totalWords: 0,
      mostActiveDay: null,
      mostAnnotatedVerse: null,
      reflectionGrowth: []
    };

    const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
    const sortedAnnotations = [...annotations].sort((a, b) =>
      (a.createdAt?.seconds || 0) - (b.createdAt?.seconds || 0)
    );

    let totalLength = 0;
    let totalWords = 0;
    const dayActivity = {};
    const verseActivity = {};
    const dailyActivity = new Map();

    sortedAnnotations.forEach((annotation, index) => {
      // By type
      const typeKey = annotation.type || 'uncategorized';
      stats.byType[typeKey] = (stats.byType[typeKey] || 0) + 1;

      // By surah
      const surahKey = `Surah ${annotation.surah}`;
      stats.bySurah[surahKey] = (stats.bySurah[surahKey] || 0) + 1;

      // By verse
      const verseKey = `${annotation.surah}:${annotation.verse}`;
      verseActivity[verseKey] = (verseActivity[verseKey] || 0) + 1;

      // Tags frequency
      annotation.tags?.forEach(tag => {
        stats.topTags[tag] = (stats.topTags[tag] || 0) + 1;
      });

      // Date analysis
      if (annotation.createdAt?.seconds) {
        const date = new Date(annotation.createdAt.seconds * 1000);

        // By month
        const monthKey = date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
        stats.byMonth[monthKey] = (stats.byMonth[monthKey] || 0) + 1;

        // By day of week
        const dayOfWeek = date.toLocaleDateString('en-US', { weekday: 'long' });
        stats.byDayOfWeek[dayOfWeek] = (stats.byDayOfWeek[dayOfWeek] || 0) + 1;

        // Daily activity for streaks
        const dayKey = date.toISOString().split('T')[0];
        dailyActivity.set(dayKey, (dailyActivity.get(dayKey) || 0) + 1);
        dayActivity[dayKey] = (dayActivity[dayKey] || 0) + 1;

        // Recent activity
        if (annotation.createdAt.seconds * 1000 > thirtyDaysAgo) {
          stats.recentDays++;
        }
      }

      // Content analysis
      const content = annotation.content || '';
      totalLength += content.length;
      totalWords += content.split(/\s+/).filter(w => w.length > 0).length;
    });

    // Calculate streaks
    const sortedDays = Array.from(dailyActivity.keys()).sort();
    let currentStreak = 0;
    let longestStreak = 0;
    let tempStreak = 0;
    let lastDate = null;

    sortedDays.forEach(dayKey => {
      const currentDate = new Date(dayKey);

      if (lastDate) {
        const dayDiff = (currentDate - lastDate) / (1000 * 60 * 60 * 24);

        if (dayDiff === 1) {
          tempStreak++;
        } else {
          longestStreak = Math.max(longestStreak, tempStreak);
          tempStreak = 1;
        }
      } else {
        tempStreak = 1;
      }

      lastDate = currentDate;
    });

    longestStreak = Math.max(longestStreak, tempStreak);

    // Check if streak is current
    const today = new Date().toISOString().split('T')[0];
    const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    if (dailyActivity.has(today) || dailyActivity.has(yesterday)) {
      currentStreak = tempStreak;
    }

    // Find most active day
    let maxDay = null;
    let maxCount = 0;
    Object.entries(dayActivity).forEach(([day, count]) => {
      if (count > maxCount) {
        maxCount = count;
        maxDay = day;
      }
    });

    // Find most annotated verse
    let maxVerse = null;
    let maxVerseCount = 0;
    Object.entries(verseActivity).forEach(([verse, count]) => {
      if (count > maxVerseCount) {
        maxVerseCount = count;
        maxVerse = verse;
      }
    });

    // Sort top tags
    stats.topTags = Object.entries(stats.topTags)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .reduce((obj, [tag, count]) => {
        obj[tag] = count;
        return obj;
      }, {});

    stats.averageLength = annotations.length > 0 ? Math.round(totalLength / annotations.length) : 0;
    stats.totalWords = totalWords;
    stats.longestStreak = longestStreak;
    stats.currentStreak = currentStreak;
    stats.mostActiveDay = maxDay;
    stats.mostAnnotatedVerse = maxVerse;

    return stats;
  };

  // Advanced filtering with multi-select
  const applyAdvancedFilters = (annotationsList) => {
    let filtered = [...annotationsList];

    // Filter by multiple types
    if (selectedTypes.length > 0) {
      filtered = filtered.filter(a => selectedTypes.includes(a.type));
    }

    // Filter by multiple tags
    if (selectedTags.length > 0) {
      filtered = filtered.filter(a =>
        a.tags?.some(tag => selectedTags.includes(tag))
      );
    }

    // Apply date range filter
    filtered = filterByDateRange(filtered);

    // Apply sorting
    return sortAnnotations(filtered);
  };

  // Smart tag suggestions based on content
  const getSuggestedTags = (content) => {
    const suggestions = [];
    const lowerContent = content.toLowerCase();

    // Islamic concept tags
    if (lowerContent.includes('allah')) suggestions.push('tawheed');
    if (lowerContent.includes('prophet') || lowerContent.includes('muhammad')) suggestions.push('seerah');
    if (lowerContent.includes('prayer') || lowerContent.includes('salah')) suggestions.push('ibadah');
    if (lowerContent.includes('patience') || lowerContent.includes('sabr')) suggestions.push('character');
    if (lowerContent.includes('grateful') || lowerContent.includes('shukr')) suggestions.push('gratitude');
    if (lowerContent.includes('parent')) suggestions.push('family');
    if (lowerContent.includes('forgive')) suggestions.push('repentance');

    // Emotion/mood tags
    if (lowerContent.includes('happy') || lowerContent.includes('joy')) suggestions.push('joy');
    if (lowerContent.includes('sad') || lowerContent.includes('difficult')) suggestions.push('trial');
    if (lowerContent.includes('hope')) suggestions.push('hope');
    if (lowerContent.includes('fear')) suggestions.push('khawf');

    // Remove duplicates
    return [...new Set(suggestions)];
  };

  if (isLoading) {
    return (
      <div className="container">
        <div className="card">
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container">
        <div className="card">
          <h1>Please sign in to view your reflections</h1>
          <Link href="/">
            <button style={{ marginTop: '20px' }}>Go to Home</button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
          <h1>📝 My Reflections</h1>
          <Link href="/">
            <button>← Back to Search</button>
          </Link>
        </div>

        {/* Search Bar */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', gap: '12px' }}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search your reflections..."
              style={{
                flex: 1,
                padding: '12px 20px',
                border: '2px solid var(--border-medium)',
                borderRadius: '12px',
                fontSize: '1rem'
              }}
            />
            <button
              onClick={handleSearch}
              style={{
                padding: '12px 24px',
                background: 'var(--gradient-teal-gold)',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                fontWeight: '700',
                cursor: 'pointer'
              }}
            >
              🔍 Search
            </button>
          </div>
        </div>

        {/* Filters */}
        <div style={{ marginBottom: '24px' }}>
          {/* Type Filters */}
          <div style={{ marginBottom: '16px' }}>
            <h3 style={{ fontSize: '0.9rem', fontWeight: '700', marginBottom: '8px', color: '#666' }}>Filter by Type:</h3>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {Object.entries(ANNOTATION_TYPE_CONFIG).map(([type, config]) => (
                <button
                  key={type}
                  onClick={() => handleTypeFilter(type)}
                  style={{
                    background: selectedType === type ? config.color : 'white',
                    color: selectedType === type ? 'white' : config.color,
                    border: `2px solid ${config.color}`,
                    padding: '6px 14px',
                    borderRadius: '20px',
                    fontSize: '0.85rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease'
                  }}
                >
                  {config.icon} {config.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tag Filters */}
          {allTags.length > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <h3 style={{ fontSize: '0.9rem', fontWeight: '700', marginBottom: '8px', color: '#666' }}>Filter by Tag:</h3>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {allTags.map(tag => (
                  <button
                    key={tag}
                    onClick={() => handleTagFilter(tag)}
                    style={{
                      background: selectedTag === tag ? 'var(--primary-teal)' : 'var(--cream)',
                      color: selectedTag === tag ? 'white' : 'var(--primary-teal)',
                      border: '2px solid var(--primary-teal)',
                      padding: '6px 14px',
                      borderRadius: '20px',
                      fontSize: '0.85rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      transition: 'all 0.3s ease'
                    }}
                  >
                    #{tag}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Clear Filters */}
          {(selectedTag || selectedType || searchQuery) && (
            <button
              onClick={handleClearFilters}
              style={{
                background: 'transparent',
                color: 'var(--error-color)',
                border: '2px solid var(--error-color)',
                padding: '8px 16px',
                borderRadius: '12px',
                fontSize: '0.85rem',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              ✕ Clear Filters
            </button>
          )}
        </div>

        {/* Stats */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '16px',
            marginBottom: '32px',
            padding: '20px',
            background: 'linear-gradient(135deg, var(--cream) 0%, rgba(212, 175, 55, 0.05) 100%)',
            borderRadius: '16px',
            border: '2px solid var(--border-light)'
          }}
        >
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: '800', color: 'var(--primary-teal)' }}>
              {annotations.length}
            </div>
            <div style={{ fontSize: '0.85rem', color: '#666', fontWeight: '600' }}>Total Reflections</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: '800', color: 'var(--gold)' }}>
              {allTags.length}
            </div>
            <div style={{ fontSize: '0.85rem', color: '#666', fontWeight: '600' }}>Unique Tags</div>
          </div>
        </div>

        {/* Analytics Dashboard Toggle */}
        <div style={{
          display: 'flex',
          gap: '12px',
          marginBottom: '24px',
          flexWrap: 'wrap'
        }}>
          <button
            onClick={() => setShowAnalytics(!showAnalytics)}
            style={{
              padding: '10px 20px',
              background: showAnalytics ? 'var(--primary-teal)' : 'white',
              color: showAnalytics ? 'white' : 'var(--primary-teal)',
              border: '2px solid var(--primary-teal)',
              borderRadius: '12px',
              fontSize: '0.9rem',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            📊 {showAnalytics ? 'Hide' : 'Show'} Analytics Dashboard
          </button>

          <button
            onClick={() => setShowCalendar(!showCalendar)}
            style={{
              padding: '10px 20px',
              background: showCalendar ? 'var(--gold)' : 'white',
              color: showCalendar ? 'white' : 'var(--gold)',
              border: '2px solid var(--gold)',
              borderRadius: '12px',
              fontSize: '0.9rem',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            📅 {showCalendar ? 'Hide' : 'Show'} Reflection Calendar
          </button>
        </div>

        {/* Analytics Dashboard */}
        {showAnalytics && (
          <div style={{
            marginBottom: '32px',
            padding: '24px',
            background: 'white',
            borderRadius: '16px',
            border: '2px solid var(--border-light)',
            boxShadow: 'var(--shadow-soft)'
          }}>
            <h2 style={{
              fontSize: '1.5rem',
              fontWeight: '700',
              color: 'var(--primary-teal)',
              marginBottom: '24px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              📊 Your Reflection Journey Analytics
            </h2>

            {(() => {
              const stats = calculateStats();
              return (
                <>
                  {/* Key Metrics */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: '16px',
                    marginBottom: '24px'
                  }}>
                    <div style={{
                      padding: '16px',
                      background: 'linear-gradient(135deg, #10B981 0%, #0D9488 100%)',
                      color: 'white',
                      borderRadius: '12px',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '2.5rem', fontWeight: '800' }}>
                        {stats.currentStreak}
                      </div>
                      <div style={{ fontSize: '0.9rem', fontWeight: '600' }}>
                        🔥 Current Streak (days)
                      </div>
                    </div>

                    <div style={{
                      padding: '16px',
                      background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
                      color: 'white',
                      borderRadius: '12px',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '2.5rem', fontWeight: '800' }}>
                        {stats.longestStreak}
                      </div>
                      <div style={{ fontSize: '0.9rem', fontWeight: '600' }}>
                        🏆 Longest Streak
                      </div>
                    </div>

                    <div style={{
                      padding: '16px',
                      background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
                      color: 'white',
                      borderRadius: '12px',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '2.5rem', fontWeight: '800' }}>
                        {stats.totalWords.toLocaleString()}
                      </div>
                      <div style={{ fontSize: '0.9rem', fontWeight: '600' }}>
                        ✍️ Total Words Written
                      </div>
                    </div>

                    <div style={{
                      padding: '16px',
                      background: 'linear-gradient(135deg, #EC4899 0%, #DB2777 100%)',
                      color: 'white',
                      borderRadius: '12px',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '2.5rem', fontWeight: '800' }}>
                        {stats.recentDays}
                      </div>
                      <div style={{ fontSize: '0.9rem', fontWeight: '600' }}>
                        📝 Last 30 Days
                      </div>
                    </div>
                  </div>

                  {/* Reflection Types Breakdown */}
                  <div style={{
                    marginBottom: '24px',
                    padding: '20px',
                    background: 'var(--cream)',
                    borderRadius: '12px'
                  }}>
                    <h3 style={{
                      fontSize: '1.1rem',
                      fontWeight: '700',
                      marginBottom: '16px',
                      color: 'var(--primary-teal)'
                    }}>
                      📊 Reflection Types Distribution
                    </h3>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                      {Object.entries(stats.byType).map(([type, count]) => {
                        const config = getTypeConfig(type);
                        const percentage = Math.round((count / stats.totalReflections) * 100);
                        return (
                          <div
                            key={type}
                            style={{
                              flex: '1 1 150px',
                              padding: '12px',
                              background: 'white',
                              borderRadius: '8px',
                              border: `2px solid ${config.color}`,
                              textAlign: 'center'
                            }}
                          >
                            <div style={{ fontSize: '1.5rem' }}>{config.icon}</div>
                            <div style={{
                              fontSize: '0.85rem',
                              fontWeight: '600',
                              color: config.color
                            }}>
                              {config.label}
                            </div>
                            <div style={{
                              fontSize: '1.2rem',
                              fontWeight: '700',
                              color: 'var(--foreground)'
                            }}>
                              {count}
                            </div>
                            <div style={{
                              fontSize: '0.75rem',
                              color: '#666'
                            }}>
                              {percentage}%
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Top Tags */}
                  {Object.keys(stats.topTags).length > 0 && (
                    <div style={{
                      marginBottom: '24px',
                      padding: '20px',
                      background: 'var(--cream)',
                      borderRadius: '12px'
                    }}>
                      <h3 style={{
                        fontSize: '1.1rem',
                        fontWeight: '700',
                        marginBottom: '16px',
                        color: 'var(--primary-teal)'
                      }}>
                        🏷️ Top Tags
                      </h3>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {Object.entries(stats.topTags).map(([tag, count]) => (
                          <span
                            key={tag}
                            style={{
                              background: 'var(--primary-teal)',
                              color: 'white',
                              padding: '6px 14px',
                              borderRadius: '20px',
                              fontSize: '0.85rem',
                              fontWeight: '600',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px'
                            }}
                          >
                            #{tag}
                            <span style={{
                              background: 'rgba(255, 255, 255, 0.3)',
                              padding: '2px 6px',
                              borderRadius: '10px',
                              fontSize: '0.75rem'
                            }}>
                              {count}
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Day of Week Activity */}
                  <div style={{
                    marginBottom: '24px',
                    padding: '20px',
                    background: 'var(--cream)',
                    borderRadius: '12px'
                  }}>
                    <h3 style={{
                      fontSize: '1.1rem',
                      fontWeight: '700',
                      marginBottom: '16px',
                      color: 'var(--primary-teal)'
                    }}>
                      📅 Most Active Days
                    </h3>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map(day => {
                        const count = stats.byDayOfWeek[day] || 0;
                        const maxCount = Math.max(...Object.values(stats.byDayOfWeek));
                        const height = maxCount > 0 ? (count / maxCount) * 100 : 0;
                        return (
                          <div
                            key={day}
                            style={{
                              flex: '1',
                              minWidth: '60px',
                              textAlign: 'center'
                            }}
                          >
                            <div style={{
                              height: '100px',
                              position: 'relative',
                              background: '#f3f4f6',
                              borderRadius: '8px',
                              overflow: 'hidden'
                            }}>
                              <div style={{
                                position: 'absolute',
                                bottom: 0,
                                width: '100%',
                                height: `${height}%`,
                                background: 'var(--gradient-teal-gold)',
                                transition: 'height 0.3s ease'
                              }} />
                              <div style={{
                                position: 'absolute',
                                top: '50%',
                                left: '50%',
                                transform: 'translate(-50%, -50%)',
                                fontWeight: '700',
                                fontSize: '0.9rem',
                                color: height > 50 ? 'white' : 'var(--foreground)'
                              }}>
                                {count}
                              </div>
                            </div>
                            <div style={{
                              fontSize: '0.75rem',
                              marginTop: '4px',
                              fontWeight: '600'
                            }}>
                              {day.slice(0, 3)}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Insights */}
                  <div style={{
                    padding: '20px',
                    background: 'linear-gradient(135deg, var(--primary-teal) 0%, var(--deep-blue) 100%)',
                    color: 'white',
                    borderRadius: '12px'
                  }}>
                    <h3 style={{
                      fontSize: '1.1rem',
                      fontWeight: '700',
                      marginBottom: '16px'
                    }}>
                      ✨ Insights
                    </h3>
                    <div style={{ display: 'grid', gap: '12px' }}>
                      {stats.mostActiveDay && (
                        <div>
                          📅 Most active day: <strong>{new Date(stats.mostActiveDay).toLocaleDateString()}</strong>
                        </div>
                      )}
                      {stats.mostAnnotatedVerse && (
                        <div>
                          📖 Most reflected verse: <strong>Verse {stats.mostAnnotatedVerse}</strong>
                        </div>
                      )}
                      <div>
                        📝 Average reflection length: <strong>{stats.averageLength} characters</strong>
                      </div>
                    </div>
                  </div>
                </>
              );
            })()}
          </div>
        )}

        {/* Reflection Calendar */}
        {showCalendar && (
          <div style={{
            marginBottom: '32px',
            padding: '24px',
            background: 'white',
            borderRadius: '16px',
            border: '2px solid var(--border-light)',
            boxShadow: 'var(--shadow-soft)'
          }}>
            <h2 style={{
              fontSize: '1.5rem',
              fontWeight: '700',
              color: 'var(--gold)',
              marginBottom: '24px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              📅 Reflection Calendar
            </h2>

            <ReflectionCalendar annotations={annotations} />
          </div>
        )}

        {/* Annotations List */}
        {annotations.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#999' }}>
            <p style={{ fontSize: '3rem', marginBottom: '16px' }}>📝</p>
            <p style={{ fontSize: '1.2rem' }}>No reflections yet</p>
            <p style={{ marginTop: '8px' }}>
              {selectedTag || selectedType || searchQuery
                ? 'No reflections match your filters. Try adjusting them.'
                : 'Start adding notes to verses as you study to build your personal Quran journal.'}
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {annotations.map(annotation => {
              const typeConfig = getTypeConfig(annotation.type);
              const isExpanded = expandedId === annotation.id;

              return (
                <div
                  key={annotation.id}
                  onClick={() => {
                    if (annotation.share_id) {
                      window.location.href = `/shared/${annotation.share_id}`;
                    }
                  }}
                  style={{
                    padding: '20px',
                    background: 'white',
                    borderRadius: '16px',
                    border: '2px solid var(--border-light)',
                    borderLeft: `6px solid ${typeConfig.color}`,
                    transition: 'all 0.3s ease',
                    cursor: annotation.share_id ? 'pointer' : 'default'
                  }}
                  className="annotation-card"
                >
                  {/* Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <span style={{ fontSize: '1.4rem' }}>{typeConfig.icon}</span>
                        <span
                          style={{
                            background: typeConfig.color,
                            color: 'white',
                            padding: '4px 10px',
                            borderRadius: '12px',
                            fontSize: '0.75rem',
                            fontWeight: '700',
                            textTransform: 'uppercase'
                          }}
                        >
                          {typeConfig.label}
                        </span>
                      </div>

                      {/* Context based on reflection type */}
                      {annotation.reflection_type === 'verse' && annotation.verseRef && (
                        <div style={{ fontWeight: '700', fontSize: '1.1rem', color: 'var(--primary-teal)' }}>
                          📖 Verse {annotation.verseRef}
                        </div>
                      )}

                      {annotation.reflection_type === 'section' && (
                        <div>
                          <div style={{ fontWeight: '700', fontSize: '1.1rem', color: '#8b5cf6', marginBottom: '4px' }}>
                            📑 Section: {annotation.section_name}
                          </div>
                          {annotation.query_context && (
                            <div style={{ fontSize: '0.9rem', color: '#666', fontStyle: 'italic' }}>
                              Query: &quot;{annotation.query_context}&quot;
                            </div>
                          )}
                        </div>
                      )}

                      {annotation.reflection_type === 'general' && (
                        <div>
                          <div style={{ fontWeight: '700', fontSize: '1.1rem', color: '#10b981', marginBottom: '4px' }}>
                            🌟 General Reflection
                          </div>
                          {annotation.query_context && (
                            <div style={{ fontSize: '0.9rem', color: '#666', fontStyle: 'italic' }}>
                              Query: &quot;{annotation.query_context}&quot;
                            </div>
                          )}
                        </div>
                      )}

                      {annotation.reflection_type === 'highlight' && (
                        <div>
                          <div style={{ fontWeight: '700', fontSize: '1.1rem', color: '#f59e0b', marginBottom: '4px' }}>
                            ✨ Highlighted Text
                          </div>
                          {annotation.highlighted_text && (
                            <div style={{
                              fontSize: '0.9rem',
                              color: '#666',
                              fontStyle: 'italic',
                              background: 'rgba(245, 158, 11, 0.1)',
                              padding: '8px 12px',
                              borderRadius: '8px',
                              borderLeft: '3px solid #f59e0b',
                              marginTop: '8px'
                            }}>
                              &quot;{annotation.highlighted_text}&quot;
                            </div>
                          )}
                          {annotation.query_context && (
                            <div style={{ fontSize: '0.85rem', color: '#999', marginTop: '4px' }}>
                              From query: &quot;{annotation.query_context}&quot;
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px', marginLeft: '16px' }}>
                      <div style={{ fontSize: '0.85rem', color: '#999' }}>
                        {formatDate(annotation.createdAt)}
                      </div>
                      {annotation.share_id && (
                        <div style={{
                          fontSize: '0.75rem',
                          color: '#8b5cf6',
                          fontWeight: '600',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}>
                          🔗 View Response
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Content */}
                  <div style={{ marginBottom: '12px' }}>
                    <p
                      style={{
                        margin: 0,
                        color: 'var(--foreground)',
                        fontSize: '0.95rem',
                        lineHeight: '1.6',
                        whiteSpace: 'pre-wrap',
                        maxHeight: isExpanded ? '1000px' : '60px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        transition: 'max-height 0.3s ease'
                      }}
                    >
                      {annotation.content}
                    </p>
                  </div>

                  {/* Tags */}
                  {annotation.tags && annotation.tags.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {annotation.tags.map(tag => (
                        <span
                          key={tag}
                          onClick={() => handleTagFilter(tag)}
                          style={{
                            background: 'var(--cream)',
                            color: 'var(--primary-teal)',
                            padding: '4px 10px',
                            borderRadius: '12px',
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            border: '1px solid var(--border-light)',
                            cursor: 'pointer'
                          }}
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Expand/Collapse */}
                  {annotation.content && annotation.content.length > 150 && (
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : annotation.id)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--primary-teal)',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        fontWeight: '600',
                        padding: '8px 0',
                        marginTop: '8px'
                      }}
                    >
                      {isExpanded ? '▲ Show less' : '▼ Show more'}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <style jsx>{`
        .annotation-card:hover {
          transform: translateY(-2px);
          box-shadow: var(--shadow-medium);
          border-color: var(--gold);
        }
      `}</style>
    </div>
  );
}
