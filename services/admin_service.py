from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from core.database import db


def get_dashboard_stats() -> Dict[str, Any]:
    """
    Computes real-time platform statistics for the Admin Console.
    Includes active workers, verifications queue, active vs completed jobs, and report metrics.
    """
    all_users = db.list_collection("users")
    all_workers = db.list_collection("workers")
    all_jobs = db.list_collection("jobs")
    all_reports = db.list_collection("reports")

    customers_count = sum(1 for u in all_users if u.get("role") == "customer")
    workers_count = len(all_workers)
    verified_workers_count = sum(1 for w in all_workers if w.get("verified"))
    pending_verifications_count = sum(1 for w in all_workers if not w.get("verified"))

    active_statuses = {"open", "negotiating", "accepted", "in_progress"}
    active_jobs_count = sum(1 for j in all_jobs if j.get("status") in active_statuses)
    completed_jobs_count = sum(1 for j in all_jobs if j.get("status") == "completed")
    total_jobs_count = len(all_jobs)

    pending_reports = sum(1 for r in all_reports if r.get("status") == "pending")
    resolved_reports = sum(1 for r in all_reports if r.get("status") == "resolved")
    dismissed_reports = sum(1 for r in all_reports if r.get("status") == "dismissed")

    return {
        "totalCustomers": customers_count,
        "totalWorkers": workers_count,
        "verifiedWorkers": verified_workers_count,
        "pendingVerifications": pending_verifications_count,
        "activeJobs": active_jobs_count,
        "completedJobs": completed_jobs_count,
        "totalJobs": total_jobs_count,
        "reports": {
            "total": len(all_reports),
            "pending": pending_reports,
            "resolved": resolved_reports,
            "dismissed": dismissed_reports,
        }
    }


def list_all_users(role: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Admin-only listing of platform user accounts with optional role filtering.
    """
    users = db.list_collection("users")
    if role:
        users = [u for u in users if u.get("role") == role.lower()]

    cleaned = []
    for u in users:
        cleaned.append({
            "uid": u.get("uid"),
            "name": u.get("name", "Unknown"),
            "role": u.get("role", "customer"),
            "phone": u.get("phone", ""),
            "accountStatus": u.get("accountStatus", "ACTIVE"),
            "createdAt": u.get("createdAt")
        })
    return cleaned


def suspend_user(uid: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Suspends a customer or worker account, preventing new activity.
    """
    user = db.get_document("users", uid)
    worker = db.get_document("workers", uid)

    if not user and not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{uid}' not found"
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    suspension_patch = {
        "accountStatus": "SUSPENDED",
        "suspendedAt": now_iso,
        "suspensionReason": reason or "Administrative suspension"
    }

    if user:
        db.update_document("users", uid, suspension_patch)
    if worker:
        suspension_patch["isAvailableNow"] = False
        suspension_patch["isFlagged"] = True
        suspension_patch["flagged"] = True
        db.update_document("workers", uid, suspension_patch)

    return {
        "status": "success",
        "uid": uid,
        "accountStatus": "SUSPENDED",
        "message": f"User '{uid}' has been suspended"
    }


def reactivate_user(uid: str) -> Dict[str, Any]:
    """
    Reactivates a previously suspended account.
    """
    user = db.get_document("users", uid)
    worker = db.get_document("workers", uid)

    if not user and not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{uid}' not found"
        )

    reactivation_patch = {
        "accountStatus": "ACTIVE",
        "suspendedAt": None,
        "suspensionReason": None
    }

    if user:
        db.update_document("users", uid, reactivation_patch)
    if worker:
        reactivation_patch["isFlagged"] = False
        reactivation_patch["flagged"] = False
        db.update_document("workers", uid, reactivation_patch)

    return {
        "status": "success",
        "uid": uid,
        "accountStatus": "ACTIVE",
        "message": f"User '{uid}' has been reactivated"
    }
