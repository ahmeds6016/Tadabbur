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
// PERSONA THEME CONFIGURATION
// ============================================================================

const getPersonaTheme = (persona) => {
  const themes = {
    new_revert: {
      gradient: 'linear-gradient(135deg, #10B981 0%, #34D399 100%)',
      icon: '🌱',
      color: '#10B981'
    },
    revert: {
      gradient: 'linear-gradient(135deg, #059669 0%, #10B981 100%)',
      icon: '📗',
      color: '#059669'
    },
    seeker: {
      gradient: 'linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%)',
      icon: '🔍',
      color: '#8B5CF6'
    },
    practicing_muslim: {
      gradient: 'linear-gradient(135deg, #0D9488 0%, #14B8A6 100%)',
      icon: '🕌',
      color: '#0D9488'
    },
    teacher: {
      gradient: 'linear-gradient(135deg, #D97706 0%, #F59E0B 100%)',
      icon: '👨‍🏫',
      color: '#D97706'
    },
    scholar: {
      gradient: 'linear-gradient(135deg, #1E3A5F 0%, #3B5A7F 100%)',
      icon: '📚',
      color: '#1E3A5F'
    },
    student: {
      gradient: 'linear-gradient(135deg, #3B82F6 0%, #60A5FA 100%)',
      icon: '🎓',
      color: '#3B82F6'
    }
  };
  
  return themes[persona] || themes.practicing_muslim;
};

const getPersonaIcon = (persona) => {
  const theme = getPersonaTheme(persona);
  return theme.icon;
};

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
        <h1 style={{ textAlign: 'center', marginBottom: '16px' }}>Welcome to Tafsir Simplified</h1>
        <p style={{ fontSize: '1.1rem', color: '#666', marginBottom: '32px', textAlign: 'center' }}>
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
            style={{ marginBottom: '12px', width: '100%' }}
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            required
            style={{ marginBottom: '16px', width: '100%' }}
          />
          <button type="submit" style={{ width: '100%' }}>
            {isSignUp ? 'Sign Up' : 'Sign In'}
          </button>
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
        console.log('Could not fetch personas, using defaults');
        // Fallback personas
        setPersonas([
          ['new_revert', { name: 'New Revert', description: 'warm, encouraging | Format: bullets_emojis' }],
          ['revert', { name: 'Revert Muslim', description: 'supportive | Format: bullets_emojis' }],
          ['practicing_muslim', { name: 'Practicing Muslim', description: 'balanced | Format: balanced' }],
          ['scholar', { name: 'Scholar', description: 'academic | Format: academic_prose' }],
          ['student', { name: 'Islamic Studies Student', description: 'educational | Format: academic_prose' }],
          ['teacher', { name: 'Teacher/Imam', description: 'pedagogical | Format: balanced' }],
          ['seeker', { name: 'Spiritual Seeker', description: 'warm, reflective | Format: bullets_emojis' }]
        ]);
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
        <h1 style={{ textAlign: 'center', marginBottom: '12px' }}>Welcome, {user.email}!</h1>
        <p style={{ fontSize: '1.1rem', marginBottom: '32px', textAlign: 'center', color: '#666' }}>
          Let&apos;s personalize your Tafsir experience in 4 simple steps.
        </p>

        {/* Step 1: Persona Selection */}
        {step === 1 && personas.length > 0 && (
          <div>
            <h2 style={{ textAlign: 'center', color: 'var(--primary-teal)', marginBottom: '24px' }}>
              Choose Your Learning Profile
            </h2>
            <p style={{ marginBottom: '24px', color: '#666', textAlign: 'center' }}>
              Select the profile that best matches your current Islamic knowledge and learning goals.
            </p>
            <div className="level-buttons">
              {personas.map(([key, persona]) => (
                <button key={key} onClick={() => handleSelect('persona', key)}>
                  <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>
                    {getPersonaIcon(key)}
                  </div>
                  <div style={{ fontWeight: '700', fontSize: '1.1rem', marginBottom: '4px' }}>
                    {persona.name}
                  </div>
                  <div style={{ fontSize: '0.85rem', opacity: 0.7, lineHeight: '1.4' }}>
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
            <h2 style={{ textAlign: 'center', color: 'var(--primary-teal)', marginBottom: '24px' }}>
              What is your knowledge level?
            </h2>
            <div className="level-buttons">
              <button onClick={() => handleSelect('level', 'beginner')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>📚</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Beginner</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  New to tafsir
                </div>
              </button>
              <button onClick={() => handleSelect('level', 'intermediate')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>🎓</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Intermediate</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Some background
                </div>
              </button>
              <button onClick={() => handleSelect('level', 'advanced')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>📖</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Advanced</div>
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
            <h2 style={{ textAlign: 'center', color: 'var(--primary-teal)', marginBottom: '24px' }}>
              What is your primary focus?
            </h2>
            <div className="level-buttons">
              <button onClick={() => handleSelect('focus', 'practical')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>🤲</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Practical Lessons</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Daily applications
                </div>
              </button>
              <button onClick={() => handleSelect('focus', 'linguistic')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>✍️</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Linguistic Details</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Arabic insights
                </div>
              </button>
              <button onClick={() => handleSelect('focus', 'comparative')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>📊</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Comparative Analysis</div>
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
            <h2 style={{ textAlign: 'center', color: 'var(--primary-teal)', marginBottom: '24px' }}>
              How detailed would you like the answers?
            </h2>
            <div className="level-buttons">
              <button onClick={() => handleSelect('verbosity', 'short')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>⚡</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Short &amp; Concise</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Quick summaries
                </div>
              </button>
              <button onClick={() => handleSelect('verbosity', 'medium')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>📝</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Medium Detail</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Balanced depth
                </div>
              </button>
              <button onClick={() => handleSelect('verbosity', 'detailed')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>📚</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Very Detailed</div>
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
// MAIN APPLICATION COMPONENT - ENHANCED
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

  // Apply persona theme
  useEffect(() => {
    const persona = userProfile?.persona || 'practicing_muslim';
    const theme = getPersonaTheme(persona);
    document.documentElement.style.setProperty('--user-gradient', theme.gradient);
    document.documentElement.style.setProperty('--user-color', theme.color);
  }, [userProfile]);

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
    
    // NEW: Add submitting animation class
    const formElement = e.target;
    formElement.classList.add('submitting');
    setTimeout(() => formElement.classList.remove('submitting'), 300);
    
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
      const personaName = userProfile.persona.split('_').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
      ).join(' ');
      return personaName;
    }
    return `${userProfile.level} • ${userProfile.focus}`;
  };

  const personaIcon = getPersonaIcon(userProfile?.persona || 'practicing_muslim');

  return (
    <div className="container">
      <div className="card main-app">
        <div className="header">
          <h1>Tafsir Simplified</h1>
          <div className="user-info" data-persona-icon={personaIcon}>
            <span>{user.email}</span>
            <span className="persona-badge">{getProfileDisplay()}</span>
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
            {showSuggestions ? '🔼 Hide Suggestions' : '🔽 Show Query Suggestions'}
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

        {/* FIXED: Search Form - Removed conflicting Tailwind classes */}
        <form onSubmit={handleGetTafsir} className="tafsir-form">
          <select value={approach} onChange={(e) => setApproach(e.target.value)}>
            <option value="tafsir">📖 Tafsir-Based Study</option>
            <option value="thematic">🔍 Thematic Study</option>
            <option value="historical">📜 Historical Context</option>
          </select>
          
          {/* NEW: Wrapper for input with optional character counter */}
          <div style={{ position: 'relative', flex: '1 1 300px', minWidth: '250px' }}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter Surah:Verse (e.g., 2:255) or topic (e.g., charity, prayer)..."
              maxLength={200}
              style={{ width: '100%' }}
            />
            {query.length > 0 && (
              <span style={{
                position: 'absolute',
                right: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                fontSize: '0.75rem',
                color: query.length > 180 ? 'var(--warning-color)' : 'rgba(0,0,0,0.3)',
                fontWeight: 600,
                pointerEvents: 'none'
              }}>
                {query.length}/200
              </span>
            )}
          </div>
          
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
        <p style={{ textAlign: 'center', fontSize: '1.1rem', color: '#666' }}>
          No relevant information found in the source text for your query.
        </p>
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
                <ReactMarkdown>
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
