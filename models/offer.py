from typing import Optional
from pydantic import BaseModel, Field


class OfferCreate(BaseModel):
    jobId: str = Field(..., description="ID of the target job")
    workerId: str = Field(..., description="UID of the worker involved")
    price: float = Field(..., gt=0, description="Proposed price in INR")
    by: Optional[str] = Field(None, pattern="^(customer|worker)$", description="Initiator of the offer (defaults to caller role)")


class OfferCounter(BaseModel):
    price: float = Field(..., gt=0, description="Counter-offer price in INR")


class OfferResponse(BaseModel):
    id: str
    jobId: str
    workerId: str
    price: float
    by: str = Field(..., description="'customer' or 'worker'")
    status: str = Field("pending", description="'pending', 'accepted', or 'rejected'")
    createdAt: str

    model_config = {"from_attributes": True}
