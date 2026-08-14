'use client';

import { useEffect } from 'react';

export default function Error({ error, reset }) {
  useEffect(() => {
    console.error('Route rendering failed', error);
  }, [error]);

  return (
    <main
      role="alert"
      style={{
        minHeight: '70vh',
        display: 'grid',
        placeItems: 'center',
        padding: '24px',
      }}
    >
      <div style={{ maxWidth: '480px', textAlign: 'center' }}>
        <h2 style={{ marginBottom: '12px' }}>This page had a problem</h2>
        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
          Your work is still here. Please try loading this page again.
        </p>
        <button
          type="button"
          onClick={reset}
          style={{
            marginTop: '16px',
            padding: '10px 20px',
            border: 0,
            borderRadius: '8px',
            background: 'var(--primary-teal)',
            color: 'white',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Try again
        </button>
      </div>
    </main>
  );
}
