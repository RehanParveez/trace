from __future__ import annotations
import logging
from app.workers.celery_app import celery_app
import asyncio
from datetime import datetime, time, timezone
from uuid import UUID
from zoneinfo import ZoneInfo
from app.modules.notifications.service import NotificationService
from app.modules.alerts.service import KIND_PERMISSION, AlertsService
from app.shared.timeutils import today_local
from app.modules.notifications.models import Notification, NotificationType
from sqlalchemy import select
from app.core.config import settings
from app.modules.identity.models import Organization
from app.core.database import WorkerSessionLocal, dispose_worker_engine
from app.dependencies.tenancy import scope_session_to_org

logger = logging.getLogger("trace.alerts.tasks")

@celery_app.task(name="app.modules.alerts.tasks.send_attention_digests_task")
def send_attention_digests_task() -> str:
  return asyncio.run(_send_attention_digests())

def _local_midnight_utc() -> datetime:
  tz = ZoneInfo(settings.default_timezone)
  return datetime.combine(today_local(), time.min, tzinfo=tz).astimezone(timezone.utc)

async def send_digest_for_org(session, organization_id: UUID) -> int:
  notifications = NotificationService(session)
  items = await AlertsService(session).get_attention(organization_id, None)
  if not items:
    return 0
  by_user: dict[UUID, list[dict]] = {}
  for item in items:
    for user_id in await notifications.repository.get_user_ids_with_permission(organization_id, KIND_PERMISSION[item["kind"]]):
      by_user.setdefault(user_id, []).append(item)
  already = set((await session.execute(
    select(Notification.user_id).where(
      Notification.organization_id == organization_id, Notification.type == NotificationType.ATTENTION_DIGEST,
      Notification.created_at >= _local_midnight_utc(),
    )
    
  )).scalars().all())
  sent = 0
  for user_id, user_items in by_user.items():
    if user_id in already:
      continue
    total = sum(i["count"] for i in user_items)
    await notifications.notify_user(
      organization_id, user_id, NotificationType.ATTENTION_DIGEST,
      f"{total} thing(s) need your attention today",
      "; ".join(f"{i['kind'].replace('_', ' ').lower()}: {i['count']}" for i in user_items), "/dashboard", commit=False,
    )
    sent += 1
  await session.commit()
  return sent

async def _send_attention_digests() -> str:
  sent = failed = 0
  try:
    async with WorkerSessionLocal() as session:
      org_ids = [row[0] for row in (await session.execute(select(Organization.id))).all()]
    for org_id in org_ids:
      async with WorkerSessionLocal() as session:
        try:
          await scope_session_to_org(session, org_id)
          sent += await send_digest_for_org(session, org_id)
        except Exception:
          failed += 1
          logger.exception("alerts.digest_failed", extra={"organization_id": str(org_id)})
  finally:
    await dispose_worker_engine()
  return f"sent={sent} failed={failed} orgs={len(org_ids)}"