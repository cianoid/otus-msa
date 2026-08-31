import json
from typing import Any

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from src.core.logger import log


class CacheClient:
    """Fail-open Redis cache: errors are logged, never raised."""

    def __init__(self, host: str, port: int, ttl_seconds: int) -> None:
        # Быстрые таймауты и без ретраев: при недоступном Redis сервис продолжает работать через БД.
        self._redis = Redis(
            host=host,
            port=port,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
            retry=Retry(NoBackoff(), 0),
        )
        self._ttl = ttl_seconds

    async def get_json(self, key: str) -> Any | None:
        try:
            raw = await self._redis.get(key)
            return json.loads(raw) if raw is not None else None
        except (RedisError, ValueError) as exc:
            log.warning("Cache GET %s failed: %s", key, exc)
            return None

    async def set_json(self, key: str, value: Any) -> None:
        try:
            await self._redis.set(key, json.dumps(value), ex=self._ttl)
        except (RedisError, TypeError, ValueError) as exc:
            log.warning("Cache SET %s failed: %s", key, exc)

    async def delete(self, *keys: str) -> None:
        try:
            await self._redis.delete(*keys)
        except RedisError as exc:
            log.warning("Cache DEL %s failed: %s", keys, exc)

    async def close(self) -> None:
        await self._redis.aclose()
