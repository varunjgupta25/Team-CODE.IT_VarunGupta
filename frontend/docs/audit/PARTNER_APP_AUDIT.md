# Phase 0: Partner Application (Worker & Admin) Technical & Functional Audit

**Application**: RepairBuddy Partner (Service Professional Portal & Administrator Console)  
**Target Personas**:  
1. **Service Workers**: Electricians, Plumbers, Technicians receiving local leads and completing jobs.  
2. **Platform Administrators**: Back-office operations team managing verifications, disputes, and approvals.  
**Auditor**: Senior Frontend Architect & UI/UX Auditor  
**Date**: November 2026  
**Status**: Inspection-Only Audit Complete  

---

## 1. Partner Persona Architectural Split

Under the planned architecture, the **Partner Application** combines:
- **Service Worker Core**: Onboarding, KYC/verification, active dispatch radar, quote submissions, lifecycle tracking, earnings ledger.
- **Administrator Console**: Document moderation, verification approvals/rejections, dispute resolution, platform governance.

Currently, both personas exist within the single monolithic frontend codebase under route guards (`/worker/*` and `/admin`).

---

## 2. Worker Portal Audit

### 2.1 Worker Authentication & Registration (`src/pages/AuthPage.jsx`)
* **Role Selection**: User explicitly selects `"worker"` during phone authentication.
* **API Registration**: Calls `POST /workers/register` sending Firebase ID token.
* **Conflict Handling**: Returns HTTP 409 if the worker is already registered; the frontend catches this and transitions directly into `loginAsWorker()` without error toast.
* **Worker Profile Initialization**: Defaults trade rate, trade category, and verification status (`unverified`).

---

### 2.2 Worker Dashboard & Availability Radar (`src/pages/WorkerDashboard.jsx`)
* **Availability Toggle**:
  * Persistent toggle button: "You are Online (Accepting Jobs)" vs "You are Offline".
  * Calls `api.updateWorkerAvailability(isAvailable)`.
  * Visually switches dashboard between active radar scanning and idle state.
* **Nearby Job Feed**:
  * Fetches jobs within service radius using `api.getNearbyJobs({ lat, lng, radius })`.
  * Job cards display: Category badge, distance (km), customer budget (₹), posted timestamp, urgency level.
* **Active Job Banner**:
  * Highlights any currently assigned job with 1-tap navigation to `/worker/job/:jobId`.
* **Verification Status Callout**:
  * If unverified or pending, prominently displays `VerificationCard` prompting document submission.

---

### 2.3 Job Details, Quotations & Lifecycle Management (`src/pages/WorkerJobDetailsPage.jsx`)
* **Job Inspection**:
  * Displays customer location, problem description, budget, and distance.
  * Embedded `RouteMap` showing route between worker location and customer residence.
* **Bidding & Negotiation**:
  * Worker can submit a quote via `api.submitQuote(jobId, quoteAmount)`.
  * If customer counters, worker sees the counter-bid and can accept or submit a revised counter.
* **Lifecycle State Transitions**:
  * Step 1: **Accept Job** -> sets status to `accepted`.
  * Step 2: **I Have Arrived** -> sets status to `arrived`.
  * Step 3: **Start Work** -> sets status to `in_progress`.
  * Step 4: **Complete Job** -> sets status to `completed` and records payment collection.
* **Emergency & Safety**:
  * Persistent `SosButton` and `ReportModal` available during active work.

---

### 2.4 Worker Earnings & Ledger (`src/pages/WorkerEarningsPage.jsx`)
* **Current Implementation Assessment**:
  * **MOCK ONLY / CLIENT COMPUTED**: The earnings page currently queries `localStorage` (`rb_mock_jobs_v1`) to calculate total completed jobs and multiplies them by the worker's trade rate.
  * Displays: Today's Earnings, This Week's Total, Completed Jobs Count, and Job History list.
* **Backend Gap**:
  * The backend lacks dedicated endpoints for `/workers/earnings` or `/workers/ledger`. All earnings metrics are simulated client-side.

---

### 2.5 Identity Verification & Document Upload (`src/components/worker/VerificationCard.jsx`)
* **Document Requirements**:
  * Government ID (Aadhaar / Voter ID / Driving License)
  * Trade Certificate or Skill Qualification Proof
  * Police Clearance Certificate (Optional for higher trust badge)
* **File Upload Mechanism**:
  * File inputs accept JPG/PNG/PDF.
  * Dispatches `POST /workers/verify/upload` with `multipart/form-data`.
* **Status Badges**: `unverified` (gray), `pending` (amber), `verified` (emerald), `rejected` (rose).

---

## 3. Administrator Console Audit

### 3.1 Admin Authentication & Claim Gating (`src/pages/AdminPage.jsx`)
* **Authentication Gating**:
  * Protected via `ProtectedRoute` with `allowedRoles={['admin']}` and `requireAdminClaim={true}`.
  * Evaluates Firebase ID token claim:
    ```javascript
    const result = await auth.currentUser.getIdTokenResult(true);
    const isAdmin = result.claims.admin === true;
    ```
  * Rejects unprivileged users and redirects them to `/customer` with an explicit security alert toast.

---

### 3.2 Verification Moderation Queue (`src/pages/AdminPage.jsx`)
* **Pending Queue**:
  * Fetches pending worker submissions via `api.getPendingVerifications()` (`GET /admin/verifications`).
  * Lists worker name, trade skill, phone number, submission timestamp, and document links.
* **Document Inspection**:
  * Admin can click document links to view uploaded ID proofs via `GET /admin/verifications/{uid}/documents/{docType}`.
* **Decision Actions**:
  * **Approve**: Calls `api.approveWorker(workerId)` (`POST /admin/verifications/:id/approve`).
  * **Reject**: Prompts for rejection reason (e.g., "Blurry document", "Expired ID") and calls `api.rejectWorker(workerId, reason)` (`POST /admin/verifications/:id/reject`).

---

### 3.3 Platform Overview & Moderation Features
* **Platform Metrics**:
  * Displays stats cards: Total Registered Workers, Verified Workers, Active Jobs Today, Pending Verifications.
* **Dispute & SOS Oversight**:
  * Lists active emergency SOS triggers and customer/worker dispute reports submitted via `POST /reports`.
* **Identified Gaps**:
  * No search or filtering mechanism in the verification queue.
  * No user management table to suspend or ban offending customers or workers.
  * UI is forced into the mobile layout container (`max-w-md`), making administrative review of document images awkward on desktop screens.

---

## 4. Partner Application Feature Implementation Matrix

| Screen / Feature | Persona | Current Status | Data Source | Assessment & Constraints |
| :--- | :--- | :--- | :--- | :--- |
| **Worker Login / OTP** | Worker | Fully Implemented | Firebase Live SDK | Phone OTP with returning 409 handling. |
| **Worker Registration** | Worker | Fully Implemented | Backend API (`/workers/register`) | Auto-creates worker profile with trade category. |
| **Availability Toggle** | Worker | Fully Implemented | Backend API (`/workers/availability`) | Real-time status update for matchmaking. |
| **Nearby Jobs Feed** | Worker | Fully Implemented | Backend API (`/jobs/nearby`) | Displays distance, budget, and urgency. |
| **Quote & Negotiation** | Worker | Fully Implemented | Backend API (`/jobs/:id/offers`) | Counter-offer negotiation lifecycle. |
| **Lifecycle Transitions** | Worker | Fully Implemented | Backend API (`/jobs/:id/status`) | `accepted` -> `arrived` -> `in_progress` -> `completed`. |
| **Document Upload** | Worker | Fully Implemented | Backend API (`/workers/verify/upload`) | `multipart/form-data` file transmission. |
| **Earnings Dashboard** | Worker | **Mock Only** | Client LocalStorage | Computed locally; no backend ledger endpoint. |
| **Admin Route Protection**| Admin | Fully Implemented | Firebase Claims (`claims.admin === true`) | Strict cryptographic claim validation. |
| **Verification Queue** | Admin | Fully Implemented | Backend API (`/admin/verifications`) | Lists pending submissions with documents. |
| **Worker Approval/Rejection**| Admin | Fully Implemented | Backend API (`/admin/verifications/:id`) | Supports approval and rejection with reason. |
| **Platform Analytics** | Admin | Partially Implemented | Simulated / Aggregated | Basic counters; lacks historical charting. |

---

## 5. Partner Application UI/UX & Architectural Issues

1. **Admin Mobile Viewport Constraint**: Rendering the Administrator Console inside a 448px mobile container (`MobileLayout.jsx`) severely degrades productivity. Admins reviewing high-resolution identity documents require desktop grid views, image zoom modals, and tabular data layouts.
2. **Absence of Real-Time Push Notifications**: Workers must keep the browser tab open and rely on periodic polling to receive incoming job alerts.
3. **No Geolocation Background Sync**: When worker is in transit, GPS coordinates are not streamed to the backend; coordinates update only on manual action.

