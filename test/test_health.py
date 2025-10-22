"""Tests for health check routes."""
import pytest
from unittest.mock import patch, AsyncMock


def test_basic_health_check(client):
    """Test basic health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_database_health_check_healthy(client, mock_db_config):
    """Test database health check when healthy."""
    mock_db_config.health_check = AsyncMock(return_value=True)
    
    with patch("app.routes.health.db_config", mock_db_config):
        response = client.get("/health/db")
        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "healthy"
        assert data["status"] is True


def test_database_health_check_unhealthy(client, mock_db_config):
    """Test database health check when unhealthy."""
    mock_db_config.health_check = AsyncMock(return_value=False)
    
    with patch("app.routes.health.db_config", mock_db_config):
        response = client.get("/health/db")
        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "unhealthy"
        assert data["status"] is False


def test_cache_health_check_healthy(client, mock_redis_config):
    """Test cache health check when healthy."""
    mock_redis_config.health_check = AsyncMock(return_value=True)
    
    with patch("app.routes.health.redis_config", mock_redis_config):
        response = client.get("/health/cache")
        assert response.status_code == 200
        data = response.json()
        assert data["cache"] == "healthy"
        assert data["status"] is True


def test_cache_health_check_unhealthy(client, mock_redis_config):
    """Test cache health check when unhealthy."""
    mock_redis_config.health_check = AsyncMock(return_value=False)
    
    with patch("app.routes.health.redis_config", mock_redis_config):
        response = client.get("/health/cache")
        assert response.status_code == 200
        data = response.json()
        assert data["cache"] == "unhealthy"
        assert data["status"] is False


def test_full_health_check_all_healthy(client, mock_db_config, mock_redis_config):
    """Test full health check when all services are healthy."""
    mock_db_config.health_check = AsyncMock(return_value=True)
    mock_redis_config.health_check = AsyncMock(return_value=True)
    
    with patch("app.routes.health.db_config", mock_db_config), \
         patch("app.routes.health.redis_config", mock_redis_config):
        response = client.get("/health/all")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["services"]["database"] is True
        assert data["services"]["cache"] is True


def test_full_health_check_degraded(client, mock_db_config, mock_redis_config):
    """Test full health check when some services are unhealthy."""
    mock_db_config.health_check = AsyncMock(return_value=True)
    mock_redis_config.health_check = AsyncMock(return_value=False)
    
    with patch("app.routes.health.db_config", mock_db_config), \
         patch("app.routes.health.redis_config", mock_redis_config):
        response = client.get("/health/all")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["database"] is True
        assert data["services"]["cache"] is False


def test_full_health_check_all_unhealthy(client, mock_db_config, mock_redis_config):
    """Test full health check when all services are unhealthy."""
    mock_db_config.health_check = AsyncMock(return_value=False)
    mock_redis_config.health_check = AsyncMock(return_value=False)
    
    with patch("app.routes.health.db_config", mock_db_config), \
         patch("app.routes.health.redis_config", mock_redis_config):
        response = client.get("/health/all")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["database"] is False
        assert data["services"]["cache"] is False
