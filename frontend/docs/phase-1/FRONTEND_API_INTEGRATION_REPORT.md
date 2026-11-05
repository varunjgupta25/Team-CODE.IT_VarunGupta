# Phase 1: Frontend API Integration & Contract Verification Report

**Project**: RepairBuddy Frontend  
**Auditor**: Senior API Integration Specialist  
**Backend API**: `https://repair-buddy.onrender.com/api`  
**OpenAPI Spec Inspected**: Live backend schema downloaded from `/openapi.json`  
**Date**: November 2026  
**Status**: Contract Verification & Normalization Complete  

---

## 1. API Architecture & Configuration

* **Client Engine**: Axios instance (`src/api/client.js`) configured with base URL sanitization.
* **Base URL Precedence**:
  1. `import.meta.env.VITE_API_BASE_URL`
  2. `import.meta.env.VITE_API_URL`
  3. Default fallback: `https://repair-buddy.onrender.com/api`
* **Route Prefix Compatibility**:
  - The FastAPI backend mounts all routes under both `/...` and `/api/...`.
  - The client ensures the `/api` suffix is cleanly appended, routing requests directly to the verified backend endpoints.

---

## 2. Integrated Endpoints & Contract Verification Matrix

| # | Frontend Facade Method | Backend HTTP & Route | Request Body / Params Schema | Match Status | Normalization / Fix Applied |
| :- | :--- | :--- | :--- | :---: | :--- |
| **1** | `api.registerCustomer` | `POST /customers/register` | `CustomerRegisterRequest: { name*, phone*, location }` | **VERIFIED** | Uid extracted from Firebase Bearer Token on backend. 409 handled gracefully. |
| **2** | `api.registerWorker` | `POST /workers/register` | `WorkerRegisterRequest: { name*, phone*, skills*, rates*, location }` | **VERIFIED** | Skills array & rates dictionary match backend Pydantic models. |
| **3** | `api.getWorker` | `GET /workers/{worker_id}` | Path: `worker_id` | **VERIFIED** | Returns `WorkerResponse` with ratings and trust scores. |
| **4** | `api.updateWorkerAvailability` | `PATCH /workers/{worker_id}`| `WorkerAvailabilityPayload: { isAvailableNow*: boolean }` | **VERIFIED** | Toggles online radar discovery. |
| **5** | `api.createJob` | `POST /jobs` | `JobCreate: { category*, description*, location*, budget }` | **VERIFIED** | Location payload `{ lat, lng, address }` validated. |
| **6** | `api.getJob` | `GET /jobs/{id}` | Path: `id` | **VERIFIED** | Consumed by polling engine every 5000ms. |
| **7** | `api.getNearbyJobs` | `GET /jobs/nearby` | Auth: `Bearer <token>` | **VERIFIED** | Backend matches jobs using worker's registered location and category. |
| **8** | `api.getMatchedWorkers` | `GET /workers/match` | Query: `?jobId={id}` | **VERIFIED** | Returns `Array<MatchedWorkerResponse>` ranked by composite score. |
| **9** | `api.createOffer` | `POST /offers` | `OfferCreate: { jobId*, workerId*, price*, by }` | **VERIFIED** | Supports initial quotes by customer or worker. |
| **10** | `api.counterOffer` | `POST /offers/{id}/counter` | `OfferCounter: { price*: number }` | **NORMALIZED** | Normalized payload to `{ price: Number(price) }`. |
| **11** | `api.acceptOffer` | `POST /offers/{id}/accept` | None (Path: `id`) | **VERIFIED** | Transitions job to `accepted`. |
| **12** | `api.rejectOffer` | `POST /offers/{id}/reject` | None (Path: `id`) | **VERIFIED** | Rejects pending offer. |
| **13** | `api.startJob` | `POST /jobs/{id}/start` | None (Path: `id`) | **VERIFIED** | Transitions job to `in_progress`. |
| **14** | `api.completeJob` | `POST /jobs/{id}/complete` | None (Path: `id`) | **VERIFIED** | Worker marks work finished (`awaiting_confirmation`). |
| **15** | `api.confirmJob` | `POST /jobs/{id}/confirm` | None (Path: `id`) | **VERIFIED** | Customer confirms completion (`completed`). |
| **16** | `api.cancelJob` | `POST /jobs/{id}/cancel` | None (Path: `id`) | **VERIFIED** | Cancels active job request. |
| **17** | `api.submitReview` | `POST /reviews` | `ReviewCreate: { jobId*, workerId*, rating*, comment* }` | **FIXED** | Fixed null pointer in `ReviewPage.jsx` when worker is not in mock cache. |
| **18** | `api.triggerSos` | `POST /sos` | `SOSCreate: { jobId, location: { lat*, lng* } }` | **VERIFIED** | Dispatches emergency alert to Safety Ops. |
| **19** | `api.reportUser` | `POST /reports` | `ReportCreate: { workerId*, reason*, jobId }` | **NORMALIZED** | Explicitly maps `workerId: payload.workerId \|\| payload.reportedUserId`. |
| **20** | `api.setEmergencyContact` | `PUT /users/me/emergency-contact` | `EmergencyContact: { name*, phone* }` | **VERIFIED** | Updates user emergency contact details. |
| **21** | `api.getEmergencyContact` | `GET /users/me/emergency-contact` | None | **VERIFIED** | Retrieves stored emergency contact. |
| **22** | `api.uploadWorkerVerification` | `POST /workers/verify/upload` | Multipart: `documentType`, `documentNumber`, `id_document`, `selfie` | **VERIFIED** | Axios interceptor deletes default `Content-Type` for valid boundary creation. |
| **23** | `api.getPendingVerifications` | `GET /admin/verifications/pending` | None (Admin Claim Required) | **VERIFIED** | In live mode, errors are thrown to UI rather than swallowed. |
| **24** | `api.approveWorkerVerification` | `POST /admin/verifications/{uid}/approve` | Path: `uid` | **VERIFIED** | Sets worker status to verified. |
| **25** | `api.rejectWorkerVerification` | `POST /admin/verifications/{uid}/reject` | `AdminRejectRequest: { reason*: string }` | **VERIFIED** | Records rejection reason. |
| **26** | `api.getVerificationDocumentBlobUrl` | `GET /admin/verifications/{uid}/documents/{doc_type}` | Path: `uid`, `doc_type` | **VERIFIED** | Retrieves binary blob stream and converts to ObjectURL. |
| **27** | `api.getAdminSosAlerts` | `GET /admin/sos` | None (Admin Claim Required) | **VERIFIED** | Returns list of recent SOS triggers. |
| **28** | `api.getRoute` | `GET /route` | Query: `?jobId={id}&workerId={uid}` | **VERIFIED** | Returns route polyline, distance, and ETA. |

---

## 3. Remaining Backend Dependencies & Observations

1. **Worker Earnings Ledger Endpoint**:
   - The backend does not currently feature a dedicated `GET /workers/earnings` route. Earnings summaries in `WorkerEarningsPage.jsx` are calculated using `jobsDone * tradeRate` from the worker's authenticated profile. If historical transaction records are required in Phase 2, a dedicated backend endpoint should be specified.
2. **Push Notifications**:
   - Real-time updates currently operate via 5-second HTTP polling on `GET /jobs/{id}` and `GET /offers?jobId={id}`. Transitioning to WebSockets or Firebase Cloud Messaging (FCM) is recommended for Phase 2 scaling.

