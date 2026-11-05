from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ReportCreate(BaseModel):
    workerId: str = Field(..., min_length=1, max_length=128, description="UID of the worker being reported")
    reason: str = Field(..., min_length=1, max_length=2000, description="Reason for the report")
    jobId: Optional[str] = Field(None, max_length=128, description="Optional associated job ID")

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("reason must not be blank")
        return stripped


class ReportResponse(BaseModel):
    id: str
    workerId: str
    reporterId: str
    reason: str
    jobId: Optional[str] = None
    createdAt: str
    status: str = "pending"

    model_config = {"from_attributes": True}
