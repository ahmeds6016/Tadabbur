'use client';
import { useState, useEffect, useRef } from 'react';

export default function CollapsibleSection({
  title,
  children,
  count = null,
  defaultExpanded = false,
  sectionKey = null,
  className = '',
  headerAction = null
}) {
  const contentRef = useRef(null);
  const [contentHeight, setContentHeight] = useState(0);

  // Use localStorage to remember expand/collapse state
  const [isExpanded, setIsExpanded] = useState(() => {
    if (typeof window === 'undefined') return defaultExpanded;

    if (sectionKey) {
      const saved = localStorage.getItem(`section-${sectionKey}`);
      return saved !== null ? saved === 'true' : defaultExpanded;
    }
    return defaultExpanded;
  });

  // Save state to localStorage when it changes
  useEffect(() => {
    if (sectionKey && typeof window !== 'undefined') {
      localStorage.setItem(`section-${sectionKey}`, isExpanded.toString());
    }
  }, [isExpanded, sectionKey]);

  // Update content height when expanded
  useEffect(() => {
    if (contentRef.current && isExpanded) {
      setContentHeight(contentRef.current.scrollHeight);
    }
  }, [isExpanded, children]);

  // Check if we're on mobile
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Don't use collapsible on desktop
  if (!isMobile) {
    return (
      <div className={`result-section ${className}`}>
        {title && (
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '18px',
            paddingBottom: '12px',
            borderBottom: '1px solid var(--color-border)',
          }}>
            <h2 style={{
              margin: 0,
              fontSize: '1.1rem',
              fontWeight: 700,
              color: 'var(--color-text)',
              letterSpacing: '-0.01em',
            }}>
              {title}
              {count !== null && (
                <span style={{
                  fontSize: '0.8em',
                  color: 'var(--color-text-muted)',
                  marginLeft: '8px',
                  fontWeight: 500,
                }}>
                  ({count})
                </span>
              )}
            </h2>
            {headerAction}
          </div>
        )}
        {children}
      </div>
    );
  }

  return (
    <div className={`collapsible-section ${className}`}>
      <button
        className="section-header"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        style={{
          width: '100%',
          background: isExpanded ? 'var(--color-surface-muted)' : 'var(--color-surface)',
          border: 'none',
          padding: '14px 18px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          borderBottom: '1px solid var(--color-border)',
          transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          flex: 1,
        }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '20px',
              height: '20px',
              transition: 'transform 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
              transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
              fontSize: '11px',
              color: '#0d9488',
            }}
          >
            ▶
          </span>
          <h2 style={{
            margin: 0,
            fontSize: '1.05rem',
            fontWeight: 700,
            color: 'var(--color-text)',
            letterSpacing: '-0.01em',
          }}>
            {title}
            {count !== null && (
              <span style={{
                fontSize: '0.8rem',
                color: 'var(--color-text-muted)',
                marginLeft: '8px',
                fontWeight: 500,
              }}>
                ({count})
              </span>
            )}
          </h2>
        </div>
        {headerAction && (
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ marginLeft: '8px' }}
          >
            {headerAction}
          </div>
        )}
      </button>

      <div
        ref={contentRef}
        className="section-content"
        style={{
          height: isExpanded ? 'auto' : '0',
          overflow: 'hidden',
          transition: 'height 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
          visibility: isExpanded ? 'visible' : 'hidden',
        }}
      >
        <div style={{ padding: '14px 18px 18px' }}>
          {children}
        </div>
      </div>
    </div>
  );
}
