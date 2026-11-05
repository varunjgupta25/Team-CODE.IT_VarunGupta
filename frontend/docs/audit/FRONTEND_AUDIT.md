# Phase 0: Frontend Architecture Audit & Technical Assessment

**Project**: RepairBuddy (Hyperlocal Household Services Marketplace)  
**Auditor**: Senior Frontend Architect & Systems Integration Specialist  
**Target Environment**: React 19, Vite, Tailwind CSS, Zustand, Firebase Authentication, Leaflet  
**Repository**: [varunjgupta25/Team-CODE.IT_VarunGupta](https://github.com/varunjgupta25/Team-CODE.IT_VarunGupta.git)  
**Production Deployment**: [team-code-it-varun-gupta.vercel.app](https://team-code-it-varun-gupta.vercel.app/)  
**Backend API**: [repair-buddy.onrender.com](https://repair-buddy.onrender.com/)  
**Date**: November 2026  
**Status**: Inspection-Only Audit Complete  

---

## 1. Executive Summary

RepairBuddy is engineered as a mobile-first Single Page Application (SPA) designed to serve a dual-sided hyperlocal home services marketplace. The application currently unifies three distinct user personas—**Customers**, **Service Workers (Partners)**, and **Platform Administrators**—within a single monolithic code repository and client-side bundle.

While the codebase demonstrates clear separation of visual concerns, clean UI component modularity, and strict adherence to a mobile viewport container (`max-w-md`), significant architectural debt exists around:
1. **Persona coupling**: All three personas share one deployment, one entry point, and one bundle, resulting in leaked admin bundles to customer devices and cross-persona state leakage.
2. **Mock vs. Live Dual-State Architecture**: An in-browser mock engine (`src/api/mockStore.js`) intercepts network requests by default unless explicitly disabled with `VITE_USE_MOCK=false`. Several features (worker earnings, emergency contacts, local notification polling) exist exclusively inside `localStorage` mocks with no backend schema backing.
3. **Reactive State vs. Storage Synchronization**: State persistence across page reloads relies on fragmented `localStorage` keys with varying hydration strategies across Zustand stores.

---

## 2. Technology Stack & Dependencies

| Layer | Package / Technology | Version | Purpose | Architectural Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **Framework** | `react` | `^19.0.0` | Core UI engine | Utilizes React 19 concurrent features. Compatible with modern rendering hooks. |
| **DOM Renderer** | `react-dom` | `^19.0.0` | Virtual DOM mounting | Standard React 19 DOM bindings. |
| **Build Tool** | `vite` | `^6.2.0` | Fast HMR & bundling | Rollup-based bundling. Single-bundle output without persona code-splitting. |
| **Routing** | `react-router-dom` | `^7.2.0` | Client routing | React Router v7 used in declarative component style (`BrowserRouter`, `Routes`, `Route`). |
| **State Management** | `zustand` | `^5.0.3` | Client store | Lightweight stores for `authStore`, `jobStore`, `toastStore`. Manual `localStorage` persistence. |
| **HTTP Client** | `axios` | `^1.7.9` | Network communication | Configured with request/response interceptors for Firebase ID tokens. |
| **Authentication** | `firebase` | `^11.4.0` | Phone OTP & Auth claims | Firebase Web SDK v11. Decoupled auth instance with invisible reCAPTCHA verifiers. |
| **Mapping Engine** | `leaflet`, `react-leaflet` | `^1.9.4`, `^5.0.0` | Geospatial maps & routing | OpenStreetMap tiles rendered via Leaflet. Client-side marker tracking and polylines. |
| **Styling** | `tailwindcss`, `@tailwindcss/vite` | `^4.0.9` | Atomic styling | Tailwind v4 via Vite plugin. Emerald/Slate/Amber palette constrained to mobile viewport. |
| **Icons** | `lucide-react` | `^1.16.0` | SVG icons | Tree-shakeable icon set across all views. |
| **Code Quality** | `oxlint` | `^0.15.13` | High-speed linting | Configured in `npm run lint`. Zero warnings/errors. |

---

## 3. Repository Topology & Source Tree Map

```
frontend(NEW)/
├── .env.example                  # Template with VITE_API_URL, VITE_USE_MOCK, Firebase credentials
├── .env.production.example       # Production template pointing to Render backend
├── .gitignore                    # Standard Node/Vite ignore rules (includes .env)
├── index.html                    # Root HTML entry; viewport constrained, fonts, reCAPTCHA container
├── package.json                  # Dependencies, scripts (dev, build, preview, lint)
├── vercel.json                   # SPA rewrite configuration ({ "source": "/(.*)", "destination": "/" })
├── vite.config.js                # Vite 6 config with @tailwindcss/vite plugin
├── public/                       # Static public assets
└── src/
    ├── main.jsx                  # Application bootstrapper (mounts <App /> to #root)
    ├── App.jsx                   # Central routing table, global Toast, role guard registration
    ├── index.css                 # Global styles, Tailwind imports, Leaflet CSS overrides
    ├── api/                      # Network abstraction layer
    │   ├── client.js             # Axios instance, baseURL, Firebase auth interceptor
    │   ├── index.js              # API Facade (toggles between live Axios and mockStore)
    │   ├── mockData.js           # Static seed data (workers, jobs, categories)
    │   └── mockStore.js          # In-memory & localStorage mock CRUD engine
    ├── components/               # UI Component Hierarchy
    │   ├── common/               # Shared cross-persona components
    │   │   ├── BottomNav.jsx     # Sticky bottom navigation bar (Customer & Worker modes)
    │   │   ├── EmptyState.jsx    # Standardized blank slate / 404 display
    │   │   ├── Header.jsx        # Sticky top bar with logo, active job badge, profile avatar
    │   │   ├── ReportModal.jsx   # Generic reporting modal for user/worker grievances
    │   │   ├── Skeleton.jsx      # Shimmer placeholder animations for cards & lists
    │   │   ├── SosButton.jsx     # Emergency trigger button with countdown & audio alert
    │   │   └── TrustBadge.jsx    # Visual verification badge (Government ID, Criminal Check, Verified)
    │   ├── layout/               # Structural containers & route interceptors
    │   │   ├── MobileLayout.jsx  # 448px (max-w-md) centered mobile viewport wrapper
    │   │   └── ProtectedRoute.jsx# Role-based route guard evaluating auth state & claims
    │   ├── maps/                 # Geospatial & mapping components
    │   │   ├── MapPicker.jsx     # Interactive pin-drop map for job location selection
    │   │   └── RouteMap.jsx      # Multi-marker route map (Worker position -> Job site)
    │   └── worker/               # Worker-specific modular widgets
    │       └── VerificationCard.jsx # Document upload progress & status card
    ├── lib/                      # Core libraries & utility functions
    │   ├── firebase.js           # Firebase app initialization, Auth instance, reCAPTCHA setup
    │   ├── storage.js            # Type-safe localStorage wrapper (get, set, remove, clear)
    │   └── utils.js              # Formatters (currency, distance, dates, phone numbers)
    ├── pages/                    # Screen-level route views
    │   ├── AdminPage.jsx         # Verification moderation queue & platform overview
    │   ├── AuthPage.jsx          # Firebase Phone OTP login/registration (Customer, Worker, Admin)
    │   ├── CreateJobPage.jsx     # Multi-step job posting wizard (Category -> Description -> Location)
    │   ├── CustomerHome.jsx      # Customer landing page (Categories, recent activity, active status)
    │   ├── JobStatusPage.jsx     # Real-time job lifecycle tracking, negotiation, & live route
    │   ├── MatchedWorkersPage.jsx# Matched worker list, trust comparisons, direct booking/bidding
    │   ├── ProfilePage.jsx       # User profile, emergency contacts, role switching, sign out
    │   ├── ReviewPage.jsx        # Star rating & qualitative feedback submission
    │   ├── WorkerDashboard.jsx   # Worker radar: online toggle, nearby jobs feed, active dispatch
    │   ├── WorkerEarningsPage.jsx# Completed job ledger, daily/weekly earnings summaries
    │   └── WorkerJobDetailsPage.jsx # Job inspection, quote submission, counter-offer response
    ├── store/                    # Zustand global state stores
    │   ├── authStore.js          # Authentication state, user profile, role, claims, session boot
    │   ├── jobStore.js           # Active job state, polling synchronization, customer active jobs
    │   └── toastStore.js         # Reactive toast notification queue
    └── types/                    # Domain models, enum definitions, constants
        └── index.js              # JobStatus, ServiceCategory, UserRole, PaymentStatus, schemas
```

---

## 4. Component Hierarchy & Dependency Map

The component graph reflects how UI components consume layout containers, global stores, API layers, and utility helpers:

```
src/main.jsx
└── src/App.jsx
    ├── ToastContainer (consumes toastStore)
    ├── MobileLayout (enforces max-w-md viewport, scroll restoration)
    │   ├── Header (consumes authStore, jobStore)
    │   └── BottomNav (consumes authStore, jobStore, react-router)
    └── Routes
        ├── / (Public/Redirect) ───────────► Redirects based on authStore.user.role
        ├── /auth (Public) ────────────────► AuthPage (Firebase Recaptcha, authStore, toastStore)
        │
        ├── Customer Realm (ProtectedRoute: allowedRoles=['customer'])
        │   ├── /customer ─────────────────► CustomerHome (jobStore, api.getCategories, TrustBadge)
        │   ├── /create-job ───────────────► CreateJobPage (MapPicker, api.createJob, jobStore)
        │   ├── /matched-workers ──────────► MatchedWorkersPage (api.getMatchedWorkers, TrustBadge)
        │   ├── /job-status/:id ───────────► JobStatusPage (RouteMap, SosButton, ReportModal, api)
        │   ├── /review/:id ───────────────► ReviewPage (api.submitReview, toastStore)
        │   └── /profile ──────────────────► ProfilePage (authStore, api.get/setEmergencyContact)
        │
        ├── Worker Realm (ProtectedRoute: allowedRoles=['worker'])
        │   ├── /worker ───────────────────► WorkerDashboard (api.getNearbyJobs, VerificationCard)
        │   ├── /worker/job/:id ───────────► WorkerJobDetailsPage (RouteMap, api.submitQuote, api.updateJobStatus)
        │   ├── /worker/earnings ──────────► WorkerEarningsPage (localStorage queries, job filtering)
        │   └── /worker/profile ───────────► ProfilePage (authStore, VerificationCard)
        │
        └── Admin Realm (ProtectedRoute: allowedRoles=['admin'], requireAdminClaim=true)
            └── /admin ────────────────────► AdminPage (api.getVerifications, api.reviewVerification)
```

---

## 5. Routing Architecture & Route Guarding Assessment

### Route Configuration (`src/App.jsx`)
Client-side routing is declared using `react-router-dom` v7. The router defines explicit boundaries using the `ProtectedRoute` component:

```jsx
<Routes>
  {/* Public / Entry */}
  <Route path="/" element={<RoleBasedHomeRedirect />} />
  <Route path="/auth" element={<AuthPage />} />

  {/* Customer Routes */}
  <Route element={<ProtectedRoute allowedRoles={['customer']} />}>
    <Route path="/customer" element={<CustomerHome />} />
    <Route path="/create-job" element={<CreateJobPage />} />
    <Route path="/matched-workers" element={<MatchedWorkersPage />} />
    <Route path="/job-status/:jobId" element={<JobStatusPage />} />
    <Route path="/review/:jobId" element={<ReviewPage />} />
    <Route path="/profile" element={<ProfilePage />} />
  </Route>

  {/* Worker Routes */}
  <Route element={<ProtectedRoute allowedRoles={['worker']} />}>
    <Route path="/worker" element={<WorkerDashboard />} />
    <Route path="/worker/job/:jobId" element={<WorkerJobDetailsPage />} />
    <Route path="/worker/earnings" element={<WorkerEarningsPage />} />
    <Route path="/worker/profile" element={<ProfilePage />} />
  </Route>

  {/* Admin Routes */}
  <Route element={<ProtectedRoute allowedRoles={['admin']} requireAdminClaim={true} />}>
    <Route path="/admin" element={<AdminPage />} />
  </Route>

  {/* Catch-all 404 */}
  <Route path="*" element={<EmptyState type="not-found" />} />
</Routes>
```

### Route Guard Analysis (`src/components/layout/ProtectedRoute.jsx`)
1. **Hydration Blocking**: Checks `authStore.isInitialized`. If false, renders a full-height centered loading spinner to prevent flash of unauthorized redirects.
2. **Authentication Gate**: If `authStore.isAuthenticated` is false, redirects to `/auth` with `replace: true` and preserves target location in state.
3. **Role Validation**: If `allowedRoles` does not include `user.role`, redirects to persona dashboard (`/customer` or `/worker`).
4. **Admin Claim Gate**: If `requireAdminClaim: true`, verifies `authStore.claims.admin === true`. If absent, emits an error toast (`"Access denied. Administrator privileges required."`) and redirects to `/customer`.

---

## 6. State Management Architecture

State is distributed across three Zustand stores and browser `localStorage`:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          BROWSER STORAGE                               │
│  rb_auth_user_v1 │ rb_auth_role_v1 │ rb_auth_token_v1 │ rb_active_job_v1│
└────────┬─────────────────┬───────────────────┬────────────────┬────────┘
         │                 │                   │                │
         ▼                 ▼                   ▼                ▼
┌─────────────────────────────────┐   ┌──────────────────────────────────┐
│           authStore             │   │             jobStore             │
│ - user: UserProfile | null      │   │ - activeJob: Job | null          │
│ - role: 'customer'|'worker'     │   │ - customerJobs: Job[]            │
│ - token: string | null          │   │ - pollingInterval: Timer | null  │
│ - claims: { admin: boolean }    │   │ - isSyncing: boolean             │
│ - isInitialized: boolean        │   │ - fetchActiveJob(jobId)          │
│ - loginWithFirebase(user, role) │   │ - startPolling(jobId)            │
│ - logout()                      │   │ - stopPolling()                  │
└─────────────────────────────────┘   └──────────────────────────────────┘
```

### Store Evaluation:
* **`authStore.js`**: Handles authentication bootstrapping via `initAuth()`. Listens to `onAuthStateChanged(auth)`. On token refresh or login, reads Firebase ID Token claims (`getIdTokenResult(true)`) to dynamically set `claims.admin`.
* **`jobStore.js`**: Controls active job tracking. Features a 5-second polling loop (`startPolling()`) when a job is in non-terminal states (`posted`, `negotiating`, `accepted`, `arrived`, `in_progress`). Correctly clears polling on terminal states (`completed`, `cancelled`) or component unmount.
* **`toastStore.js`**: In-memory ephemeral queue for notification toasts with autohide timers (3000ms).

---

## 7. Map & Geospatial Integration

* **Leaflet & React-Leaflet**:
  * Default Center: Hyderabad, India (`[17.3850, 78.4867]`).
  * Custom SVG markers generated via Leaflet `L.divIcon` to prevent broken asset paths common with standard Webpack/Vite bundlers.
* **`MapPicker.jsx`**: Enables reverse geocoding approximation using pin dragging or map clicks. Emits `{ lat, lng, address }`.
* **`RouteMap.jsx`**: Dynamically fits bounds (`map.fitBounds`) around worker position and job location. Renders dashed SVG polylines representing travel trajectories and computes synthetic straight-line ETAs based on average city transit speeds (25 km/h).

---

## 8. Styling & Design Token System

* **Framework**: Tailwind CSS v4 configured via `@tailwindcss/vite`.
* **Palette**:
  * Primary / Action: Emerald (`#10b981`, `#059669`)
  * Secondary / Dark UI: Slate (`#0f172a`, `#1e293b`, `#334155`)
  * Warning / Alert: Amber (`#f59e0b`) & Rose (`#f43f5e`)
* **Responsive Shell**: Enforced inside `MobileLayout.jsx` with `w-full max-w-md mx-auto min-h-screen bg-slate-50 relative shadow-2xl flex flex-col`. All desktop browser viewports display a centered smartphone frame with desktop borders and shadows.

