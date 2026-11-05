import pytest
from fastapi.testclient import TestClient
from main import app
from core.database import db
from core.config import settings
from services.notification_provider import (
    ConsoleProvider,
    get_notification_provider,
    set_notification_provider,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_provider():
    provider = ConsoleProvider()
    set_notification_provider(provider)
    yield provider
    set_notification_provider(None)


def test_save_and_get_emergency_contact_validation(auth_customer_headers, client):
    """
    User can save emergency contact with E.164 +91 validation.
    """
    # 1. Invalid phone number (invalid format or short) -> 422
    res_bad = client.put(
        "/users/me/emergency-contact",
        json={"name": "Emergency Parent", "phone": "12345"},
        headers=auth_customer_headers
    )
    assert res_bad.status_code == 422

    # 2. Valid 10-digit Indian number converts to E.164
    res_ok = client.put(
        "/users/me/emergency-contact",
        json={"name": "Rohit Sharma", "phone": "9820199999"},
        headers=auth_customer_headers
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["emergencyContact"]["phone"] == "+919820199999"
    assert data["emergencyContact"]["name"] == "Rohit Sharma"

    # 3. GET /users/me/emergency-contact retrieves saved contact
    res_get = client.get("/users/me/emergency-contact", headers=auth_customer_headers)
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "Rohit Sharma"
    assert res_get.json()["phone"] == "+919820199999"


def test_sos_success_with_contact_and_ops_notified(auth_customer_headers, reset_provider, client):
    """
    On SOS, both the user's emergency contact and ops phone are notified.
    Status returns 'notified', recipients stored, message includes maps URL.
    """
    # Save emergency contact
    client.put(
        "/users/me/emergency-contact",
        json={"name": "Kavita Customer", "phone": "+919820188888"},
        headers=auth_customer_headers
    )

    sos_payload = {
        "jobId": "job_test_open",
        "location": {"lat": 19.2825, "lng": 72.8570}
    }
    res = client.post("/sos", json=sos_payload, headers=auth_customer_headers)
    assert res.status_code == 201
    data = res.json()

    assert data["status"] == "notified"
    assert "https://www.google.com/maps?q=19.2825,72.857" in data["mapsUrl"]
    assert len(data["recipients"]) >= 2

    # Verify notification provider was called
    recipients_phones = [m["to"] for m in reset_provider.sent_messages]
    assert "+919820188888" in recipients_phones
    assert settings.OPS_ALERT_PHONE in recipients_phones

    # Check alert content
    msg = reset_provider.sent_messages[0]["message"]
    assert "EMERGENCY SOS ALERT" in msg
    assert "job_test_open" in msg


def test_sos_provider_failure_honest_status(auth_customer_headers, reset_provider, client):
    """
    If notification provider fails, status must return 'failed',
    and record is still saved in DB with recipient error details.
    """
    reset_provider.should_fail = True

    # User with emergency contact
    client.put(
        "/users/me/emergency-contact",
        json={"name": "Kavita", "phone": "+919820188888"},
        headers=auth_customer_headers
    )

    sos_payload = {
        "jobId": "job_test_open",
        "location": {"lat": 19.2825, "lng": 72.8570}
    }
    res = client.post("/sos", json=sos_payload, headers=auth_customer_headers)
    assert res.status_code == 201
    data = res.json()

    assert data["status"] == "failed"
    assert all(r["status"] == "failed" for r in data["recipients"])

    # Record exists in DB
    db_record = db.get_document("sos_alerts", data["id"])
    assert db_record is not None
    assert db_record["status"] == "failed"


def test_sos_unauthorized_user_blocked(auth_customer_2_headers, auth_worker_2_headers, auth_worker_headers, client):
    """
    Only the job's customer or accepted worker can trigger SOS. Others get 403.
    """
    # Job customer is cust_test_1, acceptedWorker is worker_elec_1
    sos_payload = {
        "jobId": "job_test_in_progress",
        "location": {"lat": 19.2825, "lng": 72.8570}
    }

    # 1. Customer 2 (not job's customer) -> 403
    res_other_cust = client.post("/sos", json=sos_payload, headers=auth_customer_2_headers)
    assert res_other_cust.status_code == 403
    assert "Only the job's customer or accepted worker" in res_other_cust.json()["detail"]

    # 2. Worker 2 (not assigned worker) -> 403
    res_other_worker = client.post("/sos", json=sos_payload, headers=auth_worker_2_headers)
    assert res_other_worker.status_code == 403

    # 3. Accepted worker -> 201 Allowed
    res_assigned_worker = client.post("/sos", json=sos_payload, headers=auth_worker_headers)
    assert res_assigned_worker.status_code == 201


def test_sos_duplicate_within_60s_returns_existing(auth_customer_headers, reset_provider, client):
    """
    Duplicate SOS for the same job within 60s returns the existing record without re-sending.
    """
    sos_payload = {
        "jobId": "job_test_open",
        "location": {"lat": 19.2825, "lng": 72.8570}
    }

    # 1st call
    res1 = client.post("/sos", json=sos_payload, headers=auth_customer_headers)
    assert res1.status_code == 201
    alert_1 = res1.json()
    msg_count_1 = len(reset_provider.sent_messages)

    # 2nd call immediately (<60s)
    res2 = client.post("/sos", json=sos_payload, headers=auth_customer_headers)
    assert res2.status_code == 201
    alert_2 = res2.json()

    # Must return same alert ID
    assert alert_1["id"] == alert_2["id"]
    # No duplicate notifications dispatched
    assert len(reset_provider.sent_messages) == msg_count_1


def test_sos_rate_limit_3_per_hour(auth_customer_headers, client):
    """
    Maximum 3 distinct SOS alerts per hour per user. 4th alert returns 429.
    """
    # Create 3 jobs for testing distinct alerts
    for i in range(1, 4):
        db.set_document("jobs", f"job_rate_limit_{i}", {
            "id": f"job_rate_limit_{i}",
            "customerId": "cust_test_1",
            "status": "open"
        })

    for i in range(1, 4):
        res = client.post(
            "/sos",
            json={"jobId": f"job_rate_limit_{i}", "location": {"lat": 19.28, "lng": 72.85}},
            headers=auth_customer_headers
        )
        assert res.status_code == 201, f"Alert {i} failed"

    # 4th alert -> 429
    db.set_document("jobs", "job_rate_limit_4", {
        "id": "job_rate_limit_4",
        "customerId": "cust_test_1",
        "status": "open"
    })
    res_over = client.post(
        "/sos",
        json={"jobId": "job_rate_limit_4", "location": {"lat": 19.28, "lng": 72.85}},
        headers=auth_customer_headers
    )
    assert res_over.status_code == 429
    assert "Rate limit exceeded" in res_over.json()["detail"]


def test_admin_list_sos_alerts(auth_admin_headers, auth_customer_headers, client):
    """
    GET /admin/sos lists all recorded SOS alerts with delivery status. Admin-only.
    """
    # Non-admin -> 403
    assert client.get("/admin/sos", headers=auth_customer_headers).status_code == 403

    # Admin -> 200
    res = client.get("/admin/sos", headers=auth_admin_headers)
    assert res.status_code == 200
    alerts = res.json()
    assert isinstance(alerts, list)

