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
    growth_edges = [],
  } = trajectory;

  const stateConf = STATE_CONFIG[current_state] || STATE_CONFIG.calibrating;

  // Build category bar data
  const categoryBars = categories.map((cat) => {
    const scores = category_scores[cat.id] || {};
    return {
      id: cat.id,
      label: cat.label,
      color: cat.color,
      composite: scores.composite || 0,
      performance: scores.performance || 0,
      consistency: scores.consistency || 0,
      trajectory: scores.trajectory || 0,
      isGrowthEdge: growth_edges.includes(cat.id),
    };
  });

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
        </div>
      </div>

      {/* Calibration progress bar */}
      {!baseline_established && (
        <div className="calibration-bar">
          <div
            className="calibration-fill"
            style={{ width: `${Math.min((days_logged / 14) * 100, 100)}%` }}
          />
        </div>
      )}

      {/* Category bars (only after baseline) */}
      {baseline_established && categoryBars.length > 0 && (
        <div className="category-bars">
          {categoryBars.map((bar) => {
            // Scale composite from [-1, 1] to visual width [0, 100]
            const visual = Math.max(0, Math.min(100, (bar.composite + 1) * 50));
            return (
              <div key={bar.id} className={`cat-bar-row ${bar.isGrowthEdge ? 'growth-edge' : ''}`}>
                <span className="cat-label">{bar.label}</span>
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

      <style jsx>{`
        .trajectory-display {
          padding: 16px;
          border-radius: 12px;
          border: 1px solid var(--border-light, #e5e7eb);
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
          color: #6b7280;
        }
        .calibration-bar {
          margin-top: 12px;
          height: 6px;
          background: rgba(0, 0, 0, 0.06);
          border-radius: 3px;
          overflow: hidden;
        }
        .calibration-fill {
          height: 100%;
          background: var(--primary-teal, #0d9488);
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
          color: #6b7280;
          width: 110px;
          flex-shrink: 0;
          text-align: right;
        }
        .cat-bar-track {
          flex: 1;
          height: 8px;
          background: rgba(0, 0, 0, 0.06);
          border-radius: 4px;
          overflow: hidden;
        }
        .cat-bar-fill {
          height: 100%;
          border-radius: 4px;
          transition: width 0.4s ease;
          min-width: 2px;
        }
      `}</style>
    </div>
  );
}
