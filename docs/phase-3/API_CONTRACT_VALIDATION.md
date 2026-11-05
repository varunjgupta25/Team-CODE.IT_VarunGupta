# API Contract Validation — Phase 3

All endpoints are mounted under both root (`""`) and `/api`. Every contract has been verified for request schemas, response models, HTTP status codes, and error formats.

---

## 1. Public & Core System Endpoints

| Endpoint | Method | Status Code | Auth Required | Contract Summary |
|---|---|---|---|---|
| `/health` | `GET` | `200 OK` | Public | Returns system health, database mode, and transit speed. |
| `/` | `GET` | `200 OK` | Public | Returns service info, documentation links, and frontend URL. |

---

## 2. Customer Endpoints

| Endpoint | Method | Status Code | Auth Required | Contract Summary |
|---|---|---|---|---|
| `/customers/register` | `POST` | `201 Created` / `409 Conflict` | Bearer Token | Registers profile using token-derived UID. Duplicate returns 409. |
| `/customers/{id}` | `GET` | `200 OK` / `404 Not Found` | Bearer Token | Retrieves profile. Non-owner receives masked phone number. |
| `/customers/{id}` | `PATCH` | `200 OK` / `403 Forbidden` | Customer / Admin | Updates profile (name, phone, location). Non-owners rejected with 403. |
| `/users/me` | `GET` | `200 OK` | Bearer Token | Resolves current caller's profile (customer or worker). |
| `/jobs` | `POST` | `201 Created` / `422 Unprocessable` | Customer / Admin | Creates job. Validates category, non-negative budget, coordinates. |
| `/jobs/{id}` | `GET` | `200 OK` / `404 Not Found` | Bearer Token | Fetches job details. Masks address for unassigned workers. |
| `/jobs/{id}/cancel` | `POST` | `200 OK` / `400 Bad Request` | Customer / Admin | Cancels active job. Rejects if already completed (400). |
| `/reviews` | `POST` | `201 Created` / `400 Bad Request` | Customer / Admin | Submits review. Requires job status == completed. Prevents duplicates. |

---

## 3. Worker Endpoints

| Endpoint | Method | Status Code | Auth Required | Contract Summary |
|---|---|---|---|---|
| `/workers/register` | `POST` | `201 Created` / `409 Conflict` | Bearer Token | Registers worker profile. Validates skills against category whitelist. |
| `/workers` | `GET` | `200 OK` | Bearer Token | Returns public worker feed. Filters out flagged/under-review accounts. |
| `/workers/{id}` | `GET` | `200 OK` / `404 Not Found` | Bearer Token | Fetches profile. Masks private contact information for non-owners. |
| `/workers/{id}` | `PATCH` | `200 OK` / `403 Forbidden` | Worker / Admin | Updates availability, skills, rates, service radius. Guarded by 403. |
| `/workers/{id}/earnings` | `GET` | `200 OK` / `403 Forbidden` | Worker / Admin | Calculates net cash earnings from completed jobs. Guarded by 403. |
| `/workers/match` | `GET` | `200 OK` / `422 Unprocessable` | Customer / Admin | Ranks workers by composite score (distance, rating, budget, jobsDone). |
| `/jobs/nearby` | `GET` | `200 OK` / `403 Forbidden` | Worker / Admin | Worker job feed. Filtered by worker skills and saved service radius. |
| `/workers/verify` | `POST` | `200 OK` / `403 Forbidden` | Worker only | Submits ID verification request. Sets status to pending. |

---

## 4. Offers & Negotiation Endpoints

| Endpoint | Method | Status Code | Auth Required | Contract Summary |
|---|---|---|---|---|
| `/offers` | `POST` | `201 Created` / `400 Bad Request` | Customer / Worker | Creates offer or bid. Automatically transitions job to negotiating. |
| `/offers` | `GET` | `200 OK` | Bearer Token | Queries offers for a job (`?jobId=...`). |
| `/offers/{id}/counter`| `POST` | `200 OK` / `400 Bad Request` | Bearer Token | Counters price in an active negotiation. |
| `/offers/{id}/accept` | `POST` | `200 OK` / `400 Bad Request` | Customer / Worker | Accepts offer. Assigns worker, locks final price, rejects rival offers. |
| `/offers/{id}/reject` | `POST` | `200 OK` / `400 Bad Request` | Customer / Worker | Rejects pending offer. |

---

## 5. Job Lifecycle Transitions

| Endpoint | Method | Status Code | Auth Required | Contract Summary |
|---|---|---|---|---|
| `/jobs/{id}/start` | `POST` | `200 OK` / `400 Bad Request` | Worker / Admin | Transitions accepted -> in_progress. Assigned worker only. |
| `/jobs/{id}/complete`| `POST` | `200 OK` / `400 Bad Request` | Worker / Admin | Transitions in_progress -> completed. Increments worker jobsDone. |

---

## 6. Admin Endpoints

| Endpoint | Method | Status Code | Auth Required | Contract Summary |
|---|---|---|---|---|
| `/admin/verifications` | `GET` | `200 OK` / `403 Forbidden` | Admin only | Pending verification queue with masked document numbers. |
| `/admin/verifications/pending` | `GET` | `200 OK` / `403 Forbidden` | Admin only | Unverified workers list. |
| `/admin/verifications/{uid}/approve` | `POST` | `200 OK` / `403 Forbidden` | Admin only | Approves verification. Sets verified = True. |
| `/admin/verifications/{uid}/reject` | `POST` | `200 OK` / `403 Forbidden` | Admin only | Rejects verification. Sets verified = False, status = rejected. |
| `/admin/stats` / `/admin/dashboard` | `GET` | `200 OK` / `403 Forbidden` | Admin only | Real-time counts of users, workers, jobs, reports. |
| `/admin/reports` | `GET` | `200 OK` / `403 Forbidden` | Admin only | Filterable reports listing (`?status=pending\|resolved\|dismissed`). |
| `/admin/reports/{id}` | `GET` | `200 OK` / `403 Forbidden` | Admin only | Retrieves single report detail. |
| `/admin/reports/{id}/resolve` | `POST` | `200 OK` / `403 Forbidden` | Admin only | Resolves report with moderator notes. |
| `/admin/reports/{id}/dismiss` | `POST` | `200 OK` / `403 Forbidden` | Admin only | Dismisses report. |
| `/admin/users` | `GET` | `200 OK` / `403 Forbidden` | Admin only | User listing with role filter (`?role=...`). |
| `/admin/users/{uid}/suspend` | `POST` | `200 OK` / `403 Forbidden` | Admin only | Suspends user/worker account. |
| `/admin/users/{uid}/reactivate` | `POST` | `200 OK` / `403 Forbidden` | Admin only | Reactivates account. |

