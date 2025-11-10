'use client';
import ReactMarkdown from 'react-markdown';
import { useState, useEffect, useCallback, useRef } from 'react';
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
import iOS18TextHighlighter from './components/iOS18TextHighlighter';
import onboardingConfig from '../config/onboarding-messages.json';

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
  const [onboardingMessage, setOnboardingMessage] = useState(null);
  const [arabicGreeting, setArabicGreeting] = useState(null);

  // Select random onboarding message on mount
  useEffect(() => {
    const messages = onboardingConfig.onboardingMessages;
    const greetings = onboardingConfig.arabicGreetings;

    // Select random message
    const randomMessage = messages[Math.floor(Math.random() * messages.length)];

    // Find corresponding greeting
    const greeting = greetings.find(g => g.id === randomMessage.greetingId);

    setOnboardingMessage(randomMessage);
    setArabicGreeting(greeting);
  }, []);

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

  // Show loading state while message loads
  if (!onboardingMessage || !arabicGreeting) {
    return (
      <div className="container">
        <div className="card">
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="card">
        {/* Arabic Greeting */}
        <div style={{
          textAlign: 'center',
          marginBottom: '20px',
          padding: '16px',
          background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
          borderRadius: '12px',
          border: '2px solid var(--primary-teal)'
        }}>
          <h1 style={{
            fontFamily: 'Traditional Arabic, Scheherazade, serif',
            fontSize: '2.5rem',
            margin: '0 0 8px 0',
            color: 'var(--primary-teal)',
            direction: 'rtl'
          }}>
            {arabicGreeting.arabic}
          </h1>
          <p style={{ margin: '4px 0', fontSize: '0.95rem', color: '#666', fontStyle: 'italic' }}>
            {arabicGreeting.meaning}
          </p>
        </div>

        {/* Personalized Welcome Message */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <p style={{
            fontSize: '1.15rem',
            lineHeight: '1.7',
            color: '#555',
            whiteSpace: 'pre-line',
            marginBottom: '16px'
          }}>
            {onboardingMessage.message}
          </p>
          <p style={{ fontSize: '1.05rem', fontWeight: '600', color: 'var(--primary-teal)' }}>
            {onboardingMessage.callToAction}
          </p>
        </div>

        {/* Step 1: Persona Selection */}
        {step === 1 && personas.length > 0 && (
          <div>
            <div className="level-buttons">
              {personas.map(([key, persona]) => {
                // Get description from config if available, otherwise use API description
                const personaConfig = onboardingConfig.personaDescriptions[key];
                const displayDescription = personaConfig ? personaConfig.description : persona.description;

                return (
                  <button key={key} onClick={() => handlePersonaSelect(key, persona)}>
                    <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>
                      {getPersonaIcon(key)}
                    </div>
                    <div style={{ fontWeight: '700', fontSize: '1.1rem', marginBottom: '4px' }}>
                      {personaConfig ? personaConfig.name : persona.name}
                    </div>
                    <div style={{ fontSize: '0.85rem', opacity: 0.7, lineHeight: '1.4' }}>
                      {displayDescription}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Step 2: Knowledge Level (Only for Variable Personas) */}
        {step === 2 && !isDeterministicPersona && (
          <div>
            <button
              onClick={() => setStep(1)}
              style={{
                marginBottom: '20px',
                padding: '8px 16px',
                background: 'transparent',
                border: '1px solid var(--primary-teal)',
                borderRadius: '8px',
                color: 'var(--primary-teal)',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              ← Back to Profile Selection
            </button>
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
            <button
              onClick={() => setStep(isDeterministicPersona ? 1 : 2)}
              style={{
                marginBottom: '20px',
                padding: '8px 16px',
                background: 'transparent',
                border: '1px solid var(--primary-teal)',
                borderRadius: '8px',
                color: 'var(--primary-teal)',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              ← Back to {isDeterministicPersona ? 'Profile Selection' : 'Knowledge Level'}
            </button>
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

      // Check if backend needs clarification (fuzzy match suggestions)
      if (data.needs_clarification) {
        setResponse(data);  // Show suggestions in response area
        return;
      }

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

  const handleSuggestionClick = (suggestionObj) => {
    // Handle both old format (string) and new format (object with query and approach)
    if (typeof suggestionObj === 'string') {
      setQuery(suggestionObj);
    } else {
      setQuery(suggestionObj.query);
      setApproach(suggestionObj.approach);
    }
  };

  const handleCopyToClipboard = (event) => {
    if (!response) return;

    const button = event.currentTarget;
    const originalText = button.innerHTML;

    // Copy the complete response object as JSON
    const formattedText = JSON.stringify(response, null, 2);

    // ALWAYS use fallback method - most reliable across browsers
    const textArea = document.createElement('textarea');
    textArea.value = formattedText;
    textArea.style.position = 'absolute';
    textArea.style.left = '-9999px';
    textArea.style.top = '0';
    document.body.appendChild(textArea);

    try {
      textArea.select();
      textArea.setSelectionRange(0, 99999); // For mobile devices

      const successful = document.execCommand('copy');
      document.body.removeChild(textArea);

      if (successful) {
        // Show success notification
        button.innerHTML = '✅ Copied!';
        button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';

        setTimeout(() => {
          button.innerHTML = originalText;
          button.style.background = 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)';
        }, 2000);
      } else {
        throw new Error('Copy command failed');
      }
    } catch (err) {
      console.error('Copy failed:', err);
      document.body.removeChild(textArea);

      // Show error in button
      button.innerHTML = '❌ Copy Failed';
      button.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';

      setTimeout(() => {
        button.innerHTML = originalText;
        button.style.background = 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)';
      }, 2000);
    }
  };

  const handleShareLink = async (event) => {
    if (!response) return;

    const button = event.currentTarget;
    const originalText = button.innerHTML;

    // Show loading state
    button.innerHTML = '⏳ Creating link...';
    button.disabled = true;

    try {
      // Create shareable link via backend
      const res = await fetch(`${BACKEND_URL}/share`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: query,
          approach: approach,
          response: response
        })
      });

      if (!res.ok) {
        throw new Error('Failed to create shareable link');
      }

      const data = await res.json();
      const shareUrl = `${window.location.origin}/shared/${data.share_id}`;

      // PWA-compatible clipboard: Use Web Share API first on mobile
      if (navigator.share && /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)) {
        try {
          await navigator.share({
            title: 'Tafsir Simplified Response',
            text: 'Check out this Islamic Q&A response',
            url: shareUrl
          });

          button.innerHTML = '✅ Shared!';
          button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';

          setTimeout(() => {
            button.innerHTML = originalText;
            button.style.background = 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)';
            button.disabled = false;
          }, 2000);
          return;
        } catch (shareErr) {
          // User cancelled or share failed, fall through to clipboard
          if (shareErr.name !== 'AbortError') {
            console.log('Share API failed, using clipboard:', shareErr);
          }
        }
      }

      // Clipboard API for PWA (works in secure context with user gesture)
      if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
          await navigator.clipboard.writeText(shareUrl);

          button.innerHTML = '✅ Link Copied!';
          button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';

          setTimeout(() => {
            button.innerHTML = originalText;
            button.style.background = 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)';
            button.disabled = false;
          }, 2000);
        } catch (clipboardErr) {
          console.error('Clipboard API error:', clipboardErr);
          // Fallback to textarea method
          throw new Error('Clipboard API failed');
        }
      } else {
        // Fallback: textarea method for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = shareUrl;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
          const successful = document.execCommand('copy');
          document.body.removeChild(textArea);

          if (successful) {
            button.innerHTML = '✅ Link Copied!';
            button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';

            setTimeout(() => {
              button.innerHTML = originalText;
              button.style.background = 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)';
              button.disabled = false;
            }, 2000);
          } else {
            throw new Error('Copy command failed');
          }
        } catch (e) {
          document.body.removeChild(textArea);
          throw e;
        }
      }
    } catch (err) {
      console.error('Share link failed:', err);

      // Show error in button
      button.innerHTML = '❌ Share Failed - Tap to retry';
      button.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';

      setTimeout(() => {
        button.innerHTML = originalText;
        button.style.background = 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)';
        button.disabled = false;
      }, 3000);
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
        
        {/* Query Suggestions - Always Visible */}
        {suggestions.length > 0 && (
          <div className="suggestions-section" style={{ marginBottom: '24px', display: 'block', opacity: 1, visibility: 'visible' }}>
            <h3 style={{
              textAlign: 'center',
              color: 'var(--primary-teal)',
              marginBottom: '16px',
              fontSize: '1.1rem',
              fontWeight: '600'
            }}>
              🌟 Explore These Questions
            </h3>
            <div className="suggestions-grid" style={{ display: 'grid', opacity: 1, visibility: 'visible' }}>
              {suggestions.slice(0, 12).map((suggestion, index) => {
                const displayText = typeof suggestion === 'string' ? suggestion : suggestion.query;
                const approach = typeof suggestion === 'object' ? suggestion.approach : null;
                const type = typeof suggestion === 'object' ? suggestion.type : null;

                // Simplified icons: 📖 for direct verse/tafsir, 🔍 for exploration
                const approachIcon = approach === 'tafsir' || type === 'verse' ? '📖' : '🔍';
                const approachLabel = approach === 'tafsir' ? 'Tafsir' : 'Explore';

                return (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="suggestion-chip"
                    title={`${approachIcon} ${approachLabel}`}
                  >
                    <span>{approachIcon && <span style={{marginRight: '4px'}}>{approachIcon}</span>}{displayText}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Search Form - Fixed alignment */}
        <form onSubmit={handleGetTafsir} className="tafsir-form">
          <select value={approach} onChange={(e) => setApproach(e.target.value)}>
            <option value="tafsir">📖 Tafsir</option>
            <option value="explore">🔍 Explore</option>
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

        {response && response.needs_clarification && (
          <div style={{
            background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
            border: '2px solid #f59e0b',
            borderRadius: '12px',
            padding: '24px',
            marginBottom: '20px'
          }}>
            <h3 style={{ color: '#92400e', marginBottom: '12px', fontSize: '1.1rem' }}>
              {response.message}
            </h3>
            <p style={{ color: '#78350f', marginBottom: '16px', fontSize: '0.95rem' }}>
              {response.help_text}
            </p>
            {response.suggestions && response.suggestions.length > 0 && (
              <>
                <p style={{ fontWeight: '600', color: '#92400e', marginBottom: '10px' }}>
                  Did you mean:
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {response.suggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => {
                        setQuery(suggestion);
                        setResponse(null);
                      }}
                      style={{
                        padding: '12px 16px',
                        background: 'white',
                        border: '2px solid #f59e0b',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        textAlign: 'left',
                        fontSize: '0.95rem',
                        color: '#78350f',
                        fontWeight: '500',
                        transition: 'all 0.2s ease'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = '#fef3c7';
                        e.currentTarget.style.transform = 'translateX(4px)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'white';
                        e.currentTarget.style.transform = 'translateX(0)';
                      }}
                    >
                      → {suggestion}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {response && !response.needs_clarification && (
          <>
            {/* Save & Export Section - Moved to top for better accessibility */}
            <div className="export-section" style={{
              marginBottom: '24px',
              padding: '16px 20px',
              background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
              border: '2px solid #0ea5e9',
              borderRadius: '12px',
              boxShadow: '0 2px 8px rgba(14, 165, 233, 0.15)'
            }}>
              <div className="export-controls" style={{
                display: 'flex',
                gap: '12px',
                flexWrap: 'wrap',
                alignItems: 'center'
              }}>
                <button onClick={handleSaveSearch} className="export-btn" style={{
                  padding: '10px 20px',
                  background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: '600',
                  color: '#fff',
                  fontSize: '0.9rem',
                  boxShadow: '0 2px 6px rgba(245, 158, 11, 0.3)',
                  transition: 'all 0.3s ease'
                }}>
                  ⭐ Save
                </button>
                <button onClick={handleShareLink} className="export-btn" style={{
                  padding: '10px 20px',
                  background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: '600',
                  color: '#fff',
                  fontSize: '0.9rem',
                  boxShadow: '0 2px 6px rgba(139, 92, 246, 0.3)',
                  transition: 'all 0.3s ease'
                }}>
                  🔗 Share Link
                </button>
              </div>
            </div>

            {/* Approach Suggestion Banner */}
            {response.approach_suggestion && (
              <div style={{
                padding: '16px 20px',
                background: 'linear-gradient(135deg, #fff3cd 0%, #fffaeb 100%)',
                border: '2px solid #ffc107',
                borderRadius: '12px',
                marginBottom: '24px',
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                boxShadow: '0 2px 8px rgba(255, 193, 7, 0.15)'
              }}>
                <span style={{ fontSize: '1.5rem', flexShrink: 0 }}>💡</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: '700', color: '#856404', marginBottom: '4px' }}>
                    Suggestion
                  </div>
                  <div style={{ color: '#856404', fontSize: '0.95rem', lineHeight: '1.5' }}>
                    {response.approach_suggestion.reason}. Try the{' '}
                    <strong>
                      {response.approach_suggestion.suggested === 'tafsir' ? '📖 Tafsir-Based' : '🔍 Explore'}
                    </strong> approach instead.
                  </div>
                </div>
                <button
                  onClick={async () => {
                    // Set the approach first
                    setApproach(response.approach_suggestion.suggested);

                    // Wait for state update, then trigger search
                    setTimeout(async () => {
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
                          body: JSON.stringify({
                            approach: response.approach_suggestion.suggested,
                            query
                          })
                        });

                        const data = await res.json();

                        if (res.status === 429) {
                          setRateLimitWarning('You have reached your query limit. Please try again later.');
                          return;
                        }

                        if (!res.ok) throw new Error(data.error || 'Unknown error fetching Tafsir.');

                        setResponse(data);
                        await saveQueryToHistory(query, response.approach_suggestion.suggested, userProfile?.persona || '', true);
                      } catch (err) {
                        setError(err.message);
                        await saveQueryToHistory(query, response.approach_suggestion.suggested, userProfile?.persona || '', false);
                      } finally {
                        setIsTafsirLoading(false);
                      }
                    }, 0);
                  }}
                  style={{
                    padding: '10px 20px',
                    background: 'linear-gradient(135deg, #ffc107 0%, #ffb300 100%)',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: '700',
                    color: '#fff',
                    fontSize: '0.9rem',
                    whiteSpace: 'nowrap',
                    flexShrink: 0,
                    boxShadow: '0 2px 6px rgba(255, 193, 7, 0.3)',
                    transition: 'all 0.3s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.transform = 'translateY(-2px)';
                    e.target.style.boxShadow = '0 4px 12px rgba(255, 193, 7, 0.4)';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.transform = 'translateY(0)';
                    e.target.style.boxShadow = '0 2px 6px rgba(255, 193, 7, 0.3)';
                  }}
                >
                  Try It
                </button>
              </div>
            )}

            <EnhancedResultsDisplay data={response} user={user} query={query} approach={approach} />
          </>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// INLINE ANNOTATION FORM COMPONENT
// ============================================================================

function InlineAnnotationForm({ verse, user, onSaved, onCancel }) {
  const [content, setContent] = useState('');
  const [type, setType] = useState('personal_insight');
  const [customType, setCustomType] = useState('');
  const [tags, setTags] = useState([]);
  const [tagInput, setTagInput] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');

  const ANNOTATION_TYPES = [
    { value: 'personal_insight', label: '💡 Insight', icon: '💡' },
    { value: 'question', label: '❓ Question', icon: '❓' },
    { value: 'application', label: '✅ Application', icon: '✅' },
    { value: 'memory', label: '💭 Memory', icon: '💭' },
    { value: 'connection', label: '🔗 Connection', icon: '🔗' },
    { value: 'dua', label: '🤲 Dua/Prayer', icon: '🤲' },
    { value: 'gratitude', label: '🙏 Gratitude', icon: '🙏' },
    { value: 'reminder', label: '⏰ Reminder', icon: '⏰' },
    { value: 'story', label: '📚 Story/Example', icon: '📚' },
    { value: 'linguistic', label: '📝 Linguistic Note', icon: '📝' },
    { value: 'historical', label: '📜 Historical Context', icon: '📜' },
    { value: 'scientific', label: '🔬 Scientific Reflection', icon: '🔬' },
    { value: 'personal_experience', label: '💭 Personal Experience', icon: '💭' },
    { value: 'teaching_point', label: '👨‍🏫 Teaching Point', icon: '👨‍🏫' },
    { value: 'warning', label: '⚠️ Warning/Caution', icon: '⚠️' },
    { value: 'goal', label: '🎯 Goal/Action Item', icon: '🎯' },
    { value: 'contemplation', label: '🤔 Deep Contemplation', icon: '🤔' },
    { value: 'custom', label: '✨ Custom', icon: '✨' }
  ];

  const handleSave = async () => {
    if (!content.trim()) {
      setError('Please enter some content');
      return;
    }

    setIsSaving(true);
    setError('');

    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/annotations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          surah: verse.surah,
          verse: verse.verse_number,
          content,
          type: type === 'custom' ? customType : type,
          tags
        })
      });

      if (res.ok) {
        onSaved();
      } else {
        const errorData = await res.json();
        setError(errorData.error || 'Failed to save');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddTag = () => {
    const trimmed = tagInput.trim().toLowerCase();
    if (trimmed && !tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove) => {
    setTags(tags.filter(t => t !== tagToRemove));
  };

  // Get smart tag suggestions based on content
  const getSuggestedTags = () => {
    const suggestions = [];
    const lowerContent = content.toLowerCase();

    // Islamic concept tags
    if (lowerContent.includes('allah')) suggestions.push('tawheed');
    if (lowerContent.includes('prophet') || lowerContent.includes('muhammad')) suggestions.push('seerah');
    if (lowerContent.includes('prayer') || lowerContent.includes('salah')) suggestions.push('ibadah');
    if (lowerContent.includes('patience') || lowerContent.includes('sabr')) suggestions.push('character');
    if (lowerContent.includes('grateful') || lowerContent.includes('shukr')) suggestions.push('gratitude');
    if (lowerContent.includes('parent')) suggestions.push('family');
    if (lowerContent.includes('forgive')) suggestions.push('repentance');
    if (lowerContent.includes('mercy') || lowerContent.includes('rahman')) suggestions.push('mercy');
    if (lowerContent.includes('faith') || lowerContent.includes('iman')) suggestions.push('faith');
    if (lowerContent.includes('knowledge') || lowerContent.includes('ilm')) suggestions.push('knowledge');

    // Emotion/mood tags
    if (lowerContent.includes('happy') || lowerContent.includes('joy')) suggestions.push('joy');
    if (lowerContent.includes('sad') || lowerContent.includes('difficult')) suggestions.push('trial');
    if (lowerContent.includes('hope')) suggestions.push('hope');
    if (lowerContent.includes('fear')) suggestions.push('khawf');
    if (lowerContent.includes('peace')) suggestions.push('peace');

    // Remove duplicates and already added tags
    return [...new Set(suggestions)].filter(tag => !tags.includes(tag));
  };

  const suggestedTags = content.length > 20 ? getSuggestedTags() : [];

  return (
    <div style={{
      marginTop: '16px',
      padding: '20px',
      background: 'linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)',
      border: '2px solid var(--gold)',
      borderRadius: '12px',
      animation: 'slideDown 0.3s ease'
    }}>
      {/* Type Selector */}
      <div style={{ marginBottom: '16px' }}>
        <label style={{ display: 'block', fontWeight: '700', marginBottom: '8px', color: 'var(--primary-teal)', fontSize: '0.9rem' }}>
          Type
        </label>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {ANNOTATION_TYPES.map(({ value, icon, label }) => (
            <button
              key={value}
              onClick={() => setType(value)}
              style={{
                padding: '8px 12px',
                background: type === value ? 'var(--primary-teal)' : 'white',
                color: type === value ? 'white' : 'var(--foreground)',
                border: '2px solid var(--border-light)',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: '600',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <span>{icon}</span>
              <span>{label.split(' ')[1]}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Custom Type Input */}
      {type === 'custom' && (
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontWeight: '700', marginBottom: '8px', color: 'var(--primary-teal)', fontSize: '0.9rem' }}>
            Custom Type Name
          </label>
          <input
            type="text"
            value={customType}
            onChange={(e) => setCustomType(e.target.value)}
            placeholder="Enter your custom annotation type..."
            style={{
              width: '100%',
              padding: '10px 12px',
              border: '2px solid var(--border-medium)',
              borderRadius: '8px',
              fontSize: '0.9rem'
            }}
          />
        </div>
      )}

      {/* Content Textarea */}
      <div style={{ marginBottom: '16px' }}>
        <label style={{ display: 'block', fontWeight: '700', marginBottom: '8px', color: 'var(--primary-teal)', fontSize: '0.9rem' }}>
          Your Reflection
        </label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Write your thoughts, insights, or questions..."
          style={{
            width: '100%',
            minHeight: '100px',
            padding: '12px',
            border: '2px solid var(--border-medium)',
            borderRadius: '8px',
            fontSize: '0.95rem',
            fontFamily: 'inherit',
            resize: 'vertical',
            background: 'white'
          }}
          autoFocus
        />
      </div>

      {/* Tags */}
      <div style={{ marginBottom: '16px' }}>
        <label style={{ display: 'block', fontWeight: '700', marginBottom: '8px', color: 'var(--primary-teal)', fontSize: '0.9rem' }}>
          Tags (optional)
        </label>
        <div style={{ display: 'flex', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
          {tags.map(tag => (
            <span
              key={tag}
              style={{
                background: 'var(--primary-teal)',
                color: 'white',
                padding: '4px 10px',
                borderRadius: '12px',
                fontSize: '0.8rem',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              {tag}
              <button
                onClick={() => handleRemoveTag(tag)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'white',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  padding: 0,
                  width: '14px',
                  height: '14px'
                }}
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
            placeholder="Add tag..."
            style={{
              flex: 1,
              padding: '8px 12px',
              border: '2px solid var(--border-medium)',
              borderRadius: '8px',
              fontSize: '0.9rem',
              background: 'white'
            }}
          />
          <button
            onClick={handleAddTag}
            style={{
              padding: '8px 16px',
              background: 'var(--primary-teal)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.9rem',
              fontWeight: '600'
            }}
          >
            Add
          </button>
        </div>

        {/* Smart Tag Suggestions */}
        {suggestedTags.length > 0 && (
          <div style={{ marginTop: '8px' }}>
            <div style={{
              fontSize: '0.75rem',
              color: '#666',
              marginBottom: '6px',
              fontWeight: '600'
            }}>
              💡 Suggested tags based on your reflection:
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {suggestedTags.map(tag => (
                <button
                  key={tag}
                  onClick={() => {
                    if (!tags.includes(tag)) {
                      setTags([...tags, tag]);
                    }
                  }}
                  style={{
                    padding: '4px 10px',
                    background: 'rgba(13, 148, 136, 0.1)',
                    color: 'var(--primary-teal)',
                    border: '1px solid var(--primary-teal)',
                    borderRadius: '12px',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.background = 'var(--primary-teal)';
                    e.target.style.color = 'white';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.background = 'rgba(13, 148, 136, 0.1)';
                    e.target.style.color = 'var(--primary-teal)';
                  }}
                >
                  + {tag}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div style={{
          padding: '10px',
          background: 'rgba(220, 38, 38, 0.1)',
          border: '2px solid var(--error-color)',
          borderRadius: '8px',
          color: 'var(--error-color)',
          marginBottom: '12px',
          fontSize: '0.9rem',
          fontWeight: '600'
        }}>
          {error}
        </div>
      )}

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
        <button
          onClick={onCancel}
          style={{
            padding: '10px 20px',
            background: 'white',
            border: '2px solid var(--border-medium)',
            color: 'var(--foreground)',
            borderRadius: '8px',
            fontSize: '0.95rem',
            fontWeight: '700',
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving || !content.trim()}
          style={{
            padding: '10px 24px',
            background: isSaving || !content.trim() ? '#ccc' : 'var(--gradient-teal-gold)',
            border: 'none',
            color: 'white',
            borderRadius: '8px',
            fontSize: '0.95rem',
            fontWeight: '700',
            cursor: isSaving || !content.trim() ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          {isSaving ? '💾 Saving...' : '💾 Save Reflection'}
        </button>
      </div>

      <style jsx>{`
        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}

// ============================================================================
// RESULTS DISPLAY COMPONENT WITH ANNOTATIONS
// ============================================================================

function EnhancedResultsDisplay({ data, user, query, approach }) {
  const [annotations, setAnnotations] = useState({});
  const [annotationPanelOpen, setAnnotationPanelOpen] = useState(false);
  const [currentVerse, setCurrentVerse] = useState(null);
  const [editingAnnotation, setEditingAnnotation] = useState(null);
  const [inlineAnnotationVerse, setInlineAnnotationVerse] = useState(null);
  const [currentShareId, setCurrentShareId] = useState(null);

  // Track pending share ID request to prevent duplicates
  const pendingShareRequest = useRef(null);

  // Ref for clearing text selection (releases scroll lock)
  const clearSelectionRef = useRef(null);

  // Use ref for data to stabilize handleTextHighlight callback
  const dataRef = useRef(data);
  useEffect(() => {
    dataRef.current = data;
  }, [data]);

  const fetchVerseAnnotations = useCallback(async (surah, verse) => {
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
  }, [user]);

  // Extract data properties
  const {
    verses = [],
    tafsir_explanations = [],
    cross_references = [],
    lessons_practical_applications = [],
    summary = ''
  } = data || {};

  // Fetch annotations for all verses when component mounts
  useEffect(() => {
    if (verses.length > 0 && user) {
      verses.forEach(verse => {
        fetchVerseAnnotations(verse.surah, verse.verse_number);
      });
    }
  }, [verses, user, fetchVerseAnnotations]);

  // Ensure we have a share_id for linking reflections back to responses
  const ensureShareId = useCallback(async () => {
    if (currentShareId) return currentShareId;

    // Prevent duplicate requests - reuse in-flight promise
    if (pendingShareRequest.current) {
      return pendingShareRequest.current;
    }

    try {
      const promise = fetch(`${BACKEND_URL}/share`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: query,
          approach: approach,
          response: data
        })
      }).then(async (res) => {
        if (!res.ok) {
          console.error('Failed to create share link for annotation');
          return null;
        }
        const shareData = await res.json();
        setCurrentShareId(shareData.share_id);
        return shareData.share_id;
      });

      pendingShareRequest.current = promise;
      const result = await promise;
      pendingShareRequest.current = null;
      return result;
    } catch (err) {
      pendingShareRequest.current = null;
      console.error('Error creating share link:', err);
      return null;
    }
  }, [currentShareId, query, approach, data]);

  const handleTextHighlight = useCallback((highlightedText) => {
    // Use ref to access current data value (stabilizes callback)
    const currentData = dataRef.current;

    // Open panel immediately for instant UX (don't await)
    setCurrentVerse({
      reflectionType: 'highlight',
      highlightedText,
      queryContext: currentData?.verses?.[0] ? `${currentData.verses[0].surah}:${currentData.verses[0].verse_number}` : 'Response'
    });

    // Ensure share ID in background (non-blocking)
    ensureShareId().catch(err => console.error('Failed to create share link:', err));
  }, [ensureShareId]);

  // Early return after all hooks
  if (!data) return <div className="results-container"><p>No results to display.</p></div>;

  const handleAddAnnotation = (verse) => {
    const verseKey = `${verse.surah}:${verse.verse_number}`;
    // Toggle inline annotation form
    if (inlineAnnotationVerse === verseKey) {
      setInlineAnnotationVerse(null);
    } else {
      setInlineAnnotationVerse(verseKey);
      setCurrentVerse(verse);
      setEditingAnnotation(null);
    }
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
      setInlineAnnotationVerse(null); // Close inline form after saving
    }
    // Release scroll lock if there's an active text selection
    clearSelectionRef.current?.(); // ✅ Release scroll lock
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
    <iOS18TextHighlighter
      onHighlight={handleTextHighlight}
      onClearSelection={clearSelectionRef}
      enabled={true}
    >
      <div className="results-container">
        {/* General Reflection Button */}
      {user && (
        <div style={{
          position: 'sticky',
          top: '20px',
          zIndex: 100,
          display: 'flex',
          justifyContent: 'flex-end',
          marginBottom: '20px',
          paddingRight: '20px'
        }}>
          <button
            onClick={() => {
              setCurrentVerse({ reflectionType: 'general', queryContext: query });
              ensureShareId().catch(err => console.error('Failed to create share link:', err));
            }}
            style={{
              background: 'var(--gradient-teal-gold)',
              border: 'none',
              color: 'white',
              padding: '12px 24px',
              borderRadius: '24px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: 'var(--shadow-medium)',
              transition: 'all 0.3s ease'
            }}
            className="unified-add-note-btn"
            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          >
            ✨ Reflect on Entire Response
          </button>
        </div>
      )}

      {/* General Annotation Panel */}
      {currentVerse?.reflectionType === 'general' && (
        <AnnotationPanel
          isOpen={true}
          verse={{}}
          user={user}
          reflectionType="general"
          queryContext={currentVerse.queryContext}
          shareId={currentShareId}
          onClose={() => {
            setCurrentVerse(null);
            clearSelectionRef.current?.(); // ✅ Release scroll lock
          }}
          onSaved={() => {
            setCurrentVerse(null);
            clearSelectionRef.current?.(); // ✅ Release scroll lock
            // Refresh annotations
            Object.keys(annotations).forEach(key => {
              const [surah, verse] = key.split(':');
              fetchVerseAnnotations(surah, verse);
            });
          }}
        />
      )}

      {/* Annotation Panel for verses */}
      {currentVerse && currentVerse.surah && (
        <AnnotationPanel
          isOpen={annotationPanelOpen}
          onClose={() => {
            setAnnotationPanelOpen(false);
            clearSelectionRef.current?.(); // ✅ Release scroll lock
          }}
          verse={currentVerse}
          user={user}
          existingAnnotation={editingAnnotation}
          onSaved={handleAnnotationSaved}
          reflectionType="verse"
          shareId={currentShareId}
        />
      )}

      {/* Annotation Panel for sections */}
      {currentVerse && currentVerse.reflectionType === 'section' && (
        <AnnotationPanel
          isOpen={true}
          onClose={() => {
            setCurrentVerse(null);
            clearSelectionRef.current?.(); // ✅ Release scroll lock
          }}
          verse={{}}
          user={user}
          reflectionType="section"
          sectionName={currentVerse.sectionName}
          queryContext={currentVerse.queryContext}
          shareId={currentShareId}
          onSaved={() => {
            setCurrentVerse(null);
            clearSelectionRef.current?.(); // ✅ Release scroll lock
          }}
        />
      )}

      {/* Annotation Panel for highlighted text */}
      {currentVerse && currentVerse.reflectionType === 'highlight' && (
        <AnnotationPanel
          isOpen={true}
          onClose={() => {
            setCurrentVerse(null);
            clearSelectionRef.current?.(); // ✅ Release scroll lock
          }}
          verse={{}}
          user={user}
          reflectionType="highlight"
          highlightedText={currentVerse.highlightedText}
          queryContext={currentVerse.queryContext}
          shareId={currentShareId}
          onSaved={() => {
            setCurrentVerse(null);
            clearSelectionRef.current?.(); // ✅ Release scroll lock
          }}
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
                  <div style={{ marginBottom: '16px' }}>
                    <p className="verse-ref" style={{ margin: 0 }}>
                      <strong>{verse.surah_name ? `${verse.surah_name} ` : `Surah ${verse.surah}, `}Verse {verse.verse_number}</strong>
                    </p>
                  </div>
                  {verse.arabic_text && verse.arabic_text !== 'Not available' && (
                    <p className="arabic-text" dir="rtl">{verse.arabic_text}</p>
                  )}
                  <p className="translation">
                    <em>&quot;{verse.text_saheeh_international}&quot;</em>
                  </p>

                  {/* Inline Annotation Form */}
                  {inlineAnnotationVerse === verseKey && (
                    <InlineAnnotationForm
                      verse={verse}
                      user={user}
                      onSaved={handleAnnotationSaved}
                      onCancel={() => setInlineAnnotationVerse(null)}
                    />
                  )}

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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ margin: 0 }}>Tafsir Explanations</h2>
            {user && (
              <button
                onClick={() => {
                  setCurrentVerse({ reflectionType: 'section', sectionName: 'Tafsir Explanations', queryContext: query });
                  ensureShareId().catch(err => console.error('Failed to create share link:', err));
                }}
                style={{
                  padding: '8px 16px',
                  background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                  border: 'none',
                  borderRadius: '8px',
                  color: 'white',
                  fontSize: '0.85rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
              >
                💭 Reflect
              </button>
            )}
          </div>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ margin: 0 }}>Related Verses</h2>
            {user && (
              <button
                onClick={() => {
                  setCurrentVerse({ reflectionType: 'section', sectionName: 'Related Verses', queryContext: query });
                  ensureShareId().catch(err => console.error('Failed to create share link:', err));
                }}
                style={{
                  padding: '8px 16px',
                  background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                  border: 'none',
                  borderRadius: '8px',
                  color: 'white',
                  fontSize: '0.85rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
              >
                💭 Reflect
              </button>
            )}
          </div>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ margin: 0 }}>Lessons &amp; Practical Applications</h2>
            {user && (
              <button
                onClick={() => {
                  setCurrentVerse({ reflectionType: 'section', sectionName: 'Lessons & Practical Applications', queryContext: query });
                  ensureShareId().catch(err => console.error('Failed to create share link:', err));
                }}
                style={{
                  padding: '8px 16px',
                  background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                  border: 'none',
                  borderRadius: '8px',
                  color: 'white',
                  fontSize: '0.85rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
              >
                💭 Reflect
              </button>
            )}
          </div>
          <ul className="lessons-list">
            {lessons_practical_applications.map((lesson, index) => (
              <li key={index} className="lesson-item">{lesson.point}</li>
            ))}
          </ul>
        </div>
      )}

      {summary && (
        <div className="result-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ margin: 0 }}>Summary</h2>
            {user && (
              <button
                onClick={() => {
                  setCurrentVerse({ reflectionType: 'section', sectionName: 'Summary', queryContext: query });
                  ensureShareId().catch(err => console.error('Failed to create share link:', err));
                }}
                style={{
                  padding: '8px 16px',
                  background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                  border: 'none',
                  borderRadius: '8px',
                  color: 'white',
                  fontSize: '0.85rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
              >
                💭 Reflect
              </button>
            )}
          </div>
          <div className="summary-content">
            <p>{summary}</p>
          </div>
        </div>
      )}
      </div>
    </iOS18TextHighlighter>
  );
}
