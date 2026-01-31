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
            marginBottom: '16px'
          }}>
            <h2 style={{ margin: 0 }}>
              {title}
              {count !== null && (
                <span style={{
                  fontSize: '0.8em',
                  color: '#718096',
                  marginLeft: '8px',
                  fontWeight: 'normal'
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
          background: isExpanded ? 'var(--cream, #faf6f0)' : 'white',
          border: 'none',
          padding: '12px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          borderBottom: '1px solid var(--border-light, #e5e7eb)',
          transition: 'background 0.2s ease'
        }}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          flex: 1
        }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '18px',
              height: '18px',
              transition: 'transform 0.2s ease',
              transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
              fontSize: '12px',
              color: 'var(--primary-teal, #0d9488)'
            }}
          >
            ▶
          </span>
          <h2 style={{
            margin: 0,
            fontSize: '1rem',
            fontWeight: '600',
            color: 'var(--deep-blue, #1e293b)'
          }}>
            {title}
            {count !== null && (
              <span style={{
                fontSize: '0.8rem',
                color: '#6b7280',
                marginLeft: '8px',
                fontWeight: 'normal'
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
          transition: 'height 0.2s ease',
          visibility: isExpanded ? 'visible' : 'hidden'
        }}
      >
        <div style={{ padding: '12px 16px' }}>
          {children}
        </div>
      </div>
    </div>
  );
}
