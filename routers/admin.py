from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Response, status
from core.auth import require_role
from models.worker import (
    AdminApproveResponse,
    PendingVerificationWorker,
    PendingVerificationWorkerDTO,
    AdminRejectRequest,
)
from services.verification_service import (
    approve_worker_verification,
    reject_worker_verification,
    reset_worker_verification_attempts,
    get_pending_verifications_dto,
    get_worker_document_stream,
)
from core.database import db

router = APIRouter(tags=["Admin"])


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


@router.get("/admin/verifications/pending", response_model=List[PendingVerificationWorkerDTO])
def api_get_pending_verifications(
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
) -> List[PendingVerificationWorkerDTO]:
    """
    Admin retrieves trimmed DTO queue of workers requiring verification:
    (uid, name, docType, last4, submittedAt, attemptCount, status).
    Never exposes complete worker records or private storage file paths.
    """
    return [PendingVerificationWorkerDTO(**d) for d in get_pending_verifications_dto()]


@router.get("/admin/verifications/{uid}/documents/{doc_type}")
def api_get_verification_document(
    uid: str,
    doc_type: str,
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin securely streams a private worker verification document (id_document or selfie).
    Enforces role=admin, verifies authorization, and streams bytes directly.
    Never exposes permanent public URLs.
    """
    content, mime = get_worker_document_stream(uid, doc_type, current_user)
    return Response(
        content=content,
        media_type=mime,
        headers={"Cache-Control": "private, no-cache, no-store, must-revalidate"}
    )


@router.post("/admin/verifications/{uid}/approve", response_model=AdminApproveResponse)
def api_approve_verification(
    uid: str,
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin approves a worker verification request.
    Sets verified = True, permanently deletes uploaded images, and writes an audit log.
    Non-admin callers receive 403 Forbidden.
    """
    reviewer_uid = current_user.get("uid") or "admin"
    res = approve_worker_verification(uid, reviewer_uid=reviewer_uid)
    return AdminApproveResponse(
        status="approved",
        workerId=res["workerId"],
        verified=True
    )


@router.post("/admin/verifications/{uid}/reject")
def api_reject_verification(
    uid: str,
    payload: AdminRejectRequest,
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin rejects a worker verification with a required reason.
    Permanently deletes uploaded images, increments rejectionCount, and writes an audit log.
    """
    reviewer_uid = current_user.get("uid") or "admin"
    return reject_worker_verification(uid, reason=payload.reason, reviewer_uid=reviewer_uid)


@router.post("/admin/verifications/{uid}/reset_attempts")
def api_reset_verification_attempts(
    uid: str,
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin resets worker rejection attempts count if the worker reached maximum allowed rejections.
    """
    reviewer_uid = current_user.get("uid") or "admin"
    return reset_worker_verification_attempts(uid, reviewer_uid=reviewer_uid)
