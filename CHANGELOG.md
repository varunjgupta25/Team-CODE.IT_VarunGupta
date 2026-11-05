# Changelog

All notable changes to RepairBuddy are documented here.

---

## [Unreleased] — 2026-11-05

### Security & Compliance — Worker ID & Selfie Verification (Fix 3)

**Problem:** Worker verification previously stored only docType + last-4 digits with no real document upload, no selfie verification, no reject-with-reason, and `/admin/verifications/pending` leaked full worker documents.

**Fix:**
- `services/storage_provider.py` *(new)* — DPDP-compliant private object storage abstraction (`LocalStorageProvider` and `FirebaseStorageProvider`). No permanent public URLs.
- `services/image_utils.py` *(new)* — Validates magic bytes (blocks spoofed extensions), enforces max 5MB, verifies via Pillow, re-encodes clean image to strip all EXIF metadata.
- `routers/workers.py` — `POST /workers/verify/upload` accepts ID card photo + live selfie, document type, document number (stores only last-4 digits masked).
- Rate limits enforced: max 5 submissions per worker per 24 hours; max 3 rejections before account is locked pending admin reset.
- `routers/admin.py` —
  - `GET /admin/verifications/pending` returns a trimmed DTO (`uid`, `name`, `docType`, `last4`, `submittedAt`, `attemptCount`, `status`) to prevent data leakage.
  - `GET /admin/verifications/{uid}/documents/{doc_type}` streams document images directly with admin authentication. Non-admins or cross-worker access gets 403.
  - `POST /admin/verifications/{uid}/approve` approves worker, permanently deletes stored images, and writes an immutable audit record to `verification_audits`.
  - `POST /admin/verifications/{uid}/reject` requires a mandatory reason, sets status to `rejected`, deletes images, increments rejectionCount, and writes audit record.
  - `POST /admin/verifications/{uid}/reset_attempts` unlocks worker if maximum rejections reached.
- Frontend: `VerificationCard.jsx` supports ID + selfie upload with live preview, displays rejection reasons with resubmission form; `AdminPage.jsx` includes document inspection modal with approve and reject-with-reason dialog. Mock mode in `mockStore.js` and `api/index.js` mirrored.
- Tests: 10 new pytest cases in `tests/test_verification_uploads.py` covering uploads, magic bytes, spoofing, oversized files, auth, rate limiting, trimmed DTOs, streaming authorization, image deletion, and audit logging.

---

### Security — Firebase Auth Hardening

**Problem:** `core/auth.py` had a dev-token fallthrough (`token-customer-<uid>`, `token-worker-<uid>`, `token-admin-<uid>`, `dev-`, `mock-` prefixes) that was never gated on ENV. `render.yaml` set `USE_MOCK_FIREBASE=true` in production, so `Bearer admin_user` worked on the live API.

**Fix:**
- `core/auth.py` — completely rewritten. Dev convenience (direct UID DB lookup) gated on **both** `ENV=development AND USE_MOCK_FIREBASE=true`. Any other config → strict Firebase `verify_id_token()`, no fallthrough.
- Removed: all `id_aliases` dicts, `token-customer-/token-worker-/token-admin-/dev-/mock-` prefix stripping.
- Admin role: **only** via Firebase custom claim `{'admin': True}`. Never auto-promoted from DB alone in production.
- `scripts/set_admin.py` — new script; the only blessed path to grant admin.
- `render.yaml` — `USE_MOCK_FIREBASE=false`, `AUTO_SEED=false`, `ENV=production`.
- `core/database.py` — `FIREBASE_CREDENTIALS_JSON` env var support (JSON string, ideal for Render secrets).

**Files changed:** `core/auth.py`, `core/config.py`, `core/database.py`, `render.yaml`, `.env.example`, `scripts/set_admin.py` *(new)*

---

### Security — Registration Endpoint Hardening

**Problem:** `POST /customers/register` and `POST /workers/register` were unauthenticated and trusted a client-supplied `uid`, allowing overwrite of any existing user/worker document including `admin_user`. Role and verification fields could be changed by anyone.

**Fix:**
- Both endpoints now **require** a valid Bearer token. `uid` is taken from the verified token; any `uid` in the request body is ignored.
- Registration blocked if a document already exists for that UID (no overwrite).
- `role`, `verified`, `rating`, `trustScore` are immutable after first registration — cannot be changed via re-registration.
- `routers/workers.py` PATCH `/workers/{id}` — added caller authorization (worker can only update own document; admin can update any).

**Files changed:** `routers/workers.py`, `routers/jobs.py` (customer register section)

---

### Feature — Two-Step Job Completion

**Problem:** Worker alone could set status `completed` and increment `jobsDone`, which feeds trust score. No customer confirmation window. Guard `acceptedWorkerId is None` let any worker start/complete unassigned jobs.

**Fix:**

New job state: `awaiting_confirmation` inserted between `in_progress` and `completed`.

| Step | Caller | Endpoint | Transition | jobsDone |
|------|--------|----------|------------|----------|
| Worker marks done | Worker | `POST /jobs/{id}/complete` | `in_progress → awaiting_confirmation` | ❌ not incremented |
| Customer confirms | Customer | `POST /jobs/{id}/confirm` *(new)* | `awaiting_confirmation → completed` | ✅ incremented once |
| Auto-confirm | system | lazy, on read/list | `awaiting_confirmation → completed` after `AUTO_CONFIRM_HOURS` (default 48h) | ✅ incremented once |

- Second call to `/confirm` on an already-completed job is a no-op (no double increment).
- `start_job()` tightened: `acceptedWorkerId` must be non-None AND match caller.
- `complete_job()` tightened: same guard.
- Reviews still require `completed` status (after confirmation).
- Cancel still blocked on `completed` jobs.

**Files changed:** `services/job_service.py`, `routers/jobs.py`, `models/job.py`

---

### Feature — Firebase Phone Auth (Frontend)

- `frontend/src/lib/firebase.js` *(new)* — Firebase Web SDK wrapper: `setupRecaptcha`, `sendPhoneOtp`, `verifyPhoneOtp`, `getFreshIdToken`, `signOutFirebase`.
- `frontend/src/api/client.js` — interceptor now awaits `getFreshIdToken()` (auto-refresh) before falling back to localStorage `rb_auth_token`.
- `frontend/src/store/authStore.js` — `requestPhoneOtp`/`confirmPhoneOtp` wired to Firebase; `logout()` calls `signOutFirebase()`; no more hardcoded `token-customer-` prefixed tokens.
- `frontend/src/pages/AuthPage.jsx` — reCAPTCHA container; supports Firebase (6-digit OTP) and mock (4-digit) flows.

**Files changed:** `frontend/src/lib/firebase.js` *(new)*, `frontend/src/api/client.js`, `frontend/src/store/authStore.js`, `frontend/src/pages/AuthPage.jsx`

---

### Feature — Customer Confirmation UI

- `frontend/src/pages/customer/JobStatusPage.jsx` — "Confirm job done" button panel shown when status is `awaiting_confirmation`.
- `frontend/src/pages/worker/WorkerJobDetailsPage.jsx` — "Awaiting Customer Confirmation" status panel.
- `frontend/src/api/index.js` — `confirmJob(jobId)` added.
- `frontend/src/api/mockStore.js` — `completeJob()` → `AWAITING_CONFIRMATION`; `confirmJob()` → `COMPLETED`.
- `frontend/src/types/index.js` — `AWAITING_CONFIRMATION` added to `JOB_STATUS`.
- `frontend/src/pages/customer/CustomerHome.jsx`, `frontend/src/components/common/BottomNav.jsx` — `hasActiveJob` includes `awaiting_confirmation`.

---

### Tests — New (13 added, total: 108)

**`tests/test_auth_roles.py`** (+4):
- `test_production_env_rejects_dev_and_fake_tokens` — proves prod mode rejects all dev-format tokens with 401.
- `test_registration_requires_valid_token_and_ignores_body_uid`
- `test_registration_role_immutability_and_overwrite_protection`
- `test_user_cannot_become_admin_without_firebase_claim`

**`tests/test_two_step_completion.py`** *(new, +9)*:
- `test_worker_complete_moves_to_awaiting_confirmation_and_does_not_increment_jobs_done`
- `test_customer_confirm_moves_to_completed_and_increments_jobs_done`
- `test_confirm_second_call_does_not_double_increment`
- `test_unauthenticated_and_worker_and_other_customers_cannot_confirm`
- `test_accepted_worker_none_blocks_start_and_complete`
- `test_auto_confirm_after_configured_hours_applied_lazily_on_read`
- `test_auto_confirm_after_configured_hours_applied_lazily_on_listing`
- `test_reviews_blocked_on_awaiting_confirmation_and_allowed_after_confirm`
- `test_cancel_blocked_on_completed_job`

**`tests/conftest.py`** — `isolated_db` fixture now saves/restores `settings.USE_MOCK_FIREBASE` and `settings.ENV` to prevent `.env` file from poisoning test mode.

**`tests/test_lifecycle.py`**, **`tests/test_e2e_flow.py`** — updated for two-step completion flow.

---

### Scripts — Token Format Update

All integration scripts updated from `token-customer-<uid>` / `token-worker-<uid>` / `token-admin-<uid>` → plain UID (dev mode) or comment updated:

- `scripts/e2e_deployed.py`
- `scripts/local_integration_test.py`
- `scripts/verify_live_flow.py`
- `scripts/verify_verification_security.py`

Also updated lifecycle in scripts to match two-step completion (`complete → awaiting_confirmation`, `confirm → completed`).

---

### Manual Steps Checklist (Firebase Setup)

- [ ] Create Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
- [ ] Enable **Phone** sign-in provider under Authentication
- [ ] Add test numbers: `+91 9999900001` → OTP `123456` and `+91 9999900002` → OTP `123456`
- [ ] Create a Web App in Firebase → copy `apiKey`, `authDomain`, `projectId`, `appId`
- [ ] Add to `frontend/.env.local` (never commit): `VITE_FIREBASE_API_KEY=...` etc.
- [ ] Add same vars to Vercel project environment variables
- [ ] Generate service account key (Project Settings → Service Accounts → Generate new private key)
- [ ] In Render: set `FIREBASE_CREDENTIALS_JSON` = *(paste entire JSON content)*, mark as **secret/sync:false**
- [ ] Set `USE_MOCK_FIREBASE=false` and `ENV=production` in Render environment
- [ ] After first deploy: `python scripts/set_admin.py <your-firebase-uid>` to grant admin claim
- [ ] Verify: `Bearer admin_user` on the live API returns **401** ✅

---

### Verification Commands

```bash
# Full test suite (should show 108 passed)
pytest -v

# Grep for forbidden patterns in non-test backend code
grep -rn "id_aliases\|token-customer\|w_plumb" --include="*.py" core/ routers/ services/ scripts/
# Expected: no output

# Frontend build
cd frontend && npm run build
# Expected: ✓ built in ~11s, no errors

# Local e2e against running server
python scripts/e2e_deployed.py http://127.0.0.1:8000
```

