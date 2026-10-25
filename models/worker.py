from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class WorkerLocation(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")


class WorkerBase(BaseModel):
    name: Optional[str] = None
    skills: List[str] = Field(..., min_length=1, description="List of skills e.g. plumber, electrician")
    rates: Dict[str, float] = Field(..., description="Hourly or per-job rate in INR per skill")
    isAvailableNow: bool = Field(True, description="Availability toggle")
    verified: bool = Field(False, description="Whether worker ID has been verified")
    rating: float = Field(5.0, ge=0.0, le=5.0, description="Rolling average rating")
    jobsDone: int = Field(0, ge=0, description="Completed jobs count")
    location: WorkerLocation
    serviceRadiusKm: float = Field(5.0, gt=0, description="Maximum service coverage radius in km")
    isFlagged: bool = Field(False, description="Flagged for admin review if 3+ reports")
    flagged: bool = Field(False, description="Alias for isFlagged")
    avatarUrl: Optional[str] = Field(None, description="Worker profile avatar image URL")
    about: Optional[str] = Field(None, description="Short bio or experience description")
    rate: Optional[float] = Field(None, description="Selected skill rate")


class WorkerCreate(WorkerBase):
    uid: str


class WorkerResponse(WorkerBase):
    uid: str
    trustScore: Optional[float] = None
    trustBadge: Optional[str] = None

    model_config = {"from_attributes": True}


class MatchedWorkerResponse(BaseModel):
    worker: WorkerResponse
    distanceKm: float
    etaMinutes: float
    within30: bool
    score: float
    trustScore: float
    trustBadge: str


class WorkerVerifyRequest(BaseModel):
    documentType: Optional[str] = Field("aadhaar", description="ID document type (e.g. aadhaar, pan, voter_id)")
    documentNumber: Optional[str] = Field(None, description="Document identification number")


class WorkerVerifyResponse(BaseModel):
    status: str = "pending"
    workerId: str
    message: str


class AdminApproveResponse(BaseModel):
    status: str = "approved"
    workerId: str
    verified: bool = True


class PendingVerificationWorker(BaseModel):
    workerId: str
    name: str
    skills: List[str]
    documentType: Optional[str] = None
    documentNumberMasked: Optional[str] = None
    requestedAt: Optional[str] = None


