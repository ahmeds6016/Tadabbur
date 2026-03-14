'use client';
import { useState, useEffect } from 'react';
import { BACKEND_URL } from '../lib/config';

export default function DigestViewer({ user, onDigestGenerated, refreshKey = 0 }) {
  const [digest, setDigest] = useState(null);
  const [weekId, setWeekId] = useState('');
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  // Fetch latest digest on mount and when refreshKey changes (e.g. after new log)
  useEffect(() => {
    if (user) fetchLatest();
  }, [user, refreshKey]);

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

  const [restriction, setRestriction] = useState(null);

  const handleGenerate = async () => {
    if (generating) return;
    setGenerating(true);
    setError('');
    setRestriction(null);
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
        if (data.restriction) {
          setRestriction(data);
          return;
        }
        setError(data.error || 'Failed to generate digest');
        return;
      }
      setDigest(data.digest);
      setWeekId(data.week_id || '');
      if (onDigestGenerated) onDigestGenerated();
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
          {restriction ? (
            <>
              {restriction.restriction === 'monday_only' ? (
                <>
                  <p className="dv-empty-text">
                    Your weekly digest will be ready on Monday.
                  </p>
                  <p style={{ fontSize: '0.78rem', color: '#9ca3af', margin: '4px 0 0 0' }}>
                    Today is {restriction.day_of_week}. Keep logging — your reflection awaits.
                  </p>
                </>
              ) : restriction.restriction === 'min_days' ? (
                <>
                  <p className="dv-empty-text">
                    Almost there! Log a few more days to unlock your digest.
                  </p>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'center',
                    gap: 6,
                    margin: '10px 0',
                  }}>
                    {[1, 2, 3, 4].map((n) => (
                      <div key={n} style={{
                        width: 28,
                        height: 28,
                        borderRadius: '50%',
                        background: n <= (restriction.days_logged || 0) ? '#0d9488' : '#e5e7eb',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        color: n <= (restriction.days_logged || 0) ? 'white' : '#9ca3af',
                      }}>
                        {n}
                      </div>
                    ))}
                  </div>
                  <p style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', margin: 0 }}>
                    {restriction.days_logged}/4 days logged this week
                  </p>
                </>
              ) : null}
            </>
          ) : (() => {
            const isMonday = new Date().getDay() === 1;
            return (
              <>
                <p className="dv-empty-text">
                  Your weekly spiritual reflection awaits.
                </p>
                {!isMonday && (
                  <p style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', margin: '0 0 12px 0' }}>
                    Digests are generated on Mondays. Keep logging — your reflection awaits.
                  </p>
                )}
                <button
                  className="dv-generate-btn"
                  onClick={handleGenerate}
                  disabled={generating || !isMonday}
                >
                  {generating ? 'Reflecting on your week...' : "Generate This Week's Digest"}
                </button>
                {error && <p className="dv-error">{error}</p>}
              </>
            );
          })()}
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
          background: var(--color-surface);
          border-radius: 14px;
          border: 1px solid var(--color-border);
          overflow: hidden;
        }
        .dv-empty {
          padding: 24px 16px;
          text-align: center;
        }
        .dv-empty-text {
          font-size: 0.9rem;
          color: var(--color-text-secondary);
          margin: 0 0 14px 0;
        }
        .dv-generate-btn {
          padding: 10px 20px;
          border-radius: 10px;
          border: none;
          background: var(--color-secondary, #0d9488);
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
          color: var(--color-error);
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
          color: var(--color-text-muted);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .dv-opening {
          font-size: 0.95rem;
          color: var(--color-text);
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
          color: var(--color-text-secondary);
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
          color: var(--color-text);
          margin: 0;
          line-height: 1.6;
        }
        .dv-verse-card {
          margin: 16px 0;
          padding: 14px;
          background: var(--color-surface-muted);
          border-radius: 10px;
          border-left: 3px solid var(--color-secondary, #0d9488);
          text-align: center;
        }
        .dv-verse-text {
          font-size: 0.9rem;
          font-style: italic;
          color: var(--color-text);
          margin: 0 0 6px 0;
          line-height: 1.5;
        }
        .dv-verse-ref {
          font-size: 0.7rem;
          color: var(--color-text-secondary);
          display: block;
        }
        .dv-verse-why {
          font-size: 0.78rem;
          color: var(--color-text-secondary);
          margin: 8px 0 0 0;
          font-style: italic;
          line-height: 1.4;
        }
        .dv-closing {
          font-size: 0.8rem;
          color: var(--color-text-secondary);
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
          border: 1px solid var(--color-border);
          background: transparent;
          font-size: 0.75rem;
          color: var(--color-text-secondary);
          cursor: pointer;
        }
        .dv-regenerate-btn:disabled {
          opacity: 0.5;
        }
      `}</style>
    </div>
  );
}
