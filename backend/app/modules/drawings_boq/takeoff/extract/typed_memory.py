from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import site_items as SI
from app.modules.drawings_boq.takeoff.extract import drainage as DR

KEY = "typed"

def fields_used(category: str, missing: list, facts: dict | None, typed: dict, notes: list | None = None, height_field=None) -> dict:
  """{field: value mm} of the typed sizes a candidate took when it was accepted."""
  f = facts or {}
  out: dict = {}
  
  def put(field: str | None) -> None:
    if field and typed.get(field) is not None:
      out[field] = float(typed[field])
  if category == "SITE":
    tokens = ("length_mm", "width_mm", "height_mm", "thickness_mm") if f.get("site_kind") in SI.TANK_KINDS else (missing or [])
    for token in tokens:
      put(SI.TYPED_FIELD.get(token))
    return out

  if category == "WALL" and f.get("foundation_item") in DR.TYPED_FIELD:
    put(DR.TYPED_FIELD[f["foundation_item"]])
    return out

  if category == "STAIR" and "waist_mm" in (missing or []):
    put("stair_waist_mm")
  if category == "SLAB" and any(n.get("code") == "SLAB_THICKNESS_DISAGREES" for n in notes or []):
    put("slab_thickness_mm")
  for need in missing or []:
    spec = height_field(category, need, f) if height_field else None
    if spec:
      put(spec[0])
  return out

def latest(rows: list) -> list:
  """rows: [(kind, facts, decided_at)] of accepted items, any order. -> [{"kind", "field", "value_mm", "times", "at"}], newest first, one per (kind, field)."""
  seen: dict = {}
  
  for kind, facts, at in sorted(rows, key=lambda r: r[2], reverse=True):
    for field, value in ((facts or {}).get(KEY) or {}).items():
      slot = seen.get((kind, field))
      if slot is None:
        seen[(kind, field)] = {"kind": kind, "field": field, "value_mm": float(value), "times": 1, "at": at}
      elif slot["value_mm"] == float(value):
        slot["times"] += 1
  return sorted(seen.values(), key=lambda e: e["at"], reverse=True)
