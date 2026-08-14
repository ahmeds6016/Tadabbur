'use client';

import { useState } from 'react';
import { THEME_QUICK_SELECTS } from './SurahVersePicker';

export default function ThemeExplorer({ onSelect }) {
  const [selectedThemeId, setSelectedThemeId] = useState(null);
  const selectedTheme = THEME_QUICK_SELECTS.find(theme => theme.id === selectedThemeId);

  return (
    <section className="theme-explorer" aria-labelledby="theme-explorer-title">
      <h2 id="theme-explorer-title">Explore a theme</h2>
      <div className="theme-chips" aria-label="Quran themes">
        {THEME_QUICK_SELECTS.map(theme => (
          <button
            key={theme.id}
            type="button"
            className="theme-chip"
            aria-pressed={selectedThemeId === theme.id}
            onClick={() => setSelectedThemeId(
              selectedThemeId === theme.id ? null : theme.id
            )}
          >
            {theme.label}
          </button>
        ))}
      </div>

      {selectedTheme && (
        <div className="theme-suggestions">
          <p className="editorial-label">Editorial suggestions</p>
          <div className="verse-cards">
            {selectedTheme.verses.slice(0, 4).map(verse => (
              <button
                key={verse.query}
                type="button"
                className="verse-card"
                onClick={() => onSelect?.(verse.query)}
              >
                <span className="verse-reference">{verse.query}</span>
                <span className="verse-description">{verse.description}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <style jsx>{`
        .theme-explorer {
          margin: 0 0 16px;
          padding: 16px;
          background: var(--color-surface, white);
          border: 1px solid var(--color-border, #e5e7eb);
          border-radius: 10px;
        }
        h2 {
          margin: 0 0 10px;
          font-size: 1rem;
          color: var(--foreground, #1f2937);
        }
        .theme-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .theme-chip {
          padding: 7px 12px;
          border: 1px solid var(--primary-teal, #0d9488);
          border-radius: 999px;
          background: var(--color-surface, white);
          color: var(--primary-teal, #0d9488);
          font-size: 0.78rem;
          font-weight: 600;
          cursor: pointer;
        }
        .theme-chip[aria-pressed='true'] {
          background: var(--primary-teal, #0d9488);
          color: white;
        }
        .theme-suggestions {
          margin-top: 16px;
        }
        .editorial-label {
          margin: 0 0 8px;
          color: var(--color-text-secondary, #6b7280);
          font-size: 0.7rem;
          font-weight: 700;
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }
        .verse-cards {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
        }
        .verse-card {
          display: flex;
          flex-direction: column;
          gap: 4px;
          min-width: 0;
          padding: 11px 12px;
          border: 1px solid var(--color-border, #e5e7eb);
          border-radius: 9px;
          background: var(--cream, #faf6f0);
          text-align: left;
          cursor: pointer;
        }
        .verse-card:hover {
          border-color: var(--primary-teal, #0d9488);
        }
        .verse-reference {
          color: var(--primary-teal, #0d9488);
          font-size: 0.82rem;
          font-weight: 700;
        }
        .verse-description {
          overflow: hidden;
          color: var(--color-text-secondary, #5f6368);
          font-size: 0.74rem;
          line-height: 1.35;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        @media (max-width: 520px) {
          .verse-cards {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </section>
  );
}
