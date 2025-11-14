'use client';
import { useState, useEffect, useRef } from 'react';

const BACKEND_URL = 'https://tafsir-backend-612616741510.us-central1.run.app';

const ANNOTATION_TYPES = [
  { value: 'personal_insight', label: '💡 Personal Insight', icon: '💡' },
  { value: 'question', label: '❓ Question', icon: '❓' },
  { value: 'application', label: '✅ Application', icon: '✅' },
  { value: 'memory', label: '💭 Memory', icon: '💭' },
  { value: 'connection', label: '🔗 Connection', icon: '🔗' }
];

// Comprehensive smart tag suggestion helper
const getSuggestedTags = (content) => {
  const suggestions = [];
  const lowerContent = content.toLowerCase();

  // Core Islamic concepts (Aqeedah)
  if (lowerContent.match(/\b(allah|god|creator|lord)\b/)) suggestions.push('tawheed');
  if (lowerContent.match(/\b(prophet|muhammad|messenger|rasul|nabi)\b/)) suggestions.push('seerah');
  if (lowerContent.match(/\b(quran|qur'an|revelation|book)\b/)) suggestions.push('quran');
  if (lowerContent.match(/\b(angel|angels|jibril|gabriel)\b/)) suggestions.push('angels');
  if (lowerContent.match(/\b(judgment|hereafter|afterlife|akhirah)\b/)) suggestions.push('akhirah');
  if (lowerContent.match(/\b(paradise|jannah|heaven)\b/)) suggestions.push('jannah');
  if (lowerContent.match(/\b(hell|jahannam|fire)\b/)) suggestions.push('jahannam');

  // Worship & Practice (Ibadah)
  if (lowerContent.match(/\b(prayer|salah|salat|pray|praying)\b/)) suggestions.push('salah');
  if (lowerContent.match(/\b(fast|fasting|ramadan|sawm)\b/)) suggestions.push('fasting');
  if (lowerContent.match(/\b(charity|zakat|sadaqah|give|giving)\b/)) suggestions.push('charity');
  if (lowerContent.match(/\b(hajj|pilgrimage|makkah|mecca|kaaba)\b/)) suggestions.push('hajj');
  if (lowerContent.match(/\b(dua|supplication|asking|invoke)\b/)) suggestions.push('dua');
  if (lowerContent.match(/\b(dhikr|remembrance|remember)\b/)) suggestions.push('dhikr');
  if (lowerContent.match(/\b(worship|ibadah|devotion)\b/)) suggestions.push('ibadah');

  // Character & Morality (Akhlaq)
  if (lowerContent.match(/\b(patient|patience|sabr|endure|persever)\b/)) suggestions.push('sabr');
  if (lowerContent.match(/\b(grateful|gratitude|shukr|thank|appreciate)\b/)) suggestions.push('shukr');
  if (lowerContent.match(/\b(humble|humility|modest)\b/)) suggestions.push('humility');
  if (lowerContent.match(/\b(honest|honesty|truth|truthful)\b/)) suggestions.push('honesty');
  if (lowerContent.match(/\b(kind|kindness|compassion|mercy|rahma)\b/)) suggestions.push('kindness');
  if (lowerContent.match(/\b(forgive|forgiveness|pardon)\b/)) suggestions.push('forgiveness');
  if (lowerContent.match(/\b(trust|tawakkul|reliance|rely)\b/)) suggestions.push('tawakkul');
  if (lowerContent.match(/\b(sincer|ikhlas|pure|intention)\b/)) suggestions.push('sincerity');

  // Relationships & Social
  if (lowerContent.match(/\b(parent|mother|father|family)\b/)) suggestions.push('family');
  if (lowerContent.match(/\b(marriage|spouse|husband|wife)\b/)) suggestions.push('marriage');
  if (lowerContent.match(/\b(children|child|kids|parenting)\b/)) suggestions.push('parenting');
  if (lowerContent.match(/\b(friend|friendship|companion)\b/)) suggestions.push('friendship');
  if (lowerContent.match(/\b(community|ummah|brotherhood|sisterhood)\b/)) suggestions.push('community');
  if (lowerContent.match(/\b(neighbor|neighbour)\b/)) suggestions.push('neighbors');

  // Trials & Challenges
  if (lowerContent.match(/\b(trial|test|difficulty|hardship|struggle)\b/)) suggestions.push('trial');
  if (lowerContent.match(/\b(sad|grief|sorrow|loss)\b/)) suggestions.push('grief');
  if (lowerContent.match(/\b(anxiety|worry|stress|concern)\b/)) suggestions.push('anxiety');
  if (lowerContent.match(/\b(fear|afraid|scared|khawf)\b/)) suggestions.push('fear');
  if (lowerContent.match(/\b(anger|angry|frustrat)\b/)) suggestions.push('anger');
  if (lowerContent.match(/\b(doubt|uncertain|confusion)\b/)) suggestions.push('doubt');

  // Positive States & Growth
  if (lowerContent.match(/\b(hope|optimis|positive)\b/)) suggestions.push('hope');
  if (lowerContent.match(/\b(joy|happy|happiness|delight)\b/)) suggestions.push('joy');
  if (lowerContent.match(/\b(peace|tranquil|calm|serenity)\b/)) suggestions.push('peace');
  if (lowerContent.match(/\b(guidance|hidayah|guided)\b/)) suggestions.push('guidance');
  if (lowerContent.match(/\b(growth|improve|better|progress)\b/)) suggestions.push('growth');
  if (lowerContent.match(/\b(reflection|contemplate|ponder|think)\b/)) suggestions.push('reflection');

  // Knowledge & Learning
  if (lowerContent.match(/\b(knowledge|learn|study|ilm)\b/)) suggestions.push('knowledge');
  if (lowerContent.match(/\b(wisdom|wise|hikma)\b/)) suggestions.push('wisdom');
  if (lowerContent.match(/\b(understand|comprehend|grasp)\b/)) suggestions.push('understanding');
  if (lowerContent.match(/\b(question|ask|curious|wonder)\b/)) suggestions.push('questions');

  // Spiritual States
  if (lowerContent.match(/\b(repent|tawbah|regret|sorry)\b/)) suggestions.push('repentance');
  if (lowerContent.match(/\b(rememb|aware|conscious|mindful)\b/)) suggestions.push('mindfulness');
  if (lowerContent.match(/\b(love|loving|beloved|mahabbah)\b/)) suggestions.push('love');
  if (lowerContent.match(/\b(fear.*allah|taqwa|conscious|pious)\b/)) suggestions.push('taqwa');

  // Life Areas
  if (lowerContent.match(/\b(work|job|career|profession)\b/)) suggestions.push('work');
  if (lowerContent.match(/\b(money|wealth|finance|rizq)\b/)) suggestions.push('wealth');
  if (lowerContent.match(/\b(health|sick|illness|disease)\b/)) suggestions.push('health');
  if (lowerContent.match(/\b(death|dying|passed)\b/)) suggestions.push('death');
  if (lowerContent.match(/\b(justice|fair|rights|oppression)\b/)) suggestions.push('justice');

  // Personal Development
  if (lowerContent.match(/\b(habit|routine|practice|discipline)\b/)) suggestions.push('habits');
  if (lowerContent.match(/\b(goal|aim|objective|target)\b/)) suggestions.push('goals');
  if (lowerContent.match(/\b(change|transform|different)\b/)) suggestions.push('change');
  if (lowerContent.match(/\b(remind|reminder|memory)\b/)) suggestions.push('reminder');

  // Remove duplicates and return max 8 suggestions (prioritize first matches)
  return [...new Set(suggestions)].slice(0, 8);
};

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
  const [suggestedTags, setSuggestedTags] = useState([]);
  const textareaRef = useRef(null);

  // Focus textarea after panel opens, but without scrolling
  useEffect(() => {
    if (isOpen && textareaRef.current) {
      // Small delay to ensure panel is fully rendered
      setTimeout(() => {
        textareaRef.current?.focus({ preventScroll: true });
      }, 100);
    }
  }, [isOpen]);

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

  // Smart tag suggestions with debouncing
  useEffect(() => {
    if (!content || content.length < 10) {
      setSuggestedTags([]);
      return;
    }

    const timeoutId = setTimeout(() => {
      const suggestions = getSuggestedTags(content);
      // Filter out tags that are already added
      const newSuggestions = suggestions.filter(tag => !tags.includes(tag));
      setSuggestedTags(newSuggestions);
    }, 500); // 500ms debounce

    return () => clearTimeout(timeoutId);
  }, [content, tags]);

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
          animation: 'slideInRight 0.3s ease',
          overflow: 'hidden'
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
            alignItems: 'center',
            flexShrink: 0
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

        {/* Content - Scrollable */}
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden', padding: '24px' }}>
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
              ref={textareaRef}
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
            />
          </div>

          {/* Tags */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontWeight: '700', marginBottom: '8px', color: 'var(--primary-teal)' }}>
              Tags
            </label>

            {/* Smart Tag Suggestions */}
            {suggestedTags.length > 0 && (
              <div style={{ marginBottom: '12px' }}>
                <p style={{ fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '8px' }}>
                  ✨ Suggested tags:
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {suggestedTags.map(tag => (
                    <button
                      key={tag}
                      onClick={() => handleAddTag(tag)}
                      style={{
                        background: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)',
                        color: 'var(--primary-teal)',
                        padding: '6px 12px',
                        borderRadius: '20px',
                        fontSize: '0.85rem',
                        fontWeight: '600',
                        border: '1px dashed var(--primary-teal)',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                      }}
                      onMouseEnter={(e) => {
                        e.target.style.background = 'var(--primary-teal)';
                        e.target.style.color = 'white';
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.background = 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)';
                        e.target.style.color = 'var(--primary-teal)';
                      }}
                    >
                      + {tag}
                    </button>
                  ))}
                </div>
              </div>
            )}

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

        </div>

        {/* Footer - Fixed at bottom */}
        <div
          style={{
            padding: '24px',
            borderTop: '2px solid var(--border-light)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            background: 'var(--cream)',
            flexShrink: 0
          }}
        >
          {/* Error message - always visible in footer */}
          {error && (
            <div
              style={{
                padding: '12px',
                background: 'rgba(220, 38, 38, 0.1)',
                border: '2px solid var(--error-color)',
                borderRadius: '8px',
                color: 'var(--error-color)',
                fontWeight: '600',
                textAlign: 'center'
              }}
            >
              {error}
            </div>
          )}

          {/* Buttons */}
          <div style={{ display: 'flex', gap: '12px' }}>
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
