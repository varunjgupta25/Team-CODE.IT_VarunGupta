import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from core.database import db
from models.report import ReportCreate
from services.trust_engine import (
    evaluate_abuse_threshold,
    VALID_REPORT_CATEGORIES,
    UNDER_REVIEW_STATUS,
)


def create_report(
    report_data: ReportCreate,
    reporter_id: str
) -> Dict[str, Any]:
    worker = db.get_document("workers", report_data.workerId)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID '{report_data.workerId}' not found"
        )

    if report_data.jobId:
        job = db.get_document("jobs", report_data.jobId)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with ID '{report_data.jobId}' not found"
            )

    # Validate category tag, default to "other"
    category = (report_data.category or "other").lower().strip()
    if category not in VALID_REPORT_CATEGORIES:
        category = "other"

    report_id = f"rep_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    doc_data = {
        "id": report_id,
        "workerId": report_data.workerId,
        "reporterId": reporter_id,
        "reason": report_data.reason,
        "category": category,
        "jobId": report_data.jobId,
        "createdAt": now_iso,
        "status": "pending"
    }

    db.set_document("reports", report_id, doc_data)

    # Evaluate abuse threshold using trust engine rules
    # Fetch all reports for this worker and check if threshold is breached
    worker_reports = db.query_collection("reports", {"workerId": report_data.workerId})

    if evaluate_abuse_threshold(worker_reports):
        # Auto-flag worker: set account status to UNDER_REVIEW and demote from feed
        db.update_document("workers", report_data.workerId, {
            "isFlagged": True,
            "flagged": True,
            "accountStatus": UNDER_REVIEW_STATUS,
        })

    return doc_data


def list_reports(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List reports, optionally filtered by status (pending, resolved, dismissed).
    """
    reports = db.list_collection("reports")
    if status_filter:
        reports = [r for r in reports if r.get("status") == status_filter.lower().strip()]
    return reports


def get_report(report_id: str) -> Dict[str, Any]:
    """
    Retrieve single report by ID.
    """
    report = db.get_document("reports", report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' not found"
        )
    return report


def resolve_report(report_id: str, action: Optional[str] = None) -> Dict[str, Any]:
    """
    Mark a report as resolved with recorded action.
    """
    report = db.get_document("reports", report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' not found"
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    action_note = action or "Reviewed by admin"
    db.update_document("reports", report_id, {
        "status": "resolved",
        "resolvedAt": now_iso,
        "actionTaken": action_note
    })
    report["status"] = "resolved"
    report["resolvedAt"] = now_iso
    report["actionTaken"] = action_note
    return report


def dismiss_report(report_id: str) -> Dict[str, Any]:
    """
    Dismiss a report as unfounded.
    """
    report = db.get_document("reports", report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' not found"
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    db.update_document("reports", report_id, {
        "status": "dismissed",
        "dismissedAt": now_iso
    })
    report["status"] = "dismissed"
    report["dismissedAt"] = now_iso
    return report
