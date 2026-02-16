'use client';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { onAuthStateChanged } from 'firebase/auth';
import { ChevronRight, ChevronDown } from 'lucide-react';
import { auth } from '../lib/firebase';
import { BACKEND_URL } from '../lib/config';
import BadgeDisplay from '../components/BadgeDisplay';
import BottomNav from '../components/BottomNav';

export default function PlansPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [tab, setTab] = useState('plans'); // 'plans' | 'browse' | 'progress'
  const [plans, setPlans] = useState([]);
  const [activePlans, setActivePlans] = useState([]);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState(null);
  const [expandedPlanId, setExpandedPlanId] = useState(null);

  // Progress map state
  const [quranProgress, setQuranProgress] = useState(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setIsLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const fetchActivePlans = useCallback(async () => {
    if (!user) return [];
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/reading-plans/active`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) return [];
      const data = await res.json();
      return (data.plans || []).filter(p => p.active);
    } catch {
      return [];
    }
  }, [user]);

  const fetchPlans = useCallback(async () => {
    const res = await fetch(`${BACKEND_URL}/reading-plans`);
    if (!res.ok) throw new Error('Failed to fetch plans');
    const data = await res.json();
    return data.plans || [];
  }, []);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    async function load() {
      setError(null);
      try {
        const [planList, active] = await Promise.all([fetchPlans(), fetchActivePlans()]);
        if (cancelled) return;
        setPlans(planList);
        setActivePlans(active);
        if (active.length === 0) setTab('browse');
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [user, fetchPlans, fetchActivePlans]);

  // Quran progress (lazy)
  const fetchQuranProgress = useCallback(async () => {
    if (!user || quranProgress) return;
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/progress`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to load progress');
      setQuranProgress(await res.json());
    } catch { /* non-critical */ }
  }, [user, quranProgress]);

  useEffect(() => {
    if (tab === 'progress') fetchQuranProgress();
  }, [tab, fetchQuranProgress]);

  // --- Plan actions ---
  const handleStart = async (planId) => {
    if (!user) return;
    setActionLoading(true);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/reading-plans/${planId}/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ action: 'start' })
      });
      if (!res.ok) throw new Error('Failed to start plan');
      const active = await fetchActivePlans();
      setActivePlans(active);
      setTab('plans');
    } catch {
      setError('Could not start plan. Please try again.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCompleteDay = async (planId, day) => {
    if (!user) return;
    setActionLoading(true);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/reading-plans/${planId}/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ action: 'complete_day', day })
      });
      if (!res.ok) throw new Error('Failed to complete day');
      const active = await fetchActivePlans();
      setActivePlans(active);
    } catch {
      setError('Could not complete day. Please try again.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStudyVerse = (surah, verse) => {
    router.push(`/?query=${surah}:${verse}`);
  };

  // Progress map helpers
  const getTileColor = (explored, total) => {
    if (total === 0) return '#f1f5f9';
    const pct = (explored / total) * 100;
    if (pct === 0) return '#f1f5f9';
    if (pct <= 25) return '#ccfbf1';
    if (pct <= 75) return '#5eead4';
    if (pct < 100) return '#f0c040';
    return '#fbbf24';
  };

  // Categories for browse filter
  const categories = [...new Set(plans.map(p => p.category))];
  const filteredPlans = categoryFilter
    ? plans.filter(p => p.category === categoryFilter)
    : plans;
  const activePlanIds = new Set(activePlans.map(p => p.plan_id));

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <p style={{ color: '#6b7280' }}>Loading...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <p style={{ color: '#6b7280' }}>Please sign in to view your plans.</p>
      </div>
    );
  }

  const tabs = [
    { id: 'plans', label: `My Plans${activePlans.length ? ` (${activePlans.length})` : ''}` },
    { id: 'browse', label: 'Browse' },
    { id: 'progress', label: 'Progress Map' },
  ];

  return (
    <>
      <div className="plans-page">
        {/* Page header */}
        <div className="plans-header">
          <h1 className="plans-title">Reading Plans</h1>
        </div>

        {/* Segmented control */}
        <div className="segmented-control">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => { setTab(t.id); setExpandedPlanId(null); }}
              className={`segment ${tab === t.id ? 'active' : ''}`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {error && (
          <div className="error-banner">{error}</div>
        )}

        {/* ===================== MY PLANS TAB ===================== */}
        {tab === 'plans' && (
          <>
            {activePlans.length > 0 ? (
              <div className="plan-list">
                {activePlans.map((ap) => {
                  const plan = plans.find(p => p.id === ap.plan_id);
                  if (!plan) return null;
                  const totalDays = ap.duration_days || plan.duration_days;
                  const completedCount = ap.completed_days?.length || 0;
                  const progressPct = totalDays > 0 ? Math.round((completedCount / totalDays) * 100) : 0;
                  const isExpanded = expandedPlanId === ap.plan_id;

                  return (
                    <div key={ap.plan_id} className={`plan-row ${isExpanded ? 'expanded' : ''}`}>
                      {/* Collapsed row — always visible, tappable */}
                      <div
                        className="plan-row-header"
                        onClick={() => setExpandedPlanId(isExpanded ? null : ap.plan_id)}
                      >
                        <div className="plan-row-left">
                          <div className="plan-row-title">{ap.title || plan.title}</div>
                          <div className="plan-row-meta">
                            Day {ap.current_day}/{totalDays}
                            {ap.category || plan.category ? ` · ${ap.category || plan.category}` : ''}
                          </div>
                        </div>
                        <div className="plan-row-right">
                          <div className="plan-row-progress-mini">
                            <div className="mini-bar">
                              <div className="mini-bar-fill" style={{ width: `${progressPct}%` }} />
                            </div>
                            <span className="mini-pct">{progressPct}%</span>
                          </div>
                          {isExpanded ? <ChevronDown size={18} color="#9ca3af" /> : <ChevronRight size={18} color="#9ca3af" />}
                        </div>
                      </div>

                      {/* Expanded detail */}
                      {isExpanded && (
                        <div className="plan-row-detail">
                          {(ap.description || plan.description) && (
                            <p className="plan-desc">{ap.description || plan.description}</p>
                          )}

                          {/* Today's verse */}
                          {ap.today_verse && (
                            <div className="today-verse">
                              <div className="today-label">Today: {ap.today_verse.title}</div>
                              <div
                                className="today-ref"
                                onClick={() => handleStudyVerse(ap.today_verse.surah, ap.today_verse.verse)}
                              >
                                {ap.today_verse.surah_name} ({ap.today_verse.surah}:{ap.today_verse.verse})
                              </div>
                              {ap.today_verse.prompt && (
                                <div className="today-prompt">Reflect: {ap.today_verse.prompt}</div>
                              )}
                            </div>
                          )}

                          <div className="plan-actions">
                            {ap.today_verse && (
                              <button
                                className="btn-primary"
                                onClick={() => handleStudyVerse(ap.today_verse.surah, ap.today_verse.verse)}
                                disabled={actionLoading}
                              >
                                Study Verse
                              </button>
                            )}
                            <button
                              className="btn-secondary"
                              onClick={() => handleCompleteDay(ap.plan_id, ap.current_day)}
                              disabled={actionLoading}
                            >
                              {actionLoading ? 'Saving...' : 'Complete Day'}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state">
                <p className="empty-title">No active plans</p>
                <p className="empty-desc">Start a reading plan from Browse.</p>
                <button className="btn-primary" onClick={() => setTab('browse')}>
                  Browse Plans
                </button>
              </div>
            )}
          </>
        )}

        {/* ===================== BROWSE PLANS TAB ===================== */}
        {tab === 'browse' && (
          <div>
            {/* Category filters */}
            {categories.length > 1 && (
              <div className="cat-filters">
                <button
                  onClick={() => setCategoryFilter(null)}
                  className={`cat-chip ${!categoryFilter ? 'active' : ''}`}
                >
                  All ({plans.length})
                </button>
                {categories.map(cat => {
                  const count = plans.filter(p => p.category === cat).length;
                  return (
                    <button
                      key={cat}
                      onClick={() => setCategoryFilter(cat)}
                      className={`cat-chip ${categoryFilter === cat ? 'active' : ''}`}
                    >
                      {cat} ({count})
                    </button>
                  );
                })}
              </div>
            )}

            <div className="plan-list">
              {filteredPlans.map((plan) => {
                const isActive = activePlanIds.has(plan.id);
                const isExpanded = expandedPlanId === plan.id;

                return (
                  <div key={plan.id} className={`plan-row ${isActive ? 'is-active' : ''} ${isExpanded ? 'expanded' : ''}`}>
                    <div
                      className="plan-row-header"
                      onClick={() => setExpandedPlanId(isExpanded ? null : plan.id)}
                    >
                      <div className="plan-row-left">
                        <div className="plan-row-title">{plan.title}</div>
                        <div className="plan-row-meta">
                          {plan.duration_days} days · {plan.category}
                        </div>
                      </div>
                      <div className="plan-row-right">
                        {isActive ? (
                          <span className="active-pill">Active</span>
                        ) : (
                          <button
                            className="start-btn"
                            onClick={(e) => { e.stopPropagation(); handleStart(plan.id); }}
                            disabled={actionLoading}
                          >
                            Start
                          </button>
                        )}
                        {isExpanded ? <ChevronDown size={18} color="#9ca3af" /> : <ChevronRight size={18} color="#9ca3af" />}
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="plan-row-detail">
                        <p className="plan-desc">{plan.description}</p>
                        {!isActive && (
                          <button
                            className="btn-primary"
                            onClick={() => handleStart(plan.id)}
                            disabled={actionLoading}
                            style={{ alignSelf: 'flex-start' }}
                          >
                            {actionLoading ? 'Starting...' : 'Start Plan'}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ===================== PROGRESS MAP TAB ===================== */}
        {tab === 'progress' && (
          <div>
            {quranProgress && (
              <div style={{ textAlign: 'center', marginBottom: 16 }}>
                <div style={{ fontSize: '1rem', marginBottom: 8 }}>
                  <span style={{ fontWeight: 800, color: 'var(--primary-teal, #0d9488)', fontSize: '1.2rem' }}>
                    {(quranProgress.total_explored || 0).toLocaleString()}
                  </span>
                  <span style={{ color: '#666', fontWeight: 600 }}> / 6,236</span>
                  <span style={{ color: 'var(--gold, #d4a017)', fontWeight: 700 }}> ({quranProgress.percentage || 0}%)</span>
                </div>
                <div style={{ height: 8, background: 'var(--border-light, #e5e7eb)', borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%',
                    width: `${Math.min(quranProgress.percentage || 0, 100)}%`,
                    background: 'linear-gradient(90deg, var(--primary-teal, #0d9488), var(--gold, #d4a017))',
                    borderRadius: 4, transition: 'width 0.8s ease',
                  }} />
                </div>
              </div>
            )}

            {quranProgress && (
              <div style={{
                marginBottom: 16, padding: 14,
                background: 'var(--cream, #faf6f0)', borderRadius: 10,
                border: '1px solid var(--border-light, #e5e7eb)',
              }}>
                <BadgeDisplay user={user} compact={false} />
              </div>
            )}

            {quranProgress?.surahs ? (
              <>
                <div className="surah-grid-plans">
                  {quranProgress.surahs.map((surah) => {
                    const pct = surah.total_verses > 0
                      ? Math.round((surah.explored_count / surah.total_verses) * 100)
                      : 0;
                    const bg = getTileColor(surah.explored_count, surah.total_verses);
                    const complete = surah.total_verses > 0 && surah.explored_count === surah.total_verses;

                    return (
                      <button
                        key={surah.number}
                        onClick={() => handleStudyVerse(surah.number, 1)}
                        title={`${surah.name} - ${surah.explored_count}/${surah.total_verses} explored`}
                        className="surah-tile-plans"
                        style={{
                          background: bg,
                          borderColor: complete ? 'var(--gold, #d4a017)' : 'var(--border-light, #e5e7eb)',
                        }}
                      >
                        <span className="surah-tile-plans__number">{surah.number}</span>
                        <span className="surah-tile-plans__name">{surah.name}</span>
                        <div className="surah-tile-plans__bar">
                          <div style={{ height: '100%', width: `${pct}%`, background: 'var(--primary-teal, #0d9488)', borderRadius: 2 }} />
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div style={{ display: 'flex', justifyContent: 'center', gap: 12, flexWrap: 'wrap', fontSize: '0.72rem', color: '#6b7280', marginTop: 12 }}>
                  {[['#f1f5f9', '0%'], ['#ccfbf1', '1-25%'], ['#5eead4', '26-75%'], ['#f0c040', '76-99%'], ['#fbbf24', '100%']].map(([color, label]) => (
                    <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ width: 12, height: 12, borderRadius: 3, background: color, border: '1px solid #e5e7eb' }} />
                      <span>{label}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="empty-state">
                <p className="empty-desc">Loading progress map...</p>
              </div>
            )}
          </div>
        )}
      </div>

      <style jsx>{`
        /* ===== Page layout ===== */
        .plans-page {
          max-width: 600px;
          margin: 0 auto;
          padding: calc(16px + env(safe-area-inset-top, 0px)) 16px calc(60px + env(safe-area-inset-bottom, 0px));
        }

        .plans-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 4px 0 12px;
        }

        .plans-title {
          font-size: 1.5rem;
          font-weight: 700;
          color: #1a1a1a;
          margin: 0;
        }

        /* ===== Segmented control ===== */
        .segmented-control {
          display: flex;
          background: #f3f4f6;
          border-radius: 10px;
          padding: 3px;
          margin-bottom: 16px;
          gap: 2px;
        }

        .segment {
          flex: 1;
          padding: 8px 4px;
          border: none;
          border-radius: 8px;
          background: transparent;
          font-size: 0.78rem;
          font-weight: 500;
          color: #6b7280;
          cursor: pointer;
          transition: all 0.15s ease;
          text-align: center;
          white-space: nowrap;
        }

        .segment.active {
          background: white;
          color: #1a1a1a;
          font-weight: 600;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        }

        /* ===== Error banner ===== */
        .error-banner {
          padding: 10px 14px;
          background: #fef2f2;
          color: #dc2626;
          border-radius: 8px;
          font-size: 0.85rem;
          margin-bottom: 12px;
        }

        /* ===== Plan list ===== */
        .plan-list {
          display: flex;
          flex-direction: column;
          gap: 1px;
          background: #e5e7eb;
          border-radius: 12px;
          overflow: hidden;
        }

        /* ===== Plan row (accordion) ===== */
        .plan-row {
          background: white;
        }

        .plan-row.is-active {
          background: rgba(13, 148, 136, 0.03);
        }

        .plan-row-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 12px 14px;
          cursor: pointer;
          -webkit-tap-highlight-color: transparent;
          touch-action: manipulation;
        }

        .plan-row-header:active {
          background: #f9fafb;
        }

        .plan-row-left {
          flex: 1;
          min-width: 0;
        }

        .plan-row-title {
          font-size: 0.9rem;
          font-weight: 600;
          color: #1a1a1a;
          line-height: 1.3;
        }

        .plan-row-meta {
          font-size: 0.72rem;
          color: #9ca3af;
          margin-top: 2px;
        }

        .plan-row-right {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-shrink: 0;
        }

        /* Mini progress bar (My Plans collapsed view) */
        .plan-row-progress-mini {
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .mini-bar {
          width: 40px;
          height: 4px;
          background: #e5e7eb;
          border-radius: 2px;
          overflow: hidden;
        }

        .mini-bar-fill {
          height: 100%;
          background: var(--primary-teal, #0d9488);
          border-radius: 2px;
          transition: width 0.3s ease;
        }

        .mini-pct {
          font-size: 0.68rem;
          font-weight: 600;
          color: var(--primary-teal, #0d9488);
          min-width: 28px;
          text-align: right;
        }

        /* Active pill (Browse tab) */
        .active-pill {
          font-size: 0.68rem;
          font-weight: 600;
          color: var(--primary-teal, #0d9488);
          background: rgba(13, 148, 136, 0.08);
          padding: 3px 8px;
          border-radius: 6px;
        }

        .start-btn {
          font-size: 0.75rem;
          font-weight: 600;
          color: white;
          background: var(--primary-teal, #0d9488);
          border: none;
          border-radius: 6px;
          padding: 5px 12px;
          cursor: pointer;
        }

        .start-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        /* Expanded detail */
        .plan-row-detail {
          display: flex;
          flex-direction: column;
          gap: 10px;
          padding: 0 14px 14px;
          border-top: 1px solid #f3f4f6;
        }

        .plan-desc {
          font-size: 0.82rem;
          color: #6b7280;
          line-height: 1.5;
          margin: 0;
          padding-top: 10px;
        }

        .today-verse {
          padding: 10px 12px;
          background: #faf8f5;
          border-radius: 8px;
          border: 1px solid #f0ebe3;
        }

        .today-label {
          font-size: 0.8rem;
          font-weight: 600;
          color: #1a1a1a;
          margin-bottom: 4px;
        }

        .today-ref {
          font-size: 0.78rem;
          color: var(--primary-teal, #0d9488);
          cursor: pointer;
          text-decoration: underline;
          text-underline-offset: 2px;
          margin-bottom: 4px;
        }

        .today-prompt {
          font-size: 0.75rem;
          color: #6b7280;
          font-style: italic;
          line-height: 1.4;
        }

        .plan-actions {
          display: flex;
          gap: 8px;
        }

        .btn-primary {
          flex: 1;
          padding: 8px 14px;
          background: var(--primary-teal, #0d9488);
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 0.82rem;
          font-weight: 600;
          cursor: pointer;
        }

        .btn-primary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .btn-secondary {
          flex: 1;
          padding: 8px 14px;
          background: #f9fafb;
          color: #374151;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          font-size: 0.82rem;
          font-weight: 600;
          cursor: pointer;
        }

        .btn-secondary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        /* ===== Category filter chips ===== */
        .cat-filters {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
          margin-bottom: 12px;
        }

        .cat-chip {
          padding: 5px 12px;
          border-radius: 16px;
          font-size: 0.75rem;
          font-weight: 600;
          border: 1px solid #e5e7eb;
          background: white;
          color: #6b7280;
          cursor: pointer;
          transition: all 0.15s;
        }

        .cat-chip.active {
          background: var(--primary-teal, #0d9488);
          color: white;
          border-color: var(--primary-teal, #0d9488);
        }

        /* ===== Empty state ===== */
        .empty-state {
          text-align: center;
          padding: 40px 20px;
        }

        .empty-title {
          font-size: 1rem;
          font-weight: 600;
          color: #374151;
          margin: 0 0 4px;
        }

        .empty-desc {
          font-size: 0.85rem;
          color: #9ca3af;
          margin: 0 0 16px;
        }

        /* ===== Surah grid (progress map) ===== */
        .surah-grid-plans {
          display: grid;
          grid-template-columns: repeat(6, 1fr);
          gap: 6px;
          margin-bottom: 8px;
        }
        @media (max-width: 640px) {
          .surah-grid-plans { grid-template-columns: repeat(4, 1fr); }
        }
        @media (max-width: 380px) {
          .surah-grid-plans { grid-template-columns: repeat(3, 1fr); }
        }
        .surah-tile-plans {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 2px;
          padding: 8px 4px 6px;
          border-radius: 8px;
          border: 1px solid var(--border-light, #e5e7eb);
          cursor: pointer;
          text-align: center;
          min-height: 64px;
        }
        .surah-tile-plans:active {
          transform: scale(0.97);
        }
        .surah-tile-plans__number {
          font-size: 0.6rem;
          font-weight: 600;
          color: #888;
          line-height: 1;
        }
        .surah-tile-plans__name {
          font-size: 0.68rem;
          font-weight: 700;
          color: var(--deep-blue, #1e293b);
          line-height: 1.2;
          text-align: center;
          word-break: break-word;
          max-width: 100%;
        }
        .surah-tile-plans__bar {
          width: 80%;
          height: 3px;
          background: rgba(0, 0, 0, 0.08);
          border-radius: 2px;
          overflow: hidden;
          margin-top: 2px;
        }

        @media (min-width: 1024px) {
          .plans-page {
            padding: 24px 24px 40px;
            max-width: 640px;
          }
        }
      `}</style>

      <BottomNav user={user} />
    </>
  );
}
