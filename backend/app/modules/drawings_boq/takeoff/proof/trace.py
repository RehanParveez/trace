from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import scalegate as SG
from app.modules.drawings_boq.takeoff.extract import config as C

TUNED, STANDARD, DEFAULT = "TUNED", "STANDARD", "DEFAULT"

RULES = (
  ("SCALE_GATE", "Whether the printed scale, or the printed dimensions, set the scale of the sheet", TUNED, ("SCALE_UNVERIFIED", "VIEW_SCALE_DIFFERS", "SCALE_CONFLICT"), ("SG.MIN_DECLARED_TRUST", "SG.STRONG_CONFLICT_SUPPORT")),
  ("WALL_PEN", "Which line weights are walls and which are dimensions, furniture or boundary lines", TUNED, ("WALL_PEN_SELECTED", "LIGHT_PEN_WALLS_KEPT", "LIGHT_PEN_WALL"), ("WALL_T_MIN_MM", "WALL_T_MAX_MM", "WALL_MIN_FACE_MM", "WALL_MIN_OVERLAP_MM", "WALL_MIN_RUN_MM")),
  ("WALL_GAP_BRIDGE", "Walls carried across a gap where nothing is drawn (a door or window gap)", TUNED, ("WALL_BRIDGED", "WALL_WIDE_OPENING"), ("WALL_BRIDGE_MAX_MM", "WALL_GAP_MAX_MM", "WALL_GAP_CLEAR_MAX_MM", "WALL_STUB_MAX_MM")),
  ("OUTER_WALL_FILTER", "Lines outside the outer walls (dimension lines, projection outlines, plot lines) left out of the walls", TUNED, ("RUNS_OUTSIDE_PLAN_WALLS", "RUNS_OUTSIDE_CONCRETE_WALLS"), ("OUTER_CORE_MIN_MM", "OUTER_TOL_MM", "OUTER_WALL_TOL_FACTOR")),
  ("STAIR_TREADS", "Rows of short parallel lines taken as the treads of a stair, not as walls", TUNED, ("STAIR_TREADS_NOT_WALLS", "STAIR_LOCATED_BY_TREADS"), ("LADDER_MIN_RUNGS", "LADDER_MAX_STEP_MM", "LADDER_LENGTH_TOL", "LADDER_STEP_TOL", "STAIR_MIN_TREADS", "STAIR_TREAD_TOL")),
  ("VIEW_SPLIT", "A sheet that holds several drawings cut into plans and read plan by plan, with the floor each one is", TUNED, ("PLAN_REGIONS_READ", "FLOOR_READ_ON_OTHER_SHEET", "STRUCTURAL_SHEET", "SHEET_NOT_A_PLAN", "STAGE_FAILED"), ()),
  ("COLUMN_SHAPES", "Black squares and rectangles on a plan taken as columns, joined when close, sized into classes", TUNED, ("COLUMN_SHAPES_WITHOUT_MARK", "UNMARKED_COLUMNS", "COLUMN_FROM_FLOOR_ABOVE", "COLUMN_NOT_PLACED", "UNTAGGED_SAME_SIZE", "COUNT_DIFFERS_FROM_DRAWN",
    "COLUMN_MARKS_EXCEED_SHAPES", "COUNT_MATCHES_OTHER_FLOOR"), ("COLUMN_PIECE_MIN_MM", "COLUMN_PIECE_MAX_MM", "COLUMN_FILL_MIN", "COLUMN_JOIN_GAP_MM", "COLUMN_JOIN_ALIGN", "COLUMN_CLASS_TOL", "COLUMN_GRID_BIN_MM", "COLUMN_GRID_MIN_VOTES", "COLUMN_GRID_MIN_SHARE")),
  ("MEMBER_MATCH", "A mark on the plan matched to the shape drawn beside it", TUNED, ("MEMBER_MATCH_AMBIGUOUS", "SIZE_VARIES", "SIZE_NOT_FOUND", "COLUMN_SIZE_FROM_PLAN", "SIZE_FROM_OTHER_VIEW"), ("MEMBER_SEARCH_MM", "SIZE_TOL", "MEMBER_MIN_MM", "MEMBER_MAX_MM")),
  ("FOOTING_PAIRING", "Footing sizes printed on the details paired with footing marks (in order, when the details do not say)", TUNED, ("FOOTING_SIZE_ORDER_ASSUMED", "FOOTING_SIZES_LISTED", "SIZE_FROM_DETAIL"), ()),
  ("ROOM_OUTLINE", "A room taken from the walls round its label, or from the size printed in the label", TUNED, ("ROOM_FROM_OUTLINE", "ROOM_FROM_LABEL", "ROOM_OUTLINE_REPLACED", "ROOM_INSIDE_ROOM", "ROOM_NO_LABEL", "ROOM_MULTIPLE_LABELS", "ROOM_SIZE_MISMATCH"), ("ROOM_SIZE_TOL",)),
  ("BEAM_STRIPS", "Hatched strips on a framing plan taken as beams, with their length along the centre line", TUNED, ("BEAM_LENGTH_FROM_STRIPS", "BEAM_STRIP_MARK_FROM_NEIGHBOUR", "BEAM_STRIP_NO_MARK", "BEAM_MARK_WITHOUT_STRIP", "BEAM_STRIPS_OVERLAP_WALL_BEAMS"), ("STRIP_MAX_SEGMENTS", "BEAM_WIDTH_SNAP_TOL")),
  ("SLAB_THICKNESS", "Which slab thickness is taken when the plan note and the section labels differ", TUNED, ("SLAB_THICKNESS_DISAGREES", "SLAB_THICKNESS_SECTIONS", "SLAB_THICKNESS_FROM_OTHER_SHEET", "SLAB_THICKNESSES_LISTED"), ("SLAB_LABEL_MIN_COUNT", "SLAB_LABEL_SECTIONS_TOL_MM", "SLAB_SECTION_MIN_MM", "SLAB_SECTION_MAX_MM")),
  ("SLAB_PROJECTIONS", "Roof projections printed on the plans added to the covered area of the slab", TUNED, ("SLAB_PROJECTIONS_ADDED", "SLAB_PROJECTION_UNPLACED", "SLAB_PROJECTION_CONFLICT", "SLAB_PROJECTION_AXIS_UNKNOWN"), ()),
  ("OPENING_MARKS", "Door and window marks matched to the gaps in the walls they stand beside", TUNED, ("OPENINGS_ASSIGNED", "OPENING_GAP_IS_ANOTHER_MARK", "LINTEL_OVER_UNMARKED_OPENING"), ()),
  ("LINTELS", "Lintel sections, heads and the tie band that may replace them", TUNED, ("LINTEL_SECTION_FROM_TABLE", "LINTEL_HEAD_AT_DOOR", "LINTEL_HEAD_AT_COMMON_DOOR_HEAD", "LINTEL_COVERED_BY_TIE_BAND", "TIE_BAND_FROM_NOTE", "LINTEL_SPAN_ABOVE_TABLE", "LINTEL_IN_THIN_WALL"), ()),
  ("RCC_WALLS", "Solid black strips taken as concrete walls, and the closing of a ring drawn on three sides", TUNED, ("RCC_WALL_FROM_FILL", "RCC_WALL_COMPLETES_ENCLOSURE"), ()),
  ("SITE_ITEMS", "Tanks, boundary wall, gate and ramp read from labels, sections and elevations", TUNED, ("TANK_WALL", "TANK_SECTIONS_LISTED", "SITE_TANK_SIZES_TYPED", "SITE_TANK_SIZES_LISTED", "SITE_PIECES_DO_NOT_ADD_UP", "SITE_GATE_NOT_LOCATED", "SITE_GATE_TAKEN_OUT", "SITE_HEIGHT_NEAREST_DIMENSION"), ("TANK_REACH_MM", "TANK_MAX_MM")),
  ("ROOF_EDGE", "Parapet, coping, chajja, balcony and sunken-slab labels read from the roof plans", TUNED, ("ROOF_PARAPET_LENGTH_FROM_OUTLINE", "ROOF_BALCONY_MAY_BE_IN_SLAB", "ROOF_SUNK_FILL_NOTE", "ROOF_COPING_AS_LONG_AS_PARAPET"), ()),
  ("SLAB_OPENINGS", "Stair wells, ducts and shafts taken out of the slab they are in", TUNED, ("SLAB_OPENINGS_DEDUCTED", "SLAB_OPENING_SIZE_NOT_PRINTED", "STAIR_LANDINGS_ADDED"), ("VOID_LABEL_REACH_MM", "VOID_MIN_SIDE_MM", "LANDING_MIN_SIDE_MM", "STAIR_LANDING_REACH_MM")),
  ("WALL_THICKNESS", "A drawn wall thickness snapped to a standard size", STANDARD, ("THICKNESS_OFF_STANDARD",), ("STANDARD_TOL", "IMPERIAL_TOL")),
  ("SIZE_FROM_PRINT", "A size, a layer or a grade taken from a schedule, a detail or a note printed on the drawing", STANDARD, ("SIZE_FROM_SCHEDULE", "SIZE_DIFFERS_FROM_SCHEDULE", "COLUMN_PLAN_VS_DETAIL", "SIZE_FROM_COLUMN_DETAIL", "COLUMN_DETAILS_DISAGREE", "FLOOR_LAYER_FROM_SPEC", "FLOOR_LAYERS_LEFT_OUT", "FLOOR_LAYERS_AMBIGUOUS", "SPEC_VALUE_PRINTED_TWO_WAYS", "SPEC_GRADE_PRINTED", "SPEC_GRADE_CONFLICT", "MEMBRANE_LAYER_FROM_SPEC", "FLOOR_LAYER_UNDER_HEADING", "MEMBRANE_LAYER_UNDER_HEADING", "ROOF_LAYERS_FROM_SPEC", "OPENING_SIZE_FROM_PLAN_LABEL", "OPENING_HEIGHT_FROM_NOTE", "OPENING_LABEL_DIFFERS_FROM_SCHEDULE", "OPENING_LABELS_UNPAIRED"), ()),
  ("PICTURE_READING", "Text read from the picture of a sheet (a scan, a beam section or a tank drawing)", TUNED, ("SCAN_TEXT_READ", "SCAN_FIGURES_ASKED", "SCAN_FIGURES_REPAIRED", "BEAM_SECTION_FROM_DETAIL", "BEAM_SECTION_FROM_MARK"), ()),
  ("ASSUMED_VALUES", "A value used because the drawing prints none (stair waist, lintel bearing, trench working space, brick steps)", DEFAULT, ("STAIR_WAIST_ASSUMED", "LINTEL_BEARING_ASSUMED", "TRENCH_WORKING_SPACE_ASSUMED", "BRICK_STEPS_ASSUMED", "TERMITE_BOTTOM_ONLY"), ("STAIR_WAIST_DEFAULT_MM", "LINTEL_BEARING_MM", "TRENCH_SIDE_ALLOWANCE_MM")),
  ("MEMBER_MATCH", "A mark on the plan matched to the shape drawn beside it", TUNED, ("MEMBER_MATCH_AMBIGUOUS", "SIZE_VARIES", "SIZE_NOT_FOUND", "COLUMN_SIZE_FROM_PLAN", "SIZE_FROM_OTHER_VIEW"), ("MEMBER_SEARCH_MM", "SIZE_TOL", "MEMBER_MIN_MM", "MEMBER_MAX_MM")),
  ("ROOM_OUTLINE", "A room taken from the walls round its label, or from the size printed in the label", TUNED, ("ROOM_FROM_OUTLINE", "ROOM_FROM_LABEL", "ROOM_OUTLINE_REPLACED", "ROOM_INSIDE_ROOM", "ROOM_NO_LABEL", "ROOM_MULTIPLE_LABELS", "ROOM_SIZE_MISMATCH", "ROOM_GEOMETRY_REPAIRED", "ROOM_FACE_SKIPPED"), ("ROOM_SIZE_TOL",)),
)

def _value(name: str):
  mod, _, attr = name.rpartition(".")
  v = getattr(SG if mod == "SG" else C, attr)
  return round(v, 3) if isinstance(v, float) else v

def thresholds(names: tuple) -> dict:
  return {n.split(".")[-1]: _value(n) for n in names}

def known_codes() -> set:
  return {code for r in RULES for code in r[3]}

def scale_record(analysis: dict | None) -> dict:
  a = analysis or {}
  
  rec = a.get("recommended") or {}
  ok, code, _ = SG.auto_scale_gate(analysis)
  agreement = a.get("agreement")
  how = ("OVERRIDE" if agreement == "CONFLICT" and ok else "PRINTED_SCALE" if agreement == "DECLARED_ONLY" and ok else "DIMENSIONS" if ok else "PERSON")
  return {"agreement": agreement, "support": int(rec.get("support") or 0), "trust": rec.get("trust"), "gate": "OPEN" if ok else code, "decided_by": how}

def sheet_trace(page_no: int, notes: list, candidates: list, analysis: dict | None = None, stats: dict | None = None) -> dict:
  """{"page_no", "scale", "rules": [...fired, most items first], "silent": [ids of rules that did not fire]} of one sheet."""
  by_code: dict = {}
  
  for n in notes or []:
    by_code.setdefault(n.get("code"), {"notes": 0, "items": set(), "tags": []})["notes"] += 1
  for c in candidates:
    for n in c.notes or []:
      slot = by_code.setdefault(n.get("code"), {"notes": 0, "items": set(), "tags": []})
      slot["items"].add(str(c.id))
      if (c.tag or c.category) not in slot["tags"] and len(slot["tags"]) < 5:
        slot["tags"].append(c.tag or c.category)
        
  scale = scale_record(analysis)
  fired, silent = [], []
  for rid, label, basis, codes, consts in RULES:
    items = set().union(*[by_code[c]["items"] for c in codes if c in by_code]) if any(c in by_code for c in codes) else set()
    notes_n = sum(by_code[c]["notes"] for c in codes if c in by_code)
    tags: list = []
    
    for c in codes:
      for t in by_code.get(c, {}).get("tags", []):
        if t not in tags and len(tags) < 5:
          tags.append(t)
          
    count = len(items) + notes_n
    if rid == "SCALE_GATE" and scale["decided_by"] in ("OVERRIDE", "PRINTED_SCALE"):
      count += 1
    if rid == "VIEW_SPLIT":
      count += int(((stats or {}).get("plan_regions") or {}).get("count") or 0)
    if count:
      fired.append({"id": rid, "label": label, "basis": basis, "items": len(items), "notes": notes_n, "codes": sorted(c for c in codes if c in by_code), "examples": tags, "thresholds": thresholds(consts)})
    else:
      silent.append(rid)
  fired.sort(key=lambda r: (-(r["items"] + r["notes"]), r["id"]))
  return {"page_no": page_no, "scale": scale, "rules": fired, "silent": silent}

def drawing_summary(sheets: list) -> dict:
  tuned = {r["id"] for s in sheets for r in s["rules"] if r["basis"] == TUNED}
  default = {r["id"] for s in sheets for r in s["rules"] if r["basis"] == DEFAULT}
  return {"sheets": len(sheets), "tuned_rules_fired": sorted(tuned), "default_rules_fired": sorted(default),
    "tuned_items": sum(r["items"] for s in sheets for r in s["rules"] if r["basis"] == TUNED)}
