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
    comfort = null,
    strain_recovery = null,
    safeguards = null,
  } = trajectory;

  const stateConf = STATE_CONFIG[current_state] || STATE_CONFIG.calibrating;
  const showComfort = comfort && (comfort.comfort_verse || comfort.message);
  const showEmergency = safeguards?.emergency_override?.active;
  const showHumility = safeguards?.humility_reset?.active;

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

      {/* Category bars (only after baseline, hidden in comfort/humility mode) */}
      {baseline_established && !showComfort && !showHumility && categoryBars.length > 0 && (
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
        .mirror-note {
          font-size: 0.7rem;
          color: #9ca3af;
          font-style: italic;
          margin-top: 2px;
        }
        .comfort-section {
          margin-top: 14px;
          padding: 12px;
          background: rgba(255, 255, 255, 0.6);
          border-radius: 8px;
          text-align: center;
        }
        .comfort-verse {
          font-size: 0.95rem;
          font-style: italic;
          color: var(--deep-blue, #1e293b);
          margin: 0 0 8px 0;
          line-height: 1.5;
        }
        .comfort-ref {
          display: block;
          font-size: 0.75rem;
          color: #6b7280;
          font-style: normal;
          margin-top: 4px;
        }
        .comfort-message {
          font-size: 0.8rem;
          color: #6b7280;
          margin: 0;
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
          border-top: 1px solid rgba(0, 0, 0, 0.06);
        }
        .sr-bar-row {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 6px;
        }
        .sr-label {
          font-size: 0.7rem;
          color: #6b7280;
          width: 60px;
          flex-shrink: 0;
          text-align: right;
          text-transform: uppercase;
          letter-spacing: 0.3px;
        }
        .sr-bar-track {
          flex: 1;
          height: 6px;
          background: rgba(0, 0, 0, 0.06);
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
          color: #6b7280;
          margin: 4px 0 0 0;
          font-style: italic;
          text-align: center;
        }
      `}</style>
    </div>
  );
}
