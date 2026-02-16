'use client';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { onAuthStateChanged } from 'firebase/auth';
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

  return (
    <>
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '20px 16px 120px' }}>
        {/* Tab navigation */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-light, #e5e7eb)',
          marginBottom: 16,
        }}>
          {[
            { id: 'plans', label: `My Plans${activePlans.length ? ` (${activePlans.length})` : ''}` },
            { id: 'browse', label: 'Browse Plans' },
            { id: 'progress', label: 'Progress Map' },
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                flex: 1,
                padding: '10px 8px',
                background: 'none',
                border: 'none',
                borderBottom: `2px solid ${tab === t.id ? 'var(--primary-teal, #0d9488)' : 'transparent'}`,
                marginBottom: -1,
                fontSize: '0.85rem',
                fontWeight: tab === t.id ? 600 : 400,
                color: tab === t.id ? 'var(--primary-teal, #0d9488)' : '#6b7280',
                cursor: 'pointer',
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {error && (
          <div style={{
            padding: '10px 14px', background: '#fef2f2', color: '#dc2626',
            borderRadius: 8, fontSize: '0.85rem', marginBottom: 12,
          }}>
            {error}
          </div>
        )}

        {/* ===================== MY PLANS TAB ===================== */}
        {tab === 'plans' && (
          <>
            {activePlans.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {activePlans.map((ap) => {
                  const plan = plans.find(p => p.id === ap.plan_id);
                  if (!plan) return null;
                  const totalDays = ap.duration_days || plan.duration_days;
                  const completedCount = ap.completed_days?.length || 0;
                  const progressPct = totalDays > 0 ? Math.round((completedCount / totalDays) * 100) : 0;

                  return (
                    <div key={ap.plan_id} style={{
                      background: 'white',
                      border: '1px solid var(--primary-teal, #0d9488)',
                      borderRadius: 12,
                      padding: 16,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                        <div>
                          <div style={{
                            fontSize: '0.7rem', fontWeight: 600,
                            textTransform: 'uppercase', letterSpacing: '0.05em',
                            color: 'var(--primary-teal, #0d9488)', marginBottom: 4,
                          }}>
                            {ap.category || plan.category} · Day {ap.current_day} of {totalDays}
                          </div>
                          <h2 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--deep-blue, #1e293b)' }}>
                            {ap.title || plan.title}
                          </h2>
                        </div>
                        <span style={{
                          fontSize: '0.75rem', fontWeight: 700,
                          color: 'var(--primary-teal, #0d9488)',
                          background: 'rgba(13, 148, 136, 0.08)',
                          padding: '4px 10px', borderRadius: 6,
                        }}>
                          {progressPct}%
                        </span>
                      </div>

                      {/* Description */}
                      <p style={{ fontSize: '0.82rem', color: '#6b7280', lineHeight: 1.5, margin: '0 0 10px' }}>
                        {ap.description || plan.description}
                      </p>

                      {/* Progress bar */}
                      <div style={{ height: 5, background: 'var(--border-light, #e5e7eb)', borderRadius: 3, overflow: 'hidden', marginBottom: 10 }}>
                        <div style={{ height: '100%', width: `${progressPct}%`, background: 'var(--primary-teal, #0d9488)', borderRadius: 3, transition: 'width 0.3s ease' }} />
                      </div>

                      {/* Today's verse detail */}
                      {ap.today_verse && (
                        <div style={{
                          padding: 12, background: 'var(--cream, #faf6f0)',
                          borderRadius: 8, marginBottom: 10,
                          border: '1px solid var(--border-light, #e5e7eb)',
                        }}>
                          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--deep-blue, #1e293b)', marginBottom: 4 }}>
                            Today: {ap.today_verse.title}
                          </div>
                          <div
                            onClick={() => handleStudyVerse(ap.today_verse.surah, ap.today_verse.verse)}
                            style={{ fontSize: '0.78rem', color: 'var(--primary-teal, #0d9488)', cursor: 'pointer', textDecoration: 'underline', textUnderlineOffset: 2, marginBottom: 6 }}
                          >
                            {ap.today_verse.surah_name} ({ap.today_verse.surah}:{ap.today_verse.verse})
                          </div>
                          {ap.today_verse.prompt && (
                            <div style={{ fontSize: '0.78rem', color: '#6b7280', fontStyle: 'italic', lineHeight: 1.4 }}>
                              Reflect: {ap.today_verse.prompt}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Action buttons */}
                      <div style={{ display: 'flex', gap: 8 }}>
                        {ap.today_verse && (
                          <button
                            onClick={() => handleStudyVerse(ap.today_verse.surah, ap.today_verse.verse)}
                            disabled={actionLoading}
                            style={{
                              flex: 1, padding: '9px 14px', background: 'var(--primary-teal, #0d9488)',
                              color: 'white', border: 'none', borderRadius: 8, fontSize: '0.82rem',
                              fontWeight: 600, cursor: actionLoading ? 'not-allowed' : 'pointer', opacity: actionLoading ? 0.5 : 1,
                            }}
                          >
                            Study Verse
                          </button>
                        )}
                        <button
                          onClick={() => handleCompleteDay(ap.plan_id, ap.current_day)}
                          disabled={actionLoading}
                          style={{
                            flex: 1, padding: '9px 14px', background: 'var(--cream, #faf6f0)',
                            color: 'var(--deep-blue, #1e293b)', border: '1px solid var(--border-light, #e5e7eb)',
                            borderRadius: 8, fontSize: '0.82rem', fontWeight: 600,
                            cursor: actionLoading ? 'not-allowed' : 'pointer', opacity: actionLoading ? 0.5 : 1,
                          }}
                        >
                          {actionLoading ? 'Saving...' : 'Complete Day'}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: '#6b7280' }}>
                <p style={{ fontSize: '1rem', marginBottom: 8 }}>No active plans</p>
                <p style={{ fontSize: '0.85rem', marginBottom: 16 }}>Start one or more reading plans from the Browse tab.</p>
                <button
                  onClick={() => setTab('browse')}
                  style={{
                    padding: '10px 20px', background: 'var(--primary-teal, #0d9488)',
                    color: 'white', border: 'none', borderRadius: 8, fontSize: '0.85rem',
                    fontWeight: 600, cursor: 'pointer',
                  }}
                >
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
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
                <button
                  onClick={() => setCategoryFilter(null)}
                  style={{
                    padding: '6px 12px', borderRadius: 16, fontSize: '0.78rem', fontWeight: 600,
                    background: !categoryFilter ? 'var(--primary-teal, #0d9488)' : 'white',
                    color: !categoryFilter ? 'white' : '#6b7280',
                    border: `1px solid ${!categoryFilter ? 'var(--primary-teal, #0d9488)' : 'var(--border-light, #e5e7eb)'}`,
                    cursor: 'pointer',
                  }}
                >
                  All ({plans.length})
                </button>
                {categories.map(cat => {
                  const count = plans.filter(p => p.category === cat).length;
                  return (
                    <button
                      key={cat}
                      onClick={() => setCategoryFilter(cat)}
                      style={{
                        padding: '6px 12px', borderRadius: 16, fontSize: '0.78rem', fontWeight: 600,
                        background: categoryFilter === cat ? 'var(--primary-teal, #0d9488)' : 'white',
                        color: categoryFilter === cat ? 'white' : '#6b7280',
                        border: `1px solid ${categoryFilter === cat ? 'var(--primary-teal, #0d9488)' : 'var(--border-light, #e5e7eb)'}`,
                        cursor: 'pointer',
                      }}
                    >
                      {cat} ({count})
                    </button>
                  );
                })}
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {filteredPlans.map((plan) => {
                const isActive = activePlanIds.has(plan.id);
                return (
                  <div key={plan.id} style={{
                    padding: '14px 16px',
                    border: `1px solid ${isActive ? 'var(--primary-teal, #0d9488)' : 'var(--border-light, #e5e7eb)'}`,
                    borderRadius: 10, background: isActive ? 'rgba(13, 148, 136, 0.04)' : 'white',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--deep-blue, #1e293b)', marginBottom: 2 }}>
                          {plan.title}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--gold, #b8860b)', fontWeight: 500, marginBottom: 6 }}>
                          {plan.duration_days} days · {plan.category}
                        </div>
                        <div style={{ fontSize: '0.82rem', color: '#6b7280', lineHeight: 1.5 }}>
                          {plan.description}
                        </div>
                      </div>
                      <button
                        onClick={() => handleStart(plan.id)}
                        disabled={actionLoading || isActive}
                        style={{
                          flexShrink: 0, padding: '8px 16px',
                          background: isActive ? 'var(--border-light, #e5e7eb)' : 'var(--primary-teal, #0d9488)',
                          color: isActive ? '#6b7280' : 'white', border: 'none', borderRadius: 8,
                          fontSize: '0.78rem', fontWeight: 600,
                          cursor: (actionLoading || isActive) ? 'not-allowed' : 'pointer', opacity: actionLoading ? 0.5 : 1,
                        }}
                      >
                        {isActive ? 'Active' : 'Start'}
                      </button>
                    </div>
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
              <div style={{ textAlign: 'center', padding: '40px 20px', color: '#6b7280', fontSize: '0.9rem' }}>
                Loading progress map...
              </div>
            )}
          </div>
        )}
      </div>

      <style jsx>{`
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
      `}</style>

      <BottomNav user={user} />
    </>
  );
}
