'use client';
import { useState, useEffect, useRef } from 'react';

export default function TextHighlighter({ children, onHighlight, enabled = true }) {
  const [selection, setSelection] = useState(null);
  const [menuPosition, setMenuPosition] = useState(null);

  // Refs for menu and annotation state tracking
  const menuRef = useRef(null);
  const isAnnotatingRef = useRef(false);

  useEffect(() => {
    if (!enabled) return;

    const handleMouseUp = (e) => {
      // Don't process if clicking the menu
      if (menuRef.current && menuRef.current.contains(e.target)) {
        return;
      }

      const selectedText = window.getSelection()?.toString().trim();

      if (selectedText && selectedText.length > 0) {
        const range = window.getSelection()?.getRangeAt(0);
        const rect = range?.getBoundingClientRect();

        if (rect) {
          setSelection(selectedText);
          setMenuPosition({
            x: rect.left + rect.width / 2,
            y: rect.top - 10
          });
        }
      } else {
        // Only clear if we're not in the middle of annotating
        if (!isAnnotatingRef.current) {
          setSelection(null);
          setMenuPosition(null);
        }
      }
    };

    const handleClickOutside = (e) => {
      // Don't close if clicking the menu or if we're annotating
      if (isAnnotatingRef.current || (menuRef.current && menuRef.current.contains(e.target))) {
        return;
      }

      if (!e.target.closest('.highlight-menu')) {
        setSelection(null);
        setMenuPosition(null);
      }
    };

    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('mousedown', handleClickOutside, true);

    return () => {
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mousedown', handleClickOutside, true);
    };
  }, [enabled]);

  const handleAnnotate = (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (selection && onHighlight) {
      isAnnotatingRef.current = true;
      onHighlight(selection);

      // Clean up after a short delay
      setTimeout(() => {
        setSelection(null);
        setMenuPosition(null);
        window.getSelection()?.removeAllRanges();
        isAnnotatingRef.current = false;
      }, 100);
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
            transform: 'translate(-50%, -100%)',
            zIndex: 1000,
            animation: 'fadeIn 0.2s ease'
          }}
        >
          <button
            onMouseDown={handleAnnotate}
            style={{
              padding: '8px 16px',
              background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
              border: 'none',
              borderRadius: '8px',
              color: 'white',
              fontSize: '0.85rem',
              fontWeight: '700',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(245, 158, 11, 0.4)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => {
              e.target.style.transform = 'scale(1.05)';
              e.target.style.boxShadow = '0 6px 16px rgba(245, 158, 11, 0.5)';
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'scale(1)';
              e.target.style.boxShadow = '0 4px 12px rgba(245, 158, 11, 0.4)';
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
            transform: translate(-50%, -100%) scale(0.9);
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
