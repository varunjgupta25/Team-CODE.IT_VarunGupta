# Phase 0: Frontend Gap Analysis & Technical Debt Registry

**Project**: RepairBuddy Frontend  
**Auditor**: Senior Frontend Architect & Systems Reliability Auditor  
**Date**: November 2026  
**Status**: Comprehensive Gap Audit Complete  

---

## 1. Feature Gap & Architectural Debt Matrix

| Feature / Domain | Persona | Current Status | Identified Gap | Priority | Recommendation |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Worker Earnings Ledger** | Worker | **Mock Only** | Calculations are performed client-side using `localStorage` (`rb_mock_jobs_v1`). No backend ledger or payout calculation endpoint exists. | **CRITICAL** | Implement backend `GET /workers/earnings` and `GET /workers/ledger` endpoints and replace client storage queries. |
| **Admin Layout Ergonomics** | Admin | **Partially Implemented** | Admin dashboard is forced inside a 448px mobile container (`MobileLayout.jsx`). Moderating document images and verification queues is severely constrained. | **CRITICAL** | Unbind `/admin` from `MobileLayout` and implement a full-width desktop layout with tabular queues and image zoom modals. |
| **Payment Gateway Integration**| Customer | **Missing** | Job completion immediately redirects to review submission without digital payment settlement (Razorpay / UPI / Cash collection confirmation). | **HIGH** | Integrate Razorpay checkout SDK or an explicit "Cash on Delivery" receipt acknowledgment before review. |
| **Damage Photo Attachments** | Customer | **Missing** | `CreateJobPage.jsx` does not permit image uploads. Workers must bid blind without seeing the repair issue. | **HIGH** | Add multi-file image picker with client compression (`browser-image-compression`) and upload to S3/Cloud Storage. |
| **Address Autocomplete** | Customer | **Missing** | `MapPicker.jsx` allows coordinate pin-dropping but lacks a search box with Google Places or OpenStreetMap Nominatim geocoding. | **HIGH** | Add search input with debounced geocoding query to auto-position map pin and format address. |
| **Real-Time GPS Transit Feed** | Customer / Worker | **Partially Implemented** | Route tracking polls `GET /jobs/{id}` every 5 seconds. Movement is choppy and worker location is not streamed continuously while driving. | **MEDIUM** | Implement WebSocket or Server-Sent Events (SSE) for sub-second GPS coordinate streaming during transit. |
| **Real-Time Job Notifications**| Worker | **Missing** | Workers receive leads only when looking at `WorkerDashboard.jsx`. No Firebase Cloud Messaging (FCM) push notifications when app is backgrounded. | **MEDIUM** | Integrate Firebase Cloud Messaging Service Worker (`firebase-messaging-sw.js`) for background push alerts. |
| **In-App Messaging / Chat** | Customer / Worker | **Missing** | Parties cannot message each other to discuss landmark details, tool requirements, or schedule adjustments during negotiation. | **MEDIUM** | Implement simple lightweight chat channel attached to `jobId`. |
| **Emergency Contact Persistence**| Global | **Partially Implemented** | Backend `/users/me/emergency-contact` is not universally implemented across backend revisions; relies on local storage fallback. | **MEDIUM** | Standardize user profile schema on backend to persist emergency contacts in MongoDB/PostgreSQL. |
| **Category Search & Filter** | Customer | **Missing** | `CustomerHome.jsx` displays 8 static category cards with no keyword search or sub-category filtering. | **LOW** | Add fuzzy search bar filtering categories and common household repair keywords. |
| **WCAG 2.1 AA Button Contrast** | Global | **Partially Implemented** | Disabled buttons and subtle slate metadata text fail minimum 4.5:1 contrast ratio. | **LOW** | Adjust color tokens in `index.css` to ensure `#64748b` on `#f8fafc` satisfies WCAG standards. |
| **Missing Accessibility Labels**| Global | **Partially Implemented** | Interactive icons (`SosButton`, close triggers, map controls) lack explicit `aria-label` attributes. | **LOW** | Add explicit `aria-label` and `aria-live` attributes to interactive elements. |

---

## 2. Summary of Architectural Risks

1. **Monolithic Bundle Exposure**: Admin verification screens and moderation actions are packaged inside the client bundle delivered to ordinary customer devices. Although protected by runtime route guards and cryptographic Firebase token claims, administrative code paths should be completely removed from public-facing customer bundles.
2. **Mock Default Risk**: The application defaults to `VITE_USE_MOCK !== 'false'`. If an environment variable is omitted in a production deployment, the entire system silently falls back to browser `localStorage` mocks instead of connecting to Render production APIs.
3. **Polling vs. Sockets Load**: Polling `GET /jobs/{id}` every 5 seconds across thousands of active sessions will generate heavy backend traffic on Render free/starter tiers. Transitioning active job tracking to SSE/WebSockets is strongly recommended before scale.

