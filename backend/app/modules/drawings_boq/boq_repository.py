from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.drawings_boq.models import (BOQVersion, BOQItem, BOQItemAdjustment, BOQItemLedgerLink, BOQItemSourceElement, BOQItemStatus, BOQSnapshot, BOQSnapshotItem, BOQVersionStatus,
  BuildingLevel, CalculationRun, Drawing, DrawingElement, ExportJob, LedgerDeduction, ModelAuditResult, QuantityLedger, ReviewIssue, WorkItem, QuantitySolid
)
from sqlalchemy import select, delete, func, insert, or_, update

_WORKING = ("DRAFT", "CALCULATING", "CALCULATED", "UNDER_REVIEW")
_CHUNK = 1000

def _now():
  return datetime.now(timezone.utc)

class BOQEngineRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def version_for_update(self, version_id: UUID, org: UUID) -> BOQVersion | None:
    r = await self.session.execute(
      select(BOQVersion).where(BOQVersion.id == version_id, BOQVersion.organization_id == org).with_for_update())
    return r.scalar_one_or_none()

  async def working_engine_version(self, org: UUID, project_id: UUID) -> BOQVersion | None:
    r = await self.session.execute(
      select(BOQVersion).where(
        BOQVersion.organization_id == org, BOQVersion.project_id == project_id,
        BOQVersion.origin == "ENGINE", BOQVersion.lifecycle.in_(_WORKING))
      .order_by(BOQVersion.created_at.desc()).limit(1).with_for_update())
    return r.scalar_one_or_none()

  async def latest_engine_version(self, org: UUID, project_id: UUID, exclude_id: UUID | None = None):
    stmt = select(BOQVersion).where(
      BOQVersion.organization_id == org, BOQVersion.project_id == project_id, BOQVersion.origin == "ENGINE")
    if exclude_id is not None:
      stmt = stmt.where(BOQVersion.id != exclude_id)
    r = await self.session.execute(stmt.order_by(BOQVersion.created_at.desc()).limit(1))
    return r.scalar_one_or_none()

  async def transition(self, version_id: UUID, org: UUID, expected: str, to: str, **values) -> bool:
    r = await self.session.execute(
      update(BOQVersion)
      .where(BOQVersion.id == version_id, BOQVersion.organization_id == org, BOQVersion.lifecycle == expected)
      .values(lifecycle=to, **values).execution_options(synchronize_session=False))
    return r.rowcount == 1

  async def supersede_engine(self, org: UUID, project_id: UUID, exclude_id: UUID) -> None:
    await self.session.execute(
      update(BOQVersion)
      .where(BOQVersion.organization_id == org, BOQVersion.project_id == project_id,
        BOQVersion.origin == "ENGINE", BOQVersion.lifecycle.in_(("APPROVED", "ISSUED")),
        BOQVersion.id != exclude_id)
      .values(lifecycle="SUPERSEDED", status=BOQVersionStatus.SUPERSEDED)
      .execution_options(synchronize_session=False))

  async def count_issued(self, org: UUID, project_id: UUID, exclude_id: UUID) -> int:
    r = await self.session.execute(
      select(func.count()).select_from(BOQVersion).where(
        BOQVersion.organization_id == org, BOQVersion.project_id == project_id,
        BOQVersion.origin == "ENGINE", BOQVersion.lifecycle == "ISSUED", BOQVersion.id != exclude_id))
    return r.scalar_one()

  async def min_audit_score(self, org: UUID, drawing_ids: list[UUID]):
    if not drawing_ids:
      return None
    r = await self.session.execute(
      select(func.min(ModelAuditResult.overall_score))
      .join(Drawing, Drawing.latest_audit_id == ModelAuditResult.id)
      .where(Drawing.id.in_(drawing_ids), Drawing.organization_id == org))
    return r.scalar_one_or_none()

  async def items_by_key(self, version_id: UUID, org: UUID) -> dict[str, BOQItem]:
    r = await self.session.execute(
      select(BOQItem).where(BOQItem.boq_version_id == version_id, BOQItem.organization_id == org,
         BOQItem.item_key.is_not(None)))
    return {i.item_key: i for i in r.scalars().all()}

  async def approve_items(self, version_id: UUID, org: UUID, user_id: UUID, now: datetime) -> None:
    await self.session.execute(
      update(BOQItem).where(BOQItem.boq_version_id == version_id, BOQItem.organization_id == org)
      .values(status=BOQItemStatus.APPROVED, approved_by_user_id=user_id, approved_at=now,
        version=BOQItem.version + 1).execution_options(synchronize_session=False))

  async def delete_links(self, version_id: UUID) -> None:
    await self.session.execute(delete(BOQItemLedgerLink).where(BOQItemLedgerLink.boq_version_id == version_id))
    ids = select(BOQItem.id).where(BOQItem.boq_version_id == version_id)
    await self.session.execute(
      delete(BOQItemSourceElement).where(
        BOQItemSourceElement.boq_item_id.in_(ids), BOQItemSourceElement.contribution_type == "ledger"))

  async def add_links(self, rows: list[dict]) -> None:
    for i in range(0, len(rows), _CHUNK):
      await self.session.execute(insert(BOQItemLedgerLink), rows[i:i + _CHUNK])

  async def add_source_elements(self, rows: list[dict]) -> None:
    for i in range(0, len(rows), _CHUNK):
      await self.session.execute(insert(BOQItemSourceElement), rows[i:i + _CHUNK])

  async def link_pairs(self, version_id: UUID, org: UUID) -> dict[UUID, list[tuple]]:
    r = await self.session.execute(
      select(BOQItemLedgerLink.boq_item_id, BOQItemLedgerLink.ledger_id, BOQItemLedgerLink.quantity_contributed)
      .where(BOQItemLedgerLink.boq_version_id == version_id, BOQItemLedgerLink.organization_id == org))
    out: dict = {}
    for item_id, ledger_id, qty in r.all():
      out.setdefault(item_id, []).append((ledger_id, qty))
    return out

  async def ledger_for_run(self, run_id: UUID, org: UUID) -> list[QuantityLedger]:
    r = await self.session.execute(
      select(QuantityLedger).where(QuantityLedger.run_id == run_id, QuantityLedger.organization_id == org)
      .order_by(QuantityLedger.id.asc()))
    return list(r.scalars().all())

  async def ledger_for_version(self, version_id: UUID, org: UUID, *, limit: int, after: UUID | None = None,
    work_item_code: str | None = None, item_id: UUID | None = None, level_id: UUID | None = None):
    stmt = (select(QuantityLedger)
      .join(BOQItemLedgerLink, BOQItemLedgerLink.ledger_id == QuantityLedger.id)
      .where(BOQItemLedgerLink.boq_version_id == version_id, QuantityLedger.organization_id == org))
    if work_item_code:
      stmt = stmt.where(QuantityLedger.work_item_code == work_item_code)
    if item_id:
      stmt = stmt.where(BOQItemLedgerLink.boq_item_id == item_id)
    if level_id:
      stmt = stmt.where(QuantityLedger.level_id == level_id)
    if after:
      stmt = stmt.where(QuantityLedger.id > after)
    r = await self.session.execute(stmt.order_by(QuantityLedger.id.asc()).limit(limit + 1))
    return list(r.scalars().all())

  async def ledger_for_item(self, item_id: UUID, org: UUID) -> list[QuantityLedger]:
    r = await self.session.execute(
      select(QuantityLedger).join(BOQItemLedgerLink, BOQItemLedgerLink.ledger_id == QuantityLedger.id)
      .where(BOQItemLedgerLink.boq_item_id == item_id, QuantityLedger.organization_id == org)
      .order_by(QuantityLedger.id.asc()))
    return list(r.scalars().all())

  async def ledger_by_ids(self, ids: list[UUID]) -> list[QuantityLedger]:
    if not ids:
      return []
    r = await self.session.execute(select(QuantityLedger).where(QuantityLedger.id.in_(ids)))
    return list(r.scalars().all())

  async def deductions_for_solids(self, run_id: UUID, org: UUID, solid_ids: list[UUID]) -> list[LedgerDeduction]:
    if not solid_ids:
      return []
    r = await self.session.execute(
      select(LedgerDeduction).where(LedgerDeduction.run_id == run_id, LedgerDeduction.organization_id == org,
       LedgerDeduction.from_solid_id.in_(solid_ids))
      .order_by(LedgerDeduction.id.asc()))
    return list(r.scalars().all())

  async def active_adjustments(self, item_ids: list[UUID]) -> dict[UUID, list[BOQItemAdjustment]]:
    if not item_ids:
      return {}
    r = await self.session.execute(
      select(BOQItemAdjustment).where(BOQItemAdjustment.boq_item_id.in_(item_ids),
      BOQItemAdjustment.revoked_at.is_(None))
      .order_by(BOQItemAdjustment.created_at.asc(), BOQItemAdjustment.id.asc()))
    out: dict = {}
    for a in r.scalars().all():
      out.setdefault(a.boq_item_id, []).append(a)
    return out

  async def list_adjustments(self, item_id: UUID, org: UUID) -> list[BOQItemAdjustment]:
    r = await self.session.execute(
      select(BOQItemAdjustment).where(BOQItemAdjustment.boq_item_id == item_id,
      BOQItemAdjustment.organization_id == org)
      .order_by(BOQItemAdjustment.created_at.asc(), BOQItemAdjustment.id.asc()))
    return list(r.scalars().all())

  async def adjustments_for_version(self, version_id: UUID, org: UUID) -> list[tuple]:
    r = await self.session.execute(
      select(BOQItemAdjustment, BOQItem.material_name)
      .join(BOQItem, BOQItem.id == BOQItemAdjustment.boq_item_id)
      .where(BOQItem.boq_version_id == version_id, BOQItemAdjustment.organization_id == org)
      .order_by(BOQItemAdjustment.created_at.asc()))
    return list(r.all())

  async def get_adjustment(self, adjustment_id: UUID, org: UUID) -> BOQItemAdjustment | None:
    r = await self.session.execute(
      select(BOQItemAdjustment).where(BOQItemAdjustment.id == adjustment_id,
       BOQItemAdjustment.organization_id == org))
    return r.scalar_one_or_none()

  async def next_snapshot_no(self, version_id: UUID) -> int:
    r = await self.session.execute(
      select(func.coalesce(func.max(BOQSnapshot.version_no), 0) + 1).where(BOQSnapshot.boq_version_id == version_id))
    return r.scalar_one()

  async def get_snapshot(self, snapshot_id: UUID, org: UUID) -> BOQSnapshot | None:
    r = await self.session.execute(
      select(BOQSnapshot).where(BOQSnapshot.id == snapshot_id, BOQSnapshot.organization_id == org))
    return r.scalar_one_or_none()

  async def list_snapshots(self, version_id: UUID, org: UUID) -> list[BOQSnapshot]:
    r = await self.session.execute(
      select(BOQSnapshot).where(BOQSnapshot.boq_version_id == version_id, BOQSnapshot.organization_id == org)
      .order_by(BOQSnapshot.version_no.asc()))
    return list(r.scalars().all())

  async def snapshot_items(self, snapshot_id: UUID, org: UUID) -> list[BOQSnapshotItem]:
    r = await self.session.execute(
      select(BOQSnapshotItem).where(BOQSnapshotItem.snapshot_id == snapshot_id,
        BOQSnapshotItem.organization_id == org)
      .order_by(BOQSnapshotItem.line_no.asc()))
    return list(r.scalars().all())

  async def add_snapshot_items(self, rows: list[dict]) -> None:
    for i in range(0, len(rows), _CHUNK):
      await self.session.execute(insert(BOQSnapshotItem), rows[i:i + _CHUNK])

  async def issues_for_version(self, version_id: UUID, org: UUID, status: str | None = None) -> list[ReviewIssue]:
    stmt = select(ReviewIssue).where(ReviewIssue.boq_version_id == version_id, ReviewIssue.organization_id == org)
    if status:
      stmt = stmt.where(ReviewIssue.status == status)
    r = await self.session.execute(stmt.order_by(ReviewIssue.severity.asc(), ReviewIssue.code.asc()))
    return list(r.scalars().all())

  async def issues_for_project(self, org: UUID, project_id: UUID, status: str | None = None,
    version_id: UUID | None = None) -> list[ReviewIssue]:
    stmt = select(ReviewIssue).where(ReviewIssue.organization_id == org, ReviewIssue.project_id == project_id)
    if status:
      stmt = stmt.where(ReviewIssue.status == status)
    if version_id:
      stmt = stmt.where(ReviewIssue.boq_version_id == version_id)
    r = await self.session.execute(stmt.order_by(ReviewIssue.created_at.desc()))
    return list(r.scalars().all())

  async def get_issue(self, issue_id: UUID, org: UUID) -> ReviewIssue | None:
    r = await self.session.execute(
      select(ReviewIssue).where(ReviewIssue.id == issue_id, ReviewIssue.organization_id == org).with_for_update())
    return r.scalar_one_or_none()

  async def issue_by_dedupe(self, version_id: UUID, dedupe_key: str) -> ReviewIssue | None:
    r = await self.session.execute(
      select(ReviewIssue).where(ReviewIssue.boq_version_id == version_id, ReviewIssue.dedupe_key == dedupe_key))
    return r.scalar_one_or_none()

  async def count_open(self, version_id: UUID, org: UUID, blocks: tuple) -> int:
    r = await self.session.execute(
      select(func.count()).select_from(ReviewIssue).where(
        ReviewIssue.boq_version_id == version_id, ReviewIssue.organization_id == org,
        ReviewIssue.status == "OPEN", ReviewIssue.blocks.in_(blocks)))
    return r.scalar_one()

  async def work_items_by_codes(self, org: UUID, codes) -> dict[str, WorkItem]:
    codes = list(codes)
    if not codes:
      return {}
    r = await self.session.execute(
      select(WorkItem).where(WorkItem.code.in_(codes), WorkItem.is_active.is_(True),
        or_(WorkItem.organization_id == org, WorkItem.organization_id.is_(None))))
    out: dict = {}
    for w in sorted(r.scalars().all(), key=lambda w: w.organization_id is not None):
      out[w.code] = w 
    return out

  async def invalid_counts(self, org: UUID, drawing_ids: list[UUID], ifc_types: list[str], roles: list[str]) -> dict:
    if not drawing_ids or not ifc_types:
      return {}
    r = await self.session.execute(
      select(DrawingElement.ifc_type, func.count()).where(
        DrawingElement.organization_id == org, DrawingElement.drawing_id.in_(drawing_ids),
        DrawingElement.normalization_status == "INVALID", DrawingElement.ifc_type.in_(ifc_types),
        DrawingElement.structural_role.in_(roles)).group_by(DrawingElement.ifc_type))
    return {t: n for t, n in r.all()}

  async def element_names(self, ids: list[UUID]) -> dict[UUID, str]:
    if not ids:
      return {}
    r = await self.session.execute(
      select(DrawingElement.id, DrawingElement.name, DrawingElement.ifc_type).where(DrawingElement.id.in_(ids)))
    return {i: (n or t) for i, n, t in r.all()}

  async def level_names(self, org: UUID, ids: list[UUID]) -> dict[UUID, str]:
    if not ids:
      return {}
    r = await self.session.execute(
      select(BuildingLevel.id, BuildingLevel.name).where(BuildingLevel.id.in_(ids), BuildingLevel.organization_id == org))
    return {i: n for i, n in r.all()}

  async def merge_run_stats(self, run_id: UUID, patch: dict) -> None:
    r = await self.session.execute(select(CalculationRun).where(CalculationRun.id == run_id))
    row = r.scalar_one_or_none()
    if row is not None:
      row.stats = {**(row.stats or {}), **patch}
      await self.session.flush()

  def add_export_job(self, job: ExportJob) -> None:
    self.session.add(job)

  async def get_export_job(self, job_id: UUID, org: UUID) -> ExportJob | None:
    r = await self.session.execute(select(ExportJob).where(ExportJob.id == job_id, ExportJob.organization_id == org))
    return r.scalar_one_or_none()

  async def find_reusable_export(self, org: UUID, version_id: UUID, snapshot_id: UUID, kind: str, fmt: str,
    compare_snapshot_id: str | None, newer_than: datetime) -> ExportJob | None:
    """A queued, running or finished async export of the same snapshot: snapshots never change, so it is the same file."""
    r = await self.session.execute(
      select(ExportJob).where(
        ExportJob.organization_id == org, ExportJob.boq_version_id == version_id, ExportJob.snapshot_id == snapshot_id,
        ExportJob.kind == kind, ExportJob.format == fmt, ExportJob.created_at >= newer_than,
        or_(ExportJob.status.in_(("QUEUED", "RUNNING")),
          (ExportJob.status == "SUCCEEDED") & ExportJob.storage_key.is_not(None)))
      .order_by(ExportJob.created_at.desc()).limit(5))
    for job in r.scalars().all():
      if (job.parameters or {}).get("compare_snapshot_id") == compare_snapshot_id:
        return job
    return None

  async def claim_export_job(self, job_id: UUID) -> ExportJob | None:
    r = await self.session.execute(
      update(ExportJob).where(ExportJob.id == job_id, ExportJob.status == "QUEUED")
      .values(status="RUNNING", started_at=_now()).returning(ExportJob))
    return r.scalar_one_or_none()

  async def finish_export_job(self, job_id: UUID, status: str, *, storage_key: str | None = None, size: int | None = None,
    parameters: dict | None = None, error_code: str | None = None, error_message: str | None = None) -> None:
    values = {"status": status, "finished_at": _now(), "error_code": error_code, "error_message": error_message}
    if storage_key is not None:
      values["storage_key"] = storage_key
    if size is not None:
      values["file_size_bytes"] = size
    if parameters is not None:
      values["parameters"] = parameters
    await self.session.execute(update(ExportJob).where(ExportJob.id == job_id).values(**values))

  async def stale_export_jobs(self, queued_before: datetime, running_before: datetime, limit: int = 100) -> list[ExportJob]:
    r = await self.session.execute(
      select(ExportJob).where(or_(
        (ExportJob.status == "QUEUED") & (ExportJob.created_at < queued_before),
        (ExportJob.status == "RUNNING") & (ExportJob.started_at < running_before)))
      .order_by(ExportJob.created_at).limit(limit))
    return list(r.scalars().all())

  async def expired_export_files(self, before: datetime, limit: int = 500) -> list[ExportJob]:
    r = await self.session.execute(
      select(ExportJob).where(ExportJob.storage_key.is_not(None), ExportJob.finished_at < before)
      .order_by(ExportJob.finished_at).limit(limit))
    return list(r.scalars().all())
    
  async def delete_items(self, ids: list[UUID]) -> None:
    for i in range(0, len(ids), _CHUNK):
      await self.session.execute(delete(BOQItem).where(BOQItem.id.in_(ids[i:i + _CHUNK])))

  async def adjustment_history(self, item_ids: list[UUID]) -> set[UUID]:
    if not item_ids:
      return set()
    r = await self.session.execute(
      select(BOQItemAdjustment.boq_item_id).where(BOQItemAdjustment.boq_item_id.in_(item_ids)).distinct())
    return {row[0] for row in r.all()}

  async def get_adjustment_for_update(self, adjustment_id: UUID, org: UUID) -> BOQItemAdjustment | None:
    r = await self.session.execute(
      select(BOQItemAdjustment).where(BOQItemAdjustment.id == adjustment_id,
        BOQItemAdjustment.organization_id == org).with_for_update())
    return r.scalar_one_or_none()

  async def latest_snapshot(self, version_id: UUID, org: UUID) -> BOQSnapshot | None:
    r = await self.session.execute(
      select(BOQSnapshot).where(BOQSnapshot.boq_version_id == version_id, BOQSnapshot.organization_id == org)
      .order_by(BOQSnapshot.version_no.desc()).limit(1))
    return r.scalar_one_or_none()

  async def waive_open_by_code(self, version_id: UUID, org: UUID, code: str, note: str, user_id: UUID) -> int:
    r = await self.session.execute(
      update(ReviewIssue)
      .where(ReviewIssue.boq_version_id == version_id, ReviewIssue.organization_id == org,
        ReviewIssue.code == code, ReviewIssue.status == "OPEN")
      .values(status="WAIVED", resolution_note=note, resolved_by_user_id=user_id, resolved_at=_now())
      .execution_options(synchronize_session=False))
    return r.rowcount

  async def solids_by_ids(self, ids: list[UUID], org: UUID) -> dict:
    if not ids:
      return {}
    r = await self.session.execute(
      select(QuantitySolid).where(QuantitySolid.id.in_(ids), QuantitySolid.organization_id == org))
    return {s.id: s for s in r.scalars().all()}
  
  async def previous_snapshot_for_project(self, org: UUID, project_id: UUID, exclude_version_id: UUID) -> BOQSnapshot | None:
    r = await self.session.execute(
      select(BOQSnapshot).join(BOQVersion, BOQVersion.id == BOQSnapshot.boq_version_id)
      .where(BOQSnapshot.organization_id == org, BOQVersion.project_id == project_id,
        BOQSnapshot.boq_version_id != exclude_version_id)
      .order_by(BOQSnapshot.created_at.desc(), BOQSnapshot.version_no.desc()).limit(1))
    return r.scalar_one_or_none()