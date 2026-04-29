from fastapi import APIRouter
from app.api.v1 import ingest_endpoints, tutor_endpoints

api_v1_router = APIRouter()

api_v1_router.include_router(
    ingest_endpoints.router, prefix="/ingest", tags=["Ingestion"])

api_v1_router.include_router(
    tutor_endpoints.router, prefix="/tutor", tags=["Tutor"])
