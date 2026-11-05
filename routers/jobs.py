from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import JSONResponse
from core.database import db
from core.auth import get_current_user, require_role
from models.job import JobCreate, JobResponse, NearbyJobResponse
from services.job_service import (
    create_job,
    get_job,
    get_nearby_jobs_for_worker,
    start_job,
    complete_job,
    cancel_job,
)
from services.customer_service import (
    get_customer_profile,
    update_customer_profile,
    get_current_user_profile,
)

router = APIRouter(tags=["Jobs"])


class CustomerRegisterRequest(BaseModel):
    uid: Optional[str] = Field(None, description="Ignored: UID is strictly derived from authenticated token")
    name: str = Field(..., min_length=1, max_length=128, description="Customer full name")
    phone: str = Field(..., min_length=4, max_length=32, description="Contact phone number")
    location: Optional[Dict[str, Any]] = None


@router.post("/customers/register", status_code=status.HTTP_201_CREATED)
@router.post("/register", status_code=status.HTTP_201_CREATED)
def api_register_customer(
    payload: CustomerRegisterRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Register customer profile dynamically.
    Candidate UID is strictly derived from the authenticated token context.
    Any 'uid' present in the request body is explicitly ignored.
    Duplicate registrations return HTTP 409 Conflict.
    """
    candidate_uid = current_user.get("uid")
    if not candidate_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated context missing valid user ID"
        )

    with db._lock:
        if db.get_document("users", candidate_uid):
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": "conflict",
                    "message": "User profile already registered.",
                    "detail": "User profile already registered."
                }
            )

        default_loc = {"lat": 19.2812, "lng": 72.8697, "address": "Mira Road, Mumbai"}
        cust_loc = payload.location or default_loc

        user_data = {
            "uid": candidate_uid,
            "role": "customer",
            "name": payload.name.strip(),
            "phone": payload.phone.strip(),
            "location": cust_loc,
        }
        db.set_document("users", candidate_uid, user_data)
        return user_data


class CustomerUpdatePayload(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    phone: Optional[str] = Field(None, min_length=4, max_length=32)
    location: Optional[Dict[str, Any]] = None


@router.get("/customers/{customer_id}")
def api_get_customer(
    customer_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves customer profile with privacy masking.
    Non-owners and non-admins receive a masked phone number.
    """
    return get_customer_profile(customer_id, requester=current_user)


@router.patch("/customers/{customer_id}")
def api_update_customer(
    customer_id: str,
    payload: CustomerUpdatePayload,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Updates customer profile. Customer themselves or admin only.
    """
    return update_customer_profile(
        customer_id,
        updates=payload.model_dump(exclude_unset=True),
        requester=current_user
    )


@router.get("/users/me")
def api_get_current_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Returns full profile for the authenticated user (customer or worker).
    """
    return get_current_user_profile(current_user)


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def api_create_job(
    payload: JobCreate,
    current_user: Dict[str, Any] = Depends(require_role(["customer", "admin"]))
):
    """
    Creates a new job request. Customer specifies category, description,
    location coordinates, and optional budget.
    """
    customer_id = current_user.get("uid")
    return create_job(payload, customer_id, current_user=current_user)


@router.get("/jobs/nearby", response_model=List[NearbyJobResponse])
def api_get_nearby_jobs(
    current_user: Dict[str, Any] = Depends(require_role(["worker", "admin"]))
):
    """
    Worker feed of nearby open jobs matching the worker's skills
    and service radius, sorted by distance.
    """
    worker_id = current_user.get("uid")
    return get_nearby_jobs_for_worker(worker_id)


@router.get("/jobs/{id}", response_model=JobResponse)
def api_get_job(
    id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Fetches job details. Hides exact street address from unassigned workers
    until an offer has been accepted.
    """
    return get_job(id, requester=current_user)


@router.post("/jobs/{id}/start", response_model=JobResponse)
def api_start_job(
    id: str,
    current_user: Dict[str, Any] = Depends(require_role(["worker", "admin"]))
):
    """
    Worker starts the accepted job. Transitions status from 'accepted' to 'in_progress'.
    Rejects invalid state transitions with HTTP 400.
    """
    worker_id = current_user.get("uid")
    caller_role = current_user.get("role", "worker")
    return start_job(id, worker_id, caller_role=caller_role)


@router.post("/jobs/{id}/complete", response_model=JobResponse)
def api_complete_job(
    id: str,
    current_user: Dict[str, Any] = Depends(require_role(["worker", "admin"]))
):
    """
    Worker marks the job as complete. Transitions status from 'in_progress' to 'completed'.
    Increments worker's jobsDone counter. Rejects invalid transitions with HTTP 400.
    """
    worker_id = current_user.get("uid")
    caller_role = current_user.get("role", "worker")
    return complete_job(id, worker_id, caller_role=caller_role)


@router.post("/jobs/{id}/cancel", response_model=JobResponse)
def api_cancel_job(
    id: str,
    current_user: Dict[str, Any] = Depends(require_role(["customer", "admin"]))
):
    """
    Customer or admin cancels an active job. Cannot cancel a completed job (HTTP 400).
    """
    caller_uid = current_user.get("uid")
    caller_role = current_user.get("role", "customer")
    return cancel_job(id, caller_uid, caller_role)
