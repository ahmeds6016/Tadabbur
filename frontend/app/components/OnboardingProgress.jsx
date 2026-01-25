'use client';
import { useState } from 'react';

const milestones = [
  { id: 'hasSeenWelcome', label: 'Welcome Tour', icon: '👋' },
  { id: 'hasSearched', label: 'First Search', icon: '🔍' },
  { id: 'hasUsedAnnotations', label: 'First Reflection', icon: '📝' },
  { id: 'hasViewedSaved', label: 'Saved an Answer', icon: '⭐' },
  { id: 'hasViewedHistory', label: 'Viewed History', icon: '📜' },
  { id: 'hasSharedContent', label: 'Shared Content', icon: '🔗' }
];

export default function OnboardingProgress({ onboardingState, onResumeTour, onHide }) {
  const [isExpanded, setIsExpanded] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('onboarding_minimized') !== 'true';
    }
    return true;
  });
  const [showCelebration, setShowCelebration] = useState(false);

  const completedCount = milestones.filter(m => onboardingState[m.id]).length;
  const progressPercentage = (completedCount / milestones.length) * 100;
  const isComplete = progressPercentage === 100;

  const handleComplete = () => {
    setShowCelebration(true);
    setTimeout(() => {
      onHide();
    }, 3000);
  };

  if (isComplete && !showCelebration) {
    handleComplete();
  }

  if (onboardingState.completedAt) return null;

  return (
    <>
      {/* Backdrop when expanded for better visibility */}
      {isExpanded && (
        <div
          className="onboarding-backdrop"
          onClick={() => {
            setIsExpanded(false);
            localStorage.setItem('onboarding_minimized', 'true');
          }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            zIndex: 9997,
            animation: 'fadeIn 0.3s ease'
          }}
        />
      )}

      <div className={`onboarding-progress ${isExpanded ? 'expanded' : 'collapsed'}`}>
        <div
          className="progress-header"
          onClick={() => {
            const nextState = !isExpanded;
            setIsExpanded(nextState);
            localStorage.setItem('onboarding_minimized', (!nextState).toString());
          }}
        >
          <div className="progress-title">
            <span className="progress-icon">🎯</span>
            <span className="progress-text">Getting Started</span>
            <span className="progress-count">{completedCount}/{milestones.length}</span>
          </div>
          <button className="expand-btn" aria-label={isExpanded ? 'Collapse' : 'Expand'}>
            {isExpanded ? '−' : '+'}
          </button>
        </div>

      {isExpanded && (
        <div className="progress-content">
          <div className="progress-bar-container">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
            <span className="progress-percentage">{Math.round(progressPercentage)}%</span>
          </div>

          <div className="milestones-list">
            {milestones.map((milestone) => {
              const isCompleted = onboardingState[milestone.id];
              const tourType = milestone.id.replace('has', '').toLowerCase().replace('used', '');

              return (
                <div
                  key={milestone.id}
                  className={`milestone-item ${isCompleted ? 'completed' : ''}`}
                >
                  <div className="milestone-icon">
                    {isCompleted ? '✓' : milestone.icon}
                  </div>
                  <div className="milestone-content">
                    <span className="milestone-label">{milestone.label}</span>
                    {!isCompleted && onResumeTour && (
                      <button
                        className="milestone-action"
                        onClick={() => onResumeTour(tourType)}
                      >
                        Start
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {!isComplete && (
            <div className="progress-footer">
              <button
                className="resume-tour-btn"
                onClick={() => onResumeTour('welcome')}
              >
                Resume Tour →
              </button>
              <button
                className="skip-btn"
                onClick={onHide}
              >
                Skip for now
              </button>
            </div>
          )}

          {showCelebration && (
            <div className="celebration">
              <div className="celebration-content">
                <span className="celebration-emoji">🎉</span>
                <h3>Congratulations!</h3>
                <p>You've completed the onboarding!</p>
              </div>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .onboarding-progress {
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 400px;
          max-width: 90vw;
          background: white;
          border: 3px solid var(--gold);
          border-radius: 20px;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
          z-index: 9998;
          transition: all 0.3s ease;
          animation: slideInCenter 0.5s ease;
        }

        @keyframes slideInCenter {
          from {
            transform: translate(-50%, -50%) scale(0.8);
            opacity: 0;
          }
          to {
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
          }
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .onboarding-progress.collapsed {
          width: auto;
          min-width: 200px;
        }

        .progress-header {
          padding: 16px;
          background: linear-gradient(135deg, var(--cream) 0%, white 100%);
          border-bottom: 1px solid var(--border-light);
          cursor: pointer;
          display: flex;
          justify-content: space-between;
          align-items: center;
          border-radius: 16px 16px 0 0;
        }

        .progress-title {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .progress-icon {
          font-size: 1.2rem;
        }

        .progress-text {
          font-weight: 600;
          color: var(--deep-blue);
        }

        .progress-count {
          padding: 2px 8px;
          background: var(--primary-teal);
          color: white;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 600;
        }

        .expand-btn {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          border: 1px solid var(--border-light);
          background: white;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
        }

        .expand-btn:hover {
          background: var(--cream);
        }

        .progress-content {
          padding: 16px;
          animation: expand 0.3s ease;
        }

        @keyframes expand {
          from {
            opacity: 0;
            max-height: 0;
          }
          to {
            opacity: 1;
            max-height: 500px;
          }
        }

        .progress-bar-container {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
        }

        .progress-bar {
          flex: 1;
          height: 8px;
          background: var(--cream);
          border-radius: 4px;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, var(--primary-teal) 0%, var(--gold) 100%);
          transition: width 0.3s ease;
          border-radius: 4px;
        }

        .progress-percentage {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--primary-teal);
        }

        .milestones-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 16px;
        }

        .milestone-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 12px;
          border-radius: 8px;
          transition: all 0.2s ease;
        }

        .milestone-item:hover {
          background: var(--cream);
        }

        .milestone-item.completed {
          opacity: 0.7;
        }

        .milestone-icon {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: var(--cream);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.9rem;
          transition: all 0.2s ease;
        }

        .milestone-item.completed .milestone-icon {
          background: var(--primary-teal);
          color: white;
          font-weight: 600;
        }

        .milestone-content {
          flex: 1;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .milestone-label {
          font-size: 0.9rem;
          color: var(--deep-blue);
        }

        .milestone-item.completed .milestone-label {
          text-decoration: line-through;
          color: #999;
        }

        .milestone-action {
          padding: 4px 12px;
          background: var(--primary-teal);
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 0.75rem;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .milestone-action:hover {
          background: var(--gold);
        }

        .progress-footer {
          display: flex;
          gap: 8px;
          padding-top: 12px;
          border-top: 1px solid var(--border-light);
        }

        .resume-tour-btn {
          flex: 1;
          padding: 8px 16px;
          background: linear-gradient(135deg, var(--primary-teal) 0%, var(--gold) 100%);
          color: white;
          border: none;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .resume-tour-btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }

        .skip-btn {
          padding: 8px 16px;
          background: transparent;
          color: #999;
          border: 1px solid var(--border-light);
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .skip-btn:hover {
          background: var(--cream);
        }

        .celebration {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(255, 255, 255, 0.98);
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 16px;
          animation: celebrateIn 0.5s ease;
        }

        @keyframes celebrateIn {
          from {
            opacity: 0;
            transform: scale(0.8);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        .celebration-content {
          text-align: center;
        }

        .celebration-emoji {
          font-size: 3rem;
          animation: bounce 1s ease infinite;
        }

        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }

        .celebration h3 {
          color: var(--primary-teal);
          margin: 12px 0 8px;
        }

        .celebration p {
          color: #666;
          margin: 0;
        }

        /* Mobile adjustments */
        @media (max-width: 768px) {
          .onboarding-progress {
            right: 12px;
            bottom: 90px;
            left: 12px;
            width: auto;
          }
        }

        /* Hide on very small screens */
        @media (max-width: 400px) {
          .onboarding-progress {
            display: none;
          }
        }
      `}</style>
    </div>
    </>
  );
}
