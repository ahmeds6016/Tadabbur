'use client';
import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * iOS 18-Style Text Highlighting System - Built from Ground Zero
 *
 * Core Design Principles:
 * 1. Instant visual feedback - no delays
 * 2. Bulletproof scroll-lock during interaction
 * 3. Native-feeling touch interactions
 * 4. Zero race conditions or timing bugs
 * 5. Clean, minimal state management
 *
 * Key Behaviors (iOS 18):
 * - Select text → callout appears instantly above selection
 * - Tap callout button → immediate action, clean dismissal
 * - Tap outside → dismisses cleanly
 * - Page scroll completely locked when callout visible
 * - Smooth, native-feeling animations
 */

export default function iOS18TextHighlighter({ children, onHighlight, enabled = true }) {
  // ═══════════════════════════════════════════════════════════════
  // STATE MANAGEMENT - Keep it minimal and clean
  // ═══════════════════════════════════════════════════════════════

  const [selectionState, setSelectionState] = useState(null);
  // selectionState = { text: string, rect: DOMRect, range: Range } | null

  const calloutRef = useRef(null);
  const isInteractingRef = useRef(false);
  const scrollPositionRef = useRef(0);

  // ═══════════════════════════════════════════════════════════════
  // SCROLL LOCK SYSTEM - iOS 18 Style (Zero Movement)
  // ═══════════════════════════════════════════════════════════════

  useEffect(() => {
    if (!selectionState) return;

    // Capture current scroll position
    const scrollY = window.pageYOffset;
    const scrollX = window.pageXOffset;
    scrollPositionRef.current = { x: scrollX, y: scrollY };

    // Store original styles
    const body = document.body;
    const html = document.documentElement;

    const originalBodyOverflow = body.style.overflow;
    const originalBodyPosition = body.style.position;
    const originalBodyTop = body.style.top;
    const originalBodyLeft = body.style.left;
    const originalBodyWidth = body.style.width;
    const originalHtmlOverflow = html.style.overflow;

    // Calculate scrollbar width to prevent layout shift
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;

    // Apply iOS-style freeze
    html.style.overflow = 'hidden';
    body.style.overflow = 'hidden';
    body.style.position = 'fixed';
    body.style.top = `-${scrollY}px`;
    body.style.left = `-${scrollX}px`;
    body.style.width = `calc(100% - ${scrollbarWidth}px)`;

    // Cleanup: restore everything
    return () => {
      body.style.overflow = originalBodyOverflow;
      body.style.position = originalBodyPosition;
      body.style.top = originalBodyTop;
      body.style.left = originalBodyLeft;
      body.style.width = originalBodyWidth;
      html.style.overflow = originalHtmlOverflow;

      // Restore scroll position
      window.scrollTo(scrollPositionRef.current.x, scrollPositionRef.current.y);
    };
  }, [selectionState]);

  // ═══════════════════════════════════════════════════════════════
  // SELECTION DETECTION - Native browser behavior
  // ═══════════════════════════════════════════════════════════════

  const handleSelectionChange = useCallback(() => {
    if (!enabled || isInteractingRef.current) return;

    const selection = window.getSelection();
    const selectedText = selection?.toString().trim();

    // User selected some text
    if (selectedText && selectedText.length > 0) {
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();

      // Valid selection with visible bounds
      if (rect.width > 0 && rect.height > 0) {
        setSelectionState({
          text: selectedText,
          rect: rect,
          range: range.cloneRange() // Clone to preserve
        });
      }
    }
    // No selection - clear state
    else if (!isInteractingRef.current) {
      setSelectionState(null);
    }
  }, [enabled]);

  // Listen to selection changes
  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('selectionchange', handleSelectionChange);

    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange);
    };
  }, [enabled, handleSelectionChange]);

  // ═══════════════════════════════════════════════════════════════
  // CALLOUT INTERACTION HANDLERS
  // ═══════════════════════════════════════════════════════════════

  const handleCalloutClick = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();

    if (!selectionState) return;

    isInteractingRef.current = true;

    // Trigger the highlight callback
    if (onHighlight) {
      onHighlight(selectionState.text);
    }

    // Clear selection and dismiss
    window.getSelection()?.removeAllRanges();
    setSelectionState(null);

    // Reset interaction flag after a short delay
    setTimeout(() => {
      isInteractingRef.current = false;
    }, 100);
  }, [selectionState, onHighlight]);

  const handleDismiss = useCallback((e) => {
    // Don't dismiss if clicking the callout itself
    if (calloutRef.current && calloutRef.current.contains(e.target)) {
      return;
    }

    // Clear selection
    window.getSelection()?.removeAllRanges();
    setSelectionState(null);
  }, []);

  // Click/touch outside handler
  useEffect(() => {
    if (!selectionState) return;

    // Use capture phase to catch events before they reach children
    document.addEventListener('mousedown', handleDismiss, true);
    document.addEventListener('touchstart', handleDismiss, true);

    return () => {
      document.removeEventListener('mousedown', handleDismiss, true);
      document.removeEventListener('touchstart', handleDismiss, true);
    };
  }, [selectionState, handleDismiss]);

  // ═══════════════════════════════════════════════════════════════
  // CALLOUT POSITIONING - iOS 18 Style (Above selection)
  // ═══════════════════════════════════════════════════════════════

  const getCalloutPosition = () => {
    if (!selectionState) return null;

    const { rect } = selectionState;

    // Position callout above selection, centered horizontally
    // Account for scroll position since we're using fixed positioning
    const scrollY = window.pageYOffset;
    const scrollX = window.pageXOffset;

    return {
      left: rect.left + scrollX + (rect.width / 2),
      top: rect.top + scrollY - 8, // 8px gap above selection
    };
  };

  const calloutPosition = getCalloutPosition();

  // ═══════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════

  return (
    <>
      {children}

      {/* iOS 18-Style Callout Menu */}
      {selectionState && calloutPosition && (
        <div
          ref={calloutRef}
          style={{
            position: 'absolute',
            left: `${calloutPosition.left}px`,
            top: `${calloutPosition.top}px`,
            transform: 'translate(-50%, -100%)',
            zIndex: 999999,
            pointerEvents: 'auto',
            animation: 'ios-callout-appear 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
          }}
          onMouseDown={(e) => e.preventDefault()} // Prevent selection from being cleared
          onTouchStart={(e) => {
            e.preventDefault();
            isInteractingRef.current = true;
          }}
        >
          <button
            onClick={handleCalloutClick}
            onTouchEnd={(e) => {
              e.preventDefault();
              handleCalloutClick(e);
            }}
            style={{
              // iOS 18-inspired design
              padding: '12px 24px',
              background: 'linear-gradient(180deg, #0A84FF 0%, #0066CC 100%)',
              border: 'none',
              borderRadius: '14px',
              color: 'white',
              fontSize: '16px',
              fontWeight: '600',
              cursor: 'pointer',
              boxShadow: '0 4px 20px rgba(10, 132, 255, 0.4), 0 2px 8px rgba(0, 0, 0, 0.15)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              whiteSpace: 'nowrap',
              userSelect: 'none',
              WebkitUserSelect: 'none',
              WebkitTapHighlightColor: 'transparent',
              transition: 'all 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
              backdropFilter: 'blur(20px) saturate(180%)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'scale(1.05)';
              e.currentTarget.style.boxShadow = '0 6px 24px rgba(10, 132, 255, 0.5), 0 3px 12px rgba(0, 0, 0, 0.2)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.boxShadow = '0 4px 20px rgba(10, 132, 255, 0.4), 0 2px 8px rgba(0, 0, 0, 0.15)';
            }}
          >
            <span style={{ fontSize: '18px' }}>✨</span>
            <span>Reflect</span>
          </button>

          {/* iOS-style arrow/tail pointing to selection */}
          <div
            style={{
              position: 'absolute',
              bottom: '-6px',
              left: '50%',
              transform: 'translateX(-50%)',
              width: 0,
              height: 0,
              borderLeft: '8px solid transparent',
              borderRight: '8px solid transparent',
              borderTop: '8px solid #0066CC',
              filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1))',
            }}
          />
        </div>
      )}

      <style jsx>{`
        @keyframes ios-callout-appear {
          from {
            opacity: 0;
            transform: translate(-50%, -100%) scale(0.88) translateY(4px);
          }
          to {
            opacity: 1;
            transform: translate(-50%, -100%) scale(1) translateY(0);
          }
        }

        /* Highlight selected text with iOS-style blue */
        ::selection {
          background-color: #0A84FF44;
          color: inherit;
        }

        ::-moz-selection {
          background-color: #0A84FF44;
          color: inherit;
        }
      `}</style>
    </>
  );
}
