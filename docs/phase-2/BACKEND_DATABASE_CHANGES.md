# Backend Database Changes — Phase 2

## 1. Overview
No secondary databases or external storage mechanisms were added. All data models continue to reside within Google Cloud Firestore and its mock in-memory layer (`core/database.py`).

---

## 2. Updated Collections & Schema Additions

### `users` Collection
- Added `accountStatus` (`"ACTIVE" | "SUSPENDED"`). Defaults to `"ACTIVE"`.
- Added `suspendedAt` (`ISO 8601 UTC timestamp`, nullable).
- Added `suspensionReason` (`str`, nullable).

### `workers` Collection
- Extended `accountStatus` (`"ACTIVE" | "UNDER_REVIEW" | "SUSPENDED"`).
- Extended `isFlagged` & `flagged` (`bool`).
- Supported dynamic profile update fields: `skills` (`list[str]`), `rates` (`dict[str, float]`), `serviceRadiusKm` (`float`), `name` (`str`), `phone` (`str`).

### `reports` Collection
- Added `status` (`"pending" | "resolved" | "dismissed"`). Defaults to `"pending"`.
- Added `resolvedAt` (`ISO 8601 UTC timestamp`, nullable).
- Added `actionTaken` (`str`, nullable).
- Added `dismissedAt` (`ISO 8601 UTC timestamp`, nullable).

### `jobs` Collection
- Preserved transactional fields: `acceptedWorkerId`, `finalPrice`, `startedAt`, `completedAt`, `cancelledAt`.

---

## 3. Firestore Compound Indexes

The compound index configuration established in Phase 1 (`firestore.indexes.json`) covers the query patterns used by matching, reports, and job feeds:
- `workers` collection: `(skills ASC, verified ASC, isAvailableNow ASC)`
- `jobs` collection: `(status ASC, category ASC, createdAt DESC)`
- `reports` collection: `(workerId ASC, status ASC, createdAt DESC)`
- `offers` collection: `(jobId ASC, status ASC, createdAt DESC)`
