'use client';
import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { onAuthStateChanged, EmailAuthProvider, reauthenticateWithCredential, signOut } from 'firebase/auth';
import { auth } from '../lib/firebase';
import { BACKEND_URL } from '../lib/config';
import { requestErrorFrom, userMessage } from '../lib/errors';
import ErrorNotice from '../components/ErrorNotice';

export default function SettingsPage() {
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const [user, setUser] = useState(null);
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState('');
  useEffect(() => onAuthStateChanged(auth, current => {
    setUser(current); setPassword(''); setConfirmation(''); setError(null);
  }), []);

  async function deleteAccount(event) {
    event.preventDefault();
    if (!user || confirmation !== 'DELETE') return;
    const owner = user;
    setBusy(true); setError(null);
    try {
      await reauthenticateWithCredential(owner, EmailAuthProvider.credential(owner.email, password));
      setPassword('');
      const token = await owner.getIdToken(true);
      while (mounted.current && auth.currentUser?.uid === owner.uid) {
        const response = await fetch(`${BACKEND_URL}/account/delete`, {
          method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ confirmation: 'DELETE' }),
        });
        if (!response.ok) throw await requestErrorFrom(response);
        const result = await response.json();
        if (!mounted.current || auth.currentUser?.uid !== owner.uid) return;
        if (result.complete) {
          await signOut(auth);
          localStorage.removeItem(`onboarding-${owner.uid}`);
          sessionStorage.clear();
          window.location.replace('/');
          return;
        }
        setStatus('Account deletion is in progress. Keep this page open, or return here to resume.');
        await new Promise(resolve => setTimeout(resolve, Math.min(30, result.retry_after || 1) * 1000));
      }
    } catch (err) {
      if (auth.currentUser?.uid === owner.uid) setError(userMessage(err, 'Deletion could not finish. Please retry to resume.'));
    } finally { if (mounted.current) setBusy(false); }
  }

  return <main className="container"><div className="card">
    <h1>Settings</h1>
    <p><Link href="/">Study and profile</Link> · <Link href="/privacy">Privacy notice</Link></p>
    <h2>Delete account</h2>
    <p>This permanently removes your profile, reflections, saved answers, history, progress and private journal data, then your sign-in account. It cannot be undone. Deletion may take several minutes while active requests finish.</p>
    <p>Public share links contain only the verse explanation, so they stay available after deletion. To remove one, send the link to the contact address in the <Link href="/privacy">privacy notice</Link>.</p>
    {user ? <form onSubmit={deleteAccount} className="form">
      <label>Current password<input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} disabled={busy} /></label>
      <label>Type DELETE to confirm<input value={confirmation} onChange={e => setConfirmation(e.target.value)} disabled={busy} required /></label>
      <button type="submit" disabled={busy || confirmation !== 'DELETE'}>{busy ? 'Deleting account...' : 'Delete account permanently'}</button>
    </form> : <p><Link href="/">Sign in to manage your account</Link></p>}
    <p role="status">{status}</p><ErrorNotice message={error} />
  </div></main>;
}
