# Database Persistence Report — Phase 3

## 1. Storage Abstraction Overview

In [`core/database.py`](file:///c:/Users/Kashish/OneDrive/Desktop/Backend/core/database.py):
The backend communicates with a unified `FirestoreDB` adapter that switches transparently between:
- **Production Mode**: Real Google Cloud Firestore via `google-cloud-firestore`.
- **Test / Mock Mode**: Thread-safe in-memory collections with an atomic transaction manager (`TransactionContext`).

---

## 2. Verified Collections & Document Shapes

| Collection | Key Prefix | Primary Identifiers | Key Indexed Fields |
|---|---|---|---|
| `users` | `cust_` / `admin_` | `uid` | `uid`, `role`, `accountStatus` |
| `workers` | `worker_` | `uid` | `skills`, `verified`, `isAvailableNow`, `accountStatus` |
| `jobs` | `job_` | `id` | `status`, `category`, `createdAt`, `acceptedWorkerId` |
| `offers` | `off_` | `id` | `jobId`, `status`, `createdAt`, `workerId` |
| `reviews` | `rev_` | `id` | `jobId`, `workerId`, `customerId` |
| `reports` | `rep_` | `id` | `workerId`, `status`, `createdAt` |
| `sos_alerts`| `sos_` | `id` | `jobId`, `userId`, `createdAt` |

---

## 3. Transaction Safety & Atomic Mutations

All multi-document state transitions use `db.run_transaction()`:
1. **Offer Acceptance**:
   - Updates target offer status to `"accepted"`.
   - Transitions job status from `"negotiating"` to `"accepted"`.
   - Assigns `acceptedWorkerId` and locks `finalPrice`.
   - Automatically queries and transitions all other pending offers on the job to `"rejected"`.
2. **Job Completion**:
   - Transitions job status from `"in_progress"` to `"completed"`.
   - Atomically increments worker's `jobsDone` counter.
3. **Review Submission**:
   - Ensures job status is `"completed"`.
   - Prevents duplicate reviews for the same `jobId`.
   - Atomically recalculates worker rolling average rating.

