from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

# Canonical service categories accepted by the platform
VALID_CATEGORIES: List[str] = [
    "plumber", "electrician", "painter", "cleaner", "maid", "cook",
    "carpenter", "ac_repair", "appliance_repair", "pest_control"
]

# Valid job modes
VALID_MODES = Literal["on-demand", "scheduled"]


class JobLocation(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")
    address: str = Field(..., min_length=1, max_length=500, description="Street or area address")


class JobCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=64,
                          description="Service category (plumber, electrician, painter, cleaner, maid, cook, ...)")
    description: str = Field(..., min_length=3, max_length=1000, description="Problem description")
    location: JobLocation
    budget: Optional[float] = Field(None, gt=0, le=1_000_000, description="Optional customer budget in INR (> 0)")
    mode: VALID_MODES = Field("on-demand", description="on-demand or scheduled")
    scheduledAt: Optional[str] = Field(None, max_length=64, description="ISO timestamp for scheduled jobs")
    customerName: Optional[str] = Field(None, max_length=128)
    customerPhone: Optional[str] = Field(None, max_length=32)

    @field_validator("category")
    @classmethod
    def normalise_category(cls, v: str) -> str:
        normalised = v.strip().lower()
        if normalised not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{v}'. Must be one of: {', '.join(VALID_CATEGORIES)}"
            )
        return normalised


class JobResponse(BaseModel):
    id: str
    customerId: str
    customerName: Optional[str] = None
    customerPhone: Optional[str] = None
    category: str
    description: str
    location: JobLocation
    budget: Optional[float] = None
    status: str = Field("open", description="open, negotiating, accepted, in_progress, completed, cancelled")
    acceptedWorkerId: Optional[str] = None
    finalPrice: Optional[float] = None
    createdAt: str
    mode: Optional[str] = "on-demand"
    scheduledAt: Optional[str] = None

    model_config = {"from_attributes": True}


class NearbyJobResponse(BaseModel):
    job: JobResponse
    distanceKm: float
    etaMinutes: float
