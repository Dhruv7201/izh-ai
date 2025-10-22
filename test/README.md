# Test Suite

This directory contains the test suite for the AI Backend API project.

## Structure

- `conftest.py` - Shared pytest fixtures and configuration
- `test_main.py` - Tests for main application and lifecycle
- `test_health.py` - Tests for health check endpoints
- `test_chat.py` - Tests for chat endpoints
- `test_openai_helper.py` - Tests for OpenAI helper
- `test_cache_helper.py` - Tests for cache helper
- `test_settings.py` - Tests for settings configuration

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=app --cov-report=html
```

### Run specific test file
```bash
pytest test/test_health.py
```

### Run specific test
```bash
pytest test/test_health.py::test_basic_health_check
```

### Run tests matching a pattern
```bash
pytest -k "health"
```

### Run with verbose output
```bash
pytest -v
```

### Run only fast tests (exclude slow tests)
```bash
pytest -m "not slow"
```

## Test Coverage

To view the coverage report after running tests with coverage:
```bash
# Terminal report
pytest --cov=app --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Writing Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

### Using Fixtures
Common fixtures are available in `conftest.py`:
- `client` - FastAPI test client
- `async_client` - Async test client
- `mock_db_config` - Mocked database configuration
- `mock_redis_config` - Mocked Redis configuration
- `mock_openai_client` - Mocked OpenAI client

### Example Test
```python
def test_my_feature(client, mock_openai_client):
    """Test description."""
    with patch("app.helpers.openai_helper.openai_helper.client", mock_openai_client):
        response = client.post("/my-endpoint", json={"data": "test"})
        assert response.status_code == 200
```

## Mocking External Services

Tests use mocks for external services:
- **OpenAI API**: Mocked to avoid API calls and costs
- **PostgreSQL**: Mocked database connections
- **Redis**: Mocked cache operations

## Continuous Integration

Tests are designed to run in CI/CD pipelines without requiring external services.

## Dependencies

Test dependencies are managed in `pyproject.toml`:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `httpx` - Async HTTP client for testing
