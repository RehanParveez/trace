from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.models import CalculationRun, QuantityLedger, QuantitySolid, RunStageLog, StagedQuantityLedger, StagedQuantitySolid, LedgerDeduction, StagedLedgerDeduction
from uuid import UUID
from sqlalchemy import delete, func, insert, select, update

_ACTIVE = ("QUEUED", "RUNNING", "STAGED", "PROMOTED")
_CHUNK = 1000

def _now():
  return datetime.now(timezone.utc)

class CalculationRunRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, run: CalculationRun) -> CalculationRun:
    self.session.add(run)
    await self.session.flush()
    return run

  async def get_by_id_and_org(self, run_id: UUID, organization_id: UUID) -> CalculationRun | None:
    result = await self.session.execute(
      select(CalculationRun).where(CalculationRun.id == run_id, CalculationRun.organization_id == organization_id)
    )
    return result.scalar_one_or_none()

  async def get_completed_by_fingerprint(self, organization_id: UUID, fingerprint: str) -> CalculationRun | None:
    result = await self.session.execute(
      select(CalculationRun).where(
        CalculationRun.organization_id == organization_id,
        CalculationRun.fingerprint == fingerprint,
        CalculationRun.status == "COMPLETED",
      )
    )
    return result.scalar_one_or_none()

  async def get_active_for_project(self, organization_id: UUID, project_id: UUID) -> CalculationRun | None:
    result = await self.session.execute(
      select(CalculationRun).where(
        CalculationRun.organization_id == organization_id,
        CalculationRun.project_id == project_id,
        CalculationRun.status.in_(_ACTIVE),
      )
    )
    return result.scalars().first()

  async def claim_queued(self, run_id: UUID) -> CalculationRun | None:
    result = await self.session.execute(
      update(CalculationRun)
      .where(CalculationRun.id == run_id, CalculationRun.status == "QUEUED")
      .values(status="RUNNING", started_at=_now(), progress_pct=5)
      .returning(CalculationRun)
      .execution_options(synchronize_session=False)
    )
    return result.scalar_one_or_none()

  async def set_progress(self, run_id: UUID, pct: int, status: str | None = None) -> None:
    values: dict = {"progress_pct": pct}
    if status:
      values["status"] = status
    await self.session.execute(update(CalculationRun).where(CalculationRun.id == run_id).values(**values))

  async def mark_failed(self, run_id: UUID, code: str, message: str) -> None:
    await self.session.execute(
      update(CalculationRun)
      .where(CalculationRun.id == run_id, CalculationRun.status.in_(_ACTIVE))
      .values(status="FAILED", error_code=code, error_message=message[:2000], completed_at=_now())
    )

  async def complete(self, run_id: UUID, stats: dict) -> None:
    await self.session.execute(
      update(CalculationRun).where(CalculationRun.id == run_id)
      .values(status="COMPLETED", progress_pct=100, completed_at=_now(), stats=stats)
    )

  async def supersede_older_completed(self, organization_id: UUID, project_id: UUID, exclude_id: UUID,
    drawing_revision_ids: list[UUID]) -> None:
    await self.session.execute(
      update(CalculationRun)
      .where(
        CalculationRun.organization_id == organization_id,
        CalculationRun.project_id == project_id,
        CalculationRun.status == "COMPLETED",
        CalculationRun.id != exclude_id,
        CalculationRun.drawing_revision_ids == drawing_revision_ids,
    )
    .values(status="SUPERSEDED")
  )

  async def start_stage(self, run: CalculationRun, stage: str) -> None:
    self.session.add(RunStageLog(
      organization_id=run.organization_id, run_id=run.id, stage=stage, status="RUNNING", started_at=_now(),
    ))
    await self.session.flush()

  async def log_skipped(self, run: CalculationRun, stage: str, reason: str) -> None:
    now = _now()
    self.session.add(RunStageLog(
      organization_id=run.organization_id, run_id=run.id, stage=stage, status="SKIPPED",
      started_at=now, finished_at=now, counts={"reason": reason},
    ))
    await self.session.flush()

  async def finish_stage(self, run_id: UUID, stage: str, counts: dict) -> None:
    await self.session.execute(
      update(RunStageLog).where(RunStageLog.run_id == run_id, RunStageLog.stage == stage)
      .values(status="SUCCEEDED", finished_at=_now(), counts=counts)
    )

  async def fail_running_stages(self, run_id: UUID, error: str) -> None:
    await self.session.execute(
      update(RunStageLog).where(RunStageLog.run_id == run_id, RunStageLog.status == "RUNNING")
      .values(status="FAILED", finished_at=_now(), error=error[:2000])
    )

  async def list_stages(self, run_id: UUID, organization_id: UUID) -> list[RunStageLog]:
    result = await self.session.execute(
      select(RunStageLog)
      .where(RunStageLog.run_id == run_id, RunStageLog.organization_id == organization_id)
      .order_by(RunStageLog.started_at.asc())
    )
    return list(result.scalars().all())

  async def clear_staged(self, run_id: UUID) -> None:
    await self.session.execute(delete(StagedLedgerDeduction).where(StagedLedgerDeduction.run_id == run_id))
    await self.session.execute(delete(StagedQuantityLedger).where(StagedQuantityLedger.run_id == run_id))
    await self.session.execute(delete(StagedQuantitySolid).where(StagedQuantitySolid.run_id == run_id))

  async def stage_solids(self, rows: list[dict]) -> None:
    for i in range(0, len(rows), _CHUNK):
      await self.session.execute(insert(StagedQuantitySolid), rows[i:i + _CHUNK])

  async def stage_ledger(self, rows: list[dict]) -> None:
    for i in range(0, len(rows), _CHUNK):
      await self.session.execute(insert(StagedQuantityLedger), rows[i:i + _CHUNK])

  async def stage_deductions(self, rows: list[dict]) -> None:
    for i in range(0, len(rows), _CHUNK):
      await self.session.execute(insert(StagedLedgerDeduction), rows[i:i + _CHUNK])

  async def promote(self, run_id: UUID) -> dict:
    solid_cols = [c.name for c in QuantitySolid.__table__.columns]
    ledger_cols = [c.name for c in QuantityLedger.__table__.columns]
    s_src, l_src = StagedQuantitySolid.__table__, StagedQuantityLedger.__table__
    await self.session.execute(
      insert(QuantitySolid.__table__).from_select(
        solid_cols, select(*[s_src.c[n] for n in solid_cols]).where(s_src.c.run_id == run_id))
    )
    await self.session.execute(
      insert(QuantityLedger.__table__).from_select(
        ledger_cols, select(*[l_src.c[n] for n in ledger_cols]).where(l_src.c.run_id == run_id))
    )
    ded_cols = [c.name for c in LedgerDeduction.__table__.columns]
    d_src = StagedLedgerDeduction.__table__
    await self.session.execute(
      insert(LedgerDeduction.__table__).from_select(
        ded_cols, select(*[d_src.c[n] for n in ded_cols]).where(d_src.c.run_id == run_id))
    )
    deductions = (await self.session.execute(
      select(func.count()).select_from(LedgerDeduction).where(LedgerDeduction.run_id == run_id))).scalar_one()
    solids = (await self.session.execute(
      select(func.count()).select_from(QuantitySolid).where(QuantitySolid.run_id == run_id))).scalar_one()
    ledger = (await self.session.execute(
      select(func.count()).select_from(QuantityLedger).where(QuantityLedger.run_id == run_id))).scalar_one()
    return {"solids": solids, "ledger_rows": ledger, "deductions": deductions}

  async def list_solids(self, run_id: UUID, organization_id: UUID, *, limit: int, after: UUID | None = None,
    role: str | None = None, level_id: UUID | None = None) -> list[QuantitySolid]:
    stmt = select(QuantitySolid).where(QuantitySolid.run_id == run_id, QuantitySolid.organization_id == organization_id)
    if role:
      stmt = stmt.where(QuantitySolid.role == role)
    if level_id:
      stmt = stmt.where(QuantitySolid.level_id == level_id)
    if after:
      stmt = stmt.where(QuantitySolid.id > after)
    result = await self.session.execute(stmt.order_by(QuantitySolid.id.asc()).limit(limit + 1))
    return list(result.scalars().all())

  async def list_ledger(self, run_id: UUID, organization_id: UUID, *, limit: int, after: UUID | None = None,
    work_item_code: str | None = None, level_id: UUID | None = None) -> list[QuantityLedger]:
    stmt = select(QuantityLedger).where(QuantityLedger.run_id == run_id, QuantityLedger.organization_id == organization_id)
    if work_item_code:
      stmt = stmt.where(QuantityLedger.work_item_code == work_item_code)
    if level_id:
      stmt = stmt.where(QuantityLedger.level_id == level_id)
    if after:
      stmt = stmt.where(QuantityLedger.id > after)
    result = await self.session.execute(stmt.order_by(QuantityLedger.id.asc()).limit(limit + 1))
    return list(result.scalars().all())

  async def list_deductions(self, run_id: UUID, organization_id: UUID, *, limit: int, after: UUID | None = None,
    from_solid_id: UUID | None = None, deduction_type: str | None = None) -> list[LedgerDeduction]:
    stmt = select(LedgerDeduction).where(
      LedgerDeduction.run_id == run_id, LedgerDeduction.organization_id == organization_id)
    if from_solid_id:
      stmt = stmt.where(LedgerDeduction.from_solid_id == from_solid_id)
    if deduction_type:
      stmt = stmt.where(LedgerDeduction.deduction_type == deduction_type)
    if after:
      stmt = stmt.where(LedgerDeduction.id > after)
    result = await self.session.execute(stmt.order_by(LedgerDeduction.id.asc()).limit(limit + 1))
    return list(result.scalars().all())