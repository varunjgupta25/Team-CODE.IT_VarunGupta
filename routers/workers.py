from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, status
from pydantic import BaseModel, Field
from core.auth import get_current_user, require_role
from models.worker import (
    MatchedWorkerResponse,
    WorkerVerifyRequest,
    WorkerVerifyResponse,
)
from services.matching import match_workers_for_job
from services.verification_service import (
    request_worker_verification,
    submit_worker_verification_upload,
)

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
    Worker requests ID verification (metadata only).
    Only workers may call this endpoint (customers receive 403 Forbidden).
    """
    worker_id = current_user.get("uid")
    return request_worker_verification(worker_id, payload or WorkerVerifyRequest())


@router.post("/workers/verify/upload", response_model=WorkerVerifyResponse)
async def api_upload_verification(
    documentType: str = Form("aadhaar"),
    documentNumber: Optional[str] = Form(None),
    id_document: UploadFile = File(..., description="ID document image (JPEG/PNG, max 5MB)"),
    selfie: UploadFile = File(..., description="Live face selfie (JPEG/PNG, max 5MB)"),
    current_user: Dict[str, Any] = Depends(require_role(["worker"]))
):
    """
    Worker uploads ID photo and selfie for manual admin verification:
    - JPEG / PNG only, max 5MB
    - Magic bytes validated (spoofed extensions rejected)
    - EXIF stripped and re-encoded
    - Stored in DPDP-compliant private storage (no public URL)
    """
    worker_id = current_user.get("uid")
    id_bytes = await id_document.read()
    selfie_bytes = await selfie.read()

    return submit_worker_verification_upload(
        worker_id=worker_id,
        document_type=documentType,
        document_number=documentNumber,
        id_doc_bytes=id_bytes,
        id_doc_filename=id_document.filename or "id_document.jpg",
        selfie_bytes=selfie_bytes,
        selfie_filename=selfie.filename or "selfie.jpg"
    )


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

    if current_user.get("role") != "admin" and current_user.get("uid") != worker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update another worker's availability"
        )

    worker = db.get_document("workers", worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID '{worker_id}' not found"
        )

    db.update_document("workers", worker_id, {"isAvailableNow": payload.isAvailableNow})
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
    name: str = Field(..., min_length=2, description="Worker full name")
    phone: str = Field(..., description="Phone number")
    skills: List[str] = Field(..., min_length=1, description="List of worker skills")
    rates: Dict[str, float] = Field(..., description="Hourly/visit rates per skill")
    location: Optional[Dict[str, Any]] = None
    serviceRadiusKm: Optional[float] = 10.0
    avatarUrl: Optional[str] = None
    about: Optional[str] = None


@router.post("/workers/register", status_code=status.HTTP_201_CREATED)
def api_register_worker(
    payload: WorkerRegisterRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Register a real worker into the database.
    Requires a valid token; UID is strictly taken from the authenticated token.
    Roles are immutable once set and existing documents cannot be overwritten.
    """
    from core.database import db
    from fastapi import HTTPException

    worker_uid = current_user.get("uid")
    if not worker_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user UID not found"
        )

    existing_user = db.get_document("users", worker_uid)
    existing_worker = db.get_document("workers", worker_uid)

    if existing_user and existing_user.get("role") == "customer":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already registered as a customer; roles are immutable"
        )

    if existing_user and existing_user.get("role") == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin profiles cannot be overwritten via registration"
        )

    if existing_worker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Worker is already registered; cannot overwrite existing worker profile"
        )

    default_loc = {"lat": 19.2812, "lng": 72.8697, "address": "Mira Road, Mumbai"}
    worker_loc = payload.location or default_loc
    if "lat" not in worker_loc:
        worker_loc["lat"] = 19.2812
    if "lng" not in worker_loc:
        worker_loc["lng"] = 72.8697

    new_worker = {
        "uid": worker_uid,
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

    db.set_document("workers", worker_uid, new_worker)
    db.set_document("users", worker_uid, {
        "uid": worker_uid,
        "role": "worker",
        "name": new_worker["name"],
        "phone": new_worker["phone"],
        "location": worker_loc
    })
    return new_worker
