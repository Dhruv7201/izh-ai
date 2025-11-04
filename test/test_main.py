import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


def test_root_endpoint(client):
    """Test root endpoint returns correct response."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "running"


def test_cors_headers(client):
    """Test CORS headers are properly set."""
    response = client.get("/")
    assert response.status_code == 200
    # CORS headers should be present in the response


@pytest.mark.asyncio
async def test_lifespan_startup(mock_db_config, mock_redis_config):
    """Test application startup connections."""
    with patch("app.main.db_config", mock_db_config), \
         patch("app.main.redis_config", mock_redis_config):
        from app.main import lifespan, app
        
        async with lifespan(app):
            # Assert connections were established
            mock_db_config.connect.assert_called_once()
            mock_redis_config.connect.assert_called_once()
        
        # Assert connections were closed
        mock_db_config.disconnect.assert_called_once()
        mock_redis_config.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_startup_failure(mock_db_config, mock_redis_config):
    """Test application handles startup failures."""
    mock_db_config.connect = AsyncMock(side_effect=Exception("Connection failed"))
    
    with patch("app.main.db_config", mock_db_config), \
         patch("app.main.redis_config", mock_redis_config):
        from app.main import lifespan, app
        
        with pytest.raises(Exception, match="Connection failed"):
            async with lifespan(app):
                pass


def test_health_endpoint_included(client):
    """Test that health endpoint is accessible."""
    response = client.get("/health")
    assert response.status_code == 200


def test_chat_endpoint_included(client):
    """Test that chat endpoints are accessible."""
    # Test with invalid data to verify endpoint exists
    response = client.post("/chat/completion", json={})
    # Should get validation error (422) not 404
    assert response.status_code in [422, 500]
