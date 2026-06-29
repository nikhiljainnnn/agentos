"""
Unit tests for LLM Router, Critic Agent, RAG Agent, and Orchestrator graph.
All external I/O is mocked — no live services required.
Run: pytest tests/unit/ -v
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.llm_router import LLMRouter, Provider, _GLOBAL_STATS, get_global_stats, get_router
from agents.critic_agent import CriticAgent


# ─── LLM Router ───────────────────────────────────────────────────────────────

class TestLLMRouter:

    def setup_method(self):
        # Reset global stats before each test
        for p in Provider:
            _GLOBAL_STATS[p]["calls"] = 0
            _GLOBAL_STATS[p]["errors"] = 0
            _GLOBAL_STATS[p]["total_latency_ms"] = 0.0

    def test_priority_default_azure_first(self):
        r = LLMRouter(preferred=Provider.AZURE)
        assert r._priority[0] == Provider.AZURE

    def test_priority_anthropic_preferred(self):
        r = LLMRouter(preferred=Provider.ANTHROPIC)
        assert r._priority[0] == Provider.ANTHROPIC
        assert Provider.ANTHROPIC not in r._priority[1:]

    def test_priority_google_preferred(self):
        r = LLMRouter(preferred=Provider.GOOGLE)
        assert r._priority[0] == Provider.GOOGLE
        assert len(r._priority) == 3

    @pytest.mark.asyncio
    async def test_chat_returns_primary_provider_response(self):
        router = LLMRouter(preferred=Provider.AZURE)
        fake_response = ("Hello!", Provider.AZURE, 120.0, 50)
        with patch.object(router, "_call_provider", new=AsyncMock(return_value=fake_response)):
            content, provider, latency, tokens = await router.chat(
                messages=[{"role": "user", "content": "hi"}]
            )
        assert content == "Hello!"
        assert provider == Provider.AZURE

    @pytest.mark.asyncio
    async def test_failover_to_anthropic_when_azure_fails(self):
        router = LLMRouter(preferred=Provider.AZURE)
        call_log = []

        async def fake_call(provider, *args, **kwargs):
            call_log.append(provider)
            if provider == Provider.AZURE:
                raise ConnectionError("Azure timeout")
            return ("Fallback!", provider, 200.0, 30)

        with patch.object(router, "_call_provider", side_effect=fake_call):
            content, provider, _, _ = await router.chat(
                messages=[{"role": "user", "content": "test"}]
            )

        assert call_log[0] == Provider.AZURE
        assert provider == Provider.ANTHROPIC
        assert content == "Fallback!"

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises_runtime_error(self):
        router = LLMRouter()
        with patch.object(router, "_call_provider", new=AsyncMock(side_effect=Exception("down"))):
            with pytest.raises(RuntimeError, match="All providers failed"):
                await router.chat(messages=[{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_global_stats_accumulate_across_instances(self):
        """Key fix test: two different router instances should both write to _GLOBAL_STATS."""
        router_a = LLMRouter(preferred=Provider.AZURE)
        router_b = LLMRouter(preferred=Provider.ANTHROPIC)

        # Build minimal fake ModelResponse objects so _call_provider can parse them
        def _fake_response(provider_val, content):
            resp = MagicMock()
            resp.choices = [MagicMock()]
            resp.choices[0].message.content = content
            resp.usage.total_tokens = 20
            return resp

        # Patch litellm.acompletion so _call_provider runs fully (including _record_stat)
        with patch("agents.llm_router.acompletion", new=AsyncMock(
            return_value=_fake_response(Provider.AZURE, "azure ok")
        )):
            with patch("agents.llm_router.publish_event", new=AsyncMock()):
                await router_a.chat(messages=[{"role": "user", "content": "a"}])

        with patch("agents.llm_router.acompletion", new=AsyncMock(
            return_value=_fake_response(Provider.ANTHROPIC, "anthropic ok")
        )):
            with patch("agents.llm_router.publish_event", new=AsyncMock()):
                await router_b.chat(messages=[{"role": "user", "content": "b"}])

        stats = get_global_stats()
        # Both calls recorded globally
        assert stats["azure"]["calls"] == 1
        assert stats["anthropic"]["calls"] == 1

    @pytest.mark.asyncio
    async def test_error_recorded_in_global_stats(self):
        router = LLMRouter(preferred=Provider.AZURE)

        async def fail_azure(provider, *args, **kwargs):
            if provider == Provider.AZURE:
                raise Exception("Azure down")
            return ("ok", provider, 100.0, 10)

        with patch.object(router, "_call_provider", side_effect=fail_azure):
            await router.chat(messages=[{"role": "user", "content": "test"}])

        stats = get_global_stats()
        assert stats["azure"]["errors"] == 1

    def test_get_router_always_creates_correct_priority(self):
        r = get_router("anthropic")
        assert r._priority[0] == Provider.ANTHROPIC

    def test_get_router_default_is_azure(self):
        r = get_router()
        assert r._priority[0] == Provider.AZURE


# ─── Critic Agent ─────────────────────────────────────────────────────────────

class TestCriticAgent:

    def _make_critic(self):
        router = MagicMock()
        return CriticAgent(router)

    def test_parse_clean_json(self):
        agent = self._make_critic()
        result = agent._parse_eval_response(
            '{"faithfulness": 0.9, "answer_relevancy": 0.85, "context_precision": 0.8, "reasoning": "Good"}'
        )
        assert result["faithfulness"] == 0.9
        assert result["answer_relevancy"] == 0.85
        assert result["context_precision"] == 0.8

    def test_parse_json_wrapped_in_markdown_fences(self):
        agent = self._make_critic()
        result = agent._parse_eval_response(
            '```json\n{"faithfulness": 0.7, "answer_relevancy": 0.6, "context_precision": 0.5, "reasoning": "ok"}\n```'
        )
        assert result["faithfulness"] == 0.7

    def test_parse_malformed_json_falls_back_gracefully(self):
        agent = self._make_critic()
        # Should not raise — returns defaults
        result = agent._parse_eval_response("this is not json at all")
        assert "faithfulness" in result
        assert isinstance(result["faithfulness"], float)

    def test_parse_partial_json_extracts_numbers(self):
        agent = self._make_critic()
        result = agent._parse_eval_response(
            'faithfulness: 0.8, answer_relevancy: 0.75, context_precision: 0.7'
        )
        assert result["faithfulness"] == 0.8

    @pytest.mark.asyncio
    async def test_eval_passes_on_high_scores(self):
        agent = self._make_critic()
        mock_resp = (
            '{"faithfulness": 0.95, "answer_relevancy": 0.9, "context_precision": 0.88, "reasoning": "Excellent"}',
            Provider.ANTHROPIC, 80.0, 40,
        )
        with patch("agents.critic_agent.LLMRouter") as MockRouter:
            MockRouter.return_value.chat = AsyncMock(return_value=mock_resp)
            with patch("agents.critic_agent.publish_event", new=AsyncMock()):
                result = await agent.evaluate("What is AI?", "AI is artificial intelligence.", "AI = Artificial Intelligence")
        assert result["passed"] is True
        assert result["overall_score"] > 0.65

    @pytest.mark.asyncio
    async def test_eval_fails_on_low_scores(self):
        agent = self._make_critic()
        mock_resp = (
            '{"faithfulness": 0.1, "answer_relevancy": 0.2, "context_precision": 0.1, "reasoning": "Poor"}',
            Provider.ANTHROPIC, 80.0, 40,
        )
        with patch("agents.critic_agent.LLMRouter") as MockRouter:
            MockRouter.return_value.chat = AsyncMock(return_value=mock_resp)
            with patch("agents.critic_agent.publish_event", new=AsyncMock()):
                result = await agent.evaluate("What is AI?", "The sky is blue.", "AI = Artificial Intelligence")
        assert result["passed"] is False
        assert result["overall_score"] < 0.65

    @pytest.mark.asyncio
    async def test_eval_survives_llm_failure(self):
        """If eval LLM call fails, should pass-through rather than crash."""
        agent = self._make_critic()
        with patch("agents.critic_agent.LLMRouter") as MockRouter:
            MockRouter.return_value.chat = AsyncMock(side_effect=Exception("LLM down"))
            with patch("agents.critic_agent.publish_event", new=AsyncMock()):
                result = await agent.evaluate("query", "response", "context")
        # Should return a neutral pass-through, not raise
        assert "passed" in result
        assert result["passed"] is True  # fail-open on eval errors

    @pytest.mark.asyncio
    async def test_overall_score_weighted_correctly(self):
        """overall = faithfulness*0.4 + relevancy*0.4 + precision*0.2"""
        agent = self._make_critic()
        mock_resp = (
            '{"faithfulness": 1.0, "answer_relevancy": 1.0, "context_precision": 0.0, "reasoning": "test"}',
            Provider.ANTHROPIC, 80.0, 40,
        )
        with patch("agents.critic_agent.LLMRouter") as MockRouter:
            MockRouter.return_value.chat = AsyncMock(return_value=mock_resp)
            with patch("agents.critic_agent.publish_event", new=AsyncMock()):
                result = await agent.evaluate("q", "a", "c")
        # 1.0*0.4 + 1.0*0.4 + 0.0*0.2 = 0.8
        assert abs(result["overall_score"] - 0.8) < 0.01


# ─── Orchestrator Graph ───────────────────────────────────────────────────────

class TestOrchestratorGraph:
    """
    Tests for the LangGraph orchestrator — verifies the corrected fan-in pattern.
    All agent nodes are mocked to isolate graph logic.
    """

    @pytest.mark.asyncio
    async def test_gather_node_runs_all_enabled_agents(self):
        """gather_node should call rag, search, and code when all enabled."""
        from orchestrator.graph import gather_node, OrchestratorState

        state: OrchestratorState = {
            "query": "test query",
            "session_id": "test-session",
            "history": [],
            "enable_rag": True,
            "enable_search": True,
            "enable_code": False,
            "enable_eval": True,
            "preferred_provider": "azure",
            "rag_context": "",
            "search_context": "",
            "code_context": "",
            "synthesized_response": "",
            "agent_steps": [],
            "retry_count": 0,
            "final_response": "",
            "provider_used": "",
            "total_latency_ms": 0,
            "eval_metrics": None,
        }

        mock_rag = MagicMock()
        mock_rag.retrieve = AsyncMock(return_value=([{"content": "ctx", "metadata": {"title": "T"}, "score": 0.9}], 50.0))
        mock_rag.format_context = MagicMock(return_value="## RAG context")

        mock_search = MagicMock()
        mock_search.search = AsyncMock(return_value=([{"title": "Result", "url": "http://x.com", "content": "web result", "score": 0.8}], 80.0))
        mock_search.format_results = MagicMock(return_value="## Search results")

        with patch("orchestrator.graph.get_rag_agent", return_value=mock_rag), \
             patch("orchestrator.graph.get_search_agent", return_value=mock_search):
            result = await gather_node(state)

        assert result["rag_context"] == "## RAG context"
        assert result["search_context"] == "## Search results"
        assert result["code_context"] == ""
        # Should have 2 agent steps (rag + search, no code)
        assert len(result["agent_steps"]) == 2

    @pytest.mark.asyncio
    async def test_gather_node_skips_disabled_agents(self):
        """With all agents disabled, gather returns empty strings and no steps."""
        from orchestrator.graph import gather_node, OrchestratorState

        state: OrchestratorState = {
            "query": "simple question",
            "session_id": "s",
            "history": [],
            "enable_rag": False,
            "enable_search": False,
            "enable_code": False,
            "enable_eval": False,
            "preferred_provider": "azure",
            "rag_context": "",
            "search_context": "",
            "code_context": "",
            "synthesized_response": "",
            "agent_steps": [],
            "retry_count": 0,
            "final_response": "",
            "provider_used": "",
            "total_latency_ms": 0,
            "eval_metrics": None,
        }

        result = await gather_node(state)
        assert result["rag_context"] == ""
        assert result["search_context"] == ""
        assert result["code_context"] == ""
        assert result["agent_steps"] == []

    def test_should_retry_returns_retry_on_low_score(self):
        from orchestrator.graph import should_retry
        state = {
            "eval_metrics": {"passed": False, "overall_score": 0.4},
            "retry_count": 0,
        }
        assert should_retry(state) == "retry"

    def test_should_retry_returns_done_on_pass(self):
        from orchestrator.graph import should_retry
        state = {
            "eval_metrics": {"passed": True, "overall_score": 0.9},
            "retry_count": 0,
        }
        assert should_retry(state) == "done"

    def test_should_retry_returns_done_when_budget_exhausted(self):
        from orchestrator.graph import should_retry, MAX_RETRIES
        state = {
            "eval_metrics": {"passed": False, "overall_score": 0.3},
            "retry_count": MAX_RETRIES,  # at limit
        }
        assert should_retry(state) == "done"

    @pytest.mark.asyncio
    async def test_retry_node_rotates_provider(self):
        from orchestrator.graph import retry_node
        state = {"retry_count": 0, "preferred_provider": "azure"}
        result = await retry_node(state)
        assert result["retry_count"] == 1
        assert result["preferred_provider"] != "azure"
        assert result["synthesized_response"] == ""

    @pytest.mark.asyncio
    async def test_full_orchestrator_run(self):
        """Integration-level test: run the full graph with all nodes mocked."""
        from orchestrator.graph import run_orchestrator

        mock_rag = MagicMock()
        mock_rag.retrieve = AsyncMock(return_value=([], 10.0))
        mock_rag.format_context = MagicMock(return_value="")

        mock_router = MagicMock()
        mock_router.chat = AsyncMock(return_value=("Final answer.", Provider.ANTHROPIC, 300.0, 100))

        mock_eval = {"faithfulness": 0.9, "answer_relevancy": 0.9, "context_precision": 0.85,
                     "overall_score": 0.9, "passed": True, "retry_count": 0,
                     "reasoning": "Good", "latency_ms": 50.0}

        mock_critic = MagicMock()
        mock_critic.evaluate = AsyncMock(return_value=mock_eval)

        with patch("orchestrator.graph.get_rag_agent", return_value=mock_rag), \
             patch("orchestrator.graph.get_search_agent", return_value=MagicMock(
                 search=AsyncMock(return_value=([], 5.0)),
                 format_results=MagicMock(return_value="")
             )), \
             patch("orchestrator.graph.get_router", return_value=mock_router), \
             patch("orchestrator.graph.CriticAgent", return_value=mock_critic), \
             patch("orchestrator.graph.publish_event", new=AsyncMock()):

            result = await run_orchestrator(
                query="What is LangGraph?",
                session_id="test-session",
                enable_rag=True,
                enable_search=False,
                enable_code=False,
                enable_eval=True,
            )

        assert result["final_response"] == "Final answer."
        assert result["eval_metrics"]["passed"] is True
        assert result["total_latency_ms"] > 0
