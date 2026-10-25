# RepairBuddy

> **"Blinkit for Blue-Collar Workers"** — Hyperlocal On-Demand Blue-Collar Services Platform  
> **Author & Developer:** Varun jayshankar gupta ([@varunjgupta25](https://github.com/varunjgupta25))  
> Built for VIT National Level Hackathon (Social Impact Domain)  
> Stack: **FastAPI (Backend) + React & Vite & Tailwind CSS (Frontend)**

---

## 1. Project Overview & Architecture

RepairBuddy connects urban households to nearby verified skilled workers (plumbers, electricians, painters, cleaners, maids, cooks) in under 60 seconds with arrival ETAs under 30 minutes.

### Key Differentiators
- **Worker-Set Pricing & Turn-Based Negotiation:** Workers set their own rates; customers negotiate directly through alternating offers and counters (zero corporate middleman commission).
- **Hyperlocal Haversine Matching:** Workers are matched based on distance ($40\%$), rating ($30\%$), price proximity ($20\%$), and completed jobs ($10\%$) with real-time ETA ($25\text{ km/h}$) and `within30` flag.
- **Trust & Safety:** Unverified workers are strictly hidden from matching. 0–100 Trust Score maps into Bronze, Silver, and Gold badges. Instant SOS emergency recording with location.

---

## 2. File Tree

```
Backend/
├── core/
│   ├── __init__.py
│   ├── auth.py              # Firebase ID Token verification & Dev token resolution
│   ├── config.py            # Pydantic Settings (.env, CORS, transit speed)
│   └── database.py          # Unified Firestore client with local persistent store fallback
├── data/
│   └── store.json           # Local JSON-backed Firestore data store
├── models/
│   ├── __init__.py
│   ├── job.py               # JobLocation, JobCreate, JobResponse, NearbyJobResponse
│   ├── offer.py             # OfferCreate, OfferCounter, OfferResponse
│   ├── review.py            # ReviewCreate, ReviewResponse
│   ├── sos.py               # SOSLocation, SOSCreate, SOSResponse
│   ├── user.py              # UserBase, UserCreate, UserResponse
│   └── worker.py            # WorkerBase, WorkerResponse, MatchedWorkerResponse
├── routers/
│   ├── __init__.py
│   ├── jobs.py              # POST /jobs, GET /jobs/{id}, GET /jobs/nearby, /start, /complete
│   ├── offers.py            # POST /offers, /counter, /accept, /reject
│   ├── reviews.py           # POST /reviews
│   ├── sos.py               # POST /sos
│   └── workers.py           # GET /workers/match?jobId=
├── services/
│   ├── __init__.py
│   ├── distance.py          # Haversine distance, ETA (distance / 25 km/h), within30 flag
│   ├── job_service.py       # Job state machine, address privacy masking, worker job feed
│   ├── matching.py          # Weighted ranking score engine (40-30-20-10) & filtering
│   ├── offer_service.py     # Turn enforcement, offer negotiation, auto-reject peers on accept
│   ├── review_service.py    # Rolling average rating calculation on completion
│   ├── sos_service.py       # Emergency SOS alert dispatcher
│   └── trust.py             # 0-100 Trust Score and Bronze/Silver/Gold tier badge logic
├── .env                     # Local environment settings
├── .env.example             # Example environment file
├── main.py                  # FastAPI application entrypoint with CORS & error handlers
├── requirements.txt         # Project dependencies
├── seed.py                  # Seeds 25 Mira Road workers, 5 customers, 5 jobs
├── test_suite.py            # Full test suite covering all success criteria
└── README.md                # Documentation and cURL run commands
```

---

## 3. Quickstart & Installation

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Seed the Database
Seeds 25 realistic workers across 6 categories around Mira Road, Mumbai (21 verified, 4 unverified), 5 customers, and 5 jobs:
```bash
python seed.py
```

### Step 3: Run the Server
```bash
uvicorn main:app --reload --port 8000
```
- API Base URL: `http://localhost:8000`
- Interactive Swagger Docs: `http://localhost:8000/docs`
- Redoc Documentation: `http://localhost:8000/redoc`

---

## 4. Run Automated Test Suite
To verify all PRD success criteria (matching filters, turn-based counters, auto-rejection, state validation, rolling rating, SOS):
```bash
python test_suite.py
```

---

## 5. Complete cURL Commands for Every Endpoint

> Note: All endpoints accept `Authorization: Bearer <token>`. In local development/demo mode, use user UIDs directly (e.g. `cust_priya`, `worker_elec_1`, `worker_plumber_1`).

### 1. Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

---

### 2. Match Workers for a Job (`GET /workers/match?jobId=...`)
Returns verified, available workers matching the skill within their service radius, ranked by score (distance 40%, rating 30%, price vs budget 20%, jobsDone 10%), with `distanceKm`, `etaMinutes`, `within30`, and trust badges.
```bash
curl -X GET "http://localhost:8000/workers/match?jobId=job_seed_plumber_open" \
     -H "Authorization: Bearer cust_priya"
```

---

### 3. Create a Job (`POST /jobs`)
```bash
curl -X POST "http://localhost:8000/jobs" \
     -H "Authorization: Bearer cust_priya" \
     -H "Content-Type: application/json" \
     -d '{
       "category": "plumber",
       "description": "Bathroom tap leakage and low water pressure",
       "location": {
         "lat": 19.2825,
         "lng": 72.8570,
         "address": "Flat 402, Beverly Park, Mira Road East, Mumbai"
       },
       "budget": 350.0,
       "mode": "on-demand"
     }'
```

---

### 4. Get Job Details (`GET /jobs/{id}`)
Hides exact address from unassigned workers; reveals upon booking confirmation.
```bash
curl -X GET "http://localhost:8000/jobs/job_seed_plumber_open" \
     -H "Authorization: Bearer cust_priya"
```

---

### 5. Worker Nearby Job Feed (`GET /jobs/nearby`)
Returns open/negotiating jobs matching worker skills within their service radius, sorted by distance.
```bash
curl -X GET "http://localhost:8000/jobs/nearby" \
     -H "Authorization: Bearer worker_plumber_1"
```

---

### 6. Make an Offer (`POST /offers`)
Can be created by customer or worker. Sets job status to `negotiating`.
```bash
curl -X POST "http://localhost:8000/offers" \
     -H "Authorization: Bearer cust_priya" \
     -H "Content-Type: application/json" \
     -d '{
       "jobId": "job_seed_plumber_open",
       "workerId": "worker_plumber_1",
       "price": 300.0,
       "by": "customer"
     }'
```

---

### 7. Counter an Offer (`POST /offers/{id}/counter`)
Enforces alternating turns: only the other party can counter.
```bash
curl -X POST "http://localhost:8000/offers/offer_seed_demo_1/counter" \
     -H "Authorization: Bearer cust_amit" \
     -H "Content-Type: application/json" \
     -d '{
       "price": 480.0
     }'
```

---

### 8. Accept an Offer (`POST /offers/{id}/accept`)
Locks `acceptedWorkerId`, `finalPrice`, sets job `status = accepted`, and auto-rejects all other pending offers on this job.
```bash
curl -X POST "http://localhost:8000/offers/offer_seed_demo_1/accept" \
     -H "Authorization: Bearer cust_amit"
```

---

### 9. Reject an Offer (`POST /offers/{id}/reject`)
```bash
curl -X POST "http://localhost:8000/offers/offer_seed_demo_1/reject" \
     -H "Authorization: Bearer cust_amit"
```

---

### 10. Worker Starts Job (`POST /jobs/{id}/start`)
Validates that job status is `accepted` and requester is the assigned worker. Transitions status to `in_progress`.
```bash
curl -X POST "http://localhost:8000/jobs/job_seed_cleaner_accepted/start" \
     -H "Authorization: Bearer worker_cleaner_1"
```

---

### 11. Worker Completes Job (`POST /jobs/{id}/complete`)
Validates that job status is `in_progress`. Transitions status to `completed` and increments worker's `jobsDone` counter.
```bash
curl -X POST "http://localhost:8000/jobs/job_seed_painter_progress/complete" \
     -H "Authorization: Bearer worker_painter_1"
```

---

### 12. Submit Rating and Review (`POST /reviews`)
Requires job status to be `completed`. Automatically updates the worker's rolling average rating.
```bash
curl -X POST "http://localhost:8000/reviews" \
     -H "Authorization: Bearer cust_ananya" \
     -H "Content-Type: application/json" \
     -d '{
       "jobId": "job_seed_cook_completed",
       "workerId": "worker_cook_1",
       "rating": 5.0,
       "comment": "Delicious food cooked quickly. Very polite and clean!"
     }'
```

---

### 13. Emergency SOS Alert (`POST /sos`)
Records user coordinates and active job ID into `sos_alerts`.
```bash
curl -X POST "http://localhost:8000/sos" \
     -H "Authorization: Bearer cust_priya" \
     -H "Content-Type: application/json" \
     -d '{
       "jobId": "job_seed_plumber_open",
       "location": {
         "lat": 19.2825,
         "lng": 72.8570
       }
     }'
```

---

## 6. Mathematical Formulas Implemented

1. **Haversine Distance ($d$ in km):**
   $$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
   $$d = 2 \cdot R \cdot \arctan2(\sqrt{a}, \sqrt{1-a}), \quad R = 6371\text{ km}$$

2. **ETA (Minutes):**
   $$\text{ETA} = \left(\frac{d}{25\text{ km/h}}\right) \times 60, \quad \text{within30} = (\text{ETA} \le 30.0)$$

3. **Matching Ranking Score (0–100):**
   $$\text{Score} = 0.40 \cdot S_{\text{dist}} + 0.30 \cdot S_{\text{rating}} + 0.20 \cdot S_{\text{price}} + 0.10 \cdot S_{\text{jobs}}$$

4. **Trust Score (0–100) & Badging:**
   $$\text{Trust} = \text{Verified}(30) + \text{RatingScaled}(30) + \text{JobsCapped}(20) + \text{Age}(10) + \text{CleanRecord}(10) - \text{Penalty}$$
   - **Gold:** $\ge 80$
   - **Silver:** $\ge 60$
   - **Bronze:** $\ge 40$

---

## 7. Deploy to Render

Repair Buddy includes automated deployment configuration for [Render](https://render.com) (`render.yaml` Blueprint and `Procfile`).

### Exact Deployment Steps

1. **Push your code to GitHub**:
   Ensure `data/mira_bhayandar.graphml`, `.python-version`, and `render.yaml` are committed.

2. **Create New Blueprint / Web Service on Render**:
   - Navigate to [Render Dashboard](https://dashboard.render.com).
   - Click **New +** → **Blueprint** (or **Web Service**).
   - Select your repository: `varunjgupta25/Team-CODE.IT_VarunGupta`.
   - Render will automatically detect `render.yaml`. If setting up manually as a Web Service:
     - **Runtime:** `Python` (pinned via `.python-version` to `3.11.9`)
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
     - **Health Check Path:** `/health`

3. **Configure Environment Variables**:
   In Render's **Environment** tab, configure the following variables:

   | Variable | Value / Example | Description |
   |---|---|---|
   | `ENV` | `production` | Environment mode |
   | `USE_MOCK_FIREBASE` | `true` | Runs in persistent mock Firestore mode (or provide `FIREBASE_CREDENTIALS_PATH` for live Firebase) |
   | `AUTO_SEED` | `true` | Idempotently seeds 25 workers, 5 customers, 5 jobs, and `admin_user` on cold boot if database is empty |
   | `CORS_ORIGINS` | `http://localhost:5173,https://repair-buddy.vercel.app` | Comma-separated list of exact allowed origins |
   | `CORS_ORIGIN_REGEX` | `https://.*\.vercel\.app` | Optional regex to permit all Vercel PR preview deployments |
   | `TRANSIT_SPEED_KMH` | `25.0` | Travel speed constant for ETA calculations |
   | `PORT` | *(Provided by Render automatically)* | Port assigned dynamically by Render |

4. **Verify Deployment**:
   - The deployment runs in ~30–45s installing wheel dependencies.
   - Render verifies the `/health` health check.
   - On startup, `auto_seed_if_empty()` populates the database and `load_graph()` preloads the Mira-Bhayandar road network (~2.41 MB, <160 MB peak RAM).

