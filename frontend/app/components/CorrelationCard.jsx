'use client';

export default function CorrelationCard({ correlations, weeklyInsight }) {
  if ((!correlations || correlations.length === 0) && !weeklyInsight) return null;

  return (
    <div style={{
      background: 'white',
      borderRadius: 14,
      border: '1px solid #e5e7eb',
      padding: '16px',
    }}>
      <div style={{
        fontSize: '0.7rem',
        fontWeight: 600,
        color: '#9ca3af',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        marginBottom: 12,
      }}>
        Patterns Observed
      </div>

      {/* Weekly insight (highlighted) */}
      {weeklyInsight && (
        <div style={{
          padding: '10px 12px',
          background: '#f0fdf4',
          borderRadius: 10,
          marginBottom: correlations?.length > 0 ? 12 : 0,
          borderLeft: '3px solid #0d9488',
        }}>
          <p style={{
            fontSize: '0.85rem',
            color: '#1e293b',
            margin: 0,
            lineHeight: 1.5,
          }}>
            {weeklyInsight.insight_text}
          </p>
        </div>
      )}

      {/* All correlations */}
      {correlations?.map((corr, i) => {
        // Skip if same as weekly insight
        if (weeklyInsight && corr.insight_text === weeklyInsight.insight_text) return null;

        const isPositive = corr.direction === 'positive';
        const strength = Math.abs(corr.r || 0);
        const barWidth = Math.round(strength * 100);

        return (
          <div key={i} style={{
            padding: '8px 0',
            borderTop: i > 0 || weeklyInsight ? '1px solid #f3f4f6' : 'none',
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
                  color: '#374151',
                  margin: 0,
                  lineHeight: 1.5,
                }}>
                  {corr.insight_text}
                </p>
                {/* Strength bar */}
                <div style={{
                  marginTop: 4,
                  height: 3,
                  background: '#f3f4f6',
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

      <p style={{
        fontSize: '0.7rem',
        color: '#9ca3af',
        margin: '10px 0 0 0',
        fontStyle: 'italic',
        textAlign: 'center',
      }}>
        These are patterns, not rules. Your journey is unique.
      </p>
    </div>
  );
}
