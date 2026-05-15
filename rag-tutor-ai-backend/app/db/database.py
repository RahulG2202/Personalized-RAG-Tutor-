from langchain_chroma import Chroma
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from app.core.config import ingestion_settings, global_settings


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
            self.db = PineconeVectorStore(
                index_name=ingestion_settings.PINECONE_INDEX_NAME,
                embedding=self.get_embeddings(),
                pinecone_api_key=global_settings.PINECONE_API_KEY
            )
        return self.db

    def create_new_db(self, chunks):
        self.db = Chroma.from_documents(
            documents=chunks,
            embedding=self.get_embeddings(),
            index_name=ingestion_settings.PINECONE_INDEX_NAME,
            pinecone_api_key=global_settings.PINECONE_API_KEY
        )

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

    def reset_db(self):
        print("⚠️ Wiping Pinecone Index...")
        self.get_db().delete(delete_all=True)


vector_db = VectorDatabase()
