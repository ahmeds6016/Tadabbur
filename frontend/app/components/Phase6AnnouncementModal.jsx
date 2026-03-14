'use client';
import { useState, useEffect, useCallback } from 'react';
import { Z_INDEX } from '../utils/zIndex';

const FEATURES = [
  {
    color: '#6366f1',
    title: 'Deep Personalization',
    desc: 'Your weekly digests and daily insights now address you by name, reference your heart note themes, and connect to the verses you\'ve explored.',
  },
  {
    color: '#0d9488',
    title: 'Refined Trajectory',
    desc: 'After your first two weeks, see weekly sparklines, category trends, and milestone badges — a richer picture of your spiritual rhythm.',
  },
  {
    color: '#2563eb',
    title: 'Intelligent Correlation Insights',
    desc: 'Your weekly patterns are now synthesized into a personalized narrative — surfacing key insights grounded in your actual spiritual data.',
  },
  {
    color: '#d97706',
    title: 'In-App Feedback',
    desc: 'Found a bug or have a feature idea? The FAQ now includes a built-in feedback form — tap the help button on any page to reach it.',
  },
  {
    color: '#059669',
    title: 'Dark Mode',
    desc: 'The entire app — including the journal, heart notes, digests, and trajectory — now adapts to your device\'s dark mode setting.',
  },
];

const STORAGE_KEY = 'tadabbur_phase6_announced';

export default function Phase6AnnouncementModal({ user }) {
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
          animation: 'p6FadeIn 0.3s ease',
        }}
      />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="What's new in Tadabbur"
        style={{
          position: 'fixed',
          top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '92%', maxWidth: '440px',
          background: 'var(--color-surface, #faf6f0)',
          borderRadius: '16px',
          boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
          zIndex: Z_INDEX.MODAL,
          overflow: 'hidden',
          animation: 'p6SlideIn 0.35s ease',
          color: 'var(--color-text, #2C3E50)',
        }}
      >
        {/* Close */}
        <button
          onClick={dismiss}
          aria-label="Dismiss"
          style={{
            position: 'absolute', top: 12, right: 12,
            background: 'none', border: 'none',
            color: 'var(--color-text-muted, #6b7280)', fontSize: '18px',
            cursor: 'pointer', padding: '4px 8px',
            borderRadius: 6, zIndex: 1,
          }}
        >
          X
        </button>

        {/* Header */}
        <div style={{
          padding: '28px 24px 18px',
          background: 'var(--color-surface-muted, #FDFBF7)',
          borderBottom: '2px solid var(--color-border, #e5e7eb)',
          textAlign: 'center',
        }}>
          <div style={{
            width: 52, height: 52, borderRadius: '50%',
            background: 'linear-gradient(135deg, #6366f1, #0d9488)',
            color: 'white',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.3rem', fontWeight: 700, marginBottom: 10,
          }}>
            <span style={{ lineHeight: 1 }}>&#x2728;</span>
          </div>
          <h2 style={{
            margin: '0 0 6px', fontSize: '1.25rem',
            color: 'var(--color-primary, #1e3a5f)',
          }}>
            What&apos;s New in Tadabbur
          </h2>
          <p style={{
            margin: 0, fontSize: '0.85rem',
            color: 'var(--color-text-secondary, #64748B)', lineHeight: 1.5,
          }}>
            Your journal and app experience just got a major upgrade.
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
                  color: 'var(--color-primary, #1e3a5f)', marginBottom: 2,
                }}>{f.title}</div>
                <div style={{
                  fontSize: '0.8rem', lineHeight: 1.5,
                  color: 'var(--color-text-secondary, #64748B)',
                }}>{f.desc}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{
          padding: '14px 24px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          borderTop: '1px solid var(--color-border, #e5e7eb)',
          background: 'var(--color-surface-muted, #faf6f0)',
        }}>
          <button
            onClick={dismiss}
            style={{
              padding: '8px 16px', background: 'none', border: 'none',
              color: 'var(--color-text-muted, #6b7280)', cursor: 'pointer', fontSize: '0.9rem',
            }}
          >
            Got it
          </button>
          <button
            onClick={goToJournal}
            style={{
              padding: '10px 24px', border: 'none', borderRadius: '10px',
              background: 'linear-gradient(135deg, #6366f1 0%, #0d9488 100%)',
              color: 'white', cursor: 'pointer',
              fontWeight: 600, fontSize: '0.9rem',
            }}
          >
            Try the Journal
          </button>
        </div>
      </div>

      {/* Animations */}
      <style>{`
        @keyframes p6FadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes p6SlideIn {
          from { opacity: 0; transform: translate(-50%, -48%); }
          to { opacity: 1; transform: translate(-50%, -50%); }
        }
      `}</style>
    </>
  );
}
