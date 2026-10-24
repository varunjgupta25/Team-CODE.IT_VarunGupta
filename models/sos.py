from typing import Optional
from pydantic import BaseModel, Field


class SOSLocation(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")


class SOSCreate(BaseModel):
    jobId: Optional[str] = Field(None, description="Optional ID of active job when emergency triggered")
    location: SOSLocation = Field(..., description="Current user coordinates")


class SOSResponse(BaseModel):
    id: str
    jobId: Optional[str] = None
    userId: str
    location: SOSLocation
    createdAt: str
    status: str = "recorded"

    model_config = {"from_attributes": True}
