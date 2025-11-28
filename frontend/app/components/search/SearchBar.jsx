'use client';

import { useState, useCallback } from 'react';
import { SearchModeSelector } from './SearchModeSelector';

/**
 * SearchBar Component
 * Handles search input and mode selection
 * Extracted from main page for reusability and testing
 */
export function SearchBar({
  onSearch,
  initialQuery = '',
  initialMode = 'tafsir',
  isLoading = false,
  placeholder = "What would you like to explore in the Quran today?",
  showModeSelector = true
}) {
  const [query, setQuery] = useState(initialQuery);
  const [mode, setMode] = useState(initialMode);
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = useCallback(
    (e) => {
      e.preventDefault();

      // Validate input
      const trimmedQuery = query.trim();
      if (!trimmedQuery) {
        return;
      }

      // Call parent's search handler
      onSearch({
        query: trimmedQuery,
        approach: mode
      });
    },
    [query, mode, onSearch]
  );

  const handleKeyDown = useCallback((e) => {
    // Allow Escape key to clear input
    if (e.key === 'Escape') {
      setQuery('');
      e.target.blur();
    }
  }, []);

  return (
    <div className="search-bar-container">
      {/* Mode selector cards */}
      {showModeSelector && (
        <SearchModeSelector
          mode={mode}
          onModeChange={setMode}
        />
      )}

      {/* Search form */}
      <form
        onSubmit={handleSubmit}
        className={`search-form ${isFocused ? 'focused' : ''}`}
        role="search"
        aria-label="Search the Quran"
      >
        <div className="search-input-group">
          {/* Mode indicator badge */}
          <div className="mode-badge">
            {mode === 'tafsir' ? '📖 Tafsir' : '🔍 Explore'}
          </div>

          {/* Search input */}
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="search-input"
            disabled={isLoading}
            aria-label="Search query"
            autoComplete="off"
            spellCheck="false"
          />

          {/* Clear button */}
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="clear-button"
              aria-label="Clear search"
              disabled={isLoading}
            >
              ×
            </button>
          )}

          {/* Submit button */}
          <button
            type="submit"
            className="search-button"
            disabled={isLoading || !query.trim()}
            aria-label="Submit search"
          >
            {isLoading ? (
              <span className="loading-spinner"></span>
            ) : (
              'Search'
            )}
          </button>
        </div>
      </form>

      <style jsx>{`
        .search-bar-container {
          width: 100%;
          max-width: 800px;
          margin: 0 auto;
        }

        .search-form {
          margin-top: 24px;
          transition: transform 0.3s ease;
        }

        .search-form.focused {
          transform: translateY(-2px);
        }

        .search-input-group {
          display: flex;
          align-items: center;
          background: white;
          border: 2px solid var(--border-light);
          border-radius: 16px;
          padding: 4px;
          transition: all 0.3s ease;
          box-shadow: var(--shadow-soft);
        }

        .search-form.focused .search-input-group {
          border-color: var(--primary-teal);
          box-shadow: var(--shadow-medium);
        }

        .mode-badge {
          padding: 8px 12px;
          background: var(--cream);
          border-radius: 10px;
          font-size: 0.9rem;
          font-weight: 600;
          color: var(--text-primary);
          white-space: nowrap;
          margin-left: 4px;
        }

        .search-input {
          flex: 1;
          padding: 12px 16px;
          border: none;
          background: transparent;
          font-size: 1rem;
          color: var(--text-primary);
          outline: none;
        }

        .search-input::placeholder {
          color: var(--text-muted);
        }

        .search-input:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .clear-button {
          background: none;
          border: none;
          font-size: 1.5rem;
          color: var(--text-muted);
          cursor: pointer;
          padding: 0 12px;
          height: 100%;
          display: flex;
          align-items: center;
          transition: color 0.2s;
        }

        .clear-button:hover {
          color: var(--text-primary);
        }

        .clear-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .search-button {
          padding: 12px 24px;
          background: var(--primary-teal);
          color: white;
          border: none;
          border-radius: 12px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          margin-right: 4px;
        }

        .search-button:hover:not(:disabled) {
          background: var(--primary-teal-dark);
          transform: translateY(-1px);
        }

        .search-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .loading-spinner {
          display: inline-block;
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        /* Mobile adjustments */
        @media (max-width: 640px) {
          .search-input-group {
            flex-direction: column;
            padding: 12px;
            gap: 12px;
          }

          .mode-badge {
            align-self: flex-start;
          }

          .search-input {
            width: 100%;
            padding: 12px 0;
          }

          .clear-button {
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
          }

          .search-button {
            width: 100%;
            padding: 14px;
          }
        }
      `}</style>
    </div>
  );
}