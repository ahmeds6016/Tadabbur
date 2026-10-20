/**
 * Centralized Firebase initialization.
 * Import { auth } from this file instead of initializing Firebase in each component.
 */
import { initializeApp, getApps } from 'firebase/app';
import { getAuth, initializeRecaptchaConfig } from 'firebase/auth';
import { firebaseConfig } from './config';

// Initialize Firebase only once
const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
const auth = getAuth(app);
if (typeof window !== 'undefined') {
  initializeRecaptchaConfig(auth).catch(() => {
    // Firebase retries verification during sign-in. Keep protection enabled.
    console.warn('Sign-in verification could not be prepared. Please retry sign-in.');
  });
}

export { app, auth };
