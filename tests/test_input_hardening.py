"""
Loop 4: Input Validation Hardening Tests
- Category whitelist enforcement
- Field length caps
- Mode enum constraint
- Price ceiling
- Blank-after-strip rejection for comment/reason
"""
import pytest


# ---------------------------------------------------------------------------
# Job category whitelist
# ---------------------------------------------------------------------------

def test_invalid_job_category_returns_422(client, auth_customer_headers):
    """Non-whitelisted category strings must yield 422."""
    for bad_cat in ["hacker", "SELECT * FROM users", "", "  ", "notarealskill"]:
        res = client.post("/jobs", json={
            "category": bad_cat,
            "description": "Some work needed",
            "location": {"lat": 19.28, "lng": 72.86, "address": "Mira Road"},
        }, headers=auth_customer_headers)
        assert res.status_code == 422, (
            f"Expected 422 for category '{bad_cat}', got {res.status_code}: {res.json()}"
        )


def test_valid_job_categories_accepted(client, auth_customer_headers):
    """All whitelisted categories must be accepted."""
    from models.job import VALID_CATEGORIES
    for cat in VALID_CATEGORIES:
        res = client.post("/jobs", json={
            "category": cat,
            "description": "Some work needed",
            "location": {"lat": 19.28, "lng": 72.86, "address": "Mira Road"},
        }, headers=auth_customer_headers)
        assert res.status_code == 201, (
            f"Expected 201 for valid category '{cat}', got {res.status_code}: {res.json()}"
        )


def test_category_is_case_normalised(client, auth_customer_headers):
    """Category should be normalised to lowercase."""
    res = client.post("/jobs", json={
        "category": "Electrician",
        "description": "Light fitting issue",
        "location": {"lat": 19.28, "lng": 72.86, "address": "Mira Road"},
    }, headers=auth_customer_headers)
    assert res.status_code == 201
    assert res.json()["category"] == "electrician"


# ---------------------------------------------------------------------------
# Job mode enum constraint
# ---------------------------------------------------------------------------

def test_invalid_job_mode_returns_422(client, auth_customer_headers):
    """mode field must be 'on-demand' or 'scheduled' only."""
    res = client.post("/jobs", json={
        "category": "electrician",
        "description": "Some wiring issue",
        "location": {"lat": 19.28, "lng": 72.86, "address": "Mira Road"},
        "mode": "ASAP"
    }, headers=auth_customer_headers)
    assert res.status_code == 422


def test_valid_modes_accepted(client, auth_customer_headers):
    """on-demand and scheduled are accepted modes."""
    for mode in ["on-demand", "scheduled"]:
        res = client.post("/jobs", json={
            "category": "plumber",
            "description": "Leaking pipe",
            "location": {"lat": 19.28, "lng": 72.86, "address": "Mira Road"},
            "mode": mode,
        }, headers=auth_customer_headers)
        assert res.status_code == 201, f"mode='{mode}' failed: {res.json()}"


# ---------------------------------------------------------------------------
# Field length caps
# ---------------------------------------------------------------------------

def test_description_max_length_enforced(client, auth_customer_headers):
    """description > 1000 chars must yield 422."""
    long_desc = "x" * 1001
    res = client.post("/jobs", json={
        "category": "plumber",
        "description": long_desc,
        "location": {"lat": 19.28, "lng": 72.86, "address": "Mira Road"},
    }, headers=auth_customer_headers)
    assert res.status_code == 422


def test_address_max_length_enforced(client, auth_customer_headers):
    """address > 500 chars must yield 422."""
    res = client.post("/jobs", json={
        "category": "plumber",
        "description": "Pipe leak",
        "location": {"lat": 19.28, "lng": 72.86, "address": "A" * 501},
    }, headers=auth_customer_headers)
    assert res.status_code == 422


def test_budget_ceiling_enforced(client, auth_customer_headers):
    """budget > 1,000,000 must yield 422."""
    res = client.post("/jobs", json={
        "category": "plumber",
        "description": "Full renovation",
        "location": {"lat": 19.28, "lng": 72.86, "address": "Mira Road"},
        "budget": 2_000_000.0
    }, headers=auth_customer_headers)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Offer price ceiling
# ---------------------------------------------------------------------------

def test_offer_price_ceiling_enforced(client, auth_customer_headers):
    """Offer price > 10,000,000 must yield 422."""
    res = client.post("/offers", json={
        "jobId": "job_test_open",
        "workerId": "worker_elec_1",
        "price": 20_000_000.0,
    }, headers=auth_customer_headers)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Review / Report blank-after-strip
# ---------------------------------------------------------------------------

def test_review_blank_whitespace_comment_rejected(client, auth_customer_headers):
    """A comment that is only whitespace must yield 422."""
    res = client.post("/reviews", json={
        "jobId": "job_test_completed",
        "workerId": "worker_elec_1",
        "rating": 4.0,
        "comment": "   "
    }, headers=auth_customer_headers)
    assert res.status_code == 422


def test_review_comment_max_length_enforced(client, auth_customer_headers):
    """comment > 2000 chars must yield 422."""
    res = client.post("/reviews", json={
        "jobId": "job_test_completed",
        "workerId": "worker_elec_1",
        "rating": 4.0,
        "comment": "x" * 2001
    }, headers=auth_customer_headers)
    assert res.status_code == 422


def test_report_blank_whitespace_reason_rejected(client, auth_customer_headers):
    """A reason that is only whitespace must yield 422."""
    res = client.post("/reports", json={
        "workerId": "worker_elec_1",
        "reason": "   "
    }, headers=auth_customer_headers)
    assert res.status_code == 422


def test_report_reason_max_length_enforced(client, auth_customer_headers):
    """reason > 2000 chars must yield 422."""
    res = client.post("/reports", json={
        "workerId": "worker_elec_1",
        "reason": "y" * 2001
    }, headers=auth_customer_headers)
    assert res.status_code == 422

