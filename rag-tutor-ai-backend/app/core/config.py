import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def env_value(name, default=""):
    return os.getenv(name, default).strip()


class GlobalSettings(BaseSettings):
    PROJECT_NAME: str = "Personalized RAG Tutor"
    GOOGLE_API_KEY: str = env_value("GOOGLE_API_KEY")
    CORS_ORIGINS: str = env_value(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000"
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
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 100


class ChatSettings(BaseSettings):
    LLM_MODEL: str = "gemini-2.5-flash"
    RETRIVAL_K: int = 3
    TEMPERATURE: float = 0.7


class S3Settings(BaseSettings):
    AWS_ACCESS_KEY_ID: str = env_value("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = env_value("AWS_SECRET_ACCESS_KEY")
    AWS_SESSION_TOKEN: str = env_value("AWS_SESSION_TOKEN")
    AWS_REGION: str = env_value("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET: str = env_value("AWS_S3_BUCKET")
    AWS_S3_PREFIX: str = env_value("AWS_S3_PREFIX", "materials")


global_settings = GlobalSettings()
ingestion_settings = IngestionSettings()
chat_settings = ChatSettings()
s3_settings = S3Settings()
