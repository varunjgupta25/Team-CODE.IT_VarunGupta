from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from core.auth import get_current_user
from models.sos import SOSCreate, SOSResponse
from services.sos_service import trigger_sos

router = APIRouter(tags=["Safety & SOS"])


@router.post("/sos", response_model=SOSResponse, status_code=status.HTTP_201_CREATED)
def api_trigger_sos(
    payload: SOSCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Triggers an emergency SOS alert, saving current coordinates, user ID,
    and optional active job ID in the sos_alerts collection.
    """
    user_id = current_user.get("uid")
    return trigger_sos(payload, user_id)
