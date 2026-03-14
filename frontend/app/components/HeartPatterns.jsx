'use client';
import { useState, useEffect } from 'react';
import { BACKEND_URL } from '../lib/config';

export default function HeartPatterns({ user }) {
  const [patterns, setPatterns] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    const fetchPatterns = async () => {
      try {
        const token = await user.getIdToken();
        const res = await fetch(`${BACKEND_URL}/iman/heart-patterns`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setPatterns(data.patterns);
        }
      } catch (err) {
        console.error('Failed to fetch heart patterns:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchPatterns();
  }, [user]);

  if (loading || !patterns?.has_patterns) return null;

  const allInsights = [
    ...(patterns.temporal_patterns || []).map((p) => p.insight_text),
    ...(patterns.emotional_arcs || []).map((a) => a.insight_text),
    ...(patterns.score_correlation ? [patterns.score_correlation.insight_text] : []),
  ];

  if (allInsights.length === 0) return null;

  return (
    <div className="heart-patterns-card">
      <h3 className="hp-card-title">Heart Note Insights</h3>
      {allInsights.map((insight, i) => (
        <p key={i} className="hp-insight-text">{insight}</p>
      ))}

      <style jsx>{`
        .heart-patterns-card {
          background: var(--color-surface);
          border-radius: 14px;
          border: 1px solid var(--color-border);
          padding: 16px;
        }
        .hp-card-title {
          font-size: 0.8rem;
          font-weight: 600;
          color: var(--color-text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.4px;
          margin: 0 0 10px 0;
        }
        .hp-insight-text {
          font-size: 0.85rem;
          color: var(--color-text);
          margin: 0 0 6px 0;
          line-height: 1.5;
          padding-left: 16px;
          position: relative;
        }
        .hp-insight-text::before {
          content: '\\2022';
          position: absolute;
          left: 4px;
          color: var(--primary-teal, #0d9488);
        }
        .hp-insight-text:last-child {
          margin-bottom: 0;
        }
      `}</style>
    </div>
  );
}
