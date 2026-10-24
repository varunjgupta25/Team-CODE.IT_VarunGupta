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


def test_worker_cannot_offer_when_unverified(client):
    """An unverified worker cannot submit an offer (HTTP 400)."""
    db.set_document("workers", "worker_unverified_1", {
        "uid": "worker_unverified_1",
        "name": "Unverified Joe",
        "skills": ["electrician"],
        "rates": {"electrician": 300.0},
        "isAvailableNow": True,
        "verified": False,
        "serviceRadiusKm": 5.0,
        "location": {"lat": 19.2825, "lng": 72.8570}
    })
    db.set_document("users", "worker_unverified_1", {
        "uid": "worker_unverified_1",
        "role": "worker"
    })
    headers = {"Authorization": "Bearer worker_unverified_1"}

    res = client.post("/offers", json={
        "jobId": "job_test_open",
        "workerId": "worker_unverified_1",
        "price": 300.0,
        "by": "worker"
    }, headers=headers)
    assert res.status_code == 400
    assert "unverified" in res.json().get("detail", "").lower()


def test_worker_cannot_offer_outside_skill(client, auth_worker_headers):
    """A worker cannot make an offer on a job requiring a skill they do not possess."""
    # Create plumbing job
    job = {
        "id": "job_plumbing_only",
        "customerId": "cust_test_1",
        "category": "plumber",
        "description": "Pipe leaking",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road"},
        "budget": 400.0,
        "status": "open",
        "createdAt": "2026-10-24T10:00:00Z"
    }
    db.set_document("jobs", "job_plumbing_only", job)

    # worker_elec_1 only has skill 'electrician'
    res = client.post("/offers", json={
        "jobId": "job_plumbing_only",
        "workerId": "worker_elec_1",
        "price": 400.0,
        "by": "worker"
    }, headers=auth_worker_headers)
    assert res.status_code == 400
    assert "skill" in res.json().get("detail", "").lower()


def test_worker_cannot_offer_outside_radius(client, auth_worker_headers):
    """A worker cannot make an offer on a job outside their service radius."""
    # Create job far away (~20 km)
    job = {
        "id": "job_far_away",
        "customerId": "cust_test_1",
        "category": "electrician",
        "description": "Far away electrical job",
        "location": {"lat": 19.1000, "lng": 72.8500, "address": "Andheri West"},
        "budget": 500.0,
        "status": "open",
        "createdAt": "2026-10-24T10:00:00Z"
    }
    db.set_document("jobs", "job_far_away", job)

    # worker_elec_1 is at Mira Road (19.2840, 72.8590) with 6 km radius
    res = client.post("/offers", json={
        "jobId": "job_far_away",
        "workerId": "worker_elec_1",
        "price": 500.0,
        "by": "worker"
    }, headers=auth_worker_headers)
    assert res.status_code == 400
    assert "radius" in res.json().get("detail", "").lower()


def test_get_offers_and_get_offer_by_id_privacy(client, auth_customer_headers, auth_customer_2_headers, auth_worker_headers, auth_worker_2_headers):
    """GET /offers and GET /offers/{id} only expose a user's own offers."""
    # Customer 1 creates an offer with Worker 1
    res = client.post("/offers", json={
        "jobId": "job_test_open",
        "workerId": "worker_elec_1",
        "price": 350.0,
        "by": "customer"
    }, headers=auth_customer_headers)
    assert res.status_code == 201
    offer_id = res.json()["id"]

    # Customer 1 can view
    r_c1 = client.get(f"/offers/{offer_id}", headers=auth_customer_headers)
    assert r_c1.status_code == 200

    r_c1_list = client.get("/offers?jobId=job_test_open", headers=auth_customer_headers)
    assert r_c1_list.status_code == 200
    assert len(r_c1_list.json()) >= 1

    # Worker 1 (involved) can view
    r_w1 = client.get(f"/offers/{offer_id}", headers=auth_worker_headers)
    assert r_w1.status_code == 200

    r_w1_list = client.get("/offers?jobId=job_test_open", headers=auth_worker_headers)
    assert r_w1_list.status_code == 200

    # Customer 2 (unrelated) gets 403
    r_c2 = client.get(f"/offers/{offer_id}", headers=auth_customer_2_headers)
    assert r_c2.status_code == 403

    r_c2_list = client.get("/offers?jobId=job_test_open", headers=auth_customer_2_headers)
    assert r_c2_list.status_code == 403

    # Worker 2 (unrelated) gets 403
    r_w2 = client.get(f"/offers/{offer_id}", headers=auth_worker_2_headers)
    assert r_w2.status_code == 403


def test_simultaneous_accepts_produce_exactly_one_accepted_offer(client, auth_customer_headers, auth_worker_headers, auth_worker_2_headers):
    """
    Two simultaneous accepts on competing offers for the same job produce
    exactly one accepted offer and one rejected/failed response.
    """
    from concurrent.futures import ThreadPoolExecutor

    # Create competing offers from worker 1 and worker 2
    res1 = client.post("/offers", json={
        "jobId": "job_test_open",
        "workerId": "worker_elec_1",
        "price": 400.0,
        "by": "worker"
    }, headers=auth_worker_headers)
    assert res1.status_code == 201
    offer1_id = res1.json()["id"]

    res2 = client.post("/offers", json={
        "jobId": "job_test_open",
        "workerId": "worker_elec_2",
        "price": 380.0,
        "by": "worker"
    }, headers=auth_worker_2_headers)
    assert res2.status_code == 201
    offer2_id = res2.json()["id"]

    def try_accept(off_id):
        return client.post(f"/offers/{off_id}/accept", headers=auth_customer_headers)

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(try_accept, offer1_id)
        f2 = executor.submit(try_accept, offer2_id)
        resp1 = f1.result()
        resp2 = f2.result()

    statuses = [resp1.status_code, resp2.status_code]
    # Exactly one should be 200, the other must be 400
    assert 200 in statuses, f"No accept succeeded: {statuses}"
    assert 400 in statuses, f"Expected one 400, got: {statuses}"

    # Verify database state has exactly one accepted offer
    job = db.get_document("jobs", "job_test_open")
    assert job["status"] == "accepted"
    off1 = db.get_document("offers", offer1_id)
    off2 = db.get_document("offers", offer2_id)
    accepted_count = sum(1 for o in [off1, off2] if o["status"] == "accepted")
    assert accepted_count == 1


def test_offer_service_404_and_400_edge_cases(client, auth_customer_headers, auth_worker_headers):
    """
    Covers remaining 404 / 400 branches in offer_service:
    - create_offer on unknown job -> 404
    - create_offer with unknown worker -> 404
    - counter_offer on unknown offer -> 404
    - reject_offer on unknown offer -> 404
    - get_offers_for_job on unknown job -> 404
    - get_offer_by_id on unknown offer -> 404
    """
    # 1. create_offer unknown job
    res1 = client.post("/offers", json={
        "jobId": "job_nonexistent_xyz",
        "workerId": "worker_elec_1",
        "price": 300.0,
        "by": "customer"
    }, headers=auth_customer_headers)
    assert res1.status_code == 404

    # 2. create_offer unknown worker (customer makes offer to unknown worker ID)
    # Seed a worker in users with role worker so worker auth works
    db.set_document("users", "worker_ghost", {"uid": "worker_ghost", "role": "worker"})
    res2 = client.post("/offers", json={
        "jobId": "job_test_open",
        "workerId": "worker_ghost",
        "price": 300.0,
        "by": "worker"
    }, headers={"Authorization": "Bearer worker_ghost"})
    assert res2.status_code == 404

    # 3. counter_offer unknown offer
    assert client.post("/offers/offer_nonexistent_xyz/counter", json={"price": 400.0}, headers=auth_worker_headers).status_code == 404

    # 4. reject_offer unknown offer
    assert client.post("/offers/offer_nonexistent_xyz/reject", headers=auth_customer_headers).status_code == 404

    # 5. get_offers_for_job unknown job
    assert client.get("/offers?jobId=job_nonexistent_xyz", headers=auth_customer_headers).status_code == 404

    # 6. get_offer_by_id unknown offer
    assert client.get("/offers/offer_nonexistent_xyz", headers=auth_customer_headers).status_code == 404


