from __future__ import annotations
import re
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.projects.repository import ProjectRepository
from app.modules.drawings_boq.models import ProjectDatum
from decimal import Decimal
from app.engine.measure import stages as stages_module
from datetime import datetime, timezone
from app.core.exceptions import TraceException
from fastapi import APIRouter, Depends
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from sqlalchemy import delete, select
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User

TYPED, RUN = "TYPED", "RUN"
NAME = re.compile(r"^(FFL|DPC|LINTEL|PARAPET_TOP|SLAB_(?:[1-9]|[1-3][0-9]))$")
ORDER = ("FFL", "DPC", "LINTEL")
EXPLAIN = {
  "FFL": "Finished floor level of the lowest storey",
  "DPC": "Damp-proof course level",
  "LINTEL": "Level of the lintels (top of the openings) on the lowest storey",
  "PARAPET_TOP": "Top of the roof parapet",
  "MUMTY_SLAB": "Top of the stair room (mumty) slab, found from the model; it is shown, it cannot be typed",
}

def rank(name: str) -> tuple:
  if name in ORDER:
    return (0, ORDER.index(name), 0)
  m = re.match(r"^SLAB_(\d+)$", name)
  if m:
    return (1, int(m.group(1)), 0)
  return (2, 0, 0 if name == "PARAPET_TOP" else 1)

class DatumView(BaseModel):
  name: str
  label: str
  typed_z_mm: float | None = None
  run_z_mm: float | None = None
  run_basis: str | None = Field(default=None, description="How the last run found the level: model, drawing, param, default or typed.")
  run_note: str | None = None
  editable: bool = True

class DatumsResponse(BaseModel):
  datums: list[DatumView] = Field(default_factory=list)
  typed: dict[str, float] = Field(default_factory=dict)
  run_id: UUID | None = None
  recorded_at: datetime | None = None

class DatumsUpdate(BaseModel):
  values: dict[str, float | None] = Field(default_factory=dict,
    description="Datum name to level in millimetres. A null value removes the level you typed so the run finds it again.")

LEVEL_PREFIX = "LEVEL:"

def label_of(name: str) -> str:
  if name in EXPLAIN:
    return EXPLAIN[name]
  if name.startswith(LEVEL_PREFIX):
    return f"Level of the {name[len(LEVEL_PREFIX):].lower()} floor"
  m = re.match(r"^SLAB_(\d+)$", name)
  return f"Top of floor slab {m.group(1)}" if m else name

def _stage_datums(stats: dict) -> list[dict]:
  stages = (stats or {}).get("stages") or {}
  if stages.get("resolved"):
    return list(stages.get("datums") or [])
  pdf = ((stats or {}).get("pdf_space") or {}).get("datums") or {}
  for group in sorted(pdf):
    if (pdf[group] or {}).get("resolved"):
      return list(pdf[group].get("datums") or [])
  return []

def _source_line(s: dict) -> str:
  how = {"TYPED": "typed", "SUM_OF_STOREYS": "worked out from the storey height next to it", "AT_DATUM": "the datum", "TYPICAL": "typical storey"}.get(str(s.get("how")), "printed")
  return f"{s.get('kind')} {s.get('field')} {s.get('value')} ({how}{', used' if s.get('used') else ''})"

def levels_of_stats(stats: dict) -> list[dict]:
  groups = ((stats or {}).get("pdf_space") or {}).get("levels") or {}
  out: dict = {}
  for group in sorted(groups):
    for row in groups[group] or []:
      key = str(row.get("key") or "")
      if not key or key in out or row.get("level_mm") is None:
        continue
      sources = [s for s in row.get("sources") or [] if s.get("field") == "level_mm"]
      used = next((s for s in sources if s.get("used")), None)
      kind = "typed" if used and used.get("how") == "TYPED" else "default" if used and used.get("how") == "AT_DATUM" else "drawing"
      open_q = [d for d in row.get("decisions") or [] if d.get("chosen") is None]
      text = "; ".join(_source_line(s) for s in sources)
      for d in open_q:
        text = f"OPEN: {d.get('question')}: " + " or ".join(f"{o.get('value')} ({'/'.join(o.get('sources') or [])})" for o in d.get("options") or []) + ". The most trusted is used until you decide. " + text
      out[key] = {"name": LEVEL_PREFIX + key, "z_mm": float(row["level_mm"]), "source": kind, "note": text[:300] or None}
  return list(out.values())

def datums_of_stats(stats: dict) -> list[dict]:
  return _stage_datums(stats) + levels_of_stats(stats)

class DatumsService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.projects = ProjectRepository(session)

  async def _require_project(self, organization_id: UUID, project_id: UUID) -> None:
    if await self.projects.get_by_id_and_org(project_id, organization_id) is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

  async def _rows(self, organization_id: UUID, project_id: UUID) -> list[ProjectDatum]:
    return list((await self.session.execute(select(ProjectDatum).where(
      ProjectDatum.organization_id == organization_id, ProjectDatum.project_id == project_id))).scalars().all())

  async def stored_for_run(self, organization_id: UUID, project_id: UUID) -> dict[str, float]:
    return {r.name: float(r.z_mm) for r in await self._rows(organization_id, project_id) if r.source == TYPED}

  async def get(self, organization_id: UUID, project_id: UUID) -> DatumsResponse:
    await self._require_project(organization_id, project_id)
    rows = await self._rows(organization_id, project_id)
    typed = {r.name: r for r in rows if r.source == TYPED}
    ran = {r.name: r for r in rows if r.source == RUN}
    out = []
    
    for name in sorted(set(typed) | set(ran), key=lambda n: (rank(n), n)):
      t, r = typed.get(name), ran.get(name)
      out.append(DatumView(name=name, label=label_of(name), typed_z_mm=float(t.z_mm) if t else None, run_z_mm=float(r.z_mm) if r else None,
        run_basis=r.basis if r else None, run_note=r.note if r else None, editable=bool(NAME.match(name))))
    latest = max((r for r in ran.values()), key=lambda r: r.updated_at, default=None)
    return DatumsResponse(datums=out, typed={n: float(r.z_mm) for n, r in typed.items()}, run_id=latest.run_id if latest else None,
      recorded_at=latest.updated_at if latest else None)

  async def update(self, organization_id: UUID, project_id: UUID, user_id: UUID | None, values: dict[str, float | None]) -> DatumsResponse:
    await self._require_project(organization_id, project_id)
    low, high = stages_module.OVERRIDE_RANGE
    for name, value in values.items():
      if not NAME.match(name):
        raise TraceException(f"'{name}' is not a datum that can be typed.", status_code=422, code="UNKNOWN_DATUM")
      if value is not None and (value != value or not (low <= value <= high)):
        raise TraceException(f"{name} must be between {low:g} and {high:g} mm.", status_code=422, code="DATUM_OUT_OF_RANGE")
    existing = {r.name: r for r in await self._rows(organization_id, project_id) if r.source == TYPED}
    for name, value in values.items():
      row = existing.get(name)
      if value is None:
        if row is not None:
          await self.session.execute(delete(ProjectDatum).where(ProjectDatum.id == row.id))
      elif row is None:
        self.session.add(ProjectDatum(id=uuid4(), organization_id=organization_id, project_id=project_id, name=name, source=TYPED,
          z_mm=Decimal(str(value)), basis="typed", updated_by_user_id=user_id))
      else:
        row.z_mm = Decimal(str(value))
        row.updated_by_user_id = user_id
        row.updated_at = datetime.now(timezone.utc)
    await self.session.commit()
    return await self.get(organization_id, project_id)

  async def record_run(self, organization_id: UUID, project_id: UUID, run_id: UUID, stats: dict) -> int:
    used = [d for d in datums_of_stats(stats) if d.get("name") and d.get("z_mm") is not None]
    
    if not used:
      return 0
    await self.session.execute(delete(ProjectDatum).where(
      ProjectDatum.organization_id == organization_id, ProjectDatum.project_id == project_id, ProjectDatum.source == RUN))
    for d in used:
      self.session.add(ProjectDatum(id=uuid4(), organization_id=organization_id, project_id=project_id, name=str(d["name"])[:40], source=RUN,
        z_mm=Decimal(str(d["z_mm"])), basis=str(d.get("source") or "")[:20] or None, note=(d.get("note") or None) and str(d["note"])[:300], run_id=run_id))
    await self.session.flush()
    return len(used)

router = APIRouter(prefix="/drawings-boq", tags=["Drawings & BOQ"])

@router.get("/projects/{project_id}/datums", response_model=DatumsResponse)
async def get_datums(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await DatumsService(session).get(current_user.active_membership.organization_id, project_id)

@router.put("/projects/{project_id}/datums", response_model=DatumsResponse)
async def put_datums(
  project_id: UUID,
  payload: DatumsUpdate,
  current_user: User = Depends(require_permission(PermissionKey.CALC_RUN)),
  session: AsyncSession = Depends(get_db),
):
  return await DatumsService(session).update(current_user.active_membership.organization_id, project_id, current_user.id, payload.values)
