# Phase 1: Frontend Authentication & Authorization Report

**Project**: RepairBuddy Frontend  
**Auditor**: Senior Frontend Architect & Security Engineer  
**Date**: November 2026  
**Status**: Authentication Hardening Complete  

---

## 1. Firebase Authentication Lifecycle & Persistence

RepairBuddy uses **Firebase Phone Authentication** (SMS OTP) backed by Firebase Web SDK v11/v13:
- Primary Entry: `src/pages/AuthPage.jsx`
- Auth Helper: `src/lib/firebase.js`
- State Store: `src/store/authStore.js`

### Improvements Implemented in Phase 1:
1. **Reactive Session Synchronization (`initAuth`)**:
   - Subscribed to `onAuthStateChanged(auth, callback)`.
   - On application startup or browser reload, Firebase restores session credentials asynchronously from IndexedDB.
   - Fresh tokens are extracted via `firebaseUser.getIdToken()` and synced to `localStorage.getItem('rb_auth_token')`.
2. **Hydration Protection (`isInitialized`)**:
   - Introduced `isInitialized` boolean flag in `useAuthStore`.
   - `ProtectedRoute.jsx` intercepts route rendering while `isInitialized === false` and displays a centered loading indicator:
     ```jsx
     if (!isInitialized) {
       return (
         <div className="flex flex-col items-center justify-center min-h-[50vh] text-slate-500 text-xs font-semibold gap-2">
           <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
           <span>Verifying authentication session...</span>
         </div>
       );
     }
     ```
   - This eliminates the previous bug where reloading any protected page caused an immediate false redirect to `/login`.

---

## 2. Token Management & Refresh Strategy

* **Per-Request Token Attachment**:
  - `apiClient.interceptors.request` calls `getFreshIdToken(false)`.
  - Firebase SDK handles internal token caching and refreshes tokens before the 1-hour expiration window.
* **401 Unauthorized Auto-Recovery**:
  - If the backend returns `401 Unauthorized` on an authenticated request, `apiClient.interceptors.response` initiates a single force-refresh with `getFreshIdToken(true)`.
  - The request config is marked with `_authRetry = true` to strictly prevent infinite retry loops.
  - If force-refresh succeeds, the failed request is re-dispatched with the fresh Bearer token transparently.
  - If force-refresh fails, local tokens are cleared and the user is signed out cleanly.

---

## 3. Role-Based Route Protection & Admin Claim Gating

Route authorization is strictly validated inside `src/components/layout/ProtectedRoute.jsx`:

1. **Unauthenticated Users**:
   - If `!user || !role`, redirects to `/login` with `state: { from: location }` to allow post-login restoration of destination.
2. **Role Boundaries**:
   - Customers accessing `/worker/*` receive an explicit error toast and are redirected to `/`.
   - Workers accessing Customer job creation/status pages receive an error toast and are redirected to `/worker`.
3. **Administrator Route Protection (`/admin`)**:
   - Evaluates cryptographic Firebase ID Token claims:
     ```javascript
     const result = await currentUser.getIdTokenResult(true);
     const hasAdminClaim =
       result.claims?.[ADMIN_CLAIM_KEY] === true || result.claims?.role === 'admin';
     ```
   - If claims are absent or invalid, access is revoked, an error toast is emitted (`"Access denied. Administrator privileges required."`), and the user is redirected to their default persona dashboard.

---

## 4. Session Teardown & Logout Verification

When `authStore.logout()` is called:
1. `signOutFirebase()` terminates the Firebase Auth session.
2. `storage.remove('rb_auth_user_session')` and `storage.remove('rb_auth_role_session')` purge user profiles.
3. `localStorage.removeItem('rb_auth_token')` destroys the Bearer token.
4. Active background job polling is stopped (`stopPolling()`), and active job state is reset to prevent orphan network requests.
5. Store user and role are set to `null`.

