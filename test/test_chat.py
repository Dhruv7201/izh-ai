import pytest
from unittest.mock import patch, AsyncMock, MagicMock


def test_chat_completion_success(client, sample_chat_request, mock_openai_client):
    """Test successful chat completion."""
    with patch("app.helpers.openai_helper.openai_helper.client", mock_openai_client):
        response = client.post("/chat/completion", json=sample_chat_request)
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "model" in data
        assert "usage" in data
        assert data["content"] == "This is a test response"


def test_chat_completion_validation_error(client):
    """Test chat completion with invalid request."""
    invalid_request = {
        "messages": [{"role": "invalid", "content": "test"}],
        "temperature": 3.0  # Invalid: should be <= 2
    }
    response = client.post("/chat/completion", json=invalid_request)
    assert response.status_code == 422  # Validation error


def test_chat_completion_missing_messages(client):
    """Test chat completion without messages."""
    response = client.post("/chat/completion", json={})
    assert response.status_code == 422


def test_chat_completion_api_error(client, sample_chat_request):
    """Test chat completion when OpenAI API fails."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=Exception("API Error")
    )
    
    with patch("app.helpers.openai_helper.openai_helper.client", mock_client):
        response = client.post("/chat/completion", json=sample_chat_request)
        assert response.status_code == 500
        assert "Chat completion failed" in response.json()["detail"]


def test_simple_chat_success(client, mock_openai_client):
    """Test simple chat endpoint."""
    with patch("app.helpers.openai_helper.openai_helper.client", mock_openai_client):
        response = client.post(
            "/chat/simple",
            params={
                "prompt": "Hello",
                "system_message": "You are helpful"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data


def test_simple_chat_without_system_message(client, mock_openai_client):
    """Test simple chat without system message."""
    with patch("app.helpers.openai_helper.openai_helper.client", mock_openai_client):
        response = client.post(
            "/chat/simple",
            params={"prompt": "Hello"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data


def test_simple_chat_error(client):
    """Test simple chat when API fails."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=Exception("API Error")
    )
    
    with patch("app.helpers.openai_helper.openai_helper.client", mock_client):
        response = client.post(
            "/chat/simple",
            params={"prompt": "Hello"}
        )
        assert response.status_code == 500
        assert "Chat failed" in response.json()["detail"]


def test_chat_completion_with_all_parameters(client, mock_openai_client):
    """Test chat completion with all optional parameters."""
    full_request = {
        "messages": [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ],
        "model": "gpt-4o",
        "temperature": 0.5,
        "max_tokens": 500,
        "top_p": 0.9,
        "frequency_penalty": 0.5,
        "presence_penalty": 0.5,
        "stop": ["END"]
    }
    
    with patch("app.helpers.openai_helper.openai_helper.client", mock_openai_client):
        response = client.post("/chat/completion", json=full_request)
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
