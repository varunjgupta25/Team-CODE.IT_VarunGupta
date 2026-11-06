# Blockers, Gaps, and Backend Recommendations Report
**Project:** RepairBuddy  
**Phase:** 3 — Frontend Integration & Verification  
**Audience:** Backend Engineering Agent / Team  
**Status:** REPORTED (No backend files modified by Phase 3)

---

## 1. Compliance Notice
As mandated by the Phase 3 Codebase Protection Rules, **the backend codebase was kept strictly untouched** during this frontend workstream. All discovered backend discrepancies have been buffered within the frontend API adapter layer (`frontend/src/api/index.js`), and are formally documented below for backend implementation.

---

## 2. Discovered Backend Discrepancies & Recommendations

### Item 1: Worker Document & Live Selfie Upload Endpoint
- **Affected File:** `routers/workers.py`
- **Current Backend Contract:** Only exposes `POST /workers/verify`, accepting `{ documentType: str, documentNumber: str }`.
- **Frontend Expectation:** `VerificationCard.jsx` collects multipart form data containing:
  - `documentType` (e.g. `aadhaar`, `pan`)
  - `documentNumber` (12 or 10 digits)
  - `id_document` (binary file, JPEG/PNG up to 5MB)
  - `selfie` (binary file, JPEG/PNG up to 5MB)
- **Frontend Mitigation:** If `POST /workers/verify/upload` returns 404, `api.uploadWorkerVerification` automatically falls back to `POST /workers/verify` with `{ documentType, documentNumber }`.
- **Required Backend Action:** Implement `POST /workers/verify/upload` with `fastapi.UploadFile` handling, magic bytes inspection, and private DPDP-compliant disk storage.

---

### Item 2: User Emergency Contact Endpoint
- **Affected File:** `routers/jobs.py` (or new `routers/users.py`)
- **Current Backend Contract:** No endpoint mounted for `/users/me/emergency-contact`.
- **Frontend Expectation:**
  - `PUT /users/me/emergency-contact` with `{ name: str, phone: str }`
  - `GET /users/me/emergency-contact` returning `{ name, phone }`
- **Frontend Mitigation:** `api.setEmergencyContact` and `api.getEmergencyContact` persist and retrieve contacts via `localStorage` (`rb_emergency_contact`) when the backend returns 404.
- **Required Backend Action:** Add `PUT` and `GET` routes on `/users/me/emergency-contact` to persist emergency contacts on the user document in Firestore.

---

### Item 3: Admin Emergency SOS Alerts Feed
- **Affected File:** `routers/sos.py` or `routers/admin.py`
- **Current Backend Contract:** `POST /sos` records alerts in `sos_alerts`, but no endpoint exists to retrieve them.
- **Frontend Expectation:** `GET /admin/sos` returning list of recent SOS records (`id`, `userId`, `jobId`, `location`, `createdAt`, `status`).
- **Frontend Mitigation:** `api.getAdminSosAlerts` catches 404 and safely returns an empty list `[]` without disrupting the admin dashboard.
- **Required Backend Action:** Add `GET /admin/sos` with `require_role(["admin"])` that lists documents from `sos_alerts` sorted by `createdAt` descending.

---

### Item 4: Two-Step Job Completion Confirmation (`confirmJob`)
- **Affected File:** `routers/jobs.py` and `services/job_service.py`
- **Current Backend Contract:** `POST /jobs/{id}/complete` moves `in_progress -> completed` directly and immediately increments worker's `jobsDone`.
- **Frontend Expectation:** Two-step confirmation:
  1. Worker marks done -> `awaiting_confirmation`
  2. Customer inspects work & pays cash -> `POST /jobs/{id}/confirm` -> `completed`
- **Frontend Mitigation:** `api.confirmJob(jobId)` handles 404 by fetching `GET /jobs/{jobId}`. If the job is already completed by the worker, the customer UI renders the completed screen with the review button.
- **Required Backend Action:** Add `POST /jobs/{id}/confirm` and `awaiting_confirmation` status to `services/job_service.py` when two-step completion is activated.

---

### Item 5: Local Test Suite Fail-Fast Credential Monkeypatch
- **Affected File:** `tests/test_database.py` line 109
- **Current Backend Test:** `test_production_fail_fast_without_credentials` monkeypatches `_use_mock = False` and `_firestore_client = None`, but does not mock `settings.FIREBASE_CREDENTIALS_PATH`. On developer machines where `firebase_credentials.json` is present locally, Firestore initializes credentials instead of failing fast.
- **Required Backend Action:** Update test fixture in `tests/test_database.py`:
  ```python
  monkeypatch.setattr(settings, "FIREBASE_CREDENTIALS_PATH", "")
  ```
