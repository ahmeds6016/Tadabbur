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
import AnnotationPanel from './components/AnnotationPanel';
import AnnotationDisplay from './components/AnnotationDisplay';

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
// FIXED ONBOARDING COMPONENT - Matches New Backend Profile System
// Replace your existing OnboardingComponent in page.js
// ============================================================================

function OnboardingComponent({ user, onProfileComplete }) {
  const [step, setStep] = useState(1);
  const [profile, setProfile] = useState({ 
    persona: '', 
    knowledge_level: '', 
    learning_goal: '',
    // Keep old fields for backwards compatibility
    level: '', 
    focus: '', 
    verbosity: '' 
  });
  const [error, setError] = useState('');
  const [personas, setPersonas] = useState([]);
  const [isDeterministicPersona, setIsDeterministicPersona] = useState(false);

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
        setPersonas([
          ['new_revert', { 
            name: 'New Revert', 
            description: 'warm, encouraging | Format: bullets_emojis',
            requires_knowledge_level_input: false 
          }],
          ['revert', { 
            name: 'Revert Muslim', 
            description: 'supportive | Format: bullets_emojis',
            requires_knowledge_level_input: true 
          }],
          ['practicing_muslim', { 
            name: 'Practicing Muslim', 
            description: 'balanced | Format: balanced',
            requires_knowledge_level_input: true 
          }],
          ['scholar', { 
            name: 'Scholar', 
            description: 'academic | Format: academic_prose',
            requires_knowledge_level_input: false 
          }],
          ['student', { 
            name: 'Islamic Studies Student', 
            description: 'educational | Format: academic_prose',
            requires_knowledge_level_input: false 
          }],
          ['teacher', { 
            name: 'Teacher/Imam', 
            description: 'pedagogical | Format: balanced',
            requires_knowledge_level_input: true 
          }],
          ['seeker', { 
            name: 'Spiritual Seeker', 
            description: 'warm, reflective | Format: bullets_emojis',
            requires_knowledge_level_input: true 
          }]
        ]);
      }
    };
    fetchPersonas();
  }, []);

  const handleSetProfile = useCallback(async () => {
    setError('');
    try {
      const token = await user.getIdToken();
      
      // Build the profile payload for the NEW backend API
      const payload = {
        persona: profile.persona,
        learning_goal: profile.learning_goal
      };
      
      // Only send knowledge_level for variable personas
      if (!isDeterministicPersona) {
        payload.knowledge_level = profile.knowledge_level;
      }
      
      console.log('Sending profile:', payload);
      
      const response = await fetch(`${BACKEND_URL}/set_profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to save profile.');
      }
      
      const result = await response.json();
      console.log('Profile saved:', result);
      onProfileComplete(result.profile);
    } catch (err) {
      console.error('Profile error:', err);
      setError(err.message);
    }
  }, [user, profile, onProfileComplete, isDeterministicPersona]);

  const handlePersonaSelect = (personaKey, personaData) => {
    setProfile((prev) => ({ ...prev, persona: personaKey }));
    
    // Check if this is a deterministic persona (auto-sets knowledge_level)
    const deterministic = ['scholar', 'student', 'new_revert'];
    setIsDeterministicPersona(deterministic.includes(personaKey));
    
    // Auto-advance to next step
    if (deterministic.includes(personaKey)) {
      // Skip knowledge_level step for deterministic personas
      setStep(3); // Go straight to learning_goal
    } else {
      setStep(2); // Go to knowledge_level selection
    }
  };

  const handleKnowledgeLevelSelect = (level) => {
    setProfile((prev) => ({ ...prev, knowledge_level: level }));
    setStep(3); // Move to learning_goal
  };

  const handleLearningGoalSelect = (goal) => {
    setProfile((prev) => ({ ...prev, learning_goal: goal }));
    setStep(4); // Trigger profile save
  };

  useEffect(() => {
    if (step === 4) {
      handleSetProfile();
    }
  }, [step, handleSetProfile]);

  return (
    <div className="container">
      <div className="card">
        <h1 style={{ textAlign: 'center', marginBottom: '12px' }}>Welcome, {user.email}!</h1>
        <p style={{ fontSize: '1.1rem', marginBottom: '32px', textAlign: 'center', color: '#666' }}>
          Let&apos;s personalize your Tafsir experience in 3 simple steps.
        </p>

        {/* Step 1: Persona Selection */}
        {step === 1 && personas.length > 0 && (
          <div>
            <h2 style={{ textAlign: 'center', color: 'var(--primary-teal)', marginBottom: '24px' }}>
              1. Choose Your Learning Profile
            </h2>
            <p style={{ marginBottom: '24px', color: '#666', textAlign: 'center' }}>
              Select the profile that best matches your Islamic knowledge journey.
            </p>
            <div className="level-buttons">
              {personas.map(([key, persona]) => (
                <button key={key} onClick={() => handlePersonaSelect(key, persona)}>
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

        {/* Step 2: Knowledge Level (Only for Variable Personas) */}
        {step === 2 && !isDeterministicPersona && (
          <div>
            <h2 style={{ textAlign: 'center', color: 'var(--primary-teal)', marginBottom: '24px' }}>
              2. What is your knowledge level?
            </h2>
            <p style={{ marginBottom: '24px', color: '#666', textAlign: 'center' }}>
              This helps us tailor the depth and complexity of explanations.
            </p>
            <div className="level-buttons">
              <button onClick={() => handleKnowledgeLevelSelect('beginner')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>📚</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Beginner</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  New to Islamic studies
                </div>
              </button>
              <button onClick={() => handleKnowledgeLevelSelect('intermediate')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>🎓</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Intermediate</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Some Islamic background
                </div>
              </button>
              <button onClick={() => handleKnowledgeLevelSelect('advanced')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>📖</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Advanced</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Strong Islamic knowledge
                </div>
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Learning Goal */}
        {step === 3 && (
          <div>
            <h2 style={{ textAlign: 'center', color: 'var(--primary-teal)', marginBottom: '24px' }}>
              {isDeterministicPersona ? '2' : '3'}. What is your learning goal?
            </h2>
            <p style={{ marginBottom: '24px', color: '#666', textAlign: 'center' }}>
              Choose what matters most to you when studying Quran.
            </p>
            <div className="level-buttons">
              <button onClick={() => handleLearningGoalSelect('application')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>🤲</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Practical Application</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Focus on how to apply teachings in daily life
                </div>
              </button>
              <button onClick={() => handleLearningGoalSelect('understanding')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>📖</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Deep Understanding</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Focus on scholarly depth and theological context
                </div>
              </button>
              <button onClick={() => handleLearningGoalSelect('balanced')}>
                <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>⚖️</div>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Balanced Approach</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Mix of practical insights and scholarly depth
                </div>
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Saving (shown automatically) */}
        {step === 4 && !error && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div className="loading-spinner"></div>
            <p style={{ marginTop: '20px', color: '#666' }}>Saving your profile...</p>
          </div>
        )}

        {error && (
          <div className="error" style={{ marginTop: '24px' }}>
            <p><strong>Error:</strong> {error}</p>
            <button 
              onClick={() => {
                setError('');
                setStep(1);
                setProfile({ persona: '', knowledge_level: '', learning_goal: '', level: '', focus: '', verbosity: '' });
              }}
              style={{ marginTop: '16px', width: '100%' }}
            >
              Start Over
            </button>
          </div>
        )}
        
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

      // Save to query history
      await saveQueryToHistory(query, approach, userProfile?.persona || '', true);
    } catch (err) {
      setError(err.message);
      // Save failed query to history too
      await saveQueryToHistory(query, approach, userProfile?.persona || '', false);
    } finally {
      setIsTafsirLoading(false);
    }
  };

  const saveQueryToHistory = async (queryText, queryApproach, persona, hasResult) => {
    try {
      const token = await user.getIdToken();
      await fetch(`${BACKEND_URL}/query-history`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          query: queryText,
          approach: queryApproach,
          persona: persona,
          hasResult: hasResult
        })
      });
    } catch (err) {
      console.error('Failed to save query to history:', err);
    }
  };

  const handleSaveSearch = async () => {
    if (!response || !query) return;

    // Extract snippet from response
    const snippet = response.summary ||
      (response.tafsir_explanations && response.tafsir_explanations[0]?.explanation?.substring(0, 200)) ||
      'Tafsir result';

    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/saved-searches`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          query: query,
          approach: approach,
          folder: 'Uncategorized',
          title: query,
          responseSnippet: snippet,
          fullResponse: response
        })
      });

      if (res.ok) {
        alert('Answer saved! View it in your Saved Searches.');
      }
    } catch (err) {
      console.error('Failed to save search:', err);
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

        {/* Navigation Links */}
        <div style={{
          display: 'flex',
          gap: '12px',
          marginBottom: '24px',
          flexWrap: 'wrap',
          justifyContent: 'center'
        }}>
          <a
            href="/history"
            style={{
              padding: '10px 20px',
              background: 'linear-gradient(135deg, var(--cream) 0%, rgba(212, 175, 55, 0.1) 100%)',
              border: '2px solid var(--border-light)',
              borderRadius: '12px',
              color: 'var(--primary-teal)',
              fontWeight: '600',
              textDecoration: 'none',
              transition: 'all 0.3s ease'
            }}
            className="nav-link"
          >
            🕒 Query History
          </a>
          <a
            href="/saved"
            style={{
              padding: '10px 20px',
              background: 'linear-gradient(135deg, var(--cream) 0%, rgba(212, 175, 55, 0.1) 100%)',
              border: '2px solid var(--border-light)',
              borderRadius: '12px',
              color: 'var(--primary-teal)',
              fontWeight: '600',
              textDecoration: 'none',
              transition: 'all 0.3s ease'
            }}
            className="nav-link"
          >
            ⭐ Saved Answers
          </a>
          <a
            href="/annotations"
            style={{
              padding: '10px 20px',
              background: 'linear-gradient(135deg, var(--cream) 0%, rgba(212, 175, 55, 0.1) 100%)',
              border: '2px solid var(--border-light)',
              borderRadius: '12px',
              color: 'var(--primary-teal)',
              fontWeight: '600',
              textDecoration: 'none',
              transition: 'all 0.3s ease'
            }}
            className="nav-link"
          >
            📝 My Reflections
          </a>
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

        {/* Search Form - Fixed alignment */}
        <form onSubmit={handleGetTafsir} className="tafsir-form">
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
            maxLength={200}
          />

          <button type="submit" disabled={isTafsirLoading} className="search-button">
            {isTafsirLoading ? '⏳' : '🔍'}
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
            <EnhancedResultsDisplay data={response} user={user} />
            <div className="export-section">
              <h3>Save & Export</h3>
              <div className="export-controls">
                <button onClick={handleSaveSearch} className="export-btn">
                  ⭐ Save this Answer
                </button>
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
// RESULTS DISPLAY COMPONENT WITH ANNOTATIONS
// ============================================================================

function EnhancedResultsDisplay({ data, user }) {
  const [annotations, setAnnotations] = useState({});
  const [annotationPanelOpen, setAnnotationPanelOpen] = useState(false);
  const [currentVerse, setCurrentVerse] = useState(null);
  const [editingAnnotation, setEditingAnnotation] = useState(null);

  if (!data) return <div className="results-container"><p>No results to display.</p></div>;

  const {
    verses = [],
    tafsir_explanations = [],
    cross_references = [],
    lessons_practical_applications = [],
    summary = ''
  } = data;

  // Fetch annotations for all verses when component mounts
  useEffect(() => {
    if (verses.length > 0 && user) {
      verses.forEach(verse => {
        fetchVerseAnnotations(verse.surah, verse.verse_number);
      });
    }
  }, [verses, user]);

  const fetchVerseAnnotations = async (surah, verse) => {
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/annotations/verse/${surah}/${verse}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setAnnotations(prev => ({
          ...prev,
          [`${surah}:${verse}`]: data.annotations || []
        }));
      }
    } catch (err) {
      console.error('Failed to fetch annotations:', err);
    }
  };

  const handleAddAnnotation = (verse) => {
    setCurrentVerse(verse);
    setEditingAnnotation(null);
    setAnnotationPanelOpen(true);
  };

  const handleEditAnnotation = (verse, annotation) => {
    setCurrentVerse(verse);
    setEditingAnnotation(annotation);
    setAnnotationPanelOpen(true);
  };

  const handleDeleteAnnotation = async (surah, verse, annotationId) => {
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/annotations/${annotationId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        // Refresh annotations
        fetchVerseAnnotations(surah, verse);
      }
    } catch (err) {
      console.error('Failed to delete annotation:', err);
    }
  };

  const handleAnnotationSaved = () => {
    // Refresh annotations for current verse
    if (currentVerse) {
      fetchVerseAnnotations(currentVerse.surah, currentVerse.verse_number);
    }
  };

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
      {/* Annotation Panel */}
      {currentVerse && (
        <AnnotationPanel
          isOpen={annotationPanelOpen}
          onClose={() => setAnnotationPanelOpen(false)}
          verse={currentVerse}
          user={user}
          existingAnnotation={editingAnnotation}
          onSaved={handleAnnotationSaved}
        />
      )}

      {verses.length > 0 && (
        <div className="result-section">
          <h2>Relevant Verses</h2>
          {verses.map((verse, index) => {
            const verseKey = `${verse.surah}:${verse.verse_number}`;
            const verseAnnotations = annotations[verseKey] || [];

            return (
              <div key={index} style={{ marginBottom: '32px' }}>
                <div className="verse-card enhanced">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                    <p className="verse-ref" style={{ margin: 0 }}>
                      <strong>Surah {verse.surah}, Verse {verse.verse_number}</strong>
                    </p>
                    <button
                      onClick={() => handleAddAnnotation(verse)}
                      style={{
                        background: 'var(--gradient-teal-gold)',
                        border: 'none',
                        color: 'white',
                        padding: '8px 16px',
                        borderRadius: '20px',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        fontWeight: '700',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        transition: 'all 0.3s ease'
                      }}
                      className="add-annotation-btn"
                    >
                      📝 Add Note
                    </button>
                  </div>
                  {verse.arabic_text && verse.arabic_text !== 'Not available' && (
                    <p className="arabic-text" dir="rtl">{verse.arabic_text}</p>
                  )}
                  <p className="translation">
                    <em>&quot;{verse.text_saheeh_international}&quot;</em>
                  </p>

                  {/* Display Annotations */}
                  {verseAnnotations.length > 0 && (
                    <AnnotationDisplay
                      annotations={verseAnnotations}
                      onEdit={(annotation) => handleEditAnnotation(verse, annotation)}
                      onDelete={(annotationId) => handleDeleteAnnotation(verse.surah, verse.verse_number, annotationId)}
                    />
                  )}
                </div>
              </div>
            );
          })}
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
