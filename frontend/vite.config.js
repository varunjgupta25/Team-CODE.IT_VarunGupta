import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const targetApp = process.env.VITE_APP || env.VITE_APP;

  // Strict validation for production builds
  if (command === 'build') {
    if (!targetApp) {
      throw new Error(
        `[Vite Build Error] Missing VITE_APP environment variable.\n` +
        `Expected 'customer' or 'partner'.\n` +
        `Run: npm run build:customer OR npm run build:partner`
      );
    }
    if (targetApp !== 'customer' && targetApp !== 'partner') {
      throw new Error(
        `[Vite Build Error] Invalid VITE_APP value '${targetApp}'.\n` +
        `Allowed values: 'customer' | 'partner'.`
      );
    }

    // Guard against missing API URL in production builds
    const rawApiUrl = (process.env.VITE_API_BASE_URL || env.VITE_API_BASE_URL || '').trim();
    if (!rawApiUrl) {
      throw new Error(
        `[Vite Build Error] Missing VITE_API_BASE_URL in production build.\n` +
        `Expected a valid production backend URL (e.g., https://repair-buddy.onrender.com/api).`
      );
    }

    // Guard against unresolved placeholders
    if (
      rawApiUrl.includes('<') ||
      rawApiUrl.includes('>') ||
      rawApiUrl.includes('your-render-service')
    ) {
      throw new Error(
        `[Vite Build Error] Unresolved placeholder in VITE_API_BASE_URL: '${rawApiUrl}'.\n` +
        `Please specify a valid production backend URL.`
      );
    }

    // Guard against localhost / loopback URLs in production builds (strict, zero-bypass)
    if (
      rawApiUrl.includes('localhost') ||
      rawApiUrl.includes('127.0.0.1') ||
      rawApiUrl.includes('0.0.0.0')
    ) {
      throw new Error(
        `[Vite Build Error] VITE_API_BASE_URL cannot point to localhost/loopback in production mode.\n` +
        `Configured URL: '${rawApiUrl}'. Production builds must point to a live HTTPS backend.`
      );
    }

    // Require secure HTTPS in production
    if (!rawApiUrl.startsWith('https://')) {
      throw new Error(
        `[Vite Build Error] Insecure protocol in VITE_API_BASE_URL: '${rawApiUrl}'.\n` +
        `Production API base URL must use HTTPS.`
      );
    }

    // Guard against mock mode in production builds (strict, zero-bypass)
    const useMockVal = (process.env.VITE_USE_MOCK || env.VITE_USE_MOCK || '').trim().toLowerCase();
    if (useMockVal === 'true') {
      throw new Error(
        `[Vite Build Error] VITE_USE_MOCK cannot be 'true' in production mode.\n` +
        `Production builds must connect to the live backend. Mock mode is strictly prohibited.`
      );
    }
  }

  // Map application entry point for strict bundle isolation
  const appEntryMap = {
    customer: path.resolve(__dirname, 'src/apps/customer/CustomerApp.jsx'),
    partner: path.resolve(__dirname, 'src/apps/partner/PartnerApp.jsx'),
  };

  const appEntry = appEntryMap[targetApp] || path.resolve(__dirname, 'src/App.jsx');

  return {
    plugins: [react()],
    define: {
      __APP_MODE__: JSON.stringify(targetApp || 'customer'),
    },
    resolve: {
      alias: {
        '@app-entry': appEntry,
      },
    },
    build: {
      outDir: targetApp === 'partner' ? 'dist/partner' : targetApp === 'customer' ? 'dist/customer' : 'dist',
      emptyOutDir: true,
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      allowedHosts: true,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  };
});
