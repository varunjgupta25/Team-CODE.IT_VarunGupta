# Phase 4 — Cross-App Session & State Report

## 1. Cross-Domain Browser Isolation

Because the Customer App and Partner App are deployed on **distinct frontend origins** (e.g. `https://repairbuddy-customer.vercel.app` and `https://repairbuddy-partner.vercel.app`):
- Browsers enforce the **Same-Origin Policy** (SOP).
- `localStorage`, `sessionStorage`, and `IndexedDB` **are completely isolated per origin**.
- Logging in or storing credentials in the Customer App does **not** grant authentication state to the Partner App, and vice versa.

---

## 2. Authentication Flow & Token Lifecycle

```
Customer App (Domain A)              Partner App (Domain B)
      │                                     │
      ▼                                     ▼
Firebase Auth SDK                      Firebase Auth SDK
 (Customer Creds)                      (Worker / Admin Creds)
      │                                     │
      ├────── Both retrieve JWTs from ──────┤
      │        SAME Firebase Project        │
      ▼                                     ▼
Authorization: Bearer <JWT>            Authorization: Bearer <JWT>
      │                                     │
      └──────────── Shared Backend ─────────┘
             Cryptographic Verification
```

### Key Operational Rules:
1. **Independent Sign-In Required**:
   - A user operating as both a Customer and a Worker must sign in independently on each application.
   - No custom cross-domain cookie-sharing or iframe postMessage relay is implemented, eliminating cross-site session hijacking attack vectors.
2. **Zero URL Token Exposure**:
   - Authentication tokens must **never** be passed through query parameters or hash fragments in cross-domain redirect URLs.
   - All token transfers must occur strictly within the `Authorization: Bearer <token>` HTTP header.
3. **Session Expiration & Refresh**:
   - Standard Firebase ID tokens expire after 1 hour (3600 seconds).
   - Each client frontend application's Firebase client SDK is responsible for automatically refreshing ID tokens using its local refresh token.
   - The shared backend validates token timestamps and rejects expired tokens with `401 Unauthorized`.
4. **Predictable Logout**:
   - Clicking "Log Out" in the Customer App clears the session in the Customer App domain only.
   - Revoking refresh tokens via Firebase Admin Auth invalidates sessions platform-wide.

