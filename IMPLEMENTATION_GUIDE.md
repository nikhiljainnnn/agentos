# AgentOS — Full Production Implementation Guide

## Architecture Overview

```
                        ┌─────────────────────────────────────┐
                        │          React Dashboard              │
                        │   (Vite + TailwindCSS + shadcn/ui)   │
                        └──────────────┬──────────────────────┘
                                       │ HTTP / WebSocket
                        ┌──────────────▼──────────────────────┐
                        │       FastAPI Gateway (8000)          │
                        │  Auth · Rate Limit · WS · REST       │
                        └──┬───────────┬──────────────────┬───┘
                           │           │                  │
              ┌────────────▼──┐  ┌─────▼──────┐  ┌──────▼──────┐
              │  LangGraph    │  │   Redis     │  │  PostgreSQL  │
              │  Orchestrator │  │   Cache     │  │  + pgvector  │
              └──┬────────────┘  └─────────────┘  └─────────────┘
                 │
    ┌────────────┼────────────────────────────────┐
    │            │                                │
┌───▼───┐  ┌────▼──────┐  ┌──────────┐  ┌───────▼──────┐
│  RAG  │  │  Search   │  │  Code    │  │   Critic /   │
│ Agent │  │  Agent    │  │  Exec    │  │   Eval Agent │
└───┬───┘  └────┬──────┘  │  Agent   │  └───────┬──────┘
    │            │         └──────────┘          │
    └────────────┴──────────────┬────────────────┘
                                │
                    ┌───────────▼──────────┐
                    │  LiteLLM Router      │
                    │  Azure → Claude →    │
                    │  Gemini (fallback)   │
                    └───────────┬──────────┘
                                │
                    ┌───────────▼──────────┐
                    │  Observability       │
                    │  LangSmith · Prom ·  │
                    │  Grafana · Kafka     │
                    └──────────────────────┘
```

## Phase-by-Phase Implementation

### Phase 1: Backend Foundation (Days 1-2)
- FastAPI gateway with JWT auth
- PostgreSQL + pgvector setup
- Redis caching layer
- Pydantic schemas

### Phase 2: Agent System (Days 3-5)
- LangGraph orchestrator + supervisor
- RAG agent (ChromaDB + pgvector)
- Search agent (Tavily)
- Code exec agent (sandboxed subprocess)
- Critic/eval agent (RAGAS metrics)

### Phase 3: LLM Router (Day 6)
- LiteLLM provider-agnostic routing
- Azure OpenAI primary
- Claude fallback
- Gemini tertiary
- Latency + cost tracking

### Phase 4: Observability (Day 7)
- LangSmith tracing
- Kafka event streaming
- Prometheus metrics
- Grafana dashboards

### Phase 5: Frontend (Days 8-9)
- React + Vite dashboard
- WebSocket live streaming
- Agent trace visualization
- Eval metrics display

### Phase 6: K8s Deployment (Day 10)
- Dockerfiles for each service
- k3d local cluster
- Helm charts
- GitHub Actions CI/CD

## Running the Project

```bash
# 1. Clone and setup
git clone <your-repo>
cd agentos
cp .env.example .env  # fill in keys

# 2. Start infrastructure
docker compose -f infra/docker/docker-compose.yml up -d

# 3. Run migrations
cd gateway && alembic upgrade head

# 4. Start services
uvicorn gateway.main:app --reload --port 8000

# 5. Start frontend
cd frontend && npm install && npm run dev

# 6. Deploy to k3d
cd infra/k8s && ./deploy.sh
```
