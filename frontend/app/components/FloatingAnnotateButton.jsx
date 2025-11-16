'use client';
import { useState, useEffect, useRef } from 'react';

export default function FloatingAnnotateButton({
  selectedText,
  onAnnotate,
  onDismiss
}) {
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const [isVisible, setIsVisible] = useState(false);
  const buttonRef = useRef(null);

  useEffect(() => {
    if (!selectedText || selectedText.length < 3) {
      setIsVisible(false);
      return;
    }

    // Get selection position
    const selection = window.getSelection();
    if (!selection.rangeCount) {
      setIsVisible(false);
      return;
    }

    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();

    // Calculate button position (above the selection)
    const buttonWidth = 120; // Approximate button width
    const buttonHeight = 36; // Approximate button height
    const padding = 8;

    let top = rect.top + window.scrollY - buttonHeight - padding;
    let left = rect.left + window.scrollX + (rect.width / 2) - (buttonWidth / 2);

    // Ensure button stays within viewport
    left = Math.max(padding, Math.min(left, window.innerWidth - buttonWidth - padding));

    // If not enough space above, show below
    if (top < padding) {
      top = rect.bottom + window.scrollY + padding;
    }

    setPosition({ top, left });
    setIsVisible(true);
  }, [selectedText]);

  const handleClick = () => {
    onAnnotate();
    setIsVisible(false);
  };

  const handleDismiss = () => {
    if (onDismiss) {
      onDismiss();
    }
    setIsVisible(false);
    // Clear selection
    window.getSelection()?.removeAllRanges();
  };

  if (!isVisible || !selectedText) return null;

  return (
    <div
      ref={buttonRef}
      className="floating-annotate-button"
      style={{
        position: 'absolute',
        top: `${position.top}px`,
        left: `${position.left}px`,
        zIndex: 1000,
        animation: 'fadeInScale 0.2s ease'
      }}
    >
      <button
        onClick={handleClick}
        className="annotate-btn"
        title="Add a reflection on this text"
      >
        📝 Annotate
      </button>
      <button
        onClick={handleDismiss}
        className="dismiss-btn"
        title="Dismiss"
        aria-label="Dismiss annotation option"
      >
        ×
      </button>

      <style jsx>{`
        @keyframes fadeInScale {
          from {
            opacity: 0;
            transform: scale(0.9) translateY(5px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }

        .floating-annotate-button {
          display: flex;
          gap: 4px;
          align-items: center;
          background: white;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          border: 2px solid var(--primary-teal);
          padding: 4px;
        }

        .annotate-btn {
          padding: 6px 12px;
          background: linear-gradient(135deg, var(--primary-teal) 0%, var(--gold) 100%);
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 0.9rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .annotate-btn:hover {
          transform: scale(1.05);
          box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
        }

        .dismiss-btn {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          border: 1px solid #ddd;
          background: white;
          color: #999;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.2rem;
          transition: all 0.2s ease;
        }

        .dismiss-btn:hover {
          background: #f5f5f5;
          color: #333;
        }

        /* Mobile adjustments */
        @media (max-width: 768px) {
          .floating-annotate-button {
            position: fixed;
            top: auto !important;
            bottom: 100px !important;
            left: 50% !important;
            transform: translateX(-50%);
            z-index: 999;
          }
        }
      `}</style>
    </div>
  );
}