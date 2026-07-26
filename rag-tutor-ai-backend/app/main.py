import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.router import api_v1_router
from app.core.config import global_settings
from app.db.redis_client import ping_redis, close_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()

app = FastAPI(title=global_settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=global_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"status": "Tutor is Online"}

@app.get("/health/redis")
async def redis_health():
    is_connected = await ping_redis()

    if not is_connected:
        raise HTTPException(status_code=503, detail="Redis is not available")

    return {"status": "Redis is Connected"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    is_dev = os.getenv("ENVIRONMENT", "development") == "development"
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=is_dev)
