from __future__ import annotations
import asyncio
from app.modules.drawings_boq.calc_service import CalculationService
from app.core.database import WorkerSessionLocal, dispose_worker_engine
from uuid import UUID
from app.workers.celery_app import celery_app

@celery_app.task(
  name="app.modules.drawings_boq.calc_tasks.calculate_run_task",
  time_limit=1800,
  soft_time_limit=1500,
)
def calculate_run_task(run_id: str) -> str:
  async def _run() -> None:
    try:
      async with WorkerSessionLocal() as session:
        await CalculationService(session).execute_run(UUID(run_id))
    finally:
      await dispose_worker_engine()

  asyncio.run(_run())
  return "done"