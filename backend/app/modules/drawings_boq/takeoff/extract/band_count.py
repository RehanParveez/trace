from __future__ import annotations
from app.engine.measure import readings as QS
from app.engine.measure import proposed as PR
from app.modules.drawings_boq.takeoff.extract import config as C

TIE_BAND_MIN_WALL_MM = 200.0      

def single_count() -> bool:
  v = QS.param("tie_band_single_count")
  return True if v is None else float(v) >= 0.5

def lintels_counted() -> bool:
  v = QS.param("tie_band_replaces_lintel")
  return not (v is not None and float(v) >= 0.5)

def _role(c) -> str | None:
  return (c.facts or {}).get("beam_role")

def _key(c) -> tuple:
  f = c.facts or {}
  return (round(float(f.get("wall_thickness_mm") or 0.0), 1), f.get("beam_mark") or "")

def _depth(c, assumed_mm: float) -> tuple:
  d = (c.params or {}).get("depth_mm")
  return (float(d), False) if d else (float(assumed_mm), True)

def _beam_m3(c, length_m: float, assumed_mm: float) -> tuple:
  depth, assumed = _depth(c, assumed_mm)
  if _role(c) == "ROOF" and QS.param("beam_depth_includes_slab"):
    depth = max(depth - float(QS.convention("slab_thickness_mm") or 0.0), 0.0)
  width = float((c.params or {}).get("width_mm") or 0.0)
  return length_m * width * depth / 1e6, assumed

def lintel_m3(lintels: list) -> float:
  total = 0.0
  for c in lintels or []:
    p = c.params or {}
    if p.get("length_mm") and p.get("width_mm") and p.get("depth_mm"):
      total += float(p["length_mm"]) * float(p["width_mm"]) * float(p["depth_mm"]) / 1e9 * int(c.count or 1)
  return total

def lintel_run_m(lintels: list, thickness_mm: float) -> float:
  total = 0.0
  for c in lintels or []:
    p, h = c.params or {}, ((c.facts or {}).get("hosted") or {})
    if not p.get("length_mm") or not h:
      continue
    part = ((c.facts or {}).get("split") or {}).get("part")
    thin, rcc, hosted = int(h.get("thin") or 0), int(h.get("rcc") or 0), int(h.get("hosted") or 0)
    if part:
      n = int(c.count or 0) if (part == "WALL") == (thickness_mm >= TIE_BAND_MIN_WALL_MM) else 0
    else:
      n = max(hosted - thin - rcc, 0) if thickness_mm >= TIE_BAND_MIN_WALL_MM else thin
    total += float(p["length_mm"]) / 1000.0 * n
  return total

def solid_length_m(band, lintels: list) -> float:
  f = band.facts or {}
  full = float(f.get("length_m") or 0.0)
  if not lintels_counted():
    return full
  run = lintel_run_m(lintels, float(f.get("wall_thickness_mm") or 0.0))
  if run <= 0.0:
    run = float(f.get("openings_m") or 0.0)
  return round(max(full - run, 0.0), 3)

def _relabel(c, old_m: float, new_m: float) -> None:
  if c.label and f"{old_m:.2f} m" in c.label:
    c.label = c.label.replace(f"{old_m:.2f} m", f"{new_m:.2f} m")

def _text(rec: dict) -> str:
  return (f"{rec['without_band_cft']:,.0f} cft of roof beam and lintel concrete without the tie band, {rec['with_band_cft']:,.0f} cft with the tie band laid separately over the solid wall "
    f"(difference {rec['delta_cft']:,.0f} cft)" + ("; a depth is assumed in this figure" if rec["depth_assumed"] else ""))

def resolve(beams: list, roof_band: dict | None, lintels: list, level_hint: str | None = None, roof_band_read: bool = True) -> tuple:
  bands = [c for c in beams if _role(c) == "BAND"]
  if not bands:
    return list(beams), None
  sizes = PR.sizes()
  assumed = float(sizes["beam_depth_mm"]["mm"])
  roofs = [c for c in beams if _role(c) == "ROOF"]
  
  eligible = [b for b in bands if float((b.facts or {}).get("wall_thickness_mm") or 0.0) >= TIE_BAND_MIN_WALL_MM]
  elig_ids = {id(b) for b in eligible}
  thin_ids = {id(b) for b in bands if id(b) not in elig_ids}
  solid = {id(b): solid_length_m(b, lintels) for b in eligible}
  roof_m3 = sum(_beam_m3(c, float((c.facts or {}).get("length_m") or 0.0), assumed)[0] for c in roofs)
  lint_m3 = lintel_m3(lintels)
  band_m3, band_assumed = 0.0, False
  
  for b in eligible:
    v, a = _beam_m3(b, solid[id(b)], assumed)
    band_m3 += v
    band_assumed = band_assumed or a
  roof_assumed = any(_depth(c, assumed)[1] for c in roofs)
  without, with_ = roof_m3 + lint_m3, roof_m3 + lint_m3 + band_m3
  printed = (bool(roof_band) or not roof_band_read) and bool(roofs)
  one = single_count()
  if not one:
    member = "BOTH"
  else:
    member = "ROOF_BAND" if printed else "TIE_BAND"
  keep: list = []
  gone: list = []
  
  for c in beams:
    role = _role(c)
    if role == "BAND":
      if id(c) in thin_ids:
        gone.append((c, "THIN_WALL"))
      elif one and printed:
        gone.append((c, "ROOF_BAND_PRINTED"))
      else:
        keep.append(c)
    elif role == "ROOF" and one and not printed and any(_key(c) == _key(b) for b in eligible):
      gone.append((c, "TIE_BAND_IS_THE_MEMBER"))
    else:
      keep.append(c)
  kept_ids = {id(c) for c in keep}
  
  for b in eligible:
    if id(b) in kept_ids:
      new = solid[id(b)]
      f = b.facts
      f["length_full_m"], f["length_m"] = f.get("length_m"), new
      _relabel(b, float(f["length_full_m"]), new)
      b.params["length_mm"] = round(new * 1000.0, 1)
      
  counted = sum(_beam_m3(c, float((c.facts or {}).get("length_m") or 0.0), assumed)[0] for c in keep if _role(c) in ("ROOF", "BAND")) + lint_m3
  cft = float(QS.param("cft_per_m3"))
  rec = {"floor": level_hint, "mode": "SINGLE" if one else "SEPARATE", "member": member, "roof_band_printed": printed, "roof_band_read": bool(roof_band_read), "roof_band": dict(roof_band) if roof_band else None,
    "without_band_m3": round(without, 3), "with_band_m3": round(with_, 3), "delta_m3": round(band_m3, 3), "counted_m3": round(counted, 3),
    "without_band_cft": round(without * cft, 1), "with_band_cft": round(with_ * cft, 1), "delta_cft": round(band_m3 * cft, 1), "counted_cft": round(counted * cft, 1),
    "tie_band_solid_m": round(sum(solid.values()), 3),
    "depth_assumed": bool(roof_assumed or band_assumed), "lintels_counted": lintels_counted(),
    "dropped": [{"tag": g.tag, "why": why, "length_m": (g.facts or {}).get("length_m")} for g, why in gone]}
  rec["tie_band_full_m"] = round(sum(float((b.facts or {}).get("length_full_m") or (b.facts or {}).get("length_m") or 0.0) for b in eligible), 3)
  
  for c in keep:
    if _role(c) in ("ROOF", "BAND"):
      c.facts["band_count"] = dict(rec)
  head = _text(rec)
  for c in keep:
    role = _role(c)
    
    if role == "ROOF" and member == "ROOF_BAND" and _key(c) in {_key(b) for b in eligible}:
      note = C.note("TIE_BAND_COUNTED_ONCE")
      lead = ("The drawing prints a roof band detail and also a tie band at lintel level over the same walls. They are one band here, the roof band at slab level, so the same wall is not listed twice; "
        if roof_band_read else "The drawing prints a tie band at lintel level over the same walls as the roof beam. The roof band was not read on this sheet (it was prepared before pack 44; prepare the drawing again), so the roof beam is taken as the one band and the tie band is not listed again; ")
      note["message"] = lead + "the lintels over the openings are listed as before. " + head[0].upper() + head[1:] + ". Choose 'Band and beam' under Decisions to list the tie band as well."
      c.notes.append(note)
      
      if roof_band:
        c.facts["band_detail"] = {"text": roof_band.get("text"), "binding": roof_band.get("binding"), "pages": roof_band.get("pages")}
        c.notes.append(C.note("ROOF_BAND_DETAIL"))
    elif role == "BAND" and member == "TIE_BAND":
      note = C.note("TIE_BAND_COUNTED_ONCE")
      note["message"] = ("The drawing prints a tie band at lintel level and no roof band detail. The tie band is the one band member over the walls it covers, so the roof beam derived over the same walls is not "
        "listed as well; the lintels over the openings are listed as before and the band runs over the solid wall only. " + head[0].upper() + head[1:] + ". Choose 'Band and beam' under Decisions to list both.")
      
      c.notes.append(note)
    elif role == "BAND" and member == "BOTH":
      note = C.note("TIE_BAND_COUNTED_SEPARATELY")
      note["message"] = ("The tie band at lintel level is listed beside the roof beam, over the solid wall only (the lintels stand where the openings are, and a 4.5 in partition carries no band). " + head[0].upper() + head[1:] + ".")
      c.notes.append(note)
  return keep, rec
