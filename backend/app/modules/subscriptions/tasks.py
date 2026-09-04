from __future__ import annotations
import logging
from app.workers.celery_app import celery_app
import asyncio
from datetime import datetime, timezone
from app.core.database import WorkerSessionLocal, dispose_worker_engine
from app.modules.identity.models import Organization
from app.modules.subscriptions.service import SubscriptionService
from sqlalchemy import select
from app.dependencies.tenancy import scope_session_to_org

logger = logging.getLogger("trace.subscriptions.tasks")

@celery_app.task(name="app.modules.subscriptions.tasks.roll_expired_subscriptions_task")
def roll_expired_subscriptions_task() -> str:
  return asyncio.run(_roll_expired_subscriptions())

async def _roll_expired_subscriptions() -> str:
  now = datetime.now(timezone.utc)
  rolled = 0
  failed = 0

  try:
    async with WorkerSessionLocal() as session:
      result = await session.execute(select(Organization.id))
      org_ids = [row[0] for row in result.all()]

    for org_id in org_ids:
      async with WorkerSessionLocal() as session:
        try:
          await scope_session_to_org(session, org_id)
          service = SubscriptionService(session)
          outcome = await service.roll_subscription_if_expired(org_id, now)
          if outcome is not None:
            rolled += 1
        except Exception:
          failed += 1
          logger.exception(
            "subscription.period_roll_failed",
            extra={"organization_id": str(org_id)},
        )
  finally:
    await dispose_worker_engine()

  summary = f"rolled={rolled} failed={failed} checked={len(org_ids)}"
  logger.info("subscription.period_roll_complete", extra={"summary": summary})
  return summary