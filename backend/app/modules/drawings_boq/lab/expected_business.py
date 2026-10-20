from __future__ import annotations
from app.modules.drawings_boq.lab import expected as X
import json
from app.core.exceptions import TraceException
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.projects.repository import ProjectRepository
from app.modules.drawings_boq.lab.expected_models import ProjectExpectedBoq
from app.modules.identity.enums import PermissionKey
from app.modules.drawings_boq.models import CalculationRun
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import delete, select
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from fastapi import APIRouter, Body, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from app.modules.drawings_boq.lab import tolerances as T
from app.modules.drawings_boq.lab.bill import parse_bill
from app.modules.drawings_boq.lab.history_service import RunHistoryService
from app.modules.drawings_boq.lab.service import MAX_BILL_BYTES, BillCompareService
from app.modules.identity.models import User

MAX_PER_PROJECT = 50

def _iso(v):
  return v.isoformat() if isinstance(v, datetime) else None

def detail_of(row) -> dict:
  tol = dict(row.tolerances or {})
  every = float(row.default_tolerance_pct) if row.default_tolerance_pct is not None else None
  lines = list(row.lines or [])
  table = X.tolerance_table(lines, tol, every)
  fams = [{**f, "tolerance_pct": table[f["key"]][0], "tolerance_from": table[f["key"]][1], "default_pct": T.default_for(f["key"])} for f in X.families(lines)]
  return {"id": str(row.id), "name": row.name, "source": row.source, "default_tolerance_pct": every, "tolerances": tol, "families": fams, "rows": len(lines),
    "updated_at": _iso(getattr(row, "updated_at", None))}

def summary_of(row) -> dict:
  d = detail_of(row)
  return {k: d[k] for k in ("id", "name", "source", "default_tolerance_pct", "rows", "updated_at")} | {"family_count": len(d["families"])}

def read_upload(filename: str | None, data: bytes) -> tuple:
  """(lines, unmapped, source document) from a QS workbook or from a stored expected BOQ (.json)."""
  if len(data) > MAX_BILL_BYTES:
    raise TraceException("The file is too large.", status_code=413, code="BILL_TOO_LARGE")
  if (filename or "").lower().endswith(".json"):
    try:
      doc = X.validate(json.loads(data.decode("utf-8")))
    except ValueError as e:
      raise TraceException("This file is not an expected BOQ that can be read.", status_code=422, code=str(e) if str(e).startswith("EXPECTED_") else "EXPECTED_UNREADABLE")
    return doc["lines"], [], doc
  try:
    bill = parse_bill(data)
  except ValueError as e:
    raise TraceException("The bill could not be read. It needs a summary sheet with Description, Unit and Quantity columns.", status_code=422, code=str(e))
  except Exception:
    raise TraceException("The file could not be opened as an Excel workbook.", status_code=422, code="BILL_UNREADABLE")
  lines, unmapped = X.from_bill(bill.lines)
  return lines, unmapped, None

class TolerancesIn(BaseModel):
  default_tolerance_pct: float | None = Field(default=None, ge=0, le=100, description="One tolerance for every family that has none of its own. Empty: the starting values.")
  tolerances: dict[str, float | None] = Field(default_factory=dict, description="Family key to percentage. Null removes the family's own value.")

def merge_tolerances(existing: dict, given: dict) -> dict:
  out = dict(existing or {})
  for k, v in (given or {}).items():
    if v is None:
      out.pop(k, None)
    else:
      out.update(T.clean({k: v}))
  return out

class ExpectedBoqService:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def _require_project(self, org: UUID, project_id: UUID) -> None:
    if await ProjectRepository(self.session).get_by_id_and_org(project_id, org) is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

  async def _rows(self, org: UUID, project_id: UUID) -> list:
    return list((await self.session.execute(select(ProjectExpectedBoq).where(
      ProjectExpectedBoq.organization_id == org, ProjectExpectedBoq.project_id == project_id).order_by(ProjectExpectedBoq.name))).scalars().all())

  async def _one(self, org: UUID, project_id: UUID, expected_id: UUID) -> ProjectExpectedBoq:
    await self._require_project(org, project_id)
    row = (await self.session.execute(select(ProjectExpectedBoq).where(
      ProjectExpectedBoq.organization_id == org, ProjectExpectedBoq.project_id == project_id, ProjectExpectedBoq.id == expected_id))).scalar_one_or_none()
    if row is None:
      raise TraceException("Expected BOQ not found.", status_code=404, code="EXPECTED_BOQ_NOT_FOUND")
    return row

  async def list_for_project(self, org: UUID, project_id: UUID) -> dict:
    await self._require_project(org, project_id)
    return {"items": [summary_of(r) for r in await self._rows(org, project_id)]}

  async def get(self, org: UUID, project_id: UUID, expected_id: UUID) -> dict:
    return detail_of(await self._one(org, project_id, expected_id))

  async def save(self, org: UUID, project_id: UUID, user_id: UUID | None, filename: str | None, data: bytes, name: str | None,
      default_pct: float | None, tolerances: dict | None) -> dict:
    await self._require_project(org, project_id)
    lines, unmapped, doc = read_upload(filename, data)
    if not lines:
      raise TraceException("No line of this file belongs to an item family.", status_code=422, code="EXPECTED_NO_LINES")
    title = (name or (doc or {}).get("name") or (filename or "Expected BOQ").rsplit(".", 1)[0]).strip()[:160] or "Expected BOQ"
    rows = await self._rows(org, project_id)
    same = next((r for r in rows if r.name == title), None)
    tol = T.clean(tolerances) if tolerances else T.clean((doc or {}).get("tolerances"))
    every = T.clamp(default_pct) if T.clamp(default_pct) is not None else (doc or {}).get("default_tolerance_pct")
    if same is None:
      if len(rows) >= MAX_PER_PROJECT:
        raise TraceException(f"A project can keep {MAX_PER_PROJECT} expected BOQs. Remove some first.", status_code=422, code="EXPECTED_TOO_MANY")
      same = ProjectExpectedBoq(id=uuid4(), organization_id=org, project_id=project_id, name=title, source=(filename or "")[:255] or None, lines=lines, tolerances=tol,
        default_tolerance_pct=every, updated_by_user_id=user_id)
      self.session.add(same)
      
    else:
      same.lines, same.source, same.updated_by_user_id = lines, (filename or "")[:255] or same.source, user_id
      if tolerances or doc:
        same.tolerances = tol
      if every is not None:
        same.default_tolerance_pct = every
    await self.session.commit()
    await self.session.refresh(same)
    return {**detail_of(same), "unmapped": unmapped}

  async def set_tolerances(self, org: UUID, project_id: UUID, user_id: UUID | None, expected_id: UUID, body: TolerancesIn) -> dict:
    row = await self._one(org, project_id, expected_id)
    row.tolerances = merge_tolerances(row.tolerances, body.tolerances)
    row.default_tolerance_pct = body.default_tolerance_pct
    row.updated_by_user_id = user_id
    await self.session.commit()
    await self.session.refresh(row)
    return detail_of(row)

  async def remove(self, org: UUID, project_id: UUID, expected_id: UUID) -> dict:
    await self._require_project(org, project_id)
    await self.session.execute(delete(ProjectExpectedBoq).where(
      ProjectExpectedBoq.organization_id == org, ProjectExpectedBoq.project_id == project_id, ProjectExpectedBoq.id == expected_id))
    await self.session.commit()
    return await self.list_for_project(org, project_id)

  async def export(self, org: UUID, project_id: UUID, expected_id: UUID) -> dict:
    row = await self._one(org, project_id, expected_id)
    return X.document(row.name, row.source or "", row.lines, row.tolerances, float(row.default_tolerance_pct) if row.default_tolerance_pct is not None else None)

  async def check(self, org: UUID, user_id: UUID | None, run_id: UUID, expected_id: UUID, classes: dict | None) -> dict:
    run = (await self.session.execute(select(CalculationRun).where(CalculationRun.id == run_id, CalculationRun.organization_id == org))).scalar_one_or_none()
    if run is None:
      raise TraceException("Calculation run not found.", status_code=404, code="RUN_NOT_FOUND")
    row = await self._one(org, run.project_id, expected_id)
    rows = await BillCompareService(self.session)._rows(org, run_id)
    every = float(row.default_tolerance_pct) if row.default_tolerance_pct is not None else None
    out = X.check(list(row.lines or []), rows, dict(row.tolerances or {}), every, None, classes)
    out.update({"expected_id": str(row.id), "expected_name": row.name, "run_id": str(run_id), "software_rows": len(rows)})
    await RunHistoryService(self.session).record_compare(org, user_id, run_id, "EXPECTED", row.name, out)
    return out

router = APIRouter(prefix="/drawings-boq", tags=["Drawings & BOQ"])

def _json_object(raw: str | None, what: str) -> dict | None:
  if not raw:
    return None
  try:
    v = json.loads(raw)
  except ValueError:
    raise TraceException(f"{what} must be valid JSON.", status_code=422, code="BAD_JSON")
  if not isinstance(v, dict):
    raise TraceException(f"{what} must be an object.", status_code=422, code="BAD_JSON")
  return v

@router.get("/projects/{project_id}/expected-boq")
async def list_expected_boq(project_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await ExpectedBoqService(session).list_for_project(current_user.active_membership.organization_id, project_id)

@router.post("/projects/{project_id}/expected-boq")
async def save_expected_boq(
  project_id: UUID,
  file: UploadFile = File(...),
  name: str | None = Form(default=None),
  default_tolerance_pct: float | None = Form(default=None),
  tolerances: str | None = Form(default=None),
  current_user: User = Depends(require_permission(PermissionKey.CALC_RUN)),
  session: AsyncSession = Depends(get_db),
):
  data = await file.read()
  return await ExpectedBoqService(session).save(current_user.active_membership.organization_id, project_id, current_user.id, file.filename, data, name,
    default_tolerance_pct, _json_object(tolerances, "tolerances"))

@router.get("/projects/{project_id}/expected-boq/{expected_id}")
async def get_expected_boq(project_id: UUID, expected_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await ExpectedBoqService(session).get(current_user.active_membership.organization_id, project_id, expected_id)

@router.put("/projects/{project_id}/expected-boq/{expected_id}/tolerances")
async def put_expected_boq_tolerances(project_id: UUID, expected_id: UUID, payload: TolerancesIn,
    current_user: User = Depends(require_permission(PermissionKey.CALC_RUN)), session: AsyncSession = Depends(get_db)):
  return await ExpectedBoqService(session).set_tolerances(current_user.active_membership.organization_id, project_id, current_user.id, expected_id, payload)

@router.delete("/projects/{project_id}/expected-boq/{expected_id}")
async def delete_expected_boq(project_id: UUID, expected_id: UUID, current_user: User = Depends(require_permission(PermissionKey.CALC_RUN)), session: AsyncSession = Depends(get_db)):
  return await ExpectedBoqService(session).remove(current_user.active_membership.organization_id, project_id, expected_id)

@router.get("/projects/{project_id}/expected-boq/{expected_id}/export")
async def export_expected_boq(project_id: UUID, expected_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  doc = await ExpectedBoqService(session).export(current_user.active_membership.organization_id, project_id, expected_id)
  return Response(content=json.dumps(doc, indent=2), media_type="application/json", headers={"Content-Disposition": 'attachment; filename="expected-boq.json"'})

@router.post("/calculation-runs/{run_id}/check-expected-boq/{expected_id}")
async def check_expected_boq(run_id: UUID, expected_id: UUID, classes: dict | None = Body(default=None),
    current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await ExpectedBoqService(session).check(current_user.active_membership.organization_id, current_user.id, run_id, expected_id, classes)
