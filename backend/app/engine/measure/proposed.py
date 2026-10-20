from __future__ import annotations

PROPOSED_BY = "proposed from the QS's answers to sections A to D and from his workbook; not given by the QS"

WORKBOOK, PRINTED, PRACTICE, SOFTWARE = "WORKBOOK", "PRINTED", "PRACTICE", "SOFTWARE"
BASES = (WORKBOOK, PRINTED, PRACTICE, SOFTWARE)
BASIS_TEXT = {
  WORKBOOK: "His workbook shows it.",
  PRINTED: "The drawing prints it.",
  PRACTICE: "Usual site practice; his workbook is silent. Check it.",
  SOFTWARE: "His workbook is silent; the software's present behaviour is proposed and stays.",
}

VALUE, SUGGESTION, KEPT, HOLD = "VALUE", "SUGGESTION", "KEPT", "HOLD"
EFFECTS = (VALUE, SUGGESTION, KEPT, HOLD)
EFFECT_TEXT = {
  VALUE: "Changes the standard value. Still marked assumed; type a value to override.",
  SUGGESTION: "Shown as a suggestion on the measurement. Nothing is filled in.",
  KEPT: "No change. The software already does this.",
  HOLD: "Not proposed. Waits for the rate list.",
}

PARAM_VALUES = {
  "footing_formwork": 1.0,
  "steel_wastage_pct": 5.0,
  "pcc_thickness_mm": 76.2,
}
PARAM_EVIDENCE = {
  "footing_formwork": "Form Work, FOOTING: F-1 x10, F-2 x4, F-3 x3, perimeter x 0.75 ft = 179.25 sft. Every footing, all four sides, 0.75 ft deep.",
  "steel_wastage_pct": "Steel Summary: 22.62 t plus 'Steel Waistage 5%' of 1.13 t = 23.75 t.",
  "pcc_thickness_mm": "PCC 1:4:8: every line is 0.25 ft thick (3 in, 76.2 mm).",
}

BASEMENT_DIG_MM = 2438.4    
TRENCH_DEPTH_MM = 914.4     
BRICK_STEP_OFFSET_MM = 114.3  
BRICK_STEP_HEIGHTS_MM = {
  "THIN": (152.4, 228.6, 381.0),
  "THICK": (152.4, 152.4, 381.0, 228.6),
}

def _p(ident, section, topic, question, proposed, basis, effect, evidence, params=(), confirm=None):
  return {"id": ident, "section": section, "topic": topic, "question": question, "proposed": proposed, "basis": basis, "effect": effect,
    "evidence": evidence, "params": list(params), "confirm": confirm}

PROPOSALS = [
  _p("N17", "E", "Footing and basement levels", "How far below natural ground is the underside of the footing, and how deep is the basement floor?",
    "Footing underside 3.5 ft below natural ground, as the QS said (X4). The basement is dug 8 ft.", WORKBOOK, SUGGESTION,
    "X4: 3.5 ft is right. Excavation sheet: the whole basement area is 30 x 54 x 8 ft. The printed 3'-3\" is a section detail; the QS value is used.",
    confirm="Is 8 ft the depth dug to the basement floor, below the natural ground?"),
  _p("S6", "E", "Height of brick foundation steps", "What is the height of step 2 for the thin wall?",
    "Thin wall: steps of 6, 9 and 15 in. Thick wall: 6, 6, 15 and 9 in. Each step is 4.5 in narrower than the one below. Step 2 of the thin wall is 9 in (0.75 ft).", WORKBOOK, SUGGESTION,
    "Brick Work sheet, steps 1 to 4: widths 1.875, 1.5, 1.125, 0.75 ft (thick) and 1.125, 0.75, 0.375 ft (4.5 in wall); heights 0.5, 0.5, 1.25, 0.75 ft and 0.5, 0.75, 1.25 ft.",
    confirm="Are these step heights the ones to build?"),
  _p("Q21", "E", "Load-bearing, framed or both", "Is the building load-bearing, framed, or both?",
    "Framed with brick infill.", PRINTED, KEPT,
    "The plans draw columns and beams on every floor, and the workbook counts columns, beams and lintels with brick walls between them."),
  _p("Q22", "E", "Working space per side of the trench", "Working space per side of the trench.",
    "3 in on each side of the concrete bed.", WORKBOOK, KEPT,
    "Excavation and PCC sheets: a 3.5 ft bed has a 4 ft trench. The software already adds 3 in a side."),
  _p("Q23", "E", "Ballast or PCC under foundations", "Thickness, projection beyond the foundation, under every footing?",
    "PCC 3 in thick under every footing and wall. A pad bed is as large as its footing; the 1 ft ballast with 6 in clearance stays.", WORKBOOK, VALUE,
    "PCC 1:4:8: 0.25 ft thick; F-1 bed 3 x 3 ft and F-2 bed 3.5 x 5 ft, the same size as the footings.", params=["pcc_thickness_mm"],
    confirm="The footing PCC projection added by the engine (100 mm a side) is not in his sheet; should it be 0?"),
  _p("Q24", "E", "Backfill extras", "Compaction, swell, carted-away surplus, plinth filling.",
    "None. Backfill is the excavated volume less the concrete and brickwork below ground.", SOFTWARE, KEPT,
    "The workbook has no backfill, swell or surplus line."),
  _p("Q25", "E", "Anti-termite", "On the faces of the excavation, or on the wall footprint?",
    "On the bottom of the trench along each wall, as wide as the bed, and on the area under the floors. Not on the sides.", WORKBOOK, KEPT,
    "Termite sheet: strips 3 ft (outer) and 3.5 ft (inner) wide along each wall, 1.5 ft for 4.5 in walls, plus the under-floor areas."),
  _p("Q26", "E", "DPC", "Thickness, door deduction, vertical DPC.",
    "DPC as thick as the wall at the datum, door widths deducted, no vertical DPC.", PRACTICE, KEPT,
    "The workbook measures a membrane (S1) and has no DPC line."),
  
  _p("S14", "F", "Footing formwork", "Are all footings shuttered, or only some?",
    "All footings, all four sides, at the footing depth of 0.75 ft.", WORKBOOK, VALUE, PARAM_EVIDENCE["footing_formwork"], params=["footing_formwork"],
    confirm="Is a footing resting directly on earth shuttered on all four sides?"),
  _p("Q29", "F", "Formwork faces by member", "Formwork faces for each member type, and footings.",
    "Footings four sides; columns all faces; beams 0.75 ft and lintels 0.5 ft a running foot (S13); slab edges on; faces shared between members counted once.", WORKBOOK, KEPT,
    "Form Work sheet: footings 179.25 sft, columns by perimeter, roof beams x 0.75, lintels x 0.5."),
  _p("S15", "F", "Steel conventions", "Cover, lap, hook, anchorage, ring rule and the 5 percent.",
    "The 5 percent is wastage added to the total. Cover, lap and hook are the drawing's own notes where it prints them, and the standard values where it does not.", WORKBOOK, VALUE,
    PARAM_EVIDENCE["steel_wastage_pct"], params=["steel_wastage_pct"],
    confirm="Is the 5 percent wastage only, with no lap or hook allowance inside it?"),
  _p("S16", "F", "Slab steel", "Is any slab steel counted that the drawing does not print?",
    "No. Only the bars the drawing prints are counted.", SOFTWARE, KEPT,
    "His answers kept the drawing as the source where it prints a value (S7, X5, X10)."),
  
  _p("Q30", "G", "Bill order", "Should the BOQ run by trade or by stage, and in what chapter order?",
    "By trade, with the stage (up to plinth, plinth to lintel, lintel to slab) as a sort. Chapters follow his Breakdown of Summary.", WORKBOOK, KEPT,
    "Breakdown of Summary lists the items by stage, and each item has its own sheet by trade."),
  _p("Q31", "G", "Roof types", "Roof types and units (RCC only today).",
    "RCC slab roofs only.", WORKBOOK, KEPT, "Every roof in the workbook is an RCC slab (Roof Treatment, RCC Basement Slab, Concrete Work)."),
  _p("Q32", "G", "Datum defaults", "Datum defaults: floor, DPC, lintel and slab levels.",
    "Floor-to-floor heights from the sections; basement 10.75 ft (11 ft for walls); parapet top 3 ft 1 in; the levels the QS gave stay.", WORKBOOK, KEPT,
    "S5, X9 and X10 gave the heights; the other levels are read from the sections."),
  _p("Q34", "G", "Calibration tolerance", "How close counts as a match?",
    "5 percent.", SOFTWARE, KEPT, "Not in the workbook; the comparison already uses 5 percent."),
  _p("Q-A", "G", "First version scope and order", "Which items does the first version have to cover, and in what order?",
    "The items of his Breakdown of Summary, in its order: excavation, termite, membrane, brick foundation, PCC, foundation concrete, plinth beam, columns, walls, lintels, plaster, roof, steel.", WORKBOOK, KEPT,
    "Breakdown of Summary."),
  
  _p("S2", "A", "Width of the roof projections", "Which projection width applies on which floor?",
    "Basement 3 ft; ground and first floor 3 ft and 2 ft; roof floor 2 ft. The printed width is still read as before; these widths are only recorded here.", WORKBOOK, KEPT,
    "Roof Treatment sheet: projection strips of 3 ft and 2 ft on each floor, 2 ft on the roof floor.",
    confirm="Which floor has which width?"),
  
  _p("Q28", "A", "Smallest opening to deduct", "What is the smallest opening deducted?",
    "0.5 m2 for plaster, as the placeholder is. An opening at a junction is deducted (his answer).", PRACTICE, KEPT,
    "The usual measurement rule for plaster; the clause number is not checked."),
  _p("S13", "B", "Beam and lintel formwork (open point)", "Are the sides below the slab shuttered?",
    "Keep the switch off. The measured faces stay in use and his 0.75 ft and 0.5 ft figure is shown beside them.", WORKBOOK, KEPT,
    "Form Work sheet: roof beams x 0.75, lintels x 0.5 a running foot."),
  _p("S9", "C", "Roof treatment (open point)", "Does it turn up the parapet?",
    "No. It is the roof slab area plus the projection strips of each floor.", WORKBOOK, KEPT,
    "Roof Treatment sheet: roof 1,125.87 sft plus the strips of every floor = 1,982.75 sft; no parapet line."),
  _p("S11", "D", "Tank slab thickness (open point)", "Is the bottom slab 8 in?",
    "Keep 6 in top and 8 in bottom as the QS said; the sheet's own tanks differ and are compared, not copied.", WORKBOOK, KEPT,
    "UGWT and OHWT sheets use 6 in for both slabs; the septic bottom is 9 in."),
  _p("X11", "D", "Thickness of boundary, gate and ramp walls (open point)", "Read the thickness from the elevation?",
    "No. The thickness is typed at accept; 4.5 in is offered.", SOFTWARE, KEPT, "He said the thickness has to be typed."),

  _p("S17", "G", "Rates", "Which rate system, edition and district?", "No proposal.", SOFTWARE, HOLD, "Rates wait for the full rate list."),
  _p("Q33", "G", "Rate breakdown", "Wastage and overhead in the rates?", "No proposal.", SOFTWARE, HOLD, "Rates wait for the full rate list."),
  _p("Q-B", "G", "Punjab rate system", "Which Punjab rate system and edition?", "No proposal.", SOFTWARE, HOLD, "Rates wait for the full rate list."),
]

def param(name: str):
  return PARAM_VALUES.get(name)

def is_proposed(name: str) -> bool:
  return name in PARAM_VALUES

def by_effect() -> dict:
  out = {e: 0 for e in EFFECTS}
  for p in PROPOSALS:
    out[p["effect"]] += 1
  return out

def public() -> dict:
  return {"note": PROPOSED_BY, "bases": dict(BASIS_TEXT), "effects": dict(EFFECT_TEXT), "params": dict(PARAM_VALUES), "evidence": dict(PARAM_EVIDENCE),
    "items": [dict(p) for p in PROPOSALS], "counts": by_effect()}

def _inch(mm: float) -> str:
  return f"{mm / 25.4:g}"

def excavation_extra() -> dict:
  return {"message": f"Suggestion, not an answer from the QS: his workbook digs the basement {BASEMENT_DIG_MM / 304.8:g} ft deep (the 'Complete Area' line, 30 x 54 x 8 ft). "
    f"The drawing does not print the depth. Type {BASEMENT_DIG_MM:g} mm in the depth if that is the depth to dig.", "suggest": {"depth_mm": BASEMENT_DIG_MM}}

def trench_extra() -> dict:
  return {"message": f"Suggestion, not an answer from the QS: his workbook digs the wall trenches {TRENCH_DEPTH_MM / 304.8:g} ft deep. "
    f"The drawing does not print the depth for this wall. Type {TRENCH_DEPTH_MM:g} mm in the depth if that is right.", "suggest": {"depth_mm": TRENCH_DEPTH_MM}}

def brick_step(strip_class: str, step_no: int):
  heights = BRICK_STEP_HEIGHTS_MM.get(str(strip_class).upper())
  if not heights or not (1 <= int(step_no) <= len(heights)):
    return None
  return {"step_height_mm": heights[int(step_no) - 1], "step_offset_mm": BRICK_STEP_OFFSET_MM}

def brick_step_extra(strip_class: str, step_no: int) -> dict:
  s = brick_step(strip_class, step_no)
  if s is None:
    return {"message": "His workbook has no such step.", "suggest": {}}
  return {"message": f"Suggestion, not an answer from the QS: his workbook gives step {int(step_no)} of a {str(strip_class).lower()} wall a height of {_inch(s['step_height_mm'])} in "
    f"({s['step_height_mm']:g} mm), each step {_inch(s['step_offset_mm'])} in narrower than the one below ({s['step_offset_mm']:g} mm). Type them if they are right.", "suggest": s}
