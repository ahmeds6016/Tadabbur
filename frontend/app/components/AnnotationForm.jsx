'use client';
import { useState, useEffect, useRef } from 'react';
import { BACKEND_URL } from '../lib/config';

const ANNOTATION_TYPES = [
  { value: 'personal_insight', label: 'Personal Insight' },
  { value: 'question', label: 'Question' },
  { value: 'application', label: 'Application' },
  { value: 'memory', label: 'Memory' },
  { value: 'connection', label: 'Connection' }
];

/**
 * AnnotationForm - Clean form component
 *
 * PRINCIPLES:
 * - Just the form, no positioning logic
 * - No scroll manipulation
 * - Native form behavior
 * - Accessible by default
 */

export default function AnnotationForm({
  selectedText,
  verse,
  user,
  reflectionType = 'verse',
  onSaved,
  onCancel,
  existingAnnotation = null,
  sectionName = null,
  queryContext = null,
  shareId = null
}) {
  const [content, setContent] = useState('');
  const [type, setType] = useState('personal_insight');
  const [tags, setTags] = useState([]);
  const [tagInput, setTagInput] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const textareaRef = useRef(null);

  // Initialize form with existing data
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

  // Focus textarea when form loads
  useEffect(() => {
    // Small delay to ensure dialog animation completes
    const timer = setTimeout(() => {
      textareaRef.current?.focus();
    }, 300);
    return () => clearTimeout(timer);
  }, []);

  // Handle save
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

      // Add context based on reflection type
      if (shareId) body.share_id = shareId;

      if (!existingAnnotation) {
        if (reflectionType === 'verse' && verse?.surah && verse?.verse_number) {
          body.surah = verse.surah;
          body.verse = verse.verse_number;
        }

        if (reflectionType === 'section') {
          body.section_name = sectionName;
          body.query_context = queryContext;
        }

        if (reflectionType === 'general') {
          body.query_context = queryContext;
        }

        if (reflectionType === 'highlight') {
          body.highlighted_text = selectedText;
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
        onSaved?.(data);
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

  // Handle tag input
  const handleAddTag = (tag) => {
    const trimmedTag = tag.trim().toLowerCase();
    if (trimmedTag && !tags.includes(trimmedTag)) {
      setTags([...tags, trimmedTag]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove) => {
    setTags(tags.filter(t => t !== tagToRemove));
  };

  const handleTagKeyDown = (e) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault();
      handleAddTag(tagInput);
    } else if (e.key === 'Backspace' && !tagInput && tags.length > 0) {
      handleRemoveTag(tags[tags.length - 1]);
    }
  };

  // Get title based on reflection type
  const getTitle = () => {
    if (existingAnnotation) return 'Edit Reflection';

    switch (reflectionType) {
      case 'highlight':
        return 'Reflect on Selection';
      case 'section':
        return `Reflect on ${sectionName}`;
      case 'general':
        return 'General Reflection';
      default:
        return 'Add Reflection';
    }
  };

  return (
    <div className="annotation-form">
      {/* Header */}
      <div className="form-header">
        <h2 id="annotation-dialog-title">{getTitle()}</h2>
        {verse?.surah && verse?.verse_number && reflectionType === 'verse' && (
          <p className="verse-info">
            {verse.surah_name ? `${verse.surah_name} ` : `Surah ${verse.surah}, `}
            Verse {verse.verse_number}
          </p>
        )}
      </div>

      {/* Context Display */}
      {selectedText && (
        <div className="context-display">
          <label>Selected Text:</label>
          <p className="selected-text">"{selectedText}"</p>
        </div>
      )}

      {verse?.text_saheeh_international && reflectionType === 'verse' && (
        <div className="context-display">
          <label>Verse Text:</label>
          <p className="verse-text">"{verse.text_saheeh_international}"</p>
        </div>
      )}

      {/* Form Fields */}
      <div className="form-body">
        {/* Annotation Type */}
        <div className="form-group">
          <label>Type:</label>
          <div className="type-buttons">
            {ANNOTATION_TYPES.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                className={`type-button ${type === value ? 'active' : ''}`}
                onClick={() => setType(value)}
                title={label}
              >
                <span className="type-label">{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="form-group">
          <label htmlFor="annotation-content">Your Reflection:</label>
          <textarea
            ref={textareaRef}
            id="annotation-content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Write your thoughts, insights, or questions..."
            className="content-textarea"
            rows={6}
          />
        </div>

        {/* Privacy Notice */}
        <div className="privacy-notice">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          <span>Your reflections are encrypted and private — only you can access them.</span>
        </div>

        {/* Tags */}
        <div className="form-group">
          <label htmlFor="annotation-tags">Tags (optional):</label>
          <div className="tags-container">
            {tags.map((tag) => (
              <span key={tag} className="tag">
                {tag}
                <button
                  type="button"
                  onClick={() => handleRemoveTag(tag)}
                  className="tag-remove"
                  aria-label={`Remove ${tag} tag`}
                >
                  ×
                </button>
              </span>
            ))}
            <input
              id="annotation-tags"
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagKeyDown}
              placeholder={tags.length === 0 ? "Add tags..." : ""}
              className="tag-input"
            />
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}
      </div>

      {/* Footer with Actions */}
      <div className="form-footer">
        <button
          type="button"
          onClick={onCancel}
          className="btn btn-cancel"
          disabled={isSaving}
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          className="btn btn-save"
          disabled={isSaving || !content.trim()}
        >
          {isSaving ? 'Saving...' : existingAnnotation ? 'Update' : 'Save'}
        </button>
      </div>

      <style jsx>{`
        .annotation-form {
          display: flex;
          flex-direction: column;
          height: 100%;
          padding: 20px;
        }

        /* Header */
        .form-header {
          padding-bottom: 20px;
          border-bottom: 1px solid var(--color-border, #e5e7eb);
          margin-bottom: 20px;
        }

        .form-header h2 {
          margin: 0 0 8px 0;
          font-size: 1.5rem;
          color: var(--foreground, #111827);
        }

        .verse-info {
          margin: 0;
          color: #6b7280;
          font-size: 0.875rem;
        }

        /* Context Display */
        .context-display {
          background: var(--color-surface-muted, #f9fafb);
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 16px;
        }

        .context-display label {
          display: block;
          font-size: 0.75rem;
          text-transform: uppercase;
          color: var(--color-text-secondary, #6b7280);
          margin-bottom: 4px;
        }

        .selected-text,
        .verse-text {
          margin: 0;
          font-style: italic;
          color: var(--foreground, #374151);
        }

        /* Form Body */
        .form-body {
          flex: 1;
          overflow-y: auto;
          padding-right: 8px;
        }

        .form-group {
          margin-bottom: 24px;
        }

        .form-group label {
          display: block;
          margin-bottom: 8px;
          font-weight: 500;
          color: var(--foreground, #374151);
        }

        /* Type Buttons - All visible */
        .type-buttons {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .type-button {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 14px;
          border: 2px solid var(--primary-teal, #0D9488);
          border-radius: 8px;
          background: var(--cream, #faf6f0);
          color: var(--primary-teal, #0D9488);
          cursor: pointer;
          transition: all 0.2s;
          font-weight: 500;
        }

        .type-button:hover {
          background: rgba(13, 148, 136, 0.1);
        }

        .type-button.active {
          background: var(--primary-teal, #0D9488);
          color: white;
        }

        .type-label {
          font-size: 0.8rem;
        }

        /* Content Textarea */
        .content-textarea {
          width: 100%;
          padding: 12px;
          border: 2px solid var(--color-border, #e5e7eb);
          border-radius: 8px;
          font-size: 1rem;
          font-family: inherit;
          resize: vertical;
          min-height: 120px;
          transition: border-color 0.2s;
          background: var(--color-surface, white);
          color: var(--foreground);
        }

        .content-textarea:focus {
          outline: none;
          border-color: #0D9488;
        }

        /* Tags */
        .tags-container {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          padding: 8px;
          border: 2px solid var(--color-border, #e5e7eb);
          border-radius: 8px;
          min-height: 44px;
          background: var(--color-surface, white);
        }

        .tag {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 4px 8px;
          background: #0D9488;
          color: white;
          border-radius: 4px;
          font-size: 0.875rem;
        }

        .tag-remove {
          background: none;
          border: none;
          color: white;
          cursor: pointer;
          font-size: 1.25rem;
          padding: 0;
          width: 20px;
          height: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .tag-input {
          flex: 1;
          min-width: 120px;
          border: none;
          outline: none;
          font-size: 16px; /* Prevent iOS zoom - must be 16px or larger */
          background: transparent;
          color: var(--foreground);
        }

        /* Privacy Notice */
        .privacy-notice {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 12px;
          background: rgba(5, 150, 105, 0.08);
          border-radius: 6px;
          font-size: 0.75rem;
          color: var(--color-secondary-light, #15803d);
          margin-bottom: 20px;
        }

        .privacy-notice svg {
          flex-shrink: 0;
        }

        /* Error Message */
        .error-message {
          padding: 12px;
          background: #fee2e2;
          border: 1px solid #fca5a5;
          border-radius: 8px;
          color: #dc2626;
          font-size: 0.875rem;
        }

        /* Footer */
        .form-footer {
          display: flex;
          gap: 12px;
          justify-content: flex-end;
          padding-top: 20px;
          border-top: 1px solid var(--color-border, #e5e7eb);
          margin-top: 20px;
        }

        /* Buttons */
        .btn {
          padding: 10px 24px;
          border-radius: 8px;
          font-size: 1rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
          border: none;
        }

        .btn-cancel {
          background: var(--color-surface, white);
          border: 2px solid var(--color-border, #e5e7eb);
          color: var(--color-text-secondary, #6b7280);
        }

        .btn-cancel:hover:not(:disabled) {
          background: var(--color-surface-muted, #f9fafb);
        }

        .btn-save {
          background: #0D9488;
          color: white;
        }

        .btn-save:hover:not(:disabled) {
          background: #0F766E;
        }

        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        /* Mobile adjustments */
        @media (max-width: 768px) {
          .annotation-form {
            padding: 16px;
          }

          .type-buttons {
            grid-template-columns: 1fr 1fr;
          }

          .form-footer {
            position: sticky;
            bottom: 0;
            background: var(--color-surface, white);
            padding: 16px;
            margin: -16px -16px 0;
            box-shadow: 0 -4px 6px -1px rgba(0, 0, 0, 0.1);
          }
        }
      `}</style>
    </div>
  );
}