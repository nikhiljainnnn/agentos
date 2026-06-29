"""
Integration tests for FastAPI endpoints.
Requires running Postgres and Redis.
Run with: pytest tests/integration/ -v
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

# DB setup and client fixtures are provided by conftest.py
# (setup_test_db, client, auth_headers, authenticated_client)


# ─── Auth Tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post("/api/auth/register", json={
        "username": "newuser123",
        "email": "new@test.com",
        "password": "password123",
    })
    assert resp.status_code == 201
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_invalid(client):
    resp = await client.post("/api/auth/login", json={
        "username": "nonexistent",
        "password": "wrong",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_duplicate(client):
    data = {"username": "dupuser", "email": "dup@test.com", "password": "pass1234"}
    await client.post("/api/auth/register", json=data)
    resp = await client.post("/api/auth/register", json=data)
    assert resp.status_code == 400


# ─── Session Tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_session(authenticated_client):
    resp = await authenticated_client.post("/api/sessions/", json={"title": "Test Session"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Session"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_sessions(authenticated_client):
    await authenticated_client.post("/api/sessions/", json={"title": "Session A"})
    await authenticated_client.post("/api/sessions/", json={"title": "Session B"})
    resp = await authenticated_client.get("/api/sessions/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_unauthorized_access(client):
    resp = await client.get("/api/sessions/")
    assert resp.status_code == 403


# ─── Message Tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_message(authenticated_client):
    # Create session
    sess_resp = await authenticated_client.post("/api/sessions/", json={"title": "Message Test"})
    session_id = sess_resp.json()["id"]

    # Mock orchestrator
    mock_state = {
        "final_response": "AI is artificial intelligence.",
        "agent_steps": [],
        "eval_metrics": {"faithfulness": 0.9, "answer_relevancy": 0.9, "context_precision": 0.8, "overall_score": 0.9, "passed": True, "retry_count": 0},
        "provider_used": "anthropic",
        "total_latency_ms": 350.0,
    }

    with patch("gateway.routers.messages.run_orchestrator", new=AsyncMock(return_value=mock_state)):
        resp = await authenticated_client.post("/api/messages/", json={
            "content": "What is AI?",
            "session_id": session_id,
            "enable_rag": False,
            "enable_search": False,
            "enable_code": False,
            "enable_eval": True,
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "AI is artificial intelligence."
    assert data["role"] == "assistant"
    assert data["eval_metrics"]["passed"] is True


# ─── Health Check ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
