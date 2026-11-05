from typing import Literal, Optional
from pydantic import BaseModel, Field

# Maximum price ceiling to prevent absurd values slipping through
_MAX_PRICE = 10_000_000.0


class OfferCreate(BaseModel):
    jobId: str = Field(..., min_length=1, max_length=128, description="ID of the target job")
    workerId: str = Field(..., min_length=1, max_length=128, description="UID of the worker involved")
    price: float = Field(..., gt=0, le=_MAX_PRICE, description="Proposed price in INR")
    by: Optional[Literal["customer", "worker"]] = Field(
        None, description="Initiator of the offer (defaults to caller role)"
    )


class OfferCounter(BaseModel):
    price: float = Field(..., gt=0, le=_MAX_PRICE, description="Counter-offer price in INR")


class OfferResponse(BaseModel):
    id: str
    jobId: str
    workerId: str
    price: float
    by: str = Field(..., description="'customer' or 'worker'")
    status: str = Field("pending", description="'pending', 'accepted', or 'rejected'")
    createdAt: str

    model_config = {"from_attributes": True}
