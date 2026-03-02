'use client';
import { useState, useEffect, useCallback } from 'react';
import CollapsibleSection from './CollapsibleSection';
import HeartNoteComposer from './HeartNoteComposer';
import { BACKEND_URL } from '../lib/config';

const HEART_STATES = [
  { id: 'grateful', label: 'Grateful', arabic: 'Shukr', color: '#059669' },
  { id: 'anxious', label: 'Anxious', arabic: 'Qalaq', color: '#d97706' },
  { id: 'grieving', label: 'Grieving', arabic: 'Huzn', color: '#64748b' },
  { id: 'spiritually_dry', label: 'Spiritually Dry', arabic: 'Qasawah', color: '#94a3b8' },
  { id: 'joyful', label: 'Joyful', arabic: 'Farah', color: '#0d9488' },
  { id: 'seeking_guidance', label: 'Seeking Guidance', arabic: 'Istikhara', color: '#2563eb' },
  { id: 'remorseful', label: 'Remorseful', arabic: 'Nadam', color: '#8b5cf6' },
];

function BinaryInput({ value, onChange, label }) {
  return (
    <button
      className={`binary-toggle ${value ? 'on' : 'off'}`}
      onClick={() => onChange(value ? 0 : 1)}
      aria-label={`${label}: ${value ? 'Done' : 'Not done'}`}
      style={{
        width: 36, height: 36, minWidth: 36, borderRadius: '50%',
        border: `2px solid ${value ? 'var(--primary-teal, #0d9488)' : 'var(--border-light, #e5e7eb)'}`,
        background: value ? 'var(--primary-teal, #0d9488)' : 'white',
        color: value ? 'white' : '#9ca3af',
        padding: 0, fontSize: '1.1rem', cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxSizing: 'border-box', transition: 'all 0.15s ease',
      }}
    >
      {value ? '\u2713' : '\u25CB'}
    </button>
  );
}

function Scale5Input({ value, onChange, scaleLabels }) {
  const filled = value || 0;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <div style={{ display: 'flex', gap: 5 }}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            onClick={() => onChange(value === n ? 0 : n)}
            aria-label={scaleLabels?.[String(n)] || `${n} of 5`}
            style={{
              width: 22, height: 22, minWidth: 22, borderRadius: '50%',
              border: `2px solid ${filled >= n ? 'var(--primary-teal, #0d9488)' : 'var(--border-light, #e5e7eb)'}`,
              background: filled >= n ? 'var(--primary-teal, #0d9488)' : 'white',
              cursor: 'pointer', padding: 0, boxSizing: 'border-box',
              transition: 'all 0.12s ease',
              transform: value === n ? 'scale(1.15)' : 'none',
              boxShadow: value === n ? '0 0 0 2px rgba(13,148,136,0.3)' : 'none',
            }}
          />
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.6rem', color: '#9ca3af' }}>{scaleLabels?.['1'] || 'Low'}</span>
        <span style={{ fontSize: '0.6rem', color: '#9ca3af' }}>{scaleLabels?.['5'] || 'High'}</span>
      </div>
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

const stepperBtnStyle = {
  width: 30, height: 30, minWidth: 30, borderRadius: 8,
  border: '1px solid var(--border-light, #e5e7eb)', background: 'white',
  fontSize: '1rem', cursor: 'pointer', padding: 0,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  color: 'var(--deep-blue, #1e293b)', boxSizing: 'border-box',
};

function CountInput({ value, onChange }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <button
        style={{ ...stepperBtnStyle, opacity: !value ? 0.3 : 1 }}
        onClick={() => onChange(Math.max(0, (value || 0) - 1))}
        disabled={!value}
      >{'\u2212'}</button>
      <span style={{ fontSize: '0.95rem', fontWeight: 600, minWidth: 20, textAlign: 'center', color: 'var(--deep-blue, #1e293b)' }}>
        {value || 0}
      </span>
      <button
        style={stepperBtnStyle}
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
        return <Scale5Input value={value || 0} onChange={onChange} scaleLabels={behavior.scale_labels} />;
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
  const [heartResponse, setHeartResponse] = useState(null);
  const [loadingResponse, setLoadingResponse] = useState(false);
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
        // Merge SR + safeguards into trajectory for TrajectoryDisplay
        const enrichedTrajectory = {
          ...data.trajectory,
          ...(data.strain_recovery ? { strain_recovery: data.strain_recovery } : {}),
          ...(data.safeguards ? { safeguards: data.safeguards } : {}),
        };
        onTrajectoryUpdate(enrichedTrajectory, data.safeguards);
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

  const handleHeartStateSelect = async (stateId) => {
    const newState = heartState === stateId ? null : stateId;
    setHeartState(newState);
    setSaved(false);
    setHeartResponse(null);

    if (newState && user) {
      setLoadingResponse(true);
      try {
        const token = await user.getIdToken();
        const res = await fetch(
          `${BACKEND_URL}/iman/heart-state/${newState}/response`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (res.ok) {
          setHeartResponse(await res.json());
        }
      } catch (err) {
        console.error('Failed to load heart state response:', err);
      } finally {
        setLoadingResponse(false);
      }
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

  // Group tracked behaviors by category, then by practice_group within each category
  const trackedIds = new Set(
    (config?.tracked_behaviors || [])
      .filter((b) => b.active !== false)
      .map((b) => b.id)
  );

  // Build practice groups per category for visual sub-grouping
  const groupedByCategory = {};
  for (const cat of categories) {
    const catBehaviors = allBehaviors.filter(
      (b) => b.category === cat.id && trackedIds.has(b.id)
    );
    // Group by practice_group preserving catalog order
    const groups = [];
    const seen = new Set();
    for (const b of catBehaviors) {
      const gid = b.practice_group || b.id;
      if (!seen.has(gid)) {
        seen.add(gid);
        groups.push({ id: gid, behaviors: catBehaviors.filter((x) => (x.practice_group || x.id) === gid) });
      }
    }
    groupedByCategory[cat.id] = groups;
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

      {/* Behavior sections grouped by category, sub-grouped by practice */}
      {categories.map((cat) => {
        const groups = groupedByCategory[cat.id] || [];
        const totalBehaviors = groups.reduce((n, g) => n + g.behaviors.length, 0);
        if (totalBehaviors === 0) return null;
        return (
          <CollapsibleSection
            key={cat.id}
            title={cat.label}
            count={totalBehaviors}
            defaultExpanded={cat.id === 'fard'}
            sectionKey={`journal-${cat.id}`}
          >
            <div className="behavior-list">
              {groups.map((group) => (
                <div key={group.id} className="practice-group">
                  {group.behaviors.length > 1 && (
                    <span className="pg-label">{group.id.replace(/_/g, ' ')}</span>
                  )}
                  {group.behaviors.map((b) => (
                    <BehaviorRow
                      key={b.id}
                      behavior={b}
                      value={values[b.id]}
                      onChange={(v) => handleValueChange(b.id, v)}
                    />
                  ))}
                </div>
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
              onClick={() => handleHeartStateSelect(hs.id)}
              style={heartState === hs.id ? { background: hs.color, borderColor: hs.color } : undefined}
            >
              <span className="hp-label">{hs.label}</span>
              <span className="hp-arabic">{hs.arabic}</span>
            </button>
          ))}
        </div>

        {/* Tailored response card */}
        {heartState && heartResponse && (
          <div className="heart-response-card" style={{ borderLeftColor: HEART_STATES.find(s => s.id === heartState)?.color }}>
            <p className="hr-verse">
              &ldquo;{heartResponse.verse?.text}&rdquo;
              <span className="hr-ref">
                &mdash; Surah {heartResponse.verse?.surah}:{heartResponse.verse?.verse}
              </span>
            </p>
            <p className="hr-insight">{heartResponse.insight}</p>
            <p className="hr-action"><strong>Try this:</strong> {heartResponse.action}</p>
            {heartResponse.guidance_excerpts?.length > 0 && (
              <details className="hr-excerpts">
                <summary className="hr-excerpts-label">From the scholars</summary>
                {heartResponse.guidance_excerpts.slice(0, 2).map((g, i) => (
                  <div key={i} className="hr-excerpt">
                    <span className="hr-source">{g.source}: {g.title}</span>
                    <p className="hr-text">{g.text?.slice(0, 400)}{g.text?.length > 400 ? '...' : ''}</p>
                  </div>
                ))}
              </details>
            )}
          </div>
        )}
        {heartState && loadingResponse && (
          <p className="hr-loading">Loading spiritual guidance...</p>
        )}
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

        /* Practice group sub-headings */
        .behavior-list :global(.practice-group) {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .behavior-list :global(.practice-group + .practice-group) {
          margin-top: 8px;
          padding-top: 8px;
          border-top: 1px solid rgba(0, 0, 0, 0.04);
        }
        .behavior-list :global(.pg-label) {
          font-size: 0.65rem;
          font-weight: 600;
          color: #9ca3af;
          text-transform: uppercase;
          letter-spacing: 0.4px;
          margin-bottom: -4px;
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
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1px;
        }
        .heart-pill:hover {
          border-color: #9ca3af;
        }
        .heart-pill.active {
          color: white;
        }
        .hp-label {
          font-weight: 500;
        }
        .hp-arabic {
          font-size: 0.6rem;
          opacity: 0.7;
        }
        .heart-response-card {
          margin-top: 12px;
          padding: 14px;
          background: white;
          border-radius: 10px;
          border-left: 3px solid #0d9488;
        }
        .hr-verse {
          font-size: 0.88rem;
          font-style: italic;
          color: var(--deep-blue, #1e293b);
          margin: 0 0 10px 0;
          line-height: 1.5;
        }
        .hr-ref {
          display: block;
          font-size: 0.7rem;
          color: #6b7280;
          font-style: normal;
          margin-top: 4px;
        }
        .hr-insight {
          font-size: 0.82rem;
          color: #374151;
          margin: 0 0 8px 0;
          line-height: 1.5;
        }
        .hr-action {
          font-size: 0.82rem;
          color: #374151;
          margin: 0 0 10px 0;
          line-height: 1.5;
        }
        .hr-excerpts {
          margin-top: 8px;
        }
        .hr-excerpts-label {
          font-size: 0.75rem;
          font-weight: 600;
          color: #6b7280;
          cursor: pointer;
        }
        .hr-excerpt {
          margin-top: 8px;
          padding: 10px;
          background: #f8fafc;
          border-radius: 6px;
        }
        .hr-source {
          font-size: 0.7rem;
          font-weight: 600;
          color: #9ca3af;
          display: block;
          margin-bottom: 4px;
        }
        .hr-text {
          font-size: 0.78rem;
          color: #4b5563;
          margin: 0;
          line-height: 1.5;
        }
        .hr-loading {
          font-size: 0.8rem;
          color: #9ca3af;
          font-style: italic;
          margin: 8px 0 0 0;
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
