from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.drawings_boq.models import CalculationRun, BuildingLevel, Drawing, DrawingElement, MeasurementRuleSet, QuantityLedger, ReviewIssue
from app.modules.projects.repository import ProjectRepository
from app.modules.drawings_boq.difference import diff as D
from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.core.exceptions import TraceException
from app.modules.drawings_boq.finish_schedule.common import work_item_catalog
from app.modules.drawings_boq.difference import export as X
from app.modules.drawings_boq.difference import fixlist as F
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User

DONE = ("COMPLETED", "PROMOTED")
RUN_LIST_CAP = 40
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def run_label(run: dict) -> str:
  when = (run.get("completed_at") or "")[:16].replace("T", " ")
  names = ", ".join(d.get("name") or "drawing" for d in run.get("drawings") or [])
  return f"{when} {names}".strip() or str(run.get("id"))[:8]

def clamp_pct(value, default: float, high: float = 100.0) -> float:
  try:
    v = float(value)
  except (TypeError, ValueError):
    return default
  return default if v != v else max(0.0, min(v, high))

class RunDifferenceService:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def _run(self, org: UUID, run_id: UUID) -> CalculationRun:
    run = (await self.session.execute(select(CalculationRun).where(CalculationRun.id == run_id, CalculationRun.organization_id == org))).scalar_one_or_none()
    if run is None:
      raise TraceException("Calculation run not found.", status_code=404, code="RUN_NOT_FOUND")
    return run

  async def _drawings(self, org: UUID, ids) -> dict:
    if not ids:
      return {}
    rows = (await self.session.execute(select(Drawing).where(Drawing.organization_id == org, Drawing.id.in_(list(ids))))).scalars().all()
    return {str(d.id): {"id": str(d.id), "name": d.original_filename, "revision_label": d.revision_label, "revision_group_id": str(d.revision_group_id) if d.revision_group_id else None,
      "is_current": bool(d.is_current_revision)} for d in rows}

  async def runs(self, org: UUID, project_id: UUID) -> dict:
    if await ProjectRepository(self.session).get_by_id_and_org(project_id, org) is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
    found = (await self.session.execute(select(CalculationRun).where(CalculationRun.organization_id == org, CalculationRun.project_id == project_id, CalculationRun.status.in_(DONE))
      .order_by(CalculationRun.completed_at.desc().nullslast(), CalculationRun.created_at.desc()).limit(RUN_LIST_CAP))).scalars().all()
    
    ids = {str(i) for r in found for i in (r.drawing_revision_ids or [])}
    drawings = await self._drawings(org, ids)
    out = []
    for r in found:
      item = {"id": str(r.id), "completed_at": r.completed_at.isoformat() if r.completed_at else None, "convention_code": r.convention_code, "engine_version": r.engine_version,
        "drawings": [drawings[str(i)] for i in (r.drawing_revision_ids or []) if str(i) in drawings]}
      item["label"] = run_label(item)
      out.append(item)
    return {"runs": out}

  async def _rows(self, org: UUID, run_id: UUID) -> list:
    q = (select(QuantityLedger.work_item_code, QuantityLedger.unit, QuantityLedger.source_kind, QuantityLedger.quantity_net, QuantityLedger.trace,
        BuildingLevel.name, DrawingElement.ifc_global_id, DrawingElement.name)
      .outerjoin(BuildingLevel, BuildingLevel.id == QuantityLedger.level_id)
      .outerjoin(DrawingElement, DrawingElement.id == QuantityLedger.element_id)
      .where(QuantityLedger.run_id == run_id, QuantityLedger.organization_id == org))
    return [D.row_from(code, unit, src, qty, lvl, trace, gid, ename) for code, unit, src, qty, trace, lvl, gid, ename in (await self.session.execute(q)).all()]

  async def _context(self, org: UUID, run: CalculationRun) -> dict:
    code = None
    if run.rule_set_id:
      code = (await self.session.execute(select(MeasurementRuleSet.code).where(MeasurementRuleSet.id == run.rule_set_id))).scalar_one_or_none()
    return {"id": str(run.id), "convention_code": run.convention_code, "engine_version": run.engine_version, "rule_set_code": code,
      "drawing_revision_ids": [str(i) for i in run.drawing_revision_ids or []], "settings": run.settings or {},
      "completed_at": run.completed_at.isoformat() if run.completed_at else None}

  async def difference(self, org: UUID, from_run: UUID, to_run: UUID, same_pct, min_change_pct) -> dict:
    if from_run == to_run:
      raise TraceException("Choose two different runs.", status_code=422, code="DIFFERENCE_SAME_RUN")
    a, b = await self._run(org, from_run), await self._run(org, to_run)
    if a.project_id != b.project_id:
      raise TraceException("The two runs belong to different projects.", status_code=422, code="DIFFERENCE_OTHER_PROJECT")
    if a.status not in DONE or b.status not in DONE:
      raise TraceException("Both runs must be completed.", status_code=422, code="DIFFERENCE_RUN_NOT_COMPLETED")
  
    rows_a, rows_b = await self._rows(org, a.id), await self._rows(org, b.id)
    catalog = await work_item_catalog(self.session, org, {r["code"] for r in rows_a + rows_b})
    ca, cb = await self._context(org, a), await self._context(org, b)
    drawings = await self._drawings(org, set(ca["drawing_revision_ids"]) | set(cb["drawing_revision_ids"]))
    out = D.diff_runs(rows_a, rows_b, clamp_pct(same_pct, D.SAME_PCT, 10.0), {c: w.description for c, w in catalog.items()})
    out["causes"] = D.causes_of(ca, cb, drawings)
    labels = {"from": run_label({**ca, "drawings": [drawings[i] for i in ca["drawing_revision_ids"] if i in drawings]}),
      "to": run_label({**cb, "drawings": [drawings[i] for i in cb["drawing_revision_ids"] if i in drawings]})}
    
    out["from_run"], out["to_run"], out["labels"] = str(a.id), str(b.id), labels
    out["variation"] = D.variation_of(out, clamp_pct(min_change_pct, D.MIN_CHANGE_PCT, 100.0), out["causes"], labels)
    return out

  async def fix_list(self, org: UUID, run_id: UUID) -> dict:
    run = await self._run(org, run_id)
    found = (await self.session.execute(select(ReviewIssue).where(ReviewIssue.organization_id == org, ReviewIssue.calculation_run_id == run.id, ReviewIssue.status == "OPEN")
      .order_by(ReviewIssue.created_at))).scalars().all()
    issues = [{"id": str(i.id), "code": i.code, "severity": i.severity, "blocks": i.blocks, "message": i.message, "suggested_fix": i.suggested_fix, "details": i.details or {}} for i in found]
    wanted = {str(l) for i in issues for l in (i["details"].get("ledger_ids") or [])[:F.LEDGER_CAP]}
    ledger: dict = {}
    
    if wanted:
      q = (select(QuantityLedger.id, QuantityLedger.work_item_code, QuantityLedger.trace, BuildingLevel.name, DrawingElement.name)
        .outerjoin(BuildingLevel, BuildingLevel.id == QuantityLedger.level_id).outerjoin(DrawingElement, DrawingElement.id == QuantityLedger.element_id)
        .where(QuantityLedger.organization_id == org, QuantityLedger.run_id == run.id, QuantityLedger.id.in_([UUID(x) for x in wanted])))
      for lid, code, trace, lvl, ename in (await self.session.execute(q)).all():
        ledger[str(lid)] = D.row_from(code, "", None, 0, lvl, trace, None, ename)
    places = {i["id"]: F.places_of([ledger[str(l)] for l in (i["details"].get("ledger_ids") or [])[:F.LEDGER_CAP] if str(l) in ledger]) for i in issues}
    out = F.fix_list(issues, places)
    out["run_id"] = str(run.id)
    out["text"] = F.as_text(out)
    return out

router = APIRouter(prefix="/drawings-boq", tags=["Drawings & BOQ"])

@router.get("/projects/{project_id}/difference/runs")
async def difference_runs(project_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await RunDifferenceService(session).runs(current_user.active_membership.organization_id, project_id)

@router.get("/run-difference")
async def run_difference(from_run_id: UUID, to_run_id: UUID, same_pct: float | None = Query(default=None), min_change_pct: float | None = Query(default=None),
    current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await RunDifferenceService(session).difference(current_user.active_membership.organization_id, from_run_id, to_run_id, same_pct, min_change_pct)

@router.post("/run-difference/export")
async def export_run_difference(kind: str = Query(default="difference", pattern="^(difference|variation)$"), result: dict = Body(...),
    current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ))):
  if kind == "variation":
    data, name = X.variation_xlsx(result.get("variation") if "variation" in result else result), "variation-statement.xlsx"
  else:
    data, name = X.difference_xlsx(result), "run-difference.xlsx"
  return Response(content=data, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})

@router.get("/calculation-runs/{run_id}/fix-list")
async def run_fix_list(run_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await RunDifferenceService(session).fix_list(current_user.active_membership.organization_id, run_id)

@router.post("/fix-list/export")
async def export_fix_list(fix: dict = Body(...), current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ))):
  return Response(content=X.fixlist_xlsx(fix), media_type=XLSX, headers={"Content-Disposition": 'attachment; filename="drawing-queries.xlsx"'})
