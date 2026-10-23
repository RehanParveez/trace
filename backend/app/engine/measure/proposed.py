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

PARAM_VALUES = {}         
PARAM_EVIDENCE = {
  "footing_formwork": "Form Work, FOOTING: F-1 x10, F-2 x4, F-3 x3, perimeter x 0.75 ft = 179.25 sft. Every footing, all four sides, 0.75 ft deep.",
  "steel_wastage_pct": "Steel Summary: 22.62 t plus 'Steel Waistage 5%' of 1.13 t = 23.75 t.",
  "pcc_thickness_mm": "PCC 1:4:8: every line is 0.25 ft thick (3 in, 76.2 mm).",
  "slab_steel_kg_per_m2": "Steel Summary: slab steel = slab area x 1.6 kg/sft (1,554.547 sft x 1.6 = 2,487.275 kg), a rule of thumb, not bar by bar. 1.6 kg/sft = 17.2223 kg/m2.",
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
    confirm="Is 8 ft the depth dug to the basement floor, below the natural ground? The QS's later answer (22 Oct) gives the footing as 4 ft overall, against 3.5 ft in X4."),
  _p("Q22", "E", "Working space per side of the trench", "Working space per side of the trench.",
    "3 in on each side of the concrete bed.", WORKBOOK, KEPT,
    "Excavation and PCC sheets: a 3.5 ft bed has a 4 ft trench. The software already adds 3 in a side.",
    confirm="The QS answered 1 ft extra on each side (22 Oct); the workbook has 3 in. Which is right?"),
  _p("Q26", "E", "DPC", "Thickness, door deduction, vertical DPC.",
    "DPC as thick as the wall at the datum, door widths deducted, no vertical DPC.", PRACTICE, KEPT,
    "The workbook measures a membrane (S1) and has no DPC line."),
  
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

  _p("Q33", "G", "Rate breakdown", "Wastage and overhead in the rates?", "No proposal.", SOFTWARE, HOLD, "Rates wait for the full rate list."),

  _p("P24-1", "G", "Plaster thickness", "How thick is the plaster when the drawing does not print it?",
    "Inside faces 1/2 in (12.7 mm), outside faces 3/4 in (19.05 mm), ceilings 3/8 in (9.525 mm). A thickness printed on a detail is read as the inside face's and replaces only that figure; the outside and the ceiling keep the practice figure.",
    PRACTICE, VALUE,
    "Usual cement-sand plaster practice for brick walls: 12 mm inside, 20 mm outside, 6 to 10 mm on concrete ceilings. Both 10 Marla sheets print 1/2 in on their wall details; none prints an outside thickness.",
    params=("plaster_inside_mm", "plaster_outside_mm", "plaster_ceiling_mm"),
    confirm="Is 3/4 in right for the outside faces on your sites?"),
  _p("P24-2", "E", "Soil stabilisation under foundations", "Is the stabilised layer measured?",
    "Only when the drawing prints it with no condition, or the estimator switches it on. A note that says 'in case of loose soil only' is recorded as printed and not measured; the volume it would add is shown beside the excavation. One 6 in layer under the whole concrete bed, mixed with 10 percent cement, compacted to 95 percent of modified AASHTO.",
    PRACTICE, SUGGESTION,
    "Islamabad_Plot_1 page 6: 'Filling shall be done in 6\" thick compacted layers', 'not less than 95% of Modified AASHTO', 'Arrangement of Soil Stabilisation ... in case of loose soil only ... using 10% Cement'. The stabilised thickness is not printed. Whether the soil is loose is known only from the soil test.",
    params=("soil_stabilisation", "soil_stab_thickness_mm", "soil_stab_cement_pct"),
    confirm="Does the soil report call the soil loose? What thickness is stabilised?"),
  _p("P24-3", "E", "Which PCC thickness is the foundation's", "Plain concrete appears under footings and in floor, terrace and roof build-ups.",
    "A bed whose mix is lean (1:4:8, 1:3:6) is the foundation bed; a rich mix (1:2:4, 1:1.5:3) is a floor, terrace or roof layer and never sets the foundation thickness. A bed with no mix printed is read as the foundation's, as before.",
    PRACTICE, KEPT,
    "10 Marla architectural page AD-12: '2\" THICK P.C.C. (1:2:4)' and '1 1/2\" THICK P.C.C. (1:2:4)' in the floor and terrace lists, against 3 in of 1:4:8 under the foundations in the QS's workbook."),
  _p("P24-4", "E", "A figure on both sides of the PCC note", "'12\" PCC (1:4:8) 12\"' on a footing section.",
    "The same figure on both sides of the bed is the width it projects past the footing on each side, not its thickness. It sets the PCC projection. Two different figures around the bed are not read.",
    SOFTWARE, VALUE,
    "Islamabad_Plot_1 page 6, raft section: 12 in is drawn on each side of the bed and the 3 in thickness is a separate label; the old reader took 12 in as the thickness.",
    params=("pcc_projection_mm",)),
  _p("P24-5", "A", "Opening deduction in plaster and paint", "Which openings come off the plaster and paint?",
    "Standard: an opening under 0.5 m2 is not deducted (his answer, Q28). From 0.5 to 3 m2 it comes off one face only and the reveals are not measured; over 3 m2 it comes off every face and the reveals are measured (IS 1200). The software takes every opening of 0.5 m2 or more off every face, as his sheet does, and the IS 1200 steps are one switch away (finish_opening_rule = 1, with the 3 m2 size adjustable).",
    PRACTICE, SUGGESTION,
    "IS 1200 (finishing): deductions of openings by area. Built in pack 28; the switch is off by default so the result still matches his sheet.",
    params=("finish_opening_min_m2", "finish_opening_rule", "finish_opening_one_face_max_m2"),
    confirm="Does your sheet deduct every opening of 0.5 m2 or more from both faces, or one face for the middle sizes?"),
  _p("P28-1", "D", "Faces of a boundary wall", "Which faces of the boundary wall are plastered and painted?",
     
    "A free-standing wall has two faces. The area of both (length x height x 2, the gate taken out) is shown with the wall; it is not added to the bill because the drawing does not say which faces are finished. Coping is not assumed.",
    PRACTICE, SUGGESTION, "Site items are read from the elevation: length, height and gate; the finish of the faces is not drawn.",
    confirm="Are both faces of the boundary wall plastered and painted, or only the street face?"),
  
  _p("P29-1", "D", "Floor finish, skirting and dado of the drawn rooms", "How are the floor finish, skirting and dado measured from the plan?",
    "Floor finish: the total of the room areas of each floor, leaving out lift shafts, lawns and courtyards. Skirting: the perimeter of every dry room less the width of its doors. A bath and a toilet have no skirting but a tile dado 7 ft (2134 mm) high, the perimeter less its doors; windows are not taken out of the dado.",
    PRACTICE, SUGGESTION,
    "Usual practice and the default finish rules (bath and toilet dado 2134 mm, kitchen and pantry dado 600 mm held back). The material (tile, marble, mosaic) and the dado height are not drawn on the plan; the dado height cannot be typed yet.",
    confirm="Is the dado 7 ft in baths and toilets, and is there a kitchen dado (600 mm) on this job?"),
  _p("P29-2", "D", "Paint on walls and ceilings", "What is painted, and what is taken off?",
    "Wall paint is on the same faces as the plaster, openings of 0.5 m2 and over taken off. The tile dado is taken off the inside paint, because tile is not painted. Ceiling paint has the same area as the ceiling plaster.",
    PRACTICE, SUGGESTION,
    "Usual practice. The one-face rule for middle-sized openings (IS 1200, built for the model route in pack 28) is not on the drawing route; only the 0.5 m2 minimum is.",
    confirm="Does your sheet paint the whole of the inside walls of a bath above the dado, and are ceilings painted in every room?"),
  _p("P24-6", "G", "Order of the bill (Q30)", "Stage first, or item first?",
    "Stage first, in the order of his Breakdown of Summary: substructure (excavation, termite, membrane, foundation), then frame, walls, lintels, finishes, roof, steel. Inside a stage the items follow his order and each floor is shown by itself.",
    WORKBOOK, KEPT, "Breakdown of Summary order (Q-A); the usual stage-wise summary above trade-wise sheets."),
  _p("P24-7", "A", "Inverted (upstand) beams (v4-N1)", "A beam above the slab top.",
    "A beam whose top is above the slab top is an upstand beam: its full depth is concrete and shuttered on both sides, and nothing is taken off the slab below it. Found by comparing the beam top with the slab top. Not built; the estimator confirms each one.",
    PRACTICE, SUGGESTION, "Usual measurement of an upstand beam; no sheet of his workbook shows one."),
  _p("P24-8", "A", "Arches over openings (N13)", "How is an arch measured?",
    "The opening is deducted as the full rectangle to the top of the arch; the plaster to the arch soffit is measured separately by its girth. Not built.",
    PRACTICE, SUGGESTION, "IS 1200 treats an arched opening by the rectangle that encloses it; the soffit is extra."),
  _p("P24-9", "D", "Coping size (N12)", "Size of the parapet and boundary-wall coping.",
    "Read from the detail when the drawing prints one; otherwise the estimator types it. No standard size is assumed because it is plot specific.",
    SOFTWARE, KEPT, "N12 was answered as plot specific."),
  _p("P24-10", "G", "Working space and depth conflicts (Q22, N17)", "The QS's later answers (1 ft each side; 4 ft overall) differ from his workbook (3 in; 3.5 ft).",
    "Keep the workbook's figures, because the software is checked against his sheet; show the other figures as an alternative. The extra volume from 1 ft each side is worked out beside the excavation when asked.",
    WORKBOOK, KEPT, "X4 and the Excavation sheet give 3.5 ft and a 4 ft trench for a 3.5 ft bed; the 22 Oct answers give 1 ft and 4 ft.",
    confirm="Which of the two do you want as the standard?"),
  _p("P43-1", "A", "Wall height basis for brick, and brick net of lintels", "Which height is a brick wall measured to when a plinth beam and a roof beam stand in it, and are the lintels taken off the brick?",
    "Floor to floor stays the standard (S5). The brick is net of the lintels over its openings (IS 1200 and usual practice; assumed). The QS worksheet's 9.25 ft in the basement is the choice ABOVE_PLINTH_BEAM; BETWEEN_BEAMS also takes off the roof-beam web.",
    PRACTICE, VALUE, "S5: basement 10.75 ft floor to floor. Plinth Beam sheet: 1.5 ft deep. Concrete Work: roof beam 0.75 ft deep, which includes the 6 in slab (N1). The QS worksheet's basement brick is 769 cft.",
    params=["brick_net_of_lintels"], confirm="Is the basement brick measured from the top of the plinth beam to the underside of the roof beam, and are the lintels taken off it?"),
  _p("P44-1", "A", "Roof band, tie band and lintels: one member each", "The drawing prints a roof band and a tie band at lintel level over the same walls. Is the concrete counted once?",
    "One band member, chosen by what the drawing prints: the roof band at slab level when its detail is printed, else the tie band. The lintels over the openings stay (Q27), and a tie band listed separately runs over the solid wall only, on 9 in walls. The decision shows the concrete with and without the tie band and the difference.",
    PRACTICE, VALUE, "Q27: the lintel is added separately; the QS worksheet has roof beams and lintels and no tie band. The sample drawing prints a roof band detail and a 9 x 12 in tie beam / lintel level band detail.",
    params=["tie_band_single_count"], confirm="Is there a continuous tie band at lintel level on the job, separate from the roof beam and the lintels?"),
  _p("P45-1", "A", "Roof projections: which strips are slab", "A roof projection label gives a width but not a length. Which strips are slab, and is a narrow one a chajja?",
    "A strip is added to the slab only when its label is bound to an overall length printed beside it and that length is the length of the side of the plan it stands beside. A strip of 18 in (457.2 mm) or less is a chajja and is not in the slab concrete (assumed). A strip that cannot be bound or checked is listed with its width and what it would add, and is not added.",
    PRACTICE, VALUE, "Islamabad_Plot_1: the 1'-6\" left projection is bound to 60'-0\" on the ground plan (the overall length of the site, not the 48'-0\" side) and to 48'-0\" on the first-floor plan; the QS's slab concrete (808.3 and 808.8 cft) is the slab without it. S2 left the widths open.",
    params=["slab_projection_chajja_max_mm"], confirm="Is the 1'-6\" strip along the left side a chajja measured separately, or part of the slab?"),
  _p("P45-2", "A", "Slab thickness: three witnesses", "The structural note says 5 in, the sections are labelled 6 in and the building sections imply 6 in. Which governs?",
    "The thickness labelled on the sections, printed more than once and agreeing with the building sections, governs over a general slab note (6 in on Islamabad). The concrete at every thickness the drawing prints is shown with the slab, and the report adds it up: the choice is worth about 13 m3 (460 cft) over the four slabs.",
    PRACTICE, VALUE, "Islamabad_Plot_1: sheet 6 prints a general slab note of 5 in (all slabs, 3 times); the section labels of sheet 5 print 6 in (12 times); floor-to-floor less clear height gives 6 in on the ground, first and roof floors.",
    confirm="Are the slabs 5 in or 6 in thick?"),
  _p("P45-3", "B", "Slab steel from the framing plan", "The framing plan draws each bar set as an arrowed line with a bar string. How is the steel of a panel taken from it?",
    "One set per distinct bar string in a panel and direction (the string is repeated on every line of the set), the bar as long as the drawn line, the number of bars the other span over the spacing plus one. Top steel over the supports, bearing, anchorage and laps are not in it. Only a panel with one panel mark inside gets steel.",
    PRACTICE, SUGGESTION, "Islamabad_Plot_1 sheet 6: 6 marked panels on each of the basement, ground and first framing plans; bars about 11 kg per m2 of panel against the QS rule of 16.1 kg per m2 of slab.",
    confirm="Are the top bars over the supports separate from the lines drawn, and how much bearing does a bar take into its beam?"),
  _p("P46-1", "B", "Neck column height", "The neck column runs from the top of the footing to the lowest floor, and that height is not printed on the sheet. What height does it take?",
    "The QS's 3.5 ft, as the registry holds it (neck_height_mm), on every neck column and marked assumed. Type a height to override it.",
    WORKBOOK, VALUE, "Concrete Work, NECK COLUMNS: C-1, C-2 and C-3 are 3.5 ft high.",
    confirm="Is 3.5 ft the height from the top of the footing to the basement floor, for every neck column?"),
  _p("P46-2", "B", "Footing pad sizes follow the column", "The footing details print sizes without a footing mark. Which footing has which size?",
    "Each footing mark is paired with the column mark written beside it on the foundation plan. The larger column takes the larger pad, and a single size left over once the marks have theirs goes to the stair footing. All of it marked assumed.",
    SOFTWARE, KEPT, "Islamabad_Plot_1 sheet 6: F1 is written beside C1 ten times and F2 beside C2 four times; C1 is 9 x 9 in and C2 9 x 15 in. The details print 3 ft, 3 ft and 5 ft pads: F1 takes 3 ft, F2 5 ft, and the stair footing the other 3 ft.",
    confirm="Does F2 (under C2) have the 5 ft pad, and is the stair footing the second 3 ft pad?"),
  _p("P46-3", "B", "Column marks against column details", "The details are captioned by mark and the plans mark the columns, and the two lists differ. Which detail is which mark?",
    "By size, never silently: a plan mark with no detail takes the detail of its size whose mark no plan uses (a mark captioned twice first); squares with no mark take the one unused detail of their size. Sizes already read are not changed; each match is a note to check.",
    SOFTWARE, SUGGESTION, "Islamabad_Plot_1 sheet 6: no detail is captioned C1; C3 is captioned twice (9 x 9 and 9 x 18 in); the roof shows three unmarked 9 x 9 in squares; C4 and C5 have details and no plan mark.",
    confirm="Is the 9 x 9 in detail captioned C3 the detail of C1, and are the three roof squares C5?"),
  _p("P47-1", "B", "Beam length between column faces", "A beam drawn as a hatched strip runs from column centre to column centre. What length goes into the concrete?",
    "The length between column faces: the width of each column a strip runs into is taken off, because the column concrete is counted in the column (IS 1200). The centre to centre length is kept on the row.",
    PRACTICE, VALUE, "Islamabad_Plot_1 sheet 6, ground framing plan: GB-1 and GB-2 run 23.35 m centre to centre between 223 to 235 mm columns; the strips begin and end at column centres.",
    confirm="Does your workbook measure beams between column faces, or from centre to centre?"),
  _p("P47-2", "B", "Beam sections for a mark with no section", "The plan marks the strips GB-1 and GB-2; the sheet captions sections B2, GB-4, PB-1, PB-2, RB-1 to RB-4 and the tie band. Which section is GB-1?",
    "Nothing is chosen. The sections of the kind the mark names (GB a grade beam, RB a roof beam, PB a plinth beam) are listed on the beam to pick from, or a depth is typed.",
    SOFTWARE, SUGGESTION, "Islamabad_Plot_1 sheet 6: the only grade beam section is GB-4, 18 in deep; RB-3 prints its bars but no depth that could be read.",
    confirm="Are GB-1 and GB-2 on the plans the beam of section GB-4 (18 in deep)?"),
]

SIZE_VALUES = {
  "beam_depth_mm": {"mm": 228.6, "text": "0.75 ft", "evidence": "Concrete Work, ROOF BEAMS on every floor: 0.75 ft wide (0.375 ft on a 4.5 in wall) and 0.75 ft deep."},
  "plinth_beam_depth_mm": {"mm": 457.2, "text": "1.5 ft", "evidence": "Plinth Beam sheet: 0.75 ft wide and 1.5 ft deep under a 9 in wall; none under a 4.5 in wall."},
  "neck_height_mm": {"mm": 1066.8, "text": "3.5 ft", "evidence": "Concrete Work, NECK COLUMNS: C-1, C-2 and C-3 are 3.5 ft high."},
  "tank_wall_height_mm": {"mm": 1524.0, "text": "5 ft", "evidence": "Concrete Work, UGWT and OHWT: the long and short walls are 5 ft high."},
}

def sizes() -> dict:
  return {k: dict(v) for k, v in SIZE_VALUES.items()}

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
  return {"note": PROPOSED_BY, "bases": dict(BASIS_TEXT), "effects": dict(EFFECT_TEXT), "params": dict(PARAM_VALUES), "evidence": dict(PARAM_EVIDENCE), "sizes": sizes(),
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
