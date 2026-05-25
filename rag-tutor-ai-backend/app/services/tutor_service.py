from pathlib import PurePosixPath

from app.core.engine import get_rag_chat
from app.schemas.chat import ChatRequest


class TutorService:
    def __init__(self):
        self.rag_chain = None

    def get_rag_chain(self):
        if self.rag_chain is None:
            self.rag_chain = get_rag_chat()
        return self.rag_chain

    def ask_question(self, request: ChatRequest):
        response = self.get_rag_chain().invoke({"input": request.message})
        sources = []

        for document in response.get("context", []):
            metadata = getattr(document, "metadata", {}) or {}
            source = (
                metadata.get("source_name")
                or metadata.get("source_file")
                or metadata.get("source")
            )

            if source:
                sources.append(PurePosixPath(str(source)).name)

        return {
            "answer": response["answer"],
            "sources": list(dict.fromkeys(sources)),
        }


tutor_service = TutorService()
