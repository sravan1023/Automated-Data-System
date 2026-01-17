"""
AutoDocs AI - DataSource Schemas
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.models.datasource import DataSourceStatus, FileType


class DataSourceCreate(BaseModel):
    """Schema for datasource creation (used internally after upload)."""
    workspace_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    file_type: FileType


class DataSourceUpdate(BaseModel):
    """Schema for datasource update."""
    name: str | None = Field(None, min_length=1, max_length=255)


class DataSourceResponse(BaseModel):
    """Schema for datasource response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    workspace_id: UUID
    name: str
    original_filename: str | None = None
    file_type: FileType
    file_size_bytes: int | None
    row_count: int | None
    status: DataSourceStatus
    error_message: str | None
    created_at: datetime


class DataSourceDetailResponse(DataSourceResponse):
    """Schema for datasource detail response with schema."""
    schema_json: dict | None


class SchemaColumn(BaseModel):
    """Schema for inferred column."""
    name: str
    type: str  # string, number, date, boolean
    nullable: bool
    sample_values: list[str | None]


class DataSourceSchema(BaseModel):
    """Schema for datasource schema."""
    columns: list[SchemaColumn]
    total_rows: int
    has_headers: bool
