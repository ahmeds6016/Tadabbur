'use client';
import { useState, useEffect, useCallback } from 'react';
import { initializeApp, getApps } from 'firebase/app';
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

// Avoid duplicate initialization
const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
const auth = getAuth(app);

// --- Main Component ---
export default function HomePage() {
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUserProfile = async (currentUser) => {
    if (!currentUser) return;
    try {
      const token = await currentUser.getIdToken();
      const response = await fetch(`${BACKEND_URL}/get_profile`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('No profile found');
      const data = await response.json();
      if (data?.level && data?.focus && data?.verbosity) {
        setUserProfile(data);
      }
    } catch {
      console.log('No saved profile, proceeding to onboarding.');
    }
  };

  useEffect(() => {
    let isMounted = true;
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      if (!isMounted) return;
      setUser(currentUser);
      if (currentUser) {
        await fetchUserProfile(currentUser);
      } else {
        setUserProfile(null);
      }
      setIsLoading(false);
    });
    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, []);

  if (isLoading) {
    return (
      <div className="container">
        <div className="card">
          <h1>Loading...</h1>
        </div>
      </div>
    );
  }
  if (!user) {
    return <AuthComponent />;
  }
  if (user && !userProfile) {
    return <OnboardingComponent user={user} onProfileComplete={setUserProfile} />;
  }
  return <MainApp user={user} userProfile={userProfile} />;
}

// --- Child Components ---

function AuthComponent() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSignUp, setIsSignUp] = useState(true);

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

  return (
    <div className="container">
      <div className="card">
        <h1>Welcome to Tafsir Simplified</h1>
        <p>
          {isSignUp ? 'Create an account to get started.' : 'Sign in to your account.'}
        </p>
        <form onSubmit={handleAuthAction} className="form">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            required
          />
          <button type="submit">{isSignUp ? 'Sign Up' : 'Sign In'}</button>
        </form>
        {error && <p className="error">{error}</p>}
        <button onClick={() => setIsSignUp(!isSignUp)} className="toggle-auth">
          {isSignUp
            ? 'Already have an account? Sign In'
            : 'Need an account? Sign Up'}
        </button>
      </div>
    </div>
  );
}

function OnboardingComponent({ user, onProfileComplete }) {
  const [step, setStep] = useState(1);
  const [profile, setProfile] = useState({ level: '', focus: '', verbosity: '' });
  const [error, setError] = useState('');

  const handleSetProfile = useCallback(async () => {
    setError('');
    try {
      const token = await user.getIdToken();
      const response = await fetch(`${BACKEND_URL}/set_profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(profile)
      });
      if (!response.ok) throw new Error('Failed to save profile.');
      onProfileComplete(profile);
    } catch (err) {
      setError(err.message);
    }
  }, [user, profile, onProfileComplete]);

  const handleSelect = (key, value) => {
    setProfile((prev) => ({ ...prev, [key]: value }));
    setStep((prev) => prev + 1);
  };

  useEffect(() => {
    if (step === 4) {
      handleSetProfile();
    }
  }, [step, handleSetProfile]);

  return (
    <div className="container">
      <div className="card">
        <h1>Welcome, {user.email}!</h1>
        <p>Let&apos;s personalize your experience.</p>

        {step === 1 && (
          <div>
            <h2>First, what is your knowledge level?</h2>
            <div className="level-buttons">
              <button onClick={() => handleSelect('level', 'beginner')}>Beginner</button>
              <button onClick={() => handleSelect('level', 'intermediate')}>
                Intermediate
              </button>
              <button onClick={() => handleSelect('level', 'advanced')}>Advanced</button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <h2>What is your primary focus?</h2>
            <div className="level-buttons">
              <button onClick={() => handleSelect('focus', 'practical')}>
                Practical Lessons
              </button>
              <button onClick={() => handleSelect('focus', 'linguistic')}>
                Linguistic Details
              </button>
              <button onClick={() => handleSelect('focus', 'comparative')}>
                Comparative Analysis
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <h2>How detailed would you like the answers?</h2>
            <div className="level-buttons">
              <button onClick={() => handleSelect('verbosity', 'short')}>
                Short &amp; Concise
              </button>
              <button onClick={() => handleSelect('verbosity', 'medium')}>
                Medium Detail
              </button>
              <button onClick={() => handleSelect('verbosity', 'detailed')}>
                Very Detailed
              </button>
            </div>
          </div>
        )}

        {error && <p className="error">{error}</p>}
        <button onClick={() => signOut(auth)} className="logout-button">
          Sign Out
        </button>
      </div>
    </div>
  );
}

function MainApp({ user, userProfile }) {
  const [approach, setApproach] = useState('tafsir');
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');
  const [isTafsirLoading, setIsTafsirLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Enhanced state for new features
  const [rateLimitWarning, setRateLimitWarning] = useState('');
  const [exportFormat, setExportFormat] = useState('markdown');

  // Fetch suggestions on component mount
  useEffect(() => {
    const fetchSuggestions = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/suggestions`);
        if (res.ok) {
          const data = await res.json();
          setSuggestions(data.suggestions || []);
        }
      } catch (err) {
        console.log('Could not fetch suggestions');
      }
    };
    fetchSuggestions();
  }, []);

  const handleGetTafsir = async (e) => {
    e.preventDefault();
    if (!query) return;
    setIsTafsirLoading(true);
    setResponse(null);
    setError('');
    setRateLimitWarning('');
    
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/tafsir`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ approach, query })
      });
      
      const data = await res.json();
      
      if (res.status === 429) {
        setRateLimitWarning('You have reached your query limit. Please try again later.');
        return;
      }
      
      if (!res.ok) throw new Error(data.error || 'Unknown error fetching Tafsir.');
      
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsTafsirLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion);
    setShowSuggestions(false);
  };

  const handleExport = async (format) => {
    if (!response) return;
    
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/export/${format}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ response_data: response })
      });
      
      if (res.ok) {
        const data = await res.json();
        
        // Create download
        const blob = new Blob([data.content], { 
          type: format === 'json' ? 'application/json' : 'text/markdown' 
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  return (
    <div className="container">
      <div className="card main-app">
        <div className="header">
          <h1>Tafsir Simplified</h1>
          <div className="user-info">
            <span>
              {user.email} ({userProfile.level}, {userProfile.focus},{' '}
              {userProfile.verbosity})
            </span>
            <button onClick={() => signOut(auth)} className="logout-button">
              Sign Out
            </button>
          </div>
        </div>
        
        {/* Query Suggestions */}
        <div className="suggestions-section">
          <button 
            onClick={() => setShowSuggestions(!showSuggestions)}
            className="suggestions-toggle"
          >
            {showSuggestions ? 'Hide' : 'Show'} Suggestions
          </button>
          
          {showSuggestions && (
            <div className="suggestions-grid">
              {suggestions.slice(0, 12).map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="suggestion-chip"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </div>

        <form onSubmit={handleGetTafsir} className="form tafsir-form">
          <select value={approach} onChange={(e) => setApproach(e.target.value)}>
            <option value="tafsir">Tafsir-Based Study</option>
            <option value="thematic">Thematic Study</option>
            <option value="historical">Historical Context</option>
          </select>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter Surah, Verse, or Topic (e.g., 2:255, charity, prayer)..."
          />
          <button type="submit" disabled={isTafsirLoading}>
            {isTafsirLoading ? 'Loading...' : 'Get Tafsir'}
          </button>
        </form>
        
        {rateLimitWarning && (
          <div className="rate-limit-warning">
            ⚠️ {rateLimitWarning}
          </div>
        )}
        
        {error && <p className="error">{error}</p>}
        {isTafsirLoading && <div className="loading-spinner"></div>}
        
        {response && (
          <>
            <EnhancedResultsDisplay data={response} />
            <div className="export-section">
              <h3>Export Response</h3>
              <div className="export-controls">
                <button onClick={() => handleExport('markdown')} className="export-btn">
                  📄 Export as Markdown
                </button>
                <button onClick={() => handleExport('json')} className="export-btn">
                  📋 Export as JSON
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function EnhancedResultsDisplay({ data }) {
  if (!data) {
    return (
      <div className="results-container">
        <p>No results to display.</p>
      </div>
    );
  }

  const {
    verses = [],
    tafsir_explanations = [],
    cross_references = [],
    lessons_practical_applications = [],
    summary = ''
  } = data;

  if (
    verses.length === 0 &&
    tafsir_explanations.length === 0 &&
    lessons_practical_applications.length === 0
  ) {
    return (
      <div className="results-container">
        <p>No relevant information found in the source text for your query.</p>
      </div>
    );
  }

  return (
    <div className="results-container">
      {verses.length > 0 && (
        <div className="result-section">
          <h2>Relevant Verses</h2>
          {verses.map((verse, index) => (
            <div key={index} className="verse-card enhanced">
              <p className="verse-ref">
                <strong>
                  {verse.surah}, Verse {verse.verse_number}
                </strong>
              </p>
              {verse.arabic_text && verse.arabic_text !== 'Not available' && (
                <p className="arabic-text" dir="rtl">
                  {verse.arabic_text}
                </p>
              )}
              <p className="translation">
                <em>&quot;{verse.text_saheeh_international}&quot;</em>
              </p>
            </div>
          ))}
        </div>
      )}

      {tafsir_explanations.length > 0 && (
        <div className="result-section">
          <h2>Tafsir Explanations</h2>
          {tafsir_explanations.map((tafsir, index) => (
            <details key={index} className="tafsir-details enhanced" open>
              <summary>
                <strong>{tafsir.source}</strong>
                {tafsir.explanation.includes('Limited relevant content') && (
                  <span className="limited-content-badge">Limited Content</span>
                )}
              </summary>
              <div className="explanation-content">
                <p>{tafsir.explanation}</p>
              </div>
            </details>
          ))}
        </div>
      )}

      {cross_references.length > 0 && (
        <div className="result-section">
          <h2>Related Verses</h2>
          <div className="cross-references">
            {cross_references.map((ref, index) => (
              <div key={index} className="cross-ref-item">
                <strong>{ref.verse}</strong>: {ref.relevance}
              </div>
            ))}
          </div>
        </div>
      )}

      {lessons_practical_applications.length > 0 && (
        <div className="result-section">
          <h2>Lessons &amp; Practical Applications</h2>
          <ul className="lessons-list">
            {lessons_practical_applications.map((lesson, index) => (
              <li key={index} className="lesson-item">{lesson.point}</li>
            ))}
          </ul>
        </div>
      )}

      {summary && (
        <div className="result-section">
          <h2>Summary</h2>
          <div className="summary-content">
            <p>{summary}</p>
          </div>
        </div>
      )}
    </div>
  );
}
