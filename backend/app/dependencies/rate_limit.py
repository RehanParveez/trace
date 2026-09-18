from __future__ import annotations
from fastapi import Depends
from app.core.config import settings
from app.core.redis import get_redis
from app.modules.identity.rate_limit import RateLimiter
import redis.asyncio as redis

async def get_rate_limiter(
  client: redis.Redis = Depends(get_redis),
) -> RateLimiter:
  return RateLimiter(client)

def rate_limit_webhook():
  async def _check(
    limiter: RateLimiter = Depends(get_rate_limiter),
  ) -> None:
    await limiter.check(
      key="whatsapp_webhook",
      limit=settings.rate_limit_webhook_per_minute,
      window_seconds=60,
    )
  return _check

def pipeline(self):
  return self

async def execute(self):
  return []