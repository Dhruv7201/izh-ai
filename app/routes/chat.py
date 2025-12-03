from fastapi import APIRouter, HTTPException, Request, Query
from typing import List, Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.helpers.openai_helper import ChatRequest, ChatResponse, Message, openai_helper
from app.helpers.cache_helper import cache_helper
from app.config.settings import settings

router = APIRouter(prefix="/chat", tags=["chat"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/completion", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_CHAT_COMPLETION)
async def chat_completion(
    request: Request, 
    chat_request: ChatRequest,
    mask_pii: bool = Query(True, description="Mask PII before sending to AI")
):
    """
    Generate chat completion using OpenAI.
    
    Args:
        request: FastAPI request object (for rate limiting)
        chat_request: Chat completion request
        mask_pii: Whether to mask PII in messages (default: True)
        
    Returns:
        Chat completion response
    """
    try:
        response = await openai_helper.chat_completion(chat_request, mask_pii=mask_pii)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")


@router.post("/simple")
@limiter.limit(settings.RATE_LIMIT_SIMPLE_CHAT)
async def simple_chat(
    request: Request, 
    prompt: str, 
    system_message: Optional[str] = None,
    mask_pii: bool = Query(True, description="Mask PII before sending to AI")
):
    """
    Simple chat endpoint.
    
    Args:
        request: FastAPI request object (for rate limiting)
        prompt: User prompt
        system_message: Optional system message
        mask_pii: Whether to mask PII before sending to AI (default: True)
        
    Returns:
        Generated response
    """
    try:
        response = await openai_helper.simple_completion(
            prompt=prompt,
            system_message=system_message,
            mask_pii=mask_pii
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
