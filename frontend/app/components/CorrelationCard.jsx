'use client';
import { useState } from 'react';

export default function CorrelationCard({ correlations, weeklyInsight, narrative }) {
  const [showRawData, setShowRawData] = useState(false);
  const hasNarrative = narrative && (narrative.narrative || narrative.key_insight);
  const hasClusters = narrative?.clusters?.length > 0;
  const hasCorrelations = correlations?.length > 0;

  if (!hasCorrelations && !weeklyInsight && !hasNarrative) return null;

  return (
    <div style={{
      background: 'var(--color-surface)',
      borderRadius: 14,
      border: '1px solid var(--color-border)',
      padding: '16px',
    }}>
      <div style={{
        fontSize: '0.7rem',
        fontWeight: 600,
        color: 'var(--color-text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        marginBottom: 12,
      }}>
        Patterns Observed
      </div>

      {/* AI-powered narrative (primary display when available) */}
      {hasNarrative && (
        <div style={{ marginBottom: 12 }}>
          {/* Main narrative */}
          <p style={{
            fontSize: '0.88rem',
            color: 'var(--color-text)',
            margin: '0 0 10px 0',
            lineHeight: 1.65,
          }}>
            {narrative.narrative}
          </p>

          {/* Key insight (highlighted) */}
          {narrative.key_insight && (
            <div style={{
              padding: '10px 12px',
              background: 'var(--color-surface-muted)',
              borderRadius: 10,
              borderLeft: '3px solid #0d9488',
              marginBottom: hasClusters ? 12 : 0,
            }}>
              <span style={{
                fontSize: '0.62rem',
                fontWeight: 600,
                color: '#0d9488',
                textTransform: 'uppercase',
                letterSpacing: '0.4px',
                display: 'block',
                marginBottom: 4,
              }}>
                Key Insight
              </span>
              <p style={{
                fontSize: '0.85rem',
                color: 'var(--color-text)',
                margin: 0,
                lineHeight: 1.5,
              }}>
                {narrative.key_insight}
              </p>
            </div>
          )}

          {/* Behavior clusters */}
          {hasClusters && (
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 8,
              marginTop: 8,
            }}>
              {narrative.clusters.map((cluster, i) => (
                <div key={i} style={{
                  flex: '1 1 auto',
                  minWidth: '140px',
                  padding: '10px 12px',
                  background: 'var(--color-surface-muted)',
                  borderRadius: 10,
                  borderLeft: `3px solid ${cluster.direction === 'positive' ? '#0d9488' : '#d97706'}`,
                }}>
                  <span style={{
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    color: cluster.direction === 'positive' ? '#0d9488' : '#d97706',
                    display: 'block',
                    marginBottom: 4,
                  }}>
                    {cluster.theme}
                  </span>
                  <p style={{
                    fontSize: '0.78rem',
                    color: 'var(--color-text-secondary)',
                    margin: 0,
                    lineHeight: 1.4,
                  }}>
                    {cluster.description}
                  </p>
                  <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 4,
                    marginTop: 6,
                  }}>
                    {cluster.behaviors?.map((b, j) => (
                      <span key={j} style={{
                        fontSize: '0.62rem',
                        padding: '2px 6px',
                        background: 'var(--color-surface)',
                        borderRadius: 8,
                        color: 'var(--color-text-secondary)',
                        border: '1px solid var(--color-border)',
                      }}>
                        {b}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Toggle to see raw correlations */}
          {hasCorrelations && (
            <button
              onClick={() => setShowRawData(!showRawData)}
              style={{
                display: 'block',
                margin: '10px auto 0',
                padding: '4px 12px',
                borderRadius: 6,
                border: '1px solid var(--color-border)',
                background: 'transparent',
                fontSize: '0.7rem',
                color: 'var(--color-text-muted)',
                cursor: 'pointer',
              }}
            >
              {showRawData ? 'Hide details' : 'See raw patterns'}
            </button>
          )}
        </div>
      )}

      {/* Raw correlations (shown by default when no narrative, or toggled) */}
      {(!hasNarrative || showRawData) && (
        <>
          {/* Weekly insight (highlighted) */}
          {!hasNarrative && weeklyInsight && (
            <div style={{
              padding: '10px 12px',
              background: 'var(--color-surface-muted)',
              borderRadius: 10,
              marginBottom: hasCorrelations ? 12 : 0,
              borderLeft: '3px solid #0d9488',
            }}>
              <p style={{
                fontSize: '0.85rem',
                color: 'var(--color-text)',
                margin: 0,
                lineHeight: 1.5,
              }}>
                {weeklyInsight.insight_text}
              </p>
            </div>
          )}

          {/* All correlations */}
          {correlations?.map((corr, i) => {
            if (!hasNarrative && weeklyInsight && corr.insight_text === weeklyInsight.insight_text) return null;

            const isPositive = corr.direction === 'positive';
            const strength = Math.abs(corr.r || 0);
            const barWidth = Math.round(strength * 100);

            return (
              <div key={i} style={{
                padding: '8px 0',
                borderTop: i > 0 || (!hasNarrative && weeklyInsight) ? '1px solid var(--color-border-light)' : 'none',
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                }}>
                  <span style={{
                    fontSize: '0.85rem',
                    color: isPositive ? '#059669' : '#dc2626',
                    fontWeight: 600,
                    lineHeight: 1,
                    marginTop: 2,
                    flexShrink: 0,
                  }}>
                    {isPositive ? '\u2191' : '\u2193'}
                  </span>
                  <div style={{ flex: 1 }}>
                    <p style={{
                      fontSize: '0.82rem',
                      color: 'var(--color-text)',
                      margin: 0,
                      lineHeight: 1.5,
                    }}>
                      {corr.insight_text}
                    </p>
                    <div style={{
                      marginTop: 4,
                      height: 3,
                      background: 'var(--color-border-light)',
                      borderRadius: 2,
                      overflow: 'hidden',
                      maxWidth: 80,
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${barWidth}%`,
                        background: isPositive ? '#0d9488' : '#dc2626',
                        borderRadius: 2,
                        transition: 'width 0.3s ease',
                      }} />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </>
      )}

      <p style={{
        fontSize: '0.7rem',
        color: 'var(--color-text-muted)',
        margin: '10px 0 0 0',
        fontStyle: 'italic',
        textAlign: 'center',
      }}>
        These are patterns, not rules. Your journey is unique.
      </p>
    </div>
  );
}
