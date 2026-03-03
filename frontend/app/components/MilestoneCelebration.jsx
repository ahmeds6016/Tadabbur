'use client';
import { useState, useEffect } from 'react';
import { Award, X } from 'lucide-react';

export default function MilestoneCelebration({ struggle, milestone }) {
  const [dismissed, setDismissed] = useState(false);
  const [alreadySeen, setAlreadySeen] = useState(false);

  const storageKey = milestone
    ? `milestone_${struggle.struggle_id}_phase_${milestone.phase_completed}`
    : '';

  useEffect(() => {
    if (!storageKey) return;
    try {
      if (localStorage.getItem(storageKey)) setAlreadySeen(true);
    } catch {}
  }, [storageKey]);

  if (!milestone || !milestone.just_transitioned || dismissed || alreadySeen) return null;

  const handleDismiss = () => {
    setDismissed(true);
    try {
      localStorage.setItem(storageKey, 'true');
    } catch {}
  };

  const comfortVerse = struggle.comfort_verse;
  const color = struggle.color || '#0d9488';

  return (
    <div style={{
      background: 'white',
      borderRadius: 14,
      border: `2px solid ${color}`,
      padding: '16px',
      position: 'relative',
      animation: 'fadeIn 0.5s ease',
      boxShadow: `0 4px 16px ${color}20`,
    }}>
      {/* Dismiss button */}
      <button
        onClick={handleDismiss}
        style={{
          position: 'absolute',
          top: 10,
          right: 10,
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 4,
          color: '#9ca3af',
        }}
      >
        <X size={16} />
      </button>

      {/* Badge */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        marginBottom: 12,
      }}>
        <div style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          background: `${color}15`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Award size={20} color={color} strokeWidth={2} />
        </div>
        <div>
          <div style={{
            fontSize: '0.7rem',
            fontWeight: 600,
            color: color,
            textTransform: 'uppercase',
            letterSpacing: '0.4px',
          }}>
            Phase Complete
          </div>
          <div style={{
            fontSize: '0.92rem',
            fontWeight: 600,
            color: '#1e293b',
          }}>
            {struggle.label}
          </div>
        </div>
      </div>

      {/* Previous phase */}
      {milestone.previous_phase_label && (
        <p style={{
          fontSize: '0.78rem',
          color: '#9ca3af',
          margin: '0 0 6px 0',
          lineHeight: 1.4,
          textDecoration: 'line-through',
          fontStyle: 'italic',
        }}>
          {milestone.previous_phase_label}
        </p>
      )}

      {/* New phase */}
      {milestone.phase_label && (
        <p style={{
          fontSize: '0.85rem',
          color: '#1e293b',
          margin: '0 0 12px 0',
          lineHeight: 1.5,
          fontWeight: 500,
        }}>
          {milestone.phase_label}
        </p>
      )}

      {/* Comfort verse */}
      {comfortVerse && (
        <div style={{
          padding: '10px 12px',
          background: '#f0fdf4',
          borderRadius: 10,
          borderLeft: `3px solid ${color}`,
          textAlign: 'center',
        }}>
          <p style={{
            fontSize: '0.82rem',
            fontStyle: 'italic',
            color: '#1e293b',
            margin: '0 0 4px 0',
            lineHeight: 1.5,
          }}>
            "{comfortVerse.text}"
          </p>
          <span style={{
            fontSize: '0.65rem',
            color: '#6b7280',
          }}>
            — Surah {comfortVerse.surah}:{comfortVerse.verse}
          </span>
        </div>
      )}
    </div>
  );
}
