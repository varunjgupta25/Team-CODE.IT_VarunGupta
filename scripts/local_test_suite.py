import os
import sys
import warnings
warnings.filterwarnings("ignore")

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from seed import seed_database
from core.database import db

client = TestClient(app)


def run_checks():
    print("\n================== REPAIRBUDDY TEST SUITE ==================")
    seed_database()

    # 1. Test Health
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] Health endpoint working.")

    # 2. Test Criterion 1: /workers/match
    # Plumber job: job_seed_plumber_open (customer: cust_priya, category: plumber, budget: 400)
    auth_customer = {"Authorization": "Bearer cust_priya"}
    res = client.get("/workers/match?jobId=job_seed_plumber_open", headers=auth_customer)
    assert res.status_code == 200, f"Match failed: {res.text}"
    matches = res.json()
    print(f"[CHECK] Matched workers count: {len(matches)}")
    assert len(matches) > 0, "No workers matched"

    for m in matches:
        w = m["worker"]
        # Must be verified
        assert w["verified"] is True, f"Unverified worker matched! {w['uid']}"
        # Must be available
        assert w["isAvailableNow"] is True, f"Unavailable worker matched! {w['uid']}"
        # Must have plumber skill
        assert "plumber" in [s.lower() for s in w["skills"]], f"Worker without skill matched! {w['uid']}"
        # Must be within service radius
        assert m["distanceKm"] <= w["serviceRadiusKm"], f"Worker outside radius matched! {m['distanceKm']} > {w['serviceRadiusKm']}"
        # Must have etaMinutes and within30
        assert "etaMinutes" in m, "Missing etaMinutes"
        assert "within30" in m, "Missing within30"
        assert "score" in m, "Missing score"
        print(f"   -> {w['name']}: dist={m['distanceKm']}km, ETA={m['etaMinutes']}m, within30={m['within30']}, score={m['score']}, badge={m['trustBadge']}")

    # Verify unverified workers were excluded
    matched_uids = [m["worker"]["uid"] for m in matches]
    assert "worker_plumber_unverified" not in matched_uids, "FAIL: Unverified plumber appeared in matching!"
    print("[PASS] Criterion 1 (/workers/match filtering & ranking) verified.")

    # 3. Test POST /jobs
    new_job_payload = {
        "category": "electrician",
        "description": "Fan regulator replacement in hall",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Beverly Park, Mira Road"},
        "budget": 350.0
    }
    res = client.post("/jobs", json=new_job_payload, headers=auth_customer)
    assert res.status_code == 201, f"Create job failed: {res.text}"
    created_job = res.json()
    new_job_id = created_job["id"]
    print(f"[PASS] POST /jobs created job: {new_job_id}")

    # 4. Test GET /jobs/{id}
    res = client.get(f"/jobs/{new_job_id}", headers=auth_customer)
    assert res.status_code == 200
    assert res.json()["status"] == "open"
    print(f"[PASS] GET /jobs/{new_job_id} working.")

    # 5. Test GET /jobs/nearby (Worker feed)
    auth_electrician = {"Authorization": "Bearer worker_elec_1"}
    res = client.get("/jobs/nearby", headers=auth_electrician)
    assert res.status_code == 200, f"Nearby jobs failed: {res.text}"
    nearby = res.json()
    print(f"[PASS] GET /jobs/nearby returned {len(nearby)} open electrician jobs.")

    # 6. Test Criterion 2: Offer flow and Turn enforcement
    # Customer makes offer 300 to worker_elec_1
    offer_payload = {
        "jobId": new_job_id,
        "workerId": "worker_elec_1",
        "price": 300.0,
        "by": "customer"
    }
    res = client.post("/offers", json=offer_payload, headers=auth_customer)
    assert res.status_code == 201, f"Make offer failed: {res.text}"
    offer1 = res.json()
    offer1_id = offer1["id"]
    print(f"[PASS] POST /offers created offer: {offer1_id} for Rs.{offer1['price']}")

    # Check job transitioned to 'negotiating'
    res = client.get(f"/jobs/{new_job_id}", headers=auth_customer)
    assert res.json()["status"] == "negotiating", "Job should be 'negotiating'"

    # Turn test: Customer tries to counter own offer -> MUST FAIL with 400
    res = client.post(f"/offers/{offer1_id}/counter", json={"price": 320.0}, headers=auth_customer)
    assert res.status_code == 400, f"Turn enforcement failed! Expected 400, got: {res.status_code}"
    print(f"[PASS] Turn enforcement check 1 passed: Customer cannot counter own offer -> '{res.json().get('detail')}'")

    # Worker counters offer to 450 -> MUST SUCCEED
    res = client.post(f"/offers/{offer1_id}/counter", json={"price": 450.0}, headers=auth_electrician)
    assert res.status_code == 200, f"Worker counter failed: {res.text}"
    offer2 = res.json()
    offer2_id = offer2["id"]
    print(f"[PASS] Worker countered successfully with new offer {offer2_id} at Rs.{offer2['price']}")

    # Turn test: Worker tries to counter worker's own counter -> MUST FAIL with 400
    res = client.post(f"/offers/{offer2_id}/counter", json={"price": 475.0}, headers=auth_electrician)
    assert res.status_code == 400, "Worker countered own offer without waiting for customer!"
    print(f"[PASS] Turn enforcement check 2 passed: Worker cannot counter own offer -> '{res.json().get('detail')}'")

    # Seed competing offer on the same job from worker_elec_2
    auth_elec2 = {"Authorization": "Bearer worker_elec_2"}
    res = client.post("/offers", json={"jobId": new_job_id, "workerId": "worker_elec_2", "price": 400.0, "by": "worker"}, headers=auth_elec2)
    assert res.status_code == 201
    competing_offer_id = res.json()["id"]

    # Customer accepts worker 1's counter offer
    res = client.post(f"/offers/{offer2_id}/accept", headers=auth_customer)
    assert res.status_code == 200, f"Accept offer failed: {res.text}"
    accepted_offer = res.json()
    assert accepted_offer["status"] == "accepted"

    # Verify job state after accept: acceptedWorkerId, finalPrice, status=accepted
    res = client.get(f"/jobs/{new_job_id}", headers=auth_customer)
    job_after_accept = res.json()
    assert job_after_accept["status"] == "accepted", f"Job status is {job_after_accept['status']}, expected 'accepted'"
    assert job_after_accept["acceptedWorkerId"] == "worker_elec_1"
    assert job_after_accept["finalPrice"] == 450.0
    print("[PASS] Job updated: status=accepted, worker=worker_elec_1, price=450.0")

    # Verify auto-rejection: competing offer must now be 'rejected'
    competing_in_db = db.get_document("offers", competing_offer_id)
    assert competing_in_db["status"] == "rejected", f"Competing offer was not auto-rejected: {competing_in_db['status']}"
    print(f"[PASS] Competing offer {competing_offer_id} was automatically rejected.")

    # 7. Test Criterion 3: Invalid state transitions
    # Cannot complete a job that is only in 'accepted' status (not started yet)
    res = client.post(f"/jobs/{new_job_id}/complete", headers=auth_electrician)
    assert res.status_code == 400, f"Expected 400 completing unstarted job, got: {res.status_code}"
    print(f"[PASS] Invalid transition rejected: {res.json().get('detail')}")

    # Start job successfully
    res = client.post(f"/jobs/{new_job_id}/start", headers=auth_electrician)
    assert res.status_code == 200, f"Start job failed: {res.text}"
    assert res.json()["status"] == "in_progress"
    print(f"[PASS] Job {new_job_id} transitioned to 'in_progress'")

    # Cannot start again while in_progress
    res = client.post(f"/jobs/{new_job_id}/start", headers=auth_electrician)
    assert res.status_code == 400
    print(f"[PASS] Cannot re-start in-progress job: {res.json().get('detail')}")

    # Complete job successfully
    res = client.post(f"/jobs/{new_job_id}/complete", headers=auth_electrician)
    assert res.status_code == 200, f"Complete job failed: {res.text}"
    assert res.json()["status"] == "completed"
    print(f"[PASS] Job {new_job_id} completed successfully.")

    # 8. Test Criterion 4: Review submission & rolling average rating
    worker_before_review = db.get_document("workers", "worker_elec_1")
    old_rating = worker_before_review["rating"]
    print(f"[INFO] Worker elec_1 rating before review: {old_rating}")

    review_payload = {
        "jobId": new_job_id,
        "workerId": "worker_elec_1",
        "rating": 5.0,
        "comment": "Quick service, arrived in 15 minutes and fixed the regulator perfectly!"
    }
    res = client.post("/reviews", json=review_payload, headers=auth_customer)
    assert res.status_code == 201, f"Review failed: {res.text}"
    review_res = res.json()
    print(f"[PASS] POST /reviews submitted: {review_res['id']}")

    worker_after_review = db.get_document("workers", "worker_elec_1")
    new_rating = worker_after_review["rating"]
    print(f"[PASS] Worker rolling average updated: {old_rating} -> {new_rating}")

    # Reviewing non-completed or duplicate must return 400
    res = client.post("/reviews", json=review_payload, headers=auth_customer)
    assert res.status_code == 400, "Duplicate review was allowed!"
    print(f"[PASS] Duplicate review blocked: {res.json().get('detail')}")

    # 9. Test POST /sos
    sos_payload = {
        "jobId": new_job_id,
        "location": {"lat": 19.2825, "lng": 72.8570}
    }
    res = client.post("/sos", json=sos_payload, headers=auth_customer)
    assert res.status_code == 201, f"SOS failed: {res.text}"
    sos_res = res.json()
    assert sos_res["status"] == "recorded"
    print(f"[PASS] POST /sos triggered and recorded alert ID: {sos_res['id']}")

    print("\n================ ALL SUCCESS CRITERIA PASSED! ================\n")


if __name__ == "__main__":
    run_checks()
