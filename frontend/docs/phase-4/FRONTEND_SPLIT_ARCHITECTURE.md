# Phase 4 — Frontend Split Architecture Report

## 1. Executive Summary

RepairBuddy's frontend has been successfully restructured into **two independently buildable, high-performance web applications** residing within a single shared codebase:
1. **Customer App** (`VITE_APP=customer`): Dedicated to household customers booking, negotiating, tracking, and reviewing hyperlocal home repairs.
2. **Partner App** (`VITE_APP=partner`): Dedicated to tradesmen (workers) and operations administrators for accepting jobs, managing bids, tracking cash earnings, reviewing ID verifications, and monitoring live safety alerts.

Both applications share reusable UI components, authentication infrastructure, Zustand state stores, API services, and domain types, adhering strictly to the **zero codebase duplication** mandate.

---

## 2. Architecture & Directory Organization

```
frontend/
├── .env.customer                       # Customer app build environment
├── .env.partner                        # Partner app build environment
├── package.json                        # Independent build and dev scripts
├── vite.config.js                      # Build-time validation & entry routing
├── vercel.customer.json                # Vercel project configuration for Customer
├── vercel.partner.json                 # Vercel project configuration for Partner
├── src/
│   ├── main.jsx                        # Shared entrypoint importing '@app-entry'
│   ├── App.jsx                         # Unified fallback application
│   ├── apps/
│   │   ├── customer/
│   │   │   ├── CustomerApp.jsx         # Customer root router & shell
│   │   │   ├── CustomerHeader.jsx      # Customer branded navigation header
│   │   │   ├── CustomerBottomNav.jsx   # Customer navigation bar (Book, Status, Profile)
│   │   │   └── CustomerAuthPage.jsx    # Focused customer OTP sign-in
│   │   └── partner/
│   │       ├── PartnerApp.jsx          # Partner root router & shell
│   │       ├── PartnerHeader.jsx       # Partner branded navigation header
│   │       ├── PartnerBottomNav.jsx    # Partner navigation bar (Feed, Earnings, Admin, Profile)
│   │       └── PartnerAuthPage.jsx     # Tradesman and Admin dual-portal sign-in
│   ├── components/                     # 100% Shared UI components
│   │   ├── common/                     # ToastContainer, SosButton, ReportModal, etc.
│   │   ├── layout/                     # ProtectedRoute, MobileLayout
│   │   ├── map/                        # RouteMap, MapPicker (Leaflet)
│   │   └── worker/                     # VerificationCard
│   ├── pages/                          # Specialized page components
│   │   ├── customer/                   # CustomerHome, CreateJobPage, MatchedWorkersPage, etc.
│   │   ├── worker/                     # WorkerDashboard, WorkerJobDetailsPage, WorkerEarningsPage
│   │   ├── admin/                      # AdminPage
│   │   └── ProfilePage.jsx             # Shared user profile & emergency contact editor
│   ├── store/                          # Shared Zustand state stores
│   ├── api/                            # Shared Axios client and mockStore
│   ├── lib/                            # Shared Firebase auth & utilities
│   └── types/                          # Shared role, category, and status constants
└── tests/
    ├── phase1-verification.test.js
    ├── phase2-verification.test.js
    ├── phase3-integration.test.js
    └── phase4-separation.test.js       # Phase 4 architecture verification suite
```

---

## 3. Build-Time Resolution & Dynamic Entry Mapping

The separation is achieved through Vite compile-time aliasing (`@app-entry`):

1. **Environment Flag (`VITE_APP`)**:
   - Running `npm run build:customer` launches `vite build --mode customer`, which loads `.env.customer` containing `VITE_APP=customer`.
   - Running `npm run build:partner` launches `vite build --mode partner`, which loads `.env.partner` containing `VITE_APP=partner`.
2. **Build-Time Entry Aliasing**:
   In `vite.config.js`:
   ```javascript
   const appEntryMap = {
     customer: path.resolve(__dirname, 'src/apps/customer/CustomerApp.jsx'),
     partner: path.resolve(__dirname, 'src/apps/partner/PartnerApp.jsx'),
   };
   const appEntry = appEntryMap[targetApp] || path.resolve(__dirname, 'src/App.jsx');
   ```
3. **Tree-Shaking & Bundle Isolation**:
   Because `CustomerApp.jsx` exclusively imports customer pages, Rollup's module graph never crawls `WorkerDashboard`, `WorkerEarningsPage`, `WorkerJobDetailsPage`, or `AdminPage`. These pages are **completely excluded from the customer production JavaScript bundle**.
   Similarly, `PartnerApp.jsx` never imports customer booking pages, completely excluding `CustomerHome`, `CreateJobPage`, `MatchedWorkersPage`, etc., from the partner bundle.

---

## 4. Component Reuse & Shared Architecture Matrix

| Module / Component | Shared / Dedicated | Purpose |
|---|---|---|
| `Header` / `CustomerHeader` / `PartnerHeader` | Dedicated Shells | Distinct branding ("RepairBuddy" vs "RepairBuddy Partner") and role navigation |
| `BottomNav` / `CustomerBottomNav` / `PartnerBottomNav` | Dedicated Navigation | App-specific tab switching (no cross-contamination of worker/customer links) |
| `AuthPage` / `CustomerAuthPage` / `PartnerAuthPage` | Dedicated Portals | Customer-only OTP flow vs Tradesman skill selection & Admin claim sign-in |
| `ProfilePage` | 100% Shared | Profile editing, avatar display, and emergency contact phone number management |
| `SosButton` | 100% Shared | Hyperlocal emergency safety triggering with real SMS/WhatsApp dispatch |
| `ReportModal` | 100% Shared | Incident report submission for both customers and workers |
| `RouteMap` & `MapPicker` | 100% Shared | Leaflet-based GPS coordinate selection and live worker tracking |
| `ToastContainer` | 100% Shared | Unified user feedback and notification alerts |
| `authStore`, `jobStore`, `workerStore`, `adminStore` | 100% Shared | Reactive state management, session hydration, and data caching |
| `api/index.js` & `api/mockStore.js` | 100% Shared | Offline-first mock fallback and FastAPI REST communication |

---

## 5. Cross-App Role Segregation & Access Security

1. **Customer App Route Guard (`RequireCustomer`)**:
   - Validates that the active session has `role === ROLES.CUSTOMER`.
   - If an authenticated worker or admin accesses the Customer App, it intercepts the session and presents a prominent **"Partner Account Detected"** screen advising them to launch the Partner App or sign out.
2. **Partner App Route Guard (`RequireWorker` & `RequireAdmin`)**:
   - `RequireWorker`: Restricts `/worker/*` routes strictly to `role === ROLES.WORKER`. If a customer arrives, an informative **"Customer Account Detected"** screen is displayed with an easy sign-out button.
   - `RequireAdmin`: Restricts `/admin` strictly to `role === ROLES.ADMIN` and verifies Firebase custom claim `admin: true`.
   - `RequirePartner`: Permits both Workers and Admins to access `/profile`.

