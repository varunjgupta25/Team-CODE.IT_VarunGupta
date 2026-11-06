# Phase 4.3 — Deployment Readiness & Infrastructure Report

**Project:** RepairBuddy  
**Branch:** `phase-4.3-final-production-hardening`  
**Date:** 2026-11-06  
**Status:** Ready for Owner Verification  

---

## 1. Production Architecture Overview

The system runs across two managed hosting environments communicating with Google Cloud Firestore:

1. **Customer Frontend (Vercel):** Independent deployment serving households.
2. **Partner Frontend (Vercel):** Independent deployment serving workers and administrators.
3. **Backend API (Render):** Shared Python FastAPI web service.
4. **Database (Firestore):** Shared persistent NoSQL database.

---

## 2. Infrastructure Specifications

### 2.1 Customer Vercel Project
- **Project Name:** `repair-buddy-customer`
- **Root Directory:** `frontend`
- **Build Command:** `npm run build:customer`
- **Output Directory:** `dist/customer`
- **Production URL:** `https://repair-buddy-customer.vercel.app`
- **Required Environment Variables:**
  - `VITE_APP` = `customer`
  - `VITE_USE_MOCK` = `false`
  - `VITE_API_BASE_URL` = `https://repair-buddy.onrender.com/api`
  - `VITE_FIREBASE_API_KEY` = `<production_key>`
  - `VITE_FIREBASE_PROJECT_ID` = `repair-buddy`

### 2.2 Partner Vercel Project
- **Project Name:** `repair-buddy-partner`
- **Root Directory:** `frontend`
- **Build Command:** `npm run build:partner`
- **Output Directory:** `dist/partner`
- **Production URL:** `https://repair-buddy-partner.vercel.app`
- **Required Environment Variables:**
  - `VITE_APP` = `partner`
  - `VITE_USE_MOCK` = `false`
  - `VITE_API_BASE_URL` = `https://repair-buddy.onrender.com/api`
  - `VITE_FIREBASE_API_KEY` = `<production_key>`
  - `VITE_FIREBASE_PROJECT_ID` = `repair-buddy`

### 2.3 Shared Render Backend
- **Service Name:** `repair-buddy`
- **Runtime:** Python 3.11+
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health`
- **Auto Deploy:** `false` (Strict manual deployment)
- **Required Environment Variables:**
  - `ENV` = `production`
  - `USE_MOCK_FIREBASE` = `false`
  - `AUTO_SEED` = `false`
  - `CUSTOMER_APP_ORIGIN` = `https://repair-buddy-customer.vercel.app`
  - `PARTNER_APP_ORIGIN` = `https://repair-buddy-partner.vercel.app`
  - `CORS_ORIGINS` = `https://repair-buddy-customer.vercel.app,https://repair-buddy-partner.vercel.app`
  - `FIREBASE_CREDENTIALS_JSON` = `<service_account_credentials_json>`

---

## 3. Verification State Classification

- **Source Code & Local Builds:** VERIFIED
- **Configuration Manifests:** VERIFIED
- **External Dashboard Settings:** PENDING OWNER VERIFICATION
- **Live Production Deployment:** PENDING OWNER VERIFICATION
