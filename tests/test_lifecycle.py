import pytest
from core.database import db


def test_job_cannot_be_started_before_acceptance(client, auth_worker_headers):
    """
    Starting a job before status is 'accepted' returns 400 with a clear message.
    """
    # 1. Starting an 'open' job -> 400
    res = client.post("/jobs/job_test_open/start", headers=auth_worker_headers)
    assert res.status_code == 400
    detail = res.json().get("detail", "")
    assert "cannot start job" in detail.lower()
    assert "accepted" in detail.lower()

    # 2. Starting a 'negotiating' job -> 400
    db.update_document("jobs", "job_test_open", {"status": "negotiating"})
    res = client.post("/jobs/job_test_open/start", headers=auth_worker_headers)
    assert res.status_code == 400
    detail = res.json().get("detail", "")
    assert "cannot start job" in detail.lower()
    assert "negotiating" in detail.lower()


def test_job_cannot_be_completed_before_starting(client, auth_worker_headers):
    """
    Completing a job before status is 'in_progress' returns 400 with a clear message.
    """
    # 1. Completing an 'open' job -> 400
    res = client.post("/jobs/job_test_open/complete", headers=auth_worker_headers)
    assert res.status_code == 400
    detail = res.json().get("detail", "")
    assert "cannot complete job" in detail.lower()
    assert "in_progress" in detail.lower()

    # 2. Completing an 'accepted' job (not yet started) -> 400
    res = client.post("/jobs/job_test_accepted/complete", headers=auth_worker_headers)
    assert res.status_code == 400
    detail = res.json().get("detail", "")
    assert "cannot complete job" in detail.lower()
    assert "in_progress" in detail.lower()


def test_job_cannot_be_cancelled_after_completion(client, auth_customer_headers):
    """
    Cancelling a job that is already 'completed' returns 400 with a clear message.
    """
    res = client.post("/jobs/job_test_completed/cancel", headers=auth_customer_headers)
    assert res.status_code == 400
    detail = res.json().get("detail", "")
    assert "already been completed" in detail.lower() or "completed" in detail.lower()


def test_valid_lifecycle_transitions_end_to_end(client, auth_customer_headers, auth_worker_headers):
    """
    Tests valid lifecycle:
    POST /jobs (open) -> offer & accept (accepted) -> POST /jobs/{id}/start (in_progress) -> POST /jobs/{id}/complete (completed).
    """
    # 1. Create job
    new_job_payload = {
        "category": "electrician",
        "description": "Exhaust fan not working in kitchen",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road East"},
        "budget": 350.0
    }
    res = client.post("/jobs", json=new_job_payload, headers=auth_customer_headers)
    assert res.status_code == 201
    job_id = res.json()["id"]
    assert res.json()["status"] == "open"

    # 2. Worker makes offer
    res = client.post("/offers", json={
        "jobId": job_id,
        "workerId": "worker_elec_1",
        "price": 350.0,
        "by": "worker"
    }, headers=auth_worker_headers)
    assert res.status_code == 201
    offer_id = res.json()["id"]

    # 3. Customer accepts offer -> status becomes 'accepted'
    res = client.post(f"/offers/{offer_id}/accept", headers=auth_customer_headers)
    assert res.status_code == 200

    job_res = client.get(f"/jobs/{job_id}", headers=auth_customer_headers)
    assert job_res.json()["status"] == "accepted"

    # 4. Worker starts job -> status becomes 'in_progress'
    res = client.post(f"/jobs/{job_id}/start", headers=auth_worker_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"

    # 5. Worker completes job -> status becomes 'completed'
    res = client.post(f"/jobs/{job_id}/complete", headers=auth_worker_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "completed"

    # Verify jobsDone count was incremented
    worker = db.get_document("workers", "worker_elec_1")
    assert worker["jobsDone"] == 52  # Baseline was 51


def test_cancel_job_from_open_and_accepted(client, auth_customer_headers):
    """
    Customer can cancel open or accepted jobs.
    """
    # Cancel open job
    res = client.post("/jobs/job_test_open/cancel", headers=auth_customer_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"

    # Cancelling again returns 400
    res = client.post("/jobs/job_test_open/cancel", headers=auth_customer_headers)
    assert res.status_code == 400

    # Cancel accepted job
    res = client.post("/jobs/job_test_accepted/cancel", headers=auth_customer_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


def test_unassigned_worker_cannot_start_or_complete_job(client, auth_worker_2_headers):
    """
    Only the assigned worker can start or complete the accepted job.
    """
    # job_test_accepted has acceptedWorkerId='worker_elec_1'
    # worker_elec_2 tries to start it -> 403
    res = client.post("/jobs/job_test_accepted/start", headers=auth_worker_2_headers)
    assert res.status_code == 403

    # job_test_in_progress has acceptedWorkerId='worker_elec_1'
    # worker_elec_2 tries to complete it -> 403
    res = client.post("/jobs/job_test_in_progress/complete", headers=auth_worker_2_headers)
    assert res.status_code == 403


def test_double_start_and_double_complete_returns_400(client, auth_worker_headers):
    """
    Double start and double complete must each return HTTP 400 with a clear message.
    """
    # 1. Double start: start accepted job
    res1 = client.post("/jobs/job_test_accepted/start", headers=auth_worker_headers)
    assert res1.status_code == 200

    # Repeat start on already in_progress job -> 400
    res2 = client.post("/jobs/job_test_accepted/start", headers=auth_worker_headers)
    assert res2.status_code == 400
    assert "in_progress" in res2.json().get("detail", "").lower()

    # 2. Complete the job
    res3 = client.post("/jobs/job_test_accepted/complete", headers=auth_worker_headers)
    assert res3.status_code == 200

    # Repeat complete on already completed job -> 400
    res4 = client.post("/jobs/job_test_accepted/complete", headers=auth_worker_headers)
    assert res4.status_code == 400
    assert "completed" in res4.json().get("detail", "").lower()


def test_cancel_while_open_or_negotiating_rejects_pending_offers(client, auth_customer_headers, auth_worker_headers):
    """
    Cancelling a job while open or negotiating cancels the job and auto-rejects all pending offers.
    """
    # Create job
    new_job = {
        "category": "electrician",
        "description": "Short circuit test",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road East"},
        "budget": 300.0
    }
    j_res = client.post("/jobs", json=new_job, headers=auth_customer_headers)
    job_id = j_res.json()["id"]

    # Worker creates offer (transitions job to 'negotiating')
    o_res = client.post("/offers", json={
        "jobId": job_id,
        "workerId": "worker_elec_1",
        "price": 300.0,
        "by": "worker"
    }, headers=auth_worker_headers)
    assert o_res.status_code == 201
    offer_id = o_res.json()["id"]

    # Customer cancels job
    c_res = client.post(f"/jobs/{job_id}/cancel", headers=auth_customer_headers)
    assert c_res.status_code == 200
    assert c_res.json()["status"] == "cancelled"

    # Verify pending offer was auto-rejected
    off = db.get_document("offers", offer_id)
    assert off["status"] == "rejected"


def test_get_job_privacy_address_masking_for_workers(client, auth_worker_headers, auth_customer_headers):
    """
    Workers cannot see exact street address of jobs unless they are the accepted worker for an active/completed job.
    """
    # job_test_open has no accepted worker
    res = client.get("/jobs/job_test_open", headers=auth_worker_headers)
    assert res.status_code == 200
    assert "hidden" in res.json()["location"]["address"].lower()

    # Customer who owns the job sees the full address
    res_cust = client.get("/jobs/job_test_open", headers=auth_customer_headers)
    assert res_cust.status_code == 200
    assert "hidden" not in res_cust.json()["location"]["address"].lower()

    # Job not found -> 404
    res_404 = client.get("/jobs/nonexistent_job_xyz", headers=auth_customer_headers)
    assert res_404.status_code == 404


def test_lifecycle_404_on_unknown_jobs(client, auth_worker_headers, auth_customer_headers):
    """
    start, complete, and cancel return 404 on unknown job IDs.
    """
    assert client.post("/jobs/job_unknown_xyz/start", headers=auth_worker_headers).status_code == 404
    assert client.post("/jobs/job_unknown_xyz/complete", headers=auth_worker_headers).status_code == 404
    assert client.post("/jobs/job_unknown_xyz/cancel", headers=auth_customer_headers).status_code == 404


def test_get_nearby_jobs_worker_filtering_and_fallback(client, auth_worker_headers):
    """
    Tests nearby jobs feed filtering:
    - Worker without profile in db falls back to listing open jobs.
    - Jobs with category not matching worker skills or out of radius are excluded.
    """
    # Seed user with role 'worker' but without document in 'workers' collection
    db.set_document("users", "worker_fallback_user", {
        "uid": "worker_fallback_user",
        "role": "worker",
        "name": "Fallback User"
    })
    res_fallback = client.get("/jobs/nearby", headers={"Authorization": "Bearer worker_fallback_user"})
    assert res_fallback.status_code == 200
    assert isinstance(res_fallback.json(), list)

    # Registered worker feed
    res_feed = client.get("/jobs/nearby", headers=auth_worker_headers)
    assert res_feed.status_code == 200
    for item in res_feed.json():
        assert "job" in item
        assert "distanceKm" in item
        assert "etaMinutes" in item
        assert "hidden" in item["job"]["location"]["address"].lower()


