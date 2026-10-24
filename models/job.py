from typing import Optional
from pydantic import BaseModel, Field


class JobLocation(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")
    address: str = Field(..., description="Street or area address")


class JobCreate(BaseModel):
    category: str = Field(..., description="Service category (e.g. plumber, electrician, painter, cleaner, maid, cook)")
    description: str = Field(..., min_length=3, description="Problem description")
    location: JobLocation
    budget: Optional[float] = Field(None, gt=0, description="Optional customer budget in INR (> 0)")
    mode: Optional[str] = Field("on-demand", description="on-demand or scheduled")
    scheduledAt: Optional[str] = Field(None, description="ISO timestamp for scheduled jobs")
    customerName: Optional[str] = None
    customerPhone: Optional[str] = None


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
