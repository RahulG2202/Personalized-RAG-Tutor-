import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class GlobalSettings(BaseSettings):
    PROJECT_NAME: str = "Personalized RAG Tutor"
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")


class IngestionSettings(BaseSettings):
    DATA_DIR: str = "data"
    TEMP_DIR: str = "temp_compressed"
    DB_PATH: str = "./chroma_db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 100


class ChatSettings(BaseSettings):
    LLM_MODEL: str = "gemini-2.5-flash"
    RETRIVAL_K: int = 3
    TEMPERATURE: float = 0.7


global_settings = GlobalSettings()
ingestion_settings = IngestionSettings()
chat_settings = ChatSettings()
