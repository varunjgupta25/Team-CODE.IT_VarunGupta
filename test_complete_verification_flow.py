import sys
import time
import requests

BASE_URL = "http://127.0.0.1:8000/api"

def run_test():
    print("=" * 60)
    print("🚀 AUTOMATED END-TO-END VERIFICATION & SECURITY TEST")
    print("=" * 60)

    # Health check
    print("\n[STEP 1] Checking FastAPI backend health...")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"  --> Status: {r.status_code}, Response: {r.json()}")
        assert r.status_code == 200
    except Exception as e:
        print(f"  ❌ Backend unreachable: {e}")
        sys.exit(1)

    # 1. Register a brand-new worker dynamically
    new_worker_id = f"worker_test_{int(time.time())}"
    print(f"\n[STEP 2] Registering brand-new worker dynamically ({new_worker_id})...")
    payload = {
        "uid": new_worker_id,
        "name": "Sanjay Electrician",
        "phone": "+91 98765 43210",
        "skills": ["electrician"],
        "rates": {"electrician": 400.0},
        "location": {"lat": 19.2812, "lng": 72.8697, "address": "Mira Road East, Mumbai"}
    }
    r = requests.post(f"{BASE_URL}/workers/register", json=payload)
    print(f"  --> Status: {r.status_code}")
    data = r.json()
    print(f"  --> Worker Verified: {data.get('verified')}, VerificationStatus: {data.get('verificationStatus')}")
    assert r.status_code == 201
    assert data.get("verified") is False, "New worker MUST NOT be directly approved!"
    assert data.get("verificationStatus") == "unverified", "New worker status must be 'unverified'!"
    assert data.get("trustScore") == 60.0, "New worker trust score must be 60.0!"
    print("  ✅ PASS: New worker created as UNVERIFIED (not auto-approved)!")

    # 2. Check matching before verification
    print(f"\n[STEP 3] Verifying worker does NOT appear in match results before verification...")
    # Create an open job for electrician
    job_payload = {
        "customerId": "cust_priya",
        "category": "electrician",
        "description": "Short circuit in switchboard",
        "budget": 450.0,
        "mode": "on_demand",
        "location": {"lat": 19.2812, "lng": 72.8697, "address": "Mira Road East"}
    }
    cust_headers = {"Authorization": "Bearer token-customer-cust_priya"}
    r_job = requests.post(f"{BASE_URL}/jobs", json=job_payload, headers=cust_headers)
    assert r_job.status_code == 201, f"Failed to create job: {r_job.text}"
    job_id = r_job.json().get("id")
    print(f"  --> Created test job: {job_id}")

    # Query matches as customer
    cust_headers = {"Authorization": "Bearer token-customer-cust_priya"}
    r_match = requests.get(f"{BASE_URL}/workers/match?jobId={job_id}", headers=cust_headers)
    assert r_match.status_code == 200
    matched_ids = [m.get("worker", {}).get("uid") for m in r_match.json()]
    print(f"  --> Matched workers count: {len(matched_ids)}")
    assert new_worker_id not in matched_ids, f"Unverified worker {new_worker_id} must NOT be matched!"
    print("  ✅ PASS: Unverified worker excluded from customer matching!")

    # 3. Worker submits documentation
    print(f"\n[STEP 4] Worker submits Aadhaar document for verification...")
    worker_headers = {"Authorization": f"Bearer token-worker-{new_worker_id}"}
    verify_payload = {
        "documentType": "aadhaar",
        "documentNumber": "5555 4444 3333"
    }
    r_verify = requests.post(f"{BASE_URL}/workers/verify", json=verify_payload, headers=worker_headers)
    print(f"  --> Status: {r_verify.status_code}, Response: {r_verify.json()}")
    assert r_verify.status_code == 200
    assert r_verify.json().get("status") == "pending"
    print("  ✅ PASS: Worker document submitted, status changed to PENDING!")

    # 4. Check Admin Pending Queue
    print(f"\n[STEP 5] Checking Admin Pending Verifications Queue...")
    admin_headers = {"Authorization": "Bearer token-admin-admin_user"}
    r_pending = requests.get(f"{BASE_URL}/admin/verifications/pending", headers=admin_headers)
    print(f"  --> Status: {r_pending.status_code}")
    assert r_pending.status_code == 200
    pending_list = r_pending.json()
    pending_uids = [w.get("uid") for w in pending_list]
    print(f"  --> Pending worker UIDs in queue: {pending_uids}")
    assert new_worker_id in pending_uids, f"Worker {new_worker_id} must appear in Admin pending list!"
    print(f"  ✅ PASS: Worker {new_worker_id} is visible in Admin pending review queue!")

    # 5. Security check: Customer or Worker cannot approve
    print(f"\n[STEP 6] Security Check: Unauthorized user cannot approve verification...")
    r_sec = requests.post(f"{BASE_URL}/admin/verifications/{new_worker_id}/approve", headers=worker_headers)
    print(f"  --> Worker approval attempt status: {r_sec.status_code}")
    assert r_sec.status_code == 403, "Non-admin MUST receive 403 Forbidden!"
    print("  ✅ PASS: Role-based security strictly enforced (403 Forbidden for non-admins)!")

    # 6. Admin approves verification
    print(f"\n[STEP 7] Admin approves worker verification...")
    r_app = requests.post(f"{BASE_URL}/admin/verifications/{new_worker_id}/approve", headers=admin_headers)
    print(f"  --> Status: {r_app.status_code}, Response: {r_app.json()}")
    assert r_app.status_code == 200
    assert r_app.json().get("verified") is True
    print("  ✅ PASS: Admin successfully approved worker!")

    # 7. Check worker profile post-approval
    print(f"\n[STEP 8] Worker profile verification check post-approval...")
    r_w = requests.get(f"{BASE_URL}/workers/{new_worker_id}", headers=worker_headers)
    w_data = r_w.json()
    print(f"  --> Worker Verified: {w_data.get('verified')}, Status: {w_data.get('verificationStatus')}")
    assert w_data.get("verified") is True, "Worker must now be verified!"
    assert w_data.get("verificationStatus") == "approved", "Worker status must now be 'approved'!"
    print("  ✅ PASS: Worker profile confirms verified: true and status: approved!")

    # 8. Check worker now matches for jobs
    print(f"\n[STEP 9] Verifying worker NOW appears in customer matching results...")
    r_match2 = requests.get(f"{BASE_URL}/workers/match?jobId={job_id}", headers=cust_headers)
    matched_ids2 = [m.get("worker", {}).get("uid") for m in r_match2.json()]
    print(f"  --> Matched worker UIDs: {matched_ids2}")
    assert new_worker_id in matched_ids2, f"Approved worker {new_worker_id} must now match for job!"
    print("  ✅ PASS: Approved worker now successfully appears in matching!")

    # 9. Test Seeded Unverified Worker (Kamlesh Verma)
    print(f"\n[STEP 10] Testing Seeded Unverified Worker 'worker_plumber_unverified'...")
    kw_headers = {"Authorization": "Bearer token-worker-worker_plumber_unverified"}
    r_kw = requests.get(f"{BASE_URL}/workers/worker_plumber_unverified", headers=kw_headers)
    kw_data = r_kw.json()
    print(f"  --> Kamlesh initial state: verified={kw_data.get('verified')}, status={kw_data.get('verificationStatus')}")
    assert kw_data.get("verified") is False, "Kamlesh must start unverified!"

    # Kamlesh submits Aadhaar
    r_kw_sub = requests.post(
        f"{BASE_URL}/workers/verify",
        json={"documentType": "aadhaar", "documentNumber": "1234 5678 9012"},
        headers=kw_headers
    )
    assert r_kw_sub.status_code == 200
    print("  --> Kamlesh document submitted: status=pending")

    # Admin approves Kamlesh
    r_kw_app = requests.post(f"{BASE_URL}/admin/verifications/worker_plumber_unverified/approve", headers=admin_headers)
    assert r_kw_app.status_code == 200
    print(f"  --> Kamlesh approved by admin: verified={r_kw_app.json().get('verified')}")

    # Verify Kamlesh is now verified
    r_kw2 = requests.get(f"{BASE_URL}/workers/worker_plumber_unverified", headers=kw_headers)
    assert r_kw2.json().get("verified") is True
    print("  ✅ PASS: Seeded unverified worker flow fully functional!")

    print("\n" + "=" * 60)
    print("🎉 ALL 10/10 VERIFICATION & MATCHING TESTS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_test()
