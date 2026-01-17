"""
AutoDocs AI - DataSource Model
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4
import enum

from sqlalchemy import String, Integer, BigInteger, ForeignKey, DateTime, Text, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class DataSourceStatus(str, enum.Enum):
    """Data source processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class FileType(str, enum.Enum):
    """Supported file types."""
    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"
    GOOGLE_SHEETS = "google_sheets"


class DataSource(Base):
    """Uploaded data source model."""
    
    __tablename__ = "datasources"
    
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(512))
    file_type: Mapped[FileType] = mapped_column(
        SQLEnum(FileType),
        nullable=False,
    )
    raw_file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    schema_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    row_count: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[DataSourceStatus] = mapped_column(
        SQLEnum(DataSourceStatus),
        default=DataSourceStatus.PENDING,
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="datasources",
    )
    rows: Mapped[list["DataSourceRow"]] = relationship(
        "DataSourceRow",
        back_populates="datasource",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<DataSource {self.name}>"


class DataSourceRow(Base):
    """Normalized data source row model."""
    
    __tablename__ = "datasource_rows"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    datasource_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("datasources.id"),
        nullable=False,
        index=True,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    row_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validation_errors: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Relationships
    datasource: Mapped["DataSource"] = relationship(
        "DataSource",
        back_populates="rows",
    )
    
    def __repr__(self) -> str:
        return f"<DataSourceRow {self.datasource_id}:{self.row_index}>"
