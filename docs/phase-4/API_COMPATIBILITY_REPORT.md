# Phase 4 — API Compatibility Report

## 1. Zero Duplicate Endpoints

The RepairBuddy backend maintains **100% contract compatibility** across both the Customer App and Partner App deployments without duplicating any endpoints, models, or business logic.

Both client applications communicate with identical endpoint paths:
- Root mounted: `/jobs`, `/workers`, `/offers`, `/reviews`, `/admin`, `/reports`, `/sos`, `/health`
- API prefix mounted: `/api/jobs`, `/api/workers`, `/api/offers`, `/api/reviews`, `/api/admin`, `/api/reports`, `/api/sos`, `/api/health`

---

## 2. Shared API Contract Inventory

### A. Customer App Contracts
| Method | Route | Description | Request Schema | Response Schema |
|---|---|---|---|---|
| `GET` | `/users/me` | Customer profile | None | `UserProfileResponse` |
| `POST` | `/customers/register` | Customer onboarding | `CustomerRegisterRequest` | `UserRecord` (`201`) |
| `POST` | `/jobs` | Job request creation | `JobCreate` | `JobResponse` (`201`) |
| `GET` | `/jobs/{id}` | Real-time job tracking | None | `JobResponse` (`200`) |
| `POST` | `/jobs/{id}/cancel` | Job cancellation | None | `JobResponse` (`200`) |
| `GET` | `/workers/match?jobId=...` | Discovery of nearby verified workers | Query Param `jobId` | `List[MatchedWorkerResponse]` (`200`) |
| `GET` | `/offers?jobId=...` | Incoming price bids | Query Param `jobId` | `List[OfferResponse]` (`200`) |
| `POST` | `/offers/{id}/accept` | Accept worker proposal | None | `OfferResponse` (`200`) |
| `POST` | `/offers/{id}/counter` | Counter-offer negotiation | `{"price": float}` | `OfferResponse` (`200`) |
| `POST` | `/reviews` | Post-service rating | `ReviewCreate` | `ReviewResponse` (`201`) |
| `POST` | `/reports` | Safety incident report | `ReportCreate` | `ReportResponse` (`201`) |

### B. Partner App — Worker Contracts
| Method | Route | Description | Request Schema | Response Schema |
|---|---|---|---|---|
| `GET` | `/users/me` | Worker profile | None | `UserProfileResponse` |
| `POST` | `/workers/register` | Worker onboarding | `WorkerRegisterRequest` | `WorkerRecord` (`201`) |
| `GET` | `/workers/{id}` | Worker public/private view | None | `WorkerPublicResponse` (`200`) |
| `PATCH` | `/workers/{id}` | Availability toggle / rates | `WorkerUpdatePayload` | `WorkerRecord` (`200`) |
| `GET` | `/jobs/nearby` | Local jobs feed | None | `List[NearbyJobResponse]` (`200`) |
| `POST` | `/offers` | Send price offer | `OfferCreate` | `OfferResponse` (`201`) |
| `POST` | `/jobs/{id}/start` | Transition to in_progress | None | `JobResponse` (`200`) |
| `POST` | `/jobs/{id}/complete` | Transition to completed | None | `JobResponse` (`200`) |
| `POST` | `/workers/verify` | Request ID verification | `WorkerVerifyRequest` | `WorkerVerifyResponse` (`200`) |

### C. Partner App — Admin Console Contracts
| Method | Route | Description | Request Schema | Response Schema |
|---|---|---|---|---|
| `GET` | `/admin/stats` | Platform metrics & KPIs | None | `DashboardStats` (`200`) |
| `GET` | `/admin/verifications/pending` | Worker KYC queue | None | `List[WorkerSummary]` (`200`) |
| `POST` | `/admin/verifications/{uid}/approve` | Approve worker KYC | None | `AdminApproveResponse` (`200`) |
| `POST` | `/admin/verifications/{uid}/reject` | Reject worker KYC | None | `AdminRejectResponse` (`200`) |
| `GET` | `/admin/reports` | Moderation queue | Query Param `status` | `List[ReportResponse]` (`200`) |
| `POST` | `/admin/reports/{id}/resolve` | Resolve safety report | `ReportActionPayload` | `ReportResponse` (`200`) |
| `POST` | `/admin/users/{uid}/suspend` | Suspend user account | `{"reason": str}` | `UserRecord` (`200`) |
| `POST` | `/admin/users/{uid}/reactivate` | Reactivate user account | None | `UserRecord` (`200`) |

---

## 3. Error Handling Compatibility

All error responses strictly adhere to FastAPI / Starlette JSON format:
- `400 Bad Request`: `{"detail": "<specific validation or transition message>"}`
- `401 Unauthorized`: `{"detail": "<token or authentication failure message>"}`
- `403 Forbidden`: `{"detail": "<role or ownership violation message>"}`
- `404 Not Found`: `{"detail": "<resource not found message>"}`
- `409 Conflict`: `{"error": "conflict", "message": "<duplicate description>", "detail": "<detail>"}`
- `422 Unprocessable Content`: `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`
- `429 Too Many Requests`: `{"detail": "Rate limit exceeded. Try again in X seconds."}`

