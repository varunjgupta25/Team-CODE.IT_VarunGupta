import math
import pytest
from core.database import db


def test_reviews_rolling_average_three_sequential_reviews(client, auth_customer_headers):
    """
    Submitting reviews updates the rolling average correctly (verified with 3 sequential reviews).
    We seed 3 completed jobs for worker_elec_1, submitted by cust_test_1:
    - Review 1: 4.0 -> rolling avg = 4.0
    - Review 2: 5.0 -> rolling avg = (4.0 + 5.0) / 2 = 4.5
    - Review 3: 3.0 -> rolling avg = (4.0 + 5.0 + 3.0) / 3 = 4.0
    """
    worker_id = "worker_elec_1"

    # Clear reviews for worker
    db.clear_collection("reviews")

    # Seed 3 distinct completed jobs for this customer and worker
    job_ids = ["job_comp_seq_1", "job_comp_seq_2", "job_comp_seq_3"]
    for jid in job_ids:
        db.set_document("jobs", jid, {
            "id": jid,
            "customerId": "cust_test_1",
            "category": "electrician",
            "description": f"Completed task {jid}",
            "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road East"},
            "budget": 400.0,
            "status": "completed",
            "acceptedWorkerId": worker_id,
            "finalPrice": 400.0,
            "createdAt": "2026-10-24T10:00:00Z"
        })

    # Review 1: 4.0
    res1 = client.post("/reviews", json={
        "jobId": job_ids[0],
        "workerId": worker_id,
        "rating": 4.0,
        "comment": "Good job, on time"
    }, headers=auth_customer_headers)
    assert res1.status_code == 201, res1.text
    worker = db.get_document("workers", worker_id)
    assert math.isclose(worker["rating"], 4.0, abs_tol=0.01)

    # Review 2: 5.0
    res2 = client.post("/reviews", json={
        "jobId": job_ids[1],
        "workerId": worker_id,
        "rating": 5.0,
        "comment": "Exceptional work, very polite"
    }, headers=auth_customer_headers)
    assert res2.status_code == 201, res2.text
    worker = db.get_document("workers", worker_id)
    assert math.isclose(worker["rating"], 4.5, abs_tol=0.01)

    # Review 3: 3.0
    res3 = client.post("/reviews", json={
        "jobId": job_ids[2],
        "workerId": worker_id,
        "rating": 3.0,
        "comment": "Average job, slight delay"
    }, headers=auth_customer_headers)
    assert res3.status_code == 201, res3.text
    worker = db.get_document("workers", worker_id)
    assert math.isclose(worker["rating"], 4.0, abs_tol=0.01)


def test_duplicate_review_on_same_job_rejected(client, auth_customer_headers):
    """
    Submitting a duplicate review on the same job must return 400.
    """
    job_id = "job_test_completed"
    review_payload = {
        "jobId": job_id,
        "workerId": "worker_elec_1",
        "rating": 5.0,
        "comment": "Initial review"
    }

    # First review succeeds
    res = client.post("/reviews", json=review_payload, headers=auth_customer_headers)
    assert res.status_code == 201

    # Second review on same job must fail with 400
    res_dup = client.post("/reviews", json=review_payload, headers=auth_customer_headers)
    assert res_dup.status_code == 400
    assert "already been submitted" in res_dup.json()["detail"].lower()


def test_reviews_on_non_completed_jobs_rejected(client, auth_customer_headers):
    """
    Submitting reviews on non-completed jobs (open, accepted, in_progress) returns 400.
    """
    # 1. On open job -> 400
    res = client.post("/reviews", json={
        "jobId": "job_test_open",
        "workerId": "worker_elec_1",
        "rating": 5.0,
        "comment": "Review on open job"
    }, headers=auth_customer_headers)
    assert res.status_code == 400
    assert "completed" in res.json()["detail"].lower()

    # 2. On accepted job -> 400
    res = client.post("/reviews", json={
        "jobId": "job_test_accepted",
        "workerId": "worker_elec_1",
        "rating": 5.0,
        "comment": "Review on accepted job"
    }, headers=auth_customer_headers)
    assert res.status_code == 400

    # 3. On in_progress job -> 400
    res = client.post("/reviews", json={
        "jobId": "job_test_in_progress",
        "workerId": "worker_elec_1",
        "rating": 5.0,
        "comment": "Review on in_progress job"
    }, headers=auth_customer_headers)
    assert res.status_code == 400


def test_non_job_owner_cannot_review_job(client, auth_customer_2_headers):
    """
    A customer who did not create the job cannot review it (returns 403).
    """
    # job_test_completed belongs to cust_test_1. cust_test_2 attempts review -> 403
    res = client.post("/reviews", json={
        "jobId": "job_test_completed",
        "workerId": "worker_elec_1",
        "rating": 5.0,
        "comment": "Stranger review"
    }, headers=auth_customer_2_headers)
    assert res.status_code == 403


def test_sos_stores_alert_with_job_and_location(client, auth_customer_headers):
    """
    POST /sos stores an emergency alert in sos_alerts collection with userId, jobId, and coordinates.
    """
    sos_payload = {
        "jobId": "job_test_open",
        "location": {
            "lat": 19.2825,
            "lng": 72.8570
        }
    }
    res = client.post("/sos", json=sos_payload, headers=auth_customer_headers)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["status"] == "recorded"
    assert data["jobId"] == "job_test_open"
    assert data["userId"] == "cust_test_1"
    assert math.isclose(data["location"]["lat"], 19.2825)
    assert math.isclose(data["location"]["lng"], 72.8570)

    # Check alert was persisted in db
    alert_doc = db.get_document("sos_alerts", data["id"])
    assert alert_doc is not None
    assert alert_doc["userId"] == "cust_test_1"


def test_worker_with_three_reports_gets_flagged(client, auth_customer_headers):
    """
    A worker with 3 reports gets flagged automatically:
    - Initial state: isFlagged=False, flagged=False.
    - Submit 1st report -> isFlagged=False.
    - Submit 2nd report -> isFlagged=False.
    - Submit 3rd report -> isFlagged=True, flagged=True.
    """
    worker_id = "worker_elec_1"
    worker_before = db.get_document("workers", worker_id)
    assert worker_before["isFlagged"] is False

    # 1st report
    res1 = client.post("/reports", json={
        "workerId": worker_id,
        "reason": "Late arrival without notification",
        "jobId": "job_test_completed"
    }, headers=auth_customer_headers)
    assert res1.status_code == 201
    w1 = db.get_document("workers", worker_id)
    assert w1["isFlagged"] is False

    # 2nd report
    res2 = client.post("/reports", json={
        "workerId": worker_id,
        "reason": "Rude behavior during repair"
    }, headers=auth_customer_headers)
    assert res2.status_code == 201
    w2 = db.get_document("workers", worker_id)
    assert w2["isFlagged"] is False

    # 3rd report -> worker MUST be flagged now
    res3 = client.post("/reports", json={
        "workerId": worker_id,
        "reason": "Demanded additional unapproved cash"
    }, headers=auth_customer_headers)
    assert res3.status_code == 201
    w3 = db.get_document("workers", worker_id)
    assert w3["isFlagged"] is True
    assert w3["flagged"] is True


def test_rating_bounds_1_to_5_enforced(client, auth_customer_headers):
    """
    Rating must be between 1.0 and 5.0 (HTTP 422 for values < 1.0 or > 5.0).
    """
    # Rating 0.5 (< 1.0) -> 422
    res_low = client.post("/reviews", json={
        "jobId": "job_test_completed",
        "workerId": "worker_elec_1",
        "rating": 0.5,
        "comment": "Too low"
    }, headers=auth_customer_headers)
    assert res_low.status_code == 422

    # Rating 5.5 (> 5.0) -> 422
    res_high = client.post("/reviews", json={
        "jobId": "job_test_completed",
        "workerId": "worker_elec_1",
        "rating": 5.5,
        "comment": "Too high"
    }, headers=auth_customer_headers)
    assert res_high.status_code == 422


def test_trust_score_range_and_sensitivity():
    """
    Trust score stays strictly within 0-100 and responds sensibly to
    verified status, rating, jobsDone, and report counts.
    """
    from services.trust import compute_trust_score, compute_trust_badge

    base_worker = {
        "verified": False,
        "rating": 3.0,
        "jobsDone": 5,
    }
    score_unverified = compute_trust_score(base_worker, reports_count=0)
    assert 0.0 <= score_unverified <= 100.0

    # 1. Verified bonus (+30)
    verified_worker = {**base_worker, "verified": True}
    score_verified = compute_trust_score(verified_worker, reports_count=0)
    assert score_verified == score_unverified + 30.0

    # 2. Rating sensitivity (higher rating -> higher score)
    high_rating_worker = {**verified_worker, "rating": 5.0}
    score_high_rating = compute_trust_score(high_rating_worker, reports_count=0)
    assert score_high_rating > score_verified

    # 3. Jobs done sensitivity
    experienced_worker = {**high_rating_worker, "jobsDone": 50}
    score_experienced = compute_trust_score(experienced_worker, reports_count=0)
    assert score_experienced > score_high_rating
    assert score_experienced <= 100.0

    # 4. Reports penalty
    score_with_reports = compute_trust_score(experienced_worker, reports_count=2)
    assert score_with_reports < score_experienced

    # 5. Badges mapping
    assert compute_trust_badge(85.0) == "Gold"
    assert compute_trust_badge(65.0) == "Silver"
    assert compute_trust_badge(45.0) == "Bronze"
    assert compute_trust_badge(30.0) == "New"

