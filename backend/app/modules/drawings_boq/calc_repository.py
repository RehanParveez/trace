from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.models import ( CalculationRun, RunStageLog, DrawingElement, QuantityLedger, QuantitySolid, RunDependencyEdge, RunElementState, StagedQuantityLedger, StagedQuantitySolid,
 LedgerDeduction, StagedLedgerDeduction, RebarBarMark, StagedRebarBarMark 
)
import json
from uuid import UUID, uuid5
from decimal import Decimal
from sqlalchemy import Integer, and_, delete, func, insert, or_, select, update
from app.core.config import settings
from app.engine.measure.incremental import Baseline, StoredElement, baseline_from_run
from app.engine.measure.material import wall_material_class
from app.engine.measure.models import ModelElement

_ACTIVE = ("QUEUED", "RUNNING", "STAGED", "PROMOTED")
_CHUNK = 1000

def _chunk() -> int:
  return max(int(settings.calc_stage_chunk_rows), 1)

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
      .values(status="RUNNING", started_at=_now(), heartbeat_at=_now(), progress_pct=5)
      .returning(CalculationRun)
      .execution_options(synchronize_session=False)
    )
    return result.scalar_one_or_none()

  async def fail_stale(self, project_id: UUID, older_than: datetime) -> None:
    await self.session.execute(
      update(CalculationRun).where(
        CalculationRun.project_id == project_id,
        ((CalculationRun.status.in_(("RUNNING", "STAGED"))
          & (func.coalesce(CalculationRun.heartbeat_at, CalculationRun.started_at) < older_than))
         | ((CalculationRun.status == "QUEUED") & (CalculationRun.created_at < older_than))),
      ).values(status="FAILED", error_code="RUN_STALE",
      error_message="The worker did not finish within the time limit.", completed_at=_now())
    )

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

  async def finish_stage(self, run_id: UUID, stage: str, counts: dict, duration_ms: int | None = None,
    peak_rss_mb: int | None = None) -> None:
    await self.session.execute(
      update(RunStageLog).where(RunStageLog.run_id == run_id, RunStageLog.stage == stage)
      .values(status="SUCCEEDED", finished_at=_now(), counts=counts, duration_ms=duration_ms, peak_rss_mb=peak_rss_mb)
    )

  async def fail_running_stages(self, run_id: UUID, error: str) -> None:
    now = _now()
    await self.session.execute(
      update(RunStageLog).where(RunStageLog.run_id == run_id, RunStageLog.status == "RUNNING")
      .values(status="FAILED", finished_at=now, error=error[:2000],
        duration_ms=func.floor(func.extract("epoch", now - RunStageLog.started_at) * 1000).cast(Integer))
    )

  async def list_stages(self, run_id: UUID, organization_id: UUID) -> list[RunStageLog]:
    result = await self.session.execute(
      select(RunStageLog)
      .where(RunStageLog.run_id == run_id, RunStageLog.organization_id == organization_id)
      .order_by(RunStageLog.started_at.asc())
    )
    return list(result.scalars().all())

  async def clear_staged(self, run_id: UUID) -> None:
    await self.session.execute(delete(StagedRebarBarMark).where(StagedRebarBarMark.run_id == run_id))
    await self.session.execute(delete(StagedLedgerDeduction).where(StagedLedgerDeduction.run_id == run_id))
    await self.session.execute(delete(StagedQuantityLedger).where(StagedQuantityLedger.run_id == run_id))
    await self.session.execute(delete(StagedQuantitySolid).where(StagedQuantitySolid.run_id == run_id))

  async def stage_solids(self, rows: list[dict]) -> None:
    for i in range(0, len(rows), _chunk()):
      await self.session.execute(insert(StagedQuantitySolid), rows[i:i + _chunk()])

  async def stage_ledger(self, rows: list[dict]) -> None:
    for i in range(0, len(rows), _chunk()):
      await self.session.execute(insert(StagedQuantityLedger), rows[i:i + _chunk()])

  async def stage_deductions(self, rows: list[dict]) -> None:
    for i in range(0, len(rows), _chunk()):
      await self.session.execute(insert(StagedLedgerDeduction), rows[i:i + _chunk()])
      
  async def stage_bar_marks(self, rows: list[dict]) -> None:
    for i in range(0, len(rows), _chunk()):
      await self.session.execute(insert(StagedRebarBarMark), rows[i:i + _chunk()])

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
    mark_cols = [c.name for c in RebarBarMark.__table__.columns]
    m_src = StagedRebarBarMark.__table__
    await self.session.execute(
      insert(RebarBarMark.__table__).from_select(
        mark_cols, select(*[m_src.c[n] for n in mark_cols]).where(m_src.c.run_id == run_id))
    )
    bar_marks = (await self.session.execute(
      select(func.count()).select_from(RebarBarMark).where(RebarBarMark.run_id == run_id))).scalar_one()
    deductions = (await self.session.execute(
      select(func.count()).select_from(LedgerDeduction).where(LedgerDeduction.run_id == run_id))).scalar_one()
    solids = (await self.session.execute(
      select(func.count()).select_from(QuantitySolid).where(QuantitySolid.run_id == run_id))).scalar_one()
    ledger = (await self.session.execute(
      select(func.count()).select_from(QuantityLedger).where(QuantityLedger.run_id == run_id))).scalar_one()
    return {"solids": solids, "ledger_rows": ledger, "deductions": deductions, "bar_marks": bar_marks}

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
  
  async def list_bar_marks(self, run_id: UUID, organization_id: UUID, *, limit: int, after: UUID | None = None,
    solid_id: UUID | None = None, provenance: str | None = None, role: str | None = None) -> list[RebarBarMark]:
    stmt = select(RebarBarMark).where(RebarBarMark.run_id == run_id, RebarBarMark.organization_id == organization_id)
    if solid_id:
      stmt = stmt.where(RebarBarMark.solid_id == solid_id)
    if provenance:
      stmt = stmt.where(RebarBarMark.provenance == provenance)
    if role:
      stmt = stmt.where(RebarBarMark.role == role)
    if after:
      stmt = stmt.where(RebarBarMark.id > after)
    result = await self.session.execute(stmt.order_by(RebarBarMark.id.asc()).limit(limit + 1))
    return list(result.scalars().all())
  
  async def merge_stats(self, run_id: UUID, patch: dict) -> None:
    row = (await self.session.execute(select(CalculationRun).where(CalculationRun.id == run_id))).scalar_one_or_none()
    if row is not None:
      row.stats = {**(row.stats or {}), **patch}
      await self.session.flush()

  async def touch_heartbeat(self, run_id: UUID, attempt: int) -> bool:
    result = await self.session.execute(
      update(CalculationRun)
      .where(CalculationRun.id == run_id, CalculationRun.status.in_(("RUNNING", "STAGED")),
        CalculationRun.attempts == attempt)
      .values(heartbeat_at=_now()).returning(CalculationRun.id)
    )
    return result.scalar_one_or_none() is not None

  async def set_metrics(self, run_id: UUID, patch: dict, **columns) -> None:
    row = (await self.session.execute(select(CalculationRun).where(CalculationRun.id == run_id))).scalar_one_or_none()
    if row is not None:
      row.metrics = {**(row.metrics or {}), **json.loads(json.dumps(patch, default=str))}
      for name, value in columns.items():
        setattr(row, name, value)
      await self.session.flush()

  async def get_attempt_state(self, run_id: UUID):
    row = (await self.session.execute(
      select(CalculationRun.attempts, CalculationRun.status).where(CalculationRun.id == run_id))).first()
    return (row.attempts, row.status) if row is not None else None

  async def count_active_for_org(self, organization_id: UUID) -> int:
    return (await self.session.execute(
      select(func.count()).select_from(CalculationRun).where(
        CalculationRun.organization_id == organization_id, CalculationRun.status.in_(_ACTIVE))
    )).scalar_one()

  async def reset_for_retry(self, run_id: UUID) -> None:
    await self.clear_staged(run_id)
    await self.session.execute(delete(RunStageLog).where(RunStageLog.run_id == run_id))
    await self.session.execute(
      update(CalculationRun).where(CalculationRun.id == run_id)
      .values(status="QUEUED", progress_pct=0, started_at=None, heartbeat_at=None, attempts=CalculationRun.attempts + 1,
        error_code=None, error_message=None)
    )

  async def bump_queued(self, run_id: UUID) -> None:
    await self.session.execute(
      update(CalculationRun).where(CalculationRun.id == run_id, CalculationRun.status == "QUEUED")
      .values(attempts=CalculationRun.attempts + 1)
    )

  async def find_stale(self, heartbeat_before: datetime, queued_before: datetime, limit: int = 200) -> list[CalculationRun]:
    result = await self.session.execute(
      select(CalculationRun).where(
        or_(
          and_(CalculationRun.status.in_(("RUNNING", "STAGED")),
            func.coalesce(CalculationRun.heartbeat_at, CalculationRun.started_at, CalculationRun.created_at) < heartbeat_before),
          and_(CalculationRun.status == "QUEUED", CalculationRun.updated_at < queued_before),
        )
      ).order_by(CalculationRun.created_at.asc()).limit(limit)
    )
    return list(result.scalars().all())

  async def stream_model_elements(self, drawing_id: UUID, organization_id: UUID, fetch_rows: int | None = None):
    e = DrawingElement
    stmt = select(
      e.id, e.ifc_global_id, e.ifc_type, e.structural_role, e.level_id, e.geometry_kind, e.profile, e.placement,
      e.volume_mm3, e.bbox_min_x_mm, e.bbox_min_y_mm, e.bbox_min_z_mm, e.bbox_max_x_mm, e.bbox_max_y_mm,
      e.bbox_max_z_mm, e.classification_confidence, e.normalization_status, e.raw_material_text,
    ).where(e.drawing_id == drawing_id, e.organization_id == organization_id).execution_options(
      yield_per=fetch_rows or int(settings.calc_element_fetch_rows))
    result = await self.session.stream(stmt)
    
    async for r in result:
      lo = (r.bbox_min_x_mm, r.bbox_min_y_mm, r.bbox_min_z_mm)
      hi = (r.bbox_max_x_mm, r.bbox_max_y_mm, r.bbox_max_z_mm)
      yield ModelElement(
        id=r.id, ifc_type=r.ifc_type, role=r.structural_role or "UNKNOWN", level_id=r.level_id,
        geometry_kind=r.geometry_kind, profile=r.profile, placement=r.placement, volume_mm3=r.volume_mm3,
        bbox_min_mm=lo if all(v is not None for v in lo) else None,
        bbox_max_mm=hi if all(v is not None for v in hi) else None,
        classification_confidence=r.classification_confidence if r.classification_confidence is not None else Decimal("0"),
        normalization_status=r.normalization_status, ifc_global_id=r.ifc_global_id,
        material_class=wall_material_class(r.structural_role, r.raw_material_text),
      )

  async def find_baseline_run(self, organization_id: UUID, project_id: UUID, signature: str,
    exclude_run_id: UUID) -> CalculationRun | None:
    result = await self.session.execute(
      select(CalculationRun).where(
        CalculationRun.organization_id == organization_id, CalculationRun.project_id == project_id,
        CalculationRun.state_available.is_(True), CalculationRun.alloc_signature == signature,
        CalculationRun.status.in_(("COMPLETED", "SUPERSEDED")), CalculationRun.id != exclude_run_id,
      ).order_by(CalculationRun.completed_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()

  async def load_baseline(self, run: CalculationRun) -> Baseline:
    s = RunElementState
    rows = (await self.session.execute(
      select(s.element_key, s.element_id, s.solid_id, s.alloc_hash, s.participating, s.approximate, s.warnings,
        s.owned_mm3, s.bounds).where(s.run_id == run.id)
    )).all()
    stored = [StoredElement(
      key=r.element_key, element_id=r.element_id, solid_id=r.solid_id, alloc_hash=r.alloc_hash,
      participating=r.participating, approximate=r.approximate, warnings=tuple(r.warnings or ()),
      owned_mm3=r.owned_mm3 or 0.0, bounds=tuple(r.bounds) if r.bounds else None) for r in rows]
    g = RunDependencyEdge
    edge_rows = (await self.session.execute(
      select(g.key_a, g.key_b, g.element_a_id, g.element_b_id, g.overlap_mm3).where(g.run_id == run.id)
    )).all()
    edges = [(r.key_a, r.key_b, r.element_a_id, r.element_b_id, r.overlap_mm3) for r in edge_rows]
    d = LedgerDeduction
    deductions = (await self.session.execute(
      select(d.from_solid_id, d.to_solid_id, d.deduction_type, d.quantity, d.unit, d.rule_code, d.geometry,
        d.explanation).where(d.run_id == run.id, d.to_solid_id.is_not(None), d.deduction_type != "VOID_DEDUCTION")
    )).all()
    return baseline_from_run(run.id, run.alloc_signature or "", stored, edges, deductions)

  async def persist_state(self, run: CalculationRun, elements: list, edges: list) -> None:
    rows = [{
      "id": uuid5(run.id, f"state|{e.key}"), "organization_id": run.organization_id, "run_id": run.id,
      "element_key": e.key, "element_id": e.element_id, "solid_id": e.solid_id, "alloc_hash": e.alloc_hash,
      "participating": e.participating, "approximate": e.approximate, "warnings": list(e.warnings),
      "owned_mm3": e.owned_mm3, "bounds": list(e.bounds) if e.bounds else None,
    } for e in elements]
    
    for i in range(0, len(rows), _chunk()):
      await self.session.execute(insert(RunElementState), rows[i:i + _chunk()])
    edge_rows = [{
      "id": uuid5(run.id, f"edge|{ka}|{kb}"), "organization_id": run.organization_id, "run_id": run.id,
      "key_a": ka, "key_b": kb, "element_a_id": ea, "element_b_id": eb, "overlap_mm3": vol,
    } for ka, kb, ea, eb, vol in edges]
    for i in range(0, len(edge_rows), _chunk()):
      await self.session.execute(insert(RunDependencyEdge), edge_rows[i:i + _chunk()])

  async def prune_state(self, organization_id: UUID, project_id: UUID, keep: int) -> int:
    ids = (await self.session.execute(
      select(CalculationRun.id).where(
        CalculationRun.organization_id == organization_id, CalculationRun.project_id == project_id,
        CalculationRun.state_available.is_(True),
      ).order_by(CalculationRun.completed_at.desc().nullslast(), CalculationRun.created_at.desc()).offset(max(keep, 1))
    )).scalars().all()
    if not ids:
      return 0
    await self.session.execute(delete(RunDependencyEdge).where(RunDependencyEdge.run_id.in_(ids)))
    await self.session.execute(delete(RunElementState).where(RunElementState.run_id.in_(ids)))
    await self.session.execute(update(CalculationRun).where(CalculationRun.id.in_(ids)).values(state_available=False))
    return len(ids)

  async def touching(self, run_id: UUID, organization_id: UUID, element_id: UUID):
    g = RunDependencyEdge
    rows = (await self.session.execute(
      select(g.element_a_id, g.element_b_id, g.overlap_mm3).where(
        g.run_id == run_id, g.organization_id == organization_id,
        or_(g.element_a_id == element_id, g.element_b_id == element_id))
    )).all()
    return [(r.element_b_id if r.element_a_id == element_id else r.element_a_id, r.overlap_mm3) for r in rows]

  async def has_element_state(self, run_id: UUID, organization_id: UUID, element_id: UUID) -> bool:
    s = RunElementState
    return (await self.session.execute(
      select(func.count()).select_from(s).where(s.run_id == run_id, s.organization_id == organization_id,
        s.element_id == element_id))).scalar_one() > 0

  async def ledger_for_elements(self, run_id: UUID, organization_id: UUID, element_ids: list[UUID]) -> list[QuantityLedger]:
    if not element_ids:
      return []
    result = await self.session.execute(
      select(QuantityLedger).where(QuantityLedger.run_id == run_id, QuantityLedger.organization_id == organization_id,
        QuantityLedger.element_id.in_(element_ids)).order_by(QuantityLedger.work_item_code, QuantityLedger.id)
    )
    return list(result.scalars().all())

  async def solids_for_elements(self, run_id: UUID, organization_id: UUID, element_ids: list[UUID]) -> list[QuantitySolid]:
    if not element_ids:
      return []
    result = await self.session.execute(
      select(QuantitySolid).where(QuantitySolid.run_id == run_id, QuantitySolid.organization_id == organization_id,
        QuantitySolid.element_id.in_(element_ids)).order_by(QuantitySolid.id)
    )
    return list(result.scalars().all())

  async def purge_staging(self, older_than: datetime) -> dict:
    out = {}
    for name, model in (("bar_marks", StagedRebarBarMark), ("deductions", StagedLedgerDeduction),
      ("ledger", StagedQuantityLedger), ("solids", StagedQuantitySolid)):
      res = await self.session.execute(delete(model).where(model.created_at < older_than))
      out[name] = res.rowcount or 0
    return out

  async def org_run_rows(self, organization_id: UUID, since: datetime, limit: int = 5000):
    r = CalculationRun
    result = await self.session.execute(
      select(r.id, r.project_id, r.status, r.mode, r.error_code, r.started_at, r.completed_at, r.created_at,
        r.metrics["counts"]["elements"].astext.label("elements"),
        r.metrics["counts"]["warnings"].astext.label("warnings"),
        r.metrics["peak_rss_mb"].astext.label("peak_rss_mb"))
      .where(r.organization_id == organization_id, r.created_at >= since)
      .order_by(r.created_at.desc()).limit(limit)
    )
    return result.all()