'use client';
import { useState } from 'react';

const NOTE_TYPES = [
  { id: 'gratitude', label: 'Gratitude', emoji: 'Shukr' },
  { id: 'dua', label: 'Dua', emoji: 'Dua' },
  { id: 'tawbah', label: 'Tawbah', emoji: 'Tawbah' },
  { id: 'connection', label: 'Connection', emoji: 'Bond' },
  { id: 'reflection', label: 'Reflection', emoji: 'Fikr' },
  { id: 'quran_insight', label: 'Quran Insight', emoji: 'Ayah' },
];

const CHAR_LIMITS = {
  gratitude: 280,
  dua: 280,
  tawbah: 280,
  connection: 280,
  reflection: 500,
  quran_insight: 500,
};

export default function HeartNoteComposer({ onSave, disabled = false }) {
  const [selectedType, setSelectedType] = useState(null);
  const [text, setText] = useState('');
  const [saving, setSaving] = useState(false);

  const maxChars = CHAR_LIMITS[selectedType] || 280;
  const charsLeft = maxChars - text.length;
  const canSave = selectedType && text.trim().length > 0 && charsLeft >= 0;

  const handleSave = async () => {
    if (!canSave || saving) return;
    setSaving(true);
    try {
      await onSave({ type: selectedType, text: text.trim() });
      setText('');
      setSelectedType(null);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="heart-note-composer">
      <h3 className="heart-note-title">Heart Note</h3>
      <p className="heart-note-subtitle">Capture a thought, dua, or moment of gratitude</p>

      <div className="type-pills">
        {NOTE_TYPES.map((nt) => (
          <button
            key={nt.id}
            className={`type-pill ${selectedType === nt.id ? 'active' : ''}`}
            onClick={() => setSelectedType(selectedType === nt.id ? null : nt.id)}
            disabled={disabled}
          >
            {nt.label}
          </button>
        ))}
      </div>

      {selectedType && (
        <div className="note-input-area">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value.slice(0, maxChars))}
            placeholder={`Write your ${NOTE_TYPES.find(n => n.id === selectedType)?.label.toLowerCase()}...`}
            rows={3}
            disabled={disabled || saving}
            className="note-textarea"
          />
          <div className="note-footer">
            <span className={`char-count ${charsLeft < 30 ? 'warning' : ''} ${charsLeft < 0 ? 'over' : ''}`}>
              {charsLeft}
            </span>
            <button
              className="save-note-btn"
              onClick={handleSave}
              disabled={!canSave || saving}
            >
              {saving ? 'Saving...' : 'Save Note'}
            </button>
          </div>
        </div>
      )}

      <style jsx>{`
        .heart-note-composer {
          padding: 16px;
          background: var(--cream, #faf6f0);
          border-radius: 12px;
          border: 1px solid var(--border-light, #e5e7eb);
        }
        .heart-note-title {
          margin: 0 0 4px 0;
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--deep-blue, #1e293b);
        }
        .heart-note-subtitle {
          margin: 0 0 12px 0;
          font-size: 0.8rem;
          color: #6b7280;
        }
        .type-pills {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 12px;
        }
        .type-pill {
          padding: 6px 14px;
          border-radius: 20px;
          border: 1px solid var(--border-light, #e5e7eb);
          background: white;
          font-size: 0.8rem;
          cursor: pointer;
          transition: all 0.15s ease;
          color: #374151;
        }
        .type-pill:hover:not(:disabled) {
          border-color: var(--primary-teal, #0d9488);
        }
        .type-pill.active {
          background: var(--primary-teal, #0d9488);
          color: white;
          border-color: var(--primary-teal, #0d9488);
        }
        .type-pill:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .note-input-area {
          margin-top: 8px;
        }
        .note-textarea {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid var(--border-light, #e5e7eb);
          border-radius: 8px;
          font-size: 0.9rem;
          font-family: inherit;
          resize: vertical;
          min-height: 72px;
          background: white;
          color: var(--deep-blue, #1e293b);
        }
        .note-textarea:focus {
          outline: none;
          border-color: var(--primary-teal, #0d9488);
          box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.1);
        }
        .note-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 8px;
        }
        .char-count {
          font-size: 0.75rem;
          color: #9ca3af;
        }
        .char-count.warning {
          color: #d97706;
        }
        .char-count.over {
          color: #ef4444;
        }
        .save-note-btn {
          padding: 6px 16px;
          border-radius: 8px;
          border: none;
          background: var(--primary-teal, #0d9488);
          color: white;
          font-size: 0.85rem;
          font-weight: 500;
          cursor: pointer;
          transition: opacity 0.15s ease;
        }
        .save-note-btn:hover:not(:disabled) {
          opacity: 0.9;
        }
        .save-note-btn:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}
