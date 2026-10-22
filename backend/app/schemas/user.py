from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: str


class UserResponse(UserBase):
    """Outbound user representation."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    company_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
