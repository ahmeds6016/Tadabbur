'use client';
import { useState } from 'react';

const milestones = [
  { id: 'hasSeenWelcome', label: 'Welcome Tour', number: 1 },
  { id: 'hasSearched', label: 'First Search', number: 2 },
  { id: 'hasUsedAnnotations', label: 'First Reflection', number: 3 },
  { id: 'hasViewedSaved', label: 'Saved an Answer', number: 4 },
  { id: 'hasViewedHistory', label: 'Viewed History', number: 5 },
  { id: 'hasSharedContent', label: 'Shared Content', number: 6 }
];

export default function OnboardingProgress({ onboardingState, onResumeTour, onHide }) {
  // Start collapsed by default - less intrusive
  const [isExpanded, setIsExpanded] = useState(() => {
    if (typeof window !== 'undefined') {
      // Start collapsed unless explicitly expanded
      return localStorage.getItem('onboarding_expanded') === 'true';
    }
    return false;
  });
  const [showCelebration, setShowCelebration] = useState(false);

  const completedCount = milestones.filter(m => onboardingState[m.id]).length;
  const progressPercentage = (completedCount / milestones.length) * 100;
  const isComplete = progressPercentage === 100;

  const handleComplete = () => {
    setShowCelebration(true);
    setTimeout(() => {
      onHide();
    }, 2000);
  };

  if (isComplete && !showCelebration) {
    handleComplete();
  }

  if (onboardingState.completedAt) return null;

  const toggleExpanded = () => {
    const nextState = !isExpanded;
    setIsExpanded(nextState);
    localStorage.setItem('onboarding_expanded', nextState.toString());
  };

  return (
    <div className={`onboarding-progress ${isExpanded ? 'expanded' : 'collapsed'}`}>
      {/* Collapsed: Simple progress pill */}
      {!isExpanded && (
        <button
          className="progress-pill"
          onClick={toggleExpanded}
          aria-label="Show onboarding progress"
        >
          <span className="pill-text">Getting Started</span>
          <span className="pill-count">{completedCount}/{milestones.length}</span>
        </button>
      )}

      {/* Expanded: Compact checklist */}
      {isExpanded && (
        <div className="progress-panel">
          <div className="panel-header">
            <span className="panel-title">Getting Started</span>
            <button
              className="close-btn"
              onClick={toggleExpanded}
              aria-label="Minimize"
            >
              x
            </button>
          </div>

          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>

          <div className="milestones-list">
            {milestones.map((milestone) => {
              const isCompleted = onboardingState[milestone.id];
              return (
                <div
                  key={milestone.id}
                  className={`milestone-item ${isCompleted ? 'completed' : ''}`}
                >
                  <span className="milestone-check">
                    {isCompleted ? 'Done' : milestone.number}
                  </span>
                  <span className="milestone-label">{milestone.label}</span>
                </div>
              );
            })}
          </div>

          <div className="panel-footer">
            <button className="skip-btn" onClick={onHide}>
              Dismiss
            </button>
          </div>

          {showCelebration && (
            <div className="celebration">
              <span>Complete!</span>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .onboarding-progress {
          position: fixed;
          bottom: 100px;
          right: 16px;
          z-index: 900;
        }

        /* Collapsed pill */
        .progress-pill {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          background: white;
          border: 1px solid var(--border-light, #e5e7eb);
          border-radius: 20px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          cursor: pointer;
          font-size: 0.8rem;
          transition: all 0.2s ease;
        }

        .progress-pill:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          transform: translateY(-1px);
        }

        .pill-text {
          color: var(--deep-blue, #1e293b);
          font-weight: 500;
        }

        .pill-count {
          background: var(--primary-teal, #0d9488);
          color: white;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 0.7rem;
          font-weight: 600;
        }

        /* Expanded panel */
        .progress-panel {
          width: 240px;
          background: white;
          border: 1px solid var(--border-light, #e5e7eb);
          border-radius: 12px;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
          overflow: hidden;
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px;
          background: var(--cream, #faf6f0);
          border-bottom: 1px solid var(--border-light, #e5e7eb);
        }

        .panel-title {
          font-weight: 600;
          font-size: 0.85rem;
          color: var(--deep-blue, #1e293b);
        }

        .close-btn {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          border: none;
          background: transparent;
          color: #999;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.9rem;
        }

        .close-btn:hover {
          background: var(--border-light, #e5e7eb);
        }

        .progress-bar {
          height: 4px;
          background: var(--border-light, #e5e7eb);
        }

        .progress-fill {
          height: 100%;
          background: var(--primary-teal, #0d9488);
          transition: width 0.3s ease;
        }

        .milestones-list {
          padding: 8px;
          max-height: 200px;
          overflow-y: auto;
        }

        .milestone-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 8px;
          border-radius: 6px;
          font-size: 0.8rem;
        }

        .milestone-item.completed {
          opacity: 0.6;
        }

        .milestone-check {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: var(--cream, #faf6f0);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.65rem;
          font-weight: 600;
          flex-shrink: 0;
        }

        .milestone-item.completed .milestone-check {
          background: var(--primary-teal, #0d9488);
          color: white;
        }

        .milestone-label {
          color: var(--deep-blue, #1e293b);
        }

        .milestone-item.completed .milestone-label {
          text-decoration: line-through;
          color: #999;
        }

        .panel-footer {
          padding: 8px 12px;
          border-top: 1px solid var(--border-light, #e5e7eb);
        }

        .skip-btn {
          width: 100%;
          padding: 6px;
          background: transparent;
          border: 1px solid var(--border-light, #e5e7eb);
          border-radius: 6px;
          font-size: 0.75rem;
          color: #666;
          cursor: pointer;
        }

        .skip-btn:hover {
          background: var(--cream, #faf6f0);
        }

        .celebration {
          position: absolute;
          inset: 0;
          background: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          color: var(--primary-teal, #0d9488);
          border-radius: 12px;
        }

        /* Mobile: Position above bottom nav */
        @media (max-width: 768px) {
          .onboarding-progress {
            bottom: 80px;
            right: 12px;
          }
        }

        /* PWA standalone mode */
        @media (display-mode: standalone) {
          .onboarding-progress {
            bottom: 100px;
          }
        }

        /* Very small screens: hide completely */
        @media (max-width: 360px) {
          .onboarding-progress {
            display: none;
          }
        }
      `}</style>
    </div>
  );
}
