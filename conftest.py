"""
Shared pytest fixtures for all test suites.
"""
import os
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

# ─── Set test environment before importing app ─────────────────────────────────
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://agentos:secret@localhost:5432/agentos_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-chars-ok")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("TAVILY_API_KEY", "test-key")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from gateway.main import app
from gateway.database import get_db
from gateway.models import Base


# ─── Database engine for tests ────────────────────────────────────────────────
TEST_DB_URL = os.environ["DATABASE_URL"]

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create all tables at test session start; drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fresh session per test, rolled back after."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Test HTTP client with DB override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register + login, return auth headers."""
    await client.post("/api/auth/register", json={
        "username": "fixtureuser",
        "email": "fixture@test.com",
        "password": "fixture123",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "fixtureuser",
        "password": "fixture123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, auth_headers: dict) -> AsyncClient:
    """Client with auth headers pre-set."""
    client.headers.update(auth_headers)
    return client


# ─── Mocks for external services ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_kafka():
    """Auto-mock Kafka for all tests — no real broker needed."""
    with patch("gateway.observability.kafka_producer.publish_event", new=AsyncMock(return_value=True)):
        yield


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator response for message endpoint tests."""
    return {
        "final_response": "Mocked AI response.",
        "agent_steps": [
            {"agent": "supervisor", "input": "test", "output": "routing", "latency_ms": 10.0, "tokens_used": 0, "provider": None},
            {"agent": "synthesizer", "input": "test", "output": "Mocked AI response.", "latency_ms": 300.0, "tokens_used": 150, "provider": "anthropic"},
        ],
        "eval_metrics": {
            "faithfulness": 0.9,
            "answer_relevancy": 0.85,
            "context_precision": 0.8,
            "overall_score": 0.87,
            "passed": True,
            "retry_count": 0,
            "reasoning": "High quality response",
            "latency_ms": 120.0,
        },
        "provider_used": "anthropic",
        "total_latency_ms": 430.0,
        "retry_count": 0,
    }
