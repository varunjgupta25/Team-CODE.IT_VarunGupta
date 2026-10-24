from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query, status
from core.auth import get_current_user
from models.offer import OfferCreate, OfferCounter, OfferResponse
from services.offer_service import (
    create_offer,
    counter_offer,
    accept_offer,
    reject_offer,
    get_offers_for_job,
    get_offer_by_id,
)

router = APIRouter(tags=["Offers"])


@router.post("/offers", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def api_create_offer(
    payload: OfferCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Submits a new offer or booking proposal for a job.
    Can be initiated by a customer or worker. Sets job status to 'negotiating'.
    """
    caller_uid = current_user.get("uid")
    caller_role = current_user.get("role", "customer")
    return create_offer(payload, caller_uid, caller_role)


@router.get("/offers", response_model=List[OfferResponse])
def api_get_offers(
    jobId: str = Query(..., description="ID of the job"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Fetches offers for a job.
    A user cannot read another user's job offers (returns 403).
    """
    caller_uid = current_user.get("uid")
    caller_role = current_user.get("role", "customer")
    return get_offers_for_job(jobId, caller_uid, caller_role)


@router.get("/offers/{id}", response_model=OfferResponse)
def api_get_offer(
    id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Fetches a specific offer by ID.
    A user cannot read another user's job offers (returns 403).
    """
    caller_uid = current_user.get("uid")
    caller_role = current_user.get("role", "customer")
    return get_offer_by_id(id, caller_uid, caller_role)


@router.post("/offers/{id}/counter", response_model=OfferResponse)
def api_counter_offer(
    id: str,
    payload: OfferCounter,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Counters an existing pending offer with a new proposed price.
    Enforces alternating turns: only the opposing party can counter.
    """
    caller_uid = current_user.get("uid")
    caller_role = current_user.get("role", "customer")
    return counter_offer(id, payload, caller_uid, caller_role)


@router.post("/offers/{id}/accept", response_model=OfferResponse)
def api_accept_offer(
    id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Accepts a pending offer. Sets job status to 'accepted', locks in final price
    and assigned worker, and automatically rejects all other pending offers on the job.
    """
    caller_uid = current_user.get("uid")
    caller_role = current_user.get("role", "customer")
    return accept_offer(id, caller_uid, caller_role)


@router.post("/offers/{id}/reject", response_model=OfferResponse)
def api_reject_offer(
    id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Rejects a pending offer.
    """
    caller_uid = current_user.get("uid")
    caller_role = current_user.get("role", "customer")
    return reject_offer(id, caller_uid, caller_role)
