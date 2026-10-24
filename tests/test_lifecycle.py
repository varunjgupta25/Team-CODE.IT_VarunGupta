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
