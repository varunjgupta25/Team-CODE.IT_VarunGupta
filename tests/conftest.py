import copy
import pytest
from fastapi.testclient import TestClient

from main import app
from core.database import db
from core.auth import get_current_user


@pytest.fixture(autouse=True)
def isolated_db():
    """
    Ensures each test runs against a completely clean, isolated, in-memory Firestore.
    Disables saving to disk so no files on disk are touched during test runs.
    """
    db._save_to_disk = False

    # Baseline seed data for tests
    baseline_users = {
        "cust_test_1": {
            "uid": "cust_test_1",
            "role": "customer",
            "name": "Customer Priya",
            "phone": "+91 98201 11222",
            "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road East"}
        },
        "cust_test_2": {
            "uid": "cust_test_2",
            "role": "customer",
            "name": "Customer Amit",
            "phone": "+91 98202 22333",
            "location": {"lat": 19.2860, "lng": 72.8620, "address": "Poonam Sagar"}
        },
        "worker_elec_1": {
            "uid": "worker_elec_1",
            "role": "worker",
            "name": "Rajesh Electrician",
            "phone": "+91 91102 00001",
            "location": {"lat": 19.2840, "lng": 72.8590}
        },
        "worker_elec_2": {
            "uid": "worker_elec_2",
            "role": "worker",
            "name": "Manoj Electrician",
            "phone": "+91 91102 00002",
            "location": {"lat": 19.2810, "lng": 72.8540}
        },
        "worker_plumber_1": {
            "uid": "worker_plumber_1",
            "role": "worker",
            "name": "Ramesh Plumber",
            "phone": "+91 91101 00001",
            "location": {"lat": 19.2830, "lng": 72.8580}
        },
        "admin_user": {
            "uid": "admin_user",
            "role": "admin",
            "name": "Super Admin",
            "phone": "+91 99999 00000",
            "location": {"lat": 19.2825, "lng": 72.8570}
        }
    }

    baseline_workers = {
        "worker_elec_1": {
            "uid": "worker_elec_1",
            "name": "Rajesh Electrician",
            "skills": ["electrician"],
            "rates": {"electrician": 450.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.9,
            "jobsDone": 51,
            "location": {"lat": 19.2840, "lng": 72.8590},
            "serviceRadiusKm": 6.0,
            "isFlagged": False,
            "flagged": False
        },
        "worker_elec_2": {
            "uid": "worker_elec_2",
            "name": "Manoj Electrician",
            "skills": ["electrician"],
            "rates": {"electrician": 400.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.6,
            "jobsDone": 23,
            "location": {"lat": 19.2810, "lng": 72.8540},
            "serviceRadiusKm": 5.0,
            "isFlagged": False,
            "flagged": False
        },
        "worker_plumber_1": {
            "uid": "worker_plumber_1",
            "name": "Ramesh Plumber",
            "skills": ["plumber"],
            "rates": {"plumber": 350.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.8,
            "jobsDone": 42,
            "location": {"lat": 19.2830, "lng": 72.8580},
            "serviceRadiusKm": 6.0,
            "isFlagged": False,
            "flagged": False
        }
    }

    baseline_jobs = {
        "job_test_open": {
            "id": "job_test_open",
            "customerId": "cust_test_1",
            "category": "electrician",
            "description": "Wiring repair in living room",
            "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road East"},
            "budget": 450.0,
            "mode": "on-demand",
            "status": "open",
            "acceptedWorkerId": None,
            "finalPrice": None,
            "createdAt": "2026-10-24T10:00:00Z"
        },
        "job_test_accepted": {
            "id": "job_test_accepted",
            "customerId": "cust_test_1",
            "category": "electrician",
            "description": "Fan installation",
            "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road East"},
            "budget": 400.0,
            "mode": "on-demand",
            "status": "accepted",
            "acceptedWorkerId": "worker_elec_1",
            "finalPrice": 400.0,
            "createdAt": "2026-10-24T10:00:00Z"
        },
        "job_test_in_progress": {
            "id": "job_test_in_progress",
            "customerId": "cust_test_1",
            "category": "electrician",
            "description": "Switchboard fix",
            "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road East"},
            "budget": 400.0,
            "mode": "on-demand",
            "status": "in_progress",
            "acceptedWorkerId": "worker_elec_1",
            "finalPrice": 400.0,
            "createdAt": "2026-10-24T10:00:00Z"
        },
        "job_test_completed": {
            "id": "job_test_completed",
            "customerId": "cust_test_1",
            "category": "electrician",
            "description": "Light fitting replacement",
            "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road East"},
            "budget": 450.0,
            "mode": "on-demand",
            "status": "completed",
            "acceptedWorkerId": "worker_elec_1",
            "finalPrice": 450.0,
            "createdAt": "2026-10-24T10:00:00Z"
        }
    }

    with db._lock:
        db._mem_store = {
            "users": copy.deepcopy(baseline_users),
            "workers": copy.deepcopy(baseline_workers),
            "jobs": copy.deepcopy(baseline_jobs),
            "offers": {},
            "reviews": {},
            "sos_alerts": {},
            "reports": {},
        }

    # Reset any dependency overrides
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_customer_headers():
    return {"Authorization": "Bearer cust_test_1"}


@pytest.fixture
def auth_customer_2_headers():
    return {"Authorization": "Bearer cust_test_2"}


@pytest.fixture
def auth_worker_headers():
    return {"Authorization": "Bearer worker_elec_1"}


@pytest.fixture
def auth_worker_2_headers():
    return {"Authorization": "Bearer worker_elec_2"}


@pytest.fixture
def auth_admin_headers():
    return {"Authorization": "Bearer admin_user"}


def set_mock_user(uid: str, role: str, name: str = "Test User"):
    """
    Utility helper to inject uid and role directly via FastAPI dependency override.
    """
    def mock_get_current_user():
        return {
            "uid": uid,
            "role": role,
            "name": name,
            "is_firebase": False
        }
    app.dependency_overrides[get_current_user] = mock_get_current_user
