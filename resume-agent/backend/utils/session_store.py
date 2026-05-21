# backend/utils/session_store.py
"""
Redis-backed session store for optimizer state.
Saves the LangGraph state between the "pause" and "resume" steps
so the user can take time reviewing without losing progress.
"""

import json
import uuid
from typing import Optional
import redis.asyncio as aioredis
from api.config import get_settings

settings = get_settings()

SESSION_TTL_SECONDS = 60 * 30  # 30 minutes — session expires if user doesn't respond


def get_redis():
    """Returns an async Redis client."""
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def save_session(state: dict) -> str:
    """
    Saves optimizer state to Redis and returns a unique session_id.
    Called when the graph pauses after rewrite_node.

    Returns:
        session_id: UUID string the frontend uses to resume the session
    """
    session_id = str(uuid.uuid4())
    r = get_redis()
    await r.setex(
        f"optimizer_session:{session_id}",
        SESSION_TTL_SECONDS,
        json.dumps(state)
    )
    await r.aclose()
    return session_id


async def get_session(session_id: str) -> Optional[dict]:
    """
    Retrieves optimizer state from Redis by session_id.
    Returns None if session expired or doesn't exist.
    """
    r = get_redis()
    data = await r.get(f"optimizer_session:{session_id}")
    await r.aclose()
    if data is None:
        return None
    return json.loads(data)


async def update_session(session_id: str, state: dict) -> None:
    """
    Updates an existing session with new state.
    Resets the TTL so user gets another 30 minutes.
    """
    r = get_redis()
    await r.setex(
        f"optimizer_session:{session_id}",
        SESSION_TTL_SECONDS,
        json.dumps(state)
    )
    await r.aclose()


async def delete_session(session_id: str) -> None:
    """Cleans up a session after optimization is complete."""
    r = get_redis()
    await r.delete(f"optimizer_session:{session_id}")
    await r.aclose()
