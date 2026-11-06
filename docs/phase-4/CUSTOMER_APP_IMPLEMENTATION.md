# Customer App Implementation Report

## 1. Overview

The **RepairBuddy Customer App** is an on-demand, mobile-first web application designed for household residents seeking reliable, vetted blue-collar repair services (plumbing, electrical, appliance repair, carpentry, painting, cleaning, masonry) delivered within 30 minutes.

- **Build Target**: `VITE_APP=customer`
- **Output Bundle**: `dist/`
- **Target Audience**: Household customers in suburban and metropolitan clusters.
- **Entry Point**: `src/apps/customer/CustomerApp.jsx`

---

## 2. Implemented Core User Flows

### A. Authentication & Sign-In (`CustomerAuthPage.jsx`)
- **Phone OTP Verification**: Enter 10-digit mobile number, receives 6-digit SMS code via Firebase Phone Auth or automated simulated OTP (`1234` in mock mode).
- **Session Persistence**: User profile, Firebase ID token, and role are synchronized into `localStorage` (`repair_buddy_user_v1`, `repair_buddy_role_v1`).
- **1-Click Testing Profile**: Preconfigured sign-in for `Priya Sharma (+91 98200 11001, Mira Road East)` enabling immediate QA without manual typing.
- **Strict Role Boundary**: Exclusively registers and signs in users with `role: 'customer'`.

### B. Hyperlocal Home & Category Exploration (`CustomerHome.jsx`)
- **Location Context**: Displays current neighbourhood detection (`Mira Road East, Mumbai`).
- **Service Categories**: Grid displaying 8 core categories with standard market visit rates:
  - Plumber (₹350)
  - Electrician (₹300)
  - Appliance Repair (₹400)
  - House Painter (₹500)
  - Deep Cleaner (₹450)
  - Maid & Househelp (₹250)
  - Carpenter (₹400)
  - Mason (₹450)
- **Active Job Quick Bar**: Floating live banner notifying customer if an active job is in negotiation or in progress.

### C. Household Service Job Creation (`CreateJobPage.jsx`)
- **Description & Validation**: Minimum 10 characters describing the home issue.
- **Hyperlocal Location Input**: Manual address text with fallback or GPS coordinate selection using interactive Leaflet map pin (`MapPicker.jsx`).
- **Pricing Mode**: Support for `on-demand` (immediate 30-min doorstep dispatch) or scheduled visit.
- **Customer Budget**: Numerical budget input with category-specific suggestions.

### D. Worker Discovery & Hyperlocal Matching (`MatchedWorkersPage.jsx`)
- **Matching Engine Integration**: Fetches top nearest qualified workers within a 10 km radius ranked by proximity, composite rating, and trust score.
- **Worker Cards**: Displays worker photo, verified Aadhaar badge, rating, completed jobs count, distance (km), and ETA (mins).
- **Initial Offer Dispatch**: Customer submits their booking offer (quote) to start direct negotiation.

### E. Price Negotiation & Direct Bidding
- Real-time polling of worker counter-bids.
- Visual display of worker counter-offers with price delta.
- Single-tap **"Accept Offer"** action locking the final agreed rate into the job record.

### F. Doorstep Arrival & Job Tracking (`JobStatusPage.jsx`)
- Live 5-stage progress tracker: `Requested` ➔ `Agreed` ➔ `Worker Heading Over` ➔ `In Progress` ➔ `Work Complete`.
- Leaflet Route Map (`RouteMap.jsx`) rendering the customer's home and the technician's route.
- Direct worker phone call shortcut.

### G. Two-Step Completion & 0% Escrow Cash Settlement
- **Worker Complete**: Technician marks job complete, transitioning status to `awaiting_confirmation`.
- **Customer Cash Payment**: Customer inspects completed work, hands cash directly to the technician, and clicks **"Confirm & Settle Cash Payment"**.
- Status transitions to `completed` with zero platform escrow deductions.

### H. Review & Reputation Submission (`ReviewPage.jsx`)
- 5-star interactive rating system.
- One-tap compliment tags: *"On Time"*, *"Clean Work"*, *"Polite"*, *"Fair Pricing"*, *"Expert Diagnostician"*.
- Optional text review updating the tradesman's public trust rating.

### I. Safety & Emergency SOS (`SosButton.jsx` & `EmergencyModal`)
- Prominent SOS trigger accessible during active service delivery.
- One-tap dispatch sending instant emergency SMS/WhatsApp alerts with GPS coordinates to the customer's registered emergency contact and operations center.
- In-app incident reporting (`ReportModal.jsx`) allowing photo attachments and incident categorization.

---

## 3. Dedicated Customer Layout & Navigation

- **`CustomerHeader.jsx`**:
  - Branded as `RepairBuddy` with emerald `30m Guarantee` badge.
  - User avatar with clickable dropdown for `/profile` and `Log Out`.
- **`CustomerBottomNav.jsx`**:
  - Tab 1: **Book** (`/`)
  - Tab 2: **Active Job** (`/customer/status`) with green pulsing badge when job is active.
  - Tab 3: **Profile** (`/profile`)
  - **Zero Worker Links**: Excludes all worker feeds, earnings, and admin pages.

