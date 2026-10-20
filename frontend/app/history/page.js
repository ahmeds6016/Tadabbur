'use client';
import { useState, useEffect, useRef } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import Link from 'next/link';
import { createRequestIdentity } from '../lib/requestIdentity';
import { requestErrorFrom, userMessage } from '../lib/errors';
import { auth } from '../lib/firebase';
import { BACKEND_URL } from '../lib/config';
import ErrorNotice from '../components/ErrorNotice';
import { reportBackendFailure, reportBackendSuccess } from '../lib/backendHealth';
import BottomNav from '../components/BottomNav';

export default function QueryHistoryPage() {
  const requests = useRef(createRequestIdentity()).current;
  const [nextCursor, setNextCursor] = useState(null);
  const [user, setUser] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadError, setLoadError] = useState(null);
  const [needsSignIn, setNeedsSignIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      requests.reset(); setNextCursor(null);
      const authTicket = requests.start("auth", currentUser?.uid ?? null);
      setHistory([]); setLoadError(null);
      setIsLoading(true);
      setUser(currentUser);
      if (currentUser) {
        await fetchHistory(currentUser);
      }
      if (requests.current(authTicket, auth.currentUser?.uid ?? null)) setIsLoading(false);
    });
    return () => { requests.reset(); unsubscribe(); };
  }, []);

  const fetchHistory = async (currentUser, cursor = null) => {
    if (!cursor) setNextCursor(null);
    const ticket = requests.start('history', currentUser?.uid ?? null);
    const current = () => requests.current(ticket, auth.currentUser?.uid ?? null);
    setLoadError(null); setNeedsSignIn(false);
    try {
      const token = await currentUser.getIdToken();
      const res = await fetch(`${BACKEND_URL}/query-history?limit=50${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) throw await requestErrorFrom(res, { fallback: "We couldn't load your saved activity. Please try again." });
      if (res.ok) {
        reportBackendSuccess();
        const data = await res.json();
        if (!current()) return;
        // Filter to only show Deep Tafsir entries (exclude Explore mode queries)
        const tafsirHistory = (data.history || []).filter(
          item => !item.approach || item.approach === 'tafsir'
        );
        setHistory(previous => cursor ? [...previous, ...tafsirHistory] : tafsirHistory);
        setNextCursor(data.next_cursor || null);
      }
    } catch (err) {
      if (!current()) return;
      if (err instanceof TypeError) reportBackendFailure();
      setNeedsSignIn(err.status === 401);
      setLoadError(userMessage(err, "We couldn't load your saved activity. Please try again."));
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Unknown date';
    try {
      let date;
      // Handle Firestore timestamp format {seconds: number, nanoseconds: number}
      if (timestamp.seconds) {
        date = new Date(timestamp.seconds * 1000);
      }
      // Handle alternate format {_seconds: number}
      else if (timestamp._seconds) {
        date = new Date(timestamp._seconds * 1000);
      }
      // Fallback: try to parse as ISO string or number
      else {
        date = new Date(timestamp);
      }

      // Validate the date is valid
      if (isNaN(date.getTime())) {
        return 'Unknown date';
      }

      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Unknown date';
    }
  };

  if (isLoading) {
    return (
      <div className="container">
        <div className="card">
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container">
        <div className="card">
          <h1>Please sign in to view your query history</h1>
          <Link href="/">
            <button style={{ marginTop: '20px' }}>Go to Home</button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container" style={{ paddingBottom: 100 }}>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
          <h1>Query History</h1>
        </div>

        <p style={{ marginBottom: '24px', color: '#666' }}>
          Your recent queries are saved here. Click any query to run it again.
        </p>

        <ErrorNotice message={loadError} actionLabel={needsSignIn ? 'Sign in again' : 'Retry'}
          onAction={async () => needsSignIn ? signOut(auth).then(() => window.location.assign('/')) : fetchHistory(user)} />

        {history.length === 0 && !loadError ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#999' }}>
            <p style={{ fontSize: '1.5rem', marginBottom: '16px', color: 'var(--primary-teal)' }}>No history yet</p>
            <p style={{ fontSize: '1.2rem' }}>No queries yet</p>
            <p style={{ marginTop: '8px' }}>Your tafsir search history will appear here as you use the app.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {history.map((item) => (
              <Link
                key={item.id}
                href={`/?query=${encodeURIComponent(item.query)}`}
                style={{ textDecoration: 'none' }}
              >
                <div
                  style={{
                    padding: '16px',
                    background: 'white',
                    borderRadius: '10px',
                    border: '1px solid var(--border-light)',
                    cursor: 'pointer'
                  }}
                  className="history-item"
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: '700', fontSize: '1.1rem', marginBottom: '8px', color: 'var(--primary-teal)' }}>
                        {item.query}
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#999' }}>
                        {formatTimestamp(item.timestamp)}
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                      {item.hasResult ? (
                        <span style={{ background: 'var(--success-color)', color: 'white', padding: '4px 12px', borderRadius: '12px', fontSize: '0.8rem', fontWeight: '600' }}>
                          Success
                        </span>
                      ) : (
                        <span style={{ background: 'var(--error-color)', color: 'white', padding: '4px 12px', borderRadius: '12px', fontSize: '0.8rem', fontWeight: '600' }}>
                          Failed
                        </span>
                      )}
                      <span style={{ fontSize: '0.75rem', color: 'var(--primary-teal)', fontWeight: '600' }}>
                        Click to re-run →
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
        {nextCursor && <button onClick={() => fetchHistory(user, nextCursor)}>Load more history</button>}
      </div>

      <style jsx>{`
        .history-item:hover {
          border-color: var(--primary-teal-light, #5eead4);
        }
      `}</style>

      <BottomNav user={user} />
    </div>
  );
}
