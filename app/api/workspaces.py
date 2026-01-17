"""
AutoDocs AI - Workspace Endpoints

Handles workspace (tenant) management and membership.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, get_workspace
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
    WorkspaceMemberResponse,
    WorkspaceMemberInvite,
)

router = APIRouter()


@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user: CurrentUser,
    db: DbSession,
):
    """
    List all workspaces the current user has access to.
    """
    # Get workspaces user owns or is member of
    result = await db.execute(
        select(Workspace)
        .join(
            WorkspaceMember,
            WorkspaceMember.workspace_id == Workspace.id,
            isouter=True,
        )
        .where(
            (Workspace.owner_id == current_user.id) |
            (WorkspaceMember.user_id == current_user.id)
        )
        .distinct()
    )
    workspaces = result.scalars().all()
    
    return workspaces


@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Create a new workspace.
    
    The creating user becomes the owner.
    """
    # Check slug uniqueness
    result = await db.execute(
        select(Workspace).where(Workspace.slug == workspace_data.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace slug already exists",
        )
    
    workspace = Workspace(
        name=workspace_data.name,
        slug=workspace_data.slug,
        owner_id=current_user.id,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    
    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace_details(
    workspace_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Get workspace details.
    """
    workspace = await get_workspace(workspace_id, current_user, db)
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    workspace_update: WorkspaceUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Update workspace settings.
    
    Only owner and admins can update.
    """
    workspace = await get_workspace(workspace_id, current_user, db)
    
    # Check if user is owner or admin
    if workspace.owner_id != current_user.id:
        result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == current_user.id,
                WorkspaceMember.role == WorkspaceRole.ADMIN,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owner or admin can update workspace",
            )
    
    update_data = workspace_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workspace, field, value)
    
    await db.commit()
    await db.refresh(workspace)
    
    return workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Delete a workspace.
    
    Only the owner can delete a workspace.
    """
    workspace = await get_workspace(workspace_id, current_user, db)
    
    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner can delete workspace",
        )
    
    await db.delete(workspace)
    await db.commit()


# Member management
@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
async def list_workspace_members(
    workspace_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    List all members of a workspace.
    """
    await get_workspace(workspace_id, current_user, db)
    
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id
        )
    )
    members = result.scalars().all()
    
    return members


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_workspace_member(
    workspace_id: UUID,
    invite_data: WorkspaceMemberInvite,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Invite a user to the workspace.
    
    Only owner and admins can invite.
    """
    workspace = await get_workspace(workspace_id, current_user, db)
    
    # Check permissions
    if workspace.owner_id != current_user.id:
        result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == current_user.id,
                WorkspaceMember.role.in_([WorkspaceRole.ADMIN, WorkspaceRole.OWNER]),
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owner or admin can invite members",
            )
    
    # Find user by email
    from app.models.user import User
    result = await db.execute(
        select(User).where(User.email == invite_data.email.lower())
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check if already member
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member",
        )
    
    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user.id,
        role=invite_data.role,
        invited_by=current_user.id,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    
    return member


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Remove a member from the workspace.
    
    Owner and admins can remove members. Users can remove themselves.
    """
    workspace = await get_workspace(workspace_id, current_user, db)
    
    # Can't remove owner
    if user_id == workspace.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove workspace owner",
        )
    
    # Check permissions (user removing self, or admin/owner)
    if user_id != current_user.id:
        if workspace.owner_id != current_user.id:
            result = await db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == current_user.id,
                    WorkspaceMember.role == WorkspaceRole.ADMIN,
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only owner or admin can remove members",
                )
    
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    
    if member:
        await db.delete(member)
        await db.commit()
