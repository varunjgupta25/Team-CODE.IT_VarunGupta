# Blockers, Gaps, and Architecture Report — Phase 3
**Project:** RepairBuddy  
**Phase:** 3 — Integration & Verification (Backend & Frontend)  
**Status:** REPORTED & HARMONIZED

---

## 1. Resolved In Phase 3
- Full verification of all 200 regression and integration test cases across the FastAPI backend.
- Verified all 48 frontend integration and regression test cases across React 19/Vite application.
- Validated atomic state changes for competing offer rejection and lifecycle transitions.
- Validated complete moderation loop: abuse report submission -> automatic flag -> admin resolution -> account reactivation.
- Front-end integration buffered against missing or variant backend endpoints via the resilient adapter layer.

---

## 2. Platform Architecture Constraints (Intentional / By Design)

### 2.1 Direct Cash Payment Model (No Payment Gateway)
- **Status**: By design.
- **Impact**: RepairBuddy operates on a 0% commission direct-cash model. Payments are settled directly between customer and worker upon completion of physical household tasks.
- **Action**: No backend escrow or gateway integration required for Phase 3.

### 2.2 Client-Side Polling for Live Status Updates
- **Status**: Polling pattern in use (`/jobs/{id}`, `/offers?jobId=...`).
- **Impact**: Backend does not maintain persistent WebSocket or FCM push connections. Status changes are communicated via standard HTTP polling intervals (5-second intervals).
- **Action**: Fully supported by current rate limits (default 120 requests/min per IP).

---

## 3. Frontend-Discovered Backend Gaps & Recommendations

### 3.1 Worker Document & Live Selfie Upload Endpoint
- **Affected File:** `routers/workers.py`
- **Current Backend Contract:** Exposes `POST /workers/verify`, accepting `{ documentType: str, documentNumber: str }`.
- **Frontend Expectation:** `VerificationCard.jsx` collects multipart form data (`id_document`, `selfie`).
- **Frontend Mitigation:** If `POST /workers/verify/upload` returns 404, `api.uploadWorkerVerification` automatically falls back to `POST /workers/verify` with `{ documentType, documentNumber }`.
- **Recommendation:** Implement `POST /workers/verify/upload` with `fastapi.UploadFile` handling, magic bytes inspection, and private DPDP-compliant disk storage.

### 3.2 User Emergency Contact Endpoint
- **Affected File:** `routers/jobs.py` (or new `routers/users.py`)
- **Current Backend Contract:** No endpoint mounted for `/users/me/emergency-contact`.
- **Frontend Expectation:** `PUT` and `GET` `/users/me/emergency-contact`.
- **Frontend Mitigation:** `api.setEmergencyContact` and `api.getEmergencyContact` persist and retrieve contacts via `localStorage` (`rb_emergency_contact`) when the backend returns 404.
- **Recommendation:** Add `PUT` and `GET` routes on `/users/me/emergency-contact` to persist emergency contacts on the user document in Firestore.

### 3.3 Admin Emergency SOS Alerts Feed
- **Affected File:** `routers/sos.py` or `routers/admin.py`
- **Current Backend Contract:** `POST /sos` records alerts in `sos_alerts`, but no endpoint exists to retrieve them.
- **Frontend Expectation:** `GET /admin/sos` returning list of recent SOS records (`id`, `userId`, `jobId`, `location`, `createdAt`, `status`).
- **Frontend Mitigation:** `api.getAdminSosAlerts` catches 404 and safely returns an empty list `[]` without disrupting the admin dashboard.
- **Recommendation:** Add `GET /admin/sos` with `require_role(["admin"])` that lists documents from `sos_alerts` sorted by `createdAt` descending.

### 3.4 Two-Step Job Completion Confirmation (`confirmJob`)
- **Affected File:** `routers/jobs.py` and `services/job_service.py`
- **Current Backend Contract:** `POST /jobs/{id}/complete` moves `in_progress -> completed` directly and immediately increments worker's `jobsDone`.
- **Frontend Expectation:** Two-step confirmation (`awaiting_confirmation -> confirmJob() -> completed`).
- **Frontend Mitigation:** `api.confirmJob(jobId)` handles 404 by fetching `GET /jobs/{jobId}`. If the job is already completed by the worker, the customer UI renders the completed screen with the review button.
- **Recommendation:** Add `POST /jobs/{id}/confirm` and `awaiting_confirmation` status to `services/job_service.py` when two-step completion is activated.

### 3.5 Local Test Suite Fail-Fast Credential Monkeypatch
- **Affected File:** `tests/test_database.py` line 109
- **Current Backend Test:** `test_production_fail_fast_without_credentials` monkeypatches `_use_mock = False` and `_firestore_client = None`, but does not mock `settings.FIREBASE_CREDENTIALS_PATH`. On developer machines where `firebase_credentials.json` is present locally, Firestore initializes credentials instead of failing fast.
- **Recommendation:** Update test fixture in `tests/test_database.py`:
  ```python
  monkeypatch.setattr(settings, "FIREBASE_CREDENTIALS_PATH", "")
  ```
