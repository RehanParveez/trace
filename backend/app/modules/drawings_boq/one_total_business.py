from __future__ import annotations
from app.engine.measure import one_total_rules as RU
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from sqlalchemy import select, delete
from app.modules.projects.repository import ProjectRepository
from app.modules.drawings_boq.repository import DrawingRepository
from app.core.exceptions import TraceException
from app.modules.drawings_boq.one_total_models import ProjectOneTotalRule
from app.modules.drawings_boq.models import BuildingLevel, DrawingFormat, DrawingStatus
from app.modules.drawings_boq.measurement_params import MeasurementParametersService
from app.modules.drawings_boq.takeoff.repository import takeoff_drawing_ids
from app.modules.identity.models import User
from app.modules.identity.enums import PermissionKey

ONE_TOTAL = "one_total"
MAX_RULES = 500

def rule_settings(rows, ids_by_name: dict) -> list:
  out: list = []
  
  for r in rows:
    level_ids = None
    if (r.level_name or "").strip():
      level_ids = sorted(ids_by_name.get(r.level_name.strip().upper(), ()))
    out.append({"kind": r.kind, "mark": r.mark or "", "level_ids": level_ids, "prefer": r.prefer, "note": r.note or ""})
  out.sort(key=lambda d: (d["kind"], d["mark"], d["level_ids"] if d["level_ids"] is not None else [], d["prefer"]))
  return out

def run_additions(rows, ids_by_name: dict, names_by_id: dict, model_drawings: int, pdf_drawings: int, stored_one_total: float | None, given_one_total: float | None) -> dict:
  add: dict = {}
  rules = rule_settings(rows, ids_by_name)
  if rules:
    add["one_total_rules"] = rules
  found = RU.detect(model_drawings, pdf_drawings, given_one_total if given_one_total is not None else stored_one_total)
  if found["one_total"]["source"] == "detected":
    add["detected_params"] = {ONE_TOTAL: 1.0}
  if (rules or found["both"]) and names_by_id:
    add["level_names"] = dict(sorted(names_by_id.items()))
  return add

class RuleIn(BaseModel):
  kind: Literal["COLUMN", "FOOTING", "BEAM", "SLAB", "STAIR", "ITEM"]
  mark: str = Field(default="", max_length=60, description="The mark (C1), or for ITEM the work item code. Empty: every mark of the kind.")
  level_name: str = Field(default="", max_length=200, description="The storey, by name. Empty: every storey.")
  prefer: Literal["DRAWING", "MODEL", "BOTH"]
  note: str | None = Field(default=None, max_length=500)

class RuleOut(BaseModel):
  id: UUID
  kind: str
  mark: str
  level_name: str
  prefer: str
  note: str | None = None
  updated_at: datetime | None = None

class RulesResponse(BaseModel):
  rules: list[RuleOut] = Field(default_factory=list)

class SourcesResponse(BaseModel):
  model_drawings: int
  pdf_drawings: int
  both: bool
  one_total: dict
  needs_attention: bool
  rules: int = 0

def _norm_mark(kind: str, mark: str) -> str:
  return RU.norm(mark)[:60]

class OneTotalService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.projects = ProjectRepository(session)
    self.drawings = DrawingRepository(session)

  async def _require_project(self, org: UUID, project_id: UUID) -> None:
    if await self.projects.get_by_id_and_org(project_id, org) is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

  async def _rows(self, org: UUID, project_id: UUID) -> list:
    return list((await self.session.execute(select(ProjectOneTotalRule).where(
      ProjectOneTotalRule.organization_id == org, ProjectOneTotalRule.project_id == project_id)
      .order_by(ProjectOneTotalRule.kind, ProjectOneTotalRule.mark, ProjectOneTotalRule.level_name))).scalars().all())

  @staticmethod
  def _out(rows) -> RulesResponse:
    return RulesResponse(rules=[RuleOut(id=r.id, kind=r.kind, mark=r.mark or "", level_name=r.level_name or "", prefer=r.prefer, note=r.note, updated_at=r.updated_at) for r in rows])

  async def list_rules(self, org: UUID, project_id: UUID) -> RulesResponse:
    await self._require_project(org, project_id)
    return self._out(await self._rows(org, project_id))

  async def set_rule(self, org: UUID, project_id: UUID, user_id: UUID | None, body: RuleIn) -> RulesResponse:
    await self._require_project(org, project_id)
    mark = _norm_mark(body.kind, body.mark)
    
    if body.kind == "ITEM" and not mark:
      raise TraceException("A rule for a work item needs the work item code.", status_code=422, code="ONE_TOTAL_RULE_NEEDS_ITEM")
    level = body.level_name.strip()
    rows = await self._rows(org, project_id)
    same = next((r for r in rows if r.kind == body.kind and (r.mark or "") == mark and (r.level_name or "") == level), None)
    if same is None:
      if len(rows) >= MAX_RULES:
        raise TraceException(f"A project can have {MAX_RULES} rules. Remove some first.", status_code=422, code="ONE_TOTAL_TOO_MANY_RULES")
      self.session.add(ProjectOneTotalRule(id=uuid4(), organization_id=org, project_id=project_id, kind=body.kind, mark=mark, level_name=level,
        prefer=body.prefer, note=body.note, updated_by_user_id=user_id))
    else:
      same.prefer, same.note, same.updated_by_user_id = body.prefer, body.note, user_id
    await self.session.commit()
    return self._out(await self._rows(org, project_id))

  async def remove_rule(self, org: UUID, project_id: UUID, rule_id: UUID) -> RulesResponse:
    await self._require_project(org, project_id)
    await self.session.execute(delete(ProjectOneTotalRule).where(
      ProjectOneTotalRule.organization_id == org, ProjectOneTotalRule.project_id == project_id, ProjectOneTotalRule.id == rule_id))
    await self.session.commit()
    return self._out(await self._rows(org, project_id))

  async def _current_sources(self, org: UUID, project_id: UUID) -> tuple:
    drawings = await self.drawings.list_by_project(org, project_id)
    ifc = [d for d in drawings if d.format == DrawingFormat.IFC and d.status == DrawingStatus.PARSED and d.is_current_revision]
    with_takeoff = await takeoff_drawing_ids(self.session, org, project_id)
    pdf = [d for d in drawings if d.format == DrawingFormat.PDF and d.id in with_takeoff and d.is_current_revision]
    return ifc, pdf

  async def sources(self, org: UUID, project_id: UUID) -> SourcesResponse:
    await self._require_project(org, project_id)
    ifc, pdf = await self._current_sources(org, project_id)
    stored = (await MeasurementParametersService(self.session).stored_for_run(org, project_id)).get(ONE_TOTAL)
    found = RU.detect(len(ifc), len(pdf), stored)
    return SourcesResponse(**found, rules=len(await self._rows(org, project_id)))

  async def run_settings(self, org: UUID, project_id: UUID, chosen: list, derived_params: dict | None) -> dict:
    rows = await self._rows(org, project_id)
    model_n = sum(1 for d in chosen if d.format == DrawingFormat.IFC)
    pdf_n = sum(1 for d in chosen if d.format == DrawingFormat.PDF)
    if not rows and not (model_n and pdf_n):
      return {}
  
    levels = (await self.session.execute(select(BuildingLevel).where(BuildingLevel.organization_id == org, BuildingLevel.drawing_id.in_([d.id for d in chosen])))).scalars().all()
    ids_by_name: dict = {}
    names_by_id: dict = {}
    for lv in levels:
      ids_by_name.setdefault((lv.name or "").strip().upper(), []).append(str(lv.id))
      names_by_id[str(lv.id)] = lv.name
    stored = (await MeasurementParametersService(self.session).stored_for_run(org, project_id)).get(ONE_TOTAL)
    given = (derived_params or {}).get(ONE_TOTAL)
    return run_additions(rows, ids_by_name, names_by_id, model_n, pdf_n, stored, float(given) if given is not None and not isinstance(given, bool) else None)

router = APIRouter(prefix="/drawings-boq", tags=["Drawings & BOQ"])

@router.get("/projects/{project_id}/one-total/rules", response_model=RulesResponse)
async def get_one_total_rules(project_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await OneTotalService(session).list_rules(current_user.active_membership.organization_id, project_id)

@router.put("/projects/{project_id}/one-total/rules", response_model=RulesResponse)
async def put_one_total_rule(project_id: UUID, payload: RuleIn, current_user: User = Depends(require_permission(PermissionKey.CALC_RUN)), session: AsyncSession = Depends(get_db)):
  return await OneTotalService(session).set_rule(current_user.active_membership.organization_id, project_id, current_user.id, payload)

@router.delete("/projects/{project_id}/one-total/rules/{rule_id}", response_model=RulesResponse)
async def delete_one_total_rule(project_id: UUID, rule_id: UUID, current_user: User = Depends(require_permission(PermissionKey.CALC_RUN)), session: AsyncSession = Depends(get_db)):
  return await OneTotalService(session).remove_rule(current_user.active_membership.organization_id, project_id, rule_id)

@router.get("/projects/{project_id}/one-total/sources", response_model=SourcesResponse)
async def get_one_total_sources(project_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await OneTotalService(session).sources(current_user.active_membership.organization_id, project_id)
