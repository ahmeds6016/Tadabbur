'use client';
import { useState, useEffect } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../lib/firebase';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

import ImanSettings from '../components/ImanSettings';
import BottomNav from '../components/BottomNav';

export default function SettingsPage() {
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
      <div className="settings-page">
        <div className="loading-state">Loading...</div>
        <style jsx>{`
          .settings-page { min-height: 100vh; background: var(--cream, #faf6f0); }
          .loading-state {
            display: flex; align-items: center; justify-content: center;
            min-height: 60vh; color: #6b7280;
          }
        `}</style>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="settings-page">
        <div className="auth-gate">
          <p>Sign in to access settings.</p>
          <Link href="/"><button className="go-home-btn">Go to Home</button></Link>
        </div>
        <BottomNav user={null} />
        <style jsx>{`
          .settings-page { min-height: 100vh; background: var(--cream, #faf6f0); }
          .auth-gate {
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; min-height: 60vh; gap: 12px;
          }
          .auth-gate p { color: #6b7280; font-size: 0.95rem; }
          .go-home-btn {
            padding: 10px 24px; border-radius: 8px; border: none;
            background: var(--primary-teal, #0d9488); color: white;
            font-size: 0.95rem; cursor: pointer;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="settings-page">
      <div className="settings-container">
        <header className="settings-header">
          <Link href="/journal" className="back-link">
            <ArrowLeft size={20} />
          </Link>
          <h1>Settings</h1>
        </header>

        <ImanSettings user={user} />
      </div>

      <BottomNav user={user} />

      <style jsx>{`
        .settings-page {
          min-height: 100vh;
          background: var(--cream, #faf6f0);
        }
        .settings-container {
          max-width: 600px;
          margin: 0 auto;
          padding: 16px 16px 80px;
        }
        .settings-header {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 0 16px;
        }
        .back-link {
          color: #6b7280;
          display: flex;
          align-items: center;
          transition: color 0.15s ease;
        }
        .back-link:hover {
          color: var(--primary-teal, #0d9488);
        }
        .settings-header h1 {
          margin: 0;
          font-size: 1.4rem;
          color: var(--primary-teal, #0d9488);
          font-weight: 700;
        }
      `}</style>
    </div>
  );
}
