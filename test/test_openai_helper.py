import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.helpers.openai_helper import (
    OpenAIHelper,
    ChatRequest,
    Message,
    EmbeddingRequest,
)


@pytest.fixture
def openai_helper(mock_settings):
    """Create OpenAI helper instance."""
    with patch("app.helpers.openai_helper.settings", mock_settings):
        helper = OpenAIHelper()
        return helper


@pytest.mark.asyncio
async def test_chat_completion_success(openai_helper, mock_openai_client):
    """Test successful chat completion."""
    openai_helper.client = mock_openai_client
    
    request = ChatRequest(
        messages=[
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello")
        ]
    )
    
    response = await openai_helper.chat_completion(request)
    
    assert response.content == "This is a test response"
    assert response.model == "gpt-4o"
    assert response.usage["total_tokens"] == 30
    assert response.finish_reason == "stop"
    
    # Verify API was called
    mock_openai_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_chat_completion_with_custom_parameters(openai_helper, mock_openai_client):
    """Test chat completion with custom parameters."""
    openai_helper.client = mock_openai_client
    
    request = ChatRequest(
        messages=[Message(role="user", content="Hello")],
        model="gpt-3.5-turbo",
        temperature=0.5,
        max_tokens=500,
        top_p=0.9,
        frequency_penalty=0.3,
        presence_penalty=0.3,
        stop=["END"]
    )
    
    response = await openai_helper.chat_completion(request)
    
    assert response.content == "This is a test response"
    
    # Verify parameters were passed
    call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-3.5-turbo"
    assert call_kwargs["temperature"] == 0.5
    assert call_kwargs["max_tokens"] == 500


@pytest.mark.asyncio
async def test_chat_completion_api_error(openai_helper):
    """Test chat completion handles API errors."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=Exception("API Error")
    )
    openai_helper.client = mock_client
    
    request = ChatRequest(
        messages=[Message(role="user", content="Hello")]
    )
    
    with pytest.raises(Exception, match="API Error"):
        await openai_helper.chat_completion(request)


@pytest.mark.asyncio
async def test_simple_completion_success(openai_helper, mock_openai_client):
    """Test simple completion helper method."""
    openai_helper.client = mock_openai_client
    
    response = await openai_helper.simple_completion(
        prompt="Hello",
        system_message="You are helpful"
    )
    
    assert response == "This is a test response"


@pytest.mark.asyncio
async def test_simple_completion_without_system_message(openai_helper, mock_openai_client):
    """Test simple completion without system message."""
    openai_helper.client = mock_openai_client
    
    response = await openai_helper.simple_completion(prompt="Hello")
    
    assert response == "This is a test response"


@pytest.mark.asyncio
async def test_create_embedding_success(openai_helper, mock_openai_client):
    """Test successful embedding generation."""
    openai_helper.client = mock_openai_client
    
    request = EmbeddingRequest(input="Test text")
    response = await openai_helper.create_embedding(request)
    
    assert len(response.embedding) > 0
    assert response.model == "text-embedding-ada-002"
    assert response.usage["total_tokens"] == 5


@pytest.mark.asyncio
async def test_create_embedding_with_custom_model(openai_helper, mock_openai_client):
    """Test embedding with custom model."""
    openai_helper.client = mock_openai_client
    
    request = EmbeddingRequest(
        input="Test text",
        model="text-embedding-3-small"
    )
    
    response = await openai_helper.create_embedding(request)
    
    assert len(response.embedding) > 0
    
    # Verify model was passed
    call_kwargs = mock_openai_client.embeddings.create.call_args.kwargs
    assert call_kwargs["model"] == "text-embedding-3-small"


@pytest.mark.asyncio
async def test_create_embedding_api_error(openai_helper):
    """Test embedding handles API errors."""
    mock_client = AsyncMock()
    mock_client.embeddings.create = AsyncMock(
        side_effect=Exception("API Error")
    )
    openai_helper.client = mock_client
    
    request = EmbeddingRequest(input="Test text")
    
    with pytest.raises(Exception, match="API Error"):
        await openai_helper.create_embedding(request)


def test_message_model_validation():
    """Test Message model validation."""
    message = Message(role="user", content="Hello")
    assert message.role == "user"
    assert message.content == "Hello"


def test_chat_request_validation():
    """Test ChatRequest model validation."""
    request = ChatRequest(
        messages=[Message(role="user", content="Hello")],
        temperature=0.7
    )
    assert len(request.messages) == 1
    assert request.temperature == 0.7


def test_chat_request_invalid_temperature():
    """Test ChatRequest rejects invalid temperature."""
    with pytest.raises(ValueError):
        ChatRequest(
            messages=[Message(role="user", content="Hello")],
            temperature=3.0  # Invalid: > 2
        )


def test_embedding_request_validation():
    """Test EmbeddingRequest model validation."""
    request = EmbeddingRequest(input="Test text")
    assert request.input == "Test text"
    assert request.model == "text-embedding-ada-002"  # Default
