import logging
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config.settings import settings

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Role of the message sender (system, user, assistant)")
    content: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    """Chat completion request model."""
    messages: List[Message] = Field(..., description="List of messages in the conversation")
    model: Optional[str] = Field(default=None, description="Model to use for completion")
    temperature: Optional[float] = Field(default=None, ge=0, le=2, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, gt=0, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1, description="Nucleus sampling parameter")
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2, le=2, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2, le=2, description="Presence penalty")
    stop: Optional[List[str]] = Field(default=None, description="Stop sequences")


class ChatResponse(BaseModel):
    """Chat completion response model."""
    content: str = Field(..., description="Generated response content")
    model: str = Field(..., description="Model used for completion")
    usage: Dict[str, int] = Field(..., description="Token usage information")
    finish_reason: Optional[str] = Field(default=None, description="Reason for completion finish")


class EmbeddingRequest(BaseModel):
    """Embedding request model."""
    input: str = Field(..., description="Text to embed")
    model: str = Field(default="text-embedding-ada-002", description="Model to use for embeddings")


class EmbeddingResponse(BaseModel):
    """Embedding response model."""
    embedding: List[float] = Field(..., description="Embedding vector")
    model: str = Field(..., description="Model used for embedding")
    usage: Dict[str, int] = Field(..., description="Token usage information")


class OpenAIHelper:
    """Helper class for OpenAI API interactions."""
    
    def __init__(self):
        """Initialize OpenAI helper."""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = settings.OPENAI_MODEL
        self.default_max_tokens = settings.OPENAI_MAX_TOKENS
        self.default_temperature = settings.OPENAI_TEMPERATURE
    
    async def chat_completion(
        self, 
        request: ChatRequest
    ) -> ChatResponse:
        """
        Generate chat completion.
        
        Args:
            request: Chat completion request
            
        Returns:
            Chat completion response
        """
        try:
            # Prepare parameters
            model = request.model or self.default_model
            temperature = request.temperature if request.temperature is not None else self.default_temperature
            max_tokens = request.max_tokens or self.default_max_tokens
            
            # Convert messages to dict format
            messages = [msg.model_dump() for msg in request.messages]
            
            # Make API call
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty,
                stop=request.stop,
            )
            
            # Parse response
            choice = response.choices[0]
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            
            logger.info(f"Chat completion: {usage['total_tokens']} tokens used")
            
            return ChatResponse(
                content=choice.message.content,
                model=response.model,
                usage=usage,
                finish_reason=choice.finish_reason,
            )
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            raise
    
    async def simple_completion(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Simple chat completion with just a prompt.
        
        Args:
            prompt: User prompt
            system_message: Optional system message
            **kwargs: Additional parameters
            
        Returns:
            Generated response content
        """
        messages = []
        
        if system_message:
            messages.append(Message(role="system", content=system_message))
        
        messages.append(Message(role="user", content=prompt))
        
        request = ChatRequest(messages=messages, **kwargs)
        response = await self.chat_completion(request)
        
        return response.content
    
    async def streaming_completion(
        self,
        request: ChatRequest
    ):
        """
        Generate streaming chat completion.
        
        Args:
            request: Chat completion request
            
        Yields:
            Content chunks
        """
        try:
            model = request.model or self.default_model
            temperature = request.temperature if request.temperature is not None else self.default_temperature
            max_tokens = request.max_tokens or self.default_max_tokens
            
            messages = [msg.model_dump() for msg in request.messages]
            
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty,
                stop=request.stop,
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Streaming completion error: {e}")
            raise
    
    async def create_embedding(
        self,
        request: EmbeddingRequest
    ) -> EmbeddingResponse:
        """
        Create text embedding.
        
        Args:
            request: Embedding request
            
        Returns:
            Embedding response
        """
        try:
            response = await self.client.embeddings.create(
                model=request.model,
                input=request.input,
            )
            
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            
            logger.info(f"Embedding created: {usage['total_tokens']} tokens used")
            
            return EmbeddingResponse(
                embedding=response.data[0].embedding,
                model=response.model,
                usage=usage,
            )
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise
    
    async def moderate_content(self, text: str) -> Dict[str, Any]:
        """
        Moderate content using OpenAI moderation API.
        
        Args:
            text: Text to moderate
            
        Returns:
            Moderation results
        """
        try:
            response = await self.client.moderations.create(input=text)
            result = response.results[0]
            
            return {
                "flagged": result.flagged,
                "categories": result.categories.model_dump(),
                "category_scores": result.category_scores.model_dump(),
            }
        except Exception as e:
            logger.error(f"Moderation error: {e}")
            raise


# Global OpenAI helper instance
openai_helper = OpenAIHelper()
