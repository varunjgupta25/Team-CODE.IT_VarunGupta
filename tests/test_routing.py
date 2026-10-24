"""
tests/test_routing.py

Unit / integration tests for Stage A (routing.py) and Stage B (h3_index.py)
and their integration into the matching pipeline.

All tests run without a real OSM graph or internet:
- routing.py tests use a minimal synthetic networkx graph.
- h3_index.py tests rely on the real h3 library (installed).
- Matching integration tests mock load_graph() / road_eta() via monkeypatch.
"""

import importlib
import math
import types
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────── helpers ─────────────────────────────────────────

def _make_synthetic_graph():
    """
    Tiny 3-node networkx MultiDiGraph:
        A(19.28, 72.87) -- 500 m / 60 s --> B(19.284, 72.874)
        B              -- 500 m / 60 s --> C(19.288, 72.878)
    """
    nx = pytest.importorskip("networkx")
    G = nx.MultiDiGraph()
    # nodes: id, y=lat, x=lng
    nodes = [
        (0, {"y": 19.280, "x": 72.870}),
        (1, {"y": 19.284, "x": 72.874}),
        (2, {"y": 19.288, "x": 72.878}),
    ]
    G.add_nodes_from(nodes)
    G.add_edge(0, 1, 0, length=500.0, travel_time=60.0)
    G.add_edge(1, 0, 0, length=500.0, travel_time=60.0)
    G.add_edge(1, 2, 0, length=500.0, travel_time=60.0)
    G.add_edge(2, 1, 0, length=500.0, travel_time=60.0)
    return G


# ─────────────────────────── routing.py tests ────────────────────────────────

class TestLoadGraph:
    def test_returns_none_when_file_missing(self, tmp_path, monkeypatch):
        """load_graph() must return None (not raise) when GraphML is absent."""
        import services.routing as routing
        monkeypatch.setattr(routing, "_graph", None)
        monkeypatch.setattr(routing, "_graph_loaded", False)
        monkeypatch.setattr(routing, "_GRAPH_PATH", str(tmp_path / "nonexistent.graphml"))
        result = routing.load_graph()
        assert result is None

    def test_returns_cached_graph_on_second_call(self, monkeypatch):
        """load_graph() must not re-load; returns the same object."""
        import services.routing as routing
        sentinel = object()
        monkeypatch.setattr(routing, "_graph", sentinel)
        monkeypatch.setattr(routing, "_graph_loaded", True)
        assert routing.load_graph() is sentinel


class TestRoadRoute:
    def _patch_graph(self, monkeypatch, G):
        import services.routing as routing
        monkeypatch.setattr(routing, "_graph", G)
        monkeypatch.setattr(routing, "_graph_loaded", True)

    def test_returns_none_when_graph_not_loaded(self, monkeypatch):
        import services.routing as routing
        monkeypatch.setattr(routing, "_graph", None)
        monkeypatch.setattr(routing, "_graph_loaded", True)
        assert routing.road_route(19.28, 72.87, 19.29, 72.88) is None

    def test_valid_route_returns_dict(self, monkeypatch):
        """road_route returns dict with correct keys for a synthetic graph."""
        nx = pytest.importorskip("networkx")
        ox = pytest.importorskip("osmnx")
        G = _make_synthetic_graph()
        self._patch_graph(monkeypatch, G)

        # Patch nearest_nodes to return node 0 for origin and node 2 for dest
        call_count = {"n": 0}
        def fake_nearest(graph, X, Y, return_dist=False):
            node = 0 if call_count["n"] == 0 else 2
            call_count["n"] += 1
            if return_dist:
                return node, 10.0   # 10 m snap distance
            return node

        import services.routing as routing
        with patch("osmnx.nearest_nodes", side_effect=fake_nearest):
            result = routing.road_route(19.280, 72.870, 19.288, 72.878)

        assert result is not None
        assert "distanceKm" in result
        assert "etaMinutes" in result
        assert "polyline" in result
        # 2 edges × 500 m = 1000 m = 1.0 km
        assert abs(result["distanceKm"] - 1.0) < 0.01
        # 2 edges × 60 s = 120 s = 2.0 min
        assert abs(result["etaMinutes"] - 2.0) < 0.1
        # polyline should have 3 points
        assert len(result["polyline"]) == 3

    def test_snap_too_far_returns_none(self, monkeypatch):
        """road_route must return None if snap distance > 1 km."""
        nx = pytest.importorskip("networkx")
        G = _make_synthetic_graph()
        self._patch_graph(monkeypatch, G)

        def fake_nearest(graph, X, Y, return_dist=False):
            if return_dist:
                return 0, 5000.0   # 5 km > 1 km limit
            return 0

        with patch("osmnx.nearest_nodes", side_effect=fake_nearest):
            import services.routing as routing
            result = routing.road_route(99.0, 99.0, 99.1, 99.1)
        assert result is None

    def test_no_path_returns_none(self, monkeypatch):
        """road_route must return None when no path exists."""
        nx = pytest.importorskip("networkx")
        G = _make_synthetic_graph()
        # Add isolated node 99 – no edges to/from it
        G.add_node(99, y=19.300, x=72.900)
        self._patch_graph(monkeypatch, G)

        call_count = {"n": 0}
        def fake_nearest(graph, X, Y, return_dist=False):
            node = 0 if call_count["n"] == 0 else 99
            call_count["n"] += 1
            if return_dist:
                return node, 10.0
            return node

        with patch("osmnx.nearest_nodes", side_effect=fake_nearest):
            import services.routing as routing
            result = routing.road_route(19.280, 72.870, 19.300, 72.900)
        assert result is None


class TestRoadEta:
    def test_road_eta_wraps_road_route(self, monkeypatch):
        import services.routing as routing
        monkeypatch.setattr(
            routing, "road_route",
            lambda *a, **k: {"distanceKm": 3.5, "etaMinutes": 7.0, "polyline": []}
        )
        dist, eta = routing.road_eta(0, 0, 1, 1)
        assert dist == 3.5
        assert eta == 7.0

    def test_road_eta_returns_none_on_failure(self, monkeypatch):
        import services.routing as routing
        monkeypatch.setattr(routing, "road_route", lambda *a, **k: None)
        dist, eta = routing.road_eta(0, 0, 1, 1)
        assert dist is None
        assert eta is None


# ─────────────────────────── h3_index.py tests ───────────────────────────────

class TestH3Index:
    def test_to_cell_returns_string(self):
        h3 = pytest.importorskip("h3")
        from services.h3_index import to_cell
        cell = to_cell(19.2813, 72.8688, resolution=8)
        assert isinstance(cell, str)
        assert len(cell) > 0

    def test_cells_within_contains_centre(self):
        h3 = pytest.importorskip("h3")
        from services.h3_index import cells_within, to_cell
        lat, lng = 19.2813, 72.8688
        disk = cells_within(lat, lng, radius_km=2.0, resolution=8)
        centre = to_cell(lat, lng, resolution=8)
        assert centre in disk

    def test_cells_within_nearby_included(self):
        h3 = pytest.importorskip("h3")
        from services.h3_index import cells_within, to_cell
        lat, lng = 19.2813, 72.8688
        disk = cells_within(lat, lng, radius_km=5.0, resolution=8)
        # A point ~2 km away should be in the disk
        nearby_cell = to_cell(19.299, 72.868, resolution=8)
        assert nearby_cell in disk

    def test_filter_workers_keeps_nearby(self):
        pytest.importorskip("h3")
        from services.h3_index import filter_workers_by_h3
        workers = [
            {"uid": "w1", "location": {"lat": 19.2813, "lng": 72.8688}},   # exact centre
            {"uid": "w2", "location": {"lat": 19.282,  "lng": 72.869}},    # ~0.2 km away
            {"uid": "w3", "location": {"lat": 19.700,  "lng": 73.500}},    # ~55 km away
        ]
        result = filter_workers_by_h3(workers, 19.2813, 72.8688, radius_km=5.0)
        uids = {w["uid"] for w in result}
        assert "w1" in uids
        assert "w2" in uids
        assert "w3" not in uids

    def test_filter_fallback_when_all_removed(self):
        """If all workers are filtered out, original list is returned."""
        pytest.importorskip("h3")
        from services.h3_index import filter_workers_by_h3
        far_workers = [
            {"uid": "wX", "location": {"lat": 28.6, "lng": 77.2}},  # Delhi – far from Mumbai
        ]
        result = filter_workers_by_h3(far_workers, 19.2813, 72.8688, radius_km=1.0)
        # Fallback: original list returned unchanged
        assert result == far_workers

    def test_filter_skips_workers_without_location(self):
        pytest.importorskip("h3")
        from services.h3_index import filter_workers_by_h3
        workers = [
            {"uid": "wOK", "location": {"lat": 19.2813, "lng": 72.8688}},
            {"uid": "wNoLoc"},  # missing location key
            {"uid": "wPartial", "location": {"lat": 19.282}},  # missing lng
        ]
        result = filter_workers_by_h3(workers, 19.2813, 72.8688, radius_km=5.0)
        uids = {w["uid"] for w in result}
        assert "wOK" in uids
        # workers with missing coords are dropped from filtered set
        assert "wNoLoc" not in uids
        assert "wPartial" not in uids


# ────────────────────── matching pipeline integration ────────────────────────

class TestMatchingWithRouting:
    """
    Tests that verify the matching pipeline correctly integrates Dijkstra
    routing and H3 filtering, using monkeypatching instead of real services.
    """

    def _setup_db(self, monkeypatch):
        from core.database import db
        from services.trust import get_worker_trust_info

        job = {
            "id": "job1",
            "category": "plumber",
            "location": {"lat": 19.2813, "lng": 72.8688},
            "budget": 800,
            "status": "open",
        }

        def _worker(uid, dist_deg, rating=4.5, jobs_done=10):
            """Create a worker `dist_deg` degrees away from job centre."""
            return {
                "id": uid,
                "uid": uid,
                "name": f"Worker {uid}",
                "skills": ["plumber"],
                "rates": {"plumber": 600},
                "rating": rating,
                "jobsDone": jobs_done,
                "verified": True,
                "isAvailableNow": True,
                "serviceRadiusKm": 20.0,
                "location": {"lat": 19.2813 + dist_deg, "lng": 72.8688},
            }

        workers = [_worker("wA", 0.01), _worker("wB", 0.02), _worker("wC", 0.03),
                   _worker("wD", 0.04), _worker("wE", 0.05), _worker("wF", 0.06)]

        monkeypatch.setattr(db, "get_document", lambda col, id: job if col == "jobs" else None)
        monkeypatch.setattr(db, "list_collection", lambda col: workers if col == "workers" else [])
        monkeypatch.setattr(db, "query_collection", lambda col, q: [])
        return workers

    def test_matching_fallback_when_no_routing(self, monkeypatch):
        """
        If routing returns None, matching must still succeed using Haversine.
        etaMinutes must be positive.
        """
        self._setup_db(monkeypatch)

        # Disable routing by making road_eta return (None, None)
        with patch("services.routing.road_eta", return_value=(None, None)):
            from services import matching
            importlib.reload(matching)
            # Force routing to appear as loaded but returning None
            monkeypatch.setattr(matching, "_routing",
                                lambda: (lambda *a, **k: (None, None), None))
            results = matching.match_workers_for_job("job1")

        assert len(results) >= 1
        for r in results:
            assert r["etaMinutes"] > 0
            assert r["distanceKm"] > 0
            assert "polyline" not in r  # polyline only in /route endpoint

    def test_matching_uses_road_eta_for_top5(self, monkeypatch):
        """
        When road_eta succeeds, top-5 workers must have etaMinutes == road value.
        """
        self._setup_db(monkeypatch)

        ROAD_ETA = 3.3
        ROAD_DIST = 1.5

        def fake_road_eta(lat1, lng1, lat2, lng2):
            return ROAD_DIST, ROAD_ETA

        from services import matching as m_mod
        importlib.reload(m_mod)
        monkeypatch.setattr(m_mod, "_routing", lambda: (fake_road_eta, None))
        monkeypatch.setattr(m_mod, "_h3_filter", lambda: None)  # skip H3

        results = m_mod.match_workers_for_job("job1")
        # Top workers should have road ETA
        for entry in results[:5]:
            assert abs(entry["etaMinutes"] - ROAD_ETA) < 0.01
            assert abs(entry["distanceKm"] - ROAD_DIST) < 0.01

    def test_top5_sorted_by_road_eta(self, monkeypatch):
        """Top-5 results are sorted by road ETA ascending after Dijkstra."""
        self._setup_db(monkeypatch)

        call_order = {"n": 0}
        etas = [5.0, 2.0, 8.0, 1.0, 4.0]  # out-of-order ETAs

        def fake_road_eta(lat1, lng1, lat2, lng2):
            idx = call_order["n"] % len(etas)
            call_order["n"] += 1
            return 1.0, etas[idx]

        from services import matching as m_mod
        importlib.reload(m_mod)
        monkeypatch.setattr(m_mod, "_routing", lambda: (fake_road_eta, None))
        monkeypatch.setattr(m_mod, "_h3_filter", lambda: None)

        results = m_mod.match_workers_for_job("job1")
        top = results[:5]
        etas_out = [r["etaMinutes"] for r in top]
        assert etas_out == sorted(etas_out), f"Top-5 not sorted by ETA: {etas_out}"


# ──────────────────────────── /route endpoint ────────────────────────────────

class TestRouteEndpoint:
    def _make_client(self):
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)

    def _auth_headers(self, client):
        """Reuse the existing auth-mock mechanism from conftest if present."""
        return {"Authorization": "Bearer test_customer_token"}

    def test_route_returns_haversine_fallback(self, monkeypatch):
        """
        When the road graph is unavailable, /route returns Haversine values
        with an empty polyline.
        """
        import services.routing as routing
        monkeypatch.setattr(routing, "_graph", None)
        monkeypatch.setattr(routing, "_graph_loaded", True)

        from core.database import db
        job    = {"id": "j1", "location": {"lat": 19.2813, "lng": 72.8688},
                  "category": "plumber", "status": "open"}
        worker = {"id": "w1", "uid": "w1", "location": {"lat": 19.285, "lng": 72.872}}

        def fake_get(col, id):
            if col == "jobs":   return job
            if col == "workers": return worker
            return None

        monkeypatch.setattr(db, "get_document", fake_get)
        monkeypatch.setattr(db, "list_collection", lambda c: [])
        monkeypatch.setattr(db, "query_collection", lambda c, q: [])

        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app) as client:
            resp = client.get(
                "/api/route?jobId=j1&workerId=w1",
                headers={"Authorization": "Bearer test_customer_token"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "distanceKm" in body
        assert "etaMinutes" in body
        assert body["polyline"] == []
        assert body["distanceKm"] > 0
        assert body["etaMinutes"] > 0

    def test_route_404_for_unknown_job(self, monkeypatch):
        from core.database import db
        from core.auth import get_current_user
        from main import app

        def fake_get(col, id):
            return None  # every lookup returns None → job not found

        monkeypatch.setattr(db, "get_document", fake_get)
        monkeypatch.setattr(db, "list_collection", lambda c: [])
        monkeypatch.setattr(db, "query_collection", lambda c, q: [])

        def mock_user():
            return {"uid": "cust_test_1", "role": "customer", "name": "T", "is_firebase": False}
        app.dependency_overrides[get_current_user] = mock_user

        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            resp = client.get("/api/route?jobId=missing&workerId=w1")
        app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_route_404_for_unknown_worker(self, monkeypatch):
        from core.database import db
        from core.auth import get_current_user
        from main import app

        job = {"id": "j1", "location": {"lat": 19.2813, "lng": 72.8688},
               "category": "plumber", "status": "open"}

        def fake_get(col, id):
            if col == "jobs": return job
            return None  # worker not found

        monkeypatch.setattr(db, "get_document", fake_get)
        monkeypatch.setattr(db, "list_collection", lambda c: [])
        monkeypatch.setattr(db, "query_collection", lambda c, q: [])

        def mock_user():
            return {"uid": "cust_test_1", "role": "customer", "name": "T", "is_firebase": False}
        app.dependency_overrides[get_current_user] = mock_user

        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            resp = client.get("/api/route?jobId=j1&workerId=missing")
        app.dependency_overrides.clear()
        assert resp.status_code == 404
