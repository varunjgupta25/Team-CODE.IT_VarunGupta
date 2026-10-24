"""
services/routing.py

Stage A: Road-network routing using OSMnx + NetworkX Dijkstra.

The graph (OSM drive network, 12 km radius around Mira-Bhayandar centre) is
loaded ONCE at module import time (startup) from the cached GraphML file.
All public functions fail-safe: any exception → returns None so the caller
can fall back to Haversine without raising.

Public API
----------
load_graph()         -> loads / returns the singleton graph (called at startup)
road_route(lat1,lng1, lat2,lng2) -> dict | None
    {distanceKm: float, etaMinutes: float, polyline: list[[lat,lng]]}
road_eta(lat1,lng1, lat2,lng2)   -> (distanceKm, etaMinutes) | (None, None)
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
_GRAPH_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "mira_bhayandar.graphml"
)
_CENTRE_LAT = 19.2813
_CENTRE_LNG = 72.8688
_RADIUS_M   = 12_000          # 12 km radius for graph download
_MAX_SNAP_M = 1_000           # nearest node must be within 1 km

# Speed fallback if travel_time weight is missing (km/h)
_DEFAULT_SPEED_KMH = 30.0

# ── Singleton graph ──────────────────────────────────────────────────────────
_graph: Optional[Any] = None          # networkx.MultiDiGraph
_graph_lock = threading.Lock()
_graph_loaded = False                 # True once load was attempted (success or fail)


def _try_import():
    """Return (nx, ox) or raise ImportError."""
    import networkx as nx
    import osmnx as ox
    return nx, ox


def load_graph() -> Optional[Any]:
    """
    Load the OSM graph from the GraphML cache file exactly once.
    Returns the graph or None if unavailable (no file, no internet, import error).
    Thread-safe.
    """
    global _graph, _graph_loaded
    with _graph_lock:
        if _graph_loaded:
            return _graph
        _graph_loaded = True
        try:
            nx, ox = _try_import()
        except ImportError:
            logger.warning("routing: osmnx/networkx not installed – routing disabled")
            return None

        if os.path.exists(_GRAPH_PATH):
            try:
                G = ox.load_graphml(_GRAPH_PATH)
                # Ensure travel_time weights are present
                G = _ensure_travel_time(ox, G)
                _graph = G
                node_count = G.number_of_nodes()
                edge_count = G.number_of_edges()
                logger.info(
                    "routing: loaded graph from %s  (%d nodes, %d edges)",
                    _GRAPH_PATH, node_count, edge_count,
                )
                return _graph
            except Exception as exc:
                logger.warning("routing: failed to load graph from %s: %s", _GRAPH_PATH, exc)
                return None
        else:
            logger.warning(
                "routing: graph file not found at %s – run scripts/build_graph.py once. "
                "Falling back to Haversine.",
                _GRAPH_PATH,
            )
            return None


def _ensure_travel_time(ox: Any, G: Any) -> Any:
    """
    Add 'travel_time' (seconds) edge attribute if missing, using edge length
    and a conservative 30 km/h default.
    osmnx ≥ 1.x provides add_edge_speeds / add_edge_travel_times.
    """
    try:
        G = ox.add_edge_speeds(G)
        G = ox.add_edge_travel_times(G)
    except Exception:
        # Fallback: compute travel_time from 'length' (metres)
        speed_ms = (_DEFAULT_SPEED_KMH * 1000.0) / 3600.0
        for _, _, data in G.edges(data=True):
            if "travel_time" not in data:
                length_m = data.get("length", 50.0)
                data["travel_time"] = length_m / speed_ms
    return G


def _snap_node(ox: Any, G: Any, lat: float, lng: float) -> Optional[int]:
    """
    Return the nearest graph node to (lat, lng).
    Returns None if the nearest node is further than _MAX_SNAP_M metres.
    """
    try:
        node_id, dist_m = ox.nearest_nodes(G, X=lng, Y=lat, return_dist=True)
        if dist_m > _MAX_SNAP_M:
            logger.debug(
                "routing: snap distance %.0f m > %.0f m limit for (%.4f, %.4f)",
                dist_m, _MAX_SNAP_M, lat, lng,
            )
            return None
        return node_id
    except Exception as exc:
        logger.debug("routing: nearest_nodes failed: %s", exc)
        return None


def road_route(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
) -> Optional[Dict[str, Any]]:
    """
    Compute the shortest road route from (lat1,lng1) to (lat2,lng2).

    Returns
    -------
    dict with keys:
        distanceKm  : float   – road distance in km
        etaMinutes  : float   – travel time in minutes
        polyline    : [[lat, lng], ...]  – ordered list of coordinates
    or None if:
        - graph not loaded
        - either point is outside the graph (snap > 1 km)
        - no path exists between the two nodes
    """
    G = _graph
    if G is None:
        return None

    try:
        nx, ox = _try_import()
    except ImportError:
        return None

    try:
        orig = _snap_node(ox, G, lat1, lng1)
        dest = _snap_node(ox, G, lat2, lng2)
        if orig is None or dest is None:
            return None

        # Dijkstra shortest path by travel_time weight
        node_path: List[int] = nx.shortest_path(
            G, orig, dest, weight="travel_time"
        )

        # Sum up route attributes
        total_length_m = 0.0
        total_time_s   = 0.0
        for u, v in zip(node_path[:-1], node_path[1:]):
            # MultiDiGraph: pick minimum-travel_time parallel edge
            edges = G[u][v]
            best_tt = min(
                edata.get("travel_time", 0.0) for edata in edges.values()
            )
            best_len = min(
                edata.get("length", 0.0) for edata in edges.values()
            )
            total_time_s   += best_tt
            total_length_m += best_len

        dist_km     = round(total_length_m / 1000.0, 3)
        eta_minutes = round(total_time_s   / 60.0,   1)

        # Build polyline from node coordinates
        polyline: List[List[float]] = [
            [G.nodes[n]["y"], G.nodes[n]["x"]] for n in node_path
        ]

        return {
            "distanceKm":  dist_km,
            "etaMinutes":  eta_minutes,
            "polyline":    polyline,
        }

    except Exception as exc:
        logger.debug("routing: road_route failed: %s", exc)
        return None


def road_eta(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Convenience wrapper returning (distanceKm, etaMinutes) or (None, None).
    """
    result = road_route(lat1, lng1, lat2, lng2)
    if result is None:
        return None, None
    return result["distanceKm"], result["etaMinutes"]
