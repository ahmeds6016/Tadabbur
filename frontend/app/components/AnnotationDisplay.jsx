'use client';
import { useState } from 'react';

const ANNOTATION_TYPE_CONFIG = {
  personal_insight: { icon: '💡', label: 'Insight', color: '#0D9488' },
  question: { icon: '❓', label: 'Question', color: '#8B5CF6' },
  application: { icon: '✅', label: 'Application', color: '#059669' },
  memory: { icon: '💭', label: 'Memory', color: '#3B82F6' },
  connection: { icon: '🔗', label: 'Connection', color: '#D97706' }
};

export default function AnnotationDisplay({
  annotations,
  onEdit,
  onDelete
}) {
  const [expandedId, setExpandedId] = useState(null);

  if (!annotations || annotations.length === 0) {
    return null;
  }

  const formatDate = (timestamp) => {
    if (!timestamp) return 'Recently';
    try {
      const date = new Date(timestamp.seconds * 1000);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return 'Recently';
    }
  };

  return (
    <div style={{ marginTop: '24px' }}>
      <h4
        style={{
          fontSize: '1.1rem',
          fontWeight: '700',
          color: 'var(--primary-teal)',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}
      >
        📝 Your Annotations ({annotations.length})
      </h4>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {annotations.map(annotation => {
          const typeConfig = ANNOTATION_TYPE_CONFIG[annotation.type] || ANNOTATION_TYPE_CONFIG.personal_insight;
          const isExpanded = expandedId === annotation.id;

          return (
            <div
              key={annotation.id}
              style={{
                padding: '16px',
                background: 'white',
                borderRadius: '12px',
                border: '2px solid var(--border-light)',
                borderLeft: `4px solid ${typeConfig.color}`,
                transition: 'all 0.3s ease'
              }}
              className="annotation-card"
            >
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '1.2rem' }}>{typeConfig.icon}</span>
                  <span
                    style={{
                      background: typeConfig.color,
                      color: 'white',
                      padding: '4px 10px',
                      borderRadius: '12px',
                      fontSize: '0.75rem',
                      fontWeight: '700',
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px'
                    }}
                  >
                    {typeConfig.label}
                  </span>
                  <span style={{ fontSize: '0.85rem', color: '#999' }}>
                    {formatDate(annotation.createdAt)}
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '4px' }}>
                  <button
                    onClick={() => onEdit(annotation)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--primary-teal)',
                      cursor: 'pointer',
                      fontSize: '1.2rem',
                      padding: '4px 8px'
                    }}
                    title="Edit annotation"
                  >
                    ✏️
                  </button>
                  <button
                    onClick={() => {
                      if (confirm('Delete this annotation?')) {
                        onDelete(annotation.id);
                      }
                    }}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--error-color)',
                      cursor: 'pointer',
                      fontSize: '1.2rem',
                      padding: '4px 8px'
                    }}
                    title="Delete annotation"
                  >
                    🗑️
                  </button>
                </div>
              </div>

              {/* Content */}
              <div style={{ marginBottom: '12px' }}>
                <p
                  style={{
                    margin: 0,
                    color: 'var(--foreground)',
                    fontSize: '0.95rem',
                    lineHeight: '1.6',
                    whiteSpace: isExpanded ? 'pre-wrap' : 'nowrap',
                    overflow: isExpanded ? 'visible' : 'hidden',
                    textOverflow: 'ellipsis'
                  }}
                >
                  {annotation.content}
                </p>
              </div>

              {/* Tags */}
              {annotation.tags && annotation.tags.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
                  {annotation.tags.map(tag => (
                    <span
                      key={tag}
                      style={{
                        background: 'var(--cream)',
                        color: 'var(--primary-teal)',
                        padding: '4px 10px',
                        borderRadius: '12px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        border: '1px solid var(--border-light)'
                      }}
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Expand/Collapse for long content */}
              {annotation.content && annotation.content.length > 150 && (
                <button
                  onClick={() => setExpandedId(isExpanded ? null : annotation.id)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--primary-teal)',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: '600',
                    padding: '4px 0'
                  }}
                >
                  {isExpanded ? '▲ Show less' : '▼ Show more'}
                </button>
              )}
            </div>
          );
        })}
      </div>

      <style jsx>{`
        .annotation-card:hover {
          transform: translateX(4px);
          box-shadow: var(--shadow-soft);
          border-color: var(--gold);
        }
      `}</style>
    </div>
  );
}
