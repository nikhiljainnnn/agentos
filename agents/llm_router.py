"""
LiteLLM-backed provider-agnostic LLM router.
Priority: Azure OpenAI → Anthropic Claude → Google Gemini

FIX: Previously, get_router(preferred=X) created a new LLMRouter instance,
     losing all accumulated stats. Per-request routers with different preferred
     providers all tracked stats in isolation.

SOLUTION: Stats live in a module-level _GLOBAL_STATS dict, shared across ALL
router instances. Each instance writes to the same counters, so the /metrics
endpoint always sees the full picture regardless of which router handled each call.
"""

import time
import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional
from enum import Enum

import structlog
from litellm import acompletion, ModelResponse

from gateway.config import get_settings
from gateway.observability.kafka_producer import publish_event

logger = structlog.get_logger(__name__)
settings = get_settings()


class Provider(str, Enum):
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


PROVIDER_MODELS = {
    Provider.AZURE: f"azure/{settings.azure_openai_deployment_name}",
    Provider.ANTHROPIC: "claude-sonnet-4-6",
    Provider.GOOGLE: "gemini/gemini-1.5-pro",
}

PROVIDER_CONFIG = {
    Provider.AZURE: {
        "api_key": settings.azure_openai_api_key,
        "api_base": settings.azure_openai_endpoint,
        "api_version": settings.azure_openai_api_version,
    },
    Provider.ANTHROPIC: {
        "api_key": settings.anthropic_api_key,
    },
    Provider.GOOGLE: {
        "api_key": settings.google_api_key,
    },
}

# ─── Global stats (shared across all LLMRouter instances) ────────────────────
# This dict lives at module scope so every router instance increments the same
# counters — solving the stat-loss bug when preferred= creates a new instance.
_GLOBAL_STATS: Dict[Provider, Dict] = {
    p: {"calls": 0, "errors": 0, "total_latency_ms": 0.0}
    for p in Provider
}


def _record_stat(provider: Provider, latency_ms: float, tokens: int, error: bool = False):
    """Thread-safe stat update (GIL protects dict increments in CPython)."""
    s = _GLOBAL_STATS[provider]
    if error:
        s["errors"] += 1
    else:
        s["calls"] += 1
        s["total_latency_ms"] += latency_ms


def get_global_stats() -> Dict:
    """Return a snapshot of global provider stats for the metrics endpoint."""
    return {
        p.value: {
            **s,
            "avg_latency_ms": round(
                s["total_latency_ms"] / s["calls"] if s["calls"] > 0 else 0.0, 1
            ),
            "error_rate": round(
                s["errors"] / (s["calls"] + s["errors"]) if (s["calls"] + s["errors"]) > 0 else 0.0,
                3,
            ),
        }
        for p, s in _GLOBAL_STATS.items()
    }


# ─── Router ───────────────────────────────────────────────────────────────────

class LLMRouter:
    """
    Failover-capable LLM router. Can be instantiated per-request with a
    different preferred provider — stats always accumulate in _GLOBAL_STATS.
    """

    def __init__(self, preferred: Provider = Provider.AZURE):
        self._priority: List[Provider] = self._build_priority(preferred)

    def _build_priority(self, preferred: Provider) -> List[Provider]:
        order = [Provider.AZURE, Provider.ANTHROPIC, Provider.GOOGLE]
        order.remove(preferred)
        return [preferred] + order

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> tuple[str, Provider, float, int]:
        """Returns: (response_text, provider_used, latency_ms, tokens_used)"""
        last_error = None
        for provider in self._priority:
            try:
                return await self._call_provider(provider, messages, temperature, max_tokens)
            except Exception as e:
                last_error = e
                logger.warning("provider_failed", provider=provider.value, error=str(e))
                _record_stat(provider, 0, 0, error=True)

        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[tuple[str, Provider]]:
        """Async generator yielding (token, provider) tuples."""
        for provider in self._priority:
            try:
                model = PROVIDER_MODELS[provider]
                cfg = PROVIDER_CONFIG[provider]
                t0 = time.monotonic()

                response = await acompletion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    **cfg,
                )

                async for chunk in response:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content, provider

                _record_stat(provider, (time.monotonic() - t0) * 1000, 0)
                return

            except Exception as e:
                logger.warning("stream_provider_failed", provider=provider.value, error=str(e))
                _record_stat(provider, 0, 0, error=True)

        raise RuntimeError("All providers failed during streaming")

    async def _call_provider(
        self,
        provider: Provider,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, Provider, float, int]:
        model = PROVIDER_MODELS[provider]
        cfg = PROVIDER_CONFIG[provider]
        t0 = time.monotonic()

        response: ModelResponse = await acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **cfg,
        )

        latency_ms = (time.monotonic() - t0) * 1000
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0

        _record_stat(provider, latency_ms, tokens)

        await publish_event("agent-events", {
            "event": "llm_call",
            "provider": provider.value,
            "latency_ms": latency_ms,
            "tokens": tokens,
        })

        logger.info(
            "llm_call_success",
            provider=provider.value,
            latency_ms=round(latency_ms, 1),
            tokens=tokens,
        )
        return content, provider, latency_ms, tokens

    # Instance-level get_stats now delegates to global for consistency
    def get_stats(self) -> Dict:
        return get_global_stats()


# ─── Factory ──────────────────────────────────────────────────────────────────
# No cached singleton — always create with the correct preferred provider.
# Stats survive because they're in _GLOBAL_STATS, not in the instance.

def get_router(preferred: Optional[str] = None) -> LLMRouter:
    return LLMRouter(preferred=Provider(preferred) if preferred else Provider.AZURE)
