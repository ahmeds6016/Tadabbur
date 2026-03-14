'use client';

const STATE_CONFIG = {
  ascending:      { arrow: '↑', label: 'Ascending',      bg: '#ecfdf5' },
  gently_rising:  { arrow: '↗', label: 'Gently Rising',  bg: '#f0fdf4' },
  steady:         { arrow: '→', label: 'Steady',          bg: '#fffbeb' },
  recalibrating:  { arrow: '↻', label: 'Recalibrating',  bg: '#fef3c7' },
  calibrating:    { arrow: '◎', label: 'Calibrating',     bg: '#f0f9ff' },
};

const VOL_LABELS = {
  stable:    'Stable',
  dynamic:   'Dynamic',
  turbulent: 'Turbulent',
};

const TREND_ARROWS = {
  improving: { symbol: '↑', color: '#059669' },
  stable: { symbol: '→', color: '#6b7280' },
  declining: { symbol: '↓', color: '#d97706' },
};

export default function TrajectoryDisplay({ trajectory, categories = [] }) {
  if (!trajectory) return null;

  const {
    current_state,
    volatility_state,
    composite_display,
    color,
    days_logged = 0,
    baseline_established,
    calibration_days_remaining = 0,
    category_scores = {},
    category_trends = {},
    weekly_composites = [],
    milestones = [],
    growth_edges = [],
    comfort = null,
    strain_recovery = null,
    safeguards = null,
  } = trajectory;

  const stateConf = STATE_CONFIG[current_state] || STATE_CONFIG.calibrating;
  const showComfort = comfort && (comfort.comfort_verse || comfort.message);
  const showEmergency = safeguards?.emergency_override?.active;
  const showHumility = safeguards?.humility_reset?.active;

  // Build category bar data with trends
  const categoryBars = categories.map((cat) => {
    const scores = category_scores[cat.id] || {};
    const trend = category_trends[cat.id] || {};
    return {
      id: cat.id,
      label: cat.label,
      color: cat.color,
      composite: scores.composite || 0,
      performance: scores.performance || 0,
      consistency: scores.consistency || 0,
      trajectory: scores.trajectory || 0,
      isGrowthEdge: growth_edges.includes(cat.id),
      trend: trend.trend || null,
      trendDelta: trend.delta || 0,
    };
  });

  // Compute weekly sparkline from weekly_composites
  const sparklineData = weekly_composites.length >= 2 ? weekly_composites : null;

  // Emergency override replaces ALL content
  if (showEmergency) {
    const eo = safeguards.emergency_override;
    return (
      <div className="trajectory-display" style={{ background: '#fef2f2' }}>
        <div className="emergency-section">
          <p className="emergency-verse">"{eo.verse?.text}"</p>
          <span className="emergency-ref">
            — Surah {eo.verse?.surah}:{eo.verse?.verse}
          </span>
          <p className="emergency-message">{eo.message}</p>
        </div>
        <style jsx>{`
          .trajectory-display {
            padding: 16px;
            border-radius: 12px;
            border: 1px solid #fecaca;
          }
          .emergency-section {
            text-align: center;
            padding: 12px 0;
          }
          .emergency-verse {
            font-size: 1.05rem;
            font-style: italic;
            color: var(--deep-blue, #1e293b);
            margin: 0 0 8px 0;
            line-height: 1.6;
          }
          .emergency-ref {
            font-size: 0.75rem;
            color: #6b7280;
            display: block;
            margin-bottom: 12px;
          }
          .emergency-message {
            font-size: 0.85rem;
            color: #6b7280;
            margin: 0;
            line-height: 1.5;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="trajectory-display" style={{ background: stateConf.bg }}>
      {/* Main state indicator */}
      <div className="state-row">
        <span className="state-arrow" style={{ color: color || '#0d9488' }}>
          {stateConf.arrow}
        </span>
        <div className="state-text">
          <span className="state-label" style={{ color: color || '#0d9488' }}>
            {composite_display || stateConf.label}
          </span>
          <span className="state-sub">
            {baseline_established
              ? `Day ${days_logged} — ${VOL_LABELS[volatility_state] || ''}`
              : `Day ${days_logged} of 14 — Building your baseline`
            }
          </span>
          <span className="mirror-note">A mirror, not a measure</span>
        </div>
      </div>

      {/* Comfort mode: verse replaces bars when recalibrating 14+ days */}
      {showComfort && (
        <div className="comfort-section">
          <p className="comfort-verse">
            "{comfort.comfort_verse?.text}"
            <span className="comfort-ref">
              — Surah {comfort.comfort_verse?.surah}:{comfort.comfort_verse?.verse}
            </span>
          </p>
          <p className="comfort-message">{comfort.message}</p>
        </div>
      )}

      {/* Calibration progress bar */}
      {!baseline_established && (
        <div className="calibration-bar">
          <div
            className="calibration-fill"
            style={{ width: `${Math.min((days_logged / 14) * 100, 100)}%` }}
          />
        </div>
      )}

      {/* Humility reset overlay (replaces category bars + SR) */}
      {showHumility && (
        <div className="humility-overlay">
          <p className="humility-title">{safeguards.humility_reset.message}</p>
          <p className="humility-hadith">{safeguards.humility_reset.hadith}</p>
          <p className="humility-instruction">{safeguards.humility_reset.instruction}</p>
        </div>
      )}

      {/* Weekly trend sparkline (after baseline) */}
      {baseline_established && !showComfort && !showHumility && sparklineData && (
        <div className="sparkline-section">
          <span className="sparkline-label">Weekly trend</span>
          <div className="sparkline-container">
            {sparklineData.map((val, i) => {
              const min = Math.min(...sparklineData);
              const max = Math.max(...sparklineData);
              const range = max - min || 1;
              const height = Math.max(4, ((val - min) / range) * 28);
              const isLast = i === sparklineData.length - 1;
              return (
                <div
                  key={i}
                  className="sparkline-bar"
                  style={{
                    height: `${height}px`,
                    backgroundColor: isLast ? (color || '#0d9488') : '#d1d5db',
                    opacity: isLast ? 1 : 0.5,
                  }}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Category bars with trends (only after baseline, hidden in comfort/humility mode) */}
      {baseline_established && !showComfort && !showHumility && categoryBars.length > 0 && (
        <div className="category-bars">
          {categoryBars.map((bar) => {
            // Scale composite from [-1, 1] to visual width [0, 100]
            const visual = Math.max(0, Math.min(100, (bar.composite + 1) * 50));
            const trendInfo = bar.trend ? TREND_ARROWS[bar.trend] : null;
            return (
              <div key={bar.id} className={`cat-bar-row ${bar.isGrowthEdge ? 'growth-edge' : ''}`}>
                <span className="cat-label">
                  {bar.label}
                  {trendInfo && (
                    <span className="cat-trend" style={{ color: trendInfo.color }}>
                      {' '}{trendInfo.symbol}
                    </span>
                  )}
                </span>
                <div className="cat-bar-track">
                  <div
                    className="cat-bar-fill"
                    style={{ width: `${visual}%`, backgroundColor: bar.color }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Milestones */}
      {baseline_established && !showComfort && !showHumility && milestones.length > 0 && (
        <div className="milestones-section">
          {milestones.map((m, i) => (
            <span key={i} className="milestone-pill">
              {m.type === 'peak' ? '★' : m.type === 'streak' ? '🏅' : '◎'} {m.text}
            </span>
          ))}
        </div>
      )}

      {/* Strain/Recovery bars (after baseline, hidden in comfort/humility mode) */}
      {baseline_established && !showComfort && !showHumility && strain_recovery && (
        <div className="sr-section">
          <div className="sr-bar-row">
            <span className="sr-label">Strain</span>
            <div className="sr-bar-track">
              <div
                className="sr-bar-fill strain"
                style={{ width: `${strain_recovery.strain_pct}%` }}
              />
            </div>
          </div>
          <div className="sr-bar-row">
            <span className="sr-label">Recovery</span>
            <div className="sr-bar-track">
              <div
                className="sr-bar-fill recovery"
                style={{ width: `${strain_recovery.recovery_pct}%` }}
              />
            </div>
          </div>
          {strain_recovery.status_message && (
            <p className="sr-status-msg">{strain_recovery.status_message}</p>
          )}
        </div>
      )}

      <style jsx>{`
        .trajectory-display {
          padding: 16px;
          border-radius: 12px;
          border: 1px solid var(--color-border);
        }
        .state-row {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .state-arrow {
          font-size: 2rem;
          line-height: 1;
        }
        .state-text {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .state-label {
          font-size: 1.1rem;
          font-weight: 600;
        }
        .state-sub {
          font-size: 0.8rem;
          color: var(--color-text-secondary);
        }
        .mirror-note {
          font-size: 0.7rem;
          color: var(--color-text-muted);
          font-style: italic;
          margin-top: 2px;
        }
        .comfort-section {
          margin-top: 14px;
          padding: 12px;
          background: var(--color-surface-muted);
          border-radius: 8px;
          text-align: center;
        }
        .comfort-verse {
          font-size: 0.95rem;
          font-style: italic;
          color: var(--color-text);
          margin: 0 0 8px 0;
          line-height: 1.5;
        }
        .comfort-ref {
          display: block;
          font-size: 0.75rem;
          color: var(--color-text-secondary);
          font-style: normal;
          margin-top: 4px;
        }
        .comfort-message {
          font-size: 0.8rem;
          color: var(--color-text-secondary);
          margin: 0;
        }
        .calibration-bar {
          margin-top: 12px;
          height: 6px;
          background: var(--color-border-light);
          border-radius: 3px;
          overflow: hidden;
        }
        .calibration-fill {
          height: 100%;
          background: var(--color-secondary, #0d9488);
          border-radius: 3px;
          transition: width 0.3s ease;
        }
        .category-bars {
          margin-top: 14px;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .cat-bar-row {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .cat-bar-row.growth-edge .cat-label {
          font-weight: 600;
        }
        .cat-label {
          font-size: 0.75rem;
          color: var(--color-text-secondary);
          width: 110px;
          flex-shrink: 0;
          text-align: right;
        }
        .cat-bar-track {
          flex: 1;
          height: 8px;
          background: var(--color-border-light);
          border-radius: 4px;
          overflow: hidden;
        }
        .cat-bar-fill {
          height: 100%;
          border-radius: 4px;
          transition: width 0.4s ease;
          min-width: 2px;
        }
        .cat-trend {
          font-size: 0.7rem;
          font-weight: 600;
        }

        /* Sparkline */
        .sparkline-section {
          margin-top: 12px;
          margin-bottom: 4px;
          display: flex;
          align-items: flex-end;
          gap: 8px;
        }
        .sparkline-label {
          font-size: 0.65rem;
          color: var(--color-text-muted);
          text-transform: uppercase;
          letter-spacing: 0.3px;
          width: 70px;
          flex-shrink: 0;
          text-align: right;
          padding-bottom: 2px;
        }
        .sparkline-container {
          display: flex;
          align-items: flex-end;
          gap: 3px;
          flex: 1;
          height: 32px;
        }
        .sparkline-bar {
          width: 12px;
          border-radius: 2px;
          transition: height 0.3s ease;
        }

        /* Milestones */
        .milestones-section {
          margin-top: 10px;
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        .milestone-pill {
          font-size: 0.68rem;
          padding: 3px 8px;
          background: rgba(13, 148, 136, 0.08);
          border-radius: 10px;
          color: #0d9488;
          font-weight: 500;
        }

        /* Humility Reset */
        .humility-overlay {
          margin-top: 14px;
          padding: 16px;
          background: #fffbeb;
          border-radius: 10px;
          text-align: center;
          border: 1px solid #fde68a;
        }
        .humility-title {
          font-size: 1.1rem;
          font-weight: 600;
          color: #92400e;
          margin: 0 0 8px 0;
        }
        .humility-hadith {
          font-size: 0.85rem;
          font-style: italic;
          color: #78350f;
          margin: 0 0 8px 0;
          line-height: 1.5;
        }
        .humility-instruction {
          font-size: 0.8rem;
          color: #92400e;
          margin: 0;
        }

        /* Strain/Recovery */
        .sr-section {
          margin-top: 14px;
          padding-top: 10px;
          border-top: 1px solid var(--color-border-light);
        }
        .sr-bar-row {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 6px;
        }
        .sr-label {
          font-size: 0.7rem;
          color: var(--color-text-secondary);
          width: 60px;
          flex-shrink: 0;
          text-align: right;
          text-transform: uppercase;
          letter-spacing: 0.3px;
        }
        .sr-bar-track {
          flex: 1;
          height: 6px;
          background: var(--color-border-light);
          border-radius: 3px;
          overflow: hidden;
        }
        .sr-bar-fill {
          height: 100%;
          border-radius: 3px;
          transition: width 0.4s ease;
          min-width: 2px;
        }
        .sr-bar-fill.strain {
          background: #d97706;
        }
        .sr-bar-fill.recovery {
          background: #0d9488;
        }
        .sr-status-msg {
          font-size: 0.75rem;
          color: var(--color-text-secondary);
          margin: 4px 0 0 0;
          font-style: italic;
          text-align: center;
        }
      `}</style>
    </div>
  );
}
