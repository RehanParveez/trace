from __future__ import annotations
from app.engine.measure import rule_registry as RR

RULE = "FOOTING_SECTION_ITEMS"
META_KEY = "footing_section_items"
IN_MM = 25.4
FT_MM = 304.8
CONFLICT_ISSUES = ("CAPTION_WALL_DIFFERS", "LAYERS_DISAGREE", "BASE_WIDTH_DISAGREES")

def enabled() -> bool:
  return RR.on(RULE)

def _inches(mm) -> float | None:
  return round(float(mm) / IN_MM, 2) if mm else None

def _feet(mm) -> float:
  return round(float(mm) / FT_MM * 2) / 2

def section_attrs(rec: dict) -> dict:
  a: dict = {"key": f"{rec['mark']}-section"}
  if rec.get("wall_in"):
    a["wall_in"] = rec["wall_in"]
  if rec.get("exterior") is not None:
    a["exterior"] = bool(rec["exterior"])
  steps = rec.get("steps") or []
  
  if steps:
    a["step_widths_in"] = sorted(s["width_in"] for s in steps)
    heights = {s["height_in"] for s in steps}
    if len(heights) == 1:
      a["step_height_in"] = next(iter(heights))
  if _inches(rec.get("base_width_mm")):
    a["trench_width_in"] = _inches(rec["base_width_mm"])
  if _inches(rec.get("pcc_mm")):
    a["pcc_in"] = _inches(rec["pcc_mm"])
  if _inches(rec.get("sand_mm")):
    a["sand_in"] = _inches(rec["sand_mm"])
  return a

def view_attrs(rec: dict) -> dict:
  sides = sorted(float(x) for x in rec["size_mm"])
  return {"key": f"{rec['mark']}-section", "width_ft": _feet(sides[0]), "length_ft": _feet(sides[1])}

def _reasons(rec: dict) -> list:
  return ["CONFLICT_IN_DRAWING"] if any(i in CONFLICT_ISSUES for i in rec.get("issues") or []) else []

def sections_of(meta: dict) -> list:
  out: list = []
  
  for rec in meta.get("footing_sections") or []:
    if rec.get("read") == "OK" and rec.get("mark"):
      out.append({"mark": rec["mark"], "attrs": section_attrs(rec), "reasons": _reasons(rec), "source": "SECTION"})
  for rec in meta.get("footing_views") or []:
    if rec.get("read") == "OK" and rec.get("mark") and rec.get("size_mm"):
      out.append({"mark": rec["mark"], "attrs": view_attrs(rec), "reasons": _reasons(rec), "source": "VIEW"})
  return out

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
