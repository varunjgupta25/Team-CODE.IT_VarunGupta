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
