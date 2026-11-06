# Authentication & Routing Architecture Report

## 1. Overview

RepairBuddy employs a unified, secure authentication engine coupled with **strict role-segregated routing** tailored to the Customer and Partner applications.

---

## 2. Authentication Flow

### A. Phone OTP Verification
1. User enters a 10-digit Indian mobile number (`+91`).
2. **Production Mode**: Firebase Phone Auth issues a 6-digit SMS OTP using an invisible reCAPTCHA anchor.
3. **Mock Mode (`VITE_USE_MOCK=true`)**: An in-browser SMS simulator immediately provides OTP code `1234` with an auto-fill button.
4. **Token Resolution**: Upon successful OTP submission, the Firebase Auth SDK issues a signed JWT ID token.
5. **Backend Authentication**: Every API request automatically attaches `Authorization: Bearer <token>` in HTTP headers. The FastAPI backend verifies the token using the Firebase Admin SDK.

### B. Admin Claim Verification
- Administrators are protected via Firebase Custom Claims: `claims: { admin: true }`.
- When an admin attempts to load `/admin`, `RequireAdmin` explicitly invokes `user.getIdTokenResult(true)` to force-refresh and evaluate the token's administrative custom claims. If missing or invalid, access is immediately blocked.

---

## 3. Route Tables

### Customer App (`VITE_APP=customer`)

| Path | Component | Access Level | Description |
|---|---|---|---|
| `/login` | `CustomerAuthPage` | Public | Dedicated customer phone OTP login. |
| `/auth` | `<Navigate to="/login" />` | Public | Convenience redirect. |
| `/` | `CustomerHome` | Customer Only | Hyperlocal neighbourhood banner, category grid, and booking bar. |
| `/customer/create-job` | `CreateJobPage` | Customer Only | Problem description, location pin picker, mode, and budget. |
| `/customer/match/:jobId` | `MatchedWorkersPage` | Customer Only | Nearest ranked tradesmen with distance, rating, and initial quote. |
| `/customer/status` | `JobStatusPage` | Customer Only | Active service request tracking and route map. |
| `/customer/status/:jobId`| `JobStatusPage` | Customer Only | Direct link to specific job tracking. |
| `/customer/review/:jobId`| `ReviewPage` | Customer Only | Post-completion 5-star rating and compliment tags. |
| `/profile` | `ProfilePage` | Customer Only | Customer name, phone, and emergency contact manager. |
| `*` | `<Navigate to="/" />` | Catch-all | Redirects unmatched URLs to customer home. |

### Partner App (`VITE_APP=partner`)

| Path | Component | Access Level | Description |
|---|---|---|---|
| `/login` | `PartnerAuthPage` | Public | Tradesman skill selection and Administrator claim login. |
| `/auth` | `<Navigate to="/login" />` | Public | Convenience redirect. |
| `/` | Redirect Handler | Public | Redirects authenticated workers to `/worker` and admins to `/admin`. |
| `/worker` | `WorkerDashboard` | Worker Only | Online toggle, dispatch radius slider, verification banner, job feed. |
| `/worker/job/:jobId` | `WorkerJobDetailsPage` | Worker Only | Problem details, customer address, quote acceptance, counter-bidding. |
| `/worker/earnings` | `WorkerEarningsPage` | Worker Only | Direct cash earnings summary and completed jobs ledger. |
| `/admin` | `AdminPage` | Admin Only | Identity verification queue, document preview, approve/reject, live SOS. |
| `/profile` | `ProfilePage` | Worker / Admin | Technician / Admin profile and emergency contact manager. |
| `*` | Redirect Handler | Catch-all | Redirects unmatched URLs to worker dashboard or login. |

---

## 4. Cross-App Boundary Guards

To protect user experience and prevent accidental role cross-contamination:

1. **Customer App Guard (`RequireCustomer`)**:
   - If a user with `role: 'worker'` or `role: 'admin'` arrives at the Customer App:
     - Navigation is intercepted.
     - A clear alert screen is displayed:
       > **"Partner Account Detected"**
       > *"You are signed in as a Worker/Admin. The Customer App is reserved for household service bookings. Please switch to the Partner App or sign out."*
     - A 1-tap **"Sign Out"** button is provided.

2. **Partner App Guards (`RequireWorker` & `RequireAdmin`)**:
   - If a user with `role: 'customer'` arrives at `/worker` or `/admin`:
     - Navigation is intercepted.
     - A clear alert screen is displayed:
       > **"Customer Account Detected"**
       > *"You are signed in as a Customer. The Partner App is reserved for Tradesmen and Operations Admins. Please switch to the Customer App or sign out."*
     - A 1-tap **"Sign Out"** button is provided.

---

## 5. Session Storage & Teardown

- **Storage Keys**:
  - `repair_buddy_user_v1`: JSON string representing the authenticated user object.
  - `repair_buddy_role_v1`: Plain string (`customer`, `worker`, `admin`).
  - `repair_buddy_token_v1`: JWT ID token.
  - `rb_emergency_contact`: Cached offline emergency contact phone number.
- **Teardown**: Calling `logout()` synchronously clears all session keys from `localStorage`, signs out of the Firebase Auth client SDK, and navigates the user cleanly to `/login`.

