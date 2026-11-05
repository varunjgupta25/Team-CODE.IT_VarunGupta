# API INVENTORY & ENDPOINT SPECIFICATION AUDIT

**Audit Date:** 2026-11-05  
**Service:** RepairBuddy FastAPI Backend  
**Base URLs:**  
* Root Mount: `https://repair-buddy.onrender.com/`  
* API Namespace Mount: `https://repair-buddy.onrender.com/api/`  
* API Specification: OpenAPI 3.1 (`/docs`, `/openapi.json`)

---

## 1. Global Route Mounting & Prefix Compatibility

All functional routers are mounted in `main.py` under both the root prefix `""` and the `/api` prefix to ensure 100% backward compatibility across disparate frontend client builds:
```python
for prefix in ["", "/api"]:
    app.include_router(health_router, prefix=prefix)
    app.include_router(jobs_router, prefix=prefix)
    app.include_router(workers_router, prefix=prefix)
    app.include_router(offers_router, prefix=prefix)
    app.include_router(reviews_router, prefix=prefix)
    app.include_router(sos_router, prefix=prefix)
    app.include_router(reports_router, prefix=prefix)
    app.include_router(admin_router, prefix=prefix)
    app.include_router(route_router, prefix=prefix)
```

---

## 2. Categorized Endpoint Inventory

### Category 1: System Health & Discovery

| Method | Endpoint Path | Authentication | Required Role | Request Schema | Response Schema | DB Access | Status |
|---|---|---|---|---|---|---|---|
| `GET` | `/health` | None (Public) | Any | None | `{"status": str, "service": str, "mock_mode": bool, "transit_speed_kmh": float}` | Read (config check) | **Operational** |
| `GET` | `/` | None (Public) | Any | None | `{"service": str, "version": str, "status": str, "documentation": str, "health": str, "frontend": str}` | None | **Operational** |

---

### Category 2: Registration & Identity Management

| Method | Endpoint Path | Authentication | Required Role | Request Schema | Response Schema | DB Access | Status |
|---|---|---|---|---|---|---|---|
| `POST` | `/customers/register` | Required (Bearer) | Any authenticated | `CustomerRegisterRequest` (`name`, `phone`, `location`, `language`) | `UserResponse` | Read-check + Write (`users`) | **Operational** (409 on duplicate, ignores body UID) |
| `POST` | `/register` | Required (Bearer) | Any authenticated | `CustomerRegisterRequest` | `UserResponse` | Read-check + Write (`users`) | **Operational** (Alias to customer register) |
| `POST` | `/workers/register` | Required (Bearer) | Any authenticated | `WorkerRegisterRequest` (`name`, `phone`, `skills`, `rates`, etc.) | `Dict[str, Any]` (Worker document) | Read-check + Write (`workers`, `users`) | **Operational** (409 on duplicate, token UID enforced) |

---

### Category 3: Worker Management, Feed & Privacy

| Method | Endpoint Path | Authentication | Required Role | Request Schema | Response Schema | DB Access | Status |
|---|---|---|---|---|---|---|---|
| `GET` | `/workers/feed` | Required (Bearer) | Any | Query params: None | `List[Dict[str, Any]]` | Read (`workers`) | **Operational** (Filters out flagged / `UNDER_REVIEW`, obfuscates address & coords) |
| `GET` | `/workers` | Required (Bearer) | Any | Query params: None | `List[Dict[str, Any]]` | Read (`workers`) | **Operational** (Alias to `/workers/feed`) |
| `GET` | `/workers/{worker_id}` | Required (Bearer) | Any | Path: `worker_id` | `Dict[str, Any]` | Read (`workers`) | **Operational** (Masks phone/address for non-owners, unmasks for owner/admin) |
| `PATCH` | `/workers/{worker_id}` | Required (Bearer) | Worker, Admin | `WorkerAvailabilityPayload` (`isAvailableNow: bool`) | `{"status": str, "workerId": str, "isAvailableNow": bool}` | Read + Update (`workers`) | **Operational** (Enforces owner UID match, returns 403 on mismatch) |

---

### Category 4: Worker Matching Engine

| Method | Endpoint Path | Authentication | Required Role | Request Schema | Response Schema | DB Access | Status |
|---|---|---|---|---|---|---|---|
| `GET` | `/workers/match` | Required (Bearer) | Customer, Admin | Query: `jobId` (str) | `List[MatchedWorkerResponse]` | Read (`jobs`, `workers`, `reports`) | **Operational** (Haversine + H3 + Dijkstra ETA, composite scoring, N+1 eliminated) |

---

### Category 5: Job Lifecycle Management

| Method | Endpoint Path | Authentication | Required Role | Request Schema | Response Schema | DB Access | Status |
|---|---|---|---|---|---|---|---|
| `POST` | `/jobs` | Required (Bearer) | Customer, Admin | `JobCreate` (`category`, `description`, `address`, `location`, `budget`, `mode`) | `JobResponse` | Read-check + Write (`jobs`) | **Operational** (Strict category whitelist, length caps) |
| `GET` | `/jobs/nearby` | Required (Bearer) | Worker, Admin | Query: None | `List[JobResponse]` | Read (`jobs`) | **Operational** (Filters `open` jobs matching worker skill & radius) |
| `GET` | `/jobs/{id}` | Required (Bearer) | Customer, Worker, Admin | Path: `id` | `JobResponse` | Read (`jobs`) | **Operational** (Access limited to job owner, assigned worker, or admin) |
| `POST` | `/jobs/{id}/start` | Required (Bearer) | Worker, Admin | Path: `id` | `JobStartCompleteResponse` | Read + Update (`jobs`) | **Operational** (Guards unassigned worker with 400, checks role) |
| `POST` | `/jobs/{id}/complete` | Required (Bearer) | Worker, Admin | Path: `id` | `JobStartCompleteResponse` | Atomic Tx Read + Update (`jobs`, `workers`) | **Operational** (Guards unassigned worker with 400, increments `jobsDone`) |
| `POST` | `/jobs/{id}/cancel` | Required (Bearer) | Customer, Admin | Path: `id` | `JobCancelResponse` | Atomic Tx Read + Update (`jobs`) | **Operational** (Rejects cancel once in progress or completed) |

---

### Category 6: Offer Negotiation (Price Bargaining State Machine)

| Method | Endpoint Path | Authentication | Required Role | Request Schema | Response Schema | DB Access | Status |
|---|---|---|---|---|---|---|---|
| `POST` | `/offers` | Required (Bearer) | Customer, Worker, Admin | `OfferCreate` (`jobId`, `workerId`, `proposedPrice`, `by`, `note`) | `OfferResponse` | Read + Write (`offers`, `jobs`) | **Operational** (Validates role, checks existing pending offers) |
| `GET` | `/offers` | Required (Bearer) | Customer, Worker, Admin | Query: `jobId` (str) | `List[OfferResponse]` | Read (`offers`) | **Operational** (Lists offers for a specific job) |
| `GET` | `/offers/{id}` | Required (Bearer) | Customer, Worker, Admin | Path: `id` | `OfferResponse` | Read (`offers`) | **Operational** (Returns specific offer details) |
| `POST` | `/offers/{id}/counter` | Required (Bearer) | Customer, Worker, Admin | Path: `id`, Body: `OfferCounter` (`proposedPrice`, `note`) | `OfferResponse` | Read + Write (`offers`) | **Operational** (Enforces strict turn-taking alternating counter-offers) |
| `POST` | `/offers/{id}/accept` | Required (Bearer) | Customer, Worker, Admin | Path: `id` | `OfferResponse` | Atomic Tx (`offers`, `jobs`) | **Operational** (Sets offer `accepted`, sets job `assigned`, marks `acceptedWorkerId`, rejects competing offers) |
| `POST` | `/offers/{id}/reject` | Required (Bearer) | Customer, Worker, Admin | Path: `id` | `OfferResponse` | Read + Update (`offers`) | **Operational** (Transitions status to `rejected`) |

---

### Category 7: Reviews & Customer Feedback

| Method | Endpoint Path | Authentication | Required Role | Request Schema | Response Schema | DB Access | Status |
|---|---|---|---|---|---|---|---|
| `POST` | `/reviews` | Required (Bearer) | Customer, Admin | `ReviewCreate` (`jobId`, `workerId`, `rating`, `comment`) | `ReviewResponse` | Atomic Tx (`reviews`, `workers`) | **Operational** (Requires job completion, updates worker Bayesian rating & reviewCount) |

---

### Category 8: Worker Verification & Admin Queue

| Method | Endpoint Path | Authentication | Required Role | Request Schema | Response Schema | DB Access | Status |
|---|---|---|---|---|---|---|---|
| `POST` | `/workers/verify` | Required (Bearer) | Worker | `WorkerVerifyRequest` (`documentType`, `documentNumber`) | `WorkerVerifyResponse` | Read + Update (`workers`) | **Operational** (Masks document `XXXX-XXXX-1234`, sets status to `pending`) |
| `GET` | `/admin/verifications` | Required (Bearer) | Admin | None | `List[PendingVerificationWorker]` | Read (`workers`) | **Operational** (Returns queue without unmasked document numbers) |
| `GET` | `/admin/verifications/pending` | Required (Bearer) | Admin | None | `List[Dict[str, Any]]` | Read (`workers`) | **Operational** (Lists unverified workers) |
| `POST` | `/admin/verifications/{uid}/approve` | Required (Bearer) | Admin | Path: `uid` | `AdminApproveResponse` | Read + Update (`workers`) | **Operational** (Sets `verified=True`, `verificationStatus="verified"`) |

---

### Category 9: Safety & Incident Reporting

| Method | Endpoint Path | Authentication | Required Role | Request Schema | Response Schema | DB Access | Status |
|---|---|---|---|---|---|---|---|
| `POST` | `/reports` | Required (Bearer) | Customer, Worker, Admin | `ReportCreate` (`workerId`, `reason`, `category`, `jobId`) | `ReportResponse` | Read + Write (`reports`, `workers`) | **Operational** (Records category, evaluates abuse threshold $\ge 3$ in 48h to set `UNDER_REVIEW`) |
| `POST` | `/sos` | Required (Bearer) | Customer, Worker, Admin | `SOSCreate` (`jobId`, `location`, `reason`) | `SOSResponse` | Read + Write (`sos_alerts`) | **Operational** (Rate limited to 5 req/min, logs emergency event) |

---

### Category 10: Road Network Routing

| Method | Endpoint Path | Authentication | Required Role | Request Schema | Response Schema | DB Access | Status |
|---|---|---|---|---|---|---|---|
| `GET` | `/route` | Required (Bearer) | Customer, Worker, Admin | Query: `jobId`, `workerId` | `RouteResponse` (`distanceKm`, `etaMinutes`, `polyline`) | Read (`jobs`, `workers`) | **Operational** (OSM graph Dijkstra traversal; verifies caller is participant or admin) |

---

## 3. Findings & Inventory Summary

* **Total Registered Endpoints:** 23 endpoints (accessible via 46 URL routes counting dual `/` and `/api/` prefix mounting).
* **Missing Endpoints:** 0 endpoints missing from PRD specifications.
* **Unauthenticated Exposure:** Only `/health` and `/` are public. All 21 functional operational routes require valid Bearer token authentication.
* **Role Mismatches:** None detected. Role permissions are enforced via `require_role(...)` or verified within service authorization blocks.

