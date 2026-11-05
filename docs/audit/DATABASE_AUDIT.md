# DATABASE AUDIT: Firestore Implementation & Persistence Layer

**Audit Date:** 2026-11-05  
**Service:** RepairBuddy Backend  
**Database Driver:** Google Cloud Firestore Python SDK (`firebase-admin` / `google-cloud-firestore`)  
**Abstraction Layer:** `core/database.py` (`FirestoreDB`)

---

## 1. Database Architecture & Mode Selection

The RepairBuddy persistence layer is managed through a singleton instance of `FirestoreDB` defined in `core/database.py`. The database operates in two primary modes:

```mermaid
flowchart TD
    AppStartup[Application Startup / Lifespan] --> CheckConfig{Check Configuration}
    CheckConfig -->|settings.USE_MOCK_FIREBASE == True AND ENV == development| InMemMode[In-Memory Mock Storage]
    CheckConfig -->|settings.USE_MOCK_FIREBASE == False OR ENV in production, staging| RemoteFSMode[Google Cloud Firestore]

    subgraph Mock_Store[In-Memory Thread-Safe Replica]
        InMemMode --> MemDict["_mem_store: Dict[str, Dict[str, Any]]"]
        InMemMode --> MemLock["_lock: threading.RLock()"]
        InMemMode --> LocalDisk["Optional local data/store.json sync"]
    end

    subgraph Production_Firestore[Cloud Firestore Engine]
        RemoteFSMode --> InitApp[firebase_admin.initialize_app]
        InitApp --> CredSource{Credential Resolution}
        CredSource -->|FIREBASE_CREDENTIALS_JSON| JSONCreds[Certificate dict from ENV]
        CredSource -->|FIREBASE_CREDENTIALS_PATH| FileCreds[Certificate from File Path]
        CredSource -->|FIRESTORE_PROJECT_ID| ADC[Application Default Credentials]
        JSONCreds --> FSClient[firestore.client()]
        FileCreds --> FSClient
        ADC --> FSClient
    end
```

### Mode Selection Rules:
1. **Production Gating:** If `ENV in ["production", "staging"]`, `FirestoreDB.connect()` requires a functional Firestore client. If credentials fail or `firebase-admin` is absent, it immediately raises a fatal `RuntimeError("CRITICAL: Failed to connect to production Firestore database.")`.
2. **Development Fallback:** In local development or automated testing, if `USE_MOCK_FIREBASE=True` or credentials are not supplied, the adapter falls back safely to an in-memory dictionary.
3. **Observed Live Production Status:** Live query to `https://repair-buddy.onrender.com/health` returned:
   ```json
   {"status":"healthy","service":"Repair Buddy API","mock_mode":false,"transit_speed_kmh":25.0}
   ```
   **Verified:** The active Render production instance is successfully connected to Cloud Firestore (`mock_mode: false`).

---

## 2. Collections & Schema Schema Definition

The database schemas across both in-memory and Cloud Firestore manage seven primary collections:

| Collection Name | Document ID Pattern | Primary Fields | Key Relationships |
|---|---|---|---|
| `users` | `cust_<id>` or Firebase UID | `uid`, `role`, `name`, `phone`, `location`, `language` | 1-to-many with `jobs` (as customer) |
| `workers` | `worker_<id>` or Firebase UID | `uid`, `name`, `phone`, `skills`, `rating`, `jobsDone`, `verified`, `location`, `rates`, `isAvailableNow`, `accountStatus` | 1-to-many with `offers`, `reviews`, `reports` |
| `jobs` | `job_<uuid>` | `id`, `customerId`, `category`, `description`, `budget`, `status`, `location`, `acceptedWorkerId` | Belongs to `users`, references `workers` |
| `offers` | `off_<uuid>` | `id`, `jobId`, `workerId`, `customerId`, `proposedPrice`, `by`, `status`, `history` | Belongs to `jobs`, references `workers` & `users` |
| `reviews` | `rev_<uuid>` | `id`, `jobId`, `workerId`, `customerId`, `rating`, `comment`, `createdAt` | References `jobs`, `workers`, `users` |
| `reports` | `rep_<uuid>` | `id`, `workerId`, `reporterId`, `reason`, `category`, `jobId`, `status`, `createdAt` | References `workers`, `users`, `jobs` |
| `sos_alerts` | `sos_<uuid>` | `id`, `jobId`, `userId`, `location`, `reason`, `createdAt`, `status` | References `jobs`, `users` |

---

## 3. Database Lifecycle & Transaction Management

### Lifecycle Hooks:
* `connect()`: Invoked during FastAPI startup inside `lifespan(app)`. Validates connection readiness and runs optional auto-seeding if enabled.
* `disconnect()`: Invoked during FastAPI shutdown. Calls `.close()` on the Firestore client and resets connection references.

### Transaction Semantics (`TransactionContext`):
The codebase implements atomic transactions via `db.run_transaction(callback)`.
* In Cloud Firestore: Uses `firestore_client.transaction()` to acquire server-side optimistic concurrency locks and execute atomic read-modify-write cycles.
* In Mock DB: Uses a re-entrant mutex lock (`threading.RLock()`) that buffers operations and applies them atomically upon callback success, or rolls back changes if an exception is raised.

#### Critical Operations Executed in Atomic Transactions:
1. **Offer Acceptance (`accept_offer` in `services/offer_service.py`):**
   - Reads target offer and target job atomically.
   - Updates target offer to `accepted`.
   - Transitions job state to `assigned` and sets `acceptedWorkerId`.
   - Reads all other pending offers on the job and transitions them to `rejected`.
2. **Job Completion (`complete_job` in `services/job_service.py`):**
   - Transitions job status from `in_progress` to `completed`.
   - Atomically increments worker's `jobsDone` counter and triggers trust score recomputation.
3. **Job Cancellation (`cancel_job` in `services/job_service.py`):**
   - Validates job state (`open` or `assigned`), updates status to `cancelled`, and records cancellation reason.
4. **Review Submission (`submit_review` in `services/review_service.py`):**
   - Inserts review record.
   - Atomically recalculates worker average rating, increments review count, and re-runs the Bayesian rating formula.

---

## 4. Query Optimization & N+1 Audit

### Findings:
1. **Matching Engine Optimization:** Earlier versions of `services/matching.py` iterated through eligible candidate workers and queried the `reports` collection individually for each candidate ($O(N)$ database round-trips).
   - **Resolution Implemented:** `core/database.py` was extended with `get_reports_count_in_bulk(worker_ids)` and `get_documents_in_bulk(collection, doc_ids)`.
   - In both Firestore and mock modes, active reports are aggregated in a single pass ($O(1)$ database calls relative to worker count), eliminating network latency bottlenecks during matching.
2. **Soft Deletion Support:**
   - `FirestoreDB.soft_delete_document(collection, doc_id)` sets `deleted: True`, `isDeleted: True`, and `deletedAt: <UTC ISO>` without physically purging document records, supporting audit compliance and historical recovery.

---

## 5. Identified Database Gaps & Recommendations

| Item | Observation | Risk Level | Recommendation |
|---|---|:---:|---|
| **Firestore Composite Indexes** | Advanced queries filtering across multiple fields simultaneously (e.g. `skills` array-contains + `verified` + `isAvailableNow`) require composite indexes in Firestore. | **MEDIUM** | Ensure `firestore.indexes.json` is maintained in the repository and deployed via Firebase CLI. |
| **Local Mock Persistence** | `store.json` local file persistence is disabled by default to prevent dirty test state bleeding across runs. | **LOW** | Keep `_save_to_disk=False` in test configurations, using dynamic fixtures exclusively. |
| **Connection Pool Tuning** | Firestore gRPC channel multiplexing uses default channel pools. | **INFORMATIONAL** | For high-throughput production (>1,000 req/sec), configure gRPC channel pool options on `firestore.Client`. |

