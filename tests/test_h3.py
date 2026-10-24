"""
tests/test_h3.py

Tests for Stage B H3 spatial indexing:
1. Nearby point is inside cells_within, a ~20 km point is outside.
2. Filtering keeps nearby workers and drops far ones.
3. The all-filtered case falls back to the unfiltered list.
4. Behaviour is the same with h3 import patched to fail (graceful fallback).
"""

from unittest.mock import patch
import pytest
from services.h3_index import cells_within, filter_workers_by_h3, to_cell


def test_nearby_inside_and_20km_outside():
    """
    H3 resolution 8 cells_within for a 5 km radius:
    - A point ~2 km away is inside cells_within.
    - A point ~20 km away is strictly outside cells_within.
    """
    centre_lat, centre_lng = 19.2813, 72.8688  # Mira Road
    disk = cells_within(centre_lat, centre_lng, radius_km=5.0, resolution=8)

    # 1. Centre cell is inside
    centre_cell = to_cell(centre_lat, centre_lng, resolution=8)
    assert centre_cell in disk

    # 2. Nearby point (~1.8 km North): 19.2975, 72.8688
    nearby_cell = to_cell(19.2975, 72.8688, resolution=8)
    assert nearby_cell in disk

    # 3. Far point (~20 km South): Andheri West (19.1136, 72.8335)
    far_cell = to_cell(19.1136, 72.8335, resolution=8)
    assert far_cell not in disk


def test_filter_keeps_nearby_and_drops_far():
    """
    filter_workers_by_h3 retains nearby workers and excludes workers outside the 5 km disk.
    """
    workers = [
        {"uid": "w_near_1", "location": {"lat": 19.2820, "lng": 72.8690}},  # ~0.1 km
        {"uid": "w_near_2", "location": {"lat": 19.2950, "lng": 72.8700}},  # ~1.5 km
        {"uid": "w_far_20km", "location": {"lat": 19.1136, "lng": 72.8335}}, # ~20 km
    ]
    filtered = filter_workers_by_h3(workers, 19.2813, 72.8688, radius_km=5.0)
    uids = {w["uid"] for w in filtered}
    assert "w_near_1" in uids
    assert "w_near_2" in uids
    assert "w_far_20km" not in uids
    assert len(filtered) == 2


def test_all_filtered_fallback_to_unfiltered_list():
    """
    When all workers are located outside the disk, filter_workers_by_h3
    gracefully falls back to returning the full unfiltered list.
    """
    far_workers = [
        {"uid": "w_pune", "location": {"lat": 18.5204, "lng": 73.8567}},   # ~120 km
        {"uid": "w_delhi", "location": {"lat": 28.7041, "lng": 77.1025}},  # ~1150 km
    ]
    result = filter_workers_by_h3(far_workers, 19.2813, 72.8688, radius_km=5.0)
    assert result == far_workers
    assert len(result) == 2


def test_h3_import_patched_to_fail_graceful_fallback():
    """
    When the h3 library is missing or raises ImportError, filter_workers_by_h3
    falls back silently and returns the unfiltered workers list.
    """
    workers = [
        {"uid": "w_1", "location": {"lat": 19.2813, "lng": 72.8688}},
        {"uid": "w_2", "location": {"lat": 19.1136, "lng": 72.8335}},
    ]
    with patch("services.h3_index._h3", side_effect=ImportError("No module named 'h3'")):
        result = filter_workers_by_h3(workers, 19.2813, 72.8688, radius_km=5.0)

    assert result == workers
    assert len(result) == 2
