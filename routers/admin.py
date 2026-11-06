from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from core.auth import require_role
from models.worker import AdminApproveResponse, AdminRejectResponse, PendingVerificationWorker
from services.verification_service import approve_worker_verification, reject_worker_verification
from services.admin_service import (
    get_dashboard_stats,
    list_all_users,
    suspend_user,
    reactivate_user,
)
from services.report_service import (
    list_reports,
    get_report,
    resolve_report,
    dismiss_report,
)
from core.database import db

router = APIRouter(tags=["Admin"])


# ─────────────────────────────────────────────────────────────────────────────
# Verification Management (Phase 1 Baseline)
# ─────────────────────────────────────────────────────────────────────────────

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


@router.post("/admin/verifications/{uid}/reject", response_model=AdminRejectResponse)
def api_reject_verification(
    uid: str,
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin rejects a worker verification request. Sets verified = False, verificationStatus = 'rejected'.
    Non-admin callers receive 403 Forbidden.
    """
    return reject_worker_verification(uid)


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard Statistics (Module D)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/admin/stats")
@router.get("/admin/dashboard")
def api_get_admin_dashboard_stats(
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Returns aggregated platform health, activity, and safety metrics for the admin console.
    Strictly admin-only.
    """
    return get_dashboard_stats()


# ─────────────────────────────────────────────────────────────────────────────
# Report Management (Module C)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/admin/reports")
def api_admin_list_reports(
    status: Optional[str] = Query(None, description="Filter by status: pending, resolved, dismissed"),
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin retrieves safety/abuse reports with optional status filtering.
    """
    return list_reports(status_filter=status)


@router.get("/admin/reports/{report_id}")
def api_admin_get_report(
    report_id: str,
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin retrieves detailed information for a single safety report.
    """
    return get_report(report_id)


class ReportResolvePayload(BaseModel):
    action: Optional[str] = Field(None, description="Action taken, e.g. 'Warned worker', 'Flagged account'")


@router.post("/admin/reports/{report_id}/resolve")
def api_admin_resolve_report(
    report_id: str,
    payload: Optional[ReportResolvePayload] = None,
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin resolves a safety report.
    """
    action_note = payload.action if payload else None
    return resolve_report(report_id, action=action_note)


@router.post("/admin/reports/{report_id}/dismiss")
def api_admin_dismiss_report(
    report_id: str,
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin dismisses an unfounded report.
    """
    return dismiss_report(report_id)


# ─────────────────────────────────────────────────────────────────────────────
# User Management (Module C)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/admin/users")
def api_admin_list_users(
    role: Optional[str] = Query(None, description="Filter by role: customer, worker, admin"),
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin lists registered platform users with optional role filtering.
    """
    return list_all_users(role=role)


class SuspendUserPayload(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for administrative suspension")


@router.post("/admin/users/{uid}/suspend")
def api_admin_suspend_user(
    uid: str,
    payload: Optional[SuspendUserPayload] = None,
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin suspends a user or worker account.
    """
    reason = payload.reason if payload else None
    return suspend_user(uid, reason=reason)


@router.post("/admin/users/{uid}/reactivate")
def api_admin_reactivate_user(
    uid: str,
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin reactivates a suspended user or worker account.
    """
    return reactivate_user(uid)


@router.get("/admin/sos")
def api_admin_get_sos_alerts(
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Returns all emergency SOS alerts sorted by newest first for administrative monitoring.
    """
    alerts = db.list_collection("sos_alerts")
    return sorted(alerts, key=lambda a: a.get("createdAt", ""), reverse=True)


@router.post("/admin/verifications/{uid}/reset_attempts")
def api_admin_reset_verification_attempts(
    uid: str,
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Resets verification attempts for a rejected worker. Admin only.
    """
    worker = db.get("workers", uid)
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Worker '{uid}' not found")
    worker["verificationAttempts"] = 0
    worker["rejectedReason"] = None
    db.set_document("workers", uid, worker)
    return {"status": "success", "workerId": uid, "verificationAttempts": 0}
