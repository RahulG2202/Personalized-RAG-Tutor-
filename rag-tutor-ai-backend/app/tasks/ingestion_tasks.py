import asyncio

from app.core.celery_app import celery_app
from app.services.ingest import ingest_service


@celery_app.task(bind=True, name="ingestion.run_ingestion")
def run_ingestion_task(self, reset_db: bool = False):
    self.update_state(state="STARTED", meta={
                      "message": "Ingestion task started."})

    files, page_count = asyncio.run(
        ingest_service.run_ingestion(reset_db=reset_db))

    return {
        "status": "Success",
        "files_processed": files,
        "total_pages_extracted": page_count
    }
