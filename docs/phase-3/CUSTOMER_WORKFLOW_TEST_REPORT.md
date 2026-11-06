# Customer Workflow Verification Report
**Project:** RepairBuddy  
**Phase:** 3 — Frontend Integration & Verification  
**Component:** Customer Journey (`frontend/src/pages/customer/`)  
**Status:** FULLY VERIFIED

---

## 1. Verified Customer Steps

| Step | Operation | Component / Route | Backend API Contract | Test Status |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Customer Registration | `AuthPage.jsx` (`/login`) | `POST /customers/register` | **PASS** |
| **2** | Phone OTP Authentication | `AuthPage.jsx` | Firebase Phone Auth / `confirmPhoneOtp` | **PASS** |
| **3** | Session Persistence | `authStore.js` | `rb_auth_user_session`, `rb_auth_token` | **PASS** |
| **4** | Customer Dashboard | `CustomerHome.jsx` (`/`) | Dynamic category search & active job tracking | **PASS** |
| **5** | Profile & Emergency Contact | `ProfilePage.jsx` (`/profile`) | `PUT /users/me/emergency-contact` | **PASS** |
| **6** | Job Creation (Category & Location) | `CreateJobPage.jsx` (`/customer/create-job`) | `POST /jobs` | **PASS** |
| **7** | Job Mode & Budget Validation | `CreateJobPage.jsx` | `mode: 'on-demand'` / `'scheduled'`, min ₹100 | **PASS** |
| **8** | Proximity Worker Discovery | `MatchedWorkersPage.jsx` (`/customer/match/:id`) | `GET /workers/match?jobId=` | **PASS** |
| **9** | Worker Profile & Trust Tier Modal | `MatchedWorkersPage.jsx` | `GET /workers/:id` (Trust badge & jobsDone) | **PASS** |
| **10** | Quoting / Direct Offer Creation | `MatchedWorkersPage.jsx` | `POST /offers` (`by: 'customer'`) | **PASS** |
| **11** | Negotiation Turn-Taking & Accept | `JobStatusPage.jsx` (`/customer/status/:id`) | `POST /offers/:id/accept` | **PASS** |
| **12** | Live Tracking & Polling Loop | `JobStatusPage.jsx` | 5-second interval `GET /jobs/:id` & RouteMap | **PASS** |
| **13** | Job Completion & Cash Settlement | `JobStatusPage.jsx` | `POST /jobs/:id/confirm` & Cash on Delivery | **PASS** |
| **14** | Rating & Compliment Review | `ReviewPage.jsx` (`/customer/review/:id`) | `POST /reviews` (1.0–5.0★ + compliment tags) | **PASS** |
| **15** | Safety / Abuse Incident Report | `ReportModal.jsx` | `POST /reports` (`workerId`, `reason`) | **PASS** |
| **16** | Emergency SOS Dispatch | `SosButton.jsx` | `POST /sos` (`jobId`, `location`) | **PASS** |

---

## 2. In-Depth Flow Verification

### A. Authentication & Registration
- Users enter their 10-digit Indian mobile number (`+91`).
- Firebase Phone Auth dispatches real SMS OTP or invokes mock development fallback (`1234`).
- Upon OTP verification, `loginAsCustomer` derived UID is verified.
- Account role is permanently stamped as `customer`. An existing worker cannot sign in via customer portal (conflict guard).

### B. Service Request Creation (`CreateJobPage.jsx`)
- Supports all 8 standard service categories: Plumber, Electrician, Painter, Cleaner, Maid, Cook, Carpenter, Appliance Repair.
- Normalized `mode`: correctly sets `'on-demand'` for doorstep arrival in ~30 mins, or `'scheduled'` with datetime picker.
- Budget field validates a minimum customer budget of ₹100 with dynamic fair price hint badges.
- Coordinates default to Mira Road (`lat: 19.2812, lng: 72.8697`) with interactive Leaflet map dragging.

### C. Matching & Negotiation
- Calls `GET /workers/match?jobId=`.
- Defensive normalization handles both flattened worker objects and nested `{ worker, distanceKm, etaMinutes, within30, score, trustScore }`.
- "Within 30 Min Tag" dynamically appears if ETA is within 30 minutes.
- Negotiation enforces turn-taking: customer makes initial quote -> worker counters -> customer accepts.

### D. Cash Settlement & Review
- No payment gateway / 0% platform escrow by design: customer pays agreed amount directly to worker in cash/UPI upon job completion.
- Review allows 1 to 5 stars, review text, and selective compliment tags (`Punctual arrival`, `Clean Workmanship`, `Fair agreed pricing`, etc.).

### E. SOS Workflow
- `SosButton.jsx` checks for emergency contact and prompts if missing.
- Dispatches emergency alert to `POST /sos`.
- Successfully recognizes backend `status: "recorded"` and `status: "notified"` to display immediate positive confirmation without triggering false failure warnings.

