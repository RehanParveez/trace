from __future__ import annotations
import asyncio
import logging
from datetime import timedelta, datetime, timezone
from app.workers.celery_app import celery_app
from uuid import UUID
from app.dependencies.tenancy import scope_session_as_dispatch, scope_session_to_org
from app.modules.privacy.models import DataExportJob, ExportStatus, DeletionStatus, OrganizationDeletionRequest
from sqlalchemy import select, update
from app.core.database import WorkerSessionLocal, dispose_worker_engine
from app.modules.privacy.exporter import OrgExporter
from app.modules.privacy.storage_ops import default_store
from app.modules.privacy.purge import OrgPurger

logger = logging.getLogger("trace.privacy.tasks")
_STALE_QUEUED = timedelta(minutes=10)
_STALE_RUNNING = timedelta(hours=2)
_STALE_DELETING = timedelta(minutes=45)

def _now() -> datetime:
  return datetime.now(timezone.utc)

@celery_app.task(name="app.modules.privacy.tasks.run_data_export_task", time_limit=3600, soft_time_limit=3300)
def run_data_export_task(job_id: str) -> str:
  async def _run() -> str:
    try:
      return await claim_and_export(UUID(job_id))
    finally:
      await dispose_worker_engine()
  return asyncio.run(_run())

async def claim_and_export(job_id: UUID, session_factory=None, store=None) -> str:
  factory = session_factory or WorkerSessionLocal
  async with factory() as session:
    await scope_session_as_dispatch(session)
    row = (await session.execute(
      update(DataExportJob).where(DataExportJob.id == job_id, DataExportJob.status == ExportStatus.QUEUED.value)
      .values(status=ExportStatus.RUNNING.value, started_at=_now()).returning(DataExportJob.organization_id))).first()
    await session.commit()
    if row is None:
      return "skipped"
    await scope_session_to_org(session, row[0])
    job = await OrgExporter(session, store or default_store).run(job_id)
    return job.status

@celery_app.task(name="app.modules.privacy.tasks.execute_deletion_task", time_limit=7200, soft_time_limit=6900)
def execute_deletion_task(request_id: str) -> str:
  async def _run() -> str:
    try:
      return await claim_and_delete(UUID(request_id))
    finally:
      await dispose_worker_engine()
  return asyncio.run(_run())

async def claim_and_delete(request_id: UUID, session_factory=None, store=None) -> str:
  factory = session_factory or WorkerSessionLocal
  now = _now()
  org_id = None
  async with factory() as session:
    await scope_session_as_dispatch(session)
    R = OrganizationDeletionRequest
    row = (await session.execute(
      update(R).where(R.id == request_id, (
        ((R.status == DeletionStatus.PENDING.value) & (R.scheduled_for <= now)) |
        ((R.status == DeletionStatus.EXECUTING.value) & (R.executed_at < now - _STALE_DELETING))))
      .values(status=DeletionStatus.EXECUTING.value, executed_at=now, error_message=None).returning(R.organization_id))).first()
    await session.commit()
    if row is None:
      return "skipped"
    org_id = row[0]
    try:
      await scope_session_to_org(session, org_id)
      await OrgPurger(session, store or default_store).purge(org_id)
      return "erased"
    except Exception as exc: 
      logger.exception("erasure of organization %s failed", org_id)
      await session.rollback()
      await scope_session_as_dispatch(session)
      await session.execute(update(R).where(R.id == request_id).values(status=DeletionStatus.FAILED.value, error_message=str(exc)[:900]))
      await session.commit()
      return "failed"

@celery_app.task(name="app.modules.privacy.tasks.privacy_sweep_task")
def privacy_sweep_task() -> dict:
  async def _run() -> dict:
    try:
      return await sweep()
    finally:
      await dispose_worker_engine()
  return asyncio.run(_run())

async def sweep(session_factory=None, store=None, send_export=None, send_deletion=None) -> dict:
  factory = session_factory or WorkerSessionLocal
  store = store or default_store
  send_export = send_export or (lambda i: run_data_export_task.delay(str(i)))
  send_deletion = send_deletion or (lambda i: execute_deletion_task.delay(str(i)))
  now = _now()
  
  report = {"requeued": 0, "failed": 0, "expired": 0, "deletions": 0}
  async with factory() as session:
    await scope_session_as_dispatch(session)
    J, R = DataExportJob, OrganizationDeletionRequest
    queued = (await session.execute(select(J.id).where(J.status == ExportStatus.QUEUED.value, J.created_at < now - _STALE_QUEUED))).scalars().all()
    stuck = await session.execute(update(J).where(J.status == ExportStatus.RUNNING.value, J.started_at < now - _STALE_RUNNING)
      .values(status=ExportStatus.FAILED.value, error_message="The export worker stopped before finishing. Request the export again.", finished_at=now))
    report["failed"] = stuck.rowcount or 0
    due_exports = (await session.execute(select(J.id, J.storage_key).where(J.status == ExportStatus.COMPLETED.value, J.expires_at.is_not(None), J.expires_at < now))).all()
    
    for job_id, key in due_exports:
      try:
        if key:
          await asyncio.to_thread(store.delete, key)
      except Exception:  
        logger.warning("could not delete expired export file %s", key, exc_info=True)
        continue
      await session.execute(update(J).where(J.id == job_id).values(status=ExportStatus.EXPIRED.value, storage_key=None))
      report["expired"] += 1
    deletions = (await session.execute(select(R.id).where(
      ((R.status == DeletionStatus.PENDING.value) & (R.scheduled_for <= now)) |
      ((R.status == DeletionStatus.EXECUTING.value) & (R.executed_at < now - _STALE_DELETING))))).scalars().all()
    await session.commit()
    
  for job_id in queued:
    try:
      send_export(job_id)
      report["requeued"] += 1
    except Exception:  
      logger.warning("could not queue export %s", job_id, exc_info=True)
  for request_id in deletions:
    try:
      send_deletion(request_id)
      report["deletions"] += 1
    except Exception:  
      logger.warning("could not queue erasure %s", request_id, exc_info=True)
  return report
