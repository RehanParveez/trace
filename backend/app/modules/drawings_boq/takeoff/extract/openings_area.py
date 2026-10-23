from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import finishes as FN

MIN_MM, MAX_MM = 200.0, 6000.0

def _size(c) -> tuple | None:
  f = c.facts or {}
  size = f.get("size_schedule_mm") or f.get("size_drawn_mm")
  if not size or len(size) != 2:
    return None
  w, h = float(size[0]), float(size[1])
  return (w, h) if MIN_MM <= w <= MAX_MM and MIN_MM <= h <= MAX_MM else None

def _group(cands: list) -> list:
  rows: dict = {}
  for c in cands:
    if c.status == "INVALID" or not c.tag:
      continue
  
    size = _size(c)
    pts = [list(p) for p in ((c.geometry or {}).get("points") or [])]
    if size is None or not pts:
      continue
    rows.setdefault((str(c.tag).upper(), size), {"first": c, "points": [], "size": size})["points"].extend(pts)
  return sorted(rows.values(), key=lambda r: str(r["first"].tag))

def opening_area_candidates(doors: list, windows: list, ctx: dict, level_hint: str | None, spec, cls, finish) -> list:
  out = []
  
  for item, label, tag, cands in ((FN.DOOR_AREA, "Door area", "DOOR-AREA", doors), (FN.WINDOW_AREA, "Window area", "WINDOW-AREA", windows)):
    for row in _group(cands):
      c, (w, h), pts = row["first"], row["size"], row["points"]
      n = len(pts)
      area_each = w * h / 1e6
      f = c.facts or {}
      
      kind = f.get("opening_kind") or ("DOOR" if item == FN.DOOR_AREA else "WINDOW")
      facts = {"derived_from": "OPENINGS", "opening_key": c.key, "opening_tag": c.tag, "opening_kind": kind, "opening_count": n, "size_mm": [w, h],
        "area_each_m2": round(area_each, 3), "area_m2": round(area_each * n, 3), "size_source": "SCHEDULE" if f.get("size_schedule_mm") else "DRAWN",
        "material": None}
      notes = [C.note("OPENING_AREA_FROM_OPENINGS"), C.note("OPENING_MATERIAL_NOT_READ")]
      if f.get("height_assumed") and not f.get("size_schedule_mm"):
        facts["height_assumed"] = True
        notes.append(C.note("OPENING_HEIGHT_ASSUMED", height_mm=h))
      if f.get("view"):
        facts["view"] = f["view"]
      where = f" · {spec[0]}" if spec else ""
      out.append(FN._make(cls, ctx, finish, (item, c.key), item, f"{label} {c.tag} ×{n} · {w:g}×{h:g} mm · {area_each * n:.2f} m²{where}", f"{tag}-{c.tag}", pts,
        {"length_mm": round(w, 1), "width_mm": round(h, 1)}, [], notes, facts,
        0.8 if facts["size_source"] == "SCHEDULE" else 0.6, count=n))
  return out
