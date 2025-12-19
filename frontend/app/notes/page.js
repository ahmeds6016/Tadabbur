'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function NotesRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/annotations');
  }, [router]);

  // Show loading while redirecting
  return (
    <div className="container">
      <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
        <div className="loading-spinner"></div>
        <p style={{ marginTop: '16px', color: '#666' }}>Redirecting to Notes...</p>
      </div>
    </div>
  );
}
