'use client';
import { useState, useEffect } from 'react';

const BACKEND_URL = 'https://tafsir-backend-612616741510.us-central1.run.app';

const ANNOTATION_TYPES = [
  { value: 'personal_insight', label: '💡 Personal Insight', icon: '💡' },
  { value: 'question', label: '❓ Question', icon: '❓' },
  { value: 'application', label: '✅ Application', icon: '✅' },
  { value: 'memory', label: '💭 Memory', icon: '💭' },
  { value: 'connection', label: '🔗 Connection', icon: '🔗' }
];

export default function AnnotationPanel({
  isOpen,
  onClose,
  verse,
  user,
  existingAnnotation = null,
  onSaved,
  reflectionType = 'verse', // 'verse', 'section', 'general', 'highlight'
  sectionName = null, // e.g., 'Summary', 'Cross References'
  highlightedText = null, // For text highlighting feature
  queryContext = null, // The original query for context
  shareId = null // Link back to the original response
}) {
  const [content, setContent] = useState('');
  const [type, setType] = useState('personal_insight');
  const [tags, setTags] = useState([]);
  const [tagInput, setTagInput] = useState('');
  const [allTags, setAllTags] = useState([]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [showTagSuggestions, setShowTagSuggestions] = useState(false);

  useEffect(() => {
    if (existingAnnotation) {
      setContent(existingAnnotation.content || '');
      setType(existingAnnotation.type || 'personal_insight');
      setTags(existingAnnotation.tags || []);
    } else {
      setContent('');
      setType('personal_insight');
      setTags([]);
    }
  }, [existingAnnotation]);

  useEffect(() => {
    if (isOpen && user) {
      fetchAllTags();
    }
  }, [isOpen, user]);

  const fetchAllTags = async () => {
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/annotations/tags`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setAllTags(data.tags || []);
      }
    } catch (err) {
      console.error('Failed to fetch tags:', err);
    }
  };

  const handleSave = async () => {
    if (!content.trim()) {
      setError('Please enter some content for your annotation');
      return;
    }

    setIsSaving(true);
    setError('');

    try {
      const token = await user.getIdToken();
      const url = existingAnnotation
        ? `${BACKEND_URL}/annotations/${existingAnnotation.id}`
        : `${BACKEND_URL}/annotations`;

      const method = existingAnnotation ? 'PUT' : 'POST';

      const body = {
        content,
        type,
        tags,
        reflection_type: reflectionType
      };

      // Add share_id to link back to original response
      if (shareId) {
        body.share_id = shareId;
      }

      if (!existingAnnotation) {
        // For verse-specific reflections
        if (reflectionType === 'verse' && verse?.surah && verse?.verse_number) {
          body.surah = verse.surah;
          body.verse = verse.verse_number;
        }

        // For section-specific reflections
        if (reflectionType === 'section') {
          body.section_name = sectionName;
          body.query_context = queryContext;
        }

        // For general reflections
        if (reflectionType === 'general') {
          body.query_context = queryContext;
        }

        // For highlighted text reflections
        if (reflectionType === 'highlight') {
          body.highlighted_text = highlightedText;
          body.query_context = queryContext;
        }
      }

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(body)
      });

      if (res.ok) {
        const data = await res.json();
        onSaved && onSaved(data);
        onClose();
      } else {
        const errorData = await res.json();
        setError(errorData.error || 'Failed to save annotation');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddTag = (tag) => {
    const trimmedTag = tag.trim().toLowerCase();
    if (trimmedTag && !tags.includes(trimmedTag)) {
      setTags([...tags, trimmedTag]);
      setTagInput('');
      setShowTagSuggestions(false);
    }
  };

  const handleRemoveTag = (tagToRemove) => {
    setTags(tags.filter(t => t !== tagToRemove));
  };

  const handleTagInputKeyDown = (e) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault();
      handleAddTag(tagInput);
    } else if (e.key === 'Backspace' && !tagInput && tags.length > 0) {
      handleRemoveTag(tags[tags.length - 1]);
    }
  };

  const filteredTagSuggestions = allTags.filter(
    tag => tag.toLowerCase().includes(tagInput.toLowerCase()) && !tags.includes(tag)
  );

  if (!isOpen) return null;

  return (
    <>
      {/* Overlay */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          zIndex: 999,
          animation: 'fadeIn 0.3s ease'
        }}
        onClick={onClose}
      />

      {/* Panel */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: '100%',
          maxWidth: '600px',
          background: 'linear-gradient(135deg, #ffffff 0%, rgba(250, 246, 240, 1) 100%)',
          boxShadow: 'var(--shadow-strong)',
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column',
          animation: 'slideInRight 0.3s ease'
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '24px',
            background: 'var(--gradient-teal-gold)',
            color: 'white',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: '1.5rem' }}>
              📝 {existingAnnotation ? 'Edit' : 'Add'} Reflection
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.9rem', opacity: 0.9 }}>
              {reflectionType === 'verse' && verse?.surah && verse?.verse_number && (
                verse.surah_name ? `${verse.surah_name} (${verse.surah}:${verse.verse_number})` : `${verse.surah}:${verse.verse_number}`
              )}
              {reflectionType === 'section' && sectionName && `On: ${sectionName}`}
              {reflectionType === 'general' && queryContext && `On: ${queryContext}`}
              {reflectionType === 'highlight' && 'On: Selected Text'}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: '2px solid white',
              color: 'white',
              borderRadius: '50%',
              width: '36px',
              height: '36px',
              fontSize: '1.5rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '24px' }}>
          {/* Context Display */}
          {(reflectionType === 'verse' && verse?.text_saheeh_international) && (
            <div
              style={{
                padding: '16px',
                background: 'var(--cream)',
                borderRadius: '12px',
                marginBottom: '24px',
                border: '2px solid var(--border-light)'
              }}
            >
              <p style={{ fontStyle: 'italic', color: 'var(--deep-blue)', margin: 0 }}>
                "{verse.text_saheeh_international}"
              </p>
            </div>
          )}

          {reflectionType === 'highlight' && highlightedText && (
            <div
              style={{
                padding: '16px',
                background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
                borderRadius: '12px',
                marginBottom: '24px',
                border: '2px solid var(--gold)'
              }}
            >
              <p style={{ fontSize: '0.85rem', fontWeight: '600', color: '#92400e', marginBottom: '8px' }}>
                Selected Text:
              </p>
              <p style={{ fontStyle: 'italic', color: '#78350f', margin: 0 }}>
                "{highlightedText}"
              </p>
            </div>
          )}

          {reflectionType === 'section' && sectionName && (
            <div
              style={{
                padding: '16px',
                background: 'linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)',
                borderRadius: '12px',
                marginBottom: '24px',
                border: '2px solid var(--primary-teal)'
              }}
            >
              <p style={{ fontSize: '0.85rem', fontWeight: '600', color: 'var(--primary-teal)', margin: 0 }}>
                Reflecting on: {sectionName}
              </p>
            </div>
          )}

          {reflectionType === 'general' && queryContext && (
            <div
              style={{
                padding: '16px',
                background: 'linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%)',
                borderRadius: '12px',
                marginBottom: '24px',
                border: '2px solid #a855f7'
              }}
            >
              <p style={{ fontSize: '0.85rem', fontWeight: '600', color: '#7c3aed', marginBottom: '4px' }}>
                General Reflection on Query:
              </p>
              <p style={{ fontStyle: 'italic', color: '#6b21a8', margin: 0 }}>
                "{queryContext}"
              </p>
            </div>
          )}

          {/* Annotation Type */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontWeight: '700', marginBottom: '12px', color: 'var(--primary-teal)' }}>
              Annotation Type
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px' }}>
              {ANNOTATION_TYPES.map(({ value, icon, label }) => (
                <button
                  key={value}
                  onClick={() => setType(value)}
                  style={{
                    padding: '12px',
                    background: type === value ? 'var(--primary-teal)' : 'white',
                    color: type === value ? 'white' : 'var(--foreground)',
                    border: '2px solid var(--border-light)',
                    borderRadius: '12px',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: '600',
                    transition: 'all 0.3s ease',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <span style={{ fontSize: '1.5rem' }}>{icon}</span>
                  <span>{label.split(' ')[1]}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Content Textarea */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontWeight: '700', marginBottom: '8px', color: 'var(--primary-teal)' }}>
              Your Reflection
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write your thoughts, insights, or questions about this verse..."
              style={{
                width: '100%',
                minHeight: '200px',
                padding: '16px',
                border: '2px solid var(--border-medium)',
                borderRadius: '12px',
                fontSize: '1rem',
                fontFamily: 'inherit',
                resize: 'vertical',
                background: 'white'
              }}
              autoFocus
            />
          </div>

          {/* Tags */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontWeight: '700', marginBottom: '8px', color: 'var(--primary-teal)' }}>
              Tags
            </label>
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '8px',
                padding: '12px',
                border: '2px solid var(--border-medium)',
                borderRadius: '12px',
                background: 'white',
                minHeight: '48px'
              }}
            >
              {tags.map(tag => (
                <span
                  key={tag}
                  style={{
                    background: 'var(--primary-teal)',
                    color: 'white',
                    padding: '6px 12px',
                    borderRadius: '20px',
                    fontSize: '0.85rem',
                    fontWeight: '600',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  {tag}
                  <button
                    onClick={() => handleRemoveTag(tag)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'white',
                      cursor: 'pointer',
                      fontSize: '1rem',
                      padding: 0,
                      width: '16px',
                      height: '16px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
              <input
                type="text"
                value={tagInput}
                onChange={(e) => {
                  setTagInput(e.target.value);
                  setShowTagSuggestions(e.target.value.length > 0);
                }}
                onKeyDown={handleTagInputKeyDown}
                onFocus={() => tagInput && setShowTagSuggestions(true)}
                placeholder="Add tags..."
                style={{
                  flex: 1,
                  minWidth: '120px',
                  border: 'none',
                  outline: 'none',
                  fontSize: '0.9rem',
                  background: 'transparent'
                }}
              />
            </div>

            {/* Tag Suggestions */}
            {showTagSuggestions && filteredTagSuggestions.length > 0 && (
              <div
                style={{
                  marginTop: '8px',
                  padding: '8px',
                  background: 'white',
                  border: '2px solid var(--border-light)',
                  borderRadius: '8px',
                  maxHeight: '150px',
                  overflowY: 'auto'
                }}
              >
                {filteredTagSuggestions.slice(0, 10).map(tag => (
                  <div
                    key={tag}
                    onClick={() => handleAddTag(tag)}
                    style={{
                      padding: '8px 12px',
                      cursor: 'pointer',
                      borderRadius: '6px',
                      fontSize: '0.9rem',
                      transition: 'background 0.2s ease'
                    }}
                    onMouseEnter={(e) => e.target.style.background = 'var(--cream)'}
                    onMouseLeave={(e) => e.target.style.background = 'transparent'}
                  >
                    {tag}
                  </div>
                ))}
              </div>
            )}
          </div>

          {error && (
            <div
              style={{
                padding: '12px',
                background: 'rgba(220, 38, 38, 0.1)',
                border: '2px solid var(--error-color)',
                borderRadius: '8px',
                color: 'var(--error-color)',
                marginBottom: '16px',
                fontWeight: '600'
              }}
            >
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '24px',
            borderTop: '2px solid var(--border-light)',
            display: 'flex',
            gap: '12px',
            background: 'var(--cream)'
          }}
        >
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: '14px',
              background: 'transparent',
              border: '2px solid var(--primary-teal)',
              color: 'var(--primary-teal)',
              borderRadius: '12px',
              fontSize: '1rem',
              fontWeight: '700',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || !content.trim()}
            style={{
              flex: 1,
              padding: '14px',
              background: isSaving || !content.trim() ? '#ccc' : 'var(--gradient-teal-gold)',
              border: 'none',
              color: 'white',
              borderRadius: '12px',
              fontSize: '1rem',
              fontWeight: '700',
              cursor: isSaving || !content.trim() ? 'not-allowed' : 'pointer'
            }}
          >
            {isSaving ? 'Saving...' : existingAnnotation ? 'Update' : 'Save'}
          </button>
        </div>
      </div>

      <style jsx>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        @media (max-width: 768px) {
          div[style*="maxWidth: '600px'"] {
            max-width: 100% !important;
          }
        }
      `}</style>
    </>
  );
}
