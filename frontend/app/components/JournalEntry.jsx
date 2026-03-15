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

/* ── Binary toggle: compact square checkbox ── */
function BinaryInput({ value, onChange, label }) {
  const isOn = !!value;
  return (
    <button
      onClick={() => onChange(value ? 0 : 1)}
      aria-label={`${label}: ${isOn ? 'Done' : 'Not done'}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 5,
        padding: '3px 8px 3px 4px',
        borderRadius: 6,
        border: isOn ? '1.5px solid #0d9488' : '1.5px solid var(--color-border, #d1d5db)',
        background: isOn ? 'rgba(13, 148, 136, 0.08)' : 'transparent',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
      }}
    >
      <span style={{
        width: 16,
        height: 16,
        minWidth: 16,
        borderRadius: 3,
        border: isOn ? '1.5px solid #0d9488' : '1.5px solid var(--color-border, #cbd5e1)',
        background: isOn ? '#0d9488' : 'transparent',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'all 0.12s ease',
        color: 'white',
        fontSize: '0.6rem',
        fontWeight: 700,
      }}>
        {isOn ? '\u2713' : ''}
      </span>
      <span style={{
        fontSize: '0.7rem',
        fontWeight: 600,
        color: isOn ? '#0d9488' : 'var(--color-text-muted, #9ca3af)',
        transition: 'color 0.12s ease',
        userSelect: 'none',
        lineHeight: 1,
      }}>
        {isOn ? 'Completed' : 'Mark'}
      </span>
    </button>
  );
}

/* ── Scale 1-5: numbered steps with anchor labels ── */
function Scale5Input({ value, onChange, scaleLabels }) {
  const current = value || 0;
  const lowLabel = scaleLabels?.['1'] || 'Low';
  const highLabel = scaleLabels?.['5'] || 'High';
  const selectedLabel = current > 0 ? (scaleLabels?.[String(current)] || `${current}/5`) : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3, width: '100%' }}>
      {/* Numbered step buttons */}
      <div style={{ display: 'flex', gap: 6 }}>
        {[1, 2, 3, 4, 5].map((n) => {
          const isSelected = current === n;
          return (
            <button
              key={n}
              onClick={() => onChange(current === n ? 0 : n)}
              aria-label={scaleLabels?.[String(n)] || `${n} of 5`}
              style={{
                width: 36,
                height: 32,
                minWidth: 36,
                borderRadius: 6,
                border: isSelected
                  ? '1.5px solid #0d9488'
                  : '1px solid var(--color-border, #e2e8f0)',
                background: isSelected ? '#0d9488' : 'var(--color-surface-muted, #f5f5f5)',
                color: isSelected ? 'white' : 'var(--color-text-secondary, #6b7280)',
                fontSize: '0.82rem',
                fontWeight: isSelected ? 700 : 500,
                cursor: 'pointer',
                transition: 'all 0.12s ease',
                padding: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: isSelected ? '0 1px 4px rgba(13, 148, 136, 0.2)' : 'none',
              }}
            >
              {n}
            </button>
          );
        })}
      </div>
      {/* Anchor labels + selected meaning */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'baseline',
        maxWidth: 36 * 5 + 6 * 4,
      }}>
        <span style={{ fontSize: '0.6rem', color: 'var(--color-text-muted, #94a3b8)', fontWeight: 500 }}>
          {lowLabel}
        </span>
        {selectedLabel && (
          <span style={{ fontSize: '0.6rem', color: '#0d9488', fontWeight: 600 }}>
            {selectedLabel}
          </span>
        )}
        <span style={{ fontSize: '0.6rem', color: 'var(--color-text-muted, #94a3b8)', fontWeight: 500 }}>
          {highLabel}
        </span>
      </div>
    </div>
  );
}

/* ── Duration helper ── */
function formatDuration(totalMinutes) {
  if (!totalMinutes) return '0m';
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  if (h > 0 && m > 0) return `${h}h ${m}m`;
  if (h > 0) return `${h}h`;
  return `${m}m`;
}

/* ── Time entry: compact h/m fields + increment chips ── */
function TimeInput({ value, onChange }) {
  const totalMins = value || 0;
  const hours = Math.floor(totalMins / 60);
  const mins = totalMins % 60;

  const updateTime = (h, m) => {
    const clamped = Math.max(0, Math.min(h * 60 + m, 960));
    onChange(clamped);
  };

  const addMinutes = (delta) => {
    onChange(Math.max(0, Math.min(totalMins + delta, 960)));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {/* Entry row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 3,
          background: 'var(--color-surface-muted, #f5f5f5)',
          borderRadius: 6,
          border: '1px solid var(--color-border, #e2e8f0)',
          padding: '3px 6px',
        }}>
          <input
            type="number"
            min="0"
            max="16"
            value={hours}
            onChange={(e) => updateTime(Math.max(0, Math.min(16, parseInt(e.target.value) || 0)), mins)}
            style={{
              width: 22,
              border: 'none',
              background: 'transparent',
              fontSize: '0.85rem',
              fontWeight: 600,
              textAlign: 'center',
              color: 'var(--color-text)',
              outline: 'none',
              padding: 0,
              fontVariantNumeric: 'tabular-nums',
            }}
          />
          <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted, #9ca3af)', fontWeight: 500 }}>h</span>
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 3,
          background: 'var(--color-surface-muted, #f5f5f5)',
          borderRadius: 6,
          border: '1px solid var(--color-border, #e2e8f0)',
          padding: '3px 6px',
        }}>
          <input
            type="number"
            min="0"
            max="59"
            step="5"
            value={mins}
            onChange={(e) => updateTime(hours, Math.max(0, Math.min(59, parseInt(e.target.value) || 0)))}
            style={{
              width: 22,
              border: 'none',
              background: 'transparent',
              fontSize: '0.85rem',
              fontWeight: 600,
              textAlign: 'center',
              color: 'var(--color-text)',
              outline: 'none',
              padding: 0,
              fontVariantNumeric: 'tabular-nums',
            }}
          />
          <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted, #9ca3af)', fontWeight: 500 }}>m</span>
        </div>
        {/* Increment chips */}
        {[15, 30, 60].map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => addMinutes(d)}
            style={{
              padding: '3px 7px',
              borderRadius: 5,
              border: '1px solid var(--color-border, #e2e8f0)',
              background: 'transparent',
              color: 'var(--color-text-muted, #9ca3af)',
              fontSize: '0.62rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.12s ease',
              lineHeight: 1,
            }}
          >
            +{formatDuration(d)}
          </button>
        ))}
      </div>
      {/* Total summary — secondary */}
      {totalMins > 0 && (
        <span style={{
          fontSize: '0.62rem',
          fontWeight: 500,
          color: 'var(--color-text-muted, #9ca3af)',
        }}>
          Total: {formatDuration(totalMins)}
        </span>
      )}
    </div>
  );
}

function MinutesInput({ value, onChange }) {
  return <TimeInput value={value} onChange={onChange} />;
}

function HoursInput({ value, onChange }) {
  const totalMins = Math.round((value || 0) * 60);
  return (
    <TimeInput
      value={totalMins}
      onChange={(newMins) => onChange(Math.round(newMins / 30) * 0.5)}
    />
  );
}

/* ── Count stepper ── */
const stepperBtnStyle = {
  width: 28,
  height: 28,
  minWidth: 28,
  borderRadius: 6,
  border: '1.5px solid var(--color-border, #e2e8f0)',
  background: 'var(--color-surface-muted)',
  fontSize: '0.9rem',
  fontWeight: 500,
  cursor: 'pointer',
  padding: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'var(--color-text-secondary)',
  boxSizing: 'border-box',
  transition: 'all 0.12s ease',
};

function CountInput({ value, onChange }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
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
        fontSize: '0.95rem',
        fontWeight: 700,
        minWidth: 20,
        textAlign: 'center',
        color: 'var(--color-text)',
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

/* ── Behavior row ── */
function BehaviorRow({ behavior, value, onChange, struggleInfo }) {
  const isWide = ['scale_5', 'minutes', 'hours'].includes(behavior.input_type);

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
      flexDirection: isWide ? 'column' : 'row',
      justifyContent: isWide ? 'flex-start' : 'space-between',
      alignItems: isWide ? 'stretch' : 'center',
      gap: isWide ? 4 : 0,
      padding: '5px 0',
    }}>
      <span style={{
        fontSize: '0.85rem',
        color: 'var(--color-text)',
        flex: isWide ? 'none' : 1,
        display: 'flex',
        alignItems: 'center',
        gap: 5,
        lineHeight: 1.3,
      }}>
        {behavior.label}
        {struggleInfo && (
          <span style={{
            fontSize: '0.55rem',
            fontWeight: 600,
            padding: '1px 5px',
            borderRadius: 6,
            background: `${struggleInfo.color}15`,
            color: struggleInfo.color,
            whiteSpace: 'nowrap',
          }}>
            {struggleInfo.label}
          </span>
        )}
      </span>
      <div style={{
        flexShrink: isWide ? 1 : 0,
        marginLeft: isWide ? 0 : 8,
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
  const [activeStruggles, setActiveStruggles] = useState([]);
  const [struggleReflections, setStruggleReflections] = useState({});
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
      // Reset values for the new date — don't carry over previous day's data
      setValues({});
      setHeartState(null);
      setStruggleReflections({});
      setHeartResponse(null);
      setSaved(false);
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
            setActiveStruggles(retryData.active_struggles || []);
          }
        } else if (configRes.ok) {
          const configData = await configRes.json();
          if (!cancelled) {
            setConfig(configData.config);
            setCategories(configData.categories || []);
            setAllBehaviors(configData.all_behaviors || []);
            setActiveStruggles(configData.active_struggles || []);
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
            // Pre-fill struggle reflections
            if (logData.log.struggle_reflections) {
              const existingReflections = {};
              for (const [sid, ref] of Object.entries(logData.log.struggle_reflections)) {
                if (ref?.text) existingReflections[sid] = ref.text;
              }
              setStruggleReflections(existingReflections);
            }
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
          struggle_reflections: Object.keys(struggleReflections).length > 0
            ? struggleReflections : undefined,
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

  // Build a map of behavior_id → struggle info for visual indicators
  const struggleBehaviorMap = {};
  for (const s of activeStruggles) {
    for (const bid of (s.linked_behaviors || [])) {
      if (!struggleBehaviorMap[bid]) {
        struggleBehaviorMap[bid] = { label: s.label, color: s.color };
      }
    }
  }

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
            background: quickLog ? '#0d948815' : 'var(--color-surface)',
            fontSize: '0.75rem',
            fontWeight: 600,
            color: quickLog ? '#0d9488' : 'var(--color-text-secondary, #6b7280)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          {quickLog ? 'Quick Log ON' : 'Quick Log'}
        </button>
        <span style={{
          fontSize: '0.75rem',
          fontWeight: 600,
          color: filledCount === totalTracked ? '#059669' : 'var(--color-text-secondary, #9ca3af)',
          background: filledCount === totalTracked ? 'rgba(5, 150, 105, 0.08)' : 'var(--color-surface-muted)',
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
                      struggleInfo={struggleBehaviorMap[b.id]}
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
          <div className="hr-loading">
            <div className="hr-loading-spinner" />
            <span>Loading spiritual guidance...</span>
          </div>
        )}
      </div>

      {/* Heart Note Composer */}
      <HeartNoteComposer onSave={handleHeartNote} disabled={saving} />

      {/* Struggle reflections */}
      {activeStruggles.length > 0 && (
        <div className="struggle-reflections-section">
          <h3 className="section-title">Active Struggles</h3>
          <p className="sr-subtitle">How did today go?</p>
          {activeStruggles.map((s) => (
            <div key={s.struggle_id} className="sr-card" style={{ borderLeftColor: s.color }}>
              <span className="sr-label" style={{ color: s.color }}>{s.label}</span>
              <textarea
                className="sr-input"
                placeholder={`Any slips, wins, or reflections on ${s.label.toLowerCase()} today?`}
                value={struggleReflections[s.struggle_id] || ''}
                onChange={(e) => {
                  setStruggleReflections(prev => ({
                    ...prev,
                    [s.struggle_id]: e.target.value,
                  }));
                  setSaved(false);
                }}
                maxLength={500}
                rows={2}
              />
            </div>
          ))}
        </div>
      )}

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
          gap: 14px;
        }
        .journal-loading, .journal-error {
          text-align: center;
          padding: 40px 20px;
          color: var(--color-text-secondary);
          font-size: 0.95rem;
        }
        .journal-error {
          color: var(--color-error);
        }
        .welcome-back-banner {
          padding: 12px 16px;
          background: rgba(5, 150, 105, 0.08);
          border-radius: 12px;
          border: 1px solid rgba(5, 150, 105, 0.2);
          color: var(--foreground, #065f46);
          font-size: 0.9rem;
          text-align: center;
          font-weight: 500;
          }
        .riya-reminder {
          padding: 12px 16px;
          background: rgba(234, 179, 8, 0.08);
          border-radius: 12px;
          border: 1px solid rgba(234, 179, 8, 0.25);
          color: var(--foreground, #92400e);
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
          gap: 2px;
        }
        .behavior-list :global(.practice-group) {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .behavior-list :global(.practice-group + .practice-group) {
          margin-top: 8px;
          padding-top: 8px;
          border-top: 1px solid var(--color-border-light);
        }
        .behavior-list :global(.pg-label) {
          font-size: 0.65rem;
          font-weight: 600;
          color: var(--color-text-muted);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          padding-bottom: 1px;
        }

        /* Time input — hide browser number spinners */
        .behavior-list input[type="number"]::-webkit-inner-spin-button,
        .behavior-list input[type="number"]::-webkit-outer-spin-button {
          -webkit-appearance: none;
          margin: 0;
        }
        .behavior-list input[type="number"] {
          -moz-appearance: textfield;
        }

        /* Heart state */
        .heart-state-section {
          padding: 16px;
          background: var(--color-surface-muted);
          border-radius: 12px;
          border: 1px solid var(--color-border);
        }
        .section-title {
          margin: 0 0 12px 0;
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--color-text);
        }
        .heart-state-pills {
          display: flex;
          flex-wrap: wrap;
          gap: 7px;
        }
        .heart-pill {
          padding: 7px 14px;
          border-radius: 20px;
          border: 1.5px solid var(--color-border);
          background: var(--color-surface);
          font-size: 0.78rem;
          cursor: pointer;
          transition: all 0.15s ease;
          color: var(--color-text-secondary);
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1px;
        }
        .heart-pill:hover {
          border-color: var(--color-text-muted);
          background: var(--color-surface-elevated);
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
          background: var(--color-surface);
          border-radius: 12px;
          border-left: 3px solid #0d9488;
          box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
        }
        .hr-verse {
          font-size: 0.88rem;
          font-style: italic;
          color: var(--color-text);
          margin: 0 0 10px 0;
          line-height: 1.5;
        }
        .hr-ref {
          display: block;
          font-size: 0.65rem;
          color: var(--color-text-secondary);
          font-style: normal;
          margin-top: 4px;
        }
        .hr-insight {
          font-size: 0.82rem;
          color: var(--color-text);
          margin: 0 0 8px 0;
          line-height: 1.5;
        }
        .hr-action {
          font-size: 0.82rem;
          color: var(--color-text);
          margin: 0 0 10px 0;
          line-height: 1.5;
        }
        .hr-excerpts {
          margin-top: 8px;
        }
        .hr-excerpts-label {
          font-size: 0.75rem;
          font-weight: 600;
          color: var(--color-text-secondary);
          cursor: pointer;
        }
        .hr-excerpt {
          margin-top: 8px;
          padding: 10px;
          background: var(--color-surface-muted);
          border-radius: 6px;
        }
        .hr-source {
          font-size: 0.65rem;
          font-weight: 600;
          color: var(--color-text-muted);
          display: block;
          margin-bottom: 4px;
        }
        .hr-text {
          font-size: 0.78rem;
          color: var(--color-text-secondary);
          margin: 0;
          line-height: 1.5;
        }
        .hr-loading {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.8rem;
          color: var(--color-text-muted);
          font-style: italic;
          margin: 10px 0 0 0;
          padding: 10px 12px;
          background: var(--color-surface-muted);
          border-radius: 8px;
        }
        .hr-loading-spinner {
          width: 14px;
          height: 14px;
          border: 2px solid var(--color-border);
          border-top-color: #0d9488;
          border-radius: 50%;
          animation: hr-spin 0.6s linear infinite;
          flex-shrink: 0;
        }
        @keyframes hr-spin {
          to { transform: rotate(360deg); }
        }

        /* Struggle reflections */
        .struggle-reflections-section {
          padding-top: 4px;
        }
        .sr-subtitle {
          font-size: 0.78rem;
          color: var(--color-text-secondary);
          margin: 0 0 10px 0;
        }
        .sr-card {
          padding: 10px 12px;
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-left: 3px solid;
          border-radius: 10px;
          margin-bottom: 8px;
        }
        .sr-label {
          font-size: 0.8rem;
          font-weight: 600;
          display: block;
          margin-bottom: 6px;
        }
        .sr-input {
          width: 100%;
          border: 1px solid var(--color-border);
          border-radius: 8px;
          padding: 8px 10px;
          font-size: 0.82rem;
          font-family: inherit;
          background: var(--color-surface-muted);
          color: var(--color-text);
          resize: none;
          line-height: 1.4;
        }
        .sr-input::placeholder {
          color: var(--color-text-muted);
        }
        .sr-input:focus {
          outline: none;
          border-color: var(--primary-teal);
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
          background: #0d9488;
          color: white;
          font-size: 0.95rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.15s ease;
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
