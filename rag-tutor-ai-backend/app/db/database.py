from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from app.core.config import ingestion_settings


class VectorDatabase:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=ingestion_settings.EMBEDDING_MODEL)
        self.db = Chroma(
            persist_directory=ingestion_settings.DB_PATH,
            embedding_function=self.embeddings
        )

    def create_new_db(self, chunks):
        self.db = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=ingestion_settings.DB_PATH
        )

    def get_existing_files(self):
        data = self.db.get()
        if not data or not data['metadatas']:
            return set()
        return {m['source_file'] for m in data['metadatas'] if 'source_file' in m}

    def add_documents(self, chunks):
        self.db.add_documents(documents=chunks)

    def reset_db(self):
        import shutil
        import os
        if os.path.exists(ingestion_settings.DB_PATH):
            shutil.rmtree(ingestion_settings.DB_PATH)
        self.db = Chroma(
            persist_directory=ingestion_settings.DB_PATH,
            embedding_function=self.embeddings
        )


vector_db = VectorDatabase()
