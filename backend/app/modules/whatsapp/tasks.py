from __future__ import annotations
import asyncio
from uuid import UUID
from app.core.database import AsyncSessionLocal
from app.workers.celery_app import celery_app

@celery_app.task(
  name="app.modules.whatsapp.tasks.process_whatsapp_photo_task",
  time_limit=180,
  soft_time_limit=150,
)
def process_whatsapp_photo_task(message_id: str) -> str:
  asyncio.run(_process(UUID(message_id)))
  return "processed"

async def _process(message_id: UUID) -> None:
  from app.modules.whatsapp.service import WhatsAppService
  async with AsyncSessionLocal() as session:
    service = WhatsAppService(session)
    await service.process_photo_message(message_id)