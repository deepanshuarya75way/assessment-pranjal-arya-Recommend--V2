from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_rag_service import chat_rag_service

router = APIRouter()

@router.post("/chat", response_model=ChatResponse, summary="Natural Language Chatbot with CSV RAG")
async def chat_endpoint(request: ChatRequest):
    try:
        return await chat_rag_service.generate_chat_response(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
