'use client';
import { useState, useEffect } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import Link from 'next/link';
import ReflectionDetailPanel from '../components/ReflectionDetailPanel';
import { Lightbulb, HelpCircle, CheckSquare, Heart, Link2, BookOpen, ChevronDown, Search, X } from 'lucide-react';
import { auth } from '../lib/firebase';
import { BACKEND_URL } from '../lib/config';
import BottomNav from '../components/BottomNav';

// Core 5 reflection types with Lucide icons
const ANNOTATION_TYPE_CONFIG = {
  insight: { iconComponent: Lightbulb, label: 'Insight', color: '#0D9488' },
  question: { iconComponent: HelpCircle, label: 'Question', color: '#8B5CF6' },
  application: { iconComponent: CheckSquare, label: 'Application', color: '#059669' },
  dua: { iconComponent: Heart, label: 'Dua/Prayer', color: '#10B981' },
  connection: { iconComponent: Link2, label: 'Connection', color: '#D97706' }
};

// Legacy type mapping for backward compatibility (map old 17 types to new 5)
const LEGACY_TYPE_MAPPING = {
  personal_insight: 'insight',
  memory: 'insight',
  contemplation: 'insight',
  personal_experience: 'insight',
  gratitude: 'dua',
  reminder: 'application',
  teaching_point: 'application',
  goal: 'application',
  story: 'connection',
  linguistic: 'connection',
  historical: 'connection',
  scientific: 'connection',
  warning: 'question'
};

// Helper function to get config for any type (core, legacy, or custom)
const getTypeConfig = (type) => {
  if (ANNOTATION_TYPE_CONFIG[type]) {
    return ANNOTATION_TYPE_CONFIG[type];
  }
  if (LEGACY_TYPE_MAPPING[type]) {
    return ANNOTATION_TYPE_CONFIG[LEGACY_TYPE_MAPPING[type]];
  }
  return {
    iconComponent: BookOpen,
    label: type ? type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, ' ') : 'Custom',
    color: '#6B7280'
  };
};

export default function MyReflectionsPage() {
  const [user, setUser] = useState(null);
  const [annotations, setAnnotations] = useState([]);
  const [allTags, setAllTags] = useState([]);
  const [selectedTag, setSelectedTag] = useState(null);
  const [selectedType, setSelectedType] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [sortBy, setSortBy] = useState('newest');
  const [selectedAnnotation, setSelectedAnnotation] = useState(null);
  const [showFilters, setShowFilters] = useState(false);

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
    setSelectedType(type === selectedType ? null : type);
    setSelectedTag(null);
    if (type === selectedType) {
      fetchAnnotations(user);
    } else {
      fetchAnnotations(user, null, type);
    }
  };

  const handleClearFilters = () => {
    setSelectedTag(null);
    setSelectedType(null);
    setSearchQuery('');
    fetchAnnotations(user);
  };

  const handleDeleteAnnotation = async (annotationId) => {
    if (!user) return;
    try {
      const token = await user.getIdToken();
      const response = await fetch(`${BACKEND_URL}/annotations/${annotationId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        setAnnotations(prev => prev.filter(a => a.id !== annotationId));
      }
    } catch (error) {
      console.error('Error deleting annotation:', error);
    }
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return 'Recently';
    try {
      const date = new Date(timestamp.seconds * 1000);
      const now = new Date();
      const diffMs = now - date;
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffDays === 0) return 'Today';
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays}d ago`;
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return 'Recently';
    }
  };

  const sortAnnotations = (annotationsList) => {
    const sorted = [...annotationsList];
    switch(sortBy) {
      case 'newest':
        return sorted.sort((a, b) => (b.createdAt?.seconds || 0) - (a.createdAt?.seconds || 0));
      case 'oldest':
        return sorted.sort((a, b) => (a.createdAt?.seconds || 0) - (b.createdAt?.seconds || 0));
      default:
        return sorted;
    }
  };

  const hasActiveFilters = selectedTag || selectedType || searchQuery;
  const displayAnnotations = sortAnnotations(annotations);

  if (isLoading) {
    return (
      <div className="container">
        <div className="card" style={{ display: 'flex', justifyContent: 'center', padding: '60px 20px' }}>
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container">
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <p style={{ fontSize: '1rem', color: '#6b7280', marginBottom: '16px' }}>Sign in to view your reflections</p>
          <Link href="/">
            <button style={{ padding: '10px 24px', background: '#1a1a1a', color: 'white', border: 'none', borderRadius: '8px', fontWeight: '600', cursor: 'pointer' }}>Go Home</button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="reflections-page">
      {/* Header */}
      <div className="reflections-header">
        <h1 className="reflections-title">Reflections</h1>
        <div className="reflections-count">{annotations.length}</div>
      </div>

      {/* Search */}
      <div className="search-bar">
        <Search size={16} className="search-icon" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Search reflections..."
          className="search-input"
        />
        {searchQuery && (
          <button className="search-clear" onClick={() => { setSearchQuery(''); fetchAnnotations(user); }}>
            <X size={14} />
          </button>
        )}
      </div>

      {/* Type filter chips */}
      <div className="filter-chips">
        {Object.entries(ANNOTATION_TYPE_CONFIG).map(([type, config]) => (
          <button
            key={type}
            onClick={() => handleTypeFilter(type)}
            className={`filter-chip ${selectedType === type ? 'active' : ''}`}
            style={{
              '--chip-color': config.color,
            }}
          >
            {config.label}
          </button>
        ))}
      </div>

      {/* Tag filter row */}
      {allTags.length > 0 && (
        <div className="tag-row">
          {allTags.slice(0, 8).map(tag => (
            <button
              key={tag}
              onClick={() => handleTagFilter(tag)}
              className={`tag-chip ${selectedTag === tag ? 'active' : ''}`}
            >
              #{tag}
            </button>
          ))}
        </div>
      )}

      {/* Active filter indicator */}
      {hasActiveFilters && (
        <button className="clear-filters" onClick={handleClearFilters}>
          Clear filters
        </button>
      )}

      {/* Annotations List */}
      {displayAnnotations.length === 0 ? (
        <div className="empty-state">
          <BookOpen size={40} strokeWidth={1.2} color="#d1d5db" />
          <p className="empty-title">
            {hasActiveFilters ? 'No matches' : 'No reflections yet'}
          </p>
          <p className="empty-desc">
            {hasActiveFilters
              ? 'Try different filters.'
              : 'Reflect on verses as you study to build your journal.'}
          </p>
        </div>
      ) : (
        <div className="annotations-list">
          {displayAnnotations.map(annotation => {
            const typeConfig = getTypeConfig(annotation.type);
            const IconComp = typeConfig.iconComponent;

            // Build context label
            let contextLabel = '';
            if (annotation.reflection_type === 'verse' && annotation.verseRef) {
              contextLabel = annotation.verseRef;
            } else if (annotation.reflection_type === 'section' && annotation.section_name) {
              contextLabel = annotation.section_name;
            } else if (annotation.reflection_type === 'general') {
              contextLabel = annotation.query_context || 'General';
            } else if (annotation.reflection_type === 'highlight') {
              contextLabel = 'Highlight';
            }

            return (
              <div
                key={annotation.id}
                className="annotation-card"
                onClick={() => setSelectedAnnotation(annotation)}
              >
                {/* Top row: type badge + date */}
                <div className="card-top">
                  <div className="type-badge" style={{ color: typeConfig.color }}>
                    {IconComp && <IconComp size={14} strokeWidth={2} />}
                    <span>{typeConfig.label}</span>
                  </div>
                  <span className="card-date">{formatDate(annotation.createdAt)}</span>
                </div>

                {/* Context */}
                {contextLabel && (
                  <div className="card-context">{contextLabel}</div>
                )}

                {/* Content preview */}
                <p className="card-content">{annotation.content}</p>

                {/* Tags */}
                {annotation.tags && annotation.tags.length > 0 && (
                  <div className="card-tags">
                    {annotation.tags.map(tag => (
                      <span key={tag} className="card-tag" onClick={(e) => {
                        e.stopPropagation();
                        handleTagFilter(tag);
                      }}>#{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <style jsx>{`
        .reflections-page {
          max-width: 600px;
          margin: 0 auto;
          padding: 16px 16px calc(60px + env(safe-area-inset-bottom, 0px));
        }

        .reflections-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 0 16px;
        }

        .reflections-title {
          font-size: 1.5rem;
          font-weight: 700;
          color: #1a1a1a;
          margin: 0;
        }

        .reflections-count {
          font-size: 0.8rem;
          font-weight: 600;
          color: #6b7280;
          background: #f3f4f6;
          padding: 4px 10px;
          border-radius: 12px;
        }

        /* Search */
        .search-bar {
          position: relative;
          margin-bottom: 12px;
        }

        .search-bar :global(.search-icon) {
          position: absolute;
          left: 12px;
          top: 50%;
          transform: translateY(-50%);
          color: #9ca3af;
        }

        .search-input {
          width: 100%;
          padding: 10px 36px 10px 36px;
          border: 1px solid #e5e7eb;
          border-radius: 10px;
          font-size: 0.9rem;
          background: #f9fafb;
          outline: none;
          transition: border-color 0.15s;
          box-sizing: border-box;
        }

        .search-input:focus {
          border-color: #d1d5db;
          background: white;
        }

        .search-clear {
          position: absolute;
          right: 10px;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          color: #9ca3af;
          cursor: pointer;
          padding: 4px;
          display: flex;
        }

        /* Filter chips */
        .filter-chips {
          display: flex;
          gap: 6px;
          overflow-x: auto;
          padding-bottom: 8px;
          margin-bottom: 4px;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: none;
        }

        .filter-chips::-webkit-scrollbar {
          display: none;
        }

        .filter-chip {
          flex-shrink: 0;
          padding: 6px 14px;
          border: 1px solid #e5e7eb;
          border-radius: 20px;
          background: white;
          font-size: 0.78rem;
          font-weight: 500;
          color: #374151;
          cursor: pointer;
          transition: all 0.15s;
          white-space: nowrap;
        }

        .filter-chip.active {
          background: var(--chip-color);
          color: white;
          border-color: var(--chip-color);
        }

        /* Tag row */
        .tag-row {
          display: flex;
          gap: 6px;
          overflow-x: auto;
          padding-bottom: 8px;
          margin-bottom: 4px;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: none;
        }

        .tag-row::-webkit-scrollbar {
          display: none;
        }

        .tag-chip {
          flex-shrink: 0;
          padding: 4px 10px;
          border: none;
          border-radius: 12px;
          background: #f3f4f6;
          font-size: 0.72rem;
          font-weight: 500;
          color: #6b7280;
          cursor: pointer;
          transition: all 0.15s;
          white-space: nowrap;
        }

        .tag-chip.active {
          background: #0d9488;
          color: white;
        }

        .clear-filters {
          display: block;
          background: none;
          border: none;
          color: #ef4444;
          font-size: 0.78rem;
          font-weight: 500;
          cursor: pointer;
          padding: 4px 0;
          margin-bottom: 8px;
        }

        /* Empty state */
        .empty-state {
          text-align: center;
          padding: 60px 20px;
        }

        .empty-title {
          font-size: 1rem;
          font-weight: 600;
          color: #374151;
          margin: 12px 0 4px;
        }

        .empty-desc {
          font-size: 0.85rem;
          color: #9ca3af;
          margin: 0;
          line-height: 1.5;
        }

        /* Annotations list */
        .annotations-list {
          display: flex;
          flex-direction: column;
          gap: 1px;
          background: #e5e7eb;
          border-radius: 12px;
          overflow: hidden;
        }

        .annotation-card {
          padding: 14px 16px;
          background: white;
          cursor: pointer;
          transition: background 0.1s;
        }

        .annotation-card:active {
          background: #f9fafb;
        }

        .card-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 6px;
        }

        .type-badge {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 0.72rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.03em;
        }

        .card-date {
          font-size: 0.72rem;
          color: #9ca3af;
        }

        .card-context {
          font-size: 0.85rem;
          font-weight: 600;
          color: #1a1a1a;
          margin-bottom: 4px;
        }

        .card-content {
          font-size: 0.88rem;
          color: #4b5563;
          line-height: 1.5;
          margin: 0;
          display: -webkit-box;
          -webkit-line-clamp: 3;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .card-tags {
          display: flex;
          gap: 6px;
          margin-top: 8px;
          flex-wrap: wrap;
        }

        .card-tag {
          font-size: 0.68rem;
          color: #6b7280;
          background: #f3f4f6;
          padding: 2px 8px;
          border-radius: 8px;
          cursor: pointer;
        }

        .card-tag:active {
          background: #e5e7eb;
        }

        @media (min-width: 1024px) {
          .reflections-page {
            padding: 24px 24px 40px;
            max-width: 640px;
          }

          .annotation-card:hover {
            background: #fafafa;
          }
        }
      `}</style>

      {/* Reflection Detail Panel */}
      <ReflectionDetailPanel
        annotation={selectedAnnotation}
        isOpen={!!selectedAnnotation}
        onClose={() => setSelectedAnnotation(null)}
        onDelete={handleDeleteAnnotation}
      />

      <BottomNav user={user} />
    </div>
  );
}
