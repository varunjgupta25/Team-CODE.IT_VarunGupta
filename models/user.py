from typing import Optional
from pydantic import BaseModel, Field


class UserLocation(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")


class UserBase(BaseModel):
    role: str = Field(..., pattern="^(customer|worker|admin)$", description="User role")
    name: str = Field(..., min_length=1, description="Full name")
    phone: str = Field(..., description="Contact phone number")
    location: UserLocation = Field(..., description="Coordinates")
    language: Optional[str] = Field("en", description="Preferred language code")


class UserCreate(UserBase):
    uid: Optional[str] = Field(None, description="Firebase user ID (if omitted, generated)")


class UserResponse(UserBase):
    uid: str

    model_config = {"from_attributes": True}
