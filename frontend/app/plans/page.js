'use client';
import { useState, useEffect } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import Link from 'next/link';
import { auth } from '../lib/firebase';
import ReadingPlanCard from '../components/ReadingPlanCard';
import BottomNav from '../components/BottomNav';

export default function PlansPage() {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setIsLoading(false);
    });
    return () => unsubscribe();
  }, []);

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <p style={{ color: 'var(--text-muted, #6b7280)' }}>Loading...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <p style={{ color: 'var(--text-muted, #6b7280)' }}>Please sign in to view your plans.</p>
      </div>
    );
  }

  return (
    <>
      <div style={{
        maxWidth: 800,
        margin: '0 auto',
        padding: '24px 16px 120px',
      }}>
        <h1 style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          color: 'var(--deep-blue, #1e3a5f)',
          marginBottom: 8,
        }}>
          Reading Plans
        </h1>
        <p style={{
          color: 'var(--text-secondary, #64748B)',
          marginBottom: 24,
          fontSize: '0.95rem',
        }}>
          Follow structured reading plans or explore your Quran progress.
        </p>

        {/* Reading Plan Card — shows active plan + browse */}
        <ReadingPlanCard user={user} onStudyVerse={() => {}} />

        {/* Link to full Progress Map */}
        <Link href="/progress" style={{
          display: 'block',
          marginTop: 24,
          padding: '20px 24px',
          background: 'var(--cream, #faf6f0)',
          border: '2px solid var(--border-light, #e5e7eb)',
          borderRadius: 16,
          textDecoration: 'none',
          color: 'var(--foreground, #2c3e50)',
          transition: 'all 0.2s ease',
        }}>
          <div style={{ fontWeight: 600, fontSize: '1.05rem', marginBottom: 4 }}>
            Quran Progress Map
          </div>
          <div style={{ color: 'var(--text-secondary, #64748B)', fontSize: '0.9rem' }}>
            View your exploration across all 114 surahs, earned badges, and overall journey.
          </div>
        </Link>
      </div>

      <BottomNav user={user} />
    </>
  );
}
