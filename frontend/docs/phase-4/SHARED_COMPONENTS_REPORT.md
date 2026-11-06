# Shared Components & Architecture Report

## 1. Principles & Objectives

A primary requirement of Phase 4 is **preventing codebase duplication**. Rather than creating two separate frontend repositories or cloning files, RepairBuddy uses a unified repository where all business logic, communication clients, state management, and reusable UI components reside in a single shared directory tree.

Both the Customer App and Partner App import directly from these shared modules.

---

## 2. Shared Component Inventory

| Component Path | Component Name | Consumers | Functionality |
|---|---|---|---|
| `src/components/common/ToastContainer.jsx` | `ToastContainer` | Customer & Partner | Global notification system for instant success, error, and info toasts. |
| `src/components/common/SosButton.jsx` | `SosButton` | Customer & Partner | Emergency SOS trigger with 5-second cancel countdown and emergency contact verification. |
| `src/components/common/ReportModal.jsx` | `ReportModal` | Customer & Partner | In-app modal for submitting misconduct, damage, and price dispute reports. |
| `src/components/common/TrustBadge.jsx` | `TrustBadge` | Customer & Partner | Renders trust level (Gold, Silver, Bronze) with score-based styling. |
| `src/components/common/EmptyState.jsx` | `EmptyState` | Customer & Partner | Clean visual fallback when lists or feeds are empty. |
| `src/components/common/Skeleton.jsx` | `Skeleton` | Customer & Partner | Pulse loading skeleton for async feed and profile hydration. |
| `src/components/map/RouteMap.jsx` | `RouteMap` | Customer & Partner | Interactive Leaflet map displaying customer home, worker location, and routing. |
| `src/components/map/MapPicker.jsx` | `MapPicker` | Customer & Partner | Draggable GPS pin selector for setting precise service coordinates. |
| `src/components/worker/VerificationCard.jsx` | `VerificationCard` | Partner | Multi-step document and selfie upload interface with magic-byte validation. |
| `src/pages/ProfilePage.jsx` | `ProfilePage` | Customer & Partner | Universal profile page for managing name, phone, and emergency contact details. |

---

## 3. Shared State Management (Zustand)

All client-side reactive state is centralized in `src/store/`:

1. **`authStore.js`**:
   - Manages user profile, role (`customer`, `worker`, `admin`), and session token.
   - Synchronizes with `localStorage` (`repair_buddy_user_v1`, `repair_buddy_role_v1`).
   - Handles Firebase Phone Auth (`requestPhoneOtp`, `confirmPhoneOtp`) and mock fallback.
2. **`jobStore.js`**:
   - Tracks active job lifecycle (`open` ➔ `negotiating` ➔ `accepted` ➔ `in_progress` ➔ `awaiting_confirmation` ➔ `completed`).
   - Manages price offers, counter-bids, and completion confirmations.
3. **`toastStore.js`**:
   - Centralized message queue for notifications across the entire application lifecycle.

---

## 4. Shared API & Communication Layer

1. **`src/api/index.js`**:
   - Single API facade dispatching to either the live FastAPI backend via `axios` or to `mockStore.js`.
   - Auto-attaches `Authorization: Bearer <token>` from `useAuthStore`.
   - Provides unified methods: `createJob()`, `getNearbyJobs()`, `submitOffer()`, `acceptOffer()`, `startJob()`, `completeJob()`, `confirmJob()`, `triggerSos()`, `submitVerification()`, `getPendingVerifications()`, and `reviewVerification()`.
2. **`src/api/mockStore.js`**:
   - Full in-browser simulation supporting offline development and automated Node test suites.
   - Seeds 25 verified tradesmen across Mumbai clusters (Mira Road, Bandra, Andheri, Borivali, Thane).

---

## 5. Domain Models & Constants (`src/types/index.js`)

Single source of truth for all domain constants:
- **`ROLES`**: `CUSTOMER: 'customer'`, `WORKER: 'worker'`, `ADMIN: 'admin'`.
- **`JOB_STATUS`**: `OPEN`, `NEGOTIATING`, `ACCEPTED`, `IN_PROGRESS`, `AWAITING_CONFIRMATION`, `COMPLETED`, `CANCELLED`.
- **`OFFER_STATUS`**: `PENDING`, `ACCEPTED`, `REJECTED`, `EXPIRED`.
- **`CATEGORIES`**: 8 primary household repair categories with labels, icons, and typical market visit rates.
- **`ADMIN_CLAIM_KEY`**: Custom claim identifier `admin` verified on Firebase ID tokens.

---

## 6. Duplication Audit Findings

- **Zero Duplicate CSS**: Both apps share `tailwind.config.js` and `src/index.css`.
- **Zero Duplicate Models**: Both apps consume the same types file.
- **Zero Duplicate Store State**: State operations run through identical store functions.
- **Separation Mechanism**: Separation is performed at the router and entrypoint layer via build-time module aliasing, ensuring maximum code reuse while maintaining complete bundle isolation.

