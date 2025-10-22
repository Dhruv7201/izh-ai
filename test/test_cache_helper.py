"""Tests for cache helper."""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

from app.helpers.cache_helper import CacheHelper


@pytest.fixture
def cache_helper(mock_settings, mock_redis_config, mock_redis_client):
    """Create cache helper instance."""
    mock_redis_config.get_client = MagicMock(return_value=mock_redis_client)
    
    with patch("app.helpers.cache_helper.redis_config", mock_redis_config), \
         patch("app.helpers.cache_helper.settings", mock_settings):
        helper = CacheHelper()
        helper.redis = mock_redis_config
        return helper


@pytest.mark.asyncio
async def test_cache_get_hit(cache_helper, mock_redis_client):
    """Test cache get with existing value."""
    test_value = {"key": "value"}
    mock_redis_client.get = AsyncMock(return_value=json.dumps(test_value))
    
    result = await cache_helper.get("test_key")
    
    assert result == test_value
    mock_redis_client.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_cache_get_miss(cache_helper, mock_redis_client):
    """Test cache get with non-existent key."""
    mock_redis_client.get = AsyncMock(return_value=None)
    
    result = await cache_helper.get("test_key")
    
    assert result is None
    mock_redis_client.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_cache_get_error(cache_helper, mock_redis_client):
    """Test cache get handles errors gracefully."""
    mock_redis_client.get = AsyncMock(side_effect=Exception("Redis error"))
    
    result = await cache_helper.get("test_key")
    
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_success(cache_helper, mock_redis_client):
    """Test cache set with value."""
    test_value = {"key": "value"}
    
    result = await cache_helper.set("test_key", test_value, ttl=600)
    
    assert result is True
    mock_redis_client.setex.assert_called_once_with(
        "test_key",
        600,
        json.dumps(test_value)
    )


@pytest.mark.asyncio
async def test_cache_set_default_ttl(cache_helper, mock_redis_client):
    """Test cache set uses default TTL."""
    test_value = {"key": "value"}
    
    result = await cache_helper.set("test_key", test_value)
    
    assert result is True
    # Should use default TTL from settings
    call_args = mock_redis_client.setex.call_args
    assert call_args[0][1] == cache_helper.default_ttl


@pytest.mark.asyncio
async def test_cache_set_error(cache_helper, mock_redis_client):
    """Test cache set handles errors gracefully."""
    mock_redis_client.setex = AsyncMock(side_effect=Exception("Redis error"))
    
    result = await cache_helper.set("test_key", {"key": "value"})
    
    assert result is False


@pytest.mark.asyncio
async def test_cache_delete_success(cache_helper, mock_redis_client):
    """Test cache delete."""
    mock_redis_client.delete = AsyncMock(return_value=1)
    
    result = await cache_helper.delete("test_key")
    
    assert result is True
    mock_redis_client.delete.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_cache_delete_error(cache_helper, mock_redis_client):
    """Test cache delete handles errors gracefully."""
    mock_redis_client.delete = AsyncMock(side_effect=Exception("Redis error"))
    
    result = await cache_helper.delete("test_key")
    
    assert result is False


@pytest.mark.asyncio
async def test_cache_exists_true(cache_helper, mock_redis_client):
    """Test cache exists check when key exists."""
    mock_redis_client.exists = AsyncMock(return_value=1)
    
    result = await cache_helper.exists("test_key")
    
    assert result is True
    mock_redis_client.exists.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_cache_exists_false(cache_helper, mock_redis_client):
    """Test cache exists check when key doesn't exist."""
    mock_redis_client.exists = AsyncMock(return_value=0)
    
    result = await cache_helper.exists("test_key")
    
    assert result is False


@pytest.mark.asyncio
async def test_cache_disabled(mock_settings, mock_redis_config):
    """Test cache operations when cache is disabled."""
    mock_settings.CACHE_ENABLED = False
    
    with patch("app.helpers.cache_helper.redis_config", mock_redis_config), \
         patch("app.helpers.cache_helper.settings", mock_settings):
        helper = CacheHelper()
        
        # All operations should return None/False when disabled
        assert await helper.get("key") is None
        assert await helper.set("key", "value") is False
        assert await helper.delete("key") is False


@pytest.mark.asyncio
async def test_cache_key_generation(cache_helper):
    """Test cache key generation."""
    key = cache_helper.cache_key("arg1", "arg2", kwarg1="val1")
    
    assert isinstance(key, str)
    assert len(key) > 0
    
    # Same inputs should generate same key
    key2 = cache_helper.cache_key("arg1", "arg2", kwarg1="val1")
    assert key == key2
    
    # Different inputs should generate different keys
    key3 = cache_helper.cache_key("arg1", "arg3", kwarg1="val1")
    assert key != key3


@pytest.mark.asyncio
async def test_cache_decorator(mock_redis_client, mock_settings, mock_redis_config):
    """Test cache decorator functionality."""
    mock_redis_config.get_client = MagicMock(return_value=mock_redis_client)
    mock_redis_client.get = AsyncMock(return_value=None)
    mock_redis_client.setex = AsyncMock(return_value=True)
    
    with patch("app.helpers.cache_helper.redis_config", mock_redis_config), \
         patch("app.helpers.cache_helper.settings", mock_settings):
        from app.helpers.cache_helper import cached
        
        call_count = 0
        
        @cached(ttl=300, key_prefix="test")
        async def test_function(arg1, arg2):
            nonlocal call_count
            call_count += 1
            return f"{arg1}-{arg2}"
        
        # First call - should execute function
        result1 = await test_function("a", "b")
        assert result1 == "a-b"
        assert call_count == 1
        
        # Mock cache hit for second call
        mock_redis_client.get = AsyncMock(return_value=json.dumps("a-b"))
        
        # Second call - should use cache
        result2 = await test_function("a", "b")
        assert result2 == "a-b"
        # Function should not be called again (count stays at 1)
        assert call_count == 1
