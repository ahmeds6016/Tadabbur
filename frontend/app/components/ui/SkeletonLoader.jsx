'use client';

/**
 * SkeletonLoader Components
 * Provides skeleton loading states for different content types
 * Improves perceived performance and user experience
 */

// Base skeleton component
export function Skeleton({ width, height, className = '', variant = 'text' }) {
  const variants = {
    text: 'skeleton-text',
    rectangular: 'skeleton-rectangular',
    circular: 'skeleton-circular',
  };

  return (
    <>
      <div
        className={`skeleton ${variants[variant]} ${className}`}
        style={{ width, height }}
      />
      <style jsx>{`
        .skeleton {
          background: linear-gradient(
            90deg,
            var(--cream) 0%,
            var(--cream-dark) 50%,
            var(--cream) 100%
          );
          background-size: 200% 100%;
          animation: shimmer 1.5s ease-in-out infinite;
          border-radius: 4px;
        }

        .skeleton-text {
          height: 16px;
          margin: 4px 0;
        }

        .skeleton-rectangular {
          border-radius: 8px;
        }

        .skeleton-circular {
          border-radius: 50%;
        }

        @keyframes shimmer {
          0% {
            background-position: 200% 0;
          }
          100% {
            background-position: -200% 0;
          }
        }
      `}</style>
    </>
  );
}

// Tafsir result skeleton
export function TafsirSkeleton() {
  return (
    <div className="tafsir-skeleton">
      {/* Verse card skeleton */}
      <div className="skeleton-card">
        <div className="skeleton-header">
          <Skeleton width="80px" height="20px" />
          <Skeleton width="60px" height="32px" variant="rectangular" />
        </div>
        <Skeleton width="100%" height="120px" variant="rectangular" className="skeleton-arabic" />
        <Skeleton width="100%" height="60px" />
        <Skeleton width="80%" height="20px" />
      </div>

      {/* Tafsir explanation skeleton */}
      <div className="skeleton-card">
        <Skeleton width="120px" height="24px" className="skeleton-title" />
        <Skeleton width="100%" height="16px" />
        <Skeleton width="100%" height="16px" />
        <Skeleton width="90%" height="16px" />
        <Skeleton width="75%" height="16px" />
      </div>

      {/* Lessons skeleton */}
      <div className="skeleton-card">
        <Skeleton width="100px" height="24px" className="skeleton-title" />
        <div className="skeleton-list">
          <Skeleton width="95%" height="16px" />
          <Skeleton width="90%" height="16px" />
          <Skeleton width="85%" height="16px" />
        </div>
      </div>

      <style jsx>{`
        .tafsir-skeleton {
          padding: 20px;
        }

        .skeleton-card {
          background: white;
          border-radius: 16px;
          padding: 24px;
          margin-bottom: 20px;
          box-shadow: var(--shadow-soft);
        }

        .skeleton-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .skeleton-arabic {
          margin: 24px 0;
        }

        .skeleton-title {
          margin-bottom: 16px;
        }

        .skeleton-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        @media (max-width: 640px) {
          .skeleton-card {
            padding: 16px;
            border-radius: 12px;
          }
        }
      `}</style>
    </div>
  );
}

// Search suggestions skeleton
export function SuggestionsSkeleton() {
  return (
    <div className="suggestions-skeleton">
      <Skeleton width="150px" height="24px" className="skeleton-title" />
      <div className="skeleton-chips">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton
            key={i}
            width={`${80 + Math.random() * 40}px`}
            height="36px"
            variant="rectangular"
          />
        ))}
      </div>

      <style jsx>{`
        .suggestions-skeleton {
          padding: 20px;
        }

        .skeleton-title {
          margin-bottom: 16px;
        }

        .skeleton-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
        }
      `}</style>
    </div>
  );
}

// Profile skeleton
export function ProfileSkeleton() {
  return (
    <div className="profile-skeleton">
      <div className="skeleton-avatar-section">
        <Skeleton width="80px" height="80px" variant="circular" />
        <div className="skeleton-info">
          <Skeleton width="150px" height="24px" />
          <Skeleton width="200px" height="16px" />
        </div>
      </div>

      <div className="skeleton-stats">
        {[1, 2, 3].map((i) => (
          <div key={i} className="skeleton-stat">
            <Skeleton width="60px" height="32px" />
            <Skeleton width="80px" height="16px" />
          </div>
        ))}
      </div>

      <style jsx>{`
        .profile-skeleton {
          padding: 20px;
        }

        .skeleton-avatar-section {
          display: flex;
          align-items: center;
          gap: 20px;
          margin-bottom: 24px;
        }

        .skeleton-info {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .skeleton-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 16px;
        }

        .skeleton-stat {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
        }
      `}</style>
    </div>
  );
}

// Annotation list skeleton
export function AnnotationListSkeleton() {
  return (
    <div className="annotation-skeleton">
      {[1, 2, 3].map((i) => (
        <div key={i} className="skeleton-annotation">
          <div className="skeleton-annotation-header">
            <Skeleton width="100px" height="16px" />
            <Skeleton width="60px" height="16px" />
          </div>
          <Skeleton width="100%" height="16px" />
          <Skeleton width="90%" height="16px" />
          <Skeleton width="70%" height="16px" />
        </div>
      ))}

      <style jsx>{`
        .annotation-skeleton {
          padding: 20px;
        }

        .skeleton-annotation {
          background: white;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 12px;
          box-shadow: var(--shadow-soft);
        }

        .skeleton-annotation-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 12px;
        }
      `}</style>
    </div>
  );
}

// Table skeleton
export function TableSkeleton({ rows = 5, columns = 4 }) {
  return (
    <div className="table-skeleton">
      <table>
        <thead>
          <tr>
            {Array.from({ length: columns }).map((_, i) => (
              <th key={i}>
                <Skeleton width="100%" height="20px" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={rowIndex}>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <td key={colIndex}>
                  <Skeleton
                    width={colIndex === 0 ? '120px' : '100%'}
                    height="16px"
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <style jsx>{`
        .table-skeleton {
          width: 100%;
          overflow-x: auto;
        }

        table {
          width: 100%;
          border-collapse: collapse;
        }

        th {
          padding: 12px;
          text-align: left;
          border-bottom: 2px solid var(--border-light);
        }

        td {
          padding: 12px;
          border-bottom: 1px solid var(--border-light);
        }
      `}</style>
    </div>
  );
}

// Navigation skeleton
export function NavigationSkeleton() {
  return (
    <div className="nav-skeleton">
      <Skeleton width="40px" height="40px" variant="circular" />
      <div className="nav-items">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} width="80px" height="20px" />
        ))}
      </div>

      <style jsx>{`
        .nav-skeleton {
          display: flex;
          align-items: center;
          gap: 24px;
          padding: 16px 24px;
          background: white;
          box-shadow: var(--shadow-soft);
        }

        .nav-items {
          display: flex;
          gap: 20px;
          flex: 1;
        }

        @media (max-width: 640px) {
          .nav-skeleton {
            justify-content: space-around;
            padding: 12px;
          }

          .nav-items {
            gap: 12px;
          }
        }
      `}</style>
    </div>
  );
}