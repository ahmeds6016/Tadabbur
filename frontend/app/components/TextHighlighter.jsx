'use client';
import { useState, useEffect, useRef } from 'react';

export default function TextHighlighter({ children, onHighlight, enabled = true }) {
  const [selection, setSelection] = useState(null);
  const [menuPosition, setMenuPosition] = useState(null);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!enabled) return;

    const updateMenu = () => {
      const selectedText = window.getSelection()?.toString().trim();

      if (selectedText && selectedText.length > 0) {
        const range = window.getSelection()?.getRangeAt(0);
        const rect = range?.getBoundingClientRect();

        if (rect) {
          setSelection(selectedText);

          // Position button BELOW the selection with spacing
          setMenuPosition({
            x: rect.left + rect.width / 2,
            y: rect.bottom + 10  // 10px below selection
          });
        }
      } else {
        // Clear immediately when no selection (user deselected)
        setSelection(null);
        setMenuPosition(null);
      }
    };

    const hideMenu = (e) => {
      // Don't hide if clicking the menu button itself
      if (menuRef.current && menuRef.current.contains(e.target)) {
        return;
      }

      // If clicking anywhere else, check if there's still a selection
      // This will be handled by updateMenu on the next selectionchange
    };

    // Update menu position as selection changes (real-time)
    document.addEventListener('selectionchange', updateMenu);

    // Also update on mouse/touch events for immediate feedback
    document.addEventListener('mouseup', updateMenu);
    document.addEventListener('touchend', updateMenu);

    // Only hide menu if clicking outside (but let selectionchange handle clearing)
    document.addEventListener('mousedown', hideMenu, true);
    document.addEventListener('touchstart', hideMenu, true);

    return () => {
      document.removeEventListener('selectionchange', updateMenu);
      document.removeEventListener('mouseup', updateMenu);
      document.removeEventListener('touchend', updateMenu);
      document.removeEventListener('mousedown', hideMenu, true);
      document.removeEventListener('touchstart', hideMenu, true);
    };
  }, [enabled]);

  const handleAnnotate = (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (selection && onHighlight) {
      onHighlight(selection);

      // Immediate cleanup
      setSelection(null);
      setMenuPosition(null);
      window.getSelection()?.removeAllRanges();
    }
  };

  return (
    <>
      {children}

      {selection && menuPosition && (
        <div
          ref={menuRef}
          className="highlight-menu"
          style={{
            position: 'fixed',
            left: `${menuPosition.x}px`,
            top: `${menuPosition.y}px`,
            transform: 'translate(-50%, 0)',  // Center horizontally, no vertical offset
            zIndex: 10000,  // Very high z-index to ensure it's always on top
            animation: 'fadeIn 0.2s ease',
            pointerEvents: 'auto'  // Ensure it's clickable
          }}
        >
          <button
            onMouseDown={handleAnnotate}
            onTouchStart={handleAnnotate}  // Touch support for mobile
            style={{
              padding: '10px 18px',
              background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
              border: 'none',
              borderRadius: '8px',
              color: 'white',
              fontSize: '0.9rem',
              fontWeight: '700',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(245, 158, 11, 0.5)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s ease',
              userSelect: 'none',  // Prevent text selection on button
              WebkitUserSelect: 'none',  // Safari
              MozUserSelect: 'none',  // Firefox
              msUserSelect: 'none',  // IE/Edge
              WebkitTapHighlightColor: 'transparent'  // Remove tap highlight on mobile
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'scale(1.05)';
              e.currentTarget.style.boxShadow = '0 6px 16px rgba(245, 158, 11, 0.6)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(245, 158, 11, 0.5)';
            }}
          >
            <span style={{ fontSize: '1.1rem' }}>✨</span>
            <span>Reflect on Selection</span>
          </button>
        </div>
      )}

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translate(-50%, 0) scale(0.95);
          }
          to {
            opacity: 1;
            transform: translate(-50%, 0) scale(1);
          }
        }

        .highlight-menu {
          -webkit-touch-callout: none;
          -webkit-user-select: none;
          -khtml-user-select: none;
          -moz-user-select: none;
          -ms-user-select: none;
          user-select: none;
        }
      `}</style>
    </>
  );
}
