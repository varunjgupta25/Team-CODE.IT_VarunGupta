"""
tests/test_trust_verification.py

Tests for:
1. POST /workers/verify sets worker status to pending.
2. POST /admin/verifications/{uid}/approve works only for admin (403 otherwise).
3. Approving an unknown worker UID returns 404.
4. Once approved, the worker appears in /workers/match.
"""

import pytest
from core.database import db


def test_worker_verification_request_flow(client, auth_worker_headers, auth_customer_headers):
    """
    Worker requests ID verification -> status set to pending.
    Customer attempting to call /workers/verify gets 403 Forbidden.
    """
    # Customer gets 403
    res_cust = client.post("/workers/verify", json={"idProofType": "aadhaar"}, headers=auth_customer_headers)
    assert res_cust.status_code == 403

    # Worker request succeeds and sets verificationStatus to pending
    res_worker = client.post("/workers/verify", json={"idProofType": "aadhaar"}, headers=auth_worker_headers)
    assert res_worker.status_code == 200
    data = res_worker.json()
    assert data["status"] == "pending"
    assert data["workerId"] == "worker_elec_1"

    worker_doc = db.get_document("workers", "worker_elec_1")
    assert worker_doc["verificationStatus"] == "pending"


def test_admin_approves_worker_verification_and_worker_appears_in_match(
    client, auth_admin_headers, auth_customer_headers, auth_worker_headers
):
    """
    1. An unverified worker does NOT appear in /workers/match.
    2. Non-admin calls approve -> 403 Forbidden.
    3. Admin approves unknown worker -> 404 Not Found.
    4. Admin approves valid unverified worker -> verified=True, verificationStatus=approved.
    5. The approved worker now appears in /workers/match.
    """
    # Seed an unverified worker
    wid = "worker_new_unverified"
    db.set_document("workers", wid, {
        "uid": wid,
        "name": "Arjun Electrician",
        "skills": ["electrician"],
        "rates": {"electrician": 400.0},
        "isAvailableNow": True,
        "verified": False,
        "verificationStatus": "pending",
        "rating": 5.0,
        "jobsDone": 10,
        "location": {"lat": 19.2825, "lng": 72.8570},
        "serviceRadiusKm": 5.0,
        "isFlagged": False
    })
    db.set_document("users", wid, {
        "uid": wid,
        "role": "worker"
    })

    # 1. Unverified worker does not appear in match
    res_match1 = client.get("/workers/match?jobId=job_test_open", headers=auth_customer_headers)
    assert res_match1.status_code == 200
    matched_uids_before = [m["worker"]["uid"] for m in res_match1.json()]
    assert wid not in matched_uids_before

    # 2. Non-admin caller receives 403
    res_unauth = client.post(f"/admin/verifications/{wid}/approve", headers=auth_customer_headers)
    assert res_unauth.status_code == 403

    # 3. Admin approves unknown worker -> 404
    res_404 = client.post("/admin/verifications/unknown_worker_999/approve", headers=auth_admin_headers)
    assert res_404.status_code == 404

    # 4. Admin approves valid unverified worker -> 200
    res_approve = client.post(f"/admin/verifications/{wid}/approve", headers=auth_admin_headers)
    assert res_approve.status_code == 200
    app_data = res_approve.json()
    assert app_data["verified"] is True
    assert app_data["status"] == "approved"

    # 5. Worker now appears in /workers/match
    res_match2 = client.get("/workers/match?jobId=job_test_open", headers=auth_customer_headers)
    assert res_match2.status_code == 200
    matched_uids_after = [m["worker"]["uid"] for m in res_match2.json()]
    assert wid in matched_uids_after
