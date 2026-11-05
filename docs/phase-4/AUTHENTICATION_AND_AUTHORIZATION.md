# Phase 4 — Authentication and Authorization Report

## 1. Authentication Architecture

Both the **Customer App** and the **Partner App** (Worker + Admin Console) authenticate using the **same Firebase Authentication project**. 

### Core Principles
1. **Cryptographic Token Verification**:
   - Clients send `Authorization: Bearer <firebase_id_token>` on every protected request.
   - The backend validates the signature, issuer (`iss`), expiration (`exp`), and audience (`aud`) using `firebase_admin.auth.verify_id_token()`.
2. **Server-Side Identity Derivation**:
   - The authenticated user ID (`uid`) is derived exclusively from the token's `sub` or `uid` claim.
   - Client-provided `uid` fields in request payloads (e.g. `POST /customers/register` or `POST /workers/register`) are explicitly ignored.
3. **Server-Side Role Authority**:
   - User roles (`customer`, `worker`, `admin`) are determined from verified Firebase custom claims or server-side database records in the `users` collection.
   - The backend **never** trusts client-submitted role fields in request bodies.
4. **Origin Independence**:
   - HTTP `Origin` headers govern browser cross-origin preflight requests (CORS) only.
   - An origin header **never confers permissions**. A customer cannot access worker/admin endpoints simply by issuing requests with a Partner App origin header, and vice-versa.

---

## 2. Role-Based Access Control (RBAC) Matrix

| Endpoint Group | Permitted Roles | Unauthorized Behavior |
|---|---|---|
| `/jobs` (Create) | `customer`, `admin` | `worker` receives `403 Forbidden` |
| `/jobs/nearby` (Worker Feed) | `worker`, `admin` | `customer` receives `403 Forbidden` |
| `/jobs/{id}/start`, `/complete` | `worker`, `admin` | `customer` receives `403 Forbidden`; non-assigned worker receives `400/403` |
| `/jobs/{id}/cancel` | `customer`, `admin` | Non-owner customer receives `403 Forbidden` |
| `/offers` (Submit proposal) | `customer`, `worker` | Authenticated users only; role-checked per context |
| `/offers/{id}/accept` | `customer`, `admin` | Non-job-owner customer receives `403 Forbidden` |
| `/workers/verify` (Request ID verification) | `worker` | `customer` receives `403 Forbidden` |
| `/workers/{id}` (Update profile/availability) | `worker`, `admin` | Non-owner worker receives `403 Forbidden` |
| `/admin/*` (All admin endpoints) | `admin` | `customer` & `worker` receive `403 Forbidden` |
| `/reports` (Safety reporting) | `customer`, `worker`, `admin` | Authenticated users only |

---

## 3. Strict Development Environment Gating

In `core/auth.py`:
- Mock/dev tokens (`token-customer-*`, `token-worker-*`, `token-admin-*`, raw seed UIDs) are permitted **strictly** when `ENV == "development"`.
- If `ENV in ["production", "staging"]`, any non-JWT token is immediately rejected with `401 Unauthorized` ("Dev tokens strictly prohibited in non-development environments").

