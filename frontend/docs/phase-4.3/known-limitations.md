# Phase 4.3 — Known Limitations & Architectural Boundaries

**Project:** RepairBuddy  
**Branch:** `phase-4.3-final-production-hardening`  
**Date:** 2026-11-06  

---

## 1. Documented Boundaries & Explicit Product Decisions

1. **Direct Cash Settlement Model (Zero Escrow by Design):**
   - RepairBuddy intentionally operates on a direct cash settlement model (0% platform commission).
   - The platform does not escrow or hold customer funds in a digital wallet. This simplifies compliance with Indian financial regulations and builds immediate trust with blue-collar workers.
2. **Static Regional Road Network (Mira-Bhayandar, Mumbai):**
   - Accurate road navigation and Dijkstra graph calculations use the static OpenStreetMap GraphML asset (`data/mira_bhayandar.graphml`).
   - For geographic areas outside the Mira-Bhayandar region, the backend falls back to high-accuracy Haversine distance calculations ($25\text{ km/h}$ average transit speed) to ensure nationwide availability without crashing.
3. **External Dashboard Configuration:**
   - Setting private production secrets in the Render dashboard (`FIREBASE_CREDENTIALS_JSON`) and setting up the two independent Vercel projects requires owner intervention via web interfaces that cannot be automated via CLI.
