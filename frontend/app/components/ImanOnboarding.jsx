'use client';
import { useState, useEffect, useCallback } from 'react';
import { BACKEND_URL } from '../lib/config';
import BehaviorSelector from './BehaviorSelector';

const MAX_STRUGGLES = 3;

export default function ImanOnboarding({ user, onComplete }) {
  const [step, setStep] = useState(0);
  const [catalog, setCatalog] = useState(null);
  const [selectedBehaviors, setSelectedBehaviors] = useState([]);
  const [selectedStruggles, setSelectedStruggles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Fetch catalog on mount
  useEffect(() => {
    if (!user) return;
    const fetchCatalog = async () => {
      try {
        const token = await user.getIdToken();
        const res = await fetch(`${BACKEND_URL}/iman/catalog`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setCatalog(data);
          // Pre-select default behaviors
          setSelectedBehaviors(data.defaults?.default_behavior_ids || []);
        }
      } catch (err) {
        console.error('Failed to fetch catalog:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchCatalog();
  }, [user]);

  const handleSkip = useCallback(async () => {
    // Silent default setup (same as current behavior)
    setSubmitting(true);
    try {
      const token = await user.getIdToken();
      await fetch(`${BACKEND_URL}/iman/setup`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ onboarding_complete: true }),
      });
      onComplete();
    } catch (err) {
      setError('Setup failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }, [user, onComplete]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/setup`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          behavior_ids: selectedBehaviors,
          struggle_ids: selectedStruggles,
          onboarding_complete: true,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.error || 'Setup failed');
        return;
      }
      onComplete();
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleStruggle = (sid) => {
    setSelectedStruggles((prev) => {
      if (prev.includes(sid)) return prev.filter((id) => id !== sid);
      if (prev.length >= MAX_STRUGGLES) return prev;
      return [...prev, sid];
    });
  };

  // Keyboard navigation
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') handleSkip();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleSkip]);

  if (loading) {
    return (
      <div className="onboarding-loading">
        <p>Preparing your journal...</p>
        <style jsx>{`
          .onboarding-loading {
            display: flex; align-items: center; justify-content: center;
            min-height: 60vh; color: #6b7280; font-size: 0.95rem;
          }
        `}</style>
      </div>
    );
  }

  const canProceedStep1 = selectedBehaviors.length >= 3;
  const totalSteps = 4;

  return (
    <div className="iman-onboarding">
      <div className="ob-container">
        {/* Progress dots */}
        <div className="ob-progress">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className={`ob-dot ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}
            />
          ))}
        </div>

        {/* Skip button */}
        <button className="ob-skip" onClick={handleSkip} disabled={submitting}>
          Skip
        </button>

        {/* Step 0: Introduction */}
        {step === 0 && (
          <div className="ob-step">
            <div className="ob-medallion">
              <span className="ob-medallion-icon">&#xFDFD;</span>
            </div>
            <h2 className="ob-title">A Mirror, Not a Measure</h2>
            <p className="ob-body">
              Your spiritual journey is between you and Allah. This journal is
              simply a mirror — helping you see your patterns, celebrate your
              growth, and gently notice where you might turn your heart.
            </p>
            <p className="ob-body">
              There are no scores to chase, no grades to earn. Just honest
              reflection.
            </p>
            <p className="ob-verse">
              "O you who believe, fear Allah, and let every soul look to what it
              has put forth for tomorrow."
              <span className="ob-ref">— Surah Al-Hashr, 59:18</span>
            </p>
            <button className="ob-btn primary" onClick={() => setStep(1)}>
              Begin
            </button>
          </div>
        )}

        {/* Step 1: Behavior Selection */}
        {step === 1 && catalog && (
          <div className="ob-step">
            <h2 className="ob-title">What would you like to reflect on?</h2>
            <p className="ob-subtitle">
              Choose the practices you want to track daily. Start with 6-10 for
              the clearest picture. You can always change these later.
            </p>
            <BehaviorSelector
              categories={catalog.categories}
              behaviors={catalog.behaviors}
              selectedIds={selectedBehaviors}
              onChange={setSelectedBehaviors}
              maxSelections={catalog.defaults?.max_tracked || 15}
              minSelections={3}
            />
            <div className="ob-nav">
              <button className="ob-btn secondary" onClick={() => setStep(0)}>
                Back
              </button>
              <button
                className="ob-btn primary"
                onClick={() => setStep(2)}
                disabled={!canProceedStep1}
              >
                Next
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Struggle Declaration (optional) */}
        {step === 2 && catalog && (
          <div className="ob-step">
            <h2 className="ob-title">Is there something you are working on?</h2>
            <p className="ob-subtitle">
              Declaring a struggle is an act of courage, not weakness. Scholarly
              guidance from the Ihya, Madarij, and Riyad will be matched to help
              you. This step is optional.
            </p>
            <div className="ob-struggle-grid">
              {catalog.struggles.map((s) => {
                const isSelected = selectedStruggles.includes(s.id);
                const atMax = selectedStruggles.length >= MAX_STRUGGLES && !isSelected;
                return (
                  <button
                    key={s.id}
                    className={`ob-struggle-card ${isSelected ? 'selected' : ''} ${atMax ? 'disabled' : ''}`}
                    onClick={() => !atMax && toggleStruggle(s.id)}
                    disabled={atMax}
                    style={{ borderColor: isSelected ? s.color : undefined }}
                  >
                    <span className="ob-s-label" style={{ color: isSelected ? s.color : undefined }}>
                      {s.label}
                    </span>
                    <span className="ob-s-desc">{s.description}</span>
                    {isSelected && <span className="ob-s-check" style={{ color: s.color }}>&#10003;</span>}
                  </button>
                );
              })}
            </div>
            {selectedStruggles.length > 0 && (
              <p className="ob-struggle-count">
                {selectedStruggles.length} of {MAX_STRUGGLES} selected
              </p>
            )}
            <div className="ob-nav">
              <button className="ob-btn secondary" onClick={() => setStep(1)}>
                Back
              </button>
              <button className="ob-btn primary" onClick={() => setStep(3)}>
                {selectedStruggles.length > 0 ? 'Next' : 'Skip This Step'}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Calibration */}
        {step === 3 && (
          <div className="ob-step">
            <h2 className="ob-title">Your First 14 Days</h2>
            <p className="ob-body">
              For the first 14 days, we are learning YOUR normal. Log honestly —
              there is no right or wrong. After 14 days, the journal will start
              showing you patterns and gentle observations based on your own
              baseline, not anyone else's.
            </p>

            <div className="ob-cal-bar">
              <div className="ob-cal-fill" style={{ width: '7%' }} />
            </div>
            <p className="ob-cal-label">Day 1 of 14 — Calibrating</p>

            <div className="ob-tips">
              <p className="ob-tip"><span className="ob-bullet">&#x2022;</span> Log daily, even if briefly — consistency matters more than perfection</p>
              <p className="ob-tip"><span className="ob-bullet">&#x2022;</span> Missed a day? That is okay. The journal does not judge gaps</p>
              <p className="ob-tip"><span className="ob-bullet">&#x2022;</span> Your data is private and encrypted</p>
            </div>

            {error && <p className="ob-error">{error}</p>}

            <div className="ob-nav">
              <button className="ob-btn secondary" onClick={() => setStep(2)}>
                Back
              </button>
              <button
                className="ob-btn primary large"
                onClick={handleSubmit}
                disabled={submitting}
              >
                {submitting ? 'Setting up...' : 'Start My Journey'}
              </button>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .iman-onboarding {
          min-height: calc(100vh - 80px);
          background: var(--cream, #faf6f0);
          display: flex;
          justify-content: center;
          padding: 16px;
        }
        .ob-container {
          max-width: 520px;
          width: 100%;
          position: relative;
          padding-top: 40px;
        }
        .ob-progress {
          display: flex;
          justify-content: center;
          gap: 8px;
          margin-bottom: 24px;
        }
        .ob-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #d1d5db;
          transition: all 0.2s ease;
        }
        .ob-dot.active {
          background: var(--primary-teal, #0d9488);
          width: 24px;
          border-radius: 4px;
        }
        .ob-dot.done {
          background: var(--primary-teal, #0d9488);
        }
        .ob-skip {
          position: absolute;
          top: 8px;
          right: 0;
          background: none;
          border: none;
          color: #9ca3af;
          font-size: 0.85rem;
          cursor: pointer;
          padding: 4px 8px;
        }
        .ob-skip:hover {
          color: #6b7280;
        }
        .ob-step {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
        }
        .ob-medallion {
          width: 80px;
          height: 80px;
          border-radius: 50%;
          background: linear-gradient(135deg, #f0fdf4, #ecfdf5);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 20px;
          border: 2px solid var(--primary-teal, #0d9488);
          overflow: hidden;
        }
        .ob-medallion-icon {
          font-size: 1.8rem;
          color: var(--primary-teal, #0d9488);
          max-width: 100%;
        }
        .ob-title {
          font-size: 1.4rem;
          font-weight: 700;
          color: var(--deep-blue, #1e293b);
          margin: 0 0 12px 0;
        }
        .ob-subtitle {
          font-size: 0.85rem;
          color: #6b7280;
          margin: 0 0 16px 0;
          line-height: 1.5;
          max-width: 400px;
        }
        .ob-body {
          font-size: 0.9rem;
          color: #374151;
          line-height: 1.6;
          margin: 0 0 12px 0;
          max-width: 420px;
        }
        .ob-verse {
          font-size: 0.85rem;
          font-style: italic;
          color: var(--deep-blue, #1e293b);
          margin: 16px 0 24px 0;
          line-height: 1.5;
          max-width: 380px;
        }
        .ob-ref {
          display: block;
          font-size: 0.7rem;
          color: #6b7280;
          font-style: normal;
          margin-top: 6px;
        }
        .ob-nav {
          display: flex;
          gap: 12px;
          margin-top: 20px;
          width: 100%;
          max-width: 400px;
        }
        .ob-btn {
          flex: 1;
          padding: 12px 20px;
          border-radius: 10px;
          font-size: 0.9rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.15s ease;
          border: none;
        }
        .ob-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .ob-btn.primary {
          background: var(--primary-teal, #0d9488);
          color: white;
        }
        .ob-btn.primary:hover:not(:disabled) {
          background: #0f766e;
        }
        .ob-btn.primary.large {
          padding: 14px 24px;
          font-size: 1rem;
          font-weight: 600;
        }
        .ob-btn.secondary {
          background: white;
          color: #374151;
          border: 1px solid #e5e7eb;
        }
        .ob-struggle-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 10px;
          width: 100%;
          text-align: left;
          margin-bottom: 10px;
        }
        .ob-struggle-card {
          position: relative;
          display: flex;
          flex-direction: column;
          gap: 4px;
          padding: 12px;
          background: white;
          border: 1.5px solid #e5e7eb;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.15s ease;
          text-align: left;
        }
        .ob-struggle-card:hover:not(:disabled) {
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        }
        .ob-struggle-card.selected {
          background: #f0fdf4;
        }
        .ob-struggle-card.disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
        .ob-s-label {
          font-size: 0.8rem;
          font-weight: 600;
          color: #374151;
        }
        .ob-s-desc {
          font-size: 0.7rem;
          color: #9ca3af;
          line-height: 1.3;
        }
        .ob-s-check {
          position: absolute;
          top: 8px;
          right: 10px;
          font-size: 0.9rem;
          font-weight: 700;
        }
        .ob-struggle-count {
          font-size: 0.75rem;
          color: #6b7280;
          margin: 0;
        }
        .ob-cal-bar {
          width: 100%;
          max-width: 300px;
          height: 8px;
          background: rgba(0, 0, 0, 0.06);
          border-radius: 4px;
          overflow: hidden;
          margin: 20px 0 6px 0;
        }
        .ob-cal-fill {
          height: 100%;
          background: var(--primary-teal, #0d9488);
          border-radius: 4px;
          transition: width 0.3s ease;
        }
        .ob-cal-label {
          font-size: 0.8rem;
          color: #6b7280;
          margin: 0 0 20px 0;
        }
        .ob-tips {
          text-align: left;
          width: 100%;
          max-width: 400px;
          display: flex;
          flex-direction: column;
          gap: 10px;
          margin-bottom: 8px;
        }
        .ob-tip {
          font-size: 0.82rem;
          color: #4b5563;
          margin: 0;
          line-height: 1.4;
        }
        .ob-tip :global(.ob-bullet) {
          color: var(--primary-teal, #0d9488);
          font-weight: 700;
          margin-right: 4px;
        }
        .ob-error {
          color: #dc2626;
          font-size: 0.8rem;
          margin: 8px 0 0 0;
        }
      `}</style>
    </div>
  );
}
