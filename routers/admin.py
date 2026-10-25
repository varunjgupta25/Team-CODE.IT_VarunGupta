from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from core.auth import require_role
from models.worker import AdminApproveResponse
from services.verification_service import approve_worker_verification
from core.database import db

router = APIRouter(tags=["Admin"])


from models.worker import AdminApproveResponse, PendingVerificationWorker

@router.get("/admin/verifications", response_model=List[PendingVerificationWorker])
def api_get_verifications_queue(
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
) -> List[PendingVerificationWorker]:
    """
    Admin retrieves the verification queue of workers with verificationStatus == 'pending'.
    Never returns full document numbers.
    """
    all_workers = db.list_collection("workers")
    pending: List[PendingVerificationWorker] = []
    for w in all_workers:
        if w.get("verificationStatus") == "pending":
            worker_id = w.get("uid") or w.get("workerId") or ""
            pending.append(
                PendingVerificationWorker(
                    workerId=worker_id,
                    name=w.get("name") or "Unknown Worker",
                    skills=w.get("skills") or [],
                    documentType=w.get("documentType"),
                    documentNumberMasked=w.get("documentNumberMasked"),
                    requestedAt=w.get("requestedAt")
                )
            )
    return pending


@router.get("/admin/verifications/pending")
def api_get_pending_verifications(
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin retrieves list of workers requiring verification (pending or unverified).
    """
    all_workers = db.list_collection("workers")
    pending = [
        w for w in all_workers
        if not w.get("verified")
    ]
    return pending


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
