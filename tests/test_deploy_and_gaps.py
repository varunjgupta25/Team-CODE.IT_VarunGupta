import os
import unittest.mock as mock
import pytest
from fastapi.testclient import TestClient

from main import app
from core.database import db
from core.config import settings
import services.routing as routing_svc
from seed import auto_seed_if_empty


client = TestClient(app)


def test_admin_verifications_auth_and_queue():
    """
    Test GET /admin/verifications and /api/admin/verifications:
    - 401 without token
    - 403 for customer and worker roles
    - 200 for admin returning pending queue
    - Masks document number and never exposes full number
    - Worker enters queue on /workers/verify and exits on /admin/verifications/{uid}/approve
    """
    # 1. 401 Unauthorized without token
    res = client.get("/admin/verifications")
    assert res.status_code == 401
    res_api = client.get("/api/admin/verifications")
    assert res_api.status_code == 401

    # 2. 403 Forbidden for non-admin roles
    res_cust = client.get(
        "/admin/verifications",
        headers={"Authorization": "Bearer token-customer-cust_test_1"}
    )
    assert res_cust.status_code == 403

    res_worker = client.get(
        "/admin/verifications",
        headers={"Authorization": "Bearer token-worker-worker_elec_1"}
    )
    assert res_worker.status_code == 403

    # 3. Create a test worker needing verification
    worker_id = "worker_gap_test_1"
    db.set_document("workers", worker_id, {
        "uid": worker_id,
        "name": "Suresh VerifiedTest",
        "skills": ["electrician"],
        "rates": {"electrician": 400.0},
        "isAvailableNow": True,
        "verified": False,
        "verificationStatus": "unverified",
        "rating": 5.0,
        "jobsDone": 0,
        "location": {"lat": 19.2813, "lng": 72.8688},
        "serviceRadiusKm": 5.0,
        "isFlagged": False,
        "flagged": False
    })

    # Worker requests verification with a full 12-digit Aadhaar number
    full_doc = "987654321099"
    verify_res = client.post(
        "/workers/verify",
        json={"documentType": "aadhaar", "documentNumber": full_doc},
        headers={"Authorization": f"Bearer token-worker-{worker_id}"}
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "pending"

    # 4. Admin lists verifications (check root and /api prefixes)
    admin_headers = {"Authorization": "Bearer token-admin-admin_user"}
    res_admin = client.get("/admin/verifications", headers=admin_headers)
    assert res_admin.status_code == 200
    pending_list = res_admin.json()
    assert isinstance(pending_list, list)

    target = next((w for w in pending_list if w["workerId"] == worker_id), None)
    assert target is not None, "Worker should be present in admin pending verifications list"
    assert target["name"] == "Suresh VerifiedTest"
    assert target["documentType"] == "aadhaar"
    assert target["documentNumberMasked"] == "•••• 1099"
    assert full_doc not in str(target), "Full document number must never be exposed"
    assert target["requestedAt"] is not None

    # Check /api/admin/verifications prefix works identically
    res_admin_api = client.get("/api/admin/verifications", headers=admin_headers)
    assert res_admin_api.status_code == 200
    assert any(w["workerId"] == worker_id for w in res_admin_api.json())

    # 5. Admin approves worker
    appr_res = client.post(f"/admin/verifications/{worker_id}/approve", headers=admin_headers)
    assert appr_res.status_code == 200
    assert appr_res.json()["verified"] is True

    # 6. Worker no longer appears in pending verifications
    res_after = client.get("/admin/verifications", headers=admin_headers)
    assert not any(w["workerId"] == worker_id for w in res_after.json())


def test_auto_seed_empty_and_idempotent():
    """
    Test auto-seeding behavior:
    - Empty workers collection triggers auto_seed_if_empty
    - Populates 25+ workers, customers, jobs, and admin_user
    - Calling again is idempotent and doesn't duplicate
    - Respects settings.AUTO_SEED = False
    """
    # 1. Clear database
    db.clear_collection("workers")
    db.clear_collection("users")
    db.clear_collection("jobs")

    assert len(db.list_collection("workers")) == 0

    # Test AUTO_SEED = False
    with mock.patch.object(settings, "AUTO_SEED", False):
        auto_seed_if_empty()
        assert len(db.list_collection("workers")) == 0

    # Test AUTO_SEED = True
    with mock.patch.object(settings, "AUTO_SEED", True):
        auto_seed_if_empty()
        workers = db.list_collection("workers")
        assert len(workers) >= 25
        admin = db.get_document("users", "admin_user")
        assert admin is not None
        assert admin.get("role") == "admin"

        count_before = len(workers)
        # 2. Second run is a no-op (idempotent)
        auto_seed_if_empty()
        assert len(db.list_collection("workers")) == count_before


def test_database_readonly_persistence_resilience():
    """
    Test that if disk writes fail with PermissionError/OSError,
    the app continues operating in-memory without crashing.
    """
    db._save_to_disk = True
    with mock.patch("builtins.open", side_effect=PermissionError("Read-only filesystem")):
        # Saving should log warning and not raise
        db._save_local_store()

    # Database operations still work in memory
    db.set_document("workers", "w_mem_test", {"uid": "w_mem_test", "name": "Memory Worker"})
    doc = db.get_document("workers", "w_mem_test")
    assert doc is not None
    assert doc["name"] == "Memory Worker"
    db._save_to_disk = False


def test_cors_origin_regex_and_preflight():
    """
    Test CORS headers for:
    - Standard allowed origins (localhost:5173)
    - Vercel preview deployments matching CORS_ORIGIN_REGEX
    - Disallowed origin (evil.example.com)
    """
    # 1. Allowed localhost origin
    res_local = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res_local.headers.get("access-control-allow-origin") == "http://localhost:5173"

    # 2. Allowed Vercel preview domain
    preview_origin = "https://repair-buddy-abc123.vercel.app"
    res_preview = client.options(
        "/health",
        headers={
            "Origin": preview_origin,
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res_preview.headers.get("access-control-allow-origin") == preview_origin

    # 3. Disallowed origin
    res_evil = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res_evil.headers.get("access-control-allow-origin") is None


def test_routing_graph_present_and_missing():
    """
    Test routing endpoints with graph present vs graph missing:
    - When graph is present: /route returns valid polyline (>=2 points) and distanceKm/etaMinutes
    - When graph is missing: /route returns 404, /workers/match falls back to Haversine and returns 200
    """
    # 1. Graph loaded (ensure graph is loaded)
    routing_svc._graph_loaded = False
    routing_svc._graph = None
    G = routing_svc.load_graph()
    assert G is not None, "GraphML must be present and loadable"

    auth_customer = {"Authorization": "Bearer token-customer-cust_test_1"}

    # Test /route with valid job and worker
    route_res = client.get(
        "/route",
        params={
            "jobId": "job_test_open",
            "workerId": "worker_elec_1"
        },
        headers=auth_customer
    )
    assert route_res.status_code == 200
    data = route_res.json()
    assert "polyline" in data
    assert len(data["polyline"]) >= 2
    assert data["distanceKm"] > 0
    assert data["etaMinutes"] > 0

    # Check top matched workers have road ETAs
    match_res = client.get(
        "/workers/match",
        params={"jobId": "job_test_open"},
        headers=auth_customer
    )
    assert match_res.status_code == 200
    matches = match_res.json()
    assert len(matches) > 0
    assert matches[0]["distanceKm"] > 0
    assert matches[0]["etaMinutes"] > 0

    # 2. Simulate graph missing
    saved_graph = routing_svc._graph
    try:
        routing_svc._graph = None

        # /route returns 404 when graph is missing
        missing_route = client.get(
            "/route",
            params={
                "jobId": "job_test_open",
                "workerId": "worker_elec_1"
            },
            headers=auth_customer
        )
        assert missing_route.status_code == 404

        # /workers/match still returns 200 via Haversine fallback
        fallback_match = client.get(
            "/workers/match",
            params={"jobId": "job_test_open"},
            headers=auth_customer
        )
        assert fallback_match.status_code == 200
        fb_matches = fallback_match.json()
        assert len(fb_matches) > 0
        assert fb_matches[0]["distanceKm"] > 0
        assert fb_matches[0]["etaMinutes"] > 0
    finally:
        routing_svc._graph = saved_graph
