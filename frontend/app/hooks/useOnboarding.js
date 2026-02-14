'use client';
import { useState, useEffect } from 'react';

export function useOnboarding(userId) {
  const [onboardingState, setOnboardingState] = useState({
    hasSeenWelcome: false,
    hasSeenFeatureIntro: false,
    hasSearched: false,
    hasUsedAnnotations: false,
    hasViewedSaved: false,
    hasExploredQuestions: false,
    hasSharedContent: false,
    hasViewedHistory: false,
    completedAt: null,
    currentStep: 'welcome',
    tutorialActive: false,
    featureTours: {
      search: false,
      annotations: false,
      explore: false,
      saved: false,
      sharing: false
    }
  });

  const [showTour, setShowTour] = useState(false);
  const [currentTourStep, setCurrentTourStep] = useState(0);
  const [tourType, setTourType] = useState(null);
  const [isLoaded, setIsLoaded] = useState(false); // Track if localStorage has been loaded

  // Load onboarding state from localStorage
  useEffect(() => {
    if (!userId) return;

    const savedState = localStorage.getItem(`onboarding-${userId}`);
    if (savedState) {
      const parsed = JSON.parse(savedState);
      setOnboardingState(parsed);
    }
    // No auto-start of TourOverlay — FeatureIntroModal handles first-time intro
    setIsLoaded(true); // Mark as loaded after processing
  }, [userId]);

  // Save state to localStorage whenever it changes
  useEffect(() => {
    if (userId && isLoaded) {
      localStorage.setItem(`onboarding-${userId}`, JSON.stringify(onboardingState));
    }
  }, [onboardingState, userId, isLoaded]);

  const markStepComplete = (step) => {
    setOnboardingState(prev => ({
      ...prev,
      [step]: true,
      currentStep: getNextStep(step)
    }));
  };

  const startFeatureTour = (feature) => {
    setTourType(feature);
    setShowTour(true);
    setCurrentTourStep(0);
  };

  const endFeatureTour = (feature) => {
    setOnboardingState(prev => ({
      ...prev,
      featureTours: {
        ...prev.featureTours,
        [feature]: true
      }
    }));
    setShowTour(false);
    setTourType(null);
    setCurrentTourStep(0);
  };

  const getNextStep = (currentStep) => {
    const steps = [
      'welcome',
      'search',
      'annotations',
      'explore',
      'saved',
      'complete'
    ];
    const currentIndex = steps.indexOf(currentStep);
    return currentIndex < steps.length - 1 ? steps[currentIndex + 1] : 'complete';
  };

  const isOnboardingComplete = () => {
    return onboardingState.hasSeenWelcome &&
           onboardingState.hasSearched &&
           onboardingState.hasUsedAnnotations;
  };

  const markFeatureIntroSeen = () => {
    setOnboardingState(prev => ({
      ...prev,
      hasSeenFeatureIntro: true,
      hasSeenWelcome: true
    }));
  };

  const resetOnboarding = () => {
    const initialState = {
      hasSeenWelcome: false,
      hasSeenFeatureIntro: false,
      hasSearched: false,
      hasUsedAnnotations: false,
      hasViewedSaved: false,
      hasExploredQuestions: false,
      hasSharedContent: false,
      hasViewedHistory: false,
      completedAt: null,
      currentStep: 'welcome',
      tutorialActive: false,
      featureTours: {
        search: false,
        annotations: false,
        explore: false,
        saved: false,
        sharing: false
      }
    };
    setOnboardingState(initialState);
    if (userId) {
      localStorage.setItem(`onboarding-${userId}`, JSON.stringify(initialState));
    }
  };

  return {
    onboardingState,
    markStepComplete,
    markFeatureIntroSeen,
    startFeatureTour,
    endFeatureTour,
    isOnboardingComplete,
    resetOnboarding,
    showTour,
    setShowTour,
    currentTourStep,
    setCurrentTourStep,
    tourType,
    isLoaded  // Expose loading state to prevent race conditions
  };
}
