from __future__ import annotations
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.drawings_boq.models import CalculationRun, QuantityLedger, RunCheckpoint
from sqlalchemy import and_, select
from fastapi import HTTPException
from app.modules.drawings_boq.lab import history as H

log = logging.getLogger(__name__)

DONE = ("COMPLETED", "PROMOTED")

class RunHistoryService:

  def __init__(self, session: AsyncSession):
    self.session = session

  async def _run(self, org: UUID, run_id: UUID) -> CalculationRun:
    run = (await self.session.execute(select(CalculationRun).where(CalculationRun.id == run_id, CalculationRun.organization_id == org))).scalar_one_or_none()
    if run is None:
      raise HTTPException(404, {"code": "RUN_NOT_FOUND", "message": "Calculation run not found."})
    return run

  async def _put(self, org: UUID, run: CalculationRun, user_id: UUID | None, kind: str, label: str, payload: dict) -> None:
    row = (await self.session.execute(select(RunCheckpoint).where(RunCheckpoint.run_id == run.id, RunCheckpoint.kind == kind, RunCheckpoint.label == label))).scalar_one_or_none()
    if row is None:
      self.session.add(RunCheckpoint(organization_id=org, project_id=run.project_id, run_id=run.id, kind=kind, label=label, payload=payload, created_by_user_id=user_id))
    else:
      row.payload = payload
      row.created_by_user_id = user_id
    await self.session.flush()

  async def record_compare(self, org: UUID, user_id: UUID | None, run_id: UUID, scope: str, filename: str | None, result: dict) -> None:
    try:
      run = await self._run(org, run_id)
      await self._put(org, run, user_id, "COMPARE", f"{scope}:{(filename or 'bill')[:150]}", H.compare_payload(result, scope))
      await self.session.commit()
    except Exception:
      await self.session.rollback()
      log.exception("The comparison of run %s could not be recorded", run_id)

  async def _ledger_rows(self, org: UUID, run_id: UUID) -> list[dict]:
    result = await self.session.execute(
      select(QuantityLedger.work_item_code, QuantityLedger.quantity_net, QuantityLedger.unit, QuantityLedger.trace)
      .where(QuantityLedger.run_id == run_id, QuantityLedger.organization_id == org))
    return [{"work_item_code": w, "quantity": q, "unit": u, "trace": t} for w, q, u, t in result.all()]

  async def history(self, org: UUID, user_id: UUID | None, run_id: UUID) -> dict:
    run = await self._run(org, run_id)
    have = (await self.session.execute(select(RunCheckpoint.id).where(RunCheckpoint.run_id == run.id, RunCheckpoint.kind == "RANGE"))).first()
    if have is None and run.status in DONE:
      rows = await self._ledger_rows(org, run.id)
      
      if rows:
        await self._put(org, run, user_id, "RANGE", "", H.range_payload(rows))
        await self.session.commit()
    found = (await self.session.execute(
      select(RunCheckpoint, CalculationRun.created_at)
      .join(CalculationRun, and_(CalculationRun.id == RunCheckpoint.run_id, CalculationRun.organization_id == RunCheckpoint.organization_id))
      .where(RunCheckpoint.organization_id == org, RunCheckpoint.project_id == run.project_id))).all()
    points = [{"id": str(c.id), "run_id": c.run_id, "kind": c.kind, "label": c.label, "created_at": c.created_at.isoformat(),
      "run_created_at": created.isoformat(), "payload": c.payload} for c, created in found]
    return {"project_id": str(run.project_id), "current_run_id": str(run_id), **H.trend(points)}
