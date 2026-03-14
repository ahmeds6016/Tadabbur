'use client';
import { useState, useEffect } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import Link from 'next/link';
import { auth } from '../lib/firebase';
import { BACKEND_URL } from '../lib/config';
import ConfirmDialog from '../components/ConfirmDialog';
import BottomNav from '../components/BottomNav';

export default function SavedSearchesPage() {
  const [user, setUser] = useState(null);
  const [saved, setSaved] = useState([]);
  const [folders, setFolders] = useState([]);
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        await Promise.all([fetchSaved(currentUser), fetchFolders(currentUser)]);
      }
      setIsLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const fetchSaved = async (currentUser, folder = null) => {
    try {
      const token = await currentUser.getIdToken();
      const url = folder
        ? `${BACKEND_URL}/saved-searches?folder=${encodeURIComponent(folder)}`
        : `${BACKEND_URL}/saved-searches`;

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setSaved(data.saved || []);
      }
    } catch (err) {
      // Fetch failed — non-critical
    }
  };

  const fetchFolders = async (currentUser) => {
    try {
      const token = await currentUser.getIdToken();
      const res = await fetch(`${BACKEND_URL}/saved-searches/folders`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setFolders(data.folders || []);
      }
    } catch (err) {
      // Folders fetch failed — non-critical
    }
  };

  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  const handleDelete = async (id) => {
    setDeleteError(null);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/saved-searches/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        setSaved(saved.filter(item => item.id !== id));
      } else {
        setDeleteError('Could not delete this item. Please try again.');
      }
    } catch {
      setDeleteError('Could not delete this item. Please try again.');
    }
  };

  const handleFolderSelect = (folderName) => {
    setSelectedFolder(folderName);
    fetchSaved(user, folderName);
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
          <h1>Please sign in to view your saved searches</h1>
          <Link href="/">
            <button style={{ marginTop: '20px' }}>Go to Home</button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="saved-page">
      <div className="saved-inner">
        <div className="saved-header">
          <h1 className="saved-title">Saved Answers</h1>
          <div className="saved-count">{saved.length}</div>
        </div>

        {/* Folder Filter */}
        {folders.length > 0 && (
          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                onClick={() => {
                  setSelectedFolder(null);
                  fetchSaved(user);
                }}
                style={{
                  background: !selectedFolder ? 'var(--primary-teal)' : 'transparent',
                  color: !selectedFolder ? 'white' : 'var(--primary-teal)',
                  border: '1px solid var(--primary-teal)',
                  padding: '8px 16px',
                  borderRadius: '20px',
                  fontSize: '0.9rem'
                }}
              >
                All Folders ({folders.reduce((sum, f) => sum + f.count, 0)})
              </button>
              {folders.map((folder) => (
                <button
                  key={folder.name}
                  onClick={() => handleFolderSelect(folder.name)}
                  style={{
                    background: selectedFolder === folder.name ? 'var(--primary-teal)' : 'transparent',
                    color: selectedFolder === folder.name ? 'white' : 'var(--primary-teal)',
                    border: '1px solid var(--primary-teal)',
                    padding: '8px 16px',
                    borderRadius: '20px',
                    fontSize: '0.9rem'
                  }}
                >
                  {folder.name} ({folder.count})
                </button>
              ))}
            </div>
          </div>
        )}

        {deleteError && (
          <div style={{
            padding: '12px 16px',
            background: 'rgba(220, 38, 38, 0.1)',
            color: 'var(--error-color, #dc2626)',
            borderRadius: 8,
            fontSize: '0.9rem',
            marginBottom: 16,
          }}>
            {deleteError}
          </div>
        )}

        {saved.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#999' }}>
            <p style={{ fontSize: '1.5rem', marginBottom: '16px', color: 'var(--primary-teal)' }}>No saved items</p>
            <p style={{ fontSize: '1.2rem' }}>No saved answers yet</p>
            <p style={{ marginTop: '8px' }}>
              {selectedFolder
                ? `No answers saved in the "${selectedFolder}" folder.`
                : 'Click "Save this Answer" on any search result to bookmark it here.'}
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {saved.map((item) => (
              <div
                key={item.id}
                style={{
                  padding: '16px',
                  background: 'var(--color-surface)',
                  borderRadius: '12px',
                  border: '1px solid var(--color-border-light)',
                  position: 'relative'
                }}
                className="saved-item"
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: '700', fontSize: '1.2rem', marginBottom: '8px', color: 'var(--primary-teal)' }}>
                      {item.title}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)', marginBottom: '8px' }}>
                      <span style={{ background: 'var(--cream)', padding: '4px 12px', borderRadius: '12px', fontWeight: '600', marginRight: '8px' }}>
                        {item.folder}
                      </span>
                      <span style={{ color: 'var(--color-text-muted)' }}>{formatTimestamp(item.savedAt)}</span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteTarget(item.id);
                    }}
                    style={{
                      background: 'transparent',
                      color: 'var(--error-color)',
                      border: '1px solid var(--error-color)',
                      padding: '6px 12px',
                      borderRadius: '8px',
                      fontSize: '0.85rem',
                      cursor: 'pointer'
                    }}
                  >
                    Delete
                  </button>
                </div>

                <div style={{ fontSize: '0.95rem', color: 'var(--color-text-secondary)', marginBottom: '8px' }}>
                  {item.responseSnippet}...
                </div>

                {/* Link to view the verse */}
                {item.query && (
                  <a
                    href={`/?query=${encodeURIComponent(item.query)}`}
                    onClick={(e) => e.stopPropagation()}
                    style={{
                      display: 'inline-block',
                      marginTop: '8px',
                      color: 'var(--primary-teal)',
                      fontSize: '0.85rem',
                      fontWeight: '600',
                      textDecoration: 'none',
                      borderBottom: '1px dashed var(--primary-teal)',
                      paddingBottom: '1px'
                    }}
                  >
                    View {item.query.includes('-') ? 'ayat' : 'ayah'} [{item.query}]
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        .saved-page {
          max-width: 600px;
          margin: 0 auto;
          padding: calc(16px + env(safe-area-inset-top, 0px)) 16px calc(60px + env(safe-area-inset-bottom, 0px));
        }

        .saved-inner {
          /* No card wrapper — direct feed */
        }

        .saved-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 4px 0 12px;
        }

        .saved-title {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--foreground, #1a1a1a);
          margin: 0;
        }

        .saved-count {
          font-size: 0.8rem;
          font-weight: 600;
          color: var(--color-text-secondary, #6b7280);
          background: var(--color-surface-muted, #f3f4f6);
          padding: 4px 10px;
          border-radius: 12px;
        }

        .saved-item:hover {
          border-color: var(--primary-teal-light, #5eead4);
        }

        @media (min-width: 1024px) {
          .saved-page {
            padding: 24px 24px 40px;
            max-width: 640px;
          }
        }
      `}</style>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        title="Delete Saved Answer"
        message="Are you sure you want to delete this saved answer? This cannot be undone."
        confirmText="Delete"
        confirmStyle="danger"
        onConfirm={() => { handleDelete(deleteTarget); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />

      <BottomNav user={user} />
    </div>
  );
}
