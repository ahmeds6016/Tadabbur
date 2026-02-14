'use client';
import { useState, useEffect, useCallback } from 'react';
import { BACKEND_URL } from '../lib/config';

export default function ReadingPlanCard({ user, onStudyVerse }) {
  const [plans, setPlans] = useState([]);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [view, setView] = useState('active'); // 'active' | 'browse'

  const fetchProgress = useCallback(async () => {
    if (!user) return null;
    try {
      const token = await user.getIdToken();
      // Fetch active plan ID from localStorage or try known plans
      const activePlanId = localStorage.getItem('active_reading_plan');
      if (!activePlanId) return null;
      const res = await fetch(`${BACKEND_URL}/reading-plans/${activePlanId}/progress`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) {
        if (res.status === 404) {
          localStorage.removeItem('active_reading_plan');
          return null;
        }
        throw new Error('Failed to fetch progress');
      }
      return await res.json();
    } catch {
      return null;
    }
  }, [user]);

  const fetchPlans = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/reading-plans`);
      if (!res.ok) throw new Error('Failed to fetch plans');
      const data = await res.json();
      return data.plans || [];
    } catch {
      throw new Error('Could not load reading plans');
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [planList, prog] = await Promise.all([fetchPlans(), fetchProgress()]);
        if (cancelled) return;
        setPlans(planList);
        setProgress(prog);
        if (!prog) setView('browse');
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [fetchPlans, fetchProgress]);

  const handleStart = async (planId) => {
    if (!user) return;
    setActionLoading(true);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/reading-plans/${planId}/progress`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ action: 'start' })
      });
      if (!res.ok) throw new Error('Failed to start plan');
      const data = await res.json();
      localStorage.setItem('active_reading_plan', planId);
      setProgress(data);
      setView('active');
    } catch {
      setError('Could not start plan. Please try again.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCompleteDay = async () => {
    if (!user || !progress) return;
    setActionLoading(true);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/reading-plans/${progress.plan_id}/progress`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ action: 'complete_day', day: progress.current_day })
      });
      if (!res.ok) throw new Error('Failed to complete day');
      const data = await res.json();
      setProgress(data);
    } catch {
      setError('Could not complete day. Please try again.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleContinue = () => {
    if (!progress?.today_verse) return;
    const { surah, verse } = progress.today_verse;
    onStudyVerse(surah, verse);
  };

  const activePlan = progress
    ? plans.find((p) => p.id === progress.plan_id)
    : null;
  const totalDays = activePlan?.duration_days || 0;
  const completedCount = progress?.completed_days?.length || 0;
  const progressPct = totalDays > 0 ? (completedCount / totalDays) * 100 : 0;

  if (loading) {
    return (
      <div className="rp-card">
        <div className="rp-loading">Loading reading plans...</div>
        <style jsx>{styles}</style>
      </div>
    );
  }

  if (error && !plans.length) {
    return (
      <div className="rp-card">
        <div className="rp-error">{error}</div>
        <style jsx>{styles}</style>
      </div>
    );
  }

  return (
    <div className="rp-card">
      {/* Tab toggle */}
      {progress && (
        <div className="rp-tabs">
          <button
            className={`rp-tab ${view === 'active' ? 'active' : ''}`}
            onClick={() => setView('active')}
          >
            My Plan
          </button>
          <button
            className={`rp-tab ${view === 'browse' ? 'active' : ''}`}
            onClick={() => setView('browse')}
          >
            Browse Plans
          </button>
        </div>
      )}

      {error && <div className="rp-error">{error}</div>}

      {/* Active plan view */}
      {view === 'active' && progress && progress.today_verse && (
        <div className="rp-active">
          <h3 className="rp-title">
            Day {progress.current_day} of {totalDays} — {progress.today_verse.title}
          </h3>
          <p className="rp-verse-ref">
            Surah {progress.today_verse.surah}, Verse {progress.today_verse.verse}
          </p>
          <div className="rp-progress-bar">
            <div className="rp-progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <p className="rp-progress-label">
            {completedCount} of {totalDays} days completed
          </p>
          <div className="rp-actions">
            <button
              className="rp-btn rp-btn-primary"
              onClick={handleContinue}
              disabled={actionLoading}
            >
              Continue
            </button>
            <button
              className="rp-btn rp-btn-secondary"
              onClick={handleCompleteDay}
              disabled={actionLoading}
            >
              {actionLoading ? 'Saving...' : 'Complete Day'}
            </button>
          </div>
        </div>
      )}

      {/* Browse plans view */}
      {view === 'browse' && (
        <div className="rp-browse">
          <h3 className="rp-browse-heading">Reading Plans</h3>
          <ul className="rp-plan-list">
            {plans.map((plan) => (
              <li key={plan.id} className="rp-plan-item">
                <div className="rp-plan-info">
                  <span className="rp-plan-title">{plan.title}</span>
                  <span className="rp-plan-meta">
                    {plan.duration_days} days &middot; {plan.category}
                  </span>
                  <span className="rp-plan-desc">{plan.description}</span>
                </div>
                <button
                  className="rp-btn rp-btn-start"
                  onClick={() => handleStart(plan.id)}
                  disabled={actionLoading || (progress?.plan_id === plan.id)}
                >
                  {progress?.plan_id === plan.id ? 'Active' : 'Start'}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <style jsx>{styles}</style>
    </div>
  );
}

const styles = `
  .rp-card {
    background: white;
    border: 1px solid var(--border-light, #e5e7eb);
    border-radius: 12px;
    overflow: hidden;
  }
  .rp-loading, .rp-error {
    padding: 20px;
    text-align: center;
    font-size: 0.85rem;
    color: #6b7280;
  }
  .rp-error {
    color: #dc2626;
    background: #fef2f2;
  }

  /* Tabs */
  .rp-tabs {
    display: flex;
    border-bottom: 1px solid var(--border-light, #e5e7eb);
  }
  .rp-tab {
    flex: 1;
    padding: 10px;
    background: none;
    border: none;
    font-size: 0.8rem;
    font-weight: 500;
    color: #6b7280;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s ease;
  }
  .rp-tab.active {
    color: var(--primary-teal, #0d9488);
    border-bottom-color: var(--primary-teal, #0d9488);
  }
  .rp-tab:hover {
    background: var(--cream, #faf6f0);
  }

  /* Active plan */
  .rp-active {
    padding: 16px;
  }
  .rp-title {
    margin: 0 0 6px;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--deep-blue, #1e293b);
    line-height: 1.3;
  }
  .rp-verse-ref {
    margin: 0 0 12px;
    font-size: 0.8rem;
    color: var(--gold, #b8860b);
    font-weight: 500;
  }
  .rp-progress-bar {
    height: 6px;
    background: var(--border-light, #e5e7eb);
    border-radius: 3px;
    overflow: hidden;
  }
  .rp-progress-fill {
    height: 100%;
    background: var(--primary-teal, #0d9488);
    border-radius: 3px;
    transition: width 0.3s ease;
  }
  .rp-progress-label {
    margin: 6px 0 14px;
    font-size: 0.75rem;
    color: #6b7280;
  }
  .rp-actions {
    display: flex;
    gap: 8px;
  }

  /* Buttons */
  .rp-btn {
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    border: none;
    transition: opacity 0.2s ease, transform 0.1s ease;
  }
  .rp-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .rp-btn:active:not(:disabled) {
    transform: scale(0.97);
  }
  .rp-btn-primary {
    flex: 1;
    background: var(--primary-teal, #0d9488);
    color: white;
  }
  .rp-btn-primary:hover:not(:disabled) {
    opacity: 0.9;
  }
  .rp-btn-secondary {
    flex: 1;
    background: var(--cream, #faf6f0);
    color: var(--deep-blue, #1e293b);
    border: 1px solid var(--border-light, #e5e7eb);
  }
  .rp-btn-secondary:hover:not(:disabled) {
    background: #f0ebe3;
  }

  /* Browse plans */
  .rp-browse {
    padding: 16px;
  }
  .rp-browse-heading {
    margin: 0 0 12px;
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--deep-blue, #1e293b);
  }
  .rp-plan-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .rp-plan-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 12px;
    border: 1px solid var(--border-light, #e5e7eb);
    border-radius: 8px;
    background: var(--cream, #faf6f0);
  }
  .rp-plan-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .rp-plan-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--deep-blue, #1e293b);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .rp-plan-meta {
    font-size: 0.7rem;
    color: var(--gold, #b8860b);
    font-weight: 500;
  }
  .rp-plan-desc {
    font-size: 0.75rem;
    color: #6b7280;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .rp-btn-start {
    flex-shrink: 0;
    background: var(--primary-teal, #0d9488);
    color: white;
    padding: 6px 14px;
    font-size: 0.75rem;
  }
  .rp-btn-start:hover:not(:disabled) {
    opacity: 0.9;
  }
  .rp-btn-start:disabled {
    background: var(--border-light, #e5e7eb);
    color: #6b7280;
  }
`;
