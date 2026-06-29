# ─── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps (using uv for lightning fast resolution)
COPY pyproject.toml ./
RUN pip install uv && uv pip compile pyproject.toml -o requirements.txt && uv pip install --system -r requirements.txt

# App code
COPY gateway/ ./gateway/
COPY agents/ ./agents/
COPY orchestrator/ ./orchestrator/

# Non-root user
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
