'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import { ChevronDown, Pencil, Trash2, Search } from 'lucide-react';
import { BACKEND_URL } from '../lib/config';

const NOTE_TYPE_COLORS = {
  gratitude: '#059669',
  dua: '#2563eb',
  tawbah: '#8b5cf6',
  connection: '#d97706',
  reflection: '#0d9488',
  quran_insight: '#dc2626',
};

const NOTE_TYPE_LABELS = {
  gratitude: 'Gratitude',
  dua: 'Dua',
  tawbah: 'Tawbah',
  connection: 'Connection',
  reflection: 'Reflection',
  quran_insight: 'Quran Insight',
};

function formatHistoryDate(dateStr) {
  const today = new Date().toISOString().split('T')[0];
  const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
  if (dateStr === today) return 'Today';
  if (dateStr === yesterday) return 'Yesterday';
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function HeartNoteHistory({ user }) {
  const [expanded, setExpanded] = useState(false);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [days, setDays] = useState(30);
  const [editingNote, setEditingNote] = useState(null);
  const [editText, setEditText] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const searchTimerRef = useRef(null);

  // Debounce search query (300ms)
  useEffect(() => {
    clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(searchTimerRef.current);
  }, [searchQuery]);

  const fetchNotes = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const token = await user.getIdToken();
      let url = `${BACKEND_URL}/iman/heart-notes?days=${days}`;
      if (filterType) url += `&type=${filterType}`;
      if (debouncedSearch) url += `&q=${encodeURIComponent(debouncedSearch)}`;

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setNotes(data.notes || []);
      }
    } catch (err) {
      console.error('Failed to fetch heart notes:', err);
    } finally {
      setLoading(false);
    }
  }, [user, days, filterType, debouncedSearch]);

  useEffect(() => {
    if (expanded) fetchNotes();
  }, [expanded, fetchNotes]);

  const today = new Date().toISOString().split('T')[0];

  const handleEdit = async (note) => {
    if (actionLoading) return;
    setActionLoading(true);
    try {
      const token = await user.getIdToken();
      const res = await fetch(
        `${BACKEND_URL}/iman/heart-note/${note.date}/${note.index}`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ text: editText }),
        }
      );
      if (res.ok) {
        setEditingNote(null);
        setEditText('');
        fetchNotes();
      }
    } catch (err) {
      console.error('Failed to edit note:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async (note) => {
    if (actionLoading) return;
    setActionLoading(true);
    try {
      const token = await user.getIdToken();
      const res = await fetch(
        `${BACKEND_URL}/iman/heart-note/${note.date}/${note.index}`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        fetchNotes();
      }
    } catch (err) {
      console.error('Failed to delete note:', err);
    } finally {
      setActionLoading(false);
    }
  };

  // Group notes by date
  const grouped = {};
  notes.forEach((note) => {
    if (!grouped[note.date]) grouped[note.date] = [];
    grouped[note.date].push(note);
  });
  const sortedDates = Object.keys(grouped).sort((a, b) => b.localeCompare(a));

  return (
    <div style={{
      background: 'white',
      borderRadius: 14,
      border: '1px solid #e5e7eb',
      overflow: 'hidden',
    }}>
      {/* Header toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          width: '100%',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '14px 16px',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
        }}
      >
        <span style={{
          fontSize: '0.85rem',
          fontWeight: 600,
          color: '#1e293b',
        }}>
          Heart Note History
        </span>
        <ChevronDown
          size={18}
          color="#6b7280"
          style={{
            transition: 'transform 0.2s ease',
            transform: expanded ? 'rotate(180deg)' : 'none',
          }}
        />
      </button>

      {expanded && (
        <div style={{ padding: '0 16px 16px' }}>
          {/* Search */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 10px',
            background: '#f8fafc',
            borderRadius: 8,
            marginBottom: 10,
            border: '1px solid #e5e7eb',
          }}>
            <Search size={14} color="#9ca3af" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search notes..."
              style={{
                flex: 1,
                border: 'none',
                background: 'none',
                fontSize: '0.82rem',
                color: '#1e293b',
                outline: 'none',
              }}
            />
          </div>

          {/* Type filter pills */}
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 6,
            marginBottom: 12,
          }}>
            <button
              onClick={() => setFilterType('')}
              style={{
                padding: '4px 10px',
                borderRadius: 14,
                border: '1px solid #e5e7eb',
                background: !filterType ? '#0d9488' : 'white',
                color: !filterType ? 'white' : '#6b7280',
                fontSize: '0.72rem',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              All
            </button>
            {Object.entries(NOTE_TYPE_LABELS).map(([id, label]) => (
              <button
                key={id}
                onClick={() => setFilterType(filterType === id ? '' : id)}
                style={{
                  padding: '4px 10px',
                  borderRadius: 14,
                  border: `1px solid ${filterType === id ? NOTE_TYPE_COLORS[id] : '#e5e7eb'}`,
                  background: filterType === id ? NOTE_TYPE_COLORS[id] : 'white',
                  color: filterType === id ? 'white' : '#6b7280',
                  fontSize: '0.72rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {loading ? (
            <p style={{ fontSize: '0.82rem', color: '#9ca3af', textAlign: 'center', margin: '16px 0' }}>
              Loading notes...
            </p>
          ) : notes.length === 0 ? (
            <p style={{ fontSize: '0.82rem', color: '#9ca3af', textAlign: 'center', margin: '16px 0' }}>
              No heart notes found.
            </p>
          ) : (
            <>
              {sortedDates.map((date) => (
                <div key={date} style={{ marginBottom: 14 }}>
                  <div style={{
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    color: '#9ca3af',
                    textTransform: 'uppercase',
                    letterSpacing: '0.3px',
                    marginBottom: 6,
                  }}>
                    {formatHistoryDate(date)}
                  </div>
                  {grouped[date].map((note, i) => {
                    const isEditing = editingNote === `${note.date}-${note.index}`;
                    const isSameDay = note.date === today;
                    const typeColor = NOTE_TYPE_COLORS[note.type] || '#6b7280';

                    return (
                      <div key={i} style={{
                        padding: '8px 10px',
                        background: '#fafbfc',
                        borderRadius: 8,
                        marginBottom: 6,
                        borderLeft: `3px solid ${typeColor}`,
                      }}>
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          marginBottom: 4,
                        }}>
                          <span style={{
                            fontSize: '0.65rem',
                            fontWeight: 600,
                            color: typeColor,
                            textTransform: 'uppercase',
                          }}>
                            {NOTE_TYPE_LABELS[note.type] || note.type}
                          </span>
                          {!isSameDay && (
                            <span style={{
                              fontSize: '0.58rem',
                              color: '#c4c8cd',
                              fontStyle: 'italic',
                            }}>
                              Editable today only
                            </span>
                          )}
                          {isSameDay && !isEditing && (
                            <div style={{ display: 'flex', gap: 6 }}>
                              <button
                                onClick={() => {
                                  setEditingNote(`${note.date}-${note.index}`);
                                  setEditText(note.text);
                                }}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  padding: 2,
                                  color: '#9ca3af',
                                }}
                              >
                                <Pencil size={13} />
                              </button>
                              <button
                                onClick={() => handleDelete(note)}
                                disabled={actionLoading}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  padding: 2,
                                  color: '#9ca3af',
                                }}
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          )}
                        </div>
                        {isEditing ? (
                          <div>
                            <textarea
                              value={editText}
                              onChange={(e) => setEditText(e.target.value)}
                              style={{
                                width: '100%',
                                padding: '6px 8px',
                                border: '1px solid #e5e7eb',
                                borderRadius: 6,
                                fontSize: '0.82rem',
                                fontFamily: 'inherit',
                                minHeight: 50,
                                resize: 'vertical',
                                color: '#1e293b',
                                background: 'white',
                              }}
                            />
                            <div style={{ display: 'flex', gap: 6, marginTop: 6, justifyContent: 'flex-end' }}>
                              <button
                                onClick={() => { setEditingNote(null); setEditText(''); }}
                                style={{
                                  padding: '4px 10px',
                                  borderRadius: 6,
                                  border: '1px solid #e5e7eb',
                                  background: 'white',
                                  fontSize: '0.75rem',
                                  cursor: 'pointer',
                                  color: '#6b7280',
                                }}
                              >
                                Cancel
                              </button>
                              <button
                                onClick={() => handleEdit(note)}
                                disabled={actionLoading || !editText.trim()}
                                style={{
                                  padding: '4px 10px',
                                  borderRadius: 6,
                                  border: 'none',
                                  background: '#0d9488',
                                  color: 'white',
                                  fontSize: '0.75rem',
                                  fontWeight: 500,
                                  cursor: 'pointer',
                                  opacity: actionLoading ? 0.5 : 1,
                                }}
                              >
                                Save
                              </button>
                            </div>
                          </div>
                        ) : (
                          <p style={{
                            fontSize: '0.82rem',
                            color: '#374151',
                            margin: 0,
                            lineHeight: 1.5,
                          }}>
                            {note.text}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}

              {/* Load more */}
              <button
                onClick={() => setDays(days + 30)}
                style={{
                  display: 'block',
                  width: '100%',
                  padding: '8px',
                  borderRadius: 8,
                  border: '1px solid #e5e7eb',
                  background: 'white',
                  fontSize: '0.78rem',
                  color: '#6b7280',
                  cursor: 'pointer',
                  textAlign: 'center',
                  marginTop: 4,
                }}
              >
                Load older notes
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
