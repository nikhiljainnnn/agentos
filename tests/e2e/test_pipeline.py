"""
E2E tests for the complete agent pipeline flow.
Tests the full orchestrator → agents → response chain with mocked LLMs.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient


class TestFullPipeline:
    """Test the complete message → orchestrator → response flow."""

    @pytest.mark.asyncio
    async def test_message_with_rag_enabled(
        self, authenticated_client: AsyncClient, mock_orchestrator: dict
    ):
        # Create session
        sess = await authenticated_client.post("/api/sessions/", json={"title": "E2E RAG Test"})
        assert sess.status_code == 201
        session_id = sess.json()["id"]

        with patch("gateway.routers.messages.run_orchestrator", new=AsyncMock(return_value=mock_orchestrator)):
            resp = await authenticated_client.post("/api/messages/", json={
                "content": "What is machine learning?",
                "session_id": session_id,
                "enable_rag": True,
                "enable_search": False,
                "enable_code": False,
                "enable_eval": True,
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "assistant"
        assert len(data["content"]) > 0
        assert data["eval_metrics"]["passed"] is True
        assert data["provider_used"] == "anthropic"
        assert data["total_latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_message_history_preserved(
        self, authenticated_client: AsyncClient, mock_orchestrator: dict
    ):
        sess = await authenticated_client.post("/api/sessions/", json={"title": "History Test"})
        session_id = sess.json()["id"]

        with patch("gateway.routers.messages.run_orchestrator", new=AsyncMock(return_value=mock_orchestrator)):
            await authenticated_client.post("/api/messages/", json={
                "content": "First message",
                "session_id": session_id,
                "enable_rag": False,
                "enable_eval": False,
            })
            await authenticated_client.post("/api/messages/", json={
                "content": "Second message",
                "session_id": session_id,
                "enable_rag": False,
                "enable_eval": False,
            })

        msgs = await authenticated_client.get(f"/api/messages/{session_id}")
        assert msgs.status_code == 200
        # user + assistant for each = 4 messages
        assert len(msgs.json()) == 4

    @pytest.mark.asyncio
    async def test_eval_retry_on_failure(
        self, authenticated_client: AsyncClient
    ):
        """Verify that when eval fails, retry_count is reflected in response."""
        sess = await authenticated_client.post("/api/sessions/", json={"title": "Retry Test"})
        session_id = sess.json()["id"]

        failed_then_pass = {
            "final_response": "Retried and improved response.",
            "agent_steps": [],
            "eval_metrics": {
                "faithfulness": 0.75, "answer_relevancy": 0.8,
                "context_precision": 0.7, "overall_score": 0.76,
                "passed": True, "retry_count": 1,
                "reasoning": "Improved after retry", "latency_ms": 100.0,
            },
            "provider_used": "anthropic",
            "total_latency_ms": 800.0,
            "retry_count": 1,
        }

        with patch("gateway.routers.messages.run_orchestrator", new=AsyncMock(return_value=failed_then_pass)):
            resp = await authenticated_client.post("/api/messages/", json={
                "content": "Complex question needing retry",
                "session_id": session_id,
                "enable_rag": False,
                "enable_eval": True,
            })

        assert resp.status_code == 200
        assert resp.json()["eval_metrics"]["retry_count"] == 1
        assert resp.json()["eval_metrics"]["passed"] is True

    @pytest.mark.asyncio
    async def test_document_ingest_and_retrieval(
        self, authenticated_client: AsyncClient
    ):
        """Test document ingestion returns correct metadata."""
        mock_rag = MagicMock()
        mock_rag.ingest = AsyncMock(return_value={
            "title": "Test Doc",
            "chunk_count": 5,
            "namespace": "test",
        })

        with patch("gateway.routers.documents.get_rag_agent", return_value=mock_rag):
            resp = await authenticated_client.post("/api/documents/", json={
                "title": "Test Document",
                "content": "This is test content " * 100,
                "namespace": "test",
                "metadata": {"source": "unit-test"},
            })

        assert resp.status_code == 201
        data = resp.json()
        assert data["chunk_count"] == 5
        assert data["namespace"] == "test"

    @pytest.mark.asyncio
    async def test_session_isolation(self, authenticated_client: AsyncClient, mock_orchestrator: dict):
        """Messages from one session should not appear in another."""
        s1 = (await authenticated_client.post("/api/sessions/", json={"title": "S1"})).json()["id"]
        s2 = (await authenticated_client.post("/api/sessions/", json={"title": "S2"})).json()["id"]

        with patch("gateway.routers.messages.run_orchestrator", new=AsyncMock(return_value=mock_orchestrator)):
            await authenticated_client.post("/api/messages/", json={
                "content": "Session 1 message",
                "session_id": s1,
                "enable_rag": False,
                "enable_eval": False,
            })

        s1_msgs = (await authenticated_client.get(f"/api/messages/{s1}")).json()
        s2_msgs = (await authenticated_client.get(f"/api/messages/{s2}")).json()

        assert len(s1_msgs) == 2  # user + assistant
        assert len(s2_msgs) == 0  # empty

    @pytest.mark.asyncio
    async def test_unauthorized_session_access(self, client: AsyncClient):
        """Accessing sessions without auth should fail."""
        resp = await client.get("/api/messages/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/metrics/")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_queries_today" in data
        assert "eval_pass_rate" in data
        assert "provider_distribution" in data

    @pytest.mark.asyncio
    async def test_provider_stats_endpoint(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/metrics/providers")
        assert resp.status_code == 200
        data = resp.json()
        # Should have entries for all 3 providers
        for provider in ["azure", "anthropic", "google"]:
            assert provider in data
