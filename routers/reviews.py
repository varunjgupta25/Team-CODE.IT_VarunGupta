from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from core.auth import require_role
from models.review import ReviewCreate, ReviewResponse
from services.review_service import submit_review

router = APIRouter(tags=["Reviews"])


@router.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def api_submit_review(
    payload: ReviewCreate,
    current_user: Dict[str, Any] = Depends(require_role(["customer", "admin"]))
):
    """
    Submits a rating and review for a completed job.
    Updates the worker's rolling average rating automatically.
    Only customers or admins can submit reviews.
    """
    customer_id = current_user.get("uid")
    return submit_review(payload, customer_id)
