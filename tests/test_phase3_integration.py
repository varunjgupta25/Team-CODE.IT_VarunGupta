"""
tests/test_phase3_integration.py

Phase 3 Comprehensive Integration & Safety Test Suite
Validates:
1. End-to-end admin verification approval & rejection
2. State machine transaction integrity & competing offer rejection
3. Safety report moderation & automatic trust flag resolution
4. Account suspension and access rejection
5. Cross-collection persistence
"""

import pytest
from core.database import db
from seed import seed_database


def test_admin_verification_lifecycle(client):
    """
    Worker requests verification -> shows up in pending queue -> admin approves -> verified status is set.
    Another worker requests verification -> admin rejects -> verified is False.
    """
    seed_database()

    # 1. Inspect initial pending queue (admin auth)
    auth_admin = {"Authorization": "Bearer admin_user"}
    res_pending = client.get("/admin/verifications/pending", headers=auth_admin)
    assert res_pending.status_code == 200
    pending_workers = res_pending.json()
    assert isinstance(pending_workers, list)

    # 2. Worker requests verification
    unverified_worker_id = "worker_plumber_unverified"
    auth_worker = {"Authorization": f"Bearer {unverified_worker_id}"}
    verify_payload = {
        "documentType": "aadhaar",
        "documentNumber": "987654321098"
    }
    res_req = client.post("/workers/verify", json=verify_payload, headers=auth_worker)
    assert res_req.status_code == 200
    assert res_req.json()["status"] == "pending"

    # 3. Admin approves
    res_approve = client.post(f"/admin/verifications/{unverified_worker_id}/approve", headers=auth_admin)
    assert res_approve.status_code == 200
    assert res_approve.json()["verified"] is True

    worker_doc = db.get_document("workers", unverified_worker_id)
    assert worker_doc["verified"] is True

    # 4. Another worker rejected
    unverified_elec_id = "worker_elec_unverified"
    auth_elec = {"Authorization": f"Bearer {unverified_elec_id}"}
    client.post("/workers/verify", json=verify_payload, headers=auth_elec)
    res_reject = client.post(f"/admin/verifications/{unverified_elec_id}/reject", headers=auth_admin)
    assert res_reject.status_code == 200
    assert res_reject.json()["verified"] is False
    assert res_reject.json()["status"] == "rejected"


def test_competing_offers_atomic_rejection(client):
    """
    When customer accepts an offer on a job with multiple pending offers,
    the selected offer transitions to 'accepted', the job transitions to 'accepted',
    and ALL competing pending offers for that job are auto-rejected.
    """
    seed_database()

    customer_uid = "cust_priya"
    worker_1 = "worker_elec_1"
    worker_2 = "worker_elec_2"

    auth_customer = {"Authorization": f"Bearer {customer_uid}"}
    auth_worker_1 = {"Authorization": f"Bearer {worker_1}"}
    auth_worker_2 = {"Authorization": f"Bearer {worker_2}"}

    # 1. Create open job
    job_payload = {
        "category": "electrician",
        "description": "Short circuit repair in bedroom",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road East"},
        "budget": 500.0,
        "mode": "on-demand"
    }
    res_job = client.post("/jobs", json=job_payload, headers=auth_customer)
    assert res_job.status_code == 201
    job_id = res_job.json()["id"]

    # 2. Worker 1 submits offer
    off_1 = client.post("/offers", json={
        "jobId": job_id, "workerId": worker_1, "price": 450.0, "by": "worker"
    }, headers=auth_worker_1).json()

    # 3. Worker 2 submits competing offer
    off_2 = client.post("/offers", json={
        "jobId": job_id, "workerId": worker_2, "price": 400.0, "by": "worker"
    }, headers=auth_worker_2).json()

    assert off_1["status"] == "pending"
    assert off_2["status"] == "pending"

    # 4. Customer accepts Worker 2's offer
    res_accept = client.post(f"/offers/{off_2['id']}/accept", headers=auth_customer)
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "accepted"

    # 5. Verify Job state
    job_doc = client.get(f"/jobs/{job_id}", headers=auth_customer).json()
    assert job_doc["status"] == "accepted"
    assert job_doc["acceptedWorkerId"] == worker_2
    assert job_doc["finalPrice"] == 400.0

    # 6. Verify Worker 1's competing offer was automatically rejected
    competing_off = db.get_document("offers", off_1["id"])
    assert competing_off["status"] == "rejected"


def test_safety_report_resolution_and_reactivation_flow(client):
    """
    Submitting multiple reports auto-flags worker -> admin inspects reports ->
    resolves report -> reactivates worker.
    """
    seed_database()

    worker_id = "worker_elec_1"
    auth_admin = {"Authorization": "Bearer admin_user"}
    auth_cust_1 = {"Authorization": "Bearer cust_priya"}
    auth_cust_2 = {"Authorization": "Bearer cust_amit"}
    auth_cust_3 = {"Authorization": "Bearer cust_test_1"}

    # 3 customer reports in short window
    rep1 = client.post("/reports", json={"workerId": worker_id, "reason": "No show", "category": "no_show"}, headers=auth_cust_1).json()
    rep2 = client.post("/reports", json={"workerId": worker_id, "reason": "Rude", "category": "harassment"}, headers=auth_cust_2).json()
    rep3 = client.post("/reports", json={"workerId": worker_id, "reason": "Overcharging", "category": "other"}, headers=auth_cust_3).json()

    # Worker must now be auto-flagged and under review
    w_doc = db.get_document("workers", worker_id)
    assert w_doc["isFlagged"] is True
    assert w_doc["accountStatus"] == "UNDER_REVIEW"

    # Admin checks reports
    res_reps = client.get("/admin/reports?status=pending", headers=auth_admin)
    assert res_reps.status_code == 200
    assert len(res_reps.json()) >= 3

    # Admin resolves report
    res_res = client.post(f"/admin/reports/{rep1['id']}/resolve", json={"action": "Warned worker"}, headers=auth_admin)
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "resolved"

    # Admin reactivates worker
    res_react = client.post(f"/admin/users/{worker_id}/reactivate", headers=auth_admin)
    assert res_react.status_code == 200
    w_after = db.get_document("workers", worker_id)
    assert w_after["isFlagged"] is False
    assert w_after["accountStatus"] == "ACTIVE"


def test_suspended_user_isolation(client):
    """
    Admin suspends a user -> user profile reflects SUSPENDED status -> admin reactivates.
    """
    seed_database()
    auth_admin = {"Authorization": "Bearer admin_user"}
    target_user = "cust_amit"

    # Suspend user
    sus_res = client.post(f"/admin/users/{target_user}/suspend", json={"reason": "Terms violation"}, headers=auth_admin)
    assert sus_res.status_code == 200
    assert sus_res.json()["accountStatus"] == "SUSPENDED"

    user_doc = db.get_document("users", target_user)
    assert user_doc["accountStatus"] == "SUSPENDED"

    # Reactivate user
    act_res = client.post(f"/admin/users/{target_user}/reactivate", headers=auth_admin)
    assert act_res.status_code == 200
    assert act_res.json()["accountStatus"] == "ACTIVE"

