from __future__ import annotations
from app.engine.measure import derived as derived_module
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.projects.repository import ProjectRepository
from app.modules.drawings_boq.models import ProjectElementParameter
from app.core.exceptions import TraceException
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from sqlalchemy import delete, select
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User

def allowed() -> dict[str, tuple[float, float, float]]:
  return {n: (derived_module.PARAMS[n][1], derived_module.PARAMS[n][2], derived_module.PARAMS[n][0]) for n in derived_module.ELEMENT_PARAMS}

class ElementParametersResponse(BaseModel):
  values: dict[str, dict[str, float]] = Field(default_factory=dict, description="Element id to the values typed for it.")
  labels: dict[str, str] = Field(default_factory=dict)
  ranges: dict[str, dict[str, float]] = Field(default_factory=dict, description="For each name that can be typed: low, high and the project default.")

class ElementParametersUpdate(BaseModel):
  values: dict[str, dict[str, float | None]] = Field(default_factory=dict,
    description="Element id to name to value. A null value removes that value so the project's applies again.")
  labels: dict[str, str] = Field(default_factory=dict, description="A name to show for the element (its mark), kept with the value.")

class ElementParametersService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.projects = ProjectRepository(session)

  async def _require_project(self, organization_id: UUID, project_id: UUID) -> None:
    if await self.projects.get_by_id_and_org(project_id, organization_id) is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

  async def _rows(self, organization_id: UUID, project_id: UUID) -> list[ProjectElementParameter]:
    return list((await self.session.execute(select(ProjectElementParameter).where(
      ProjectElementParameter.organization_id == organization_id, ProjectElementParameter.project_id == project_id))).scalars().all())

  async def stored_for_run(self, organization_id: UUID, project_id: UUID) -> dict[str, dict[str, float]]:
    known = allowed()
    out: dict[str, dict[str, float]] = {}
    for r in await self._rows(organization_id, project_id):
      if r.code in known:
        out.setdefault(str(r.element_id), {})[r.code] = float(r.value)
    return out

  async def get(self, organization_id: UUID, project_id: UUID) -> ElementParametersResponse:
    await self._require_project(organization_id, project_id)
    rows = await self._rows(organization_id, project_id)
    known = allowed()
    values: dict[str, dict[str, float]] = {}
    labels: dict[str, str] = {}
    for r in rows:
      if r.code in known:
        values.setdefault(str(r.element_id), {})[r.code] = float(r.value)
        if r.label:
          labels[str(r.element_id)] = r.label
    return ElementParametersResponse(values=values, labels=labels,
      ranges={n: {"low": lo, "high": hi, "default": d} for n, (lo, hi, d) in known.items()})

  async def update(self, organization_id: UUID, project_id: UUID, user_id: UUID | None, values: dict, labels: dict[str, str]) -> ElementParametersResponse:
    await self._require_project(organization_id, project_id)
    known = allowed()
    parsed: dict[UUID, dict[str, float | None]] = {}
    
    for eid, items in values.items():
      try:
        key = UUID(str(eid))
      except ValueError:
        raise TraceException(f"'{eid}' is not an element id.", status_code=422, code="INVALID_ELEMENT_ID")
      for code, value in (items or {}).items():
        if code not in known:
          raise TraceException(f"'{code}' cannot be typed for a single element.", status_code=422, code="UNKNOWN_ELEMENT_PARAMETER")
        if value is None:
          continue
      
        low, high, _ = known[code]
        if value != value or not (low <= value <= high):
          raise TraceException(f"{code} must be between {low:g} and {high:g}.", status_code=422, code="ELEMENT_PARAMETER_OUT_OF_RANGE")
      parsed[key] = dict(items or {})
    existing = {(r.element_id, r.code): r for r in await self._rows(organization_id, project_id)}
    for eid, items in parsed.items():
      label = (labels.get(str(eid)) or "")[:120] or None
      for code, value in items.items():
        row = existing.get((eid, code))
        if value is None:
          if row is not None:
            await self.session.execute(delete(ProjectElementParameter).where(ProjectElementParameter.id == row.id))
        elif row is None:
          self.session.add(ProjectElementParameter(id=uuid4(), organization_id=organization_id, project_id=project_id, element_id=eid, code=code,
            value=Decimal(str(value)), label=label, updated_by_user_id=user_id))
        else:
          row.value = Decimal(str(value))
          row.label = label or row.label
          row.updated_by_user_id = user_id
          row.updated_at = datetime.now(timezone.utc)
    await self.session.commit()
    return await self.get(organization_id, project_id)

router = APIRouter(prefix="/drawings-boq", tags=["Drawings & BOQ"])

@router.get("/projects/{project_id}/element-parameters", response_model=ElementParametersResponse)
async def get_element_parameters(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await ElementParametersService(session).get(current_user.active_membership.organization_id, project_id)

@router.put("/projects/{project_id}/element-parameters", response_model=ElementParametersResponse)
async def put_element_parameters(
  project_id: UUID,
  payload: ElementParametersUpdate,
  current_user: User = Depends(require_permission(PermissionKey.CALC_RUN)),
  session: AsyncSession = Depends(get_db),
):
  return await ElementParametersService(session).update(
    current_user.active_membership.organization_id, project_id, current_user.id, payload.values, payload.labels)
