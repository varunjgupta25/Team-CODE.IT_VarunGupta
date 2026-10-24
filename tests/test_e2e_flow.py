"""
tests/test_e2e_flow.py

End-to-End single test:
seed -> post job -> match -> offer -> counter -> accept -> start -> complete -> review -> SOS
and verifies the final state across all entities.
"""

import math
import pytest
from seed import seed_database
from core.database import db


def test_full_e2e_journey(client):
    """
    Executes the full user lifecycle:
    1. Seed database
    2. Customer posts a job (open)
    3. Customer queries matching workers
    4. Customer submits offer to top-matched worker
    5. Worker counters the offer
    6. Customer accepts the counter-offer (job -> accepted)
    7. Worker starts the job (job -> in_progress)
    8. Worker completes the job (job -> completed, jobsDone incremented)
    9. Customer submits 5-star review (worker rating updated)
    10. Customer triggers SOS alert (recorded in sos_alerts)
    11. Verify all final states
    """
    # 1. Seed database
    seed_database()

    customer_uid = "cust_priya"
    worker_uid = "worker_elec_1"
    auth_customer = {"Authorization": f"Bearer {customer_uid}"}
    auth_worker = {"Authorization": f"Bearer {worker_uid}"}

    # 2. Customer posts a job
    new_job_payload = {
        "category": "electrician",
        "description": "Ceiling fan sparking and vibrating loudly",
        "location": {
            "lat": 19.2825,
            "lng": 72.8570,
            "address": "B-302, Shanti Park, Mira Road East"
        },
        "budget": 500.0,
        "mode": "on-demand"
    }
    res_job = client.post("/jobs", json=new_job_payload, headers=auth_customer)
    assert res_job.status_code == 201
    job = res_job.json()
    job_id = job["id"]
    assert job["status"] == "open"
    assert job["customerId"] == customer_uid

    # 3. Customer queries matching workers
    res_match = client.get(f"/workers/match?jobId={job_id}", headers=auth_customer)
    assert res_match.status_code == 200
    matches = res_match.json()
    assert len(matches) > 0
    top_worker = matches[0]["worker"]
    assert top_worker["verified"] is True
    assert top_worker["isAvailableNow"] is True

    # 4. Customer submits offer
    offer_payload = {
        "jobId": job_id,
        "workerId": worker_uid,
        "price": 350.0,
        "by": "customer"
    }
    res_offer = client.post("/offers", json=offer_payload, headers=auth_customer)
    assert res_offer.status_code == 201
    offer1 = res_offer.json()
    offer1_id = offer1["id"]
    assert offer1["status"] == "pending"

    # Verify job transitioned to negotiating
    job_state1 = client.get(f"/jobs/{job_id}", headers=auth_customer).json()
    assert job_state1["status"] == "negotiating"

    # 5. Worker counters the offer
    res_counter = client.post(
        f"/offers/{offer1_id}/counter",
        json={"price": 450.0},
        headers=auth_worker
    )
    assert res_counter.status_code == 200
    offer2 = res_counter.json()
    offer2_id = offer2["id"]
    assert offer2["price"] == 450.0
    assert offer2["by"] == "worker"

    # 6. Customer accepts the counter-offer
    res_accept = client.post(f"/offers/{offer2_id}/accept", headers=auth_customer)
    assert res_accept.status_code == 200
    accepted_off = res_accept.json()
    assert accepted_off["status"] == "accepted"

    # Verify job is accepted with locked final price and assigned worker
    job_state2 = client.get(f"/jobs/{job_id}", headers=auth_customer).json()
    assert job_state2["status"] == "accepted"
    assert job_state2["acceptedWorkerId"] == worker_uid
    assert job_state2["finalPrice"] == 450.0

    # 7. Worker starts the job
    res_start = client.post(f"/jobs/{job_id}/start", headers=auth_worker)
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "in_progress"

    # 8. Worker completes the job
    worker_before = db.get_document("workers", worker_uid)
    jobs_done_before = int(worker_before.get("jobsDone", 0))

    res_comp = client.post(f"/jobs/{job_id}/complete", headers=auth_worker)
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "completed"

    worker_after = db.get_document("workers", worker_uid)
    assert int(worker_after["jobsDone"]) == jobs_done_before + 1

    # 9. Customer submits review
    review_payload = {
        "jobId": job_id,
        "workerId": worker_uid,
        "rating": 5.0,
        "comment": "Repaired in 15 minutes, excellent service!"
    }
    res_rev = client.post("/reviews", json=review_payload, headers=auth_customer)
    assert res_rev.status_code == 201
    rev_data = res_rev.json()
    assert rev_data["rating"] == 5.0

    # 10. Customer triggers SOS alert
    sos_payload = {
        "jobId": job_id,
        "location": {
            "lat": 19.2825,
            "lng": 72.8570
        }
    }
    res_sos = client.post("/sos", json=sos_payload, headers=auth_customer)
    assert res_sos.status_code == 201
    sos_data = res_sos.json()
    assert sos_data["status"] == "recorded"
    assert sos_data["jobId"] == job_id
    assert sos_data["userId"] == customer_uid

    # 11. Final verification across all collections
    final_job = db.get_document("jobs", job_id)
    assert final_job["status"] == "completed"
    assert final_job["acceptedWorkerId"] == worker_uid
    assert final_job["finalPrice"] == 450.0

    final_worker = db.get_document("workers", worker_uid)
    assert final_worker["rating"] >= 4.0
    assert final_worker["jobsDone"] == jobs_done_before + 1

    final_sos = db.get_document("sos_alerts", sos_data["id"])
    assert final_sos is not None
    assert final_sos["userId"] == customer_uid
