from __future__ import annotations
from collections.abc import AsyncIterator
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(
  settings.redis_url,
  encoding = "utf-8",
  decode_responses=True,
)

async def get_redis() -> AsyncIterator[redis.Redis]:
  yield redis_client

async def close_redis() -> None:
  await redis_client.aclose()