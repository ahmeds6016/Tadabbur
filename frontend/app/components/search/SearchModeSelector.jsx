'use client';

import React from 'react';

export function SearchModeSelector({ mode, onModeChange }) {
  return (
    <div className="search-mode-selector">
      <div className="mode-cards">
        <button
          className={`mode-card ${mode === 'tafsir' ? 'active' : ''}`}
          onClick={() => onModeChange('tafsir')}
          aria-pressed={mode === 'tafsir'}
        >
          <div className="mode-icon">📖</div>
          <h3>Deep Tafsir</h3>
          <p>Detailed commentary on specific verses</p>
        </button>

        <button
          className={`mode-card ${mode === 'explore' ? 'active' : ''}`}
          onClick={() => onModeChange('explore')}
          aria-pressed={mode === 'explore'}
        >
          <div className="mode-icon">🔍</div>
          <h3>Topic Explorer</h3>
          <p>Discover verses by theme or concept</p>
        </button>
      </div>

      <style jsx>{`
        .search-mode-selector {
          margin: 20px 0;
          padding: 0 20px;
        }

        .mode-cards {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          max-width: 600px;
          margin: 0 auto;
        }

        .mode-card {
          padding: 24px;
          border: 2px solid var(--border-light);
          border-radius: 16px;
          background: white;
          cursor: pointer;
          transition: all 0.3s ease;
          text-align: center;
        }

        .mode-card:hover {
          transform: translateY(-2px);
          box-shadow: var(--shadow-medium);
        }

        .mode-card.active {
          border-color: var(--primary-teal);
          background: linear-gradient(135deg,
            rgba(13, 148, 136, 0.05) 0%,
            rgba(13, 148, 136, 0.1) 100%);
        }

        .mode-icon {
          font-size: 2rem;
          margin-bottom: 8px;
        }

        .mode-card h3 {
          font-size: 1.1rem;
          font-weight: 700;
          color: var(--foreground);
          margin-bottom: 8px;
        }

        .mode-card p {
          font-size: 0.9rem;
          color: var(--text-secondary);
          line-height: 1.4;
        }

        @media (max-width: 640px) {
          .mode-cards {
            grid-template-columns: 1fr;
          }

          .mode-card {
            padding: 16px;
          }
        }
      `}</style>
    </div>
  );
}