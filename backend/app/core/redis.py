from __future__ import annotations
from collections.abc import AsyncIterator
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(
  settings.redis_url,
  encoding="utf-8",
  decode_responses=True,
)

async def get_redis() -> AsyncIterator[redis.Redis]:
  yield redis_client

async def close_redis() -> None:
  await redis_client.aclose()

class IdentityTokenStore:
  def __init__(self, client: redis.Redis):
    self.client = client

  def _key(
    self,
    prefix: str,
    token: str,
  ) -> str:
    return f"trace:{prefix}:{token}"

  async def create(
    self,
    prefix: str,
    user_id: str,
    ttl_seconds: int,
  ) -> str:
    import secrets

    token = secrets.token_urlsafe(48)

    key = self._key(
      prefix,
      token,
    )

    await self.client.set(
      key,
      user_id,
      ex=ttl_seconds,
    )

    return token

  async def consume(
    self,
    prefix: str,
    token: str,
  ) -> str | None:
    key = self._key(
      prefix,
      token,
    )

    user_id = await self.client.get(key)

    if user_id is None:
      return None

    await self.client.delete(key)

    return user_id

  async def delete(
    self,
    prefix: str,
    token: str,
  ) -> None:
    await self.client.delete(
      self._key(
        prefix,
        token,
      )
    )

  async def exists(
    self,
    prefix: str,
    token: str,
  ) -> bool:
    return bool(
      await self.client.exists(
        self._key(
          prefix,
          token,
        )
      )
    )