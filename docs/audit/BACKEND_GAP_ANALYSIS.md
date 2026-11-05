# BACKEND GAP ANALYSIS & ARCHITECTURAL ROADMAP

**Audit Date:** 2026-11-05  
**Service:** RepairBuddy Backend  
**Audit Purpose:** Gap identification, priority classification, and Phase 1 technical recommendations.

---

## 1. Prioritized Module Gap Matrix

| Module | Current Status | Identified Gap | Priority | Recommendation |
|---|---|---|:---:|---|
| **`core/database.py`** | Operational with Firestore & Mock | Cloud Firestore composite index configuration file (`firestore.indexes.json`) is not explicitly committed in repository source control. | **HIGH** | Generate and check in `firestore.indexes.json` covering multi-field queries (e.g. `skills` + `verified` + `isAvailableNow`). |
| **`render.yaml`** | Operational (Production running with `mock_mode: false`) | Repository default in `render.yaml` specifies `USE_MOCK_FIREBASE: "true"`, relying on Render dashboard secret overrides to enable real Firestore. | **MEDIUM** | Provide sample documentation or secret manager instructions detailing how `FIREBASE_CREDENTIALS_JSON` should be provisioned for new environment branches. |
| **`services/routing.py`** | Operational (Dijkstra over OSM NetworkX Graph) | Graph file (`mira_road_drive.graphml`) is loaded from disk into memory on startup; if route graphs expand beyond Mira Road, disk I/O and deserialization time will scale linearly. | **MEDIUM** | Implement binary serialization (e.g. pickle or graph cache) or lazy per-cluster partition loading when expanding geographic coverage beyond Mira Road. |
| **`core/rate_limit.py`** | Operational (Pure Python Token Bucket) | Token bucket stores state in-memory per single OS process; does not synchronize across multi-worker clusters (e.g. multi-process Gunicorn/Uvicorn). | **MEDIUM** | If scaling beyond single-worker Render instances, introduce an optional Redis-backed backend or sticky routing. |
| **`services/trust_engine.py`** | Operational (Bayesian Rating & Abuse Auto-Flagging) | Global mean rating baseline $C$ (default 4.5) and minimum review weight $m$ (default 5.0) are hard-coded module constants. | **LOW** | Expose Bayesian calibration hyperparameters in `core/config.py` (`BAYESIAN_GLOBAL_MEAN`, `BAYESIAN_MIN_WEIGHT`) for dynamic platform tuning. |
| **`services/verification_service.py`** | Operational (Aadhaar Masking & Admin Queue) | Document verification operates via manual administrator approval; no automated third-party KYC or DigiLocker integration. | **LOW** | In Phase 2, explore sandbox webhook integrations for automated government ID validation (e.g. Surepass/Cashfree KYC API). |
| **`routers/sos.py`** | Operational (Emergency SOS Endpoint) | Records alert in `sos_alerts` collection and logs emergency event, but lacks outward push notification / SMS dispatch integration. | **LOW** | Integrate Twilio or Firebase Cloud Messaging (FCM) to trigger instant push notifications to emergency contacts or safety monitors upon SOS. |

---

## 2. Priority Classification Guidelines

* **CRITICAL**: Immediate risk of security compromise, data loss, or total service disruption. (0 Critical gaps identified).
* **HIGH**: Operational resilience or scalability gap that must be addressed prior to multi-region or high-traffic production launch.
* **MEDIUM**: Architecture improvements that simplify deployments, enhance distributed consistency, or optimize startup times.
* **LOW**: Functional feature enhancements, automated third-party integrations, or parameter flexibility improvements planned for Phase 2.

---

## 3. Recommended Phase 1 Technical Workstream

1. **Firestore Index Manifest:** Check in `firestore.indexes.json` to guarantee all compound queries used in matching and feeds have pre-built indexes deployed.
2. **Dynamic Bayesian Hyperparameters:** Promote Bayesian engine constants (`DEFAULT_GLOBAL_MEAN_RATING`, `DEFAULT_MIN_REVIEWS_WEIGHT`, `AUTO_FLAG_THRESHOLD`) into `core/config.py` settings.
3. **Graph Deserialization Optimization:** Add a binary caching layer (`.pkl`) for `mira_road_drive.graphml` to reduce container cold-start time from ~2.5s to <0.3s.
4. **Outward Alert Dispatch (Webhooks):** Connect the SOS trigger to an asynchronous webhook dispatcher for outward notification delivery.

