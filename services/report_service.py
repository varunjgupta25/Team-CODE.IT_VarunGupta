import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import HTTPException, status
from core.database import db
from models.report import ReportCreate


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

    report_id = f"rep_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    doc_data = {
        "id": report_id,
        "workerId": report_data.workerId,
        "reporterId": reporter_id,
        "reason": report_data.reason,
        "jobId": report_data.jobId,
        "createdAt": now_iso,
        "status": "pending"
    }

    db.set_document("reports", report_id, doc_data)

    # Check report count for this worker - 3+ reports flags the worker
    worker_reports = db.query_collection("reports", {"workerId": report_data.workerId})
    if len(worker_reports) >= 3:
        db.update_document("workers", report_data.workerId, {
            "isFlagged": True,
            "flagged": True
        })

    return doc_data
