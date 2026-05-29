from threading import RLock
from typing import Any

import requests
from langchain_core.embeddings import Embeddings
from langchain_pinecone import PineconeVectorStore
from app.core.config import ingestion_settings, global_settings


class HuggingFaceRouterEmbeddings(Embeddings):
    def __init__(
        self,
        api_key: str,
        model_name: str,
        api_base_url: str,
        dimensions: int
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.dimensions = dimensions
        self.api_url = (
            f"{api_base_url.rstrip('/')}/models/"
            f"{model_name}/pipeline/feature-extraction"
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = self._post({"inputs": [self._clean_text(text) for text in texts]})

        if self._is_vector(response):
            response = [response]

        return [self._normalize(self._coerce_vector(item)) for item in response]

    def embed_query(self, text: str) -> list[float]:
        response = self._post({"inputs": self._clean_text(text)})
        return self._normalize(self._coerce_vector(response))

    def _post(self, payload: dict[str, Any]):
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            response = exc.response
            status_code = response.status_code if response is not None else "unknown"
            response_text = response.text[:500] if response is not None else str(exc)
            permission_hint = (
                " The token was accepted, but it is not allowed to call "
                "Inference Providers. Create a Hugging Face fine-grained "
                "user access token with 'Make calls to Inference Providers' "
                "permission and set it as HUGGINGFACEHUB_API_TOKEN."
                if status_code == 403
                else ""
            )
            raise RuntimeError(
                "Hugging Face embedding request failed "
                f"with status {status_code}: {response_text}{permission_hint}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(
                "Hugging Face embedding request failed. "
                "Check HUGGINGFACEHUB_API_TOKEN, outbound network/DNS access, "
                f"and that {self.api_url} is reachable. Root cause: {exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                "Hugging Face returned a non-JSON embedding response: "
                f"{response.text[:500]}"
            ) from exc

        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"Hugging Face embedding error: {data['error']}")

        if isinstance(data, dict) and "embeddings" in data:
            return data["embeddings"]

        if isinstance(data, dict):
            raise RuntimeError(f"Unexpected Hugging Face embedding response: {data}")

        return data

    def _coerce_vector(self, value):
        if not isinstance(value, list) or not value:
            raise RuntimeError("Hugging Face returned an invalid embedding response.")

        if self._is_vector(value):
            return [float(item) for item in value]

        if all(isinstance(item, list) for item in value):
            token_vectors = [self._coerce_vector(item) for item in value]
            vector_length = len(token_vectors[0])
            return [
                sum(vector[index] for vector in token_vectors) / len(token_vectors)
                for index in range(vector_length)
            ]

        raise RuntimeError("Hugging Face returned an unsupported embedding shape.")

    def _is_vector(self, value):
        return (
            isinstance(value, list)
            and len(value) > 0
            and all(isinstance(item, (int, float)) for item in value)
        )

    def _normalize(self, vector: list[float]) -> list[float]:
        if len(vector) != self.dimensions:
            raise RuntimeError(
                f"Embedding dimension mismatch: expected {self.dimensions}, "
                f"got {len(vector)}. Recreate the Pinecone index or update "
                "EMBEDDING_DIMENSIONS."
            )

        magnitude = sum(value * value for value in vector) ** 0.5

        if magnitude == 0:
            return vector

        return [value / magnitude for value in vector]

    def _clean_text(self, text: str) -> str:
        return text.replace("\n", " ")


class VectorDatabase:
    def __init__(self):
        self.embeddings = None
        self.db = None
        self._lock = RLock()

    def get_embeddings(self):
        if self.embeddings is None:
            with self._lock:
                if self.embeddings is None:
                    if not global_settings.HUGGINGFACEHUB_API_TOKEN:
                        raise RuntimeError(
                            "HUGGINGFACEHUB_API_TOKEN is not configured."
                        )
                    print(f"HUGGINGFACEHUB_API_TOKEN {global_settings.HUGGINGFACEHUB_API_TOKEN}")

                    self.embeddings = HuggingFaceRouterEmbeddings(
                        api_key=global_settings.HUGGINGFACEHUB_API_TOKEN,
                        model_name=ingestion_settings.EMBEDDING_MODEL,
                        api_base_url=ingestion_settings.HUGGINGFACE_EMBEDDING_API_URL,
                        dimensions=ingestion_settings.EMBEDDING_DIMENSIONS
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

        if index is None:
            return {
                "total_vector_count": 0,
                "has_embeddings": False
            }

        stats = index.describe_index_stats()
        total_vector_count = self._extract_total_vector_count(stats)

        return {
            "total_vector_count": total_vector_count,
            "has_embeddings": total_vector_count > 0
        }

    def _extract_total_vector_count(self, stats):
        if isinstance(stats, dict):
            return self._extract_total_vector_count_from_dict(stats)

        to_dict = getattr(stats, "to_dict", None)
        if callable(to_dict):
            return self._extract_total_vector_count_from_dict(to_dict())

        return int(getattr(stats, "total_vector_count", 0) or 0)

    def _extract_total_vector_count_from_dict(self, stats):
        total = stats.get("total_vector_count")

        if total is not None:
            return int(total or 0)

        namespaces = stats.get("namespaces") or {}
        return sum(
            int(namespace_stats.get("vector_count", 0) or 0)
            for namespace_stats in namespaces.values()
        )
    
    def get_existing_files(self):
        try:
            index = getattr(self.get_db(), "_index", None)

            if index is None:
                print("⚠️ No underlying Pinecone index found.")
                return set()
            
            dummy_vector = [0.0] * 384

            results = index.query(
                vector=dummy_vector,
                top_k=10000,
                include_metadata = True
            )

            matches = getattr(results, "matches", None)
            if matches is None and isinstance(results, dict):
                matches = results.get("matches", [])

            existing_files = set()
            for match in (matches or []):
                metadata = getattr(match, "metadata", None)
                if metadata is None and isinstance(match, dict):
                    metadata = match.get("metadata", {})

                source_file = metadata.get("source_file")
                if source_file:
                    existing_files.add(source_file)

            print(f"📁 Found {len(existing_files)} unique files already in Pinecone.")
            return existing_files 
        
        except Exception as e:
            print(f"⚠️ Error fetching existing files from Pinecone: {e}")
            return set()
    def check_file_exists(self, filename: str) -> bool:
        """
        Pinecone check: Unlike Chroma, we can't 'get all'. 
        Query with a placeholder vector so this metadata check does not spend an
        embedding API call before ingestion.
        """
        index = getattr(self.get_db(), "_index", None)

        if index is None:
            return False

        results = index.query(
            vector=[1.0] + [0.0] * (ingestion_settings.EMBEDDING_DIMENSIONS - 1),
            top_k=1,
            filter={"source_file": filename},
            include_metadata=False
        )
        matches = getattr(results, "matches", None)

        if matches is None and isinstance(results, dict):
            matches = results.get("matches", [])

        return len(matches or []) > 0

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
