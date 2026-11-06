from __future__ import annotations
from app.engine.measure import rule_registry as RR

RULE = "LINTEL_SCHEDULE_ITEMS"
META_KEY = "lintel_schedule_items"
MM_INCH = 25.4
ORDER_MARK = "L{n}"
BASIS_PRINTED = "PRINTED"
BASIS_ORDER = "ROW_ORDER"
REASON_ORDER = "VALUE_DEFAULTED"
STEEL_KEYS = {"bottom": "bottom_bars", "top": "top_bars", "bars": "bars", "extra": "extra_bars"}

def enabled() -> bool:
  return RR.on(RULE)

def bars_text(rec: dict | None) -> str | None:
  if not rec or not rec.get("n") or not rec.get("bar"):
    return None
  return f"{int(rec['n'])}#{int(rec['bar'])}"

def ring_text(rec: dict | None) -> str | None:
  if not rec or not rec.get("bar") or not rec.get("spacing_mm"):
    return None
  return f"#{int(rec['bar'])}-{float(rec['spacing_mm']) / MM_INCH:g}\" C/C"

def type_of(row: dict, order: int) -> dict:
  steel = row.get("steel") or {}
  printed = row.get("mark")
  attrs = {"key": printed or ORDER_MARK.format(n=order), "width_in": round(float(row["width_mm"]) / MM_INCH, 2), "depth_in": round(float(row["depth_mm"]) / MM_INCH, 2)}
  for name, key in STEEL_KEYS.items():
    text = bars_text(steel.get(name))
    if text:
      attrs[key] = text
      
  ring = ring_text(steel.get("ring"))
  if ring:
    attrs["rings"] = ring
  return {"mark": attrs["key"], "attrs": attrs, "basis": BASIS_PRINTED if printed else BASIS_ORDER, "span_max_ft": row.get("span_max_ft"), "reasons": [] if printed else [REASON_ORDER]}

def types_of(rows: list) -> list:
  usable = [r for r in rows or [] if r.get("width_mm") and r.get("depth_mm")]
  return [type_of(r, i + 1) for i, r in enumerate(usable)]

def apply(rows: list) -> int:
  made = 0
  for row in rows:
    meta = row.get("meta")
    if meta is None:
      continue
    meta.pop(META_KEY, None)
    if not enabled():
      continue
    
    types = types_of(((meta.get("schedule") or {}).get("lintels")))
    if types:
      meta[META_KEY] = {"types": types}
      made += len(types)
  return made
