from __future__ import annotations
import math
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.calc_repository import CalculationRunRepository
from uuid import UUID
from app.core.exceptions import TraceException
from datetime import datetime, timedelta, timezone
from app.modules.drawings_boq.models import DrawingElement
from app.modules.drawings_boq.recalculation.calc_limits import CalcLimits
from sqlalchemy import select

CALC_BUDGET_ELEMENTS = 20_000
CALC_BUDGET_SECONDS = 300
IMPACT_LIMIT = 500

def _percentile(values: list[float], q: float) -> float | None:
  if not values:
    return None
  ordered = sorted(values)
  k = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
  return round(ordered[k], 2)

def _num(raw) -> float | None:
  try:
    return float(raw) if raw is not None else None
  except (TypeError, ValueError):
    return None

def run_budgets(run, metrics: dict, duration_ms: int | None) -> list[dict]:
  out = []
  secs = None if duration_ms is None else duration_ms / 1000
  out.append({"name": "calculation_time", "limit": float(CALC_BUDGET_SECONDS), "actual": secs, "unit": "s",
    "ok": None if secs is None else secs <= CALC_BUDGET_SECONDS})
  rss = metrics.get("peak_rss_mb")
  budget = float(settings.calc_memory_budget_mb)
  out.append({"name": "peak_memory", "limit": budget, "actual": None if rss is None else float(rss), "unit": "MB",
    "ok": None if rss is None else rss <= budget})
  return out

class CalcInsightService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.runs = CalculationRunRepository(session)

  async def _run(self, org: UUID, run_id: UUID):
    run = await self.runs.get_by_id_and_org(run_id, org)
    if run is None:
      raise TraceException("Calculation run not found.", status_code=404, code="RUN_NOT_FOUND")
    return run

  async def run_metrics(self, org: UUID, run_id: UUID) -> dict:
    run = await self._run(org, run_id)
    stages = await self.runs.list_stages(run_id, org)
    metrics = dict(run.metrics or {})
    timings = dict(metrics.get("timings_ms") or {})
    duration_ms = timings.get("total")
    if duration_ms is None and run.started_at and run.completed_at:
      duration_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)
    return {
      "run_id": run.id, "organization_id": run.organization_id, "project_id": run.project_id, "status": run.status,
      "mode": run.mode, "baseline_run_id": run.baseline_run_id, "engine_version": run.engine_version,
      "fingerprint": run.fingerprint, "attempts": run.attempts, "started_at": run.started_at,
      "completed_at": run.completed_at, "duration_ms": duration_ms,
      "stages": [{"stage": s.stage, "status": s.status, "duration_ms": s.duration_ms, "peak_rss_mb": s.peak_rss_mb}
        for s in stages],
      "timings_ms": timings, "counts": metrics.get("counts") or {}, "allocation": metrics.get("allocation") or {},
      "verify": metrics.get("verify"), "peak_rss_mb": metrics.get("peak_rss_mb"), "failure": metrics.get("failure"),
      "budgets": run_budgets(run, metrics, duration_ms) if run.status in ("COMPLETED", "SUPERSEDED") else [],
    }

  async def org_metrics(self, org: UUID, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = await self.runs.org_run_rows(org, since)
    by_status: dict[str, int] = {}
    by_mode: dict[str, int] = {}
    failures: dict[str, int] = {}
    durations: list[float] = []
    elements = 0
    warnings = 0
    timed_runs = []
    for r in rows:
      by_status[r.status] = by_status.get(r.status, 0) + 1
      if r.status in ("COMPLETED", "SUPERSEDED"):
        by_mode[r.mode] = by_mode.get(r.mode, 0) + 1
        if r.started_at and r.completed_at:
          secs = (r.completed_at - r.started_at).total_seconds()
          durations.append(secs)
          timed_runs.append({"run_id": str(r.id), "project_id": str(r.project_id), "mode": r.mode,
            "duration_seconds": round(secs, 2), "elements": int(_num(r.elements) or 0)})
        elements += int(_num(r.elements) or 0)
        warnings += int(_num(r.warnings) or 0)
      elif r.status == "FAILED":
        failures[r.error_code or "UNKNOWN"] = failures.get(r.error_code or "UNKNOWN", 0) + 1
    finished = sum(by_mode.values())
    timed_runs.sort(key=lambda d: d["duration_seconds"], reverse=True)
    usage = await CalcLimits(self.session).snapshot(org)
    
    return {
      "organization_id": org, "window_days": days, "runs_total": len(rows), "runs_by_status": by_status,
      "runs_by_mode": by_mode, "failure_codes": failures,
      "active_now": sum(v for k, v in by_status.items() if k in ("QUEUED", "RUNNING", "STAGED", "PROMOTED")),
      "duration_seconds": {"p50": _percentile(durations, 0.5), "p95": _percentile(durations, 0.95),
        "max": round(max(durations), 2) if durations else None},
      "elements_processed": elements, "warnings_total": warnings,
      "incremental_share": round(by_mode.get("INCREMENTAL", 0) / finished, 4) if finished else 0.0,
      "slowest_runs": timed_runs[:5], "usage": usage,
    }

  async def usage(self, org: UUID) -> dict:
    return await CalcLimits(self.session).snapshot(org)

  async def impact(self, org: UUID, run_id: UUID, element_id: UUID) -> dict:
    run = await self._run(org, run_id)
    if run.status not in ("COMPLETED", "SUPERSEDED"):
      raise TraceException("Impact is available once a run has completed.", status_code=409, code="RUN_NOT_COMPLETED")
    if not run.state_available:
      raise TraceException("This run did not keep its dependency data.", status_code=409, code="RUN_STATE_UNAVAILABLE")
    if not await self.runs.has_element_state(run_id, org, element_id):
      raise TraceException("Element is not part of this run.", status_code=404, code="ELEMENT_NOT_IN_RUN")
  
    touching = await self.runs.touching(run_id, org, element_id)
    ids = [element_id] + [t[0] for t in touching]
    truncated = len(ids) > IMPACT_LIMIT
    ids = ids[:IMPACT_LIMIT]
    info = {}
    
    if ids:
      res = await self.session.execute(select(DrawingElement.id, DrawingElement.ifc_type, DrawingElement.name,
        DrawingElement.ifc_global_id).where(DrawingElement.id.in_(ids), DrawingElement.organization_id == org))
      info = {r.id: r for r in res.all()}
    overlap = {t[0]: t[1] for t in touching}
    
    def _el(eid):
      r = info.get(eid)
      return {"element_id": eid, "ifc_type": getattr(r, "ifc_type", None), "name": getattr(r, "name", None),
        "ifc_global_id": getattr(r, "ifc_global_id", None),
        "overlap_mm3": float(overlap[eid]) if eid in overlap and overlap[eid] is not None else None}
    ledger = await self.runs.ledger_for_elements(run_id, org, ids)
    return {
      "run_id": run_id, "element_id": element_id,
      "touching": [_el(t[0]) for t in touching[:IMPACT_LIMIT]],
      "affected_ledger": [{"element_id": r.element_id, "work_item_code": r.work_item_code,
        "quantity_net": r.quantity_net, "unit": r.unit, "ledger_id": r.id} for r in ledger[:IMPACT_LIMIT * 4]],
      "truncated": truncated,
    }