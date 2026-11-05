import axios from 'axios';
import { auth } from '../lib/firebase';
import { storage } from '../lib/storage';

// One-time migration on app load: delete old raw token keys from localStorage & sessionStorage
if (typeof window !== 'undefined') {
  try {
    localStorage.removeItem('rb_auth_token');
    localStorage.removeItem('rb_otp');
    localStorage.removeItem('token');
    sessionStorage.removeItem('rb_auth_token');
    sessionStorage.removeItem('token');
  } catch {}
}

// Resolve and sanitize backend API Base URL
let rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'https://repair-buddy.onrender.com/api';

if (typeof rawBaseUrl === 'string') {
  // Strip any accidental wrapping quotes
  rawBaseUrl = rawBaseUrl.trim().replace(/^["']|["']$/g, '');
  // If the placeholder <your-render-service> was left unchanged in Vercel, replace it with repair-buddy
  if (rawBaseUrl.includes('<your-render-service>') || rawBaseUrl.includes('<') || rawBaseUrl.includes('your-render-service')) {
    rawBaseUrl = rawBaseUrl
      .replace(/<your-render-service>/g, 'repair-buddy')
      .replace(/your-render-service/g, 'repair-buddy')
      .replace(/<[^>]+>/g, 'repair-buddy');
  }
  // Ensure protocol
  if (!rawBaseUrl.startsWith('http://') && !rawBaseUrl.startsWith('https://')) {
    rawBaseUrl = `https://${rawBaseUrl}`;
  }
  // Ensure /api suffix
  if (!rawBaseUrl.endsWith('/api')) {
    rawBaseUrl = `${rawBaseUrl.replace(/\/+$/, '')}/api`;
  }
}

export const apiClient = axios.create({
  baseURL: rawBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Attach fresh Firebase ID token per request (auto-refreshed by the Firebase Web SDK)
// No raw tokens stored or read from localStorage/sessionStorage
apiClient.interceptors.request.use(
  async (config) => {
    if (auth?.currentUser) {
      try {
        const idToken = await auth.currentUser.getIdToken();
        if (idToken) {
          config.headers.Authorization = `Bearer ${idToken}`;
        }
      } catch (err) {
        console.warn('[API Client] Failed to retrieve fresh Firebase ID token:', err);
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: standard error formatting & 401 force-refresh retry
apiClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;

    // On 401, force-refresh once with getIdToken(true) and retry; if it still fails, sign out and redirect to login
    if (status === 401 && originalRequest && !originalRequest._retry && auth?.currentUser) {
      originalRequest._retry = true;
      try {
        const refreshedToken = await auth.currentUser.getIdToken(true);
        if (refreshedToken) {
          originalRequest.headers.Authorization = `Bearer ${refreshedToken}`;
          return apiClient(originalRequest);
        }
      } catch {
        // Force refresh failed
      }

      // If force refresh still fails or returns 401, sign out and clean up session
      try {
        await auth.signOut();
      } catch {}
      storage.remove('rb_auth_user_session');
      storage.remove('rb_auth_role_session');

      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }

    const message = error.response?.data?.detail || error.message || 'Network request failed';
    const customError = new Error(message);
    if (status) {
      customError.status = status;
    }
    customError.response = error.response;
    return Promise.reject(customError);
  }
);
