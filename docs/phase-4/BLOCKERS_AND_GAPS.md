# Phase 4 — Blockers and Gaps Report

## 1. Blocker Status

**Zero Critical Backend Blockers** exist for the frontend separation into Customer and Partner applications. The backend is fully tested and ready to serve both frontends from a single service instance.

---

## 2. Frontend Coordination Requirements

To achieve a seamless end-to-end integration across the two Vercel frontends, the frontend development team must ensure the following configurations:

1. **Identical Backend Base URL**:
   - Both Customer App and Partner App frontends must configure their API clients to target the same backend:
     `VITE_API_BASE_URL=https://repair-buddy.onrender.com` (or equivalent environment variable).
2. **Unified Firebase Project Credentials**:
   - Both frontend deployments must initialize their Firebase client SDKs using the **exact same Firebase project credentials**:
     - `apiKey`
     - `authDomain`
     - `projectId`
     - `storageBucket`
     - `messagingSenderId`
     - `appId`
   - Initializing against different Firebase projects will cause `firebase_admin.auth.verify_id_token()` to reject tokens due to mismatched project IDs (`aud` / `iss`).
3. **Production Origin Registration**:
   - Once production domains or Vercel URLs are assigned to the two frontends, the repository owner should update Render environment variables:
     - `CUSTOMER_APP_ORIGIN=https://<customer-app-domain>`
     - `PARTNER_APP_ORIGIN=https://<partner-app-domain>`
4. **Independent User Authentication**:
   - Since browsers isolate `localStorage` per origin domain, users must sign in separately on the Customer and Partner applications. Frontends should avoid passing raw auth tokens in cross-app URL query parameters.

---

## 3. Future Architectural Considerations (Non-Blocking)

- **Real-Time Push Notifications**: The platform currently uses polling (`GET /jobs/{id}`, `GET /offers?jobId=...`). If instantaneous alerts are required in subsequent phases, Firebase Cloud Messaging (FCM) or WebSockets may be integrated.
- **Payment Handling**: The platform operates on a direct cash-on-completion / 0% platform commission model by design. No payment gateway integration is required.

