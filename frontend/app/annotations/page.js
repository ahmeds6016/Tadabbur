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
  connection: { icon: '🔗', label: 'Connection', color: '#D97706' }
};

export default function MyReflectionsPage() {
  const [user, setUser] = useState(null);
  const [annotations, setAnnotations] = useState([]);
  const [allTags, setAllTags] = useState([]);
  const [selectedTag, setSelectedTag] = useState(null);
  const [selectedType, setSelectedType] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);

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
              const typeConfig = ANNOTATION_TYPE_CONFIG[annotation.type] || ANNOTATION_TYPE_CONFIG.personal_insight;
              const isExpanded = expandedId === annotation.id;

              return (
                <div
                  key={annotation.id}
                  style={{
                    padding: '20px',
                    background: 'white',
                    borderRadius: '16px',
                    border: '2px solid var(--border-light)',
                    borderLeft: `6px solid ${typeConfig.color}`,
                    transition: 'all 0.3s ease'
                  }}
                  className="annotation-card"
                >
                  {/* Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <div>
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
                      <div style={{ fontWeight: '700', fontSize: '1.1rem', color: 'var(--primary-teal)' }}>
                        📖 {annotation.verseRef}
                      </div>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#999' }}>
                      {formatDate(annotation.createdAt)}
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
                        whiteSpace: isExpanded ? 'pre-wrap' : 'nowrap',
                        overflow: isExpanded ? 'visible' : 'hidden',
                        textOverflow: 'ellipsis'
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
