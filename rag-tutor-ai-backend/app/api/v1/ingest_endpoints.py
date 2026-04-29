from fastapi import APIRouter, Query
from app.services.ingest import ingest_service

router = APIRouter()


@router.post("/run-ingestion")
async def run_ingestion(reset_db: bool = Query(False)):
    files, page_count = await ingest_service.run_ingestion(reset_db=reset_db)
    return {
        "status": "Success",
        "files_processed": files,
        "total_pages_extracted": page_count
    }
