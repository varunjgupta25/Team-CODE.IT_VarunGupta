import { create } from 'zustand';
import { storage } from '../lib/storage';
import { ROLES } from '../types';
import { api } from '../api';
import {
  isFirebaseConfigured,
  setupRecaptcha,
  sendPhoneOtp,
  verifyPhoneOtp,
  signOutFirebase,
  getFreshIdToken,
} from '../lib/firebase';

const AUTH_USER_KEY = 'rb_auth_user_session';
const AUTH_ROLE_KEY = 'rb_auth_role_session';

const initialRole = storage.get(AUTH_ROLE_KEY, null);
const initialUser = storage.get(AUTH_USER_KEY, null);

export const useAuthStore = create((set, get) => ({
  user: initialUser,
  role: initialRole,
  isAvailableNow: initialUser?.isAvailableNow ?? true,
  pendingOtpPhone: null,
  confirmationResult: null,
  generatedOtp: null,

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
    const { generatedOtp } = get();
    if (otpCode === (generatedOtp || '1234')) {
      return { uid: `mock_user_${Date.now()}` };
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
    const customerUser = {
      uid: userData?.uid || `cust_${Date.now()}`,
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

    storage.set(AUTH_ROLE_KEY, ROLES.CUSTOMER);
    storage.set(AUTH_USER_KEY, customerUser);
    if (!isFirebaseConfigured()) {
      localStorage.setItem('rb_auth_token', customerUser.uid);
    }

    // Register with backend using fresh Bearer token
    try {
      await api.registerCustomer({
        name: customerUser.name,
        phone: customerUser.phone,
        location: customerUser.location,
      });
    } catch (err) {
      console.warn('Customer sync to backend:', err);
    }

    set({
      user: customerUser,
      role: ROLES.CUSTOMER,
      isAvailableNow: false,
      pendingOtpPhone: null,
      confirmationResult: null,
      generatedOtp: null,
    });
    return customerUser;
  },

  // Login as Worker (Strict role enforcement, dynamic registration)
  loginAsWorker: async (workerData) => {
    const isNewRegistration = !workerData?.uid;
    const workerUid = workerData?.uid || `worker_${Date.now()}`;
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

    storage.set(AUTH_ROLE_KEY, ROLES.WORKER);
    storage.set(AUTH_USER_KEY, workerUser);
    if (!isFirebaseConfigured()) {
      localStorage.setItem('rb_auth_token', workerUser.uid);
    }

    // If registering a new worker, submit registration with backend
    if (isNewRegistration) {
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
          storage.set(AUTH_USER_KEY, workerUser);
        }
      } catch (err) {
        console.warn('Worker sync to backend:', err);
      }
    } else {
      // Fetch fresh profile from backend if existing worker
      try {
        const existing = await api.getWorker(workerUser.uid);
        if (existing) {
          workerUser.verified = Boolean(existing.verified);
          workerUser.verificationStatus = existing.verificationStatus || (existing.verified ? 'approved' : 'unverified');
          if (existing.trustScore !== undefined) workerUser.trustScore = existing.trustScore;
          if (existing.trustBadge) workerUser.trustBadge = existing.trustBadge;
          if (existing.jobsDone !== undefined) workerUser.jobsDone = existing.jobsDone;
          if (existing.rating !== undefined) workerUser.rating = existing.rating;
          storage.set(AUTH_USER_KEY, workerUser);
        }
      } catch {
        // Offline fallback
      }
    }

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

  // Login as Admin
  loginAsAdmin: () => {
    const adminUser = {
      uid: 'admin_user',
      name: 'Super Admin',
      phone: '+91 99999 00000',
      role: ROLES.ADMIN,
      avatarUrl: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&auto=format&fit=crop&q=80',
    };

    storage.set(AUTH_ROLE_KEY, ROLES.ADMIN);
    storage.set(AUTH_USER_KEY, adminUser);
    if (!isFirebaseConfigured()) {
      localStorage.setItem('rb_auth_token', 'admin_user');
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
