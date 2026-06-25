"""sessions.py — Session CRUD router"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from gateway.database import get_db
from gateway.models import User, Session, Message
from gateway.auth import get_current_user
from gateway.schemas import SessionCreate, SessionResponse, SessionStatus

router = APIRouter()


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = Session(
        user_id=current_user.id,
        title=payload.title or "New Chat",
        system_prompt=payload.system_prompt,
        preferred_provider=payload.preferred_provider.value,
    )
    db.add(session)
    await db.flush()
    return SessionResponse(
        id=session.id,
        title=session.title,
        status=SessionStatus.ACTIVE,
        created_at=session.created_at,
        message_count=0,
    )


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Session).where(Session.user_id == current_user.id).order_by(Session.created_at.desc())
    )
    sessions = result.scalars().all()
    out = []
    for s in sessions:
        count_result = await db.execute(
            select(func.count()).where(Message.session_id == s.id)
        )
        count = count_result.scalar() or 0
        out.append(SessionResponse(
            id=s.id, title=s.title, status=s.status,
            created_at=s.created_at, message_count=count,
        ))
    return out


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
