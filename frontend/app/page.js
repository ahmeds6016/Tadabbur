'use client';
import ReactMarkdown from 'react-markdown';
import { useState, useEffect, useCallback } from 'react';
import { initializeApp, getApps } from 'firebase/app';
import {
  getAuth,
  onAuthStateChanged,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut
} from 'firebase/auth';

// Firebase Configuration
const firebaseConfig = {
  apiKey: "AIzaSyBKPuVvuJC1bTUsZsZkiMHRoBRRqF6YqVU",
  authDomain: "tafsir-simplified-6b262.firebaseapp.com",
  projectId: "tafsir-simplified-6b262",
  storageBucket: "tafsir-simplified-6b262.appspot.com",
  messagingSenderId: "69730898944",
  appId: "1:69730898944:web:ee2cbeee72be8d856474e5",
  measurementId: "G-7RZD1G66YH"
};

const BACKEND_URL = 'https://tafsir-backend-612616741510.us-central1.run.app';

// Initialize Firebase
const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
const auth = getAuth(app);

// ============================================================================
// MAIN COMPONENT
// ============================================================================

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
      if (data?.level || data?.persona) {
        setUserProfile(data);
      }
    } catch (error) {
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
          <div className="loading-spinner"></div>
          <h2 style={{ textAlign: 'center', marginTop: '20px' }}>Loading Tafsir Simplified...</h2>
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

// ============================================================================
// AUTHENTICATION COMPONENT
// ============================================================================

function AuthComponent() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSignUp, setIsSignUp] = useState(true);

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

  return (
    <div className="container">
      <div className="card">
        <h1>Welcome to Tafsir Simplified</h1>
        <p style={{ fontSize: '1.1rem', color: '#666', marginBottom: '24px' }}>
          {isSignUp 
            ? 'Create an account to explore classical Islamic tafsir with AI-powered insights.' 
            : 'Sign in to continue your Quranic journey.'}
        </p>
        <form onSubmit={handleAuthAction} className="form">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
            style={{ marginBottom: '12px' }}
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            required
            style={{ marginBottom: '16px' }}
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

// ============================================================================
// ONBOARDING COMPONENT WITH ENHANCED PERSONA SYSTEM
// ============================================================================

function OnboardingComponent({ user, onProfileComplete }) {
  const [step, setStep] = useState(1);
  const [profile, setProfile] = useState({ level: '', focus: '', verbosity: '', persona: '' });
  const [error, setError] = useState('');
  const [personas, setPersonas] = useState([]);

  // Fetch available personas on mount
  useEffect(() => {
    const fetchPersonas = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/personas`);
        if (res.ok) {
          const data = await res.json();
          setPersonas(Object.entries(data.personas));
        }
      } catch (err) {
        console.log('Could not fetch personas');
      }
    };
    fetchPersonas();
  }, []);

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
    if (step === 5) {
      handleSetProfile();
    }
  }, [step, handleSetProfile]);

  return (
    <div className="container">
      <div className="card">
        <h1>Welcome, {user.email}!</h1>
        <p style={{ fontSize: '1.1rem', marginBottom: '32px' }}>
          Let&apos;s personalize your Tafsir experience in 4 simple steps.
        </p>

        {/* Step 1: Persona Selection */}
        {step === 1 && personas.length > 0 && (
          <div>
            <h2>Choose Your Learning Profile</h2>
            <p style={{ marginBottom: '20px', color: '#666' }}>
              Select the profile that best matches your current Islamic knowledge and learning goals.
            </p>
            <div className="level-buttons">
              {personas.map(([key, persona]) => (
                <button key={key} onClick={() => handleSelect('persona', key)}>
                  <div style={{ fontSize: '2rem', marginBottom: '8px' }}>
                    {key === 'new_revert' && '🌱'}
                    {key === 'revert' && '📗'}
                    {key === 'practicing_muslim' && '🕌'}
                    {key === 'scholar' && '📚'}
                    {key === 'student' && '🎓'}
                    {key === 'teacher' && '👨‍🏫'}
                    {key === 'seeker' && '🔍'}
                  </div>
                  {persona.name}
                  <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                    {persona.description}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Knowledge Level */}
        {step === 2 && (
          <div>
            <h2>What is your knowledge level?</h2>
            <div className="level-buttons">
              <button onClick={() => handleSelect('level', 'beginner')}>
                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📚</div>
                Beginner
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  New to tafsir
                </div>
              </button>
              <button onClick={() => handleSelect('level', 'intermediate')}>
                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🎓</div>
                Intermediate
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Some background
                </div>
              </button>
              <button onClick={() => handleSelect('level', 'advanced')}>
                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📖</div>
                Advanced
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Deep knowledge
                </div>
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Focus Area */}
        {step === 3 && (
          <div>
            <h2>What is your primary focus?</h2>
            <div className="level-buttons">
              <button onClick={() => handleSelect('focus', 'practical')}>
                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🤲</div>
                Practical Lessons
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Daily applications
                </div>
              </button>
              <button onClick={() => handleSelect('focus', 'linguistic')}>
                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>✍️</div>
                Linguistic Details
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Arabic insights
                </div>
              </button>
              <button onClick={() => handleSelect('focus', 'comparative')}>
                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📊</div>
                Comparative Analysis
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Multiple views
                </div>
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Verbosity */}
        {step === 4 && (
          <div>
            <h2>How detailed would you like the answers?</h2>
            <div className="level-buttons">
              <button onClick={() => handleSelect('verbosity', 'short')}>
                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>⚡</div>
                Short &amp; Concise
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Quick summaries
                </div>
              </button>
              <button onClick={() => handleSelect('verbosity', 'medium')}>
                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📝</div>
                Medium Detail
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Balanced depth
                </div>
              </button>
              <button onClick={() => handleSelect('verbosity', 'detailed')}>
                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📚</div>
                Very Detailed
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Comprehensive
                </div>
              </button>
            </div>
          </div>
        )}

        {error && <p className="error">{error}</p>}
        <button 
          onClick={() => signOut(auth)} 
          className="logout-button"
          style={{ marginTop: '32px' }}
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN APPLICATION COMPONENT
// ============================================================================

function MainApp({ user, userProfile }) {
  const [approach, setApproach] = useState('tafsir');
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');
  const [isTafsirLoading, setIsTafsirLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [rateLimitWarning, setRateLimitWarning] = useState('');

  // Fetch suggestions on mount
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

  // Display persona name if available
  const getProfileDisplay = () => {
    if (userProfile.persona) {
      return `Persona: ${userProfile.persona.replace('_', ' ')}`;
    }
    return `${userProfile.level} • ${userProfile.focus} • ${userProfile.verbosity}`;
  };

  return (
    <div className="container">
      <div className="card main-app">
        <div className="header">
          <h1>Tafsir Simplified</h1>
          <div className="user-info">
            <span>{user.email} • {getProfileDisplay()}</span>
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
            {showSuggestions ? '🔼 Hide' : '🔽 Show'} Suggestions
          </button>
          
          {showSuggestions && suggestions.length > 0 && (
            <div className="suggestions-grid">
              {suggestions.slice(0, 12).map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="suggestion-chip"
                >
                  <span>{suggestion}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <form onSubmit={handleGetTafsir} className="form tafsir-form">
          <select value={approach} onChange={(e) => setApproach(e.target.value)}>
            <option value="tafsir">📖 Tafsir-Based Study</option>
            <option value="thematic">🔍 Thematic Study</option>
            <option value="historical">📜 Historical Context</option>
          </select>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter Surah:Verse (e.g., 2:255) or topic (e.g., charity, prayer)..."
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
        
        {error && <p className="error">❌ {error}</p>}
        {isTafsirLoading && (
          <div className="loading-spinner"></div>
        )}
        
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

// ============================================================================
// RESULTS DISPLAY COMPONENT
// ============================================================================

function EnhancedResultsDisplay({ data }) {
  if (!data) return <div className="results-container"><p>No results to display.</p></div>;

  const {
    verses = [],
    tafsir_explanations = [],
    cross_references = [],
    lessons_practical_applications = [],
    summary = ''
  } = data;

  if (verses.length === 0 && tafsir_explanations.length === 0 && lessons_practical_applications.length === 0) {
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
                <strong>Surah {verse.surah}, Verse {verse.verse_number}</strong>
              </p>
              {verse.arabic_text && verse.arabic_text !== 'Not available' && (
                <p className="arabic-text" dir="rtl">{verse.arabic_text}</p>
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
<div className="explanation-content markdown-content">
  <ReactMarkdown
    components={{
      // Custom rendering for better styling
      h1: ({node, ...props}) => <h1 style={{fontSize: '1.5rem', marginTop: '20px', marginBottom: '12px', color: 'var(--primary-color)'}} {...props} />,
      h2: ({node, ...props}) => <h2 style={{fontSize: '1.3rem', marginTop: '16px', marginBottom: '10px', color: 'var(--primary-color)'}} {...props} />,
      h3: ({node, ...props}) => <h3 style={{fontSize: '1.1rem', marginTop: '12px', marginBottom: '8px'}} {...props} />,
      p: ({node, ...props}) => <p style={{marginBottom: '16px', lineHeight: '1.8'}} {...props} />,
      ul: ({node, ...props}) => <ul style={{marginLeft: '20px', marginBottom: '16px', listStyle: 'none'}} {...props} />,
      ol: ({node, ...props}) => <ol style={{marginLeft: '20px', marginBottom: '16px'}} {...props} />,
      li: ({node, ...props}) => <li style={{marginBottom: '8px', paddingLeft: '8px'}} {...props} />,
      strong: ({node, ...props}) => <strong style={{fontWeight: '600', color: 'var(--primary-color)'}} {...props} />,
      em: ({node, ...props}) => <em style={{fontStyle: 'italic', color: '#555'}} {...props} />,
      code: ({node, ...props}) => <code style={{background: 'var(--secondary-color)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.9em'}} {...props} />,
    }}
  >
    {tafsir.explanation}
  </ReactMarkdown>
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
