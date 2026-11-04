from __future__ import annotations
import asyncio
import hashlib
import io
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.projects.repository import ProjectRepository
from app.modules.audit.service import AuditLogService
from uuid import UUID, uuid4
from app.modules.drawings_boq.rebar.bbs_models import RebarBbsRow, RebarBbsSheet, RebarAuditFinding, RebarAuditRun, RebarBbsDocument
from app.core.exceptions import TraceException
from app.modules.drawings_boq.schedule_parsing import ScheduleParseError
from app.shared.storage import build_storage_key, delete_object, upload_fileobj
from app.modules.drawings_boq.rebar.bbs_layouts import BbsDocument, BbsRow, BbsSheet, bbs_summary, read_bbs_pdf
from pathlib import PurePosixPath
from decimal import Decimal
from fastapi import UploadFile
from app.modules.audit.models import AuditAction
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from app.modules.drawings_boq.rebar import rebar_repository as repo
from app.modules.drawings_boq.rebar import bbs_audit as audit
from app.modules.drawings_boq.finish_schedule.common import audit_entity

MAX_BBS_BYTES = 25 * 1024 * 1024
PAGE_SIZE_MAX = 500
CLASS_ORDER = {"ERROR": 0, "CONFLICT": 1, "METHOD": 2, "CHECK": 3, "MISSING": 3, "EXTRA": 3, "UNVERIFIABLE": 4, "ROUNDING": 5, "NAMING": 6, "INFO": 7}
DECISIONS_DIGEST = hashlib.sha256(b"{}").hexdigest()

def _now():
  return datetime.now(timezone.utc)

def _finding_key(f) -> str:
  r = f.bbs_ref
  return f"{f.code}|{r.get('sheet')}|{r.get('page')}|{r.get('member')}|{r.get('sr')}|{r.get('description')}"

class BbsService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.projects = ProjectRepository(session)
    self.audit_log = AuditLogService(session)

  async def _log(self, org, user_id, entity_id, action, message) -> None:
    await self.audit_log.log(org, user_id, audit_entity("SCHEDULE_IMPORT"), entity_id, action, message)

  async def _require_project(self, org: UUID, project_id: UUID) -> None:
    if await self.projects.get_by_id_and_org(project_id, org) is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

  async def _document(self, org: UUID, document_id: UUID) -> RebarBbsDocument:
    doc = (await self.session.execute(select(RebarBbsDocument).where(RebarBbsDocument.id == document_id,
      RebarBbsDocument.organization_id == org))).scalar_one_or_none()
    if doc is None:
      raise TraceException("Bar bending schedule not found.", status_code=404, code="BBS_NOT_FOUND")
    return doc

  async def _counts(self, org: UUID, document_ids: list[UUID]) -> dict:
    if not document_ids:
      return {}
    rows = (await self.session.execute(select(RebarBbsRow.document_id, func.count()).where(RebarBbsRow.organization_id == org,
      RebarBbsRow.document_id.in_(document_ids)).group_by(RebarBbsRow.document_id))).all()
    sheets = (await self.session.execute(select(RebarBbsSheet.document_id, func.count()).where(RebarBbsSheet.organization_id == org,
      RebarBbsSheet.document_id.in_(document_ids)).group_by(RebarBbsSheet.document_id))).all()
    
    out = {d: {"row_count": 0, "sheet_count": 0} for d in document_ids}
    for d, n in rows:
      out[d]["row_count"] = n
    for d, n in sheets:
      out[d]["sheet_count"] = n
    return out

  def _doc_out(self, doc: RebarBbsDocument, counts: dict) -> dict:
    return {"id": doc.id, "project_id": doc.project_id, "file_name": doc.file_name, "sha256": doc.sha256, "status": doc.status, "version": doc.version,
      "title": doc.title, "pages": doc.pages, "profile": doc.profile, "created_at": doc.created_at, **counts.get(doc.id, {})}

  async def upload(self, org: UUID, project_id: UUID, user_id: UUID, file: UploadFile) -> dict:
    await self._require_project(org, project_id)
    name = file.filename or "bbs.pdf"
    if PurePosixPath(name).suffix.lower() != ".pdf":
      raise TraceException("Upload the bar bending schedule as a PDF.", status_code=422, code="BBS_NOT_PDF")
    contents = await file.read(MAX_BBS_BYTES + 1)
    if len(contents) > MAX_BBS_BYTES:
      raise TraceException("The bar bending schedule file is too large.", status_code=413, code="FILE_TOO_LARGE")
    if not contents:
      raise TraceException("The uploaded file is empty.", status_code=422, code="EMPTY_UPLOAD")
  
    sha = hashlib.sha256(contents).hexdigest()
    dup = await self.session.execute(select(RebarBbsDocument.version).where(RebarBbsDocument.project_id == project_id, RebarBbsDocument.sha256 == sha))
    if dup.first() is not None:
      raise TraceException("This bar bending schedule has already been uploaded for this project.", status_code=409, code="BBS_ALREADY_UPLOADED")
    try:
      parsed = await asyncio.to_thread(read_bbs_pdf, contents)
    except ScheduleParseError as exc:
      raise TraceException(str(exc), status_code=422, code="SCHEDULE_UNREADABLE")
    last = (await self.session.execute(select(RebarBbsDocument).where(RebarBbsDocument.project_id == project_id, RebarBbsDocument.organization_id == org)
      .order_by(RebarBbsDocument.version.desc()).limit(1))).scalar_one_or_none()
    key = build_storage_key(org, project_id, name)
    previous_version = last.version if last else None
    await asyncio.to_thread(upload_fileobj, key, io.BytesIO(contents), "application/pdf")
    summary = bbs_summary(parsed)
    
    doc = RebarBbsDocument(id=uuid4(), organization_id=org, project_id=project_id, file_name=name[:500], sha256=sha, storage_key=key, status="ACTIVE",
      version=(last.version + 1) if last else 1, title=parsed.title, pages=parsed.pages, profile=parsed.profile, summary=summary,
      page_counters=[[n, m] for n, m in parsed.page_counters], unread_lines=summary["unread_lines"], dropped_repeats=summary["dropped_repeats"], created_by_user_id=user_id)
    sheet_ids = {s.index: uuid4() for s in parsed.sheets}
    sheets = [RebarBbsSheet(id=sheet_ids[s.index], organization_id=org, document_id=doc.id, idx=s.index, name=s.name[:300], first_page=s.first_page,
      last_page=s.last_page, printed_total_kg=s.printed_total_kg, dia_totals={str(k): str(v) for k, v in s.dia_totals_kg.items()}) for s in parsed.sheets]
    rows = [RebarBbsRow(id=uuid4(), organization_id=org, document_id=doc.id, sheet_id=sheet_ids[r.sheet], row_no=i, page=r.page, y=Decimal(str(r.y)),
      member=(r.member or "")[:300] or None, sr=r.sr, description=(r.description or "")[:300], dia=r.dia, spacing_in=r.spacing_in, members=r.members,
      each=r.each, total=r.total, cut_ft=r.cut_ft, total_ft=r.total_ft, unit_kg_ft=r.unit_kg_ft, total_kg=r.total_kg, parts=[str(p) for p in r.parts],
      notes=list(r.notes), issues=list(r.issues)) for i, r in enumerate(parsed.rows, start=1)]
    try:
      if last is not None:
        for old in (await self.session.execute(select(RebarBbsDocument).where(RebarBbsDocument.project_id == project_id,
          RebarBbsDocument.organization_id == org, RebarBbsDocument.status == "ACTIVE"))).scalars().all():
          old.status = "SUPERSEDED"
          
      self.session.add(doc)
      await self.session.flush()
      self.session.add_all(sheets)
      await self.session.flush()
      self.session.add_all(rows)
      await self.session.flush()
      document_id, version_no = doc.id, doc.version
      await self.session.commit()
      
    except IntegrityError:
      await self.session.rollback()
      await asyncio.to_thread(delete_object, key)
      raise TraceException("This bar bending schedule has already been uploaded for this project.", status_code=409, code="BBS_ALREADY_UPLOADED")
    await self._log(org, user_id, document_id, AuditAction.CREATE, f"Uploaded bar bending schedule version {version_no}: {len(rows)} row(s), {len(sheets)} sheet(s)")
    doc = await self._document(org, document_id)
    counts = await self._counts(org, [document_id])
    return {"document": self._doc_out(doc, counts), "summary": summary, "previous_version": previous_version}

  async def list_documents(self, org: UUID, project_id: UUID) -> list[dict]:
    await self._require_project(org, project_id)
    docs = list((await self.session.execute(select(RebarBbsDocument).where(RebarBbsDocument.organization_id == org,
      RebarBbsDocument.project_id == project_id).order_by(RebarBbsDocument.version.desc()))).scalars().all())
    counts = await self._counts(org, [d.id for d in docs])
    return [self._doc_out(d, counts) for d in docs]

  async def get(self, org: UUID, document_id: UUID, sheet_idx: int | None, page: int, page_size: int) -> dict:
    doc = await self._document(org, document_id)
    page_size = max(1, min(page_size, PAGE_SIZE_MAX))
    page = max(1, page)
    
    sheets = list((await self.session.execute(select(RebarBbsSheet).where(RebarBbsSheet.document_id == document_id,
      RebarBbsSheet.organization_id == org).order_by(RebarBbsSheet.idx))).scalars().all())
    sums = {sid: (n, kg) for sid, n, kg in (await self.session.execute(select(RebarBbsRow.sheet_id, func.count(), func.coalesce(func.sum(RebarBbsRow.total_kg), 0))
      .where(RebarBbsRow.document_id == document_id, RebarBbsRow.organization_id == org).group_by(RebarBbsRow.sheet_id))).all()}
    sheet_out = []
    for s in sheets:
      n, kg = sums.get(s.id, (0, Decimal("0")))
      kg = Decimal(kg)
      sheet_out.append({"id": s.id, "idx": s.idx, "name": s.name, "first_page": s.first_page, "last_page": s.last_page, "printed_total_kg": s.printed_total_kg,
        "computed_kg": kg, "diff_kg": None if s.printed_total_kg is None else kg - s.printed_total_kg, "row_count": n, "dia_totals": s.dia_totals})
      
    stmt = select(RebarBbsRow).where(RebarBbsRow.document_id == document_id, RebarBbsRow.organization_id == org)
    if sheet_idx is not None:
      match = next((s.id for s in sheets if s.idx == sheet_idx), None)
      if match is None:
        raise TraceException("Sheet not found.", status_code=404, code="BBS_SHEET_NOT_FOUND")
      stmt = stmt.where(RebarBbsRow.sheet_id == match)
    total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = list((await self.session.execute(stmt.order_by(RebarBbsRow.row_no).offset((page - 1) * page_size).limit(page_size))).scalars().all())
    counts = await self._counts(org, [document_id])
    return {"document": self._doc_out(doc, counts), "sheets": sheet_out, "rows": rows, "row_total": total, "page": page, "page_size": page_size,
      "page_counters": doc.page_counters, "unread_lines": doc.unread_lines, "dropped_repeats": doc.dropped_repeats}

  async def _load_parsed(self, org: UUID, doc: RebarBbsDocument) -> tuple[BbsDocument, dict]:
    sheets = list((await self.session.execute(select(RebarBbsSheet).where(RebarBbsSheet.document_id == doc.id,
      RebarBbsSheet.organization_id == org).order_by(RebarBbsSheet.idx))).scalars().all())
    rows = list((await self.session.execute(select(RebarBbsRow).where(RebarBbsRow.document_id == doc.id,
      RebarBbsRow.organization_id == org).order_by(RebarBbsRow.row_no))).scalars().all())
    index_of = {s.id: s.idx for s in sheets}
    
    parsed = BbsDocument(title=doc.title, pages=doc.pages, profile=doc.profile, page_counters=[(n, m) for n, m in doc.page_counters])
    parsed.sheets = [BbsSheet(index=s.idx, name=s.name, first_page=s.first_page, last_page=s.last_page, printed_total_kg=s.printed_total_kg,
      dia_totals_kg={k: Decimal(v) for k, v in (s.dia_totals or {}).items()}) for s in sheets]
    parsed.rows = [BbsRow(page=r.page, y=float(r.y or 0), sheet=index_of[r.sheet_id], member=r.member, sr=r.sr, description=r.description, dia=r.dia,
      spacing_in=r.spacing_in, members=r.members, each=r.each, total=r.total, cut_ft=r.cut_ft, total_ft=r.total_ft, unit_kg_ft=r.unit_kg_ft,
      total_kg=r.total_kg, parts=[Decimal(p) for p in r.parts], notes=list(r.notes), issues=list(r.issues)) for r in rows]
    return parsed, {s.idx: s.name for s in sheets}

  async def _shapes_and_rules(self, org: UUID):
    shapes = {s.code: s for s in (repo.shape_spec(r) for r in await repo.load_shape_rows(self.session, org))}
    try:
      from app.engine.measure.rebar import pick_rule
      from app.modules.drawings_boq.service import DrawingBOQService
      from app.modules.drawings_boq.standards.service import StandardsService
      rule_set = await DrawingBOQService(self.session).get_active_rule_set(org, None)
      rules = (await StandardsService(self.session).profile_for_rule_set(rule_set.id)).reinforcement_rules
      return shapes, {"MAIN": pick_rule(rules, None, None, "MAIN"), "STIRRUP": pick_rule(rules, None, None, "STIRRUP")}
    except TraceException:
      return shapes, None

  async def run_audit(self, org: UUID, document_id: UUID, user_id: UUID) -> RebarAuditRun:
    doc = await self._document(org, document_id)
    parsed, names = await self._load_parsed(org, doc)
    bands = audit.load_bands()
    shapes, rule = await self._shapes_and_rules(org)
    result = audit.run_l1(parsed, bands, shapes, rule)
    previous = None
    if doc.version > 1:
      previous = (await self.session.execute(select(RebarBbsDocument).where(RebarBbsDocument.project_id == doc.project_id,
        RebarBbsDocument.organization_id == org, RebarBbsDocument.version == doc.version - 1))).scalar_one_or_none()
    diff = {}
    
    if previous is not None:
      old_parsed, old_names = await self._load_parsed(org, previous)
      diff = audit.diff_rows(old_parsed.rows, old_names, parsed.rows, names)
      diff["from_version"], diff["to_version"] = previous.version, doc.version
    before = (await self.session.execute(select(RebarAuditRun.id).where(RebarAuditRun.document_id == document_id, RebarAuditRun.organization_id == org)
      .order_by(RebarAuditRun.created_at.desc()).limit(1))).scalar_one_or_none()
    
    carried: dict = {}
    if before is not None:
      for f in (await self.session.execute(select(RebarAuditFinding).where(RebarAuditFinding.run_id == before, RebarAuditFinding.organization_id == org,
        RebarAuditFinding.status != "OPEN"))).scalars().all():
        carried[f.finding_key] = f
        
    run = RebarAuditRun(id=uuid4(), organization_id=org, document_id=document_id, level="L1",
      engine_digest=hashlib.sha256(f"{audit.AUDIT_VERSION}|{parsed.profile}".encode()).hexdigest(), rules_digest=bands.digest, decisions_digest=DECISIONS_DIGEST,
      previous_document_id=previous.id if previous else None, totals=_json_safe(result.totals), diff=diff, created_by_user_id=user_id)
    self.session.add(run)
    await self.session.flush()
    run_id, version_no, finding_count = run.id, doc.version, len(result.findings)
    
    for f in result.findings:
      row = RebarAuditFinding(id=uuid4(), organization_id=org, run_id=run_id, document_id=document_id, code=f.code, finding_class=f.finding_class, rule=f.rule[:300],
        finding_key=_finding_key(f)[:600], bbs_ref=_json_safe(f.bbs_ref), drawing_ref=None, bbs_value=f.bbs_value, trace_value=f.trace_value, diff_kg=f.diff_kg,
        diff_pct=f.diff_pct, confidence=f.confidence, question=f.question)
      old = carried.get(row.finding_key)
      if old is not None:
        row.status, row.reason, row.decided_by_user_id, row.decided_at = old.status, old.reason, old.decided_by_user_id, old.decided_at
      self.session.add(row)
    await self.session.commit()
    await self._log(org, user_id, document_id, AuditAction.CREATE, f"Ran the L1 audit on bar bending schedule version {version_no}: {finding_count} finding(s)")
    return (await self.session.execute(select(RebarAuditRun).where(RebarAuditRun.id == run_id))).scalar_one()

  async def latest_run(self, org: UUID, document_id: UUID) -> RebarAuditRun | None:
    await self._document(org, document_id)
    return (await self.session.execute(select(RebarAuditRun).where(RebarAuditRun.document_id == document_id, RebarAuditRun.organization_id == org)
      .order_by(RebarAuditRun.created_at.desc()).limit(1))).scalar_one_or_none()

  async def findings(self, org: UUID, document_id: UUID, finding_class: str | None, code: str | None, sheet: int | None, status: str | None,
    page: int, page_size: int) -> dict:
    run = await self.latest_run(org, document_id)
    page_size = max(1, min(page_size, PAGE_SIZE_MAX))
    page = max(1, page)
    
    if run is None:
      return {"run_id": None, "total": 0, "page": page, "page_size": page_size, "items": [], "counts_by_class": {}, "counts_by_status": {}}
    base = [RebarAuditFinding.run_id == run.id, RebarAuditFinding.organization_id == org]
    stmt = select(RebarAuditFinding).where(*base)
    if finding_class:
      stmt = stmt.where(RebarAuditFinding.finding_class == finding_class)
    if code:
      stmt = stmt.where(RebarAuditFinding.code == code)
    if status:
      stmt = stmt.where(RebarAuditFinding.status == status)
    if sheet is not None:
      stmt = stmt.where(RebarAuditFinding.bbs_ref["sheet"].astext == str(sheet))
      
    total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    order = case(CLASS_ORDER, value=RebarAuditFinding.finding_class, else_=9)
    items = list((await self.session.execute(stmt.order_by(order, RebarAuditFinding.code, RebarAuditFinding.bbs_ref["page"].astext, RebarAuditFinding.id)
      .offset((page - 1) * page_size).limit(page_size))).scalars().all())
    by_class = dict((await self.session.execute(select(RebarAuditFinding.finding_class, func.count()).where(*base).group_by(RebarAuditFinding.finding_class))).all())
    by_status = dict((await self.session.execute(select(RebarAuditFinding.status, func.count()).where(*base).group_by(RebarAuditFinding.status))).all())
    return {"run_id": run.id, "total": total, "page": page, "page_size": page_size, "items": items, "counts_by_class": by_class, "counts_by_status": by_status}

  async def decide(self, org: UUID, finding_id: UUID, user_id: UUID, status: str, reason: str) -> RebarAuditFinding:
    finding = (await self.session.execute(select(RebarAuditFinding).where(RebarAuditFinding.id == finding_id, RebarAuditFinding.organization_id == org)
      .with_for_update())).scalar_one_or_none()
    if finding is None:
      raise TraceException("Finding not found.", status_code=404, code="FINDING_NOT_FOUND")
    if finding.status == "SIGNED":
      raise TraceException("A signed finding cannot be changed.", status_code=409, code="FINDING_SIGNED")
    reason = reason.strip()
    
    if not reason:
      raise TraceException("Give the reason for this decision.", status_code=422, code="REASON_REQUIRED")
    finding.status = status
    finding.reason = reason
    finding.decided_by_user_id = None if status == "OPEN" else user_id
    finding.decided_at = None if status == "OPEN" else _now()
    document_id, code = finding.document_id, finding.code
    await self.session.commit()
    await self._log(org, user_id, document_id, AuditAction.UPDATE, f"Finding {code} set to {status}")
    return (await self.session.execute(select(RebarAuditFinding).where(RebarAuditFinding.id == finding_id))).scalar_one()

def _json_safe(value):
  if isinstance(value, dict):
    return {str(k): _json_safe(v) for k, v in value.items()}
  if isinstance(value, (list, tuple)):
    return [_json_safe(v) for v in value]
  if isinstance(value, Decimal):
    return str(value)
  return value
