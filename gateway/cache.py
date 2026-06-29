import json
from typing import Any, Optional
import redis.asyncio as aioredis
from gateway.config import get_settings

settings = get_settings()
_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    value = await r.get(key)
    if value:
        return json.loads(value)
    return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    r = await get_redis()
    await r.setex(key, ttl, json.dumps(value, default=str))


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def rate_limit_check(user_id: str, limit: int = 60, window: int = 60) -> bool:
    """Sliding window rate limiter. Returns True if request is allowed."""
    r = await get_redis()
    key = f"rl:{user_id}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    results = await pipe.execute()
    count = results[0]
    return count <= limit


async def increment_query_counter(user_id: str) -> int:
    r = await get_redis()
    key = f"queries:{user_id}:{__import__('datetime').date.today()}"
    count = await r.incr(key)
    await r.expire(key, 86400)
    return count
