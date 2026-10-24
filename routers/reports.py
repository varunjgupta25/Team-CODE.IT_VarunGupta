from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from core.auth import get_current_user
from models.report import ReportCreate, ReportResponse
from services.report_service import create_report

router = APIRouter(tags=["Reports"])


@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def api_create_report(
    payload: ReportCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Submits a safety/incident report against a worker.
    Workers with 3+ reports are automatically flagged.
    """
    reporter_id = current_user.get("uid")
    return create_report(payload, reporter_id)
