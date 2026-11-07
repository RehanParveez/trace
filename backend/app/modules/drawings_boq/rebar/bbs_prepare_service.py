from __future__ import annotations
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.rebar.bbs_expect_service import BbsExpectService
from app.modules.drawings_boq.rebar.bbs_report_service import BbsReportService
from uuid import UUID
from app.modules.drawings_boq.rebar import expect_source as ES
from app.core.exceptions import TraceException
from datetime import datetime, timezone
from app.modules.drawings_boq.rebar import bbs_prepare as BP
from app.modules.drawings_boq.rebar import bbs_prepare_export as EXP

class BbsPrepareService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.expect = BbsExpectService(session)
    self.report = BbsReportService(session)

  async def prepared(self, org: UUID, project_id: UUID, document_id: UUID | None = None) -> tuple:
    await self.expect.bbs._require_project(org, project_id)
    project = await self.expect.bbs.projects.get_by_id_and_org(project_id, org)
    decisions = await self.expect.expect_decisions(org, project_id)
    sheets, cands = await self.expect._read(org, project_id)
    jobs = ES.build_jobs(sheets, cands, decisions)
    
    if not jobs:
      raise TraceException("No structural drawing of this project has been read yet, so there is nothing to prepare a schedule from. Upload and prepare the structural drawings first.",
        status_code=409, code="NO_DRAWING_MEMBERS")
    prepared = BP.prepare(ES.run_jobs(jobs), {"id": str(project_id), "name": getattr(project, "name", None)})
    if document_id is None:
      return prepared, None
    c = await self.report._with_run(org, document_id)
    if c["doc"].project_id != project_id:
      raise TraceException("That bar schedule belongs to another project.", status_code=422, code="BBS_OTHER_PROJECT")
    coverage = ((c["run"].totals or {}).get("crosscheck") or {}).get("coverage")
    return prepared, BP.compare(prepared, c["rows"], c["sheets"], c["findings"], c["row_expect"], coverage)

  @staticmethod
  def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%d %b %Y")

  async def export_xlsx(self, org: UUID, project_id: UUID, document_id: UUID | None) -> tuple:
    prepared, comparison = await self.prepared(org, project_id, document_id)
    return await asyncio.to_thread(EXP.build_xlsx, prepared, comparison, self._stamp()), "trace-bbs.xlsx"

  async def export_pdf(self, org: UUID, project_id: UUID, document_id: UUID | None) -> tuple:
    prepared, comparison = await self.prepared(org, project_id, document_id)
    return await asyncio.to_thread(EXP.build_pdf, prepared, comparison, self._stamp()), "trace-bbs.pdf"
