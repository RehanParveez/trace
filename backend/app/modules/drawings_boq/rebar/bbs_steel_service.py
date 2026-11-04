from __future__ import annotations
from uuid import UUID
from sqlalchemy import func, select
from app.modules.drawings_boq.rebar.bbs_report_service import BbsReportService
from app.modules.drawings_boq.rebar.bbs_match_service import BbsMatchService
from app.modules.audit.service import AuditLogService
from app.modules.drawings_boq.models import QuantityLedger, CalculationRun
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.engine.measure.rebar import FORMULA_BBS, FORMULA_ESTIMATE, REBAR_WORK_ITEM
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.rebar.bbs_models import RebarBbsDocument
from app.modules.drawings_boq.rebar import bbs_audited as BA
from app.modules.drawings_boq.finish_schedule.common import audit_entity

SOURCE_KEY = "steel_source"

class SteelFiguresService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.report = BbsReportService(session)
    self.match = BbsMatchService(session)
    self.audit_log = AuditLogService(session)

  async def _run(self, org: UUID, run_id: UUID) -> CalculationRun:
    run = (await self.session.execute(select(CalculationRun).where(CalculationRun.id == run_id, CalculationRun.organization_id == org))).scalar_one_or_none()
    if run is None:
      raise TraceException("Calculation run not found.", status_code=404, code="RUN_NOT_FOUND")
    return run

  async def ledger_kg(self, org: UUID, run_id: UUID) -> dict:
    q = (select(QuantityLedger.formula_code, func.sum(QuantityLedger.quantity_net))
      .where(QuantityLedger.run_id == run_id, QuantityLedger.organization_id == org, QuantityLedger.work_item_code == REBAR_WORK_ITEM,
        QuantityLedger.formula_code.in_((FORMULA_BBS, FORMULA_ESTIMATE))).group_by(QuantityLedger.formula_code))
    return {code: kg for code, kg in (await self.session.execute(q)).all()}

  async def latest_document(self, org: UUID, project_id: UUID) -> RebarBbsDocument | None:
    return (await self.session.execute(select(RebarBbsDocument).where(RebarBbsDocument.project_id == project_id, RebarBbsDocument.organization_id == org,
      RebarBbsDocument.status == "ACTIVE").order_by(RebarBbsDocument.version.desc()).limit(1))).scalar_one_or_none()

  async def chosen_source(self, org: UUID, project_id: UUID) -> str | None:
    value = (await self.match.decisions(org, project_id)).get(SOURCE_KEY)
    return value.get("source") if isinstance(value, dict) else None

  async def figures(self, org: UUID, run_id: UUID, source: str | None = None, wastage_pct=None) -> dict:
    run = await self._run(org, run_id)
    ledger = await self.ledger_kg(org, run_id)
    requested = source or await self.chosen_source(org, run.project_id)
    doc = await self.latest_document(org, run.project_id)
    rows = sheets = None
    
    findings: list = []
    has_run = False
    info = None
    if doc is not None:
      c = await self.report._data(org, doc.id)
      rows, sheets, findings, has_run = c["rows"], c["sheets"], c["findings"], c["run"] is not None
      info = {"document_id": doc.id, "file_name": doc.file_name, "version": doc.version, "run_id": c["run"].id if c["run"] else None,
        "run_level": c["run"].level if c["run"] else None, "run_created_at": c["run"].created_at if c["run"] else None}
    out = BA.build(rows, sheets, findings, has_run=has_run, ledger_bbs_kg=ledger.get(FORMULA_BBS), ledger_estimate_kg=ledger.get(FORMULA_ESTIMATE), requested=requested,
      wastage_pct=wastage_pct, document=info)
    return {**out, "run_id": run_id, "project_id": run.project_id, "sources": list(BA.SOURCES)}

  async def get_source(self, org: UUID, project_id: UUID) -> dict:
    await self.report.bbs._require_project(org, project_id)
    return {"project_id": project_id, "source": await self.chosen_source(org, project_id), "sources": list(BA.SOURCES)}

  async def set_source(self, org: UUID, project_id: UUID, user_id: UUID, source: str) -> dict:
    await self.report.bbs._require_project(org, project_id)
    await self.match._put(org, project_id, user_id, SOURCE_KEY, {"source": source})
    await self.session.commit()
    await self.audit_log.log(org, user_id, audit_entity("SCHEDULE_IMPORT"), project_id, AuditAction.UPDATE, f"Chose {source} as the steel line of the project's bill of quantities")
    return await self.get_source(org, project_id)
