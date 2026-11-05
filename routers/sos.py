from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from core.auth import get_current_user, require_role
from models.sos import SOSCreate, SOSResponse, EmergencyContact
from services.sos_service import (
    trigger_sos,
    set_user_emergency_contact,
    get_user_emergency_contact,
    list_sos_alerts,
)

router = APIRouter(tags=["Safety & SOS"])


@router.post("/sos", response_model=SOSResponse, status_code=status.HTTP_201_CREATED)
def api_trigger_sos(
    payload: SOSCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Triggers an emergency SOS alert:
    - Allowed ONLY for the active job's customer or accepted worker
    - Range-validates latitude/longitude coordinates
    - Deduplicates alerts within 60s
    - Rate limits to 3 alerts/hour
    - Notifies emergency contact and ops via NotificationProvider with retries
    - Returns honest delivery status: 'notified', 'partial', or 'failed'
    """
    user_id = current_user.get("uid")
    return trigger_sos(payload, user_id)


@router.put("/users/me/emergency-contact")
@router.post("/users/me/emergency-contact")
def api_set_emergency_contact(
    payload: EmergencyContact,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Saves or updates user's emergency contact:
    - Name and valid Indian mobile number in E.164 format (+91XXXXXXXXXX)
    """
    user_id = current_user.get("uid")
    return set_user_emergency_contact(user_id, payload)


@router.get("/users/me/emergency-contact")
def api_get_emergency_contact(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves currently authenticated user's emergency contact details.
    """
    user_id = current_user.get("uid")
    contact = get_user_emergency_contact(user_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No emergency contact registered for this user"
        )
    return contact


@router.get("/admin/sos", response_model=List[SOSResponse])
def api_admin_list_sos_alerts(
    current_user: Dict[str, Any] = Depends(require_role(["admin"]))
):
    """
    Admin-only endpoint listing recent emergency SOS alerts with delivery statuses and recipient audit trails.
    """
    return list_sos_alerts()
