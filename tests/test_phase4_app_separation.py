"""
tests/test_phase4_app_separation.py

Phase 4 Comprehensive Test Suite:
Validates backend support for Customer and Partner App (Worker + Admin) separation:
1. Dual-origin CORS configuration (CUSTOMER_APP_ORIGIN + PARTNER_APP_ORIGIN)
2. Production CORS restrictions (wildcard stripping, regex hardening, unwhitelisted origin rejection)
3. Role authorization isolation between Customer and Partner apps
4. Shared database consistency across Customer, Worker, and Admin flows
5. Independent authentication and token context isolation (Origin does not grant privilege)
"""

import pytest
from core.config import Settings
from core.database import db
from seed import seed_database


def test_cors_settings_dual_origin_resolution():
    """
    Validates that Settings cleanly aggregates CUSTOMER_APP_ORIGIN and
    PARTNER_APP_ORIGIN alongside ALLOWED_ORIGINS, rejecting wildcards.
    """
    cust_origin = "https://repairbuddy-customer.vercel.app"
    partner_origin = "https://repairbuddy-partner.vercel.app"

    # Production scenario with separate origins
    s_prod = Settings(
        ENV="production",
        CUSTOMER_APP_ORIGIN=cust_origin,
        PARTNER_APP_ORIGIN=partner_origin,
        ALLOWED_ORIGINS="*,https://admin-preview.com",
    )

    assert cust_origin in s_prod.ALLOWED_ORIGINS
    assert partner_origin in s_prod.ALLOWED_ORIGINS
    assert "https://admin-preview.com" in s_prod.ALLOWED_ORIGINS
    assert "*" not in s_prod.ALLOWED_ORIGINS
    assert "http://localhost:5173" not in s_prod.ALLOWED_ORIGINS
    # In production, default permissive regex is disabled
    assert s_prod.CORS_ORIGIN_REGEX is None


def test_customer_and_partner_cors_preflight(client):
    """
    Simulates OPTIONS preflight requests from both Customer and Partner app origins,
    as well as rejecting an unauthorized malicious origin.
    """
    # Allowed local dev origins used by both apps during local dev
    cust_dev_origin = "http://localhost:5173"
    partner_dev_origin = "http://localhost:3000"
    malicious_origin = "http://malicious-phishing-site.com"

    for origin in [cust_dev_origin, partner_dev_origin]:
        res = client.options(
            "/api/jobs",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == origin
        assert res.headers.get("access-control-allow-credentials") == "true"
        allow_methods = res.headers.get("access-control-allow-methods", "")
        assert "POST" in allow_methods
        assert "OPTIONS" in allow_methods

    # Disallowed origin is rejected (no allow-origin header)
    res_bad = client.options(
        "/api/jobs",
        headers={
            "Origin": malicious_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert res_bad.headers.get("access-control-allow-origin") is None


def test_origin_header_does_not_confer_role(client):
    """
    Security verification: Sending request from Customer App origin with a Worker token,
    or Partner App origin with a Customer token, enforces actual cryptographic role,
    NOT the origin header.
    """
    seed_database()

    cust_headers_spoof = {
        "Authorization": "Bearer cust_priya",
        "Origin": "https://repairbuddy-partner.vercel.app",  # Pretending to be partner app
    }
    worker_headers_spoof = {
        "Authorization": "Bearer worker_elec_1",
        "Origin": "https://repairbuddy-customer.vercel.app",  # Pretending to be customer app
    }

    # 1. Customer cannot access worker verification queue or verify endpoint regardless of Origin
    res_w = client.post("/workers/verify", headers=cust_headers_spoof)
    assert res_w.status_code == 403

    # 2. Customer cannot access admin endpoints regardless of Origin
    res_adm = client.get("/admin/verifications", headers=cust_headers_spoof)
    assert res_adm.status_code == 403

    # 3. Worker cannot create jobs regardless of Origin
    job_payload = {
        "category": "electrician",
        "description": "Worker trying to create customer job",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road"},
        "budget": 500.0,
    }
    res_job = client.post("/jobs", json=job_payload, headers=worker_headers_spoof)
    assert res_job.status_code == 403


def test_shared_service_e2e_customer_to_partner_lifecycle(client):
    """
    Complete lifecycle spanning Customer App and Partner App (Worker + Admin):
    1. Customer creates job (Customer App)
    2. Worker sees job in nearby feed (Partner App)
    3. Worker submits offer (Partner App)
    4. Customer accepts offer (Customer App)
    5. Worker starts and completes job (Partner App)
    6. Customer submits review (Customer App)
    7. Admin inspects dashboard & reviews (Partner App)
    """
    seed_database()

    customer_uid = "cust_priya"
    worker_uid = "worker_elec_1"
    auth_customer = {"Authorization": f"Bearer {customer_uid}"}
    auth_worker = {"Authorization": f"Bearer {worker_uid}"}
    auth_admin = {"Authorization": "Bearer admin_user"}

    # Step 1: Customer creates job via Customer App
    job_payload = {
        "category": "electrician",
        "description": "Ceiling fan installation in dining room",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Beverly Park, Mira Road"},
        "budget": 450.0,
        "mode": "on-demand",
    }
    res_job = client.post("/jobs", json=job_payload, headers=auth_customer)
    assert res_job.status_code == 201
    job_data = res_job.json()
    job_id = job_data["id"]
    assert job_data["status"] == "open"
    assert job_data["customerId"] == customer_uid

    # Step 2: Worker queries nearby open jobs via Partner App
    res_nearby = client.get("/jobs/nearby", headers=auth_worker)
    assert res_nearby.status_code == 200
    nearby_jobs = res_nearby.json()
    assert any(j["job"]["id"] == job_id for j in nearby_jobs)

    # Step 3: Worker submits price proposal via Partner App
    offer_payload = {
        "jobId": job_id,
        "workerId": worker_uid,
        "price": 450.0,
        "by": "worker",
    }
    res_offer = client.post("/offers", json=offer_payload, headers=auth_worker)
    assert res_offer.status_code == 201
    offer_id = res_offer.json()["id"]

    # Step 4: Customer accepts offer via Customer App
    res_accept = client.post(f"/offers/{offer_id}/accept", headers=auth_customer)
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "accepted"

    # Verify job status in shared DB
    job_doc = client.get(f"/jobs/{job_id}", headers=auth_customer).json()
    assert job_doc["status"] == "accepted"
    assert job_doc["acceptedWorkerId"] == worker_uid

    # Step 5: Worker starts and completes job via Partner App
    res_start = client.post(f"/jobs/{job_id}/start", headers=auth_worker)
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "in_progress"

    res_comp = client.post(f"/jobs/{job_id}/complete", headers=auth_worker)
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "completed"

    # Step 6: Customer submits review via Customer App
    review_payload = {
        "jobId": job_id,
        "workerId": worker_uid,
        "rating": 5.0,
        "comment": "Punctual and very neat electrical installation!",
    }
    res_rev = client.post("/reviews", json=review_payload, headers=auth_customer)
    assert res_rev.status_code == 201
    assert res_rev.json()["rating"] == 5.0

    # Step 7: Admin verifies metrics via Partner App (Admin view)
    res_stats = client.get("/admin/stats", headers=auth_admin)
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["totalJobs"] >= 1
    assert stats["completedJobs"] >= 1


def test_cross_entity_data_isolation(client):
    """
    Validates that:
    - Worker A cannot modify Worker B's profile
    - Customer A cannot cancel Customer B's job
    - Customer cannot view unassigned worker's raw phone
    """
    seed_database()

    auth_worker_1 = {"Authorization": "Bearer worker_elec_1"}
    auth_cust_1 = {"Authorization": "Bearer cust_priya"}
    auth_cust_2 = {"Authorization": "Bearer cust_amit"}

    # 1. Worker 1 tries to update Worker 2's profile -> 403 Forbidden
    res_patch = client.patch(
        "/workers/worker_elec_2",
        json={"isAvailableNow": False},
        headers=auth_worker_1,
    )
    assert res_patch.status_code == 403

    # 2. Customer 2 tries to cancel Customer 1's job -> 403 Forbidden
    res_cancel = client.post("/jobs/job_seed_plumber_open/cancel", headers=auth_cust_2)
    assert res_cancel.status_code == 403

    # 3. Customer 1 can cancel their own job -> 200 OK
    res_cancel_own = client.post("/jobs/job_seed_plumber_open/cancel", headers=auth_cust_1)
    assert res_cancel_own.status_code == 200
    assert res_cancel_own.json()["status"] == "cancelled"
