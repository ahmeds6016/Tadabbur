'use client';
import { useState, useEffect, useRef } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import Link from 'next/link';
import { createRequestIdentity } from '../lib/requestIdentity';
import { requestErrorFrom, userMessage } from '../lib/errors';
import { auth } from '../lib/firebase';
import { BACKEND_URL } from '../lib/config';
import ReactMarkdown from 'react-markdown';
import ConfirmDialog from '../components/ConfirmDialog';
import ErrorNotice from '../components/ErrorNotice';
import BottomNav from '../components/BottomNav';
import { reportBackendFailure, reportBackendSuccess } from '../lib/backendHealth';

export default function SavedSearchesPage() {
  const requests = useRef(createRequestIdentity());
  const [snapshot, setSnapshot] = useState(null);
  const [folderCursor, setFolderCursor] = useState(null);
  const [nextCursor, setNextCursor] = useState(null);
  const [user, setUser] = useState(null);
  const [saved, setSaved] = useState([]);
  const [folders, setFolders] = useState([]);
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [needsSignIn, setNeedsSignIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const requestsIdentity = requests.current;
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      requestsIdentity.reset(); setNextCursor(null); setSnapshot(null); setFolderCursor(null);
      const authTicket = requestsIdentity.start("auth", currentUser?.uid ?? null);
      setSaved([]); setFolders([]); setSelectedFolder(null); setDeleteTarget(null); setDeleteError(null); setLoadError(null);
      setIsLoading(true);
      setUser(currentUser);
      if (currentUser) {
        await Promise.all([fetchSaved(currentUser), fetchFolders(currentUser)]);
      }
      if (requestsIdentity.current(authTicket, auth.currentUser?.uid ?? null)) setIsLoading(false);
    });
    return () => { requestsIdentity.reset(); unsubscribe(); };
  }, []);

  const fetchSaved = async (currentUser, folder = null, cursor = null) => {
    if (!cursor) setNextCursor(null);
    const ticket = requests.current.start('saved', currentUser?.uid ?? null);
    const current = () => requests.current.current(ticket, auth.currentUser?.uid ?? null);
    setLoadError(null); setNeedsSignIn(false);
    try {
      const token = await currentUser.getIdToken();
      const url = folder
        ? `${BACKEND_URL}/saved-searches?folder=${encodeURIComponent(folder)}`
        : `${BACKEND_URL}/saved-searches`;

      const pagedUrl = `${url}${url.includes('?') ? '&' : '?'}limit=50${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`;
      const res = await fetch(pagedUrl, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) throw await requestErrorFrom(res, { fallback: "We couldn't load your saved activity. Please try again." });
      if (res.ok) {
        reportBackendSuccess();
        const data = await res.json();
        if (!current()) return;
        setSaved(previous => cursor ? [...previous, ...(data.saved || [])] : data.saved || []);
        setNextCursor(data.next_cursor || null);
      }
    } catch (err) {
      if (!current()) return;
      if (err instanceof TypeError) reportBackendFailure();
      setNeedsSignIn(err.status === 401);
      setLoadError(userMessage(err, "We couldn't load your saved activity. Please try again."));
    }
  };

  const fetchFolders = async (currentUser, cursor = null) => {
    const ticket = requests.current.start('folders', currentUser?.uid ?? null);
    const current = () => requests.current.current(ticket, auth.currentUser?.uid ?? null);
    setLoadError(null); setNeedsSignIn(false);
    try {
      const token = await currentUser.getIdToken();
      const res = await fetch(`${BACKEND_URL}/saved-searches/folders${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) throw await requestErrorFrom(res, { fallback: "We couldn't load your saved activity. Please try again." });
      if (res.ok) {
        reportBackendSuccess();
        const data = await res.json();
        if (!current()) return;
        setFolders(previous => cursor ? [...new Map([...previous, ...(data.folders || [])].map(folder => [folder.name, folder])).values()] : data.folders || []);
        setFolderCursor(data.next_cursor || null);
      }
    } catch (err) {
      if (!current()) return;
      if (err instanceof TypeError) reportBackendFailure();
      setNeedsSignIn(err.status === 401);
      setLoadError(userMessage(err, "We couldn't load your saved activity. Please try again."));
    }
  };

  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  const handleDelete = async (id) => {
    // One ticket per item, so a second delete cannot make the first look stale.
    const ticket = requests.current.start(`delete:${id}`, user?.uid ?? null);
    const current = () => requests.current.current(ticket, auth.currentUser?.uid ?? null);
    setDeleteError(null);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/saved-searches/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!current()) return;
      if (res.ok) {
        setSaved(previous => previous.filter(item => item.id !== id));
        if (id === nextCursor) {
          // The page cursor was the deleted item: continue from the one before it.
          const index = saved.findIndex(item => item.id === id);
          if (index > 0) setNextCursor(saved[index - 1].id);
          else fetchSaved(user, selectedFolder, null);
        }
      } else {
        setDeleteError('Could not delete this item. Please try again.');
      }
    } catch {
      if (!current()) return;
      setDeleteError('Could not delete this item. Please try again.');
    }
  };

  const viewSavedAnswer = async (item) => {
    const ticket = requests.current.start('snapshot', user?.uid ?? null);
    setSnapshot(null); setLoadError(null);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/saved-searches/${encodeURIComponent(item.id)}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw await requestErrorFrom(res);
      const data = await res.json();
      if (requests.current.current(ticket, auth.currentUser?.uid ?? null)) setSnapshot(data);
    } catch (err) {
      if (requests.current.current(ticket, auth.currentUser?.uid ?? null)) { setNeedsSignIn(err.status === 401); setLoadError(userMessage(err, 'This saved answer could not be loaded. Please try again.')); }
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

        {snapshot && <section className="card">
          <h2>Saved answer: {snapshot.query}</h2>
          <p>This stored snapshot may predate current citation checks.</p>
          <button onClick={() => setSnapshot(null)}>Close saved answer</button>
          {(snapshot.response?.verses || []).map((verse, i) => <section key={i}><h3>{verse.surah}:{verse.verse_number}</h3><p lang="ar" dir="rtl">{verse.arabic_text}</p><p>{verse.text_saheeh_international}</p></section>)}
          <ReactMarkdown>{snapshot.response?.summary || ''}</ReactMarkdown>
          {(snapshot.response?.tafsir_explanations || []).map((item, i) => <section key={i}><h3>{item.source}</h3><ReactMarkdown>{item.explanation || ''}</ReactMarkdown></section>)}
          {(snapshot.response?.hadith || []).map((item, i) => <section key={i}><p>{typeof item.reference === 'string' ? item.reference : 'Source excerpt'}</p><ReactMarkdown>{item.text || ''}</ReactMarkdown><p>{item.relevance}</p></section>)}
          {(snapshot.response?.lessons_practical_applications || []).map((item, i) => <section key={i}><h3>{item.point}</h3>{['body', 'core_principle', 'contemplation', 'prophetic_anchor', 'baseline', 'ascent', 'peak'].map(field => item[field] && <ReactMarkdown key={field}>{item[field]}</ReactMarkdown>)}</section>)}
          {(snapshot.response?.cross_references || []).map((item, i) => <p key={i}>{item.verse}: {item.relevance}</p>)}
          <p>{snapshot.response?.reflection_prompt}</p>
        </section>}
        {folderCursor && <button onClick={() => fetchFolders(user, folderCursor)}>Load more folders</button>}
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
                All folders
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
                  {folder.name}
                </button>
              ))}
            </div>
          </div>
        )}

        <ErrorNotice message={deleteError} compact />

        <ErrorNotice message={loadError} actionLabel={needsSignIn ? 'Sign in again' : 'Retry'}
          onAction={async () => needsSignIn ? signOut(auth).then(() => window.location.assign('/')) : Promise.all([fetchSaved(user, selectedFolder), fetchFolders(user)])} />

        {saved.length === 0 && !loadError ? (
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

                <button onClick={() => viewSavedAnswer(item)}>View saved answer</button>
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
        {nextCursor && <button onClick={() => fetchSaved(user, selectedFolder, nextCursor)}>Load more saved answers</button>}
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
