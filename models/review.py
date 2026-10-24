from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    jobId: str = Field(..., description="ID of the completed job")
    workerId: str = Field(..., description="UID of the worker who completed the job")
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating from 1.0 to 5.0")
    comment: str = Field(..., min_length=1, description="Customer review text")


class ReviewResponse(BaseModel):
    id: str
    jobId: str
    workerId: str
    customerId: str
    rating: float
    comment: str
    createdAt: str

    model_config = {"from_attributes": True}
