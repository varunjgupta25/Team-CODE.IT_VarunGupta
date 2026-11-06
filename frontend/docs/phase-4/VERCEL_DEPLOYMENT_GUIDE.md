# Vercel Production Deployment Guide

## 1. Overview

RepairBuddy's dual frontend architecture allows deploying two separate production applications (**Customer App** and **Partner App**) directly from the **same single Git repository** on Vercel without creating duplicated codebases.

---

## 2. Deployment Architecture

```
                    GitHub Repository (Team-CODE.IT_VarunGupta)
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
        Vercel Project 1                        Vercel Project 2
    "repair-buddy-customer"                 "repair-buddy-partner"
  (Root: frontend, Mode: customer)        (Root: frontend, Mode: partner)
                 │                                       │
                 ▼                                       ▼
    https://repairbuddy.app               https://partner.repairbuddy.app
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     ▼
                            FastAPI Backend
                    (https://repair-buddy.onrender.com)
```

---

## 3. Project 1: RepairBuddy Customer App

### Setup Steps in Vercel Dashboard:
1. Click **"Add New..."** ➔ **"Project"**.
2. Import the repository: `varunjgupta25/Team-CODE.IT_VarunGupta`.
3. Set **Project Name**: `repair-buddy-customer`.
4. Set **Framework Preset**: `Vite`.
5. Set **Root Directory**: `frontend` (Click *Edit* and select the `frontend` folder).
6. Under **Build & Development Settings**:
   - Toggle **Build Command**: `npm run build:customer`
   - Toggle **Output Directory**: `dist`
7. Under **Environment Variables**, add:
   ```env
   VITE_APP=customer
   VITE_APP_TITLE=RepairBuddy | Hyperlocal Blue-Collar Services
   VITE_USE_MOCK=false
   VITE_API_BASE_URL=https://repair-buddy.onrender.com/api
   VITE_FIREBASE_API_KEY=<YOUR_FIREBASE_WEB_API_KEY>
   VITE_FIREBASE_AUTH_DOMAIN=repair-buddy-662c6.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=repair-buddy-662c6
   VITE_FIREBASE_STORAGE_BUCKET=repair-buddy-662c6.firebasestorage.app
   VITE_FIREBASE_MESSAGING_SENDER_ID=<YOUR_SENDER_ID>
   VITE_FIREBASE_APP_ID=<YOUR_APP_ID>
   ```
8. Click **Deploy**.

---

## 4. Project 2: RepairBuddy Partner App (Worker + Admin)

### Setup Steps in Vercel Dashboard:
1. Click **"Add New..."** ➔ **"Project"**.
2. Select the **same repository**: `varunjgupta25/Team-CODE.IT_VarunGupta`.
3. Set **Project Name**: `repair-buddy-partner`.
4. Set **Framework Preset**: `Vite`.
5. Set **Root Directory**: `frontend` (Click *Edit* and select the `frontend` folder).
6. Under **Build & Development Settings**:
   - Toggle **Build Command**: `npm run build:partner`
   - Toggle **Output Directory**: `dist`
7. Under **Environment Variables**, add:
   ```env
   VITE_APP=partner
   VITE_APP_TITLE=RepairBuddy Partner | Tradesman & Admin Console
   VITE_USE_MOCK=false
   VITE_API_BASE_URL=https://repair-buddy.onrender.com/api
   VITE_FIREBASE_API_KEY=<YOUR_FIREBASE_WEB_API_KEY>
   VITE_FIREBASE_AUTH_DOMAIN=repair-buddy-662c6.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=repair-buddy-662c6
   VITE_FIREBASE_STORAGE_BUCKET=repair-buddy-662c6.firebasestorage.app
   VITE_FIREBASE_MESSAGING_SENDER_ID=<YOUR_SENDER_ID>
   VITE_FIREBASE_APP_ID=<YOUR_APP_ID>
   ```
8. Click **Deploy**.

---

## 5. Single-Page Application (SPA) Rewrites

To prevent HTTP 404 errors when users refresh deep URLs like `/customer/status/job-123` or `/worker/job/job-456`, both projects use standard rewrite rules:

```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```
Pre-configured configuration files are provided in the repository:
- `frontend/vercel.customer.json`
- `frontend/vercel.partner.json`

---

## 6. Backend CORS Alignment (Render)

Once both Vercel projects are deployed, configure the live frontend URLs in your Render FastAPI environment settings:

```env
CUSTOMER_APP_ORIGIN=https://repair-buddy-customer.vercel.app
PARTNER_APP_ORIGIN=https://repair-buddy-partner.vercel.app
```
The FastAPI backend will automatically validate `Origin` headers against both URLs, permitting credentials (`Access-Control-Allow-Credentials: true`) and preflight options requests.

