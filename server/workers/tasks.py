"""
AutoDocs AI - Celery Tasks

Background task definitions for document processing.
"""
from datetime import datetime, timedelta
from uuid import UUID
from celery import shared_task
from sqlalchemy import select, update, create_engine
from sqlalchemy.orm import Session, sessionmaker

from server.workers.celery_app import celery_app
from server.models.datasource import DataSource, DataSourceRow, DataSourceStatus
from server.models.job import Job, JobItem, JobStatus, JobItemStatus, GenerationMode
from server.models.output import Output, OutputType
from server.services.storage import download_from_s3, upload_to_s3
from server.services.file_parser import parse_file
from server.services.template_engine import render_template, apply_mapping


# Create sync engine for Celery tasks
_sync_engine = None
_SyncSession = None


def get_sync_session():
    """Get synchronous database session for Celery tasks."""
    global _sync_engine, _SyncSession
    
    if _sync_engine is None:
        from server.config import settings
        # Convert async URL to sync
        sync_url = settings.database_url.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
        _sync_engine = create_engine(sync_url)
        _SyncSession = sessionmaker(bind=_sync_engine)
    
    return _SyncSession()


@celery_app.task(bind=True, max_retries=3)
def parse_datasource(self, datasource_id: str):
    """
    Parse and normalize uploaded data source.
    
    1. Download raw file from S3
    2. Parse CSV/XLSX
    3. Infer schema
    4. Store normalized rows
    """
    db = get_sync_session()
    
    try:
        datasource = db.query(DataSource).get(UUID(datasource_id))
        if not datasource:
            return {"error": "DataSource not found"}
        
        # Update status
        datasource.status = DataSourceStatus.PROCESSING
        db.commit()
        
        # Download file
        import asyncio
        content = asyncio.run(download_from_s3(datasource.raw_file_url))
        
        # Parse file
        rows, schema = parse_file(content, datasource.file_type)
        
        # Store schema
        datasource.schema_json = schema
        datasource.row_count = len(rows)
        
        # Delete existing rows (for reprocessing)
        db.query(DataSourceRow).filter(
            DataSourceRow.datasource_id == datasource.id
        ).delete()
        
        # Store normalized rows
        for idx, row_data in enumerate(rows):
            row = DataSourceRow(
                datasource_id=datasource.id,
                row_index=idx,
                row_data=row_data,
            )
            db.add(row)
        
        datasource.status = DataSourceStatus.READY
        db.commit()
        
        return {
            "status": "success",
            "row_count": len(rows),
            "columns": len(schema["columns"]),
        }
    
    except Exception as e:
        if datasource:
            datasource.status = DataSourceStatus.FAILED
            datasource.error_message = str(e)
            db.commit()
        
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
    
    finally:
        db.close()


@celery_app.task(bind=True)
def process_job(self, job_id: str):
    """
    Process a document generation job.
    
    1. Load job and related data
    2. Create job items for each row
    3. Dispatch render tasks (per row or per datasource)
    """
    db = get_sync_session()
    
    try:
        job = db.query(Job).get(UUID(job_id))
        if not job:
            return {"error": "Job not found"}
        
        # Update status
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Get template version
        from server.models.template import TemplateVersion
        template_version = db.query(TemplateVersion).get(job.template_version_id)
        
        # Get datasource rows
        rows = db.query(DataSourceRow).filter(
            DataSourceRow.datasource_id == job.datasource_id
        ).order_by(DataSourceRow.row_index).all()
        
        # Handle based on generation mode
        if job.generation_mode == GenerationMode.per_datasource:
            # Single PDF with all rows - create one job item
            job_item = JobItem(
                job_id=job.id,
                datasource_row_id=rows[0].id if rows else None,
                row_index=0,
                row_data={"_all_rows": True},  # Marker for combined mode
                status=JobItemStatus.PENDING,
            )
            db.add(job_item)
            job.total_items = 1  # Single output
            db.commit()
            
            # Collect all row data
            all_rows_data = [row.row_data for row in rows]
            
            # Dispatch single combined render task
            render_combined_document.delay(
                str(job_item.id),
                template_version.content,
                template_version.css_content or "",
                job.mapping_json,
                job.output_format,
                all_rows_data,
            )
            
            return {
                "status": "processing",
                "mode": "per_datasource",
                "total_pages": len(rows),
            }
        else:
            # Per row mode (original behavior) - create job items for each row
            for row in rows:
                job_item = JobItem(
                    job_id=job.id,
                    datasource_row_id=row.id,
                    row_index=row.row_index,
                    row_data=row.row_data,
                    status=JobItemStatus.PENDING,
                )
                db.add(job_item)
            
            job.total_items = len(rows)
            db.commit()
            
            # Get created job items
            job_items = db.query(JobItem).filter(
                JobItem.job_id == job.id
            ).all()
            
            # Dispatch render tasks
            for item in job_items:
                render_document.delay(
                    str(item.id),
                    template_version.content,
                    template_version.css_content or "",
                    job.mapping_json,
                    job.output_format,
                )
            
            return {
                "status": "processing",
                "mode": "per_row",
                "items_created": len(job_items),
            }
    
    except Exception as e:
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            db.commit()
        raise
    
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def render_document(
    self,
    job_item_id: str,
    template_content: str,
    css_content: str,
    mapping: dict,
    output_format: str,
):
    """
    Render a single document.
    
    1. Apply mapping to row data
    2. Render template
    3. Convert to output format (PDF)
    4. Upload to S3
    """
    db = get_sync_session()
    
    try:
        job_item = db.query(JobItem).get(UUID(job_item_id))
        if not job_item:
            return {"error": "JobItem not found"}
        
        # Update status
        job_item.status = JobItemStatus.PROCESSING
        job_item.started_at = datetime.utcnow()
        db.commit()
        
        # Apply mapping
        mapped_data = apply_mapping(job_item.row_data, mapping)
        
        # Render template
        html = render_template(template_content, css_content, mapped_data)
        
        # Convert to output format
        if output_format == "pdf":
            from server.workers.pdf_generator import generate_pdf
            output_bytes = generate_pdf(html)
            content_type = "application/pdf"
            extension = "pdf"
        elif output_format == "html":
            output_bytes = html.encode("utf-8")
            content_type = "text/html"
            extension = "html"
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        # Upload to S3
        job = db.query(Job).get(job_item.job_id)
        s3_key = f"outputs/{job.workspace_id}/{job.id}/{job_item_id}.{extension}"
        
        import asyncio
        output_url = asyncio.run(
            upload_to_s3(output_bytes, s3_key, content_type)
        )
        
        # Update job item
        job_item.status = JobItemStatus.COMPLETED
        job_item.output_url = output_url
        job_item.file_size_bytes = len(output_bytes)
        job_item.completed_at = datetime.utcnow()
        db.commit()
        
        # Update job progress atomically
        from sqlalchemy import update
        db.execute(
            update(Job)
            .where(Job.id == job_item.job_id)
            .values(completed_items=Job.completed_items + 1)
        )
        db.commit()
        
        # Re-fetch job to check completion
        job = db.query(Job).get(job_item.job_id)
        
        # Check if job is complete
        total_processed = job.completed_items + job.failed_items
        if total_processed >= job.total_items:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            db.commit()
            
            # Trigger bundle creation
            create_bundle.delay(str(job.id))
        
        return {
            "status": "success",
            "output_url": output_url,
            "file_size": len(output_bytes),
        }
    
    except Exception as e:
        if job_item:
            job_item.status = JobItemStatus.FAILED
            job_item.error_message = str(e)
            job_item.retry_count += 1
            
            job = db.query(Job).get(job_item.job_id)
            job.failed_items += 1
            
            db.commit()
        
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
    
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def render_combined_document(
    self,
    job_item_id: str,
    template_content: str,
    css_content: str,
    mapping: dict,
    output_format: str,
    all_rows_data: list,
):
    """
    Render a combined document with all rows (multiple pages).
    
    1. Apply mapping to each row
    2. Render template for each row
    3. Combine into single PDF with page breaks
    4. Upload to S3
    """
    db = get_sync_session()
    
    try:
        job_item = db.query(JobItem).get(UUID(job_item_id))
        if not job_item:
            return {"error": "JobItem not found"}
        
        # Update status
        job_item.status = JobItemStatus.PROCESSING
        job_item.started_at = datetime.utcnow()
        db.commit()
        
        # Render each row and combine with page breaks
        all_pages_html = []
        
        for idx, row_data in enumerate(all_rows_data):
            # Apply mapping
            mapped_data = apply_mapping(row_data, mapping)
            
            # Render template for this row (without full HTML wrapper)
            html_content = render_template(template_content, "", mapped_data)
            
            # Extract body content if it's a full HTML doc
            if "<body" in html_content.lower():
                import re
                body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
                if body_match:
                    html_content = body_match.group(1)
            
            all_pages_html.append(html_content)
        
        # Combine all pages with CSS page breaks
        page_break_css = """
        <style>
            .page-container {
                page-break-after: always;
            }
            .page-container:last-child {
                page-break-after: avoid;
            }
        </style>
        """
        
        combined_body = "\n".join(
            f'<div class="page-container">{page}</div>' 
            for page in all_pages_html
        )
        
        # Build final HTML document
        combined_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    {page_break_css}
    <style>{css_content}</style>
</head>
<body>
    {combined_body}
</body>
</html>"""
        
        # Convert to output format
        if output_format == "pdf":
            from server.workers.pdf_generator import generate_pdf
            output_bytes = generate_pdf(combined_html)
            content_type = "application/pdf"
            extension = "pdf"
        elif output_format == "html":
            output_bytes = combined_html.encode("utf-8")
            content_type = "text/html"
            extension = "html"
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        # Upload to S3
        job = db.query(Job).get(job_item.job_id)
        s3_key = f"outputs/{job.workspace_id}/{job.id}/combined_document.{extension}"
        
        import asyncio
        output_url = asyncio.run(
            upload_to_s3(output_bytes, s3_key, content_type)
        )
        
        # Update job item
        job_item.status = JobItemStatus.COMPLETED
        job_item.output_url = output_url
        job_item.file_size_bytes = len(output_bytes)
        job_item.completed_at = datetime.utcnow()
        
        # Update job progress
        job.completed_items = 1
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        db.commit()
        
        # Create output record for easy access
        output = Output(
            job_id=job.id,
            type=OutputType.single,
            name=f"combined_document.{extension}",
            file_url=output_url,
            file_size_bytes=len(output_bytes),
            mime_type=content_type,
        )
        db.add(output)
        db.commit()
        
        return {
            "status": "success",
            "output_url": output_url,
            "file_size": len(output_bytes),
            "total_pages": len(all_rows_data),
        }
    
    except Exception as e:
        if job_item:
            job_item.status = JobItemStatus.FAILED
            job_item.error_message = str(e)
            job_item.retry_count += 1
            
            job = db.query(Job).get(job_item.job_id)
            job.failed_items += 1
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            
            db.commit()
        
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
    
    finally:
        db.close()


@celery_app.task(bind=True)
def create_bundle(self, job_id: str):
    """
    Create ZIP bundle of all job outputs.
    """
    import zipfile
    from io import BytesIO
    import asyncio
    
    db = get_sync_session()
    
    try:
        job = db.query(Job).get(UUID(job_id))
        if not job:
            return {"error": "Job not found"}
        
        # Get completed items
        items = db.query(JobItem).filter(
            JobItem.job_id == job.id,
            JobItem.status == JobItemStatus.COMPLETED,
        ).all()
        
        if not items:
            return {"status": "no_items"}
        
        # Create ZIP in memory
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in items:
                # Parse S3 URL to get key
                output_url = item.output_url
                if output_url.startswith("s3://"):
                    # Parse s3://bucket/key format
                    _, _, bucket_key = output_url.partition("s3://")
                    _, _, key = bucket_key.partition("/")
                else:
                    key = output_url
                
                # Download file
                content = asyncio.run(download_from_s3(key))
                
                # Add to ZIP with numbered filename
                filename = f"document_{item.row_index + 1:04d}.pdf"
                zf.writestr(filename, content)
        
        # Upload ZIP to S3
        zip_buffer.seek(0)
        s3_key = f"bundles/{job.workspace_id}/{job.id}/bundle.zip"
        
        bundle_url = asyncio.run(
            upload_to_s3(
                zip_buffer.read(),
                s3_key,
                "application/zip",
            )
        )
        
        # Create output record
        output = Output(
            job_id=job.id,
            type=OutputType.bundle,
            name=f"job_{job.id}_bundle.zip",
            file_url=bundle_url,
            file_size_bytes=zip_buffer.tell(),
            mime_type="application/zip",
        )
        db.add(output)
        db.commit()
        
        return {
            "status": "success",
            "bundle_url": bundle_url,
            "item_count": len(items),
        }
    
    except Exception as e:
        raise
    
    finally:
        db.close()


@celery_app.task
def cleanup_expired_outputs():
    """
    Clean up expired output files.
    
    Runs periodically to remove old files.
    """
    import asyncio
    from server.services.storage import delete_from_s3
    
    db = get_sync_session()
    
    try:
        # Find expired outputs
        expired_outputs = db.query(Output).filter(
            Output.expires_at < datetime.utcnow()
        ).all()
        
        deleted_count = 0
        for output in expired_outputs:
            # Delete from S3
            asyncio.run(delete_from_s3(output.file_url))
            
            # Delete record
            db.delete(output)
            deleted_count += 1
        
        db.commit()
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
        }
    
    finally:
        db.close()
