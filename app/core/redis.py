import os
import logging
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger("uvicorn.error")

redis_client: Optional[redis.Redis] = None

ONLINE_USERS_KEY = "forglory:online_users"  # Redis Set
ONLINE_TTL_SECONDS = 120  # safety TTL for heartbeat-based tracking

async def init_redis() -> Optional[redis.Redis]:
    """Initialize a global Redis client (async). Safe to call multiple times."""
    global redis_client

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning("REDIS_URL not set; Redis features disabled.")
        redis_client = None
        return None

    # Render Valkey/Redis URL usually already starts with redis://
    client = redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    # Connection test
    try:
        await client.ping()
    except Exception as e:
        logger.exception("Redis connection failed: %s", e)
        redis_client = None
        return None

    redis_client = client
    logger.info("✅ Redis connected")
    return redis_client

async def close_redis() -> None:
    global redis_client
    if redis_client is None:
        return
    try:
        await redis_client.close()
    finally:
        redis_client = None

def get_redis() -> Optional[redis.Redis]:
    return redis_client

async def online_add(user_id: int) -> None:
    """Mark user online (best-effort)."""
    r = get_redis()
    if r is None:
        return
    try:
        await r.sadd(ONLINE_USERS_KEY, str(user_id))
        # Optional: keep a TTL marker per user for cleanup if you add heartbeat later
        await r.setex(f"forglory:online_user:{user_id}", ONLINE_TTL_SECONDS, "1")
    except Exception:
        logger.exception("Failed to online_add(%s)", user_id)

async def online_remove(user_id: int) -> None:
    """Mark user offline (best-effort)."""
    r = get_redis()
    if r is None:
        return
    try:
        await r.srem(ONLINE_USERS_KEY, str(user_id))
        await r.delete(f"forglory:online_user:{user_id}")
    except Exception:
        logger.exception("Failed to online_remove(%s)", user_id)

async def online_list() -> list[int]:
    """Return online users from Redis if available."""
    r = get_redis()
    if r is None:
        return []
    try:
        ids = await r.smembers(ONLINE_USERS_KEY)
        out=[]
        for s in ids:
            try:
                out.append(int(s))
            except Exception:
                pass
        return out
    except Exception:
        logger.exception("Failed to online_list()")
        return []
