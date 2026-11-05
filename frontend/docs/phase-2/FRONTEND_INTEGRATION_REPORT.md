# RepairBuddy — Phase 2: Frontend Integration Report

**Project**: RepairBuddy Marketplace  
**Phase**: Phase 2 — Frontend Feature Development  
**Audience**: Integration Engineers, DevOps, Full-Stack Architects  
**Date**: November 2026  
**Status**: Completed & Verified  

---

## 1. Executive Summary

This report assesses the integration fidelity between the RepairBuddy React frontend and the FastAPI backend (`https://repair-buddy.onrender.com/`). The integration features a centralized Axios client, automatic Bearer token injection, retry policies with exponential backoff for network/5xx faults, multi-stage polling loops, normalized DTO payloads, and dual-mode execution (Mock and Live).

---

## 2. API Facade & Endpoint Mapping

| Domain | Facade Method | HTTP & Endpoint Path | Payload / Query | Backend Response Schema | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Auth** | `api.registerCustomer(d)` | `POST /customers/register` | `{ name, phone, location }` | `{ success, customer }` | **Integrated** |
| **Auth** | `api.registerWorker(d)` | `POST /workers/register` | `{ name, phone, skills, rates, location }` | `{ success, worker }` | **Integrated** |
| **Auth** | `api.getWorker(uid)` | `GET /workers/{uid}` | Path: `uid` | `{ uid, name, skills, rates, rating }` | **Integrated** |
| **Jobs** | `api.createJob(d)` | `POST /jobs` | `{ category, description, budget, mode, location }` | `{ id, status, category, ... }` | **Integrated** |
| **Jobs** | `api.getJob(id)` | `GET /jobs/{id}` | Path: `id` | `{ id, status, offers, acceptedWorkerId }` | **Integrated** |
| **Jobs** | `api.cancelJob(id)` | `POST /jobs/{id}/cancel` | Path: `id` | `{ id, status: 'cancelled' }` | **Integrated** |
| **Jobs** | `api.getMatchedWorkers(id)` | `GET /workers/match?jobId=` | Query: `jobId` | `Array<{ worker, distanceKm, etaMinutes, trustScore }>` | **Integrated** |
| **Offers** | `api.createOffer(d)` | `POST /offers` | `{ jobId, workerId, price, by }` | `{ id, status: 'pending', price }` | **Integrated** |
| **Offers** | `api.counterOffer(id, d)` | `POST /offers/{id}/counter` | `{ price, by }` | `{ id, status: 'pending', price }` | **Integrated** |
| **Offers** | `api.acceptOffer(id)` | `POST /offers/{id}/accept` | Path: `id` | `{ offer, job }` | **Integrated** |
| **Offers** | `api.rejectOffer(id)` | `POST /offers/{id}/reject` | Path: `id` | `{ id, status: 'rejected' }` | **Integrated** |
| **Lifecycle**| `api.startJob(id)` | `POST /jobs/{id}/start` | Path: `id` | `{ id, status: 'in_progress' }` | **Integrated** |
| **Lifecycle**| `api.completeJob(id)` | `POST /jobs/{id}/complete`| Path: `id` | `{ id, status: 'awaiting_confirmation' }` | **Integrated** |
| **Lifecycle**| `api.confirmJob(id)` | `POST /jobs/{id}/confirm` | Path: `id` | `{ id, status: 'completed' }` | **Integrated** |
| **Reviews** | `api.submitReview(d)` | `POST /reviews` | `{ jobId, workerId, rating, comment, tags }` | `{ id, rating, workerId }` | **Integrated** |
| **Safety** | `api.triggerSos(d)` | `POST /sos` | `{ jobId, location, reason }` | `{ alertId / id, status }` | **Integrated** |
| **Admin** | `api.getPendingVerifications()` | `GET /admin/verifications/pending` | None | `Array<{ uid, name, docType, last4 }>` | **Integrated** |
| **Admin** | `api.approveWorkerVerification(uid)` | `POST /admin/verifications/{uid}/approve` | Path: `uid` | `{ status: 'approved', workerId }` | **Integrated** |
| **Admin** | `api.rejectWorkerVerification(uid, r)` | `POST /admin/verifications/{uid}/reject` | `{ reason }` | `{ status: 'rejected', reason }` | **Integrated** |
| **Admin** | `api.resetVerificationAttempts(uid)` | `POST /admin/verifications/{uid}/reset_attempts` | Path: `uid` | `{ success: true, attemptCount: 0 }` | **Integrated** |
| **Admin** | `api.getAdminSosAlerts()` | `GET /admin/sos` | None | `Array<{ id, status, location, mapsUrl }>` | **Integrated** |

---

## 3. Resilience & Network Strategy

1. **Bearer Token Synchronization**:
   - Axios request interceptor attaches the current Firebase ID token.
   - 401 response interceptor performs automatic force-refresh via `getIdToken(true)` once per request cycle.
2. **Error Isolation**:
   - Network / 5xx errors retry with exponential backoff (1s, 2s, 4s).
   - 4xx client errors (e.g. 400 Bad Request, 403 Forbidden, 409 Conflict) bypass retry cycles and present immediate feedback via `toastStore`.
3. **Data Normalization**:
   - Handles both raw array and envelope `{ data: [] }` responses across FastAPI router mounts (`/...` and `/api/...`).
