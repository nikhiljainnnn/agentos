"""
LangGraph Supervisor Orchestrator.

FIX: The fan-in bug — original code had parallel edges:
  rag → synthesizer
  search → synthesizer   ← LangGraph can't merge these; last write wins
  code → synthesizer

CORRECT APPROACH: supervisor runs first, then a single "gather" node runs
rag/search/code sequentially (or via asyncio.gather) and merges results,
then passes merged state to synthesizer. This is the idiomatic LangGraph
pattern for fan-in without requiring the experimental Send() API.

State flow:
  START → supervisor → gather → synthesizer → critic
                ↑_____________retry___________|
"""

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional, TypedDict

import structlog
from langgraph.graph import END, START, StateGraph

from agents.llm_router import LLMRouter, Provider, get_router
from agents.rag_agent import get_rag_agent
from agents.search_agent import get_search_agent
from agents.code_agent import get_code_agent
from agents.critic_agent import CriticAgent, EVAL_THRESHOLD, MAX_RETRIES
from gateway.observability.kafka_producer import publish_event

logger = structlog.get_logger(__name__)


# ─── State Schema ─────────────────────────────────────────────────────────────

class AgentStep(TypedDict):
    agent: str
    input: str
    output: str
    latency_ms: float
    tokens_used: int
    provider: Optional[str]


class OrchestratorState(TypedDict):
    # Inputs
    query: str
    session_id: str
    history: List[Dict[str, str]]
    enable_rag: bool
    enable_search: bool
    enable_code: bool
    enable_eval: bool
    preferred_provider: str

    # Working state — each agent writes its own key, no fan-in collision
    rag_context: str
    search_context: str
    code_context: str
    synthesized_response: str
    agent_steps: List[AgentStep]
    retry_count: int

    # Outputs
    final_response: str
    provider_used: str
    total_latency_ms: float
    eval_metrics: Optional[Dict[str, Any]]


# ─── Node Functions ────────────────────────────────────────────────────────────

async def supervisor_node(state: OrchestratorState) -> Dict:
    """
    Supervisor: classifies query and decides which agents to activate.
    Merges LLM routing decision with user's explicit enable_* flags.
    """
    t0 = time.monotonic()
    router = get_router(state["preferred_provider"])

    classify_prompt = (
        f"Analyze this query and return JSON only — no markdown, no explanation.\n"
        f'Query: {state["query"]}\n\n'
        f'Return: {{"needs_rag": bool, "needs_search": bool, "needs_code": bool, "reasoning": "str"}}\n'
        f"- needs_rag: query benefits from knowledge base documents\n"
        f"- needs_search: query needs current/real-time web data\n"
        f"- needs_code: query requires executing/testing code"
    )

    try:
        response_text, _, _, _ = await router.chat(
            messages=[{"role": "user", "content": classify_prompt}],
            temperature=0.1,
            max_tokens=256,
        )
        clean = re.sub(r"```(?:json)?", "", response_text).strip()
        routing = json.loads(clean)
    except Exception as e:
        logger.warning("supervisor_classify_failed", error=str(e))
        routing = {"needs_rag": True, "needs_search": False, "needs_code": False}

    latency = (time.monotonic() - t0) * 1000
    step: AgentStep = {
        "agent": "supervisor",
        "input": state["query"],
        "output": str(routing),
        "latency_ms": latency,
        "tokens_used": 0,
        "provider": None,
    }

    return {
        # User flags take precedence; supervisor can add but not remove
        "enable_rag": state["enable_rag"] and routing.get("needs_rag", True),
        "enable_search": state["enable_search"] or routing.get("needs_search", False),
        "enable_code": state["enable_code"] or routing.get("needs_code", False),
        "agent_steps": state.get("agent_steps", []) + [step],
    }


async def gather_node(state: OrchestratorState) -> Dict:
    """
    FAN-OUT + FAN-IN node.

    Runs rag, search, and code agents concurrently via asyncio.gather,
    then merges all results into state before synthesizer runs.

    This replaces the broken pattern of three separate nodes each having
    their own edge to synthesizer (last-write-wins race condition).
    """
    t0 = time.monotonic()

    async def run_rag() -> tuple[str, Optional[AgentStep]]:
        if not state.get("enable_rag"):
            return "", None
        rag = get_rag_agent()
        contexts, latency = await rag.retrieve(state["query"])
        formatted = rag.format_context(contexts)
        step: AgentStep = {
            "agent": "rag",
            "input": state["query"],
            "output": f"Retrieved {len(contexts)} chunks",
            "latency_ms": latency,
            "tokens_used": 0,
            "provider": None,
        }
        return formatted, step

    async def run_search() -> tuple[str, Optional[AgentStep]]:
        if not state.get("enable_search"):
            return "", None
        search = get_search_agent()
        results, latency = await search.search(state["query"])
        formatted = search.format_results(results)
        step: AgentStep = {
            "agent": "search",
            "input": state["query"],
            "output": f"Found {len(results)} web results",
            "latency_ms": latency,
            "tokens_used": 0,
            "provider": None,
        }
        return formatted, step

    async def run_code() -> tuple[str, Optional[AgentStep]]:
        if not state.get("enable_code"):
            return "", None
        code_match = re.search(r"```(?:python)?\n(.*?)```", state["query"], re.DOTALL)
        if not code_match:
            return "No executable code block found in query.", None
        code = code_match.group(1)
        code_agent = get_code_agent()
        result = await code_agent.execute(code)
        formatted = code_agent.format_result(result)
        step: AgentStep = {
            "agent": "code",
            "input": code[:100],
            "output": (result["stdout"] or result["stderr"])[:200],
            "latency_ms": result["latency_ms"],
            "tokens_used": 0,
            "provider": None,
        }
        return formatted, step

    # All three run concurrently — true parallel fan-out
    (rag_ctx, rag_step), (search_ctx, search_step), (code_ctx, code_step) = (
        await asyncio.gather(run_rag(), run_search(), run_code())
    )

    new_steps = [s for s in [rag_step, search_step, code_step] if s is not None]

    logger.info(
        "gather_complete",
        rag=bool(rag_ctx),
        search=bool(search_ctx),
        code=bool(code_ctx),
        latency_ms=round((time.monotonic() - t0) * 1000, 1),
    )

    return {
        "rag_context": rag_ctx,
        "search_context": search_ctx,
        "code_context": code_ctx,
        "agent_steps": state.get("agent_steps", []) + new_steps,
    }


async def synthesizer_node(state: OrchestratorState) -> Dict:
    """
    Synthesizer: merges all gathered context and generates the response.
    This node always runs after gather — state is fully populated.
    """
    t0 = time.monotonic()
    router = get_router(state["preferred_provider"])

    context_parts = [
        ctx for ctx in [
            state.get("rag_context", ""),
            state.get("search_context", ""),
            state.get("code_context", ""),
        ] if ctx
    ]
    context_block = "\n\n".join(context_parts)

    system = (
        "You are AgentOS, an expert AI assistant. "
        "Use the provided context to give accurate, well-structured answers. "
        "If context is provided, ground your answer in it and do not hallucinate. "
        "Be concise but complete."
    )

    user_content = (
        f"{context_block}\n\n## Query\n{state['query']}"
        if context_block
        else state["query"]
    )

    full_messages = (
        [{"role": "system", "content": system}]
        + state.get("history", [])
        + [{"role": "user", "content": user_content}]
    )

    response_text, provider, latency_ms, tokens = await router.chat(
        messages=full_messages,
        temperature=0.7,
        max_tokens=2048,
    )

    step: AgentStep = {
        "agent": "synthesizer",
        "input": state["query"],
        "output": response_text[:200],
        "latency_ms": latency_ms,
        "tokens_used": tokens,
        "provider": provider.value,
    }

    await publish_event("agent-events", {
        "event": "synthesizer_complete",
        "session_id": state["session_id"],
        "provider": provider.value,
        "latency_ms": latency_ms,
        "tokens": tokens,
    })

    return {
        "synthesized_response": response_text,
        "provider_used": provider.value,
        "agent_steps": state.get("agent_steps", []) + [step],
    }


async def critic_node(state: OrchestratorState) -> Dict:
    """
    Critic: evaluates the synthesized response using RAGAS-style metrics.
    If score < threshold AND retries remain, the conditional edge triggers retry.
    """
    if not state.get("enable_eval"):
        return {
            "final_response": state["synthesized_response"],
            "eval_metrics": None,
        }

    router = get_router(state["preferred_provider"])
    critic = CriticAgent(router)

    combined_context = " ".join(filter(None, [
        state.get("rag_context", ""),
        state.get("search_context", ""),
    ]))

    metrics = await critic.evaluate(
        query=state["query"],
        response=state["synthesized_response"],
        context=combined_context,
        retry_count=state.get("retry_count", 0),
    )

    return {
        "eval_metrics": metrics,
        "final_response": state["synthesized_response"],
    }


def should_retry(state: OrchestratorState) -> str:
    """Conditional edge: retry if eval failed and budget remains."""
    metrics = state.get("eval_metrics")
    retry_count = state.get("retry_count", 0)

    if metrics and not metrics["passed"] and retry_count < MAX_RETRIES:
        logger.info(
            "eval_retry_triggered",
            score=metrics["overall_score"],
            retry_count=retry_count + 1,
        )
        return "retry"
    return "done"


async def retry_node(state: OrchestratorState) -> Dict:
    """Bump retry counter and rotate to next provider for re-synthesis."""
    retry_count = state.get("retry_count", 0) + 1
    providers = [Provider.AZURE, Provider.ANTHROPIC, Provider.GOOGLE]
    next_provider = providers[retry_count % len(providers)].value

    logger.info("retry_provider_rotation", next_provider=next_provider, retry_count=retry_count)

    return {
        "retry_count": retry_count,
        "preferred_provider": next_provider,
        "synthesized_response": "",
    }


# ─── Graph Assembly ────────────────────────────────────────────────────────────

def build_orchestrator() -> StateGraph:
    g = StateGraph(OrchestratorState)

    g.add_node("supervisor", supervisor_node)
    g.add_node("gather", gather_node)       # ← replaces rag/search/code nodes
    g.add_node("synthesizer", synthesizer_node)
    g.add_node("critic", critic_node)
    g.add_node("retry", retry_node)

    # Linear flow — no fan-in ambiguity
    g.add_edge(START, "supervisor")
    g.add_edge("supervisor", "gather")      # supervisor decides flags
    g.add_edge("gather", "synthesizer")     # gather merges all contexts
    g.add_edge("synthesizer", "critic")     # critic evaluates

    # Retry loop: critic → retry → synthesizer (skip gather on retry)
    g.add_conditional_edges(
        "critic",
        should_retry,
        {"retry": "retry", "done": END},
    )
    g.add_edge("retry", "synthesizer")

    return g.compile()


_graph = None


def get_orchestrator():
    global _graph
    if _graph is None:
        _graph = build_orchestrator()
    return _graph


async def run_orchestrator(
    query: str,
    session_id: str,
    history: List[Dict[str, str]] = [],
    enable_rag: bool = True,
    enable_search: bool = False,
    enable_code: bool = False,
    enable_eval: bool = True,
    preferred_provider: str = "azure",
) -> OrchestratorState:
    graph = get_orchestrator()
    t0 = time.monotonic()

    initial_state: OrchestratorState = {
        "query": query,
        "session_id": session_id,
        "history": history,
        "enable_rag": enable_rag,
        "enable_search": enable_search,
        "enable_code": enable_code,
        "enable_eval": enable_eval,
        "preferred_provider": preferred_provider,
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

    final_state = await graph.ainvoke(initial_state)
    final_state["total_latency_ms"] = (time.monotonic() - t0) * 1000

    logger.info(
        "orchestrator_complete",
        session_id=session_id,
        latency_ms=round(final_state["total_latency_ms"], 1),
        provider=final_state.get("provider_used"),
        retries=final_state.get("retry_count", 0),
        eval_passed=(
            final_state["eval_metrics"]["passed"]
            if final_state.get("eval_metrics") else None
        ),
    )

    return final_state
