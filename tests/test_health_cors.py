"""
tests/test_health_cors.py

Tests for:
1. /health returns 200 with status and mock_mode.
2. /api/health also returns 200 (both prefixes supported).
3. CORS preflight allows Origin: http://localhost:5173.
4. Core endpoints answer on both "/x" and "/api/x".
"""

import pytest
from core.config import settings


def test_health_endpoint_root_and_api(client):
    """
    GET /health and GET /api/health return 200 with status, mock_mode, and transit_speed_kmh.
    """
    for path in ["/health", "/api/health"]:
        res = client.get(path)
        assert res.status_code == 200, f"{path} failed with {res.status_code}"
        data = res.json()
        assert data["status"] == "healthy"
        assert "mock_mode" in data
        assert data["mock_mode"] == settings.USE_MOCK_FIREBASE
        assert data["transit_speed_kmh"] == settings.TRANSIT_SPEED_KMH


def test_cors_preflight_allows_frontend_origin(client):
    """
    OPTIONS preflight request from http://localhost:5173 returns allowed CORS headers.
    """
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    for path in ["/jobs", "/api/jobs", "/health", "/api/health"]:
        res = client.options(path, headers=headers)
        assert res.status_code == 200, f"CORS preflight failed for {path}"
        assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_endpoints_mounted_on_both_prefixes(client, auth_customer_headers, auth_worker_headers):
    """
    Endpoints respond consistently on both "/" and "/api/" prefixes.
    """
    # 1. GET /jobs/{id} and /api/jobs/{id}
    res1 = client.get("/jobs/job_test_open", headers=auth_customer_headers)
    res2 = client.get("/api/jobs/job_test_open", headers=auth_customer_headers)
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["id"] == res2.json()["id"]

    # 2. GET /workers/match and /api/workers/match
    res3 = client.get("/workers/match?jobId=job_test_open", headers=auth_customer_headers)
    res4 = client.get("/api/workers/match?jobId=job_test_open", headers=auth_customer_headers)
    assert res3.status_code == 200
    assert res4.status_code == 200
    assert len(res3.json()) == len(res4.json())

    # 3. GET /jobs/nearby and /api/jobs/nearby
    res5 = client.get("/jobs/nearby", headers=auth_worker_headers)
    res6 = client.get("/api/jobs/nearby", headers=auth_worker_headers)
    assert res5.status_code == 200
    assert res6.status_code == 200
