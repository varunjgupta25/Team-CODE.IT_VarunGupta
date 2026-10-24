"""
services/h3_index.py

Stage B: H3 hexagonal spatial index for fast worker pre-filtering.

Uses Uber H3 v4 API:
  h3.latlng_to_cell(lat, lng, resolution) -> cell_id
  h3.grid_disk(cell_id, k)                -> set of cell_ids within k rings

Public API
----------
to_cell(lat, lng, resolution=8) -> str          H3 cell id
cells_within(lat, lng, radius_km, resolution=8) -> frozenset[str]
filter_workers_by_h3(workers, job_lat, job_lng, radius_km=5.0, resolution=8)
    -> List[worker]   (falls back to unfiltered list if all filtered out)
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# H3 resolution 8  average cell edge length ≈ 0.461 km
# grid_disk ring k covers roughly (k * edge_length) km radius
# radius_km / edge_length ≈ rings needed
_RES8_EDGE_KM = 0.461


def _h3():
    """Lazy import so the module loads even if h3 is not installed."""
    import h3 as _h3_lib
    return _h3_lib


def to_cell(lat: float, lng: float, resolution: int = 8) -> str:
    """Return the H3 cell id at the given resolution for (lat, lng)."""
    return _h3().latlng_to_cell(lat, lng, resolution)


def cells_within(
    lat: float,
    lng: float,
    radius_km: float = 5.0,
    resolution: int = 8,
) -> frozenset:
    """
    Return the set of H3 cell ids whose centres are within approximately
    `radius_km` km from (lat, lng) at the given resolution.

    Converts radius_km to a ring count k = ceil(radius_km / edge_length).
    """
    h3 = _h3()
    edge_km = _RES8_EDGE_KM  # valid for res 8
    # Slightly different edge lengths per resolution; we use a simple formula
    # res8 edge ≈ 0.461 km; each step halves area so edge ≈ 0.461 * sqrt(7)^(8-res)
    # For simplicity, only res 8 is specified; keep edge_km constant.
    k = max(1, math.ceil(radius_km / edge_km))
    centre_cell = h3.latlng_to_cell(lat, lng, resolution)
    disk = h3.grid_disk(centre_cell, k)
    return frozenset(disk)


def filter_workers_by_h3(
    workers: List[Dict[str, Any]],
    job_lat: float,
    job_lng: float,
    radius_km: float = 5.0,
    resolution: int = 8,
) -> List[Dict[str, Any]]:
    """
    Filter `workers` to those whose H3 cell (resolution 8) is within the
    grid_disk centred on the job location.

    Constraints:
    - Filtering is done entirely in Python from in-memory worker data.
    - No new Firestore queries or stored fields are required.
    - If ALL workers are filtered out the original list is returned unchanged
      (fail-open / fallback).
    - If h3 is not installed, returns the original list unchanged.
    """
    try:
        h3 = _h3()
    except ImportError:
        logger.warning("h3_index: h3 library not installed – H3 pre-filter skipped")
        return workers

    try:
        candidate_cells = cells_within(job_lat, job_lng, radius_km, resolution)
        filtered: List[Dict[str, Any]] = []
        for w in workers:
            loc = w.get("location", {})
            w_lat = loc.get("lat")
            w_lng = loc.get("lng")
            if w_lat is None or w_lng is None:
                continue
            worker_cell = h3.latlng_to_cell(w_lat, w_lng, resolution)
            if worker_cell in candidate_cells:
                filtered.append(w)

        if not filtered:
            logger.debug(
                "h3_index: all workers filtered out – falling back to unfiltered list"
            )
            return workers  # fallback

        return filtered

    except Exception as exc:
        logger.warning("h3_index: filter error %s – using unfiltered list", exc)
        return workers
