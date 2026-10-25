from __future__ import annotations
from app.modules.drawings_boq.takeoff.ranges import range_for

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

QS_INPUTS = (
  ("FOOTING_DEPTH_QS", "footing depth"),
  ("NECK_HEIGHT_ASSUMED", "neck column height"),
  ("HEIGHT_FROM_QS", "height"),
  ("TANK_SLABS_QS", "tank slab thicknesses"),
  ("SITE_WALL_QS_ESTIMATE", "boundary wall thickness"),
)

def from_qs(cand) -> list:
  """The inputs of a row that come from the QS's workbook and not from the drawing, as short names. A height printed on the building section or in a note wins, so it is not listed."""
  if getattr(cand, "decision", None) == "ACCEPTED":
    return []
  codes = _codes(cand)
  printed_height = bool({"HEIGHT_FROM_SECTION", "HEIGHT_FROM_NOTE"} & codes)
  return [name for code, name in QS_INPUTS if code in codes and not (code == "HEIGHT_FROM_QS" and printed_height)]

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

  def height(self, name: str, value, section_how: str = "storey height printed on the drawing (building section or room notes)") -> None:
    if value is None:
      self.add(name, MISSING, "not on the drawing")
    elif "NECK_HEIGHT_ASSUMED" in self.codes:
      self.add(name, ASSUMED, "the height is not printed on the drawing; the QS's workbook height for the neck columns is used (type another to override it)")
    elif "FOOTING_DEPTH_QS" in self.codes:
      self.add(name, ASSUMED, "the footing thickness is not printed as a figure; the QS's footing depth is used")
    elif "HEIGHT_FROM_SECTION" in self.codes:
      self.add(name, PRINTED, section_how)
    elif "HEIGHT_FROM_NOTE" in self.codes:
      self.add(name, PRINTED, "from a note on the drawing")
    elif "HEIGHT_FROM_QS" in self.codes:
      self.add(name, ASSUMED, "the height is not printed on the drawing; the QS's workbook height (S1, S5) is used (type another to override it)")
    else:
      self.add(name, CONFIRMED, "typed by you")

def _count(inp: _Inputs, cand) -> None:
  codes = inp.codes
  f = cand.facts or {}
  if "UNMARKED_COLUMNS" in codes:
    inp.add("count", ASSUMED, "black squares or circles with no mark beside them, counted by their size")
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
  elif "FOOTING_SIZE_PAIRED" in codes:
    inp.add("size", ASSUMED, "the footing details print the sizes but not which mark each belongs to; the larger column's footing takes the larger pad")
  elif "FOOTING_SIZE_BY_ELIMINATION" in codes:
    inp.add("size", ASSUMED, "the size the footing marks do not use is taken for the stair footing")
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
    inp.measured("projections", f"roof projection widths printed on the floor plan ({shown}); each is bound to the overall length printed beside it and checked against its side of the plan outline")
  elif proj and proj.get("strips"):
    left = ", ".join(f"{s['side'].lower()} {s['width_mm'] / 304.8:g} ft ({s['status'].lower().replace('_', ' ')})" for s in proj["strips"])
    inp.add("projections", ASSUMED, f"the plan prints roof projections but none could be added to the slab ({left}), so the slab is the covered area only")
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
  elif f.get("thickness_source") == "CHOSEN":
    printed = ", ".join(f"{o['mm'] / 25.4:g}\"" for o in (f.get("thickness_options") or []) if o.get("mm"))
    inp.add("thickness", CONFIRMED, f"{t / 25.4:g}\" chosen by you between the thicknesses the drawing prints ({printed})")
  elif f.get("thickness_source") == "POLICY":
    pol = (f.get("conflict") or {}).get("policy") or "the policy"
    printed = ", ".join(f"{o['mm'] / 25.4:g}\"" for o in (f.get("thickness_options") or []) if o.get("mm"))
    inp.add("thickness", ASSUMED, f"{t / 25.4:g}\" taken by the {pol.lower()} policy between the thicknesses the drawing prints ({printed}); choose one to confirm it")
  elif "SLAB_THICKNESS_DISAGREES" in codes:
    note = next((n for n in (cand.notes or []) if n.get("code") == "SLAB_THICKNESS_DISAGREES"), {})
    other = ", ".join(f"{o['mm'] / 25.4:g}\"" for o in (note.get("others") or []) if o.get("mm"))
    sections = f"; the building sections imply {note['sections_mm'] / 25.4:g}\"" if note.get("sections_mm") else ""
    if f.get("thickness_source") == "SECTION_LABEL":
      inp.add("thickness", ASSUMED, f"the plan's general slab note says {note['plan_mm'] / 25.4:g}\" but the sections of the drawing label {t / 25.4:g}\"{sections}; the label is used, type another thickness to override")
    else:
      inp.add("thickness", ASSUMED, f"the slab note on the plan says {t / 25.4:g}\" but another sheet prints {other}{sections}; the plan note is used")
  elif f.get("thickness_source") == "OTHER_SHEET":
    inp.add("thickness", PRINTED, "this plan has no slab note; the one thickness the drawing prints elsewhere is used")
  else:
    inp.add("thickness", PRINTED, "the slab note on the framing plan")
  opens = f.get("openings") or []
  if not opens:
    inp.add("openings", NOT_READ, "no stair well, shaft or duct was found for this slab on the floor plans; type any as a deduction on the measurement")
  else:
    big = [o for o in opens if o.get("deduct")]
    wells = [o for o in big if o.get("kind") == "STAIR_WELL"]
    named = ", ".join(f"{o['name']} {o['area_m2']:.2f} m2" for o in big) or "none"
    small = f"; {len(opens) - len(big)} of 0.1 m2 or less left in (IS 1200 Part 2 cl. 4.1.6)" if len(big) < len(opens) else ""
    text = f"taken off: {named}{small}"
    if wells:
      inp.measured("openings", f"{text}. A stair well is the area the treads drawn cover on the plan, so a stair drawn short of its cut line takes off less than the well")
    else:
      inp.add("openings", PRINTED, f"{text}. Sizes are printed on the floor plans")

def _depth_choice_text(choice: dict) -> str:
  return f"the section of this mark prints no depth that could be read; {choice.get('mm', 0) / 25.4:g}\" was chosen by a person from the depth printed for {', '.join(choice.get('from') or [])}"

def _beam_from_walls(inp: _Inputs, cand) -> None:
  f, params = cand.facts or {}, cand.params or {}
  t = f.get("wall_thickness_mm") or 0.0
  inp.measured("length", f"{f.get('wall_count', 0)} brick walls of {t / 25.4:g} in measured on this floor, laid end to end ({f.get('length_m', 0):g} m, openings included)")
  inp.measured("width", "as wide as the wall: the measured wall thickness snapped to a standard size")
  if _value(params, "depth_mm") is None:
    inp.add("depth", MISSING, "the beam section printed on the drawing is not read; type the depth when you accept the beam")
  elif f.get("depth_choice"):
    inp.add("depth", ASSUMED, _depth_choice_text(f["depth_choice"]))
  else:
    inp.add("depth", CONFIRMED, "typed by you")
  inp.add("position", ASSUMED, "a beam is assumed on top of every brick wall; the plan does not draw it")

def _beam_from_strips(inp: _Inputs, cand) -> None:
  f, params = cand.facts or {}, cand.params or {}
  gross = f.get("length_gross_m", f.get("length_m", 0))
  cut = f", less the width of {f['columns_taken']} columns: {f.get('length_m', 0):g} m between column faces" if f.get("columns_taken") else ""
  inp.measured("length", f"{f.get('strip_count', 0)} hatched strips measured along their centre line ({gross:g} m, corners counted once){cut}")
  inp.measured("width", "the width of the hatched strip" + (", taken to a whole number of inches" if f.get("beam_width_mm") else ""))
  if "BEAM_STRIP_MARK_FROM_NEIGHBOUR" in inp.codes:
    inp.add("mark", ASSUMED, "some strips have no mark beside them and take the mark of the beam they carry on")
  if "BEAM_STRIP_NO_MARK" in inp.codes:
    inp.add("mark", MISSING, "no beam mark is written beside these strips")
  if _value(params, "depth_mm") is None:
    inp.add("depth", MISSING, "no section with this mark gives a depth; type it when you accept the beam")
  elif f.get("section_mark"):
    inp.add("depth", PICTURE, f"read from the picture of the beam section {f['section_mark']}")
  elif f.get("depth_choice"):
    inp.add("depth", ASSUMED, _depth_choice_text(f["depth_choice"]))
  else:
    inp.add("depth", CONFIRMED, "typed by you")

def _lintel(inp: _Inputs, cand) -> None:
  """A lintel is the opening's schedule width, the section of the lintel table printed on the drawing, and a bearing at each end that the drawing does not print."""
  f, params, codes = cand.facts or {}, cand.params or {}, inp.codes
  split = f.get("split") or {}
  inp.add("count", PRINTED, "opening marks counted on the sheet" + (f", {split['in_rcc_left_out']} in RCC walls left out" if split.get("in_rcc_left_out") else ""))
  
  if _value(params, "depth_mm") is None:
    inp.add("section", MISSING, "the opening is wider than every row of the lintel table")
  else:
    pages = ", ".join(str(x) for x in (f.get("table_pages") or []))
    inp.add("section", PRINTED, f"row of the lintel table{' (sheet ' + pages + ')' if pages else ''} for a span up to {f.get('table_span_max_mm', 0) / 304.8:g} ft")
  bearing = f.get("bearing_mm")
  inp.add("length", ASSUMED, f"opening width from the schedule plus {bearing / 25.4:g}\" bearing at each end; the drawing prints no bearing" if bearing else "the drawing prints no bearing")
  if "LINTEL_IN_THIN_WALL" in codes:
    inp.add("host wall", ASSUMED, "some of these openings sit in 4.5 inch walls and the table section is 9 inches wide")
  if "LINTEL_WIDTH_FROM_WALL" in codes:
    inp.add("width", ASSUMED, f"as wide as the {(f.get('section_mm') or [0])[0] / 25.4:g} inch wall these openings stand in, not the {(f.get('table_section_mm') or [0])[0] / 25.4:g} inch of the table; the drawing prints no lintel width for thin walls")

def _stair(inp: _Inputs, cand) -> None:
  """A stair is the riser, tread, width and number of steps printed on the drawing. The waist slab under the steps is rarely printed, and landings are not included."""
  f, params = cand.facts or {}, cand.params or {}
  inp.add("count", PRINTED, "staircases named on the plan")
  if _value(params, "depth_mm") is None:
    inp.add("size", MISSING, "the drawing does not print all of riser, tread, width and number of steps")
    return
  pages = ", ".join(str(x) for x in (f.get("stair_pages") or []))
  where = f" (sheet {pages})" if pages else ""
  if f.get("width_source") == "PRINTED_BESIDE":
    inp.add("steps, riser, tread", PRINTED, f"printed on the drawing{where}: {f.get('steps')} steps, riser {f.get('riser_mm', 0):g} mm, tread {f.get('tread_mm', 0):g} mm")
    inp.add("width", PRINTED, f"{f.get('stair_width_mm', 0):g} mm printed beside this flight on the plan; the stair detail gives {f.get('detail_width_mm', 0):g} mm for the main stair")
  else:
    inp.add("steps, riser, tread, width", PRINTED, f"printed on the drawing{where}: {f.get('stair_text')}")
  if f.get("waist_source") == "PRINTED":
    inp.add("waist slab", PRINTED, f"{f.get('waist_mm', 0):g} mm printed on the drawing")
  else:
    inp.add("waist slab", ASSUMED, f"the drawing prints no waist thickness; {f.get('waist_mm', 0):g} mm assumed")
  if f.get("landings"):
    sizes = ", ".join(l["text"] for l in f["landings"])
    inp.add("landings", PRINTED, f"{len(f['landings'])} printed beside this stair ({sizes}); added as flat slabs of the waist thickness")
  else:
    inp.add("landings", NOT_READ, "no landing size is printed beside this stair, so none is included; measure the landings as slabs")

def _site(inp: _Inputs, cand) -> None:
  """An item outside the building: its label or caption is on the sheet; a size is printed on the elevation, or it is missing and typed. Nothing is measured from lines."""
  f, params, codes = cand.facts or {}, cand.params or {}, inp.codes
  kind = f.get("site_kind")
  sizes = f.get("sizes_mm") or {}
  inp.add("count", PRINTED, "label or caption on the sheet" + (f" (written {f['labels_on_sheet']} times on the sheet; one item)" if f.get("labels_on_sheet", 1) > 1 else ""))
  def typed(token: str, name: str, value) -> None:
    if value is None:
      inp.add(name, MISSING, "not printed on the drawing in a form the reader takes")
    else:
      inp.add(name, CONFIRMED, f"{value / 25.4:g}\" typed by you")
  if kind in ("OHWT", "UGWT", "SEPTIC"):
    listed = f.get("tank_drawings")
    if listed:
      inp.add("tank drawings", PICTURE if any(any(x for x in d.get("sizes") or []) for d in listed) else NOT_READ, "the sizes the tank drawings print are listed with the item; none is applied because the drawing does not say which is the outside size and which the wall")
    said = f.get("sizes_assumed") or {}
    for token, name in (("length_mm", "outside length"), ("width_mm", "outside width"), ("height_mm", "outside height"), ("thickness_mm", "wall and slab thickness")):
      if token in said and sizes.get(token):
        inp.add(name, ASSUMED, f"{sizes[token] / 25.4:g}\" worked out from the tank drawings: {said[token]}")
      else:
        typed(token, name, sizes.get(token))
    if f.get("tank_slabs_mm"):
      inp.add("slabs", ASSUMED, "the top and bottom slab are as thick as the section prints them (the thickness read most often); not the QS's 8 in")
    elif all(sizes.get(t) for t in ("length_mm", "width_mm", "height_mm", "thickness_mm")):
      inp.add("slabs", ASSUMED, "the top and bottom slab are taken as thick as the walls")
  elif kind == "BOUNDARY_WALL":
    pieces = f.get("pieces_mm") or []
    if pieces:
      inp.add("length", PRINTED, f"the pieces of the elevation add up to the printed overall length {f.get('overall_text')}" + ("; the gate piece is taken out" if f.get("gate_deducted") else ""))
    elif f.get("overall_mm"):
      inp.add("length", ASSUMED, f"the overall length {f.get('overall_text')} is printed but no row of dimensions adds up to it, so the gate could not be taken out")
    else:
      inp.add("length", MISSING, "no overall length on the drawing")
    if f.get("height_mm") is None:
      inp.add("height", MISSING, "no height printed on the elevation")
    elif f.get("height_pick") == "NEAREST":
      inp.add("height", ASSUMED, "the elevation prints more than one height; the one nearest to the wall pieces is used")
    else:
      inp.add("height", PRINTED, "the height printed on the elevation")
      typed("thickness_mm", "thickness", sizes.get("thickness_mm"))
    inp.add("piers", ASSUMED, "piers taller than the wall are measured at the wall height")
    if f.get("faces_area_mm2"):
      inp.add("faces", ASSUMED, f"a free-standing wall has two faces: {f['faces_area_mm2'] / 1e6:.2f} m2 of plaster and paint on the front wall if both are finished (length x height x 2, gate taken out); "
        "they are the boundary wall plaster and paint items, which also take the side and rear walls, because the drawing does not say which faces are finished")
  elif kind == "GATE":
    inp.add("width", PRINTED, "the piece of the elevation the word GATE is written on, " + (f"{f.get('width_mm', 0) / 304.8:g} ft" if f.get("width_mm") else "not found"))
    if f.get("height_mm") is None:
      inp.add("height", MISSING, "no height printed on the elevation")
    elif f.get("height_pick") == "NEAREST":
      inp.add("height", ASSUMED, "the elevation prints more than one height; the one nearest to the gate is used")
    else:
      inp.add("height", PRINTED, "the height printed on the elevation")
  elif kind == "PORCH_RAMP":
    for token, name in (("length_mm", "length"), ("width_mm", "width"), ("thickness_mm", "slab thickness")):
      typed(token, name, sizes.get(token))
    levels = f.get("levels_printed") or []
    inp.add("levels", NOT_READ if not levels else PRINTED, "levels printed on the section: " + ", ".join(levels) if levels else "no level printed on the section")

DERIVED_ASSUMED = (
  ("DOOR_WIDTH_ASSUMED", "door width", "some doors have no width on the plan or in a schedule; 900 mm is used for them"),
  ("OPENING_HEIGHT_ASSUMED", "opening height", "the plan prints no height for some openings; the usual height of a door or window is used"),
  ("DADO_HEIGHT_DEFAULT", "dado height", "the 7 ft dado height is the default of the finish rules, not printed on the drawing"),
  ("WINDOW_SILL_ASSUMED", "window sill", "some windows print no sill level; a usual sill is assumed"),
  ("WET_TURNUP_DEFAULT", "turn-up height", "the 300 mm turn-up of the waterproofing is usual practice, not printed on the drawing"),
  ("TRENCH_WORKING_SPACE_ASSUMED", "working space", "the drawing prints no working space beside the concrete bed; 3 inches a side is used"),
  ("ARCH_CENTRING_FROM_SCHEDULE", "arch shape", "the schedule says the opening is arched but not how high the arch rises; a semicircle is used, and the wall thickness is read from the walls the opening stands in, else 9 in"),
  ("TRENCH_DEPTH_ASSUMED", "trench depth", "no footing section was found for these walls; the QS workbook's 3 ft trench is used"),
  ("EXCAVATION_DEPTH_ASSUMED", "excavation depth", "the plans print no depth for the dig over the basement; the QS workbook's 8 ft is used"),
  ("FILL_DEPTH_ASSUMED", "filling depth", "the plans print no depth of filling; 1.5 ft, the usual filling up to the plinth, is used"),
  ("BRICK_STEPS_ASSUMED", "brick steps", "the steps of the brick foundation are drawn as dimension lines that cannot be read; usual steps are used"),
  ("FOOTING_DEPTH_QS", "footing depth", "the footing thickness is not printed as a figure; the QS's depth is used"),
  ("PCC_PAD_DEPTH_FROM_STRIP_SECTION", "bed thickness", "the column footing sections print the bed thickness as a dimension line that cannot be read; the bed under the wall footing section is used"),
  ("DOOR_FRAME_WIDTH_FROM_WALL", "frame width", "the drawing prints no frame section; the frame is taken as wide as the wall the doors stand in"),
  ("TANK_SIZES_DERIVED", "tank sizes", "the tank drawings print lengths without saying which is which; the sizes are worked out from them and listed with the item"),
  ("RAIN_PIPE_COUNT_ASSUMED", "pipe count", "one pipe is taken for each label on the sheet; the label does not say how many outlets it stands for"),
  ("PILE_UNIT_ASSUMED", "pile units", "a figure of the pile has no unit written; a diameter below 100 is taken as inches, a length with no unit as metres"),
  ("RAFT_FOOTPRINT_FROM_AREA_TABLE", "raft outline", "the raft is not dimensioned; the covered area of the lowest floor in the area table is used"),
  ("RAFT_PCC_ASSUMED", "bed thickness", "the drawing prints no bed under the raft; the QS workbook's 3 in is used"),
  ("RAFT_EDGE_FORM_ASSUMED", "edge shuttering", "the shuttering is taken round the outline, as high as the raft is thick; usual practice, not printed"),
  ("RAFT_UNIT_ASSUMED", "raft thickness unit", "the thickness has no unit written; a figure below 100 is taken as inches"),
  ("RAIN_PIPE_DROP_ASSUMED", "pipe length", "the pipe is taken from the roof level down to the ground floor level of the building sections; the run to the drain is not drawn"),
  ("SCAFFOLD_ABOVE_THRESHOLD", "scaffolding height", "the height above which scaffolding is billed (3.6 m, 12 ft) is usual practice, not printed on the drawing; IS 1200 includes scaffolding in the rate of the work"),
  ("PROPS_ABOVE_THRESHOLD", "props height", "the clear height above which props are billed (3.6 m, 12 ft) and the step of 1 m of extra height are usual practice, not printed on the drawing; IS 1200 sets neither"),
  ("BOUNDARY_FACES_ASSUMED", "faces", "the drawing does not say which faces of the boundary wall are plastered and painted; both are taken, the side and rear walls at the height of the front wall"),
  ("BOUNDARY_RETURNS_ASSUMED", "side and rear walls", "the side and rear walls are not drawn; their lengths are typed, the two sides are taken as equal, and the height and thickness are those of the front wall"),
)

def _derived(inp: _Inputs, cand) -> None:
  """A finishing or foundation item worked out from other readings (rooms, walls, openings): its quantity is as good as those readings, and each value the rules assume is listed."""
  facts = cand.facts or {}
  source = facts.get("derived_from")
  if source == "SITE":
    inp.add("front wall", PRINTED if facts.get("front_printed") else ASSUMED,
      "the length and height of the front of the boundary wall as printed on the elevation" if facts.get("front_printed") else "the front of the boundary wall as read from the elevation (see that item for what was assumed)")
  elif source in ("OPENINGS", "DOORS"):
    inp.add("count", PRINTED, "marks counted on the sheet")
    if facts.get("size_source") in ("SCHEDULE", "LABEL"):
      inp.add("size", PRINTED, "from the schedule or the label written on the drawing")
    else:
      inp.measured("size", "the width and height of the doors and windows read on this plan")
  elif facts.get("drainage") == "RAIN_PIPE":
    inp.add("count", PRINTED, "pipe labels counted on the sheet")
    if facts.get("length_basis") == "LEVELS":
      inp.add("levels", PRINTED, "the roof level and the ground floor level printed on the building sections")
  elif facts.get("drainage") == "SEWER_PIPE":
    inp.add("pipe size", PRINTED if facts.get("diameter_in") else MISSING, "written on the label" if facts.get("diameter_in") else "the label does not write a size")
    inp.add("line", PRINTED, "the pipe line labelled on the sheet")
  elif facts.get("drainage") in ("DRAIN_MANHOLE", "INSPECTION_CHAMBER", "GULLY_TRAP"):
    inp.add("count", PRINTED, "chamber marks counted on the sheet")
  elif facts.get("foundation_item") in ("PILE_BORE", "PILE_CONCRETE"):
    inp.add("pile size and number", PRINTED, "the diameter, the length and the number written in the note or the pile schedule")
  elif facts.get("foundation_item") in ("RAFT_SLAB", "RAFT_PCC", "RAFT_EDGE_FORM"):
    inp.add("raft thickness", PRINTED, "the thickness written with the word raft on the sheet")
  elif facts.get("electrical"):
    if facts.get("counted_by") == "TEXT":
      inp.add("count", PRINTED, "the text tag of the symbol counted on the sheet")
    else:
      inp.measured("count", "the symbols that match the legend picture, counted on this plan")
  elif facts.get("staging") == "SCAFFOLD":
    inp.measured("outside face length", "the outer wall faces measured on this plan")
    inp.add("floor levels", PRINTED, "the level and the floor-to-floor height of this floor printed on the building section")
  elif facts.get("staging") == "PROPS":
    inp.add("slab area", PRINTED, "the covered area printed in the area table")
    inp.add("clear height", PRINTED, "the clear storey height printed on the building section")
  else:
    inp.measured("quantity", "worked out from the rooms, walls or footings measured on this plan")
    if facts.get("layer") and facts.get("spec_pages"):
      inp.add("printed layer", PRINTED, "the layer and its thickness or number of coats are printed in the specification block")
  for code, name, how in DERIVED_ASSUMED:
    if code in inp.codes:
      inp.add(name, ASSUMED, how)
  for need in getattr(cand, "missing", None) or []:
    inp.add(need.replace("_mm", "").replace("_", " "), MISSING, "not on the drawing; type it when you accept the item")

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
  elif cat == "BEAM" and facts.get("from_strips"):
    _beam_from_strips(inp, cand)
  elif cat == "BEAM":
    _count(inp, cand)
    inp.add("length", NOT_READ, "beam marks are counted only; the length is not read yet")
  elif cat == "SLAB":
    _slab(inp, cand)
  elif cat == "LINTEL":
    _lintel(inp, cand)
  elif cat == "STAIR":
    _stair(inp, cand)
  elif cat == "SITE":
    _site(inp, cand)
  elif cat in ("DOOR", "WINDOW"):
    inp.add("count", PRINTED, "marks counted on the sheet")
    if "SIZE_FROM_SCHEDULE" in codes:
      inp.add("size", PRINTED, "from the schedule on the drawing")
    elif "SCHEDULE_MARK_NOT_FOUND" in codes:
      inp.add("size", MISSING, "the mark is not in the schedule")
    else:
      inp.add("size", NOT_READ, "no schedule on the drawing")
  elif cat == "WALL" and facts.get("foundation_item") and facts.get("derived_from"):
    _derived(inp, cand)
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
    elif facts.get("outline_from") == "CLOSED" and facts.get("deviation_pct") is not None:
      inp.add("area", VERIFIED, f"measured inside the walls, joined across {(facts.get('closed_across') or {}).get('openings', 0)} door or window openings; the printed area agrees within {abs(facts['deviation_pct']):.1f}%")
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
  return {"grade": grade, "inputs": inp.items, "ask": ask, "range": range_for(cand, inp.items), "from_qs": from_qs(cand)}

def valid_on_assumption(rows: list) -> int:
  """Rows whose status is VALID although a value is assumed, disputed or missing (the grade of a row is its worst value)."""
  n = 0
  for r in rows:
    props = ((r.get("properties") if isinstance(r, dict) else getattr(r, "properties", None)) or {}).get("_pdf") or {}
    status = r.get("normalization_status") if isinstance(r, dict) else getattr(r, "normalization_status", None)
    if status == "VALID" and (props.get("evidence") or {}).get("grade") in (ASSUMED, MISSING):
      n += 1
  return n

def tally(rows: list) -> dict:
  """{"PRINTED": n, "MEASURED": n, "ASSUMED": n, "MISSING": n} over register rows (each a dict with properties._pdf.evidence)."""
  out = {g: 0 for g in GRADES}
  for r in rows:
    ev = (((r.get("properties") if isinstance(r, dict) else getattr(r, "properties", None)) or {}).get("_pdf") or {}).get("evidence")
    if ev and ev.get("grade") in out:
      out[ev["grade"]] += 1
  return out