'use client';
import { useState } from 'react';
import { BACKEND_URL } from '../lib/config';
import ConfirmDialog from './ConfirmDialog';

const BEHAVIOR_LABELS = {
  fajr_prayer: 'Fajr', dhuhr_prayer: 'Dhuhr', asr_prayer: 'Asr',
  maghrib_prayer: 'Maghrib', isha_prayer: 'Isha', masjid_attendance: 'Masjid',
  fasting: 'Fasting', avoided_sins: 'Avoided Sins', tawbah_moment: 'Tawbah',
  lowering_gaze: 'Gaze', device_discipline: 'Device', quran_minutes: 'Quran',
  tadabbur_session: 'Tadabbur', quran_memorization: 'Memorization',
  sunnah_prayers: 'Sunnah', tahajjud: 'Tahajjud', dhikr_minutes: 'Dhikr',
  dua_moments: 'Dua', charity: 'Charity', gratitude_entry: 'Gratitude',
  kindness_act: 'Kindness', forgiveness: 'Forgiveness', family_rights: 'Family',
  tongue_control: 'Tongue', sleep_hours: 'Sleep', exercise: 'Exercise',
  healthy_eating: 'Eating',
};

const TREND_ARROWS = {
  improving: { symbol: '↑', color: '#059669' },
  stable: { symbol: '→', color: '#6b7280' },
  declining: { symbol: '↓', color: '#dc2626' },
  insufficient_data: { symbol: '·', color: '#d1d5db' },
};

export default function StruggleCard({ struggle, user, onResolved }) {
  const [showGuidance, setShowGuidance] = useState(false);
  const [guidance, setGuidance] = useState(null);
  const [loadingGuidance, setLoadingGuidance] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [expandedExcerpts, setExpandedExcerpts] = useState({});
  const [showResolveConfirm, setShowResolveConfirm] = useState(false);

  const progress = struggle.progress || {};
  const phases = ['Acknowledge', 'Anchor', 'Expand', 'Sustain'];
  const currentPhase = progress.current_phase || 0;
  const trends = progress.linked_behavior_trends || {};

  const handleReadGuidance = async () => {
    if (guidance) {
      setShowGuidance(!showGuidance);
      return;
    }
    setLoadingGuidance(true);
    try {
      const token = await user.getIdToken();
      const res = await fetch(
        `${BACKEND_URL}/iman/struggle/${struggle.struggle_id}/guidance`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await res.json();
      if (res.ok) {
        setGuidance(data);
        setShowGuidance(true);
      }
    } catch (err) {
      console.error('Failed to load guidance:', err);
    } finally {
      setLoadingGuidance(false);
    }
  };

  const handleResolve = async () => {
    if (resolving) return;
    setResolving(true);
    try {
      const token = await user.getIdToken();
      const res = await fetch(
        `${BACKEND_URL}/iman/struggle/${struggle.struggle_id}`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ action: 'resolve' }),
        }
      );
      if (res.ok && onResolved) {
        onResolved(struggle.struggle_id);
      }
    } catch (err) {
      console.error('Failed to resolve struggle:', err);
    } finally {
      setResolving(false);
    }
  };

  return (
    <div className="struggle-card" style={{ borderLeftColor: struggle.color }}>
      {/* Header */}
      <div className="sc-header">
        <span className="sc-label" style={{ color: struggle.color }}>
          {struggle.label}
        </span>
        <span className="sc-weeks">
          {progress.weeks_active != null
            ? `Week ${progress.weeks_active + 1}`
            : ''}
        </span>
      </div>

      {/* Phase progress bar */}
      <div className="sc-phases">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`sc-phase-dot ${i < currentPhase ? 'done' : ''} ${i === currentPhase ? 'active' : ''}`}
            style={{
              backgroundColor:
                i <= currentPhase ? struggle.color : '#e5e7eb',
            }}
          />
        ))}
        <div className="sc-phase-bar">
          <div
            className="sc-phase-fill"
            style={{
              width: `${((currentPhase * 100) + (progress.phase_progress_pct || 0)) / 4}%`,
              backgroundColor: struggle.color,
            }}
          />
        </div>
      </div>

      {/* Current phase description */}
      {progress.phase_title && (
        <p className="sc-phase-text">{progress.phase_title}</p>
      )}

      {/* Linked behavior trends */}
      {Object.keys(trends).length > 0 && (
        <div className="sc-trends">
          {struggle.linked_behaviors?.map((bid) => {
            const trend = trends[bid];
            if (!trend) return null;
            const t = TREND_ARROWS[trend] || TREND_ARROWS.insufficient_data;
            return (
              <span key={bid} className="sc-trend-pill" style={{ color: t.color }}>
                {BEHAVIOR_LABELS[bid] || bid} {t.symbol}
              </span>
            );
          })}
        </div>
      )}

      {/* Comfort verse */}
      {struggle.comfort_verse && (
        <p className="sc-comfort">
          "{struggle.comfort_verse.text}"
          <span className="sc-comfort-ref">
            — {struggle.comfort_verse.surah}:{struggle.comfort_verse.verse}
          </span>
        </p>
      )}

      {/* Actions */}
      <div className="sc-actions">
        <button
          className="sc-btn guidance"
          onClick={handleReadGuidance}
          disabled={loadingGuidance}
        >
          {loadingGuidance ? (
            <><span className="sc-spinner" /> Loading...</>
          ) : showGuidance ? 'Hide Guidance' : 'Read Guidance'}
        </button>
        <button
          className="sc-btn resolve"
          onClick={() => setShowResolveConfirm(true)}
          disabled={resolving}
        >
          {resolving ? '...' : 'Mark Resolved'}
        </button>
      </div>

      <ConfirmDialog
        isOpen={showResolveConfirm}
        title="Resolve this struggle?"
        message={
          currentPhase < 3
            ? `You're in ${phases[currentPhase]} (Week ${(progress.weeks_active || 0) + 1}). Resolving now means you won't continue through the remaining phases. Are you sure?`
            : `You've reached the Sustain phase — well done. Ready to mark this resolved?`
        }
        confirmText={resolving ? '...' : 'Yes, resolve'}
        cancelText="Keep going"
        confirmStyle="warning"
        onConfirm={() => { setShowResolveConfirm(false); handleResolve(); }}
        onCancel={() => setShowResolveConfirm(false)}
      />

      {/* Expanded guidance */}
      {showGuidance && guidance && (
        <div className="sc-guidance">
          {guidance.guidance_excerpts?.map((g, i) => (
            <div key={i} className="sc-excerpt">
              <span className="sc-source">{g.source}</span>
              {g.title && <span className="sc-title">{g.title}</span>}
              <p className="sc-text">
                {expandedExcerpts[i] ? g.text : g.text?.slice(0, 300)}
                {g.text?.length > 300 && (
                  <button
                    className="sc-expand-btn"
                    onClick={() => setExpandedExcerpts(prev => ({ ...prev, [i]: !prev[i] }))}
                  >
                    {expandedExcerpts[i] ? 'Show less' : '...Show more'}
                  </button>
                )}
              </p>
            </div>
          ))}
          {guidance.comfort_verses?.length > 1 && (
            <div className="sc-more-verses">
              {guidance.comfort_verses.slice(1).map((v, i) => (
                <p key={i} className="sc-verse-item">
                  "{v.text}" — {v.surah}:{v.verse}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .struggle-card {
          padding: 14px;
          background: var(--color-surface);
          border-radius: 12px;
          border: 1px solid var(--color-border);
          border-left: 3px solid;
          margin-bottom: 12px;
        }
        .sc-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
        }
        .sc-label {
          font-size: 0.95rem;
          font-weight: 600;
        }
        .sc-weeks {
          font-size: 0.75rem;
          color: var(--color-text-secondary);
        }
        .sc-phases {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 8px;
          position: relative;
        }
        .sc-phase-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          z-index: 1;
          flex-shrink: 0;
        }
        .sc-phase-bar {
          position: absolute;
          left: 5px;
          right: 5px;
          height: 3px;
          background: var(--color-border);
          border-radius: 2px;
          z-index: 0;
        }
        .sc-phase-fill {
          height: 100%;
          border-radius: 2px;
          transition: width 0.4s ease;
        }
        .sc-phase-text {
          font-size: 0.78rem;
          color: var(--color-text);
          margin: 0 0 10px 0;
          line-height: 1.4;
          font-style: italic;
        }
        .sc-trends {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-bottom: 10px;
        }
        .sc-trend-pill {
          font-size: 0.7rem;
          font-weight: 500;
          padding: 2px 8px;
          background: var(--color-surface-muted);
          border-radius: 12px;
        }
        .sc-comfort {
          font-size: 0.78rem;
          font-style: italic;
          color: var(--color-text);
          margin: 0 0 10px 0;
          line-height: 1.5;
        }
        .sc-comfort-ref {
          font-size: 0.65rem;
          color: var(--color-text-muted);
          font-style: normal;
        }
        .sc-actions {
          display: flex;
          gap: 8px;
        }
        .sc-btn {
          flex: 1;
          padding: 8px 12px;
          border-radius: 8px;
          font-size: 0.78rem;
          font-weight: 500;
          border: none;
          cursor: pointer;
          transition: opacity 0.15s;
        }
        .sc-btn:disabled {
          opacity: 0.5;
          cursor: wait;
        }
        .sc-spinner {
          display: inline-block;
          width: 12px;
          height: 12px;
          border: 2px solid #bfe0fb;
          border-top-color: #0284c7;
          border-radius: 50%;
          animation: sc-spin 0.6s linear infinite;
          vertical-align: middle;
          margin-right: 4px;
        }
        @keyframes sc-spin {
          to { transform: rotate(360deg); }
        }
        .sc-btn.guidance {
          background: var(--color-info-bg, #f0f9ff);
          color: var(--color-info, #0284c7);
        }
        .sc-btn.resolve {
          background: var(--color-success-bg, #f0fdf4);
          color: var(--color-success, #059669);
        }
        .sc-guidance {
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid var(--color-border);
        }
        .sc-excerpt {
          margin-bottom: 10px;
          padding: 10px;
          background: var(--color-surface-muted);
          border-radius: 8px;
        }
        .sc-source {
          font-size: 0.68rem;
          font-weight: 600;
          color: var(--color-text-muted);
          text-transform: uppercase;
          display: block;
        }
        .sc-title {
          font-size: 0.75rem;
          font-weight: 500;
          color: var(--color-text-secondary);
          display: block;
          margin-top: 2px;
        }
        .sc-text {
          font-size: 0.8rem;
          color: var(--color-text);
          margin: 4px 0 0 0;
          line-height: 1.5;
        }
        .sc-expand-btn {
          background: none;
          border: none;
          color: var(--color-info, #0284c7);
          font-size: 0.78rem;
          cursor: pointer;
          padding: 0;
          margin-left: 2px;
          font-weight: 500;
        }
        .sc-expand-btn:hover {
          text-decoration: underline;
        }
        .sc-more-verses {
          margin-top: 8px;
        }
        .sc-verse-item {
          font-size: 0.78rem;
          font-style: italic;
          color: var(--color-text-secondary);
          margin: 4px 0;
          line-height: 1.4;
        }
      `}</style>
    </div>
  );
}
