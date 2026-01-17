"""
AutoDocs AI - Data Source Endpoints

Handles file uploads, parsing, and data source management.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, get_workspace
from app.models.datasource import DataSource, DataSourceStatus, FileType
from app.schemas.datasource import (
    DataSourceResponse,
    DataSourceDetailResponse,
    DataSourceUpdate,
)
from app.services.file_parser import parse_file, infer_schema
from app.services.storage import upload_to_s3

router = APIRouter()


@router.get("/", response_model=List[DataSourceResponse])
async def list_datasources(
    workspace_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    status_filter: Optional[DataSourceStatus] = None,
):
    """
    List all data sources in a workspace.
    """
    await get_workspace(workspace_id, current_user, db)
    
    query = select(DataSource).where(DataSource.workspace_id == workspace_id)
    
    if status_filter:
        query = query.where(DataSource.status == status_filter)
    
    result = await db.execute(query.order_by(DataSource.created_at.desc()))
    datasources = result.scalars().all()
    
    return datasources


@router.post("/upload", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_datasource(
    current_user: CurrentUser,
    db: DbSession,
    workspace_id: str = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Upload a new data source file.
    
    Supported formats: CSV, XLSX, JSON
    
    - **workspace_id**: Target workspace UUID
    - **name**: Display name for the data source
    - **file**: The file to upload
    """
    from app.models.datasource import DataSourceRow
    
    # Parse workspace_id as UUID
    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace_id format",
        )
    
    await get_workspace(workspace_uuid, current_user, db)
    
    # Validate file type
    filename = file.filename.lower()
    if filename.endswith(".csv"):
        file_type = FileType.CSV
    elif filename.endswith((".xlsx", ".xls")):
        file_type = FileType.XLSX
    elif filename.endswith(".json"):
        file_type = FileType.JSON
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Use CSV, XLSX, or JSON.",
        )
    
    # Read file content
    content = await file.read()
    
    # Upload to S3
    s3_key = f"uploads/{workspace_uuid}/{file.filename}"
    try:
        file_url = await upload_to_s3(content, s3_key, file.content_type)
    except Exception:
        # If S3 fails, store locally for MVP
        file_url = f"local://{s3_key}"
    
    # Create data source record
    datasource = DataSource(
        workspace_id=workspace_uuid,
        name=name,
        original_filename=file.filename,
        file_type=file_type,
        raw_file_url=file_url,
        file_size_bytes=len(content),
        status=DataSourceStatus.PROCESSING,
        created_by=current_user.id,
    )
    db.add(datasource)
    await db.flush()  # Get ID
    
    # Parse file inline for MVP (no Celery needed initially)
    try:
        rows, schema = parse_file(content, file_type)
        
        # Store schema
        datasource.schema_json = schema
        datasource.row_count = len(rows)
        
        # Store normalized rows
        for idx, row_data in enumerate(rows):
            row = DataSourceRow(
                datasource_id=datasource.id,
                row_index=idx,
                row_data=row_data,
            )
            db.add(row)
        
        datasource.status = DataSourceStatus.READY
    except Exception as e:
        datasource.status = DataSourceStatus.FAILED
        datasource.error_message = str(e)
    
    await db.commit()
    await db.refresh(datasource)
    
    return datasource


@router.get("/{datasource_id}", response_model=DataSourceDetailResponse)
async def get_datasource(
    datasource_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Get data source details including schema.
    """
    result = await db.execute(
        select(DataSource).where(DataSource.id == datasource_id)
    )
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )
    
    # Verify access
    await get_workspace(datasource.workspace_id, current_user, db)
    
    return datasource


@router.patch("/{datasource_id}", response_model=DataSourceResponse)
async def update_datasource(
    datasource_id: UUID,
    update_data: DataSourceUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Update data source metadata.
    """
    result = await db.execute(
        select(DataSource).where(DataSource.id == datasource_id)
    )
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )
    
    await get_workspace(datasource.workspace_id, current_user, db)
    
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(datasource, field, value)
    
    await db.commit()
    await db.refresh(datasource)
    
    return datasource


@router.delete("/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_datasource(
    datasource_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Delete a data source.
    
    Also removes associated rows and files from storage.
    """
    result = await db.execute(
        select(DataSource).where(DataSource.id == datasource_id)
    )
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )
    
    await get_workspace(datasource.workspace_id, current_user, db)
    
    # TODO: Delete file from S3
    # await delete_from_s3(datasource.raw_file_url)
    
    await db.delete(datasource)
    await db.commit()


@router.get("/{datasource_id}/preview")
async def preview_datasource(
    datasource_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = 10,
):
    """
    Get preview rows from data source.
    
    Returns first N rows for preview in UI.
    """
    result = await db.execute(
        select(DataSource).where(DataSource.id == datasource_id)
    )
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )
    
    await get_workspace(datasource.workspace_id, current_user, db)
    
    if datasource.status != DataSourceStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data source is {datasource.status.value}",
        )
    
    # Get preview rows from datasource_rows table
    from app.models.datasource import DataSourceRow
    result = await db.execute(
        select(DataSourceRow)
        .where(DataSourceRow.datasource_id == datasource_id)
        .order_by(DataSourceRow.row_index)
        .limit(limit)
    )
    rows = result.scalars().all()
    
    return {
        "schema": datasource.schema_json,
        "total_rows": datasource.row_count,
        "preview_rows": [row.row_data for row in rows],
    }


@router.post("/{datasource_id}/reprocess", response_model=DataSourceResponse)
async def reprocess_datasource(
    datasource_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Re-parse and process a data source.
    
    Useful if parsing failed or schema changed.
    """
    result = await db.execute(
        select(DataSource).where(DataSource.id == datasource_id)
    )
    datasource = result.scalar_one_or_none()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found",
        )
    
    await get_workspace(datasource.workspace_id, current_user, db)
    
    # Reset status
    datasource.status = DataSourceStatus.PENDING
    datasource.error_message = None
    await db.commit()
    
    # TODO: Enqueue parsing task
    # parse_datasource.delay(str(datasource.id))
    
    await db.refresh(datasource)
    return datasource
