import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from gateway.database import get_db
from gateway.models import User, Session, Message
from gateway.auth import get_current_user
from gateway.schemas import MessageCreate, MessageResponse, MessageRole, AgentStep, EvalMetrics
from gateway.observability.metrics import record_request, record_eval
from orchestrator.graph import run_orchestrator

router = APIRouter()


@router.post("/", response_model=MessageResponse)
async def send_message(
    payload: MessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate session ownership
    result = await db.execute(
        select(Session).where(
            Session.id == payload.session_id,
            Session.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch conversation history (last 10 messages)
    hist_result = await db.execute(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(desc(Message.created_at))
        .limit(10)
    )
    history_msgs = list(reversed(hist_result.scalars().all()))
    history = [
        {"role": m.role, "content": m.content}
        for m in history_msgs
    ]

    # Save user message
    user_msg = Message(
        session_id=session.id,
        role=MessageRole.USER,
        content=payload.content,
    )
    db.add(user_msg)
    await db.flush()

    # Run orchestrator
    try:
        state = await run_orchestrator(
            query=payload.content,
            session_id=str(session.id),
            history=history,
            enable_rag=payload.enable_rag,
            enable_search=payload.enable_search,
            enable_code=payload.enable_code,
            enable_eval=payload.enable_eval,
            preferred_provider=session.preferred_provider,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestrator error: {str(e)}")

    # Parse response
    steps = [
        AgentStep(**s) for s in state.get("agent_steps", [])
    ]

    eval_m = state.get("eval_metrics")
    eval_metrics = EvalMetrics(**eval_m) if eval_m else None

    # Save assistant message
    assistant_msg = Message(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=state["final_response"],
        agent_steps=[s.model_dump() for s in steps],
        eval_metrics=eval_m,
        provider_used=state.get("provider_used"),
        total_latency_ms=state.get("total_latency_ms", 0),
        tokens_used=sum(s.tokens_used for s in steps),
    )
    db.add(assistant_msg)

    # Record prometheus metrics
    record_request(
        provider=state.get("provider_used", "unknown"),
        status="success",
        latency_ms=state.get("total_latency_ms", 0),
    )
    if eval_m:
        record_eval(eval_m)

    # Set user-id header for rate limiter
    request.headers.__dict__["_list"].append(
        (b"x-user-id", str(current_user.id).encode())
    )

    return MessageResponse(
        id=assistant_msg.id,
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=state["final_response"],
        agent_steps=steps,
        eval_metrics=eval_metrics,
        provider_used=state.get("provider_used"),
        total_latency_ms=state.get("total_latency_ms", 0),
        created_at=assistant_msg.created_at or datetime.utcnow(),
    )


@router.get("/{session_id}", response_model=List[MessageResponse])
async def get_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    # Verify session ownership
    sess_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == current_user.id,
        )
    )
    if not sess_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
        .offset(offset)
        .limit(limit)
    )
    messages = result.scalars().all()

    return [
        MessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            agent_steps=[AgentStep(**s) for s in (m.agent_steps or [])],
            eval_metrics=EvalMetrics(**m.eval_metrics) if m.eval_metrics else None,
            provider_used=m.provider_used,
            total_latency_ms=m.total_latency_ms,
            created_at=m.created_at,
        )
        for m in messages
    ]
