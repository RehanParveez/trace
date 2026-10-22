from __future__ import annotations
from datetime import datetime, timezone, timedelta
import asyncio
import hashlib
import io
import re
from uuid import UUID, uuid4
from app.core.exceptions import TraceException
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.service import AuditLogService
from app.modules.drawings_boq.pricing.rate_repository import RateRepository
from app.modules.audit.models import AuditAction, AuditEntityType
from decimal import Decimal
from sqlalchemy import delete, func, or_, select
from app.modules.drawings_boq.pricing import mrs_parse as mp
from app.modules.drawings_boq.pricing import mrs_extract as ex
from app.modules.drawings_boq.pricing import mrs_import
from app.modules.drawings_boq.models import RateBook, RateItem, WorkItem
from app.modules.drawings_boq.pricing.models import RateImport, RateImportRow
from app.modules.drawings_boq.pricing.import_schemas import ImportUpdateRequest, BulkRowsRequest, PublishRequest, ReparseRequest, RowUpdateRequest
from app.modules.drawings_boq.pricing import import_logic as il
from app.modules.drawings_boq import boq_logic as logic

MAX_FILE_BYTES = 50 * 1024 * 1024
INLINE_CSV_BYTES = 1024 * 1024
INSERT_BATCH = 500
BULK_LIMIT = 20000
_EDITABLE = ("REVIEW",)

def _now():
  return datetime.now(timezone.utc)

class ObjectStore:
  def put(self, key: str, data: bytes, content_type: str | None = None) -> None:
    from app.shared.storage import upload_fileobj
    upload_fileobj(key, io.BytesIO(data), content_type)

  def get(self, key: str) -> bytes:
    from app.shared.storage import download_bytes
    return download_bytes(key)

  def delete(self, key: str) -> None:
    from app.shared.storage import delete_object
    delete_object(key)

def _default_enqueue(org: UUID, import_id: UUID) -> None:
  from app.modules.drawings_boq.pricing.import_tasks import parse_rate_import_task
  parse_rate_import_task.delay(str(org), str(import_id))

STALE_PARSING = timedelta(minutes=30)

def _safe_name(name: str) -> str:
  base = re.sub(r"[^A-Za-z0-9._\-]+", "_", (name or "schedule").replace("\\", "/").split("/")[-1])
  return base[:120] or "schedule"

def storage_key(org: UUID, import_id: UUID, filename: str) -> str:
  return f"{org}/rate-imports/{import_id}/{_safe_name(filename)}"

def _sniff(filename: str, data: bytes) -> str:
  if data[:5] == b"%PDF-":
    return "PDF"
  if (filename or "").lower().endswith((".csv", ".txt")):
    return "CSV"
  raise TraceException("Upload a PDF or a UTF-8 CSV file.", status_code=422, code="RATE_IMPORT_FILE_TYPE")

class RateImportService:
  def __init__(self, session: AsyncSession, store: ObjectStore | None = None, enqueue=None):
    self.session = session
    self.store = store or ObjectStore()
    self.enqueue = enqueue or _default_enqueue
    self.audit = AuditLogService(session)
    self.rates = RateRepository(session)

  async def _import(self, org: UUID, import_id: UUID, *, for_update: bool = False) -> RateImport:
    q = select(RateImport).where(RateImport.id == import_id, RateImport.organization_id == org)
    if for_update:
      q = q.with_for_update()
    imp = (await self.session.execute(q)).scalar_one_or_none()
    if imp is None:
      raise TraceException("Rate import not found.", status_code=404, code="RATE_IMPORT_NOT_FOUND")
    return imp

  async def _open(self, org: UUID, import_id: UUID) -> RateImport:
    imp = await self._import(org, import_id, for_update=True)
    if imp.status not in _EDITABLE:
      raise TraceException(f"This import is {imp.status} and can no longer be edited.", status_code=409, code="RATE_IMPORT_LOCKED")
    return imp

  async def _row(self, org: UUID, import_id: UUID, row_id: UUID) -> RateImportRow:
    row = (await self.session.execute(select(RateImportRow).where(
      RateImportRow.id == row_id, RateImportRow.import_id == import_id, RateImportRow.organization_id == org).with_for_update())).scalar_one_or_none()
    if row is None:
      raise TraceException("Row not found.", status_code=404, code="RATE_IMPORT_ROW_NOT_FOUND")
    return row

  async def counts(self, imp: RateImport) -> dict:
    r = RateImportRow
    q = select(
      func.count(), func.count().filter(r.skipped.is_(False)), func.count().filter(r.needs_review.is_(True)),
      func.count().filter(r.skipped.is_(False), r.work_item_code.is_not(None)),
      func.count().filter(r.skipped.is_(False), r.work_item_code.is_(None)),
      func.count().filter(r.skipped.is_(True)),
      func.count().filter(r.is_sample.is_(True)),
      func.count().filter(r.is_sample.is_(True), r.sample_verified.is_(False)),
      func.count().filter(r.edited.is_(True)),
    ).where(r.import_id == imp.id, r.organization_id == imp.organization_id)
    t = (await self.session.execute(q)).one()
    return {"rows": t[0], "live": t[1], "to_review": t[2], "mapped": t[3], "unmapped": t[4], "skipped": t[5], "samples": t[6],
      "samples_unverified": t[7], "edited": t[8]}

  async def with_counts(self, imp: RateImport) -> RateImport:
    imp.counts = await self.counts(imp)
    return imp

  async def get(self, org: UUID, import_id: UUID) -> RateImport:
    return await self.with_counts(await self._import(org, import_id))

  async def list_imports(self, org: UUID, *, status: str | None, limit: int, after: UUID | None):
    q = select(RateImport).where(RateImport.organization_id == org).order_by(RateImport.created_at.desc(), RateImport.id.desc())
    if status:
      q = q.where(RateImport.status == status)
    if after is not None:
      anchor = (await self.session.execute(select(RateImport.created_at, RateImport.id).where(RateImport.id == after, RateImport.organization_id == org))).first()
      if anchor is not None:
        q = q.where(or_(RateImport.created_at < anchor[0], (RateImport.created_at == anchor[0]) & (RateImport.id < anchor[1])))
        
    rows = list((await self.session.execute(q.limit(limit + 1))).scalars().all())
    nxt = rows[limit - 1].id if len(rows) > limit else None
    rows = rows[:limit]
    for imp in rows:
      await self.with_counts(imp)
    return rows, nxt

  async def create(self, org: UUID, user_id: UUID, filename: str, data: bytes, meta: dict) -> RateImport:
    if not data:
      raise TraceException("The file is empty.", status_code=422, code="RATE_IMPORT_EMPTY")
    if len(data) > MAX_FILE_BYTES:
      raise TraceException(f"The file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.", status_code=413, code="RATE_IMPORT_TOO_LARGE")
    kind = _sniff(filename, data)
    profile = meta.get("layout_profile") or "GENERIC"
    try:
      mp.get_profile(profile)
    except ValueError as exc:
      raise TraceException(str(exc), status_code=422, code="RATE_IMPORT_PROFILE") from exc
    first, last = int(meta.get("first_page") or 1), meta.get("last_page")
    if last is not None and int(last) < first:
      raise TraceException("The last page is before the first page.", status_code=422, code="RATE_IMPORT_PAGES")
    digest = hashlib.sha256(data).hexdigest()
    twin = (await self.session.execute(select(RateImport.id).where(RateImport.organization_id == org, RateImport.content_hash == digest,
      RateImport.status.in_(("REVIEW", "PUBLISHED"))).order_by(RateImport.created_at.desc()).limit(1))).scalar_one_or_none()
    import_id = uuid4()
    
    key = storage_key(org, import_id, filename)
    await asyncio.to_thread(self.store.put, key, data, "application/pdf" if kind == "PDF" else "text/csv")
    imp = RateImport(id=import_id, organization_id=org, created_by_user_id=user_id, status="UPLOADED", source_kind=kind,
      filename=_safe_name(filename), storage_key=key, file_size=len(data), content_hash=digest, layout_profile=profile,
      first_page=first, last_page=int(last) if last else None, book_code=(meta.get("book_code") or None), book_name=meta.get("book_name"),
      edition=meta.get("edition"), jurisdiction=meta.get("jurisdiction"), province=meta.get("province"), city=meta.get("city"),
      currency=(meta.get("currency") or "PKR").upper(), effective_from=meta.get("effective_from"), effective_to=meta.get("effective_to"),
      sample_seq=[], row_count=0)
    
    self.session.add(imp)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, imp.id, AuditAction.CREATE, f"Uploaded rate schedule {imp.filename} ({kind}, {len(data) // 1024} KB)")
    imp.duplicate_of_id = twin
    imp.counts = {}
    return imp

  async def dispatch(self, org: UUID, imp: RateImport) -> RateImport:
    if imp.source_kind == "CSV" and imp.file_size <= INLINE_CSV_BYTES:
      return await self.process(org, imp.id)
    try:
      await asyncio.to_thread(self.enqueue, org, imp.id)
    except Exception as exc:  
      imp = await self._import(org, imp.id, for_update=True)
      imp.status, imp.error_message = "FAILED", f"The file could not be queued for reading ({exc.__class__.__name__}). Try again."
      await self.session.commit()
    return await self.with_counts(await self._import(org, imp.id))

  async def update_meta(self, org: UUID, user_id: UUID, import_id: UUID, payload: ImportUpdateRequest) -> RateImport:
    imp = await self._import(org, import_id, for_update=True)
    if imp.status == "PUBLISHED":
      raise TraceException("A published import can't be changed.", status_code=409, code="RATE_IMPORT_LOCKED")
    for k, v in payload.model_dump(exclude_unset=True).items():
      setattr(imp, k, v.strip().upper() if k == "book_code" and isinstance(v, str) else v)
    await self.session.commit()
    return await self.with_counts(imp)

  async def delete(self, org: UUID, user_id: UUID, import_id: UUID) -> None:
    imp = await self._import(org, import_id, for_update=True)
    if imp.status == "PUBLISHED":
      raise TraceException("A published import is kept as the record of where the book's rates came from.", status_code=409, code="RATE_IMPORT_PUBLISHED")
    if imp.status == "PARSING" and not (imp.updated_at is not None and _now() - imp.updated_at > STALE_PARSING):
      raise TraceException("The file is being read. Try again when it finishes.", status_code=409, code="RATE_IMPORT_BUSY")
    key, name = imp.storage_key, imp.filename
    await self.session.delete(imp)
    await self.session.commit()
    if key:
      try:
        await asyncio.to_thread(self.store.delete, key)
      except Exception: 
        pass
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, import_id, AuditAction.DELETE, f"Deleted rate schedule import {name}")

  @staticmethod
  def _read_file(kind: str, data: bytes, profile_name: str, first_page: int, last_page: int | None, digest: str) -> dict:
    """CPU-heavy: runs in a thread. Returns plain data only."""
    profile = mp.get_profile(profile_name)
    if profile.reader == "table":
      if kind != "PDF":
        raise ValueError("This layout reads PDF files only.")
      return mrs_import.read_table(data, first_page, last_page, digest)
    if kind == "CSV":
      rows = mp.parse_csv(data, profile)
      unparsed: list[dict] = []
      report = mp.apply_checks(rows, unparsed, page_count=None, second_pass_tokens=None, content_hash=digest, profile=profile)
      return {"rows": rows, "report": report, "page_count": None, "offset": 0}
    extracted = ex.extract_pdf(data, first_page=first_page, last_page=last_page)
    offset = first_page - 1
    pages = extracted.pages
    
    rows, unparsed = mp.parse_pages(pages, profile)
    relative = {n - offset: toks for n, toks in extracted.second_pass_tokens.items()}
    report = mp.apply_checks(rows, unparsed, page_count=len(pages), second_pass_tokens=relative, content_hash=digest, profile=profile)
    if extracted.empty_text_pages:
      report["checks"].append({"code": "NO_TEXT_PAGES", "label": "Pages with no readable text", "status": "warn" if len(extracted.empty_text_pages) < max(1, len(pages) // 10) else "fail",
        "detail": "Scanned or image-only pages cannot be read here: " + ", ".join(str(p) for p in extracted.empty_text_pages[:30]), "count": len(extracted.empty_text_pages)})
      statuses = {c["status"] for c in report["checks"]}
      report["status"] = "FAIL" if "fail" in statuses else "PASS_WITH_WARNINGS" if "warn" in statuses else "PASS"
      
    for r in rows:
      if r.page is not None:
        r.page += offset
    for u in report.get("unparsed_sample", []):
      if u.get("page") is not None:
        u["page"] += offset
    report["page_range"] = [first_page, first_page + len(pages) - 1 if pages else first_page]
    return {"rows": rows, "report": report, "page_count": extracted.page_count, "offset": offset}

  async def catalog(self, org: UUID) -> list[il.CatalogEntry]:
    rows = (await self.session.execute(select(WorkItem.code, WorkItem.description, WorkItem.unit, WorkItem.csr_ref, WorkItem.trade).where(
      or_(WorkItem.organization_id == org, WorkItem.organization_id.is_(None)), WorkItem.is_active.is_(True)))).all()
    seen, out = set(), []
    for code, desc, unit, ref, trade in rows:
      if code in seen:
        continue
      seen.add(code)
      out.append(il.CatalogEntry(code=code, description=desc or "", unit=unit, csr_ref=ref, trade=trade))
    return out

  async def process(self, org: UUID, import_id: UUID) -> RateImport:
    """Read the stored file into rows. Safe to call again: the previous rows are replaced."""
    imp = await self._import(org, import_id, for_update=True)
    if imp.status in ("PUBLISHED", "CANCELLED"):
      raise TraceException(f"This import is {imp.status}.", status_code=409, code="RATE_IMPORT_LOCKED")
    imp.status, imp.error_message = "PARSING", None
    await self.session.commit()
    
    try:
      data = await asyncio.to_thread(self.store.get, imp.storage_key)
      out = await asyncio.to_thread(self._read_file, imp.source_kind, data, imp.layout_profile, imp.first_page, imp.last_page, imp.content_hash)
    except Exception as exc:  
      await self.session.rollback()
      imp = await self._import(org, import_id, for_update=True)
      imp.status = "FAILED"
      imp.error_message = (str(exc) or exc.__class__.__name__)[:500]
      await self.session.commit()
      return await self.with_counts(imp)

    imp = await self._import(org, import_id, for_update=True)
    await self.session.execute(delete(RateImportRow).where(RateImportRow.import_id == imp.id, RateImportRow.organization_id == org))
    rows, report = out["rows"], out["report"]
    sample = set(mp.spot_sample_indices(len(rows), imp.content_hash))
    catalog = await self.catalog(org)
    batch: list[RateImportRow] = []
    for idx, raw in enumerate(rows):
      seq = idx + 1
      suggestions = il.suggest(raw.description, raw.unit, raw.item_no, catalog) if raw.unit_known else []
      batch.append(RateImportRow(
        id=uuid4(), import_id=imp.id, organization_id=org, seq=seq, page=raw.page, line_no=raw.line_no, chapter=(raw.chapter or None) and raw.chapter[:200],
        item_no=(raw.item_no or None) and raw.item_no[:60], description=raw.description, raw_line=raw.raw_line, unit_raw=(raw.unit_raw or None) and raw.unit_raw[:60],
        basis_qty=raw.basis_qty, unit=raw.unit, unit_known=raw.unit_known, rate_raw=(raw.rate_raw or None) and raw.rate_raw[:60], rate=raw.rate, rate_alt=raw.rate_alt,
        unit_rate=il.unit_rate_of(raw.rate, raw.basis_qty), spec_key=raw.spec_key, labour=raw.labour, rate_kind=raw.rate_kind, flags=list(raw.flags), needs_review=il.needs_review(raw.flags, reviewed=False, skipped=False),
        suggestions=suggestions, is_sample=idx in sample))
      if len(batch) >= INSERT_BATCH:
        self.session.add_all(batch)
        await self.session.flush()
        batch = []
        
    if batch:
      self.session.add_all(batch)
    imp.status, imp.row_count, imp.report, imp.page_count = "REVIEW", len(rows), report, out["page_count"]
    imp.sample_seq = sorted(i + 1 for i in sample)
    imp.parsed_at = _now()
    await self.session.commit()
    await self.audit.log(org, imp.created_by_user_id, AuditEntityType.RATE_BOOK, imp.id, AuditAction.UPDATE,
      f"Read rate schedule {imp.filename}: {len(rows)} rows, checks {report['status']}")
    return await self.with_counts(imp)

  async def reparse(self, org: UUID, user_id: UUID, import_id: UUID, payload: ReparseRequest) -> RateImport:
    imp = await self._import(org, import_id, for_update=True)
    stale = imp.status == "PARSING" and imp.updated_at is not None and _now() - imp.updated_at > STALE_PARSING
    if imp.status == "PUBLISHED" or (imp.status == "PARSING" and not stale):
      raise TraceException(f"This import is {imp.status}.", status_code=409, code="RATE_IMPORT_LOCKED")
    data = payload.model_dump(exclude_unset=True)
    if data.get("layout_profile"):
      try:
        mp.get_profile(data["layout_profile"])
      except ValueError as exc:
        raise TraceException(str(exc), status_code=422, code="RATE_IMPORT_PROFILE") from exc
      imp.layout_profile = data["layout_profile"]
    if "first_page" in data and data["first_page"]:
      imp.first_page = data["first_page"]
    if "last_page" in data:
      imp.last_page = data["last_page"]
    if imp.last_page is not None and imp.last_page < imp.first_page:
      raise TraceException("The last page is before the first page.", status_code=422, code="RATE_IMPORT_PAGES")
    imp.status = "UPLOADED"
    await self.session.commit()
    return await self.with_counts(imp)

  def _row_query(self, org: UUID, import_id: UUID, *, flt: str | None, chapter: str | None, q: str | None):
    r = RateImportRow
    query = select(r).where(r.import_id == import_id, r.organization_id == org)
    if flt == "review":
      query = query.where(r.needs_review.is_(True))
    elif flt == "unmapped":
      query = query.where(r.work_item_code.is_(None), r.skipped.is_(False))
    elif flt == "mapped":
      query = query.where(r.work_item_code.is_not(None), r.skipped.is_(False))
    elif flt == "skipped":
      query = query.where(r.skipped.is_(True))
    elif flt == "sample":
      query = query.where(r.is_sample.is_(True))
    elif flt == "flagged":
      query = query.where(func.jsonb_array_length(r.flags) > 0)
    if chapter is not None:
      query = query.where(r.chapter == chapter) if chapter else query.where(r.chapter.is_(None))
    if q:
      like = f"%{q.strip().lower()}%"
      query = query.where(or_(func.lower(r.description).like(like), func.lower(func.coalesce(r.item_no, "")).like(like),
        func.lower(func.coalesce(r.work_item_code, "")).like(like)))
    return query

  async def list_rows(self, org: UUID, import_id: UUID, *, flt: str | None, chapter: str | None, q: str | None, after_seq: int | None, limit: int):
    await self._import(org, import_id)
    query = self._row_query(org, import_id, flt=flt, chapter=chapter, q=q)
    if after_seq is not None:
      query = query.where(RateImportRow.seq > after_seq)
    rows = list((await self.session.execute(query.order_by(RateImportRow.seq).limit(limit + 1))).scalars().all())
    nxt = rows[limit - 1].seq if len(rows) > limit else None
    return rows[:limit], nxt

  async def chapters(self, org: UUID, import_id: UUID) -> list[dict]:
    await self._import(org, import_id)
    r = RateImportRow
    q = select(r.chapter, func.count(), func.count().filter(r.needs_review.is_(True))).where(r.import_id == import_id, r.organization_id == org).group_by(r.chapter).order_by(func.min(r.seq))
    return [{"chapter": c, "rows": n, "to_review": k} for c, n, k in (await self.session.execute(q)).all()]

  async def samples(self, org: UUID, import_id: UUID) -> list[RateImportRow]:
    await self._import(org, import_id)
    r = RateImportRow
    return list((await self.session.execute(select(r).where(r.import_id == import_id, r.organization_id == org, r.is_sample.is_(True)).order_by(r.seq))).scalars().all())

  def _apply_edit(self, row: RateImportRow, data: dict) -> None:
    content = {"description", "item_no", "chapter", "unit", "basis_qty", "rate", "spec_key"} & set(data)
    if content and row.original is None:
      row.original = {"description": row.description, "item_no": row.item_no, "chapter": row.chapter, "unit_raw": row.unit_raw, "unit": row.unit, "spec_key": row.spec_key,
        "basis_qty": str(row.basis_qty), "rate": None if row.rate is None else str(row.rate), "flags": list(row.flags or [])}
    edited_unit = edited_rate = False
    if "description" in data and data["description"] is not None:
      row.description = data["description"].strip()
    if "item_no" in data:
      row.item_no = (data["item_no"] or "").strip() or None
    if "chapter" in data:
      row.chapter = (data["chapter"] or "").strip() or None
    if "spec_key" in data:
      row.spec_key = (data["spec_key"] or "").strip().lower() or None
    if data.get("unit") is not None:
      ub = mp.parse_unit_basis(data["unit"])
      
      if ub.unit is None:
        raise TraceException(f"'{data['unit']}': {ub.note or 'unit not recognised'}", status_code=422, code="RATE_IMPORT_UNIT")
      row.unit, row.unit_known, row.unit_raw, edited_unit = ub.unit, ub.known, data["unit"].strip()[:60], True
      if data.get("basis_qty") is None and ub.basis_qty != 1:
        row.basis_qty, edited_rate = ub.basis_qty, True  
    if data.get("basis_qty") is not None:
      row.basis_qty, edited_rate = Decimal(data["basis_qty"]), True
    if "rate" in data and data["rate"] is not None:
      row.rate, row.rate_raw, edited_rate = Decimal(data["rate"]), str(data["rate"])[:60], True
    if edited_unit or edited_rate:
      row.unit_rate = il.unit_rate_of(row.rate, row.basis_qty)
      flags = il.derive_flags(row.flags or [], unit=row.unit, unit_known=row.unit_known, rate=row.rate, edited_unit=edited_unit, edited_rate=edited_rate)
      flags = [f for f in flags if f != "BASIS_APPLIED"] + (["BASIS_APPLIED"] if row.basis_qty != 1 else [])
      row.flags = flags
    if content:
      row.edited = True
      row.reviewed = True  
      row.suggestions = []

  async def update_row(self, org: UUID, user_id: UUID, import_id: UUID, row_id: UUID, payload: RowUpdateRequest) -> RateImportRow:
    await self._open(org, import_id)
    row = await self._row(org, import_id, row_id)
    data = payload.model_dump(exclude_unset=True)
    self._apply_edit(row, data)
    
    if payload.clear_mapping:
      row.work_item_code, row.mapping_source = None, None
    elif data.get("work_item_code"):
      row.work_item_code, row.mapping_source = data["work_item_code"], "MANUAL"
    if data.get("reviewed") is not None:
      row.reviewed = data["reviewed"]
    if data.get("skipped") is not None:
      row.skipped = data["skipped"]
    if data.get("sample_verified") is not None:
      if not row.is_sample:
        raise TraceException("Only the spot-check rows are verified.", status_code=422, code="RATE_IMPORT_NOT_SAMPLE")
      row.sample_verified = data["sample_verified"]
    if "note" in data:
      row.note = (data["note"] or "").strip() or None
    row.needs_review = il.needs_review(row.flags or [], reviewed=row.reviewed, skipped=row.skipped)
    await self.session.commit()
    return row

  async def bulk(self, org: UUID, user_id: UUID, import_id: UUID, payload: BulkRowsRequest) -> dict:
    await self._open(org, import_id)
    
    r = RateImportRow
    if payload.row_ids:
      query = select(r).where(r.import_id == import_id, r.organization_id == org, r.id.in_(payload.row_ids))
    else:
      flt = payload.filter or ("unmapped" if payload.action == "accept_suggestions" else None)
      query = self._row_query(org, import_id, flt=flt, chapter=payload.chapter, q=payload.q)
    rows = list((await self.session.execute(query.order_by(r.seq).limit(BULK_LIMIT).with_for_update())).scalars().all())
    changed = skipped = 0
    
    for row in rows:
      did = False
      if payload.action == "confirm":
        if not row.skipped and not row.reviewed:
          row.reviewed, did = True, True
      elif payload.action == "skip":
        if not row.skipped:
          row.skipped, did = True, True
      elif payload.action == "unskip":
        if row.skipped:
          row.skipped, did = False, True
      elif payload.action == "map":
        if not row.skipped and row.work_item_code != payload.work_item_code.strip().upper():
          row.work_item_code, row.mapping_source, did = payload.work_item_code.strip().upper(), "MANUAL", True
      elif payload.action == "clear_mapping":
        if row.work_item_code is not None:
          row.work_item_code, row.mapping_source, did = None, None, True
      elif payload.action == "accept_suggestions":
        if row.skipped or row.work_item_code is not None:
          pass
        else:
          pick = il.confident(row.suggestions or [], threshold=payload.min_score)
          if pick is not None:
            row.work_item_code = pick["code"]
            row.mapping_source = "CSR_REF" if str(pick.get("reason", "")).startswith("same reference") else "SUGGESTED"
            did = True
      if did:
        row.needs_review = il.needs_review(row.flags or [], reviewed=row.reviewed, skipped=row.skipped)
        changed += 1
      else:
        skipped += 1
    await self.session.commit()
    return {"changed": changed, "skipped": skipped}

  async def refresh_suggestions(self, org: UUID, user_id: UUID, import_id: UUID) -> dict:
    """Recompute the suggestions of every unmapped row (after work items were added to the catalog)."""
    await self._open(org, import_id)
    catalog = await self.catalog(org)
    r = RateImportRow
    rows = list((await self.session.execute(select(r).where(r.import_id == import_id, r.organization_id == org, r.work_item_code.is_(None),
      r.skipped.is_(False)).order_by(r.seq).with_for_update())).scalars().all())
    with_s = 0
    
    for row in rows:
      row.suggestions = il.suggest(row.description, row.unit, row.item_no, catalog) if row.unit_known else []
      with_s += 1 if row.suggestions else 0
    await self.session.commit()
    return {"rows_with_suggestions": with_s, "rows_without": len(rows) - with_s, "catalog_size": len(catalog)}

  async def _row_dicts(self, org: UUID, import_id: UUID) -> list[dict]:
    r = RateImportRow
    rows = (await self.session.execute(select(r).where(r.import_id == import_id, r.organization_id == org).order_by(r.seq))).scalars().all()
    return [{"id": x.id, "seq": x.seq, "skipped": x.skipped, "needs_review": x.needs_review, "is_sample": x.is_sample, "sample_verified": x.sample_verified,
      "work_item_code": x.work_item_code, "unit": x.unit, "unit_rate": x.unit_rate, "item_no": x.item_no, "description": x.description,
      "chapter": x.chapter, "page": x.page, "unit_raw": x.unit_raw, "basis_qty": x.basis_qty, "rate": x.rate,
      "spec_key": x.spec_key, "rate_kind": x.rate_kind} for x in rows]

  async def readiness(self, org: UUID, import_id: UUID, include_unmapped: bool = False) -> il.Readiness:
    imp = await self._import(org, import_id)
    return il.readiness(status=imp.status, report=imp.report, rows=await self._row_dicts(org, import_id), include_unmapped=include_unmapped)

  async def publish(self, org: UUID, user_id: UUID, import_id: UUID, payload: PublishRequest) -> dict:
    imp = await self._import(org, import_id, for_update=True)
    rows = await self._row_dicts(org, import_id)
    ready = il.readiness(status=imp.status, report=imp.report, rows=rows, include_unmapped=payload.include_unmapped)
    if not ready.can_publish:
      raise TraceException("The import isn't ready to publish: " + "; ".join(b["message"] for b in ready.blockers), status_code=422, code="RATE_IMPORT_NOT_READY")
    meta = {k: getattr(payload, k) for k in ("edition", "jurisdiction", "province", "city", "effective_from", "effective_to")}
    
    for k, v in meta.items():
      if v is not None:
        setattr(imp, k, v)
    if payload.code:
      imp.book_code = payload.code
    if payload.name:
      imp.book_name = payload.name
    if payload.existing_book_id:
      book = await self.rates.get_book(payload.existing_book_id, org, for_update=True)
      if book is None:
        raise TraceException("Rate book not found.", status_code=404, code="RATE_BOOK_NOT_FOUND")
      if book.organization_id != org:
        raise TraceException("System rate books are read-only.", status_code=403, code="RATE_BOOK_READ_ONLY")
      if book.status != "DRAFT":
        raise TraceException("Only a DRAFT rate book can receive rates. Start a new version of it first.", status_code=409, code="RATE_BOOK_IMMUTABLE")
      existing = {(i.work_item_code, logic.normalise_unit(i.unit)): i for i in await self.rates.all_items(book.id)}
    else:
      code = imp.book_code or mp.book_code(imp.province, imp.city)
      version = await self.rates.max_version(org, code) + 1
      book = RateBook(id=uuid4(), organization_id=org, code=code, name=(imp.book_name or f"{code} {imp.edition or ''}").strip()[:200], description=f"Loaded from {imp.filename}",
        edition=imp.edition, currency=imp.currency, jurisdiction=imp.jurisdiction, province=imp.province, city=imp.city, effective_from=imp.effective_from,
        effective_to=imp.effective_to, status="DRAFT", immutable_version=version, is_system=False, extra={})
      self.session.add(book)
      await self.session.flush()
      
      existing = {}
    book.extra = {**(book.extra or {}), "source": {"import_id": str(imp.id), "filename": imp.filename, "content_hash": imp.content_hash, "layout_profile": imp.layout_profile,
      "checks": (imp.report or {}).get("status")}}
    items, notes = il.publishable_items(rows, include_unmapped=payload.include_unmapped, prefix=book.code[:20])
    spec_notes = il.spec_notes(items)
    
    created = updated = 0
    for it in items:
      key = (it["work_item_code"], logic.normalise_unit(it["unit"]))
      extra = {"import_id": str(imp.id), "row_id": str(it["id"]), "page": it.get("page"), "unit_raw": it.get("unit_raw"),
        "basis_qty": str(it.get("basis_qty")), "printed_rate": None if it.get("rate") is None else str(it["rate"])}
      if it.get("code_spec"):
        extra.update({"base_code": it["base_code"], "spec_key": it["code_spec"]})
      if it.get("rate_kind"):
        extra["rate_kind"] = it["rate_kind"]
      current = existing.get(key)
      
      if current is None:
        obj = RateItem(id=uuid4(), rate_book_id=book.id, organization_id=org, work_item_code=it["work_item_code"], unit=logic.normalise_unit(it["unit"]),
          rate=logic.q2(it["unit_rate"]), description=(it["description"] or "")[:500] or None, trade=(it.get("chapter") or None) and it["chapter"][:80],
          csr_ref=(it.get("item_no") or None) and it["item_no"][:80], is_active=True, extra=extra)
        self.session.add(obj)
        existing[key] = obj
        created += 1
        
      else:
        current.rate = logic.q2(it["unit_rate"])
        current.description = (it["description"] or "")[:500] or current.description
        current.trade = ((it.get("chapter") or None) and it["chapter"][:80]) or current.trade
        current.csr_ref = ((it.get("item_no") or None) and it["item_no"][:80]) or current.csr_ref
        current.extra = {**(current.extra or {}), **extra}
        current.is_active = True
        updated += 1
        
    imp.status, imp.rate_book_id, imp.published_at, imp.published_by_user_id = "PUBLISHED", book.id, _now(), user_id
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.CREATE if not payload.existing_book_id else AuditAction.UPDATE,
      f"Loaded {created} new and {updated} updated rates into {book.code} v{book.immutable_version} from {imp.filename}")
    live = [r for r in rows if not r["skipped"]]
    left_out = len(live) - len(items)
    return {"rate_book_id": book.id, "created": created, "updated": updated, "left_out": left_out, "unit_changes": notes, "spec_notes": spec_notes}
