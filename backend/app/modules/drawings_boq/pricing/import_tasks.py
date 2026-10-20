from __future__ import annotations
import asyncio
import logging
from uuid import UUID
from app.modules.drawings_boq.pricing.import_service import RateImportService
from app.core.database import WorkerSessionLocal, dispose_worker_engine
from app.workers.celery_app import celery_app
from app.dependencies.tenancy import scope_session_to_org

logger = logging.getLogger("trace.pricing.import_tasks")

async def process_import(org_id: UUID, import_id: UUID, session_factory=None, store=None) -> str:
  """Reads the stored schedule into review rows. The organisation is passed explicitly and the session is scoped to it before any query."""
  factory = session_factory or WorkerSessionLocal
  async with factory() as session:
    await scope_session_to_org(session, org_id)
    imp = await RateImportService(session, store).process(org_id, import_id)
    return imp.status

@celery_app.task(name="app.modules.drawings_boq.pricing.import_tasks.parse_rate_import_task", time_limit=1800, soft_time_limit=1650)
def parse_rate_import_task(org_id: str, import_id: str) -> str:
  async def _run() -> str:
    try:
      return await process_import(UUID(org_id), UUID(import_id))
    except Exception:
      logger.exception("rate import %s failed", import_id)
      raise
    finally:
      await dispose_worker_engine()
  return asyncio.run(_run())
