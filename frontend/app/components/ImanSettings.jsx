'use client';
import { useState, useEffect } from 'react';
import { BACKEND_URL } from '../lib/config';
import BehaviorSelector from './BehaviorSelector';

export default function ImanSettings({ user }) {
  const [catalog, setCatalog] = useState(null);
  const [config, setConfig] = useState(null);
  const [selectedBehaviors, setSelectedBehaviors] = useState([]);
  const [activeStruggles, setActiveStruggles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  useEffect(() => {
    if (!user) return;
    const load = async () => {
      try {
        const token = await user.getIdToken();
        const headers = { Authorization: `Bearer ${token}` };
        const [catRes, cfgRes, strRes] = await Promise.all([
          fetch(`${BACKEND_URL}/iman/catalog`, { headers }),
          fetch(`${BACKEND_URL}/iman/config`, { headers }),
          fetch(`${BACKEND_URL}/iman/struggles`, { headers }),
        ]);
        if (catRes.ok) setCatalog(await catRes.json());
        if (cfgRes.ok) {
          const cfgData = await cfgRes.json();
          setConfig(cfgData);
          setSelectedBehaviors(cfgData.tracked_behaviors?.map((b) => b.id) || []);
        }
        if (strRes.ok) {
          const strData = await strRes.json();
          setActiveStruggles(strData.active || []);
        }
      } catch (err) {
        console.error('Failed to load settings:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [user]);

  const handleSaveBehaviors = async () => {
    setSaving(true);
    setSaveMsg('');
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/config`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ behavior_ids: selectedBehaviors }),
      });
      if (res.ok) {
        setSaveMsg('Saved! Baselines will recalibrate over 14 days.');
        const cfgData = await res.json();
        if (cfgData.tracked_behaviors) {
          setConfig((prev) => ({ ...prev, tracked_behaviors: cfgData.tracked_behaviors }));
        }
      } else {
        const data = await res.json();
        setSaveMsg(data.error || 'Save failed');
      }
    } catch {
      setSaveMsg('Network error');
    } finally {
      setSaving(false);
    }
  };

  const handleResolveStruggle = async (struggleId) => {
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/struggle/${struggleId}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ resolved: true }),
      });
      if (res.ok) {
        setActiveStruggles((prev) => prev.filter((s) => s.struggle_id !== struggleId));
      }
    } catch (err) {
      console.error('Failed to resolve struggle:', err);
    }
  };

  const handleDeleteAll = async () => {
    setDeleting(true);
    setDeleteError('');
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/iman/data`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ confirm: 'DELETE_ALL_IMAN_DATA' }),
      });
      if (res.ok) {
        // Redirect to journal — will trigger fresh onboarding
        window.location.href = '/journal';
      } else {
        const data = await res.json();
        setDeleteError(data.error || 'Delete failed');
      }
    } catch {
      setDeleteError('Network error');
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="is-loading">
        <p>Loading settings...</p>
        <style jsx>{`
          .is-loading {
            display: flex; align-items: center; justify-content: center;
            min-height: 40vh; color: #6b7280; font-size: 0.9rem;
          }
        `}</style>
      </div>
    );
  }

  const hasChanges =
    config &&
    JSON.stringify(selectedBehaviors.sort()) !==
      JSON.stringify((config.tracked_behaviors?.map((b) => b.id) || []).sort());

  return (
    <div className="iman-settings">
      {/* Tracked Behaviors */}
      <section className="is-section">
        <h3 className="is-section-title">Tracked Behaviors</h3>
        <p className="is-section-desc">
          Choose which practices to reflect on daily. Changing behaviors will
          trigger a 14-day baseline recalibration.
        </p>
        {catalog && (
          <BehaviorSelector
            categories={catalog.categories}
            behaviors={catalog.behaviors}
            selectedIds={selectedBehaviors}
            onChange={setSelectedBehaviors}
            maxSelections={catalog.defaults?.max_tracked || 15}
            minSelections={3}
          />
        )}
        {hasChanges && (
          <div className="is-save-row">
            <button
              className="is-save-btn"
              onClick={handleSaveBehaviors}
              disabled={saving || selectedBehaviors.length < 3}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        )}
        {saveMsg && <p className="is-save-msg">{saveMsg}</p>}
      </section>

      {/* Active Struggles */}
      {activeStruggles.length > 0 && (
        <section className="is-section">
          <h3 className="is-section-title">Active Struggles</h3>
          <div className="is-struggle-list">
            {activeStruggles.map((s) => (
              <div key={s.struggle_id} className="is-struggle-row">
                <div className="is-struggle-info">
                  <span className="is-struggle-label">{s.label || s.struggle_id}</span>
                  <span className="is-struggle-phase">Phase {(s.current_phase || 0) + 1} of 4</span>
                </div>
                <button
                  className="is-resolve-btn"
                  onClick={() => handleResolveStruggle(s.struggle_id)}
                >
                  Resolve
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Data & Privacy */}
      <section className="is-section danger">
        <h3 className="is-section-title">Data & Privacy</h3>
        <p className="is-section-desc">
          Your journal data is encrypted and private. Deleting is permanent and
          cannot be undone.
        </p>
        {!deleteConfirm ? (
          <button
            className="is-delete-btn"
            onClick={() => setDeleteConfirm(true)}
          >
            Delete All Iman Data
          </button>
        ) : (
          <div className="is-delete-confirm">
            <p className="is-delete-warning">
              This will permanently delete all your journal entries, baselines,
              trajectory, struggles, and digests. You will need to re-onboard.
            </p>
            <div className="is-delete-actions">
              <button
                className="is-cancel-btn"
                onClick={() => setDeleteConfirm(false)}
              >
                Cancel
              </button>
              <button
                className="is-confirm-delete-btn"
                onClick={handleDeleteAll}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Yes, Delete Everything'}
              </button>
            </div>
            {deleteError && <p className="is-delete-error">{deleteError}</p>}
          </div>
        )}
      </section>

      {/* About */}
      <section className="is-section about">
        <p className="is-about-text">
          A mirror, not a measure. Your spiritual journey is between you and
          Allah.
        </p>
        {config && (
          <p className="is-about-meta">
            Engine v{config.engine_version || '?'}
            {config.calibration_days_remaining > 0 &&
              ` · Calibrating (${config.calibration_days_remaining} days left)`}
          </p>
        )}
      </section>

      <style jsx>{`
        .iman-settings {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .is-section {
          background: white;
          border-radius: 14px;
          border: 1px solid var(--border-light, #e5e7eb);
          padding: 18px 16px;
        }
        .is-section.danger {
          border-color: #fecaca;
        }
        .is-section.about {
          background: #fafaf8;
          text-align: center;
        }
        .is-section-title {
          font-size: 1rem;
          font-weight: 700;
          color: var(--deep-blue, #1e293b);
          margin: 0 0 6px 0;
        }
        .is-section-desc {
          font-size: 0.82rem;
          color: #6b7280;
          line-height: 1.5;
          margin: 0 0 14px 0;
        }
        .is-save-row {
          margin-top: 14px;
          text-align: center;
        }
        .is-save-btn {
          padding: 10px 24px;
          border-radius: 10px;
          border: none;
          background: var(--primary-teal, #0d9488);
          color: white;
          font-size: 0.9rem;
          font-weight: 500;
          cursor: pointer;
        }
        .is-save-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .is-save-msg {
          font-size: 0.8rem;
          color: #059669;
          text-align: center;
          margin: 8px 0 0 0;
        }
        .is-struggle-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .is-struggle-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 12px;
          background: #fafaf8;
          border-radius: 8px;
        }
        .is-struggle-info {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .is-struggle-label {
          font-size: 0.85rem;
          font-weight: 600;
          color: #374151;
        }
        .is-struggle-phase {
          font-size: 0.7rem;
          color: #9ca3af;
        }
        .is-resolve-btn {
          padding: 6px 14px;
          border-radius: 6px;
          border: 1px solid #e5e7eb;
          background: white;
          font-size: 0.75rem;
          color: #6b7280;
          cursor: pointer;
        }
        .is-delete-btn {
          padding: 10px 20px;
          border-radius: 10px;
          border: 1px solid #fca5a5;
          background: white;
          color: #dc2626;
          font-size: 0.85rem;
          font-weight: 500;
          cursor: pointer;
        }
        .is-delete-confirm {
          margin-top: 4px;
        }
        .is-delete-warning {
          font-size: 0.8rem;
          color: #dc2626;
          line-height: 1.5;
          margin: 0 0 12px 0;
        }
        .is-delete-actions {
          display: flex;
          gap: 10px;
        }
        .is-cancel-btn {
          flex: 1;
          padding: 10px;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          background: white;
          font-size: 0.85rem;
          color: #374151;
          cursor: pointer;
        }
        .is-confirm-delete-btn {
          flex: 1;
          padding: 10px;
          border-radius: 8px;
          border: none;
          background: #dc2626;
          color: white;
          font-size: 0.85rem;
          font-weight: 500;
          cursor: pointer;
        }
        .is-confirm-delete-btn:disabled {
          opacity: 0.5;
        }
        .is-delete-error {
          font-size: 0.8rem;
          color: #dc2626;
          margin: 8px 0 0 0;
        }
        .is-about-text {
          font-size: 0.85rem;
          color: #6b7280;
          font-style: italic;
          margin: 0 0 6px 0;
          line-height: 1.5;
        }
        .is-about-meta {
          font-size: 0.7rem;
          color: #9ca3af;
          margin: 0;
        }
      `}</style>
    </div>
  );
}
