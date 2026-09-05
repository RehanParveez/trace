from __future__ import annotations
import asyncio
from uuid import UUID
from app.core.database import WorkerSessionLocal, dispose_worker_engine
from app.workers.celery_app import celery_app
from app.dependencies.tenancy import scope_session_as_platform_admin, scope_session_to_org

@celery_app.task(
  name="app.modules.whatsapp.tasks.process_whatsapp_photo_task",
  time_limit=300,
  soft_time_limit=270,
)

def process_whatsapp_photo_task(message_id: str) -> str:
  async def _run() -> None:
    try:
      await _process(UUID(message_id))
    finally:
      await dispose_worker_engine()
  asyncio.run(_run())
  return "processed"

async def _process(message_id: UUID) -> None:
  from app.modules.whatsapp.service import WhatsAppService

  async with WorkerSessionLocal() as session:
    service = WhatsAppService(session)
    await scope_session_as_platform_admin(session)
    message = await service.messages.get_by_id(message_id)
    if message is None:
      return

    await scope_session_to_org(session, message.organization_id)
    await service.process_photo_message(message_id)