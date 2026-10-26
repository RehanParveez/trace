from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import func, select
from app.modules.drawings_boq.models import CalculationRun, RunStageLog, QuantityLedger, TakeoffCandidate, TakeoffMeasurement, TakeoffSheet
from app.core.exceptions import TraceException
from app.modules.drawings_boq import bill_completeness as BC
from app.modules.drawings_boq.takeoff.printed_service import spec_facts_for_project

MAX_DRAWINGS = 6

class BillCompletenessService:
  """Reads a finished run and says what keeps its bill short."""

  def __init__(self, session: AsyncSession):
    self.session = session

  async def for_run(self, org: UUID, run_id: UUID) -> dict:
    run = (await self.session.execute(select(CalculationRun).where(CalculationRun.id == run_id, CalculationRun.organization_id == org))).scalar_one_or_none()
    if run is None:
      raise TraceException("Calculation run not found.", status_code=404, code="CALCULATION_RUN_NOT_FOUND")
    stage_rows = (await self.session.execute(select(RunStageLog).where(RunStageLog.run_id == run_id, RunStageLog.organization_id == org).order_by(RunStageLog.started_at.asc()))).scalars().all()
    stages = [{"stage": s.stage, "status": s.status, "counts": dict(s.counts or {})} for s in stage_rows]
    ledger = [{"code": code, "unit": unit, "qty": str(qty), "rows": int(n)} for code, unit, qty, n in (await self.session.execute(
      select(QuantityLedger.work_item_code, QuantityLedger.unit, func.sum(QuantityLedger.quantity_net), func.count())
      .where(QuantityLedger.run_id == run_id, QuantityLedger.organization_id == org)
      .group_by(QuantityLedger.work_item_code, QuantityLedger.unit))).all()]

    funnel = await self._funnel(org, run.project_id)
    held = await self._held(org, run.project_id)
    stats = dict(run.stats or {})
    out = BC.build(stages=stages, run_settings=dict(run.settings or {}), ledger=ledger, funnel=funnel, held_by_reason=held,
      derived=stats.get("derived") if isinstance(stats.get("derived"), dict) else None, boq_error=stats.get("boq_error") or None)
    return {"run_id": run_id, **out}

  async def _spec(self, org: UUID, project_id: UUID, run_id: UUID) -> dict:
    out = {"waterproof_pages": [], "chajja_accepted": 0, "chajja_formwork_rows": 0}
    try:
      out["waterproof_pages"] = (await spec_facts_for_project(self.session, org, project_id))["waterproof_pages"]
      cands = (await self.session.execute(select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org, TakeoffCandidate.project_id == project_id,
        TakeoffCandidate.category == "SITE", TakeoffCandidate.decision == "ACCEPTED"))).scalars().all()
      out["chajja_accepted"] = sum(1 for c in cands if (c.facts or {}).get("site_kind") == "CHAJJA")
      if out["chajja_accepted"]:
        rows = (await self.session.execute(select(QuantityLedger.spec).where(QuantityLedger.run_id == run_id, QuantityLedger.organization_id == org,
          QuantityLedger.work_item_code.like("FRM-%")))).scalars().all()
        out["chajja_formwork_rows"] = sum(1 for s in rows if (s or {}).get("category") == "CHAJJA")
    except Exception:
      return {"waterproof_pages": [], "chajja_accepted": 0, "chajja_formwork_rows": 0}
    return out

  async def _funnel(self, org: UUID, project_id: UUID) -> dict:
    meas = dict((await self.session.execute(select(TakeoffMeasurement.status, func.count()).where(TakeoffMeasurement.organization_id == org, TakeoffMeasurement.project_id == project_id)
      .group_by(TakeoffMeasurement.status))).all())
    undecided = (await self.session.execute(select(func.count()).select_from(TakeoffCandidate).where(TakeoffCandidate.organization_id == org, TakeoffCandidate.project_id == project_id,
      TakeoffCandidate.decision == "NEW"))).scalar_one()
    return {"confirmed": int(meas.get("CONFIRMED", 0)), "draft": int(sum(v for k, v in meas.items() if k != "CONFIRMED")), "undecided": int(undecided)}

  async def _held(self, org: UUID, project_id: UUID) -> dict:
    from app.modules.drawings_boq.takeoff.extract.crosschecks_service import CrossCheckService
    ids = [r[0] for r in (await self.session.execute(select(TakeoffSheet.drawing_id).distinct().join(TakeoffCandidate, TakeoffCandidate.sheet_id == TakeoffSheet.id)
      .where(TakeoffCandidate.organization_id == org, TakeoffCandidate.project_id == project_id, TakeoffCandidate.decision == "NEW"))).all()][:MAX_DRAWINGS]

    out: dict = {}
    for drawing_id in ids:
      try:
        view = await CrossCheckService(self.session).ready_to_accept(org, drawing_id)
      except Exception:
        continue
      for item in view.get("held", []):
        codes = [r["code"] for r in item.get("reasons", [])]
        if codes and "ALREADY_DECIDED" not in codes:
          out[codes[0]] = out.get(codes[0], 0) + 1
    return out
