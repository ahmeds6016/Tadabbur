'use client';
import { useState, useEffect } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../lib/firebase';
import { BACKEND_URL } from '../lib/config';
import Link from 'next/link';

import { Settings } from 'lucide-react';
import JournalEntry from '../components/JournalEntry';
import TrajectoryDisplay from '../components/TrajectoryDisplay';
import DigestViewer from '../components/DigestViewer';
import HeartPatterns from '../components/HeartPatterns';
import StruggleDeclaration from '../components/StruggleDeclaration';
import StruggleCard from '../components/StruggleCard';
import ImanOnboarding from '../components/ImanOnboarding';
import BottomNav from '../components/BottomNav';

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function getDateStr(offset = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return d.toISOString().split('T')[0];
}

export default function JournalPage() {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(getDateStr(0));
  const [trajectory, setTrajectory] = useState(null);
  const [categories, setCategories] = useState([]);
  const [activeStruggles, setActiveStruggles] = useState([]);
  const [showStruggleGrid, setShowStruggleGrid] = useState(false);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [correlationInsight, setCorrelationInsight] = useState(null);
  const [safeguards, setSafeguards] = useState(null);

  // Auth
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        await Promise.all([
          fetchTrajectory(currentUser),
          fetchStruggles(currentUser),
          fetchCorrelations(currentUser),
        ]);
      }
      setIsLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const fetchTrajectory = async (currentUser) => {
    try {
      const token = await currentUser.getIdToken();
      const headers = { Authorization: `Bearer ${token}` };

      const [trajRes, configRes] = await Promise.all([
        fetch(`${BACKEND_URL}/iman/trajectory`, { headers }),
        fetch(`${BACKEND_URL}/iman/config`, { headers }),
      ]);

      if (!configRes.ok) {
        // No config → needs onboarding
        setNeedsOnboarding(true);
        return;
      }
      const configData = await configRes.json();
      if (!configData.config?.onboarding_complete) {
        setNeedsOnboarding(true);
        return;
      }
      if (configData.categories) setCategories(configData.categories);

      if (trajRes.ok) {
        const trajData = await trajRes.json();
        if (trajData.trajectory) {
          setTrajectory(trajData.trajectory);
          if (trajData.trajectory.safeguards) {
            setSafeguards(trajData.trajectory.safeguards);
          }
        }
      }
    } catch (err) {
      console.error('Failed to fetch trajectory:', err);
    }
  };

  const fetchStruggles = async (currentUser) => {
    try {
      const token = await currentUser.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/struggles`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setActiveStruggles(data.active || []);
      }
    } catch (err) {
      console.error('Failed to fetch struggles:', err);
    }
  };

  const fetchCorrelations = async (currentUser) => {
    try {
      const token = await currentUser.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/correlations`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.weekly_insight) {
          setCorrelationInsight(data.weekly_insight);
        }
      }
    } catch (err) {
      console.error('Failed to fetch correlations:', err);
    }
  };

  const handleStruggleDeclared = (result) => {
    setShowStruggleGrid(false);
    fetchStruggles(user);
  };

  const handleStruggleResolved = (struggleId) => {
    setActiveStruggles((prev) => prev.filter((s) => s.struggle_id !== struggleId));
  };

  const handleOnboardingComplete = async () => {
    setNeedsOnboarding(false);
    if (user) {
      await Promise.all([
        fetchTrajectory(user),
        fetchStruggles(user),
        fetchCorrelations(user),
      ]);
    }
  };

  const handleTrajectoryUpdate = (newTrajectory, responseSafeguards) => {
    setTrajectory(newTrajectory);
    if (responseSafeguards) setSafeguards(responseSafeguards);
  };

  // Generate date navigation (today + past 6 days)
  const dateOptions = [];
  for (let i = 0; i < 7; i++) {
    const ds = getDateStr(-i);
    dateOptions.push({
      date: ds,
      label: i === 0 ? 'Today' : i === 1 ? 'Yesterday' : formatDate(ds),
    });
  }

  if (isLoading) {
    return (
      <div className="journal-page">
        <div className="loading-state">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="journal-page">
        <div className="auth-gate">
          <h2>Journal</h2>
          <p>Sign in to access your spiritual journal and Iman Index.</p>
          <Link href="/">
            <button className="go-home-btn">Go to Home</button>
          </Link>
        </div>
        <BottomNav user={null} />
      </div>
    );
  }

  if (needsOnboarding) {
    return (
      <div className="journal-page">
        <ImanOnboarding user={user} onComplete={handleOnboardingComplete} />
        <BottomNav user={user} />
      </div>
    );
  }

  return (
    <div className="journal-page">
      <div className="journal-container">
        {/* Header */}
        <header className="journal-header">
          <h1>Journal</h1>
          <p className="header-sub">Daily spiritual reflection</p>
          <Link href="/settings" className="settings-link">
            <Settings size={20} />
          </Link>
        </header>

        {/* Date navigation */}
        <div className="date-nav">
          <div className="date-scroll">
            {dateOptions.map((opt) => (
              <button
                key={opt.date}
                className={`date-chip ${selectedDate === opt.date ? 'active' : ''}`}
                onClick={() => setSelectedDate(opt.date)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Scrupulosity gentleness banner */}
        {safeguards?.scrupulosity?.active && (
          <div className="gentleness-banner">
            <p>{safeguards.scrupulosity.message}</p>
          </div>
        )}

        {/* Trajectory display */}
        <TrajectoryDisplay trajectory={trajectory} categories={categories} />

        {/* Weekly digest */}
        <DigestViewer user={user} />

        {/* Heart note patterns */}
        <HeartPatterns user={user} />

        {/* Correlation insight */}
        {correlationInsight && (
          <div className="correlation-card">
            <h3 className="section-label">Pattern Observed</h3>
            <p className="correlation-text">{correlationInsight.insight_text}</p>
            <span className="correlation-caveat">This is a pattern, not a rule.</span>
          </div>
        )}

        {/* Active struggles */}
        {activeStruggles.length > 0 && (
          <div className="struggles-section">
            <h3 className="section-label">Active Struggles</h3>
            {activeStruggles.map((s) => (
              <StruggleCard
                key={s.struggle_id}
                struggle={s}
                user={user}
                onResolved={handleStruggleResolved}
              />
            ))}
          </div>
        )}

        {/* Struggle declaration toggle */}
        {!showStruggleGrid ? (
          <button
            className="add-struggle-btn"
            onClick={() => setShowStruggleGrid(true)}
          >
            + Declare a Struggle
          </button>
        ) : (
          <StruggleDeclaration
            user={user}
            activeStruggleIds={activeStruggles.map((s) => s.struggle_id)}
            onDeclared={handleStruggleDeclared}
          />
        )}

        {/* Journal entry form */}
        <JournalEntry
          user={user}
          date={selectedDate}
          onTrajectoryUpdate={handleTrajectoryUpdate}
        />
      </div>

      <BottomNav user={user} />

      <style jsx>{`
        .journal-page {
          min-height: 100vh;
          background: var(--cream, #faf6f0);
        }
        .journal-container {
          max-width: 600px;
          margin: 0 auto;
          padding: 16px 16px 80px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .loading-state {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 60vh;
          color: #6b7280;
        }
        .auth-gate {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 60vh;
          text-align: center;
          padding: 24px;
          gap: 12px;
        }
        .auth-gate h2 {
          font-size: 1.5rem;
          color: var(--deep-blue, #1e293b);
        }
        .auth-gate p {
          color: #6b7280;
          font-size: 0.95rem;
        }
        .go-home-btn {
          padding: 10px 24px;
          border-radius: 8px;
          border: none;
          background: var(--primary-teal, #0d9488);
          color: white;
          font-size: 0.95rem;
          cursor: pointer;
        }

        /* Header */
        .journal-header {
          text-align: center;
          padding: 8px 0;
          position: relative;
        }
        .journal-header h1 {
          margin: 0;
          font-size: 1.6rem;
          color: var(--primary-teal, #0d9488);
          font-weight: 700;
        }
        .header-sub {
          margin: 4px 0 0;
          font-size: 0.85rem;
          color: #6b7280;
        }
        .settings-link {
          position: absolute;
          top: 10px;
          right: 0;
          color: #9ca3af;
          transition: color 0.15s ease;
        }
        .settings-link:hover {
          color: #6b7280;
        }

        /* Date navigation */
        .date-nav {
          overflow: hidden;
        }
        .date-scroll {
          display: flex;
          gap: 8px;
          overflow-x: auto;
          padding: 4px 0;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: none;
        }
        .date-scroll::-webkit-scrollbar {
          display: none;
        }
        .date-chip {
          flex-shrink: 0;
          padding: 8px 16px;
          border-radius: 20px;
          border: 1px solid var(--border-light, #e5e7eb);
          background: white;
          font-size: 0.85rem;
          cursor: pointer;
          transition: all 0.15s ease;
          color: #374151;
          white-space: nowrap;
        }
        .date-chip:hover {
          border-color: var(--primary-teal, #0d9488);
        }
        .date-chip.active {
          background: var(--primary-teal, #0d9488);
          color: white;
          border-color: var(--primary-teal, #0d9488);
        }

        /* Gentleness banner (scrupulosity safeguard) */
        .gentleness-banner {
          background: #fefce8;
          border: 1px solid #fde68a;
          border-radius: 10px;
          padding: 12px 16px;
        }
        .gentleness-banner p {
          font-size: 0.85rem;
          color: #92400e;
          margin: 0;
          line-height: 1.5;
          text-align: center;
        }

        /* Correlation insight card */
        .correlation-card {
          background: white;
          border-radius: 14px;
          border: 1px solid var(--border-light, #e5e7eb);
          padding: 16px;
        }
        .correlation-text {
          font-size: 0.85rem;
          color: #374151;
          margin: 0 0 8px 0;
          line-height: 1.5;
        }
        .correlation-caveat {
          font-size: 0.75rem;
          color: #9ca3af;
          font-style: italic;
        }

        .struggles-section {
          display: flex;
          flex-direction: column;
          gap: 0;
        }
        .section-label {
          font-size: 0.8rem;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin: 0 0 10px 0;
        }
        .add-struggle-btn {
          padding: 10px 16px;
          border-radius: 10px;
          border: 1.5px dashed #d1d5db;
          background: transparent;
          color: #6b7280;
          font-size: 0.85rem;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .add-struggle-btn:hover {
          border-color: var(--primary-teal, #0d9488);
          color: var(--primary-teal, #0d9488);
        }

        @media (min-width: 1024px) {
          .journal-container {
            padding: 32px 24px 48px;
            max-width: 640px;
          }
          .journal-header h1 {
            font-size: 1.8rem;
          }
        }
      `}</style>
    </div>
  );
}
