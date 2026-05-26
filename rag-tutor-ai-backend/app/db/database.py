from threading import RLock

from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import ingestion_settings, global_settings


class VectorDatabase:
    def __init__(self):
        self.embeddings = None
        self.db = None
        self._lock = RLock()

    def get_embeddings(self):
        if self.embeddings is None:
            with self._lock:
                if self.embeddings is None:
                    self.embeddings = GoogleGenerativeAIEmbeddings(
                        model=ingestion_settings.EMBEDDING_MODEL,
                        google_api_key=global_settings.GOOGLE_API_KEY
                    )
        return self.embeddings

    def get_db(self):
        if self.db is None:
            with self._lock:
                if self.db is None:
                    self.db = PineconeVectorStore(
                        index_name=ingestion_settings.PINECONE_INDEX_NAME,
                        embedding=self.get_embeddings(),
                        pinecone_api_key=global_settings.PINECONE_API_KEY
                    )
        return self.db

    def warm_up(self):
        db = self.get_db()
        index = getattr(db, "_index", None)

        if index is not None:
            index.describe_index_stats()

        return True

    def check_file_exists(self, filename: str) -> bool:
        """
        Pinecone check: Unlike Chroma, we can't 'get all'. 
        We search for 1 chunk with this filename.
        """
        db = self.get_db()
        # Search for the filename in metadata
        results = db.similarity_search(
            "verification query", 
            k=1, 
            filter={"source_file": filename}
        )
        return len(results) > 0

    def add_documents(self, chunks):
        self.get_db().add_documents(documents=chunks)

    def delete_documents_by_source_files(self, source_files: list[str]):
        unique_source_files = [
            source_file
            for source_file in dict.fromkeys(source_files)
            if source_file
        ]

        if not unique_source_files:
            return []

        db = self.get_db()
        deleted_sources = []

        for source_file in unique_source_files:
            db.delete(filter={"source_file": source_file})
            deleted_sources.append(source_file)

        return deleted_sources

    def reset_db(self):
        print("⚠️ Wiping Pinecone Index...")
        self.get_db().delete(delete_all=True)


vector_db = VectorDatabase()
