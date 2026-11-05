import { initializeApp, getApps, getApp } from 'firebase/app';
import {
  getAuth,
  RecaptchaVerifier,
  signInWithPhoneNumber,
  signOut,
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

export const isFirebaseConfigured = () => {
  return Boolean(
    firebaseConfig.apiKey &&
    firebaseConfig.apiKey !== 'your-firebase-api-key' &&
    firebaseConfig.projectId &&
    firebaseConfig.projectId !== 'your-firebase-project-id'
  );
};

let app = null;
let auth = null;

if (isFirebaseConfigured()) {
  try {
    app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
    auth = getAuth(app);
  } catch (err) {
    console.warn('[Firebase] Initialization error:', err);
  }
}

export { app, auth };

export const getFirebaseAuth = () => {
  if (!auth && isFirebaseConfigured()) {
    try {
      app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
      auth = getAuth(app);
    } catch (err) {
      console.warn('[Firebase] getFirebaseAuth error:', err);
    }
  }
  return auth;
};

/**
 * Initializes an invisible reCAPTCHA verifier for Firebase Phone Auth.
 * @param {string|HTMLElement} containerId - Element ID or element to mount reCAPTCHA
 */
export const setupRecaptcha = (containerId = 'recaptcha-container') => {
  const currentAuth = getFirebaseAuth();
  if (!currentAuth) {
    throw new Error('Firebase Auth is not configured. Please supply VITE_FIREBASE_* environment variables.');
  }

  // Clear existing verifier on window if any
  if (window.recaptchaVerifier) {
    try {
      window.recaptchaVerifier.clear();
    } catch {
      // Ignore cleanup error
    }
    window.recaptchaVerifier = null;
  }

  window.recaptchaVerifier = new RecaptchaVerifier(currentAuth, containerId, {
    size: 'invisible',
    callback: () => {
      // reCAPTCHA solved
    },
    'expired-callback': () => {
      console.warn('reCAPTCHA expired. Resetting verifier.');
    },
  });

  return window.recaptchaVerifier;
};

/**
 * Requests an SMS verification code (OTP) via Firebase Phone Auth.
 * @param {string} phoneNumber - Full E.164 phone number, e.g. "+919820111222"
 * @param {RecaptchaVerifier} [verifier] - Optional recaptcha verifier
 * @returns {Promise<import('firebase/auth').ConfirmationResult>}
 */
export const sendPhoneOtp = async (phoneNumber, verifier) => {
  const currentAuth = getFirebaseAuth();
  if (!currentAuth) {
    throw new Error('Firebase Auth is not configured. Please supply VITE_FIREBASE_* environment variables.');
  }

  const appVerifier = verifier || window.recaptchaVerifier || setupRecaptcha('recaptcha-container');
  return signInWithPhoneNumber(currentAuth, phoneNumber, appVerifier);
};

/**
 * Confirms OTP code with the confirmationResult returned by sendPhoneOtp.
 * @param {import('firebase/auth').ConfirmationResult} confirmationResult
 * @param {string} otpCode
 * @returns {Promise<import('firebase/auth').UserCredential>}
 */
export const verifyPhoneOtp = async (confirmationResult, otpCode) => {
  if (!confirmationResult || typeof confirmationResult.confirm !== 'function') {
    throw new Error('Invalid or missing confirmation session');
  }
  return confirmationResult.confirm(otpCode);
};

/**
 * Retrieves the current Firebase user's fresh ID token (auto-refreshed).
 * @param {boolean} forceRefresh
 * @returns {Promise<string|null>}
 */
export const getFreshIdToken = async (forceRefresh = false) => {
  const currentAuth = getFirebaseAuth();
  if (!currentAuth?.currentUser) {
    return null;
  }
  try {
    return await currentAuth.currentUser.getIdToken(forceRefresh);
  } catch (err) {
    console.warn('[Firebase] Failed to fetch fresh ID token:', err);
    return null;
  }
};

/**
 * Signs out the current Firebase user.
 */
export const signOutFirebase = async () => {
  const currentAuth = getFirebaseAuth();
  if (currentAuth) {
    try {
      await signOut(currentAuth);
    } catch (err) {
      console.warn('[Firebase] signOut error:', err);
    }
  }
};

