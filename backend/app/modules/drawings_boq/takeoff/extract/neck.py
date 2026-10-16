from __future__ import annotations
import hashlib
from app.modules.drawings_boq.takeoff.extract import config as C

def _key(*parts) -> str:
  return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:16]

def _level(c) -> str | None:
  return (((c.facts or {}).get("view") or {}).get("level_hint"))

def _area(c) -> float:
  p = c.params or {}
  return float(p.get("length_mm") or 0.0) * float(p.get("width_mm") or 0.0)

def pair(footings: list, columns: list) -> list:
  """[(footing, column)]: a footing mark and the column mark of the lowest framing plan that has as many columns, smallest with smallest.
  A footing or column with no size, or with no column of the same count, is left out."""
  out = []
  free = [c for c in columns if _area(c) > 0.0]
  by_count: dict = {}
  
  for f in footings:
    if _area(f) > 0.0:
      by_count.setdefault(f.count, []).append(f)
  for n, fs in sorted(by_count.items()):
    cs = sorted((c for c in free if c.count == n), key=_area)
    if not cs:
      continue
    fs = sorted(fs, key=_area)
    for f, c in zip(fs, cs):
      out.append((f, c))
      free.remove(c)
  return out

def candidates(cands: list, ctx: dict, Candidate, finish) -> list:
  """Neck column candidates for the footings of the foundation plan. cands is everything found on the sheet so far."""
  footings = [c for c in cands if c.category == "FOOTING" and c.count > 0 and ((c.facts or {}).get("view") or {}).get("level_hint")]
  if not footings:
    return []
  low = _level(footings[0])
  columns = [c for c in cands if c.category == "COLUMN" and _level(c) == low and "UNMARKED_COLUMNS" not in {n.get("code") for n in c.notes}
    and not (c.facts or {}).get("neck_of")]
  out = []
  
  for f, c in pair(footings, columns):
    p = {"length_mm": c.params["length_mm"], "width_mm": c.params["width_mm"], "dims_basis": "SPECIFIED"}
    facts = {"tag": c.tag, "count": f.count, "neck_of": f.tag, "column_key": c.key, "footing_key": f.key, "size_used_mm": [p["length_mm"], p["width_mm"]],
      "view": (f.facts or {}).get("view")}
    notes = [C.note("NECK_COLUMN_FROM_FOOTINGS", footing=f.tag, column=c.tag, count=f.count)]
    
    if c.params.get("steel"):
      p["steel"] = dict(c.params["steel"])
      facts["steel_text"] = (c.facts or {}).get("steel_text")
      facts["steel_source"] = (c.facts or {}).get("steel_source")
      notes.append(C.note("STEEL_FROM_DETAIL", text=facts["steel_text"]))
    label = f"Neck column {c.tag} ×{f.count} · {c.params['length_mm']:g}×{c.params['width_mm']:g} mm (footing {f.tag} to floor)"
    cand = Candidate(key=_key("COLUMN", "NECK", f.key, c.key), category="COLUMN", kind="COUNT", quantity_mode="COUNT_X_VOLUME", label=label,
      tag=None, geometry=dict(f.geometry or {}), params=p, missing=["height_mm"], work_item="CON-RCC", status="VALID", confidence=0.0, facts=facts,
      notes=notes, source="TAG_SCAN", count=f.count)
    out.append(finish(cand, ctx, 0.6))
  return out
