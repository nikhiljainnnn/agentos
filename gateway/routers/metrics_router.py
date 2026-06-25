"""metrics_router.py — System metrics endpoint"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import date

from gateway.database import get_db
from gateway.models import User, Message
from gateway.auth import get_current_user
from gateway.schemas import SystemMetrics
from agents.llm_router import get_global_stats

router = APIRouter()


@router.get("/", response_model=SystemMetrics)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()

    count_result = await db.execute(
        select(func.count(Message.id)).where(
            func.date(Message.created_at) == today,
            Message.role == "assistant",
        )
    )
    total_today = count_result.scalar() or 0

    lat_result = await db.execute(
        select(func.avg(Message.total_latency_ms)).where(
            func.date(Message.created_at) == today
        )
    )
    avg_latency = lat_result.scalar() or 0.0

    prov_result = await db.execute(
        select(Message.provider_used, func.count(Message.id))
        .where(func.date(Message.created_at) == today)
        .group_by(Message.provider_used)
    )
    provider_dist = {row[0]: row[1] for row in prov_result.fetchall() if row[0]}

    eval_result = await db.execute(
        select(func.count(Message.id)).where(
            func.date(Message.created_at) == today,
            text("eval_metrics->>'passed' = 'true'"),
        )
    )
    passed = eval_result.scalar() or 0
    pass_rate = passed / total_today if total_today > 0 else 1.0

    # Use global stats — survives across all router instances
    llm_stats = get_global_stats()
    total_errors = sum(v["errors"] for v in llm_stats.values())
    total_calls = sum(v["calls"] for v in llm_stats.values())
    error_rate = total_errors / (total_calls + total_errors) if (total_calls + total_errors) > 0 else 0.0

    return SystemMetrics(
        active_sessions=0,
        total_queries_today=total_today,
        avg_latency_ms=round(avg_latency, 1),
        provider_distribution=provider_dist,
        eval_pass_rate=round(pass_rate, 3),
        error_rate=round(error_rate, 3),
    )


@router.get("/providers")
async def provider_stats(current_user: User = Depends(get_current_user)):
    """Real-time provider stats — accumulated across all router instances."""
    return get_global_stats()
