from celery import Celery

from app.core.config import celery_settings

celery_app = Celery(
    "rag_tutor_ai",
    broker=celery_settings.CELERY_BROKER_URL,
    backend=celery_settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.ingestion_tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    work_prefetch_multiplier=1,
    broken_connection_retry_on_startup=True,
    result_expires=86400,
)