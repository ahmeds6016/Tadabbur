'use client';
import { useEffect, useRef } from 'react';

export default function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmStyle = 'danger', // 'danger', 'primary', 'warning'
  onConfirm,
  onCancel
}) {
  const dialogRef = useRef(null);

  useEffect(() => {
    if (isOpen && dialogRef.current) {
      dialogRef.current.focus();
    }

    const handleEscape = (e) => {
      if (isOpen && e.key === 'Escape') {
        onCancel();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  const getConfirmButtonClass = () => {
    switch (confirmStyle) {
      case 'danger':
        return 'confirm-btn-danger';
      case 'warning':
        return 'confirm-btn-warning';
      default:
        return 'confirm-btn-primary';
    }
  };

  return (
    <>
      <div
        className="confirm-backdrop"
        onClick={onCancel}
        aria-hidden="true"
      />
      <div
        className="confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-message"
        ref={dialogRef}
        tabIndex={-1}
      >
        <div className="confirm-content">
          <h3 id="confirm-title">{title}</h3>
          <p id="confirm-message">{message}</p>
          <div className="confirm-actions">
            <button
              onClick={onCancel}
              className="cancel-btn"
              type="button"
            >
              {cancelText}
            </button>
            <button
              onClick={onConfirm}
              className={getConfirmButtonClass()}
              type="button"
            >
              {confirmText}
            </button>
          </div>
        </div>

        <style jsx>{`
          .confirm-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 9999;
            animation: fadeIn 0.2s ease;
          }

          .confirm-dialog {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            z-index: 10000;
            max-width: 400px;
            width: 90%;
            animation: slideIn 0.2s ease;
          }

          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }

          @keyframes slideIn {
            from {
              transform: translate(-50%, -50%) scale(0.9);
              opacity: 0;
            }
            to {
              transform: translate(-50%, -50%) scale(1);
              opacity: 1;
            }
          }

          .confirm-content {
            padding: 24px;
          }

          #confirm-title {
            margin: 0 0 12px 0;
            color: var(--deep-blue);
            font-size: 1.25rem;
          }

          #confirm-message {
            margin: 0 0 24px 0;
            color: #666;
            line-height: 1.5;
          }

          .confirm-actions {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
          }

          button {
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
          }

          .cancel-btn {
            background: transparent;
            color: #666;
            border: 1px solid #ddd;
          }

          .cancel-btn:hover {
            background: #f5f5f5;
          }

          .confirm-btn-primary {
            background: var(--primary-teal);
            color: white;
          }

          .confirm-btn-primary:hover {
            background: var(--gold);
          }

          .confirm-btn-danger {
            background: #ef4444;
            color: white;
          }

          .confirm-btn-danger:hover {
            background: #dc2626;
          }

          .confirm-btn-warning {
            background: #f59e0b;
            color: white;
          }

          .confirm-btn-warning:hover {
            background: #d97706;
          }

          /* Mobile adjustments */
          @media (max-width: 768px) {
            .confirm-dialog {
              width: 95%;
              max-width: none;
            }

            .confirm-content {
              padding: 20px;
            }
          }
        `}</style>
      </div>
    </>
  );
}