from __future__ import annotations
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.projects.repository import ProjectRepository
from app.modules.audit.service import AuditLogService
from uuid import UUID, uuid4
from sqlalchemy import and_, func, or_, select
from app.modules.drawings_boq.models import BuildingLevel, BuildingSpace, DrawingElement, SpaceBoundary, SpaceFinish
from app.modules.drawings_boq.finish_schedule.common import audit_entity, current_ifc_drawing_ids, require_work_item
from app.core.exceptions import TraceException
from app.modules.audit.models import AuditAction
from app.engine.measure.models import CalculationContext
from app.modules.drawings_boq.boq_logic import UNIT_TABLE
from app.modules.drawings_boq.schedule_parsing import SURFACE_UNIT
from app.engine.measure import finishes as fin
from app.engine.measure import engine as kernel
from app.modules.drawings_boq.spatial_repository import load_phase6_inputs
from app.modules.drawings_boq.service import DrawingBOQService
from app.modules.drawings_boq.standards.service import StandardsService

_MM2_PER_M2 = Decimal("1000000")
_MM_PER_M = Decimal("1000")

def _strip(value: str | None) -> str | None:
  return (value or "").strip() or None

class SpaceService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.projects = ProjectRepository(session)
    self.audit = AuditLogService(session)

  async def _require_project(self, org: UUID, project_id: UUID) -> None:
    if await self.projects.get_by_id_and_org(project_id, org) is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

  async def _space(self, org: UUID, space_id: UUID) -> BuildingSpace:
    space = (await self.session.execute(select(BuildingSpace).where(
      BuildingSpace.id == space_id, BuildingSpace.organization_id == org))).scalar_one_or_none()
    if space is None:
      raise TraceException("Space not found.", status_code=404, code="SPACE_NOT_FOUND")
    return space

  async def _check_level(self, org: UUID, level_id: UUID | None) -> None:
    if level_id is None:
      return
    r = await self.session.execute(select(BuildingLevel.id).where(
      BuildingLevel.id == level_id, BuildingLevel.organization_id == org))
    if r.first() is None:
      raise TraceException("Level not found.", status_code=404, code="LEVEL_NOT_FOUND")

  async def _log(self, org, user_id, entity, entity_id, action, message) -> None:
    await self.audit.log(org, user_id, audit_entity(entity), entity_id, action, message)

  async def _decorate(self, org: UUID, spaces: list[BuildingSpace]) -> list[BuildingSpace]:
    ids = [s.id for s in spaces]
    fc: dict = {}
    bc: dict = {}
    if ids:
        
      fc = dict((await self.session.execute(
        select(SpaceFinish.space_id, func.count()).where(
          SpaceFinish.organization_id == org, SpaceFinish.space_id.in_(ids), SpaceFinish.is_active.is_(True))
        .group_by(SpaceFinish.space_id))).all())
      bc = dict((await self.session.execute(
        select(SpaceBoundary.space_id, func.count()).where(
          SpaceBoundary.organization_id == org, SpaceBoundary.space_id.in_(ids))
        .group_by(SpaceBoundary.space_id))).all())
    for s in spaces:
      s.finish_count, s.boundary_count = fc.get(s.id, 0), bc.get(s.id, 0)
    return spaces

  async def list_spaces(self, org: UUID, project_id: UUID, *, drawing_id: UUID | None = None,
    level_id: UUID | None = None, category: str | None = None, include_inactive: bool = False,
    current_only: bool = True) -> list[BuildingSpace]:
      
    await self._require_project(org, project_id)
    stmt = select(BuildingSpace).where(BuildingSpace.organization_id == org, BuildingSpace.project_id == project_id)
    if drawing_id:
      stmt = stmt.where(BuildingSpace.drawing_id == drawing_id)
    elif current_only:
      ids = await current_ifc_drawing_ids(self.session, org, project_id)
      stmt = stmt.where(or_(BuildingSpace.drawing_id.in_(ids), BuildingSpace.drawing_id.is_(None)))
    if level_id:
      stmt = stmt.where(BuildingSpace.level_id == level_id)
    if category:
      stmt = stmt.where(BuildingSpace.category == category.upper())
    if not include_inactive:
      stmt = stmt.where(BuildingSpace.is_active.is_(True))
    rows = (await self.session.execute(
      stmt.order_by(BuildingSpace.number.asc().nulls_last(), BuildingSpace.name.asc().nulls_last()))).scalars().all()
    return await self._decorate(org, list(rows))

  async def get_detail(self, org: UUID, space_id: UUID) -> BuildingSpace:
    space = await self._space(org, space_id)
    (await self._decorate(org, [space]))
    rows = (await self.session.execute(
      select(SpaceBoundary, DrawingElement.name, DrawingElement.ifc_type, DrawingElement.structural_role)
      .join(DrawingElement, DrawingElement.id == SpaceBoundary.element_id)
      .where(SpaceBoundary.space_id == space.id, SpaceBoundary.organization_id == org))).all()
    space.boundaries = [{"element_id": b.element_id, "name": n, "ifc_type": t, "structural_role": r,
      "boundary_kind": b.boundary_kind, "side": b.side, "source": b.source} for b, n, t, r in rows]
    space.finishes = await self._finish_rows(org, space.id, active_only=False)
    return space

  async def create_space(self, org: UUID, project_id: UUID, user_id: UUID, payload) -> BuildingSpace:
    await self._require_project(org, project_id)
    
    if not (_strip(payload.number) or _strip(payload.name)):
      raise TraceException("A space needs a number or a name.", status_code=422, code="SPACE_NEEDS_NAME")
    await self._check_level(org, payload.level_id)
    area = payload.floor_area_m2 * _MM2_PER_M2 if payload.floor_area_m2 else None
    space = BuildingSpace(
      id=uuid4(), organization_id=org, project_id=project_id, drawing_id=None, level_id=payload.level_id,
      source="MANUAL", number=_strip(payload.number), name=_strip(payload.name), long_name=_strip(payload.long_name),
      category=(payload.category or "UNKNOWN").strip().upper(), usage_text=_strip(payload.usage_text),
      is_external=payload.is_external, is_active=True, net_floor_area_mm2=area, gross_floor_area_mm2=area,
      perimeter_mm=payload.perimeter_m * _MM_PER_M if payload.perimeter_m else None,
      height_mm=payload.height_m * _MM_PER_M if payload.height_m else None,
      geometry_kind="QTO_ONLY" if area else "UNSUPPORTED", properties={"created_manually": True},
      normalization_status="VALID" if area else "WARNING",
      normalization_issues=[] if area else [{"code": "SPACE_AREA_MISSING", "severity": "warning",
        "message": "Space has no floor area."}],
      created_by_user_id=user_id)
    
    self.session.add(space)
    await self.session.flush()
    sid, label = space.id, space.number or space.name
    await self.session.commit()
    await self._log(org, user_id, "SPACE", sid, AuditAction.CREATE, f'Created space "{label}"')
    return (await self._decorate(org, [await self._space(org, sid)]))[0]

  async def update_space(self, org: UUID, space_id: UUID, user_id: UUID, payload) -> BuildingSpace:
    space = await self._space(org, space_id)
    fs = payload.model_fields_set
    overrides: list[str] = []
    
    for key in ("number", "name", "long_name", "usage_text"):
      if key in fs:
        setattr(space, key, _strip(getattr(payload, key)))
    if "category" in fs and payload.category:
      space.category = payload.category.strip().upper()
    if "level_id" in fs:
      await self._check_level(org, payload.level_id)
      space.level_id = payload.level_id
    if "is_external" in fs and payload.is_external is not None:
      space.is_external = payload.is_external
    if "is_active" in fs and payload.is_active is not None:
      space.is_active = payload.is_active
    if "floor_area_m2" in fs:
      area = payload.floor_area_m2 * _MM2_PER_M2 if payload.floor_area_m2 else None
      space.net_floor_area_mm2 = area
      if space.geometry_kind == "UNSUPPORTED" and area:
        space.geometry_kind = "QTO_ONLY"
      overrides.append("floor_area")
    if "perimeter_m" in fs:
      space.perimeter_mm = payload.perimeter_m * _MM_PER_M if payload.perimeter_m else None
      overrides.append("perimeter")
    if "height_m" in fs:
      space.height_mm = payload.height_m * _MM_PER_M if payload.height_m else None
      overrides.append("height")
    if overrides and space.source == "IFC":
      props = dict(space.properties or {})
      props["manual_overrides"] = sorted(set(props.get("manual_overrides", [])) | set(overrides))
      space.properties = props
      
    await self.session.flush()
    sid, label = space.id, space.number or space.name
    await self.session.commit()
    await self._log(org, user_id, "SPACE", sid, AuditAction.UPDATE, f'Updated space "{label}"')
    return (await self._decorate(org, [await self._space(org, sid)]))[0]

  async def delete_space(self, org: UUID, space_id: UUID, user_id: UUID) -> None:
    space = await self._space(org, space_id)
    label = space.number or space.name
    if space.source == "MANUAL":
      await self.session.delete(space)
    else:
      space.is_active = False
    await self.session.commit()
    await self._log(org, user_id, "SPACE", space_id, AuditAction.DELETE, f'Removed space "{label}"')

  async def set_boundaries(self, org: UUID, space_id: UUID, user_id: UUID, element_ids: list[UUID]) -> int:
    space = await self._space(org, space_id)
    wanted = set(element_ids)
    
    if wanted:
      found = {row[0] for row in (await self.session.execute(select(DrawingElement.id).where(
        DrawingElement.organization_id == org, DrawingElement.id.in_(list(wanted)))))}
      if found != wanted:
        raise TraceException("One or more elements were not found.", status_code=422, code="ELEMENT_NOT_FOUND")
    existing = (await self.session.execute(select(SpaceBoundary).where(
      SpaceBoundary.space_id == space.id, SpaceBoundary.organization_id == org))).scalars().all()
    have = set()
    for b in existing:
      if b.element_id in wanted:
        have.add(b.element_id)
      else:
        await self.session.delete(b)
    for eid in sorted(wanted - have, key=str):
      self.session.add(SpaceBoundary(id=uuid4(), organization_id=org, space_id=space.id, element_id=eid,
        boundary_kind="PHYSICAL", side="UNDEFINED", source="DERIVED"))
      
    await self.session.commit()
    await self._log(org, user_id, "SPACE", space_id, AuditAction.UPDATE, f"Set {len(wanted)} boundary element(s)")
    return len(wanted)

  async def _finish_rows(self, org: UUID, space_id: UUID, active_only: bool = True) -> list[SpaceFinish]:
    stmt = select(SpaceFinish).where(SpaceFinish.space_id == space_id, SpaceFinish.organization_id == org)
    if active_only:
      stmt = stmt.where(SpaceFinish.is_active.is_(True))
    return list((await self.session.execute(stmt.order_by(SpaceFinish.surface.asc(), SpaceFinish.work_item_code.asc()))).scalars().all())

  async def list_finishes(self, org: UUID, space_id: UUID) -> list[SpaceFinish]:
    await self._space(org, space_id)
    return await self._finish_rows(org, space_id)

  async def upsert_finish(self, org: UUID, space_id: UUID, user_id: UUID, payload) -> SpaceFinish:
    space = await self._space(org, space_id)
    wi = await require_work_item(self.session, org, payload.work_item_code)
    family = UNIT_TABLE.get((wi.unit or "").strip().lower())
    
    if family is not None and family[0] != SURFACE_UNIT[payload.surface]:
      raise TraceException(
        f"{payload.surface.title()} finishes are measured in {SURFACE_UNIT[payload.surface]}, "
        f"but work item {wi.code} is in {family[0]}.", status_code=422, code="FINISH_UNIT_MISMATCH")
    finish = (await self.session.execute(select(SpaceFinish).where(
      SpaceFinish.space_id == space.id, SpaceFinish.surface == payload.surface,
      SpaceFinish.work_item_code == payload.work_item_code))).scalar_one_or_none()
    if finish is None:
      finish = SpaceFinish(id=uuid4(), organization_id=org, space_id=space.id, surface=payload.surface,
        work_item_code=payload.work_item_code, created_by_user_id=user_id)
      self.session.add(finish)
    finish.finish_name, finish.height_mm = _strip(payload.finish_name), payload.height_mm
    finish.source, finish.schedule_row_id, finish.confidence = "MANUAL", None, Decimal("1")
    finish.review_status, finish.is_active = "OK", True
    
    await self.session.flush()
    fid = finish.id
    await self.session.commit()
    await self._log(org, user_id, "FINISH", fid, AuditAction.UPDATE,
      f"Set {payload.surface} finish {payload.work_item_code} on space {space.number or space.name}")
    return (await self.session.execute(select(SpaceFinish).where(SpaceFinish.id == fid))).scalar_one()

  async def delete_finish(self, org: UUID, finish_id: UUID, user_id: UUID) -> None:
    finish = (await self.session.execute(select(SpaceFinish).where(
      SpaceFinish.id == finish_id, SpaceFinish.organization_id == org))).scalar_one_or_none()
    if finish is None:
      raise TraceException("Finish not found.", status_code=404, code="FINISH_NOT_FOUND")
    finish.is_active = False
    await self.session.commit()
    await self._log(org, user_id, "FINISH", finish_id, AuditAction.DELETE, f"Removed {finish.surface} finish {finish.work_item_code}")

  async def preview_finishes(self, org: UUID, space_id: UUID, rule_set_code: str | None = None) -> dict:
    space = await self._space(org, space_id)
    drawing_ids = await current_ifc_drawing_ids(self.session, org, space.project_id)
    p6 = await load_phase6_inputs(self.session, org, space.project_id, drawing_ids)
    match = [s for s in p6.spaces if s.id == space.id]
    
    if not match:
      raise TraceException("This space is not part of the current model (inactive or an older revision).",
        status_code=404, code="SPACE_NOT_IN_CURRENT_MODEL")
    rule_set = await DrawingBOQService(self.session).get_active_rule_set(org, rule_set_code)
    profile = await StandardsService(self.session).profile_for_rule_set(rule_set.id)
    ctx = CalculationContext(run_id=uuid4(), engine_version=kernel.ENGINE_VERSION, fingerprint="preview",
      convention_code=rule_set.convention_code, rule_set_code=rule_set.code,
      rule_set_version=rule_set.immutable_version, mappings=())
    resolved = fin.resolve_finishes(match[0], profile.finish_rules)
    res = fin.measure_finishes(ctx, profile, match, p6.openings)
    surface_of = {s.id: s.component_type.replace("FINISH_", "") for s in res.solids}
    
    return {
      "space_id": space.id, "rule_set_code": rule_set.code,
      "resolved": [{"surface": f.surface, "work_item_code": f.work_item_code, "source": f.source,
        "height_mm": str(f.height_mm) if f.height_mm else None, "deduct_openings": f.deduct_openings} for f in resolved],
      "lines": [{"surface": surface_of.get(e.solid_id, ""), "work_item_code": e.work_item_code, "unit": e.unit,
        "quantity": e.quantity, "confidence": e.confidence, "formula_code": e.formula_code,
        "source_kind": e.source_kind, "warnings": list(e.warnings), "steps": e.trace.get("steps", [])} for e in res.ledger],
      "skipped": res.skipped,
    }