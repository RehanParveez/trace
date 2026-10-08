from __future__ import annotations
from app.modules.drawings_boq.models import BOQItem, DrawingElement
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq import boq_logic as logic
from app.core.exceptions import TraceException
from decimal import Decimal
from sqlalchemy import select
from app.modules.drawings_boq.repository import BOQVersionRepository, BOQItemRepository
from uuid import UUID
from app.modules.drawings_boq.boq_repository import BOQEngineRepository
from app.modules.drawings_boq.pricing import pricing_logic as pl

ELEMENT_LIST_CAP = 25

def item_row(i: BOQItem) -> dict:
  rate = i.unit_rate
  return {"id": i.id, "item_key": i.item_key, "work_item_code": i.work_item_code, "material_name": i.material_name,
    "unit": i.unit, "net_quantity": i.net_quantity, "quantity": i.quantity, "unit_rate": rate,
    "amount": logic.q2(Decimal(i.quantity) * Decimal(rate)) if rate is not None else None}

class BOQDiffService:
    
  def __init__(self, session: AsyncSession):
    self.session = session
    self.versions = BOQVersionRepository(session)
    self.items = BOQItemRepository(session)
    self.repo = BOQEngineRepository(session)

  async def _version(self, org: UUID, version_id: UUID):
    v = await self.versions.get_by_id_and_org(version_id, org)
    if v is None:
      raise TraceException("BOQ version not found.", status_code=404, code="BOQ_VERSION_NOT_FOUND")
    return v

  async def _element_keys(self, org: UUID, version_id: UUID) -> dict[UUID, dict[str, dict]]:
    links = await self.repo.link_pairs(version_id, org)
    ledger_ids = [lid for pairs in links.values() for lid, _ in pairs]
    ledger = {l.id: l for l in await self.repo.ledger_by_ids(ledger_ids)}
    element_ids = {l.element_id for l in ledger.values() if l.element_id}
    info: dict[UUID, tuple] = {}
    
    if element_ids:
      rows = await self.session.execute(select(DrawingElement.id, DrawingElement.ifc_global_id, DrawingElement.name,
        DrawingElement.ifc_type).where(DrawingElement.id.in_(element_ids)))
      info = {i: (g, n or t) for i, g, n, t in rows.all()}
    out: dict[UUID, dict[str, dict]] = {}
    
    for item_id, pairs in links.items():
      bucket: dict[str, dict] = {}
      for lid, _ in pairs:
        l = ledger.get(lid)
        if l is None or not l.element_id:
          continue
        guid, name = info.get(l.element_id, (None, None))
        bucket.setdefault(guid or str(l.element_id), {"element_id": l.element_id, "name": name, "ifc_global_id": guid})
      out[item_id] = bucket
    return out

  async def diff_versions(self, org: UUID, a_id: UUID, b_id: UUID, *, include_unchanged: bool = False,
    include_elements: bool = True) -> dict:
    if a_id == b_id:
      raise TraceException("Pick two different BOQ versions to compare.", status_code=422, code="DIFF_SAME_VERSION")
    a, b = await self._version(org, a_id), await self._version(org, b_id)
    
    if a.project_id != b.project_id:
      raise TraceException("Only versions of the same project can be compared.", status_code=422, code="DIFF_PROJECT_MISMATCH")
    rows_a = [item_row(i) for i in await self.items.list_by_version(a.id, org)]
    rows_b = [item_row(i) for i in await self.items.list_by_version(b.id, org)]
    result = pl.diff_lines(rows_a, rows_b)
    for line in result["lines"]:
      line["elements_added"], line["elements_removed"], line["element_counts"] = [], [], {}

    if include_elements:
      keyed_a, keyed_b = pl.line_keys(rows_a), pl.line_keys(rows_b)
      el_a, el_b = await self._element_keys(org, a.id), await self._element_keys(org, b.id)
      for line in result["lines"]:
        if line["status"] == "UNCHANGED":
          continue
      
        ra, rb = keyed_a.get(line["item_key"]), keyed_b.get(line["item_key"])
        ea = el_a.get(ra["id"], {}) if ra else {}
        eb = el_b.get(rb["id"], {}) if rb else {}
        if line["status"] == "CHANGED" and not (ea and eb):
          continue
        added = [eb[k] for k in sorted(set(eb) - set(ea))]
        removed = [ea[k] for k in sorted(set(ea) - set(eb))]
        line["elements_added"], line["elements_removed"] = added[:ELEMENT_LIST_CAP], removed[:ELEMENT_LIST_CAP]
        line["element_counts"] = {"a": len(ea), "b": len(eb), "added": len(added), "removed": len(removed)}

    if not include_unchanged:
      result["lines"] = [l for l in result["lines"] if l["status"] != "UNCHANGED"]
    return {"version_a_id": a.id, "version_b_id": b.id, **result}

  @staticmethod
  def diff_rows(rows_a: list[dict], rows_b: list[dict]) -> dict:
    return pl.diff_lines(rows_a, rows_b)