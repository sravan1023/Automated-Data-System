"""
AutoDocs AI - Template Model
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4
import enum

from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.database import Base

if TYPE_CHECKING:
    from server.models.workspace import Workspace


class ContentType(str, enum.Enum):
    """Template content types."""
    HTML = "html"
    DOCX = "docx"
    EMAIL = "email"


class VersionStatus(str, enum.Enum):
    """Template version status."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ARCHIVED = "archived"


class Template(Base):
    """Document template model."""
    
    __tablename__ = "templates"
    
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
    description: Mapped[Optional[str]] = mapped_column(Text)
    content_type: Mapped[ContentType] = mapped_column(
        SQLEnum(ContentType),
        default=ContentType.HTML,
    )
    active_version_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("template_versions.id", use_alter=True),
    )
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
        back_populates="templates",
    )
    versions: Mapped[List["TemplateVersion"]] = relationship(
        "TemplateVersion",
        back_populates="template",
        foreign_keys="TemplateVersion.template_id",
        cascade="all, delete-orphan",
    )
    active_version: Mapped[Optional["TemplateVersion"]] = relationship(
        "TemplateVersion",
        foreign_keys=[active_version_id],
        post_update=True,
    )
    
    def __repr__(self) -> str:
        return f"<Template {self.name}>"


class TemplateVersion(Base):
    """Template version model for version control."""
    
    __tablename__ = "template_versions"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    template_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("templates.id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    css_content: Mapped[Optional[str]] = mapped_column(Text)
    schema_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    preview_url: Mapped[Optional[str]] = mapped_column(String(1024))
    status: Mapped[VersionStatus] = mapped_column(
        SQLEnum(VersionStatus),
        default=VersionStatus.DRAFT,
        index=True,
    )
    change_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Relationships
    template: Mapped["Template"] = relationship(
        "Template",
        back_populates="versions",
        foreign_keys=[template_id],
    )
    
    def __repr__(self) -> str:
        return f"<TemplateVersion {self.template_id} v{self.version}>"
