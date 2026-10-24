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

    def test_road_route_picks_fastest_path_over_shortest_distance(self, monkeypatch):
        """road_route must pick the fastest (travel_time) path, not the shortest distance."""
        nx = pytest.importorskip("networkx")
        ox = pytest.importorskip("osmnx")

        # Graph with two paths between node 0 and node 1:
        # Path A (via 2): shorter distance (200m), slower (120s)
        # Path B (via 3): longer distance (800m), faster (30s)
        G = nx.MultiDiGraph()
        nodes = [
            (0, {"y": 19.280, "x": 72.870}),
            (1, {"y": 19.284, "x": 72.874}),
            (2, {"y": 19.281, "x": 72.871}),
            (3, {"y": 19.283, "x": 72.873}),
        ]
        G.add_nodes_from(nodes)
        # Path A: 0 -> 2 -> 1
        G.add_edge(0, 2, 0, length=100.0, travel_time=60.0)
        G.add_edge(2, 1, 0, length=100.0, travel_time=60.0)
        # Path B: 0 -> 3 -> 1
        G.add_edge(0, 3, 0, length=400.0, travel_time=15.0)
        G.add_edge(3, 1, 0, length=400.0, travel_time=15.0)

        self._patch_graph(monkeypatch, G)

        call_count = {"n": 0}
        def fake_nearest(graph, X, Y, return_dist=False):
            node = 0 if call_count["n"] == 0 else 1
            call_count["n"] += 1
            if return_dist:
                return node, 10.0
            return node

        import services.routing as routing
        with patch("osmnx.nearest_nodes", side_effect=fake_nearest):
            result = routing.road_route(19.280, 72.870, 19.284, 72.874)

        assert result is not None
        # Dijkstra should pick Path B with 30s travel_time = 0.5 minutes
        assert abs(result["etaMinutes"] - 0.5) < 0.05
        # Total distance is 800m = 0.8km
        assert abs(result["distanceKm"] - 0.8) < 0.05
        # Polyline contains node 3, not node 2
        path_coords = result["polyline"]
        assert len(path_coords) == 3
        assert path_coords[1] == [19.283, 72.873]



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
    def test_route_200_valid_job_worker_returns_polyline(self, monkeypatch):
        """Valid job and worker with existing road route returns 200 with polyline."""
        from core.database import db
        from core.auth import get_current_user
        from main import app
        import services.routing as routing

        job = {
            "id": "job_r1",
            "customerId": "cust_test_1",
            "location": {"lat": 19.280, "lng": 72.870},
            "category": "plumber",
            "status": "open"
        }
        worker = {
            "id": "worker_elec_1",
            "uid": "worker_elec_1",
            "location": {"lat": 19.288, "lng": 72.878}
        }

        monkeypatch.setattr(db, "get_document", lambda col, id: job if col == "jobs" else (worker if col == "workers" else None))
        monkeypatch.setattr(db, "list_collection", lambda c: [])
        monkeypatch.setattr(db, "query_collection", lambda c, q: [])

        # Mock road_route to return synthetic route
        fake_route = {
            "distanceKm": 1.25,
            "etaMinutes": 2.5,
            "polyline": [[19.280, 72.870], [19.284, 72.874], [19.288, 72.878]]
        }
        monkeypatch.setattr(routing, "road_route", lambda *a, **k: fake_route)

        app.dependency_overrides[get_current_user] = lambda: {"uid": "cust_test_1", "role": "customer", "name": "Priya", "is_firebase": False}

        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            resp = client.get("/api/route?jobId=job_r1&workerId=worker_elec_1")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert body["distanceKm"] == 1.25
        assert body["etaMinutes"] == 2.5
        assert len(body["polyline"]) >= 2
        assert body["polyline"] == fake_route["polyline"]

    def test_route_404_when_no_route(self, monkeypatch):
        """When road_route returns None (no road route exists), /route returns 404."""
        from core.database import db
        from core.auth import get_current_user
        from main import app
        import services.routing as routing

        job = {
            "id": "job_r1",
            "customerId": "cust_test_1",
            "location": {"lat": 19.280, "lng": 72.870},
            "category": "plumber",
            "status": "open"
        }
        worker = {
            "id": "worker_elec_1",
            "uid": "worker_elec_1",
            "location": {"lat": 19.288, "lng": 72.878}
        }

        monkeypatch.setattr(db, "get_document", lambda col, id: job if col == "jobs" else (worker if col == "workers" else None))
        monkeypatch.setattr(db, "list_collection", lambda c: [])
        monkeypatch.setattr(db, "query_collection", lambda c, q: [])
        monkeypatch.setattr(routing, "road_route", lambda *a, **k: None)

        app.dependency_overrides[get_current_user] = lambda: {"uid": "cust_test_1", "role": "customer", "name": "Priya", "is_firebase": False}

        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            resp = client.get("/api/route?jobId=job_r1&workerId=worker_elec_1")
        app.dependency_overrides.clear()

        assert resp.status_code == 404
        assert "no road route found" in resp.json()["detail"].lower()

    def test_route_401_without_token(self):
        """Calling /route without token returns 401 Unauthorized."""
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app) as client:
            resp = client.get("/api/route?jobId=job_test_open&workerId=worker_elec_1")
        assert resp.status_code == 401

    def test_route_403_for_non_participant(self, monkeypatch):
        """A user who is neither the job customer nor the target worker nor admin gets 403."""
        from core.database import db
        from core.auth import get_current_user
        from main import app

        job = {
            "id": "job_r1",
            "customerId": "cust_test_1",
            "location": {"lat": 19.280, "lng": 72.870},
            "category": "plumber",
            "status": "open"
        }
        worker = {
            "id": "worker_elec_1",
            "uid": "worker_elec_1",
            "location": {"lat": 19.288, "lng": 72.878}
        }

        monkeypatch.setattr(db, "get_document", lambda col, id: job if col == "jobs" else (worker if col == "workers" else None))
        monkeypatch.setattr(db, "list_collection", lambda c: [])
        monkeypatch.setattr(db, "query_collection", lambda c, q: [])

        # Third party customer calls route
        app.dependency_overrides[get_current_user] = lambda: {"uid": "cust_test_2", "role": "customer", "name": "Amit", "is_firebase": False}

        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            resp = client.get("/api/route?jobId=job_r1&workerId=worker_elec_1")
        app.dependency_overrides.clear()

        assert resp.status_code == 403

    def test_route_404_for_unknown_job(self, monkeypatch):
        from core.database import db
        from core.auth import get_current_user
        from main import app

        monkeypatch.setattr(db, "get_document", lambda col, id: None)
        monkeypatch.setattr(db, "list_collection", lambda c: [])
        monkeypatch.setattr(db, "query_collection", lambda c, q: [])

        app.dependency_overrides[get_current_user] = lambda: {"uid": "cust_test_1", "role": "customer", "name": "T", "is_firebase": False}

        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            resp = client.get("/api/route?jobId=missing&workerId=w1")
        app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_route_404_for_unknown_worker(self, monkeypatch):
        from core.database import db
        from core.auth import get_current_user
        from main import app

        job = {"id": "j1", "customerId": "cust_test_1", "location": {"lat": 19.2813, "lng": 72.8688},
               "category": "plumber", "status": "open"}

        monkeypatch.setattr(db, "get_document", lambda col, id: job if col == "jobs" else None)
        monkeypatch.setattr(db, "list_collection", lambda c: [])
        monkeypatch.setattr(db, "query_collection", lambda c, q: [])

        app.dependency_overrides[get_current_user] = lambda: {"uid": "cust_test_1", "role": "customer", "name": "T", "is_firebase": False}

        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            resp = client.get("/api/route?jobId=j1&workerId=missing")
        app.dependency_overrides.clear()
        assert resp.status_code == 404


class TestRoutingInternalCoverage:
    def test_load_graph_import_error(self, monkeypatch):
        """When osmnx or networkx are missing, load_graph returns None."""
        import services.routing as routing
        monkeypatch.setattr(routing, "_graph", None)
        monkeypatch.setattr(routing, "_graph_loaded", False)
        monkeypatch.setattr(routing, "_try_import", lambda: (_ for _ in ()).throw(ImportError("missing ox")))

        assert routing.load_graph() is None

    def test_load_graph_from_existing_file(self, monkeypatch):
        """When GraphML cache exists, load_graph loads and returns the graph."""
        import services.routing as routing
        nx = pytest.importorskip("networkx")
        G = nx.MultiDiGraph()
        G.add_node(1, y=19.28, x=72.87)
        G.add_edge(1, 1, 0, length=100.0, travel_time=10.0)

        monkeypatch.setattr(routing, "_graph", None)
        monkeypatch.setattr(routing, "_graph_loaded", False)
        monkeypatch.setattr("os.path.exists", lambda path: True)

        fake_ox = MagicMock()
        fake_ox.load_graphml.return_value = G
        fake_ox.add_edge_speeds.return_value = G
        fake_ox.add_edge_travel_times.return_value = G
        monkeypatch.setattr(routing, "_try_import", lambda: (nx, fake_ox))

        result = routing.load_graph()
        assert result is G

    def test_ensure_travel_time_fallback(self):
        """When add_edge_speeds raises an exception, fallback computes travel_time from length."""
        import services.routing as routing
        nx = pytest.importorskip("networkx")
        G = nx.MultiDiGraph()
        G.add_node(1, y=19.28, x=72.87)
        G.add_edge(1, 1, 0, length=500.0)  # missing travel_time

        fake_ox = MagicMock()
        fake_ox.add_edge_speeds.side_effect = Exception("Not supported")

        res_G = routing._ensure_travel_time(fake_ox, G)
        edge_data = list(res_G.edges(data=True))[0][2]
        assert "travel_time" in edge_data
        assert edge_data["travel_time"] > 0

    def test_snap_node_exception_returns_none(self):
        """When nearest_nodes raises an exception, _snap_node returns None."""
        import services.routing as routing
        fake_ox = MagicMock()
        fake_ox.nearest_nodes.side_effect = Exception("K-D tree error")

        res = routing._snap_node(fake_ox, None, 19.28, 72.87)
        assert res is None

    def test_road_route_import_error(self, monkeypatch):
        """When _try_import raises ImportError, road_route returns None."""
        import services.routing as routing
        monkeypatch.setattr(routing, "_graph", object())
        monkeypatch.setattr(routing, "_try_import", lambda: (_ for _ in ()).throw(ImportError("no ox")))

        assert routing.road_route(19.28, 72.87, 19.29, 72.88) is None


