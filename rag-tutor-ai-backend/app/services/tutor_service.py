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
        return response["answer"]


tutor_service = TutorService()
