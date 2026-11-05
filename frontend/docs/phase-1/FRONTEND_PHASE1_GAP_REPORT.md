# Phase 1: Frontend Gap Analysis & Known Limitations Report

**Project**: RepairBuddy Frontend  
**Auditor**: Senior Frontend Architect & Systems Reliability Specialist  
**Date**: November 2026  
**Status**: Phase 1 Stabilized — Phase 2 Recommendations Prepared  

---

## 1. Summary of Stabilized Areas

During Phase 1, the frontend was successfully stabilized for live backend communication:
- Centralized Axios client with automatic Bearer token injection and auto-refresh on 401 Unauthorized.
- Production environment safeguards to prevent accidental mock fallback.
- Reactive `onAuthStateChanged` session persistence and hydration spinners on page reloads.
- Contract alignment for job creation, worker matching, counter-offers, job lifecycle, verification document uploads, dispute reports, and reviews.
- Clean zero-warning linting (`oxlint`) and 100% passing test suite (13/13 tests).

---

## 2. Identified Backend Dependencies & Known Limitations

| Feature / Domain | Current Phase 1 Status | Identified Dependency / Gap | Recommended Phase 2 Action |
| :--- | :--- | :--- | :--- |
| **Worker Earnings Ledger** | Client-computed | The backend does not feature a dedicated `GET /workers/earnings` route. Metrics are computed client-side using `jobsDone * tradeRate`. | Implement backend ledger and payout calculation endpoint. |
| **In-App Payments** | Post-job direct review | Job confirmation transitions directly to rating submission without digital payment gateway collection. | Integrate Razorpay / UPI payment gateway or cash collection receipt step. |
| **Real-Time GPS Streaming**| 5s HTTP polling | Route tracking polls `GET /jobs/{id}` and updates map markers every 5 seconds. | Upgrade active tracking to WebSockets or Server-Sent Events (SSE). |
| **Push Notifications** | In-app visual alerts | Workers must keep the browser tab open to receive new job notifications. | Integrate Firebase Cloud Messaging (FCM) service worker for mobile background alerts. |
| **Job Photo Uploads** | Text description only | `CreateJobPage` currently does not accept photo attachments of household damage. | Add photo file picker with client-side image compression. |
| **Address Autocomplete** | Pin-drop and manual text | `MapPicker` allows dragging coordinates but lacks an address search autocomplete bar. | Integrate OpenStreetMap Nominatim or Google Places geocoding search input. |
| **Admin Viewport Shell** | 448px mobile wrapper | The Administrator Console is constrained inside `MobileLayout.jsx`, limiting screen real estate for document moderation. | Separate Admin layout into full-width responsive desktop dashboard. |

---

## 3. Recommended Phase 2 Roadmap

1. **Dual-App Separation**:
   - Split single repository into two distinct application deployments:
     - App 1: `RepairBuddy Customer` (Customer portal, booking, negotiation, tracking)
     - App 2: `RepairBuddy Partner` (Worker dashboard, KYC, earnings + Admin Console on desktop layout)
2. **Payment Settlement Integration**:
   - Embed Razorpay SDK into job completion lifecycle before routing to reviews.
3. **Real-time WebSockets / FCM**:
   - Replace 5-second polling loop with persistent WebSocket subscriptions for sub-second quote negotiation and route tracking.

