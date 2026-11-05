"""
Loop 5: Rate Limiting Tests
- 429 is returned when burst limit is exhausted for SOS group
- Rate-limit headers are present on successful responses
- Health endpoint is never rate-limited
- Different IPs have independent buckets
- clear_all_buckets() resets state between tests
"""
import pytest
from fastapi.testclient import TestClient
from core.rate_limit import clear_all_buckets


@pytest.fixture(autouse=True)
def reset_rate_buckets():
    """Clear token buckets before every rate-limit test."""
    clear_all_buckets()
    yield
    clear_all_buckets()


def test_rate_limit_headers_present(client, auth_customer_headers):
    """Successful responses include X-RateLimit-* headers."""
    res = client.get("/health")
    # /health is in SKIP_PATHS — headers not injected
    res2 = client.get("/jobs/nonexistent_job_id", headers=auth_customer_headers)
    # 404 is still a valid response with headers
    assert "x-ratelimit-limit" in res2.headers
    assert "x-ratelimit-remaining" in res2.headers
    assert "x-ratelimit-reset" in res2.headers


def test_health_endpoint_never_rate_limited(client):
    """Health check must never return 429 regardless of call frequency."""
    for _ in range(20):
        res = client.get("/health")
        assert res.status_code == 200


def test_sos_rate_limit_triggers_429(client, auth_customer_headers):
    """
    SOS bucket allows 5 requests per minute.
    The 6th request within the same second must return 429.
    """
    payload = {"location": {"lat": 19.28, "lng": 72.86}}
    success_count = 0
    for _ in range(6):
        res = client.post("/sos", json=payload, headers=auth_customer_headers)
        if res.status_code == 201:
            success_count += 1

    # The first 5 should succeed; at least one of the 6 must be 429
    assert success_count <= 5

    # Explicitly verify the 7th call returns 429
    res = client.post("/sos", json=payload, headers=auth_customer_headers)
    assert res.status_code == 429
    body = res.json()
    assert "detail" in body
    assert "rate limit" in body["detail"].lower()


def test_429_response_includes_retry_after(client, auth_customer_headers):
    """429 response must include Retry-After header."""
    payload = {"location": {"lat": 19.28, "lng": 72.86}}
    # Exhaust SOS bucket
    for _ in range(6):
        client.post("/sos", json=payload, headers=auth_customer_headers)
    res = client.post("/sos", json=payload, headers=auth_customer_headers)
    assert res.status_code == 429
    assert "retry-after" in res.headers
    assert int(res.headers["retry-after"]) > 0


def test_rate_limit_buckets_are_per_ip(client, auth_customer_headers, auth_customer_2_headers):
    """
    Two different clients (simulated by different test client instances with
    custom X-Forwarded-For headers) should have independent buckets.
    """
    payload = {"location": {"lat": 19.28, "lng": 72.86}}
    headers_ip1 = {**auth_customer_headers, "X-Forwarded-For": "1.2.3.4"}
    headers_ip2 = {**auth_customer_2_headers, "X-Forwarded-For": "5.6.7.8"}

    # Exhaust IP1's SOS bucket
    for _ in range(6):
        client.post("/sos", json=payload, headers=headers_ip1)

    # IP1 should now be rate-limited
    res_ip1 = client.post("/sos", json=payload, headers=headers_ip1)
    assert res_ip1.status_code == 429

    # IP2 should NOT be rate-limited (independent bucket)
    res_ip2 = client.post("/sos", json=payload, headers=headers_ip2)
    assert res_ip2.status_code == 201

