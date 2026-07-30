import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def env_value(name, default=""):
    return os.getenv(name, default).strip()


def env_int(name, default):
    value = env_value(name, str(default))
    return int(value) if value else default


def env_float(name, default):
    value = env_value(name, str(default))
    return float(value) if value else default


class GlobalSettings(BaseSettings):
    PROJECT_NAME: str = "Personalized RAG Tutor"
    GOOGLE_API_KEY: str = env_value("GOOGLE_API_KEY")
    HUGGINGFACEHUB_API_TOKEN: str = env_value(
        "HUGGINGFACEHUB_API_TOKEN")
    CORS_ORIGINS: str = env_value(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,https://personalized-rag-tutor.vercel.app"
    )
    PINECONE_API_KEY: str = env_value("PINECONE_API_KEY")

    @property
    def cors_origins(self):
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


class IngestionSettings(BaseSettings):
    DATA_DIR: str = "data"
    PINECONE_INDEX_NAME: str = env_value("PINECONE_INDEX_NAME")
    EMBEDDING_MODEL: str = env_value(
        "EMBEDDING_MODEL",
        "ibm-granite/granite-embedding-97m-multilingual-r2"
    )
    EMBEDDING_DIMENSIONS: int = env_int("EMBEDDING_DIMENSIONS", 384)
    HUGGINGFACE_EMBEDDING_API_URL: str = env_value(
        "HUGGINGFACE_EMBEDDING_API_URL",
        "https://router.huggingface.co/hf-inference"
    )
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 100


class ChatSettings(BaseSettings):
    LLM_MODEL: str = "gemini-2.5-flash"
    RETRIVAL_K: int = 3
    HYBRID_ALPHA: float = env_float("HYBRID_ALPHA", 0.5)
    TEMPERATURE: float = 0.7


class S3Settings(BaseSettings):
    AWS_ACCESS_KEY_ID: str = env_value("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = env_value("AWS_SECRET_ACCESS_KEY")
    AWS_SESSION_TOKEN: str = env_value("AWS_SESSION_TOKEN")
    AWS_REGION: str = env_value("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET: str = env_value("AWS_S3_BUCKET")
    AWS_S3_PREFIX: str = env_value("AWS_S3_PREFIX", "materials")


class RedisSettings(BaseSettings):
    REDIS_URL: str = env_value("REDIS_URL", "redis://localhost:6379/0")
    REDIS_SOCKET_CONNECT_TIMEOUT: int = env_int(
        "REDIS_SOCKET_CONNECT_TIMEOUT", 5)
    REDIS_SOCKET_TIMEOUT: int = env_int("REDIS_SOCKET_TIMEOUT", 5)
    REDIS_HEALTH_CHECK_INTERVAL: int = env_int(
        "REDIS_HEALTH_CHECK_INTERVAL", 30)


class CelerySettings(BaseSettings):
    CELERY_BROKER_URL: str = env_value(
        "CELERY_BROKER_URL", env_value("REDIS_URL", "redis://localhost:6379/0"))
    CELERY_RESULT_BACKEND: str = env_value(
        "CELERY_RESULT_BACKEND", env_value("REDIS_URL", "redis://localhost:6379/0"))


global_settings = GlobalSettings()
ingestion_settings = IngestionSettings()
chat_settings = ChatSettings()
s3_settings = S3Settings()
redis_settings = RedisSettings()
celery_settings = CelerySettings()
