'use client';

import { useEffect, useState } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../../firebase';
import { AuthSkeleton } from './AuthSkeleton';

/**
 * AuthWrapper Component
 * Handles Firebase authentication state and provides user context
 * Separates auth logic from main application logic
 */
export function AuthWrapper({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Subscribe to auth state changes
    const unsubscribe = onAuthStateChanged(
      auth,
      (user) => {
        setUser(user);
        setLoading(false);
        setError(null);
      },
      (error) => {
        console.error('Auth state error:', error);
        setError(error);
        setLoading(false);
      }
    );

    // Cleanup subscription on unmount
    return () => unsubscribe();
  }, []);

  // Show loading skeleton while checking auth
  if (loading) {
    return <AuthSkeleton />;
  }

  // Show error state if auth failed
  if (error) {
    return (
      <div className="auth-error">
        <h2>Authentication Error</h2>
        <p>There was a problem with authentication. Please refresh the page.</p>
        <button onClick={() => window.location.reload()}>
          Refresh Page
        </button>
        <style jsx>{`
          .auth-error {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
            text-align: center;
          }

          .auth-error h2 {
            color: var(--error-color);
            margin-bottom: 16px;
          }

          .auth-error p {
            color: var(--text-secondary);
            margin-bottom: 24px;
          }

          .auth-error button {
            padding: 12px 24px;
            background: var(--primary-teal);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: opacity 0.2s;
          }

          .auth-error button:hover {
            opacity: 0.9;
          }
        `}</style>
      </div>
    );
  }

  // Pass user and auth utilities to children
  return children({
    user,
    isAuthenticated: !!user,
    signOut: () => auth.signOut()
  });
}