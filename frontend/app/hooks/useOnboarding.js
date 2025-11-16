'use client';
import { useState, useEffect } from 'react';

export function useOnboarding(userId) {
  const [onboardingState, setOnboardingState] = useState({
    hasSeenWelcome: false,
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

  // Load onboarding state from localStorage
  useEffect(() => {
    if (!userId) return;

    const savedState = localStorage.getItem(`onboarding-${userId}`);
    if (savedState) {
      setOnboardingState(JSON.parse(savedState));
    } else {
      // First time user - show welcome tour
      setShowTour(true);
      setTourType('welcome');
    }
  }, [userId]);

  // Save state to localStorage whenever it changes
  useEffect(() => {
    if (userId) {
      localStorage.setItem(`onboarding-${userId}`, JSON.stringify(onboardingState));
    }
  }, [onboardingState, userId]);

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

  const resetOnboarding = () => {
    const initialState = {
      hasSeenWelcome: false,
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
    setShowTour(true);
    setTourType('welcome');
  };

  return {
    onboardingState,
    markStepComplete,
    startFeatureTour,
    endFeatureTour,
    isOnboardingComplete,
    resetOnboarding,
    showTour,
    setShowTour,
    currentTourStep,
    setCurrentTourStep,
    tourType
  };
}