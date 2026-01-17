"""
AutoDocs AI - Celery Configuration

Celery app setup for background task processing.
"""
from celery import Celery

from server.config import settings


# Create Celery app
celery_app = Celery(
    "autodocs",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    
    # Queue configuration
    task_routes={
        "server.workers.tasks.parse_datasource": {"queue": "ingest"},
        "server.workers.tasks.process_job": {"queue": "render"},
        "server.workers.tasks.render_document": {"queue": "render"},
        "server.workers.tasks.render_combined_document": {"queue": "render"},
        "server.workers.tasks.create_bundle": {"queue": "package"},
    },
    
    # Beat scheduler (for periodic tasks)
    beat_schedule={
        "cleanup-expired-outputs": {
            "task": "server.workers.tasks.cleanup_expired_outputs",
            "schedule": 3600.0,  # Every hour
        },
    },
)

# Autodiscover tasks
celery_app.autodiscover_tasks(["server.workers"])


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing."""
    print(f"Request: {self.request!r}")
