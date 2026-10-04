from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID, uuid4
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from app.engine.measure.models import OpeningInput, ScheduleLineInput, SpaceFinishInput, SpaceInput
from app.engine.measure.profile import FinishRuleSpec
from app.modules.drawings_boq.models import BuildingSpace, DrawingElement, ElementRelation, FinishRule, ScheduleImport, ScheduleRow, SpaceBoundary, SpaceFinish

_CHUNK = 1000

@dataclass(frozen=True)
class Phase6Inputs:
  spaces: tuple = ()
  openings: tuple = ()
  schedule_lines: tuple = ()

def _chunks(items: list, size: int = _CHUNK):
  for i in range(0, len(items), size):
    yield items[i:i + size]

async def finish_rule_rows(session: AsyncSession, rule_set_id: UUID) -> list[FinishRule]:
  r = await session.execute(select(FinishRule).where(FinishRule.rule_set_id == rule_set_id))
  return list(r.scalars().all())

async def finish_rule_specs(session: AsyncSession, rule_set_id: UUID) -> tuple[FinishRuleSpec, ...]:
  rows = await finish_rule_rows(session, rule_set_id)
  return tuple(sorted(
    (FinishRuleSpec(r.space_category, r.surface, r.work_item_code, r.height_mm, r.deduct_openings, r.priority,
      bool((r.extra_config or {}).get("exclude"))) for r in rows),
    key=lambda s: (s.space_category, s.surface, s.work_item_code)))

async def load_phase6_inputs(session: AsyncSession, org: UUID, project_id: UUID, drawing_ids: list[UUID]) -> Phase6Inputs:
  if not drawing_ids:
    return Phase6Inputs()
  spaces = list((await session.execute(
    select(BuildingSpace).where(
      BuildingSpace.organization_id == org, BuildingSpace.project_id == project_id,
      or_(BuildingSpace.drawing_id.in_(drawing_ids),
        and_(BuildingSpace.drawing_id.is_(None), BuildingSpace.source == "MANUAL")),
      BuildingSpace.is_active.is_(True))
  )).scalars().all())
  space_ids = [s.id for s in spaces]

  boundaries: dict = {}
  finishes: dict = {}
  for chunk in _chunks(space_ids):
    for sid, eid in (await session.execute(
      select(SpaceBoundary.space_id, SpaceBoundary.element_id).where(
        SpaceBoundary.organization_id == org, SpaceBoundary.space_id.in_(chunk)))).all():
      boundaries.setdefault(sid, []).append(eid)
    for f in (await session.execute(
      select(SpaceFinish).where(SpaceFinish.organization_id == org, SpaceFinish.space_id.in_(chunk),
        SpaceFinish.is_active.is_(True)))).scalars().all():
      finishes.setdefault(f.space_id, []).append(SpaceFinishInput(
        surface=f.surface, work_item_code=f.work_item_code, height_mm=f.height_mm, source=f.source,
        confidence=f.confidence, review_status=f.review_status, finish_name=f.finish_name))

  space_inputs = tuple(sorted((SpaceInput(
    id=s.id, level_id=s.level_id, number=s.number, name=s.name, category=s.category, is_external=s.is_external,
    net_floor_area_mm2=s.net_floor_area_mm2, gross_floor_area_mm2=s.gross_floor_area_mm2,
    perimeter_mm=s.perimeter_mm, height_mm=s.height_mm, geometry_kind=s.geometry_kind,
    footprint=tuple((float(p[0]), float(p[1])) for p in (s.footprint or {}).get("plan_mm", [])) or None,
    boundary_element_ids=tuple(sorted(boundaries.get(s.id, []), key=str)),
    finishes=tuple(finishes.get(s.id, [])),
  ) for s in spaces), key=lambda s: str(s.id)))

  Host = aliased(DrawingElement)
  rows = (await session.execute(
    select(DrawingElement, ElementRelation.to_element_id, Host.thickness_mm)
    .outerjoin(ElementRelation, (ElementRelation.from_element_id == DrawingElement.id)
      & (ElementRelation.relation == "HOSTED_IN"))
    .outerjoin(Host, Host.id == ElementRelation.to_element_id)
    .where(DrawingElement.organization_id == org, DrawingElement.drawing_id.in_(drawing_ids),
      DrawingElement.structural_role.in_(("DOOR", "WINDOW")), DrawingElement.normalization_status != "INVALID")
  )).all()
  openings: dict = {}
  for e, host_id, host_t in rows:
    if e.id in openings:
      continue
    centre = None
    if None not in (e.bbox_min_x_mm, e.bbox_max_x_mm, e.bbox_min_y_mm, e.bbox_max_y_mm):
      centre = (float(e.bbox_min_x_mm + e.bbox_max_x_mm) / 2.0, float(e.bbox_min_y_mm + e.bbox_max_y_mm) / 2.0)
    openings[e.id] = OpeningInput(
      element_id=e.id, role=e.structural_role, host_element_id=host_id, host_thickness_mm=host_t,
      width_mm=e.width_mm, height_mm=e.height_mm, level_id=e.level_id, centre_mm=centre)

  lines = (await session.execute(
    select(ScheduleRow).join(ScheduleImport, (ScheduleImport.id == ScheduleRow.schedule_import_id)
      & (ScheduleImport.organization_id == ScheduleRow.organization_id))
    .where(ScheduleImport.organization_id == org, ScheduleImport.project_id == project_id,
      ScheduleImport.status == "CONFIRMED", ScheduleRow.review_status == "CONFIRMED",
      ScheduleRow.matched_element_count == 0)
  )).scalars().all()
  line_inputs = tuple(sorted((ScheduleLineInput(
    id=r.id, import_id=r.schedule_import_id, row_no=r.row_no, schedule_kind=r.schedule_kind, description=r.description,
    mark=r.mark, work_item_code=r.work_item_code, unit=r.canonical_unit, quantity=r.canonical_quantity,
    confidence=r.confidence, level_id=r.level_id, space_id=r.space_id, raw_text=r.raw_text)
    for r in lines if not (r.schedule_kind == "FINISH" and r.space_id is not None)), key=lambda l: str(l.id)))
  return Phase6Inputs(spaces=space_inputs, openings=tuple(sorted(openings.values(), key=lambda o: str(o.element_id))),
    schedule_lines=line_inputs)

async def persist_spatial(session: AsyncSession, drawing, read_result, drawing_elements, level_ids: dict) -> None:
  try:
    async with session.begin_nested():
      by_gid = {e.ifc_global_id: e.id for e in drawing_elements if e.ifc_global_id}
      space_ids: dict = {}
      rows = []
      for sp in read_result.spaces:
        sid = uuid4()
        space_ids[sp.global_id] = sid
        rows.append(BuildingSpace(
          id=sid, organization_id=drawing.organization_id, project_id=drawing.project_id, drawing_id=drawing.id,
          level_id=level_ids.get(sp.level_global_id), source="IFC", ifc_global_id=sp.global_id,
          number=(sp.number or "")[:100] or None, name=(sp.name or "")[:300] or None,
          long_name=(sp.long_name or "")[:500] or None, category=sp.category,
          usage_text=(sp.usage_text or "")[:300] or None, is_external=sp.is_external,
          gross_floor_area_mm2=sp.gross_floor_area_mm2, net_floor_area_mm2=sp.net_floor_area_mm2,
          perimeter_mm=sp.perimeter_mm, height_mm=sp.height_mm, elevation_base_mm=sp.elevation_base_mm,
          geometry_kind=sp.geometry_kind, footprint=sp.footprint, properties=sp.properties,
          normalization_status=sp.status, normalization_issues=sp.issues))
      session.add_all(rows)
      await session.flush()

      boundary_rows, seen = [], set()
      for b in read_result.boundaries:
        sid, eid = space_ids.get(b.space_global_id), by_gid.get(b.element_global_id)
        if sid and eid and (sid, eid) not in seen:
          seen.add((sid, eid))
          boundary_rows.append(SpaceBoundary(
            id=uuid4(), organization_id=drawing.organization_id, space_id=sid, element_id=eid,
            boundary_kind=b.kind, side=b.side, source="IFC"))
          
      relation_rows, seen = [], set()
      for r in read_result.relations:
        a, b = by_gid.get(r.from_global_id), by_gid.get(r.to_global_id)
        if a and b and a != b and (a, b, r.relation) not in seen:
          seen.add((a, b, r.relation))
          relation_rows.append(ElementRelation(
            id=uuid4(), organization_id=drawing.organization_id, drawing_id=drawing.id,
            from_element_id=a, to_element_id=b, relation=r.relation, source="IFC"))
      session.add_all(boundary_rows + relation_rows)
      await session.flush()
      
  except Exception as exc:
    read_result.model_issues.append({"code": "SPATIAL_PERSIST_FAILED", "severity": "warning",
      "message": f"Spaces and relations could not be stored: {str(exc)[:200]}"})