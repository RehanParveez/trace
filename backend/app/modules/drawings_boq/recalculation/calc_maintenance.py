from __future__ import annotations
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.calc_repository import CalculationRunRepository
from datetime import timedelta, datetime, timezone
from app.modules.drawings_boq.calc_tasks import calculate_run_task
from app.modules.drawings_boq.boq_repository import BOQEngineRepository
from app.core.config import settings
from app.modules.drawings_boq.recalculation import calc_obs
from app.modules.drawings_boq.recalculation.export_task import render_export_task
from app.shared.storage import delete_object as _delete
from sqlalchemy import update
from app.modules.drawings_boq.models import ExportJob

logger = logging.getLogger("trace.calc.maintenance")

def _now() -> datetime:
  return datetime.now(timezone.utc)

async def recover_stale_runs(session: AsyncSession, send=None) -> dict:
  if send is None:
   
    send = lambda run_id: calculate_run_task.delay(str(run_id))
  repo = CalculationRunRepository(session)
  now = _now()
  stale = await repo.find_stale(now - timedelta(seconds=int(settings.calc_stale_heartbeat_seconds)),
    now - timedelta(seconds=int(settings.calc_queued_requeue_seconds)))
  report = {"requeued": 0, "failed": 0, "resent": 0, "checked": len(stale)}
  max_attempts = int(settings.calc_max_attempts)
  to_send = []
  for run in stale:
    if run.status == "QUEUED":
      if run.attempts + 1 >= max_attempts:
        await repo.mark_failed(run.id, "RUN_ENQUEUE_LOST", "The run was never picked up by a worker.")
        report["failed"] += 1
        code = "RUN_ENQUEUE_LOST"
      else:
        await repo.bump_queued(run.id)
        to_send.append(run.id)
        report["resent"] += 1
        code = None
    else:
      if run.attempts + 1 >= max_attempts:
        await repo.fail_running_stages(run.id, "worker stopped reporting")
        await repo.mark_failed(run.id, "RUN_STALE", "The worker stopped reporting and the attempt limit was reached.")
        await repo.clear_staged(run.id)
        report["failed"] += 1
        code = "RUN_STALE"
      else:
        await repo.reset_for_retry(run.id)
        to_send.append(run.id)
        report["requeued"] += 1
        code = None
    calc_obs.log_event("run_recovered" if code is None else "run_failed", run_id=run.id,
      organization_id=run.organization_id, engine_version=run.engine_version, failure_code=code, attempts=run.attempts,
      level=logging.WARNING)
  await session.commit()
  for run_id in to_send:
    try:
      send(run_id)
    except Exception:
      logger.warning("could not re-send run %s; the next sweep retries", run_id, exc_info=True)
  return report

async def purge_staging(session: AsyncSession) -> dict:
  cutoff = _now() - timedelta(days=int(settings.calc_staging_retention_days))
  out = await CalculationRunRepository(session).purge_staging(cutoff)
  await session.commit()
  calc_obs.log_event("staging_purged", **{f"purged_{k}": v for k, v in out.items()})
  return out

async def recover_exports(session: AsyncSession, send=None) -> dict:
  if send is None:
    send = lambda job_id: render_export_task.delay(str(job_id))
  repo = BOQEngineRepository(session)
  now = _now()
  jobs = await repo.stale_export_jobs(now - timedelta(minutes=10),
    now - timedelta(seconds=int(settings.export_time_limit_seconds) + 120))
  report = {"resent": 0, "failed": 0}
  to_send = []
  for job in jobs:
    if job.status == "QUEUED":
      to_send.append(job.id)
      report["resent"] += 1
    else:
      await repo.finish_export_job(job.id, "FAILED", error_code="EXPORT_STALE",
        error_message="The export worker stopped before finishing. Request the export again.")
      report["failed"] += 1
  await session.commit()
  for job_id in to_send:
    try:
      send(job_id)
    except Exception:
      logger.warning("could not re-send export %s", job_id, exc_info=True)
  return report

async def expire_export_files(session: AsyncSession, delete_object=None) -> dict:
  if delete_object is None:
    delete_object = _delete
  repo = BOQEngineRepository(session)
  jobs = await repo.expired_export_files(_now() - timedelta(days=int(settings.export_retention_days)))
  removed = 0
  for job in jobs:
    try:
      await asyncio.to_thread(delete_object, job.storage_key)
    except Exception:
      logger.warning("could not delete export file %s", job.storage_key, exc_info=True)
      continue
    await session.execute(update(ExportJob).where(ExportJob.id == job.id).values(storage_key=None))
    removed += 1
  await session.commit()
  return {"removed": removed}