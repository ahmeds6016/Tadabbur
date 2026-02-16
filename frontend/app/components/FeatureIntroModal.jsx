'use client';
import { useState, useEffect, useCallback } from 'react';
import { Z_INDEX } from '../utils/zIndex';

const FEATURE_STEPS = [
  {
    title: 'Welcome to Tadabbur',
    titleWithName: (name) => `Welcome, ${name}!`,
    description: 'Deep Quranic reflection drawn from classical scholarly sources — synthesized and personalized to your learning journey, not generated from scratch.',
    iconLabel: 'T',
  },
  {
    title: 'Choose a Surah and Verse Range',
    description: 'Browse all 114 surahs and select any verse or range. The app adjusts the range based on available commentary so every response is complete.',
    iconLabel: 'S',
  },
  {
    title: 'Grounded in Classical Scholarship',
    description: 'Each response draws from multiple authenticated scholarly works — matched to your chosen verses and presented through the lens of your learning persona.',
    iconLabel: 'C',
  },
  {
    title: 'Your Learning Journey',
    description: 'Save answers, write reflections, follow reading plans, track your progress across the Quran, and earn badges as you grow. Your reflections are encrypted and private — only you can see them.',
    iconLabel: 'R',
  }
];

export default function FeatureIntroModal({ isOpen, onComplete, userName }) {
  const [currentStep, setCurrentStep] = useState(0);

  // Reset step when opened
  useEffect(() => {
    if (isOpen) setCurrentStep(0);
  }, [isOpen]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e) => {
      if (e.key === 'Escape') { onComplete(); return; }
      if (e.key === 'ArrowRight' || e.key === 'Enter') {
        if (currentStep < FEATURE_STEPS.length - 1) setCurrentStep(s => s + 1);
        else onComplete();
      }
      if (e.key === 'ArrowLeft' && currentStep > 0) setCurrentStep(s => s - 1);
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [isOpen, currentStep, onComplete]);

  if (!isOpen) return null;

  const step = FEATURE_STEPS[currentStep];
  const isLast = currentStep === FEATURE_STEPS.length - 1;
  const isFirst = currentStep === 0;
  const title = isFirst && userName ? step.titleWithName(userName) : step.title;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onComplete}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.5)',
          zIndex: Z_INDEX.MODAL_BACKDROP,
          animation: 'featureIntroFadeIn 0.3s ease'
        }}
      />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Feature introduction"
        style={{
          position: 'fixed',
          top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '90%', maxWidth: '480px',
          background: 'var(--cream, #faf6f0)',
          borderRadius: '16px',
          boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
          zIndex: Z_INDEX.MODAL,
          overflow: 'hidden',
          animation: 'featureIntroSlideIn 0.3s ease',
          color: 'var(--foreground, #2C3E50)'
        }}
      >
        {/* Close button */}
        <button
          onClick={onComplete}
          aria-label="Skip introduction"
          style={{
            position: 'absolute', top: 12, right: 12,
            background: 'none', border: 'none',
            color: 'var(--text-muted, #6b7280)', fontSize: '18px',
            cursor: 'pointer', padding: '4px 8px',
            borderRadius: 6, zIndex: 1
          }}
        >
          X
        </button>

        {/* Header */}
        <div style={{
          padding: '28px 24px 16px',
          background: 'var(--background, #FDFBF7)',
          borderBottom: '2px solid var(--border-light, #e5e7eb)',
          textAlign: 'center'
        }}>
          <div style={{
            width: 48, height: 48, borderRadius: '50%',
            background: 'var(--primary-teal, #0d9488)', color: 'white',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.3rem', fontWeight: 700, marginBottom: 8
          }}>{step.iconLabel}</div>
          <h2 style={{
            margin: 0, fontSize: '1.3rem',
            color: 'var(--deep-blue, #1e3a5f)'
          }}>
            {title}
          </h2>
          {/* Progress dots */}
          <div style={{
            display: 'flex', gap: '8px', marginTop: '16px',
            justifyContent: 'center'
          }}>
            {FEATURE_STEPS.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentStep(i)}
                aria-label={`Go to step ${i + 1}`}
                style={{
                  width: i === currentStep ? 24 : 8,
                  height: 8, borderRadius: 4,
                  border: 'none', padding: 0,
                  backgroundColor: i === currentStep
                    ? 'var(--primary-teal, #10b981)'
                    : 'rgba(0,0,0,0.15)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              />
            ))}
          </div>
        </div>

        {/* Content */}
        <div style={{ padding: '24px', minHeight: '100px' }}>
          <p style={{
            margin: 0, color: 'var(--text-secondary, #64748B)', lineHeight: '1.7',
            fontSize: '0.95rem', textAlign: 'center'
          }}>
            {step.description}
          </p>
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px',
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'center',
          borderTop: '1px solid var(--border-light, #e5e7eb)',
          background: 'var(--cream, #faf6f0)'
        }}>
          <button
            onClick={onComplete}
            style={{
              padding: '8px 16px', background: 'none', border: 'none',
              color: 'var(--text-muted, #6b7280)', cursor: 'pointer', fontSize: '0.9rem'
            }}
          >
            Skip
          </button>
          <div style={{ display: 'flex', gap: '8px' }}>
            {!isFirst && (
              <button
                onClick={() => setCurrentStep(s => s - 1)}
                style={{
                  padding: '10px 20px', border: '1px solid var(--border-light, #e5e7eb)',
                  borderRadius: '10px', background: 'var(--background, #FDFBF7)',
                  color: 'var(--deep-blue, #1e3a5f)', cursor: 'pointer',
                  fontWeight: '600', fontSize: '0.9rem'
                }}
              >
                Back
              </button>
            )}
            <button
              onClick={() => {
                if (isLast) onComplete();
                else setCurrentStep(s => s + 1);
              }}
              style={{
                padding: '10px 24px', border: 'none', borderRadius: '10px',
                background: 'linear-gradient(135deg, var(--primary-teal, #10b981) 0%, var(--gold, #d4af37) 100%)',
                color: 'white', cursor: 'pointer',
                fontWeight: '600', fontSize: '0.9rem'
              }}
            >
              {isLast ? 'Get Started' : 'Next'}
            </button>
          </div>
        </div>
      </div>

      {/* Animations */}
      <style>{`
        @keyframes featureIntroFadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes featureIntroSlideIn {
          from { opacity: 0; transform: translate(-50%, -48%); }
          to { opacity: 1; transform: translate(-50%, -50%); }
        }
      `}</style>
    </>
  );
}
