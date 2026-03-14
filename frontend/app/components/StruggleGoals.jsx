'use client';
import { useState, useEffect, useCallback } from 'react';
import { Check } from 'lucide-react';
import { BACKEND_URL } from '../lib/config';

export default function StruggleGoals({ user, struggleId, struggleColor, struggleLabel, onGoalCompleted }) {
  const [goals, setGoals] = useState(null);
  const [loading, setLoading] = useState(true);
  const [completingId, setCompletingId] = useState(null);

  const fetchGoals = useCallback(async () => {
    if (!user || !struggleId) return;
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/struggle/${struggleId}/goals`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setGoals(data);
      }
    } catch (err) {
      console.error('Failed to fetch goals:', err);
    } finally {
      setLoading(false);
    }
  }, [user, struggleId]);

  useEffect(() => { fetchGoals(); }, [fetchGoals]);

  const handleComplete = async (goalId) => {
    if (completingId) return;
    setCompletingId(goalId);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/struggle/${struggleId}/goal/complete`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ goal_id: goalId }),
      });
      if (res.ok) {
        await fetchGoals();
        if (onGoalCompleted) onGoalCompleted();
      }
    } catch (err) {
      console.error('Failed to complete goal:', err);
    } finally {
      setCompletingId(null);
    }
  };

  if (loading || !goals) return null;

  const activeDailyGoals = (goals.daily || []).filter(g => !g.completed_today);
  const completedDailyGoals = (goals.daily || []).filter(g => g.completed_today);
  const weeklyGoal = goals.weekly;
  const allDailyDone = activeDailyGoals.length === 0 && completedDailyGoals.length > 0;

  return (
    <div style={{
      marginTop: 8,
      padding: '12px',
      background: 'var(--color-surface-muted)',
      borderRadius: 10,
      border: '1px solid var(--color-border-light)',
    }}>
      <div style={{
        fontSize: '0.7rem',
        fontWeight: 600,
        color: struggleColor || '#6b7280',
        textTransform: 'uppercase',
        letterSpacing: '0.3px',
        marginBottom: 8,
      }}>
        Today's Goals
      </div>

      {/* Active daily goals */}
      {activeDailyGoals.map((goal) => (
        <div
          key={goal.id}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '8px 0',
            borderBottom: '1px solid var(--color-border-light)',
            transition: 'opacity 0.3s ease, max-height 0.3s ease',
          }}
        >
          <button
            onClick={() => handleComplete(goal.id)}
            disabled={completingId === goal.id}
            style={{
              width: 26,
              height: 26,
              minWidth: 26,
              borderRadius: '50%',
              border: `2px solid ${struggleColor || '#d1d5db'}`,
              background: 'var(--color-surface)',
              cursor: completingId === goal.id ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 0,
              transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          >
            {completingId === goal.id && (
              <div style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: struggleColor || '#0d9488',
                opacity: 0.4,
              }} />
            )}
          </button>
          <span style={{
            fontSize: '0.82rem',
            color: 'var(--color-text)',
            lineHeight: 1.4,
            flex: 1,
          }}>
            {goal.text}
          </span>
        </div>
      ))}

      {/* Completed daily goals */}
      {completedDailyGoals.map((goal) => (
        <div
          key={goal.id}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '6px 0',
            opacity: 0.5,
            transition: 'opacity 0.3s ease',
          }}
        >
          <div style={{
            width: 26,
            height: 26,
            minWidth: 26,
            borderRadius: '50%',
            background: struggleColor || '#0d9488',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Check size={14} color="white" strokeWidth={3} />
          </div>
          <span style={{
            fontSize: '0.82rem',
            color: 'var(--color-text-muted)',
            textDecoration: 'line-through',
            lineHeight: 1.4,
            flex: 1,
          }}>
            {goal.text}
          </span>
        </div>
      ))}

      {allDailyDone && (
        <p style={{
          fontSize: '0.78rem',
          color: '#059669',
          margin: '6px 0 0 0',
          fontStyle: 'italic',
          textAlign: 'center',
        }}>
          All daily goals complete. MashaAllah!
        </p>
      )}

      {/* Weekly goal */}
      {weeklyGoal && (
        <>
          <div style={{
            borderTop: '1px solid var(--color-border)',
            marginTop: 10,
            paddingTop: 10,
          }}>
            <div style={{
              fontSize: '0.65rem',
              fontWeight: 600,
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.3px',
              marginBottom: 6,
            }}>
              Weekly Goal
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}>
              {weeklyGoal.completed_this_week ? (
                <div style={{
                  width: 26,
                  height: 26,
                  minWidth: 26,
                  borderRadius: '50%',
                  background: struggleColor || '#0d9488',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <Check size={14} color="white" strokeWidth={3} />
                </div>
              ) : (
                <button
                  onClick={() => handleComplete(weeklyGoal.id)}
                  disabled={!!completingId}
                  style={{
                    width: 26,
                    height: 26,
                    minWidth: 26,
                    borderRadius: '50%',
                    border: `2px solid ${struggleColor || '#d1d5db'}`,
                    background: 'var(--color-surface)',
                    cursor: 'pointer',
                    padding: 0,
                    transition: 'all 0.2s ease',
                  }}
                />
              )}
              <div style={{ flex: 1 }}>
                <span style={{
                  fontSize: '0.82rem',
                  color: weeklyGoal.completed_this_week ? 'var(--color-text-secondary, #9ca3af)' : 'var(--foreground, #374151)',
                  textDecoration: weeklyGoal.completed_this_week ? 'line-through' : 'none',
                  lineHeight: 1.4,
                }}>
                  {weeklyGoal.text}
                </span>
                {weeklyGoal.completed_this_week && weeklyGoal.days_until_reset > 0 && (
                  <span style={{
                    display: 'block',
                    fontSize: '0.68rem',
                    color: 'var(--color-text-muted)',
                    marginTop: 2,
                  }}>
                    Resets in {weeklyGoal.days_until_reset} day{weeklyGoal.days_until_reset !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
