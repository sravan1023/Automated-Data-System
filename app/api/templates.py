"""
AutoDocs AI - Template Endpoints

Handles template CRUD and version management.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, get_workspace
from app.models.template import Template, TemplateVersion, ContentType, VersionStatus
from app.schemas.template import (
    TemplateCreate,
    TemplateResponse,
    TemplateDetailResponse,
    TemplateUpdate,
    TemplateVersionCreate,
    TemplateVersionResponse,
)

router = APIRouter()


@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    workspace_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    content_type: Optional[ContentType] = None,
):
    """
    List all templates in a workspace.
    """
    await get_workspace(workspace_id, current_user, db)
    
    query = select(Template).where(Template.workspace_id == workspace_id)
    
    if content_type:
        query = query.where(Template.content_type == content_type)
    
    result = await db.execute(query.order_by(Template.updated_at.desc()))
    templates = result.scalars().all()
    
    return templates


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Create a new template.
    
    Creates the template and an initial draft version.
    """
    await get_workspace(template_data.workspace_id, current_user, db)
    
    # Create template
    template = Template(
        workspace_id=template_data.workspace_id,
        name=template_data.name,
        description=template_data.description,
        content_type=template_data.content_type,
        created_by=current_user.id,
    )
    db.add(template)
    await db.flush()  # Get template ID
    
    # Create initial version
    version = TemplateVersion(
        template_id=template.id,
        version=1,
        content=template_data.content,
        css_content=template_data.css_content,
        schema_json=template_data.schema_json,
        status=VersionStatus.DRAFT,
        created_by=current_user.id,
    )
    db.add(version)
    await db.flush()
    
    # Set active version
    template.active_version_id = version.id
    
    await db.commit()
    await db.refresh(template)
    
    return template


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(
    template_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Get template details with active version content.
    """
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(Template)
        .options(selectinload(Template.active_version))
        .where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    await get_workspace(template.workspace_id, current_user, db)
    
    return template


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    update_data: TemplateUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Update template metadata.
    
    To update content, create a new version.
    """
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    await get_workspace(template.workspace_id, current_user, db)
    
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    
    await db.commit()
    await db.refresh(template)
    
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Delete a template and all its versions.
    """
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    await get_workspace(template.workspace_id, current_user, db)
    
    await db.delete(template)
    await db.commit()


# Version management
@router.get("/{template_id}/versions", response_model=List[TemplateVersionResponse])
async def list_template_versions(
    template_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    List all versions of a template.
    """
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    await get_workspace(template.workspace_id, current_user, db)
    
    result = await db.execute(
        select(TemplateVersion)
        .where(TemplateVersion.template_id == template_id)
        .order_by(TemplateVersion.version.desc())
    )
    versions = result.scalars().all()
    
    return versions


@router.post("/{template_id}/versions", response_model=TemplateVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_template_version(
    template_id: UUID,
    version_data: TemplateVersionCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Create a new version of a template.
    
    Does not automatically set as active.
    """
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    await get_workspace(template.workspace_id, current_user, db)
    
    # Get next version number
    result = await db.execute(
        select(TemplateVersion.version)
        .where(TemplateVersion.template_id == template_id)
        .order_by(TemplateVersion.version.desc())
        .limit(1)
    )
    last_version = result.scalar() or 0
    
    version = TemplateVersion(
        template_id=template_id,
        version=last_version + 1,
        content=version_data.content,
        css_content=version_data.css_content,
        schema_json=version_data.schema_json,
        change_notes=version_data.change_notes,
        status=VersionStatus.DRAFT,
        created_by=current_user.id,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    
    return version


@router.post("/{template_id}/versions/{version_id}/activate", response_model=TemplateResponse)
async def activate_template_version(
    template_id: UUID,
    version_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Set a version as the active version for the template.
    """
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    await get_workspace(template.workspace_id, current_user, db)
    
    result = await db.execute(
        select(TemplateVersion).where(
            TemplateVersion.id == version_id,
            TemplateVersion.template_id == template_id,
        )
    )
    version = result.scalar_one_or_none()
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )
    
    template.active_version_id = version_id
    await db.commit()
    await db.refresh(template)
    
    return template


@router.post("/{template_id}/preview")
async def preview_template(
    template_id: UUID,
    sample_data: dict,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Render template with sample data for preview.
    
    Returns rendered HTML (not PDF).
    """
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    await get_workspace(template.workspace_id, current_user, db)
    
    # Get active version
    result = await db.execute(
        select(TemplateVersion).where(
            TemplateVersion.id == template.active_version_id
        )
    )
    version = result.scalar_one_or_none()
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active version",
        )
    
    # Render template
    from app.services.template_engine import render_template
    
    try:
        rendered_html = render_template(
            version.content,
            version.css_content or "",
            sample_data,
        )
        return {"html": rendered_html}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template render error: {str(e)}",
        )
