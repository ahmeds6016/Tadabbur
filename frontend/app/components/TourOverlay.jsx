'use client';
import { useState, useEffect, useRef } from 'react';

const tourContent = {
  welcome: [
    {
      target: '.surah-verse-picker',
      title: 'Browse by Surah',
      content: 'Use the Surah picker to browse all 114 surahs. Select a surah, optionally choose specific verses, and get deep tafsir commentary instantly.',
      position: 'bottom'
    },
    {
      target: '.tafsir-form input',
      title: 'Search for Verses',
      content: 'Search for specific verses like "2:255" or "Al-Baqarah 255", verse ranges like "1:1-7", or analytical queries like "historical context of 17:23".',
      position: 'bottom'
    },
    {
      target: '.nav-link, .bottom-nav-item',
      title: 'Track Your Learning',
      content: 'Access your History to review past searches, Saved answers for bookmarked content, and Notes for your personal reflections.',
      position: 'top'
    },
    {
      target: '.persona-badge',
      title: 'Personalized Experience',
      content: 'Your learning profile shapes how explanations are presented. Click to change between different levels and focus areas.',
      position: 'left'
    }
  ],
  search: [
    {
      target: '.tafsir-form input',
      title: 'Search Formats',
      content: 'Try different formats:\n• Single verse: "2:255" or "Al-Baqarah 255"\n• Range: "2:1-5" or "Surah 36"\n• Analysis: "historical context of 17:23"',
      position: 'bottom'
    },
    {
      target: '.surah-verse-picker',
      title: 'Browse All Surahs',
      content: 'Use the picker to browse all 114 surahs with verse counts. Quick-select famous verses like Ayatul Kursi or Al-Fatihah.',
      position: 'bottom'
    },
    {
      target: '.export-section',
      title: 'Save and Share',
      content: 'Save important answers for later reference and generate shareable links to discuss with others.',
      position: 'top'
    }
  ],
  annotations: [
    {
      target: '.verse-text',
      title: 'Add Your Reflections',
      content: 'Select any text in the results to add your own notes and reflections. Your thoughts are automatically saved.',
      position: 'top'
    },
    {
      target: '.annotation-type-selector',
      title: 'Categorize Your Thoughts',
      content: 'Choose from 17 annotation types like Insight, Question, Application, and more to organize your reflections.',
      position: 'bottom'
    },
    {
      target: '.tag-input',
      title: 'Tag for Easy Discovery',
      content: 'Add tags to make your reflections searchable. Use topics, themes, or personal categories.',
      position: 'bottom'
    },
    {
      target: '.nav-link, .bottom-nav-item',
      title: 'Review Your Notes',
      content: 'Visit the Notes page to see all your reflections in one place, filtered by date, type, or tags.',
      position: 'top'
    }
  ]
};

export default function TourOverlay({
  isOpen,
  tourType = 'welcome',
  currentStep,
  totalSteps,
  onNext,
  onPrev,
  onSkip,
  onComplete
}) {
  const [targetElement, setTargetElement] = useState(null);
  const [spotlightStyle, setSpotlightStyle] = useState({});
  const [tooltipStyle, setTooltipStyle] = useState({});
  const overlayRef = useRef(null);

  const steps = tourContent[tourType] || tourContent.welcome;
  const currentTourStep = steps[currentStep] || steps[0];
  const actualTotalSteps = totalSteps || steps.length;

  useEffect(() => {
    if (!isOpen || !currentTourStep) return;

    let retryCount = 0;
    const maxRetries = 4; // Maximum 2 seconds of retrying

    const findAndHighlight = () => {
      const target = document.querySelector(currentTourStep.target);
      if (!target) {
        // If target not found, try again after a short delay (with max retries)
        if (retryCount < maxRetries) {
          retryCount++;
          setTimeout(findAndHighlight, 500);
        } else {
          console.warn(`Tour target not found after ${maxRetries} attempts: ${currentTourStep.target}`);
          // Skip to next step or close tour
          if (currentStep < actualTotalSteps - 1) {
            onNext();
          } else {
            onSkip();
          }
        }
        return;
      }

      setTargetElement(target);
      const rect = target.getBoundingClientRect();

      // Calculate spotlight position
      setSpotlightStyle({
        position: 'fixed',
        top: rect.top - 8,
        left: rect.left - 8,
        width: rect.width + 16,
        height: rect.height + 16,
        borderRadius: '12px',
        zIndex: 12001,
        boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.7)',
        pointerEvents: 'none',
        transition: 'all 0.3s ease'
      });

      // Calculate tooltip position
      let tooltipTop, tooltipLeft;
      const isMobile = window.innerWidth <= 768;
      const tooltipWidth = isMobile ? window.innerWidth - 20 : 400;
      const tooltipHeight = 250; // Approximate, accounting for content
      const padding = 20;

      if (isMobile) {
        // On mobile, center the tooltip vertically for better visibility
        // Position it in the middle of the screen, not at bottom
        tooltipTop = Math.max(
          padding,
          Math.min(
            window.innerHeight / 2 - tooltipHeight / 2,
            window.innerHeight - tooltipHeight - padding
          )
        );
        tooltipLeft = 10; // Fixed left margin on mobile
      } else {
        // Desktop positioning
        switch (currentTourStep.position) {
          case 'bottom':
            tooltipTop = rect.bottom + padding;
            tooltipLeft = rect.left + (rect.width / 2) - (tooltipWidth / 2);
            break;
          case 'top':
            tooltipTop = rect.top - tooltipHeight - padding;
            tooltipLeft = rect.left + (rect.width / 2) - (tooltipWidth / 2);
            break;
          case 'left':
            tooltipTop = rect.top + (rect.height / 2) - (tooltipHeight / 2);
            tooltipLeft = rect.left - tooltipWidth - padding;
            break;
          case 'right':
            tooltipTop = rect.top + (rect.height / 2) - (tooltipHeight / 2);
            tooltipLeft = rect.right + padding;
            break;
          default:
            tooltipTop = rect.bottom + padding;
            tooltipLeft = rect.left;
        }

        // Ensure tooltip stays within viewport
        tooltipLeft = Math.max(10, Math.min(tooltipLeft, window.innerWidth - tooltipWidth - 10));
        tooltipTop = Math.max(10, Math.min(tooltipTop, window.innerHeight - tooltipHeight - 10));
      }

      setTooltipStyle({
        position: 'fixed',
        top: tooltipTop,
        left: tooltipLeft,
        zIndex: 12002,
        maxWidth: tooltipWidth,
        animation: 'slideIn 0.3s ease'
      });

      // Scroll target into view if needed
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    };

    findAndHighlight();
  }, [isOpen, currentStep, currentTourStep]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'Escape':
          onSkip();
          break;
        case 'ArrowRight':
          if (currentStep < actualTotalSteps - 1) onNext();
          break;
        case 'ArrowLeft':
          if (currentStep > 0) onPrev();
          break;
        case 'Enter':
          if (currentStep === actualTotalSteps - 1) {
            onComplete();
          } else {
            onNext();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, currentStep, actualTotalSteps, onNext, onPrev, onSkip, onComplete]);

  if (!isOpen) return null;

  return (
    <div className="tour-overlay" ref={overlayRef}>
      {/* Dark overlay */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          zIndex: 12000,
          animation: 'fadeIn 0.3s ease'
        }}
        onClick={onSkip}
      />

      {/* Spotlight */}
      {targetElement && <div style={spotlightStyle} />}

      {/* Tooltip */}
      <div className="tour-tooltip" style={tooltipStyle}>
        <div className="tour-header">
          <h3>{currentTourStep.title}</h3>
          <button
            onClick={onSkip}
            className="tour-close"
            aria-label="Skip tour"
          >
            ×
          </button>
        </div>

        <div className="tour-content">
          <p>{currentTourStep.content}</p>
        </div>

        <div className="tour-footer">
          <div className="tour-progress">
            {[...Array(actualTotalSteps)].map((_, i) => (
              <span
                key={i}
                className={`progress-dot ${i === currentStep ? 'active' : ''} ${i < currentStep ? 'completed' : ''}`}
              />
            ))}
          </div>

          <div className="tour-actions">
            {currentStep > 0 && (
              <button onClick={onPrev} className="tour-btn secondary">
                Previous
              </button>
            )}

            {currentStep < actualTotalSteps - 1 ? (
              <button onClick={onNext} className="tour-btn primary">
                Next →
              </button>
            ) : (
              <button onClick={onComplete} className="tour-btn primary">
                Get Started!
              </button>
            )}
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .tour-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          z-index: 12000;
        }

        .tour-tooltip {
          background: white;
          border-radius: 16px;
          padding: 24px;
          box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
          border: 2px solid var(--gold);
        }

        .tour-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .tour-header h3 {
          margin: 0;
          color: var(--primary-teal);
          font-size: 1.3rem;
          font-weight: 700;
        }

        .tour-close {
          background: transparent;
          border: none;
          font-size: 1.5rem;
          cursor: pointer;
          color: #999;
          width: 30px;
          height: 30px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
        }

        .tour-close:hover {
          background: var(--cream);
          color: var(--deep-blue);
        }

        .tour-content {
          margin-bottom: 24px;
        }

        .tour-content p {
          margin: 0;
          color: var(--deep-blue);
          line-height: 1.6;
          white-space: pre-line;
        }

        .tour-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .tour-progress {
          display: flex;
          gap: 8px;
        }

        .progress-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #ddd;
          transition: all 0.3s ease;
        }

        .progress-dot.active {
          background: var(--gold);
          width: 24px;
          border-radius: 4px;
        }

        .progress-dot.completed {
          background: var(--primary-teal);
        }

        .tour-actions {
          display: flex;
          gap: 12px;
        }

        .tour-btn {
          padding: 8px 20px;
          border-radius: 8px;
          border: none;
          font-weight: 600;
          font-size: 0.9rem;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .tour-btn.primary {
          background: linear-gradient(135deg, var(--primary-teal), var(--gold));
          color: white;
        }

        .tour-btn.primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }

        .tour-btn.secondary {
          background: var(--cream);
          color: var(--deep-blue);
          border: 1px solid var(--border-light);
        }

        .tour-btn.secondary:hover {
          background: white;
        }

        /* Mobile adjustments */
        @media (max-width: 768px) {
          .tour-tooltip {
            max-width: calc(100vw - 20px) !important;
            left: 10px !important;
            right: 10px !important;
            width: auto !important;
            padding: 20px 16px !important;
            /* Ensure it's positioned in the middle of screen for visibility */
            transform: none !important;
          }

          .tour-header h3 {
            font-size: 1.1rem;
          }

          .tour-content p {
            font-size: 0.9rem;
            line-height: 1.5;
          }

          .tour-btn {
            padding: 12px 16px;
            font-size: 0.95rem;
            /* Larger touch targets for mobile */
            min-width: 80px;
          }

          .tour-actions {
            gap: 8px;
            width: 100%;
          }

          .tour-footer {
            flex-direction: column;
            gap: 16px;
            align-items: stretch;
          }

          .tour-progress {
            justify-content: center;
            order: 2;
          }

          .tour-actions {
            order: 1;
            justify-content: space-between;
          }
        }
      `}</style>
    </div>
  );
}
