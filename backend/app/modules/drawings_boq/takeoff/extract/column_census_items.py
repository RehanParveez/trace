from __future__ import annotations
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.extract import read_status as RS

RULE = "COLUMN_PLAN_CENSUS"
META_KEY = "column_plan_census"
PLAN_KINDS = ("FLOOR", "COLUMN_LAYOUT", "SLAB")
LEVELS = ("ROOF", "FOURTH", "THIRD", "SECOND", "FIRST", "GROUND", "BASEMENT")
REASONS = ("JOIN_MISSING", "NEEDS_STOREY_HEIGHT")

def enabled() -> bool:
  return RR.on(RULE)

def _marked(row: dict) -> bool:
  if any(c.category == "COLUMN" and not (c.facts or {}).get("from_shapes") for c in row.get("candidates") or []):
    return True
  joins = (row.get("meta") or {}).get("structure_joins") or {}
  return bool(joins.get("planted"))

def members_of(row: dict) -> list:
  shapes = (row.get("stats") or {}).get("column_shapes") or {}
  if not shapes.get("classes") or shapes.get("level_hint") not in LEVELS:
    return []
  out = []
  
  for cls in shapes["classes"]:
    pts = cls.get("points") or []
    for p in pts:
      out.append({"at": [p[0], p[1]], "size_mm": [cls["a_mm"], cls["b_mm"]], "floor": shapes["level_hint"]})
    for _ in range(max(0, int(cls["count"]) - len(pts))):
      out.append({"at": None, "size_mm": [cls["a_mm"], cls["b_mm"]], "floor": shapes["level_hint"]})
  return out

def apply(rows: list) -> int:
  made = 0
  taken: set = set()
  for row in sorted(rows, key=lambda r: r.get("page_no") or 0):
    meta = row.get("meta")
    if meta is None:
      continue
    meta.pop(META_KEY, None)
    if not enabled():
      continue
    
    ident = meta.get("identity") or {}
    kind = RS.plan_kind_of(ident) or ("FLOOR" if ident.get("plan_kind") == "WORKING" else None)
    level = ((row.get("stats") or {}).get("column_shapes") or {}).get("level_hint")
    if kind not in PLAN_KINDS or level in taken or _marked(row):
      continue
    
    members = members_of(row)
    if members:
      taken.add(level)
      meta[META_KEY] = {"level": level, "members": members}
      made += len(members)
  return made
