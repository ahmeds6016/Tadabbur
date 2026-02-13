'use client';
import { useState, useEffect, useCallback } from 'react';
import ConfirmDialog from './ConfirmDialog';

const ANNOTATION_TYPE_CONFIG = {
  personal_insight: { label: 'Insight', color: '#0D9488' },
  question: { label: 'Question', color: '#8B5CF6' },
  application: { label: 'Application', color: '#059669' },
  memory: { label: 'Memory', color: '#3B82F6' },
  connection: { label: 'Connection', color: '#D97706' },
  dua: { label: 'Dua/Prayer', color: '#10B981' },
  gratitude: { label: 'Gratitude', color: '#F59E0B' },
  reminder: { label: 'Reminder', color: '#EF4444' },
  story: { label: 'Story', color: '#6366F1' },
  linguistic: { label: 'Linguistic', color: '#84CC16' },
  historical: { label: 'Historical', color: '#A78BFA' },
  scientific: { label: 'Scientific', color: '#06B6D4' },
  personal_experience: { label: 'Experience', color: '#EC4899' },
  teaching_point: { label: 'Teaching', color: '#F97316' },
  warning: { label: 'Warning', color: '#DC2626' },
  goal: { label: 'Goal', color: '#059669' },
  contemplation: { label: 'Contemplation', color: '#7C3AED' }
};

const getTypeConfig = (type) => {
  if (ANNOTATION_TYPE_CONFIG[type]) {
    return ANNOTATION_TYPE_CONFIG[type];
  }
  return {
    label: type ? type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, ' ') : 'Custom',
    color: '#6B7280'
  };
};

const formatDate = (timestamp) => {
  if (!timestamp) return '';
  const date = timestamp.seconds
    ? new Date(timestamp.seconds * 1000)
    : new Date(timestamp);
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  });
};

const getContextLabel = (annotation) => {
  if (annotation.reflection_type === 'verse' && annotation.surah && annotation.verse) {
    return `Surah ${annotation.surah}, Verse ${annotation.verse}`;
  }
  if (annotation.reflection_type === 'section' && annotation.section_name) {
    return annotation.section_name;
  }
  if (annotation.reflection_type === 'highlight' && annotation.highlighted_text) {
    return `"${annotation.highlighted_text.substring(0, 100)}${annotation.highlighted_text.length > 100 ? '...' : ''}"`;
  }
  if (annotation.query_context) {
    return `Query: "${annotation.query_context.substring(0, 80)}${annotation.query_context.length > 80 ? '...' : ''}"`;
  }
  return 'General Reflection';
};

export default function ReflectionDetailPanel({ annotation, isOpen, onClose, onEdit, onDelete }) {
  const typeConfig = annotation ? getTypeConfig(annotation.type) : {};
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Handle escape key
  const handleEscape = useCallback((e) => {
    if (e.key === 'Escape') {
      onClose();
    }
  }, [onClose]);

  // Handle browser back button
  useEffect(() => {
    if (isOpen) {
      // Add history entry
      window.history.pushState({ reflectionPanel: true }, '');

      const handlePopState = () => {
        onClose();
      };

      window.addEventListener('popstate', handlePopState);
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';

      return () => {
        window.removeEventListener('popstate', handlePopState);
        document.removeEventListener('keydown', handleEscape);
        document.body.style.overflow = '';
      };
    }
  }, [isOpen, onClose, handleEscape]);

  if (!isOpen || !annotation) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className="reflection-overlay"
        onClick={onClose}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(30, 58, 95, 0.6)',
          backdropFilter: 'blur(4px)',
          zIndex: 1000,
          animation: 'fadeIn 0.2s ease'
        }}
      />

      {/* Panel */}
      <div
        className="reflection-panel"
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: '100%',
          maxWidth: '520px',
          background: 'var(--background, #FDFBF7)',
          boxShadow: '-8px 0 32px rgba(30, 58, 95, 0.2)',
          zIndex: 1001,
          display: 'flex',
          flexDirection: 'column',
          animation: 'slideInRight 0.3s ease'
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid var(--border-light, #E5E7EB)',
            background: 'white',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Type Badge */}
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '20px',
                fontSize: '0.85rem',
                fontWeight: '600',
                background: `${typeConfig.color}15`,
                color: typeConfig.color,
                border: `1px solid ${typeConfig.color}30`
              }}
            >
              <span>{typeConfig.icon}</span>
              {typeConfig.label}
            </span>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '28px',
              cursor: 'pointer',
              color: 'var(--text-muted, #6B7280)',
              padding: '4px 8px',
              borderRadius: '8px',
              lineHeight: 1,
              transition: 'all 0.2s ease'
            }}
            onMouseOver={(e) => e.currentTarget.style.background = 'var(--cream, #FAF6F0)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
            aria-label="Close panel"
          >
            &times;
          </button>
        </div>

        {/* Context Info */}
        <div
          style={{
            padding: '16px 24px',
            background: 'var(--cream, #FAF6F0)',
            borderBottom: '1px solid var(--border-light, #E5E7EB)',
            flexShrink: 0
          }}
        >
          <div style={{
            fontSize: '0.8rem',
            color: 'var(--text-muted, #6B7280)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '4px'
          }}>
            {annotation.reflection_type === 'verse' ? 'Verse Reference' :
             annotation.reflection_type === 'section' ? 'Section' :
             annotation.reflection_type === 'highlight' ? 'Highlighted Text' : 'Context'}
          </div>
          <div style={{
            fontSize: '0.95rem',
            color: 'var(--primary-teal, #0D9488)',
            fontWeight: '600'
          }}>
            {getContextLabel(annotation)}
          </div>
        </div>

        {/* Main Content - Scrollable */}
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            padding: '24px',
            WebkitOverflowScrolling: 'touch'
          }}
        >
          <div
            style={{
              fontSize: '1.05rem',
              lineHeight: '1.85',
              color: 'var(--text-primary, #2C3E50)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}
          >
            {annotation.content}
          </div>
        </div>

        {/* Tags */}
        {annotation.tags && annotation.tags.length > 0 && (
          <div
            style={{
              padding: '16px 24px',
              borderTop: '1px solid var(--border-light, #E5E7EB)',
              background: 'white',
              flexShrink: 0
            }}
          >
            <div style={{
              fontSize: '0.75rem',
              color: 'var(--text-muted, #6B7280)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: '8px'
            }}>
              Tags
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {annotation.tags.map((tag) => (
                <span
                  key={tag}
                  style={{
                    background: 'var(--cream, #FAF6F0)',
                    color: 'var(--primary-teal, #0D9488)',
                    padding: '6px 12px',
                    borderRadius: '16px',
                    fontSize: '0.8rem',
                    fontWeight: '500',
                    border: '1px solid var(--border-light, #E5E7EB)'
                  }}
                >
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            padding: '16px 24px',
            borderTop: '1px solid var(--border-light, #E5E7EB)',
            background: 'white',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
            paddingBottom: 'max(16px, env(safe-area-inset-bottom))'
          }}
        >
          <div style={{
            fontSize: '0.8rem',
            color: 'var(--text-muted, #6B7280)'
          }}>
            {formatDate(annotation.createdAt)}
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            {onEdit && (
              <button
                onClick={() => onEdit(annotation)}
                style={{
                  background: 'var(--cream, #FAF6F0)',
                  border: '1px solid var(--border-light, #E5E7EB)',
                  color: 'var(--primary-teal, #0D9488)',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontSize: '0.85rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = 'var(--primary-teal)';
                  e.currentTarget.style.color = 'white';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = 'var(--cream, #FAF6F0)';
                  e.currentTarget.style.color = 'var(--primary-teal, #0D9488)';
                }}
              >
                Edit
              </button>
            )}
            {onDelete && (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                style={{
                  background: 'transparent',
                  border: '1px solid var(--error-color, #DC2626)',
                  color: 'var(--error-color, #DC2626)',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontSize: '0.85rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = 'var(--error-color, #DC2626)';
                  e.currentTarget.style.color = 'white';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = 'var(--error-color, #DC2626)';
                }}
              >
                Delete
              </button>
            )}
          </div>
        </div>
      </div>

      <style jsx global>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @keyframes slideInRight {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }

        @media (max-width: 640px) {
          .reflection-panel {
            max-width: 100% !important;
            border-radius: 20px 20px 0 0 !important;
            top: 60px !important;
          }
        }
      `}</style>

      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="Delete Reflection"
        message="Are you sure you want to delete this reflection? This cannot be undone."
        confirmText="Delete"
        confirmStyle="danger"
        onConfirm={() => { setShowDeleteConfirm(false); onDelete(annotation.id); onClose(); }}
        onCancel={() => setShowDeleteConfirm(false)}
      />
    </>
  );
}
