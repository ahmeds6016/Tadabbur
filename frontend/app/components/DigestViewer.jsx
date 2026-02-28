'use client';
import { useState, useEffect } from 'react';
import { BACKEND_URL } from '../lib/config';

export default function DigestViewer({ user }) {
  const [digest, setDigest] = useState(null);
  const [weekId, setWeekId] = useState('');
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  // Fetch latest digest on mount
  useEffect(() => {
    if (user) fetchLatest();
  }, [user]);

  const fetchLatest = async () => {
    setLoading(true);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/digest/latest`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok && data.digest) {
        setDigest(data.digest);
        setWeekId(data.week_id || '');
      }
    } catch (err) {
      console.error('Failed to fetch digest:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (generating) return;
    setGenerating(true);
    setError('');
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/digest/generate`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || 'Failed to generate digest');
        return;
      }
      setDigest(data.digest);
      setWeekId(data.week_id || '');
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return null;

  const verse = digest?.verse_to_carry;

  return (
    <div className="digest-viewer">
      {!digest ? (
        <div className="dv-empty">
          <p className="dv-empty-text">
            Your weekly spiritual reflection awaits.
          </p>
          <button
            className="dv-generate-btn"
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? 'Reflecting on your week...' : "Generate This Week's Digest"}
          </button>
          {error && <p className="dv-error">{error}</p>}
        </div>
      ) : (
        <div className="dv-content">
          <div className="dv-header">
            <span className="dv-week-label">
              Weekly Digest
              {digest.week_start && ` — ${digest.week_start}`}
            </span>
          </div>

          {/* Opening */}
          {digest.opening && (
            <p className="dv-opening">{digest.opening}</p>
          )}

          {/* Weekly Story */}
          {digest.weekly_story && (
            <div className="dv-section">
              <p className="dv-body">{digest.weekly_story}</p>
            </div>
          )}

          {/* Strength */}
          {digest.strength_noticed && (
            <div className="dv-section strength">
              <span className="dv-section-label">Strength noticed</span>
              <p className="dv-body">{digest.strength_noticed}</p>
            </div>
          )}

          {/* Correlation insight */}
          {digest.correlation_insight && (
            <div className="dv-section">
              <span className="dv-section-label">Pattern observed</span>
              <p className="dv-body">{digest.correlation_insight}</p>
            </div>
          )}

          {/* Gentle attention */}
          {digest.gentle_attention && (
            <div className="dv-section gentle">
              <span className="dv-section-label">Gentle attention</span>
              <p className="dv-body">{digest.gentle_attention}</p>
            </div>
          )}

          {/* Verse to carry */}
          {verse && verse.text && (
            <div className="dv-verse-card">
              <p className="dv-verse-text">"{verse.text}"</p>
              <span className="dv-verse-ref">
                — Surah {verse.surah}:{verse.verse}
              </span>
              {verse.why && (
                <p className="dv-verse-why">{verse.why}</p>
              )}
            </div>
          )}

          {/* Closing */}
          {digest.closing && (
            <p className="dv-closing">{digest.closing}</p>
          )}

          {/* Generate new */}
          <button
            className="dv-regenerate-btn"
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? 'Generating...' : 'Refresh Digest'}
          </button>
        </div>
      )}

      <style jsx>{`
        .digest-viewer {
          background: white;
          border-radius: 14px;
          border: 1px solid var(--border-light, #e5e7eb);
          overflow: hidden;
        }
        .dv-empty {
          padding: 24px 16px;
          text-align: center;
        }
        .dv-empty-text {
          font-size: 0.9rem;
          color: #6b7280;
          margin: 0 0 14px 0;
        }
        .dv-generate-btn {
          padding: 10px 20px;
          border-radius: 10px;
          border: none;
          background: var(--primary-teal, #0d9488);
          color: white;
          font-size: 0.85rem;
          font-weight: 500;
          cursor: pointer;
          transition: opacity 0.15s;
        }
        .dv-generate-btn:disabled {
          opacity: 0.6;
          cursor: wait;
        }
        .dv-error {
          color: #dc2626;
          font-size: 0.8rem;
          margin-top: 10px;
        }
        .dv-content {
          padding: 18px 16px;
        }
        .dv-header {
          margin-bottom: 14px;
        }
        .dv-week-label {
          font-size: 0.75rem;
          font-weight: 600;
          color: #9ca3af;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .dv-opening {
          font-size: 0.95rem;
          color: var(--deep-blue, #1e293b);
          margin: 0 0 14px 0;
          line-height: 1.5;
          font-weight: 500;
        }
        .dv-section {
          margin-bottom: 14px;
        }
        .dv-section-label {
          font-size: 0.7rem;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.4px;
          display: block;
          margin-bottom: 4px;
        }
        .dv-section.strength .dv-section-label {
          color: #059669;
        }
        .dv-section.gentle .dv-section-label {
          color: #d97706;
        }
        .dv-body {
          font-size: 0.85rem;
          color: #374151;
          margin: 0;
          line-height: 1.6;
        }
        .dv-verse-card {
          margin: 16px 0;
          padding: 14px;
          background: #f0fdf4;
          border-radius: 10px;
          border-left: 3px solid var(--primary-teal, #0d9488);
          text-align: center;
        }
        .dv-verse-text {
          font-size: 0.9rem;
          font-style: italic;
          color: var(--deep-blue, #1e293b);
          margin: 0 0 6px 0;
          line-height: 1.5;
        }
        .dv-verse-ref {
          font-size: 0.7rem;
          color: #6b7280;
          display: block;
        }
        .dv-verse-why {
          font-size: 0.78rem;
          color: #4b5563;
          margin: 8px 0 0 0;
          font-style: italic;
          line-height: 1.4;
        }
        .dv-closing {
          font-size: 0.8rem;
          color: #6b7280;
          font-style: italic;
          margin: 14px 0 10px 0;
          text-align: center;
          line-height: 1.5;
        }
        .dv-regenerate-btn {
          display: block;
          margin: 10px auto 0;
          padding: 6px 14px;
          border-radius: 6px;
          border: 1px solid #e5e7eb;
          background: transparent;
          font-size: 0.75rem;
          color: #6b7280;
          cursor: pointer;
        }
        .dv-regenerate-btn:disabled {
          opacity: 0.5;
        }
      `}</style>
    </div>
  );
}
