"""
AutoDocs AI - Workspace Model
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4
import enum

from sqlalchemy import String, Boolean, BigInteger, ForeignKey, DateTime, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.datasource import DataSource
    from app.models.template import Template
    from app.models.job import Job


class WorkspacePlan(str, enum.Enum):
    """Workspace subscription plans."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class WorkspaceRole(str, enum.Enum):
    """Workspace member roles."""
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Workspace(Base):
    """Workspace (tenant) model."""
    
    __tablename__ = "workspaces"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    plan: Mapped[WorkspacePlan] = mapped_column(
        SQLEnum(WorkspacePlan),
        default=WorkspacePlan.FREE,
    )
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_workspaces",
        foreign_keys=[owner_id],
    )
    members: Mapped[List["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    datasources: Mapped[List["DataSource"]] = relationship(
        "DataSource",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    templates: Mapped[List["Template"]] = relationship(
        "Template",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    jobs: Mapped[List["Job"]] = relationship(
        "Job",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Workspace {self.slug}>"


class WorkspaceMember(Base):
    """Workspace membership model."""
    
    __tablename__ = "workspace_members"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workspaces.id"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    role: Mapped[WorkspaceRole] = mapped_column(
        SQLEnum(WorkspaceRole),
        default=WorkspaceRole.VIEWER,
    )
    invited_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="workspace_memberships",
        foreign_keys=[user_id],
    )
    
    def __repr__(self) -> str:
        return f"<WorkspaceMember {self.user_id} in {self.workspace_id}>"
