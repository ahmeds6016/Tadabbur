'use client';

import styles from './VerseCard.module.css';
import { PenLine, Bookmark, Share2 } from 'lucide-react';

/**
 * VerseCard Component
 * Displays a Quranic verse with Arabic text, translation, and actions
 * Uses CSS Modules for scoped styling
 */
export function VerseCard({
  verse,
  onAnnotate,
  onBookmark,
  onShare,
  annotationCount = 0,
  showTransliteration = false
}) {
  const {
    surah_number,
    verse_number,
    arabic_text,
    translation,
    transliteration,
    surah_name
  } = verse;

  return (
    <div className={styles.card}>
      {/* Header with reference and actions */}
      <div className={styles.header}>
        <div className={styles.reference}>
          <span>{surah_number}:{verse_number}</span>
          {surah_name && (
            <span className={styles.surahName}>• {surah_name}</span>
          )}
        </div>

        <div className={styles.actions}>
          {onAnnotate && (
            <button
              onClick={() => onAnnotate(verse)}
              className={styles.actionButton}
              aria-label="Add annotation"
            >
              <PenLine size={14} />
              <span>Note</span>
            </button>
          )}
          {onBookmark && (
            <button
              onClick={() => onBookmark(verse)}
              className={styles.actionButton}
              aria-label="Bookmark verse"
            >
              <Bookmark size={14} />
              <span>Save</span>
            </button>
          )}
          {onShare && (
            <button
              onClick={() => onShare(verse)}
              className={styles.actionButton}
              aria-label="Share verse"
            >
              <Share2 size={14} />
              <span>Share</span>
            </button>
          )}
        </div>
      </div>

      {/* Arabic text */}
      <div className={styles.arabicText} lang="ar" dir="rtl">
        {arabic_text}
      </div>

      {/* Translation */}
      <div className={styles.translation}>
        {translation}
      </div>

      {/* Transliteration (optional) */}
      {showTransliteration && transliteration && (
        <div className={styles.transliteration}>
          {transliteration}
        </div>
      )}

      {/* Footer with metadata */}
      <div className={styles.footer}>
        <div className={styles.metadata}>
          <span className={styles.metaItem}>
            Sahih International
          </span>
        </div>

        {annotationCount > 0 && (
          <div className={styles.annotationIndicator}>
            <span>Notes</span>
            <span className={styles.annotationCount}>
              {annotationCount}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
