from __future__ import annotations
from datetime import datetime, timezone
from app.modules.drawings_boq import boq_logic as logic
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.pricing.rate_repository import RateRepository
from app.modules.drawings_boq.repository import LabourRateRepository
from app.core.exceptions import TraceException
from app.modules.audit.service import AuditLogService
from app.modules.drawings_boq.models import RateAnalysis, ProjectRateOverride, RateAnalysisComponent, RateBook, RateBookEscalation, RateItem
from app.modules.drawings_boq.pricing.schemas import (AnalysisComponentInput, AnalysisCreateRequest, AnalysisUpdateRequest, EscalationCreateRequest, OverrideCreateRequest,
  RateBookCreateRequest, RateBookUpdateRequest, RateItemInput, RateItemUpdateRequest,
)
import csv
import io
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.drawings_boq.pricing import pricing_logic as pl
from app.modules.drawings_boq.models import MaterialLibrary
from sqlalchemy import select, delete
from app.modules.projects.models import Project

MAX_IMPORT_ROWS = 5000

def _now():
  return datetime.now(timezone.utc)

def _unit(value: str) -> str:
  return logic.normalise_unit(value)

class RateBookService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = RateRepository(session)
    self.audit = AuditLogService(session)
    self.labour = LabourRateRepository(session)

  async def _book(self, org: UUID, book_id: UUID, *, for_update: bool = False) -> RateBook:
    book = await self.repo.get_book(book_id, org, for_update=for_update)
    if book is None:
      raise TraceException("Rate book not found.", status_code=404, code="RATE_BOOK_NOT_FOUND")
    return book

  @staticmethod
  def _own(book: RateBook, org: UUID) -> None:
    if book.organization_id != org:
      raise TraceException("System rate books are read-only. Copy the book into your organisation to change rates.",
        status_code=403, code="RATE_BOOK_READ_ONLY")

  @staticmethod
  def _draft(book: RateBook) -> None:
    if book.status != "DRAFT":
      raise TraceException("Only a DRAFT rate book can be edited. Start a new version instead.",
        status_code=409, code="RATE_BOOK_IMMUTABLE")

  async def _editable_book(self, org: UUID, book_id: UUID) -> RateBook:
    book = await self._book(org, book_id, for_update=True)
    self._own(book, org)
    self._draft(book)
    return book

  async def _with_counts(self, books: list[RateBook]) -> list[RateBook]:
    counts = await self.repo.book_counts([b.id for b in books])
    for b in books:
      for k, v in counts[b.id].items():
        setattr(b, k, v)
    return books

  async def list_books(self, org: UUID, *, status: str | None, owner: str, after: UUID | None, limit: int):
    rows = await self.repo.list_books(org, status=status, owner=owner, after=after, limit=limit)
    nxt = rows[limit - 1].id if len(rows) > limit else None
    return await self._with_counts(rows[:limit]), nxt

  async def get_book(self, org: UUID, book_id: UUID) -> RateBook:
    return (await self._with_counts([await self._book(org, book_id)]))[0]

  async def _clone_children(self, org: UUID, source: RateBook, target: RateBook) -> None:
    id_map: dict[UUID, UUID] = {}
    items = await self.repo.all_items(source.id)
    
    for it in items:
      new = RateItem(id=uuid4(), rate_book_id=target.id, organization_id=org, work_item_code=it.work_item_code,
        unit=it.unit, rate=it.rate, description=it.description, trade=it.trade, specification=it.specification,
        csr_ref=it.csr_ref, is_active=it.is_active, extra=dict(it.extra or {}))
      id_map[it.id] = new.id
      self.session.add(new)
      
    for e in await self.repo.list_escalations(source.id):
      self.session.add(RateBookEscalation(id=uuid4(), rate_book_id=target.id, organization_id=org,
        trade_scope=e.trade_scope, effective_from=e.effective_from, factor=e.factor, note=e.note))
    await self.session.flush()
    analysis_map: dict[UUID, UUID] = {}
    
    for a in await self.repo.list_analyses(source.id):
      new_a = RateAnalysis(id=uuid4(), rate_book_id=target.id, organization_id=org, code=a.code,
        work_item_code=a.work_item_code, description=a.description, unit=a.unit, basis_quantity=a.basis_quantity,
        overhead_pct=a.overhead_pct, profit_pct=a.profit_pct, computed_rate=a.computed_rate,
        computed_at=a.computed_at, is_active=a.is_active)
      analysis_map[a.id] = new_a.id
      self.session.add(new_a)
    await self.session.flush()
    
    for a in await self.repo.list_analyses(source.id):
      for c in a.components:
        self.session.add(RateAnalysisComponent(id=uuid4(), analysis_id=analysis_map[a.id], organization_id=org,
          sequence=c.sequence, component_type=c.component_type, description=c.description,
          work_item_code=c.work_item_code, rate_source=c.rate_source,
          ref_rate_item_id=id_map.get(c.ref_rate_item_id) if c.ref_rate_item_id else None,
          unit=c.unit, coefficient=c.coefficient, unit_rate=c.unit_rate))
    await self.session.flush()
    
    for it in items:
      if it.analysis_id and it.analysis_id in analysis_map:
        new_item = await self.repo.item_by_key(target.id, it.work_item_code, it.unit)
        new_item.analysis_id = analysis_map[it.analysis_id]
    await self.session.flush()

  async def create_book(self, org: UUID, user_id: UUID, payload: RateBookCreateRequest) -> RateBook:
    source = await self._book(org, payload.copy_from_id) if payload.copy_from_id else None
    version = await self.repo.max_version(org, payload.code) + 1
    book = RateBook(
      id=uuid4(), organization_id=org, code=payload.code, name=payload.name.strip(), description=payload.description,
      edition=payload.edition, currency=payload.currency.upper(), jurisdiction=payload.jurisdiction,
      province=payload.province, city=payload.city, effective_from=payload.effective_from,
      effective_to=payload.effective_to, status="DRAFT", immutable_version=version, is_system=False,
      parent_rate_book_id=source.id if source else None, extra={})
    self.repo.add(book)
    await self.session.flush()
    
    if source is not None:
      await self._clone_children(org, source, book)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.CREATE,
      f"Created rate book {book.code} v{book.immutable_version}" + (f" from {source.code} v{source.immutable_version}" if source else ""))
    return (await self._with_counts([book]))[0]

  async def update_book(self, org: UUID, user_id: UUID, book_id: UUID, payload: RateBookUpdateRequest) -> RateBook:
    book = await self._editable_book(org, book_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in list(data.items()):
      if key == "name" and value is not None:
        data[key] = value.strip()
      if key == "currency" and value is not None:
        data[key] = value.upper()
        
    start = data.get("effective_from", book.effective_from)
    end = data.get("effective_to", book.effective_to)
    if start and end and end < start:
      raise TraceException("effective_to is before effective_from.", status_code=422, code="INVALID_EFFECTIVE_RANGE")
    for key, value in data.items():
      setattr(book, key, value)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.UPDATE,
      f"Edited draft rate book {book.code} v{book.immutable_version}")
    return (await self._with_counts([book]))[0]

  async def delete_book(self, org: UUID, user_id: UUID, book_id: UUID) -> None:
    book = await self._editable_book(org, book_id)
    if await self.repo.referenced_book_ids(org, book.id):
      raise TraceException("This rate book is referenced by BOQ lines.", status_code=409, code="RATE_BOOK_IN_USE")
    code, version = book.code, book.immutable_version
    await self.session.execute(delete(RateAnalysisComponent).where(RateAnalysisComponent.analysis_id.in_(
      select(RateAnalysis.id).where(RateAnalysis.rate_book_id == book.id))))
    await self.repo.delete(book)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book_id, AuditAction.DELETE,
      f"Deleted draft rate book {code} v{version}")

  async def publish_book(self, org: UUID, user_id: UUID, book_id: UUID) -> RateBook:
    book = await self._editable_book(org, book_id)
    items = await self.repo.all_items(book.id)
    if not any(i.is_active for i in items):
      raise TraceException("A rate book needs at least one active rate before it can be published.",
        status_code=422, code="RATE_BOOK_EMPTY")
      
    analyses = await self.repo.list_analyses(book.id)
    previous = await self.repo.active_book(org, book.code)
    if previous is not None and previous.id != book.id:
      await self.repo.supersede(previous.id)
      book.supersedes_rate_book_id = previous.id
    header = {"code": book.code, "edition": book.edition, "immutable_version": book.immutable_version,
      "currency": book.currency, "effective_from": book.effective_from, "effective_to": book.effective_to}
    
    book.content_hash = pl.rate_book_hash(header, items, analyses)
    book.published_at, book.published_by_user_id, book.status = _now(), user_id, "ACTIVE"
    await self.session.flush()
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.APPROVE,
      f"Published rate book {book.code} v{book.immutable_version} (hash {book.content_hash[:12]})")
    return (await self._with_counts([book]))[0]

  async def new_version(self, org: UUID, user_id: UUID, book_id: UUID) -> RateBook:
    source = await self._book(org, book_id)
    self._own(source, org)
    if source.status == "DRAFT":
      raise TraceException("This rate book is already a draft.", status_code=409, code="RATE_BOOK_IS_DRAFT")
    version = await self.repo.max_version(org, source.code) + 1
    book = RateBook(
      id=uuid4(), organization_id=org, code=source.code, name=source.name, description=source.description,
      edition=source.edition, currency=source.currency, jurisdiction=source.jurisdiction, province=source.province,
      city=source.city, effective_from=source.effective_from, effective_to=source.effective_to, status="DRAFT",
      immutable_version=version, is_system=False, parent_rate_book_id=source.id, extra={})
    self.repo.add(book)
    
    await self.session.flush()
    await self._clone_children(org, source, book)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.CREATE,
      f"Started rate book {book.code} v{book.immutable_version} from v{source.immutable_version}")
    return (await self._with_counts([book]))[0]

  async def archive_book(self, org: UUID, user_id: UUID, book_id: UUID) -> RateBook:
    book = await self._book(org, book_id, for_update=True)
    self._own(book, org)
    if book.status not in ("ACTIVE", "SUPERSEDED"):
      raise TraceException("Only a published rate book can be archived.", status_code=409, code="INVALID_RATE_BOOK_STATE")
    book.status = "ARCHIVED"
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.STATUS_CHANGE,
      f"Archived rate book {book.code} v{book.immutable_version}")
    return (await self._with_counts([book]))[0]

  async def list_items(self, org: UUID, book_id: UUID, *, q, trade, only_active, after, limit):
    await self._book(org, book_id)
    rows = await self.repo.list_items(book_id, q=q, trade=trade, only_active=only_active, after=after, limit=limit)
    return rows[:limit], (rows[limit - 1].id if len(rows) > limit else None)

  def _new_item(self, book: RateBook, p: RateItemInput) -> RateItem:
    return RateItem(id=uuid4(), rate_book_id=book.id, organization_id=book.organization_id,
      work_item_code=p.work_item_code, unit=_unit(p.unit), rate=logic.q2(p.rate), description=p.description,
      trade=p.trade, specification=p.specification, csr_ref=p.csr_ref, is_active=True, extra={})

  async def add_item(self, org: UUID, user_id: UUID, book_id: UUID, payload: RateItemInput) -> RateItem:
    book = await self._editable_book(org, book_id)
    if await self.repo.item_by_key(book.id, payload.work_item_code, _unit(payload.unit)) is not None:
      raise TraceException("This work item already has a rate in this unit.", status_code=409, code="RATE_ITEM_EXISTS")
    item = self._new_item(book, payload)
    self.repo.add(item)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.UPDATE,
      f"Added rate {item.work_item_code} / {item.unit} = {item.rate} to {book.code} v{book.immutable_version}")
    return item

  async def bulk_upsert(self, org: UUID, user_id: UUID, book_id: UUID, rows: list[RateItemInput]) -> dict:
    book = await self._editable_book(org, book_id)
    created = updated = 0
    seen: set[tuple] = set()
    for p in rows:
      key = (p.work_item_code, _unit(p.unit))
      
      if key in seen:
        raise TraceException(f"{p.work_item_code} / {key[1]} appears twice in the upload.",
          status_code=422, code="RATE_IMPORT_DUPLICATE")
      seen.add(key)
      existing = await self.repo.item_by_key(book.id, *key)
      if existing is None:
        self.repo.add(self._new_item(book, p))
        created += 1
        
      else:
        existing.rate = logic.q2(p.rate)
        for field in ("description", "trade", "specification", "csr_ref"):
          value = getattr(p, field)
          if value is not None:
            setattr(existing, field, value)
        existing.is_active = True
        updated += 1
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.UPDATE,
      f"Imported rates into {book.code} v{book.immutable_version}: {created} new, {updated} updated")
    return {"created": created, "updated": updated, "total": created + updated}

  @staticmethod
  def parse_csv(content: bytes) -> list[RateItemInput]:
    try:
      text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
      raise TraceException("The file must be UTF-8 CSV.", status_code=422, code="RATE_IMPORT_INVALID")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
      raise TraceException("The CSV is empty.", status_code=422, code="RATE_IMPORT_INVALID")
    headers = {h.strip().lower(): h for h in reader.fieldnames if h}
    missing = [h for h in ("work_item_code", "unit", "rate") if h not in headers]
    
    if missing:
      raise TraceException(f"Missing column(s): {', '.join(missing)}.", status_code=422, code="RATE_IMPORT_INVALID")
    out: list[RateItemInput] = []
    errors: list[str] = []
    for n, raw in enumerate(reader, start=2):
      if n - 1 > MAX_IMPORT_ROWS:
        raise TraceException(f"At most {MAX_IMPORT_ROWS} rows can be imported at once.",
          status_code=422, code="RATE_IMPORT_TOO_LARGE")
      row = {k: (raw.get(headers[k]) or "").strip() for k in headers}
      if not any(row.values()):
        continue
    
      try:
        rate = Decimal(row["rate"].replace(",", ""))
        out.append(RateItemInput(work_item_code=row["work_item_code"], unit=row["unit"], rate=rate,
          description=row.get("description") or None, trade=row.get("trade") or None,
          specification=row.get("specification") or None, csr_ref=row.get("csr_ref") or None))
      except (InvalidOperation, ValueError) as exc:
        errors.append(f"row {n}: {str(exc).splitlines()[0][:80]}")
    if errors:
      shown = "; ".join(errors[:5]) + (f" (+{len(errors) - 5} more)" if len(errors) > 5 else "")
      raise TraceException(f"The CSV has invalid rows: {shown}", status_code=422, code="RATE_IMPORT_INVALID")
    if not out:
      raise TraceException("The CSV has no rows.", status_code=422, code="RATE_IMPORT_INVALID")
    return out

  async def import_csv(self, org: UUID, user_id: UUID, book_id: UUID, content: bytes) -> dict:
    return await self.bulk_upsert(org, user_id, book_id, self.parse_csv(content))

  async def update_item(self, org: UUID, user_id: UUID, item_id: UUID, payload: RateItemUpdateRequest) -> RateItem:
    item = await self.repo.get_item(item_id, org, for_update=True)
    if item is None:
      raise TraceException("Rate not found.", status_code=404, code="RATE_ITEM_NOT_FOUND")
    book = await self._editable_book(org, item.rate_book_id)
    data = payload.model_dump(exclude_unset=True)
    if "rate" in data and data["rate"] is not None:
      item.rate = logic.q2(data.pop("rate"))
    else:
      data.pop("rate", None)
    for k, v in data.items():
      if k == "is_active" and v is None:
        continue
      setattr(item, k, v)
      
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.UPDATE,
      f"Edited rate {item.work_item_code} / {item.unit} in {book.code} v{book.immutable_version}")
    return item

  async def delete_item(self, org: UUID, user_id: UUID, item_id: UUID) -> None:
    item = await self.repo.get_item(item_id, org, for_update=True)
    if item is None:
      raise TraceException("Rate not found.", status_code=404, code="RATE_ITEM_NOT_FOUND")
    book = await self._editable_book(org, item.rate_book_id)
    used_by = (await self.session.execute(select(RateAnalysisComponent.id).where(RateAnalysisComponent.ref_rate_item_id == item.id).limit(1))).first()
    if used_by is not None:
      raise TraceException("This rate is used as an ingredient in a rate analysis. Remove it from the analysis first.",
        status_code=409, code="RATE_ITEM_IN_USE")
    label = f"{item.work_item_code} / {item.unit}"
    await self.repo.delete(item)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.DELETE,
      f"Removed rate {label} from {book.code} v{book.immutable_version}")

  async def list_escalations(self, org: UUID, book_id: UUID):
    await self._book(org, book_id)
    return await self.repo.list_escalations(book_id)

  async def add_escalation(self, org: UUID, user_id: UUID, book_id: UUID, payload: EscalationCreateRequest):
    book = await self._book(org, book_id, for_update=True)
    self._own(book, org)
    if book.status not in ("DRAFT", "ACTIVE"):
      raise TraceException("Escalations can only be added to a DRAFT or ACTIVE rate book.",
        status_code=409, code="RATE_BOOK_IMMUTABLE")
      
    if await self.repo.escalation_by_key(book.id, payload.trade_scope, payload.effective_from) is not None:
      raise TraceException("An escalation for this trade and date already exists.", status_code=409, code="ESCALATION_EXISTS")
    esc = RateBookEscalation(id=uuid4(), rate_book_id=book.id, organization_id=org, trade_scope=payload.trade_scope,
      effective_from=payload.effective_from, factor=payload.factor, note=payload.note)
    self.repo.add(esc)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.UPDATE,
      f"Added escalation x{esc.factor} ({esc.trade_scope}) from {esc.effective_from} to {book.code}")
    return esc

  async def delete_escalation(self, org: UUID, user_id: UUID, esc_id: UUID) -> None:
    esc = await self.repo.get_escalation(esc_id, org)
    if esc is None:
      raise TraceException("Escalation not found.", status_code=404, code="ESCALATION_NOT_FOUND")
    book = await self._book(org, esc.rate_book_id, for_update=True)
    self._own(book, org)
    if book.status not in ("DRAFT", "ACTIVE"):
      raise TraceException("Escalations can only change on a DRAFT or ACTIVE rate book.",
        status_code=409, code="RATE_BOOK_IMMUTABLE")
    await self.repo.delete(esc)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.DELETE,
      f"Removed escalation ({esc.trade_scope}) from {esc.effective_from} on {book.code}")

  async def list_analyses(self, org: UUID, book_id: UUID):
    await self._book(org, book_id)
    return await self.repo.list_analyses(book_id)

  async def get_analysis(self, org: UUID, analysis_id: UUID) -> RateAnalysis:
    a = await self.repo.get_analysis(analysis_id, org)
    if a is None:
      raise TraceException("Rate analysis not found.", status_code=404, code="RATE_ANALYSIS_NOT_FOUND")
    return a

  async def _validate_components(self, book: RateBook, comps: list[AnalysisComponentInput]) -> None:
    for c in comps:
      if c.rate_source in ("LABOUR_RATE", "MATERIAL_LIBRARY") and book.organization_id is None:
        raise TraceException("System rate analyses can only use DIRECT and RATE_ITEM components.",
          status_code=422, code="ANALYSIS_COMPONENT_INVALID")
      if c.rate_source == "RATE_ITEM":
        if await self.repo.item_by_id_in_book(c.ref_rate_item_id, book.id) is None:
          raise TraceException("A RATE_ITEM component must reference a rate in the same rate book.",
            status_code=422, code="ANALYSIS_REF_INVALID")

  def _components(self, analysis: RateAnalysis, comps: list[AnalysisComponentInput], org: UUID | None) -> list[RateAnalysisComponent]:
    return [RateAnalysisComponent(
      id=uuid4(), analysis_id=analysis.id, organization_id=org, sequence=n, component_type=c.component_type,
      description=c.description.strip(), work_item_code=c.work_item_code, rate_source=c.rate_source,
      ref_rate_item_id=c.ref_rate_item_id, unit=_unit(c.unit), coefficient=c.coefficient,
      unit_rate=logic.q2(c.unit_rate) if c.unit_rate is not None else None) for n, c in enumerate(comps)]

  async def create_analysis(self, org: UUID, user_id: UUID, book_id: UUID, payload: AnalysisCreateRequest) -> RateAnalysis:
    book = await self._editable_book(org, book_id)
    if await self.repo.analysis_by_code(book.id, payload.code) is not None:
      raise TraceException("An analysis with this code already exists in the rate book.",
        status_code=409, code="RATE_ANALYSIS_EXISTS")
      
    await self._validate_components(book, payload.components)
    a = RateAnalysis(id=uuid4(), rate_book_id=book.id, organization_id=book.organization_id, code=payload.code,
      work_item_code=payload.work_item_code, description=payload.description.strip(), unit=_unit(payload.unit),
      basis_quantity=payload.basis_quantity, overhead_pct=payload.overhead_pct, profit_pct=payload.profit_pct,
      is_active=True)
    self.repo.add(a)
    await self.session.flush()
    for comp in self._components(a, payload.components, book.organization_id):
      self.session.add(comp)
    await self.session.commit()
    await self.session.refresh(a, ["components"])
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.UPDATE,
      f"Added rate analysis {a.code} to {book.code} v{book.immutable_version}")
    return a

  async def update_analysis(self, org: UUID, user_id: UUID, analysis_id: UUID, payload: AnalysisUpdateRequest) -> RateAnalysis:
    a = await self.repo.get_analysis(analysis_id, org, for_update=True)
    if a is None:
      raise TraceException("Rate analysis not found.", status_code=404, code="RATE_ANALYSIS_NOT_FOUND")
    book = await self._editable_book(org, a.rate_book_id)
    data = payload.model_dump(exclude_unset=True, exclude={"components"})
    for k, v in data.items():
      if v is None:
        continue
      setattr(a, k, _unit(v) if k == "unit" else v)
      
    if payload.components is not None:
      await self._validate_components(book, payload.components)
      await self.repo.clear_components(a.id)
      for comp in self._components(a, payload.components, book.organization_id):
        self.session.add(comp)
    a.computed_rate, a.computed_at = None, None
    await self.session.commit()
    await self.session.refresh(a, ["components"])
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.UPDATE,
      f"Edited rate analysis {a.code} in {book.code} v{book.immutable_version}")
    return a

  async def delete_analysis(self, org: UUID, user_id: UUID, analysis_id: UUID) -> None:
    a = await self.repo.get_analysis(analysis_id, org, for_update=True)
    if a is None:
      raise TraceException("Rate analysis not found.", status_code=404, code="RATE_ANALYSIS_NOT_FOUND")
    book = await self._editable_book(org, a.rate_book_id)
    code = a.code
    await self.repo.delete(a)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.DELETE,
      f"Removed rate analysis {code} from {book.code} v{book.immutable_version}")

  async def _component_rate(self, org: UUID, book: RateBook, c: RateAnalysisComponent, labour_rows: list) -> Decimal:
    rate: Decimal | None = None
    source_unit = c.unit
    if c.rate_source == "DIRECT":
      rate = c.unit_rate
    elif c.rate_source == "RATE_ITEM":
      ref = await self.repo.item_by_id_in_book(c.ref_rate_item_id, book.id) if c.ref_rate_item_id else None
      if ref is not None:
        rate, source_unit = ref.rate, ref.unit
        
    elif c.rate_source == "LABOUR_RATE":
      key = (c.description or "").strip().lower()
      match = next((r for r in labour_rows if (c.work_item_code and r.work_item_code == c.work_item_code)
        or (r.trade or "").strip().lower() == key), None)
      if match is not None:
        rate, source_unit = match.rate, match.unit
    elif c.rate_source == "MATERIAL_LIBRARY":
        
      stmt = select(MaterialLibrary).where(MaterialLibrary.organization_id == org, MaterialLibrary.default_rate.is_not(None))
      rows = list((await self.session.execute(stmt)).scalars().all())
      key = (c.description or "").strip().lower()
      match = next((r for r in rows if (c.work_item_code and r.work_item_code == c.work_item_code)
        or (r.raw_text or "").strip().lower() == key), None)
      if match is not None:
        rate, source_unit = match.default_rate, match.default_unit or c.unit
        
    if rate is None:
      raise TraceException(f"Component '{c.description}' has no rate to use.", status_code=422,
        code="ANALYSIS_COMPONENT_UNRESOLVED")
    converted = pl.convert(rate, source_unit, c.unit)
    if converted is None:
      raise TraceException(f"Component '{c.description}': rate unit {source_unit} cannot be converted to {c.unit}.",
        status_code=422, code="ANALYSIS_COMPONENT_UNIT_MISMATCH")
    return converted

  async def breakdown(self, org: UUID, analysis: RateAnalysis) -> dict:
    book = await self._book(org, analysis.rate_book_id)
    labour_rows = await self.labour.list_by_org(org) if book.organization_id is not None else []
    lines = []
    
    for c in sorted(analysis.components, key=lambda x: x.sequence):
      rate = await self._component_rate(org, book, c, labour_rows)
      lines.append(pl.AnalysisLine(c.sequence, c.component_type, c.description, c.unit, c.coefficient, rate))
    if not lines:
      raise TraceException("The analysis has no components.", status_code=422, code="ANALYSIS_EMPTY")
    out = pl.analysis_totals(lines, analysis.basis_quantity, analysis.overhead_pct, analysis.profit_pct)
    out["unit"] = analysis.unit
    out["analysis_id"] = analysis.id
    return out

  async def compute_analysis(self, org: UUID, user_id: UUID, analysis_id: UUID) -> RateAnalysis:
    a = await self.repo.get_analysis(analysis_id, org, for_update=True)
    
    if a is None:
      raise TraceException("Rate analysis not found.", status_code=404, code="RATE_ANALYSIS_NOT_FOUND")
    book = await self._editable_book(org, a.rate_book_id)
    out = await self.breakdown(org, a)
    a.computed_rate, a.computed_at = out["rate_value"], _now()
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.UPDATE,
      f"Computed rate analysis {a.code}: {a.computed_rate} per {a.unit}")
    return a

  async def apply_analysis(self, org: UUID, user_id: UUID, analysis_id: UUID) -> RateItem:
    a = await self.repo.get_analysis(analysis_id, org, for_update=True)
    
    if a is None:
      raise TraceException("Rate analysis not found.", status_code=404, code="RATE_ANALYSIS_NOT_FOUND")
    book = await self._editable_book(org, a.rate_book_id)
    out = await self.breakdown(org, a)
    a.computed_rate, a.computed_at = out["rate_value"], _now()
    item = await self.repo.item_by_key(book.id, a.work_item_code, a.unit)
    
    if item is None:
      item = RateItem(id=uuid4(), rate_book_id=book.id, organization_id=book.organization_id,
        work_item_code=a.work_item_code, unit=a.unit, rate=a.computed_rate, description=a.description,
        is_active=True, extra={})
      self.repo.add(item)
      
    else:
      item.rate = a.computed_rate
      item.description = item.description or a.description
    await self.session.flush()
    item.analysis_id = a.id
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_BOOK, book.id, AuditAction.UPDATE,
      f"Applied analysis {a.code}: {item.work_item_code} / {item.unit} = {item.rate}")
    return item

  async def create_override(self, org: UUID, user_id: UUID, project_id: UUID, payload: OverrideCreateRequest) -> ProjectRateOverride:
    await self._project(org, project_id)
    unit = _unit(payload.unit)
    if await self.repo.active_override(org, project_id, payload.work_item_code, unit) is not None:
      raise TraceException("This work item already has an active override in this unit. Revoke it first.",
        status_code=409, code="RATE_OVERRIDE_EXISTS")
      
    o = ProjectRateOverride(id=uuid4(), organization_id=org, project_id=project_id,
      work_item_code=payload.work_item_code, unit=unit, rate=logic.q2(payload.rate), reason=payload.reason,
      effective_from=payload.effective_from, effective_to=payload.effective_to, created_by_user_id=user_id)
    self.repo.add(o)
    await self.session.commit()
    await self.session.refresh(o)
    await self.audit.log(org, user_id, AuditEntityType.RATE_OVERRIDE, o.id, AuditAction.CREATE,
      f"Rate override {o.work_item_code} / {o.unit} = {o.rate}: {o.reason[:200]}")
    return o

  async def _project(self, org: UUID, project_id: UUID) -> None:
    found = (await self.session.execute(
      select(Project.id).where(Project.id == project_id, Project.organization_id == org))).scalar_one_or_none()
    if found is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

  async def list_overrides(self, org: UUID, project_id: UUID, *, include_revoked: bool, after: UUID | None, limit: int):
    await self._project(org, project_id)
    rows = await self.repo.list_overrides(org, project_id, include_revoked=include_revoked, after=after, limit=limit)
    return rows[:limit], (rows[limit - 1].id if len(rows) > limit else None)

  async def revoke_override(self, org: UUID, user_id: UUID, override_id: UUID, reason: str) -> ProjectRateOverride:
    o = await self.repo.get_override(override_id, org, for_update=True)
    
    if o is None:
      raise TraceException("Rate override not found.", status_code=404, code="RATE_OVERRIDE_NOT_FOUND")
    if o.revoked_at is not None:
      raise TraceException("This override is already revoked.", status_code=409, code="RATE_OVERRIDE_REVOKED")
    if not (reason or "").strip():
      raise TraceException("Revoking an override needs a reason.", status_code=422, code="OVERRIDE_REQUIRES_REASON")
    o.revoked_at, o.revoked_by_user_id, o.revoke_reason = _now(), user_id, reason.strip()
    
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.RATE_OVERRIDE, o.id, AuditAction.UPDATE,
      f"Revoked rate override {o.work_item_code} / {o.unit}: {o.revoke_reason[:200]}")
    return o