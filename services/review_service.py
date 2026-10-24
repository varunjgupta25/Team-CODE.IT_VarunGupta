import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import HTTPException, status
from core.database import db
from models.review import ReviewCreate


def submit_review(
    review_data: ReviewCreate,
    customer_id: str
) -> Dict[str, Any]:
    job = db.get_document("jobs", review_data.jobId)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{review_data.jobId}' not found"
        )

    # Job must be completed
    if job.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot review job: status is '{job.get('status')}', expected 'completed'"
        )

    # Only customer of the job can review
    if job.get("customerId") != customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the customer who created this job can submit a review"
        )

    # Check worker matches
    if job.get("acceptedWorkerId") and job.get("acceptedWorkerId") != review_data.workerId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Worker ID '{review_data.workerId}' does not match the job's accepted worker"
        )

    # Check if review already submitted for this job (duplicate review rejected)
    existing_reviews = db.query_collection("reviews", {
        "jobId": review_data.jobId
    })
    if existing_reviews:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A review has already been submitted for this job"
        )

    review_id = f"rev_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    doc_data = {
        "id": review_id,
        "jobId": review_data.jobId,
        "workerId": review_data.workerId,
        "customerId": customer_id,
        "rating": float(review_data.rating),
        "comment": review_data.comment,
        "createdAt": now_iso
    }

    db.set_document("reviews", review_id, doc_data)

    # Update worker's rolling average rating
    all_worker_reviews = db.query_collection("reviews", {"workerId": review_data.workerId})
    if all_worker_reviews:
        total_rating = sum(float(r.get("rating", 5.0)) for r in all_worker_reviews)
        new_average = round(total_rating / len(all_worker_reviews), 2)
        worker = db.get_document("workers", review_data.workerId)
        if worker:
            db.update_document("workers", review_data.workerId, {
                "rating": new_average
            })

    return doc_data
