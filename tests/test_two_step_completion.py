import pytest
from datetime import datetime, timezone, timedelta
from core.database import db
from core.config import settings


def test_worker_complete_moves_to_awaiting_confirmation_and_does_not_increment_jobs_done(client, auth_worker_headers):
    """
    Worker POST /jobs/{id}/complete moves in_progress -> awaiting_confirmation,
    sets completedByWorkerAt, and does NOT increment jobsDone.
    """
    job_id = "job_test_in_progress"
    worker_id = "worker_elec_1"

    worker_before = db.get_document("workers", worker_id)
    jobs_done_before = int(worker_before.get("jobsDone", 0))

    res = client.post(f"/jobs/{job_id}/complete", headers=auth_worker_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "awaiting_confirmation"
    assert data["completedByWorkerAt"] is not None

    # Database verify
    db_job = db.get_document("jobs", job_id)
    assert db_job["status"] == "awaiting_confirmation"
    assert db_job.get("completedByWorkerAt") is not None

    # jobsDone MUST NOT be incremented
    worker_after = db.get_document("workers", worker_id)
    assert int(worker_after["jobsDone"]) == jobs_done_before


def test_customer_confirm_moves_to_completed_and_increments_jobs_done(
    client, auth_worker_headers, auth_customer_headers
):
    """
    Customer POST /jobs/{id}/confirm moves awaiting_confirmation -> completed,
    sets completedAt, and increments worker's jobsDone exactly once.
    """
    job_id = "job_test_in_progress"
    worker_id = "worker_elec_1"

    # 1. Worker marks complete
    client.post(f"/jobs/{job_id}/complete", headers=auth_worker_headers)
    worker_before = db.get_document("workers", worker_id)
    jobs_done_before = int(worker_before.get("jobsDone", 0))

    # 2. Customer confirms completion
    res = client.post(f"/jobs/{job_id}/confirm", headers=auth_customer_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["completedAt"] is not None

    # Database verify
    db_job = db.get_document("jobs", job_id)
    assert db_job["status"] == "completed"
    assert db_job.get("completedAt") is not None

    # jobsDone MUST be incremented by 1
    worker_after = db.get_document("workers", worker_id)
    assert int(worker_after["jobsDone"]) == jobs_done_before + 1


def test_confirm_second_call_does_not_double_increment(
    client, auth_worker_headers, auth_customer_headers
):
    """
    A second call to POST /jobs/{id}/confirm returns 400 and does NOT double-increment jobsDone.
    """
    job_id = "job_test_in_progress"
    worker_id = "worker_elec_1"

    # Complete then confirm once
    client.post(f"/jobs/{job_id}/complete", headers=auth_worker_headers)
    client.post(f"/jobs/{job_id}/confirm", headers=auth_customer_headers)

    worker_confirmed = db.get_document("workers", worker_id)
    jobs_done_expected = int(worker_confirmed.get("jobsDone", 0))

    # Second confirm call -> 400
    res_second = client.post(f"/jobs/{job_id}/confirm", headers=auth_customer_headers)
    assert res_second.status_code == 400
    assert "already completed" in res_second.json().get("detail", "").lower()

    # Verify no double-increment occurred
    worker_after = db.get_document("workers", worker_id)
    assert int(worker_after["jobsDone"]) == jobs_done_expected


def test_unauthenticated_and_worker_and_other_customers_cannot_confirm(
    client, auth_worker_headers, auth_customer_headers, auth_customer_2_headers
):
    """
    Worker, other customers and unauthenticated callers get 403/401 on POST /jobs/{id}/confirm.
    """
    job_id = "job_test_in_progress"

    # Worker marks complete -> awaiting_confirmation
    client.post(f"/jobs/{job_id}/complete", headers=auth_worker_headers)

    # 1. Unauthenticated -> 401
    res_unauth = client.post(f"/jobs/{job_id}/confirm")
    assert res_unauth.status_code == 401

    # 2. Worker calls confirm -> 403
    res_worker = client.post(f"/jobs/{job_id}/confirm", headers=auth_worker_headers)
    assert res_worker.status_code == 403

    # 3. Other customer (not the creator of job_test_in_progress) calls confirm -> 403
    res_cust2 = client.post(f"/jobs/{job_id}/confirm", headers=auth_customer_2_headers)
    assert res_cust2.status_code == 403
    assert "only the customer who created this job" in res_cust2.json().get("detail", "").lower()


def test_accepted_worker_none_blocks_start_and_complete(client, auth_worker_headers):
    """
    When acceptedWorkerId is None, an arbitrary worker CANNOT start or complete the job (returns 403).
    """
    # Create an accepted job without acceptedWorkerId
    db.set_document("jobs", "job_no_worker_accepted", {
        "id": "job_no_worker_accepted",
        "customerId": "cust_test_1",
        "category": "electrician",
        "description": "Wiring",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road"},
        "status": "accepted",
        "acceptedWorkerId": None,
        "createdAt": "2026-10-24T10:00:00Z"
    })

    # Worker attempts start -> 403
    res_start = client.post("/jobs/job_no_worker_accepted/start", headers=auth_worker_headers)
    assert res_start.status_code == 403

    # Create an in_progress job without acceptedWorkerId
    db.set_document("jobs", "job_no_worker_progress", {
        "id": "job_no_worker_progress",
        "customerId": "cust_test_1",
        "category": "electrician",
        "description": "Wiring",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road"},
        "status": "in_progress",
        "acceptedWorkerId": None,
        "createdAt": "2026-10-24T10:00:00Z"
    })

    # Worker attempts complete -> 403
    res_comp = client.post("/jobs/job_no_worker_progress/complete", headers=auth_worker_headers)
    assert res_comp.status_code == 403


def test_auto_confirm_after_configured_hours_applied_lazily_on_read(client, auth_customer_headers, monkeypatch):
    """
    Auto-confirm after AUTO_CONFIRM_HOURS (default 48) applied lazily when the job is read via GET /jobs/{id}.
    """
    monkeypatch.setattr(settings, "AUTO_CONFIRM_HOURS", 48.0)
    worker_id = "worker_elec_1"
    worker_before = db.get_document("workers", worker_id)
    jobs_done_before = int(worker_before.get("jobsDone", 0))

    # 49 hours ago
    past_time = (datetime.now(timezone.utc) - timedelta(hours=49)).isoformat()

    db.set_document("jobs", "job_lazy_read", {
        "id": "job_lazy_read",
        "customerId": "cust_test_1",
        "category": "electrician",
        "description": "Fan repair",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road"},
        "status": "awaiting_confirmation",
        "acceptedWorkerId": worker_id,
        "completedByWorkerAt": past_time,
        "createdAt": past_time
    })

    # Reading the job triggers lazy auto-confirmation
    res = client.get("/jobs/job_lazy_read", headers=auth_customer_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"

    # Worker jobsDone incremented
    worker_after = db.get_document("workers", worker_id)
    assert int(worker_after["jobsDone"]) == jobs_done_before + 1


def test_auto_confirm_after_configured_hours_applied_lazily_on_listing(client, auth_worker_headers, monkeypatch):
    """
    Auto-confirm after AUTO_CONFIRM_HOURS applied lazily when jobs are listed/queried via GET /jobs/nearby.
    """
    monkeypatch.setattr(settings, "AUTO_CONFIRM_HOURS", 48.0)
    worker_id = "worker_elec_1"
    worker_before = db.get_document("workers", worker_id)
    jobs_done_before = int(worker_before.get("jobsDone", 0))

    past_time = (datetime.now(timezone.utc) - timedelta(hours=50)).isoformat()

    db.set_document("jobs", "job_lazy_list", {
        "id": "job_lazy_list",
        "customerId": "cust_test_1",
        "category": "electrician",
        "description": "Exhaust fan fix",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road"},
        "status": "awaiting_confirmation",
        "acceptedWorkerId": worker_id,
        "completedByWorkerAt": past_time,
        "createdAt": past_time
    })

    # Listing nearby jobs touches database jobs and triggers lazy check
    res = client.get("/jobs/nearby", headers=auth_worker_headers)
    assert res.status_code == 200

    # Job is now completed
    db_job = db.get_document("jobs", "job_lazy_list")
    assert db_job["status"] == "completed"
    assert db_job.get("autoConfirmed") is True

    # Worker jobsDone incremented
    worker_after = db.get_document("workers", worker_id)
    assert int(worker_after["jobsDone"]) == jobs_done_before + 1


def test_reviews_blocked_on_awaiting_confirmation_and_allowed_after_confirm(
    client, auth_worker_headers, auth_customer_headers
):
    """
    Reviews still require 'completed' status, so attempting to review while
    'awaiting_confirmation' returns 400. Once confirmed, review succeeds.
    """
    job_id = "job_test_in_progress"
    worker_id = "worker_elec_1"

    # Worker completes -> awaiting_confirmation
    client.post(f"/jobs/{job_id}/complete", headers=auth_worker_headers)

    # Customer tries to review immediately -> 400
    res_review_early = client.post("/reviews", json={
        "jobId": job_id,
        "workerId": worker_id,
        "rating": 5.0,
        "comment": "Too early review"
    }, headers=auth_customer_headers)
    assert res_review_early.status_code == 400
    assert "completed" in res_review_early.json().get("detail", "").lower()

    # Customer confirms job -> completed
    res_conf = client.post(f"/jobs/{job_id}/confirm", headers=auth_customer_headers)
    assert res_conf.status_code == 200

    # Now review succeeds -> 201
    res_review = client.post("/reviews", json={
        "jobId": job_id,
        "workerId": worker_id,
        "rating": 5.0,
        "comment": "Excellent repair, confirmed!"
    }, headers=auth_customer_headers)
    assert res_review.status_code == 201
    assert res_review.json()["rating"] == 5.0


def test_cancel_blocked_on_completed_job(client, auth_customer_headers):
    """
    Cancel is blocked on completed jobs (returns 400).
    """
    res = client.post("/jobs/job_test_completed/cancel", headers=auth_customer_headers)
    assert res.status_code == 400
    assert "completed" in res.json().get("detail", "").lower()

