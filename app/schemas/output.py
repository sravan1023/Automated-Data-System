"""
AutoDocs AI - Output Schemas
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.models.output import OutputType


class OutputResponse(BaseModel):
    """Schema for output response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    job_id: UUID
    type: OutputType
    name: str
    file_size_bytes: int | None
    mime_type: str | None
    download_count: int
    expires_at: datetime | None
    created_at: datetime


class OutputDownloadResponse(BaseModel):
    """Schema for download URL response."""
    download_url: str
    expires_in: int  # seconds
