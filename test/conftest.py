import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.config.settings import Settings


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return Settings(
        APP_NAME="Test App",
        APP_VERSION="0.1.0",
        DEBUG=True,
        OPENAI_API_KEY="test-api-key",
        OPENAI_MODEL="gpt-4o",
        OPENAI_MAX_TOKENS=1000,
        OPENAI_TEMPERATURE=0.7,
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5432,
        POSTGRES_USER="test_user",
        POSTGRES_PASSWORD="test_password",
        POSTGRES_DB="test_db",
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        REDIS_DB=0,
        CACHE_TTL=300,
        CACHE_ENABLED=True,
        CORS_ORIGINS="*",
    )


@pytest.fixture
def mock_db_config():
    """Mock database configuration."""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    mock.get_pool = MagicMock()
    return mock


@pytest.fixture
def mock_redis_config():
    """Mock Redis configuration."""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    mock.get_client = MagicMock()
    return mock


@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.ping = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    mock = AsyncMock()
    
    # Mock chat completion response
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "This is a test response"
    mock_choice.message = mock_message
    mock_choice.finish_reason = "stop"
    mock_response.choices = [mock_choice]
    
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 20
    mock_usage.total_tokens = 30
    mock_response.usage = mock_usage
    mock_response.model = "gpt-4o"
    
    mock.chat.completions.create = AsyncMock(return_value=mock_response)
    
    # Mock embeddings response
    mock_embedding_response = MagicMock()
    mock_embedding_data = MagicMock()
    mock_embedding_data.embedding = [0.1, 0.2, 0.3] * 512  # Simulated embedding vector
    mock_embedding_response.data = [mock_embedding_data]
    mock_embedding_response.model = "text-embedding-ada-002"
    
    mock_embedding_usage = MagicMock()
    mock_embedding_usage.prompt_tokens = 5
    mock_embedding_usage.total_tokens = 5
    mock_embedding_response.usage = mock_embedding_usage
    
    mock.embeddings.create = AsyncMock(return_value=mock_embedding_response)
    
    return mock


@pytest.fixture
def client(mock_db_config, mock_redis_config):
    """Create a test client with mocked dependencies."""
    with patch("app.main.db_config", mock_db_config), \
         patch("app.main.redis_config", mock_redis_config), \
         patch("app.config.database.db_config", mock_db_config), \
         patch("app.config.redis_config.redis_config", mock_redis_config):
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
async def async_client(mock_db_config, mock_redis_config) -> AsyncGenerator:
    """Create an async test client with mocked dependencies."""
    with patch("app.main.db_config", mock_db_config), \
         patch("app.main.redis_config", mock_redis_config), \
         patch("app.config.database.db_config", mock_db_config), \
         patch("app.config.redis_config.redis_config", mock_redis_config):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def sample_chat_messages():
    """Sample chat messages for testing."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]


@pytest.fixture
def sample_chat_request():
    """Sample chat request for testing."""
    return {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 1000
    }


@pytest.fixture
def sample_embedding_text():
    """Sample text for embedding tests."""
    return "This is a sample text for embedding."
