# Phase 4 — Frontend Blockers and Gaps Report

## 1. Blocker Status

**Zero Critical Blockers** exist for the frontend separation of RepairBuddy into Customer and Partner applications. Both applications build cleanly, pass all 59 verification tests, pass `oxlint`, and achieve 100% strict bundle separation.

---

## 2. Production Coordination Requirements

To achieve a seamless dual deployment on Vercel:

1. **Deploy as Two Vercel Projects**:
   - Create Project 1 on Vercel using `Root Directory: frontend`, `Build Command: npm run build:customer`, and `VITE_APP=customer`.
   - Create Project 2 on Vercel using `Root Directory: frontend`, `Build Command: npm run build:partner`, and `VITE_APP=partner`.
2. **Configure Common Backend API URL**:
   - Set `VITE_API_BASE_URL=https://repair-buddy.onrender.com/api` on both Vercel projects.
3. **Register Vercel Domains in Render**:
   - Set `CUSTOMER_APP_ORIGIN=https://<customer-vercel-domain>`
   - Set `PARTNER_APP_ORIGIN=https://<partner-vercel-domain>`
   in Render backend environment settings.
4. **Firebase Single Project Setup**:
   - Both frontends must point to the same Firebase Project (`repair-buddy-662c6`) so ID tokens are universally verifiable across the backend.

---

## 3. Recommended Future Polish (Non-Blocking)

- **Push Notifications (FCM / Web Push)**: Currently, worker offers and status transitions are polled every few seconds. Integrating Web Push or FCM service worker will provide instant notifications when a customer is not actively viewing the tab.
- **PWA Manifests**: Add `manifest.customer.json` and `manifest.partner.json` allowing home-screen app installation on Android/iOS devices for both customers and service technicians.

