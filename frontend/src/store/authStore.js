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
      verified: true,
      verificationStatus: 'verified',
      rating: 5.0,
      jobsDone: 0,
      trustScore: 90.0,
      trustBadge: 'Gold',
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

    // Dynamic backend registration
    try {
      await api.registerWorker({
        uid: workerUser.uid,
        name: workerUser.name,
        phone: workerUser.phone,
        skills: workerUser.skills,
        rates: workerUser.rates,
        location: workerUser.location,
        avatarUrl: workerUser.avatarUrl,
      });
    } catch (err) {
      console.warn('Worker sync to backend:', err);
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
