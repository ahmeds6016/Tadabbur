'use client';

import { useEffect, useState } from 'react';
import {
  getBackendUnavailable,
  subscribeBackendHealth,
} from '../lib/backendHealth';

export default function BackendStatusBanner() {
  const [isUnavailable, setIsUnavailable] = useState(getBackendUnavailable);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => subscribeBackendHealth((nextValue) => {
    setIsUnavailable(nextValue);
    if (!nextValue) setDismissed(false);
  }), []);

  if (!isUnavailable || dismissed) return null;

  return (
    <div className="backend-status-banner" role="status" aria-live="polite">
      <span>Can&apos;t reach the server — some content may be unavailable. Retrying…</span>
      <button type="button" onClick={() => setDismissed(true)} aria-label="Dismiss server status">
        ×
      </button>
      <style jsx>{`
        .backend-status-banner {
          position: sticky;
          top: 0;
          z-index: 1200;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          padding: 9px 16px;
          border-bottom: 1px solid #d97706;
          background: #fffbeb;
          color: #92400e;
          font-size: 0.875rem;
          font-weight: 500;
          text-align: center;
        }

        button {
          flex: 0 0 auto;
          border: 0;
          background: transparent;
          color: inherit;
          cursor: pointer;
          font-size: 1.25rem;
          line-height: 1;
          padding: 0 4px;
        }

        button:focus-visible {
          outline: 2px solid currentColor;
          outline-offset: 2px;
          border-radius: 3px;
        }

        @media (prefers-color-scheme: dark) {
          .backend-status-banner {
            border-color: #f59e0b;
            background: #451a03;
            color: #fde68a;
          }
        }
      `}</style>
    </div>
  );
}
