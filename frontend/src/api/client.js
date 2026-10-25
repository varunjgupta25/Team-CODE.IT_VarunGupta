import axios from 'axios';

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

// Attach Firebase ID token if present
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('rb_auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Standard error formatting
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Network request failed';
    return Promise.reject(new Error(message));
  }
);
