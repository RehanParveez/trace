from __future__ import annotations
from app.engine.measure.rebar import ShapeSpec, BarSizeSpec, RebarInputs, RebarRowInput
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from decimal import Decimal
from sqlalchemy import and_, func, or_, select
from app.modules.drawings_boq.models import BarSize, RebarBarMark, RebarScheduleRow, RebarShape, ScheduleImport

def _angles(spec) -> tuple:
  out = []
  for b in spec or []:
    try:
      out.append(int(b.get("angle") if isinstance(b, dict) else b))
    except (TypeError, ValueError):
      continue
  return tuple(out)

def shape_spec(row: RebarShape) -> ShapeSpec:
  code = row.code.upper()
  segments = tuple(str(s.get("param") if isinstance(s, dict) else s) for s in (row.segments or []))
  return ShapeSpec(code=code, segments=segments, bend_angles=_angles(row.bend_spec), hook_ends=int(row.hook_ends or 0),
    is_link=code.startswith("STIRRUP") or code.startswith("LINK"))

async def load_shape_rows(session: AsyncSession, org: UUID) -> list[RebarShape]:
  rows = (await session.execute(select(RebarShape).where(RebarShape.is_active.is_(True),
    or_(RebarShape.organization_id == org, RebarShape.organization_id.is_(None))))).scalars().all()
  merged: dict = {}
  for r in sorted(rows, key=lambda r: r.organization_id is not None):
    merged[r.code.upper()] = r
  return sorted(merged.values(), key=lambda r: r.code)

async def load_size_rows(session: AsyncSession, org: UUID) -> list[BarSize]:
  rows = (await session.execute(select(BarSize).where(BarSize.is_active.is_(True),
    or_(BarSize.organization_id == org, BarSize.organization_id.is_(None))))).scalars().all()
  merged: dict = {}
  for r in sorted(rows, key=lambda r: r.organization_id is not None):
    merged[(r.standard, r.designation, r.grade)] = r
  return sorted(merged.values(), key=lambda r: (r.standard, r.nominal_dia_mm, r.grade))

def size_spec(r: BarSize) -> BarSizeSpec:
  return BarSizeSpec(r.standard, r.designation, r.grade, Decimal(r.nominal_dia_mm), Decimal(r.unit_weight_kg_m))

def row_input(r: RebarScheduleRow, import_id: UUID | None = None) -> RebarRowInput:
  return RebarRowInput(
    id=r.id, import_id=import_id or r.schedule_import_id, row_no=r.row_no, member_mark=r.member_mark, mark=r.mark or f"R{r.row_no}",
    role=r.role, shape_code=r.shape_code, shape_params=dict(r.shape_params or {}), designation=r.designation,
    dia_mm=Decimal(r.dia_mm), grade=r.grade, count=int(r.count), spacing_mm=r.spacing_mm, cut_len_mm=r.cut_len_mm,
    declared_total_kg=r.declared_total_kg, level_id=r.level_id, matched_element_id=r.matched_element_id, confidence=Decimal(r.confidence))

async def load_rebar_inputs(session: AsyncSession, org: UUID, project_id: UUID) -> RebarInputs:
  rows = (await session.execute(
    select(RebarScheduleRow).join(ScheduleImport, and_(ScheduleImport.id == RebarScheduleRow.schedule_import_id,
      ScheduleImport.organization_id == RebarScheduleRow.organization_id))
    .where(ScheduleImport.organization_id == org, ScheduleImport.project_id == project_id,
      ScheduleImport.schedule_kind == "BBS", ScheduleImport.status == "CONFIRMED",
      RebarScheduleRow.review_status == "CONFIRMED")
  )).scalars().all()
  usable = [row_input(r) for r in rows if r.dia_mm is not None and r.count is not None]
  shapes = tuple(shape_spec(s) for s in await load_shape_rows(session, org))
  sizes = tuple(size_spec(s) for s in await load_size_rows(session, org))
  if not usable:
    return RebarInputs((), shapes, sizes)
  return RebarInputs(tuple(sorted(usable, key=lambda r: (str(r.import_id), r.row_no))), shapes, sizes)

async def marks_for_run(session: AsyncSession, org: UUID, run_id: UUID, *, include_estimates: bool = True) -> list[RebarBarMark]:
  stmt = select(RebarBarMark).where(RebarBarMark.run_id == run_id, RebarBarMark.organization_id == org)
  if not include_estimates:
    stmt = stmt.where(RebarBarMark.provenance != "RULE_ESTIMATE")
  rows = (await session.execute(stmt)).scalars().all()
  return sorted(rows, key=lambda m: (str(m.level_id), m.role, str(m.element_id), str(m.solid_id), m.mark))

async def marks_for_solids(session: AsyncSession, org: UUID, run_id: UUID, solid_ids: list[UUID]) -> list[RebarBarMark]:
  if not solid_ids:
    return []
  rows = (await session.execute(select(RebarBarMark).where(RebarBarMark.run_id == run_id,
    RebarBarMark.organization_id == org, RebarBarMark.solid_id.in_(solid_ids)))).scalars().all()
  return sorted(rows, key=lambda m: (str(m.solid_id), m.mark))

async def summary_for_run(session: AsyncSession, org: UUID, run_id: UUID) -> dict:
  by_dia = (await session.execute(
    select(RebarBarMark.dia_mm, RebarBarMark.designation, RebarBarMark.grade, func.sum(RebarBarMark.total_len_m),
      func.sum(RebarBarMark.total_kg), func.count())
    .where(RebarBarMark.run_id == run_id, RebarBarMark.organization_id == org)
    .group_by(RebarBarMark.dia_mm, RebarBarMark.designation, RebarBarMark.grade)
    .order_by(RebarBarMark.dia_mm.asc()))).all()
  tiers = dict((await session.execute(
    select(RebarBarMark.provenance, func.sum(RebarBarMark.total_kg))
    .where(RebarBarMark.run_id == run_id, RebarBarMark.organization_id == org)
    .group_by(RebarBarMark.provenance))).all())
  
  zero = Decimal("0")
  t1 = tiers.get("IFC_EXACT") or zero
  t2 = (tiers.get("SCHEDULE_IMPORT") or zero) + (tiers.get("MANUAL") or zero)
  t3 = tiers.get("RULE_ESTIMATE") or zero
  total = t1 + t2 + t3
  return {
    "rows": [{"dia_mm": d, "designation": des, "grade": g, "total_len_m": ln or zero, "total_kg": kg or zero, "mark_count": n}
      for d, des, g, ln, kg, n in by_dia],
    "total_kg": total, "tier1_kg": t1, "tier2_kg": t2, "tier3_estimate_kg": t3, "bbs_exportable": total > 0 and t3 == 0,
  }