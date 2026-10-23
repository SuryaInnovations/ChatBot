"""
Async Redis Client with automatic in-memory fallback.
Ensures seamless distributed caching, rate limiting, and circuit breaker operation in production,
while allowing local developers and test suites to run cleanly without requiring a local Redis daemon.
"""

import os
import time
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger("chatbot.redis")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class InMemoryFallbackRedis:
    """Thread-safe in-memory key-value store simulating core Redis methods."""
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}

    def _is_expired(self, key: str) -> bool:
        if key in self._expires:
            if time.time() > self._expires[key]:
                del self._expires[key]
                self._data.pop(key, None)
                return True
        return False

    async def get(self, key: str) -> Optional[str]:
        if self._is_expired(key):
            return None
        val = self._data.get(key)
        return str(val) if val is not None else None

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._data[key] = value
        if ex:
            self._expires[key] = time.time() + ex
        else:
            self._expires.pop(key, None)
        return True

    async def incr(self, key: str) -> int:
        if self._is_expired(key):
            self._data[key] = 0
        current = int(self._data.get(key, 0)) + 1
        self._data[key] = current
        return current

    async def expire(self, key: str, seconds: int) -> bool:
        if key in self._data:
            self._expires[key] = time.time() + seconds
            return True
        return False

    async def delete(self, key: str) -> int:
        deleted = 0
        if key in self._data:
            del self._data[key]
            deleted = 1
        self._expires.pop(key, None)
        return deleted

    async def ping(self) -> bool:
        return True


class DistributedRedisManager:
    def __init__(self):
        self._client = None
        self._is_connected = False
        self._fallback = InMemoryFallbackRedis()

    async def get_client(self):
        if self._client is not None and self._is_connected:
            return self._client

        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2.0)
            await client.ping()
            self._client = client
            self._is_connected = True
            logger.info(f"Connected to distributed Redis cluster at: {REDIS_URL}")
            return self._client
        except Exception as e:
            if not self._is_connected:
                logger.warning(f"Redis unavailable ({e}). Using in-memory fallback store.")
            self._is_connected = False
            return self._fallback

    async def get(self, key: str) -> Optional[str]:
        client = await self.get_client()
        return await client.get(key)

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        client = await self.get_client()
        return await client.set(key, value, ex=ex)

    async def incr(self, key: str) -> int:
        client = await self.get_client()
        return await client.incr(key)

    async def expire(self, key: str, seconds: int) -> bool:
        client = await self.get_client()
        return await client.expire(key, seconds)

    async def delete(self, key: str) -> int:
        client = await self.get_client()
        return await client.delete(key)


redis_manager = DistributedRedisManager()
