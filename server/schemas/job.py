"""
AutoDocs AI - Job Schemas
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

from server.models.job import JobStatus, JobItemStatus, GenerationMode


class JobCreate(BaseModel):
    """Schema for job creation."""
    workspace_id: UUID
    template_id: UUID
    datasource_id: UUID
    mapping: dict[str, str] | None = None  # {template_var: datasource_column}, auto-generated if not provided
    output_format: str = "pdf"
    generation_mode: GenerationMode = GenerationMode.per_row
    priority: int = Field(5, ge=1, le=10)


class JobResponse(BaseModel):
    """Schema for job response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    workspace_id: UUID
    template_id: UUID
    datasource_id: UUID
    output_format: str
    generation_mode: GenerationMode
    status: JobStatus
    priority: int
    total_items: int
    completed_items: int
    failed_items: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    
    @property
    def progress_percent(self) -> float:
        if self.total_items == 0:
            return 0.0
        return round(
            (self.completed_items + self.failed_items) / self.total_items * 100, 1
        )


class JobItemResponse(BaseModel):
    """Schema for job item response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    job_id: UUID
    row_index: int
    status: JobItemStatus
    output_url: str | None
    error_message: str | None
    retry_count: int
    started_at: datetime | None
    completed_at: datetime | None


class JobDetailResponse(JobResponse):
    """Schema for job detail with error message."""
    error_message: str | None


class JobStatsResponse(BaseModel):
    """Schema for job statistics."""
    job_id: UUID
    status: JobStatus
    total_items: int
    status_breakdown: dict[str, int]
    progress_percent: float
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
