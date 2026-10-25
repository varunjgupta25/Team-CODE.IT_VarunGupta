import { create } from 'zustand';
import { storage } from '../lib/storage';
import { ROLES } from '../types';
import { api } from '../api';

const AUTH_USER_KEY = 'rb_auth_user_session';
const AUTH_ROLE_KEY = 'rb_auth_role_session';

const initialRole = storage.get(AUTH_ROLE_KEY, null);
const initialUser = storage.get(AUTH_USER_KEY, null);

export const useAuthStore = create((set, get) => ({
  user: initialUser,
  role: initialRole,
  isAvailableNow: initialUser?.isAvailableNow ?? true,
  pendingOtpPhone: null,
  generatedOtp: null,

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
    localStorage.setItem('rb_auth_token', `token-customer-${customerUser.uid}`);

    // Dynamic backend customer registration
    try {
      await api.registerCustomer({
        uid: customerUser.uid,
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
      generatedOtp: null,
    });
    return customerUser;
  },

  // Login as Worker (Strict role enforcement, dynamic registration)
  loginAsWorker: async (workerData) => {
    // If specific UID passed (e.g. from quick login or existing worker), use it;
    // otherwise generate a unique UID for dynamically registered worker
    const isExplicitlyVerified = workerData?.verified === true || workerData?.uid === 'worker_plumber_1' || workerData?.uid === 'w_plumb_1';
    const isNewRegistration = !workerData?.uid;
    const workerUid = workerData?.uid || (isExplicitlyVerified ? 'worker_plumber_1' : `worker_${Date.now()}`);
    const skills = workerData?.skills && workerData.skills.length > 0 ? workerData.skills : ['plumber'];
    const rates = workerData?.rates || { [skills[0]]: 350 };
    const isVerified = isExplicitlyVerified;
    const vStatus = isVerified ? 'approved' : (workerData?.verificationStatus || 'unverified');

    const workerUser = {
      uid: workerUid,
      name: workerData?.name || (isVerified ? 'Ramesh Kumar (Verified)' : 'Worker'),
      phone: workerData?.phone || (isVerified ? '+91 91101 00001' : '+91 91101 00005'),
      skills,
      rates,
      role: ROLES.WORKER,
      isAvailableNow: true,
      verified: isVerified,
      verificationStatus: vStatus,
      rating: workerData?.rating ?? 4.5,
      jobsDone: workerData?.jobsDone ?? 0,
      trustScore: isVerified ? 90.0 : 60.0,
      trustBadge: isVerified ? 'Gold' : 'Bronze',
      avatarUrl: workerData?.avatarUrl || 'https://images.unsplash.com/photo-1540569014015-19a7be504e3a?w=150&auto=format&fit=crop&q=80',
      location: workerData?.location || {
        lat: 19.2812,
        lng: 72.8697,
        address: 'Mira Road East, Mumbai',
      },
    };

    storage.set(AUTH_ROLE_KEY, ROLES.WORKER);
    storage.set(AUTH_USER_KEY, workerUser);
    localStorage.setItem('rb_auth_token', `token-worker-${workerUser.uid}`);

    // If dynamically registering a new worker, register with backend
    if (isNewRegistration) {
      try {
        await api.registerWorker({
          uid: workerUser.uid,
          name: workerUser.name,
          phone: workerUser.phone,
          skills: workerUser.skills,
          rates: workerUser.rates,
          location: workerUser.location,
        });
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
    localStorage.setItem('rb_auth_token', 'token-admin-admin_user');

    set({
      user: adminUser,
      role: ROLES.ADMIN,
      isAvailableNow: false,
      pendingOtpPhone: null,
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

  // Fake OTP generation system for phone login
  sendOtp: (phone) => {
    const fakeOtp = '1234'; // Reliable test OTP for instant testing
    set({ pendingOtpPhone: phone, generatedOtp: fakeOtp });
    return fakeOtp;
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

  // Log Out (Completely destroys session so user must re-authenticate)
  logout: () => {
    storage.remove(AUTH_USER_KEY);
    storage.remove(AUTH_ROLE_KEY);
    localStorage.removeItem('rb_auth_token');
    set({
      user: null,
      role: null,
      isAvailableNow: false,
      pendingOtpPhone: null,
      generatedOtp: null,
    });
  },
}));
