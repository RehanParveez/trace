from __future__ import annotations
from app.engine.measure import readings as QS
from app.engine.measure import proposed as PR
from app.modules.drawings_boq.takeoff.extract import config as C

BASEMENT = "BASEMENT"
HEIGHT_CODES = ("HEIGHT_FROM_SECTION", "HEIGHT_FROM_NOTE", "HEIGHT_FROM_QS")

def _ft_in(mm: float) -> str:
  inches = round(mm / 25.4)
  return f"{inches // 12}'-{inches % 12}\""

BEAM_BASES = ("ABOVE_PLINTH_BEAM", "BETWEEN_BEAMS")

def less_beams(heights: dict, lowest_level: bool, ft_in) -> dict:
  basis = QS.choice("wall_height_basis")
  entry = (heights or {}).get("WALL")
  if basis not in BEAM_BASES or not entry or entry.get("basis") not in ("SECTION", "QS"):
    return heights
  sizes = PR.sizes()
  cuts: list = []
  
  if lowest_level:
    cuts.append(("plinth beam", float(sizes["plinth_beam_depth_mm"]["mm"])))
  if basis == "BETWEEN_BEAMS":
    web = float(sizes["beam_depth_mm"]["mm"])
    if QS.param("beam_depth_includes_slab"):
      web = max(web - float(QS.convention("slab_thickness_mm") or 0.0), 0.0)
    cuts.append(("roof beam web", web))
  total = sum(mm for _, mm in cuts)
  
  if total <= 0.0 or float(entry["mm"]) <= total:
    return heights
  mm = float(entry["mm"]) - total
  text = f"{entry['text']}, less the " + " and the ".join(f"{name} {ft_in(v)}" for name, v in cuts) + f" ({basis.lower().replace('_', ' ')}), {ft_in(mm)}"
  return {**heights, "WALL": {**entry, "mm": mm, "text": text, "less_beams": [{"name": n, "mm": v} for n, v in cuts]}}

def floor_heights(heights: dict, floors: dict | None, level_hint: str | None, ft_in, clear_only) -> dict:
  if not QS.flag("wall_height_floor_to_floor"):
    return clear_only(heights, floors, level_hint)
  fh = (floors or {}).get(level_hint or "") or {}
  f2f = fh.get("floor_to_floor_mm")
  
  if f2f:
    entry = {"mm": float(f2f), "text": f"floor-to-floor height {ft_in(float(f2f))} printed on the building section", "basis": "SECTION"}
  elif str(level_hint or "").upper() == BASEMENT:
    mm = float(QS.convention("basement_floor_to_floor_mm"))
    entry = {"mm": mm, "text": f"basement floor-to-floor height {ft_in(mm)}, as the QS gave it (S5)", "basis": "QS"}
  else:
    return clear_only(heights, floors, level_hint)
  out = dict(heights)
  for cat in ("WALL", "COLUMN"):
    out.setdefault(cat, entry)
  return out

def mark_clear(cands: list, floors: dict | None, level_hint: str | None) -> int:
  clear = ((floors or {}).get(level_hint or "") or {}).get("clear_mm")
  if not clear or not QS.flag("wall_height_floor_to_floor"):
    return 0
  n = 0
  for c in cands:
    if c.category != "WALL" or any(x.get("code") == "HEIGHT_FROM_NOTE" for x in c.notes or []):
      continue
    if any(x.get("code") in ("HEIGHT_FROM_SECTION", "HEIGHT_FROM_QS") for x in c.notes or []):
      c.facts = {**(c.facts or {}), "clear_height_mm": float(clear)}
      n += 1
  return n

def stamp(cand, *ids: str) -> None:
  """Put the answer numbers on the facts of a candidate, so its provenance shows whose value it used."""
  f = cand.facts if cand.facts is not None else {}
  f["qs"] = sorted(set(f.get("qs") or []) | set(ids))
  cand.facts = f

def rcc_heights(cands: list, level_hint: str | None) -> int:
  if str(level_hint or "").upper() != BASEMENT:
    return 0
  mm = float(QS.convention("basement_wall_height_mm"))
  n = 0
  
  for c in cands:
    f = c.facts or {}
    if c.category != "WALL" or f.get("construction") != "RCC":
      continue
    if any(x.get("code") == "HEIGHT_FROM_NOTE" for x in c.notes or []):
      continue
  
    c.params = {**(c.params or {}), "height_mm": mm, "dims_basis": "SPECIFIED"}
    c.missing = [m for m in (c.missing or []) if m != "height_mm"]
    c.notes = [x for x in (c.notes or []) if x.get("code") not in HEIGHT_CODES]
    c.notes.append(C.note("HEIGHT_FROM_QS", text=f"basement concrete wall {_ft_in(mm)} high for the estimate, as the QS gave it (S1, S5)"))
    stamp(c, "S1", "S5")
    n += 1
  return n

def counted_completion(completion: list) -> list:
  if not QS.flag("rcc_ring_closed"):
    return []
  for c in completion or []:
    stamp(c, "S8")
  return list(completion or [])

CFT_MM3 = 304.8 ** 3

def _piece(c, role: str, assumed: list) -> None:
  p = c.params or {}
  if p.get("length_mm") and p.get("width_mm") and p.get("depth_mm"):
    c.facts = {**(c.facts or {}), "foundation_piece": {"role": role, "cft": round(p["length_mm"] * p["width_mm"] * p["depth_mm"] / CFT_MM3, 4), "assumed": assumed}}

def apply(cands: list, level_hint: str | None) -> dict:
  stats = {"footing_depths": 0, "stairs": 0, "tanks": 0, "boundary": 0, "neck_heights": 0}
  depth = float(QS.convention("footing_depth_mm"))
  
  for c in cands:
    f = c.facts or {}
    if c.category == "FOOTING" and "depth_mm" in (c.missing or []):
      c.params = {**(c.params or {}), "depth_mm": depth}
      c.params.setdefault("dims_basis", "SPECIFIED")
      c.missing = [m for m in c.missing if m != "depth_mm"]
      c.notes.append(C.note("FOOTING_DEPTH_QS", depth_mm=depth))
      
      stamp(c, "X4")
      stats["footing_depths"] += 1
    elif c.category == "COLUMN" and f.get("neck_of") and "height_mm" in (c.missing or []):
      size = PR.sizes()["neck_height_mm"]
      c.params = {**(c.params or {}), "depth_mm": size["mm"], "dims_basis": "SPECIFIED"}
      c.missing = [m for m in c.missing if m != "height_mm"]
      c.facts = {**f, "neck_assumed": {"mm": size["mm"], "text": size["text"], "evidence": size["evidence"]}}
      nh = C.note("NECK_HEIGHT_ASSUMED", height_mm=size["mm"])
      nh["message"] = (f"The neck column runs from the top of the footing to the lowest floor. That height is not printed on the sheet. {size['text']} is used, as the QS's workbook has it "
        f"({size['evidence'].rstrip('.')}). Type another height to override it.")
      c.notes.append(nh)
      stats["neck_heights"] += 1
      
    elif c.category == "STAIR" and any(x.get("code") == "STAIR_WAIST_ASSUMED" for x in c.notes or []):
      stamp(c, "X8", "S12")
      stats["stairs"] += 1
    elif c.category == "SITE" and f.get("site_kind") in ("OHWT", "UGWT", "SEPTIC"):
      if not f.get("tank_slabs_mm"):
        c.notes.append(C.note("TANK_SLABS_QS", top_mm=QS.convention("tank_top_slab_mm"), bottom_mm=QS.convention("tank_bottom_slab_mm")))
        stamp(c, "S11")
      stats["tanks"] += 1
    elif c.category == "SITE" and f.get("site_kind") == "BOUNDARY_WALL":
      c.notes.append(C.note("SITE_WALL_QS_ESTIMATE", thickness_mm=QS.convention("boundary_wall_thickness_mm")))
      stamp(c, "S7", "X11")
      stats["boundary"] += 1
  for c in cands:
    codes = {n.get("code") for n in c.notes or []}
    if c.category == "FOOTING":
      _piece(c, "FOOTING", [x for x, k in (("depth", "FOOTING_DEPTH_QS"), ("size pairing", "FOOTING_SIZE_ORDER_ASSUMED"), ("size pairing", "FOOTING_SIZE_PAIRED"),
        ("size by elimination", "FOOTING_SIZE_BY_ELIMINATION")) if k in codes])
    elif c.category == "COLUMN" and (c.facts or {}).get("neck_of"):
      _piece(c, "NECK", ["height"] if "NECK_HEIGHT_ASSUMED" in codes else [])
  return stats
