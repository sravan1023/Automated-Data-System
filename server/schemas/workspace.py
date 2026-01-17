"""
AutoDocs AI - Workspace Schemas
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from server.models.workspace import WorkspacePlan, WorkspaceRole


class WorkspaceCreate(BaseModel):
    """Schema for workspace creation."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class WorkspaceUpdate(BaseModel):
    """Schema for workspace update."""
    name: str | None = Field(None, min_length=1, max_length=255)
    settings: dict | None = None


class WorkspaceResponse(BaseModel):
    """Schema for workspace response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    slug: str
    owner_id: UUID
    plan: WorkspacePlan
    storage_used_bytes: int
    is_active: bool
    created_at: datetime


class WorkspaceMemberInvite(BaseModel):
    """Schema for inviting a workspace member."""
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.VIEWER


class WorkspaceMemberResponse(BaseModel):
    """Schema for workspace member response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    joined_at: datetime


class WorkspaceMemberUpdate(BaseModel):
    """Schema for updating member role."""
    role: WorkspaceRole
