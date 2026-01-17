"""
AutoDocs AI - Output Endpoints

Handles document downloads and delivery.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import select
import io

from server.api.deps import CurrentUser, DbSession, get_workspace
from server.models.output import Output, OutputType
from server.models.job import Job, JobItem, JobStatus
from server.schemas.output import OutputResponse
from server.services.storage import generate_presigned_url, download_from_s3

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=List[OutputResponse])
async def list_job_outputs(
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    output_type: Optional[OutputType] = None,
):
    """
    List all outputs for a job.
    
    Includes individual documents and bundled ZIP files.
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
    
    query = select(Output).where(Output.job_id == job_id)
    
    if output_type:
        query = query.where(Output.type == output_type)
    
    result = await db.execute(query.order_by(Output.created_at.desc()))
    outputs = result.scalars().all()
    
    return outputs


@router.get("/jobs/{job_id}/download")
async def download_job_bundle(
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Download the ZIP bundle for a job.
    
    Streams the file directly from S3 storage.
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
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is {job.status.value}, cannot download",
        )
    
    # Find bundle or single document output
    result = await db.execute(
        select(Output).where(
            Output.job_id == job_id,
            Output.type.in_([OutputType.bundle, OutputType.single]),
        )
    )
    output = result.scalar_one_or_none()
    
    if not output:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output not found. Job may still be packaging.",
        )
    
    # Update download count
    output.download_count += 1
    await db.commit()
    
    # Extract key from s3:// URL
    file_url = output.file_url
    if file_url.startswith("s3://"):
        _, _, bucket_key = file_url.partition("s3://")
        _, _, key = bucket_key.partition("/")
    else:
        key = file_url
    
    # Download file from S3 and stream it
    try:
        file_content = await download_from_s3(key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download: {str(e)}",
        )
    
    # Set filename and content type based on output type
    if output.type == OutputType.single:
        filename = output.name or f"document-{job_id}.pdf"
        media_type = output.mime_type or "application/pdf"
    else:
        filename = f"job-{job_id}-bundle.zip"
        media_type = "application/zip"
    
    # Stream the file
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(file_content)),
        },
    )


@router.get("/items/{item_id}/download")
async def download_single_document(
    item_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Download a single generated document.
    
    Returns redirect to signed S3 URL.
    """
    result = await db.execute(
        select(JobItem).where(JobItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    
    # Get job for workspace verification
    result = await db.execute(
        select(Job).where(Job.id == item.job_id)
    )
    job = result.scalar_one_or_none()
    
    await get_workspace(job.workspace_id, current_user, db)
    
    if not item.output_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not generated",
        )
    
    # Generate presigned URL
    signed_url = await generate_presigned_url(item.output_url, expires_in=3600)
    
    return RedirectResponse(url=signed_url, status_code=status.HTTP_302_FOUND)


@router.get("/jobs/{job_id}/errors")
async def download_error_report(
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Download CSV error report for failed items.
    
    Contains row data and error messages for troubleshooting.
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
    
    # Find error report output
    result = await db.execute(
        select(Output).where(
            Output.job_id == job_id,
            Output.type == OutputType.ERROR_REPORT,
        )
    )
    error_report = result.scalar_one_or_none()
    
    if not error_report:
        # Generate on-the-fly if not cached
        from server.services.job_service import generate_error_report
        error_report = await generate_error_report(job_id, db)
    
    if not error_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No errors to report",
        )
    
    signed_url = await generate_presigned_url(error_report.file_url, expires_in=3600)
    
    return RedirectResponse(url=signed_url, status_code=status.HTTP_302_FOUND)


@router.post("/jobs/{job_id}/create-bundle", response_model=OutputResponse)
async def create_bundle(
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Manually trigger bundle creation for a job.
    
    Useful if automatic bundling failed.
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
    
    if job.status not in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job must be completed or failed to create bundle",
        )
    
    # TODO: Enqueue bundle creation task
    # create_bundle_task.delay(str(job.id))
    
    return {"message": "Bundle creation started"}
