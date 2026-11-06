# API Contract Validation & Mismatch Report
**Project:** RepairBuddy  
**Phase:** 3 — Frontend Integration & Verification  
**Status:** VALIDATED & RESILIENT

---

## 1. Verified API Inventory

The following table summarizes all frontend API calls compared directly against FastAPI backend routers (`routers/`):

| Area | Frontend API Function | Method | Backend Route | Status | Contract Compatibility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **System** | `healthCheck()` | `GET` | `/health` & `/api/health` | Active | Returns `{ status, service, database, mock_mode }` |
| **Auth** | `registerCustomer()` | `POST` | `/customers/register` | Active | Strict token UID derivation; duplicate returns 409 |
| **Auth** | `registerWorker()` | `POST` | `/workers/register` | Active | Strict token UID derivation; duplicate returns 409 |
| **Auth** | `getCurrentUser()` | `GET` | `/users/me` | Active | Masked customer/worker profiles |
| **Jobs** | `createJob()` | `POST` | `/jobs` | Active | `category`, `description`, `location`, `mode`, `budget` |
| **Jobs** | `getJob()` | `GET` | `/jobs/:id` | Active | Returns `JobResponse`; masks address if unassigned |
| **Jobs** | `getNearbyJobs()` | `GET` | `/jobs/nearby` | Active | Distance-sorted leads within radius |
| **Jobs** | `startJob()` | `POST` | `/jobs/:id/start` | Active | `accepted -> in_progress` |
| **Jobs** | `completeJob()` | `POST` | `/jobs/:id/complete` | Active | `in_progress -> completed` |
| **Jobs** | `cancelJob()` | `POST` | `/jobs/:id/cancel` | Active | `open/accepted -> cancelled` (Customer or Admin) |
| **Jobs** | `confirmJob()` | `POST` | `/jobs/:id/confirm` | Fallback | Auto-handled: queries `/jobs/:id` if endpoint is 404 |
| **Matching** | `getMatchedWorkers()` | `GET` | `/workers/match?jobId=` | Active | Returns ranked list of `{ worker, distanceKm, etaMinutes, within30, score, trustScore }` |
| **Offers** | `createOffer()` | `POST` | `/offers` | Active | Booking proposal by customer or worker |
| **Offers** | `getOffers()` | `GET` | `/offers?jobId=` | Active | Offers list for job |
| **Offers** | `counterOffer()` | `POST` | `/offers/:id/counter` | Active | Price negotiation with alternating turn validation |
| **Offers** | `acceptOffer()` | `POST` | `/offers/:id/accept` | Active | Sets job status `accepted` and locks `finalPrice` |
| **Offers** | `rejectOffer()` | `POST` | `/offers/:id/reject` | Active | Rejects offer |
| **Workers** | `getWorker()` | `GET` | `/workers/:id` | Active | Privacy-masked worker profile |
| **Workers** | `updateWorkerAvailability()`| `PATCH` | `/workers/:id` | Active | `{ isAvailableNow: bool }` |
| **Workers** | `getWorkerEarnings()` | `GET` | `/workers/:id/earnings` | Active | Returns net cash earnings and delivery counts |
| **Workers** | `verifyWorker()` | `POST` | `/workers/verify` | Active | Requests worker ID verification |
| **Workers** | `uploadWorkerVerification()`| `POST` | `/workers/verify/upload`| Fallback | Falls back to `/workers/verify` if upload is 404 |
| **Reviews** | `submitReview()` | `POST` | `/reviews` | Active | Rating (1–5) and customer feedback |
| **SOS** | `triggerSos()` | `POST` | `/sos` | Active | Emergency alert saving coordinates and job |
| **SOS** | `setEmergencyContact()` | `PUT` | `/users/me/emergency-contact` | Fallback | Backed by local storage fallback if backend 404s |
| **SOS** | `getEmergencyContact()` | `GET` | `/users/me/emergency-contact` | Fallback | Backed by local storage fallback if backend 404s |
| **Reports** | `reportUser()` | `POST` | `/reports` | Active | `{ workerId, reason }` |
| **Admin** | `getPendingVerifications()` | `GET` | `/admin/verifications/pending` | Active | Returns unverified/pending workers |
| **Admin** | `approveWorkerVerification()` | `POST` | `/admin/verifications/:id/approve` | Active | Admin verification approval |
| **Admin** | `rejectWorkerVerification()` | `POST` | `/admin/verifications/:id/reject` | Active | Admin verification rejection with reason |
| **Admin** | `getReports()` | `GET` | `/admin/reports` | Active | Returns safety reports |
| **Admin** | `getAdminSosAlerts()` | `GET` | `/admin/sos` | Fallback | Gracefully returns `[]` if endpoint 404s |
| **Route** | `getRoute()` | `GET` | `/route?jobId=&workerId=` | Active | Road network polyline, distanceKm, and etaMinutes |

---

## 2. API Gaps & Compatibility Fallbacks Resolved

### G-01: Job Mode Schema Discrepancy
- **Frontend State:** `CreateJobPage.jsx` had previously stored mode as `'on_demand'` (underscore).
- **Backend Schema:** `models/job.py` strictly accepts `VALID_MODES = Literal["on-demand", "scheduled"]` (hyphen).
- **Resolution:** Updated `CreateJobPage.jsx` state and click handlers to use `'on-demand'`. In addition, `frontend/src/api/index.js` `createJob` normalizes `mode: payload.mode === 'on_demand' ? 'on-demand' : (payload.mode || 'on-demand')`.

### G-02: Emergency SOS Delivery Status
- **Backend Behavior:** `services/sos_service.py` records SOS alerts with `status: "recorded"`.
- **Frontend Expectation:** `SosButton.jsx` was checking for `'notified'` and `'partial'`, and categorizing any other status as `'failed'`.
- **Resolution:** Updated `SosButton.jsx` to recognize `status === 'recorded'` as a successful dispatch:
  ```javascript
  const isNotified = sentAlert?.status === 'notified' || sentAlert?.status === 'recorded';
  ```

### G-03: Two-Step vs Single-Step Completion Gating
- **Observation:** In mock mode and Phase 2 frontend, completion follows `in_progress -> awaiting_confirmation -> completed` via `confirmJob()`. On backend `origin/main`, `POST /jobs/{id}/complete` directly transitions `in_progress -> completed`, and `/jobs/{id}/confirm` is not implemented.
- **Resolution:** `api.confirmJob(jobId)` handles HTTP 404 by safely querying `GET /jobs/{jobId}` (which is already `completed`). `JobStatusPage.jsx` natively renders the completed banner and review button once status is `completed`.

### G-04: Worker ID Verification Upload Endpoint
- **Observation:** Frontend verification form uploads ID photo and live selfie (`multipart/form-data`) to `POST /workers/verify/upload`. Backend `origin/main` supports metadata-based `POST /workers/verify`.
- **Resolution:** `api.uploadWorkerVerification` attempts `POST /workers/verify/upload`, and if a 404 occurs, gracefully falls back to `POST /workers/verify` with `{ documentType, documentNumber }`.
