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
          <h1>Tafsir Simplified</h1>
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
                Deep Tafsir Commentary
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
              <ul className="lessons-list">
                {lessons_practical_applications.map((lesson, index) => (
                  <li key={index} className="lesson-item">{lesson.point}</li>
                ))}
              </ul>
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
            Shared from <strong>Tafsir Simplified</strong>
          </p>
          <p style={{ margin: '8px 0 0 0', fontSize: '0.85rem', color: '#888' }}>
            Classical Quranic commentary personalized to your learning style
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
          Explore Tafsir Simplified
        </Link>
      </div>
    </div>
  );
}
