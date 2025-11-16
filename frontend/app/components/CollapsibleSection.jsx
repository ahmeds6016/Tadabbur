'use client';
import { useState, useEffect } from 'react';

export default function CollapsibleSection({
  title,
  children,
  count = null,
  defaultExpanded = false,
  sectionKey = null,
  className = '',
  headerAction = null // For buttons like "Reflect"
}) {
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
        style={{
          width: '100%',
          background: 'none',
          border: 'none',
          padding: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          borderBottom: '1px solid #e5e7eb',
          transition: 'background 0.2s'
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = '#f9fafb'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          flex: 1
        }}>
          <span
            className="chevron"
            style={{
              display: 'inline-block',
              width: '20px',
              height: '20px',
              transition: 'transform 0.3s',
              transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
              fontSize: '16px',
              color: '#6b7280'
            }}
          >
            ▶
          </span>
          <h2 style={{
            margin: 0,
            fontSize: '1.125rem',
            fontWeight: '600',
            color: '#1f2937'
          }}>
            {title}
            {count !== null && (
              <span style={{
                fontSize: '0.875rem',
                color: '#6b7280',
                marginLeft: '8px',
                fontWeight: 'normal',
                background: '#f3f4f6',
                padding: '2px 8px',
                borderRadius: '12px',
                display: 'inline-block'
              }}>
                {count}
              </span>
            )}
          </h2>
        </div>
        {headerAction && !isExpanded && (
          <div onClick={(e) => e.stopPropagation()}>
            {headerAction}
          </div>
        )}
      </button>

      <div
        className="section-content"
        style={{
          maxHeight: isExpanded ? '100000px' : '0',
          overflow: 'hidden',
          transition: 'max-height 0.3s ease-in-out',
          opacity: isExpanded ? 1 : 0
        }}
      >
        {isExpanded && (
          <>
            {headerAction && (
              <div style={{
                padding: '12px 16px',
                borderBottom: '1px solid #e5e7eb',
                display: 'flex',
                justifyContent: 'flex-end'
              }}>
                {headerAction}
              </div>
            )}
            <div style={{ padding: '16px' }}>
              {children}
            </div>
          </>
        )}
      </div>
    </div>
  );
}