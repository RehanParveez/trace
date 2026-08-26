from __future__ import annotations
import redis.asyncio as redis
from app.core.exceptions import TraceException

class RateLimiter:
  def __init__(self, client: redis.Redis):
    self.client = client

  async def check(
    self,
    *,
    key: str,
    limit: int,
    window_seconds: int,
  ) -> None:
    redis_key = f"trace:ratelimit:{key}"

    script = """
    local current = redis.call('INCR', KEYS[1])
    if current == 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[1])
    end

    return current
    """
    current = await self.client.eval(
      script,
      1,
      redis_key,
      window_seconds,
    )

    if int(current) > limit:
      raise TraceException(
        "Too many requests. Please try again later.",
        status_code=429,
        code="RATE_LIMIT_EXCEEDED",
      )