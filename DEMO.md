# Repair Buddy — Live Demo Kit & Playbook

> **One-Line Pitch:** *"Blinkit for Blue-Collar Workers"* — Hyperlocal, on-demand skilled trades (plumbers, electricians, painters, cleaners) connected in under 60 seconds with road-network arrival ETAs under 30 minutes, worker-set rates, zero middleman commission, and built-in trust scoring.

---

## 1. Pre-Demo Checklist (5 Minutes Before)

| Step | Action | Command / Check | Expected Result |
|---|---|---|---|
| **1. Wake Backend** | Render free tier sleeps after 15 min of inactivity. Wake it up. | `curl -s https://<your-render-app>.onrender.com/health` | HTTP 200 `{"status":"healthy","service":"Repair Buddy API"}` (allow 30–45s if cold boot) |
| **2. Verify Frontend Mode** | Ensure Vercel frontend is communicating with live backend. | Open DevTools Console on frontend URL | Console prints: `[RepairBuddy API] Running in LIVE mode.` |
| **3. Automated Health Scan** | Run the end-to-end deployed test script. | `python scripts/e2e_deployed.py https://<your-render-app>.onrender.com` | `ALL 21 CHECKS PASSED PERFECTLY!` |
| **4. Clean Browser State** | Clear `localStorage` or open an Incognito window. | In browser console: `localStorage.clear()` | Clean slate, ready to show fresh customer and worker logins |

---

## 2. 3-Minute Demo Script (Numbered Checklist & Narration)

### Step 1: Customer Login & Problem Placement (0:00 – 0:45)
- **Action:** Open frontend URL (`https://<your-vercel-app>.vercel.app`).
- **Select Role:** Click **"Customer"**.
- **Credentials:** Enter Phone `+91 98201 11222` or UID `cust_priya` (Priya Sharma, Beverly Park, Mira Road East).
- **Post a Job:**
  - Select Category: **Plumber** (or **Electrician**).
  - Issue Description: *"Kitchen sink drain leaking rapidly under cabinet"*.
  - Location: Auto-detected as Mira Road East (`19.2825, 72.8570`).
  - Budget: `₹350` (on-demand).
  - Click **"Find Nearby Workers"**.
- **What to say:**
  > *"When an emergency pipe bursts or a short circuit happens, urban households can't wait 4 hours for a marketplace scheduler. Repair Buddy instantly indexes nearby verified blue-collar workers using Uber H3 hexagonal spatial indexing."*

---

### Step 2: Hyperlocal Matching & Road-Network Dijkstra Routing (0:45 – 1:30)
- **Screen:** Worker Match List (`/workers/match`).
- **Expected Data Shown:**
  - Top 1: **Ramesh Kumar** (`worker_plumber_1`) — ⭐ 4.9 (42 jobs) — **Gold Badge** (Trust: 99/100) — Rate: `₹350` — Distance: `0.75 km` — Arrival ETA: `1.5 mins` — **Within 30 Mins: YES**.
  - Top 2: **Suresh Plumber** (`worker_plumber_2`) — ⭐ 4.7 (38 jobs) — **Silver Badge**.
- **Action:** Click on **"View Route on Map"** or the top worker card.
- **Visual:** Map opens showing Dijkstra shortest-path road polyline navigating streets between Mira Road East and the worker location.
- **What to say:**
  > *"Notice the ranking. We don't just use crude as-the-crow-flies straight lines. Repair Buddy runs Dijkstra's algorithm on a 2.4 MB OpenStreetMap road network graph of Mira-Bhayandar, giving customers actual driving ETAs and guaranteed arrival within 30 minutes."*

---

### Step 3: Turn-Based Fair Price Negotiation (1:30 – 2:15)
- **Action:**
  1. Click **"Make Offer"** on Ramesh Kumar for `₹300`.
  2. Switch browser tab / window or log in as **Worker** (`worker_plumber_1`, Ramesh Kumar).
  3. Worker receives real-time offer notification: *"Priya offered ₹300"*.
  4. Worker clicks **"Counter"** with `₹350` (*"Standard valve replacement rate"*).
  5. Switch back to Customer tab: Customer receives counter and clicks **"Accept"**.
- **What to say:**
  > *"Unlike corporate aggregators that take 25% commissions and impose fixed pricing, Repair Buddy enables zero-commission, turn-based transparent negotiation where blue-collar tradesmen set and defend their own fair wages."*

---

### Step 4: Worker Verification & Admin Queue (2:15 – 3:00)
- **Action:**
  1. Switch to Worker profile: click **"Verify Identity"**.
  2. Submit document: Document Type **Aadhaar**, Number: `9988 7766 5544`. Status updates to *"Pending Admin Verification"*.
  3. Open Admin Dashboard at `/admin` (or log in as Admin `admin_user`).
  4. Show the **Pending Verification Queue**:
     - Worker appears in table: `Devendra Plumber` / `Kailash Electrician`.
     - Document Number is strictly masked: **`•••• 5544`** (never leaking full PII).
  5. Click **"Approve Worker"**.
  6. Return to Customer search: Worker is now verified, awarded a trust badge, and immediately appears in matching search results!
- **What to say:**
  > *"For household safety, unverified workers are strictly hidden from search. The admin review queue enforces strict data privacy by masking all Aadhaar numbers to the last 4 digits, ensuring Indian data sovereignty without leaks."*

---

## 3. "If Something Breaks" Quick Fallback Matrix

| Issue | Root Cause | Fallback / Fix to Say |
|---|---|---|
| **Render URL takes 40s to load** | Free tier spinning up from sleep | *"The backend is cold-booting from Render's free tier. While it wakes, let me walk you through our offline-first architecture."* (Auto-seeds upon booting). |
| **`/route` returns fallback straight line** | Coordinates outside 6 km road graph | Built-in fail-safe fallback: Haversine distance and speed formula triggers seamlessly without crashing the user interface. |
| **Database appears empty** | Ephemeral container rebooted | Auto-seed hook `AUTO_SEED=true` automatically restores 25 workers, 5 customers, 5 jobs, and `admin_user` on first boot. |
| **Browser OTP prompt appears** | Demo authentication mode | Enter any 6-digit code (e.g. `123456`) or use direct UID login (`cust_priya`, `worker_elec_1`, `admin_user`). |

---

## 4. Honest Architectural Limitations (If Asked by Judges)

1. **Authentication:**
   - *Current:* Demo-grade client OTP simulation with signed dev tokens (`token-<role>-<uid>`).
   - *Production Roadmap:* Firebase Auth SMS phone verification or Aadhaar OTP via DigiLocker.
2. **Database:**
   - *Current:* Thread-safe local JSON-backed mock Firestore for offline hackathon reproducibility.
   - *Production Roadmap:* Seamless toggle to live Google Cloud Firestore / Supabase Postgres via single env var `USE_MOCK_FIREBASE=false`.
3. **Identity & KYC:**
   - *Current:* Document upload with masked last-4 digits stored in admin queue.
   - *Production Roadmap:* Integration with Setu / Hyperverge / Bhashini for instant automated Aadhaar OCR & face liveness.
4. **Payments:**
   - *Current:* Cash-on-delivery / negotiated settlement model.
   - *Production Roadmap:* UPI intent deep-linking (PhonePe, Google Pay) with escrow release on customer job completion.
