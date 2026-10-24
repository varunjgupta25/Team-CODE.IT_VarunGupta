import pytest


def test_post_jobs_validation_errors(client, auth_customer_headers):
    """
    POST /jobs validation:
    - Missing required fields (category, description, location) -> 422
    - Lat out of range (< -90 or > 90) -> 422
    - Lng out of range (< -180 or > 180) -> 422
    - Negative or zero budget -> 422
    - Returns 422, NEVER 500.
    """
    # 1. Missing description and category
    res = client.post("/jobs", json={
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road"}
    }, headers=auth_customer_headers)
    assert res.status_code == 422
    assert "detail" in res.json()

    # 2. Latitude out of range (> 90)
    res = client.post("/jobs", json={
        "category": "electrician",
        "description": "Wiring repair",
        "location": {"lat": 95.0, "lng": 72.8570, "address": "Mira Road"}
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 3. Latitude out of range (< -90)
    res = client.post("/jobs", json={
        "category": "electrician",
        "description": "Wiring repair",
        "location": {"lat": -95.0, "lng": 72.8570, "address": "Mira Road"}
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 4. Longitude out of range (> 180)
    res = client.post("/jobs", json={
        "category": "electrician",
        "description": "Wiring repair",
        "location": {"lat": 19.2825, "lng": 185.0, "address": "Mira Road"}
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 5. Longitude out of range (< -180)
    res = client.post("/jobs", json={
        "category": "electrician",
        "description": "Wiring repair",
        "location": {"lat": 19.2825, "lng": -190.0, "address": "Mira Road"}
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 6. Negative budget
    res = client.post("/jobs", json={
        "category": "electrician",
        "description": "Wiring repair",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road"},
        "budget": -100.0
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 7. Zero budget (budget must be gt 0)
    res = client.post("/jobs", json={
        "category": "electrician",
        "description": "Wiring repair",
        "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road"},
        "budget": 0.0
    }, headers=auth_customer_headers)
    assert res.status_code == 422


def test_post_offers_validation_errors(client, auth_customer_headers, auth_worker_headers):
    """
    POST /offers validation:
    - Missing required fields (jobId, workerId, price) -> 422
    - Negative price -> 422
    - Zero price -> 422
    - Counter offer with negative price -> 422
    """
    # 1. Missing price and workerId
    res = client.post("/offers", json={
        "jobId": "job_test_open"
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 2. Negative price
    res = client.post("/offers", json={
        "jobId": "job_test_open",
        "workerId": "worker_elec_1",
        "price": -50.0
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 3. Zero price
    res = client.post("/offers", json={
        "jobId": "job_test_open",
        "workerId": "worker_elec_1",
        "price": 0.0
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 4. Valid offer created
    res_valid = client.post("/offers", json={
        "jobId": "job_test_open",
        "workerId": "worker_elec_1",
        "price": 400.0,
        "by": "customer"
    }, headers=auth_customer_headers)
    assert res_valid.status_code == 201
    offer_id = res_valid.json()["id"]

    # 5. Counter with negative price -> 422
    res_counter_neg = client.post(f"/offers/{offer_id}/counter", json={"price": -100.0}, headers=auth_worker_headers)
    assert res_counter_neg.status_code == 422

    # 6. Counter with zero price -> 422
    res_counter_zero = client.post(f"/offers/{offer_id}/counter", json={"price": 0.0}, headers=auth_worker_headers)
    assert res_counter_zero.status_code == 422


def test_post_reviews_validation_errors(client, auth_customer_headers):
    """
    POST /reviews validation:
    - Rating < 1.0 -> 422
    - Rating > 5.0 -> 422
    - Missing required comment -> 422
    - Empty comment -> 422
    """
    # 1. Rating < 1.0
    res = client.post("/reviews", json={
        "jobId": "job_test_completed",
        "workerId": "worker_elec_1",
        "rating": 0.5,
        "comment": "Bad"
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 2. Rating > 5.0
    res = client.post("/reviews", json={
        "jobId": "job_test_completed",
        "workerId": "worker_elec_1",
        "rating": 6.0,
        "comment": "Super"
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 3. Missing comment
    res = client.post("/reviews", json={
        "jobId": "job_test_completed",
        "workerId": "worker_elec_1",
        "rating": 4.0
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 4. Empty comment
    res = client.post("/reviews", json={
        "jobId": "job_test_completed",
        "workerId": "worker_elec_1",
        "rating": 4.0,
        "comment": ""
    }, headers=auth_customer_headers)
    assert res.status_code == 422


def test_post_sos_and_reports_validation_errors(client, auth_customer_headers):
    """
    POST /sos and POST /reports validation:
    - SOS with invalid coordinates -> 422
    - Report with missing workerId or empty reason -> 422
    """
    # 1. SOS with lat > 90
    res = client.post("/sos", json={
        "location": {"lat": 100.0, "lng": 72.8570}
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 2. SOS with missing location
    res = client.post("/sos", json={}, headers=auth_customer_headers)
    assert res.status_code == 422

    # 3. Report with missing workerId
    res = client.post("/reports", json={
        "reason": "Unprofessional behavior"
    }, headers=auth_customer_headers)
    assert res.status_code == 422

    # 4. Report with empty reason
    res = client.post("/reports", json={
        "workerId": "worker_elec_1",
        "reason": ""
    }, headers=auth_customer_headers)
    assert res.status_code == 422
