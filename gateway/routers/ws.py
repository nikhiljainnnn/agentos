"""
ws.py — WebSocket endpoint for real-time agent event streaming.
Clients connect here to receive live agent step updates and token streaming.
"""
import json
import asyncio
from typing import Dict

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError

from gateway.config import get_settings
from gateway.schemas import WSEvent, WSEventType
from orchestrator.graph import run_orchestrator

logger = structlog.get_logger(__name__)
settings = get_settings()
router = APIRouter()


# Maximum concurrent WebSocket connections per user to prevent abuse.
MAX_CONNECTIONS_PER_USER = 3


class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}      # session_id → websocket
        self._user_conn_count: Dict[str, int] = {}  # user_id → active conn count

    def can_connect(self, user_id: str) -> bool:
        """Returns True if the user is below the concurrent connection limit."""
        return self._user_conn_count.get(user_id, 0) < MAX_CONNECTIONS_PER_USER

    async def connect(self, session_id: str, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active[session_id] = websocket
        self._user_conn_count[user_id] = self._user_conn_count.get(user_id, 0) + 1
        logger.info(
            "ws_connected",
            session_id=session_id,
            user_id=user_id,
            user_connections=self._user_conn_count[user_id],
        )

    def disconnect(self, session_id: str, user_id: str | None = None):
        self.active.pop(session_id, None)
        if user_id and user_id in self._user_conn_count:
            self._user_conn_count[user_id] = max(
                0, self._user_conn_count[user_id] - 1
            )
        logger.info("ws_disconnected", session_id=session_id, user_id=user_id)

    async def send(self, session_id: str, event: WSEvent):
        ws = self.active.get(session_id)
        if ws:
            try:
                await ws.send_text(event.model_dump_json())
            except Exception as e:
                logger.error("ws_send_failed", session_id=session_id, error=str(e))
                self.disconnect(session_id)

    async def broadcast_agent_step(self, session_id: str, agent: str, output: str):
        event = WSEvent(
            event=WSEventType.AGENT_STEP,
            session_id=session_id,
            data={"agent": agent, "output": output},
        )
        await self.send(session_id, event)


manager = ConnectionManager()


def _verify_token(token: str) -> str | None:
    """Returns user_id if token valid, else None."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("sub")
    except JWTError:
        return None


@router.websocket("/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
    query: str = Query(...),
    enable_rag: bool = Query(True),
    enable_search: bool = Query(False),
    enable_code: bool = Query(False),
):
    """
    WebSocket endpoint for streaming agent responses.
    Client sends auth token as query param (WS doesn't support headers easily).
    """
    user_id = _verify_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Per-user concurrent connection rate limit
    if not manager.can_connect(user_id):
        await websocket.close(
            code=4029,
            reason=f"Too many concurrent connections (max {MAX_CONNECTIONS_PER_USER})",
        )
        logger.warning("ws_rate_limited", user_id=user_id)
        return

    await manager.connect(session_id, user_id, websocket)

    try:
        # Send start event
        await manager.send(
            session_id,
            WSEvent(
                event=WSEventType.AGENT_START,
                session_id=session_id,
                data={"query": query},
            ),
        )

        # Run orchestrator — agent steps emit events
        state = await run_orchestrator(
            query=query,
            session_id=session_id,
            enable_rag=enable_rag,
            enable_search=enable_search,
            enable_code=enable_code,
            enable_eval=True,
        )

        # Stream response tokens (simulated word-by-word for UX)
        words = state["final_response"].split()
        for i, word in enumerate(words):
            await manager.send(
                session_id,
                WSEvent(
                    event=WSEventType.STREAM_TOKEN,
                    session_id=session_id,
                    data={"token": word + " ", "index": i},
                ),
            )
            await asyncio.sleep(0.02)  # ~50 tokens/s pacing

        # Send eval result
        if state.get("eval_metrics"):
            await manager.send(
                session_id,
                WSEvent(
                    event=WSEventType.EVAL_RESULT,
                    session_id=session_id,
                    data=state["eval_metrics"],
                ),
            )

        # Send complete event
        await manager.send(
            session_id,
            WSEvent(
                event=WSEventType.AGENT_COMPLETE,
                session_id=session_id,
                data={
                    "agent_steps": state.get("agent_steps", []),
                    "provider": state.get("provider_used"),
                    "latency_ms": state.get("total_latency_ms"),
                },
            ),
        )

    except WebSocketDisconnect:
        logger.info("ws_client_disconnected", session_id=session_id)
    except Exception as e:
        logger.error("ws_error", session_id=session_id, error=str(e))
        await manager.send(
            session_id,
            WSEvent(
                event=WSEventType.ERROR,
                session_id=session_id,
                data={"message": str(e)},
            ),
        )
    finally:
        manager.disconnect(session_id, user_id)


def get_manager() -> ConnectionManager:
    return manager
