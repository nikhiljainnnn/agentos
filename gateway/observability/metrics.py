"""
Prometheus metrics for AgentOS.
Exposed at /metrics endpoint.
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

registry = CollectorRegistry()

# ─── Request Metrics ──────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "agentos_requests_total",
    "Total number of queries processed",
    ["provider", "status"],
    registry=registry,
)

REQUEST_LATENCY = Histogram(
    "agentos_request_latency_ms",
    "End-to-end request latency in milliseconds",
    ["provider"],
    buckets=[100, 250, 500, 1000, 2000, 5000, 10000],
    registry=registry,
)

# ─── Agent Metrics ────────────────────────────────────────────────────────────
AGENT_LATENCY = Histogram(
    "agentos_agent_latency_ms",
    "Per-agent latency in milliseconds",
    ["agent"],
    buckets=[50, 100, 250, 500, 1000, 3000],
    registry=registry,
)

AGENT_CALL_COUNT = Counter(
    "agentos_agent_calls_total",
    "Total calls per agent",
    ["agent", "status"],
    registry=registry,
)

# ─── Eval Metrics ─────────────────────────────────────────────────────────────
EVAL_SCORE = Histogram(
    "agentos_eval_score",
    "Distribution of evaluation scores",
    ["metric"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=registry,
)

EVAL_PASS_RATE = Gauge(
    "agentos_eval_pass_rate",
    "Fraction of responses passing evaluation",
    registry=registry,
)

RETRY_COUNT = Counter(
    "agentos_retries_total",
    "Total number of eval-triggered retries",
    ["from_provider", "to_provider"],
    registry=registry,
)

# ─── System Metrics ───────────────────────────────────────────────────────────
ACTIVE_SESSIONS = Gauge(
    "agentos_active_sessions",
    "Number of currently active sessions",
    registry=registry,
)

TOKEN_USAGE = Counter(
    "agentos_tokens_total",
    "Total tokens consumed",
    ["provider"],
    registry=registry,
)


def record_request(provider: str, status: str, latency_ms: float, tokens: int = 0):
    REQUEST_COUNT.labels(provider=provider, status=status).inc()
    REQUEST_LATENCY.labels(provider=provider).observe(latency_ms)
    if tokens > 0:
        TOKEN_USAGE.labels(provider=provider).inc(tokens)


def record_agent(agent: str, latency_ms: float, success: bool):
    AGENT_LATENCY.labels(agent=agent).observe(latency_ms)
    AGENT_CALL_COUNT.labels(agent=agent, status="success" if success else "error").inc()


def record_eval(metrics: dict):
    for metric_name in ["faithfulness", "answer_relevancy", "context_precision"]:
        if metric_name in metrics:
            EVAL_SCORE.labels(metric=metric_name).observe(metrics[metric_name])
