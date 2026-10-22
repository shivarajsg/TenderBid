from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserResponse


class UserRegisterRequest(BaseModel):
    """Payload for public MSME user registration."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=100, description="Minimum 8 characters")
    full_name: str = Field(min_length=2, max_length=255)
    company_name: Optional[str] = Field(default=None, max_length=255)
    registration_number: Optional[str] = Field(default=None, max_length=100)


class UserLoginRequest(BaseModel):
    """Payload for user authentication."""
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """JWT bearer token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse
