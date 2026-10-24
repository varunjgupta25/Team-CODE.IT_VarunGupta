from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, status
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

router = APIRouter(tags=["Jobs"])


class CustomerRegisterRequest(BaseModel):
    uid: Optional[str] = None
    name: str
    phone: str
    location: Optional[Dict[str, Any]] = None


@router.post("/customers/register", status_code=status.HTTP_201_CREATED)
def api_register_customer(payload: CustomerRegisterRequest):
    """
    Register or update customer profile dynamically.
    """
    import uuid
    customer_uid = payload.uid or f"cust_{uuid.uuid4().hex[:8]}"
    default_loc = {"lat": 19.2812, "lng": 72.8697, "address": "Mira Road, Mumbai"}
    cust_loc = payload.location or default_loc

    user_data = {
        "uid": customer_uid,
        "role": "customer",
        "name": payload.name.strip(),
        "phone": payload.phone.strip(),
        "location": cust_loc,
    }
    db.set_document("users", customer_uid, user_data)
    return user_data


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
    return start_job(id, worker_id)


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
    return complete_job(id, worker_id)


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
