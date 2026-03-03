'use client';
import { useState, useEffect } from 'react';
import { BACKEND_URL } from '../lib/config';

export default function DailyInsightCard({ user, date, visible }) {
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!visible || !user || !date) return;
    fetchInsight();
  }, [visible, user, date]);

  const fetchInsight = async () => {
    setLoading(true);
    setError('');
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/daily-insight/${date}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok && data.insight) {
        setInsight(data.insight);
      } else if (res.status === 404) {
        // No log for this date yet
        setInsight(null);
      } else {
        setError(data.error || 'Could not load insight');
      }
    } catch (err) {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  if (!visible) return null;
  if (loading) {
    return (
      <div style={{
        background: 'white',
        borderRadius: 14,
        border: '1px solid #e5e7eb',
        padding: '20px 16px',
        textAlign: 'center',
      }}>
        <div style={{
          fontSize: '0.85rem',
          color: '#6b7280',
          fontStyle: 'italic',
        }}>
          Reflecting on your day...
        </div>
      </div>
    );
  }
  if (error || !insight) return null;

  return (
    <div style={{
      background: 'white',
      borderRadius: 14,
      border: '1px solid #e5e7eb',
      padding: '16px',
      animation: 'fadeIn 0.4s ease',
    }}>
      <div style={{
        fontSize: '0.7rem',
        fontWeight: 600,
        color: '#9ca3af',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        marginBottom: 10,
      }}>
        Today's Reflection
      </div>

      {/* Observation */}
      {insight.observation && (
        <p style={{
          fontSize: '0.9rem',
          color: '#1e293b',
          margin: '0 0 10px 0',
          lineHeight: 1.5,
          fontWeight: 500,
        }}>
          {insight.observation}
        </p>
      )}

      {/* Correlation */}
      {insight.correlation && (
        <div style={{
          padding: '10px 12px',
          background: '#f0fdf4',
          borderRadius: 10,
          marginBottom: 10,
        }}>
          <span style={{
            fontSize: '0.65rem',
            fontWeight: 600,
            color: '#059669',
            textTransform: 'uppercase',
            letterSpacing: '0.3px',
          }}>
            Pattern noticed
          </span>
          <p style={{
            fontSize: '0.82rem',
            color: '#374151',
            margin: '4px 0 0 0',
            lineHeight: 1.5,
          }}>
            {insight.correlation}
          </p>
        </div>
      )}

      {/* Encouragement */}
      {insight.encouragement && (
        <p style={{
          fontSize: '0.85rem',
          color: '#374151',
          margin: '0 0 8px 0',
          lineHeight: 1.5,
        }}>
          {insight.encouragement}
        </p>
      )}

      {/* Strain note */}
      {insight.strain_note && (
        <div style={{
          padding: '10px 12px',
          background: '#fffbeb',
          borderRadius: 10,
          borderLeft: '3px solid #d97706',
        }}>
          <p style={{
            fontSize: '0.82rem',
            color: '#92400e',
            margin: 0,
            lineHeight: 1.5,
          }}>
            {insight.strain_note}
          </p>
        </div>
      )}
    </div>
  );
}
