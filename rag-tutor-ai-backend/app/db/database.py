from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from app.core.config import ingestion_settings


class VectorDatabase:
    def __init__(self):
        self.embeddings = None
        self.db = None

    def get_embeddings(self):
        if self.embeddings is None:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=ingestion_settings.EMBEDDING_MODEL)
        return self.embeddings

    def get_db(self):
        if self.db is None:
            self.db = Chroma(
                persist_directory=ingestion_settings.DB_PATH,
                embedding_function=self.get_embeddings()
            )
        return self.db

    def create_new_db(self, chunks):
        self.db = Chroma.from_documents(
            documents=chunks,
            embedding=self.get_embeddings(),
            persist_directory=ingestion_settings.DB_PATH
        )

    def get_existing_files(self):
        data = self.get_db().get()
        if not data or not data['metadatas']:
            return set()
        return {m['source_file'] for m in data['metadatas'] if 'source_file' in m}

    def add_documents(self, chunks):
        self.get_db().add_documents(documents=chunks)

    def reset_db(self):
        import shutil
        import os
        if os.path.exists(ingestion_settings.DB_PATH):
            shutil.rmtree(ingestion_settings.DB_PATH)
        self.db = Chroma(
            persist_directory=ingestion_settings.DB_PATH,
            embedding_function=self.get_embeddings()
        )


vector_db = VectorDatabase()
