"""
AutoDocs AI - Output Model
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4
import enum

from sqlalchemy import String, Integer, BigInteger, ForeignKey, DateTime, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.database import Base

if TYPE_CHECKING:
    from server.models.job import Job


class OutputType(str, enum.Enum):
    """Output file types."""
    document = "document"
    bundle = "bundle"
    single = "single"  # Combined document (single PDF with multiple pages)
    error_report = "error_report"


class Output(Base):
    """Generated output file model."""
    
    __tablename__ = "outputs"
    
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
    type: Mapped[OutputType] = mapped_column(
        SQLEnum(OutputType),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Relationships
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="outputs",
    )
    
    def __repr__(self) -> str:
        return f"<Output {self.name} ({self.type.value})>"
