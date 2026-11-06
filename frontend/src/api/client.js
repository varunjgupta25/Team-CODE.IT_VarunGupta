import axios from 'axios';
import { getFreshIdToken, signOutFirebase } from '../lib/firebase.js';

const env = (typeof import.meta !== 'undefined' && import.meta.env) ? import.meta.env : {};

const isProd = Boolean(env.PROD);
if (isProd) {
  const configuredUrl = (env.VITE_API_BASE_URL || '').trim();
  if (!configuredUrl) {
    throw new Error('[RepairBuddy Config Error] Missing VITE_API_BASE_URL in production environment.');
  }
  if (
    configuredUrl.includes('localhost') ||
    configuredUrl.includes('127.0.0.1') ||
    configuredUrl.includes('0.0.0.0')
  ) {
    throw new Error('[RepairBuddy Config Error] Localhost/loopback API URLs are strictly forbidden in production.');
  }
  if (!configuredUrl.startsWith('https://')) {
    throw new Error('[RepairBuddy Config Error] Production API base URL must use HTTPS.');
  }
  if (
    configuredUrl.includes('<') ||
    configuredUrl.includes('>') ||
    configuredUrl.includes('your-render-service')
  ) {
    throw new Error('[RepairBuddy Config Error] Unresolved placeholder in VITE_API_BASE_URL.');
  }
}

// Resolve and sanitize backend API Base URL
let rawBaseUrl =
  env.VITE_API_BASE_URL ||
  env.VITE_API_URL ||
  'https://repair-buddy.onrender.com/api';

if (typeof rawBaseUrl === 'string') {
  // Strip any accidental wrapping quotes
  rawBaseUrl = rawBaseUrl.trim().replace(/^["']|["']$/g, '');
  // If the placeholder <your-render-service> or <render-service> was left unchanged in Vercel, replace it with repair-buddy
  if (
    rawBaseUrl.includes('<your-render-service>') ||
    rawBaseUrl.includes('<render-service>') ||
    rawBaseUrl.includes('<') ||
    rawBaseUrl.includes('your-render-service')
  ) {
    rawBaseUrl = rawBaseUrl
      .replace(/<your-render-service>/g, 'repair-buddy')
      .replace(/<render-service>/g, 'repair-buddy')
      .replace(/your-render-service/g, 'repair-buddy')
      .replace(/<[^>]+>/g, 'repair-buddy');
  }
  // Ensure protocol (unless relative URL like /api)
  if (!rawBaseUrl.startsWith('http://') && !rawBaseUrl.startsWith('https://')) {
    if (!rawBaseUrl.startsWith('/')) {
      rawBaseUrl = `https://${rawBaseUrl}`;
    }
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

// Attach fresh Firebase ID token if present (auto-refreshed per request)
apiClient.interceptors.request.use(
  async (config) => {
    // If payload is FormData, remove Content-Type so axios computes multipart boundary automatically
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }

    let token = null;
    try {
      token = await getFreshIdToken(false);
    } catch {
      token = null;
    }
    if (!token) {
      token = localStorage.getItem('rb_auth_token');
    }
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Standard error formatting with selective retry for 401 token refresh and network/5xx errors
apiClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const config = error.config;
    const status = error.response?.status;

    // Handle 401 Unauthorized: Attempt a single token force-refresh & retry
    if (status === 401 && config && !config._authRetry) {
      config._authRetry = true;
      try {
        const freshToken = await getFreshIdToken(true);
        if (freshToken) {
          localStorage.setItem('rb_auth_token', freshToken);
          config.headers.Authorization = `Bearer ${freshToken}`;
          return apiClient(config);
        }
      } catch (refreshErr) {
        console.warn('[ApiClient] Token refresh attempt failed:', refreshErr);
      }

      // If token refresh fails, clear stale token and notify session expiry
      localStorage.removeItem('rb_auth_token');
      try {
        await signOutFirebase();
      } catch {
        // ignore
      }
    }

    // Retry only network and 5xx errors (up to 2 times with exponential backoff)
    const isNetworkOr5xx = !error.response || (status >= 500 && status < 600);
    if (config && isNetworkOr5xx) {
      config.__retryCount = (config.__retryCount || 0) + 1;
      if (config.__retryCount <= 2) {
        await new Promise((resolve) => setTimeout(resolve, 500 * config.__retryCount));
        return apiClient(config);
      }
    }

    // Format clean error message from FastAPI HTTPException detail or Axios error
    let message = 'Network request failed';
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') {
      message = detail;
    } else if (Array.isArray(detail) && detail.length > 0) {
      message = detail.map((d) => d.msg || `${d.loc?.join('.')}: ${d.type}`).join(', ');
    } else if (error.response?.data?.message) {
      message = error.response.data.message;
    } else if (error.message) {
      message = error.message;
    }

    const err = new Error(message);
    err.status = status;
    err.response = error.response;
    return Promise.reject(err);
  }
);
