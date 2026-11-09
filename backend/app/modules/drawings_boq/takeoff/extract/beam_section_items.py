from __future__ import annotations
from app.engine.measure import rule_registry as RR

RULE = "BEAM_SECTION_ITEMS"
META_KEY = "beam_section_items"
MM_INCH = 25.4

def enabled() -> bool:
  return RR.on(RULE)

def _bars(g: dict | None) -> str | None:
  return f"{g['n']}-#{g['bar']}" if g and g.get("n") and g.get("bar") else None

def _from_details(rec: dict) -> dict:
  steel = rec.get("steel") or {}
  a: dict = {}
  
  if _bars(steel.get("top")):
    a["top_bars"] = _bars(steel["top"])
  if _bars(steel.get("bottom")):
    a["bottom_bars"] = _bars(steel["bottom"])
  ring = steel.get("ring") or {}
  if ring.get("bar") and ring.get("spacing_mm"):
    a["stirrup_bar_no"] = ring["bar"]
    a["stirrup_spacing_in"] = round(ring["spacing_mm"] / MM_INCH, 1)
  return a

def sections_of(meta: dict) -> list:
  tables = meta.get("structure_tables") or {}
  if (tables.get("beam_sections") or {}).get("sections"):
    return []
  out: dict = {}
  drawn = {rec["mark"] for rec in (tables.get("beam_callouts") or {}).get("sections") or []}

  for rec in meta.get("beam_details") or []:
    attrs = _from_details(rec)
    if attrs and rec.get("mark") and rec["mark"] not in drawn:
      low = [r for r in ("OCR_LOW_CONFIDENCE",) if rec.get("read") == "OCR" and not attrs.get("top_bars")]
      out[(rec["mark"], None)] = {"mark": rec["mark"], "attrs": {"key": rec["mark"], **attrs}, "reasons": low, "source": "DETAILS"}

  for rec in (tables.get("beam_callouts") or {}).get("sections") or []:
    attrs = {"key": rec["mark"] + ("-" + rec["at"].split()[0] if rec.get("at") else ""), "top_bars": rec["top"], "bottom_bars": rec["bottom"]}
    for name, value in (("stirrup", rec.get("stirrup")), ("section_at", rec.get("at")), ("width_in", rec.get("width_in"))):
      if value:
        attrs[name] = value
    if rec.get("vertical_in"):
      attrs["vertical_in"] = list(rec["vertical_in"])
    item = {"mark": rec["mark"], "attrs": attrs, "reasons": list(rec.get("reasons") or []), "source": "CALLOUTS"}
    if rec.get("point"):
      item["point"] = list(rec["point"])
    out[(rec["mark"], rec.get("at") or rec.get("point") and tuple(rec["point"]))] = item
  return list(out.values())

def apply(rows: list) -> int:
  made = 0
  
  for row in rows:
    meta = row.get("meta")
    if meta is None:
      continue
    
    meta.pop(META_KEY, None)
    if not enabled():
      continue
    recs = sections_of(meta)
    if recs:
      meta[META_KEY] = {"sections": recs}
      made += len(recs)
      
  return made
