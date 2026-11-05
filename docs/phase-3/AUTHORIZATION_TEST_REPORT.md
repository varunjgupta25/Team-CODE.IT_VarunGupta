# Authorization Test Report — Phase 3

## 1. Authentication Layer Guarantees

In [`core/auth.py`](file:///c:/Users/Kashish/OneDrive/Desktop/Backend/core/auth.py):
- **Zero 401 Fallthrough**: Missing headers, empty tokens, or malformed strings raise `401 Unauthorized` immediately.
- **Environment Gating**: Dev tokens (`cust_*`, `worker_*`, `token-*`) are strictly prohibited unless `ENV == "development"`. In non-development environments, dev tokens fail with `401`.
- **Production Verification**: Real Firebase ID tokens are decoded and cryptographically verified against Firebase Admin Auth.

---

## 2. Role-Based Access Control (RBAC) Test Matrix

| Resource / Endpoint | Customer Role | Worker Role | Admin Role | Unauthenticated |
|---|---|---|---|---|
| `POST /jobs` | **ALLOW (201)** | **DENY (403)** | **ALLOW (201)** | **DENY (401)** |
| `GET /jobs/nearby` | **DENY (403)** | **ALLOW (200)** | **ALLOW (200)** | **DENY (401)** |
| `POST /jobs/{id}/start` | **DENY (403)** | **ALLOW (200)** (Assigned worker) | **ALLOW (200)** | **DENY (401)** |
| `POST /jobs/{id}/complete` | **DENY (403)** | **ALLOW (200)** (Assigned worker) | **ALLOW (200)** | **DENY (401)** |
| `POST /jobs/{id}/cancel` | **ALLOW (200)** (Job owner) | **DENY (403)** | **ALLOW (200)** | **DENY (401)** |
| `POST /workers/verify` | **DENY (403)** | **ALLOW (200)** | **DENY (403)** | **DENY (401)** |
| `POST /reviews` | **ALLOW (201)** (Job owner) | **DENY (403)** | **ALLOW (201)** | **DENY (401)** |
| `GET /admin/verifications` | **DENY (403)** | **DENY (403)** | **ALLOW (200)** | **DENY (401)** |
| `POST /admin/verifications/{uid}/approve` | **DENY (403)** | **DENY (403)** | **ALLOW (200)** | **DENY (401)** |
| `GET /admin/stats` | **DENY (403)** | **DENY (403)** | **ALLOW (200)** | **DENY (401)** |
| `GET /admin/reports` | **DENY (403)** | **DENY (403)** | **ALLOW (200)** | **DENY (401)** |
| `POST /admin/users/{uid}/suspend` | **DENY (403)** | **DENY (403)** | **ALLOW (200)** | **DENY (401)** |

---

## 3. Resource Ownership Checks Verified

1. **Worker Profile Ownership**:
   - `PATCH /workers/{worker_id}`: Verifies that caller's `uid` matches `owner_uid` or `worker.uid`. Non-owner workers receive `403 Forbidden`. Admins bypass this check.
2. **Worker Earnings Privacy**:
   - `GET /workers/{worker_id}/earnings`: Only the worker themselves or an admin can access financial records (`403 Forbidden` for other callers).
3. **Customer Profile Updates**:
   - `PATCH /customers/{customer_id}`: Only the registered customer or an admin can update profile details (`403 Forbidden` on mismatch).
4. **Job Detail Address Masking**:
   - `GET /jobs/{id}`: Unassigned workers cannot inspect the customer's exact street address until their offer is accepted.

