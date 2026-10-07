from __future__ import annotations
import asyncio
import hashlib
import os
from datetime import datetime, timezone
from uuid import UUID, uuid4
import re
from app.modules.drawings_boq.schedule_parsing import ScheduleParseError, norm_key, read_table
from app.engine.measure.rebar import RebarError, compute_mark, role_family
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.projects.repository import ProjectRepository
from app.modules.audit.service import AuditLogService
from app.modules.drawings_boq.finish_schedule.common import audit_entity, current_ifc_drawing_ids
from app.core.exceptions import TraceException
from app.modules.drawings_boq.models import DrawingElement, BuildingLevel, ScheduleImport, BarSize, BOQVersion, Drawing, RebarScheduleRow, RebarShape, DrawingFormat
from app.modules.drawings_boq.schedule_service import _name_tokens
from sqlalchemy import select
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.service import DrawingBOQService
from app.modules.drawings_boq.standards.service import StandardsService
from decimal import Decimal
from app.shared.storage import download_to_path
from app.modules.drawings_boq.rebar import rebar_repository as repo
from app.modules.drawings_boq.rebar.rebar_parsing import parse_bar_size, rows_from_pdf_text, rows_from_table
import tempfile
from fastapi import UploadFile
from pathlib import PurePosixPath
from sqlalchemy.exc import IntegrityError
from app.modules.drawings_boq.pdf_extraction import extract_pdf_layout_text
from app.modules.drawings_boq.calc_service import CalculationService 

MAX_FILE_BYTES = 5 * 1024 * 1024
_ROLE_WORDS = frozenset({"column", "columns", "beam", "beams", "slab", "slabs", "footing", "footings", "wall", "walls", "lintel", "stair", "pile"})

def _now():
  return datetime.now(timezone.utc)

def _match_member(member_mark, role, elements) -> UUID | None:
  family = role_family(role)
  words = {norm_key(w) for w in re.findall(r"[A-Za-z0-9]+", member_mark or "") if len(w) >= 2 and w.lower() not in _ROLE_WORDS}
  if not words:
    return None
  hits = [eid for eid, fam, tokens in elements if (family is None or fam == family) and words & tokens]
  return hits[0] if len(hits) == 1 else None

class RebarService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.projects = ProjectRepository(session)
    self.audit = AuditLogService(session)

  async def _log(self, org, user_id, entity_id, action, message) -> None:
    await self.audit.log(org, user_id, audit_entity("SCHEDULE_IMPORT"), entity_id, action, message)

  async def _require_project(self, org: UUID, project_id: UUID) -> None:
    if await self.projects.get_by_id_and_org(project_id, org) is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

  async def _import(self, org: UUID, import_id: UUID, lock: bool = False) -> ScheduleImport:
    stmt = select(ScheduleImport).where(ScheduleImport.id == import_id, ScheduleImport.organization_id == org,
      ScheduleImport.schedule_kind == "BBS")
    if lock:
      stmt = stmt.with_for_update()
    imp = (await self.session.execute(stmt)).scalar_one_or_none()
    if imp is None:
      raise TraceException("Bar schedule import not found.", status_code=404, code="REBAR_IMPORT_NOT_FOUND")
    return imp

  async def _rows(self, org: UUID, import_id: UUID) -> list[RebarScheduleRow]:
    r = await self.session.execute(select(RebarScheduleRow).where(RebarScheduleRow.schedule_import_id == import_id,
      RebarScheduleRow.organization_id == org).order_by(RebarScheduleRow.row_no.asc()))
    return list(r.scalars().all())

  @staticmethod
  def _require_pending(imp: ScheduleImport) -> None:
    if imp.status != "PENDING_REVIEW":
      raise TraceException("Only imports awaiting review can be edited.", status_code=409, code="IMPORT_NOT_EDITABLE")

  async def _context(self, org: UUID, project_id: UUID):
    ids = await current_ifc_drawing_ids(self.session, org, project_id)
    elements, levels = [], {}
    if ids:
      for eid, name, role in (await self.session.execute(select(DrawingElement.id, DrawingElement.name, DrawingElement.structural_role)
        .where(DrawingElement.organization_id == org, DrawingElement.drawing_id.in_(ids)))).all():
        fam = role_family(role)
        if fam:
          elements.append((eid, fam, _name_tokens(name)))
      for lv in (await self.session.execute(select(BuildingLevel).where(BuildingLevel.organization_id == org,
        BuildingLevel.drawing_id.in_(ids)).order_by(BuildingLevel.sequence.asc()))).scalars().all():
        levels.setdefault(norm_key(lv.name), lv.id)
    return elements, levels

  async def _profile_rules(self, org: UUID):
    rs = await DrawingBOQService(self.session).get_active_rule_set(org, None)
    return (await StandardsService(self.session).profile_for_rule_set(rs.id)).reinforcement_rules

  async def _computable(self, org: UUID, row: RebarScheduleRow, rules, shapes, sizes) -> None:
    def fail(message: str, code: str):
      raise TraceException(f"Row {row.row_no}: {message}", status_code=422, code=code)
    if not row.mark:
      fail("a bar mark is required.", "ROW_NEEDS_MARK")
    if row.dia_mm is None or row.dia_mm <= 0:
      fail("the bar size is missing or not recognised.", "ROW_NEEDS_SIZE")
    if row.count is None or row.count <= 0:
      fail("the number of bars is missing.", "ROW_NEEDS_COUNT")
    if row.cut_len_mm is None and not (row.shape_code and row.shape_code.upper() in shapes):
      fail("give the cut length, or a known shape with its dimensions.", "ROW_NEEDS_LENGTH")
    try:
      compute_mark(repo.row_input(row), shapes.get((row.shape_code or "").upper()), sizes, rules, role_family(row.role))
    except RebarError as exc:
      fail(str(exc) + ".", "ROW_NOT_COMPUTABLE")

  def _build_row(self, imp: ScheduleImport, org: UUID, n: int, p: dict, elements, levels) -> RebarScheduleRow:
    confidence = Decimal(p.get("confidence") or "0.7")
    if p.get("dia_mm") is None or p.get("count") is None or (p.get("cut_len_mm") is None and not p.get("shape_code")):
      confidence = min(confidence, Decimal("0.4"))
    return RebarScheduleRow(
      id=uuid4(), organization_id=org, schedule_import_id=imp.id, row_no=n, raw_text=p.get("raw_text"),
      member_mark=(p.get("member_mark") or "")[:100] or None, mark=(p.get("mark") or f"R{n}")[:50], role=p.get("role"),
      shape_code=p.get("shape_code"), shape_params=p.get("shape_params") or {}, designation=(p.get("designation") or "")[:20] or None,
      dia_mm=p.get("dia_mm"), grade=p.get("grade"), count=p.get("count"), spacing_mm=p.get("spacing_mm"),
      cut_len_mm=p.get("cut_len_mm"), declared_total_kg=p.get("declared_total_kg"),
      level_id=levels.get(norm_key(p.get("level_text"))) if p.get("level_text") else None,
      matched_element_id=_match_member(p.get("member_mark"), p.get("role"), elements),
      confidence=confidence, review_status="PENDING", review_note=" ".join(p.get("notes") or []) or None)

  async def _create_import(self, org, project_id, user_id, *, source, parsed, file_name, content_hash, drawing_id=None,
    notes=None, meta=None) -> dict:
    dup = await self.session.execute(select(ScheduleImport.id).where(ScheduleImport.project_id == project_id,
      ScheduleImport.content_hash == content_hash, ScheduleImport.status.in_(("PENDING_REVIEW", "CONFIRMED"))))
    if dup.first() is not None:
      raise TraceException("This schedule has already been imported for this project.", status_code=409, code="SCHEDULE_ALREADY_IMPORTED")
    imp = ScheduleImport(id=uuid4(), organization_id=org, project_id=project_id, drawing_id=drawing_id, source=source,
      schedule_kind="BBS", status="PENDING_REVIEW", file_name=(file_name or "")[:500] or None, content_hash=content_hash,
      row_count=0, confirmed_count=0, extraction_meta=meta or {}, notes=notes, created_by_user_id=user_id)
    self.session.add(imp)
    await self.session.flush()
    elements, levels = await self._context(org, project_id)
    rows = [self._build_row(imp, org, i, p, elements, levels) for i, p in enumerate(parsed, start=1)]
    self.session.add_all(rows)
    imp.row_count = len(rows)
    try:
      await self.session.flush()
      iid = imp.id
      await self.session.commit()
    except IntegrityError:
      await self.session.rollback()
      raise TraceException("This schedule has already been imported for this project.", status_code=409, code="SCHEDULE_ALREADY_IMPORTED")
    await self._log(org, user_id, iid, AuditAction.CREATE, f"Imported {len(rows)} bar schedule row(s) from {source}")
    return await self.get_import(org, iid)

  async def create_from_file(self, org: UUID, project_id: UUID, user_id: UUID, file: UploadFile, notes: str | None) -> dict:
    await self._require_project(org, project_id)
    name = file.filename or "bbs"
    if PurePosixPath(name).suffix.lower() not in (".csv", ".txt", ".xlsx"):
      raise TraceException("Upload a .csv or .xlsx bar schedule. For a PDF, import it from the drawing.", status_code=422, code="UNSUPPORTED_SCHEDULE_FORMAT")
    contents = await file.read(MAX_FILE_BYTES + 1)
    if len(contents) > MAX_FILE_BYTES:
      raise TraceException("The schedule file is too large.", status_code=413, code="FILE_TOO_LARGE")
    if not contents:
      raise TraceException("The uploaded file is empty.", status_code=422, code="EMPTY_UPLOAD")
    try:
      parsed = rows_from_table(read_table(contents, name))
    except ScheduleParseError as exc:
      raise TraceException(str(exc), status_code=422, code="SCHEDULE_UNREADABLE")
    return await self._create_import(org, project_id, user_id, source="CSV", parsed=parsed, file_name=name,
      content_hash=hashlib.sha256(b"BBS" + contents).hexdigest(), notes=notes, meta={"format": PurePosixPath(name).suffix.lstrip(".")})

  async def create_from_pdf(self, org: UUID, project_id: UUID, user_id: UUID, drawing_id: UUID, notes: str | None) -> dict:
    await self._require_project(org, project_id)
    drawing = (await self.session.execute(select(Drawing).where(Drawing.id == drawing_id, Drawing.organization_id == org,
      Drawing.project_id == project_id))).scalar_one_or_none()
    if drawing is None:
      raise TraceException("Drawing not found.", status_code=404, code="DRAWING_NOT_FOUND")
    if drawing.format != DrawingFormat.PDF:
      raise TraceException("Bar schedules can be read from PDF drawings only.", status_code=422, code="DRAWING_NOT_PDF")
    with tempfile.TemporaryDirectory() as tmp:
      path = os.path.join(tmp, "drawing.pdf")
      await asyncio.to_thread(download_to_path, drawing.storage_key, path)
      with open(path, "rb") as handle:
        contents = handle.read()
        
    layout = await asyncio.to_thread(extract_pdf_layout_text, contents)
    if not layout.strip():
      raise TraceException("This PDF has no machine-readable text (it may be a scan).", status_code=422, code="PDF_NO_TEXT")
    try:
      parsed = rows_from_pdf_text(layout)
    except ScheduleParseError as exc:
      raise TraceException(str(exc), status_code=422, code="SCHEDULE_UNREADABLE")
    return await self._create_import(org, project_id, user_id, source="PDF_TEXT", parsed=parsed, file_name=drawing.original_filename,
      content_hash=hashlib.sha256(("BBS|" + layout).encode()).hexdigest(), drawing_id=drawing.id, notes=notes,
      meta={"extraction": "text", "text_chars": len(layout)})

  async def get_import(self, org: UUID, import_id: UUID) -> dict:
    imp = await self._import(org, import_id)
    rows = await self._rows(org, import_id)
    return {"schedule_import_id": imp.id, "row_count": len(rows), "matched_count": sum(r.matched_element_id is not None for r in rows),
      "unmatched_count": sum(r.matched_element_id is None for r in rows), "rows": rows}

  async def update_row(self, org: UUID, row_id: UUID, user_id: UUID, payload) -> RebarScheduleRow:
    row = (await self.session.execute(select(RebarScheduleRow).where(RebarScheduleRow.id == row_id,
      RebarScheduleRow.organization_id == org).with_for_update())).scalar_one_or_none()
    if row is None:
      raise TraceException("Bar schedule row not found.", status_code=404, code="REBAR_ROW_NOT_FOUND")
    imp = await self._import(org, row.schedule_import_id)
    self._require_pending(imp)
    fs = payload.model_fields_set
    
    for key in ("member_mark", "mark", "role", "shape_code", "designation", "grade"):
      if key in fs:
        value = (getattr(payload, key) or "").strip() or None
        setattr(row, key, value.upper() if key in ("role", "shape_code") and value else value)
    for key in ("shape_params", "dia_mm", "count", "spacing_mm", "cut_len_mm", "level_id"):
      if key in fs:
        setattr(row, key, getattr(payload, key) if getattr(payload, key) is not None or key in ("cut_len_mm", "spacing_mm", "level_id") else getattr(row, key))
    if "designation" in fs and payload.designation and "dia_mm" not in fs:
      desig, dia = parse_bar_size(payload.designation)
      
      if dia is not None:
        row.designation, row.dia_mm = desig, dia
    if "matched_element_id" in fs:
      if payload.matched_element_id is not None and (await self.session.execute(select(DrawingElement.id).where(
        DrawingElement.id == payload.matched_element_id, DrawingElement.organization_id == org))).first() is None:
        raise TraceException("Element not found.", status_code=404, code="ELEMENT_NOT_FOUND")
      row.matched_element_id = payload.matched_element_id
    try:
      if payload.review_status == "CONFIRMED":
        rules = await self._profile_rules(org)
        shapes = {s.code: s for s in (repo.shape_spec(r) for r in await repo.load_shape_rows(self.session, org))}
        sizes = tuple(repo.size_spec(s) for s in await repo.load_size_rows(self.session, org))
        await self._computable(org, row, rules, shapes, sizes)
        
      if payload.review_status is not None:
        row.review_status = payload.review_status
        row.reviewed_by_user_id = user_id if payload.review_status != "PENDING" else None
        row.reviewed_at = _now() if payload.review_status != "PENDING" else None
      if "review_note" in fs:
        row.review_note = (payload.review_note or "").strip() or None
    except TraceException:
      await self.session.rollback()
      raise
    await self.session.commit()
    return (await self.session.execute(select(RebarScheduleRow).where(RebarScheduleRow.id == row_id))).scalar_one()

  async def bulk_review(self, org: UUID, import_id: UUID, user_id: UUID, row_ids: list[UUID], decision: str) -> dict:
    imp = await self._import(org, import_id, lock=True)
    self._require_pending(imp)
    wanted, updated, failed = set(row_ids), 0, []
    rules = await self._profile_rules(org) if decision == "CONFIRMED" else ()
    shapes = {s.code: s for s in (repo.shape_spec(r) for r in await repo.load_shape_rows(self.session, org))}
    sizes = tuple(repo.size_spec(s) for s in await repo.load_size_rows(self.session, org))
    for row in await self._rows(org, import_id):
      if row.id not in wanted:
        continue
    
      try:
        if decision == "CONFIRMED":
          await self._computable(org, row, rules, shapes, sizes)
      except TraceException as exc:
        failed.append({"row_id": str(row.id), "code": exc.code, "message": str(exc)})
        continue
    
      row.review_status = decision
      row.reviewed_by_user_id = user_id if decision != "PENDING" else None
      row.reviewed_at = _now() if decision != "PENDING" else None
      updated += 1
    await self.session.commit()
    return {"updated": updated, "failed": failed}

  async def confirm_import(self, org: UUID, import_id: UUID, user_id: UUID, reject_pending: bool) -> dict:
    imp = await self._import(org, import_id, lock=True)
    self._require_pending(imp)
    rows = await self._rows(org, import_id)
    pending = [r for r in rows if r.review_status == "PENDING"]
    if pending and not reject_pending:
      raise TraceException(f"{len(pending)} row(s) are still pending. Confirm or reject them, or reject the rest.",
        status_code=409, code="PENDING_ROWS_REMAIN")
    for r in pending:
      r.review_status, r.reviewed_by_user_id, r.reviewed_at = "REJECTED", user_id, _now()
    confirmed = [r for r in rows if r.review_status == "CONFIRMED"]
    
    if not confirmed:
      raise TraceException("No rows were confirmed.", status_code=422, code="NO_CONFIRMED_ROWS")
    imp.status, imp.row_count, imp.confirmed_count = "CONFIRMED", len(rows), len(confirmed)
    imp.confirmed_by_user_id, imp.confirmed_at = user_id, _now()
    iid = imp.id
    await self.session.commit()
    await self._log(org, user_id, iid, AuditAction.APPROVE, f"Confirmed {len(confirmed)} of {len(rows)} bar schedule row(s)")
    return {"schedule_import_id": iid, "confirmed_count": len(confirmed), "rejected_count": sum(r.review_status == "REJECTED" for r in rows),
      "pending_count": 0}

  async def reject_import(self, org: UUID, import_id: UUID, user_id: UUID) -> dict:
    imp = await self._import(org, import_id, lock=True)
    self._require_pending(imp)
    imp.status = "REJECTED"
    await self.session.commit()
    await self._log(org, user_id, import_id, AuditAction.UPDATE, "Rejected bar schedule import")
    return {"schedule_import_id": import_id, "confirmed_count": 0, "rejected_count": imp.row_count, "pending_count": 0}

  async def archive_import(self, org: UUID, import_id: UUID, user_id: UUID) -> dict:
    imp = await self._import(org, import_id, lock=True)
    
    if imp.status != "CONFIRMED":
      raise TraceException("Only confirmed imports can be archived.", status_code=409, code="IMPORT_NOT_CONFIRMED")
    imp.status = "ARCHIVED"
    await self.session.commit()
    await self._log(org, user_id, import_id, AuditAction.DELETE, "Archived bar schedule import")
    return {"schedule_import_id": import_id, "confirmed_count": imp.confirmed_count, "rejected_count": 0, "pending_count": 0}

  async def list_shapes(self, org: UUID):
    return await repo.load_shape_rows(self.session, org)

  async def list_sizes(self, org: UUID):
    return await repo.load_size_rows(self.session, org)

  async def create_shape(self, org: UUID, user_id: UUID, payload) -> RebarShape:
    code = payload.code.strip().upper()
    if (await self.session.execute(select(RebarShape.id).where(RebarShape.organization_id == org, RebarShape.code == code))).first():
      raise TraceException("A shape with this code already exists.", status_code=409, code="REBAR_SHAPE_EXISTS")
    names = [str(s.get("param") if isinstance(s, dict) else s) for s in payload.segments]
    
    if not names:
      raise TraceException("A shape needs at least one segment.", status_code=422, code="REBAR_SHAPE_EMPTY")
    shape = RebarShape(id=uuid4(), organization_id=org, code=code, name=payload.name, description=payload.description,
      standard=payload.standard, segments=names, bend_spec=list(payload.bend_spec), bend_count=len(payload.bend_spec),
      hook_ends=payload.hook_ends, is_system=False, is_active=True)
    self.session.add(shape)
    await self.session.commit()
    return shape

  async def create_size(self, org: UUID, user_id: UUID, payload) -> BarSize:
    if (await self.session.execute(select(BarSize.id).where(BarSize.organization_id == org, BarSize.standard == payload.standard,
      BarSize.designation == payload.designation, BarSize.grade == payload.grade))).first():
      raise TraceException("This bar size already exists.", status_code=409, code="BAR_SIZE_EXISTS")
  
    size = BarSize(id=uuid4(), organization_id=org, standard=payload.standard, designation=payload.designation, grade=payload.grade,
      nominal_dia_mm=payload.nominal_dia_mm, unit_weight_kg_m=payload.unit_weight_kg_m, is_system=False, is_active=True)
    self.session.add(size)
    await self.session.commit()
    return size

  async def list_bar_marks(self, org: UUID, run_id: UUID, *, limit: int, after: UUID | None, provenance: str | None, role: str | None):
    await CalculationService(self.session).get_run(org, run_id)
    rows = await repo.bar_marks_page(self.session, org, run_id, limit=limit, after=after, provenance=provenance, role=role)
    return rows[:limit], (rows[limit - 1].id if len(rows) > limit else None)

  async def summary(self, org: UUID, version_id: UUID) -> dict:
    version = (await self.session.execute(select(BOQVersion).where(BOQVersion.id == version_id,
      BOQVersion.organization_id == org))).scalar_one_or_none()
    if version is None:
      raise TraceException("BOQ version not found.", status_code=404, code="BOQ_VERSION_NOT_FOUND")
    if version.calculation_run_id is None:
      raise TraceException("This BOQ version was not built from a calculation run.", status_code=422, code="NOT_ENGINE_VERSION")
    return {"boq_version_id": version.id, **await repo.summary_for_run(self.session, org, version.calculation_run_id)}