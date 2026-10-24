import pytest
from core.database import db


def test_missing_or_invalid_token_returns_401(client):
    """
    Endpoints requiring authentication must return 401 when:
    - Authorization header is missing.
    - Bearer token is empty.
    - Token is unknown / invalid.
    """
    # 1. Missing Authorization header
    res = client.get("/jobs/job_test_open")
    assert res.status_code == 401
    assert "missing" in res.json()["detail"].lower() or "unauthorized" in res.json()["detail"].lower()

    # 2. Empty Bearer token
    res = client.get("/jobs/job_test_open", headers={"Authorization": "Bearer "})
    assert res.status_code == 401

    # 3. Invalid/unknown token
    res = client.get("/jobs/job_test_open", headers={"Authorization": "Bearer totally_fake_token_99999"})
    assert res.status_code == 401


def test_customer_cannot_call_worker_only_endpoints(client, auth_customer_headers):
    """
    A customer cannot call worker-only endpoints:
    - GET /jobs/nearby -> 403
    - POST /jobs/{id}/start -> 403
    - POST /jobs/{id}/complete -> 403
    - POST /workers/verify -> 403
    """
    # 1. GET /jobs/nearby
    res = client.get("/jobs/nearby", headers=auth_customer_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"

    # 2. POST /jobs/{id}/start
    res = client.post("/jobs/job_test_accepted/start", headers=auth_customer_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"

    # 3. POST /jobs/{id}/complete
    res = client.post("/jobs/job_test_in_progress/complete", headers=auth_customer_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"

    # 4. POST /workers/verify
    res = client.post("/workers/verify", json={"documentType": "aadhaar"}, headers=auth_customer_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"


def test_worker_cannot_call_customer_only_endpoints(client, auth_worker_headers):
    """
    A worker cannot call customer-only endpoints:
    - POST /jobs -> 403
    - GET /workers/match -> 403
    - POST /reviews -> 403
    """
    # 1. POST /jobs
    new_job = {
        "category": "electrician",
        "description": "Short circuit in kitchen",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road East"},
        "budget": 350.0
    }
    res = client.post("/jobs", json=new_job, headers=auth_worker_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"

    # 2. GET /workers/match
    res = client.get("/workers/match?jobId=job_test_open", headers=auth_worker_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"

    # 3. POST /reviews
    review_data = {
        "jobId": "job_test_completed",
        "workerId": "worker_elec_1",
        "rating": 5.0,
        "comment": "Self review attempt by worker"
    }
    res = client.post("/reviews", json=review_data, headers=auth_worker_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"


def test_non_admin_calling_admin_approve_returns_403(client, auth_customer_headers, auth_worker_headers, auth_admin_headers):
    """
    A non-admin calling POST /admin/verifications/{uid}/approve returns 403.
    Only admin role can approve verifications.
    """
    # Seed an unverified worker
    db.set_document("workers", "worker_unverified_test", {
        "uid": "worker_unverified_test",
        "name": "Unverified Tester",
        "skills": ["electrician"],
        "rates": {"electrician": 300.0},
        "isAvailableNow": True,
        "verified": False,
        "verificationStatus": "pending",
        "rating": 4.0,
        "jobsDone": 0,
        "location": {"lat": 19.2830, "lng": 72.8575},
        "serviceRadiusKm": 5.0
    })

    # 1. Customer calls -> 403
    res = client.post("/admin/verifications/worker_unverified_test/approve", headers=auth_customer_headers)
    assert res.status_code == 403

    # 2. Worker calls -> 403
    res = client.post("/admin/verifications/worker_unverified_test/approve", headers=auth_worker_headers)
    assert res.status_code == 403

    # 3. Admin calls -> 200 (Success)
    res = client.post("/admin/verifications/worker_unverified_test/approve", headers=auth_admin_headers)
    assert res.status_code == 200
    assert res.json()["verified"] is True

    # Verify worker document was updated in database
    worker = db.get_document("workers", "worker_unverified_test")
    assert worker["verified"] is True
    assert worker["verificationStatus"] == "approved"


def test_user_cannot_read_another_users_job_offers(
    client, auth_customer_headers, auth_customer_2_headers, auth_worker_headers, auth_worker_2_headers
):
    """
    A user cannot read another user's job offers:
    - Customer A owns job_test_open.
    - Customer B tries to read offers on job_test_open -> 403.
    - Uninvolved Worker (worker_elec_2) tries to read offers on job_test_open -> 403.
    - Customer A can read offers on job_test_open -> 200.
    - Involved Worker (worker_elec_1) can read their offer -> 200.
    """
    job_id = "job_test_open"

    # Create an offer on job_test_open between cust_test_1 and worker_elec_1
    res = client.post("/offers", json={
        "jobId": job_id,
        "workerId": "worker_elec_1",
        "price": 400.0,
        "by": "customer"
    }, headers=auth_customer_headers)
    assert res.status_code == 201
    offer_id = res.json()["id"]

    # 1. Customer 2 (cust_test_2) tries to read offers for Customer 1's job -> 403
    res = client.get(f"/offers?jobId={job_id}", headers=auth_customer_2_headers)
    assert res.status_code == 403
    assert "another user's job offers" in res.json()["detail"].lower()

    # 2. Customer 2 tries to read the offer by ID -> 403
    res = client.get(f"/offers/{offer_id}", headers=auth_customer_2_headers)
    assert res.status_code == 403

    # 3. Uninvolved Worker (worker_elec_2) tries to read offers for job_test_open -> 403
    res = client.get(f"/offers?jobId={job_id}", headers=auth_worker_2_headers)
    assert res.status_code == 403

    # 4. Uninvolved Worker (worker_elec_2) tries to read the offer by ID -> 403
    res = client.get(f"/offers/{offer_id}", headers=auth_worker_2_headers)
    assert res.status_code == 403

    # 5. Customer 1 (owner) reads offers for job_test_open -> 200
    res = client.get(f"/offers?jobId={job_id}", headers=auth_customer_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1
    assert res.json()[0]["id"] == offer_id

    # 6. Involved Worker (worker_elec_1) reads offers for job_test_open -> 200
    res = client.get(f"/offers?jobId={job_id}", headers=auth_worker_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1
    assert res.json()[0]["id"] == offer_id
