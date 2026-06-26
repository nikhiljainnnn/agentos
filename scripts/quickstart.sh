#!/bin/bash
# ============================================================
# AgentOS Quick Start Script
# Run this from the project root: bash scripts/quickstart.sh
# ============================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════╗${NC}"
echo -e "${GREEN}║     AgentOS Quick Start          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════╝${NC}"

# ─── 1. Check prerequisites ───────────────────────────────────────────────────
echo -e "\n${YELLOW}[1/6] Checking prerequisites...${NC}"
command -v python3.11 >/dev/null || { echo -e "${RED}Python 3.11 required${NC}"; exit 1; }
command -v docker >/dev/null || { echo -e "${RED}Docker required${NC}"; exit 1; }
command -v node >/dev/null || { echo -e "${RED}Node.js required${NC}"; exit 1; }
echo -e "${GREEN}✓ All prerequisites met${NC}"

# ─── 2. Copy env ─────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[2/6] Setting up environment...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠  Created .env from .env.example — ADD YOUR API KEYS!${NC}"
    echo -e "${YELLOW}   Required: ANTHROPIC_API_KEY or AZURE_OPENAI_API_KEY${NC}"
else
    echo -e "${GREEN}✓ .env exists${NC}"
fi

# ─── 3. Start infrastructure ──────────────────────────────────────────────────
echo -e "\n${YELLOW}[3/6] Starting infrastructure (Postgres, Redis, Chroma, Kafka)...${NC}"
docker compose -f infra/docker/docker-compose.yml up -d
echo -e "${GREEN}✓ Infrastructure started${NC}"
echo "   Waiting 15s for services to be ready..."
sleep 15

# ─── 4. Install Python deps ───────────────────────────────────────────────────
echo -e "\n${YELLOW}[4/6] Installing Python dependencies...${NC}"
pip install poetry -q
poetry install --no-root -q
echo -e "${GREEN}✓ Python deps installed${NC}"

# ─── 5. Run migrations ────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[5/6] Running database migrations...${NC}"
poetry run alembic upgrade head || echo -e "${YELLOW}⚠  Alembic not configured yet — tables created via SQLAlchemy${NC}"
echo -e "${GREEN}✓ Migrations done${NC}"

# ─── 6. Start services ────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[6/6] Starting services...${NC}"

# Start FastAPI in background
poetry run uvicorn gateway.main:app --reload --port 8000 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"

# Start React frontend
cd frontend
npm install -q
npm run dev &
FRONTEND_PID=$!
cd ..
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"

echo -e "\n${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  AgentOS is running!                     ║${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║  Frontend:    http://localhost:5173      ║${NC}"
echo -e "${GREEN}║  API:         http://localhost:8000      ║${NC}"
echo -e "${GREEN}║  API Docs:    http://localhost:8000/docs ║${NC}"
echo -e "${GREEN}║  Grafana:     http://localhost:3001      ║${NC}"
echo -e "${GREEN}║  Prometheus:  http://localhost:9090      ║${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║  Press Ctrl+C to stop all services       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"

# Wait and cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker compose -f infra/docker/docker-compose.yml down" EXIT
wait
