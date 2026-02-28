'use client';
import { useState } from 'react';
import { BACKEND_URL } from '../lib/config';

const STRUGGLE_CATALOG = [
  { id: 'prayer_consistency', label: 'Prayer Consistency', description: 'Maintaining the five daily prayers on time', icon: '🕐', color: '#0d9488' },
  { id: 'anger_management', label: 'Anger Management', description: 'Controlling anger and choosing gentleness', icon: '🔥', color: '#dc2626' },
  { id: 'lowering_gaze', label: 'Lowering the Gaze', description: 'Guarding the eyes in a digital world', icon: '👁', color: '#7c3aed' },
  { id: 'quran_disconnection', label: 'Quranic Disconnection', description: 'Feeling distant from the Quran', icon: '📖', color: '#2563eb' },
  { id: 'spiritual_dryness', label: 'Spiritual Dryness', description: 'Worship feels mechanical, the heart feels numb', icon: '☁️', color: '#64748b' },
  { id: 'tongue_control', label: 'Tongue Control', description: 'Guarding speech from gossip and harshness', icon: '🤐', color: '#ea580c' },
  { id: 'worldly_attachment', label: 'Worldly Attachment', description: 'The heart clinging to dunya over akhira', icon: '💎', color: '#ca8a04' },
  { id: 'pride_arrogance', label: 'Pride & Arrogance', description: 'Subtle or overt feelings of superiority', icon: '👑', color: '#9333ea' },
  { id: 'laziness_procrastination', label: 'Laziness', description: 'Delaying good deeds and spiritual lethargy', icon: '⏸', color: '#0284c7' },
  { id: 'repentance_cycle', label: 'The Repentance Cycle', description: 'Falling, repenting, falling again', icon: '🔄', color: '#059669' },
];

export default function StruggleDeclaration({ user, activeStruggleIds = [], onDeclared }) {
  const [declaring, setDeclaring] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleDeclare = async (struggle) => {
    if (declaring) return;
    setDeclaring(struggle.id);
    setError('');
    setResult(null);

    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/struggle`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ struggle_id: struggle.id }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.error || 'Failed to declare struggle');
        return;
      }

      setResult(data);
      if (onDeclared) onDeclared(data);
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setDeclaring(null);
    }
  };

  const available = STRUGGLE_CATALOG.filter(
    (s) => !activeStruggleIds.includes(s.id)
  );

  return (
    <div className="struggle-declaration">
      <h3 className="sd-title">What are you working on?</h3>
      <p className="sd-subtitle">
        Declare a struggle to receive scholarly guidance and track your progress.
      </p>

      <div className="sd-grid">
        {available.map((s) => (
          <button
            key={s.id}
            className="sd-card"
            onClick={() => handleDeclare(s)}
            disabled={declaring === s.id}
            style={{ borderColor: s.color }}
          >
            <span className="sd-icon">{s.icon}</span>
            <span className="sd-label" style={{ color: s.color }}>{s.label}</span>
            <span className="sd-desc">{s.description}</span>
            {declaring === s.id && <span className="sd-loading">Resolving guidance...</span>}
          </button>
        ))}
      </div>

      {error && <p className="sd-error">{error}</p>}

      {result && (
        <div className="sd-result" style={{ borderColor: STRUGGLE_CATALOG.find(s => s.id === result.struggle_id)?.color || '#0d9488' }}>
          <h4 className="sd-result-title">{result.label}</h4>
          {result.comfort_verse && (
            <p className="sd-comfort">
              "{result.comfort_verse.text}"
              <span className="sd-ref">
                — Surah {result.comfort_verse.surah}:{result.comfort_verse.verse}
              </span>
            </p>
          )}
          {result.phases && result.phases[0] && (
            <p className="sd-phase-intro">
              <strong>This week:</strong> {result.phases[0]}
            </p>
          )}
          {result.guidance_excerpts?.length > 0 && (
            <div className="sd-guidance">
              <p className="sd-guidance-label">From the scholars:</p>
              {result.guidance_excerpts.slice(0, 2).map((g, i) => (
                <div key={i} className="sd-excerpt">
                  <span className="sd-source">{g.source}: {g.title}</span>
                  <p className="sd-text">{g.text?.slice(0, 400)}{g.text?.length > 400 ? '...' : ''}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .struggle-declaration {
          margin-top: 20px;
        }
        .sd-title {
          font-size: 1rem;
          font-weight: 600;
          color: var(--deep-blue, #1e293b);
          margin: 0 0 4px 0;
        }
        .sd-subtitle {
          font-size: 0.8rem;
          color: #6b7280;
          margin: 0 0 14px 0;
        }
        .sd-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 10px;
        }
        .sd-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          padding: 12px 8px;
          background: white;
          border: 1.5px solid #e5e7eb;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.15s ease;
          text-align: center;
        }
        .sd-card:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
        .sd-card:disabled {
          opacity: 0.6;
          cursor: wait;
        }
        .sd-icon {
          font-size: 1.5rem;
        }
        .sd-label {
          font-size: 0.8rem;
          font-weight: 600;
        }
        .sd-desc {
          font-size: 0.7rem;
          color: #9ca3af;
          line-height: 1.3;
        }
        .sd-loading {
          font-size: 0.65rem;
          color: #6b7280;
          font-style: italic;
          margin-top: 2px;
        }
        .sd-error {
          color: #dc2626;
          font-size: 0.8rem;
          margin-top: 10px;
        }
        .sd-result {
          margin-top: 16px;
          padding: 16px;
          background: #f8fafc;
          border-radius: 12px;
          border-left: 3px solid;
        }
        .sd-result-title {
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--deep-blue, #1e293b);
          margin: 0 0 10px 0;
        }
        .sd-comfort {
          font-size: 0.85rem;
          font-style: italic;
          color: var(--deep-blue, #1e293b);
          margin: 0 0 8px 0;
          line-height: 1.5;
        }
        .sd-ref {
          display: block;
          font-size: 0.7rem;
          color: #6b7280;
          font-style: normal;
          margin-top: 4px;
        }
        .sd-phase-intro {
          font-size: 0.8rem;
          color: #374151;
          margin: 8px 0;
          line-height: 1.4;
        }
        .sd-guidance {
          margin-top: 12px;
        }
        .sd-guidance-label {
          font-size: 0.75rem;
          font-weight: 600;
          color: #6b7280;
          margin: 0 0 8px 0;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .sd-excerpt {
          margin-bottom: 10px;
          padding: 10px;
          background: white;
          border-radius: 8px;
        }
        .sd-source {
          font-size: 0.7rem;
          font-weight: 600;
          color: #9ca3af;
          text-transform: uppercase;
        }
        .sd-text {
          font-size: 0.8rem;
          color: #374151;
          margin: 4px 0 0 0;
          line-height: 1.5;
        }
        @media (min-width: 640px) {
          .sd-grid {
            grid-template-columns: repeat(3, 1fr);
          }
        }
      `}</style>
    </div>
  );
}
