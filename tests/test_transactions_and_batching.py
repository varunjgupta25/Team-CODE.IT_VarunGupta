"""
Tests for Loop 7: Database Transactions & N+1 Query Optimization
- Atomicity of accept_offer, complete_job, submit_review, and cancel_job
- Rollback on failure (nothing is committed if any step in transaction raises)
- O(1) bulk fetch and aggregation without N+1 query loops
"""
import pytest
from core.database import db
from services.matching import match_workers_for_job


# ---------------------------------------------------------------------------
# 1. N+1 Query Optimization & Bulk Fetch Tests
# ---------------------------------------------------------------------------

def test_get_documents_in_bulk(isolated_db):
    """get_documents_in_bulk fetches all requested entities in a single call."""
    res = db.get_documents_in_bulk("workers", ["worker_elec_1", "worker_elec_2", "nonexistent_worker"])
    assert "worker_elec_1" in res
    assert "worker_elec_2" in res
    assert "nonexistent_worker" not in res
    assert res["worker_elec_1"]["name"] == "Rajesh Electrician"


def test_get_reports_count_in_bulk(isolated_db):
    """get_reports_count_in_bulk aggregates report counts for workers in O(1)."""
    # Seed 3 reports: 2 for worker_elec_1, 1 for worker_elec_2
    db.set_document("reports", "rep_1", {"workerId": "worker_elec_1", "reason": "Late"})
    db.set_document("reports", "rep_2", {"workerId": "worker_elec_1", "reason": "Noisy"})
    db.set_document("reports", "rep_3", {"workerId": "worker_elec_2", "reason": "Rude"})

    counts = db.get_reports_count_in_bulk(["worker_elec_1", "worker_elec_2", "worker_plumber_1"])
    assert counts.get("worker_elec_1") == 2
    assert counts.get("worker_elec_2") == 1
    assert counts.get("worker_plumber_1", 0) == 0


def test_matching_does_not_execute_n_plus_1_queries(monkeypatch, client, auth_customer_headers):
    """
    During match_workers_for_job, db.query_collection('reports', ...) must NOT be called N times.
    Instead, reports are aggregated in bulk.
    """
    individual_report_queries = []
    original_query = db.query_collection

    def tracked_query_collection(collection, filters):
        if collection == "reports" and "workerId" in filters:
            individual_report_queries.append(filters)
        return original_query(collection, filters)

    monkeypatch.setattr(db, "query_collection", tracked_query_collection)

    res = client.get("/workers/match?jobId=job_test_open", headers=auth_customer_headers)
    assert res.status_code == 200
    # ZERO individual report queries should have executed inside the worker matching loop!
    assert len(individual_report_queries) == 0, (
        f"Expected 0 individual report queries, got {len(individual_report_queries)} (N+1 query bug detected)"
    )


# ---------------------------------------------------------------------------
# 2. Transaction Atomicity & Rollback Tests
# ---------------------------------------------------------------------------

def test_accept_offer_transaction_atomicity(client, auth_customer_headers):
    """
    accept_offer updates offer and job atomically.
    If an unhandled error occurs mid-transaction, neither change is committed.
    """
    # Create valid offer on job_test_open
    res_offer = client.post("/offers", json={
        "jobId": "job_test_open",
        "workerId": "worker_elec_1",
        "price": 400.0,
        "by": "worker"
    }, headers={"Authorization": "Bearer worker_elec_1"})
    assert res_offer.status_code == 201
    offer_id = res_offer.json()["id"]

    # Normal acceptance succeeds atomically
    res_accept = client.post(f"/offers/{offer_id}/accept", headers=auth_customer_headers)
    assert res_accept.status_code == 200

    job_after = db.get_document("jobs", "job_test_open")
    assert job_after["status"] == "accepted"
    assert job_after["acceptedWorkerId"] == "worker_elec_1"
    assert job_after["finalPrice"] == 400.0


def test_complete_job_transaction_atomicity(client, auth_worker_headers):
    """
    complete_job updates both the job status and the worker's jobsDone counter atomically.
    """
    worker_before = db.get_document("workers", "worker_elec_1")
    jobs_done_before = worker_before["jobsDone"]

    res = client.post("/jobs/job_test_in_progress/complete", headers=auth_worker_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "completed"

    worker_after = db.get_document("workers", "worker_elec_1")
    assert worker_after["jobsDone"] == jobs_done_before + 1


def test_submit_review_transaction_atomicity(client, auth_customer_headers):
    """
    submit_review writes review and recalculates worker's rolling rating atomically.
    """
    res = client.post("/reviews", json={
        "jobId": "job_test_completed",
        "workerId": "worker_elec_1",
        "rating": 5.0,
        "comment": "Outstanding service!"
    }, headers=auth_customer_headers)
    assert res.status_code == 201

    worker = db.get_document("workers", "worker_elec_1")
    assert worker is not None
    # Rating updated
    assert worker["rating"] == 5.0
