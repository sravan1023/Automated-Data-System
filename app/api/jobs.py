"""
AutoDocs AI - Job Endpoints

Handles job creation, status monitoring, and management.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DbSession, get_workspace
from app.models.job import Job, JobItem, JobStatus, JobItemStatus
from app.schemas.job import (
    JobCreate,
    JobResponse,
    JobDetailResponse,
    JobItemResponse,
)

router = APIRouter()


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    workspace_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    status_filter: Optional[JobStatus] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List jobs in a workspace.
    
    - **status_filter**: Filter by job status
    - **limit**: Max results (default 50)
    - **offset**: Pagination offset
    """
    await get_workspace(workspace_id, current_user, db)
    
    query = select(Job).where(Job.workspace_id == workspace_id)
    
    if status_filter:
        query = query.where(Job.status == status_filter)
    
    result = await db.execute(
        query
        .order_by(Job.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    jobs = result.scalars().all()
    
    return jobs


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Create a new document generation job.
    
    - **template_id**: Template to use
    - **datasource_id**: Data source with rows to process
    - **mapping**: Field mapping {template_var: datasource_column}
    - **output_format**: Output format (pdf, docx, html)
    """
    await get_workspace(job_data.workspace_id, current_user, db)
    
    # Validate template exists
    from app.models.template import Template, TemplateVersion
    result = await db.execute(
        select(Template).where(
            Template.id == job_data.template_id,
            Template.workspace_id == job_data.workspace_id,
        )
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Get or ensure active version exists
    if not template.active_version_id:
        # For MVP, check if any version exists
        result = await db.execute(
            select(TemplateVersion)
            .where(TemplateVersion.template_id == template.id)
            .order_by(TemplateVersion.version.desc())
            .limit(1)
        )
        version = result.scalar_one_or_none()
        if version:
            template.active_version_id = version.id
            await db.commit()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template has no versions",
            )
    
    # Validate datasource exists and is ready
    from app.models.datasource import DataSource, DataSourceStatus
    result = await db.execute(
        select(DataSource).where(
            DataSource.id == job_data.datasource_id,
            DataSource.workspace_id == job_data.workspace_id,
        )
    )
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )
    
    if datasource.status != DataSourceStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data source is {datasource.status.value}, must be ready",
        )
    
    # Create job with auto-mapping if not provided
    mapping = job_data.mapping or {}
    if not mapping and datasource.schema_json:
        # Auto-create identity mapping
        columns = datasource.schema_json.get("columns", [])
        mapping = {col["name"]: col["name"] for col in columns}
    
    # Create job
    job = Job(
        workspace_id=job_data.workspace_id,
        template_id=job_data.template_id,
        template_version_id=template.active_version_id,
        datasource_id=job_data.datasource_id,
        mapping_json=mapping,
        output_format=job_data.output_format,
        generation_mode=job_data.generation_mode,
        priority=job_data.priority,
        total_items=datasource.row_count or 0,
        created_by=current_user.id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Enqueue job processing
    from app.workers.tasks import process_job
    process_job.delay(str(job.id))
    
    return job


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Get job details with processing status.
    """
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    await get_workspace(job.workspace_id, current_user, db)
    
    return job


@router.get("/{job_id}/items", response_model=List[JobItemResponse])
async def list_job_items(
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    status_filter: Optional[JobItemStatus] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    List items (rows) in a job.
    
    Filter by status to find failed items.
    """
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    await get_workspace(job.workspace_id, current_user, db)
    
    query = select(JobItem).where(JobItem.job_id == job_id)
    
    if status_filter:
        query = query.where(JobItem.status == status_filter)
    
    result = await db.execute(
        query
        .order_by(JobItem.row_index)
        .limit(limit)
        .offset(offset)
    )
    items = result.scalars().all()
    
    return items


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Cancel a pending or processing job.
    
    Items already completed will remain.
    """
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    await get_workspace(job.workspace_id, current_user, db)
    
    if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status {job.status.value}",
        )
    
    job.status = JobStatus.CANCELLED
    await db.commit()
    await db.refresh(job)
    
    # TODO: Send cancel signal to workers
    
    return job


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_failed_items(
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Retry all failed items in a job.
    """
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    await get_workspace(job.workspace_id, current_user, db)
    
    # Reset failed items to pending
    from sqlalchemy import update
    await db.execute(
        update(JobItem)
        .where(
            JobItem.job_id == job_id,
            JobItem.status == JobItemStatus.FAILED,
        )
        .values(
            status=JobItemStatus.PENDING,
            error_message=None,
        )
    )
    
    # Update job status
    job.status = JobStatus.PROCESSING
    job.failed_items = 0
    await db.commit()
    await db.refresh(job)
    
    # TODO: Enqueue retry processing
    # retry_job.delay(str(job.id))
    
    return job


@router.get("/{job_id}/stats")
async def get_job_stats(
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Get detailed job statistics.
    """
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    await get_workspace(job.workspace_id, current_user, db)
    
    # Get status counts
    result = await db.execute(
        select(JobItem.status, func.count(JobItem.id))
        .where(JobItem.job_id == job_id)
        .group_by(JobItem.status)
    )
    status_counts = {status.value: count for status, count in result.all()}
    
    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "total_items": job.total_items,
        "status_breakdown": status_counts,
        "progress_percent": round(
            (job.completed_items + job.failed_items) / max(job.total_items, 1) * 100, 1
        ),
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
