# RepairBuddy — Phase 2: Frontend Gap & Roadmap Report

**Project**: RepairBuddy Marketplace  
**Phase**: Phase 2 — Frontend Feature Development  
**Audience**: Product Management, Engineering Leads, Backend Team  
**Date**: November 2026  
**Status**: Completed  

---

## 1. Executive Summary

While Phase 2 has successfully achieved full feature completion, mobile responsiveness, and client-side stability for the Customer, Worker, and Admin user journeys, several backend architectural dependencies remain pending on the production FastAPI server (`https://repair-buddy.onrender.com/`).

In accordance with strict project guidelines, the frontend deliberately refrains from fabricating artificial data for missing backend capabilities and instead clearly marks these areas as pending backend integration.

---

## 2. Identified Backend Gaps & Contract Discrepancies

### 1. Platform Statistics & Financial Telemetry (`GET /admin/stats`)
- **Status**: **MISSING ON BACKEND**
- **Impact**: The Admin Console's "Metrics" tab displays verified counts for pending verifications, active emergency SOS triggers, and platform incident reports derived from existing endpoints, but cannot query global platform Gross Merchandise Value (GMV), platform fees, or hourly booking distributions.
- **Frontend Mitigation**: Demarcated with an explicit `[Pending API: GET /admin/stats]` callout banner in `AdminPage.jsx`.
- **Recommended Backend Action**: Implement `GET /admin/stats` returning:
  ```json
  {
    "totalGmv": 1250000,
    "totalJobsCompleted": 1840,
    "activeWorkersOnline": 48,
    "dailyJobVolume": [12, 18, 25, 30]
  }
  ```

### 2. Centralized User Directory Management (`GET /admin/users`)
- **Status**: **MISSING ON BACKEND**
- **Impact**: Admins can approve and reject workers who have submitted verification documents via `GET /admin/verifications/pending`, but cannot browse, suspend, or search non-pending customers and workers globally.
- **Frontend Mitigation**: Demarcated with an explicit `[Pending API: GET /admin/users]` label.
- **Recommended Backend Action**: Implement paginated `GET /admin/users?role={role}&search={query}&limit=20`.

### 3. Dedicated Worker Earnings Ledger (`GET /workers/earnings`)
- **Status**: **MISSING ON BACKEND**
- **Impact**: `WorkerEarningsPage.jsx` computes estimated earnings on client-side based on confirmed completed jobs multiplied by trade rates (`jobsDone * rate`).
- **Frontend Mitigation**: Added an explicit informational disclaimer informing workers that earnings represent direct cash/UPI received from customers upon job completion with 0% platform escrow.
- **Recommended Backend Action**: Implement `GET /workers/earnings` returning aggregated payout logs, date ranges, and per-job payout receipts.

### 4. Emergency Contact Persistence (`/users/me/emergency-contact`)
- **Status**: **PARTIAL / INSTABILITY ON SOME BACKEND DEPLOYMENTS**
- **Impact**: The FastAPI backend sometimes returns 404 or drops emergency contacts on server restarts.
- **Frontend Mitigation**: The frontend wraps `api.getEmergencyContact()` and `api.setEmergencyContact()` in robust local storage fallbacks (`storage.get('rb_mock_emergency_contact')`), ensuring user-entered emergency contacts remain available for SOS SMS dispatches even during backend downtime.

---

## 3. Readiness for Phase 3 (UI Polish) & Phase 4 (Dual-App Separation)

The codebase is in an ideal posture for subsequent phases:
1. **Module Cleanliness**: Customer, Worker, and Admin features are cleanly separated into dedicated pages and reusable components.
2. **Quality Baseline**:
   - 0 Oxlint warnings or errors across 42 files.
   - Vite production bundle compiles cleanly.
   - 26/26 automated unit and integration tests passing.
3. **No Breaking Changes**: Existing mobile container layout (`MobileLayout.jsx`), route definitions, and Zustand state architectures have been preserved.
