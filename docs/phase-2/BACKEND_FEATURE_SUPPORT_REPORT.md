# Backend Feature Support Report — Phase 2

## Executive Summary
This report documents the backend stabilization and feature extensions delivered to support RepairBuddy's Phase 2 frontend integration across Customer, Worker, and Admin interfaces. All additions strictly preserve the existing FastAPI service-layer pattern, transactional data integrity, and Firestore compatibility without introducing unvetted frameworks or breaking existing API contracts.

---

## 1. Customer API Support

| Feature | Endpoint | HTTP Method | Status | Notes |
|---|---|---|---|---|
| Profile Retrieval | `/customers/{customer_id}` | `GET` | **IMPLEMENTED** | Privacy-aware: non-owners receive masked phone number (`+91 98201 *****`). |
| Profile Update | `/customers/{customer_id}` | `PATCH` | **IMPLEMENTED** | Restricts modification to owner UID or Admin (403 Forbidden on mismatch). |
| Current User Resolution | `/users/me` | `GET` | **IMPLEMENTED** | Automatically resolves authenticated identity from token context. |
| Customer Registration | `/customers/register`, `/register` | `POST` | **IMPLEMENTED** | Token-derived UID, prevents duplicate registrations (409 Conflict). |
| Job Creation | `/jobs` | `POST` | **IMPLEMENTED** | Category validation against whitelist, non-negative budget, coordinate bounds. |
| Worker Discovery | `/workers/match?jobId={id}` | `GET` | **IMPLEMENTED** | Multi-factor weighted ranking (40% dist, 30% rating, 20% price, 10% volume). |
| Public Worker Feed | `/workers`, `/workers/feed` | `GET` | **IMPLEMENTED** | Excludes flagged / under-review accounts, obfuscates exact location coordinates. |
| Job Tracking | `/jobs/{id}` | `GET` | **IMPLEMENTED** | Address masked for unassigned workers until an offer is accepted. |
| Road Routing & ETA | `/route?jobId={id}&workerId={id}` | `GET` | **IMPLEMENTED** | Dijkstra shortest path on OSM drive network, fallback to Haversine. |
| Review Submission | `/reviews` | `POST` | **IMPLEMENTED** | Restricted to completed jobs, customer ownership enforced, duplicate reviews rejected (400). |

---

## 2. Worker API Support

| Feature | Endpoint | HTTP Method | Status | Notes |
|---|---|---|---|---|
| Worker Registration | `/workers/register` | `POST` | **IMPLEMENTED** | Token-derived UID, skill categories validated against platform whitelist. |
| Worker Profile Retrieval | `/workers/{worker_id}` | `GET` | **IMPLEMENTED** | Strips sensitive phone/PII unless requested by the worker themselves or admin. |
| Worker Profile & Availability Update | `/workers/{worker_id}` | `PATCH` | **IMPLEMENTED** | Supports updating `isAvailableNow`, `skills`, `rates`, `serviceRadiusKm`, `name`, `phone`. Ownership strictly guarded (403). |
| Worker Earnings | `/workers/{worker_id}/earnings` | `GET` | **IMPLEMENTED** | Derived dynamically from completed jobs where `acceptedWorkerId == worker_id`. Distinguishes direct cash payouts (0% platform commission). |
| Nearby Open Jobs Feed | `/jobs/nearby` | `GET` | **IMPLEMENTED** | Skill-matched and filtered by service radius based on worker's saved profile location. |
| Offer Submission | `/offers` | `POST` | **IMPLEMENTED** | Worker places initial quote or bid on open job. |
| Counter-Offers | `/offers/{id}/counter` | `POST` | **IMPLEMENTED** | Supports bidirectional negotiation between customer and worker. |
| Offer Acceptance & Rejection | `/offers/{id}/accept`, `/offers/{id}/reject` | `POST` | **IMPLEMENTED** | Atomic transaction: transitions job to `accepted`, assigns worker, auto-rejects rival offers. |
| Job Start | `/jobs/{id}/start` | `POST` | **IMPLEMENTED** | Enforces assigned worker identity, transitions `accepted` -> `in_progress`. |
| Job Complete | `/jobs/{id}/complete` | `POST` | **IMPLEMENTED** | Transitions `in_progress` -> `completed`, atomically increments `jobsDone`. |
| Verification Request | `/workers/verify` | `POST` | **IMPLEMENTED** | Worker submits ID document metadata, sets `verificationStatus = 'pending'`. |

---

## 3. Admin API Support

| Feature | Endpoint | HTTP Method | Status | Notes |
|---|---|---|---|---|
| Dashboard Statistics | `/admin/stats`, `/admin/dashboard` | `GET` | **IMPLEMENTED** | Aggregates customers, workers, verified workers, queue size, active jobs, completed jobs, and safety report breakdown. |
| Pending Verification Queue | `/admin/verifications`, `/admin/verifications/pending` | `GET` | **IMPLEMENTED** | Lists workers pending review with masked document IDs. |
| Approve Verification | `/admin/verifications/{uid}/approve` | `POST` | **IMPLEMENTED** | Sets `verified = True`, `verificationStatus = 'verified'`. Admin-only. |
| Reject Verification | `/admin/verifications/{uid}/reject` | `POST` | **IMPLEMENTED** | Sets `verified = False`, `verificationStatus = 'rejected'`. Admin-only. |
| Abuse Report Listing | `/admin/reports` | `GET` | **IMPLEMENTED** | Supports optional query filtering: `?status=pending|resolved|dismissed`. |
| Single Report Details | `/admin/reports/{id}` | `GET` | **IMPLEMENTED** | Fetches incident report details for moderator inspection. |
| Resolve Abuse Report | `/admin/reports/{id}/resolve` | `POST` | **IMPLEMENTED** | Records moderator note, transitions status to `resolved`. |
| Dismiss Abuse Report | `/admin/reports/{id}/dismiss` | `POST` | **IMPLEMENTED** | Dismisses unfounded report, transitions status to `dismissed`. |
| User Listing | `/admin/users` | `GET` | **IMPLEMENTED** | Lists registered users with optional role filtering (`?role=customer|worker|admin`). |
| Suspend User | `/admin/users/{uid}/suspend` | `POST` | **IMPLEMENTED** | Flags account, sets `accountStatus = 'SUSPENDED'`, disables worker availability. |
| Reactivate User | `/admin/users/{uid}/reactivate` | `POST` | **IMPLEMENTED** | Clears flags, sets `accountStatus = 'ACTIVE'`. |

---

## 4. Safety & Trust Engine

- **Bayesian Rating Adjustment**: Mitigates 5.0 review inflation on accounts with low volume ($m=5$, $C=4.5$).
- **Account Age Weighting**: Accounts $<7$ days receive calibrated trust curve climbing to $1.0$ at 30 days maturity.
- **Automated Abuse Rules**: 3 or more unreviewed reports within 48 hours automatically sets `accountStatus = 'UNDER_REVIEW'`, marks `isFlagged = True`, and demotes the worker from the public match feed.
