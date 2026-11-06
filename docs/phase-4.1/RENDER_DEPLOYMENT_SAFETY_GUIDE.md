# Phase 4.1 — Render Deployment Safety Guide

**Project:** RepairBuddy  
**Branch:** `phase-4.1-stabilization`  
**Date:** 2026-11-06  

---

## 1. Overview

Render hosts the RepairBuddy FastAPI backend web service (`repair-buddy`). To protect production stability and avoid unauthorized or broken deployments from active branches, Render deployment has been converted from automatic deployment to a strictly controlled, manual-release model.

---

## 2. Hardened Infrastructure as Code (`render.yaml`)

The blueprint specification `render.yaml` has been updated with the following production safety settings:

```yaml
services:
  - type: web
    name: repair-buddy
    runtime: python
    buildCommand: pip install --upgrade pip && pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    autoDeploy: false # Strictly disabled automatic deployments upon git push
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
      - key: ENV
        value: production
      - key: USE_MOCK_FIREBASE
        value: "false" # Must use real Firestore in production
      - key: AUTO_SEED
        value: "false" # Auto-seeding disabled
      - key: CUSTOMER_APP_ORIGIN
        value: https://repair-buddy-customer.vercel.app
      - key: PARTNER_APP_ORIGIN
        value: https://repair-buddy-partner.vercel.app
      - key: CORS_ORIGINS
        value: https://repair-buddy-customer.vercel.app,https://repair-buddy-partner.vercel.app
      - key: FIREBASE_CREDENTIALS_JSON
        sync: false # Sensitive JSON service account key set via Render dashboard secret
      - key: SECRET_KEY
        generateValue: true # Secure session secret generated per deployment
```

### Key Safety Rules Enforced:
1. `autoDeploy: false`: Prevents inadvertent code pushes from immediately triggering a live production rollout.
2. `USE_MOCK_FIREBASE: "false"`: Ensures the production instance never boots in ephemeral mock mode.
3. `AUTO_SEED: "false"`: Safeguards production Firestore collections from being populated with sample records.
4. `CUSTOMER_APP_ORIGIN` & `PARTNER_APP_ORIGIN`: Exact production origins configured; wildcard regular expressions are removed.

---

## 3. Pre-Deployment Verification Checklist

Before manually triggering a deployment on Render:

- [ ] **Repository Status**: Changes are committed on `main` and verified through local test suites.
- [ ] **Backend Tests**: All pytest test cases pass locally (`pytest tests` -> 209 passing).
- [ ] **Secrets Configured**: In the Render Dashboard under **Environment**:
  - `FIREBASE_CREDENTIALS_JSON` contains valid production service account credentials.
  - `FIRESTORE_PROJECT_ID` is set to the correct production project ID.
- [ ] **Database Connection**: Firestore rules in the Firebase console allow read/write access to authenticated users.
- [ ] **Domain Origins**: Vercel domains for Customer and Partner apps match `CUSTOMER_APP_ORIGIN` and `PARTNER_APP_ORIGIN`.

---

## 4. Manual Deployment Procedure

1. Log in to the [Render Dashboard](https://dashboard.render.com).
2. Navigate to the **repair-buddy** Web Service.
3. Click the **Manual Deploy** button in the top right.
4. Select **Deploy latest commit** or specify the release commit tag.
5. Monitor the build logs:
   - Ensure dependencies install cleanly (`requirements.txt`).
   - Observe uvicorn startup logs.
   - Confirm that the startup log states: `Database auto-seeding skipped (ENV=production, AUTO_SEED=False)`.
6. Confirm health check passes:
   ```bash
   curl -i https://repair-buddy.onrender.com/health
   ```
   Expected response:
   ```json
   HTTP/1.1 200 OK
   {"status":"healthy","database":"connected","version":"..."}
   ```

---

## 5. Rollback Procedure

If any anomaly occurs post-deployment:
1. In the Render Dashboard, open the **Deploys** tab.
2. Locate the previous successful deployment.
3. Click the three dots menu `...` on that deploy and select **Rollback to this deploy**.
4. Render will immediately restore the previous container snapshot within 30–60 seconds.

