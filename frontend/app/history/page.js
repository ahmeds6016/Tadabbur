'use client';
import { useState, useEffect } from 'react';
import { getAuth, onAuthStateChanged } from 'firebase/auth';
import { initializeApp, getApps } from 'firebase/app';
import Link from 'next/link';

const firebaseConfig = {
  apiKey: "AIzaSyBKPuVvuJC1bTUsZsZkiMHRoBRRqF6YqVU",
  authDomain: "tafsir-simplified-6b262.firebaseapp.com",
  projectId: "tafsir-simplified-6b262",
  storageBucket: "tafsir-simplified-6b262.appspot.com",
  messagingSenderId: "69730898944",
  appId: "1:69730898944:web:ee2cbeee72be8d856474e5",
  measurementId: "G-7RZD1G66YH"
};

const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
const auth = getAuth(app);

const BACKEND_URL = 'https://tafsir-backend-612616741510.us-central1.run.app';

export default function QueryHistoryPage() {
  const [user, setUser] = useState(null);
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        await fetchHistory(currentUser);
      }
      setIsLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const fetchHistory = async (currentUser) => {
    try {
      const token = await currentUser.getIdToken();
      const res = await fetch(`${BACKEND_URL}/query-history?limit=50`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        // Filter to only show Deep Tafsir entries (exclude Explore mode queries)
        const tafsirHistory = (data.history || []).filter(
          item => !item.approach || item.approach === 'tafsir'
        );
        setHistory(tafsirHistory);
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
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
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
          <h1>🕒 Query History</h1>
          <Link href="/">
            <button>← Back to Search</button>
          </Link>
        </div>

        <p style={{ marginBottom: '24px', color: '#666' }}>
          Your recent queries are saved here. Click any query to run it again.
        </p>

        {history.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#999' }}>
            <p style={{ fontSize: '3rem', marginBottom: '16px' }}>📝</p>
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
                    padding: '20px',
                    background: 'linear-gradient(135deg, #ffffff 0%, rgba(250, 246, 240, 1) 100%)',
                    borderRadius: '12px',
                    border: '2px solid var(--border-light)',
                    transition: 'all 0.3s ease',
                    cursor: 'pointer'
                  }}
                  className="history-item"
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: '700', fontSize: '1.1rem', marginBottom: '8px', color: 'var(--primary-teal)' }}>
                        📖 {item.query}
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#999' }}>
                        {formatTimestamp(item.timestamp)}
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                      {item.hasResult ? (
                        <span style={{ background: 'var(--success-color)', color: 'white', padding: '4px 12px', borderRadius: '12px', fontSize: '0.8rem', fontWeight: '600' }}>
                          ✓ Success
                        </span>
                      ) : (
                        <span style={{ background: 'var(--error-color)', color: 'white', padding: '4px 12px', borderRadius: '12px', fontSize: '0.8rem', fontWeight: '600' }}>
                          ✗ Failed
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
      </div>

      <style jsx>{`
        .history-item:hover {
          transform: translateX(4px);
          box-shadow: var(--shadow-medium);
          border-color: var(--gold);
        }
      `}</style>
    </div>
  );
}
