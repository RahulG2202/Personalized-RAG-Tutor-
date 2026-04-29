from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.tutor_service import tutor_service

router = APIRouter()


@router.post("/ask", response_model=ChatResponse)
async def ask_tutor(request: ChatRequest):
    try:
        answer = tutor_service.ask_question(request)
        return ChatResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
