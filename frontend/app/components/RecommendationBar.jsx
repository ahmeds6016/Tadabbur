'use client';

export default function RecommendationBar({ recommendations, onStudyVerse }) {
  const visibleRecommendations = Array.isArray(recommendations)
    ? recommendations
        .filter(rec => rec?.surah && rec?.verse)
        .slice(0, 3)
    : [];

  if (visibleRecommendations.length === 0) return null;

  return (
    <div className="recommendation-bar">
      <h3 className="answer-section-heading">Continue reflecting</h3>
      <div className="recommendation-scroll">
        {visibleRecommendations.map((rec, index) => (
          <button
            key={`${rec.surah}-${rec.verse}`}
            className="recommendation-pill"
            style={{ animationDelay: `${index * 80}ms` }}
            onClick={() => onStudyVerse(rec.surah, rec.verse)}
            aria-label={`Study ${rec.surah_name || `Surah ${rec.surah}`} ${rec.surah}:${rec.verse}${rec.reason ? `: ${rec.reason}` : ''}`}
          >
            <span className="pill-verse">
              {rec.surah_name} {rec.surah}:{rec.verse}
            </span>
            {rec.reason && (
              <span className="pill-reason">{rec.reason}</span>
            )}
          </button>
        ))}
      </div>

      <style jsx>{`
        @keyframes fadeSlideIn {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .recommendation-bar {
          margin-top: 16px;
          animation: fadeSlideIn 0.4s ease forwards;
        }

        .recommendation-scroll {
          display: flex;
          gap: 10px;
          overflow-x: auto;
          scroll-snap-type: x mandatory;
          scroll-padding-inline: 8px;
          padding: 4px 8px 12px;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: thin;
        }

        .recommendation-pill {
          flex: 0 0 220px;
          min-width: 0;
          box-sizing: border-box;
          scroll-snap-align: start;
          display: flex;
          flex-direction: column;
          gap: 4px;
          padding: 10px 16px;
          background: var(--cream, #faf6f0);
          border: 1px solid var(--border-light, #e5e7eb);
          border-radius: 20px;
          cursor: pointer;
          text-align: left;
          max-width: 100%;
          transition: border-color 0.2s, box-shadow 0.2s;
          opacity: 0;
          animation: fadeSlideIn 0.4s ease forwards;
        }

        .recommendation-pill:hover {
          border-color: var(--primary-teal, #0d9488);
          box-shadow: 0 2px 8px rgba(13, 148, 136, 0.12);
        }

        .recommendation-pill:active {
          background: var(--color-surface-muted, #f0ebe3);
        }

        .pill-verse {
          font-size: 0.82rem;
          font-weight: 600;
          color: var(--primary-teal, #0d9488);
          white-space: normal;
          overflow-wrap: anywhere;
        }

        .pill-reason {
          font-size: 0.72rem;
          color: var(--color-text-secondary, #6b7280);
          line-height: 1.3;
          overflow-wrap: anywhere;
        }
        @media (max-width: 640px) {
          .recommendation-scroll {
            flex-direction: column;
            overflow-x: visible;
            scroll-snap-type: none;
            padding: 4px 0 12px;
          }

          .recommendation-pill {
            flex: 0 0 auto;
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}
