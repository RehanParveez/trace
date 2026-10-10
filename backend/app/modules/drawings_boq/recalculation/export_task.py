from __future__ import annotations
from app.workers.celery_app import celery_app
import asyncio
from uuid import UUID
from app.core.config import settings
from app.core.database import WorkerSessionLocal, dispose_worker_engine
from app.dependencies.tenancy import scope_session_as_platform_admin

@celery_app.task(
  name="app.modules.drawings_boq.recalculation.export_task.render_export_task",
  time_limit=int(settings.export_time_limit_seconds),
  soft_time_limit=int(settings.export_soft_time_limit_seconds),
)
def render_export_task(job_id: str) -> str:
  from app.modules.drawings_boq.boq_service import BOQEngineService
  async def _run() -> str:
    
    try:
      async with WorkerSessionLocal() as session:
        await scope_session_as_platform_admin(session)
        return await BOQEngineService(session).run_export_job(UUID(job_id))
    finally:
      await dispose_worker_engine()

  return asyncio.run(_run())