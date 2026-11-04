from __future__ import annotations
import asyncio
import base64
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.rebar.bbs_service import BbsService
from app.modules.drawings_boq.rebar.bbs_match_service import BbsMatchService
from app.modules.audit.service import AuditLogService
from app.core.exceptions import TraceException
from app.modules.drawings_boq.rebar.bbs_models import RebarAuditFinding, RebarAuditRun, RebarBbsRow, RebarBbsSheet
from app.modules.audit.models import AuditAction
from uuid import UUID
from sqlalchemy import select
from app.modules.drawings_boq.finish_schedule.common import audit_entity
from app.modules.drawings_boq.models import Drawing
from app.modules.drawings_boq.rebar import bbs_crops as CR
from app.modules.drawings_boq.rebar import bbs_report as BR
from app.shared import storage

PAGE_SIZE_MAX = 200
NOTE = ("Expected total = the schedule total plus the weight effect of the findings that are still open or accepted and that state the basis of their figure. "
  "Rejected and signed findings leave the billed figure standing. Every effect is Trace minus schedule.")
ROW_FIELDS = ("page", "y", "member", "sr", "description", "dia", "spacing_in", "members", "each", "total", "cut_ft", "total_ft", "unit_kg_ft", "total_kg")
FINDING_FIELDS = ("id", "run_id", "code", "finding_class", "rule", "bbs_ref", "drawing_ref", "effect_basis", "convention", "bbs_value", "trace_value", "diff_kg", "diff_pct",
  "confidence", "question", "status", "reason", "decided_by_user_id", "decided_at")

def _now():
  return datetime.now(timezone.utc)

class BbsReportService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.bbs = BbsService(session)
    self.match = BbsMatchService(session)
    self.audit_log = AuditLogService(session)

  async def _data(self, org: UUID, document_id: UUID) -> dict:
    doc = await self.bbs._document(org, document_id)
    sheets = list((await self.session.execute(select(RebarBbsSheet).where(RebarBbsSheet.document_id == document_id, RebarBbsSheet.organization_id == org)
      .order_by(RebarBbsSheet.idx))).scalars().all())
    index_of = {s.id: s.idx for s in sheets}
    rows = [{"row_no": r.row_no, "sheet": index_of[r.sheet_id], **{k: getattr(r, k) for k in ROW_FIELDS}} for r in (await self.session.execute(select(RebarBbsRow)
      .where(RebarBbsRow.document_id == document_id, RebarBbsRow.organization_id == org).order_by(RebarBbsRow.row_no))).scalars().all()]
    run = await self.bbs.latest_run(org, document_id)
    
    stored = []
    if run is not None:
      stored = list((await self.session.execute(select(RebarAuditFinding).where(RebarAuditFinding.run_id == run.id, RebarAuditFinding.organization_id == org))).scalars().all())
    findings = BR.sort_findings([{k: getattr(f, k) for k in FINDING_FIELDS} for f in stored])
    sheet_dicts = [{"idx": s.idx, "name": s.name, "first_page": s.first_page, "last_page": s.last_page, "printed_total_kg": s.printed_total_kg} for s in sheets]
    return {"doc": doc, "run": run, "sheets": sheet_dicts, "rows": rows, "findings": findings,
      "row_expect": dict((run.totals or {}).get("row_expect") or {}) if run is not None else {}}

  @staticmethod
  def _doc_dict(doc) -> dict:
    return {"file_name": doc.file_name, "version": doc.version}

  @staticmethod
  def _run_dict(run: RebarAuditRun | None) -> dict | None:
    return None if run is None else {"id": run.id, "level": run.level, "created_at": run.created_at}

  async def summary(self, org: UUID, document_id: UUID) -> dict:
    c = await self._data(org, document_id)
    s = BR.summarize(c["rows"], c["sheets"], c["findings"])
    run = c["run"]
    return {"document_id": document_id, "version": c["doc"].version, "file_name": c["doc"].file_name, "has_run": run is not None, "run_id": run.id if run else None,
      "level": run.level if run else None, "run_created_at": run.created_at if run else None, "open_questions": len(BR.questions(c["findings"])), "note": NOTE, **s}

  async def findings(self, org: UUID, document_id: UUID, finding_class: str | None, code: str | None, sheet: int | None, status: str | None, page: int, page_size: int) -> dict:
    c = await self._data(org, document_id)
    page_size = max(1, min(page_size, PAGE_SIZE_MAX))
    page = max(1, page)
    items = [f for f in c["findings"] if (not finding_class or f["finding_class"] == finding_class) and (not code or f["code"] == code) and (not status or f["status"] == status)
      and (sheet is None or (f["bbs_ref"] or {}).get("sheet") == sheet)]
    
    by_class: dict = {}
    by_status: dict = {}
    for f in c["findings"]:
      by_class[f["finding_class"]] = by_class.get(f["finding_class"], 0) + 1
      by_status[f["status"]] = by_status.get(f["status"], 0) + 1
    run = c["run"]
    return {"run_id": run.id if run else None, "total": len(items), "page": page, "page_size": page_size, "items": items[(page - 1) * page_size:page * page_size],
      "counts_by_class": by_class, "counts_by_status": by_status}

  async def questions(self, org: UUID, document_id: UUID) -> dict:
    c = await self._data(org, document_id)
    items = BR.questions(c["findings"])
    return {"items": items, "text": BR.questions_text(items)}

  async def _with_run(self, org: UUID, document_id: UUID) -> dict:
    c = await self._data(org, document_id)
    if c["run"] is None:
      raise TraceException("Run the audit before exporting it.", status_code=409, code="NO_AUDIT_RUN")
    return c

  async def summary_md(self, org: UUID, document_id: UUID) -> str:
    c = await self._with_run(org, document_id)
    return BR.summary_md(self._doc_dict(c["doc"]), self._run_dict(c["run"]), BR.summarize(c["rows"], c["sheets"], c["findings"]), c["findings"], BR.questions(c["findings"]))

  async def export_xlsx(self, org: UUID, document_id: UUID) -> tuple:
    c = await self._with_run(org, document_id)
    summary = BR.summarize(c["rows"], c["sheets"], c["findings"])
    data = await asyncio.to_thread(BR.build_xlsx, self._doc_dict(c["doc"]), self._run_dict(c["run"]), c["rows"], c["sheets"], c["findings"], c["row_expect"], summary,
      BR.questions(c["findings"]))
    return data, f"bbs-audit-v{c['doc'].version}.xlsx"

  async def _finding(self, org: UUID, finding_id: UUID, lock: bool = False) -> RebarAuditFinding:
    stmt = select(RebarAuditFinding).where(RebarAuditFinding.id == finding_id, RebarAuditFinding.organization_id == org)
    finding = (await self.session.execute(stmt.with_for_update() if lock else stmt)).scalar_one_or_none()
    if finding is None:
      raise TraceException("Finding not found.", status_code=404, code="FINDING_NOT_FOUND")
    return finding

  async def crops(self, org: UUID, finding_id: UUID) -> dict:
    f = await self._finding(org, finding_id)
    doc = await self.bbs._document(org, f.document_id)
    ref = f.drawing_ref or None
    bbs_ref, bbs_key = dict(f.bbs_ref or {}), doc.storage_key
    drawing_key = None
    
    if ref and ref.get("pdf_key"):
      try:
        wanted = UUID(str(ref["pdf_key"]))
      except ValueError:
        wanted = None
      if wanted is not None:
        drawing_key = (await self.session.execute(select(Drawing.storage_key).where(Drawing.id == wanted, Drawing.organization_id == org))).scalar_one_or_none()
    bbs_text, drawing_text = BR.where(bbs_ref), BR.drawing_text(ref)
    return {"finding_id": finding_id, "bbs": await self._crop(bbs_key, lambda b: CR.bbs_crop(b, bbs_ref), bbs_text),
      "drawing": await self._crop(drawing_key, lambda b: CR.drawing_crop(b, ref), drawing_text, no_ref=ref is None)}

  @staticmethod
  async def _crop(key: str | None, make, text: str, no_ref: bool = False) -> dict:
    if no_ref:
      return {"png_base64": None, "reason": "NO_DRAWING_REF", "message": "The finding has no place on the drawings.", "text": text}
    if not key:
      return {"png_base64": None, "reason": "FILE_NOT_FOUND", "message": "The PDF is not in this project's files.", "text": text}
    try:
      pdf = await asyncio.to_thread(storage.download_bytes, key)
      png = await asyncio.to_thread(make, pdf)
    except CR.CropError as exc:
      return {"png_base64": None, "reason": exc.code, "message": exc.message, "text": text}
    except Exception:  
      return {"png_base64": None, "reason": "UNAVAILABLE", "message": "The picture could not be made.", "text": text}
    return {"png_base64": base64.b64encode(png).decode("ascii"), "reason": None, "message": None, "text": text}

  async def sign(self, org: UUID, finding_id: UUID, user_id: UUID, reason: str) -> RebarAuditFinding:
    f = await self._finding(org, finding_id, lock=True)
    if f.status == "SIGNED":
      raise TraceException("This finding is already signed.", status_code=409, code="FINDING_SIGNED")
    if f.finding_class != "METHOD":
      raise TraceException("Only a METHOD finding can be signed. Accept or reject the others.", status_code=422, code="SIGN_ONLY_METHOD")
    conv = f.convention or {}
    if not conv.get("key") or conv.get("value") is None:
      raise TraceException("This finding carries no convention to sign.", status_code=422, code="NO_CONVENTION")
    reason = reason.strip()
    
    if not reason:
      raise TraceException("Give the reason for signing this convention.", status_code=422, code="REASON_REQUIRED")
    doc = await self.bbs._document(org, f.document_id)
    document_id, project_id, code, key = doc.id, doc.project_id, f.code, conv["key"]
    await self.match._put(org, project_id, user_id, key, conv["value"])
    f.status, f.reason, f.decided_by_user_id, f.decided_at = "SIGNED", reason, user_id, _now()
    await self.session.commit()
    await self.audit_log.log(org, user_id, audit_entity("SCHEDULE_IMPORT"), document_id, AuditAction.UPDATE, f"Signed the convention {key} of this project from finding {code}")
    return await self._finding(org, finding_id)
