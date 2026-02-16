/**
 * Centralized configuration for the Tadabbur app.
 * Import this file instead of hardcoding values.
 */

// Backend API URL - uses environment variable with fallback
export const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://tafsir-backend-612616741510.us-central1.run.app';

// Firebase configuration
export const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "AIzaSyBKPuVvuJC1bTUsZsZkiMHRoBRRqF6YqVU",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "tafsir-simplified-6b262.firebaseapp.com",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "tafsir-simplified-6b262",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "tafsir-simplified-6b262.appspot.com",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "69730898944",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "1:69730898944:web:ee2cbeee72be8d856474e5",
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID || "G-7RZD1G66YH"
};

// App constants
export const APP_CONSTANTS = {
  MAX_VERSE_RANGE: 10,
  SEARCH_TIMEOUT_MS: 45000,
  SEARCH_STATE_EXPIRY_MS: 30 * 60 * 1000, // 30 minutes
  TEXT_SELECTION_DEBOUNCE_MS: 500,
  TEXT_SELECTION_MIN_LENGTH: 3
};

// Persona themes for UI (5 consolidated personas)
export const PERSONA_THEMES = {
  new_revert: {
    gradient: 'linear-gradient(135deg, #10B981 0%, #34D399 100%)',
    color: '#10B981'
  },
  curious_explorer: {
    gradient: 'linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%)',
    color: '#8B5CF6'
  },
  practicing_muslim: {
    gradient: 'linear-gradient(135deg, #0D9488 0%, #14B8A6 100%)',
    color: '#0D9488'
  },
  student: {
    gradient: 'linear-gradient(135deg, #3B82F6 0%, #60A5FA 100%)',
    color: '#3B82F6'
  },
  advanced_learner: {
    gradient: 'linear-gradient(135deg, #1E3A5F 0%, #3B5A7F 100%)',
    color: '#1E3A5F'
  }
};

export const getPersonaTheme = (persona) => {
  return PERSONA_THEMES[persona] || PERSONA_THEMES.practicing_muslim;
};

export const getPersonaIcon = (persona) => {
  // Icons removed - return empty string for compatibility
  return '';
};
