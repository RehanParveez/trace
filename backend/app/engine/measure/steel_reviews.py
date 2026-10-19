from __future__ import annotations
from decimal import Decimal
from app.engine.measure.member_steel import member_lines
from app.engine.measure.units import q6

ANCHOR_REVIEW_DIA = Decimal("40")
LAP_REVIEW_DIA = Decimal("60")

def review(items: list, anchor_dia: Decimal, lap_dia: Decimal, lap_is_default: bool, lap_table: dict | None) -> dict:
  """items: [{"cat", "length", "width", "depth", "steel", "count", "cover", "hook"}]. Returns the extra kg each check would add and its share of the bare total."""
  def total(anchor: Decimal, lap: Decimal, table: dict | None, only: tuple) -> Decimal:
    kg = Decimal("0")
    for it in items:
      if it["cat"] not in only:
        continue
    
      _, bare = member_lines(it["cat"], it["length"], it["width"], it["depth"], it["steel"], it["cover"], it["hook"], lap, anchor, table)
      kg += bare * it["count"]
    return kg

  bars = ("BEAM", "LINTEL", "COLUMN")
  base = total(anchor_dia, lap_dia, lap_table, bars)
  out: dict = {"bare_kg": str(q6(sum((member_lines(it["cat"], it["length"], it["width"], it["depth"], it["steel"], it["cover"], it["hook"], lap_dia, anchor_dia, lap_table)[1] * it["count"]
    for it in items), Decimal("0"))))}
  whole = Decimal(out["bare_kg"])
  if anchor_dia < ANCHOR_REVIEW_DIA:
    added = total(ANCHOR_REVIEW_DIA, lap_dia, lap_table, bars) - base
    out["anchorage"] = {"current_dia": str(anchor_dia), "assumed_dia": str(ANCHOR_REVIEW_DIA), "added_kg": str(q6(added)),
      "share_pct": str(q6(added / whole * 100)) if whole > 0 else "0"}
  if lap_is_default and not lap_table and lap_dia < LAP_REVIEW_DIA:
    added = total(anchor_dia, LAP_REVIEW_DIA, None, ("COLUMN",)) - total(anchor_dia, lap_dia, None, ("COLUMN",))
    out["lap"] = {"current_dia": str(lap_dia), "assumed_dia": str(LAP_REVIEW_DIA), "added_kg": str(q6(added)),
      "share_pct": str(q6(added / whole * 100)) if whole > 0 else "0"}
  return out
