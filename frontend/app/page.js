'use client';
import { useState, useEffect } from 'react';
import { initializeApp } from 'firebase/app';
import { 
  getAuth, 
  onAuthStateChanged, 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword, 
  signOut 
} from 'firebase/auth';

// --- Firebase Config ---
const firebaseConfig = {
  apiKey: "AIzaSyBKPuVvuJC1bTUsZsZkiMHRoBRRqF6YqVU",
  authDomain: "tafsir-simplified-6b262.firebaseapp.com",
  projectId: "tafsir-simplified-6b262",
  storageBucket: "tafsir-simplified-6b262.appspot.com",
  messagingSenderId: "69730898944",
  appId: "1:69730898944:web:ee2cbeee72be8d856474e5",
  measurementId: "G-7RZD1G66YH"
};

// --- Backend URL ---
const BACKEND_URL = 'https://tafsir-backend-612616741510.us-central1.run.app';

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export default function HomePage() {
  const [user, setUser] = useState(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSignUp, setIsSignUp] = useState(true);
  const [userLevel, setUserLevel] = useState(null);
  const [verbosity, setVerbosity] = useState('balanced');
  const [focus, setFocus] = useState('spiritual');
  const [isLoading, setIsLoading] = useState(true);

  const fetchUserProfile = async (currentUser) => {
    if (!currentUser) return;
    try {
      const token = await currentUser.getIdToken();
      const response = await fetch(`${BACKEND_URL}/get_profile`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('No profile found');
      const data = await response.json();
      if (data?.level) setUserLevel(data.level);
      if (data?.verbosity) setVerbosity(data.verbosity);
      if (data?.focus) setFocus(data.focus);
    } catch {
      console.log("No saved profile, proceeding to onboarding.");
    }
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) await fetchUserProfile(currentUser);
      else {
        setUserLevel(null);
        setVerbosity('balanced');
        setFocus('spiritual');
      }
      setIsLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const handleAuthAction = async (e) => {
    e.preventDefault();
    setError('');
    try {
      if (isSignUp) await createUserWithEmailAndPassword(auth, email, password);
      else await signInWithEmailAndPassword(auth, email, password);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSetProfile = async (level, verbosity, focus) => {
    setError('');
    if (!user) return;
    try {
      const token = await user.getIdToken();
      const response = await fetch(`${BACKEND_URL}/set_profile`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ level, verbosity, focus }),
      });
      if (!response.ok) throw new Error('Failed to set profile');
      setUserLevel(level);
      setVerbosity(verbosity);
      setFocus(focus);
    } catch (err) {
      setError(err.message);
    }
  };

  if (isLoading) return <div className="container"><div className="card"><h1>Loading...</h1></div></div>;

  if (!user) return (
    <div className="container">
      <div className="card">
        <h1>Welcome to Tafsir Simplified</h1>
        <p>{isSignUp ? 'Create an account to get started.' : 'Sign in to your account.'}</p>
        <form onSubmit={handleAuthAction} className="form">
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" required />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" required />
          <button type="submit">{isSignUp ? 'Sign Up' : 'Sign In'}</button>
        </form>
        {error && <p className="error">{error}</p>}
        <button onClick={() => setIsSignUp(!isSignUp)} className="toggle-auth">
          {isSignUp ? 'Already have an account? Sign In' : 'Need an account? Sign Up'}
        </button>
      </div>
    </div>
  );

if (user && !userLevel) return (
  <div className="container">
    <div className="card onboarding-card">
      <h1>Welcome, {user.email}!</h1>
      <p>Select your knowledge level and style to personalize your Tafsir experience:</p>
      <div className="level-grid">
        <div className="level-card" onClick={() => handleSetProfile('casual', 'brief', 'spiritual')}>
          <h3>Casual Reader</h3>
          <p>Level: Casual</p>
          <p>Verbosity: Brief</p>
          <p>Focus: Spiritual</p>
        </div>
        <div className="level-card" onClick={() => handleSetProfile('beginner', 'balanced', 'spiritual')}>
          <h3>Beginner</h3>
          <p>Level: Beginner</p>
          <p>Verbosity: Balanced</p>
          <p>Focus: Spiritual</p>
        </div>
        <div className="level-card" onClick={() => handleSetProfile('intermediate', 'balanced', 'practical')}>
          <h3>Intermediate</h3>
          <p>Level: Intermediate</p>
          <p>Verbosity: Balanced</p>
          <p>Focus: Practical</p>
        </div>
        <div className="level-card" onClick={() => handleSetProfile('advanced', 'detailed', 'linguistic')}>
          <h3>Advanced</h3>
          <p>Level: Advanced</p>
          <p>Verbosity: Detailed</p>
          <p>Focus: Linguistic</p>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <button onClick={() => signOut(auth)} className="logout-button">Sign Out</button>
    </div>
  </div>
);


  return <MainApp user={user} userLevel={userLevel} verbosity={verbosity} focus={focus} />;
}

function MainApp({ user, userLevel, verbosity, focus }) {
  const [approach, setApproach] = useState('tafsir');
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');
  const [isTafsirLoading, setIsTafsirLoading] = useState(false);

  const handleGetTafsir = async (e) => {
    e.preventDefault();
    if (!query) return;
    setIsTafsirLoading(true);
    setResponse(null);
    setError('');
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/tafsir`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ approach, query, verbosity, focus }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Unknown error fetching Tafsir.');
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsTafsirLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="card main-app">
        <div className="header">
          <h1>Tafsir Simplified</h1>
          <div className="user-info">
            <span>{user.email} ({userLevel})</span>
            <span> | Verbosity: {verbosity}, Focus: {focus}</span>
            <button onClick={() => signOut(auth)} className="logout-button">Sign Out</button>
          </div>
        </div>
        <form onSubmit={handleGetTafsir} className="form tafsir-form">
          <select value={approach} onChange={(e) => setApproach(e.target.value)}>
            <option value="tafsir">Tafsir-Based Study</option>
            <option value="thematic">Thematic Study</option>
            <option value="historical">Historical Context</option>
          </select>
          <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Enter Surah, Verse, or Topic..." />
          <button type="submit" disabled={isTafsirLoading}>
            {isTafsirLoading ? 'Loading...' : 'Get Tafsir'}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
        {isTafsirLoading && <div className="loading-spinner"></div>}
        {response && <ResultsDisplay data={response} />}
      </div>
    </div>
  );
}

function ResultsDisplay({ data }) {
  if (!data) return <div className="results-container"><p>No results to display.</p></div>;

  const {
    verses = [],
    tafsir_explanations = [],
    hadith_refs = [],
    lessons_practical_applications = []
  } = data;

  if (
    verses.length === 0 &&
    tafsir_explanations.length === 0 &&
    hadith_refs.length === 0 &&
    lessons_practical_applications.length === 0
  ) return <div className="results-container"><p>No results to display.</p></div>;

  return (
    <div className="results-container">
      {verses.length > 0 && (
        <div className="result-section">
          <h2>Relevant Verses</h2>
          {verses.map((verse, index) => (
            <div key={index} className="verse-card">
              <p className="verse-ref"><strong>{verse.surah}, Verse {verse.verse_number}</strong></p>
              <p><em>&quot;{verse.text_saheeh_international}&quot;</em></p>
            </div>
          ))}
        </div>
      )}

      {tafsir_explanations.length > 0 && (
        <div className="result-section">
          <h2>Tafsir Explanations</h2>
          {tafsir_explanations.map((tafsir, index) => (
            <details key={index} className="tafsir-details">
              <summary><strong>{tafsir.source}</strong></summary>
              <p>{tafsir.explanation}</p>
            </details>
          ))}
        </div>
      )}

      {hadith_refs.length > 0 && (
        <div className="result-section">
          <h2>Hadith References</h2>
          {hadith_refs.map((hadith, index) => (
            <div key={index} className="hadith-card">
              <p><strong>{hadith.reference} (Grade: {hadith.grade})</strong></p>
              <p>&quot;{hadith.text_short}&quot;</p>
            </div>
          ))}
        </div>
      )}

      {lessons_practical_applications.length > 0 && (
        <div className="result-section">
          <h2>Lessons & Practical Applications</h2>
          <ul>
            {lessons_practical_applications.map((lesson, index) => (
              <li key={index}>{lesson.point}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
