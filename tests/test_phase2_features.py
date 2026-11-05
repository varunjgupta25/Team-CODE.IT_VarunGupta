import pytest
from core.database import db
from services.admin_service import get_dashboard_stats, list_all_users, suspend_user, reactivate_user
from services.customer_service import get_customer_profile, update_customer_profile, get_current_user_profile
from services.report_service import list_reports, get_report, resolve_report, dismiss_report, create_report
from models.report import ReportCreate


# ==============================================================================
# Customer Profile & /users/me Unit Tests
# ==============================================================================

def test_customer_profile_retrieval_and_masking():
    db.set_document("users", "cust_alice", {
        "uid": "cust_alice",
        "name": "Alice Customer",
        "role": "customer",
        "phone": "+91 98201 11222",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road"}
    })

    # Owner requester sees full phone number
    owner_req = {"uid": "cust_alice", "role": "customer"}
    profile = get_customer_profile("cust_alice", requester=owner_req)
    assert profile["phone"] == "+91 98201 11222"
    assert profile["name"] == "Alice Customer"

    # Non-owner requester gets masked phone number
    other_req = {"uid": "cust_bob", "role": "customer"}
    masked_profile = get_customer_profile("cust_alice", requester=other_req)
    assert masked_profile["phone"] != "+91 98201 11222"
    assert "*****" in masked_profile["phone"]


def test_customer_profile_update_and_ownership():
    db.set_document("users", "cust_bob", {
        "uid": "cust_bob",
        "name": "Bob Old Name",
        "role": "customer",
        "phone": "+91 98202 22333"
    })

    owner_req = {"uid": "cust_bob", "role": "customer"}
    updated = update_customer_profile("cust_bob", {"name": "Bob Updated"}, requester=owner_req)
    assert updated["name"] == "Bob Updated"

    doc = db.get_document("users", "cust_bob")
    assert doc["name"] == "Bob Updated"

    # Non-owner cannot update -> raises 403
    intruder_req = {"uid": "cust_charlie", "role": "customer"}
    with pytest.raises(Exception) as exc_info:
        update_customer_profile("cust_bob", {"name": "Hacked"}, requester=intruder_req)
    assert "403" in str(exc_info.value) or "permission" in str(exc_info.value).lower()


def test_current_user_profile_resolver():
    # Customer
    db.set_document("users", "cust_dave", {
        "uid": "cust_dave",
        "name": "Dave",
        "role": "customer",
        "phone": "+91 98203 33444"
    })
    c_prof = get_current_user_profile({"uid": "cust_dave", "role": "customer"})
    assert c_prof["uid"] == "cust_dave"
    assert c_prof["role"] == "customer"

    # Worker
    db.set_document("workers", "worker_eva", {
        "uid": "worker_eva",
        "name": "Eva Electrician",
        "skills": ["electrician"],
        "rates": {"electrician": 500.0},
        "verified": True
    })
    w_prof = get_current_user_profile({"uid": "worker_eva", "role": "worker"})
    assert w_prof["uid"] == "worker_eva"
    assert w_prof["role"] == "worker"
    assert w_prof["verified"] is True
    assert "electrician" in w_prof["skills"]


# ==============================================================================
# Admin Dashboard Stats Tests
# ==============================================================================

def test_admin_dashboard_stats_aggregation():
    # Seed known counts
    db.set_document("users", "u_test_cust_1", {"uid": "u_test_cust_1", "role": "customer"})
    db.set_document("users", "u_test_cust_2", {"uid": "u_test_cust_2", "role": "customer"})
    db.set_document("workers", "w_test_1", {"uid": "w_test_1", "verified": True})
    db.set_document("workers", "w_test_2", {"uid": "w_test_2", "verified": False})
    db.set_document("jobs", "j_test_open", {"id": "j_test_open", "status": "open"})
    db.set_document("jobs", "j_test_done", {"id": "j_test_done", "status": "completed"})

    stats = get_dashboard_stats()
    assert "totalCustomers" in stats
    assert "totalWorkers" in stats
    assert "verifiedWorkers" in stats
    assert "pendingVerifications" in stats
    assert "activeJobs" in stats
    assert "completedJobs" in stats
    assert "reports" in stats
    assert stats["totalWorkers"] >= 2
    assert stats["completedJobs"] >= 1


# ==============================================================================
# Admin User Management Tests
# ==============================================================================

def test_admin_user_listing_and_suspension():
    db.set_document("users", "cust_to_suspend", {
        "uid": "cust_to_suspend",
        "name": "Bad Customer",
        "role": "customer",
        "phone": "+91 99999 11111"
    })
    db.set_document("workers", "worker_to_suspend", {
        "uid": "worker_to_suspend",
        "name": "Bad Worker",
        "isAvailableNow": True,
        "isFlagged": False
    })

    # Listing
    user_list = list_all_users(role="customer")
    assert any(u["uid"] == "cust_to_suspend" for u in user_list)

    # Suspension
    sus_res = suspend_user("worker_to_suspend", reason="Repeated no-shows")
    assert sus_res["accountStatus"] == "SUSPENDED"

    w_doc = db.get_document("workers", "worker_to_suspend")
    assert w_doc["accountStatus"] == "SUSPENDED"
    assert w_doc["isAvailableNow"] is False
    assert w_doc["isFlagged"] is True

    # Reactivation
    react_res = reactivate_user("worker_to_suspend")
    assert react_res["accountStatus"] == "ACTIVE"
    w_doc2 = db.get_document("workers", "worker_to_suspend")
    assert w_doc2["accountStatus"] == "ACTIVE"
    assert w_doc2["isFlagged"] is False


# ==============================================================================
# Admin Report Moderation Tests
# ==============================================================================

def test_report_listing_resolution_dismissal():
    db.set_document("workers", "w_reported", {"uid": "w_reported", "name": "Reported Worker"})
    rep1 = create_report(
        ReportCreate(workerId="w_reported", reason="Late arrival", category="no_show"),
        reporter_id="cust_reporter"
    )
    rep2 = create_report(
        ReportCreate(workerId="w_reported", reason="Spam messages", category="spam"),
        reporter_id="cust_reporter"
    )

    all_reps = list_reports()
    assert len(all_reps) >= 2

    # Get single report
    fetched = get_report(rep1["id"])
    assert fetched["id"] == rep1["id"]
    assert fetched["status"] == "pending"

    # Resolve report
    resolved = resolve_report(rep1["id"], action="Contacted worker with formal warning")
    assert resolved["status"] == "resolved"
    assert resolved["actionTaken"] == "Contacted worker with formal warning"

    # Dismiss report
    dismissed = dismiss_report(rep2["id"])
    assert dismissed["status"] == "dismissed"


# ==============================================================================
# Worker Earnings & Profile Update Tests
# ==============================================================================

def test_worker_earnings_calculation():
    from routers.workers import api_get_worker_earnings

    db.set_document("workers", "w_earn_calc", {
        "uid": "w_earn_calc",
        "name": "Earnings Specialist",
        "skills": ["electrician"],
        "rates": {"electrician": 400.0}
    })

    db.set_document("jobs", "j_earn_a", {
        "id": "j_earn_a",
        "acceptedWorkerId": "w_earn_calc",
        "status": "completed",
        "finalPrice": 500.0,
        "category": "electrician"
    })
    db.set_document("jobs", "j_earn_b", {
        "id": "j_earn_b",
        "acceptedWorkerId": "w_earn_calc",
        "status": "completed",
        "finalPrice": 350.0,
        "category": "electrician"
    })

    # Owner request
    owner_req = {"uid": "w_earn_calc", "role": "worker"}
    res = api_get_worker_earnings("w_earn_calc", current_user=owner_req)
    assert res["totalEarnings"] == 850.0
    assert res["completedJobsCount"] == 2
    assert res["currency"] == "INR"
    assert res["payoutType"] == "direct_cash"
    assert len(res["jobs"]) == 2

    # Unauthorized request (another worker) -> 403 response
    intruder_req = {"uid": "w_other", "role": "worker"}
    res_forbidden = api_get_worker_earnings("w_earn_calc", current_user=intruder_req)
    assert res_forbidden.status_code == 403


def test_worker_profile_update():
    from routers.workers import api_update_worker, WorkerUpdatePayload

    db.set_document("workers", "w_update_test", {
        "uid": "w_update_test",
        "name": "Old Name",
        "skills": ["plumber"],
        "rates": {"plumber": 300.0},
        "isAvailableNow": True
    })

    owner_req = {"uid": "w_update_test", "role": "worker"}
    payload = WorkerUpdatePayload(
        name="New Name",
        rates={"plumber": 450.0},
        isAvailableNow=False
    )
    res = api_update_worker("w_update_test", payload, current_user=owner_req)
    assert res["status"] == "success"
    assert res["name"] == "New Name"
    assert res["rates"]["plumber"] == 450.0
    assert res["isAvailableNow"] is False

    w_doc = db.get_document("workers", "w_update_test")
    assert w_doc["name"] == "New Name"
    assert w_doc["rates"]["plumber"] == 450.0
    assert w_doc["isAvailableNow"] is False
