# Job Lifecycle Test Report — Phase 3

## 1. Lifecycle State Machine Diagram

```
       [ Customer: POST /jobs ]
                  │
                  ▼
              ( open ) ◄─────────────┐ (All offers rejected)
                  │                  │
   [ Offer Made: POST /offers ]      │
                  │                  │
                  ▼                  │
           ( negotiating ) ──────────┘
                  │
  [ Offer Accepted: POST /offers/{id}/accept ]
                  │  * Locks acceptedWorkerId
                  │  * Locks finalPrice
                  ▼
             ( accepted )
                  │
    [ Worker Starts: POST /jobs/{id}/start ]
                  │  * Guarded: assigned worker only
                  ▼
            ( in_progress )
                  │
  [ Worker Completes: POST /jobs/{id}/complete ]
                  │  * Increments jobsDone
                  ▼
             ( completed )
                  │
   [ Customer: POST /reviews ]
                  ▼
             [ Terminated ]
```

---

## 2. Transition Guard Matrix & Invalid Transition Rejection

| Current State | Target Action | Expected Result | Reason |
|---|---|---|---|
| `open` | `/start` | **400 Bad Request** | Job must be `accepted` before starting. |
| `negotiating` | `/start` | **400 Bad Request** | Job must be `accepted` before starting. |
| `accepted` | `/complete`| **400 Bad Request** | Job must be `in_progress` before completion. |
| `open` | `/complete`| **400 Bad Request** | Job has not been started. |
| `completed` | `/cancel` | **400 Bad Request** | Completed jobs cannot be cancelled. |
| `in_progress`| `/cancel` | **400 Bad Request** | Active in-progress jobs cannot be cancelled. |
| `accepted` | Unassigned worker `/start` | **403 Forbidden** | Only assigned worker can start. |
| `in_progress`| Unassigned worker `/complete` | **403 Forbidden** | Only assigned worker can complete. |
| `open` | Non-owner `/cancel` | **403 Forbidden** | Only customer creator or admin can cancel. |

---

## 3. Concurrency & Competing Offers Handling

Tested in [`tests/test_phase3_integration.py::test_competing_offers_atomic_rejection`](file:///c:/Users/Kashish/OneDrive/Desktop/Backend/tests/test_phase3_integration.py):
- When Worker 1 and Worker 2 both have pending offers on `job_101`:
- Customer accepts Worker 2's offer.
- Worker 2's offer is marked `accepted`.
- `job_101` is assigned to Worker 2.
- Worker 1's offer is atomically updated to `rejected`.
- Attempting to accept Worker 1's offer afterwards fails with `400 Bad Request`.

