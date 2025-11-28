'use client';

/**
 * AuthSkeleton Component
 * Shows a loading state while checking authentication
 */
export function AuthSkeleton() {
  return (
    <div className="auth-skeleton">
      <div className="skeleton-container">
        <div className="skeleton-logo"></div>
        <div className="skeleton-title"></div>
        <div className="skeleton-subtitle"></div>
        <div className="skeleton-spinner"></div>
      </div>

      <style jsx>{`
        .auth-skeleton {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          background: var(--background);
        }

        .skeleton-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 20px;
        }

        .skeleton-logo {
          width: 80px;
          height: 80px;
          border-radius: 50%;
          background: linear-gradient(
            90deg,
            var(--cream) 0%,
            var(--cream-dark) 50%,
            var(--cream) 100%
          );
          background-size: 200% 100%;
          animation: shimmer 1.5s ease-in-out infinite;
        }

        .skeleton-title {
          width: 200px;
          height: 32px;
          border-radius: 8px;
          background: linear-gradient(
            90deg,
            var(--cream) 0%,
            var(--cream-dark) 50%,
            var(--cream) 100%
          );
          background-size: 200% 100%;
          animation: shimmer 1.5s ease-in-out infinite;
        }

        .skeleton-subtitle {
          width: 150px;
          height: 20px;
          border-radius: 6px;
          background: linear-gradient(
            90deg,
            var(--cream) 0%,
            var(--cream-dark) 50%,
            var(--cream) 100%
          );
          background-size: 200% 100%;
          animation: shimmer 1.5s ease-in-out infinite;
        }

        .skeleton-spinner {
          width: 40px;
          height: 40px;
          border: 4px solid var(--cream);
          border-top: 4px solid var(--primary-teal);
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-top: 20px;
        }

        @keyframes shimmer {
          0% {
            background-position: 200% 0;
          }
          100% {
            background-position: -200% 0;
          }
        }

        @keyframes spin {
          0% {
            transform: rotate(0deg);
          }
          100% {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}