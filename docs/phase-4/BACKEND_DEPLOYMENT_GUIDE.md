# Phase 4 — Backend Deployment Guide

## 1. Deployment Overview

The backend remains a **single shared FastAPI deployment on Render**:
- **Service Name**: `repair-buddy`
- **Public URL**: `https://repair-buddy.onrender.com`
- **Health Check Endpoint**: `https://repair-buddy.onrender.com/health`
- **Interactive API Documentation**: `https://repair-buddy.onrender.com/docs`

No secondary backend service or database cluster is required.

---

## 2. Environment Variables Checklist for Render

When configuring the Render production environment for separate Customer and Partner frontends, set the following environment variables:

| Variable Name | Required | Example Production Value | Description |
|---|---|---|---|
| `ENV` | **Yes** | `production` | Enforces production security, disabling dev tokens & permissive regex |
| `CUSTOMER_APP_ORIGIN` | **Yes** | `https://repairbuddy-customer.vercel.app` | Production origin for Customer App |
| `PARTNER_APP_ORIGIN` | **Yes** | `https://repairbuddy-partner.vercel.app` | Production origin for Partner App (Worker + Admin) |
| `ALLOWED_ORIGINS` | Optional | `https://repairbuddy-customer.vercel.app,https://repairbuddy-partner.vercel.app` | Comma-separated fallback whitelist |
| `USE_MOCK_FIREBASE` | **Yes** | `false` | Enables live Google Cloud Firestore & Firebase Auth |
| `FIREBASE_CREDENTIALS_JSON` | **Yes** | `{"type": "service_account", ...}` | Raw JSON string of Firebase service account key |
| `TRANSIT_SPEED_KMH` | Optional | `25.0` | Default vehicle speed in km/h for ETA calculation |
| `AUTO_SEED` | Optional | `false` | Set to false in production to prevent auto-seeding |

---

## 3. Deployment Verification Steps

After applying the environment variables and deploying to Render, verify the service using the following sequence:

1. **Verify Health Endpoint**:
   ```bash
   curl -i -X GET https://repair-buddy.onrender.com/health
   ```
   *Expected Response*: `HTTP/2 200` with `{"status": "healthy", "mock_mode": false, ...}`

2. **Verify Customer App CORS Preflight**:
   ```bash
   curl -i -X OPTIONS https://repair-buddy.onrender.com/jobs \
     -H "Origin: https://repairbuddy-customer.vercel.app" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: authorization,content-type"
   ```
   *Expected Response*: `HTTP/2 200` with header `access-control-allow-origin: https://repairbuddy-customer.vercel.app`

3. **Verify Partner App CORS Preflight**:
   ```bash
   curl -i -X OPTIONS https://repair-buddy.onrender.com/workers/match \
     -H "Origin: https://repairbuddy-partner.vercel.app" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: authorization"
   ```
   *Expected Response*: `HTTP/2 200` with header `access-control-allow-origin: https://repairbuddy-partner.vercel.app`

4. **Verify Unauthorized Origin Rejection**:
   ```bash
   curl -i -X OPTIONS https://repair-buddy.onrender.com/jobs \
     -H "Origin: https://malicious-attacker.com" \
     -H "Access-Control-Request-Method: POST"
   ```
   *Expected Response*: `HTTP/2 200` without any `access-control-allow-origin` header.

