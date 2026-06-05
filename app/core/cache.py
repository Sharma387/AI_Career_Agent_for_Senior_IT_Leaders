import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache with in-memory fallback."""

    def __init__(self):
        self._redis = None
        self._memory: dict[str, str] = {}
        self._initialized = False

    async def _init_redis(self):
        if self._initialized:
            return
        self._initialized = True
        from app.core.config import settings

        if not settings.REDIS_URL:
            logger.info("No REDIS_URL configured, using in-memory cache")
            return
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await self._redis.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.warning(f"Redis unavailable, falling back to in-memory cache: {e}")
            self._redis = None

    async def get(self, key: str) -> Optional[str]:
        await self._init_redis()
        if self._redis:
            try:
                return await self._redis.get(key)
            except Exception:
                return self._memory.get(key)
        return self._memory.get(key)

    async def set(self, key: str, value: str, ttl: int = 300) -> None:
        await self._init_redis()
        if self._redis:
            try:
                await self._redis.setex(key, ttl, value)
                return
            except Exception:
                pass
        self._memory[key] = value

    async def get_json(self, key: str) -> Optional[dict]:
        raw = await self.get(key)
        return json.loads(raw) if raw else None

    async def set_json(self, key: str, value: dict, ttl: int = 300) -> None:
        await self.set(key, json.dumps(value), ttl)

    async def delete(self, key: str) -> None:
        await self._init_redis()
        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception:
                pass
        self._memory.pop(key, None)

    async def close(self):
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass


cache = CacheService()
