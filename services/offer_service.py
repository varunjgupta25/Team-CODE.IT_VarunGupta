import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from core.database import db
from models.offer import OfferCreate, OfferCounter


def create_offer(
    offer_data: OfferCreate,
    caller_uid: str,
    caller_role: str
) -> Dict[str, Any]:
    job = db.get_document("jobs", offer_data.jobId)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{offer_data.jobId}' not found"
        )

    current_job_status = job.get("status")
    if current_job_status not in ["open", "negotiating"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot make offer on job with status '{current_job_status}'"
        )

    # Validate caller permissions:
    if caller_role == "customer":
        if job.get("customerId") != caller_uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only make offers on your own jobs"
            )
        by_party = "customer"
    elif caller_role == "worker":
        if offer_data.workerId != caller_uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workers can only make offers on their own behalf"
            )
        by_party = "worker"
    else:  # admin
        by_party = offer_data.by or "customer"

    if offer_data.by and offer_data.by != by_party and caller_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Party '{offer_data.by}' does not match caller role '{caller_role}'"
        )

    # Check for existing pending offer between this customer and worker on this job
    existing_offers = db.query_collection("offers", {
        "jobId": offer_data.jobId,
        "workerId": offer_data.workerId,
        "status": "pending"
    })

    if existing_offers:
        latest = existing_offers[-1]
        if latest.get("by") == by_party:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have a pending offer on this job. Please wait for the other party to counter or accept."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"There is already a pending counter-offer from the other party (ID: {latest.get('id')}). Please accept, counter, or reject it."
            )

    offer_id = f"offer_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    doc_data = {
        "id": offer_id,
        "jobId": offer_data.jobId,
        "workerId": offer_data.workerId,
        "price": float(offer_data.price),
        "by": by_party,
        "status": "pending",
        "createdAt": now_iso
    }

    db.set_document("offers", offer_id, doc_data)

    # Transition job to 'negotiating' if open
    if current_job_status == "open":
        db.update_document("jobs", offer_data.jobId, {"status": "negotiating"})

    return doc_data


def counter_offer(
    offer_id: str,
    counter_data: OfferCounter,
    caller_uid: str,
    caller_role: str
) -> Dict[str, Any]:
    offer = db.get_document("offers", offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer with ID '{offer_id}' not found"
        )

    if offer.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot counter offer with status '{offer.get('status')}'. Only pending offers can be countered."
        )

    job_id = offer.get("jobId")
    job = db.get_document("jobs", job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Associated job '{job_id}' not found"
        )

    if job.get("status") not in ["open", "negotiating"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is '{job.get('status')}'. Negotiation is closed."
        )

    job_customer_id = job.get("customerId")
    offer_worker_id = offer.get("workerId")

    # Only the customer of this job or the worker of this offer may participate
    if caller_role != "admin":
        if caller_uid != job_customer_id and caller_uid != offer_worker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to counter this offer"
            )

    offer_by = offer.get("by")  # 'customer' or 'worker'
    caller_party = "customer" if caller_uid == job_customer_id else ("worker" if caller_uid == offer_worker_id else caller_role)

    # Enforce alternating turns: only the other party can counter
    if caller_party == offer_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="It is not your turn to counter. Waiting for the other party."
        )

    # Supersede previous offer
    db.update_document("offers", offer_id, {"status": "rejected"})

    # Create new counter-offer with opposing party
    new_offer_id = f"offer_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    new_by = "worker" if offer_by == "customer" else "customer"

    new_doc = {
        "id": new_offer_id,
        "jobId": job_id,
        "workerId": offer.get("workerId"),
        "price": float(counter_data.price),
        "by": new_by,
        "status": "pending",
        "createdAt": now_iso
    }

    db.set_document("offers", new_offer_id, new_doc)
    return new_doc


def accept_offer(
    offer_id: str,
    caller_uid: str,
    caller_role: str
) -> Dict[str, Any]:
    offer = db.get_document("offers", offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer with ID '{offer_id}' not found"
        )

    if offer.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Offer cannot be accepted because its status is '{offer.get('status')}'"
        )

    job_id = offer.get("jobId")
    job = db.get_document("jobs", job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Associated job '{job_id}' not found"
        )

    if job.get("status") not in ["open", "negotiating"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot accept offer: job status is '{job.get('status')}'"
        )

    job_customer_id = job.get("customerId")
    offer_worker_id = offer.get("workerId")

    # Only parties involved can accept
    if caller_role != "admin":
        if caller_uid != job_customer_id and caller_uid != offer_worker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to accept this offer"
            )

    offer_by = offer.get("by")
    caller_party = "customer" if caller_uid == job_customer_id else ("worker" if caller_uid == offer_worker_id else caller_role)

    # Only recipient can accept an offer (cannot accept own offer)
    if caller_party == offer_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot accept your own offer. Waiting for the other party to accept."
        )

    # 1. Update this offer to accepted
    updated_offer = db.update_document("offers", offer_id, {"status": "accepted"})

    # 2. Update job status to 'accepted', set acceptedWorkerId and finalPrice
    worker_id = offer.get("workerId")
    final_price = float(offer.get("price"))
    db.update_document("jobs", job_id, {
        "status": "accepted",
        "acceptedWorkerId": worker_id,
        "finalPrice": final_price
    })

    # 3. Auto-reject all other pending offers on this job
    all_job_offers = db.query_collection("offers", {"jobId": job_id})
    for other in all_job_offers:
        if other.get("id") != offer_id and other.get("status") == "pending":
            db.update_document("offers", other.get("id"), {"status": "rejected"})

    return updated_offer


def reject_offer(
    offer_id: str,
    caller_uid: str,
    caller_role: str
) -> Dict[str, Any]:
    offer = db.get_document("offers", offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer with ID '{offer_id}' not found"
        )

    if offer.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject offer: status is '{offer.get('status')}'"
        )

    job_id = offer.get("jobId")
    job = db.get_document("jobs", job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Associated job '{job_id}' not found"
        )

    job_customer_id = job.get("customerId")
    offer_worker_id = offer.get("workerId")

    if caller_role != "admin":
        if caller_uid != job_customer_id and caller_uid != offer_worker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to reject this offer"
            )

    updated_offer = db.update_document("offers", offer_id, {"status": "rejected"})
    return updated_offer


def get_offers_for_job(
    job_id: str,
    caller_uid: str,
    caller_role: str
) -> List[Dict[str, Any]]:
    job = db.get_document("jobs", job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found"
        )

    if caller_role == "customer" and job.get("customerId") != caller_uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot read another user's job offers"
        )

    all_offers = db.query_collection("offers", {"jobId": job_id})

    if caller_role == "worker":
        filtered = [o for o in all_offers if o.get("workerId") == caller_uid]
        if not filtered:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot read another user's job offers"
            )
        return filtered

    return all_offers


def get_offer_by_id(
    offer_id: str,
    caller_uid: str,
    caller_role: str
) -> Dict[str, Any]:
    offer = db.get_document("offers", offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer with ID '{offer_id}' not found"
        )

    job = db.get_document("jobs", offer.get("jobId"))
    job_customer_id = job.get("customerId") if job else None
    offer_worker_id = offer.get("workerId")

    if caller_role != "admin":
        if caller_uid != job_customer_id and caller_uid != offer_worker_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot read another user's job offers"
            )

    return offer
