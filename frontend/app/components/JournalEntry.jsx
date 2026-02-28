'use client';
import { useState, useEffect, useCallback } from 'react';
import CollapsibleSection from './CollapsibleSection';
import HeartNoteComposer from './HeartNoteComposer';
import { BACKEND_URL } from '../lib/config';

const HEART_STATES = [
  { id: 'grateful', label: 'Grateful' },
  { id: 'peaceful', label: 'Peaceful' },
  { id: 'anxious', label: 'Anxious' },
  { id: 'struggling', label: 'Struggling' },
  { id: 'hopeful', label: 'Hopeful' },
  { id: 'spiritually_dry', label: 'Spiritually Dry' },
  { id: 'content', label: 'Content' },
];

function BinaryInput({ value, onChange, label }) {
  return (
    <button
      className={`binary-toggle ${value ? 'on' : 'off'}`}
      onClick={() => onChange(value ? 0 : 1)}
      aria-label={`${label}: ${value ? 'Done' : 'Not done'}`}
    >
      {value ? '✓' : '○'}
    </button>
  );
}

function Scale5Input({ value, onChange }) {
  return (
    <div className="scale5-dots">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          className={`scale-dot ${(value || 0) >= n ? 'filled' : ''}`}
          onClick={() => onChange(value === n ? 0 : n)}
          aria-label={`${n} of 5`}
        />
      ))}
    </div>
  );
}

function MinutesInput({ value, onChange }) {
  return (
    <div className="minutes-input">
      <input
        type="range"
        min="0"
        max="120"
        step="5"
        value={value || 0}
        onChange={(e) => onChange(Number(e.target.value))}
        className="range-slider"
      />
      <span className="minutes-label">{value || 0}m</span>
    </div>
  );
}

function HoursInput({ value, onChange }) {
  return (
    <div className="hours-input">
      <input
        type="range"
        min="0"
        max="14"
        step="0.5"
        value={value || 0}
        onChange={(e) => onChange(Number(e.target.value))}
        className="range-slider"
      />
      <span className="hours-label">{value || 0}h</span>
    </div>
  );
}

function CountInput({ value, onChange }) {
  return (
    <div className="count-stepper">
      <button
        className="stepper-btn"
        onClick={() => onChange(Math.max(0, (value || 0) - 1))}
        disabled={!value}
      >−</button>
      <span className="count-value">{value || 0}</span>
      <button
        className="stepper-btn"
        onClick={() => onChange(Math.min(100, (value || 0) + 1))}
      >+</button>
    </div>
  );
}

function BehaviorRow({ behavior, value, onChange }) {
  const renderInput = () => {
    switch (behavior.input_type) {
      case 'binary':
        return <BinaryInput value={value || 0} onChange={onChange} label={behavior.label} />;
      case 'scale_5':
        return <Scale5Input value={value || 0} onChange={onChange} />;
      case 'minutes':
        return <MinutesInput value={value || 0} onChange={onChange} />;
      case 'hours':
        return <HoursInput value={value || 0} onChange={onChange} />;
      case 'count':
      case 'count_inv':
        return <CountInput value={value || 0} onChange={onChange} />;
      default:
        return null;
    }
  };

  return (
    <div className="behavior-row">
      <span className="behavior-label">{behavior.label}</span>
      <div className="behavior-input">{renderInput()}</div>
    </div>
  );
}

export default function JournalEntry({ user, date, onTrajectoryUpdate }) {
  const [config, setConfig] = useState(null);
  const [categories, setCategories] = useState([]);
  const [allBehaviors, setAllBehaviors] = useState([]);
  const [values, setValues] = useState({});
  const [heartState, setHeartState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [welcomeBack, setWelcomeBack] = useState(null);
  const [riyaReminder, setRiyaReminder] = useState(false);

  // Fetch config and existing log
  useEffect(() => {
    if (!user || !date) return;
    let cancelled = false;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = await user.getIdToken();
        const headers = { Authorization: `Bearer ${token}` };

        // Fetch config + today's log in parallel
        const [configRes, logRes] = await Promise.all([
          fetch(`${BACKEND_URL}/iman/config`, { headers }),
          fetch(`${BACKEND_URL}/iman/log/${date}`, { headers }),
        ]);

        if (configRes.status === 404) {
          // Not set up yet — auto-setup with defaults
          const setupRes = await fetch(`${BACKEND_URL}/iman/setup`, {
            method: 'POST',
            headers: { ...headers, 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
          });
          if (!setupRes.ok) throw new Error('Setup failed');
          // Re-fetch config
          const retryRes = await fetch(`${BACKEND_URL}/iman/config`, { headers });
          if (!retryRes.ok) throw new Error('Config fetch failed');
          const retryData = await retryRes.json();
          if (!cancelled) {
            setConfig(retryData.config);
            setCategories(retryData.categories || []);
            setAllBehaviors(retryData.all_behaviors || []);
          }
        } else if (configRes.ok) {
          const configData = await configRes.json();
          if (!cancelled) {
            setConfig(configData.config);
            setCategories(configData.categories || []);
            setAllBehaviors(configData.all_behaviors || []);
          }
        } else {
          throw new Error(`Config error: ${configRes.status}`);
        }

        // Pre-fill from existing log
        if (logRes.ok) {
          const logData = await logRes.json();
          if (!cancelled && logData.log) {
            const existingValues = {};
            const behaviors = logData.log.behaviors || {};
            for (const [bid, bval] of Object.entries(behaviors)) {
              existingValues[bid] = typeof bval === 'object' ? bval.value : bval;
            }
            setValues(existingValues);
            setHeartState(logData.log.heart_state || null);
          }
        }
      } catch (err) {
        console.error('JournalEntry fetch error:', err);
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchData();
    return () => { cancelled = true; };
  }, [user, date]);

  const handleValueChange = useCallback((behaviorId, newValue) => {
    setValues((prev) => ({ ...prev, [behaviorId]: newValue }));
    setSaved(false);
  }, []);

  const handleSave = async () => {
    if (!user || saving) return;
    setSaving(true);
    setError(null);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/log`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          date,
          behaviors: values,
          heart_state: heartState,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `Save failed (${res.status})`);
      }

      const data = await res.json();
      setSaved(true);
      if (data.trajectory && onTrajectoryUpdate) {
        onTrajectoryUpdate(data.trajectory);
      }
      if (data.welcome_back) setWelcomeBack(data.welcome_back);
      if (data.anti_riya_reminder) setRiyaReminder(true);
    } catch (err) {
      console.error('Save error:', err);
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleHeartNote = async (note) => {
    if (!user) return;
    const token = await user.getIdToken();
    const res = await fetch(`${BACKEND_URL}/iman/heart-note`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(note),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error || 'Failed to save note');
    }
  };

  if (loading) {
    return <div className="journal-loading">Loading journal...</div>;
  }

  if (error && !config) {
    return <div className="journal-error">{error}</div>;
  }

  // Group tracked behaviors by category
  const trackedIds = new Set(
    (config?.tracked_behaviors || [])
      .filter((b) => b.active !== false)
      .map((b) => b.id)
  );
  const behaviorsByCategory = {};
  for (const cat of categories) {
    behaviorsByCategory[cat.id] = allBehaviors.filter(
      (b) => b.category === cat.id && trackedIds.has(b.id)
    );
  }

  return (
    <div className="journal-entry">
      {/* Welcome-back banner */}
      {welcomeBack && (
        <div className="welcome-back-banner">{welcomeBack}</div>
      )}

      {/* Anti-riya reminder toast */}
      {riyaReminder && (
        <div className="riya-reminder" onClick={() => setRiyaReminder(false)}>
          This is a mirror, not a measure. Your journey is known only to Allah.
        </div>
      )}

      {/* Behavior sections grouped by category */}
      {categories.map((cat) => {
        const catBehaviors = behaviorsByCategory[cat.id] || [];
        if (catBehaviors.length === 0) return null;
        return (
          <CollapsibleSection
            key={cat.id}
            title={cat.label}
            count={catBehaviors.length}
            defaultExpanded={cat.id === 'fard'}
            sectionKey={`journal-${cat.id}`}
          >
            <div className="behavior-list">
              {catBehaviors.map((b) => (
                <BehaviorRow
                  key={b.id}
                  behavior={b}
                  value={values[b.id]}
                  onChange={(v) => handleValueChange(b.id, v)}
                />
              ))}
            </div>
          </CollapsibleSection>
        );
      })}

      {/* Heart state picker */}
      <div className="heart-state-section">
        <h3 className="section-title">How is your heart today?</h3>
        <div className="heart-state-pills">
          {HEART_STATES.map((hs) => (
            <button
              key={hs.id}
              className={`heart-pill ${heartState === hs.id ? 'active' : ''}`}
              onClick={() => setHeartState(heartState === hs.id ? null : hs.id)}
            >
              {hs.label}
            </button>
          ))}
        </div>
      </div>

      {/* Heart Note Composer */}
      <HeartNoteComposer onSave={handleHeartNote} disabled={saving} />

      {/* Save button */}
      <div className="save-area">
        {error && <p className="save-error">{error}</p>}
        <button
          className={`save-btn ${saved ? 'saved' : ''}`}
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : saved ? 'Saved ✓' : 'Save Journal Entry'}
        </button>
      </div>

      <style jsx>{`
        .journal-entry {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .journal-loading, .journal-error {
          text-align: center;
          padding: 40px 20px;
          color: #6b7280;
          font-size: 0.95rem;
        }
        .journal-error {
          color: #ef4444;
        }
        .welcome-back-banner {
          padding: 12px 16px;
          background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
          border-radius: 10px;
          border: 1px solid #a7f3d0;
          color: #065f46;
          font-size: 0.9rem;
          text-align: center;
          font-weight: 500;
        }
        .riya-reminder {
          padding: 12px 16px;
          background: linear-gradient(135deg, #faf6f0, #fef3c7);
          border-radius: 10px;
          border: 1px solid #fde68a;
          color: #92400e;
          font-size: 0.85rem;
          text-align: center;
          font-style: italic;
          cursor: pointer;
        }

        /* Behavior rows */
        .behavior-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .behavior-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 4px 0;
        }
        .behavior-label {
          font-size: 0.9rem;
          color: var(--deep-blue, #1e293b);
          flex: 1;
        }
        .behavior-input {
          flex-shrink: 0;
          margin-left: 12px;
        }

        /* Binary toggle */
        .behavior-row :global(.binary-toggle) {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border: 2px solid var(--border-light, #e5e7eb);
          background: white;
          font-size: 1.1rem;
          cursor: pointer;
          transition: all 0.15s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #9ca3af;
        }
        .behavior-row :global(.binary-toggle.on) {
          background: var(--primary-teal, #0d9488);
          border-color: var(--primary-teal, #0d9488);
          color: white;
        }

        /* Scale 5 dots */
        .behavior-row :global(.scale5-dots) {
          display: flex;
          gap: 6px;
        }
        .behavior-row :global(.scale-dot) {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          border: 2px solid var(--border-light, #e5e7eb);
          background: white;
          cursor: pointer;
          transition: all 0.12s ease;
          padding: 0;
        }
        .behavior-row :global(.scale-dot.filled) {
          background: var(--primary-teal, #0d9488);
          border-color: var(--primary-teal, #0d9488);
        }

        /* Minutes / Hours slider */
        .behavior-row :global(.minutes-input),
        .behavior-row :global(.hours-input) {
          display: flex;
          align-items: center;
          gap: 8px;
          width: 140px;
        }
        .behavior-row :global(.range-slider) {
          flex: 1;
          height: 4px;
          -webkit-appearance: none;
          appearance: none;
          background: var(--border-light, #e5e7eb);
          border-radius: 2px;
          outline: none;
        }
        .behavior-row :global(.range-slider::-webkit-slider-thumb) {
          -webkit-appearance: none;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: var(--primary-teal, #0d9488);
          cursor: pointer;
        }
        .behavior-row :global(.minutes-label),
        .behavior-row :global(.hours-label) {
          font-size: 0.8rem;
          color: #6b7280;
          width: 32px;
          text-align: right;
        }

        /* Count stepper */
        .behavior-row :global(.count-stepper) {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .behavior-row :global(.stepper-btn) {
          width: 28px;
          height: 28px;
          border-radius: 6px;
          border: 1px solid var(--border-light, #e5e7eb);
          background: white;
          font-size: 1rem;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--deep-blue, #1e293b);
        }
        .behavior-row :global(.stepper-btn:disabled) {
          opacity: 0.3;
          cursor: not-allowed;
        }
        .behavior-row :global(.count-value) {
          font-size: 0.95rem;
          font-weight: 600;
          min-width: 20px;
          text-align: center;
          color: var(--deep-blue, #1e293b);
        }

        /* Heart state */
        .heart-state-section {
          padding: 16px;
          background: var(--cream, #faf6f0);
          border-radius: 12px;
          border: 1px solid var(--border-light, #e5e7eb);
        }
        .section-title {
          margin: 0 0 10px 0;
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--deep-blue, #1e293b);
        }
        .heart-state-pills {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .heart-pill {
          padding: 6px 14px;
          border-radius: 20px;
          border: 1px solid var(--border-light, #e5e7eb);
          background: white;
          font-size: 0.8rem;
          cursor: pointer;
          transition: all 0.15s ease;
          color: #374151;
        }
        .heart-pill:hover {
          border-color: #8B5CF6;
        }
        .heart-pill.active {
          background: #8B5CF6;
          color: white;
          border-color: #8B5CF6;
        }

        /* Save area */
        .save-area {
          padding-top: 8px;
        }
        .save-error {
          color: #ef4444;
          font-size: 0.85rem;
          margin-bottom: 8px;
        }
        .save-btn {
          width: 100%;
          padding: 14px;
          border-radius: 12px;
          border: none;
          background: var(--primary-teal, #0d9488);
          color: white;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .save-btn:hover:not(:disabled) {
          opacity: 0.9;
        }
        .save-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .save-btn.saved {
          background: #059669;
        }
      `}</style>
    </div>
  );
}
