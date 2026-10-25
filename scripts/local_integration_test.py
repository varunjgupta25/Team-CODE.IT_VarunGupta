import sys
from fastapi.testclient import TestClient
from main import app
from seed import seed_database

def test_full_live_system_flow():
    print("=" * 60)
    print("REPAIRBUDDY FRONTEND-TO-BACKEND INTEGRATION TEST")
    print("=" * 60)

    # 1. Fresh Database Seeding
    print("[1] Seeding database...")
    seed_database()

    client = TestClient(app)

    # 2. System Health Check
    print("\n[2] Testing Health Endpoint (/api/health)...")
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print(f"    Health Status: {res.json()['status']} ({res.json()['service']})")

    # 3. Customer Token Simulation (as sent by frontend apiClient)
    # Frontend sends Authorization: Bearer token-customer-cust_priya
    customer_headers = {"Authorization": "Bearer token-customer-cust_priya"}
    worker_headers = {"Authorization": "Bearer token-worker-worker_elec_1"}

    # 4. Customer Creates a Job Request
    print("\n[3] Customer posts job (/api/jobs)...")
    job_payload = {
        "category": "electrician",
        "description": "Ceiling fan sparking and switchboard loose in living room",
        "location": {
            "lat": 19.2825,
            "lng": 72.8570,
            "address": "Flat 402, Beverly Park, Mira Road East, Mumbai"
        },
        "budget": 450.0,
        "mode": "on-demand"
    }
    res = client.post("/api/jobs", json=job_payload, headers=customer_headers)
    assert res.status_code == 201, f"Create job failed: {res.text}"
    job = res.json()
    job_id = job["id"]
    print(f"    Job Created: ID={job_id}, status={job['status']}, budget=Rs.{job['budget']}")

    # 5. Worker Matching & Ranking
    print("\n[4] Querying matched workers (/api/workers/match?jobId=)...")
    res = client.get(f"/api/workers/match?jobId={job_id}", headers=customer_headers)
    assert res.status_code == 200, f"Match workers failed: {res.text}"
    matched_workers = res.json()
    print(f"    Matched Verified Workers Count: {len(matched_workers)}")
    assert len(matched_workers) > 0, "No workers matched!"
    for m in matched_workers:
        print(f"     -> {m['worker']['name']}: dist={m['distanceKm']}km, ETA={m['etaMinutes']}m, within30={m['within30']}, badge={m['trustBadge']}")

    top_worker = matched_workers[0]["worker"]
    worker_id = top_worker["uid"]

    # 6. Customer Sends Offer
    print(f"\n[5] Customer sends offer of Rs.400 to {top_worker['name']} (/api/offers)...")
    offer_payload = {
        "jobId": job_id,
        "workerId": worker_id,
        "price": 400.0,
        "by": "customer"
    }
    res = client.post("/api/offers", json=offer_payload, headers=customer_headers)
    assert res.status_code == 201, f"Create offer failed: {res.text}"
    offer = res.json()
    offer_id = offer["id"]
    print(f"    Offer Created: ID={offer_id}, price=Rs.{offer['price']}, status={offer['status']}")

    # 7. Worker Counters the Offer
    worker_specific_headers = {"Authorization": f"Bearer token-worker-{worker_id}"}
    print(f"\n[6] Worker counters offer to Rs.450 (/api/offers/{offer_id}/counter)...")
    counter_payload = {
        "price": 450.0,
        "by": "worker"
    }
    res = client.post(f"/api/offers/{offer_id}/counter", json=counter_payload, headers=worker_specific_headers)
    assert res.status_code == 200, f"Counter offer failed: {res.text}"
    countered = res.json()
    new_offer_id = countered["id"]
    print(f"    Counter Offer Created: ID={new_offer_id}, price=Rs.{countered['price']}")

    # 8. Customer Accepts Counter Offer
    print(f"\n[7] Customer accepts counter offer (/api/offers/{new_offer_id}/accept)...")
    res = client.post(f"/api/offers/{new_offer_id}/accept", headers=customer_headers)
    assert res.status_code == 200, f"Accept offer failed: {res.text}"
    accepted = res.json()
    print(f"    Offer Accepted! Status: {accepted['status']}")

    # 9. Verify Job Status is now 'accepted'
    res = client.get(f"/api/jobs/{job_id}", headers=customer_headers)
    assert res.status_code == 200
    job_details = res.json()
    assert job_details["status"] == "accepted"
    assert job_details["finalPrice"] == 450.0
    print(f"    Job Status Verified: status={job_details['status']}, finalPrice=Rs.{job_details['finalPrice']}, worker={job_details['acceptedWorkerId']}")

    # 10. Worker Starts Job
    print(f"\n[8] Worker starts job (/api/jobs/{job_id}/start)...")
    res = client.post(f"/api/jobs/{job_id}/start", headers=worker_specific_headers)
    assert res.status_code == 200, f"Start job failed: {res.text}"
    assert res.json()["status"] == "in_progress"
    print(f"    Job in progress!")

    # 11. Worker Completes Job
    print(f"\n[9] Worker completes job (/api/jobs/{job_id}/complete)...")
    res = client.post(f"/api/jobs/{job_id}/complete", headers=worker_specific_headers)
    assert res.status_code == 200, f"Complete job failed: {res.text}"
    assert res.json()["status"] == "completed"
    print(f"    Job marked completed!")

    # 12. Customer Submits Review
    print(f"\n[10] Customer leaves 5-star review (/api/reviews)...")
    review_payload = {
        "jobId": job_id,
        "workerId": worker_id,
        "rating": 5,
        "comment": "Quick arrival under 15 minutes, excellent work!"
    }
    res = client.post("/api/reviews", json=review_payload, headers=customer_headers)
    assert res.status_code == 201, f"Review failed: {res.text}"
    print(f"    Review submitted successfully: ID={res.json()['id']}")

    # 13. Trigger SOS Alert
    print(f"\n[11] Triggering emergency SOS alert (/api/sos)...")
    sos_payload = {
        "jobId": job_id,
        "location": {
            "lat": 19.2825,
            "lng": 72.8570
        }
    }
    res = client.post("/api/sos", json=sos_payload, headers=customer_headers)
    assert res.status_code == 201, f"SOS failed: {res.text}"
    print(f"    Emergency SOS Recorded: ID={res.json()['id']}")

    # 14. Worker Availability Toggle (PATCH /api/workers/{id})
    print(f"\n[12] Worker toggles availability (/api/workers/{worker_id})...")
    res = client.patch(f"/api/workers/{worker_id}", json={"isAvailableNow": False}, headers=worker_specific_headers)
    assert res.status_code == 200, f"Toggle availability failed: {res.text}"
    print(f"    Worker availability toggled: isAvailableNow={res.json()['isAvailableNow']}")

    print("\n" + "=" * 60)
    print("ALL INTEGRATION CHECKS PASSED: SYSTEM IS 100% TESTING READY!")
    print("=" * 60)

if __name__ == "__main__":
    test_full_live_system_flow()
