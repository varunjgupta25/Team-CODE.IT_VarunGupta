# Phase 0: Frontend API Inventory & Contract Specification

**Project**: RepairBuddy Frontend  
**Auditor**: Senior Integration Specialist & Backend Contract Auditor  
**Date**: November 2026  
**Status**: Complete Inspection & Parity Audit  

---

## 1. API Architecture & Configuration

* **HTTP Client**: Axios instance configured in `src/api/client.js`.
* **Base URL**: Controlled via `import.meta.env.VITE_API_URL` (Defaults to `https://repair-buddy.onrender.com`).
* **Mock Interception**: Controlled via `import.meta.env.VITE_USE_MOCK !== 'false'`. When active, `src/api/index.js` routes all function calls to `src/api/mockStore.js`.
* **Authorization Interceptor**: Attached dynamically in `src/api/client.js`:
  ```javascript
  apiClient.interceptors.request.use(async (config) => {
    const user = auth.currentUser;
    if (user) {
      const token = await user.getIdToken();
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });
  ```

---

## 2. Complete API Endpoint Inventory

| # | Calling Component / Module | Facade Method | HTTP Method | Endpoint Path | Request Payload / Query Params | Expected Response Schema | Auth Required | Integration Status & Issues |
| :- | :--- | :--- | :-: | :--- | :--- | :--- | :-: | :--- |
| **1** | `CustomerHome.jsx`, `CreateJobPage.jsx` | `api.getCategories()` | `GET` | `/categories` | None | `Array<{ id, name, icon, baseRate }>` | None (Public) | **Live Verified**. Static metadata fallback present in mock. |
| **2** | `authStore.js` (`registerCustomer`) | `api.registerCustomer(data)` | `POST` | `/customers/register` | `{ uid, phone, name, email }` | `{ success: boolean, customer: UserProfile }` | Firebase Token | **Live Verified**. Handled 409 Conflict for returning users. |
| **3** | `authStore.js` (`registerWorker`) | `api.registerWorker(data)` | `POST` | `/workers/register` | `{ uid, phone, name, trade, hourlyRate }` | `{ success: boolean, worker: WorkerProfile }` | Firebase Token | **Live Verified**. Handled 409 Conflict for returning workers. |
| **4** | `authStore.js` (`fetchProfile`) | `api.getWorker(uid)` | `GET` | `/workers/{uid}` | Path: `uid` | `{ id, name, phone, trade, verified, rating }` | Firebase Token | **Live Verified**. Used as fallback profile loader on 409. |
| **5** | `authStore.js` (`initAuth`) | `api.getMe()` | `GET` | `/users/me` | None | `{ id, phone, name, role, ... }` | Firebase Token | **Partial**. Backend returns 404 on some deployments; handled gracefully. |
| **6** | `CreateJobPage.jsx` | `api.createJob(data)` | `POST` | `/jobs` | `{ categoryId, description, budget, location, urgency }` | `{ success: boolean, job: JobObject }` | Firebase Token | **Live Verified**. Location includes `{ lat, lng, address }`. |
| **7** | `jobStore.js` (`fetchActiveJob`) | `api.getJob(jobId)` | `GET` | `/jobs/{jobId}` | Path: `jobId` | `{ id, status, customerId, workerId, offers, ... }` | Firebase Token | **Live Verified**. Used by polling engine (every 5000ms). |
| **8** | `jobStore.js` (`fetchCustomerJobs`) | `api.getCustomerJobs(id)` | `GET` | `/jobs/customer/{customerId}` | Path: `customerId` | `Array<JobObject>` | Firebase Token | **Live Verified**. Populates active & historical bookings. |
| **9** | `WorkerDashboard.jsx` | `api.getNearbyJobs(params)` | `GET` | `/jobs/nearby` | Query: `?lat={lat}&lng={lng}&radius={km}` | `Array<JobObject>` | Firebase Token | **Live Verified**. Filtered by worker category & availability. |
| **10** | `MatchedWorkersPage.jsx` | `api.getMatchedWorkers(id)` | `GET` | `/jobs/{jobId}/matched-workers` | Path: `jobId` | `Array<WorkerMatchObject>` | Firebase Token | **Live Verified**. Returns workers ranked by distance & rating. |
| **11** | `WorkerDashboard.jsx` | `api.updateWorkerAvailability()`| `POST` | `/workers/availability` | `{ isAvailable: boolean }` | `{ success: boolean, isAvailable: boolean }` | Firebase Token | **Live Verified**. Sets worker online/offline status. |
| **12** | `WorkerJobDetailsPage.jsx` | `api.submitQuote(id, quote)` | `POST` | `/jobs/{jobId}/offers` | `{ amount: number, notes?: string }` | `{ success: boolean, offer: OfferObject }` | Firebase Token | **Live Verified**. Transitions job status to `negotiating`. |
| **13** | `JobStatusPage.jsx` | `api.acceptOffer(id, offerId)`| `POST` | `/jobs/{jobId}/offers/{offerId}/accept` | None | `{ success: boolean, job: JobObject }` | Firebase Token | **Live Verified**. Sets job status to `accepted`. |
| **14** | `JobStatusPage.jsx`, `WorkerJobDetailsPage.jsx` | `api.counterOffer(id, amount)`| `POST` | `/jobs/{jobId}/offers/counter` | `{ amount: number }` | `{ success: boolean, offer: OfferObject }` | Firebase Token | **Live Verified**. Updates current bid in negotiation state. |
| **15** | `WorkerJobDetailsPage.jsx` | `api.updateJobStatus(id, status)`| `PATCH` | `/jobs/{jobId}/status` | `{ status: 'arrived'|'in_progress'|'completed' }` | `{ success: boolean, status: string }` | Firebase Token | **Live Verified**. Advances job lifecycle steps. |
| **16** | `VerificationCard.jsx` | `api.uploadVerificationDoc()`| `POST` | `/workers/verify/upload` | `FormData` (multipart: `docType`, `file`) | `{ success: boolean, docUrl: string, status: string }` | Firebase Token | **Live Verified**. Uploads ID/license files to storage. |
| **17** | `AdminPage.jsx` | `api.getVerifications()` | `GET` | `/admin/verifications` | Query: `?status=pending` | `Array<VerificationSubmission>` | Admin Claim | **Live Verified**. Requires `claims.admin === true`. |
| **18** | `AdminPage.jsx` | `api.approveWorker(id)` | `POST` | `/admin/verifications/{workerId}/approve`| None | `{ success: boolean, workerId: string }` | Admin Claim | **Live Verified**. Sets worker verification status to `verified`. |
| **19** | `AdminPage.jsx` | `api.rejectWorker(id, reason)` | `POST` | `/admin/verifications/{workerId}/reject` | `{ reason: string }` | `{ success: boolean, workerId: string }` | Admin Claim | **Live Verified**. Sets worker verification status to `rejected`. |
| **20** | `AdminPage.jsx` | `api.getDocument(uid, type)` | `GET` | `/admin/verifications/{uid}/documents/{type}`| Path: `uid`, `type` | Binary / Blob stream | Admin Claim | **Live Verified**. Renders document image in admin review. |
| **21** | `ReviewPage.jsx` | `api.submitReview(data)` | `POST` | `/reviews` | `{ jobId, workerId, rating: 1-5, comment, tags }`| `{ success: boolean, reviewId: string }` | Firebase Token | **Live Verified**. Submits post-completion ratings. |
| **22** | `SosButton.jsx` | `api.triggerSos(data)` | `POST` | `/sos` | `{ jobId, lat, lng, reason?: string }` | `{ success: boolean, alertId: string }` | Firebase Token | **Live Verified**. Emits emergency trigger to ops team. |
| **23** | `ReportModal.jsx` | `api.submitReport(data)` | `POST` | `/reports` | `{ jobId, reportedUserId, reason, description }` | `{ success: boolean, reportId: string }` | Firebase Token | **Live Verified**. Creates platform dispute record. |
| **24** | `ProfilePage.jsx` | `api.getEmergencyContact()` | `GET` | `/users/me/emergency-contact` | None | `{ name: string, phone: string, relationship: string }`| Firebase Token | **Partial**. Falls back to local storage cache if 404. |
| **25** | `ProfilePage.jsx` | `api.setEmergencyContact()` | `POST` | `/users/me/emergency-contact` | `{ name: string, phone: string, relationship: string }`| `{ success: boolean }` | Firebase Token | **Partial**. Stores in mock/local fallback if endpoint absent. |
| **26** | `WorkerEarningsPage.jsx` | *(None - Missing)* | `GET` | `/workers/earnings` | Query: `?range=week|month` | None (Client-side calculated) | Firebase Token | **MISSING BACKEND ENDPOINT**. Page calculates earnings from `localStorage`. |

---

## 3. Contract Discrepancy & Inconsistency Analysis

1. **Missing Backend Earnings Endpoint**:
   * `WorkerEarningsPage.jsx` simulates all calculations from local mock state. A real backend endpoint (`GET /workers/earnings`) returning `{ totalEarnings, todayEarnings, weeklyEarnings, ledger: [] }` is required for production live mode.
2. **Emergency Contacts Fallback**:
   * The backend does not reliably persist emergency contacts across all deployments. The frontend safely wraps `api.getEmergencyContact()` in a try/catch block with `storage.get('rb_emergency_contact_v1')` fallback.
3. **HTTP 409 vs. Profile Hydration**:
   * On registration conflict (409), the frontend loads the existing profile using `api.getWorker(uid)` for workers and cached session data for customers. Standardizing a single `GET /users/me` endpoint across all roles would eliminate this branching logic.

