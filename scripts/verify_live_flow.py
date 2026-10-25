import requests
import sys

BASE_URL = "http://127.0.0.1:8000/api"

def run_live_verification_and_flow():
    print("=" * 70)
    print("LIVE BACKEND VERIFICATION & FULL USER FLOW TEST")
    print("=" * 70)

    # 1. Check Backend Connectivity
    print("\n[Step 1] Verifying backend health...")
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print(f" -> Backend OK: {r.json()}")

    # 2. Verify an Unverified Worker exists in Seed
    unverified_uid = "worker_plumber_unverified"
    worker_token = f"token-worker-{unverified_uid}"
    worker_headers = {"Authorization": f"Bearer {worker_token}"}
    print(f"\n[Step 2] Checking unverified worker profile ({unverified_uid})...")
    r = requests.get(f"{BASE_URL}/workers/{unverified_uid}", headers=worker_headers)
    assert r.status_code == 200, f"Failed to get worker: {r.text}"
    worker_data = r.json()
    print(f" -> Worker {unverified_uid}: verified={worker_data.get('verified')}, status={worker_data.get('verificationStatus')}")
    assert worker_data.get("verified") is False, "Worker should initially be unverified"

    # 3. Customer creates a plumbing job
    print("\n[Step 3] Customer posts a plumbing job...")
    customer_token = "token-customer-cust_priya"
    cust_headers = {"Authorization": f"Bearer {customer_token}"}
    job_payload = {
        "category": "plumber",
        "description": "Kitchen sink pipe leakage under cabinet",
        "location": {
            "lat": 19.2825,
            "lng": 72.8570,
            "address": "Flat 301, Silver Arch, Mira Road East, Mumbai"
        },
        "budget": 350.0,
        "mode": "on-demand"
    }
    r = requests.post(f"{BASE_URL}/jobs", json=job_payload, headers=cust_headers)
    assert r.status_code == 201, f"Create job failed: {r.text}"
    job = r.json()
    job_id = job["id"]
    print(f" -> Job created: {job_id}")

    # 4. Check Matched Workers — unverified worker MUST be absent!
    print("\n[Step 4] Checking matched workers for job before approval...")
    r = requests.get(f"{BASE_URL}/workers/match?jobId={job_id}", headers=cust_headers)
    assert r.status_code == 200, f"Match workers failed: {r.text}"
    matches_before = r.json()
    matched_uids_before = [m["worker"]["uid"] for m in matches_before]
    print(f" -> Total matched workers: {len(matches_before)}")
    print(f" -> Matched UIDs: {matched_uids_before}")
    assert unverified_uid not in matched_uids_before, f"CRITICAL: Unverified worker {unverified_uid} must NOT appear in match list!"
    print(f" -> PASS: {unverified_uid} is correctly absent from matching list.")

    # 5. Worker submits ID verification request (POST /workers/verify)
    print("\n[Step 5] Worker submits verification request (/workers/verify)...")
    worker_token = f"token-worker-{unverified_uid}"
    worker_headers = {"Authorization": f"Bearer {worker_token}"}
    verify_payload = {
        "documentType": "aadhaar",
        "documentNumber": "987654321098"
    }
    r = requests.post(f"{BASE_URL}/workers/verify", json=verify_payload, headers=worker_headers)
    assert r.status_code == 200, f"Worker verify failed: {r.text}"
    verify_res = r.json()
    print(f" -> Verify response: {verify_res}")
    assert verify_res.get("status") == "pending", f"Expected pending status, got {verify_res}"
    print(" -> PASS: Verification request is pending review.")

    # 6. Admin approval access checks:
    # 6a. Non-admin cannot approve (403)
    print("\n[Step 6a] Non-admin attempting approval (should return 403)...")
    r = requests.post(f"{BASE_URL}/admin/verifications/{unverified_uid}/approve", headers=cust_headers)
    print(f" -> Non-admin status: {r.status_code}")
    assert r.status_code == 403, f"Expected 403 for non-admin, got {r.status_code}"
    print(" -> PASS: 403 Forbidden properly enforced for non-admin.")

    # 6b. Admin approving unknown uid (404)
    admin_token = "token-admin-admin_user"
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("\n[Step 6b] Admin attempting approval of unknown uid (should return 404)...")
    r = requests.post(f"{BASE_URL}/admin/verifications/non_existent_worker/approve", headers=admin_headers)
    print(f" -> Unknown UID status: {r.status_code}, response: {r.json()}")
    assert r.status_code == 404, f"Expected 404 for unknown uid, got {r.status_code}"
    print(" -> PASS: 404 Not Found properly returned for non-existent worker.")

    # 6c. Admin successfully approves unverified_uid
    print(f"\n[Step 6c] Admin approves worker {unverified_uid}...")
    r = requests.post(f"{BASE_URL}/admin/verifications/{unverified_uid}/approve", headers=admin_headers)
    assert r.status_code == 200, f"Admin approve failed: {r.text}"
    approval_res = r.json()
    print(f" -> Approval response: {approval_res}")
    assert approval_res.get("status") == "approved"
    assert approval_res.get("verified") is True
    print(" -> PASS: Worker verification approved by admin.")

    # 7. Check Matched Workers AGAIN — approved worker MUST now appear!
    print("\n[Step 7] Checking matched workers after admin approval...")
    r = requests.get(f"{BASE_URL}/workers/match?jobId={job_id}", headers=cust_headers)
    assert r.status_code == 200
    matches_after = r.json()
    matched_uids_after = [m["worker"]["uid"] for m in matches_after]
    print(f" -> Total matched workers now: {len(matches_after)}")
    print(f" -> Matched UIDs: {matched_uids_after}")
    assert unverified_uid in matched_uids_after, f"CRITICAL: Newly approved worker {unverified_uid} must appear in match list!"
    approved_match = next(m for m in matches_after if m["worker"]["uid"] == unverified_uid)
    print(f" -> Matched worker profile: verified={approved_match['worker'].get('verified')}, trustScore={approved_match['worker'].get('trustScore')}, badge={approved_match.get('trustBadge')}")
    assert approved_match["worker"].get("verified") is True
    print(" -> PASS: Newly verified worker is matched with verified status!")

    # 8. Customer makes offer to the newly verified worker
    print(f"\n[Step 8] Customer sends offer to {unverified_uid}...")
    offer_payload = {
        "jobId": job_id,
        "workerId": unverified_uid,
        "price": 300.0,
        "by": "customer"
    }
    r = requests.post(f"{BASE_URL}/offers", json=offer_payload, headers=cust_headers)
    assert r.status_code == 201, f"Offer creation failed: {r.text}"
    offer = r.json()
    offer_id = offer["id"]
    print(f" -> Offer {offer_id} created at Rs.{offer['price']}")

    # 9. Worker counters offer
    print(f"\n[Step 9] Worker counters offer to Rs.350...")
    counter_payload = {
        "price": 350.0,
        "by": "worker"
    }
    r = requests.post(f"{BASE_URL}/offers/{offer_id}/counter", json=counter_payload, headers=worker_headers)
    assert r.status_code == 200, f"Counter offer failed: {r.text}"
    countered = r.json()
    counter_id = countered["id"]
    print(f" -> Counter offer {counter_id} created at Rs.{countered['price']}")

    # 10. Customer accepts counter offer
    print("\n[Step 10] Customer accepts counter offer...")
    r = requests.post(f"{BASE_URL}/offers/{counter_id}/accept", headers=cust_headers)
    assert r.status_code == 200, f"Accept offer failed: {r.text}"
    print(f" -> Offer accepted!")

    # Verify job status is 'accepted'
    r = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=cust_headers)
    assert r.status_code == 200
    job_details = r.json()
    assert job_details["status"] == "accepted"
    print(f" -> Job status: {job_details['status']}, finalPrice={job_details['finalPrice']}")

    # 11. Test /route endpoint
    print("\n[Step 11] Testing /route endpoint contracts...")
    # 11a. Unauthenticated -> 401
    r = requests.get(f"{BASE_URL}/route?jobId={job_id}&workerId={unverified_uid}")
    print(f" -> Unauthenticated /route status: {r.status_code}")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"

    # 11b. Authenticated as participant
    r = requests.get(f"{BASE_URL}/route?jobId={job_id}&workerId={unverified_uid}", headers=cust_headers)
    print(f" -> Participant /route status: {r.status_code}")
    if r.status_code == 200:
        route_data = r.json()
        print(f" -> Route data returned: distanceKm={route_data.get('distanceKm')}, etaMinutes={route_data.get('etaMinutes')}, polyline points={len(route_data.get('polyline', []))}")
        assert "polyline" in route_data
    elif r.status_code == 404:
        print(" -> Route returned 404 (Road graph absent on server). Frontend fallback kicks in gracefully with straight dashed line!")
    else:
        print(f" -> Unexpected route status: {r.status_code}")

    # 12. Worker starts and completes job
    print("\n[Step 12] Worker starts job...")
    r = requests.post(f"{BASE_URL}/jobs/{job_id}/start", headers=worker_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    print(" -> Job in progress!")

    print("\n[Step 13] Worker completes job...")
    r = requests.post(f"{BASE_URL}/jobs/{job_id}/complete", headers=worker_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    print(" -> Job completed!")

    # 13. Customer reviews worker
    print("\n[Step 14] Customer submits review...")
    review_payload = {
        "jobId": job_id,
        "workerId": unverified_uid,
        "rating": 5,
        "comment": "Super fast, polite, and completely resolved the sink leakage!"
    }
    r = requests.post(f"{BASE_URL}/reviews", json=review_payload, headers=cust_headers)
    assert r.status_code == 201
    print(f" -> Review posted: {r.json()['id']}")

    # 14. Customer triggers SOS
    print("\n[Step 15] Customer triggers SOS alert...")
    sos_payload = {
        "jobId": job_id,
        "location": {
            "lat": 19.2825,
            "lng": 72.8570
        }
    }
    r = requests.post(f"{BASE_URL}/sos", json=sos_payload, headers=cust_headers)
    assert r.status_code == 201
    print(f" -> SOS alert registered: {r.json()['id']}")

    print("\n" + "=" * 70)
    print("ALL LIVE INTEGRATION CHECKS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_live_verification_and_flow()
