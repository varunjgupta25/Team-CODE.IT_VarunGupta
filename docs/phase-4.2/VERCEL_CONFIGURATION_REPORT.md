# Phase 4.2 — Vercel Configuration & Output Isolation Report

**Project:** RepairBuddy  
**Branch:** `phase-4.2-final-corrections`  
**Date:** 2026-11-06  
**Status:** Implemented & Documented  

---

## 1. Objective

Provide a reliable, unambiguous deployment architecture for running two separate Vercel projects (Customer App and Partner App) from a single shared frontend codebase without code duplication.

---

## 2. Target Architecture

```
                                  +------------------------------+
                                  |   Shared GitHub Repository   |
                                  |   (frontend/ directory)      |
                                  +--------------+---------------+
                                                 |
                       +-------------------------+-------------------------+
                       |                                                   |
                       v                                                   v
         +---------------------------+                       +---------------------------+
         |  Customer Vercel Project  |                       |  Partner Vercel Project   |
         |  (repair-buddy-customer)  |                       |  (repair-buddy-partner)   |
         +-------------+-------------+                       +-------------+-------------+
                       |                                                   |
         Build: npm run build:customer                       Build: npm run build:partner
         Output: dist/customer                               Output: dist/partner
                       |                                                   |
                       +-------------------------+-------------------------+
                                                 |
                                                 v
                                  +------------------------------+
                                  |    Render Web Service        |
                                  |  https://repair-buddy.onrender... |
                                  +------------------------------+
```

---

## 3. Project Configuration Files

### 3.1 Customer App (`frontend/vercel.customer.json`)
```json
{
  "buildCommand": "npm run build:customer",
  "outputDirectory": "dist/customer",
  "env": {
    "VITE_APP": "customer",
    "VITE_USE_MOCK": "false",
    "VITE_API_BASE_URL": "https://repair-buddy.onrender.com/api"
  },
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

### 3.2 Partner App (`frontend/vercel.partner.json`)
```json
{
  "buildCommand": "npm run build:partner",
  "outputDirectory": "dist/partner",
  "env": {
    "VITE_APP": "partner",
    "VITE_USE_MOCK": "false",
    "VITE_API_BASE_URL": "https://repair-buddy.onrender.com/api"
  },
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

---

## 4. Vercel Project Setup Instructions for Repository Owner

Because Vercel Git integration reads settings from the Project Dashboard by default, the repository owner must configure the following in the Vercel Dashboard:

### Project 1: `repair-buddy-customer`
1. **Root Directory:** `frontend`
2. **Framework Preset:** Vite
3. **Build Command:** Toggle Override ON -> `npm run build:customer`
4. **Output Directory:** Toggle Override ON -> `dist/customer`
5. **Install Command:** `npm install`
6. **Environment Variables:**
   - `VITE_APP` = `customer`
   - `VITE_USE_MOCK` = `false`
   - `VITE_API_BASE_URL` = `https://repair-buddy.onrender.com/api`
   - `VITE_FIREBASE_API_KEY` = `<production_key>`
   - `VITE_FIREBASE_PROJECT_ID` = `repair-buddy`

### Project 2: `repair-buddy-partner`
1. **Root Directory:** `frontend`
2. **Framework Preset:** Vite
3. **Build Command:** Toggle Override ON -> `npm run build:partner`
4. **Output Directory:** Toggle Override ON -> `dist/partner`
5. **Install Command:** `npm install`
6. **Environment Variables:**
   - `VITE_APP` = `partner`
   - `VITE_USE_MOCK` = `false`
   - `VITE_API_BASE_URL` = `https://repair-buddy.onrender.com/api`
   - `VITE_FIREBASE_API_KEY` = `<production_key>`
   - `VITE_FIREBASE_PROJECT_ID` = `repair-buddy`

---

## 5. Verification Status

- **Implemented:** Yes (`vite.config.js` and `vercel.*.json` files updated)
- **Tested Locally:** Both `dist/customer` and `dist/partner` independently build without collisions.
- **Pending Owner Verification:** Creation/confirmation of the two Vercel dashboard projects.

