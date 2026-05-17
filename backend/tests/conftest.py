import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_config():
    from mether.config import Settings
    return Settings(
        llm_proxy_url="http://localhost:8082",
        llm_model="test/model",
        anthropic_auth_token="test",
        mether_port=8000,
        google_credentials_path="/tmp/fake",
        google_token_path="/tmp/fake_token"
    )

@pytest.fixture
def mock_agent():
    agent = AsyncMock()
    agent.process = AsyncMock(return_value="METHER test response")
    return agent

@pytest.fixture
def client():
    from mether.main import app
    with TestClient(app) as test_client:
        yield test_client
