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

// --- PASTE YOUR FIREBASE CONFIG OBJECT HERE ---
const firebaseConfig = {
  apiKey: "AIzaSyBKPuVvuJC1bTUsZsZkiMHRoBRRqF6YqVU",
  authDomain: "tafsir-simplified-6b262.firebaseapp.com",
  projectId: "tafsir-simplified-6b262",
  storageBucket: "tafsir-simplified-6b262.appspot.com",
  messagingSenderId: "69730898944",
  appId: "1:69730898944:web:ee2cbeee72be8d856474e5",
  measurementId: "G-7RZD1G66YH"
};
// ---------------------------------------------

// --- PASTE YOUR DEPLOYED CLOUD RUN URL HERE ---
const BACKEND_URL = 'https://tafsir-backend-612616741510.us-central1.run.app';
// ---------------------------------------------

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export default function HomePage() {
  const [user, setUser] = useState(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSignUp, setIsSignUp] = useState(true);
  
  const [userLevel, setUserLevel] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetches the user's saved level from the backend
  const fetchUserLevel = async (currentUser) => {
    if (!currentUser) return;
    try {
      const token = await currentUser.getIdToken();
      const response = await fetch(`${BACKEND_URL}/get_profile`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('No profile found');
      const data = await response.json();
      if (data && data.level) {
        setUserLevel(data.level);
      }
    } catch (err) {
      console.log("User has no saved profile, will proceed to onboarding.");
    }
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        await fetchUserLevel(currentUser);
      } else {
        setUserLevel(null);
      }
      setIsLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const handleAuthAction = async (e) => {
    e.preventDefault();
    setError('');
    try {
      if (isSignUp) {
        await createUserWithEmailAndPassword(auth, email, password);
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSetLevel = async (level) => {
    setError('');
    if (!user) return;
    try {
      const token = await user.getIdToken();
      const response = await fetch(`${BACKEND_URL}/set_profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ level }),
      });
      if (!response.ok) throw new Error('Failed to set level');
      setUserLevel(level);
    } catch (err) {
      setError(err.message);
    }
  };
  
  if (isLoading) {
    return <div className="container"><div className="card"><h1>Loading...</h1></div></div>;
  }

  if (!user) {
    return (
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
  }

  if (user && !userLevel) {
    return (
      <div className="container">
        <div className="card">
          <h1>Welcome, {user.email}!</h1>
          <p>Please select your knowledge level to personalize your experience.</p>
          <div className="level-buttons">
            <button onClick={() => handleSetLevel('beginner')}>I'm just starting</button>
            <button onClick={() => handleSetLevel('intermediate')}>I have some knowledge</button>
            <button onClick={() => handleSetLevel('advanced')}>I study regularly</button>
          </div>
          {error && <p className="error">{error}</p>}
           <button onClick={() => signOut(auth)} className="logout-button">Sign Out</button>
        </div>
      </div>
    );
  }

  return <MainApp user={user} userLevel={userLevel} />;
}

// Main application component
function MainApp({ user, userLevel }) {
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
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ approach, query }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'An unknown error occurred while fetching Tafsir.');
      }
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
          <button type="submit" disabled={isTafsirLoading}>{isTafsirLoading ? 'Loading...' : 'Get Tafsir'}</button>
        </form>
        {error && <p className="error">{error}</p>}
        {isTafsirLoading && <div className="loading-spinner"></div>}
        {response && <ResultsDisplay data={response} />}
      </div>
    </div>
  );
}

// New component to display the results beautifully
function ResultsDisplay({ data }) {
  if (!data || !data.verses) return <div className="results-container"><p>No results to display.</p></div>;
  return (
    <div className="results-container">
      {data.verses && data.verses.length > 0 && (
        <div className="result-section">
          <h2>Relevant Verses</h2>
          {data.verses.map((verse, index) => (
            <div key={index} className="verse-card">
              <p className="verse-ref"><strong>{verse.surah}, Verse {verse.verse_number}</strong></p>
              <p><em>"{verse.text_saheeh_international}"</em></p>
            </div>
          ))}
        </div>
      )}

      {data.tafsir_explanations && data.tafsir_explanations.length > 0 && (
         <div className="result-section">
          <h2>Tafsir Explanations</h2>
          {data.tafsir_explanations.map((tafsir, index) => (
            <details key={index} className="tafsir-details">
              <summary><strong>{tafsir.source}</strong></summary>
              <p>{tafsir.explanation}</p>
            </details>
          ))}
        </div>
      )}

      {data.hadith_refs && data.hadith_refs.length > 0 && (
         <div className="result-section">
          <h2>Hadith References</h2>
          {data.hadith_refs.map((hadith, index) => (
            <div key={index} className="hadith-card">
                <p><strong>{hadith.reference} (Grade: {hadith.grade})</strong></p>
                <p>"{hadith.text_short}"</p>
            </div>
          ))}
        </div>
      )}

       {data.lessons_practical_applications && data.lessons_practical_applications.length > 0 && (
         <div className="result-section">
          <h2>Lessons & Practical Applications</h2>
          <ul>
            {data.lessons_practical_applications.map((lesson, index) => (
              <li key={index}>{lesson.point}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

