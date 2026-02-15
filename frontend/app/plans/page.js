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
  const [tab, setTab] = useState('plan'); // 'plan' | 'browse' | 'progress'
  const [plans, setPlans] = useState([]);
  const [planProgress, setPlanProgress] = useState(null);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Progress map state
  const [quranProgress, setQuranProgress] = useState(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setIsLoading(false);
    });
    return () => unsubscribe();
  }, []);

  // --- Reading plan data ---
  const fetchPlanProgress = useCallback(async () => {
    if (!user) return null;
    try {
      const token = await user.getIdToken();
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
        const [planList, prog] = await Promise.all([fetchPlans(), fetchPlanProgress()]);
        if (cancelled) return;
        setPlans(planList);
        setPlanProgress(prog);
        // Default to browse tab if no active plan
        if (!prog?.active) setTab('browse');
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [user, fetchPlans, fetchPlanProgress]);

  // --- Quran progress data (lazy-loaded) ---
  const fetchQuranProgress = useCallback(async () => {
    if (!user || quranProgress) return;
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/progress`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to load progress');
      const data = await res.json();
      setQuranProgress(data);
    } catch {
      // non-critical
    }
  }, [user, quranProgress]);

  // Load progress map data when tab is selected
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
      localStorage.setItem('active_reading_plan', planId);
      const prog = await fetchPlanProgress();
      setPlanProgress(prog);
      setTab('plan');
    } catch {
      setError('Could not start plan. Please try again.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCompleteDay = async () => {
    if (!user || !planProgress) return;
    setActionLoading(true);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/reading-plans/${planProgress.plan_id}/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ action: 'complete_day', day: planProgress.current_day })
      });
      if (!res.ok) throw new Error('Failed to complete day');
      const data = await res.json();
      if (data.is_complete) {
        localStorage.removeItem('active_reading_plan');
        setPlanProgress(null);
        setTab('browse');
      } else {
        const prog = await fetchPlanProgress();
        setPlanProgress(prog);
      }
    } catch {
      setError('Could not complete day. Please try again.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStudyVerse = (surah, verse) => {
    router.push(`/?query=${surah}:${verse}`);
  };

  // --- Derived state ---
  const activePlan = planProgress?.active
    ? plans.find((p) => p.id === planProgress.plan_id)
    : null;
  const totalDays = activePlan?.duration_days || 0;
  const completedCount = planProgress?.completed_days?.length || 0;
  const progressPct = totalDays > 0 ? Math.round((completedCount / totalDays) * 100) : 0;

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

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <p style={{ color: 'var(--text-muted, #6b7280)' }}>Loading...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <p style={{ color: 'var(--text-muted, #6b7280)' }}>Please sign in to view your plans.</p>
      </div>
    );
  }

  return (
    <>
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '24px 16px 120px' }}>
        {/* Tab navigation */}
        <div style={{
          display: 'flex',
          borderBottom: '2px solid var(--border-light, #e5e7eb)',
          marginBottom: 20,
        }}>
          {[
            { id: 'plan', label: 'My Plan' },
            { id: 'browse', label: 'Browse Plans' },
            { id: 'progress', label: 'Progress Map' },
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                flex: 1,
                padding: '12px 8px',
                background: 'none',
                border: 'none',
                borderBottom: `2px solid ${tab === t.id ? 'var(--primary-teal, #0d9488)' : 'transparent'}`,
                marginBottom: -2,
                fontSize: '0.85rem',
                fontWeight: tab === t.id ? 600 : 400,
                color: tab === t.id ? 'var(--primary-teal, #0d9488)' : '#6b7280',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {error && (
          <div style={{
            padding: '12px 16px',
            background: '#fef2f2',
            color: '#dc2626',
            borderRadius: 8,
            fontSize: '0.85rem',
            marginBottom: 16,
          }}>
            {error}
          </div>
        )}

        {/* ===================== MY PLAN TAB ===================== */}
        {tab === 'plan' && (
          <>
            {activePlan && planProgress?.today_verse ? (
              <div style={{
                background: 'white',
                border: '2px solid var(--primary-teal, #0d9488)',
                borderRadius: 12,
                padding: 20,
              }}>
                <div style={{
                  fontSize: '0.72rem', fontWeight: 600,
                  textTransform: 'uppercase', letterSpacing: '0.05em',
                  color: 'var(--primary-teal, #0d9488)', marginBottom: 8,
                }}>
                  Active Plan
                </div>
                <h2 style={{ margin: '0 0 4px', fontSize: '1.1rem', fontWeight: 700, color: 'var(--deep-blue, #1e293b)' }}>
                  {activePlan.title}
                </h2>
                <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--deep-blue, #1e293b)', marginBottom: 4 }}>
                  Day {planProgress.current_day} of {totalDays} — {planProgress.today_verse.title}
                </div>
                <div
                  onClick={() => handleStudyVerse(planProgress.today_verse.surah, planProgress.today_verse.verse)}
                  style={{ fontSize: '0.8rem', color: 'var(--gold, #b8860b)', fontWeight: 500, marginBottom: 12, cursor: 'pointer', textDecoration: 'underline', textUnderlineOffset: 2 }}
                >
                  {planProgress.today_verse.surah_name} ({planProgress.today_verse.surah}:{planProgress.today_verse.verse})
                </div>

                <div style={{ height: 6, background: 'var(--border-light, #e5e7eb)', borderRadius: 3, overflow: 'hidden', marginBottom: 6 }}>
                  <div style={{ height: '100%', width: `${progressPct}%`, background: 'var(--primary-teal, #0d9488)', borderRadius: 3, transition: 'width 0.3s ease' }} />
                </div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: 14 }}>
                  {completedCount} of {totalDays} days completed
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    onClick={() => handleStudyVerse(planProgress.today_verse.surah, planProgress.today_verse.verse)}
                    disabled={actionLoading}
                    style={{
                      flex: 1, padding: '10px 16px', background: 'var(--primary-teal, #0d9488)',
                      color: 'white', border: 'none', borderRadius: 8, fontSize: '0.85rem',
                      fontWeight: 600, cursor: actionLoading ? 'not-allowed' : 'pointer', opacity: actionLoading ? 0.5 : 1,
                    }}
                  >
                    Study Today&apos;s Verse
                  </button>
                  <button
                    onClick={handleCompleteDay}
                    disabled={actionLoading}
                    style={{
                      flex: 1, padding: '10px 16px', background: 'var(--cream, #faf6f0)',
                      color: 'var(--deep-blue, #1e293b)', border: '1px solid var(--border-light, #e5e7eb)',
                      borderRadius: 8, fontSize: '0.85rem', fontWeight: 600,
                      cursor: actionLoading ? 'not-allowed' : 'pointer', opacity: actionLoading ? 0.5 : 1,
                    }}
                  >
                    {actionLoading ? 'Saving...' : 'Complete Day'}
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: '#6b7280' }}>
                <p style={{ fontSize: '1rem', marginBottom: 8 }}>No active plan</p>
                <p style={{ fontSize: '0.85rem', marginBottom: 16 }}>Start a reading plan from the Browse Plans tab.</p>
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {plans.map((plan) => {
              const isActive = planProgress?.plan_id === plan.id;
              return (
                <div key={plan.id} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
                  padding: '14px 16px',
                  border: `1px solid ${isActive ? 'var(--primary-teal, #0d9488)' : 'var(--border-light, #e5e7eb)'}`,
                  borderRadius: 10, background: isActive ? 'rgba(13, 148, 136, 0.04)' : 'white',
                }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--deep-blue, #1e293b)', marginBottom: 2 }}>
                      {plan.title}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--gold, #b8860b)', fontWeight: 500, marginBottom: 2 }}>
                      {plan.duration_days} days · {plan.category}
                    </div>
                    <div style={{
                      fontSize: '0.78rem', color: '#6b7280',
                      display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                    }}>
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
              );
            })}
          </div>
        )}

        {/* ===================== PROGRESS MAP TAB ===================== */}
        {tab === 'progress' && (
          <div>
            {/* Summary */}
            {quranProgress && (
              <div style={{ textAlign: 'center', marginBottom: 20 }}>
                <div style={{ fontSize: '1.05rem', marginBottom: 8 }}>
                  <span style={{ fontWeight: 800, color: 'var(--primary-teal, #0d9488)', fontSize: '1.3rem' }}>
                    {(quranProgress.total_explored || 0).toLocaleString()}
                  </span>
                  <span style={{ color: '#666', fontWeight: 600 }}> / 6,236</span>
                  <span style={{ color: 'var(--gold, #d4a017)', fontWeight: 700 }}> ({quranProgress.percentage || 0}%)</span>
                </div>
                <div style={{ height: 10, background: 'var(--border-light, #e5e7eb)', borderRadius: 5, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%',
                    width: `${Math.min(quranProgress.percentage || 0, 100)}%`,
                    background: 'linear-gradient(90deg, var(--primary-teal, #0d9488), var(--gold, #d4a017))',
                    borderRadius: 5, transition: 'width 0.8s ease',
                  }} />
                </div>
              </div>
            )}

            {/* Badges */}
            {quranProgress && (
              <div style={{
                marginBottom: 20, padding: 16,
                background: 'var(--cream, #faf6f0)', borderRadius: 12,
                border: '1px solid var(--border-light, #e5e7eb)',
              }}>
                <BadgeDisplay user={user} compact={false} />
              </div>
            )}

            {/* Surah grid */}
            {quranProgress?.surahs ? (
              <>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(6, 1fr)',
                  gap: 8,
                  marginBottom: 16,
                }}>
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
                        style={{
                          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
                          padding: '10px 6px 8px', borderRadius: 10,
                          border: `1.5px solid ${complete ? 'var(--gold, #d4a017)' : 'var(--border-light, #e5e7eb)'}`,
                          background: bg, cursor: 'pointer',
                          transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                          minHeight: 72, textAlign: 'center',
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}
                      >
                        <span style={{ fontSize: '0.65rem', fontWeight: 600, color: '#888', lineHeight: 1 }}>{surah.number}</span>
                        <span style={{
                          fontSize: '0.72rem', fontWeight: 700, color: 'var(--deep-blue, #1e293b)',
                          lineHeight: 1.15, textAlign: 'center', wordBreak: 'break-word', maxWidth: '100%',
                          display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                        }}>{surah.name}</span>
                        <div style={{ width: '80%', height: 4, background: 'rgba(0,0,0,0.1)', borderRadius: 2, overflow: 'hidden', marginTop: 2 }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: 'var(--primary-teal, #0d9488)', borderRadius: 2 }} />
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Legend */}
                <div style={{ display: 'flex', justifyContent: 'center', gap: 16, flexWrap: 'wrap', fontSize: '0.72rem', color: '#6b7280' }}>
                  {[['#f1f5f9', '0%'], ['#ccfbf1', '1-25%'], ['#5eead4', '26-75%'], ['#f0c040', '76-99%'], ['#fbbf24', '100%']].map(([color, label]) => (
                    <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ width: 12, height: 12, borderRadius: 3, background: color, border: '1px solid #e5e7eb' }} />
                      <span>{label}</span>
                    </div>
                  ))}
                </div>

                <style jsx>{`
                  @media (max-width: 640px) {
                    div > div:first-child { grid-template-columns: repeat(4, 1fr) !important; gap: 6px !important; }
                  }
                  @media (max-width: 380px) {
                    div > div:first-child { grid-template-columns: repeat(3, 1fr) !important; }
                  }
                `}</style>
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: '#6b7280', fontSize: '0.9rem' }}>
                Loading progress map...
              </div>
            )}
          </div>
        )}
      </div>

      <BottomNav user={user} />
    </>
  );
}
