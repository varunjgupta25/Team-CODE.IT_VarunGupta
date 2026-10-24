from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from core.auth import get_current_user, require_role
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
    return match_workers_for_job(jobId)


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
