"""
AutoDocs AI - User Endpoints

Handles user profile management.
"""
from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select, func
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import UserResponse, UserUpdate, UserPasswordChange
from app.models.workspace import Workspace
from app.models.template import Template
from app.models.job import Job
from app.models.output import Output, OutputType

router = APIRouter()

# Password hashing - use argon2 instead of bcrypt
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    workspaces: int
    templates: int
    documents_generated: int


@router.get("/me/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Get dashboard statistics for the current user.
    
    Returns counts of workspaces, templates, and generated documents.
    """
    # Count workspaces
    workspace_result = await db.execute(
        select(func.count(Workspace.id)).where(Workspace.owner_id == current_user.id)
    )
    workspace_count = workspace_result.scalar() or 0
    
    # Get user's workspace IDs
    workspace_ids_result = await db.execute(
        select(Workspace.id).where(Workspace.owner_id == current_user.id)
    )
    workspace_ids = [row[0] for row in workspace_ids_result.all()]
    
    # Count templates in user's workspaces
    template_count = 0
    if workspace_ids:
        template_result = await db.execute(
            select(func.count(Template.id)).where(Template.workspace_id.in_(workspace_ids))
        )
        template_count = template_result.scalar() or 0
    
    # Count generated documents (outputs of type document, bundle, or single)
    document_count = 0
    if workspace_ids:
        # Get job IDs for user's workspaces
        job_ids_result = await db.execute(
            select(Job.id).where(Job.workspace_id.in_(workspace_ids))
        )
        job_ids = [row[0] for row in job_ids_result.all()]
        
        if job_ids:
            document_result = await db.execute(
                select(func.count(Output.id)).where(
                    Output.job_id.in_(job_ids),
                    Output.type.in_([OutputType.document, OutputType.bundle, OutputType.single])
                )
            )
            document_count = document_result.scalar() or 0
    
    return DashboardStats(
        workspaces=workspace_count,
        templates=template_count,
        documents_generated=document_count,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: CurrentUser):
    """
    Get current authenticated user's profile.
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Update current user's profile.
    
    Only provided fields will be updated.
    """
    update_data = user_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Delete current user's account.
    
    This is a soft delete - sets is_active to False.
    """
    current_user.is_active = False
    await db.commit()


@router.post("/me/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: UserPasswordChange,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Change current user's password.
    
    Requires the current password for verification.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}
