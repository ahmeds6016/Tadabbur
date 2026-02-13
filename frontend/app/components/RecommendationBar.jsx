'use client';

export default function RecommendationBar({ recommendations, onStudyVerse }) {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="recommendation-bar">
      <h3 className="recommendation-header">You might also explore...</h3>
      <div className="recommendation-scroll">
        {recommendations.map((rec, index) => (
          <button
            key={`${rec.surah}-${rec.verse}`}
            className="recommendation-pill"
            style={{ animationDelay: `${index * 80}ms` }}
            onClick={() => onStudyVerse(rec.surah, rec.verse)}
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

        .recommendation-header {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--deep-blue, #1e293b);
          margin: 0 0 10px 4px;
        }

        .recommendation-scroll {
          display: flex;
          gap: 10px;
          overflow-x: auto;
          scroll-snap-type: x mandatory;
          padding: 4px 4px 12px;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: none;
        }

        .recommendation-scroll::-webkit-scrollbar {
          display: none;
        }

        .recommendation-pill {
          flex-shrink: 0;
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
          max-width: 220px;
          transition: border-color 0.2s, box-shadow 0.2s;
          opacity: 0;
          animation: fadeSlideIn 0.4s ease forwards;
        }

        .recommendation-pill:hover {
          border-color: var(--primary-teal, #0d9488);
          box-shadow: 0 2px 8px rgba(13, 148, 136, 0.12);
        }

        .recommendation-pill:active {
          background: #f0ebe3;
        }

        .pill-verse {
          font-size: 0.82rem;
          font-weight: 600;
          color: var(--primary-teal, #0d9488);
          white-space: nowrap;
        }

        .pill-reason {
          font-size: 0.72rem;
          color: #6b7280;
          line-height: 1.3;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  );
}
