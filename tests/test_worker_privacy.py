"""
Tests for Worker Mutation Route Authorization & Privacy Masking:
1. PATCH /workers/{id} ownership authorization:
   - Worker can update own availability -> 200
   - Unauthorized worker attempting to update another worker's profile -> 403 Forbidden
     Payload: {"error": "forbidden", "message": "You do not have permission to modify this profile."}
   - Admin can update any worker's profile -> 200
2. GET /workers/{id} sensitive data stripping:
   - Public view (requester != worker): hides phone, national ID, exact address
   - Owner view (requester == worker): includes phone and full profile
   - Admin view: includes full profile
3. Worker feed endpoints (GET /workers, GET /workers/feed):
   - Returns masked address strings (e.g. '123 Main Street, Apt 4B, Sector 5' -> 'Sector 5')
   - Truncates exact coordinates to 2 decimal places
   - Excludes private phone numbers
"""
import pytest
from core.database import db


@pytest.fixture
def worker_with_sensitive_data():
    """Seeds a worker with sensitive metadata in database."""
    wid = "worker_privacy_target_1"
    doc = {
        "uid": wid,
        "name": "Rajesh Sharma",
        "phone": "+91 98200 12345",
        "skills": ["electrician"],
        "rates": {"electrician": 450.0},
        "isAvailableNow": True,
        "verified": True,
        "rating": 4.9,
        "jobsDone": 35,
        "documentType": "aadhaar",
        "documentNumber": "987654321099",
        "bank_details": {"account": "1234567890", "ifsc": "HDFC0001234"},
        "location": {
            "lat": 19.284567,
            "lng": 72.859123,
            "address": "123 Main Street, Apt 4B, Sector 5"
        },
        "serviceRadiusKm": 5.0,
        "isFlagged": False,
        "flagged": False
    }
    db.set_document("workers", wid, doc)
    db.set_document("users", wid, {
        "uid": wid,
        "role": "worker",
        "name": "Rajesh Sharma",
        "phone": "+91 98200 12345"
    })
    return wid


# ---------------------------------------------------------------------------
# 1. Ownership Authorization Tests (PATCH /workers/{id})
# ---------------------------------------------------------------------------

def test_worker_can_update_own_availability(client, worker_with_sensitive_data):
    """A worker can update their own availability status."""
    wid = worker_with_sensitive_data
    auth_headers = {"Authorization": f"Bearer token-worker-{wid}"}

    res = client.patch(f"/workers/{wid}", json={"isAvailableNow": False}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert res.json()["isAvailableNow"] is False

    # Verify update persisted
    updated = db.get_document("workers", wid)
    assert updated["isAvailableNow"] is False


def test_unauthorized_worker_cannot_modify_other_worker_profile(client, worker_with_sensitive_data):
    """An unauthorized worker modifying another worker's profile receives 403 Forbidden."""
    wid = worker_with_sensitive_data
    # Worker 2 attempts to modify worker 1
    attacker_headers = {"Authorization": "Bearer worker_elec_2"}

    res = client.patch(f"/workers/{wid}", json={"isAvailableNow": False}, headers=attacker_headers)
    assert res.status_code == 403
    body = res.json()
    assert body.get("error") == "forbidden"
    assert body.get("message") == "You do not have permission to modify this profile."


def test_customer_cannot_call_patch_worker(client, worker_with_sensitive_data, auth_customer_headers):
    """A customer cannot call PATCH /workers/{id} (returns 403)."""
    wid = worker_with_sensitive_data
    res = client.patch(f"/workers/{wid}", json={"isAvailableNow": False}, headers=auth_customer_headers)
    assert res.status_code == 403


def test_admin_can_update_any_worker_availability(client, worker_with_sensitive_data, auth_admin_headers):
    """An admin is authorized to update any worker's availability."""
    wid = worker_with_sensitive_data
    res = client.patch(f"/workers/{wid}", json={"isAvailableNow": False}, headers=auth_admin_headers)
    assert res.status_code == 200
    assert res.json()["isAvailableNow"] is False


# ---------------------------------------------------------------------------
# 2. Sensitive Data Stripping Tests (GET /workers/{id})
# ---------------------------------------------------------------------------

def test_public_view_strips_phone_and_exact_address(client, worker_with_sensitive_data, auth_customer_headers):
    """
    Public view (customer requesting worker details):
    - phone number is excluded
    - national ID / documentNumber is excluded
    - bank details are excluded
    - exact address '123 Main Street, Apt 4B, Sector 5' is masked to 'Sector 5'
    """
    wid = worker_with_sensitive_data
    res = client.get(f"/workers/{wid}", headers=auth_customer_headers)
    assert res.status_code == 200
    data = res.json()

    # Sensitive fields MUST be absent
    assert "phone" not in data or data["phone"] is None
    assert "phone_number" not in data
    assert "documentNumber" not in data
    assert "bank_details" not in data

    # Granular street address must be obfuscated
    addr = data.get("location", {}).get("address")
    assert addr == "Sector 5", f"Expected 'Sector 5', got '{addr}'"
    assert "123 Main Street" not in addr
    assert "Apt 4B" not in addr

    # Precise coordinates truncated to 2 decimal places
    lat = data.get("location", {}).get("lat")
    lng = data.get("location", {}).get("lng")
    assert lat == 19.28
    assert lng == 72.86


def test_owner_view_returns_complete_profile(client, worker_with_sensitive_data):
    """
    Owner view (worker requesting their own profile):
    - phone number is present
    - full address is present
    """
    wid = worker_with_sensitive_data
    auth_headers = {"Authorization": f"Bearer token-worker-{wid}"}

    res = client.get(f"/workers/{wid}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    # Owner gets complete details
    assert data.get("phone") == "+91 98200 12345"
    assert data.get("location", {}).get("address") == "123 Main Street, Apt 4B, Sector 5"
    assert data.get("location", {}).get("lat") == 19.284567


def test_admin_view_returns_complete_profile(client, worker_with_sensitive_data, auth_admin_headers):
    """Admin view receives the full unmasked worker profile."""
    wid = worker_with_sensitive_data
    res = client.get(f"/workers/{wid}", headers=auth_admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data.get("phone") == "+91 98200 12345"
    assert data.get("location", {}).get("address") == "123 Main Street, Apt 4B, Sector 5"


# ---------------------------------------------------------------------------
# 3. Worker Feed Address Obfuscation Tests
# ---------------------------------------------------------------------------

def test_workers_feed_masks_addresses_and_strips_phone(client, worker_with_sensitive_data, auth_customer_headers):
    """
    GET /workers/feed and GET /workers:
    - Lists workers with sensitive data stripped
    - Address masked to non-granular area
    """
    wid = worker_with_sensitive_data

    for endpoint in ["/workers/feed", "/workers", "/api/workers/feed", "/api/workers"]:
        res = client.get(endpoint, headers=auth_customer_headers)
        assert res.status_code == 200
        feed = res.json()
        assert isinstance(feed, list)
        assert len(feed) > 0

        # Locate our test worker in feed
        target = next((w for w in feed if w.get("uid") == wid), None)
        assert target is not None, f"Target worker {wid} not found in {endpoint}"

        # Verify privacy controls
        assert "phone" not in target or target["phone"] is None
        assert "documentNumber" not in target
        assert "bank_details" not in target

        addr = target.get("location", {}).get("address")
        assert addr == "Sector 5"
        assert target.get("location", {}).get("lat") == 19.28
        assert target.get("location", {}).get("lng") == 72.86
