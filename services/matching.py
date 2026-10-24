"""
services/matching.py  (updated for Stage A + B)

Pipeline
--------
1. [Stage B] H3 pre-filter: narrow all_workers to those in the
   ~5 km H3 disk around the job (falls back to unfiltered if all removed).
2. Standard filter: verified, available, not-flagged, skill-matched, within serviceRadius.
3. Haversine score & pre-rank.
4. [Stage A] Road-network Dijkstra for TOP 5 haversine workers:
   - replace distanceKm / etaMinutes with road values.
   - recompute within30 from road ETA.
   - re-sort top-5 by road ETA (ascending).
5. Return top-5 road-sorted + remaining haversine-sorted.

Frozen contract fields (unchanged): distanceKm, etaMinutes, within30, score,
trustScore, trustBadge, worker {uid, name, skills, rates, rating, jobsDone,
verified, distanceKm, etaMinutes, within30}.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from core.database import db
from services.distance import haversine_distance, calculate_eta, is_within_30_minutes
from services.trust import get_worker_trust_info

logger = logging.getLogger(__name__)

# Lazy imports – so the server still starts when h3/osmnx are absent
def _routing():
    try:
        from services.routing import road_eta, load_graph
        return road_eta, load_graph
    except ImportError:
        return None, None

def _h3_filter():
    try:
        from services.h3_index import filter_workers_by_h3
        return filter_workers_by_h3
    except ImportError:
        return None


# ── Stage A: number of top haversine workers to run Dijkstra on ──────────────
_TOP_N_ROUTING = 5


def match_workers_for_job(job_id: str, requester: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Implements the PRD Matching Service (Section 5.3) augmented with:
      - Stage B: H3 spatial pre-filter
      - Stage A: Road-network Dijkstra for top-5 re-ranking
    """
    job = db.get_document("jobs", job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found"
        )

    if requester:
        caller_role = requester.get("role", "customer")
        caller_uid = requester.get("uid")
        if caller_role != "admin" and job.get("customerId") != caller_uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to view matches for another user's job"
            )

    job_category = job.get("category", "").lower().strip()
    job_loc = job.get("location", {})
    job_lat = job_loc.get("lat")
    job_lng = job_loc.get("lng")
    job_budget = job.get("budget")

    if job_lat is None or job_lng is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job location is missing coordinates (lat, lng)"
        )

    # ── Stage B: H3 pre-filter ────────────────────────────────────────────────
    all_workers = db.list_collection("workers")
    h3_fn = _h3_filter()
    if h3_fn is not None:
        all_workers = h3_fn(all_workers, job_lat, job_lng, radius_km=5.0, resolution=8)
    # (If h3_fn is None or all filtered out, all_workers is unchanged – fallback handled inside h3_index)

    # ── Standard filter pass ──────────────────────────────────────────────────
    matched_results: List[Dict[str, Any]] = []

    for worker in all_workers:
        # Rule 1: Must be verified
        if not worker.get("verified", False):
            continue

        # Rule 2: Must be available now
        if not worker.get("isAvailableNow", True):
            continue

        # Rule 3: Must not be flagged
        if worker.get("isFlagged", False) or worker.get("flagged", False):
            continue

        # Rule 4: Must match required skill category
        worker_skills = [s.lower().strip() for s in worker.get("skills", [])]
        if job_category not in worker_skills:
            continue

        worker_loc = worker.get("location", {})
        w_lat = worker_loc.get("lat")
        w_lng = worker_loc.get("lng")
        if w_lat is None or w_lng is None:
            continue

        # Haversine distance
        dist_km = haversine_distance(job_lat, job_lng, w_lat, w_lng)
        service_radius = float(worker.get("serviceRadiusKm", 5.0))

        # Rule 5: Must be within worker's own service radius
        if dist_km > service_radius:
            continue

        # Haversine ETA (baseline; may be replaced by road ETA below)
        eta_min = calculate_eta(dist_km)
        within30 = is_within_30_minutes(eta_min)

        # Worker rate for this skill
        rates = worker.get("rates", {})
        worker_rate = (
            rates.get(job_category)
            or rates.get(job_category.capitalize())
            or rates.get("default", 400.0)
        )
        worker_rate = float(worker_rate)

        # 1. Distance score (40 pts) – closer is better
        radius_norm = max(service_radius, 0.5)
        dist_factor = max(0.0, 1.0 - (dist_km / radius_norm))
        score_dist = dist_factor * 40.0

        # 2. Rating score (30 pts)
        worker_rating = float(worker.get("rating", 5.0))
        rating_factor = max(0.0, min(worker_rating, 5.0)) / 5.0
        score_rating = rating_factor * 30.0

        # 3. Price vs Budget score (20 pts)
        if job_budget is not None and float(job_budget) > 0:
            budget_val = float(job_budget)
            if worker_rate <= budget_val:
                score_price = 20.0
            else:
                diff = worker_rate - budget_val
                score_price = max(0.0, 1.0 - (diff / budget_val)) * 20.0
        else:
            score_price = 15.0  # Neutral when no budget given

        # 4. Jobs done score (10 pts)
        jobs_done = int(worker.get("jobsDone", 0))
        score_jobs = min(1.0, float(jobs_done) / 50.0) * 10.0

        total_score = round(score_dist + score_rating + score_price + score_jobs, 2)
        worker_reports = db.query_collection("reports", {"workerId": worker.get("uid", "")})
        trust_score, trust_badge = get_worker_trust_info(worker, len(worker_reports))

        worker_dict = dict(worker)
        worker_dict["trustScore"] = trust_score
        worker_dict["trustBadge"] = trust_badge

        matched_results.append({
            "worker":      worker_dict,
            "distanceKm":  round(dist_km, 3),
            "etaMinutes":  round(eta_min, 1),
            "within30":    within30,
            "score":       total_score,
            "trustScore":  trust_score,
            "trustBadge":  trust_badge,
            # Internal fields used for routing stage; not in frozen contract
            "_w_lat":      w_lat,
            "_w_lng":      w_lng,
        })

    # Primary sort: haversine score descending
    matched_results.sort(key=lambda x: x["score"], reverse=True)

    # ── Stage A: Dijkstra on top-N ────────────────────────────────────────────
    road_eta_fn, _ = _routing()
    top_n = matched_results[:_TOP_N_ROUTING]
    rest  = matched_results[_TOP_N_ROUTING:]

    if road_eta_fn is not None and top_n:
        for entry in top_n:
            try:
                w_lat = entry.pop("_w_lat", None)
                w_lng = entry.pop("_w_lng", None)
                if w_lat is None or w_lng is None:
                    continue
                road_dist, road_eta_val = road_eta_fn(
                    job_lat, job_lng, w_lat, w_lng
                )
                if road_dist is not None and road_eta_val is not None:
                    entry["distanceKm"] = round(road_dist, 3)
                    entry["etaMinutes"] = round(road_eta_val, 1)
                    entry["within30"]   = is_within_30_minutes(road_eta_val)
            except Exception as exc:
                logger.debug("routing: failed for worker %s: %s",
                             entry.get("worker", {}).get("uid"), exc)
        # Re-sort top-5 by road ETA ascending (fastest first)
        top_n.sort(key=lambda x: x["etaMinutes"])
    else:
        # No routing – clean up internal keys
        for entry in top_n:
            entry.pop("_w_lat", None)
            entry.pop("_w_lng", None)

    # Clean up internal keys from rest
    for entry in rest:
        entry.pop("_w_lat", None)
        entry.pop("_w_lng", None)

    return top_n + rest
