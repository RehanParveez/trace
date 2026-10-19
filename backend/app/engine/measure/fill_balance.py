from __future__ import annotations
from decimal import Decimal
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE
from app.engine.measure.units import q6

FILL_CODE = "EXC-FILL"
ONE = Decimal("1")
HUNDRED = Decimal("100")

def fill_of(extra_ledger, params: dict) -> dict:
  """What the balance needs of the filling: the measured volume (all PDF rows with the filling work item) and the three switches."""
  total = sum((Decimal(str(r.quantity)) for r in (extra_ledger or ()) if getattr(r, "source_kind", None) == PDF_SOURCE
    and r.work_item_code == FILL_CODE and r.quantity > 0), Decimal("0"))
  
  def value(name: str) -> Decimal:
    return Decimal(str((params.get(name) or {}).get("value") or 0))
  return {"fill_m3": total, "swell_pct": value("earth_swell_pct"), "compaction_pct": value("fill_compaction_pct"),
    "from_excavation": value("fill_from_excavation") >= Decimal("0.5"),
    "assumed": sorted(n for n in ("earth_swell_pct", "fill_compaction_pct", "fill_from_excavation") if (params.get(n) or {}).get("source") == "default")}

def balance_fill(exc: Decimal, back: Decimal, fill: dict | None) -> dict:
    
  if not fill or fill.get("fill_m3", Decimal("0")) <= 0:
    return {"floor_fill_m3": "0", "fill_note": "NO_FILL_ITEM"}
  surplus = max(Decimal("0"), exc - back)
  surplus_loose = surplus * (ONE + fill["swell_pct"] / HUNDRED)
  need_loose = fill["fill_m3"] * (ONE + fill["compaction_pct"] / HUNDRED)
  reused = min(surplus_loose, need_loose) if fill["from_excavation"] else Decimal("0")
  
  return {
    "floor_fill_m3": str(q6(fill["fill_m3"])), "floor_fill_need_m3": str(q6(need_loose)), "surplus_loose_m3": str(q6(surplus_loose)),
    "fill_reused_m3": str(q6(reused)), "fill_imported_m3": str(q6(need_loose - reused)), "carted_loose_m3": str(q6(surplus_loose - reused)),
    "fill_reuse_on": bool(fill["from_excavation"]), "fill_assumed": fill["assumed"], "fill_note": "FILL_REPORTED"}
