from __future__ import annotations
import asyncio
from app.modules.drawings_boq.calc_service import CalculationService
from app.core.database import WorkerSessionLocal, dispose_worker_engine
from uuid import UUID
from app.workers.celery_app import celery_app
from app.core.exceptions import TraceException
from app.dependencies.tenancy import scope_session_as_platform_admin
from app.core.config import settings
from app.modules.drawings_boq.recalculation.calc_limits import RETRYABLE_CODES

@celery_app.task(
  name="app.modules.drawings_boq.calc_tasks.calculate_run_task",
  time_limit=int(settings.calc_time_limit_seconds),
  soft_time_limit=int(settings.calc_soft_time_limit_seconds),
  acks_late=True,
  reject_on_worker_lost=True,
)
def calculate_run_task(run_id: str) -> str:
  async def _run() -> None:
    try:
      async with WorkerSessionLocal() as session:
        await scope_session_as_platform_admin(session)   
        await CalculationService(session).execute_run(UUID(run_id))
    finally:
      await dispose_worker_engine()

  asyncio.run(_run())
  return "done"

@celery_app.task(
  name="app.modules.drawings_boq.calc_tasks.auto_run_task",
  max_retries=10,
  bind=True,
)

def auto_run_task(self, organization_id: str, project_id: str, user_id: str | None) -> str:

  async def _run() -> str:
    try:
      async with WorkerSessionLocal() as session:
        from app.dependencies.tenancy import scope_session_to_org
        await scope_session_to_org(session, UUID(organization_id))
        await CalculationService(session).request_run(
          UUID(organization_id), UUID(project_id), UUID(user_id) if user_id else None, None, None)
        return "requested"
    finally:
      await dispose_worker_engine()

  try:
    return asyncio.run(_run())
  except TraceException as exc:
    if exc.code in RETRYABLE_CODES:
      raise self.retry(countdown=120 if exc.code == "RUN_IN_PROGRESS" else 300)
    return f"skipped: {exc.code}"

def _maintenance(name: str):
  async def _run() -> dict:
    from app.modules.drawings_boq import calc_maintenance
    try:
      async with WorkerSessionLocal() as session:
        await scope_session_as_platform_admin(session)
        return await getattr(calc_maintenance, name)(session)
    finally:
      await dispose_worker_engine()
  return asyncio.run(_run())

@celery_app.task(name="app.modules.drawings_boq.calc_tasks.recover_stale_runs_task")
def recover_stale_runs_task() -> dict:
  return _maintenance("recover_stale_runs")

@celery_app.task(name="app.modules.drawings_boq.calc_tasks.recover_exports_task")
def recover_exports_task() -> dict:
  return _maintenance("recover_exports")

@celery_app.task(name="app.modules.drawings_boq.calc_tasks.purge_staging_task")
def purge_staging_task() -> dict:
  return _maintenance("purge_staging")

@celery_app.task(name="app.modules.drawings_boq.calc_tasks.expire_export_files_task")
def expire_export_files_task() -> dict:
  return _maintenance("expire_export_files")