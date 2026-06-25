# AgentOS

**Production Multi-Agent RAG Platform** — built to demonstrate senior-level AI engineering across the full stack.

## Architecture

```
React Dashboard → FastAPI Gateway → LangGraph Orchestrator
                                         ├── RAG Agent      (ChromaDB + sentence-transformers)
                                         ├── Search Agent   (Tavily)
                                         ├── Code Agent     (sandboxed subprocess)
                                         └── Critic Agent   (RAGAS eval + retry loop)
                                                  ↓
                                    LiteLLM Router (Azure → Claude → Gemini)
                                                  ↓
                              Observability: LangSmith · Kafka · Prometheus · Grafana
                                                  ↓
                                    Kubernetes (k3d) + GitHub Actions CI/CD
```

## Key Differentiators

- **Eval-in-the-loop**: Critic agent scores every response with RAGAS-style metrics. If `overall_score < 0.65`, automatically retries with a different provider
- **Provider failover**: LiteLLM routes Azure OpenAI → Anthropic Claude → Google Gemini on failure, with per-provider latency tracking
- **Full observability**: LangSmith traces + Kafka event streaming + Prometheus metrics + Grafana dashboards
- **MCP server**: Exposes all agents as MCP tools for Claude Code / Claude Desktop
- **Production-ready**: JWT auth, async SQLAlchemy, Redis rate limiting, HPA, rolling deployments

## Tech Stack

| Layer | Technologies |
|---|---|
| **LLM** | Azure OpenAI, Anthropic Claude, Google Gemini via LiteLLM |
| **Agents** | LangGraph, LangChain, LangSmith |
| **RAG** | ChromaDB, pgvector, sentence-transformers |
| **Search** | Tavily |
| **Backend** | FastAPI, SQLAlchemy (async), Alembic, Redis, Kafka |
| **Database** | PostgreSQL + pgvector |
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, Recharts, Zustand |
| **Infra** | Docker, Kubernetes (k3d), Prometheus, Grafana |
| **CI/CD** | GitHub Actions |
| **Protocol** | MCP (Model Context Protocol) |

## Quick Start

```bash
# 1. Clone and set environment
git clone <repo> && cd agentos
cp .env.example .env
# Add at minimum: ANTHROPIC_API_KEY or AZURE_OPENAI_API_KEY

# 2. One-command start
bash scripts/quickstart.sh
```

Services will be available at:
- **Frontend**: http://localhost:5173
- **API + Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090

## Manual Setup

```bash
# Infrastructure
docker compose -f infra/docker/docker-compose.yml up -d

# Python deps
pip install poetry && poetry install

# DB migrations
poetry run alembic upgrade head

# Backend
poetry run uvicorn gateway.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## Running Tests

```bash
# Unit tests (no external services needed)
poetry run pytest tests/unit/ -v

# Integration tests (needs Postgres + Redis)
poetry run pytest tests/integration/ -v

# E2E tests
poetry run pytest tests/e2e/ -v

# All
poetry run pytest -v --tb=short
```

## Kubernetes Deployment (k3d)

```bash
# Install k3d: https://k3d.io
brew install k3d  # macOS

# Deploy full cluster
bash infra/k8s/deploy.sh

# Check status
kubectl get pods -n agentos

# Access via port-forward if ingress isn't set up
kubectl port-forward svc/agentos-gateway-service 8000:8000 -n agentos
```

## MCP Integration (Claude Code / Claude Desktop)

```bash
# Add to claude_desktop_config.json
# (see mcp_server/claude_desktop_config.example.json)
```

Available MCP tools:
- `rag_retrieve` — semantic search over knowledge base
- `web_search` — real-time Tavily search
- `execute_python` — sandboxed code execution
- `agentos_query` — full multi-agent orchestration
- `ingest_document` — add documents to RAG

## API Reference

```bash
# Auth
POST /api/auth/register
POST /api/auth/login

# Sessions
POST   /api/sessions/
GET    /api/sessions/
DELETE /api/sessions/{id}

# Messages (main query endpoint)
POST /api/messages/
GET  /api/messages/{session_id}

# Documents (RAG)
POST /api/documents/
POST /api/documents/upload

# Metrics
GET /api/metrics/
GET /api/metrics/providers

# System
GET /health
GET /metrics  (Prometheus)

# WebSocket
WS /ws/chat/{session_id}?token=...&query=...
```

## Environment Variables

See `.env.example` for all configuration options. Required at minimum:
- `SECRET_KEY` — JWT signing key (32+ chars)
- `DATABASE_URL` — PostgreSQL connection string
- At least one of: `ANTHROPIC_API_KEY`, `AZURE_OPENAI_API_KEY`, `GOOGLE_API_KEY`

## Project Structure

```
agentos/
├── gateway/              # FastAPI application
│   ├── main.py           # App entrypoint + middleware
│   ├── auth.py           # JWT authentication
│   ├── models.py         # SQLAlchemy ORM models
│   ├── schemas.py        # Pydantic v2 schemas
│   ├── routers/          # Route handlers
│   └── observability/    # Metrics + logging + Kafka
├── agents/               # Specialist agents
│   ├── llm_router.py     # LiteLLM failover router
│   ├── rag_agent.py      # ChromaDB retrieval
│   ├── search_agent.py   # Tavily web search
│   ├── code_agent.py     # Sandboxed code execution
│   └── critic_agent.py   # RAGAS eval + retry
├── orchestrator/
│   └── graph.py          # LangGraph state machine
├── mcp_server/
│   └── server.py         # MCP tool server
├── frontend/             # React + Vite + TypeScript
│   └── src/
│       ├── pages/        # Chat, Dashboard, Login
│       └── lib/store.ts  # Zustand state
├── infra/
│   ├── docker/           # Docker Compose + Prometheus + Grafana
│   └── k8s/              # Kubernetes manifests + deploy script
├── alembic/              # DB migrations
├── tests/                # Unit + Integration + E2E
└── .github/workflows/    # CI/CD pipeline
```
