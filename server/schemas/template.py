"""
AutoDocs AI - Template Schemas
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from server.models.template import ContentType, VersionStatus


class TemplateCreate(BaseModel):
    """Schema for template creation."""
    workspace_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    content_type: ContentType = ContentType.HTML
    content: str = Field(..., min_length=1)
    css_content: str | None = None
    schema_json: dict | None = None  # Expected variables


class TemplateUpdate(BaseModel):
    """Schema for template metadata update."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class TemplateResponse(BaseModel):
    """Schema for template response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    content_type: ContentType
    active_version_id: UUID | None
    created_at: datetime
    updated_at: datetime | None


class TemplateVersionCreate(BaseModel):
    """Schema for creating a new template version."""
    content: str = Field(..., min_length=1)
    css_content: str | None = None
    schema_json: dict | None = None
    change_notes: str | None = None


class TemplateVersionResponse(BaseModel):
    """Schema for template version response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    template_id: UUID
    version: int
    status: VersionStatus
    change_notes: str | None
    created_by: UUID
    created_at: datetime


class TemplateVersionDetailResponse(TemplateVersionResponse):
    """Schema for template version detail with content."""
    content: str
    css_content: str | None
    schema_json: dict | None


class TemplateDetailResponse(TemplateResponse):
    """Schema for template detail with active version content."""
    active_version: TemplateVersionDetailResponse | None = None


class TemplatePreviewRequest(BaseModel):
    """Schema for template preview request."""
    sample_data: dict
