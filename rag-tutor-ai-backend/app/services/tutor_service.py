from app.core.engine import get_rag_chat
from app.schemas.chat import ChatRequest


class TutorService:
    def __init__(self):
        self.rag_chain = get_rag_chat()

    def ask_question(self, request: ChatRequest):
        response = self.rag_chain.invoke({"input": request.message})
        return response["answer"]


tutor_service = TutorService()
