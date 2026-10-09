from __future__ import annotations
import logging
import hashlib
from uuid import UUID
import json
from app.core.redis import redis_client
from app.core.config import settings

logger = logging.getLogger("trace.calc.cache")

IMMUTABLE_STATUSES = frozenset({"COMPLETED", "SUPERSEDED", "FAILED"})

def cacheable(status: str) -> bool:
  return status in IMMUTABLE_STATUSES and int(settings.calc_read_cache_ttl_seconds) > 0

class RunReadCache:
  def __init__(self, client=None):
    self._client_override = client

  def _client(self):
    if self._client_override is not None:
      return self._client_override
    
    return redis_client

  @staticmethod
  def key(organization_id: UUID, run_id: UUID, name: str, params: dict) -> str:
    digest = hashlib.sha1(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:20]
    return f"trace:calc:read:{organization_id}:{run_id}:{name}:{digest}"

  async def get(self, organization_id: UUID, run_id: UUID, name: str, params: dict):
    try:
      raw = await self._client().get(self.key(organization_id, run_id, name, params))
      return json.loads(raw) if raw else None
    except Exception:
      logger.debug("read cache unavailable", exc_info=True)
      return None

  async def put(self, organization_id: UUID, run_id: UUID, name: str, params: dict, payload) -> None:
    try:
      await self._client().set(self.key(organization_id, run_id, name, params), json.dumps(payload, default=str),
        ex=int(settings.calc_read_cache_ttl_seconds))
    except Exception:
      logger.debug("read cache write failed", exc_info=True)

  async def drop_run(self, organization_id: UUID, run_id: UUID) -> int:
    try:
      client = self._client()
      removed = 0
      async for k in client.scan_iter(match=f"trace:calc:read:{organization_id}:{run_id}:*", count=200):
        removed += await client.delete(k)
      return removed
    except Exception:
      return 0