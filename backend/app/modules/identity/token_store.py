from __future__ import annotations
import hashlib
import secrets
import redis.asyncio as redis

class IdentityTokenStore:
  def __init__(self, client: redis.Redis):
    self.client = client

  @staticmethod
  def generate_token() -> str:
    return secrets.token_urlsafe(48)

  @staticmethod
  def hash_token(token: str) -> str:
    return hashlib.sha256(
      token.encode("utf-8")
    ).hexdigest()
    
  async def create(
    self,
    *,
    prefix: str,
    user_id: str,
    ttl_seconds: int,
  ) -> str:
    token = self.generate_token()

    await self.store(
      prefix=prefix,
      token=token,
      value=user_id,
      ttl_seconds=ttl_seconds,
    )

    return token

  async def store(
    self,
    *,
    prefix: str,
    token: str,
    value: str,
    ttl_seconds: int,
  ) -> None:
    key = f"trace:identity:{prefix}:{self.hash_token(token)}"

    await self.client.set(
      key,
      value,
      ex=ttl_seconds,
    )

  async def consume(
    self,
    *,
    prefix: str,
    token: str,
  ) -> str | None:
    key = f"trace:identity:{prefix}:{self.hash_token(token)}"
    script = """
    local value = redis.call('GET', KEYS[1])
    if value then
        redis.call('DEL', KEYS[1])
    end
    return value
    """
    return await self.client.eval(
      script,
      1,
      key,
    )

  async def revoke(
    self,
    *,
    prefix: str,
    token: str,
  ) -> None:
    key = f"trace:identity:{prefix}:{self.hash_token(token)}"

    await self.client.delete(key)