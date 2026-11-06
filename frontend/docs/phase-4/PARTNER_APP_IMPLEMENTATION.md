# Partner App Implementation Report

## 1. Overview

The **RepairBuddy Partner App** is an operations and service fulfillment portal combining specialized interfaces for:
1. **Blue-Collar Tradesmen (Workers)**: Managing job discovery, bidding, doorstep arrival, job completion, cash collection, and government ID verification.
2. **Operations Administrators**: Reviewing worker identity verification submissions, resetting locked accounts, moderating customer disputes, and monitoring live emergency SOS alerts.

- **Build Target**: `VITE_APP=partner`
- **Output Bundle**: `dist/`
- **Entry Point**: `src/apps/partner/PartnerApp.jsx`

---

## 2. Tradesman (Worker) User Flows

### A. Dedicated Partner Authentication (`PartnerAuthPage.jsx`)
- **Portal Switcher**: Dual tabs for Tradesman Portal and Administrator Console.
- **Worker Onboarding**: Selects primary trade category (plumbing, electrical, appliance repair, etc.) and specifies standard base rate (₹/visit).
- **Fast QA Logins**:
  - `Ramesh Kumar` (+91 91101 00001) — Verified Plumber with Gold Trust Badge.
  - `Kamlesh Verma` (+91 91101 00005) — Unverified Plumber for testing document upload.

### B. Worker Dashboard & Availability Management (`WorkerDashboard.jsx`)
- **Real-Time Availability Toggle**: Switch between **"Available for Jobs"** (online) and **"Offline"**. Offline workers are automatically omitted from customer match results.
- **Service Dispatch Radius**: Configurable radius (5 km to 15 km) restricting job feed alerts to the technician's serviceable neighborhood.
- **Verification Status Banner**: Direct visual prompt for unverified workers to complete identity verification.

### C. Government ID Verification & Biometrics (`VerificationCard.jsx`)
- **Supported Documents**: Aadhaar Card, PAN Card, Driving License, Voter ID.
- **Document & Selfie Upload**: Uploads ID proof photo + live selfie.
- **Validation & Privacy**: Client-side image validation (PNG/JPEG, max 5 MB), automatic EXIF metadata stripping, and secure transmission.
- **Lifecycle Feedback**: Tracks verification state:
  - `unverified`: Initial state with upload button.
  - `pending`: Under administrative review with short-lived preview capability.
  - `approved`: Green verified checkmark and unlocked high-trust ranking.
  - `rejected`: Displays exact administrative rejection reason (e.g., *"Blurry document photo"*) with re-upload action.

### D. Hyperlocal Jobs Feed (`WorkerDashboard.jsx`)
- Continuously polls available requests in the technician's category and radius.
- Displays customer neighbourhood, distance (km), estimated travel time (mins), customer budget, and problem description.

### E. Offer Management & Price Negotiation (`WorkerJobDetailsPage.jsx`)
- **Inspect Request**: Full address, contact shortcut, and initial customer quote.
- **Accept Quote**: One-tap acceptance of the customer's initial offer.
- **Counter-Bidding**: Input a custom counter-offer (e.g., ₹450 if parts replacement is needed), triggering an instant negotiation alert on the customer's screen.

### F. Doorstep Job Execution
- **Step 1: Arrival & Start**: Worker taps **"Start Job"**, transitioning status to `in_progress`.
- **Step 2: Completion**: Worker finishes the repair and taps **"Mark Job Complete"**, transitioning status to `awaiting_confirmation`.

### G. 0% Escrow Direct Cash Earnings (`WorkerEarningsPage.jsx`)
- **Direct Cash Model**: Emphasizes RepairBuddy's core zero-commission model (workers retain 100% of cash collected).
- **Summary Metrics**: Total cash collected, jobs completed, and active platform rating.
- **Settlement Ledger**: Itemized list of completed service visits showing date, customer name, trade category, and cash amount received.

---

## 3. Administrator Operations Console (`AdminPage.jsx`)

Access to the administrator portal is strictly enforced using Firebase Custom Claims (`admin: true`) and role-based route gating (`RequireAdmin`).

### A. Worker Verification Queue
- **Live Queue**: Real-time listing of workers awaiting identity approval.
- **DPDP-Compliant Review**: Displays masked last-4 ID digits, document type, and secure short-lived preview links.
- **Approve Action**: Grants verified status, updates worker trust score, and sends approval notification.
- **Reject with Reason**: Mandatory administrative reason input (e.g., *"ID document name does not match worker profile"*), recording decision metadata and audit logs.
- **Reset Attempts**: Admin action to reset the verification counter for workers locked after 3 rejected attempts.

### B. Live Emergency SOS Alerts
- Instant real-time dashboard displaying high-priority safety emergencies triggered by customers or workers.
- Displays emergency timestamp, user identity, phone, role, GPS coordinates, registered emergency contact, and delivery status (SMS/WhatsApp).

### C. Customer & Worker Incident Reports
- Centralized queue of incident reports and disputes submitted via `ReportModal`.
- Filter by status (`pending`, `under_review`, `resolved`).
- Actions to update dispute status, record administrative notes, and resolve complaints.

---

## 4. Dedicated Partner Layout & Navigation

- **`PartnerHeader.jsx`**:
  - Branded as `RepairBuddy Partner` with amber `Partner` badge.
  - Shows `Worker` or `Admin` badge.
  - Logo click navigates directly to `/worker` (or `/admin` if administrator).
- **`PartnerBottomNav.jsx`**:
  - **Worker View**:
    1. **Jobs Feed** (`/worker`)
    2. **Earnings** (`/worker/earnings`)
    3. **Profile** (`/profile`)
  - **Admin View**:
    1. **Admin Console** (`/admin`)
    2. **Profile** (`/profile`)
  - **Zero Customer Links**: Does not render booking, category grids, or job creation tabs.

