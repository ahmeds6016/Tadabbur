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
  const isOn = !!value;
  return (
    <button
      onClick={() => onChange(value ? 0 : 1)}
      aria-label={`${label}: ${isOn ? 'Done' : 'Not done'}`}
      style={{
        width: 40,
        height: 40,
        minWidth: 40,
        borderRadius: '50%',
        border: isOn ? '2px solid #0d9488' : '2px solid #d1d5db',
        background: isOn ? '#0d9488' : '#f8fafc',
        color: isOn ? 'white' : '#cbd5e1',
        padding: 0,
        fontSize: '1.1rem',
        fontWeight: 700,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxSizing: 'border-box',
        transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        transform: isOn ? 'scale(1.05)' : 'none',
        boxShadow: isOn
          ? '0 2px 8px rgba(13, 148, 136, 0.3)'
          : 'inset 0 1px 2px rgba(0, 0, 0, 0.06)',
      }}
    >
      {isOn ? '\u2713' : ''}
    </button>
  );
}

function Scale5Input({ value, onChange, scaleLabels }) {
  const filled = value || 0;
  const [showLabel, setShowLabel] = useState(null);

  const handleTap = (n) => {
    const newVal = value === n ? 0 : n;
    onChange(newVal);
    if (newVal > 0 && scaleLabels?.[String(newVal)]) {
      setShowLabel(scaleLabels[String(newVal)]);
      setTimeout(() => setShowLabel(null), 1500);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%' }}>
      <div style={{ display: 'flex', gap: 10, position: 'relative' }}>
        {[1, 2, 3, 4, 5].map((n) => {
          const isFilled = filled >= n;
          const isCurrent = value === n;
          return (
            <button
              key={n}
              onClick={() => handleTap(n)}
              aria-label={scaleLabels?.[String(n)] || `${n} of 5`}
              style={{
                width: 32,
                height: 32,
                minWidth: 32,
                borderRadius: '50%',
                border: 'none',
                background: isFilled ? '#0d9488' : '#e8ecf1',
                cursor: 'pointer',
                padding: 0,
                boxSizing: 'border-box',
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                transform: isCurrent ? 'scale(1.12)' : 'none',
                boxShadow: isCurrent
                  ? '0 0 0 3px rgba(13, 148, 136, 0.25), 0 2px 8px rgba(13, 148, 136, 0.2)'
                  : isFilled
                    ? '0 1px 3px rgba(13, 148, 136, 0.15)'
                    : 'inset 0 1px 2px rgba(0, 0, 0, 0.06)',
              }}
            />
          );
        })}
      </div>
      {/* Tap label tooltip */}
      {showLabel && (
        <div style={{
          fontSize: '0.72rem',
          color: '#0d9488',
          fontWeight: 600,
          textAlign: 'center',
          transition: 'opacity 0.3s ease',
        }}>
          {showLabel}
        </div>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', maxWidth: 200 }}>
        <span style={{ fontSize: '0.65rem', color: '#94a3b8', fontWeight: 500 }}>
          {scaleLabels?.['1'] || 'Low'}
        </span>
        <span style={{ fontSize: '0.65rem', color: '#94a3b8', fontWeight: 500 }}>
          {scaleLabels?.['5'] || 'High'}
        </span>
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
  width: 34,
  height: 34,
  minWidth: 34,
  borderRadius: '50%',
  border: '1.5px solid #e2e8f0',
  background: '#f8fafc',
  fontSize: '1.1rem',
  fontWeight: 500,
  cursor: 'pointer',
  padding: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: '#475569',
  boxSizing: 'border-box',
  transition: 'all 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
};

function CountInput({ value, onChange }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
      <button
        style={{
          ...stepperBtnStyle,
          opacity: !value ? 0.3 : 1,
          cursor: !value ? 'default' : 'pointer',
        }}
        onClick={() => onChange(Math.max(0, (value || 0) - 1))}
        disabled={!value}
      >{'\u2212'}</button>
      <span style={{
        fontSize: '1.1rem',
        fontWeight: 700,
        minWidth: 24,
        textAlign: 'center',
        color: '#1e293b',
        fontVariantNumeric: 'tabular-nums',
      }}>
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
  const isScale = behavior.input_type === 'scale_5';

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
    <div style={{
      display: 'flex',
      flexDirection: isScale ? 'column' : 'row',
      justifyContent: isScale ? 'flex-start' : 'space-between',
      alignItems: isScale ? 'stretch' : 'center',
      gap: isScale ? 6 : 0,
      padding: '6px 0',
    }}>
      <span style={{
        fontSize: '0.9rem',
        color: '#1e293b',
        flex: isScale ? 'none' : 1,
      }}>
        {behavior.label}
      </span>
      <div style={{
        flexShrink: 0,
        marginLeft: isScale ? 0 : 12,
      }}>
        {renderInput()}
      </div>
    </div>
  );
}

export default function JournalEntry({ user, date, onTrajectoryUpdate, onSaved }) {
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
  const [quickLog, setQuickLog] = useState(() => {
    if (typeof window !== 'undefined') {
      try { return localStorage.getItem('iman_quick_log') === 'true'; } catch { return false; }
    }
    return false;
  });

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
      if (onSaved) onSaved(data);
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

  // Toggle quick-log and persist
  const toggleQuickLog = () => {
    const next = !quickLog;
    setQuickLog(next);
    if (typeof window !== 'undefined') {
      try { localStorage.setItem('iman_quick_log', String(next)); } catch {}
    }
  };

  // Group tracked behaviors by category, then by practice_group within each category
  const trackedIds = new Set(
    (config?.tracked_behaviors || [])
      .filter((b) => b.active !== false)
      .map((b) => b.id)
  );

  // Completion indicator
  const totalTracked = trackedIds.size;
  const filledCount = [...trackedIds].filter((bid) => {
    const v = values[bid];
    return v !== undefined && v !== null && v !== 0 && v !== '';
  }).length;

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

  // Filter categories for quick-log mode
  const visibleCategories = quickLog
    ? categories.filter((cat) => cat.id === 'fard')
    : categories;

  return (
    <div className="journal-entry">
      {/* Quick-log toggle + completion indicator */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 4,
      }}>
        <button
          onClick={toggleQuickLog}
          style={{
            padding: '5px 12px',
            borderRadius: 16,
            border: `1.5px solid ${quickLog ? '#0d9488' : '#e2e8f0'}`,
            background: quickLog ? '#0d948815' : 'white',
            fontSize: '0.75rem',
            fontWeight: 600,
            color: quickLog ? '#0d9488' : '#6b7280',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          {quickLog ? 'Quick Log ON' : 'Quick Log'}
        </button>
        <span style={{
          fontSize: '0.75rem',
          fontWeight: 600,
          color: filledCount === totalTracked ? '#059669' : '#9ca3af',
          background: filledCount === totalTracked ? '#ecfdf5' : '#f8fafc',
          padding: '4px 10px',
          borderRadius: 12,
          fontVariantNumeric: 'tabular-nums',
        }}>
          {filledCount}/{totalTracked} tracked
        </span>
      </div>

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
      {visibleCategories.map((cat) => {
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
          padding: 14px 18px;
          background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
          border-radius: 14px;
          border: 1px solid #a7f3d0;
          color: #065f46;
          font-size: 0.9rem;
          text-align: center;
          font-weight: 500;
          box-shadow: 0 1px 4px rgba(5, 150, 105, 0.08);
        }
        .riya-reminder {
          padding: 14px 18px;
          background: linear-gradient(135deg, #faf6f0, #fef3c7);
          border-radius: 14px;
          border: 1px solid #fde68a;
          color: #92400e;
          font-size: 0.85rem;
          text-align: center;
          font-style: italic;
          cursor: pointer;
          box-shadow: 0 1px 4px rgba(146, 64, 14, 0.06);
        }

        /* Behavior list and practice groups */
        .behavior-list {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .behavior-list :global(.practice-group) {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .behavior-list :global(.practice-group + .practice-group) {
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid #f1f5f9;
        }
        .behavior-list :global(.pg-label) {
          font-size: 0.7rem;
          font-weight: 600;
          color: #94a3b8;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          padding-bottom: 2px;
        }

        /* Minutes / Hours slider */
        .behavior-list :global(.minutes-input),
        .behavior-list :global(.hours-input) {
          display: flex;
          align-items: center;
          gap: 8px;
          width: 150px;
        }
        .behavior-list :global(.range-slider) {
          flex: 1;
          height: 4px;
          -webkit-appearance: none;
          appearance: none;
          background: #e2e8f0;
          border-radius: 2px;
          outline: none;
        }
        .behavior-list :global(.range-slider::-webkit-slider-thumb) {
          -webkit-appearance: none;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: #0d9488;
          cursor: pointer;
          box-shadow: 0 1px 4px rgba(13, 148, 136, 0.3);
        }
        .behavior-list :global(.minutes-label),
        .behavior-list :global(.hours-label) {
          font-size: 0.8rem;
          color: #64748b;
          font-weight: 500;
          width: 32px;
          text-align: right;
          font-variant-numeric: tabular-nums;
        }

        /* Heart state */
        .heart-state-section {
          padding: 20px;
          background: #fafaf8;
          border-radius: 14px;
          border: 1px solid #e8ecf1;
        }
        .section-title {
          margin: 0 0 14px 0;
          font-size: 1rem;
          font-weight: 600;
          color: #1e293b;
        }
        .heart-state-pills {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .heart-pill {
          padding: 8px 16px;
          border-radius: 24px;
          border: 1.5px solid #e2e8f0;
          background: #f8fafc;
          font-size: 0.8rem;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          color: #475569;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1px;
        }
        .heart-pill:hover {
          border-color: #94a3b8;
          background: white;
        }
        .heart-pill.active {
          color: white;
          border-color: transparent;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
          transform: scale(1.03);
        }
        .hp-label {
          font-weight: 600;
        }
        .hp-arabic {
          font-size: 0.6rem;
          opacity: 0.7;
        }
        .heart-response-card {
          margin-top: 14px;
          padding: 16px;
          background: white;
          border-radius: 12px;
          border-left: 3px solid #0d9488;
          box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
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
          padding: 16px;
          border-radius: 14px;
          border: none;
          background: #0d9488;
          color: white;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 2px 8px rgba(13, 148, 136, 0.25);
        }
        .save-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(13, 148, 136, 0.3);
        }
        .save-btn:active:not(:disabled) {
          transform: translateY(0);
          box-shadow: 0 1px 4px rgba(13, 148, 136, 0.2);
        }
        .save-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          box-shadow: none;
        }
        .save-btn.saved {
          background: #059669;
          box-shadow: 0 2px 8px rgba(5, 150, 105, 0.25);
        }
      `}</style>
    </div>
  );
}
