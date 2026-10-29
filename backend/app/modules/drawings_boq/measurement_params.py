from __future__ import annotations
from app.engine.measure import derived as derived_module
from app.engine.measure import readings as QS
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from uuid import UUID, uuid4
from app.modules.drawings_boq.models import ProjectMeasurementParameter
from app.modules.drawings_boq.company_conventions import CompanyConventionsResponse, CompanyConventionsService, CompanyConventionsUpdate
from app.modules.drawings_boq.takeoff.printed_service import printed_for_project
from decimal import Decimal
from app.modules.projects.repository import ProjectRepository
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from app.core.exceptions import TraceException
from app.core.database import get_db
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.dependencies.permissions import require_permission

def checked_override(key: str, raw):
  if key.startswith("stage."):
    from app.modules.drawings_boq.rule_book_service import checked_value
    return checked_value(key, raw)
  from app.modules.drawings_boq.company_conventions import checked
  return checked(key, raw)

def parameter_ranges() -> dict[str, tuple[float, float, float | None]]:
  out = {name: (low, high, default) for name, (default, low, high) in derived_module.PARAMS.items()}
  low, high = derived_module.NGL_RANGE
  out[derived_module.NGL_PARAM] = (low, high, None)
  for name, (lo, hi) in derived_module.ASKED_PARAMS.items():
    out[name] = (lo, hi, None)
  return out

class MeasurementParametersResponse(BaseModel):
  values: dict[str, float] = Field(default_factory=dict,
    description="Site assumptions saved for this project. A name that is missing uses the engine default.")
  defaults: dict[str, float] = Field(default_factory=dict)
  qs: dict[str, float] = Field(default_factory=dict, description="Site assumptions the QS answered. They apply when the project has no saved value.")
  drawing: dict[str, float] = Field(default_factory=dict, description="Values the project's PDF drawings print in their notes. They apply when the project has no saved value.")
  drawing_notes: dict[str, dict] = Field(default_factory=dict, description="For each such value, the note it was read from and the pages.")
  drawing_conflicts: list[dict] = Field(default_factory=list, description="Notes printed twice with different values; nothing is set from them.")
  lap_table_mm: dict[str, float] = Field(default_factory=dict, description="Lap length in mm printed for each bar number.")

class MeasurementParametersUpdate(BaseModel):
  values: dict[str, float | None] = Field(default_factory=dict,
    description="Name to value. A null value removes the saved value so the engine default applies again.")

class MeasurementParametersRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def list_for_project(self, organization_id: UUID, project_id: UUID) -> dict[str, float]:
    rows = (await self.session.execute(
      select(ProjectMeasurementParameter).where(
        ProjectMeasurementParameter.organization_id == organization_id,
        ProjectMeasurementParameter.project_id == project_id)
    )).scalars().all()
    return {r.code: float(r.value) for r in rows}

  async def upsert(self, organization_id: UUID, project_id: UUID, user_id: UUID | None, code: str, value: float) -> None:
    row = (await self.session.execute(
      select(ProjectMeasurementParameter).where(
        ProjectMeasurementParameter.project_id == project_id,
        ProjectMeasurementParameter.organization_id == organization_id,
        ProjectMeasurementParameter.code == code)
    )).scalar_one_or_none()
    if row is None:
      self.session.add(ProjectMeasurementParameter(
        id=uuid4(), organization_id=organization_id, project_id=project_id, code=code,
        value=Decimal(str(value)), updated_by_user_id=user_id))
    else:
      row.value = Decimal(str(value))
      row.updated_by_user_id = user_id
      row.updated_at = datetime.now(timezone.utc)

  async def remove(self, organization_id: UUID, project_id: UUID, code: str) -> None:
    await self.session.execute(delete(ProjectMeasurementParameter).where(
      ProjectMeasurementParameter.organization_id == organization_id,
      ProjectMeasurementParameter.project_id == project_id,
      ProjectMeasurementParameter.code == code))

class MeasurementParametersService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = MeasurementParametersRepository(session)
    self.projects = ProjectRepository(session)

  async def _require_project(self, organization_id: UUID, project_id: UUID) -> None:
    if await self.projects.get_by_id_and_org(project_id, organization_id) is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

  @staticmethod
  def defaults() -> dict[str, float]:
    return {name: default for name, (_, _, default) in parameter_ranges().items() if default is not None}

  async def get(self, organization_id: UUID, project_id: UUID) -> MeasurementParametersResponse:
    await self._require_project(organization_id, project_id)
    stored = await self.repo.list_for_project(organization_id, project_id)
    known = parameter_ranges()
    printed = await printed_for_project(self.session, organization_id, project_id)
    return MeasurementParametersResponse(values={k: v for k, v in stored.items() if k in known}, defaults=self.defaults(),
      qs={k: float(v) for k, v in QS.PARAM_VALUES.items() if k in known}, drawing={k: float(v) for k, v in printed["params"].items() if k in known},
      drawing_notes=printed["notes"], drawing_conflicts=printed["conflicts"], lap_table_mm=printed["lap_table_mm"])

  async def stored_for_run(self, organization_id: UUID, project_id: UUID) -> dict[str, float]:
    stored = await self.repo.list_for_project(organization_id, project_id)
    known = parameter_ranges()
    return {k: v for k, v in stored.items() if k in known}

  async def update(self, organization_id: UUID, project_id: UUID, user_id: UUID | None,
    values: dict[str, float | None]) -> MeasurementParametersResponse:
    await self._require_project(organization_id, project_id)
    known = parameter_ranges()
    for code, value in values.items():
      if code not in known:
        raise TraceException(f"Unknown site assumption '{code}'.", status_code=422, code="UNKNOWN_MEASUREMENT_PARAMETER")
      if value is None:
        continue
      low, high, _ = known[code]
      if value != value or not (low <= value <= high):
        raise TraceException(f"{code} must be between {low:g} and {high:g}.", status_code=422,
          code="MEASUREMENT_PARAMETER_OUT_OF_RANGE")
    for code, value in values.items():
      if value is None:
        await self.repo.remove(organization_id, project_id, code)
      else:
        await self.repo.upsert(organization_id, project_id, user_id, code, float(value))
    await self.session.commit()
    return await self.get(organization_id, project_id)

router = APIRouter(prefix="/drawings-boq", tags=["Drawings & BOQ"])

@router.get("/qs-answers")
async def get_qs_answers(current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ))):
  """The QS's answers to the measurement questions: what each one changed, what still needs his word and what belongs to one plot."""
  return QS.public()

@router.get("/projects/{project_id}/measurement-parameters", response_model=MeasurementParametersResponse)
async def get_measurement_parameters(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await MeasurementParametersService(session).get(current_user.active_membership.organization_id, project_id)

@router.put("/projects/{project_id}/measurement-parameters", response_model=MeasurementParametersResponse)
async def put_measurement_parameters(
  project_id: UUID,
  payload: MeasurementParametersUpdate,
  current_user: User = Depends(require_permission(PermissionKey.CALC_RUN)),
  session: AsyncSession = Depends(get_db),
):
  return await MeasurementParametersService(session).update(
    current_user.active_membership.organization_id, project_id, current_user.id, payload.values)

@router.get("/company-conventions", response_model=CompanyConventionsResponse)
async def get_company_conventions(
  project_id: UUID | None = Query(default=None, description="Show the figures this project holds in place of the company's."),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  """Every convention the company can hold: the figure in force, its class and version in the company's rule book, where it comes from, and how many sheets were last read with another figure."""
  return await CompanyConventionsService(session).view(current_user.active_membership.organization_id, project_id)

class ProjectRuleOverridesUpdate(BaseModel):
  values: dict[str, float | str | bool | None] = Field(default_factory=dict, description="Key to figure for this project. A null figure removes the project's figure, so the company's applies again.")
  note: str | None = Field(default=None, max_length=500)

@router.put("/projects/{project_id}/rule-overrides", response_model=CompanyConventionsResponse)
async def put_project_rule_overrides(
  project_id: UUID,
  payload: ProjectRuleOverridesUpdate,
  current_user: User = Depends(require_permission(PermissionKey.CALC_RUN)),
  session: AsyncSession = Depends(get_db),
):
  """Set or clear the figures one project holds in place of the company's. They are read on this project's runs only."""
  cleaned = {k: (None if v is None else checked_override(k, v)) for k, v in payload.values.items()}
  return await CompanyConventionsService(session).update_project(current_user.active_membership.organization_id, current_user.id, project_id, cleaned, payload.note)

class FinishRuleItem(BaseModel):
  key: str = Field(description="A finish rule: finish.floor_item, finish.dado_height_mm, finish.kitchen_band, finish.ceiling_includes, finish.pcc_under, finish.wall_faces or finish.room_type.")
  scope: dict[str, str] = Field(default_factory=dict, description="room_type, level or room_name, as the rule allows.")
  value: float | str | list[str] | dict[str, float] | None = Field(default=None, description="The value; null removes the project's rule.")

class ProjectFinishRulesUpdate(BaseModel):
  rules: list[FinishRuleItem] = Field(default_factory=list)
  note: str | None = Field(default=None, max_length=500)

class ProjectFinishRulesResponse(BaseModel):
  rules: list[FinishRuleItem] = Field(default_factory=list)

@router.get("/projects/{project_id}/finish-rules", response_model=ProjectFinishRulesResponse)
async def get_project_finish_rules(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  from app.modules.drawings_boq import rule_book_service as RBS
  if await ProjectRepository(session).get_by_id_and_org(project_id, current_user.active_membership.organization_id) is None:
    raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
  rows = [RBS.scoped_row(o) for o in await RBS.overrides_of(session, project_id) if o.key.startswith("finish.")]
  return ProjectFinishRulesResponse(rules=[FinishRuleItem(**r) for r in rows])

@router.put("/projects/{project_id}/finish-rules", response_model=ProjectFinishRulesResponse)
async def put_project_finish_rules(
  project_id: UUID,
  payload: ProjectFinishRulesUpdate,
  current_user: User = Depends(require_permission(PermissionKey.CALC_RUN)),
  session: AsyncSession = Depends(get_db),
):
  from app.modules.drawings_boq import rule_book_service as RBS
  if await ProjectRepository(session).get_by_id_and_org(project_id, current_user.active_membership.organization_id) is None:
    raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
  if any(not r.key.startswith("finish.") for r in payload.rules):
    raise TraceException("Only finish rules are set here.", status_code=422, code="FINISH_RULE_REFUSED")
  rows = await RBS.set_scoped(session, project_id, current_user.id, [r.model_dump() for r in payload.rules], payload.note)
  await session.commit()
  return ProjectFinishRulesResponse(rules=[FinishRuleItem(**r) for r in rows if r["key"].startswith("finish.")])

@router.put("/company-conventions", response_model=CompanyConventionsResponse)
async def put_company_conventions(
  payload: CompanyConventionsUpdate,
  current_user: User = Depends(require_permission(PermissionKey.ORGANIZATION_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await CompanyConventionsService(session).update(current_user.active_membership.organization_id, current_user.id, payload)

@router.post("/company-conventions/adopt-qs", response_model=CompanyConventionsResponse)
async def adopt_qs_conventions(
  current_user: User = Depends(require_permission(PermissionKey.ORGANIZATION_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  """Save the QS's figures, as the software holds them, for every convention the company has set nothing for."""
  return await CompanyConventionsService(session).adopt_qs(current_user.active_membership.organization_id, current_user.id)
