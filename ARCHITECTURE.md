# RepairBuddy Architecture Guide

## 1. What this project is

RepairBuddy is a hyperlocal, on-demand marketplace for household services such as
plumbing, electrical work, painting, cleaning, cooking, and carpentry. A customer
creates a job, the platform finds nearby verified workers, both parties can
negotiate a price, the worker completes the job, and the customer leaves a review.

The product is designed to solve four practical problems:

1. **Slow discovery:** customers need a skilled person nearby instead of calling
   several unknown service providers.
2. **Poor location estimates:** straight-line distance is not a reliable arrival
   estimate, so the backend can use an OpenStreetMap road graph and Dijkstra
   routing.
3. **Unclear pricing:** workers publish rates and customers can make transparent,
   alternating offers without a mandatory marketplace commission.
4. **Trust and safety:** verification, trust scores, privacy masking, reports, and
   SOS actions make the interaction safer than an anonymous listing.

The application is a two-part system:

```text
React/Vite SPA
    |
    | REST/JSON, Firebase ID token when live
    v
FastAPI application
    |
    +-- Routers: HTTP endpoints and authorization dependencies
    +-- Services: matching, jobs, offers, trust, routing, safety
    +-- Models: Pydantic request/response validation
    +-- Database adapter: Firestore or local mock store
    |
    +-- Optional Firestore
    +-- Cached Mira-Bhayandar road graph
```

The frontend also has an offline/demo mode. In that mode, browser local storage
acts as a small mock backend and the UI can be demonstrated without a running API.

## 2. End-to-end user flow

### Customer flow

1. The customer signs in through the frontend.
2. The customer selects a service category, describes the problem, chooses a
   location, and supplies a budget.
3. `POST /jobs` creates an `open` job.
4. `GET /workers/match?jobId=...` finds verified and available workers with the
   required skill inside their service radius.
5. H3 narrows the geographic candidate set; distance, rating, price, and completed
   jobs produce the initial ranking.
6. The top candidates may be re-ranked using road-network ETA.
7. The customer creates an offer. The job becomes `negotiating`.
8. The worker can counter. Only the other party may counter or accept the current
   offer.
9. Accepting an offer atomically sets the job to `accepted`, stores the worker and
   final price, and rejects other pending offers.
10. The worker starts and completes the job.
11. Completion increments `jobsDone`; the customer submits a review and the worker
    rating is recalculated.

### Worker flow

1. The worker registers a trade, rates, location, and service radius.
2. The worker submits identity verification. The backend stores only a masked
   document number in the verification queue.
3. An admin approves the worker. Only verified workers can appear in matching.
4. The worker views compatible nearby jobs, submits or counters offers, and sees
   only the exact address after becoming the accepted worker.
5. The worker starts and completes accepted jobs and sees estimated earnings.

### Safety and moderation flow

- An authenticated user can create an SOS record containing a job and coordinates.
- A user can report a worker or another platform entity.
- Recent unresolved reports can trigger `UNDER_REVIEW`; flagged workers are excluded
  from matching.
- Public worker serialization removes phone numbers, identity documents, bank
  details, and precise location details.

## 3. Backend architecture

### Application entry point: `main.py`

`main.py` creates the FastAPI application, registers CORS and rate-limit
middleware, formats validation errors, exposes health/root endpoints, and mounts
each router twice: at `/...` and `/api/...`. The lifespan hook connects the
database, optionally seeds demo data, preloads the road graph, and disconnects on
shutdown.

### Request boundary: `routers/`

Routers should remain thin. They:

- declare HTTP paths and response models;
- obtain the current user or enforce a role;
- validate request bodies through Pydantic models;
- call one domain service;
- return the service result.

The domain rules belong in `services/`, not in the route functions.

### Domain services: `services/`

- `distance.py` contains Haversine distance, ETA, and the 30-minute predicate.
- `h3_index.py` converts coordinates to H3 cells and performs a radius pre-filter.
- `matching.py` implements the two-stage worker matching pipeline:
  H3/filter/score first, then road ETA for the best candidates.
- `routing.py` loads `data/mira_bhayandar.graphml` once and uses NetworkX
  shortest-path routing weighted by travel time. If the graph or dependencies are
  unavailable, callers can retain Haversine estimates.
- `job_service.py` creates jobs, protects addresses, supplies worker feeds, and
  enforces the job state machine.
- `offer_service.py` implements offers, alternating counters, authorization, and
  transactional acceptance.
- `review_service.py` validates completed-job reviews and updates worker ratings.
- `trust_engine.py` calculates Bayesian ratings, account-age weighting, trust
  scores/badges, and report thresholds.
- `trust.py` is the public trust-service facade.
- `verification_service.py` manages worker verification requests and admin approval.
- `worker_privacy.py` serializes worker data for owner/admin versus public views.
- `report_service.py` records reports and applies abuse rules.
- `sos_service.py` records emergency alerts.

### Data layer: `core/database.py`

`FirestoreDB` is a storage abstraction with the same CRUD/query interface for:

- Google Cloud Firestore in configured deployments;
- a thread-safe in-memory mock store in development and tests.

The adapter adds IDs and timestamps, filters soft-deleted documents, supports
filtered queries, bulk reads, report aggregation, and transactions. Transactions
provide rollback in mock mode and Firestore transaction semantics in live mode.

The logical collections are:

```text
users, workers, jobs, offers, reviews, sos_alerts, reports
```

### Authentication and authorization

`core/auth.py` accepts Firebase ID tokens in live mode. Development accepts
explicitly recognizable demo tokens or seeded IDs, but rejects them whenever
`ENV` is not `development`. `require_role()` adds role-based access control for
customer, worker, and admin endpoints.

### Configuration and operational controls

- `core/config.py` loads environment variables, normalizes environments, resolves
  CORS origins, and defines database/transit settings.
- `core/rate_limit.py` applies per-IP token buckets: stricter limits for SOS and
  verification writes, and a larger default API limit. Health and documentation
  paths are excluded.

## 4. Core business rules

### Worker matching

Candidates must be verified, available, not flagged, skilled for the job, located
within their own service radius, and geographically close enough for the H3 filter.
The initial score is:

```text
40% distance + 30% rating + 20% price-versus-budget + 10% completed jobs
```

The top five initial candidates can receive road-network distance and ETA values,
after which those candidates are sorted by road ETA. Each result includes distance,
ETA, `within30`, score, trust score, trust badge, and privacy-safe worker data.

### Job state machine

```text
open -> negotiating -> accepted -> in_progress -> completed
  \-> cancelled
```

Offers are valid only for open/negotiating jobs. Starting requires `accepted`;
completion requires `in_progress`; completed jobs cannot be cancelled.

### Trust

Trust combines verification, Bayesian rating, completed jobs, account age, and
report history. Badges are:

```text
Gold >= 80, Silver >= 60, Bronze >= 40, otherwise New
```

Three or more active reports in the configured rolling window can place a worker
under review and remove that worker from matching.

## 5. Frontend architecture

The frontend is a mobile-first React single-page application. `App.jsx` defines
the route table and role guards. `MobileLayout` supplies the shared shell,
header, bottom navigation, and toast layer.

### Frontend state and API

- `authStore.js` owns the current session, role, worker availability, profile,
  verification status, Firebase listener, and logout.
- `jobStore.js` owns the current job, matches, offers, nearby jobs, lifecycle
  actions, SOS, reports, and polling.
- `toastStore.js` owns temporary notifications.
- `api/index.js` is the mock/live facade.
- `api/client.js` is the live Axios client; it normalizes the base URL, attaches
  Firebase tokens, unwraps responses, and handles one token refresh attempt.
- `api/mockStore.js` implements browser-local records and simulated latency.
- `api/mockData.js` supplies seeded worker data.

### Frontend route map

```text
/login                         Authentication
/                               Customer home
/customer/create-job            Create a request
/customer/match/:jobId          Matched workers and offers
/customer/status/:jobId         Negotiation and job tracking
/customer/review/:jobId         Review submission
/worker                         Worker job feed
/worker/job/:jobId              Worker offer and lifecycle actions
/worker/earnings                Earnings and trust
/profile                        Shared profile
/admin                          Verification queue
```

Leaflet powers location selection and route display. Route maps poll the API and
can render a straight-line fallback when road routing is unavailable.

## 6. Deployment and environments

The backend runs on Python 3.11 with Uvicorn and can be deployed through Render,
the `Procfile`, or the `Dockerfile`. `render.yaml` defines a Render web service,
health check, build/start commands, and environment variables.

The frontend is built with Vite and is intended for Vercel. `frontend/vercel.json`
rewrites unknown paths to `index.html`, which is required for client-side routes.
The frontend can point at the backend using `VITE_API_BASE_URL` and can opt into
live mode with `VITE_USE_MOCK=false`.

The default configuration favors reproducible demo/test operation:

- mock database enabled;
- automatic seed data enabled;
- local frontend origins allowed in development;
- Vercel preview origins supported through a configured regex.

For production, provide Firebase credentials, explicit CORS origins, and a real
authentication setup. The current payment model is negotiated/direct cash; no
payment processor or escrow is implemented.

## 7. File-by-file inventory

This section describes every tracked file in the repository.

### Root files

| File | Purpose |
|---|---|
| `.env.example` | Backend environment-variable template. |
| `.gitignore` | Excludes local secrets, caches, virtual environments, and generated files. |
| `.python-version` | Pins the intended Python runtime for hosting tools. |
| `README.md` | Product overview, architecture summary, API examples, formulas, and deployment instructions. |
| `DEMO.md` | Hackathon demo script, fallback instructions, limitations, and narration. |
| `ARCHITECTURE.md` | This detailed architecture and file-purpose guide. |
| `Dockerfile` | Builds a Python 3.11 container and starts Uvicorn. |
| `Procfile` | Defines the Render-style web process. |
| `render.yaml` | Render infrastructure-as-code service definition. |
| `.github/workflows/backend-ci.yml` | GitHub Actions workflow that installs Python dependencies, runs Ruff, and executes Pytest on backend changes. |
| `requirements.txt` | Runtime Python dependencies. |
| `requirements-dev.txt` | Runtime dependencies plus Ruff for development checks. |
| `runtime.txt` | Additional hosting runtime declaration. |
| `pytest.ini` | Pytest discovery, Python path, and warning configuration. |
| `main.py` | FastAPI application composition and lifecycle. |
| `seed.py` | Demo dataset creation and idempotent startup seeding. |
| `smoke_test.sh` | Shell-level smoke checks for a running deployment. |

### Backend core

| File | Purpose |
|---|---|
| `core/auth.py` | Bearer-token parsing, development identity handling, Firebase verification, and RBAC. |
| `core/config.py` | Typed environment settings and CORS/environment normalization. |
| `core/database.py` | Firestore/mock database adapter, CRUD, bulk operations, soft deletes, and transactions. |
| `core/rate_limit.py` | Thread-safe per-IP token-bucket middleware and test reset helper. |

### Models

| File | Purpose |
|---|---|
| `models/__init__.py` | Re-exports Pydantic models for convenient imports. |
| `models/user.py` | User location, creation, and response schemas. |
| `models/worker.py` | Worker profiles, matching output, verification, and admin queue schemas. |
| `models/job.py` | Job location, job creation/response, categories, and job validation. |
| `models/offer.py` | Offer creation, counter-offer, and offer response schemas. |
| `models/review.py` | Review request/response validation. |
| `models/report.py` | Abuse report request/response validation. |
| `models/sos.py` | SOS location, request, and response schemas. |

### HTTP routers

| File | Purpose |
|---|---|
| `routers/__init__.py` | Router package exports. |
| `routers/jobs.py` | Customer registration, job creation/read, nearby feed, start, complete, and cancel endpoints. |
| `routers/workers.py` | Worker matching, registration, profile/feed, availability, and verification endpoints. |
| `routers/offers.py` | Offer listing, creation, counter, accept, and reject endpoints. |
| `routers/reviews.py` | Completed-job review endpoint. |
| `routers/reports.py` | Abuse/safety report endpoint. |
| `routers/sos.py` | Emergency SOS endpoint. |
| `routers/admin.py` | Admin verification queue and approval endpoints. |
| `routers/route.py` | Route and polyline endpoint backed by road routing. |

### Services

| File | Purpose |
|---|---|
| `services/__init__.py` | Public service-function exports. |
| `services/distance.py` | Geographic distance and ETA primitives. |
| `services/h3_index.py` | H3 cell conversion and nearby-worker pre-filtering. |
| `services/matching.py` | Verified-worker filtering, scoring, trust enrichment, and road-ETA re-ranking. |
| `services/routing.py` | Cached OSM graph loading and Dijkstra route/ETA calculation. |
| `services/job_service.py` | Job creation, privacy-aware reads, nearby jobs, and lifecycle transitions. |
| `services/offer_service.py` | Negotiation rules and atomic offer acceptance. |
| `services/review_service.py` | Review persistence and worker rating updates. |
| `services/report_service.py` | Report creation and moderation integration. |
| `services/sos_service.py` | SOS alert persistence. |
| `services/trust.py` | Small public facade over the trust engine. |
| `services/trust_engine.py` | Bayesian rating, account age, trust score/badges, and abuse thresholds. |
| `services/verification_service.py` | Masked document submission and admin approval. |
| `services/worker_privacy.py` | Public/owner/admin worker serialization and address obfuscation. |

### Data and assets

| File | Purpose |
|---|---|
| `data/mira_bhayandar.graphml` | Cached OpenStreetMap road graph used for local Dijkstra routing. |
| `demo/screenshots/smoke_home.png` | Captured demo/smoke-test frontend screenshot. |

### Scripts

| File | Purpose |
|---|---|
| `scripts/build_graph.py` | Downloads/builds the cached Mira-Bhayandar road graph. |
| `scripts/seed_db.py` | Command-line database seeding utility with cleanup/verification options. |
| `scripts/local_test_suite.py` | Runs backend checks against the local FastAPI application. |
| `scripts/local_integration_test.py` | Exercises a complete local API integration flow. |
| `scripts/e2e_deployed.py` | Runs the deployed 21-step-style health, CORS, lifecycle, verification, and optional browser checks. |
| `scripts/verify_live_flow.py` | Verifies live worker matching and booking behavior. |
| `scripts/verify_verification_security.py` | Verifies worker registration and masked/admin verification behavior. |
| `scripts/test_spa_fallback.py` | Checks that frontend deep links are served by the SPA fallback. |

### Tests

| File | Coverage |
|---|---|
| `tests/conftest.py` | Shared isolated database, client, auth, and rate-limit fixtures. |
| `tests/test_auth_roles.py` | Authentication failures and role permissions. |
| `tests/test_database.py` | CRUD, timestamps, soft deletion, and database behavior. |
| `tests/test_deploy_and_gaps.py` | Deployment-sensitive behavior and integration gaps. |
| `tests/test_e2e_flow.py` | Complete customer-to-review booking journey. |
| `tests/test_h3.py` | H3 nearby-cell and filtering behavior. |
| `tests/test_health_cors.py` | Health routes and CORS policy. |
| `tests/test_input_hardening.py` | Category and input validation. |
| `tests/test_lifecycle.py` | Job state-machine transition rules. |
| `tests/test_matching.py` | Distance, ETA, and matching calculations. |
| `tests/test_offers.py` | Negotiation, counter, accept, and reject behavior. |
| `tests/test_rate_limit.py` | Rate-limit headers, exclusions, and 429 behavior. |
| `tests/test_registration_protection.py` | Authenticated customer/worker registration protection. |
| `tests/test_reviews_safety.py` | Review safety and rolling rating updates. |
| `tests/test_routing.py` | Road graph loading, route calculation, and fallbacks. |
| `tests/test_transactions_and_batching.py` | Transaction rollback and N+1/bulk-read protections. |
| `tests/test_trust_engine.py` | Bayesian rating, age weighting, badges, and abuse thresholds. |
| `tests/test_trust_verification.py` | Verification request, admin approval, and matching eligibility. |
| `tests/test_validation.py` | Pydantic/API validation error behavior. |
| `tests/test_worker_privacy.py` | Public versus private worker data masking. |

### Frontend configuration

| File | Purpose |
|---|---|
| `frontend/.env.example` | Local frontend environment template, including mock/live switches. |
| `frontend/.env.production.example` | Production Vercel/Render environment template. |
| `frontend/.gitignore` | Frontend-specific generated-file exclusions. |
| `frontend/.oxlintrc.json` | Oxlint configuration. |
| `frontend/README.md` | Frontend feature summary and quickstart. |
| `frontend/index.html` | Browser HTML shell, metadata, fonts, Leaflet CSS, and root element. |
| `frontend/package.json` | Frontend scripts and dependency declarations. |
| `frontend/package-lock.json` | Locked npm dependency graph. |
| `frontend/postcss.config.js` | PostCSS configuration for Tailwind and Autoprefixer. |
| `frontend/tailwind.config.js` | Tailwind content paths, colors, fonts, breakpoints, and touch sizing. |
| `frontend/vite.config.js` | Vite React plugin, dev port, and backend API proxy. |
| `frontend/vercel.json` | Vercel output settings and SPA fallback rewrite. |

### Frontend bootstrap, data, and state

| File | Purpose |
|---|---|
| `frontend/src/main.jsx` | React StrictMode bootstrap into the `root` element. |
| `frontend/src/App.jsx` | Browser router, route table, auth initialization, and role guards. |
| `frontend/src/App.css` | Application stylesheet placeholder; most styling is Tailwind-based. |
| `frontend/src/index.css` | Tailwind layers, global styles, Leaflet sizing, animations, and utilities. |
| `frontend/src/api/client.js` | Live Axios client, URL normalization, token attachment, and auth error handling. |
| `frontend/src/api/index.js` | Single API facade that selects mock or live mode. |
| `frontend/src/api/mockData.js` | Seeded mock worker records. |
| `frontend/src/api/mockStore.js` | Browser-local mock database and business rules. |
| `frontend/src/lib/firebase.js` | Firebase app/Auth initialization and browser persistence. |
| `frontend/src/lib/storage.js` | Safe local-storage JSON wrapper. |
| `frontend/src/lib/utils.js` | Class merging, distance/ETA, formatting, and trust helpers. |
| `frontend/src/types/index.js` | Shared constants for roles, categories, jobs, verification, and demo coordinates. |
| `frontend/src/store/authStore.js` | Auth session, profile, registration, verification, availability, and logout state. |
| `frontend/src/store/jobStore.js` | Job/match/offer/lifecycle/polling/SOS/report state. |
| `frontend/src/store/toastStore.js` | Transient notification state and helpers. |

### Frontend layout and shared components

| File | Purpose |
|---|---|
| `frontend/src/components/layout/MobileLayout.jsx` | Shared mobile viewport, header, outlet, navigation, and toast composition. |
| `frontend/src/components/layout/ProtectedRoute.jsx` | Older reusable role guard retained for compatibility; the main route table uses its own guard. |
| `frontend/src/components/common/Header.jsx` | Brand, role indicator, profile menu, and logout. |
| `frontend/src/components/common/BottomNav.jsx` | Customer/worker bottom navigation. |
| `frontend/src/components/common/EmptyState.jsx` | Reusable empty-result state. |
| `frontend/src/components/common/Skeleton.jsx` | Loading placeholders, including worker cards. |
| `frontend/src/components/common/ToastContainer.jsx` | Renders toast-store notifications. |
| `frontend/src/components/common/SosButton.jsx` | SOS confirmation, dispatch, and emergency call link. |
| `frontend/src/components/common/ReportModal.jsx` | Report reason form and submission. |
| `frontend/src/components/common/TrustBadge.jsx` | Trust badge display and score explanation. |
| `frontend/src/components/map/MapPicker.jsx` | Leaflet map for selecting a job location. |
| `frontend/src/components/map/RouteMap.jsx` | Leaflet route visualization, polling, ETA, and fallback line. |
| `frontend/src/components/worker/VerificationCard.jsx` | Worker document validation, preview, submission, and status display. |

### Frontend pages

| File | Purpose |
|---|---|
| `frontend/src/pages/AuthPage.jsx` | Customer/worker Firebase OTP flow plus demo/admin entry. |
| `frontend/src/pages/ProfilePage.jsx` | Role-specific profile, sync retry, verification, and logout. |
| `frontend/src/pages/admin/AdminPage.jsx` | Admin verification queue and approval console. |
| `frontend/src/pages/customer/CustomerHome.jsx` | Customer dashboard and service-category entry point. |
| `frontend/src/pages/customer/CreateJobPage.jsx` | Customer job, budget, contact, schedule, and location form. |
| `frontend/src/pages/customer/MatchedWorkersPage.jsx` | Worker cards, trust data, listed rates, and custom offers. |
| `frontend/src/pages/customer/JobStatusPage.jsx` | Negotiation, job tracker, polling, route, report, SOS, and review transition. |
| `frontend/src/pages/customer/ReviewPage.jsx` | Star rating, comments, and compliment submission. |
| `frontend/src/pages/worker/WorkerDashboard.jsx` | Availability and nearby-job feed. |
| `frontend/src/pages/worker/WorkerJobDetailsPage.jsx` | Worker quote, counter, accept, route, start, complete, and safety actions. |
| `frontend/src/pages/worker/WorkerEarningsPage.jsx` | Estimated cash earnings, trust breakdown, and completed jobs. |

### Frontend static assets

| File | Purpose |
|---|---|
| `frontend/public/favicon.svg` | Browser favicon. |
| `frontend/public/icons.svg` | Public SVG icon collection. |
| `frontend/src/assets/hero.png` | Bundled hero image asset. |
| `frontend/src/assets/react.svg` | Default Vite/React asset retained in the bundle. |
| `frontend/src/assets/vite.svg` | Default Vite asset retained in the bundle. |

## 8. Important implementation limitations

This repository is a strong demo/prototype architecture, but several production
concerns remain intentionally simplified:

- The default mock database is in-process and is not durable across all hosting
  restarts unless a persistent backing store is configured.
- Development/demo tokens and the admin bypass are not production authentication.
- Verification image selection is a local preview; the image is not uploaded.
- Payments are negotiated/direct cash; there is no payment gateway or escrow.
- Some frontend copy promises 30-minute arrival and full verification, while those
  are implemented as eligibility/routing rules rather than guarantees.
- Route calculation is limited to the cached Mira-Bhayandar graph and has a
  fallback when coordinates cannot be snapped to that graph.
- The mock frontend and live backend do not have perfectly identical persistence
  behavior because mock records live in browser local storage.

## 9. Recommended reading order for new contributors

1. Read this file and `README.md` for the product and system boundary.
2. Read `main.py`, `core/config.py`, `core/auth.py`, and `core/database.py`.
3. Read `models/` and the matching router/service pair.
4. Follow `job_service.py` and `offer_service.py` to understand the lifecycle.
5. Read `matching.py`, `h3_index.py`, `routing.py`, and `trust_engine.py`.
6. Start the frontend at `App.jsx`, then follow `api/index.js`, the stores, and
   the customer/worker pages.
7. Use the corresponding tests as executable examples of each business rule.
