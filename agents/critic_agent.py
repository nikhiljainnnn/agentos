"""
Critic Agent: Evaluates responses using RAGAS-style metrics.
If score < threshold, triggers re-routing to a different provider.
This is the KEY differentiator — eval-in-the-loop architecture.
"""

import re
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import structlog

from agents.llm_router import LLMRouter, Provider
from gateway.observability.kafka_producer import publish_event

logger = structlog.get_logger(__name__)

EVAL_THRESHOLD = 0.65
MAX_RETRIES = 2


EVAL_PROMPT = """You are a rigorous AI response evaluator. Score the following response across 3 dimensions.

## Query
{query}

## Retrieved Context (if any)
{context}

## Response to Evaluate
{response}

Score each metric from 0.0 to 1.0:

1. **Faithfulness** (0-1): Is the response factually grounded in the provided context? Does it avoid hallucination?
2. **Answer Relevancy** (0-1): Does the response directly and completely address the query?
3. **Context Precision** (0-1): Did the response efficiently use the context without including irrelevant information?

Respond ONLY with valid JSON, no markdown:
{{"faithfulness": 0.0, "answer_relevancy": 0.0, "context_precision": 0.0, "reasoning": "brief explanation"}}"""


class CriticAgent:
    def __init__(self, router: LLMRouter):
        self.router = router

    async def evaluate(
        self,
        query: str,
        response: str,
        context: str = "",
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Evaluate a response. Returns metrics dict with pass/fail.
        Uses a separate, more capable provider for evaluation.
        """
        t0 = time.monotonic()

        prompt = EVAL_PROMPT.format(
            query=query,
            context=context or "No context retrieved",
            response=response,
        )

        try:
            # Always use the best available provider for eval
            eval_router = LLMRouter(preferred=Provider.ANTHROPIC)
            eval_text, provider, _, _ = await eval_router.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # deterministic eval
                max_tokens=512,
            )

            # Parse JSON response
            metrics = self._parse_eval_response(eval_text)
            overall = (
                metrics["faithfulness"] * 0.4
                + metrics["answer_relevancy"] * 0.4
                + metrics["context_precision"] * 0.2
            )

            result = {
                "faithfulness": round(metrics["faithfulness"], 3),
                "answer_relevancy": round(metrics["answer_relevancy"], 3),
                "context_precision": round(metrics["context_precision"], 3),
                "overall_score": round(overall, 3),
                "passed": overall >= EVAL_THRESHOLD,
                "retry_count": retry_count,
                "reasoning": metrics.get("reasoning", ""),
                "latency_ms": (time.monotonic() - t0) * 1000,
            }

            await publish_event("eval-results", {
                "query": query[:100],
                "overall_score": result["overall_score"],
                "passed": result["passed"],
                "retry_count": retry_count,
            })

            logger.info(
                "eval_complete",
                score=result["overall_score"],
                passed=result["passed"],
                retry_count=retry_count,
            )
            return result

        except Exception as e:
            logger.error("eval_failed", error=str(e))
            # On eval failure, pass through (don't block the user)
            return {
                "faithfulness": 0.5,
                "answer_relevancy": 0.5,
                "context_precision": 0.5,
                "overall_score": 0.5,
                "passed": True,
                "retry_count": retry_count,
                "reasoning": f"Eval failed: {str(e)}",
                "latency_ms": (time.monotonic() - t0) * 1000,
            }

    def _parse_eval_response(self, text: str) -> Dict[str, Any]:
        """Robustly parse JSON from eval response."""
        # Strip markdown fences if present
        text = re.sub(r"```(?:json)?", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback: extract numbers with regex
            def extract(key: str) -> float:
                # Match both quoted ("faithfulness": 0.8) and bare (faithfulness: 0.8) keys
                m = re.search(rf'"?{key}"?\s*:\s*([0-9.]+)', text)
                return float(m.group(1)) if m else 0.5

            return {
                "faithfulness": extract("faithfulness"),
                "answer_relevancy": extract("answer_relevancy"),
                "context_precision": extract("context_precision"),
                "reasoning": "Parsed from malformed JSON",
            }
