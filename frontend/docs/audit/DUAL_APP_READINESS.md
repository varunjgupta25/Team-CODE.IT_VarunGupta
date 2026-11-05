# Phase 0: Dual-App Architecture Readiness Assessment

**Project**: RepairBuddy Frontend  
**Target Architecture**: Two Distinct Client Applications  
1. **RepairBuddy Customer**: Consumer-facing web app (Marketplace, Booking, Negotiation, Tracking, Reviews, SOS).  
2. **RepairBuddy Partner**: Worker dispatch radar, KYC, job lifecycle, earnings ledger + Admin Console.  
**Auditor**: Senior Frontend Architect & Systems Modularity Specialist  
**Date**: November 2026  
**Status**: Readiness Assessment Complete  

---

## 1. Executive Readiness Evaluation

* **Overall Dual-App Readiness Score**: **82 / 100 (High Readiness)**
* **Feasibility**: High. The codebase already features disciplined directory isolation (`src/pages/CustomerHome.jsx` vs `src/pages/WorkerDashboard.jsx` vs `src/pages/AdminPage.jsx`), role-gated routing in `src/App.jsx`, and a centralized API abstraction layer (`src/api`).
* **Primary Barrier**: Shared `BottomNav.jsx`, `Header.jsx`, and `authStore.js` currently maintain conditional branches checking `user.role === 'customer'` vs `'worker'` vs `'admin'`.

---

## 2. Component Coupling & Reusability Matrix

```
                          ┌──────────────────────────┐
                          │   Shared UI Foundation   │
                          │ (src/components/common)  │
                          └─────────────┬────────────┘
                                        │
           ┌────────────────────────────┴───────────────────────────┐
           ▼                                                        ▼
┌──────────────────────────┐                             ┌──────────────────────────┐
│  CUSTOMER APPLICATION    │                             │   PARTNER APPLICATION    │
│  - CustomerHome          │                             │  - WorkerDashboard       │
│  - CreateJobPage         │                             │  - WorkerJobDetailsPage  │
│  - MatchedWorkersPage    │                             │  - WorkerEarningsPage    │
│  - JobStatusPage         │                             │  - VerificationCard      │
│  - ReviewPage            │                             │  - AdminPage             │
│  - Customer Profile      │                             │  - Partner Profile       │
└──────────────────────────┘                             └──────────────────────────┘
```

| Component / Module | Current Location | Shared vs Persona-Specific | Migration Recommendation |
| :--- | :--- | :--- | :--- |
| **`Header.jsx`** | `src/components/common/` | Shared (branches by role) | Split into `CustomerHeader` and `PartnerHeader`. |
| **`BottomNav.jsx`** | `src/components/common/` | Shared (branches by role) | Split into `CustomerNav` and `PartnerNav`. |
| **`SosButton.jsx`** | `src/components/common/` | Shared (Universal SOS) | Extract to `@repairbuddy/ui-shared`. |
| **`ReportModal.jsx`** | `src/components/common/` | Shared (Universal Dispute) | Extract to `@repairbuddy/ui-shared`. |
| **`TrustBadge.jsx`** | `src/components/common/` | Shared (Displays trust scores) | Extract to `@repairbuddy/ui-shared`. |
| **`EmptyState.jsx`** | `src/components/common/` | Shared (Generic fallback UI) | Extract to `@repairbuddy/ui-shared`. |
| **`Skeleton.jsx`** | `src/components/common/` | Shared (Shimmer animation) | Extract to `@repairbuddy/ui-shared`. |
| **`MapPicker.jsx`** | `src/components/maps/` | Customer Only | Move to Customer package. |
| **`RouteMap.jsx`** | `src/components/maps/` | Shared (Job transit tracking) | Extract to `@repairbuddy/maps-shared`. |
| **`VerificationCard.jsx`** | `src/components/worker/` | Partner Only | Retain exclusively in Partner application. |
| **`authStore.js`** | `src/store/` | Shared (contains customer & worker logic) | Decouple or isolate role payloads. |
| **`jobStore.js`** | `src/store/` | Customer & Worker Polling | Share base polling engine; decouple job actions. |
| **`toastStore.js`** | `src/store/` | Shared (Global notifications) | Extract to `@repairbuddy/core-shared`. |
| **`api/client.js`** | `src/api/` | Shared (Axios + Firebase Auth) | Extract to `@repairbuddy/api-client`. |

---

## 3. Comparative Architecture Strategies for Dual-App Separation

### Option A: Monorepo with Workspaces (Recommended)
* **Structure**: `pnpm` workspaces or Turborepo:
  * `apps/customer/` (Vite + React SPA, deployed to `customer.repairbuddy.in`)
  * `apps/partner/` (Vite + React SPA, deployed to `partner.repairbuddy.in`)
  * `packages/ui/` (Shared buttons, cards, skeletons, modals)
  * `packages/api/` (Axios client, Firebase auth wrapper, shared types)
* **Pros**: Eliminates duplicate code, enables independent Vercel deployment pipelines, prevents administrative code from ever leaking into the customer bundle.
* **Cons**: Requires initial workspace restructuring and dependency configuration.

### Option B: Vite Multi-Config inside Single Repository
* **Structure**: Maintain existing single repo; introduce two Vite configs:
  * `vite.config.customer.js` -> builds `dist/customer/` targeting `index.customer.html`
  * `vite.config.partner.js` -> builds `dist/partner/` targeting `index.partner.html`
* **Pros**: Zero directory disruption; can be achieved with existing file layout.
* **Cons**: Less clear boundary for third-party packages; Vercel deployment routing requires dual project configurations.

### Option C: Standalone Separate Repositories
* **Structure**: Clone into two independent GitHub repositories.
* **Pros**: Complete physical isolation.
* **Cons**: Severe code drift and high maintenance overhead when updating shared API contracts and UI components.

---

## 4. Phase 1 Migration Roadmap

```
Step 1: Core Package Decoupling
├── Extract src/api, src/lib, src/types into a shared module layer
└── Cleanse role branching in authStore and client interceptors

Step 2: Customer App Bundling
├── Entry: src/customer-main.jsx -> AppCustomer.jsx
├── Routes: /customer, /create-job, /matched-workers, /job-status, /review, /profile
└── Target Domain: customer.repairbuddy.in / repairbuddy.vercel.app

Step 3: Partner App Bundling
├── Entry: src/partner-main.jsx -> AppPartner.jsx
├── Worker Routes: /worker, /worker/job/:id, /worker/earnings, /worker/profile
├── Admin Routes: /admin (Full desktop responsive shell)
└── Target Domain: partner.repairbuddy.in / repairbuddy-partner.vercel.app
```

