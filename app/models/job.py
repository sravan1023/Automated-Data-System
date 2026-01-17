"""
AutoDocs AI - Job Model
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4
import enum

from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.output import Output


class JobStatus(str, enum.Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobItemStatus(str, enum.Enum):
    """Individual job item status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class GenerationMode(str, enum.Enum):
    """Document generation mode."""
    per_row = "per_row"  # One PDF per row (multiple documents)
    per_datasource = "per_datasource"  # Single PDF with all rows (multiple pages)


class Job(Base):
    """Document generation job model."""
    
    __tablename__ = "jobs"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("templates.id"),
        nullable=False,
    )
    template_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("template_versions.id"),
        nullable=False,
    )
    datasource_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("datasources.id"),
        nullable=False,
    )
    mapping_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    output_format: Mapped[str] = mapped_column(String(20), default="pdf")
    generation_mode: Mapped[GenerationMode] = mapped_column(
        SQLEnum(GenerationMode),
        default=GenerationMode.per_row,
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus),
        default=JobStatus.PENDING,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, default=5)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="jobs",
    )
    items: Mapped[List["JobItem"]] = relationship(
        "JobItem",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    outputs: Mapped[List["Output"]] = relationship(
        "Output",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    
    @property
    def progress_percent(self) -> float:
        """Calculate job progress percentage."""
        if self.total_items == 0:
            return 0.0
        return round(
            (self.completed_items + self.failed_items) / self.total_items * 100, 1
        )
    
    def __repr__(self) -> str:
        return f"<Job {self.id} {self.status.value}>"


class JobItem(Base):
    """Individual job item (one document) model."""
    
    __tablename__ = "job_items"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jobs.id"),
        nullable=False,
        index=True,
    )
    datasource_row_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("datasource_rows.id"),
        nullable=False,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    row_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[JobItemStatus] = mapped_column(
        SQLEnum(JobItemStatus),
        default=JobItemStatus.PENDING,
        index=True,
    )
    output_url: Mapped[Optional[str]] = mapped_column(String(1024))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="items",
    )
    
    def __repr__(self) -> str:
        return f"<JobItem {self.job_id}:{self.row_index}>"
