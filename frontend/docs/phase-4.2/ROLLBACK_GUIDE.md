# Phase 4.2 — Rollback Guide

**Project:** RepairBuddy  
**Branch:** `phase-4.2-final-corrections`  
**Date:** 2026-11-06  

---

## 1. Local Codebase Rollback

If it becomes necessary to discard Phase 4.2 changes and restore the local environment to the exact baseline:

```bash
# 1. Switch back to the main branch
git checkout main

# 2. Delete the Phase 4.2 isolated working branch
git branch -D phase-4.2-final-corrections
```

Because zero commits were pushed to any remote branch during Phase 4.2, `origin/main` on GitHub remains pristine at commit `e12e764`.

---

## 2. Production Vercel Rollback Runbook

If an issue occurs in a deployed Vercel frontend:
1. Log in to the [Vercel Dashboard](https://vercel.com).
2. Select the affected project (`repair-buddy-customer` or `repair-buddy-partner`).
3. Open the **Deployments** tab.
4. Locate the last stable deployment.
5. Click the three dots `...` and choose **Instant Rollback**.
6. The rollback takes effect globally in under 5 seconds without requiring a rebuild.

---

## 3. Production Render Rollback Runbook

If an issue occurs in the deployed Render backend web service:
1. Log in to the [Render Dashboard](https://dashboard.render.com).
2. Open the **repair-buddy** web service.
3. Navigate to **Deploys**.
4. Select the previous successful deployment commit.
5. Click **Rollback to this deploy**.
6. Render will re-deploy the previous container image within 30–60 seconds.
