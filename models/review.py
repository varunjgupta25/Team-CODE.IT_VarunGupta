from pydantic import BaseModel, Field, field_validator


class ReviewCreate(BaseModel):
    jobId: str = Field(..., min_length=1, max_length=128, description="ID of the completed job")
    workerId: str = Field(..., min_length=1, max_length=128, description="UID of the worker who completed the job")
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating from 1.0 to 5.0")
    comment: str = Field(..., min_length=1, max_length=2000, description="Customer review text")

    @field_validator("comment")
    @classmethod
    def strip_comment(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("comment must not be blank")
        return stripped


class ReviewResponse(BaseModel):
    id: str
    jobId: str
    workerId: str
    customerId: str
    rating: float
    comment: str
    createdAt: str

    model_config = {"from_attributes": True}
