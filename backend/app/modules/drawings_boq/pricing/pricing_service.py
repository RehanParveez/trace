from __future__ import annotations
from datetime import date, datetime, timezone
from app.modules.drawings_boq.models import BOQItem, BOQItemStatus
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.repository import BOQItemRepository, BOQVersionRepository
from app.modules.drawings_boq.boq_repository import BOQEngineRepository
from app.modules.drawings_boq.boq_service import BOQEngineService, assert_mutable
from app.modules.audit.service import AuditLogService
from app.core.exceptions import TraceException
from app.modules.drawings_boq.pricing.schemas import PriceVersionRequest
from app.modules.drawings_boq.pricing.resolver import PriceResolver, apply_resolution, clear_rate
from decimal import Decimal
from uuid import UUID
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.drawings_boq import boq_logic as logic
from app.modules.drawings_boq.pricing import pricing_logic as pl

def _now():
  return datetime.now(timezone.utc)

def texts_for(item: BOQItem) -> list[str | None]:
  return [item.description, item.material_name]

class PricingService:
    
  def __init__(self, session: AsyncSession):
    self.session = session
    self.versions = BOQVersionRepository(session)
    self.items = BOQItemRepository(session)
    self.engine_repo = BOQEngineRepository(session)
    self.engine = BOQEngineService(session)
    self.audit = AuditLogService(session)

  async def _version(self, org: UUID, version_id: UUID, *, lock: bool):
    version = await (self.engine_repo.version_for_update(version_id, org) if lock
      else self.versions.get_by_id_and_org(version_id, org))
    if version is None:
      raise TraceException("BOQ version not found.", status_code=404, code="BOQ_VERSION_NOT_FOUND")
    return version

  @staticmethod
  def _protected(item: BOQItem, overwrite_manual: bool) -> str | None:
    if item.status == BOQItemStatus.APPROVED:
      return "other"
    if item.source_kind == "ESTIMATE":
      return "other"
    source = item.rate_source.value if item.rate_source is not None else None
    if item.unit_rate is not None and not overwrite_manual:
      if source == "MANUAL" or source is None:
        return "manual"
    return None

  async def price_version(self, org: UUID, version_id: UUID, user_id: UUID, req: PriceVersionRequest) -> dict:
    version = await self._version(org, version_id, lock=True)
    if version.origin == "ENGINE" and version.lifecycle in ("CALCULATING",):
      raise TraceException("The BOQ is being calculated. Try again when it finishes.", status_code=409, code="BOQ_IMMUTABLE")
    assert_mutable(version)
    if version.status.value == "SUPERSEDED":
      raise TraceException("Cannot price a superseded BOQ version.", status_code=409, code="BOQ_VERSION_SUPERSEDED")

    items = await self.items.list_by_version(version.id, org)
    wanted = set(req.item_ids) if req.item_ids else None
    if wanted and not wanted <= {i.id for i in items}:
      raise TraceException("One or more items are not part of this BOQ version.", status_code=404, code="BOQ_ITEM_NOT_FOUND")
    as_of = req.as_of or date.today()
    resolver = await PriceResolver.load(self.session, org, version.project_id, as_of=as_of,
      codes={i.work_item_code for i in items if i.work_item_code}, rate_book_ids=req.rate_book_ids)

    counts = {"priced": 0, "changed": 0, "unpriced": 0, "unit_mismatch": 0, "skipped_manual": 0, "skipped_other": 0}
    mismatched: list[BOQItem] = []
    for item in items:
      if wanted is not None and item.id not in wanted:
        continue
      why = self._protected(item, req.overwrite_manual)
      if why == "manual":
        counts["skipped_manual"] += 1
        continue
      if why == "other":
        counts["skipped_other"] += 1
        continue
    
      res = resolver.resolve(item.work_item_code, texts_for(item), item.unit)
      if res.found:
        if apply_resolution(item, res):
          item.version += 1
          counts["changed"] += 1
          
      else:
        prior = item.rate_source.value if item.rate_source is not None else None
        if prior in pl.AUTO_SOURCES or (req.overwrite_manual and prior == "MANUAL"):
          if clear_rate(item):
            item.version += 1
            counts["changed"] += 1
        if res.unit_mismatch:
          mismatched.append(item)
          counts["unit_mismatch"] += 1
    await self.session.flush()

    for item in items:
      if item.unit_rate is not None:
        counts["priced"] += 1
      else:
        counts["unpriced"] += 1
    by_source: dict[str, int] = {}
    total = Decimal("0")
    for item in items:
      key = item.rate_source.value if item.rate_source is not None else ("UNSOURCED" if item.unit_rate is not None else "UNPRICED")
      by_source[key] = by_source.get(key, 0) + 1
      if item.unit_rate is not None:
        total += logic.q2(Decimal(item.quantity) * Decimal(item.unit_rate))

    version.pricing_meta = {"as_of": as_of.isoformat(), "rate_books": resolver.stack_summary(),
      "rate_book_ids": [str(b.id) for b in resolver.books], "overwrite_manual": req.overwrite_manual, "counts": counts}
    version.priced_at = _now()
    open_issues = 0
    if version.origin == "ENGINE":
      specs = []
      spec = self.engine._pricing_spec(items)
      if spec is not None:
        specs.append(spec)
        
      for it in mismatched:
        specs.append(logic.IssueSpec(
          code="RATE_UNIT_MISMATCH", severity="error", blocks="APPROVAL", dedupe_key=f"RATE_UNIT:{it.item_key or it.id}",
          message=f"The rate for '{it.material_name}' cannot be converted to {it.unit}.",
          suggested_fix="Set a rate in the item's unit, or add a rate for this work item in a compatible unit.",
          boq_item_id=it.id))
      await self.engine.sync_issues(org, version, version.calculation_run_id, specs, prefixes=("UNPRICED", "RATE_UNIT"))
      open_issues = len(await self.engine_repo.issues_for_version(version.id, org, "OPEN"))
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.BOQ_VERSION, version.id, AuditAction.UPDATE,
      f"Priced BOQ: {counts['changed']} line(s) changed, {counts['unpriced']} unpriced "
      f"({', '.join(b['code'] for b in resolver.stack_summary()) or 'no rate books'})")
    return {"boq_version_id": version.id, "as_of": as_of, "rate_books": resolver.stack_summary(), **counts,
      "by_source": by_source, "total": logic.fmt(total, 2), "open_issues": open_issues}

  async def summary(self, org: UUID, version_id: UUID) -> dict:
    version = await self._version(org, version_id, lock=False)
    items = await self.items.list_by_version(version.id, org)
    by_source: dict[str, int] = {}
    total = Decimal("0")
    
    for item in items:
      key = item.rate_source.value if item.rate_source is not None else ("UNSOURCED" if item.unit_rate is not None else "UNPRICED")
      by_source[key] = by_source.get(key, 0) + 1
      if item.unit_rate is not None:
        total += logic.q2(Decimal(item.quantity) * Decimal(item.unit_rate))
    return {"boq_version_id": version.id, "priced_at": version.priced_at, "pricing_meta": version.pricing_meta or {},
      "item_count": len(items), "unpriced_count": sum(1 for i in items if i.unit_rate is None),
      "by_source": by_source, "total": logic.fmt(total, 2)}

  async def explain_item(self, org: UUID, item_id: UUID, as_of: date | None = None) -> dict:
    item = await self.items.get_by_id_and_org_for_update(item_id, org)
    if item is None:
      raise TraceException("BOQ item not found.", status_code=404, code="BOQ_ITEM_NOT_FOUND")
  
    version = await self.versions.get_by_id_and_org(item.boq_version_id, org)
    meta = (version.pricing_meta or {}) if version else {}
    on = as_of or (date.fromisoformat(meta["as_of"]) if meta.get("as_of") else date.today())
    ids = [UUID(i) for i in meta.get("rate_book_ids", [])] or None
    resolver = await PriceResolver.load(self.session, org, version.project_id if version else None, as_of=on,
      codes={item.work_item_code} if item.work_item_code else set(), rate_book_ids=ids)
    
    res = resolver.resolve(item.work_item_code, texts_for(item), item.unit)
    return {"item_id": item.id, "work_item_code": item.work_item_code, "unit": item.unit,
      "current": item.rate_resolution, "current_source": item.rate_source.value if item.rate_source else None,
      "current_unit_rate": item.unit_rate,
      "would_resolve_to": ({"source": res.source, "unit_rate": res.unit_rate, "base_rate": res.base_rate,
        "escalation_factor": res.escalation_factor, **res.trace} if res.found else None),
      "attempts": res.attempts, "stack": resolver.stack_summary()}