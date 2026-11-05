# Phase 0: Customer Application Technical & Functional Audit

**Application**: RepairBuddy Customer Portal  
**Target User Persona**: Urban household consumers requiring immediate or scheduled home services  
**Auditor**: Senior Frontend Architect & UI/UX Auditor  
**Date**: November 2026  
**Status**: Inspection-Only Audit Complete  

---

## 1. Customer Persona Overview

The RepairBuddy Customer Application provides an end-to-end service lifecycle: phone-based authentication, category exploration, job request posting with geo-location pinning, worker discovery, price negotiation with counter-offers, live tracking with route maps and SOS panic handling, rating/review submission, and profile management.

Currently, this portal is rendered within the unified mobile container (`/customer`, `/create-job`, `/matched-workers`, `/job-status/:jobId`, `/review/:jobId`, `/profile`).

---

## 2. Customer Screen & Workflow Audit

### 2.1 Authentication & Registration (`src/pages/AuthPage.jsx`)
* **Purpose**: Phone OTP onboarding and authentication.
* **Implementation Details**:
  * Leverages Firebase Phone Auth with invisible `recaptcha-container`.
  * Multi-step UI: Step 1 collects phone number and role selection; Step 2 verifies 6-digit OTP code.
  * Form validations ensure Indian phone format (`+91` prefix with 10 digits).
  * Automatically attempts registration via `POST /customers/register`. If returning user (HTTP 409 Conflict), gracefully completes login without throwing user-facing errors.
* **Observed Gaps**:
  * If a user logs in with a phone registered as a Worker while selecting "Customer", the system shows an error message but does not offer an automated redirect or account linking option.

---

### 2.2 Customer Homepage (`src/pages/CustomerHome.jsx`)
* **Purpose**: Primary dashboard displaying service categories, active job banners, and platform trust indicators.
* **Component Composition**: `Header`, `TrustBadge`, `Skeleton`, `BottomNav`, Service Category Grid.
* **Data Sources**:
  * Categories fetched via `api.getCategories()`.
  * Active jobs synchronized from `jobStore.activeJob`.
* **Behavior & State**:
  * Shows an animated banner if an active job exists (`posted`, `negotiating`, `accepted`, `arrived`, `in_progress`), providing a 1-tap shortcut to `/job-status/:id`.
  * Grid displays 8 default service categories (Plumbing, Electrical, Carpentry, Appliance Repair, Painting, Cleaning, Pest Control, AC Service).
* **Observed Gaps**:
  * No search or filtering bar for searching specific sub-services or keywords.
  * Category click directly routes to `/create-job?category={id}` without displaying estimated baseline pricing or sub-service selection.

---

### 2.3 Job Creation Wizard (`src/pages/CreateJobPage.jsx`)
* **Purpose**: Structured job posting interface.
* **Form Steps & Inputs**:
  1. **Category Selection**: Dropdown or preset category badge.
  2. **Problem Description**: Textarea with 10-character minimum validation.
  3. **Location Pinning**: Interactive `MapPicker` (Leaflet) with auto-detected coordinates and manual address input.
  4. **Budget Setting**: Numerical input with minimum threshold (₹100).
  5. **Urgency / Scheduling**: Radio selection ("Immediate - within 60 mins" vs "Scheduled later").
* **API Integration**: Submits payload to `api.createJob()` (`POST /jobs`).
* **Observed Gaps**:
  * Image/photo attachment for household damages is completely missing (no file input or image compression utility).
  * Address autocompletion using a Places API is not implemented; users must drag the pin or type freeform text.

---

### 2.4 Worker Discovery & Comparison (`src/pages/MatchedWorkersPage.jsx`)
* **Purpose**: Displays nearby verified service professionals matched to the created job.
* **Component Composition**: Worker list cards, Trust badges (Govt ID, Police Verified), Distance/ETA indicators, Quoted Rates.
* **Data Sources**:
  * Fetches matched workers using `api.getMatchedWorkers(jobId)`.
* **Interaction Flow**:
  * Customer can tap "Request Service" or initiate custom negotiation with an initial offer.
* **Observed Gaps**:
  * In live mode, backend matchmaking depends on worker availability radius; if backend returns an empty array, the UI renders `EmptyState` without fallback options (e.g., "Expand search radius").
  * Worker profile modal or detailed reviews history is not accessible from the list card.

---

### 2.5 Price Negotiation & Counter-Offers (`src/pages/JobStatusPage.jsx`)
* **Purpose**: Real-time counter-bidding interface between customer and assigned worker.
* **Features**:
  * Bid history card displaying Customer Offer vs. Worker Counter-Offer.
  * Quick-action buttons: "Accept Offer", "Counter with New Price", "Reject".
  * Auto-polls job updates every 5 seconds via `jobStore.startPolling(jobId)`.
* **API Integration**: Calls `api.acceptOffer(jobId, offerId)` and `api.counterOffer(jobId, amount)`.
* **Observed Gaps**:
  * Maximum counter-offer rounds (e.g., 3-round cap) are enforced solely through UI state rather than backend validation.
  * No live chat or text messaging interface between customer and worker during negotiation.

---

### 2.6 Active Job Tracking & Route Map (`src/pages/JobStatusPage.jsx` + `RouteMap.jsx`)
* **Purpose**: Geospatial tracking of worker transit and on-site service delivery.
* **Status Progression Display**:
  * `posted` -> `negotiating` -> `accepted` -> `arrived` -> `in_progress` -> `completed`
* **Route Mapping**:
  * `RouteMap.jsx` plots Customer GPS and Worker GPS using Leaflet SVG markers.
  * Synthesizes animated travel trajectory and calculates remaining distance and ETA.
* **Observed Gaps**:
  * Worker GPS updates in live mode require WebSocket or Server-Sent Events (SSE); the frontend currently relies on 5-second polling of `GET /jobs/{id}`.

---

### 2.7 Safety Features: SOS & Dispute Reports (`SosButton.jsx` & `ReportModal.jsx`)
* **SOS Button**:
  * Available on active job screens (`JobStatusPage`).
  * Features a 3-second hold-to-activate countdown with visual cancel feedback.
  * Emits `POST /jobs/{id}/sos` or `POST /sos` alerting platform dispatchers.
  * Triggers an audible browser siren alert via Web Audio API.
* **Dispute & Report Modal**:
  * Allows customer to flag workers for overcharging, property damage, harassment, or no-show.
  * Calls `POST /reports`.
* **Observed Gaps**:
  * Emergency contact auto-dialing (`tel:` protocol) relies on local browser handling without fallback SMS dispatch.

---

### 2.8 Review & Feedback Submission (`src/pages/ReviewPage.jsx`)
* **Purpose**: Post-service rating and quality appraisal.
* **Inputs**:
  * 1 to 5 Star interactive rating.
  * Quality tag chips ("Punctual", "Clean Work", "Polite", "Fair Price").
  * Written feedback textarea.
* **API Integration**: Calls `api.submitReview()` (`POST /reviews`).
* **Observed Gaps**:
  * Tipping or cashless payment settlement is not integrated into the review flow.

---

### 2.9 Profile & Emergency Management (`src/pages/ProfilePage.jsx`)
* **Features**:
  * View authenticated phone number and customer display name.
  * Emergency Contact CRUD (`api.getEmergencyContact()` / `api.setEmergencyContact()`).
  * Role Switcher shortcut (Customer <-> Worker).
  * Sign out action clearing Firebase auth and local storage tokens.

---

## 3. Customer Feature Implementation Matrix

| Screen / Feature | Current Implementation Status | Data Source (Live / Mock) | Quality / Edge Case Assessment |
| :--- | :--- | :--- | :--- |
| **Phone OTP Login** | Fully Implemented | Firebase Live SDK | Robust. Handles reCAPTCHA and token claims. |
| **User Registration** | Fully Implemented | Backend API (`/customers/register`) | Gracefully absorbs 409 for returning users. |
| **Service Categories Grid** | Fully Implemented | Backend API (`/categories`) / Mock | Displays 8 categories. Missing search bar. |
| **Job Posting Form** | Fully Implemented | Backend API (`/jobs`) | Clean form. Lacks photo damage attachments. |
| **Map Pin Location Drop** | Fully Implemented | Leaflet / OpenStreetMap | Pin dragging functional. Lacks autocomplete. |
| **Worker Matching List** | Fully Implemented | Backend API / Mock | Displays verified badges, distance, rates. |
| **Price Negotiation** | Fully Implemented | Backend API (`/jobs/:id/offers`) | Polling-based counter-offer negotiation. |
| **Route Map Tracking** | Partially Implemented | Leaflet / Client Simulation | Straight-line interpolation. Lacks live GPS feed. |
| **SOS Alert Trigger** | Fully Implemented | Backend API (`/sos`) | 3s hold-to-activate, audio siren alert. |
| **Dispute Reporting** | Fully Implemented | Backend API (`/reports`) | Modal with category tags and description. |
| **Review Submission** | Fully Implemented | Backend API (`/reviews`) | 5-star rating + feedback chips. |
| **Emergency Contact** | Partially Implemented | Backend API / LocalStorage | Dependent on `/users/me/emergency-contact`. |

---

## 4. Incomplete Customer Workflows & UI/UX Issues

1. **Lack of In-App Payments**: Once a job is marked `completed`, there is no payment gateway integration (Razorpay/Stripe). The app marks the job completed and routes directly to `/review/:jobId`.
2. **Missing Real-Time Messaging**: No chat channel between customer and worker; users must rely on external phone calls.
3. **No Photo Uploads on Creation**: Customers cannot upload photos of plumbing leaks or electrical faults.

