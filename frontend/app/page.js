'use client';
import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  onAuthStateChanged,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  updateProfile
} from 'firebase/auth';
import { auth } from './lib/firebase';
import { BACKEND_URL, getPersonaTheme, getPersonaIcon } from './lib/config';
import AnnotationDialog from './components/AnnotationDialog';
import AnnotationDisplay from './components/AnnotationDisplay';
import CollapsibleSection from './components/CollapsibleSection';
import TabNavigation from './components/TabNavigation';
import BottomNav from './components/BottomNav';
import DesktopNav from './components/DesktopNav';
import Tooltip from './components/Tooltip';
import HelpMenu, { FloatingHelpButton } from './components/HelpMenu';
import FeatureIntroModal from './components/FeatureIntroModal';
import FloatingAnnotateButton from './components/FloatingAnnotateButton';
import ConfirmDialog from './components/ConfirmDialog';
import ErrorBoundary from './components/ErrorBoundary';
import TafsirLogo from './components/Logo';
import SurahVersePicker from './components/SurahVersePicker';
import CollectionsGrid from './components/CollectionsGrid';
import BadgeDisplay, { BadgePopup } from './components/BadgeDisplay';
import { ToastContainer } from './components/ui/Toast';
import { TafsirSkeleton, Skeleton } from './components/ui/SkeletonLoader';
import { loadSearchState, saveSearchState, clearSearchState } from './utils/searchPersistence';
import { useToast } from './hooks/useToast';
import useTextSelection from './hooks/useTextSelection';
import { useOnboarding } from './hooks/useOnboarding';
import onboardingConfig from '../config/onboarding-messages.json';
import { getNameInfo, validateFirstName } from './utils/nameInfo';

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function HomePage() {
  // Global error handlers
  useEffect(() => {
    // Global error handler
    const handleError = (event) => {
      console.error('Global error caught:', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error
      });
    };

    const handleUnhandledRejection = (event) => {
      console.error('Unhandled promise rejection:', event.reason);
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, []);

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
    } catch {
      // No saved profile, will proceed to onboarding
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
        <div className="card" style={{ padding: '32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
            <Skeleton width="50px" height="50px" variant="circular" />
            <Skeleton width="200px" height="32px" />
          </div>
          <TafsirSkeleton />
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

  return (
    <MainApp
      user={user}
      userProfile={userProfile}
      onResetProfile={() => setUserProfile(null)}
    />
  );
}

// ============================================================================
// AUTHENTICATION COMPONENT
// ============================================================================

function AuthComponent() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [firstNameError, setFirstNameError] = useState(null);
  const [nameInfo, setNameInfo] = useState(null);
  const [nameInfoDismissed, setNameInfoDismissed] = useState(false);
  const [error, setError] = useState('');
  const [isSignUp, setIsSignUp] = useState(true);
  const nameDebounceRef = useRef(null);

  // Debounced name info lookup
  useEffect(() => {
    if (!isSignUp) return;
    clearTimeout(nameDebounceRef.current);
    setNameInfoDismissed(false);
    if (!firstName || firstName.trim().length < 2) {
      setNameInfo(null);
      return;
    }
    nameDebounceRef.current = setTimeout(() => {
      const info = getNameInfo(firstName);
      setNameInfo(info);
    }, 400);
    return () => clearTimeout(nameDebounceRef.current);
  }, [firstName, isSignUp]);

  const handleFirstNameChange = (value) => {
    setFirstName(value);
    const { valid, error: err } = validateFirstName(value);
    setFirstNameError(valid ? null : err);
  };

  const handleAuthAction = async (e) => {
    e.preventDefault();
    setError('');

    // Validate firstName if provided (sign-up only)
    if (isSignUp && firstName.trim()) {
      const { valid, error: err } = validateFirstName(firstName);
      if (!valid) {
        setFirstNameError(err);
        return;
      }
    }

    try {
      if (isSignUp) {
        const cred = await createUserWithEmailAndPassword(auth, email, password);
        // Set displayName if firstName provided
        if (firstName.trim()) {
          await updateProfile(cred.user, { displayName: firstName.trim() });
        }
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
        <p style={{ fontSize: '1rem', color: '#666', marginBottom: '32px', textAlign: 'center', lineHeight: '1.6' }}>
          {isSignUp
            ? 'Quranic commentary drawn from classical scholarship and personalized to how you learn — with progress tracking, reflections, and reading plans to support your journey.'
            : 'Sign in to continue your Quranic journey.'}
        </p>
        <form onSubmit={handleAuthAction} className="form">
          {isSignUp && (
            <div style={{ marginBottom: '12px' }}>
              <input
                type="text"
                value={firstName}
                onChange={(e) => handleFirstNameChange(e.target.value)}
                placeholder="First name (optional)"
                autoComplete="given-name"
                style={{ width: '100%' }}
              />
              {firstNameError && (
                <p style={{ color: '#dc2626', fontSize: '0.85rem', margin: '4px 0 0 0' }}>
                  {firstNameError}
                </p>
              )}
              {/* Name info card */}
              {nameInfo && !nameInfoDismissed && (
                <div style={{
                  marginTop: '8px',
                  padding: '12px 16px',
                  background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
                  borderRadius: '10px',
                  border: '1px solid var(--primary-teal)',
                  position: 'relative',
                  animation: 'fadeIn 0.3s ease'
                }}>
                  <button
                    type="button"
                    onClick={() => setNameInfoDismissed(true)}
                    style={{
                      position: 'absolute', top: '6px', right: '8px',
                      background: 'none', border: 'none', cursor: 'pointer',
                      fontSize: '1.1rem', color: '#999', lineHeight: 1
                    }}
                    aria-label="Dismiss"
                  >
                    x
                  </button>
                  <p style={{
                    fontWeight: '600', color: 'var(--primary-teal)',
                    margin: '0 0 4px 0', fontSize: '0.95rem'
                  }}>
                    About this name
                  </p>
                  <p style={{ margin: 0, color: '#555', fontSize: '0.9rem', lineHeight: '1.5' }}>
                    {nameInfo.short}
                  </p>
                </div>
              )}
            </div>
          )}
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
      } catch {
        // Could not fetch personas, using defaults
        setPersonas([
          ['new_revert', {
            name: 'New Revert',
            description: 'warm, encouraging | Format: academic_prose',
            requires_knowledge_level_input: false
          }],
          ['curious_explorer', {
            name: 'Curious Explorer',
            description: 'warm, reflective | Format: academic_prose',
            requires_knowledge_level_input: true
          }],
          ['practicing_muslim', {
            name: 'Practicing Muslim',
            description: 'balanced | Format: academic_prose',
            requires_knowledge_level_input: true
          }],
          ['student', {
            name: 'Islamic Studies Student',
            description: 'educational | Format: academic_prose',
            requires_knowledge_level_input: false
          }],
          ['advanced_learner', {
            name: 'Advanced Learner',
            description: 'academic, precise | Format: academic_prose',
            requires_knowledge_level_input: false
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

      // Forward first_name from Firebase Auth displayName
      if (user.displayName) {
        payload.first_name = user.displayName;
      }

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
      onProfileComplete(result.profile);
    } catch (err) {
      // Profile fetch failed — user will be redirected to onboarding
      setError(err.message);
    }
  }, [user, profile, onProfileComplete, isDeterministicPersona]);

  const handlePersonaSelect = (personaKey, personaData) => {
    setProfile((prev) => ({ ...prev, persona: personaKey }));
    
    // Check if this is a deterministic persona (auto-sets knowledge_level)
    const deterministic = ['advanced_learner', 'student', 'new_revert'];
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
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Beginner</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  New to Islamic studies
                </div>
              </button>
              <button onClick={() => handleKnowledgeLevelSelect('intermediate')}>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Intermediate</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Some Islamic background
                </div>
              </button>
              <button onClick={() => handleKnowledgeLevelSelect('advanced')}>
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
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Practical Application</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Focus on how to apply teachings in daily life
                </div>
              </button>
              <button onClick={() => handleLearningGoalSelect('understanding')}>
                <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>Deep Understanding</div>
                <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.7 }}>
                  Focus on scholarly depth and theological context
                </div>
              </button>
              <button onClick={() => handleLearningGoalSelect('balanced')}>
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

function MainApp({ user, userProfile, onResetProfile }) {
  const searchParams = useSearchParams();
  // Deep Tafsir mode only - Explore is disabled for now
  const approach = 'tafsir';
  const [query, setQuery] = useState('');
  const [pickerSurah, setPickerSurah] = useState(null);
  const [pickerVerse, setPickerVerse] = useState(null);
  const [response, setResponse] = useState(null);
  const [urlParamsProcessed, setUrlParamsProcessed] = useState(false);
  const [error, setError] = useState('');
  const [isTafsirLoading, setIsTafsirLoading] = useState(false);
  const [rateLimitWarning, setRateLimitWarning] = useState('');
  const [showPersonaConfirm, setShowPersonaConfirm] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [navCollapsed, setNavCollapsed] = useState(false);
  const [desktopStats, setDesktopStats] = useState({
    savedCount: 0,
    historyCount: 0,
    annotationCount: 0
  });

  // Daily verse & streak state
  const [dailyVerse, setDailyVerse] = useState(null);
  const [streak, setStreak] = useState({ current_streak: 0, longest_streak: 0 });

  // Badge popup state
  const [badgePopup, setBadgePopup] = useState(null);

  // Toast notifications
  const { toasts, showSuccess, showError } = useToast();

  // Save-to-folder dialog state
  const [showFolderPicker, setShowFolderPicker] = useState(false);
  const [existingFolders, setExistingFolders] = useState([]);
  const [newFolderName, setNewFolderName] = useState('');

  // Annotation state (lifted from EnhancedResultsDisplay)
  const [annotations, setAnnotations] = useState({});
  const [annotationDialogOpen, setAnnotationDialogOpen] = useState(false);
  const [currentVerse, setCurrentVerse] = useState(null);
  const [editingAnnotation, setEditingAnnotation] = useState(null);
  const [inlineAnnotationVerse, setInlineAnnotationVerse] = useState(null);
  const [currentShareId, setCurrentShareId] = useState(null);

  // Onboarding system
  const {
    onboardingState,
    markStepComplete,
    markFeatureIntroSeen,
    isLoaded: onboardingLoaded
  } = useOnboarding(user?.uid);

  // Feature intro modal — show for first-time users
  const [showFeatureIntro, setShowFeatureIntro] = useState(false);

  useEffect(() => {
    if (onboardingLoaded && !onboardingState.hasSeenFeatureIntro) {
      setShowFeatureIntro(true);
    }
  }, [onboardingLoaded, onboardingState.hasSeenFeatureIntro]);


  // Help menu state
  const [helpMenuOpen, setHelpMenuOpen] = useState(false);

  // Text selection for annotations (lifted from EnhancedResultsDisplay)
  const { selectedText, clearSelection } = useTextSelection({
    minLength: 3,
    enabled: true,
    container: '.results-container'
  });

  // AbortController for cancelling fetch requests
  const abortControllerRef = useRef(null);

  // Timeout for search requests (60 seconds for explore, 30 seconds for tafsir)
  const searchTimeoutRef = useRef(null);

  // Ref to track pending share request (for ensureShareId)
  const pendingShareRequest = useRef(null);

  // Detect mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Fetch daily verse and streak on mount
  useEffect(() => {
    fetch(`${BACKEND_URL}/daily-verse`)
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (data) setDailyVerse(data); })
      .catch(() => {});

    if (user) {
      user.getIdToken().then(token => {
        fetch(`${BACKEND_URL}/streak`, {
          headers: { Authorization: `Bearer ${token}` }
        })
          .then(res => res.ok ? res.json() : null)
          .then(data => {
            if (data) {
              setStreak(data);
            }
          })
          .catch(() => {});
      });
    }
  }, [user]);

  // Update streak helper
  const updateStreak = useCallback(async () => {
    if (!user) return;
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/streak`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setStreak(data);
        // Show badge popup if newly earned
        if (data.newly_earned_badges?.length > 0) {
          setBadgePopup(data.newly_earned_badges[0]);
        }
      }
    } catch {
      // Non-critical
    }
  }, [user]);

  // Helper to navigate to a verse (used by collections, recommendations, reading plans)
  const handleStudyVerse = useCallback((surah, verse) => {
    setPickerSurah(surah);
    setPickerVerse(verse);
    setQuery(`${surah}:${verse}`);
    setTimeout(() => {
      document.querySelector('.tafsir-form')?.requestSubmit();
    }, 100);
  }, []);

  // Load saved search state on mount (survives page refresh)
  useEffect(() => {
    const savedState = loadSearchState();
    if (savedState) {
      setQuery(savedState.query);
      setResponse(savedState.response);
    }
  }, []);

  // Handle URL parameters (for history re-run functionality)
  useEffect(() => {
    if (urlParamsProcessed) return; // Only process once

    const queryParam = searchParams.get('query');

    if (queryParam) {
      // URL params take priority over saved state
      setQuery(queryParam);
      setUrlParamsProcessed(true);

      // Parse verse ref (e.g., "7:189") and sync the dropdown
      const match = queryParam.match(/^(\d+):(\d+)/);
      if (match) {
        setPickerSurah(parseInt(match[1]));
        setPickerVerse(parseInt(match[2]));
      }

      // Auto-submit the search form
      setTimeout(() => {
        document.querySelector('.tafsir-form')?.requestSubmit();
      }, 200);

      // Clear the URL params after reading them (clean URL)
      if (typeof window !== 'undefined') {
        const url = new URL(window.location.href);
        url.searchParams.delete('query');
        window.history.replaceState({}, '', url.pathname);
      }
    }
  }, [searchParams, urlParamsProcessed]);

  // Save search state when response changes
  useEffect(() => {
    if (response && query) {
      saveSearchState(query, approach, response);
    }
  }, [response, query, approach]);

  // Define handler functions BEFORE keyboard shortcuts useEffect that references them
  const handleNewSearch = useCallback(() => {
    // Clear results and focus input for new search
    setResponse(null);
    setError('');
    clearSearchState(); // Clear persisted search
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // Open folder picker before saving
  const handleSaveSearch = useCallback(async () => {
    if (!response || !query || !user) return;
    // Fetch existing folders first
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/saved-searches/folders`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setExistingFolders((data.folders || []).map(f => f.name));
      }
    } catch { /* non-critical */ }
    setNewFolderName('');
    setShowFolderPicker(true);
  }, [response, query, user]);

  // Actually save with the chosen folder
  const doSaveToFolder = useCallback(async (folderName) => {
    if (!response || !query) return;
    setShowFolderPicker(false);

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
          folder: folderName || 'Uncategorized',
          title: query,
          responseSnippet: snippet,
          fullResponse: response
        })
      });

      if (res.ok) {
        showSuccess(`Saved to "${folderName || 'Uncategorized'}"`);
        if (!onboardingState.hasViewedSaved) {
          markStepComplete('hasViewedSaved');
        }
      } else {
        showError('Failed to save. Please try again.');
      }
    } catch {
      showError('Failed to save. Please try again.');
    }
  }, [response, query, user, approach, onboardingState.hasViewedSaved, markStepComplete, showSuccess, showError]);

  // Keyboard shortcuts for desktop and mobile
  useEffect(() => {
    // Enable keyboard shortcuts on both desktop and mobile
    const handleKeyDown = (e) => {
      // Don't trigger shortcuts if user is typing in input/textarea
      const activeElement = document.activeElement;
      const isTyping = activeElement?.tagName === 'INPUT' ||
                      activeElement?.tagName === 'TEXTAREA' ||
                      activeElement?.contentEditable === 'true';

      // Ctrl+K or Cmd+K to scroll to picker (always available)
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
      }

      // Skip other shortcuts if user is typing
      if (isTyping && e.key !== 'Escape') return;

      // Escape to cancel request or clear results (preserves query)
      if (e.key === 'Escape') {
        e.preventDefault();

        if (isTafsirLoading) {
          // Cancel in-flight request, keep query
          if (abortControllerRef.current) {
            abortControllerRef.current.abort();
          }
          setIsTafsirLoading(false);
          setError('');
        } else if (response) {
          // Clear results and scroll to picker
          setResponse(null);
          setError('');
          window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
          // Just blur if no results
          activeElement?.blur();
        }
      }

      // Alt+S to save current result
      if (e.altKey && e.key === 's' && response) {
        e.preventDefault();
        if (handleSaveSearch) {
          handleSaveSearch();
        }
      }

      // Alt+H for help
      if (e.altKey && e.key === 'h') {
        e.preventDefault();
        // Trigger help menu if available
        document.querySelector('.help-toggle')?.click();
      }

      // Alt+N for new search
      if (e.altKey && e.key === 'n') {
        e.preventDefault();
        if (handleNewSearch) {
          handleNewSearch();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [response, isTafsirLoading, handleSaveSearch, handleNewSearch]);

  // Apply persona theme
  useEffect(() => {
    const persona = userProfile?.persona || 'practicing_muslim';
    const theme = getPersonaTheme(persona);
    document.documentElement.style.setProperty('--user-gradient', theme.gradient);
    document.documentElement.style.setProperty('--user-color', theme.color);
  }, [userProfile]);

  // Start welcome tour for first-time users (only after localStorage is loaded)


  const handleCancelSearch = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsTafsirLoading(false);
    setError('');
    // Keep query intact - don't clear it!
  };

  // handleNewSearch moved to before keyboard shortcuts useEffect

  const handleGetTafsir = async (e) => {
    e.preventDefault();

    // If currently loading, cancel instead of submitting
    if (isTafsirLoading) {
      if (handleCancelSearch) {
        handleCancelSearch();
      }
      return;
    }

    if (!query) return;

    // Cancel any in-flight request and timeout
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    // Set timeout for tafsir requests (3 minutes: scholarly planning + generation + retries)
    const timeoutMs = 180000;
    searchTimeoutRef.current = setTimeout(() => {
      // Clear the ref BEFORE aborting so the catch handler knows it was a timeout
      searchTimeoutRef.current = null;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        setError('The request took too long. Please try again or simplify your query.');
        setIsTafsirLoading(false);
      }
    }, timeoutMs);

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
        body: JSON.stringify({ approach, query }),
        signal: abortControllerRef.current.signal
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
      if (!onboardingState.hasSearched) {
        markStepComplete('hasSearched');
      }

      // Update streak on successful search
      updateStreak();

      // Save to query history
      await saveQueryToHistory(query, approach, userProfile?.persona || '', true);
    } catch (err) {
      // Don't show error for user-initiated cancellations (but show for timeouts)
      if (err.name === 'AbortError') {
        // Check if this was a timeout abort (searchTimeoutRef is null after timeout fires)
        if (searchTimeoutRef.current === null) {
          // Timeout already set the error message
          return;
        }
        // User cancelled the request
        return;
      }
      // Improve error message for user
      const errorMessage = err.message.includes('Internal server error')
        ? 'The server encountered an issue. Please try again in a moment.'
        : err.message;
      setError(errorMessage);
      // Save failed query to history too
      await saveQueryToHistory(query, approach, userProfile?.persona || '', false);
    } finally {
      // Clear the timeout when request completes
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
        searchTimeoutRef.current = null;
      }
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
      // History save failed silently — non-critical
    }
  };

  // handleSaveSearch moved to before keyboard shortcuts useEffect

  // Ensure share ID exists (lifted from EnhancedResultsDisplay)
  const ensureShareId = useCallback(async () => {
    if (currentShareId) return currentShareId;

    // Prevent duplicate requests
    if (pendingShareRequest.current) {
      return pendingShareRequest.current;
    }

    try {
      const sharePromise = (async () => {
        const token = await user.getIdToken();
        const res = await fetch(`${BACKEND_URL}/share`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            query,
            approach,
            response: response
          })
        });

        if (!res.ok) throw new Error('Failed to create share');

        const data = await res.json();
        const shareId = data.share_id;
        setCurrentShareId(shareId);
        pendingShareRequest.current = null;
        return shareId;
      })();

      pendingShareRequest.current = sharePromise;
      return await sharePromise;
    } catch (error) {
      // Share creation failed — non-critical
      pendingShareRequest.current = null;
      return null;
    }
  }, [currentShareId, query, approach, response, user]);

  // Annotation handlers (centralized in MainApp) - CORRECTED
  const handleAnnotateClick = useCallback(() => {
    if (selectedText && user) {
      // Construct context object so dialog knows it's a highlight
      setCurrentVerse({
        reflectionType: 'highlight',
        highlightedText: selectedText,
        // Use the first verse as context if available, otherwise fallback to query
        queryContext: response?.verses?.[0]
          ? `${response.verses[0].surah}:${response.verses[0].verse_number}`
          : query
      });
      setAnnotationDialogOpen(true);
      ensureShareId().catch(() => {});
    }
  }, [selectedText, user, response, query, ensureShareId]);

  const handleGeneralReflection = useCallback(() => {
    setCurrentVerse({
      reflectionType: 'general',
      queryContext: query
    });
    setAnnotationDialogOpen(true);
    ensureShareId().catch(() => {});
  }, [query, ensureShareId]);

  const handleAnnotationSaved = useCallback(() => {
    setAnnotationDialogOpen(false);
    setCurrentVerse(null);
    setEditingAnnotation(null);
    clearSelection();
    if (!onboardingState.hasUsedAnnotations) {
      markStepComplete('hasUsedAnnotations');
    }
  }, [clearSelection, onboardingState.hasUsedAnnotations, markStepComplete]);

  const handleAnnotationClose = useCallback(() => {
    setAnnotationDialogOpen(false);
    setCurrentVerse(null);
    setEditingAnnotation(null);
    clearSelection();
  }, [clearSelection]);

  const handleSuggestionClick = (suggestionObj) => {
    // Handle both old format (string) and new format (object with query)
    if (typeof suggestionObj === 'string') {
      setQuery(suggestionObj);
    } else {
      setQuery(suggestionObj.query);
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
        button.innerHTML = 'Copied!';
        button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';

        setTimeout(() => {
          button.innerHTML = originalText;
          button.style.background = 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)';
        }, 2000);
      } else {
        throw new Error('Copy command failed');
      }
    } catch (err) {
      // Copy failed — fallback already handled
      document.body.removeChild(textArea);

      // Show error in button
      button.innerHTML = 'Copy Failed';
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
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/share`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
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
            title: `Tafsir Simplified — ${query}`,
            text: 'A deeper understanding of this ayah.',
            url: shareUrl
          });

          button.innerHTML = 'Shared!';
          button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
          if (!onboardingState.hasSharedContent) {
            markStepComplete('hasSharedContent');
          }

          setTimeout(() => {
            button.innerHTML = originalText;
            button.style.background = 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)';
            button.disabled = false;
          }, 2000);
          return;
        } catch (shareErr) {
          // User cancelled - this is normal, just reset button silently
          if (shareErr.name === 'AbortError') {
            button.innerHTML = originalText;
            button.style.background = 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)';
            button.disabled = false;
            return; // Exit gracefully, no error message
          }
          // For other errors, fall through to clipboard
          // Share API unavailable — fall through to clipboard
        }
      }

      // Clipboard API for PWA (works in secure context with user gesture)
      if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
          await navigator.clipboard.writeText(shareUrl);

          button.innerHTML = 'Link Copied!';
          button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
          if (!onboardingState.hasSharedContent) {
            markStepComplete('hasSharedContent');
          }

          setTimeout(() => {
            button.innerHTML = originalText;
            button.style.background = 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)';
            button.disabled = false;
          }, 2000);
        } catch (clipboardErr) {
          // Clipboard API error — textarea fallback will follow
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
            button.innerHTML = 'Link Copied!';
            button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
            if (!onboardingState.hasSharedContent) {
              markStepComplete('hasSharedContent');
            }

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
      // Share link failed — button shows retry

      // Show error in button
      button.innerHTML = 'Share Failed - Tap to retry';
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
    if (!userProfile) return 'Loading...';
    if (userProfile.persona) {
      const personaName = userProfile.persona.split('_').map(word =>
        word.charAt(0).toUpperCase() + word.slice(1)
      ).join(' ');
      return personaName;
    }
    return `${userProfile.level || 'User'} • ${userProfile.focus || 'General'}`;
  };

  const personaIcon = getPersonaIcon(userProfile?.persona || 'practicing_muslim');

  return (
    <>
      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} />

      {/* Badge Popup */}
      {badgePopup && (
        <BadgePopup
          badge={badgePopup}
          onClose={() => setBadgePopup(null)}
        />
      )}

      {/* Persona Change Confirmation */}
      <ConfirmDialog
        isOpen={showPersonaConfirm}
        title="Change Persona"
        message="Would you like to change your learning persona? This will update the style and depth of your tafsir responses."
        confirmText="Change"
        confirmStyle="primary"
        onConfirm={() => { setShowPersonaConfirm(false); onResetProfile?.(); }}
        onCancel={() => setShowPersonaConfirm(false)}
      />

      {/* Desktop Navigation Sidebar */}
      {!isMobile && (
        <DesktopNav
          user={user}
          stats={desktopStats}
          collapsed={navCollapsed}
          onToggleCollapse={() => setNavCollapsed(!navCollapsed)}
        />
      )}

      <div className={`container ${!isMobile ? (navCollapsed ? 'with-sidebar-collapsed' : 'with-sidebar') : ''}`}>
        <div className="card main-app">
        <div className="header">
          <div className="header-logo">
            <TafsirLogo size={32} showText={false} />
            <h1>Tafsir Simplified</h1>
          </div>
          <div className="user-info" data-persona-icon={personaIcon}>
            <span>{user.displayName || user.email?.split('@')[0] || 'User'}</span>
            <button
              className="persona-badge clickable"
              onClick={() => setShowPersonaConfirm(true)}
              title="Click to change persona"
              type="button"
            >
              {getProfileDisplay()}
            </button>
            <button onClick={() => signOut(auth)} className="logout-button">
              Sign Out
            </button>
          </div>
        </div>

        {/* Navigation Links - Desktop Only (compact) */}
        {!isMobile && (
          <div style={{
            display: 'flex',
            gap: '8px',
            marginBottom: '16px',
            justifyContent: 'center'
          }}>
            {[
              { href: '/history', label: 'History' },
              { href: '/saved', label: 'Saved' },
              { href: '/annotations', label: 'Reflections' },
            ].map(link => (
              <a
                key={link.href}
                href={link.href}
                style={{
                  padding: '6px 16px',
                  background: 'var(--cream, #faf6f0)',
                  border: '1px solid var(--border-light)',
                  borderRadius: '8px',
                  color: 'var(--primary-teal)',
                  fontWeight: '600',
                  textDecoration: 'none',
                  fontSize: '0.8rem',
                  transition: 'all 0.2s ease'
                }}
              >
                {link.label}
              </a>
            ))}
          </div>
        )}
        
        {/* Homepage Dashboard — visible when no response is showing */}
        {!response && !isTafsirLoading && (
          <div className="homepage-dashboard">
            {/* Daily Verse — compact clickable card */}
            {dailyVerse && (
              <button
                className="daily-verse-card"
                onClick={() => {
                  setPickerSurah(dailyVerse.surah);
                  setPickerVerse(dailyVerse.verse);
                  setQuery(`${dailyVerse.surah}:${dailyVerse.verse}`);
                  setTimeout(() => {
                    document.querySelector('.tafsir-form')?.requestSubmit();
                  }, 100);
                }}
              >
                <div className="daily-verse-top">
                  <span className="daily-verse-label">Verse of the Day</span>
                  <span className="daily-verse-ref">
                    {dailyVerse.surah_name} {dailyVerse.surah}:{dailyVerse.verse}
                  </span>
                </div>
                {dailyVerse.english_text && (
                  <p className="daily-verse-english">{dailyVerse.english_text}</p>
                )}
                <span className="daily-verse-explore-hint">Tap to explore →</span>
              </button>
            )}

            {/* Themed Collections Grid */}
            <CollectionsGrid user={user} onStudyVerse={handleStudyVerse} />

            <style jsx>{`
              .homepage-dashboard {
                margin-bottom: 16px;
              }
              .daily-verse-card {
                width: 100%;
                padding: 16px 20px;
                background: linear-gradient(135deg, #f0fdf4 0%, #f0f9ff 100%);
                border: 1px solid #d1fae5;
                border-radius: 14px;
                text-align: left;
                cursor: pointer;
                transition: all 0.2s ease;
                display: flex;
                flex-direction: column;
                gap: 8px;
                margin-bottom: 16px;
                font-family: inherit;
              }
              .daily-verse-card:hover {
                border-color: var(--primary-teal, #0d9488);
                box-shadow: 0 2px 12px rgba(13, 148, 136, 0.1);
              }
              .daily-verse-top {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
              }
              .daily-verse-label {
                text-transform: uppercase;
                font-size: 0.65rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                color: var(--primary-teal, #0d9488);
                background: rgba(13, 148, 136, 0.08);
                padding: 3px 8px;
                border-radius: 4px;
              }
              .daily-verse-ref {
                font-size: 0.78rem;
                color: #64748b;
                font-weight: 600;
              }
              .daily-verse-english {
                font-size: 0.85rem;
                color: #374151;
                line-height: 1.5;
                font-style: italic;
                margin: 0;
              }
              .daily-verse-explore-hint {
                font-size: 0.75rem;
                color: var(--primary-teal, #0d9488);
                font-weight: 600;
                align-self: flex-end;
              }
            `}</style>
          </div>
        )}

        {/* Surah/Verse Picker */}
        <SurahVersePicker
          onSelect={(queryStr) => {
            setQuery(queryStr);
            // Auto-submit after selection
            setTimeout(() => {
              document.querySelector('.tafsir-form')?.requestSubmit();
            }, 100);
          }}
          externalSurah={pickerSurah}
          externalVerse={pickerVerse}
        />

        {/* Hidden form - auto-submitted by SurahVersePicker */}
        <form onSubmit={handleGetTafsir} className="tafsir-form" style={{ display: 'none' }}>
          <input type="hidden" value={query} readOnly />
        </form>
        
        {rateLimitWarning && (
          <div className="rate-limit-warning">
            {rateLimitWarning}
          </div>
        )}
        
        {error && <p className="error">{error}</p>}
        {isTafsirLoading && (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div className="loading-spinner"></div>
            <p style={{ color: 'var(--text-secondary, #6b7280)', marginTop: '12px', fontSize: '0.95rem' }}>
              Preparing your tafsir...
            </p>
          </div>
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
            {/* Sticky Result Navigation with Save & Share */}
            <div style={{
              position: 'sticky',
              top: 'calc(env(safe-area-inset-top) + 56px)',
              zIndex: 'var(--z-sticky, 200)',
              background: 'white',
              borderBottom: '1px solid var(--border-light)',
              padding: '10px 16px',
              marginBottom: '20px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderRadius: '12px',
              gap: '8px',
            }}>
              {/* Left: Back button */}
              <button
                onClick={() => {
                  if (abortControllerRef.current) {
                    abortControllerRef.current.abort();
                  }
                  setIsTafsirLoading(false);
                  setResponse(null);
                  setError('');
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                style={{
                  padding: '7px 14px',
                  background: 'var(--primary-teal)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '0.82rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  transition: 'all 0.2s ease',
                  flexShrink: 0,
                }}
                onMouseEnter={e => { e.currentTarget.style.opacity = '0.85'; }}
                onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
                title={!isMobile ? 'Back (Esc)' : 'Back'}
              >
                ←
                {isTafsirLoading ? ' Stop' : ' Back'}
                {!isMobile && <kbd style={{
                  background: 'rgba(255,255,255,0.2)',
                  padding: '1px 5px',
                  borderRadius: '3px',
                  fontSize: '0.7rem',
                }}>Esc</kbd>}
              </button>

              {/* Center: Query label */}
              <div style={{
                fontSize: '0.8rem',
                color: '#555',
                fontWeight: '600',
                padding: '4px 10px',
                background: 'var(--cream)',
                borderRadius: '6px',
                border: '1px solid var(--border-light)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                minWidth: 0,
              }}>
                {query.substring(0, 20)}{query.length > 20 ? '…' : ''}
              </div>

              {/* Right: Save & Share actions */}
              <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                <button onClick={handleSaveSearch} style={{
                  padding: '6px 12px',
                  background: 'var(--cream, #faf6f0)',
                  border: '1px solid var(--border-light, #e5e7eb)',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: '600',
                  color: 'var(--primary-teal, #0d9488)',
                  fontSize: '0.78rem',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(13,148,136,0.08)'; e.currentTarget.style.borderColor = 'var(--primary-teal, #0d9488)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'var(--cream, #faf6f0)'; e.currentTarget.style.borderColor = 'var(--border-light, #e5e7eb)'; }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                  Save
                </button>
                <button onClick={handleShareLink} style={{
                  padding: '6px 12px',
                  background: 'var(--cream, #faf6f0)',
                  border: '1px solid var(--border-light, #e5e7eb)',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: '600',
                  color: 'var(--primary-teal, #0d9488)',
                  fontSize: '0.78rem',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(13,148,136,0.08)'; e.currentTarget.style.borderColor = 'var(--primary-teal, #0d9488)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'var(--cream, #faf6f0)'; e.currentTarget.style.borderColor = 'var(--border-light, #e5e7eb)'; }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
                  Share
                </button>
              </div>
            </div>

            <ErrorBoundary>
            <EnhancedResultsDisplay
              data={response}
              user={user}
              query={query}
              approach={approach}
              onQueryChange={(newQuery) => {
                setQuery(newQuery);
                // Parse verse ref (e.g., "7:189") and sync the dropdown
                const match = newQuery.match(/^(\d+):(\d+)/);
                if (match) {
                  setPickerSurah(parseInt(match[1]));
                  setPickerVerse(parseInt(match[2]));
                }
                // Auto-submit the form after setting the query
                setTimeout(() => {
                  const formElement = document.querySelector('.tafsir-form');
                  if (formElement) {
                    formElement.requestSubmit();
                  }
                }, 100);
              }}
              // NEW PROPS - Functions
              handleSaveSearch={handleSaveSearch}
              handleShareLink={handleShareLink}
              ensureShareId={ensureShareId}
              // NEW PROPS - Annotation state
              annotations={annotations}
              setAnnotations={setAnnotations}
              annotationDialogOpen={annotationDialogOpen}
              setAnnotationDialogOpen={setAnnotationDialogOpen}
              currentVerse={currentVerse}
              setCurrentVerse={setCurrentVerse}
              editingAnnotation={editingAnnotation}
              setEditingAnnotation={setEditingAnnotation}
              inlineAnnotationVerse={inlineAnnotationVerse}
              setInlineAnnotationVerse={setInlineAnnotationVerse}
              currentShareId={currentShareId}
              // NEW PROPS - Text selection
              selectedText={selectedText}
              clearSelection={clearSelection}
              // NEW PROPS - Handlers
              onAnnotateClick={handleAnnotateClick}
              onAnnotationSaved={handleAnnotationSaved}
              onAnnotationClose={handleAnnotationClose}
              onGeneralReflection={handleGeneralReflection}
            />
            </ErrorBoundary>
          </>
        )}
      </div>


        {/* Bottom Navigation for PWA */}
        <BottomNav user={user} />

        {/* Feature Intro Modal (first-time users) */}
        <FeatureIntroModal
          isOpen={showFeatureIntro}
          onComplete={() => {
            setShowFeatureIntro(false);
            markFeatureIntroSeen();
          }}
          userName={user.displayName || null}
        />

        {/* Help Menu */}
        <HelpMenu
          currentPage={response ? 'results' : 'home'}
          isOpen={helpMenuOpen}
          onClose={() => setHelpMenuOpen(false)}
          onReplayFeatureIntro={() => setShowFeatureIntro(true)}
          user={user}
        />

        {/* Floating Help Button */}
        <FloatingHelpButton onClick={() => setHelpMenuOpen(true)} />

        {/* Floating Annotate Button - appears when text is selected */}
        {selectedText && user && (
          <FloatingAnnotateButton
            selectedText={selectedText}
            onAnnotate={handleAnnotateClick}
            onDismiss={clearSelection}
          />
        )}

        {/* Unified Annotation Dialog for all annotation types */}
        <AnnotationDialog
          isOpen={annotationDialogOpen}
          onClose={handleAnnotationClose}
          selectedText={currentVerse?.highlightedText}
          verse={currentVerse}
          user={user}
          reflectionType={currentVerse?.reflectionType || 'verse'}
          onSaved={handleAnnotationSaved}
          existingAnnotation={editingAnnotation}
          sectionName={currentVerse?.sectionName}
          queryContext={currentVerse?.queryContext || query}
          shareId={currentShareId}
        />

        {/* Folder Picker Dialog */}
        {showFolderPicker && (
          <>
            <div
              onClick={() => setShowFolderPicker(false)}
              style={{
                position: 'fixed', inset: 0,
                background: 'rgba(0,0,0,0.4)',
                zIndex: 9000,
              }}
            />
            <div style={{
              position: 'fixed',
              bottom: 0, left: 0, right: 0,
              background: 'var(--cream, #faf6f0)',
              borderRadius: '16px 16px 0 0',
              padding: '20px 20px 32px',
              zIndex: 9001,
              maxHeight: '60vh',
              overflowY: 'auto',
              boxShadow: '0 -4px 20px rgba(0,0,0,0.15)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <h3 style={{ margin: 0, fontSize: '1.05rem', color: 'var(--deep-blue, #1e3a5f)' }}>Save to Folder</h3>
                <button
                  onClick={() => setShowFolderPicker(false)}
                  style={{ background: 'none', border: 'none', fontSize: '1.1rem', color: '#6b7280', cursor: 'pointer' }}
                >
                  x
                </button>
              </div>

              {/* Existing folders */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 16 }}>
                <button
                  onClick={() => doSaveToFolder('Uncategorized')}
                  style={{
                    padding: '10px 14px',
                    background: 'white',
                    border: '1px solid var(--border-light, #e5e7eb)',
                    borderRadius: 8,
                    textAlign: 'left',
                    fontSize: '0.9rem',
                    cursor: 'pointer',
                    color: 'var(--foreground, #2c3e50)',
                  }}
                >
                  Uncategorized
                </button>
                {existingFolders.filter(f => f !== 'Uncategorized').map(folder => (
                  <button
                    key={folder}
                    onClick={() => doSaveToFolder(folder)}
                    style={{
                      padding: '10px 14px',
                      background: 'white',
                      border: '1px solid var(--border-light, #e5e7eb)',
                      borderRadius: 8,
                      textAlign: 'left',
                      fontSize: '0.9rem',
                      cursor: 'pointer',
                      color: 'var(--foreground, #2c3e50)',
                    }}
                  >
                    {folder}
                  </button>
                ))}
              </div>

              {/* Create new folder */}
              <div style={{ borderTop: '1px solid var(--border-light, #e5e7eb)', paddingTop: 12 }}>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 6 }}>
                  Create new folder
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    type="text"
                    value={newFolderName}
                    onChange={(e) => setNewFolderName(e.target.value)}
                    placeholder="Folder name..."
                    maxLength={40}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      border: '1px solid var(--border-light, #e5e7eb)',
                      borderRadius: 8,
                      fontSize: '0.9rem',
                      outline: 'none',
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && newFolderName.trim()) {
                        doSaveToFolder(newFolderName.trim());
                      }
                    }}
                  />
                  <button
                    onClick={() => newFolderName.trim() && doSaveToFolder(newFolderName.trim())}
                    disabled={!newFolderName.trim()}
                    style={{
                      padding: '8px 16px',
                      background: newFolderName.trim() ? 'var(--primary-teal, #0d9488)' : '#e5e7eb',
                      color: newFolderName.trim() ? 'white' : '#9ca3af',
                      border: 'none',
                      borderRadius: 8,
                      fontSize: '0.85rem',
                      fontWeight: 600,
                      cursor: newFolderName.trim() ? 'pointer' : 'not-allowed',
                    }}
                  >
                    Save
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </>
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
    { value: 'personal_insight', label: 'Insight' },
    { value: 'question', label: 'Question' },
    { value: 'application', label: 'Application' },
    { value: 'memory', label: 'Memory' },
    { value: 'connection', label: 'Connection' },
    { value: 'dua', label: 'Dua/Prayer' },
    { value: 'gratitude', label: 'Gratitude' },
    { value: 'reminder', label: 'Reminder' },
    { value: 'story', label: 'Story/Example' },
    { value: 'linguistic', label: 'Linguistic Note' },
    { value: 'historical', label: 'Historical Context' },
    { value: 'scientific', label: 'Scientific Reflection' },
    { value: 'personal_experience', label: 'Personal Experience' },
    { value: 'teaching_point', label: 'Teaching Point' },
    { value: 'warning', label: 'Warning/Caution' },
    { value: 'goal', label: 'Goal/Action Item' },
    { value: 'contemplation', label: 'Deep Contemplation' },
    { value: 'custom', label: 'Custom' }
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
              Suggested tags based on your reflection:
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
          {isSaving ? 'Saving...' : 'Save Reflection'}
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

function EnhancedResultsDisplay({
  data,
  user,
  query,
  approach,
  onQueryChange,
  // NEW PROPS - Functions
  handleSaveSearch,
  handleShareLink,
  ensureShareId,
  // NEW PROPS - Annotation state
  annotations,
  setAnnotations,
  annotationDialogOpen,
  setAnnotationDialogOpen,
  currentVerse,
  setCurrentVerse,
  editingAnnotation,
  setEditingAnnotation,
  inlineAnnotationVerse,
  setInlineAnnotationVerse,
  currentShareId,
  // NEW PROPS - Text selection
  selectedText,
  clearSelection,
  // NEW PROPS - Handlers
  onAnnotateClick,
  onAnnotationSaved,
  onAnnotationClose,
  onGeneralReflection
}) {
  // All state and hooks now come from MainApp via props
  // Local state and useTextSelection hook removed

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
      // Annotation fetch failed — non-critical
    }
  }, [user, setAnnotations]);

  // Extract data properties
  const {
    verses = [],
    tafsir_explanations = [],
    cross_references = [],
    hadith = [],
    lessons_practical_applications = [],
    summary = '',
    scholarly_sources = [],
  } = data || {};

  // Fetch annotations for all verses when component mounts
  useEffect(() => {
    if (verses.length > 0 && user) {
      verses.forEach(verse => {
        fetchVerseAnnotations(verse.surah, verse.verse_number);
      });
    }
  }, [verses, user, fetchVerseAnnotations]);

  // ensureShareId now comes from MainApp as a prop - removed local duplicate

  // Early return after all hooks
  if (!data) return <div className="results-container" role="region" aria-label="Search results"><p>No results to display.</p></div>;

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
    setAnnotationDialogOpen(true);
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
      // Annotation delete failed — non-critical
    }
  };

  const handleAnnotationSaved = () => {
    // Refresh annotations for current verse
    if (currentVerse) {
      fetchVerseAnnotations(currentVerse.surah, currentVerse.verse_number);
      setInlineAnnotationVerse(null); // Close inline form after saving
    }
    // Clear any active text selection
    clearSelection();
  };

  if (verses.length === 0 && tafsir_explanations.length === 0 && lessons_practical_applications.length === 0) {
    return (
      <div className="results-container" role="region" aria-label="Search results" aria-live="polite">
        <p style={{ textAlign: 'center', fontSize: '1.1rem', color: '#666' }}>
          No relevant information found in the source text for your query.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="results-container">

      <TabNavigation
        resetKey={query}  // Reset to first tab (verses) on new query
        tabs={[
          // Verses Tab
          verses.length > 0 && {
            label: verses.length === 1 ? 'Verse' : 'Verses',
            icon: '',
            content: (
              <div className="verses-section">
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
            )
          },

          // Tafsir Tab (includes related verses)
          tafsir_explanations.length > 0 && {
            label: 'Tafsir',
            icon: '',
            sectionName: 'Tafsir Explanations',
            content: (
              <div className="tafsir-section">
          {tafsir_explanations.map((tafsir, index) => (
            <details key={index} className="tafsir-details enhanced" open>
              <summary>
                <strong>{tafsir.source}</strong>
                {tafsir.explanation.includes('Limited relevant content') && (
                  <span className="limited-content-badge">Limited Content</span>
                )}
              </summary>
              <div className="explanation-content markdown-content">
                <ReactMarkdown remarkPlugins={[remarkBreaks]}>
                  {tafsir.explanation}
                </ReactMarkdown>
              </div>
            </details>
          ))}

                {/* Related Verses embedded within Tafsir tab */}
                {cross_references.length > 0 && (
                  <div style={{ marginTop: '24px' }}>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '12px' }}>
                      {cross_references.length === 1 ? 'Related Verse' : 'Related Verses'}
                    </h3>
          <div className="cross-references">
            {cross_references.map((ref, index) => (
              <div key={index} className="cross-ref-item">
                <button
                  onClick={() => {
                    // Navigate to the Tafsir of the related verse
                    if (onQueryChange) {
                      onQueryChange(ref.verse);
                    }
                  }}
                  style={{
                    background: 'none',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    cursor: 'pointer',
                    textAlign: 'left',
                    width: '100%',
                    transition: 'all 0.2s',
                    marginBottom: '8px'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#f7fafc';
                    e.currentTarget.style.borderColor = '#cbd5e0';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'none';
                    e.currentTarget.style.borderColor = '#e2e8f0';
                  }}
                  title={`Click to view Tafsir of verse ${ref.verse}`}
                >
                  <strong style={{ color: '#4a5568' }}>{ref.verse}</strong>
                  <span style={{ color: '#718096', display: 'block', marginTop: '4px' }}>
                    {ref.relevance}
                  </span>
                </button>
              </div>
            ))}
          </div>
                  </div>
                )}

                {/* Hadith section - separate from Related Verses */}
                {hadith.length > 0 && (
                  <div style={{ marginTop: '24px' }}>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '12px' }}>
                      Hadith
                    </h3>
                    <div className="hadith-references" style={{ display: 'grid', gap: '12px' }}>
                      {hadith.map((h, index) => (
                        <div
                          key={index}
                          style={{
                            background: '#fef3c7',
                            border: '1px solid #fbbf24',
                            borderRadius: '8px',
                            padding: '12px',
                          }}
                        >
                          <div style={{ fontWeight: '600', color: '#92400e', marginBottom: '8px' }}>
                            {h.reference}
                          </div>
                          {h.text && (
                            <div style={{
                              fontStyle: 'italic',
                              color: '#78350f',
                              marginBottom: '8px',
                              lineHeight: '1.6'
                            }}>
                              &quot;{h.text}&quot;
                            </div>
                          )}
                          <div style={{ color: '#78350f', fontSize: '0.9rem' }}>
                            {h.relevance}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Reflection Prompt — once, at end of Tafsir section */}
                {data.reflection_prompt && user && (
                  <div style={{
                    display: 'flex',
                    gap: '12px',
                    padding: '14px 16px',
                    marginTop: '20px',
                    background: 'linear-gradient(135deg, #faf5ff 0%, #f3e8ff 50%, #ede9fe 100%)',
                    border: '1px solid #ddd6fe',
                    borderRadius: '12px',
                  }}>
                    <div style={{ flex: 1 }}>
                      <p style={{
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        color: '#7c3aed',
                        margin: '0 0 6px 0',
                      }}>Reflection</p>
                      <p style={{
                        fontSize: '0.92rem',
                        color: '#374151',
                        lineHeight: 1.6,
                        margin: '0 0 12px 0',
                      }}>{data.reflection_prompt}</p>
                      <button
                        onClick={() => {
                          setCurrentVerse({
                            reflectionType: 'general',
                            queryContext: query,
                            prefillPrompt: data.reflection_prompt
                          });
                          setAnnotationDialogOpen(true);
                          ensureShareId().catch(() => {});
                        }}
                        style={{
                          padding: '8px 18px',
                          background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                          color: 'white',
                          border: 'none',
                          borderRadius: '20px',
                          fontWeight: 600,
                          fontSize: '0.82rem',
                          cursor: 'pointer',
                        }}
                      >
                        Reflect
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          },

          // Lessons Tab
          lessons_practical_applications.length > 0 && {
            label: lessons_practical_applications.length === 1 ? 'Lesson' : 'Lessons',
            icon: '',
            sectionName: 'Lessons & Practical Applications',
            content: (
              <div className="lessons-section">
          <div style={{ display: 'grid', gap: '16px' }}>
            {lessons_practical_applications.map((lesson, index) => (
              <div
                key={index}
                style={{
                  background: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '12px',
                  padding: '16px',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
                }}
              >
                <div style={{
                  fontWeight: '700',
                  fontSize: '1rem',
                  color: 'var(--primary-teal)',
                  marginBottom: '12px'
                }}>
                  {lesson.point}
                </div>

                {/* Synthesis type: single narrative body */}
                {lesson.type === 'synthesis' && lesson.body && (
                  <div style={{
                    background: '#f0f9ff',
                    borderLeft: '3px solid #0ea5e9',
                    padding: '12px 14px',
                    borderRadius: '4px',
                    fontSize: '0.95rem',
                    color: '#0c4a6e',
                    lineHeight: '1.7'
                  }}>
                    {lesson.body}
                  </div>
                )}

                {/* Contemplation type: principle + question + anchor */}
                {lesson.type === 'contemplation' && (
                  <div style={{ display: 'grid', gap: '10px' }}>
                    {lesson.core_principle && (
                      <div style={{
                        background: '#f0fdf4',
                        borderLeft: '3px solid #10b981',
                        padding: '10px 12px',
                        borderRadius: '4px'
                      }}>
                        <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#059669', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Core Principle
                        </div>
                        <div style={{ fontSize: '0.95rem', color: '#065f46', lineHeight: '1.6' }}>
                          {lesson.core_principle}
                        </div>
                      </div>
                    )}
                    {lesson.contemplation && (
                      <div style={{
                        background: '#faf5ff',
                        borderLeft: '3px solid #a855f7',
                        padding: '10px 12px',
                        borderRadius: '4px'
                      }}>
                        <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#7c3aed', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Contemplation
                        </div>
                        <div style={{ fontSize: '0.95rem', color: '#4c1d95', lineHeight: '1.6', fontStyle: 'italic' }}>
                          {lesson.contemplation}
                        </div>
                      </div>
                    )}
                    {lesson.prophetic_anchor && (
                      <div style={{
                        background: '#fefce8',
                        borderLeft: '3px solid #eab308',
                        padding: '10px 12px',
                        borderRadius: '4px'
                      }}>
                        <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#ca8a04', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Prophetic Anchor
                        </div>
                        <div style={{ fontSize: '0.95rem', color: '#713f12', lineHeight: '1.6' }}>
                          {lesson.prophetic_anchor}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Progression type: baseline → ascent → peak */}
                {lesson.type === 'progression' && (
                  <div style={{ display: 'grid', gap: '10px' }}>
                    {lesson.baseline && (
                      <div style={{
                        background: '#f8fafc',
                        borderLeft: '3px solid #94a3b8',
                        padding: '10px 12px',
                        borderRadius: '4px'
                      }}>
                        <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#64748b', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          The Baseline
                        </div>
                        <div style={{ fontSize: '0.95rem', color: '#334155', lineHeight: '1.6' }}>
                          {lesson.baseline}
                        </div>
                      </div>
                    )}
                    {lesson.ascent && (
                      <div style={{
                        background: '#eff6ff',
                        borderLeft: '3px solid #3b82f6',
                        padding: '10px 12px',
                        borderRadius: '4px'
                      }}>
                        <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#2563eb', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          The Ascent
                        </div>
                        <div style={{ fontSize: '0.95rem', color: '#1e3a5f', lineHeight: '1.6' }}>
                          {lesson.ascent}
                        </div>
                      </div>
                    )}
                    {lesson.peak && (
                      <div style={{
                        background: '#fdf4ff',
                        borderLeft: '3px solid #d946ef',
                        padding: '10px 12px',
                        borderRadius: '4px'
                      }}>
                        <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#c026d3', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          The Peak
                        </div>
                        <div style={{ fontSize: '0.95rem', color: '#701a75', lineHeight: '1.6' }}>
                          {lesson.peak}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Fallback for old format or untyped lessons */}
                {!lesson.type && (
                  <>
                    {lesson.example && (
                      <div style={{
                        background: '#f0fdf4',
                        borderLeft: '3px solid #10b981',
                        padding: '10px 12px',
                        marginBottom: '12px',
                        borderRadius: '4px'
                      }}>
                        <div style={{ fontSize: '0.9rem', color: '#065f46', lineHeight: '1.6' }}>
                          {lesson.example}
                        </div>
                      </div>
                    )}
                    {lesson.action && (
                      <div style={{
                        background: '#fefce8',
                        borderLeft: '3px solid #eab308',
                        padding: '10px 12px',
                        borderRadius: '4px'
                      }}>
                        <div style={{ fontSize: '0.9rem', color: '#713f12', lineHeight: '1.6' }}>
                          {lesson.action}
                        </div>
                      </div>
                    )}
                    {lesson.body && (
                      <div style={{
                        fontSize: '0.95rem',
                        color: '#374151',
                        lineHeight: '1.7'
                      }}>
                        {lesson.body}
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
              </div>
            )
          },

          // Summary Tab
          summary && {
            label: 'Summary',
            icon: '',
            sectionName: 'Summary',
            content: (
              <div className="summary-section">
          <div className="summary-content">
            <p>{summary}</p>
          </div>
              </div>
            )
          }
        ].filter(Boolean)} // Remove null/false entries
        defaultTab={0}
        storageKey="tafsir-selected-tab"
        onReflect={user ? (sectionName) => {
          setCurrentVerse({ reflectionType: 'section', sectionName, queryContext: query });
          setAnnotationDialogOpen(true);
          ensureShareId().catch(() => {});
        } : null}
        onReflectAll={user ? () => {
          setCurrentVerse({ reflectionType: 'general', queryContext: query });
          setAnnotationDialogOpen(true);
          ensureShareId().catch(() => {});
        } : null}
      />
      </div>

      {/* FloatingAnnotateButton and AnnotationDialog moved to MainApp */}
    </>
  );
}
