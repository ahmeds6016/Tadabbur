'use client';
import { useState, useEffect, useCallback } from 'react';
import { BACKEND_URL } from '../lib/config';

const COLLECTION_ICONS = {
  patience: '\u{1F4AA}',
  trust: '\u{1F6E1}',
  mercy: '\u{1F49B}',
  gratitude: '\u{2728}',
  knowledge: '\u{1F4D6}',
  remembrance: '\u{1F56F}',
  family: '\u{1F46A}',
  justice: '\u{2696}',
  hereafter: '\u{1F319}',
  repentance: '\u{1F6AA}',
  worship: '\u{1F64F}',
  charity: '\u{1F381}',
};

export default function CollectionsGrid({ user, onStudyVerse }) {
  const [collections, setCollections] = useState([]);
  const [progress, setProgress] = useState({});
  const [expandedId, setExpandedId] = useState(null);
  const [expandedData, setExpandedData] = useState({});
  const [loading, setLoading] = useState(true);
  const [expandLoading, setExpandLoading] = useState(null);
  const [error, setError] = useState(null);

  // Fetch collection list
  useEffect(() => {
    let cancelled = false;

    async function fetchCollections() {
      try {
        setLoading(true);
        const res = await fetch(`${BACKEND_URL}/collections`);
        if (!res.ok) throw new Error('Failed to load collections');
        const data = await res.json();
        if (!cancelled) {
          setCollections(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchCollections();
    return () => { cancelled = true; };
  }, []);

  // Fetch user progress for each collection
  useEffect(() => {
    if (!user || collections.length === 0) return;
    let cancelled = false;

    async function fetchProgress() {
      try {
        const token = await user.getIdToken();
        const results = await Promise.all(
          collections.map(async (col) => {
            try {
              const res = await fetch(
                `${BACKEND_URL}/collections/${col.id}/progress`,
                { headers: { Authorization: `Bearer ${token}` } }
              );
              if (!res.ok) return [col.id, null];
              const data = await res.json();
              return [col.id, data];
            } catch {
              return [col.id, null];
            }
          })
        );
        if (!cancelled) {
          setProgress(Object.fromEntries(results.filter(([, v]) => v !== null)));
        }
      } catch {
        // Progress is non-critical; fail silently
      }
    }

    fetchProgress();
    return () => { cancelled = true; };
  }, [user, collections]);

  // Fetch expanded collection details (verse list)
  const handleExpand = useCallback(async (id) => {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }

    setExpandedId(id);

    if (expandedData[id]) return;

    try {
      setExpandLoading(id);
      const res = await fetch(`${BACKEND_URL}/collections/${id}`);
      if (!res.ok) throw new Error('Failed to load verses');
      const data = await res.json();
      setExpandedData((prev) => ({ ...prev, [id]: data }));
    } catch {
      setExpandedId(null);
    } finally {
      setExpandLoading(null);
    }
  }, [expandedId, expandedData]);

  if (loading) {
    return (
      <div className="collections-loading">
        <div className="loading-shimmer" />
        <div className="loading-shimmer" />
        <div className="loading-shimmer" />
        <style jsx>{`
          .collections-loading {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            padding: 16px 0;
          }
          .loading-shimmer {
            height: 180px;
            border-radius: 12px;
            background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
          }
          @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
          }
          @media (max-width: 1024px) {
            .collections-loading { grid-template-columns: repeat(2, 1fr); }
          }
          @media (max-width: 640px) {
            .collections-loading { grid-template-columns: 1fr; }
          }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="collections-error">
        <p>Could not load collections. Please try again later.</p>
        <style jsx>{`
          .collections-error {
            text-align: center;
            padding: 32px 16px;
            color: #6b7280;
            font-size: 0.9rem;
          }
        `}</style>
      </div>
    );
  }

  if (collections.length === 0) return null;

  return (
    <div className="collections-grid">
      {collections.map((col) => {
        const isExpanded = expandedId === col.id;
        const colProgress = progress[col.id];
        const studied = colProgress?.studied_count || 0;
        const total = col.verse_count || 1;
        const pct = Math.round((studied / total) * 100);
        const icon = COLLECTION_ICONS[col.icon] || COLLECTION_ICONS[col.id] || '\u{1F4D6}';
        const verses = expandedData[col.id]?.verses || [];
        const isLoadingVerses = expandLoading === col.id;

        return (
          <div
            key={col.id}
            className={`collection-card ${isExpanded ? 'expanded' : ''}`}
          >
            <div className="card-header">
              <span className="card-icon" role="img" aria-label={col.title}>
                {icon}
              </span>
              <div className="card-info">
                <h3 className="card-title">{col.title}</h3>
                <span className="card-meta">
                  {col.verse_count} verse{col.verse_count !== 1 ? 's' : ''}
                  {col.category ? ` \u00B7 ${col.category}` : ''}
                </span>
              </div>
            </div>

            {col.description && (
              <p className="card-description">{col.description}</p>
            )}

            {user && (
              <div className="progress-section">
                <div className="progress-track">
                  <div
                    className="progress-fill"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="progress-label">{studied}/{total} studied</span>
              </div>
            )}

            <button
              className="explore-btn"
              onClick={() => handleExpand(col.id)}
              aria-expanded={isExpanded}
            >
              {isExpanded ? 'Collapse' : 'Explore'}
            </button>

            {isExpanded && (
              <div className="verse-list">
                {isLoadingVerses ? (
                  <div className="verse-loading">Loading verses...</div>
                ) : verses.length > 0 ? (
                  verses.map((v, i) => (
                    <div key={`${v.surah}-${v.verse}`} className="verse-item">
                      <div className="verse-ref">
                        <span className="verse-number">{i + 1}</span>
                        <div className="verse-detail">
                          <span className="verse-location">
                            {v.surah_name} ({v.surah}:{v.verse})
                          </span>
                          {v.english_text && (
                            <p className="verse-preview">{v.english_text}</p>
                          )}
                        </div>
                      </div>
                      <button
                        className="study-btn"
                        onClick={() => onStudyVerse(v.surah, v.verse)}
                      >
                        Study
                      </button>
                    </div>
                  ))
                ) : (
                  <div className="verse-loading">No verses found.</div>
                )}
              </div>
            )}
          </div>
        );
      })}

      <style jsx>{`
        .collections-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 16px;
          padding: 16px 0;
        }

        .collection-card {
          background: white;
          border: 1px solid var(--border-light, #e5e7eb);
          border-radius: 12px;
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          transition: box-shadow 0.2s ease, border-color 0.2s ease;
        }

        .collection-card:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }

        .collection-card.expanded {
          grid-column: 1 / -1;
          border-color: var(--primary-teal, #0D9488);
          box-shadow: 0 4px 16px rgba(13, 148, 136, 0.12);
        }

        .card-header {
          display: flex;
          align-items: flex-start;
          gap: 12px;
        }

        .card-icon {
          font-size: 1.8rem;
          line-height: 1;
          flex-shrink: 0;
        }

        .card-info {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
        }

        .card-title {
          margin: 0;
          font-size: 1rem;
          font-weight: 600;
          color: var(--deep-blue, #1E3A5F);
          line-height: 1.3;
        }

        .card-meta {
          font-size: 0.78rem;
          color: #6b7280;
        }

        .card-description {
          margin: 0;
          font-size: 0.85rem;
          color: #4b5563;
          line-height: 1.5;
        }

        .progress-section {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .progress-track {
          flex: 1;
          height: 6px;
          background: var(--border-light, #e5e7eb);
          border-radius: 3px;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: var(--gold, #D4AF37);
          border-radius: 3px;
          transition: width 0.4s ease;
          min-width: 0;
        }

        .progress-label {
          font-size: 0.72rem;
          color: #6b7280;
          white-space: nowrap;
          flex-shrink: 0;
        }

        .explore-btn {
          width: 100%;
          padding: 8px 16px;
          background: var(--cream, #FDFBF7);
          border: 1px solid var(--primary-teal, #0D9488);
          border-radius: 8px;
          color: var(--primary-teal, #0D9488);
          font-size: 0.85rem;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.2s ease, color 0.2s ease;
        }

        .explore-btn:hover {
          background: var(--primary-teal, #0D9488);
          color: white;
        }

        .verse-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
          border-top: 1px solid var(--border-light, #e5e7eb);
          padding-top: 12px;
          margin-top: 4px;
        }

        .verse-loading {
          text-align: center;
          padding: 16px;
          color: #6b7280;
          font-size: 0.85rem;
        }

        .verse-item {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
          padding: 10px 12px;
          background: var(--cream, #FDFBF7);
          border-radius: 8px;
          border: 1px solid var(--border-light, #e5e7eb);
        }

        .verse-ref {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          min-width: 0;
          flex: 1;
        }

        .verse-number {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: var(--deep-blue, #1E3A5F);
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.7rem;
          font-weight: 600;
          flex-shrink: 0;
        }

        .verse-detail {
          display: flex;
          flex-direction: column;
          gap: 4px;
          min-width: 0;
        }

        .verse-location {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--deep-blue, #1E3A5F);
        }

        .verse-preview {
          margin: 0;
          font-size: 0.8rem;
          color: #4b5563;
          line-height: 1.4;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .study-btn {
          padding: 6px 14px;
          background: var(--primary-teal, #0D9488);
          border: none;
          border-radius: 6px;
          color: white;
          font-size: 0.8rem;
          font-weight: 600;
          cursor: pointer;
          white-space: nowrap;
          flex-shrink: 0;
          transition: background 0.2s ease;
        }

        .study-btn:hover {
          background: #0b7f74;
        }

        @media (max-width: 1024px) {
          .collections-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }

        @media (max-width: 640px) {
          .collections-grid {
            grid-template-columns: 1fr;
            gap: 12px;
          }

          .collection-card {
            padding: 16px;
          }

          .card-icon {
            font-size: 1.5rem;
          }

          .card-title {
            font-size: 0.95rem;
          }
        }
      `}</style>
    </div>
  );
}
