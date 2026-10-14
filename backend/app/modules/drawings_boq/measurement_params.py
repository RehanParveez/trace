from __future__ import annotations
from app.engine.measure import derived as derived_module
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from uuid import UUID, uuid4
from app.modules.drawings_boq.models import ProjectMeasurementParameter
from decimal import Decimal
from app.modules.projects.repository import ProjectRepository
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.core.exceptions import TraceException
from app.core.database import get_db
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.dependencies.permissions import require_permission

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
    return MeasurementParametersResponse(values={k: v for k, v in stored.items() if k in known}, defaults=self.defaults())

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
