from __future__ import annotations
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass, field
import asyncio
import hashlib
import os
import re
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.projects.repository import ProjectRepository
from app.modules.audit.service import AuditLogService
from app.modules.subscriptions.service import SubscriptionService
from app.modules.identity.rate_limit import RateLimiter
from app.core.redis import redis_client
from app.modules.drawings_boq.schedule_parsing import (norm_key, CSV_CONFIDENCE, KIND_DEFAULT_WORK_ITEM, SURFACE_UNIT, SURFACES, ScheduleParseError, build_schedule_rows_prompt, canonicalize, norm_mark, 
  parse_ai_rows, read_table, rows_from_table, suggest_finish_work_item,
)
from app.modules.drawings_boq.finish_schedule.common import audit_entity, current_ifc_drawing_ids, require_work_item, work_item_catalog
from uuid import UUID, uuid4
from app.core.exceptions import TraceException
from app.modules.drawings_boq.models import ScheduleImport, DrawingElement, BuildingLevel, BuildingSpace, Drawing, DrawingFormat, ScheduleRow, SpaceFinish
from app.modules.audit.models import AuditAction
from sqlalchemy import and_, or_, select, update
from pathlib import PurePosixPath
import tempfile
from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.modules.ai_requests.models import AIEntityType, AIRequestPurpose
from app.modules.ai_requests.service import AIOrchestratorService
from app.modules.drawings_boq.pdf_extraction import extract_pdf_text
from app.shared.storage import download_to_path
from app.modules.drawings_boq.boq_logic import UNIT_TABLE

MAX_FILE_BYTES = 5 * 1024 * 1024
_ZERO = Decimal("0")

def _now():
  return datetime.now(timezone.utc)

@dataclass(frozen=True)
class _ElementRef:
  mark_key: str
  tokens: frozenset

@dataclass
class _Match:
  elements: dict = field(default_factory=dict)
  spaces: dict = field(default_factory=dict)
  space_levels: dict = field(default_factory=dict)
  levels: dict = field(default_factory=dict)
  catalog: dict = field(default_factory=dict)

def _name_tokens(name: str | None) -> frozenset:
  parts = re.findall(r"[A-Za-z0-9]+", name or "")
  return frozenset({norm_key(p) for p in parts} | {norm_key(a + b) for a, b in zip(parts, parts[1:])})

def count_matches(kind: str, mark: str | None, elements: dict) -> int:
  key = norm_mark(mark)
  if not key:
    return 0
  return sum(1 for e in elements.get(kind, ()) if e.mark_key == key or (len(key) >= 2 and key in e.tokens))

class ScheduleService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.projects = ProjectRepository(session)
    self.audit = AuditLogService(session)
    self.subscriptions = SubscriptionService(session)
    self.rate_limiter = RateLimiter(redis_client)

  async def _log(self, org, user_id, entity_id, action, message) -> None:
    await self.audit.log(org, user_id, audit_entity("SCHEDULE_IMPORT"), entity_id, action, message)

  async def _require_project(self, org: UUID, project_id: UUID) -> None:
    if await self.projects.get_by_id_and_org(project_id, org) is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

  async def _import(self, org: UUID, import_id: UUID, lock: bool = False) -> ScheduleImport:
    stmt = select(ScheduleImport).where(ScheduleImport.id == import_id, ScheduleImport.organization_id == org)
    if lock:
      stmt = stmt.with_for_update()
    imp = (await self.session.execute(stmt)).scalar_one_or_none()
    if imp is None:
      raise TraceException("Schedule import not found.", status_code=404, code="SCHEDULE_IMPORT_NOT_FOUND")
    return imp

  async def _rows(self, org: UUID, import_id: UUID) -> list[ScheduleRow]:
    r = await self.session.execute(select(ScheduleRow).where(
      ScheduleRow.schedule_import_id == import_id, ScheduleRow.organization_id == org).order_by(ScheduleRow.row_no.asc()))
    return list(r.scalars().all())

  @staticmethod
  def _require_pending(imp: ScheduleImport) -> None:
    if imp.status != "PENDING_REVIEW":
      raise TraceException("Only imports awaiting review can be edited.", status_code=409, code="IMPORT_NOT_EDITABLE")

  async def _load_match(self, org: UUID, project_id: UUID) -> _Match:
    m = _Match()
    drawing_ids = await current_ifc_drawing_ids(self.session, org, project_id)
    if drawing_ids:
      rows = (await self.session.execute(select(DrawingElement.type_mark, DrawingElement.name, DrawingElement.structural_role)
        .where(DrawingElement.organization_id == org, DrawingElement.drawing_id.in_(drawing_ids),
          DrawingElement.structural_role.in_(("DOOR", "WINDOW")), DrawingElement.normalization_status != "INVALID"))).all()
      for mark, name, role in rows:
        m.elements.setdefault(role, []).append(_ElementRef(norm_mark(mark), _name_tokens(name)))
      for lv in (await self.session.execute(select(BuildingLevel).where(
        BuildingLevel.organization_id == org, BuildingLevel.drawing_id.in_(drawing_ids))
        .order_by(BuildingLevel.sequence.asc()))).scalars().all():
        m.levels.setdefault(norm_key(lv.name), lv.id)
        
    keyed: dict = {}
    spaces = (await self.session.execute(select(BuildingSpace).where(
      BuildingSpace.organization_id == org, BuildingSpace.project_id == project_id, BuildingSpace.is_active.is_(True),
      or_(BuildingSpace.drawing_id.in_(drawing_ids), and_(BuildingSpace.drawing_id.is_(None), BuildingSpace.source == "MANUAL"))
    ))).scalars().all()
    for s in spaces:
      m.space_levels[s.id] = s.level_id
      for k in {norm_key(s.number), norm_key(s.name), norm_key(f"{s.number or ''}{s.name or ''}"), norm_key(s.long_name)}:
        if k:
          keyed.setdefault(k, set()).add(s.id)
    m.spaces = {k: next(iter(v)) for k, v in keyed.items() if len(v) == 1}
    m.catalog = await work_item_catalog(self.session, org)
    return m

  def _build_row(self, imp: ScheduleImport, org: UUID, n: int, p: dict, m: _Match) -> ScheduleRow:
    kind = imp.schedule_kind
    extra: dict = {"notes": list(p.get("notes") or [])}
    unit, qty = p.get("unit"), p.get("quantity")
    confidence = Decimal(p.get("confidence") or CSV_CONFIDENCE)
    if kind in ("DOOR", "WINDOW"):
      unit = unit or "nos"
      if qty is None:
        qty, extra["quantity_defaulted"] = Decimal("1"), True
        confidence = min(confidence, Decimal("0.7"))
        
    surface = p.get("surface") if kind == "FINISH" else None
    location = p.get("location_text")
    space_id = m.spaces.get(norm_key(location)) if kind == "FINISH" and location else None
    level_id = m.levels.get(norm_key(p.get("level_text"))) if p.get("level_text") else m.space_levels.get(space_id)
    
    wi = p.get("work_item_code")
    if wi not in m.catalog:
      wi = KIND_DEFAULT_WORK_ITEM.get(kind)
      if kind == "FINISH":
        wi = suggest_finish_work_item(surface, f"{p.get('description') or ''} {p.get('finish_name') or ''}")
      if wi not in m.catalog:
        wi = None
    if kind == "FINISH":
      extra["surface"], extra["finish_name"] = surface, p.get("finish_name")
    row = ScheduleRow(
      id=uuid4(), organization_id=org, schedule_import_id=imp.id, row_no=n, schedule_kind=kind,
      raw_text=p.get("raw_text"), mark=(p.get("mark") or "")[:100] or None,
      description=(p.get("description") or "")[:500] or None, location_text=(location or "")[:300] or None,
      level_id=level_id, space_id=space_id, unit=(unit or "")[:20] or None, quantity=qty,
      width_mm=p.get("width_mm"), height_mm=p.get("height_mm"), work_item_code=wi,
      confidence=max(_ZERO, min(Decimal("1"), confidence)), review_status="PENDING",
      matched_element_count=count_matches(kind, p.get("mark"), m.elements) if kind in ("DOOR", "WINDOW") else 0,
      extra=extra)
    self._refresh_canonical(row)
    return row

  @staticmethod
  def _refresh_canonical(row: ScheduleRow) -> None:
    extra = dict(row.extra or {})
    notes = [x for x in extra.get("notes", []) if not x.startswith("Unit '")]
    if row.schedule_kind == "FINISH" and row.space_id and extra.get("surface") in SURFACE_UNIT:
      row.canonical_unit, row.canonical_quantity = SURFACE_UNIT[extra["surface"]], _ZERO
    else:
      cu, cq, note = canonicalize(row.unit, row.quantity)
      row.canonical_unit, row.canonical_quantity = cu, cq
      if note and note not in notes:
        notes.append(note)
      if row.unit and cu is None:
        notes.append(f"Unit '{row.unit}' is not recognised.")
    extra["notes"] = notes
    row.extra = extra

  async def _assert_not_duplicate(self, project_id: UUID, content_hash: str) -> None:
    r = await self.session.execute(select(ScheduleImport.id).where(
      ScheduleImport.project_id == project_id, ScheduleImport.content_hash == content_hash,
      ScheduleImport.status.in_(("PENDING_REVIEW", "CONFIRMED"))))
    if r.first() is not None:
      raise TraceException("This schedule has already been imported for this project.",
        status_code=409, code="SCHEDULE_ALREADY_IMPORTED")

  async def _create_import(self, org, project_id, user_id, *, source, kind, parsed, file_name, content_hash,
    drawing_id=None, notes=None, meta=None) -> ScheduleImport:
    imp = ScheduleImport(
      id=uuid4(), organization_id=org, project_id=project_id, drawing_id=drawing_id, source=source,
      schedule_kind=kind, status="PENDING_REVIEW", file_name=(file_name or "")[:500] or None,
      content_hash=content_hash, row_count=0, confirmed_count=0, extraction_meta=meta or {}, notes=notes,
      created_by_user_id=user_id)
    self.session.add(imp)
    await self.session.flush()
    m = await self._load_match(org, project_id)
    rows = [self._build_row(imp, org, i, p, m) for i, p in enumerate(parsed, start=1)]
    self.session.add_all(rows)
    imp.row_count = len(rows)
    
    try:
      await self.session.flush()
      iid = imp.id
      await self.session.commit()
    except IntegrityError:
      await self.session.rollback()
      raise TraceException("This schedule has already been imported for this project.",
        status_code=409, code="SCHEDULE_ALREADY_IMPORTED")
    await self._log(org, user_id, iid, AuditAction.CREATE, f"Imported {len(rows)} {kind.lower()} schedule row(s) from {source}")
    return await self._import(org, iid)

  async def create_from_file(self, org: UUID, project_id: UUID, user_id: UUID, kind: str, file: UploadFile,
    notes: str | None) -> ScheduleImport:
    await self._require_project(org, project_id)
    name = file.filename or "schedule"
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in (".csv", ".txt", ".xlsx"):
      raise TraceException("Upload a .csv or .xlsx file. For a PDF schedule, import it from the drawing.",
        status_code=422, code="UNSUPPORTED_SCHEDULE_FORMAT")
      
    contents = await file.read(MAX_FILE_BYTES + 1)
    if len(contents) > MAX_FILE_BYTES:
      raise TraceException("The schedule file is too large.", status_code=413, code="FILE_TOO_LARGE")
    if not contents:
      raise TraceException("The uploaded file is empty.", status_code=422, code="EMPTY_UPLOAD")
    content_hash = hashlib.sha256(kind.encode() + contents).hexdigest()
    await self._assert_not_duplicate(project_id, content_hash)
    try:
      parsed = rows_from_table(read_table(contents, name), kind)
    except ScheduleParseError as exc:
      raise TraceException(str(exc), status_code=422, code="SCHEDULE_UNREADABLE")
    except Exception:
      raise TraceException("The file could not be read as a schedule.", status_code=422, code="SCHEDULE_UNREADABLE")
    return await self._create_import(org, project_id, user_id, source="CSV", kind=kind, parsed=parsed, file_name=name,
      content_hash=content_hash, notes=notes, meta={"format": suffix.lstrip(".")})

  async def create_from_pdf(self, org: UUID, project_id: UUID, user_id: UUID, drawing_id: UUID, kind: str,
    notes: str | None) -> ScheduleImport:
    await self._require_project(org, project_id)
    drawing = (await self.session.execute(select(Drawing).where(
      Drawing.id == drawing_id, Drawing.organization_id == org, Drawing.project_id == project_id))).scalar_one_or_none()
    
    if drawing is None:
      raise TraceException("Drawing not found.", status_code=404, code="DRAWING_NOT_FOUND")
    if drawing.format != DrawingFormat.PDF:
      raise TraceException("Schedules can be extracted from PDF drawings only.", status_code=422, code="DRAWING_NOT_PDF")
    await self.subscriptions.check_quota(org, "ai_requests")
    await self.rate_limiter.check(key=f"ai_per_org:{org}", limit=settings.rate_limit_ai_per_org_per_minute, window_seconds=60)
    with tempfile.TemporaryDirectory() as tmp:
      path = os.path.join(tmp, "drawing.pdf")
      await asyncio.to_thread(download_to_path, drawing.storage_key, path)
      with open(path, "rb") as handle:
        contents = handle.read()
    text = await asyncio.to_thread(extract_pdf_text, contents)
    
    if not text:
      raise TraceException("This PDF has no machine-readable text (it may be a scan).", status_code=422, code="PDF_NO_TEXT")
    content_hash = hashlib.sha256(f"{kind}|{text}".encode()).hexdigest()
    await self._assert_not_duplicate(project_id, content_hash)
    result = await AIOrchestratorService(self.session).run(
      organization_id=org, purpose=AIRequestPurpose.PDF_SCHEDULE_EXTRACTION, entity_type=AIEntityType.DRAWING,
      entity_id=drawing.id, prompt=build_schedule_rows_prompt(kind, text))
    await self.subscriptions.increment_usage(org, "ai_requests")
    parsed = parse_ai_rows(result.parsed_output, kind) if result.success else []
    if not parsed:
      await self.session.commit()
      raise TraceException("No schedule rows could be extracted from this PDF.", status_code=422, code="NO_SCHEDULE_ROWS_FOUND")
    return await self._create_import(org, project_id, user_id, source="PDF_AI", kind=kind, parsed=parsed,
      file_name=drawing.original_filename, content_hash=content_hash, drawing_id=drawing.id, notes=notes,
      meta={"extraction": "ai", "text_chars": len(text)})

  async def create_manual(self, org: UUID, project_id: UUID, user_id: UUID, kind: str, notes: str | None) -> ScheduleImport:
    await self._require_project(org, project_id)
    return await self._create_import(org, project_id, user_id, source="MANUAL", kind=kind, parsed=[], file_name=None,
      content_hash=None, notes=notes)

  async def list_imports(self, org: UUID, project_id: UUID, status: str | None = None) -> list[ScheduleImport]:
    await self._require_project(org, project_id)
    stmt = select(ScheduleImport).where(ScheduleImport.organization_id == org, ScheduleImport.project_id == project_id)
    if status:
      stmt = stmt.where(ScheduleImport.status == status)
    return list((await self.session.execute(stmt.order_by(ScheduleImport.created_at.desc()))).scalars().all())

  @staticmethod
  def _decorate_row(r: ScheduleRow) -> ScheduleRow:
    extra = r.extra or {}
    r.surface, r.finish_name = extra.get("surface"), extra.get("finish_name")
    r.notes, r.quantity_defaulted = list(extra.get("notes", [])), bool(extra.get("quantity_defaulted"))
    return r

  @staticmethod
  def _mismatches(rows: list[ScheduleRow]) -> list[dict]:
    return [{"row_id": str(r.id), "mark": r.mark, "schedule_quantity": str(r.canonical_quantity),
      "model_count": r.matched_element_count}
      for r in rows if r.schedule_kind in ("DOOR", "WINDOW") and r.matched_element_count > 0
      and r.canonical_quantity is not None and Decimal(r.canonical_quantity) != Decimal(r.matched_element_count)]

  def _summary(self, rows: list[ScheduleRow]) -> dict:
    return {
      "pending": sum(r.review_status == "PENDING" for r in rows),
      "confirmed": sum(r.review_status == "CONFIRMED" for r in rows),
      "rejected": sum(r.review_status == "REJECTED" for r in rows),
      "model_matched": sum(r.matched_element_count > 0 for r in rows),
      "finish_rows_linked": sum(r.schedule_kind == "FINISH" and r.space_id is not None for r in rows),
      "finish_rows_unlinked": sum(r.schedule_kind == "FINISH" and r.space_id is None for r in rows),
      "count_mismatches": self._mismatches(rows),
    }

  async def get_detail(self, org: UUID, import_id: UUID) -> ScheduleImport:
    imp = await self._import(org, import_id)
    rows = await self._rows(org, import_id)
    imp.rows = [self._decorate_row(r) for r in rows]
    imp.summary = self._summary(rows)
    return imp

  async def _validate_confirmable(self, org: UUID, row: ScheduleRow) -> None:
    def fail(message: str, code: str):
      raise TraceException(f"Row {row.row_no}: {message}", status_code=422, code=code)
    if not row.work_item_code:
      fail("choose a work item.", "ROW_NEEDS_WORK_ITEM")
    wi = await require_work_item(self.session, org, row.work_item_code)
    extra = row.extra or {}
    linked_finish = row.schedule_kind == "FINISH" and row.space_id is not None
    if linked_finish and extra.get("surface") not in SURFACES:
      fail("set the surface (floor, wall, ceiling, skirting or dado).", "ROW_NEEDS_SURFACE")
    if row.canonical_unit is None or row.canonical_quantity is None:
      fail("the unit or quantity is missing or not recognised.", "ROW_NEEDS_QUANTITY")
    if not linked_finish and Decimal(row.canonical_quantity) <= 0:
      fail("the quantity must be greater than zero.", "ROW_ZERO_QUANTITY")
    family = UNIT_TABLE.get((wi.unit or "").strip().lower())
    if family is not None and family[0] != row.canonical_unit:
      fail(f"work item {wi.code} is measured in {family[0]}, but the row is in {row.canonical_unit}.", "ROW_UNIT_MISMATCH")

  async def _apply_fields(self, org: UUID, imp: ScheduleImport, row: ScheduleRow, payload, m: _Match) -> None:
    fs = payload.model_fields_set
    extra = dict(row.extra or {})
    for key, limit in (("mark", 100), ("description", 500), ("location_text", 300), ("unit", 20)):
      if key in fs:
        setattr(row, key, ((getattr(payload, key) or "").strip())[:limit] or None)
    if "quantity" in fs:
      row.quantity, extra.pop("quantity_defaulted", None) if payload.quantity is not None else None
    if "width_mm" in fs:
      row.width_mm = payload.width_mm
    if "height_mm" in fs:
      row.height_mm = payload.height_mm
    if "level_id" in fs:
      if payload.level_id is not None and (await self.session.execute(select(BuildingLevel.id).where(
        BuildingLevel.id == payload.level_id, BuildingLevel.organization_id == org))).first() is None:
        raise TraceException("Level not found.", status_code=404, code="LEVEL_NOT_FOUND")
      row.level_id = payload.level_id
      
    if "space_id" in fs:
      if payload.space_id is not None and (await self.session.execute(select(BuildingSpace.id).where(
        BuildingSpace.id == payload.space_id, BuildingSpace.organization_id == org,
        BuildingSpace.project_id == imp.project_id))).first() is None:
        raise TraceException("Space not found.", status_code=404, code="SPACE_NOT_FOUND")
      row.space_id = payload.space_id
    elif "location_text" in fs and row.schedule_kind == "FINISH" and row.space_id is None and row.location_text:
      row.space_id = m.spaces.get(norm_key(row.location_text))
    if "work_item_code" in fs:
      if payload.work_item_code:
        await require_work_item(self.session, org, payload.work_item_code)
      row.work_item_code = payload.work_item_code or None
    if "surface" in fs:
      extra["surface"] = payload.surface
    if "finish_name" in fs:
      extra["finish_name"] = (payload.finish_name or "").strip() or None
    row.extra = extra
    self._refresh_canonical(row)
    if row.schedule_kind in ("DOOR", "WINDOW") and "mark" in fs:
      row.matched_element_count = count_matches(row.schedule_kind, row.mark, m.elements)

  async def add_row(self, org: UUID, import_id: UUID, user_id: UUID, payload) -> ScheduleRow:
    imp = await self._import(org, import_id, lock=True)
    self._require_pending(imp)
    n = (await self._rows(org, import_id))[-1].row_no + 1 if imp.row_count else 1
    m = await self._load_match(org, imp.project_id)
    row = ScheduleRow(id=uuid4(), organization_id=org, schedule_import_id=imp.id, row_no=n, schedule_kind=imp.schedule_kind,
      confidence=Decimal("1"), review_status="PENDING", matched_element_count=0, extra={"notes": []})
    self.session.add(row)
    await self._apply_fields(org, imp, row, payload, m)
    imp.row_count += 1
    await self.session.flush()
    rid = row.id
    await self.session.commit()
    await self._log(org, user_id, imp.id, AuditAction.UPDATE, f"Added schedule row {n}")
    return self._decorate_row((await self.session.execute(select(ScheduleRow).where(ScheduleRow.id == rid))).scalar_one())

  async def update_row(self, org: UUID, row_id: UUID, user_id: UUID, payload) -> ScheduleRow:
    row = (await self.session.execute(select(ScheduleRow).where(
      ScheduleRow.id == row_id, ScheduleRow.organization_id == org).with_for_update())).scalar_one_or_none()
    if row is None:
      raise TraceException("Schedule row not found.", status_code=404, code="SCHEDULE_ROW_NOT_FOUND")
    imp = await self._import(org, row.schedule_import_id)
    self._require_pending(imp)
    m = await self._load_match(org, imp.project_id)
    
    try:
      await self._apply_fields(org, imp, row, payload, m)
      fs = payload.model_fields_set
      if payload.review_status == "CONFIRMED":
        await self._validate_confirmable(org, row)
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
    return self._decorate_row((await self.session.execute(select(ScheduleRow).where(ScheduleRow.id == row_id))).scalar_one())

  async def bulk_review(self, org: UUID, import_id: UUID, user_id: UUID, row_ids: list[UUID], decision: str) -> dict:
    imp = await self._import(org, import_id, lock=True)
    self._require_pending(imp)
    wanted = set(row_ids)
    updated, failed = 0, []
    for row in await self._rows(org, import_id):
      if row.id not in wanted:
        continue
    
      try:
        if decision == "CONFIRMED":
          await self._validate_confirmable(org, row)
      except TraceException as exc:
        failed.append({"row_id": str(row.id), "code": exc.code, "message": exc.message if hasattr(exc, "message") else str(exc)})
        continue
      row.review_status = decision
      row.reviewed_by_user_id = user_id if decision != "PENDING" else None
      row.reviewed_at = _now() if decision != "PENDING" else None
      updated += 1
    await self.session.commit()
    return {"updated": updated, "failed": failed}

  async def _recount(self, org: UUID, imp: ScheduleImport, rows: list[ScheduleRow]) -> int:
    m = await self._load_match(org, imp.project_id)
    changed = 0
    for r in rows:
      if r.schedule_kind in ("DOOR", "WINDOW"):
        n = count_matches(r.schedule_kind, r.mark, m.elements)
        if n != r.matched_element_count:
          r.matched_element_count, changed = n, changed + 1
    return changed

  async def rematch(self, org: UUID, import_id: UUID, user_id: UUID) -> dict:
    imp = await self._import(org, import_id, lock=True)
    if imp.status not in ("PENDING_REVIEW", "CONFIRMED"):
      raise TraceException("This import cannot be re-matched.", status_code=409, code="IMPORT_NOT_EDITABLE")
    rows = await self._rows(org, import_id)
    changed = await self._recount(org, imp, rows)
    await self.session.commit()
    return {"rows_changed": changed, "rerun_recommended": changed > 0 and imp.status == "CONFIRMED"}

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
    await self._recount(org, imp, rows)

    created = updated = 0
    conflicts: list[dict] = []
    for r in confirmed:
      surface = (r.extra or {}).get("surface")
      if r.schedule_kind != "FINISH" or r.space_id is None or surface not in SURFACES:
        continue
      cur = (await self.session.execute(select(SpaceFinish).where(
        SpaceFinish.space_id == r.space_id, SpaceFinish.surface == surface,
        SpaceFinish.work_item_code == r.work_item_code))).scalar_one_or_none()
      if cur is not None and cur.source == "MANUAL" and cur.is_active:
        conflicts.append({"row_id": str(r.id), "space_id": str(r.space_id), "surface": surface,
          "work_item_code": r.work_item_code, "reason": "A manual finish already exists; it was kept."})
        continue
    
      height = r.height_mm if r.height_mm and r.height_mm > 0 else None
      review = "OK" if r.confidence >= Decimal("0.6") else "REVIEW_REQUIRED"
      name = (r.extra or {}).get("finish_name") or r.description
      if cur is None:
        self.session.add(SpaceFinish(id=uuid4(), organization_id=org, space_id=r.space_id, surface=surface,
          work_item_code=r.work_item_code, finish_name=(name or "")[:200] or None, height_mm=height,
          source="SCHEDULE_IMPORT", schedule_row_id=r.id, confidence=r.confidence, review_status=review,
          is_active=True, created_by_user_id=user_id))
        created += 1
      else:
        cur.finish_name, cur.height_mm, cur.source = (name or "")[:200] or None, height, "SCHEDULE_IMPORT"
        cur.schedule_row_id, cur.confidence, cur.review_status, cur.is_active = r.id, r.confidence, review, True
        updated += 1

    imp.status, imp.row_count, imp.confirmed_count = "CONFIRMED", len(rows), len(confirmed)
    imp.confirmed_by_user_id, imp.confirmed_at = user_id, _now()
    await self.session.flush()
    iid = imp.id
    await self.session.commit()
    await self._log(org, user_id, iid, AuditAction.APPROVE, f"Confirmed {len(confirmed)} of {len(rows)} schedule row(s)")
    return {
      "schedule_import": await self._import(org, iid), "finishes_created": created, "finishes_updated": updated,
      "finish_conflicts": conflicts,
      "ledger_lines": sum(1 for r in confirmed if r.matched_element_count == 0
        and not (r.schedule_kind == "FINISH" and r.space_id is not None)),
      "model_matched_rows": sum(1 for r in confirmed if r.matched_element_count > 0),
      "unlinked_finish_rows": sum(1 for r in confirmed if r.schedule_kind == "FINISH" and r.space_id is None),
      "count_mismatches": self._mismatches(confirmed), "rerun_recommended": True,
    }

  async def reject_import(self, org: UUID, import_id: UUID, user_id: UUID, note: str | None) -> ScheduleImport:
    imp = await self._import(org, import_id, lock=True)
    self._require_pending(imp)
    imp.status, imp.notes = "REJECTED", (note or imp.notes)
    await self.session.commit()
    await self._log(org, user_id, import_id, AuditAction.UPDATE, "Rejected schedule import")
    return await self._import(org, import_id)

  async def archive_import(self, org: UUID, import_id: UUID, user_id: UUID) -> ScheduleImport:
    imp = await self._import(org, import_id, lock=True)
    if imp.status != "CONFIRMED":
      raise TraceException("Only confirmed imports can be archived.", status_code=409, code="IMPORT_NOT_CONFIRMED")
    ids = [r.id for r in await self._rows(org, import_id)]
    if ids:
      await self.session.execute(update(SpaceFinish).where(
        SpaceFinish.schedule_row_id.in_(ids), SpaceFinish.source == "SCHEDULE_IMPORT").values(is_active=False))
      
    imp.status = "ARCHIVED"
    await self.session.commit()
    await self._log(org, user_id, import_id, AuditAction.DELETE, "Archived schedule import")
    return await self._import(org, import_id)