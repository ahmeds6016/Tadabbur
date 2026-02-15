'use client';
import { useState, useEffect } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import Link from 'next/link';
import { auth } from '../lib/firebase';
import { BACKEND_URL } from '../lib/config';
import BottomNav from '../components/BottomNav';
import BadgeDisplay from '../components/BadgeDisplay';

export default function ProgressPage() {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        await fetchProgress(currentUser);
      }
      setIsLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const fetchProgress = async (currentUser) => {
    try {
      const token = await currentUser.getIdToken();
      const res = await fetch(`${BACKEND_URL}/progress`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error(`Failed to load progress (${res.status})`);
      const data = await res.json();
      setProgress(data);
    } catch (err) {
      console.error('Failed to fetch progress:', err);
      setError(err.message);
    }
  };

  const getTileColor = (explored, total) => {
    if (total === 0) return '#f1f5f9';
    const pct = (explored / total) * 100;
    if (pct === 0) return '#f1f5f9';
    if (pct <= 25) return '#ccfbf1';
    if (pct <= 75) return '#5eead4';
    if (pct < 100) return '#f0c040';
    return '#fbbf24';
  };

  const isComplete = (explored, total) => total > 0 && explored === total;

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
          <h1>Please sign in to view your progress</h1>
          <Link href="/">
            <button style={{ marginTop: '20px' }}>Go to Home</button>
          </Link>
        </div>
      </div>
    );
  }

  const totalExplored = progress?.total_explored || 0;
  const totalVerses = progress?.total_verses || 6236;
  const percentage = progress?.percentage || 0;
  const surahs = progress?.surahs || [];

  return (
    <div className="container" style={{ paddingBottom: 100 }}>
      <div className="card">
        {/* Header */}
        <div className="progress-header">
          <h1 className="progress-title">Your Quran Journey</h1>
          <div className="progress-summary">
            <span className="progress-count">{totalExplored.toLocaleString()}</span>
            <span className="progress-total"> / 6,236</span>
            <span className="progress-pct"> ({percentage}%)</span>
          </div>
          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{ width: `${Math.min(percentage, 100)}%` }}
            />
          </div>
        </div>

        {/* Badges */}
        <div className="badges-section">
          <BadgeDisplay user={user} compact={false} />
        </div>

        {/* Error state */}
        {error && (
          <div style={{ textAlign: 'center', padding: '20px', color: '#b91c1c', fontSize: '0.9rem' }}>
            {error}
            <button
              onClick={() => { setError(null); fetchProgress(user); }}
              style={{ display: 'block', margin: '12px auto 0', padding: '8px 16px', border: '1px solid var(--border-light)', borderRadius: '8px', background: 'white', cursor: 'pointer' }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Surah grid */}
        {!error && (
          <div className="surah-grid">
            {surahs.map((surah) => {
              const pct = surah.total_verses > 0
                ? Math.round((surah.explored_count / surah.total_verses) * 100)
                : 0;
              const complete = isComplete(surah.explored_count, surah.total_verses);
              const bg = getTileColor(surah.explored_count, surah.total_verses);

              return (
                <button
                  key={surah.number}
                  className={`surah-tile ${complete ? 'surah-tile--complete' : ''}`}
                  style={{ backgroundColor: bg }}
                  onClick={() => { window.location.href = `/?query=${surah.number}:1`; }}
                  title={`${surah.name} - ${surah.explored_count}/${surah.total_verses} verses explored`}
                >
                  <span className="surah-tile__number">{surah.number}</span>
                  <span className="surah-tile__name">{surah.name}</span>
                  <div className="surah-tile__bar-track">
                    <div
                      className="surah-tile__bar-fill"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* Legend */}
        {!error && surahs.length > 0 && (
          <div className="legend">
            <div className="legend-item">
              <span className="legend-swatch" style={{ background: '#f1f5f9' }} />
              <span>0%</span>
            </div>
            <div className="legend-item">
              <span className="legend-swatch" style={{ background: '#ccfbf1' }} />
              <span>1-25%</span>
            </div>
            <div className="legend-item">
              <span className="legend-swatch" style={{ background: '#5eead4' }} />
              <span>26-75%</span>
            </div>
            <div className="legend-item">
              <span className="legend-swatch" style={{ background: '#f0c040' }} />
              <span>76-99%</span>
            </div>
            <div className="legend-item">
              <span className="legend-swatch legend-swatch--glow" style={{ background: '#fbbf24' }} />
              <span>100%</span>
            </div>
          </div>
        )}
      </div>

      <BottomNav user={user} />

      <style jsx>{`
        .progress-header {
          text-align: center;
          margin-bottom: 28px;
        }
        .progress-title {
          font-size: 1.6rem;
          font-weight: 800;
          color: var(--deep-blue, #1e293b);
          margin: 0 0 12px 0;
        }
        .progress-summary {
          margin-bottom: 12px;
          font-size: 1.05rem;
        }
        .progress-count {
          font-weight: 800;
          color: var(--primary-teal, #0d9488);
          font-size: 1.3rem;
        }
        .progress-total {
          color: #666;
          font-weight: 600;
        }
        .progress-pct {
          color: var(--gold, #d4a017);
          font-weight: 700;
        }
        .progress-bar-track {
          width: 100%;
          height: 12px;
          background: var(--border-light, #e5e7eb);
          border-radius: 6px;
          overflow: hidden;
        }
        .progress-bar-fill {
          height: 100%;
          background: linear-gradient(90deg, var(--primary-teal, #0d9488), var(--gold, #d4a017));
          border-radius: 6px;
          transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
          animation: barPulse 2s ease-in-out infinite;
        }
        @keyframes barPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.85; }
        }

        .badges-section {
          margin-bottom: 28px;
          padding: 20px;
          background: var(--cream, #faf6f0);
          border-radius: 16px;
          border: 2px solid var(--border-light, #e5e7eb);
        }

        .surah-grid {
          display: grid;
          grid-template-columns: repeat(6, 1fr);
          gap: 8px;
          margin-bottom: 24px;
        }
        @media (max-width: 900px) {
          .surah-grid {
            grid-template-columns: repeat(4, 1fr);
          }
        }
        @media (max-width: 520px) {
          .surah-grid {
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
          }
        }

        .surah-tile {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 3px;
          padding: 10px 6px 8px;
          border-radius: 10px;
          border: 1.5px solid var(--border-light, #e5e7eb);
          cursor: pointer;
          transition: transform 0.15s ease, box-shadow 0.15s ease;
          text-align: center;
          min-height: 72px;
        }
        .surah-tile:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        .surah-tile:active {
          transform: scale(0.97);
        }
        .surah-tile--complete {
          border-color: var(--gold, #d4a017);
          animation: completedGlow 2s ease-in-out infinite;
        }
        @keyframes completedGlow {
          0%, 100% { box-shadow: 0 0 6px rgba(251, 191, 36, 0.3); }
          50% { box-shadow: 0 0 14px rgba(251, 191, 36, 0.6); }
        }

        .surah-tile__number {
          font-size: 0.65rem;
          font-weight: 600;
          color: #888;
          line-height: 1;
        }
        .surah-tile__name {
          font-size: 0.75rem;
          font-weight: 700;
          color: var(--deep-blue, #1e293b);
          line-height: 1.2;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          max-width: 100%;
        }
        .surah-tile__bar-track {
          width: 80%;
          height: 4px;
          background: rgba(0, 0, 0, 0.1);
          border-radius: 2px;
          overflow: hidden;
          margin-top: 2px;
        }
        .surah-tile__bar-fill {
          height: 100%;
          background: var(--primary-teal, #0d9488);
          border-radius: 2px;
          transition: width 0.4s ease;
        }

        .legend {
          display: flex;
          justify-content: center;
          flex-wrap: wrap;
          gap: 16px;
          padding: 16px 0 8px;
          font-size: 0.8rem;
          color: #666;
        }
        .legend-item {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .legend-swatch {
          width: 16px;
          height: 16px;
          border-radius: 4px;
          border: 1px solid #d1d5db;
          flex-shrink: 0;
        }
        .legend-swatch--glow {
          animation: completedGlow 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
