from typing import Optional
from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    workerId: str = Field(..., description="UID of the worker being reported")
    reason: str = Field(..., min_length=1, description="Reason for the report")
    jobId: Optional[str] = Field(None, description="Optional associated job ID")


class ReportResponse(BaseModel):
    id: str
    workerId: str
    reporterId: str
    reason: str
    jobId: Optional[str] = None
    createdAt: str
    status: str = "pending"

    model_config = {"from_attributes": True}
