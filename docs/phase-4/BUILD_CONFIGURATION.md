# Build Configuration & Tooling Report

## 1. Overview

RepairBuddy's build system is powered by **Vite 8** and **Node.js**, configured to produce independent, optimized single-page applications from a unified repository.

---

## 2. Environment Configuration Files

### `.env.customer`
```env
# RepairBuddy Customer App Environment
VITE_APP=customer
VITE_APP_TITLE=RepairBuddy | Hyperlocal Blue-Collar Services
VITE_USE_MOCK=true
VITE_API_BASE_URL=http://localhost:8000/api
```

### `.env.partner`
```env
# RepairBuddy Partner App Environment (Worker + Admin)
VITE_APP=partner
VITE_APP_TITLE=RepairBuddy Partner | Tradesman & Admin Console
VITE_USE_MOCK=true
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## 3. Package.json Command Reference

```json
{
  "scripts": {
    "dev": "vite",
    "dev:customer": "vite --mode customer",
    "dev:partner": "vite --mode partner",
    "build": "vite build --mode customer",
    "build:customer": "vite build --mode customer",
    "build:partner": "vite build --mode partner",
    "lint": "oxlint",
    "test": "node --test tests/*.test.js",
    "preview": "vite preview"
  }
}
```

### Command Execution Matrix
| Command | Mode | Target App | Title Injected |
|---|---|---|---|
| `npm run dev:customer` | `customer` | Customer App | *RepairBuddy \| Hyperlocal Blue-Collar Services* |
| `npm run dev:partner` | `partner` | Partner App | *RepairBuddy Partner \| Tradesman & Admin Console* |
| `npm run build:customer` | `customer` | Customer App | *RepairBuddy \| Hyperlocal Blue-Collar Services* |
| `npm run build:partner` | `partner` | Partner App | *RepairBuddy Partner \| Tradesman & Admin Console* |
| `npm run build` | `customer` | Customer App (Fallback) | *RepairBuddy \| Hyperlocal Blue-Collar Services* |

---

## 4. Vite Configuration Logic (`vite.config.js`)

```javascript
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
```

---

## 5. Strict Error Gating Verification

If a build is attempted with an unsupported or missing `VITE_APP` environment variable:
```
$ cmd /c "set VITE_APP=invalid && npm run build"

failed to load config from frontend\vite.config.js
error during build:
Error: [Vite Build Error] Invalid VITE_APP value 'invalid'.
Allowed values: 'customer' | 'partner'.
```
The build fails fast with exit code 1, preventing corrupted or misconfigured deployment artifacts.

