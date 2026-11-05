import { create } from 'zustand';
import { storage } from '../lib/storage';
import { ROLES } from '../types';
import { api } from '../api';
import { auth } from '../lib/firebase';
import { signOut, onAuthStateChanged } from 'firebase/auth';
import { useToastStore } from './toastStore';

const AUTH_USER_KEY = 'rb_auth_user_session';
const AUTH_ROLE_KEY = 'rb_auth_role_session';

const initialRole = storage.get(AUTH_ROLE_KEY, null);
const initialUser = storage.get(AUTH_USER_KEY, null);

// Helper: Check if error is network down or 5xx server error
const isNetworkOr5xx = (err) => {
  const status = err?.status || err?.response?.status;
  // Network failures / timeouts have no response status code
  if (!status) return true;
  return status >= 500 && status < 600;
};

// Automatic retry with exponential backoff (max 3 attempts) for network and 5xx only.
// Does NOT auto-retry 4xx; throws immediately.
async function executeWithAutoRetry(fn, maxAttempts = 3, initialDelayMs = 500) {
  let attempt = 0;
  while (attempt < maxAttempts) {
    try {
      return await fn();
    } catch (err) {
      attempt++;
      const status = err?.status || err?.response?.status;
      // Do not auto-retry 4xx; show the error immediately
      if (status && status >= 400 && status < 500) {
        throw err;
      }
      if (attempt < maxAttempts && isNetworkOr5xx(err)) {
        const delay = initialDelayMs * Math.pow(2, attempt - 1);
        await new Promise((resolve) => setTimeout(resolve, delay));
      } else {
        throw err;
      }
    }
  }
}

export const useAuthStore = create((set, get) => ({
  user: initialUser,
  role: initialRole,
  isAvailableNow: initialUser?.isAvailableNow ?? true,

  // Sync status for registration and profile syncing: 'idle' | 'syncing' | 'failed' | 'synced'
  syncStatus: 'idle',
  lastError: null,
  lastSyncAction: null,

  // Login as Customer (Strict role enforcement, with auto-retry and visible error handling)
  // No raw tokens in localStorage - Firebase manages token persistence safely
  loginAsCustomer: async (userData) => {
    // Prevent double submission while a request is in flight
    if (get().syncStatus === 'syncing') return;

    set({
      syncStatus: 'syncing',
      lastError: null,
      lastSyncAction: { type: 'registerCustomer', payload: userData },
    });

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

    try {
      // Automatic retry with exponential backoff for network/5xx; fails fast for 4xx
      await executeWithAutoRetry(() =>
        api.registerCustomer({
          uid: customerUser.uid,
          name: customerUser.name,
          phone: customerUser.phone,
          location: customerUser.location,
        })
      );

      storage.set(AUTH_ROLE_KEY, ROLES.CUSTOMER);
      storage.set(AUTH_USER_KEY, customerUser);

      set({
        user: customerUser,
        role: ROLES.CUSTOMER,
        isAvailableNow: false,
        syncStatus: 'synced',
        lastError: null,
        lastSyncAction: null,
      });
      return customerUser;
    } catch (err) {
      const errorMessage = err?.message || 'Failed to register customer on server.';
      set({
        syncStatus: 'failed',
        lastError: errorMessage,
      });
      useToastStore.getState().error(errorMessage);
      throw err;
    }
  },

  // Login as Worker (Strict role enforcement, dynamic registration with auto-retry)
  // No raw tokens in localStorage - Firebase manages token persistence safely
  loginAsWorker: async (workerData) => {
    // Prevent double submission while a request is in flight
    if (get().syncStatus === 'syncing') return;

    set({
      syncStatus: 'syncing',
      lastError: null,
      lastSyncAction: { type: 'registerWorker', payload: workerData },
    });

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
      verificationStatus: workerData?.verificationStatus || 'unverified',
      rating: workerData?.rating ?? null,
      jobsDone: workerData?.jobsDone ?? 0,
      trustScore: workerData?.trustScore ?? null,
      trustBadge: workerData?.trustBadge ?? null,
      avatarUrl: workerData?.avatarUrl || 'https://images.unsplash.com/photo-1540569014015-19a7be504e3a?w=150&auto=format&fit=crop&q=80',
      location: workerData?.location || {
        lat: 19.2812,
        lng: 72.8697,
        address: 'Mira Road East, Mumbai',
      },
    };

    try {
      if (isNewRegistration) {
        await executeWithAutoRetry(() =>
          api.registerWorker({
            uid: workerUser.uid,
            name: workerUser.name,
            phone: workerUser.phone,
            skills: workerUser.skills,
            rates: workerUser.rates,
            location: workerUser.location,
          })
        );
      } else {
        const existing = await executeWithAutoRetry(() => api.getWorker(workerUser.uid));
        if (existing) {
          workerUser.verified = Boolean(existing.verified);
          workerUser.verificationStatus = existing.verificationStatus || (existing.verified ? 'approved' : 'unverified');
          if (existing.trustScore !== undefined) workerUser.trustScore = existing.trustScore;
          if (existing.trustBadge) workerUser.trustBadge = existing.trustBadge;
        }
      }

      storage.set(AUTH_ROLE_KEY, ROLES.WORKER);
      storage.set(AUTH_USER_KEY, workerUser);

      set({
        user: workerUser,
        role: ROLES.WORKER,
        isAvailableNow: true,
        syncStatus: 'synced',
        lastError: null,
        lastSyncAction: null,
      });
      return workerUser;
    } catch (err) {
      const errorMessage = err?.message || 'Failed to register or sync worker on server.';
      set({
        syncStatus: 'failed',
        lastError: errorMessage,
      });
      useToastStore.getState().error(errorMessage);
      throw err;
    }
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

    set({
      user: adminUser,
      role: ROLES.ADMIN,
      isAvailableNow: false,
      syncStatus: 'synced',
      lastError: null,
      lastSyncAction: null,
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

  // Refresh worker profile with auto-retry and visible error handling
  refreshWorkerProfile: async () => {
    const { user, role, syncStatus } = get();
    if (role !== ROLES.WORKER || !user?.uid) return;
    if (syncStatus === 'syncing') return;

    set({
      syncStatus: 'syncing',
      lastError: null,
      lastSyncAction: { type: 'refreshWorkerProfile' },
    });

    try {
      const fresh = await executeWithAutoRetry(() => api.getWorker(user.uid));
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
        set({
          user: updated,
          syncStatus: 'synced',
          lastError: null,
          lastSyncAction: null,
        });
        return updated;
      }
      set({ syncStatus: 'synced', lastError: null, lastSyncAction: null });
    } catch (err) {
      const errorMessage = err?.message || 'Failed to sync worker profile from server.';
      set({
        syncStatus: 'failed',
        lastError: errorMessage,
      });
      useToastStore.getState().error(errorMessage);
      throw err;
    }
  },

  // Re-run the last failed sync or register call
  retryLastSync: async () => {
    const { lastSyncAction, syncStatus } = get();
    if (!lastSyncAction || syncStatus === 'syncing') return;
    if (lastSyncAction.type === 'registerCustomer') {
      return get().loginAsCustomer(lastSyncAction.payload);
    }
    if (lastSyncAction.type === 'registerWorker') {
      return get().loginAsWorker(lastSyncAction.payload);
    }
    if (lastSyncAction.type === 'refreshWorkerProfile') {
      return get().refreshWorkerProfile();
    }
  },

  // Synchronize and restore session on page reload using Firebase onAuthStateChanged
  initAuthListener: () => {
    if (!auth) return () => {};
    return onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        const current = get().user;
        const role = get().role || storage.get(AUTH_ROLE_KEY, ROLES.CUSTOMER);
        if (!current) {
          const cachedUser = storage.get(AUTH_USER_KEY, null);
          const user = cachedUser || {
            uid: firebaseUser.uid,
            name: firebaseUser.displayName || 'User',
            phone: firebaseUser.phoneNumber || '',
            role,
            verified: false,
            verificationStatus: 'unverified',
          };
          set({ user, role });
        }
      } else {
        // Firebase user signed out: clean up session unless using admin bypass
        const current = get().user;
        if (current && current.role !== ROLES.ADMIN && !import.meta.env.VITE_USE_MOCK) {
          storage.remove(AUTH_USER_KEY);
          storage.remove(AUTH_ROLE_KEY);
          set({ user: null, role: null });
        }
      }
    });
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
    } catch {
      useToastStore.getState().error('Failed to update availability on server.');
    }
  },

  // Log Out: Signs out of Firebase SDK, clears store state, cleans storage
  logout: async () => {
    try {
      if (auth) {
        await signOut(auth);
      }
    } catch (err) {
      console.warn('[Auth] Firebase sign-out notice:', err);
    }
    storage.remove(AUTH_USER_KEY);
    storage.remove(AUTH_ROLE_KEY);
    set({
      user: null,
      role: null,
      isAvailableNow: false,
      syncStatus: 'idle',
      lastError: null,
      lastSyncAction: null,
    });
  },
}));
