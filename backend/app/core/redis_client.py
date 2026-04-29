import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

_redis_pool: aioredis.Redis | None = None


def get_redis_pool() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    yield get_redis_pool()


def session_key(session_id: uuid.UUID | str) -> str:
    return f"session:{session_id}"


async def set_session_state(
    session_id: uuid.UUID | str,
    data: dict[str, Any],
    ttl: int = 14400,
) -> None:
    r = get_redis_pool()
    await r.set(session_key(session_id), json.dumps(data), ex=ttl)


async def get_session_state(session_id: uuid.UUID | str) -> dict[str, Any] | None:
    r = get_redis_pool()
    raw = await r.get(session_key(session_id))
    if raw is None:
        return None
    return json.loads(raw)  # type: ignore[no-any-return]


async def delete_session_state(session_id: uuid.UUID | str) -> None:
    r = get_redis_pool()
    await r.delete(session_key(session_id))
