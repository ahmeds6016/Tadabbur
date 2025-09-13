'use client';
import { useState, useEffect } from 'react';
import { initializeApp } from 'firebase/app';
import { 
  getAuth, 
  onAuthStateChanged, 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword,
  signOut
} from 'firebase/auth';
import { getFirestore, doc, getDoc, setDoc } from 'firebase/firestore';

// =================================================================
// PASTE YOUR FIREBASE CONFIG OBJECT HERE
// (The one you copied from the Firebase Console)
// =================================================================
const firebaseConfig = {
  apiKey: "AIzaSyBKPuVvuJC1bTUsZsZkiMHRoBRRqF6YqVU",
  authDomain: "tafsir-simplified-6b262.firebaseapp.com",
  projectId: "tafsir-simplified-6b262",
  storageBucket: "tafsir-simplified-6b262.firebasestorage.app",
  messagingSenderId: "69730898944",
  appId: "1:69730898944:web:ee2cbeee72be8d856474e5",
  measurementId: "G-7RZD1G66YH"
};
// =================================================================

// --- BACKEND URL ---
// PASTE YOUR DEPLOYED CLOUD RUN URL HERE
const BACKEND_URL = 'https://tafsir-backend-612616741510.us-central1.run.app';
// ---

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);


export default function HomePage() {
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // --- Login State ---
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoginView, setIsLoginView] = useState(true);

  // --- App State ---
  const [approach, setApproach] = useState('tafsir');
  const [query, setQuery] = useState('Surah An-Nas');
  const [response, setResponse] = useState(null);
  const [isQueryLoading, setIsQueryLoading] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      if (currentUser) {
        setUser(currentUser);
        // Fetch user profile from Firestore
        const userDocRef = doc(db, 'users', currentUser.uid);
        const userDocSnap = await getDoc(userDocRef);
        if (userDocSnap.exists()) {
          setUserProfile(userDocSnap.data());
        } else {
          setUserProfile({}); // No profile set yet
        }
      } else {
        setUser(null);
        setUserProfile(null);
      }
      setIsLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const handleAuthAction = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      if (isLoginView) {
        await signInWithEmailAndPassword(auth, email, password);
      } else {
        await createUserWithEmailAndPassword(auth, email, password);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSetLevel = async (level) => {
    if (!user) return;
    setIsLoading(true);
    setError('');
    try {
      const idToken = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/set_profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`
        },
        body: JSON.stringify({ level }),
      });
      if (!res.ok) throw new Error('Failed to set profile.');
      setUserProfile({ level });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!user) return;
    setIsQueryLoading(true);
    setError('');
    setResponse(null);
    try {
      const idToken = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/tafsir`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`
        },
        body: JSON.stringify({ approach, query }),
      });
      if (!res.ok) {
         const errorData = await res.json();
         throw new Error(errorData.error || 'Backend request failed.');
      }
      const data = await res.json();
      setResponse(data.candidates[0].content.parts[0].text);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsQueryLoading(false);
    }
  };

  // --- RENDER LOGIC ---

  if (isLoading) {
    return <div className="loading-spinner"></div>;
  }

  // 1. If user is NOT logged in, show the Login/Sign Up form
  if (!user) {
    return (
      <main>
        <div className="container">
          <h1>Welcome to Tafsir Simplified</h1>
          <h3>{isLoginView ? 'Sign In' : 'Create an Account'}</h3>
          <form onSubmit={handleAuthAction}>
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input type="email" id="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input type="password" id="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            <button type="submit">{isLoginView ? 'Sign In' : 'Sign Up'}</button>
          </form>
          <button onClick={() => setIsLoginView(!isLoginView)}>
            {isLoginView ? 'Need an account? Sign Up' : 'Have an account? Sign In'}
          </button>
          {error && <p className="error-message">{error}</p>}
        </div>
      </main>
    );
  }
  
  // 2. If user IS logged in but has NOT set their level, show the onboarding
  if (!userProfile?.level) {
    return (
      <main>
        <div className="container">
          <h2>Welcome, {user.email}!</h2>
          <p>Please select your knowledge level to personalize your experience.</p>
          <button onClick={() => handleSetLevel('beginner')}>I'm just starting my journey</button>
          <button onClick={() => handleSetLevel('intermediate')}>I have some background knowledge</button>
          <button onClick={() => handleSetLevel('advanced')}>I study the Qur'an regularly</button>
          {error && <p className="error-message">{error}</p>}
        </div>
      </main>
    );
  }

  // 3. If user IS logged in and has set their level, show the main app
  return (
    <main>
      <div className="container">
        <div className="header">
          <div>
            <h1>Tafsir Simplified</h1>
            <p className="user-info">Signed in as {user.email} ({userProfile.level})</p>
          </div>
          <button onClick={() => signOut(auth)} className="logout-btn">Sign Out</button>
        </div>
        
        <form onSubmit={handleQuery}>
          <div className="form-group">
            <label htmlFor="approach">1. Choose an Approach:</label>
            <select id="approach" value={approach} onChange={(e) => setApproach(e.target.value)}>
              <option value="tafsir">Tafsir-Based Study (by Surah/Verse)</option>
              <option value="thematic">Thematic Study (by Topic)</option>
              <option value="historical">Historical Context (Asbab al-Nuzul)</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="query">2. Enter Surah, Verse, or Topic:</label>
            <input id="query" type="text" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <button type="submit" disabled={isQueryLoading}>
            {isQueryLoading ? 'Loading...' : 'Get Tafsir'}
          </button>
        </form>

        {error && <p className="error-message">{error}</p>}
        
        {isQueryLoading && <div className="loading-spinner"></div>}

        {response && <RenderResponse response={response} />}
      </div>
    </main>
  );
}

// A helper component to render the structured response nicely
function RenderResponse({ response }) {
  try {
    const data = JSON.parse(response);
    return (
      <div className="response-container">
        {data.verses && (
          <div className="response-item">
            <h3>Verses</h3>
            {data.verses.map((v, i) => <p key={i}><strong>{v.surah} {v.verse_number}:</strong> {v.text_saheeh_international}</p>)}
          </div>
        )}
        {data.tafsir_explanations && (
           <div className="response-item">
             <h3>Tafsir Explanations</h3>
             {data.tafsir_explanations.map((t, i) => <div key={i}><h4>{t.source}</h4><p>{t.explanation}</p></div>)}
           </div>
        )}
        {data.lessons_practical_applications && (
           <div className="response-item">
             <h3>Lessons & Applications</h3>
             <ul>{data.lessons_practical_applications.map((l, i) => <li key={i}>{l}</li>)}</ul>
           </div>
        )}
         {data.summary_table && (
           <div className="response-item">
             <h3>Summary</h3>
             <p>{data.summary_table.concise_summary}</p>
           </div>
        )}
      </div>
    );
  } catch (e) {
    // If the response isn't valid JSON, show the raw text.
    return (
      <div className="response-container">
        <h3>Raw Response</h3>
        <pre>{response}</pre>
      </div>
    );
  }
}


