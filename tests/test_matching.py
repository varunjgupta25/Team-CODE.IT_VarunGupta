import math
import pytest
from core.database import db
from services.distance import haversine_distance, calculate_eta, is_within_30_minutes


def test_haversine_distance_known_city_pairs():
    """
    Haversine distance must be within 1% of known spherical distance values.
    """
    # 1. Mumbai (19.0760, 72.8777) to Delhi (28.7041, 77.1025) ~ 1148 km
    dist_mum_del = haversine_distance(19.0760, 72.8777, 28.7041, 77.1025)
    expected_mum_del = 1148.0
    err_mum_del = abs(dist_mum_del - expected_mum_del) / expected_mum_del
    assert err_mum_del < 0.01, f"Mumbai-Delhi error {err_mum_del:.4f} exceeds 1% (dist={dist_mum_del})"

    # 2. New York (40.7128, -74.0060) to London (51.5074, -0.1278) ~ 5570 km
    dist_nyc_lon = haversine_distance(40.7128, -74.0060, 51.5074, -0.1278)
    expected_nyc_lon = 5570.0
    err_nyc_lon = abs(dist_nyc_lon - expected_nyc_lon) / expected_nyc_lon
    assert err_nyc_lon < 0.01, f"NYC-London error {err_nyc_lon:.4f} exceeds 1% (dist={dist_nyc_lon})"

    # 3. Same point distance must be 0
    dist_zero = haversine_distance(19.2825, 72.8570, 19.2825, 72.8570)
    assert math.isclose(dist_zero, 0.0, abs_tol=1e-5)


def test_eta_and_within30_boundary():
    """
    Tests that at speed 25 km/h:
    - Exactly 12.5 km -> ETA = 30.0 minutes -> within30 is True
    - 12.51 km -> ETA > 30.0 minutes -> within30 is False
    - 5.0 km -> ETA = 12.0 minutes -> within30 is True
    """
    speed = 25.0

    # At 12.5 km: ETA = 12.5 / 25 * 60 = 30.0 min
    eta_30 = calculate_eta(12.5, speed_kmh=speed)
    assert math.isclose(eta_30, 30.0, rel_tol=1e-5)
    assert is_within_30_minutes(eta_30) is True

    # Slightly above 30 minutes boundary (12.51 km -> 30.024 min)
    eta_above = calculate_eta(12.51, speed_kmh=speed)
    assert eta_above > 30.0
    assert is_within_30_minutes(eta_above) is False

    # Below 30 minutes
    eta_below = calculate_eta(5.0, speed_kmh=speed)
    assert math.isclose(eta_below, 12.0, rel_tol=1e-5)
    assert is_within_30_minutes(eta_below) is True


def test_matching_filters_unverified_unavailable_wrong_skill_out_of_radius(client, auth_customer_headers):
    """
    Verify that unverified, unavailable, wrong-skill, and out-of-radius workers are strictly excluded.
    """
    # Seed specific workers to test each filter condition
    # Target job is category 'electrician', location: (19.2825, 72.8570)
    test_workers = {
        # 1. Valid matching electrician (should match)
        "w_valid": {
            "uid": "w_valid",
            "name": "Valid Worker",
            "skills": ["electrician"],
            "rates": {"electrician": 400.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.8,
            "jobsDone": 30,
            "location": {"lat": 19.2830, "lng": 72.8575},  # ~0.08 km away
            "serviceRadiusKm": 5.0,
            "isFlagged": False
        },
        # 2. Unverified electrician (must be excluded)
        "w_unverified": {
            "uid": "w_unverified",
            "name": "Unverified Worker",
            "skills": ["electrician"],
            "rates": {"electrician": 300.0},
            "isAvailableNow": True,
            "verified": False,
            "rating": 5.0,
            "jobsDone": 40,
            "location": {"lat": 19.2830, "lng": 72.8575},
            "serviceRadiusKm": 5.0,
            "isFlagged": False
        },
        # 3. Unavailable electrician (must be excluded)
        "w_unavailable": {
            "uid": "w_unavailable",
            "name": "Unavailable Worker",
            "skills": ["electrician"],
            "rates": {"electrician": 350.0},
            "isAvailableNow": False,
            "verified": True,
            "rating": 4.9,
            "jobsDone": 25,
            "location": {"lat": 19.2830, "lng": 72.8575},
            "serviceRadiusKm": 5.0,
            "isFlagged": False
        },
        # 4. Wrong skill (plumber only, must be excluded)
        "w_wrong_skill": {
            "uid": "w_wrong_skill",
            "name": "Plumber Worker",
            "skills": ["plumber"],
            "rates": {"plumber": 350.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 5.0,
            "jobsDone": 50,
            "location": {"lat": 19.2830, "lng": 72.8575},
            "serviceRadiusKm": 5.0,
            "isFlagged": False
        },
        # 5. Out of radius (distance ~15 km, serviceRadiusKm=5.0, must be excluded)
        "w_out_of_radius": {
            "uid": "w_out_of_radius",
            "name": "Far Worker",
            "skills": ["electrician"],
            "rates": {"electrician": 400.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.9,
            "jobsDone": 30,
            "location": {"lat": 19.1500, "lng": 72.8500},  # ~15 km away
            "serviceRadiusKm": 5.0,
            "isFlagged": False
        },
        # 6. Flagged worker (must be excluded)
        "w_flagged": {
            "uid": "w_flagged",
            "name": "Flagged Worker",
            "skills": ["electrician"],
            "rates": {"electrician": 400.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.5,
            "jobsDone": 20,
            "location": {"lat": 19.2830, "lng": 72.8575},
            "serviceRadiusKm": 5.0,
            "isFlagged": True,
            "flagged": True
        }
    }

    # Replace workers collection with our test setup
    db.clear_collection("workers")
    for wid, w in test_workers.items():
        db.set_document("workers", wid, w)

    res = client.get("/workers/match?jobId=job_test_open", headers=auth_customer_headers)
    assert res.status_code == 200, res.text
    matches = res.json()

    matched_uids = [m["worker"]["uid"] for m in matches]

    assert "w_valid" in matched_uids, "Valid worker should be matched"
    assert "w_unverified" not in matched_uids, "Unverified worker must be excluded"
    assert "w_unavailable" not in matched_uids, "Unavailable worker must be excluded"
    assert "w_wrong_skill" not in matched_uids, "Wrong-skill worker must be excluded"
    assert "w_out_of_radius" not in matched_uids, "Out-of-radius worker must be excluded"
    assert "w_flagged" not in matched_uids, "Flagged worker must be excluded"
    assert len(matches) == 1


def test_matching_ranking_order_follows_score(client, auth_customer_headers):
    """
    Tests that matched workers are returned in strictly descending score order.
    Score = distance 40% + rating 30% + price vs budget 20% + jobsDone 10%.
    """
    # Reseed two verified, available electricians at different distances and ratings
    workers = {
        "w_close_high_rated": {
            "uid": "w_close_high_rated",
            "name": "Close High Rated",
            "skills": ["electrician"],
            "rates": {"electrician": 400.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 5.0,
            "jobsDone": 50,
            "location": {"lat": 19.2826, "lng": 72.8571},  # ~0.02 km away
            "serviceRadiusKm": 5.0,
            "isFlagged": False
        },
        "w_farther_lower_rated": {
            "uid": "w_farther_lower_rated",
            "name": "Farther Lower Rated",
            "skills": ["electrician"],
            "rates": {"electrician": 550.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.0,
            "jobsDone": 10,
            "location": {"lat": 19.3000, "lng": 72.8650},  # ~2.1 km away
            "serviceRadiusKm": 5.0,
            "isFlagged": False
        }
    }

    db.clear_collection("workers")
    for wid, w in workers.items():
        db.set_document("workers", wid, w)

    res = client.get("/workers/match?jobId=job_test_open", headers=auth_customer_headers)
    assert res.status_code == 200
    matches = res.json()

    assert len(matches) == 2
    scores = [m["score"] for m in matches]
    assert scores[0] >= scores[1], "Matches must be ordered descending by score"
    assert matches[0]["worker"]["uid"] == "w_close_high_rated"
    assert matches[1]["worker"]["uid"] == "w_farther_lower_rated"

    # Verify score components
    top = matches[0]
    assert "distanceKm" in top
    assert "etaMinutes" in top
    assert "within30" in top
    assert top["within30"] is True
    assert "trustBadge" in top
    assert top["trustBadge"] in ["Gold", "Silver", "Bronze", "New"]


def test_matching_nonexistent_job_returns_404(client, auth_customer_headers):
    res = client.get("/workers/match?jobId=nonexistent_job_xyz", headers=auth_customer_headers)
    assert res.status_code == 404
