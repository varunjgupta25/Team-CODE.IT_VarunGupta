# Phase 2 API Contracts — RepairBuddy Backend

All endpoints are dual-mounted under both root (`""`) and `/api` (e.g., both `/health` and `/api/health` are valid). Bearer token authentication is required for all endpoints unless explicitly noted as public.

---

## 1. Authentication & Common Endpoints

### `GET /users/me`
- **Role**: Any authenticated user (`customer`, `worker`, `admin`)
- **Headers**: `Authorization: Bearer <token>`
- **Response `200 OK`**:
```json
{
  "uid": "cust_test_1",
  "role": "customer",
  "name": "Customer Priya",
  "phone": "+91 98201 11222",
  "location": {
    "lat": 19.2825,
    "lng": 72.8570,
    "address": "Mira Road East"
  },
  "accountStatus": "ACTIVE"
}
```

---

## 2. Customer Endpoints

### `GET /customers/{customer_id}`
- **Role**: Any authenticated user (masked for non-owners)
- **Headers**: `Authorization: Bearer <token>`
- **Response `200 OK`**:
```json
{
  "uid": "cust_test_1",
  "name": "Customer Priya",
  "role": "customer",
  "phone": "+91 98201 11222",
  "location": {
    "lat": 19.2825,
    "lng": 72.8570,
    "address": "Mira Road East"
  },
  "accountStatus": "ACTIVE"
}
```

### `PATCH /customers/{customer_id}`
- **Role**: Customer owner or Admin (`403 Forbidden` on mismatch)
- **Request Body**:
```json
{
  "name": "Priya Sharma",
  "phone": "+91 98201 99999",
  "location": {
    "lat": 19.2830,
    "lng": 72.8580,
    "address": "Poonam Sagar, Mira Road"
  }
}
```
- **Response `200 OK`**: Updated profile object.

---

## 3. Worker Endpoints

### `PATCH /workers/{worker_id}`
- **Role**: Worker owner or Admin (`403 Forbidden` on mismatch)
- **Request Body** (all fields optional):
```json
{
  "isAvailableNow": true,
  "skills": ["electrician", "appliance_repair"],
  "rates": {
    "electrician": 450.0,
    "appliance_repair": 500.0
  },
  "serviceRadiusKm": 8.0,
  "name": "Rajesh Sharma",
  "phone": "+91 91102 00001"
}
```
- **Response `200 OK`**:
```json
{
  "status": "success",
  "workerId": "worker_elec_1",
  "isAvailableNow": true,
  "serviceRadiusKm": 8.0
}
```

### `GET /workers/{worker_id}/earnings`
- **Role**: Worker owner or Admin (`403 Forbidden` on mismatch)
- **Response `200 OK`**:
```json
{
  "workerId": "worker_elec_1",
  "totalEarnings": 1250.0,
  "completedJobsCount": 3,
  "currency": "INR",
  "payoutType": "direct_cash",
  "platformCommission": 0.0,
  "jobs": [
    {
      "jobId": "job_101",
      "category": "electrician",
      "amount": 450.0,
      "completedAt": "2026-11-04T12:00:00Z"
    }
  ]
}
```

---

## 4. Admin Endpoints

### `GET /admin/stats` / `GET /admin/dashboard`
- **Role**: Admin only (`403 Forbidden` for non-admin)
- **Response `200 OK`**:
```json
{
  "totalCustomers": 5,
  "totalWorkers": 25,
  "verifiedWorkers": 21,
  "pendingVerifications": 4,
  "activeJobs": 3,
  "completedJobs": 2,
  "totalJobs": 5,
  "reports": {
    "total": 4,
    "pending": 2,
    "resolved": 1,
    "dismissed": 1
  }
}
```

### `GET /admin/reports`
- **Query Parameters**: `status` (optional: `pending`, `resolved`, `dismissed`)
- **Role**: Admin only
- **Response `200 OK`**: List of safety reports.

### `GET /admin/reports/{report_id}`
- **Role**: Admin only
- **Response `200 OK`**:
```json
{
  "id": "rep_abc123",
  "workerId": "worker_elec_1",
  "reporterId": "cust_test_1",
  "reason": "Did not show up on time",
  "category": "no_show",
  "jobId": "job_test_open",
  "status": "pending",
  "createdAt": "2026-11-05T10:00:00Z"
}
```

### `POST /admin/reports/{report_id}/resolve`
- **Role**: Admin only
- **Request Body**:
```json
{
  "action": "Issued formal warning to worker"
}
```
- **Response `200 OK`**:
```json
{
  "id": "rep_abc123",
  "status": "resolved",
  "actionTaken": "Issued formal warning to worker",
  "resolvedAt": "2026-11-06T00:00:00Z"
}
```

### `POST /admin/reports/{report_id}/dismiss`
- **Role**: Admin only
- **Response `200 OK`**:
```json
{
  "id": "rep_abc123",
  "status": "dismissed",
  "dismissedAt": "2026-11-06T00:00:00Z"
}
```

### `GET /admin/users`
- **Query Parameters**: `role` (optional: `customer`, `worker`, `admin`)
- **Role**: Admin only
- **Response `200 OK`**: List of user records.

### `POST /admin/users/{uid}/suspend`
- **Role**: Admin only
- **Request Body**:
```json
{
  "reason": "Repeated customer safety complaints"
}
```
- **Response `200 OK`**:
```json
{
  "status": "success",
  "uid": "worker_elec_bad",
  "accountStatus": "SUSPENDED",
  "message": "User 'worker_elec_bad' has been suspended"
}
```

### `POST /admin/users/{uid}/reactivate`
- **Role**: Admin only
- **Response `200 OK`**:
```json
{
  "status": "success",
  "uid": "worker_elec_bad",
  "accountStatus": "ACTIVE",
  "message": "User 'worker_elec_bad' has been reactivated"
}
```
