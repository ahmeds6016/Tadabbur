'use client';
import { useState, useRef, useEffect } from 'react';

export default function Tooltip({
  content,
  position = 'top',
  trigger = 'hover',
  showIcon = false,
  delay = 200,
  children
}) {
  const [isVisible, setIsVisible] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const containerRef = useRef(null);
  const tooltipRef = useRef(null);
  const timeoutRef = useRef(null);

  useEffect(() => {
    if (isVisible && containerRef.current && tooltipRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      const tooltipRect = tooltipRef.current.getBoundingClientRect();
      let top = 0, left = 0;

      switch (position) {
        case 'top':
          top = containerRect.top - tooltipRect.height - 8;
          left = containerRect.left + (containerRect.width / 2) - (tooltipRect.width / 2);
          break;
        case 'bottom':
          top = containerRect.bottom + 8;
          left = containerRect.left + (containerRect.width / 2) - (tooltipRect.width / 2);
          break;
        case 'left':
          top = containerRect.top + (containerRect.height / 2) - (tooltipRect.height / 2);
          left = containerRect.left - tooltipRect.width - 8;
          break;
        case 'right':
          top = containerRect.top + (containerRect.height / 2) - (tooltipRect.height / 2);
          left = containerRect.right + 8;
          break;
        default:
          top = containerRect.top - tooltipRect.height - 8;
          left = containerRect.left + (containerRect.width / 2) - (tooltipRect.width / 2);
      }

      // Ensure tooltip stays within viewport
      const padding = 10;
      left = Math.max(padding, Math.min(left, window.innerWidth - tooltipRect.width - padding));
      top = Math.max(padding, Math.min(top, window.innerHeight - tooltipRect.height - padding));

      setTooltipPosition({ top, left });
    }
  }, [isVisible, position]);

  const handleShow = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setIsVisible(true), delay);
  };

  const handleHide = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsVisible(false);
  };

  const handleClick = () => {
    if (trigger === 'click') {
      setIsVisible(!isVisible);
    }
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const eventHandlers = trigger === 'hover'
    ? {
        onMouseEnter: handleShow,
        onMouseLeave: handleHide,
        onFocus: handleShow,
        onBlur: handleHide,
      }
    : trigger === 'click'
    ? {
        onClick: handleClick,
      }
    : {};

  return (
    <div
      className="tooltip-container"
      ref={containerRef}
      {...eventHandlers}
      style={{ position: 'relative', display: 'inline-block' }}
    >
      {children}
      {showIcon && (
        <span className="tooltip-icon">
          ?
        </span>
      )}

      {isVisible && (
        <div
          ref={tooltipRef}
          className={`tooltip-content ${position}`}
          style={{
            position: 'fixed',
            top: `${tooltipPosition.top}px`,
            left: `${tooltipPosition.left}px`,
            zIndex: 1000,
          }}
          role="tooltip"
          aria-hidden={!isVisible}
        >
          <div className="tooltip-arrow" />
          {content}
        </div>
      )}

      <style jsx>{`
        .tooltip-icon {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: var(--primary-teal);
          color: white;
          font-size: 0.7rem;
          font-weight: 700;
          margin-left: 4px;
          cursor: help;
        }

        .tooltip-content {
          background: var(--deep-blue);
          color: white;
          padding: 8px 12px;
          border-radius: 8px;
          font-size: 0.875rem;
          line-height: 1.4;
          max-width: 250px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
          animation: tooltipFadeIn 0.2s ease;
          white-space: pre-line;
        }

        @keyframes tooltipFadeIn {
          from {
            opacity: 0;
            transform: translateY(4px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .tooltip-arrow {
          position: absolute;
          width: 0;
          height: 0;
          border-style: solid;
        }

        .tooltip-content.top .tooltip-arrow {
          bottom: -6px;
          left: 50%;
          transform: translateX(-50%);
          border-width: 6px 6px 0 6px;
          border-color: var(--deep-blue) transparent transparent transparent;
        }

        .tooltip-content.bottom .tooltip-arrow {
          top: -6px;
          left: 50%;
          transform: translateX(-50%);
          border-width: 0 6px 6px 6px;
          border-color: transparent transparent var(--deep-blue) transparent;
        }

        .tooltip-content.left .tooltip-arrow {
          right: -6px;
          top: 50%;
          transform: translateY(-50%);
          border-width: 6px 0 6px 6px;
          border-color: transparent transparent transparent var(--deep-blue);
        }

        .tooltip-content.right .tooltip-arrow {
          left: -6px;
          top: 50%;
          transform: translateY(-50%);
          border-width: 6px 6px 6px 0;
          border-color: transparent var(--deep-blue) transparent transparent;
        }

        /* Accessibility */
        @media (prefers-reduced-motion: reduce) {
          .tooltip-content {
            animation: none;
          }
        }

        /* Mobile adjustments */
        @media (max-width: 768px) {
          .tooltip-content {
            font-size: 0.8rem;
            padding: 6px 10px;
          }
        }
      `}</style>
    </div>
  );
}