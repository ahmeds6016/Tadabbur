'use client';

import { useEffect, useState } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

/**
 * Toast notification component for displaying temporary messages
 * @param {string} message - The message to display
 * @param {string} type - Type of toast: 'success', 'error', 'warning', 'info'
 * @param {number} duration - How long to show the toast (ms)
 * @param {function} onClose - Callback when toast closes
 * @param {string} position - Position: 'top-right', 'top-left', 'bottom-right', 'bottom-left'
 */
export function Toast({
  message,
  type = 'info',
  duration = 5000,
  onClose,
  position = 'top-right'
}) {
  const [isVisible, setIsVisible] = useState(true);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      handleClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => {
      setIsVisible(false);
      onClose?.();
    }, 300); // Match animation duration
  };

  if (!isVisible) return null;

  const getIcon = () => {
    const iconProps = { size: 20, strokeWidth: 2.5 };
    switch (type) {
      case 'success':
        return <CheckCircle {...iconProps} color="var(--success-color, #059669)" />;
      case 'error':
        return <XCircle {...iconProps} color="var(--error-color, #DC2626)" />;
      case 'warning':
        return <AlertTriangle {...iconProps} color="var(--warning-color, #D97706)" />;
      case 'info':
        return <Info {...iconProps} color="var(--info-color, #0D9488)" />;
      default:
        return <Info {...iconProps} color="var(--info-color, #0D9488)" />;
    }
  };

  const getPositionStyles = () => {
    const positions = {
      'top-right': { top: '20px', right: '20px' },
      'top-left': { top: '20px', left: '20px' },
      'bottom-right': { bottom: '20px', right: '20px' },
      'bottom-left': { bottom: '20px', left: '20px' }
    };
    return positions[position] || positions['top-right'];
  };

  return (
    <>
      <div
        className={`toast toast-${type} ${isExiting ? 'toast-exit' : ''}`}
        style={getPositionStyles()}
        role="alert"
        aria-live="assertive"
      >
        <div className="toast-content">
          <span className="toast-icon" aria-hidden="true">
            {getIcon()}
          </span>
          <p className="toast-message">{message}</p>
        </div>
        <button
          onClick={handleClose}
          className="toast-close"
          aria-label="Dismiss notification"
        >
          <X size={18} />
        </button>
      </div>

      <style jsx>{`
        .toast {
          position: fixed;
          z-index: 9999;
          background: white;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          padding: 16px 20px;
          min-width: 300px;
          max-width: 500px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          animation: slideIn 0.3s ease;
          transition: transform 0.3s ease, opacity 0.3s ease;
        }

        .toast-exit {
          animation: slideOut 0.3s ease;
          opacity: 0;
        }

        .toast-content {
          display: flex;
          align-items: center;
          gap: 12px;
          flex: 1;
        }

        .toast-icon {
          flex-shrink: 0;
          display: flex;
          align-items: center;
        }

        .toast-message {
          margin: 0;
          color: var(--text-primary);
          font-size: 0.95rem;
          line-height: 1.5;
        }

        .toast-close {
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 4px;
          transition: all 0.2s ease;
        }

        .toast-close:hover {
          background: rgba(0, 0, 0, 0.05);
          color: var(--text-primary);
        }

        /* Type-specific styles */
        .toast-success {
          border-left: 4px solid var(--success-color);
        }

        .toast-error {
          border-left: 4px solid var(--error-color);
        }

        .toast-warning {
          border-left: 4px solid var(--warning-color);
        }

        .toast-info {
          border-left: 4px solid var(--info-color);
        }

        /* Animations */
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

        @keyframes slideOut {
          from {
            transform: translateX(0);
            opacity: 1;
          }
          to {
            transform: translateX(100%);
            opacity: 0;
          }
        }

        /* Mobile adjustments */
        @media (max-width: 640px) {
          .toast {
            min-width: calc(100vw - 40px);
            max-width: calc(100vw - 40px);
          }
        }
      `}</style>
    </>
  );
}

/**
 * ToastContainer - Manages multiple toasts
 * Usage: Add this to your layout and use the useToast hook
 */
export function ToastContainer({ toasts = [] }) {
  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} />
      ))}
    </div>
  );
}
