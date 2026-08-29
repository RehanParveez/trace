from __future__ import annotations
from uuid import UUID
from typing import Any
from app.core.redis import redis_client
import json
from dataclasses import dataclass
from app.core.config import settings

@dataclass(frozen=True)
class IdempotencyContext:
  key: str
  user_id: UUID | None = None
  organization_id: UUID | None = None

def _redis_key(organization_id: UUID, scope: str, key: str) -> str:
  return f"idempotency:{organization_id}:{scope}:{key}"

async def get_cached_response(
  organization_id: UUID, scope: str, key: str,
) -> dict[str, Any] | None:
  raw = await redis_client.get(_redis_key(organization_id, scope, key))
  if raw is None:
    return None
  return json.loads(raw)

async def store_response(
  organization_id: UUID, scope: str, key: str,
  response: dict[str, Any], ttl_seconds: int | None = None,
) -> None:
  ttl = ttl_seconds or settings.idempotency_key_ttl_seconds
  await redis_client.set(
    _redis_key(organization_id, scope, key),
    json.dumps(response, default=str),
    ex=ttl,
  )