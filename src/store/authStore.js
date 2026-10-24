import { create } from 'zustand';
import { storage } from '../lib/storage';
import { ROLES } from '../types';
import { INITIAL_CUSTOMER, INITIAL_WORKER, SEED_WORKERS } from '../api/mockData';
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
  loginAsCustomer: (userData) => {
    const customerUser = {
      uid: userData?.uid || `cust_${Date.now()}`,
      name: userData?.name || 'Priya Sharma',
      phone: userData?.phone || '+91 98765 43210',
      role: ROLES.CUSTOMER,
      avatarUrl: userData?.avatarUrl || 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80',
      location: userData?.location || {
        lat: 19.2812,
        lng: 72.8697,
        address: 'B-402, Shanti Park, Mira Road East, Mumbai',
      },
    };

    storage.set(AUTH_ROLE_KEY, ROLES.CUSTOMER);
    storage.set(AUTH_USER_KEY, customerUser);
    localStorage.setItem('rb_auth_token', `token-customer-${customerUser.uid}`);

    set({
      user: customerUser,
      role: ROLES.CUSTOMER,
      isAvailableNow: false,
      pendingOtpPhone: null,
      generatedOtp: null,
    });
    return customerUser;
  },

  // Login as Worker (Strict role enforcement)
  loginAsWorker: (workerData) => {
    // If logging in as an existing seeded worker or new worker
    const matchedSeedWorker = SEED_WORKERS.find(
      (w) => w.phone === workerData?.phone || w.uid === workerData?.uid
    );

    const workerUser = {
      ...(matchedSeedWorker || INITIAL_WORKER),
      ...workerData,
      role: ROLES.WORKER,
    };

    storage.set(AUTH_ROLE_KEY, ROLES.WORKER);
    storage.set(AUTH_USER_KEY, workerUser);
    localStorage.setItem('rb_auth_token', `token-worker-${workerUser.uid}`);

    set({
      user: workerUser,
      role: ROLES.WORKER,
      isAvailableNow: workerUser.isAvailableNow ?? true,
      pendingOtpPhone: null,
      generatedOtp: null,
    });
    return workerUser;
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
