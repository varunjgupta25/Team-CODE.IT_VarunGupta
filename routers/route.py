"""
routers/route.py

GET /api/route?jobId=&workerId=
Returns the road-network route between a job location and a worker location.
Returns 404 if no road route exists between the points.
Enforces authentication (401) and participant authorization (403 for non-participants).

Response (frozen contract – never changes shape):
{
    "distanceKm": float,
    "etaMinutes": float,
    "polyline":   [[lat, lng], ...]
}
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from core.auth import get_current_user
from core.database import db

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
    Returns 404 when no route is available.
    Only job customer, the worker, or an admin can access (403 otherwise).
    """
    # 1. Resolve job
    job = db.get_document("jobs", jobId)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{jobId}' not found"
        )

    # 2. Resolve worker
    worker = db.get_document("workers", workerId)
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker '{workerId}' not found"
        )

    # 3. Authorization check: participant or admin
    caller_uid = current_user.get("uid")
    caller_role = current_user.get("role", "customer")
    customer_id = job.get("customerId")

    if caller_role != "admin" and caller_uid != customer_id and caller_uid != workerId:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You are not a participant in this job/route"
        )

    # 4. Extract locations
    job_loc = job.get("location", {})
    worker_loc = worker.get("location", {})
    j_lat, j_lng = job_loc.get("lat"), job_loc.get("lng")
    w_lat, w_lng = worker_loc.get("lat"), worker_loc.get("lng")

    if None in (j_lat, j_lng, w_lat, w_lng):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job or worker location is missing lat/lng"
        )

    # 5. Try road routing
    try:
        from services.routing import road_route
        result = road_route(j_lat, j_lng, w_lat, w_lng)
        if result is not None and result.get("polyline"):
            return RouteResponse(
                distanceKm=result["distanceKm"],
                etaMinutes=result["etaMinutes"],
                polyline=result["polyline"],
            )
    except Exception:
        pass

    # No route found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No road route found between job and worker locations"
    )
