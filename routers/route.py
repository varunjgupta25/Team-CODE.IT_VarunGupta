"""
routers/route.py

GET /api/route?jobId=&workerId=
Returns the road-network route between a job location and a worker location.
Falls back to Haversine if the road graph is unavailable.

Response (frozen contract – never changes shape):
{
    "distanceKm": float,
    "etaMinutes": float,
    "polyline":   [[lat, lng], ...]   # empty list on Haversine fallback
}
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from core.auth import get_current_user
from core.database import db
from services.distance import haversine_distance, calculate_eta

router = APIRouter(tags=["Route"])


class RouteResponse(BaseModel):
    distanceKm: float
    etaMinutes: float
    polyline: List[List[float]]


@router.get("/route", response_model=RouteResponse)
def api_get_route(
    jobId: str = Query(..., description="Job ID"),
    workerId: str = Query(..., description="Worker UID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Compute road-network route from job location to worker location.
    Uses Dijkstra on the OSM drive graph (Mira-Bhayandar area).
    Falls back to straight-line Haversine + empty polyline if the graph
    is unavailable or either point cannot be snapped to the network.
    """
    # --- resolve locations ---
    job = db.get_document("jobs", jobId)
    if job is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Job '{jobId}' not found")

    worker = db.get_document("workers", workerId)
    if worker is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Worker '{workerId}' not found")

    job_loc    = job.get("location", {})
    worker_loc = worker.get("location", {})
    j_lat, j_lng = job_loc.get("lat"), job_loc.get("lng")
    w_lat, w_lng = worker_loc.get("lat"), worker_loc.get("lng")

    if None in (j_lat, j_lng, w_lat, w_lng):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Job or worker location is missing lat/lng")

    # --- try road routing ---
    try:
        from services.routing import road_route
        result = road_route(j_lat, j_lng, w_lat, w_lng)
        if result is not None:
            return RouteResponse(
                distanceKm=result["distanceKm"],
                etaMinutes=result["etaMinutes"],
                polyline=result["polyline"],
            )
    except Exception:
        pass

    # --- Haversine fallback ---
    dist_km    = haversine_distance(j_lat, j_lng, w_lat, w_lng)
    eta_min    = calculate_eta(dist_km)
    return RouteResponse(
        distanceKm=round(dist_km, 3),
        etaMinutes=round(eta_min, 1),
        polyline=[],
    )
