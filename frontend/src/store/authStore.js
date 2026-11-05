import { create } from 'zustand';
import { storage } from '../lib/storage.js';
import { ROLES } from '../types/index.js';
import { api } from '../api/index.js';
import {
  isFirebaseConfigured,
  setupRecaptcha,
  sendPhoneOtp,
  verifyPhoneOtp,
  signOutFirebase,
  checkIsFirebaseAdmin,
  subscribeToAuthChanges,
} from '../lib/firebase.js';
import { useJobStore } from './jobStore.js';

const AUTH_USER_KEY = 'rb_auth_user_session';
const AUTH_ROLE_KEY = 'rb_auth_role_session';

const initialRole = storage.get(AUTH_ROLE_KEY, null);
const initialUser = storage.get(AUTH_USER_KEY, null);

export const useAuthStore = create((set, get) => ({
  user: initialUser,
  role: initialRole,
  isInitialized: !isFirebaseConfigured(),
  isAvailableNow: initialUser?.isAvailableNow ?? true,
  pendingOtpPhone: null,
  confirmationResult: null,
  generatedOtp: null,

  // Initialize and synchronize Firebase auth session
  initAuth: () => {
    if (!isFirebaseConfigured()) {
      set({ isInitialized: true });
      return () => {};
    }

    const unsubscribe = subscribeToAuthChanges(async (firebaseUser) => {
      if (firebaseUser) {
        try {
          const freshToken = await firebaseUser.getIdToken();
          localStorage.setItem('rb_auth_token', freshToken);
        } catch {
          // ignore
        }

        const storedUser = storage.get(AUTH_USER_KEY, null);
        const storedRole = storage.get(AUTH_ROLE_KEY, null);

        if (storedUser && storedUser.uid === firebaseUser.uid) {
          set({
            user: storedUser,
            role: storedRole,
            isAvailableNow: storedUser.isAvailableNow ?? true,
            isInitialized: true,
          });
        } else {
          set({ isInitialized: true });
        }
      } else {
        // If Firebase says no user is authenticated, clear token
        if (isFirebaseConfigured() && !initialUser) {
          localStorage.removeItem('rb_auth_token');
          set({ user: null, role: null, isInitialized: true });
        } else {
          set({ isInitialized: true });
        }
      }
    });

    return unsubscribe;
  },

  // Firebase Phone Auth: Request OTP via SMS (or mock fallback if unconfigured)
  requestPhoneOtp: async (phoneNumber, containerId = 'recaptcha-container') => {
    if (isFirebaseConfigured()) {
      try {
        const verifier = setupRecaptcha(containerId);
        const confirmation = await sendPhoneOtp(phoneNumber, verifier);
        set({
          pendingOtpPhone: phoneNumber,
          confirmationResult: confirmation,
          generatedOtp: null,
        });
        return { isFirebase: true, confirmation };
      } catch (err) {
        console.error('[Auth] Firebase sendPhoneOtp failed:', err);
        throw err;
      }
    }

    // Fallback for offline mock development
    const fakeOtp = '1234';
    set({
      pendingOtpPhone: phoneNumber,
      confirmationResult: null,
      generatedOtp: fakeOtp,
    });
    return { isFirebase: false, otp: fakeOtp };
  },

  // Firebase Phone Auth: Confirm OTP and resolve user credentials
  confirmPhoneOtp: async (otpCode) => {
    const { confirmationResult } = get();
    if (confirmationResult && isFirebaseConfigured()) {
      const userCred = await verifyPhoneOtp(confirmationResult, otpCode);
      const idToken = await userCred.user.getIdToken();
      localStorage.setItem('rb_auth_token', idToken);
      return userCred.user;
    }

    // Mock verification fallback
    const { generatedOtp, pendingOtpPhone } = get();
    if (otpCode === (generatedOtp || '1234')) {
      const phoneDigits = pendingOtpPhone ? pendingOtpPhone.replace(/\D/g, '') : 'default';
      return { uid: `mock_user_${phoneDigits}` };
    }
    throw new Error('Invalid OTP code. Please try again.');
  },

  // Legacy helper for test compatibility
  sendOtp: (phone) => {
    const fakeOtp = '1234';
    set({ pendingOtpPhone: phone, generatedOtp: fakeOtp });
    return fakeOtp;
  },

  // Login as Customer (Strict role enforcement)
  loginAsCustomer: async (userData) => {
    const customerUid = userData?.uid || (isFirebaseConfigured() ? null : 'mock_customer_user');
    if (!customerUid) {
      throw new Error('Customer authentication failed: missing user ID.');
    }

    const customerUser = {
      uid: customerUid,
      name: userData?.name || 'Customer',
      phone: userData?.phone || '',
      role: ROLES.CUSTOMER,
      avatarUrl: userData?.avatarUrl || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
      location: userData?.location || {
        lat: 19.2812,
        lng: 72.8697,
        address: 'Mira Road East, Mumbai',
      },
    };

    if (!isFirebaseConfigured()) {
      storage.set(AUTH_ROLE_KEY, ROLES.CUSTOMER);
      storage.set(AUTH_USER_KEY, customerUser);
      localStorage.setItem('rb_auth_token', customerUser.uid);
      set({
        user: customerUser,
        role: ROLES.CUSTOMER,
        isAvailableNow: false,
        pendingOtpPhone: null,
        confirmationResult: null,
        generatedOtp: null,
      });
      return customerUser;
    }

    // Register with backend using fresh Bearer token
    let isReturningUser = false;
    try {
      await api.registerCustomer({
        name: customerUser.name,
        phone: customerUser.phone,
        location: customerUser.location,
      });
    } catch (err) {
      if (err.status === 409 || err.response?.status === 409) {
        // 409 means user already exists in backend.
        // Check if existing account has a different role (Worker)
        try {
          const existingWorker = await api.getWorker(customerUser.uid);
          if (existingWorker) {
            throw new Error('This account is registered as a Service Worker. Please sign in via the Worker Portal.');
          }
        } catch (checkErr) {
          if (checkErr.message?.includes('Worker Portal')) {
            throw checkErr;
          }
          // Not found as worker -> existing customer
        }
        isReturningUser = true;
      } else {
        console.error('[Auth] Customer register failed:', err);
        throw err;
      }
    }

    // Reuse cached profile data if available for returning customer
    const cachedUser = storage.get(AUTH_USER_KEY, null);
    const finalUser = (isReturningUser && cachedUser && cachedUser.uid === customerUser.uid)
      ? { ...customerUser, ...cachedUser, name: customerUser.name || cachedUser.name }
      : customerUser;

    storage.set(AUTH_ROLE_KEY, ROLES.CUSTOMER);
    storage.set(AUTH_USER_KEY, finalUser);

    set({
      user: finalUser,
      role: ROLES.CUSTOMER,
      isAvailableNow: false,
      pendingOtpPhone: null,
      confirmationResult: null,
      generatedOtp: null,
    });
    return finalUser;
  },

  // Login as Worker (Strict role enforcement, dynamic registration)
  loginAsWorker: async (workerData) => {
    const workerUid = workerData?.uid || (isFirebaseConfigured() ? null : 'mock_worker_user');
    if (!workerUid) {
      throw new Error('Worker authentication failed: missing user ID.');
    }

    const skills = workerData?.skills && workerData.skills.length > 0 ? workerData.skills : ['plumber'];
    const rates = workerData?.rates || { [skills[0]]: 350 };

    const workerUser = {
      uid: workerUid,
      name: workerData?.name || 'Worker',
      phone: workerData?.phone || '',
      skills,
      rates,
      role: ROLES.WORKER,
      isAvailableNow: true,
      verified: workerData?.verified ?? false,
      verificationStatus: workerData?.verificationStatus || (workerData?.verified ? 'approved' : 'unverified'),
      rating: workerData?.rating ?? 5.0,
      jobsDone: workerData?.jobsDone ?? 0,
      trustScore: workerData?.trustScore ?? 60.0,
      trustBadge: workerData?.trustBadge ?? 'Bronze',
      avatarUrl: workerData?.avatarUrl || 'https://images.unsplash.com/photo-1540569014015-19a7be504e3a?w=150&auto=format&fit=crop&q=80',
      location: workerData?.location || {
        lat: 19.2812,
        lng: 72.8697,
        address: 'Mira Road East, Mumbai',
      },
    };

    if (!isFirebaseConfigured()) {
      storage.set(AUTH_ROLE_KEY, ROLES.WORKER);
      storage.set(AUTH_USER_KEY, workerUser);
      localStorage.setItem('rb_auth_token', workerUser.uid);
      set({
        user: workerUser,
        role: ROLES.WORKER,
        isAvailableNow: true,
        pendingOtpPhone: null,
        confirmationResult: null,
        generatedOtp: null,
      });
      return workerUser;
    }

    // Try registering new worker with backend
    let isReturningWorker = false;
    try {
      const created = await api.registerWorker({
        name: workerUser.name,
        phone: workerUser.phone,
        skills: workerUser.skills,
        rates: workerUser.rates,
        location: workerUser.location,
      });
      if (created) {
        workerUser.verified = Boolean(created.verified);
        workerUser.verificationStatus = created.verificationStatus || 'unverified';
        workerUser.rating = created.rating ?? 5.0;
        workerUser.jobsDone = created.jobsDone ?? 0;
        workerUser.trustScore = created.trustScore ?? 60.0;
        workerUser.trustBadge = created.trustBadge ?? 'Bronze';
      }
    } catch (err) {
      if (err.status === 409 || err.response?.status === 409) {
        // Worker already exists in backend, or existing account conflict
        isReturningWorker = true;
      } else {
        console.error('[Auth] Worker register failed:', err);
        throw err;
      }
    }

    if (isReturningWorker) {
      // Treat 409 as already registered: load worker profile with api.getWorker(uid)
      try {
        const existing = await api.getWorker(workerUser.uid);
        if (existing) {
          workerUser.name = existing.name || workerUser.name;
          workerUser.skills = existing.skills && existing.skills.length > 0 ? existing.skills : workerUser.skills;
          workerUser.rates = existing.rates || workerUser.rates;
          workerUser.verified = Boolean(existing.verified);
          workerUser.verificationStatus = existing.verificationStatus || (existing.verified ? 'approved' : 'unverified');
          if (existing.trustScore !== undefined) workerUser.trustScore = existing.trustScore;
          if (existing.trustBadge) workerUser.trustBadge = existing.trustBadge;
          if (existing.jobsDone !== undefined) workerUser.jobsDone = existing.jobsDone;
          if (existing.rating !== undefined) workerUser.rating = existing.rating;
          if (existing.location) workerUser.location = existing.location;
        } else {
          // getWorker returned null/empty - user exists as customer!
          throw new Error('This account is registered as a Customer. Please sign in via the Customer Portal.');
        }
      } catch (workerFetchErr) {
        if (workerFetchErr.message?.includes('Customer Portal')) {
          throw workerFetchErr;
        }
        if (workerFetchErr.status === 404 || workerFetchErr.response?.status === 404) {
          throw new Error('This account is registered as a Customer. Please sign in via the Customer Portal.');
        }
        throw workerFetchErr;
      }
    }

    storage.set(AUTH_ROLE_KEY, ROLES.WORKER);
    storage.set(AUTH_USER_KEY, workerUser);

    set({
      user: workerUser,
      role: ROLES.WORKER,
      isAvailableNow: true,
      pendingOtpPhone: null,
      confirmationResult: null,
      generatedOtp: null,
    });
    return workerUser;
  },

  // Login as Admin (Gated by Firebase admin custom claim)
  loginAsAdmin: async (adminData) => {
    const adminUid = adminData?.uid || (isFirebaseConfigured() ? null : 'mock_admin');
    if (!adminUid) {
      throw new Error('Admin authentication failed: missing user ID.');
    }

    if (isFirebaseConfigured()) {
      const isAdmin = await checkIsFirebaseAdmin(true);
      if (!isAdmin) {
        throw new Error('Access denied: This phone number does not have administrator privileges.');
      }
    }

    const adminUser = {
      uid: adminUid,
      name: adminData?.name || 'Super Admin',
      phone: adminData?.phone || '',
      role: ROLES.ADMIN,
      avatarUrl: adminData?.avatarUrl || 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&auto=format&fit=crop&q=80',
    };

    storage.set(AUTH_ROLE_KEY, ROLES.ADMIN);
    storage.set(AUTH_USER_KEY, adminUser);
    if (!isFirebaseConfigured()) {
      localStorage.setItem('rb_auth_token', adminUser.uid);
    }

    set({
      user: adminUser,
      role: ROLES.ADMIN,
      isAvailableNow: false,
      pendingOtpPhone: null,
      confirmationResult: null,
      generatedOtp: null,
    });
    return adminUser;
  },

  // Update current user in store & storage
  updateUser: (updates) => {
    const current = get().user;
    if (!current) return;
    const updated = { ...current, ...updates };
    storage.set(AUTH_USER_KEY, updated);
    set({ user: updated });
    return updated;
  },

  // Refresh worker profile (verification status, rating, etc.)
  refreshWorkerProfile: async () => {
    const { user, role } = get();
    if (role !== ROLES.WORKER || !user?.uid) return;
    try {
      const fresh = await api.getWorker(user.uid);
      if (fresh) {
        const updated = {
          ...user,
          verified: fresh.verified ?? user.verified,
          verificationStatus: fresh.verificationStatus ?? user.verificationStatus,
          rating: fresh.rating ?? user.rating,
          jobsDone: fresh.jobsDone ?? user.jobsDone,
          trustScore: fresh.trustScore ?? user.trustScore,
          trustBadge: fresh.trustBadge ?? user.trustBadge,
        };
        storage.set(AUTH_USER_KEY, updated);
        set({ user: updated });
        return updated;
      }
    } catch {
      // Ignore background refresh failure
    }
  },

  // Worker availability toggle (worker-only)
  toggleAvailability: async () => {
    const { user, role, isAvailableNow } = get();
    if (role !== ROLES.WORKER || !user) return;

    const nextVal = !isAvailableNow;
    set({ isAvailableNow: nextVal });

    const updatedUser = { ...user, isAvailableNow: nextVal };
    storage.set(AUTH_USER_KEY, updatedUser);
    set({ user: updatedUser });

    try {
      await api.updateWorkerAvailability(user.uid, nextVal);
    } catch (err) {
      console.error('Failed to update worker availability:', err);
    }
  },

  // Log Out: Completely destroys session, calls Firebase signOut, and clears local state
  logout: async () => {
    try {
      await signOutFirebase();
    } catch (err) {
      console.warn('Firebase signOut error:', err);
    }
    storage.remove(AUTH_USER_KEY);
    storage.remove(AUTH_ROLE_KEY);
    localStorage.removeItem('rb_auth_token');

    // Clean up job polling & active state
    try {
      useJobStore.getState().stopPolling();
      useJobStore.setState({ currentJob: null, matchedWorkers: [], offers: [], nearbyJobs: [] });
    } catch {
      // safe fallback
    }

    set({
      user: null,
      role: null,
      isAvailableNow: false,
      pendingOtpPhone: null,
      confirmationResult: null,
      generatedOtp: null,
    });
  },
}));
