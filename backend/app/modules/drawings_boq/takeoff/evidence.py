from __future__ import annotations

PRINTED, VERIFIED, CONFIRMED, PICTURE, MEASURED, ASSUMED, MISSING, NOT_READ = ("PRINTED", "VERIFIED", "CONFIRMED", "PICTURE", "MEASURED", "ASSUMED", "MISSING", "NOT_READ")
TIER = {PRINTED: 0, VERIFIED: 0, CONFIRMED: 0, PICTURE: 1, MEASURED: 1, ASSUMED: 2, MISSING: 3}
GRADES = ("PRINTED", "MEASURED", "ASSUMED", "MISSING")
GRADE_TEXT = {
  "PRINTED": "Every value is printed on the drawing, checked against a printed value, or confirmed by you.",
  "MEASURED": "At least one value is measured from the drawing's lines or read from a detail picture. Nothing is assumed or missing.",
  "ASSUMED": "At least one value was paired, defaulted or is disputed on the drawing. Check it.",
  "MISSING": "At least one value is not on the drawing. Type it when you accept the item.",
}

def _codes(cand) -> set:
  return {n.get("code") for n in (cand.notes or [])}

def _value(params: dict, key: str):
  v = (params or {}).get(key)
  try:
    f = float(v)
  except (TypeError, ValueError):
    return None
  return f if f == f else None

class _Inputs:
  def __init__(self, codes: set):
    self.codes = codes
    self.items: list = []
    self.unverified = bool({"SCALE_UNVERIFIED", "VIEW_SCALE_DIFFERS"} & codes)

  def add(self, name: str, basis: str, how: str) -> None:
    self.items.append({"name": name, "basis": basis, "how": how})

  def measured(self, name: str, how: str) -> None:
    """A value taken from the drawn lines is only as good as the scale of the sheet."""
    if self.unverified:
      self.add(name, ASSUMED, how + "; the scale of this sheet is not checked against a printed dimension")
    else:
      self.add(name, MEASURED, how)

  def height(self, name: str, value, section_how: str = "clear storey height printed on the building section") -> None:
    if value is None:
      self.add(name, MISSING, "not on the drawing")
    elif "HEIGHT_FROM_SECTION" in self.codes:
      self.add(name, PRINTED, section_how)
    elif "HEIGHT_FROM_NOTE" in self.codes:
      self.add(name, PRINTED, "from a note on the drawing")
    else:
      self.add(name, CONFIRMED, "typed by you")

def _count(inp: _Inputs, cand) -> None:
  codes = inp.codes
  f = cand.facts or {}
  if "UNMARKED_COLUMNS" in codes:
    inp.add("count", ASSUMED, "black squares with no mark beside them, counted by their size")
  elif "UNTAGGED_SAME_SIZE" in codes:
    inp.add("count", ASSUMED, f"{f.get('same_size_marks')} marks but {f.get('same_size_drawn')} shapes of this size are drawn; the marks are used")
  elif "COUNT_DIFFERS_FROM_DRAWN" in codes:
    inp.add("count", ASSUMED, f"{f.get('same_size_marks')} marks but only {f.get('same_size_drawn')} shapes drawn; the marks are used")
  elif "COUNT_MATCHES_OTHER_FLOOR" in codes:
    inp.add("count", PRINTED, "marks counted on the sheet; the same marks and number appear on another floor where every column is drawn")
  else:
    inp.add("count", PRINTED, "marks counted on the sheet")

def _size(inp: _Inputs, cand) -> None:
  codes = inp.codes
  f = cand.facts or {}
  has = bool(f.get("size_used_mm"))
  if not has:
    inp.add("size", MISSING, "no size on the drawing")
  elif "SIZE_FROM_SCHEDULE" in codes:
    inp.add("size", PRINTED, "from the schedule on the drawing")
  elif "COLUMN_DETAILS_DISAGREE" in codes:
    inp.add("size", ASSUMED, "two details of this mark show different sizes, so the plan square is used")
  elif "SIZE_FROM_COLUMN_DETAIL" in codes:
    inp.add("size", PICTURE, "written beside the column detail as strokes, read from the picture")
  elif "FOOTING_SIZE_ORDER_ASSUMED" in codes:
    inp.add("size", ASSUMED, "the footing details print the sizes but not which mark each belongs to; paired in order")
  elif "SIZE_FROM_DETAIL" in codes:
    inp.add("size", PRINTED, "printed under the footing section detail")
  elif "SIZE_VARIES" in codes:
    inp.add("size", ASSUMED, "the shapes drawn for this mark are not all the same size")
  elif "SIZE_FROM_OTHER_VIEW" in codes:
    inp.measured("size", "measured from the same mark on another plan")
  else:
    inp.measured("size", "measured from the black square on the plan (a symbol)")

def _slab(inp: _Inputs, cand) -> None:
  """A slab is the covered area of its floor as printed in the area table, with the thickness of the slab note: no value is measured from the lines."""
  f, params, codes = cand.facts or {}, cand.params or {}, inp.codes
  pages = ", ".join(str(x) for x in (f.get("area_pages") or []))
  
  if f.get("dims_mm"):
    inp.add("size", PRINTED, f"length and width printed in the area table{' (sheet ' + pages + ')' if pages else ''}, and their product agrees with the printed area")
  elif f.get("area_m2") is not None:
    inp.add("size", MISSING, "the area table prints the covered area but not its length and width")
  else:
    inp.add("size", MISSING, "no covered area for this floor on the drawing")
  proj = f.get("projections") or {}
  if proj.get("applied"):
    sides = proj.get("sides") or {}
    shown = ", ".join(f"{k.lower()} {v / 304.8:g} ft" for k, v in sorted(sides.items()))
    inp.measured("projections", f"roof projection widths printed on the floor plan ({shown}); which side each belongs to is read from where its label sits")
  elif proj:
    inp.add("projections", ASSUMED, "the plan prints roof projections but they could not be placed on a side, so the slab is the covered area only")
  else:
    inp.add("projections", NOT_READ, "no roof projection is printed on the plans of this floor, so the slab is the covered area only")
  t = _value(params, "depth_mm")
  if t is None:
    if "SLAB_THICKNESSES_LISTED" in codes:
      inp.add("thickness", MISSING, "the drawing prints more than one slab thickness and this plan has no slab note")
    else:
      inp.add("thickness", MISSING, "no slab thickness on the drawing")
  elif f.get("thickness_source") == "TYPED":
    inp.add("thickness", CONFIRMED, f"{t / 25.4:g}\" typed by you")
  elif "SLAB_THICKNESS_DISAGREES" in codes:
    note = next((n for n in (cand.notes or []) if n.get("code") == "SLAB_THICKNESS_DISAGREES"), {})
    other = ", ".join(f"{o['mm'] / 25.4:g}\"" for o in (note.get("others") or []) if o.get("mm"))
    sections = f"; the building sections imply {note['sections_mm'] / 25.4:g}\"" if note.get("sections_mm") else ""
    inp.add("thickness", ASSUMED, f"the slab note on the plan says {t / 25.4:g}\" but another sheet prints {other}{sections}; the plan note is used")
  elif f.get("thickness_source") == "OTHER_SHEET":
    inp.add("thickness", PRINTED, "this plan has no slab note; the one thickness the drawing prints elsewhere is used")
  else:
    inp.add("thickness", PRINTED, "the slab note on the framing plan")
  inp.add("openings", NOT_READ, "stair wells and shafts in the slab are not deducted; type them as a deduction on the measurement")

def _beam_from_walls(inp: _Inputs, cand) -> None:
  """A beam over the walls of a floor is not drawn: it is the measured brick walls laid end to end, as wide as the wall, with a depth the drawing's beam
  sections print but the reader does not take, so it is typed."""
  f, params = cand.facts or {}, cand.params or {}
  t = f.get("wall_thickness_mm") or 0.0
  inp.measured("length", f"{f.get('wall_count', 0)} brick walls of {t / 25.4:g} in measured on this floor, laid end to end ({f.get('length_m', 0):g} m, openings included)")
  inp.measured("width", "as wide as the wall: the measured wall thickness snapped to a standard size")
  if _value(params, "depth_mm") is None:
    inp.add("depth", MISSING, "the beam section printed on the drawing is not read; type the depth when you accept the beam")
  else:
    inp.add("depth", CONFIRMED, "typed by you")
  inp.add("position", ASSUMED, "a beam is assumed on top of every brick wall; the plan does not draw it")

def _lintel(inp: _Inputs, cand) -> None:
  """A lintel is the opening's schedule width, the section of the lintel table printed on the drawing, and a bearing at each end that the drawing does not print."""
  f, params, codes = cand.facts or {}, cand.params or {}, inp.codes
  inp.add("count", PRINTED, "opening marks counted on the sheet")
  
  if _value(params, "depth_mm") is None:
    inp.add("section", MISSING, "the opening is wider than every row of the lintel table")
  else:
    pages = ", ".join(str(x) for x in (f.get("table_pages") or []))
    inp.add("section", PRINTED, f"row of the lintel table{' (sheet ' + pages + ')' if pages else ''} for a span up to {f.get('table_span_max_mm', 0) / 304.8:g} ft")
  bearing = f.get("bearing_mm")
  inp.add("length", ASSUMED, f"opening width from the schedule plus {bearing / 25.4:g}\" bearing at each end; the drawing prints no bearing" if bearing else "the drawing prints no bearing")
  if "LINTEL_IN_THIN_WALL" in codes:
    inp.add("host wall", ASSUMED, "some of these openings sit in 4.5 inch walls and the table section is 9 inches wide")

def _stair(inp: _Inputs, cand) -> None:
  """A stair is the riser, tread, width and number of steps printed on the drawing. The waist slab under the steps is rarely printed, and landings are not included."""
  f, params = cand.facts or {}, cand.params or {}
  inp.add("count", PRINTED, "staircases named on the plan")
  if _value(params, "depth_mm") is None:
    inp.add("size", MISSING, "the drawing does not print all of riser, tread, width and number of steps")
    return
  pages = ", ".join(str(x) for x in (f.get("stair_pages") or []))
  inp.add("steps, riser, tread, width", PRINTED, f"printed on the drawing{' (sheet ' + pages + ')' if pages else ''}: {f.get('stair_text')}")
  if f.get("waist_source") == "PRINTED":
    inp.add("waist slab", PRINTED, f"{f.get('waist_mm', 0):g} mm printed on the drawing")
  else:
    inp.add("waist slab", ASSUMED, f"the drawing prints no waist thickness; {f.get('waist_mm', 0):g} mm assumed")
  inp.add("landings", NOT_READ, "not included in this quantity; measure them as slabs")

def evidence_for(cand) -> dict:
  """{"grade", "inputs": [{"name", "basis", "how"}], "ask": [what to check or type]} for one candidate."""
  codes = _codes(cand)
  inp = _Inputs(codes)
  cat = cand.category
  params, facts = cand.params or {}, cand.facts or {}
  
  if cat in ("COLUMN", "FOOTING"):
    _count(inp, cand)
    _size(inp, cand)
    inp.height("height" if cat == "COLUMN" else "depth", _value(params, "depth_mm"))
  elif cat == "BEAM" and facts.get("derived_from") == "WALLS":
    _beam_from_walls(inp, cand)
  elif cat == "BEAM":
    _count(inp, cand)
    inp.add("length", NOT_READ, "beam marks are counted only; the length is not read yet")
  elif cat == "SLAB":
    _slab(inp, cand)
  elif cat == "LINTEL":
    _lintel(inp, cand)
  elif cat == "STAIR":
    _stair(inp, cand)
  elif cat in ("DOOR", "WINDOW"):
    inp.add("count", PRINTED, "marks counted on the sheet")
    if "SIZE_FROM_SCHEDULE" in codes:
      inp.add("size", PRINTED, "from the schedule on the drawing")
    elif "SCHEDULE_MARK_NOT_FOUND" in codes:
      inp.add("size", MISSING, "the mark is not in the schedule")
    else:
      inp.add("size", NOT_READ, "no schedule on the drawing")
  elif cat == "WALL":
    inp.measured("length", "centre line measured from the drawn wall")
    if "THICKNESS_OFF_STANDARD" in codes:
      inp.add("thickness", ASSUMED, "the drawn thickness is not a standard wall size")
    else:
      inp.measured("thickness", "measured from the drawn wall and snapped to a standard size")
    inp.height("height", _value(params, "height_mm"))
    
  elif cat == "ROOM":
    from_label = facts.get("outline_from") == "LABEL"
    if "ROOM_INSIDE_ROOM" in codes:
      inp.add("area", ASSUMED, "this room lies inside another room's outline, so its area is counted twice")
    elif "ROOM_SIZE_MISMATCH" in codes or "ROOM_FROM_OUTLINE" in codes:
      inp.add("area", ASSUMED, "the outline and the printed size disagree" if "ROOM_SIZE_MISMATCH" in codes else "taken from a drawn outline, not from the wall layout")
    elif from_label:
      inp.add("area", PRINTED, "the size printed in the room label")
    elif facts.get("label_area_m2") is not None and facts.get("deviation_pct") is not None:
      inp.add("area", VERIFIED, f"measured inside the walls; the printed area agrees within {abs(facts['deviation_pct']):.1f}%")
    else:
      inp.measured("area", "measured inside the walls; no printed area to check it against")
    if "ROOM_NO_LABEL" in codes:
      inp.add("name", MISSING, "no room name inside this outline")
    elif "ROOM_MULTIPLE_LABELS" in codes:
      inp.add("name", ASSUMED, "more than one room name inside this outline")
    else:
      inp.add("name", PRINTED, "the room label")
  else:
    inp.add("count", PRINTED, "marks counted on the sheet")
    
  if cand.decision == "ACCEPTED":
    for it in inp.items:
      if it["basis"] in (ASSUMED, MISSING):
        it["how"] = "confirmed by you (was: " + it["how"] + ")"
        it["basis"] = CONFIRMED
        
  graded = [TIER[i["basis"]] for i in inp.items if i["basis"] in TIER]
  grade = GRADES[max(graded)] if graded else "PRINTED"
  ask = [f"{i['name']}: {i['how']}" for i in inp.items if i["basis"] in (ASSUMED, MISSING)]
  return {"grade": grade, "inputs": inp.items, "ask": ask}

def tally(rows: list) -> dict:
  """{"PRINTED": n, "MEASURED": n, "ASSUMED": n, "MISSING": n} over register rows (each a dict with properties._pdf.evidence)."""
  out = {g: 0 for g in GRADES}
  for r in rows:
    ev = (((r.get("properties") if isinstance(r, dict) else getattr(r, "properties", None)) or {}).get("_pdf") or {}).get("evidence")
    if ev and ev.get("grade") in out:
      out[ev["grade"]] += 1
  return out