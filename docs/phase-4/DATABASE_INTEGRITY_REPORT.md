# Phase 4 — Database Integrity Report

## 1. Shared Database Architecture

The backend utilizes a **single shared Google Cloud Firestore database** (or its in-memory thread-safe mock adapter during testing). Both Customer App and Partner App read from and write to the exact same collections, eliminating data replication and distributed sync problems.

---

## 2. Shared Collections & Schema Invariants

| Collection | Written By | Read By | Key Invariants Enforced |
|---|---|---|---|
| `users` | Customers, Workers, Admin | Self, Admin | Single account per `uid`; duplicate registrations return `409 Conflict` |
| `workers` | Workers, Admin | Public/Masked, Self, Admin | `serviceRadiusKm` clamped (1–50 km); `verified` status controlled solely by Admin |
| `jobs` | Customers | Customers, Assigned Worker, Admin | Strict status progression: `open` -> `negotiating` -> `accepted` -> `in_progress` -> `completed` |
| `offers` | Workers, Customers | Job Owner, Proposing Worker, Admin | Acceptance atomically transitions job and auto-rejects all competing offers |
| `reviews` | Customers | Public, Self, Admin | Exactly 1 review permitted per customer per completed job (duplicate blocked) |
| `reports` | Customers, Workers | Admin | Submitting >= 3 reports within 48h triggers automatic `isFlagged` & `UNDER_REVIEW` |
| `sos_alerts` | Customers, Workers | Admin | Immediate timestamped snapshot with caller location |

---

## 3. Transactional Integrity & State Transition Safeguards

1. **Atomic Offer Acceptance**:
   - When a customer accepts an offer via `POST /offers/{id}/accept`:
     - The selected offer is updated to `status: "accepted"`.
     - The corresponding job is updated to `status: "accepted"`, `acceptedWorkerId: offer.workerId`, `finalPrice: offer.price`.
     - All competing pending offers for that `jobId` are atomically set to `status: "rejected"`.
2. **Strict Job State Machine**:
   - `start_job()` can ONLY be invoked if current status is `"accepted"`. Invalid transitions raise `400 Bad Request`.
   - `complete_job()` can ONLY be invoked if current status is `"in_progress"`.
   - `cancel_job()` is rejected if the job has already reached `"completed"` status.
3. **Review Eligibility Guard**:
   - Reviews are strictly rejected with `400 Bad Request` unless the job status is `"completed"` and the reviewer is the verified customer who posted the job.

---

## 4. Verification Evidence

Validated through automated integration suites:
- `tests/test_phase4_app_separation.py::test_shared_service_e2e_customer_to_partner_lifecycle`
- `tests/test_phase3_integration.py::test_competing_offers_atomic_rejection`
- `tests/test_reviews_safety.py`
- `tests/test_lifecycle.py`

