from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────

class AgentType(str, Enum):
    RAG = "rag"
    SEARCH = "search"
    CODE = "code"
    CRITIC = "critic"
    SUPERVISOR = "supervisor"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class LLMProvider(str, Enum):
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ─── Auth ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    username: Optional[str] = None


# ─── Sessions ─────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    preferred_provider: LLMProvider = LLMProvider.AZURE


class SessionResponse(BaseModel):
    id: UUID
    title: Optional[str]
    status: SessionStatus
    created_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


# ─── Messages ─────────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=32000)
    session_id: UUID
    enable_rag: bool = True
    enable_search: bool = False
    enable_code: bool = False
    enable_eval: bool = True


class AgentStep(BaseModel):
    agent: AgentType
    input: str
    output: str
    latency_ms: float
    tokens_used: int = 0
    provider: Optional[LLMProvider] = None


class EvalMetrics(BaseModel):
    faithfulness: float = Field(..., ge=0, le=1)
    answer_relevancy: float = Field(..., ge=0, le=1)
    context_precision: float = Field(..., ge=0, le=1)
    overall_score: float = Field(..., ge=0, le=1)
    passed: bool
    retry_count: int = 0


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    agent_steps: List[AgentStep] = []
    eval_metrics: Optional[EvalMetrics] = None
    provider_used: Optional[LLMProvider] = None
    total_latency_ms: float = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Documents (RAG) ──────────────────────────────────────────────────────────

class DocumentIngest(BaseModel):
    title: str
    content: str
    metadata: Dict[str, Any] = {}
    namespace: str = "default"


class DocumentResponse(BaseModel):
    id: str
    title: str
    chunk_count: int
    namespace: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Observability ────────────────────────────────────────────────────────────

class SystemMetrics(BaseModel):
    active_sessions: int
    total_queries_today: int
    avg_latency_ms: float
    provider_distribution: Dict[str, int]
    eval_pass_rate: float
    error_rate: float


# ─── WebSocket ────────────────────────────────────────────────────────────────

class WSEventType(str, Enum):
    AGENT_START = "agent_start"
    AGENT_STEP = "agent_step"
    AGENT_COMPLETE = "agent_complete"
    STREAM_TOKEN = "stream_token"
    EVAL_RESULT = "eval_result"
    ERROR = "error"


class WSEvent(BaseModel):
    event: WSEventType
    session_id: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
