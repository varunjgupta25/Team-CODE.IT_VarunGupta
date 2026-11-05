"""
Loop 4 Tests: User Registration Protection & Hardcoded Data Removal
- Token-derived UID enforcement: body 'uid' is strictly ignored
- Overwrite & duplicate prevention: returning HTTP 409 Conflict
- Error payload schema: {"error": "conflict", "message": "User profile already registered."}
- Unauthenticated registration attempts return HTTP 401 Unauthorized
"""
import pytest
from core.database import db


def test_customer_registration_requires_auth(client):
    """Calling /customers/register without Authorization header must return 401."""
    res = client.post("/customers/register", json={
        "name": "Unauthenticated User",
        "phone": "+91 91234 56789"
    })
    assert res.status_code == 401


def test_worker_registration_requires_auth(client):
    """Calling /workers/register without Authorization header must return 401."""
    res = client.post("/workers/register", json={
        "name": "Unauthenticated Worker",
        "phone": "+91 91234 56789",
        "skills": ["electrician"],
        "rates": {"electrician": 400.0}
    })
    assert res.status_code == 401


def test_customer_registration_success(client):
    """New customer with a valid dev token can register their profile."""
    auth_headers = {"Authorization": "Bearer token-customer-cust_reg_test_1"}
    res = client.post("/customers/register", json={
        "name": "Aarav Mehta",
        "phone": "+91 98111 22334",
        "location": {"lat": 19.2815, "lng": 72.8590, "address": "Mira Road Station"}
    }, headers=auth_headers)

    assert res.status_code == 201
    data = res.json()
    assert data["uid"] == "cust_reg_test_1"
    assert data["name"] == "Aarav Mehta"
    assert data["role"] == "customer"

    # Verify saved in db
    saved = db.get_document("users", "cust_reg_test_1")
    assert saved is not None
    assert saved["name"] == "Aarav Mehta"


def test_customer_registration_duplicate_returns_409(client):
    """Registering an already-registered customer profile must return HTTP 409 Conflict."""
    auth_headers = {"Authorization": "Bearer token-customer-cust_reg_test_dup"}
    payload = {
        "name": "First Registration",
        "phone": "+91 98111 22335"
    }

    # First attempt succeeds
    res1 = client.post("/customers/register", json=payload, headers=auth_headers)
    assert res1.status_code == 201

    # Second attempt with same token must abort with 409 Conflict
    res2 = client.post("/customers/register", json={
        "name": "Overwriting Attempt",
        "phone": "+91 98999 88888"
    }, headers=auth_headers)

    assert res2.status_code == 409
    body = res2.json()
    assert body.get("error") == "conflict"
    assert body.get("message") == "User profile already registered."

    # Verify original profile was not overwritten
    original = db.get_document("users", "cust_reg_test_dup")
    assert original["name"] == "First Registration"


def test_customer_registration_ignores_body_uid(client):
    """Any custom 'uid' in request body must be ignored in favor of token-derived UID."""
    token_uid = "cust_reg_derived_from_token_99"
    auth_headers = {"Authorization": f"Bearer token-customer-{token_uid}"}

    res = client.post("/customers/register", json={
        "uid": "malicious_spoofed_uid_12345",
        "name": "Legit Name",
        "phone": "+91 97777 66666"
    }, headers=auth_headers)

    assert res.status_code == 201
    data = res.json()
    assert data["uid"] == token_uid
    assert data["uid"] != "malicious_spoofed_uid_12345"

    # Ensure spoofed UID was NEVER created in database
    assert db.get_document("users", "malicious_spoofed_uid_12345") is None
    # Ensure real token UID WAS created
    assert db.get_document("users", token_uid) is not None


def test_worker_registration_success(client):
    """New worker with a valid dev token can register their profile."""
    auth_headers = {"Authorization": "Bearer token-worker-worker_reg_test_1"}
    res = client.post("/workers/register", json={
        "name": "Vikram Plumber",
        "phone": "+91 91234 56780",
        "skills": ["plumber"],
        "rates": {"plumber": 350.0},
        "serviceRadiusKm": 8.0
    }, headers=auth_headers)

    assert res.status_code == 201
    data = res.json()
    assert data["uid"] == "worker_reg_test_1"
    assert data["name"] == "Vikram Plumber"
    assert data["verified"] is False
    assert data["verificationStatus"] == "unverified"

    # Verify saved in both workers and users collections
    assert db.get_document("workers", "worker_reg_test_1") is not None
    assert db.get_document("users", "worker_reg_test_1") is not None


def test_worker_registration_duplicate_returns_409(client):
    """Registering an already-registered worker profile must return HTTP 409 Conflict."""
    auth_headers = {"Authorization": "Bearer token-worker-worker_reg_test_dup"}
    payload = {
        "name": "First Worker Registration",
        "phone": "+91 91234 56781",
        "skills": ["electrician"],
        "rates": {"electrician": 400.0}
    }

    # First attempt succeeds
    res1 = client.post("/workers/register", json=payload, headers=auth_headers)
    assert res1.status_code == 201

    # Second attempt with same token must abort with 409 Conflict
    res2 = client.post("/workers/register", json={
        "name": "Overwriting Worker Attempt",
        "phone": "+91 98999 88888",
        "skills": ["plumber"],
        "rates": {"plumber": 500.0}
    }, headers=auth_headers)

    assert res2.status_code == 409
    body = res2.json()
    assert body.get("error") == "conflict"
    assert body.get("message") == "User profile already registered."

    # Verify original record preserved
    original = db.get_document("workers", "worker_reg_test_dup")
    assert original["name"] == "First Worker Registration"


def test_worker_registration_ignores_body_uid(client):
    """Any custom 'uid' in worker registration body must be ignored in favor of token UID."""
    token_uid = "worker_reg_derived_from_token_88"
    auth_headers = {"Authorization": f"Bearer token-worker-{token_uid}"}

    res = client.post("/workers/register", json={
        "uid": "spoofed_worker_uid_99999",
        "name": "Dev Worker",
        "phone": "+91 98888 77777",
        "skills": ["painter"],
        "rates": {"painter": 300.0}
    }, headers=auth_headers)

    assert res.status_code == 201
    data = res.json()
    assert data["uid"] == token_uid
    assert data["uid"] != "spoofed_worker_uid_99999"

    # Ensure spoofed UID was NEVER created in database
    assert db.get_document("workers", "spoofed_worker_uid_99999") is None
    assert db.get_document("users", "spoofed_worker_uid_99999") is None
    # Ensure real token UID WAS created
    assert db.get_document("workers", token_uid) is not None


def test_aliased_register_route_behaves_identically(client):
    """POST /register (aliased route) enforces token UID and 409 duplicates."""
    auth_headers = {"Authorization": "Bearer token-customer-cust_reg_alias_1"}
    res = client.post("/register", json={
        "name": "Alias Customer",
        "phone": "+91 91111 22222"
    }, headers=auth_headers)
    assert res.status_code == 201
    assert res.json()["uid"] == "cust_reg_alias_1"

    # Duplicate call returns 409
    res_dup = client.post("/register", json={
        "name": "Alias Customer 2",
        "phone": "+91 91111 22222"
    }, headers=auth_headers)
    assert res_dup.status_code == 409
    assert res_dup.json().get("error") == "conflict"
