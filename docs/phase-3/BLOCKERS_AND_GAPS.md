# Blockers and Gaps Report — Phase 3

## 1. Resolved In Phase 3
- Full verification of all 200 regression and integration test cases across the FastAPI backend.
- Validated atomic state changes for competing offer rejection and lifecycle transitions.
- Validated complete moderation loop: abuse report submission -> automatic flag -> admin resolution -> account reactivation.
- All Phase 3 work isolated on branch `phase-3-backend`.

---

## 2. Platform Architecture Constraints (Intentional / By Design)

### 1. Direct Cash Payment Model (No Payment Gateway)
- **Status**: By design.
- **Impact**: RepairBuddy operates on a 0% commission direct-cash model. Payments are settled directly between customer and worker upon completion of physical household tasks.
- **Action**: No backend escrow or gateway integration required for Phase 3.

### 2. Client-Side Polling for Live Status Updates
- **Status**: Polling pattern in use (`/jobs/{id}`, `/offers?jobId=...`).
- **Impact**: Backend does not maintain persistent WebSocket or FCM push connections. Status changes are communicated via standard HTTP polling intervals.
- **Action**: Fully supported by current rate limits (default 120 requests/min per IP).

### 3. Verification Document Uploads
- **Status**: Document metadata (type + masked number) validated and persisted in Firestore.
- **Impact**: Raw image file binary upload (e.g. photo of Aadhaar/PAN) is not stored directly on disk or in database.
- **Recommendation for Post-Phase 3**: Provision Google Cloud Storage / Firebase Storage private buckets with presigned upload URLs if physical photo uploads are requested.

