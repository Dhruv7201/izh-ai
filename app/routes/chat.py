"""Example API route for AI chat."""
from fastapi import APIRouter, HTTPException
from typing import List

from app.helpers.openai_helper import ChatRequest, ChatResponse, Message, openai_helper
from app.helpers.cache_helper import cache_helper

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/completion", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    Generate chat completion using OpenAI.
    
    Args:
        request: Chat completion request
        
    Returns:
        Chat completion response
    """
    try:
        response = await openai_helper.chat_completion(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")


@router.post("/simple")
async def simple_chat(prompt: str, system_message: str = None):
    """
    Simple chat endpoint.
    
    Args:
        prompt: User prompt
        system_message: Optional system message
        
    Returns:
        Generated response
    """
    try:
        response = await openai_helper.simple_completion(
            prompt=prompt,
            system_message=system_message
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
