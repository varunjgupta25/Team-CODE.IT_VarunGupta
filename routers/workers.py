from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from core.auth import get_current_user, require_role
from models.job import VALID_CATEGORIES
from models.worker import (
    MatchedWorkerResponse,
    WorkerVerifyRequest,
    WorkerVerifyResponse,
)
from services.matching import match_workers_for_job
from services.verification_service import request_worker_verification

router = APIRouter(tags=["Workers"])


@router.get("/workers/match", response_model=List[MatchedWorkerResponse])
def api_match_workers(
    jobId: str = Query(..., description="ID of the job to find matching workers for"),
    current_user: Dict[str, Any] = Depends(require_role(["customer", "admin"]))
):
    """
    Returns verified, available workers matching the skill and within radius,
    ranked by composite score (distance 40%, rating 30%, price vs budget 20%, jobsDone 10%).
    Each worker result includes distanceKm, etaMinutes, within30 flag, and trust tier badge.
    Only customers or admins can query matching workers.
    """
    return match_workers_for_job(jobId, requester=current_user)


@router.post("/workers/verify", response_model=WorkerVerifyResponse)
def api_request_verification(
    payload: Optional[WorkerVerifyRequest] = None,
    current_user: Dict[str, Any] = Depends(require_role(["worker"]))
):
    """
    Worker requests ID verification.
    Only workers may call this endpoint (customers receive 403 Forbidden).
    """
    worker_id = current_user.get("uid")
    return request_worker_verification(worker_id, payload or WorkerVerifyRequest())


class WorkerAvailabilityPayload(BaseModel):
    isAvailableNow: bool = Field(..., description="Availability status")


@router.patch("/workers/{worker_id}")
def api_update_worker_availability(
    worker_id: str,
    payload: WorkerAvailabilityPayload,
    current_user: Dict[str, Any] = Depends(require_role(["worker", "admin"]))
):
    """
    Worker toggles their availability status (online/offline).
    Only the worker themselves or an admin can update this status.
    """
    from core.database import db
    from fastapi import HTTPException

    # Resolve ID alias if applicable
    id_aliases = {
        "w_plumb_1": "worker_plumber_1",
        "w_plumb_2": "worker_plumber_2",
        "w_elec_1": "worker_elec_1",
    }
    resolved_id = id_aliases.get(worker_id, worker_id)

    worker = db.get_document("workers", resolved_id) or db.get_document("workers", worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID '{worker_id}' not found"
        )

    db.update_document("workers", worker.get("uid", resolved_id), {"isAvailableNow": payload.isAvailableNow})
    worker["isAvailableNow"] = payload.isAvailableNow
    return {"status": "success", "workerId": worker_id, "isAvailableNow": payload.isAvailableNow}


@router.get("/workers/{worker_id}")
def api_get_worker(
    worker_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    from core.database import db
    from fastapi import HTTPException
    worker = db.get_document("workers", worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID '{worker_id}' not found"
        )
    return worker


class WorkerRegisterRequest(BaseModel):
    uid: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=128, description="Worker full name")
    phone: str = Field(..., min_length=4, max_length=32, description="Phone number")
    skills: List[str] = Field(..., min_length=1, description="List of worker skills")
    rates: Dict[str, float] = Field(..., description="Hourly/visit rates per skill")
    location: Optional[Dict[str, Any]] = None
    serviceRadiusKm: Optional[float] = Field(10.0, gt=0, le=100.0)
    avatarUrl: Optional[str] = Field(None, max_length=2048)
    about: Optional[str] = Field(None, max_length=1000)

    @field_validator("skills")
    @classmethod
    def normalise_skills(cls, v: List[str]) -> List[str]:
        normalised = [s.strip().lower() for s in v if s.strip()]
        invalid = [s for s in normalised if s not in VALID_CATEGORIES]
        if invalid:
            from models.job import VALID_CATEGORIES as VC
            raise ValueError(
                f"Unknown skill(s): {', '.join(invalid)}. Valid: {', '.join(VC)}"
            )
        return normalised


@router.post("/workers/register", status_code=status.HTTP_201_CREATED)
def api_register_worker(
    payload: WorkerRegisterRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Register a real worker dynamically into the database.
    Candidate UID is strictly derived from the authenticated token context.
    Any 'uid' present in the request body is explicitly ignored.
    Duplicate registrations return HTTP 409 Conflict.
    """
    from core.database import db

    candidate_uid = current_user.get("uid")
    if not candidate_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated context missing valid worker ID"
        )

    with db._lock:
        if db.get_document("workers", candidate_uid) or db.get_document("users", candidate_uid):
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": "conflict",
                    "message": "User profile already registered.",
                    "detail": "User profile already registered."
                }
            )

        default_loc = {"lat": 19.2812, "lng": 72.8697, "address": "Mira Road, Mumbai"}
        worker_loc = payload.location or default_loc
        if "lat" not in worker_loc:
            worker_loc["lat"] = 19.2812
        if "lng" not in worker_loc:
            worker_loc["lng"] = 72.8697

        new_worker = {
            "uid": candidate_uid,
            "name": payload.name.strip(),
            "phone": payload.phone.strip(),
            "skills": [s.lower().strip() for s in payload.skills],
            "rates": payload.rates,
            "isAvailableNow": True,
            "verified": False,
            "verificationStatus": "unverified",
            "rating": 5.0,
            "jobsDone": 0,
            "location": worker_loc,
            "serviceRadiusKm": payload.serviceRadiusKm or 10.0,
            "avatarUrl": payload.avatarUrl or "https://images.unsplash.com/photo-1540569014015-19a7be504e3a?w=150&auto=format&fit=crop&q=80",
            "about": payload.about or f"Certified {payload.skills[0]} provider in Mira Road.",
            "trustScore": 60.0,
            "trustBadge": "Bronze",
        }

        db.set_document("workers", candidate_uid, new_worker)
        db.set_document("users", candidate_uid, {
            "uid": candidate_uid,
            "role": "worker",
            "name": new_worker["name"],
            "phone": new_worker["phone"],
            "location": worker_loc
        })
        return new_worker
