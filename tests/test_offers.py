import pytest
from core.database import db


def test_full_negotiation_flow(client, auth_customer_headers, auth_worker_headers):
    """
    Complete negotiation flow:
    1. Customer creates initial offer (Rs. 350) -> status is pending, job becomes 'negotiating'.
    2. Worker counters with Rs. 500 -> previous offer rejected, new counter offer created.
    3. Customer counters back with Rs. 420 -> previous counter rejected, new offer created.
    4. Worker accepts Rs. 420 -> offer accepted, job status='accepted', acceptedWorkerId and finalPrice set.
    """
    job_id = "job_test_open"

    # 1. Customer initiates offer
    payload1 = {
        "jobId": job_id,
        "workerId": "worker_elec_1",
        "price": 350.0,
        "by": "customer"
    }
    res = client.post("/offers", json=payload1, headers=auth_customer_headers)
    assert res.status_code == 201, res.text
    offer1 = res.json()
    assert offer1["price"] == 350.0
    assert offer1["by"] == "customer"
    assert offer1["status"] == "pending"

    # Verify job status transitioned to 'negotiating'
    res_job = client.get(f"/jobs/{job_id}", headers=auth_customer_headers)
    assert res_job.json()["status"] == "negotiating"

    # 2. Worker counters offer to 500.0
    res = client.post(f"/offers/{offer1['id']}/counter", json={"price": 500.0}, headers=auth_worker_headers)
    assert res.status_code == 200, res.text
    offer2 = res.json()
    assert offer2["price"] == 500.0
    assert offer2["by"] == "worker"
    assert offer2["status"] == "pending"

    # Verify previous offer was superseded (marked rejected)
    prev = db.get_document("offers", offer1["id"])
    assert prev["status"] == "rejected"

    # 3. Customer counters back to 420.0
    res = client.post(f"/offers/{offer2['id']}/counter", json={"price": 420.0}, headers=auth_customer_headers)
    assert res.status_code == 200, res.text
    offer3 = res.json()
    assert offer3["price"] == 420.0
    assert offer3["by"] == "customer"
    assert offer3["status"] == "pending"

    # 4. Worker accepts the 420.0 offer
    res = client.post(f"/offers/{offer3['id']}/accept", headers=auth_worker_headers)
    assert res.status_code == 200, res.text
    accepted_offer = res.json()
    assert accepted_offer["status"] == "accepted"

    # Verify job is updated: status='accepted', acceptedWorkerId='worker_elec_1', finalPrice=420.0
    res_job = client.get(f"/jobs/{job_id}", headers=auth_customer_headers)
    job_data = res_job.json()
    assert job_data["status"] == "accepted"
    assert job_data["acceptedWorkerId"] == "worker_elec_1"
    assert job_data["finalPrice"] == 420.0


def test_alternating_turns_and_wrong_party_enforcement(
    client, auth_customer_headers, auth_worker_headers, auth_customer_2_headers, auth_worker_2_headers
):
    """
    Enforces turn taking and authorization:
    - Same party countering their own offer returns 400.
    - Unrelated party countering an offer returns 403.
    - Same party accepting their own offer returns 400.
    - Unrelated party accepting an offer returns 403.
    """
    job_id = "job_test_open"

    # Customer makes offer
    res = client.post("/offers", json={
        "jobId": job_id,
        "workerId": "worker_elec_1",
        "price": 300.0,
        "by": "customer"
    }, headers=auth_customer_headers)
    assert res.status_code == 201
    offer_id = res.json()["id"]

    # 1. Customer tries to counter own offer -> 400
    res = client.post(f"/offers/{offer_id}/counter", json={"price": 320.0}, headers=auth_customer_headers)
    assert res.status_code == 400
    assert "turn" in res.json()["detail"].lower()

    # 2. Customer tries to accept own offer -> 400
    res = client.post(f"/offers/{offer_id}/accept", headers=auth_customer_headers)
    assert res.status_code == 400
    assert "own offer" in res.json()["detail"].lower()

    # 3. Third party customer (cust_test_2) tries to counter -> 403
    res = client.post(f"/offers/{offer_id}/counter", json={"price": 350.0}, headers=auth_customer_2_headers)
    assert res.status_code == 403

    # 4. Third party customer (cust_test_2) tries to accept -> 403
    res = client.post(f"/offers/{offer_id}/accept", headers=auth_customer_2_headers)
    assert res.status_code == 403

    # 5. Third party worker (worker_elec_2) tries to counter -> 403
    res = client.post(f"/offers/{offer_id}/counter", json={"price": 380.0}, headers=auth_worker_2_headers)
    assert res.status_code == 403

    # 6. Third party worker (worker_elec_2) tries to accept -> 403
    res = client.post(f"/offers/{offer_id}/accept", headers=auth_worker_2_headers)
    assert res.status_code == 403


def test_accepting_offer_auto_rejects_competing_offers(
    client, auth_customer_headers, auth_worker_headers, auth_worker_2_headers
):
    """
    When an offer is accepted on a job, all other pending offers on that job must be automatically rejected.
    """
    job_id = "job_test_open"

    # Worker 1 makes an offer
    res1 = client.post("/offers", json={
        "jobId": job_id,
        "workerId": "worker_elec_1",
        "price": 450.0,
        "by": "worker"
    }, headers=auth_worker_headers)
    assert res1.status_code == 201
    offer1_id = res1.json()["id"]

    # Worker 2 makes a competing offer
    res2 = client.post("/offers", json={
        "jobId": job_id,
        "workerId": "worker_elec_2",
        "price": 400.0,
        "by": "worker"
    }, headers=auth_worker_2_headers)
    assert res2.status_code == 201
    offer2_id = res2.json()["id"]

    # Customer accepts Worker 2's offer
    res_accept = client.post(f"/offers/{offer2_id}/accept", headers=auth_customer_headers)
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "accepted"

    # Verify Worker 1's competing offer was automatically rejected
    competing = db.get_document("offers", offer1_id)
    assert competing["status"] == "rejected", f"Competing offer was not auto-rejected: {competing['status']}"


def test_accepting_already_closed_job_fails(client, auth_customer_headers, auth_worker_headers):
    """
    Accepting an offer on an already closed/accepted/completed job returns 400.
    """
    # Create an offer on open job
    res = client.post("/offers", json={
        "jobId": "job_test_open",
        "workerId": "worker_elec_1",
        "price": 450.0,
        "by": "worker"
    }, headers=auth_worker_headers)
    assert res.status_code == 201
    offer_id = res.json()["id"]

    # Mark the job as cancelled
    db.update_document("jobs", "job_test_open", {"status": "cancelled"})

    # Try to accept offer on cancelled job -> 400
    res_accept = client.post(f"/offers/{offer_id}/accept", headers=auth_customer_headers)
    assert res_accept.status_code == 400
    assert "status is 'cancelled'" in res_accept.json()["detail"].lower()


def test_reject_offer_flow(client, auth_customer_headers, auth_worker_headers, auth_customer_2_headers):
    """
    Testing explicit offer rejection:
    - Target party can reject a pending offer.
    - Rejecting already rejected offer returns 400.
    - Unrelated party cannot reject (returns 403).
    """
    res = client.post("/offers", json={
        "jobId": "job_test_open",
        "workerId": "worker_elec_1",
        "price": 450.0,
        "by": "worker"
    }, headers=auth_worker_headers)
    offer_id = res.json()["id"]

    # Unrelated customer tries to reject -> 403
    res_unauth = client.post(f"/offers/{offer_id}/reject", headers=auth_customer_2_headers)
    assert res_unauth.status_code == 403

    # Authorized customer rejects offer -> 200
    res_reject = client.post(f"/offers/{offer_id}/reject", headers=auth_customer_headers)
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "rejected"

    # Rejecting again -> 400
    res_again = client.post(f"/offers/{offer_id}/reject", headers=auth_customer_headers)
    assert res_again.status_code == 400
