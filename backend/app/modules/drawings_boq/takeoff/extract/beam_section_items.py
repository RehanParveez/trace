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
  
  for rec in meta.get("beam_details") or []:
    attrs = _from_details(rec)
    if attrs and rec.get("mark"):
      low = [r for r in ("OCR_LOW_CONFIDENCE",) if rec.get("read") == "OCR" and not attrs.get("top_bars")]
      out[rec["mark"]] = {"mark": rec["mark"], "attrs": {"key": rec["mark"], **attrs}, "reasons": low, "source": "DETAILS"}
      
  for rec in (tables.get("beam_callouts") or {}).get("sections") or []:
    attrs = {"key": rec["mark"], "top_bars": rec["top"], "bottom_bars": rec["bottom"]}
    if rec.get("stirrup"):
      attrs["stirrup"] = rec["stirrup"]
    out[rec["mark"]] = {"mark": rec["mark"], "attrs": attrs, "reasons": list(rec.get("reasons") or []), "source": "CALLOUTS"}
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
