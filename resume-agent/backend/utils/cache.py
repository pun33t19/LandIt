# backend/utils/cache.py
"""
Redis caching for job search results.
Caches full search responses for 1 hour.
Key = hash of (query + filters) so same search = instant response.
"""

import json
import hashlib
from typing import Optional
import redis.asyncio as aioredis
from api.config import get_settings

settings = get_settings()

CACHE_TTL_SECONDS = 60 * 60  # 1 hour


def get_redis():
    return aioredis.from_url(settings.redis_url, decode_responses=True)


def make_cache_key(query: str, filters: dict) -> str:
    """
    Creates a unique cache key from the search parameters.
    Same query + same filters = same key = cache hit.

    Uses MD5 hash to keep keys short (Redis keys should be concise).
    """
    # Sort dict keys so {"a":1,"b":2} and {"b":2,"a":1} give same hash
    canonical = json.dumps(
        {"query": query, "filters": filters},
        sort_keys=True
    )
    hash_str = hashlib.md5(canonical.encode()).hexdigest()[:12]
    return f"job_search:{hash_str}"


async def get_cached_results(cache_key: str) -> Optional[dict]:
    """
    Returns cached search result if it exists.
    Returns None if cache miss or expired.
    """
    r = get_redis()
    try:
        data = await r.get(cache_key)
        if data is None:
            return None
        return json.loads(data)
    finally:
        await r.aclose()


async def cache_results(cache_key: str, results: dict) -> None:
    """
    Saves search results to Redis with 1-hour TTL.
    Called after a fresh search completes.
    """
    r = get_redis()
    try:
        await r.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(results))
    finally:
        await r.aclose()


async def invalidate_cache(cache_key: str) -> None:
    """Manually invalidate a cache entry (e.g. user requests fresh results)."""
    r = get_redis()
    try:
        await r.delete(cache_key)
    finally:
        await r.aclose()
