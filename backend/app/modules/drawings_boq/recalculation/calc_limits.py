from __future__ import annotations
import logging
from uuid import UUID
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.calc_repository import CalculationRunRepository
from app.modules.subscriptions.service import SubscriptionService
from app.core.exceptions import TraceException
from app.core.redis import redis_client
from app.modules.identity.rate_limit import RateLimiter

logger = logging.getLogger("trace.calc.limits")

USAGE_METRIC = "calculation_runs"
RETRYABLE_CODES = frozenset({"RUN_IN_PROGRESS", "RUN_CONCURRENCY_LIMIT", "RUN_RATE_LIMITED"})

def _rate_keys(organization_id: UUID) -> tuple[tuple[str, int, int], ...]:
  return (
    (f"calc_run:{organization_id}:m", int(settings.calc_run_rate_limit_per_minute), 60),
    (f"calc_run:{organization_id}:h", int(settings.calc_run_rate_limit_per_hour), 3600),
  )

class CalcLimits:
  def __init__(self, session: AsyncSession, redis_client=None):
    self.session = session
    self.runs = CalculationRunRepository(session)
    self._redis = redis_client

  def _client(self):
    if self._redis is None:
      
      self._redis = redis_client
    return self._redis

  async def ensure_can_create(self, organization_id: UUID) -> None:
    await self._check_rate(organization_id)
    cap = int(settings.calc_max_concurrent_runs_per_org)
    if cap > 0:
      active = await self.runs.count_active_for_org(organization_id)
      if active >= cap:
        raise TraceException(
          f"Your company already has {active} calculation runs in progress (the limit is {cap}). "
          "Wait for one to finish and try again.", status_code=429, code="RUN_CONCURRENCY_LIMIT")

    try:
      await SubscriptionService(self.session).check_quota(organization_id, USAGE_METRIC)
    except TraceException as exc:
      if exc.code != "SUBSCRIPTION_NOT_FOUND":
        raise

  async def _check_rate(self, organization_id: UUID) -> None:
    try:
      limiter = RateLimiter(self._client())
      for key, limit, window in _rate_keys(organization_id):
        if limit <= 0:
          continue
        await limiter.check(key=key, limit=limit, window_seconds=window)
    except TraceException:
      raise TraceException("Too many calculation runs requested. Try again in a few minutes.",
        status_code=429, code="RUN_RATE_LIMITED")
    except Exception:
      logger.warning("run rate limiter unavailable; allowing the request", exc_info=True)

  async def record_run(self, organization_id: UUID) -> None:
    try:
      await SubscriptionService(self.session).increment_usage(organization_id, USAGE_METRIC)
      await self.session.commit()
    except Exception:
      await self.session.rollback()
      logger.warning("could not record calculation run usage", exc_info=True)

  async def snapshot(self, organization_id: UUID) -> dict:
    out: dict = {"quota": None, "concurrent": {"active": await self.runs.count_active_for_org(organization_id),
      "limit": int(settings.calc_max_concurrent_runs_per_org)}, "rate_limits": []}
    try:
      
      usage = await SubscriptionService(self.session).get_usage(organization_id)
      for m in usage.metrics:
        if m.metric == USAGE_METRIC:
          out["quota"] = {"used": m.used, "limit": m.limit, "remaining": m.remaining,
            "period_start": usage.period_start, "period_end": usage.period_end}
          
    except Exception:
      pass
    try:
      client = self._client()
      for key, limit, window in _rate_keys(organization_id):
        raw = await client.get(f"trace:ratelimit:{key}")
        ttl = await client.ttl(f"trace:ratelimit:{key}")
        used = int(raw) if raw else 0
        out["rate_limits"].append({"window_seconds": window, "limit": limit, "used": used,
          "remaining": max(limit - used, 0), "resets_in_seconds": ttl if ttl and ttl > 0 else 0})
    except Exception:
      pass
    return out
