"""
AutoDocs AI - User Schemas
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserResponse(BaseModel):
    """Schema for user response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    email_verified: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Schema for user profile update."""
    full_name: str | None = Field(None, max_length=255)


class UserPasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
