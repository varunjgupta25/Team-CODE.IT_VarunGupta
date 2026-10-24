from typing import Any, Dict
from fastapi import APIRouter, Depends
from core.auth import require_role
from models.worker import AdminApproveResponse
from services.verification_service import approve_worker_verification

router = APIRouter(tags=["Admin"])


@router.post("/admin/verifications/{uid}/approve", response_model=AdminApproveResponse)
def api_approve_verification(
    uid: str,
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin approves a worker verification request. Sets verified = True.
    Non-admin callers receive 403 Forbidden.
    """
    return approve_worker_verification(uid)
