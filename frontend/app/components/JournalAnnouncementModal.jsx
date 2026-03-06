'use client';
import { useState, useEffect, useCallback } from 'react';
import { Z_INDEX } from '../utils/zIndex';

const FEATURES = [
  { color: '#0d9488', title: 'Daily Tracking', desc: 'Log salah, Quran, dhikr, and fasting with a quick-log mode for busy days.' },
  { color: '#d4af37', title: 'Heart Notes', desc: 'Write private reflections — gratitude, dua, tawbah, or Quranic insights — encrypted and visible only to you.' },
  { color: '#6366f1', title: 'Personalized Insights', desc: 'The journal learns your patterns and surfaces gentle observations about what helps your iman grow.' },
  { color: '#f59e0b', title: 'Struggle Goals', desc: 'Declare a personal struggle and receive curated daily goals, weekly milestones, and phase-based guidance.' },
  { color: '#ef4444', title: 'Strain Awareness', desc: 'Gentle signals when your effort is rising too fast — because the body has a right over you.' },
];

const STORAGE_KEY = 'tadabbur_journal_announced';

export default function JournalAnnouncementModal({ user }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!user?.uid) return;
    try {
      const seen = localStorage.getItem(`${STORAGE_KEY}_${user.uid}`);
      if (!seen) setVisible(true);
    } catch {}
  }, [user?.uid]);

  const dismiss = useCallback(() => {
    setVisible(false);
    if (user?.uid) {
      try { localStorage.setItem(`${STORAGE_KEY}_${user.uid}`, '1'); } catch {}
    }
  }, [user?.uid]);

  const goToJournal = useCallback(() => {
    dismiss();
    window.location.href = '/journal';
  }, [dismiss]);

  if (!visible) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={dismiss}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.55)',
          zIndex: Z_INDEX.MODAL_BACKDROP,
          animation: 'jAnnFadeIn 0.3s ease',
        }}
      />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Iman Journal announcement"
        style={{
          position: 'fixed',
          top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '92%', maxWidth: '440px',
          background: 'var(--cream, #faf6f0)',
          borderRadius: '16px',
          boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
          zIndex: Z_INDEX.MODAL,
          overflow: 'hidden',
          animation: 'jAnnSlideIn 0.35s ease',
          color: 'var(--foreground, #2C3E50)',
        }}
      >
        {/* Close */}
        <button
          onClick={dismiss}
          aria-label="Dismiss"
          style={{
            position: 'absolute', top: 12, right: 12,
            background: 'none', border: 'none',
            color: 'var(--text-muted, #6b7280)', fontSize: '18px',
            cursor: 'pointer', padding: '4px 8px',
            borderRadius: 6, zIndex: 1,
          }}
        >
          X
        </button>

        {/* Header */}
        <div style={{
          padding: '28px 24px 18px',
          background: 'var(--background, #FDFBF7)',
          borderBottom: '2px solid var(--border-light, #e5e7eb)',
          textAlign: 'center',
        }}>
          <div style={{
            width: 52, height: 52, borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--primary-teal, #0d9488), var(--gold, #d4af37))',
            color: 'white',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.5rem', fontWeight: 700, marginBottom: 10,
          }}>J</div>
          <h2 style={{
            margin: '0 0 6px', fontSize: '1.25rem',
            color: 'var(--deep-blue, #1e3a5f)',
          }}>
            Introducing: Your Iman Journal
          </h2>
          <p style={{
            margin: 0, fontSize: '0.85rem',
            color: 'var(--text-secondary, #64748B)', lineHeight: 1.5,
          }}>
            A private, intelligent companion for your spiritual growth.
          </p>
        </div>

        {/* Features */}
        <div style={{ padding: '18px 24px 12px' }}>
          {FEATURES.map((f, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'flex-start', gap: '12px',
              marginBottom: i < FEATURES.length - 1 ? '14px' : 0,
            }}>
              <div style={{
                width: 8, height: 8, borderRadius: '50%',
                backgroundColor: f.color, marginTop: 6, flexShrink: 0,
              }} />
              <div>
                <div style={{
                  fontSize: '0.88rem', fontWeight: 600,
                  color: 'var(--deep-blue, #1e3a5f)', marginBottom: 2,
                }}>{f.title}</div>
                <div style={{
                  fontSize: '0.8rem', lineHeight: 1.5,
                  color: 'var(--text-secondary, #64748B)',
                }}>{f.desc}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Closing line */}
        <div style={{
          padding: '0 24px 14px', textAlign: 'center',
        }}>
          <p style={{
            margin: 0, fontSize: '0.8rem', fontStyle: 'italic',
            color: 'var(--text-muted, #9ca3af)',
          }}>
            A mirror for your heart, not a scorecard.
          </p>
        </div>

        {/* Footer */}
        <div style={{
          padding: '14px 24px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          borderTop: '1px solid var(--border-light, #e5e7eb)',
          background: 'var(--cream, #faf6f0)',
        }}>
          <button
            onClick={dismiss}
            style={{
              padding: '8px 16px', background: 'none', border: 'none',
              color: 'var(--text-muted, #6b7280)', cursor: 'pointer', fontSize: '0.9rem',
            }}
          >
            Maybe later
          </button>
          <button
            onClick={goToJournal}
            style={{
              padding: '10px 24px', border: 'none', borderRadius: '10px',
              background: 'linear-gradient(135deg, var(--primary-teal, #10b981) 0%, var(--gold, #d4af37) 100%)',
              color: 'white', cursor: 'pointer',
              fontWeight: 600, fontSize: '0.9rem',
            }}
          >
            Open Journal
          </button>
        </div>
      </div>

      {/* Animations */}
      <style>{`
        @keyframes jAnnFadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes jAnnSlideIn {
          from { opacity: 0; transform: translate(-50%, -48%); }
          to { opacity: 1; transform: translate(-50%, -50%); }
        }
      `}</style>
    </>
  );
}
