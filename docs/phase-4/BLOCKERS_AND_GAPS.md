# Phase 4 — Unified Blockers and Gaps Report

## 1. Blocker Status

- **Backend**: **Zero Critical Backend Blockers**. The FastAPI backend is fully tested (204/205 tests passing, `test_phase4_app_separation.py` 5/5 passing) and configured for dual-origin CORS support (`CUSTOMER_APP_ORIGIN` and `PARTNER_APP_ORIGIN`).
- **Frontend**: **Zero Critical Frontend Blockers**. Both Customer App and Partner App build independently (`build:customer`, `build:partner`), pass all 59 verification tests, pass `oxlint`, and achieve 100% strict bundle separation.

---

## 2. Production Coordination & Vercel Setup

To deploy both applications successfully on Vercel:

1. **Deploy as Two Vercel Projects**:
   - Project 1 (Customer): `Root Directory: frontend`, `Build Command: npm run build:customer`, `VITE_APP=customer`.
   - Project 2 (Partner): `Root Directory: frontend`, `Build Command: npm run build:partner`, `VITE_APP=partner`.
2. **Common Backend Base URL**:
   - Both frontends configure `VITE_API_BASE_URL=https://repair-buddy.onrender.com/api`.
3. **Unified Firebase Project**:
   - Both frontends point to `repair-buddy-662c6` so phone OTP authentication and Firebase ID tokens are verifiable across the platform.
4. **Origin Registration on Render**:
   - Set `CUSTOMER_APP_ORIGIN` and `PARTNER_APP_ORIGIN` on the Render deployment matching the Vercel domains.
5. **Independent LocalStorage Sessions**:
   - Because modern browsers sandbox `localStorage` per domain origin, customers and workers will naturally have separated sessions on their respective domains.

---

## 3. Future Architectural Considerations (Non-Blocking)

- **Push Notifications**: Integrating Web Push or FCM service worker for background offer alerts when tabs are in background.
- **PWA Manifests**: Add standalone home-screen installation manifests (`manifest.customer.json` and `manifest.partner.json`).
- **0% Escrow Direct Cash**: The platform intentionally maintains a 0% platform fee direct cash-on-completion settlement model. No payment gateway integration is required.
