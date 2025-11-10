'use client';
import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * iOS-style Text Highlighter Component
 * Mimics iOS 18 text selection and annotation behavior
 *
 * Key behaviors:
 * 1. Callout appears ABOVE selection immediately after text selected
 * 2. Menu stays visible when moving toward it (no premature disappearing)
 * 3. Tapping button triggers annotation instantly
 * 4. Deselecting text or tapping outside dismisses menu
 */
export default function TextHighlighter({ children, onHighlight, enabled = true }) {
  const [selection, setSelection] = useState(null);
  const [menuPosition, setMenuPosition] = useState(null);
  const buttonRef = useRef(null);
  const preventClearRef = useRef(false);

  // Handle text selection changes
  const handleSelectionChange = useCallback(() => {
    if (!enabled) return;

    // Don't clear if we're about to click the button
    if (preventClearRef.current) return;

    const selectedText = window.getSelection()?.toString().trim();

    if (selectedText && selectedText.length > 0) {
      const range = window.getSelection()?.getRangeAt(0);
      const rect = range?.getBoundingClientRect();

      if (rect && rect.width > 0 && rect.height > 0) {
        setSelection(selectedText);

        // Position callout ABOVE selection (iOS style)
        // Center horizontally, 8px above selection
        setMenuPosition({
          x: rect.left + (rect.width / 2),
          y: rect.top - 8,
        });
      }
    } else {
      // Clear selection only if not prevented
      if (!preventClearRef.current) {
        setSelection(null);
        setMenuPosition(null);
      }
    }
  }, [enabled]);

  // iOS-style: Use selectionchange for real-time updates
  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('selectionchange', handleSelectionChange);

    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange);
    };
  }, [enabled, handleSelectionChange]);

  // Handle button click
  const handleButtonClick = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();

    if (selection && onHighlight) {
      // Trigger the highlight callback
      onHighlight(selection);

      // Clear the selection UI
      setSelection(null);
      setMenuPosition(null);

      // Clear browser selection
      window.getSelection()?.removeAllRanges();
    }
  }, [selection, onHighlight]);

  // Handle clicks outside - iOS dismisses on tap outside
  useEffect(() => {
    if (!selection) return;

    const handleClickOutside = (e) => {
      // Don't dismiss if clicking the button itself
      if (buttonRef.current && buttonRef.current.contains(e.target)) {
        return;
      }

      // Dismiss menu
      setSelection(null);
      setMenuPosition(null);
    };

    // Use mousedown/touchstart to catch clicks before selection changes
    document.addEventListener('mousedown', handleClickOutside, true);
    document.addEventListener('touchstart', handleClickOutside, true);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside, true);
      document.removeEventListener('touchstart', handleClickOutside, true);
    };
  }, [selection]);

  // Prevent menu from disappearing when mouse enters it
  const handleButtonMouseEnter = useCallback(() => {
    preventClearRef.current = true;
  }, []);

  const handleButtonMouseLeave = useCallback(() => {
    preventClearRef.current = false;
  }, []);

  return (
    <>
      {children}

      {/* iOS-style callout menu */}
      {selection && menuPosition && (
        <div
          ref={buttonRef}
          onMouseEnter={handleButtonMouseEnter}
          onMouseLeave={handleButtonMouseLeave}
          style={{
            position: 'fixed',
            left: `${menuPosition.x}px`,
            top: `${menuPosition.y}px`,
            transform: 'translate(-50%, -100%)',
            zIndex: 10000,
            pointerEvents: 'auto',
            animation: 'fadeInScale 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        >
          <button
            onClick={handleButtonClick}
            onTouchEnd={handleButtonClick}
            style={{
              // iOS-inspired styling
              padding: '10px 18px',
              background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
              border: 'none',
              borderRadius: '12px',
              color: 'white',
              fontSize: '0.9rem',
              fontWeight: '600',
              cursor: 'pointer',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2), 0 2px 8px rgba(245, 158, 11, 0.4)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
              userSelect: 'none',
              WebkitUserSelect: 'none',
              WebkitTapHighlightColor: 'transparent',
              backdropFilter: 'blur(10px)',
            }}
            onMouseDown={(e) => {
              // Prevent text selection from being cleared before click
              e.preventDefault();
            }}
            onTouchStart={(e) => {
              // Prevent text selection from being cleared before touch
              preventClearRef.current = true;
            }}
          >
            <span style={{ fontSize: '1.1rem' }}>✨</span>
            <span>Reflect</span>
          </button>
        </div>
      )}

      <style jsx>{`
        @keyframes fadeInScale {
          from {
            opacity: 0;
            transform: translate(-50%, -100%) scale(0.92);
          }
          to {
            opacity: 1;
            transform: translate(-50%, -100%) scale(1);
          }
        }
      `}</style>
    </>
  );
}
