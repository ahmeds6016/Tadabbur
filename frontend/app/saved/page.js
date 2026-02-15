'use client';
import { useState, useEffect } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
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
  const [expandedId, setExpandedId] = useState(null);

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

  const handleDelete = async (id) => {
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/saved-searches/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        setSaved(saved.filter(item => item.id !== id));
      }
    } catch (err) {
      // Delete failed silently — user can retry
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
    <div className="container" style={{ paddingBottom: 100 }}>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
          <h1>Saved Answers</h1>
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
                  border: '2px solid var(--primary-teal)',
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
                    border: '2px solid var(--primary-teal)',
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
                onClick={(e) => {
                  // Don't expand if clicking the delete button
                  if (e.target.closest('button')) return;
                  setExpandedId(expandedId === item.id ? null : item.id);
                }}
                style={{
                  padding: '24px',
                  background: 'linear-gradient(135deg, #ffffff 0%, rgba(250, 246, 240, 1) 100%)',
                  borderRadius: '16px',
                  border: '2px solid var(--border-light)',
                  transition: 'all 0.3s ease',
                  cursor: 'pointer',
                  position: 'relative'
                }}
                className="saved-item"
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: '700', fontSize: '1.2rem', marginBottom: '8px', color: 'var(--primary-teal)' }}>
                      {item.title}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '8px' }}>
                      <span style={{ background: 'var(--cream)', padding: '4px 12px', borderRadius: '12px', fontWeight: '600', marginRight: '8px' }}>
                        {item.folder}
                      </span>
                      <span style={{ color: '#999' }}>{formatTimestamp(item.savedAt)}</span>
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
                      border: '2px solid var(--error-color)',
                      padding: '6px 12px',
                      borderRadius: '8px',
                      fontSize: '0.85rem',
                      cursor: 'pointer'
                    }}
                  >
                    Delete
                  </button>
                </div>

                <div style={{ fontSize: '0.95rem', color: '#555', marginBottom: expandedId === item.id ? '12px' : '8px' }}>
                  {item.responseSnippet}...
                </div>

                {/* Visual indicator for expandable content */}
                {expandedId !== item.id && (
                  <div style={{
                    textAlign: 'center',
                    color: 'var(--primary-teal)',
                    fontSize: '0.85rem',
                    fontWeight: '600',
                    marginTop: '8px'
                  }}>
                    Click to view full answer ▼
                  </div>
                )}

                {expandedId === item.id ? (
                  <div>
                    <div style={{
                      textAlign: 'center',
                      color: '#999',
                      fontSize: '0.85rem',
                      marginBottom: '16px',
                      borderTop: '1px solid #e5e7eb',
                      paddingTop: '12px'
                    }}>
                      Click anywhere to collapse ▲
                    </div>
                    {/* Display full response if available */}
                    {item.fullResponse ? (
                      <div style={{ padding: '16px', background: 'var(--cream)', borderRadius: '12px' }}>
                        <div className="markdown-content">
                          {/* Verses */}
                          {item.fullResponse.verses && item.fullResponse.verses.length > 0 && (
                            <div style={{ marginBottom: '24px' }}>
                              <h3 style={{ color: 'var(--primary-teal)', marginBottom: '12px' }}>Relevant Verses</h3>
                              {item.fullResponse.verses.map((verse, idx) => (
                                <div key={idx} style={{ marginBottom: '16px', padding: '12px', background: 'white', borderRadius: '8px' }}>
                                  <p style={{ fontWeight: '700', color: 'var(--gold)' }}>
                                    Surah {verse.surah}, Verse {verse.verse_number}
                                  </p>
                                  {verse.arabic_text && verse.arabic_text !== 'Not available' && (
                                    <p style={{ fontSize: '1.3rem', margin: '8px 0', direction: 'rtl', fontFamily: 'Traditional Arabic, serif' }}>
                                      {verse.arabic_text}
                                    </p>
                                  )}
                                  <p style={{ fontStyle: 'italic', color: '#555' }}>
                                    &ldquo;{verse.text_saheeh_international}&rdquo;
                                  </p>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Tafsir Explanations */}
                          {item.fullResponse.tafsir_explanations && item.fullResponse.tafsir_explanations.length > 0 && (
                            <div style={{ marginBottom: '24px' }}>
                              <h3 style={{ color: 'var(--primary-teal)', marginBottom: '12px' }}>Tafsir Explanations</h3>
                              {item.fullResponse.tafsir_explanations.map((tafsir, idx) => (
                                <div key={idx} style={{ marginBottom: '16px', padding: '12px', background: 'white', borderRadius: '8px' }}>
                                  <h4 style={{ color: 'var(--gold)', marginBottom: '8px' }}>{tafsir.source}</h4>
                                  <ReactMarkdown remarkPlugins={[remarkBreaks]}>{tafsir.explanation}</ReactMarkdown>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Cross References */}
                          {item.fullResponse.cross_references && item.fullResponse.cross_references.length > 0 && (
                            <div style={{ marginBottom: '24px' }}>
                              <h3 style={{ color: 'var(--primary-teal)', marginBottom: '12px' }}>Related Verses</h3>
                              {item.fullResponse.cross_references.map((ref, idx) => (
                                <div key={idx} style={{ padding: '8px 12px', background: 'white', borderRadius: '8px', marginBottom: '8px' }}>
                                  <strong>{ref.verse}</strong>: {ref.relevance}
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Lessons & Applications */}
                          {item.fullResponse.lessons_practical_applications && item.fullResponse.lessons_practical_applications.length > 0 && (
                            <div style={{ marginBottom: '24px' }}>
                              <h3 style={{ color: 'var(--primary-teal)', marginBottom: '12px' }}>Lessons & Practical Applications</h3>
                              <ul style={{ paddingLeft: '20px' }}>
                                {item.fullResponse.lessons_practical_applications.map((lesson, idx) => (
                                  <li key={idx} style={{ marginBottom: '8px', color: '#555' }}>{lesson.point}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Summary */}
                          {item.fullResponse.summary && (
                            <div style={{ padding: '12px', background: 'white', borderRadius: '8px' }}>
                              <h3 style={{ color: 'var(--primary-teal)', marginBottom: '8px' }}>Summary</h3>
                              <p>{item.fullResponse.summary}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div style={{ padding: '16px', background: '#fff3cd', borderRadius: '12px', color: '#856404' }}>
                        Full response data not available for this saved answer. Only the snippet was saved.
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        .saved-item:hover {
          transform: translateY(-2px);
          box-shadow: var(--shadow-medium);
          border-color: var(--gold);
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
