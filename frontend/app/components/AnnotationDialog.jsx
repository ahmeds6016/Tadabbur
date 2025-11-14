'use client';
import { useState, useEffect, useRef } from 'react';
import AnnotationForm from './AnnotationForm';

/**
 * AnnotationDialog - Ground-Zero Rebuild
 *
 * PRINCIPLES:
 * - Uses native <dialog> element (fallback to div for older browsers)
 * - CSS-only positioning (no JavaScript calculations)
 * - Natural scroll behavior (no manual manipulation)
 * - Mobile-first with bottom sheet pattern
 * - Zero scroll-lock code
 */

export default function AnnotationDialog({
  isOpen,
  onClose,
  selectedText,
  verse,
  user,
  reflectionType = 'verse',
  onSaved,
  existingAnnotation = null,
  sectionName = null,
  queryContext = null,
  shareId = null
}) {
  const dialogRef = useRef(null);
  const [isClosing, setIsClosing] = useState(false);
  const isMobile = typeof window !== 'undefined' && window.innerWidth <= 768;

  // Open/close dialog using native API
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      // Use native showModal if available, fallback to class
      if (typeof dialog.showModal === 'function') {
        dialog.showModal();
      } else {
        dialog.classList.add('dialog-open');
        document.body.style.overflow = 'hidden'; // Simple fallback
      }
    } else {
      if (typeof dialog.close === 'function') {
        dialog.close();
      } else {
        dialog.classList.remove('dialog-open');
        document.body.style.overflow = ''; // Restore
      }
    }

    return () => {
      // Cleanup on unmount
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Handle backdrop click (native dialog handles this automatically)
  const handleBackdropClick = (e) => {
    if (e.target === dialogRef.current) {
      handleClose();
    }
  };

  // Smooth close animation
  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      onClose();
      setIsClosing(false);
    }, 200);
  };

  // Handle ESC key (native dialog handles this automatically)
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape' && isOpen) {
        handleClose();
      }
    };

    // Only add listener for fallback mode
    if (dialogRef.current && !dialogRef.current.showModal) {
      document.addEventListener('keydown', handleEsc);
      return () => document.removeEventListener('keydown', handleEsc);
    }
  }, [isOpen]);

  if (!isOpen && !isClosing) return null;

  return (
    <>
      <dialog
        ref={dialogRef}
        className={`annotation-dialog ${isClosing ? 'closing' : ''} ${isMobile ? 'mobile' : 'desktop'}`}
        onClose={handleClose}
        onClick={handleBackdropClick}
        aria-labelledby="annotation-dialog-title"
        aria-modal="true"
      >
        <div className="dialog-content" onClick={(e) => e.stopPropagation()}>
          {/* Close button */}
          <button
            className="dialog-close"
            onClick={handleClose}
            aria-label="Close dialog"
            type="button"
          >
            ×
          </button>

          {/* Form Component */}
          <AnnotationForm
            selectedText={selectedText || (reflectionType === 'highlight' ? verse?.highlightedText : null)}
            verse={verse}
            user={user}
            reflectionType={reflectionType}
            onSaved={(data) => {
              onSaved?.(data);
              handleClose();
            }}
            onCancel={handleClose}
            existingAnnotation={existingAnnotation}
            sectionName={sectionName}
            queryContext={queryContext}
            shareId={shareId}
          />
        </div>
      </dialog>

      <style jsx>{`
        /* Native dialog styles */
        dialog {
          padding: 0;
          border: none;
          background: transparent;
          max-width: none;
          max-height: none;
          width: 100%;
          height: 100%;
        }

        /* Backdrop (native ::backdrop for dialog, custom for fallback) */
        dialog::backdrop,
        .dialog-open::before {
          background: rgba(0, 0, 0, 0.5);
          backdrop-filter: blur(4px);
        }

        /* Fallback for browsers without dialog support */
        .dialog-open {
          display: flex !important;
          position: fixed;
          inset: 0;
          z-index: 9999;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }

        .dialog-open::before {
          content: '';
          position: absolute;
          inset: 0;
          z-index: -1;
        }

        /* Content container */
        .dialog-content {
          position: relative;
          background: white;
          border-radius: 16px;
          width: 100%;
          max-width: 600px;
          max-height: 90vh;
          overflow-y: auto;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
          animation: slideUp 0.3s ease-out;
        }

        /* Mobile bottom sheet */
        @media (max-width: 768px) {
          .dialog-content {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            max-height: 85vh;
            border-radius: 24px 24px 0 0;
            animation: slideUpMobile 0.3s ease-out;
          }

          dialog {
            align-items: flex-end;
            padding: 0;
          }
        }

        /* Desktop centered modal */
        @media (min-width: 769px) {
          dialog {
            display: flex;
            align-items: center;
            justify-content: center;
          }
        }

        /* Close button */
        .dialog-close {
          position: absolute;
          top: 16px;
          right: 16px;
          width: 40px;
          height: 40px;
          border-radius: 50%;
          border: none;
          background: rgba(0, 0, 0, 0.05);
          color: #666;
          font-size: 24px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
          z-index: 10;
        }

        .dialog-close:hover {
          background: rgba(0, 0, 0, 0.1);
          transform: scale(1.1);
        }

        /* Animations */
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes slideUpMobile {
          from {
            transform: translateY(100%);
          }
          to {
            transform: translateY(0);
          }
        }

        /* Closing animation */
        .annotation-dialog.closing .dialog-content {
          animation: slideDown 0.2s ease-in;
        }

        @keyframes slideDown {
          from {
            opacity: 1;
            transform: translateY(0);
          }
          to {
            opacity: 0;
            transform: translateY(20px);
          }
        }

        @media (max-width: 768px) {
          .annotation-dialog.closing .dialog-content {
            animation: slideDownMobile 0.2s ease-in;
          }

          @keyframes slideDownMobile {
            from {
              transform: translateY(0);
            }
            to {
              transform: translateY(100%);
            }
          }
        }

        /* Scrollbar styling */
        .dialog-content::-webkit-scrollbar {
          width: 8px;
        }

        .dialog-content::-webkit-scrollbar-track {
          background: #f1f1f1;
          border-radius: 4px;
        }

        .dialog-content::-webkit-scrollbar-thumb {
          background: #888;
          border-radius: 4px;
        }

        .dialog-content::-webkit-scrollbar-thumb:hover {
          background: #555;
        }

        /* Ensure dialog is always on top */
        dialog {
          z-index: 10000;
        }

        /* Smooth scroll for content */
        .dialog-content {
          scroll-behavior: smooth;
          -webkit-overflow-scrolling: touch;
        }

        /* Prevent body scroll when open (fallback) */
        body:has(dialog[open]) {
          overflow: hidden;
        }
      `}</style>
    </>
  );
}