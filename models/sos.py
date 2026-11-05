import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class SOSLocation(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")


class EmergencyContact(BaseModel):
    name: str = Field(..., min_length=2, description="Contact full name")
    phone: str = Field(..., description="E.164 formatted contact phone (+91XXXXXXXXXX)")

    @field_validator("phone", mode="before")
    @classmethod
    def validate_indian_e164_phone(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Phone number must be a string")
        clean = re.sub(r"[\s\-\(\)]", "", v.strip())
        if clean.startswith("0"):
            clean = "+91" + clean[1:]
        elif not clean.startswith("+"):
            clean = "+91" + clean

        # Validate +91 followed by 10 digits starting with 6-9
        if not re.match(r"^\+91[6-9]\d{9}$", clean):
            raise ValueError("Phone number must be a valid 10-digit Indian mobile number in E.164 format (+91XXXXXXXXXX)")
        return clean


class SOSCreate(BaseModel):
    jobId: Optional[str] = Field(None, description="Optional ID of active job when emergency triggered")
    location: SOSLocation = Field(..., description="Current user coordinates")


class SOSRecipientResult(BaseModel):
    target: str = Field(..., description="'emergency_contact' or 'ops'")
    phone: str
    channel: str = "sms"
    status: str = Field(..., description="'sent' or 'failed'")
    error: Optional[str] = None


class SOSResponse(BaseModel):
    id: str
    jobId: Optional[str] = None
    userId: str
    location: SOSLocation
    createdAt: str
    status: str = Field("recorded", description="'notified', 'partial', 'failed', or 'recorded'")
    recipients: List[SOSRecipientResult] = []
    message: Optional[str] = None
    mapsUrl: Optional[str] = None

    model_config = {"from_attributes": True}
