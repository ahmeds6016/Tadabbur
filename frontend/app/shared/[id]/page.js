'use client';
import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import { BACKEND_URL } from '../../lib/config';

export default function SharedPage() {
  const params = useParams();
  const shareId = params.id;
  const [sharedData, setSharedData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchSharedContent = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/share/${shareId}`);

        if (!res.ok) {
          if (res.status === 404) {
            setError('This shared content was not found or may have expired.');
          } else {
            setError('Failed to load shared content.');
          }
          setIsLoading(false);
          return;
        }

        const data = await res.json();
        setSharedData(data);
        setIsLoading(false);
      } catch (err) {
        console.error('Error fetching shared content:', err);
        setError('Failed to load shared content. Please try again.');
        setIsLoading(false);
      }
    };

    if (shareId) {
      fetchSharedContent();
    }
  }, [shareId]);

  if (isLoading) {
    return (
      <div className="container">
        <div className="card">
          <div className="loading-spinner"></div>
          <p style={{ textAlign: 'center', marginTop: '20px', color: '#666' }}>
            Loading shared content...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="card">
          <h1 style={{ color: 'var(--error-color)', textAlign: 'center' }}>
            Error
          </h1>
          <p style={{ textAlign: 'center', color: '#666', fontSize: '1.1rem' }}>
            {error}
          </p>
          <div style={{ textAlign: 'center', marginTop: '24px' }}>
            <Link href="/" style={{
              padding: '12px 24px',
              background: 'var(--gradient-teal-gold)',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '8px',
              fontWeight: '600',
              display: 'inline-block'
            }}>
              Go to Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!sharedData) {
    return null;
  }

  const { query, approach, response, view_count } = sharedData;
  const {
    verses = [],
    tafsir_explanations = [],
    cross_references = [],
    lessons_practical_applications = [],
    summary = ''
  } = response || {};

  return (
    <div className="container">
      <div className="card main-app">
        <div className="header">
          <h1>Tadabbur</h1>
        </div>

        {/* Shared Query Info */}
        <div style={{
          padding: '16px 20px',
          background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
          border: '2px solid #0ea5e9',
          borderRadius: '12px',
          marginBottom: '24px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <p style={{ margin: '0 0 4px 0', fontSize: '0.85rem', color: '#666' }}>
                Shared Query:
              </p>
              <p style={{ margin: 0, fontSize: '1.2rem', fontWeight: '700', color: 'var(--primary-teal)' }}>
                {query}
              </p>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: '#666' }}>
                Deep Quranic Reflection
              </p>
            </div>
            <div style={{ fontSize: '0.85rem', color: '#666' }}>
              {view_count} {view_count === 1 ? 'view' : 'views'}
            </div>
          </div>
        </div>


        {/* Results Display */}
        <div className="results-container">
          {verses.length > 0 && (
            <div className="result-section">
              <h2>Relevant Verses</h2>
              {verses.map((verse, index) => (
                <div key={index} className="verse-card enhanced" style={{ marginBottom: '24px' }}>
                  <div style={{ marginBottom: '16px' }}>
                    <p className="verse-ref" style={{ margin: 0 }}>
                      <strong>{verse.surah_name ? `${verse.surah_name} ` : `Surah ${verse.surah}, `}Verse {verse.verse_number}</strong>
                    </p>
                  </div>
                  {verse.arabic_text && verse.arabic_text !== 'Not available' && (
                    <p className="arabic-text" dir="rtl">{verse.arabic_text}</p>
                  )}
                  <p className="translation">
                    <em>&quot;{verse.text_saheeh_international}&quot;</em>
                  </p>
                </div>
              ))}
            </div>
          )}

          {tafsir_explanations.length > 0 && (
            <div className="result-section">
              <h2>Tafsir Explanations</h2>
              {tafsir_explanations.map((tafsir, index) => (
                <details key={index} className="tafsir-details enhanced" open>
                  <summary>
                    <strong>{tafsir.source}</strong>
                  </summary>
                  <div className="explanation-content markdown-content">
                    <ReactMarkdown remarkPlugins={[remarkBreaks]}>
                      {tafsir.explanation}
                    </ReactMarkdown>
                  </div>
                </details>
              ))}
            </div>
          )}

          {cross_references.length > 0 && (
            <div className="result-section">
              <h2>Related Verses</h2>
              <div className="cross-references">
                {cross_references.map((ref, index) => (
                  <div key={index} className="cross-ref-item">
                    <strong>{ref.verse}</strong>: {ref.relevance}
                  </div>
                ))}
              </div>
            </div>
          )}

          {lessons_practical_applications.length > 0 && (
            <div className="result-section">
              <h2>Lessons &amp; Practical Applications</h2>
              <div style={{ display: 'grid', gap: '16px' }}>
                {lessons_practical_applications.map((lesson, index) => (
                  <div
                    key={index}
                    style={{
                      background: 'white',
                      border: '1px solid #e2e8f0',
                      borderRadius: '12px',
                      padding: '16px',
                      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
                    }}
                  >
                    <div style={{
                      fontWeight: '700',
                      fontSize: '1rem',
                      color: 'var(--primary-teal)',
                      marginBottom: '12px'
                    }}>
                      {lesson.point}
                    </div>

                    {/* Synthesis type: single narrative body */}
                    {lesson.type === 'synthesis' && lesson.body && (
                      <div style={{
                        background: '#f0f9ff',
                        borderLeft: '3px solid #0ea5e9',
                        padding: '12px 14px',
                        borderRadius: '4px',
                        fontSize: '0.95rem',
                        color: '#0c4a6e',
                        lineHeight: '1.7'
                      }}>
                        {lesson.body}
                      </div>
                    )}

                    {/* Contemplation type: principle + question + anchor */}
                    {lesson.type === 'contemplation' && (
                      <div style={{ display: 'grid', gap: '10px' }}>
                        {lesson.core_principle && (
                          <div style={{
                            background: '#f0fdf4',
                            borderLeft: '3px solid #10b981',
                            padding: '10px 12px',
                            borderRadius: '4px'
                          }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#059669', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                              Core Principle
                            </div>
                            <div style={{ fontSize: '0.95rem', color: '#065f46', lineHeight: '1.6' }}>
                              {lesson.core_principle}
                            </div>
                          </div>
                        )}
                        {lesson.contemplation && (
                          <div style={{
                            background: '#faf5ff',
                            borderLeft: '3px solid #a855f7',
                            padding: '10px 12px',
                            borderRadius: '4px'
                          }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#7c3aed', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                              Contemplation
                            </div>
                            <div style={{ fontSize: '0.95rem', color: '#4c1d95', lineHeight: '1.6', fontStyle: 'italic' }}>
                              {lesson.contemplation}
                            </div>
                          </div>
                        )}
                        {lesson.prophetic_anchor && (
                          <div style={{
                            background: '#fefce8',
                            borderLeft: '3px solid #eab308',
                            padding: '10px 12px',
                            borderRadius: '4px'
                          }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#ca8a04', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                              Prophetic Anchor
                            </div>
                            <div style={{ fontSize: '0.95rem', color: '#713f12', lineHeight: '1.6' }}>
                              {lesson.prophetic_anchor}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Progression type: baseline > ascent > peak */}
                    {lesson.type === 'progression' && (
                      <div style={{ display: 'grid', gap: '10px' }}>
                        {lesson.baseline && (
                          <div style={{
                            background: '#f8fafc',
                            borderLeft: '3px solid #94a3b8',
                            padding: '10px 12px',
                            borderRadius: '4px'
                          }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#64748b', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                              The Baseline
                            </div>
                            <div style={{ fontSize: '0.95rem', color: '#334155', lineHeight: '1.6' }}>
                              {lesson.baseline}
                            </div>
                          </div>
                        )}
                        {lesson.ascent && (
                          <div style={{
                            background: '#eff6ff',
                            borderLeft: '3px solid #3b82f6',
                            padding: '10px 12px',
                            borderRadius: '4px'
                          }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#2563eb', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                              The Ascent
                            </div>
                            <div style={{ fontSize: '0.95rem', color: '#1e3a5f', lineHeight: '1.6' }}>
                              {lesson.ascent}
                            </div>
                          </div>
                        )}
                        {lesson.peak && (
                          <div style={{
                            background: '#fdf4ff',
                            borderLeft: '3px solid #d946ef',
                            padding: '10px 12px',
                            borderRadius: '4px'
                          }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#c026d3', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                              The Peak
                            </div>
                            <div style={{ fontSize: '0.95rem', color: '#701a75', lineHeight: '1.6' }}>
                              {lesson.peak}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Fallback for old format or untyped lessons */}
                    {!lesson.type && (
                      <>
                        {lesson.example && (
                          <div style={{
                            background: '#f0fdf4',
                            borderLeft: '3px solid #10b981',
                            padding: '10px 12px',
                            marginBottom: '12px',
                            borderRadius: '4px'
                          }}>
                            <div style={{ fontSize: '0.9rem', color: '#065f46', lineHeight: '1.6' }}>
                              {lesson.example}
                            </div>
                          </div>
                        )}
                        {lesson.action && (
                          <div style={{
                            background: '#fefce8',
                            borderLeft: '3px solid #eab308',
                            padding: '10px 12px',
                            borderRadius: '4px'
                          }}>
                            <div style={{ fontSize: '0.9rem', color: '#713f12', lineHeight: '1.6' }}>
                              {lesson.action}
                            </div>
                          </div>
                        )}
                        {lesson.body && (
                          <div style={{
                            fontSize: '0.95rem',
                            color: '#374151',
                            lineHeight: '1.7'
                          }}>
                            {lesson.body}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {summary && (
            <div className="result-section">
              <h2>Summary</h2>
              <div className="summary-content">
                <p>{summary}</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          marginTop: '32px',
          padding: '16px',
          background: 'var(--cream)',
          borderRadius: '12px',
          textAlign: 'center',
          border: '2px solid var(--border-light)'
        }}>
          <p style={{ margin: 0, fontSize: '0.9rem', color: '#666' }}>
            Shared from <strong>Tadabbur</strong>
          </p>
          <p style={{ margin: '8px 0 0 0', fontSize: '0.85rem', color: '#888' }}>
            A deeper understanding of {query?.includes('-') ? 'these ayat' : 'this ayah'}{query ? ` [${query}]` : ''}.
          </p>
        </div>
      </div>

      {/* Spacer for sticky bottom bar */}
      <div style={{ height: 80 }} />

      {/* Sticky bottom navigation */}
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(1200px, 100%)',
        background: 'rgba(255, 255, 255, 0.98)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderTop: '1px solid var(--border-light, #e5e7eb)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '12px 24px',
        paddingBottom: 'calc(12px + env(safe-area-inset-bottom))',
        zIndex: 1000,
        boxShadow: '0 -2px 10px rgba(0, 0, 0, 0.05)',
        borderRadius: '16px 16px 0 0',
      }}>
        <Link
          href="/"
          style={{
            padding: '12px 28px',
            background: 'linear-gradient(135deg, var(--primary-teal, #0d9488) 0%, var(--gold, #d4af37) 100%)',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '12px',
            fontWeight: '700',
            fontSize: '0.95rem',
          }}
        >
          Explore Tadabbur
        </Link>
      </div>
    </div>
  );
}
