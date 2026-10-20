from __future__ import annotations
from app.engine.measure import proposed

QS_NAME = "M. Junaid"
ANSWERED_ON = "2026-10-19"
SOURCE = "qs"

APPLIED, CONFIRM, OPEN, PLOT = "APPLIED", "CONFIRM", "OPEN", "PLOT"
STATUSES = (APPLIED, CONFIRM, OPEN, PLOT)
SECTIONS = {"A": "Walls, finishes and openings", "B": "Columns, footings, beams, slabs, lintels and stairs", "C": "Parapet and roof", "D": "Tanks and site works"}

CONVENTIONS = {
  "basement_wall_height_mm": 3352.8,
  "basement_floor_to_floor_mm": 3276.6,
  "footing_depth_mm": 228.6,
  "footing_below_ground_mm": 1066.8,
  "slab_thickness_mm": 152.4,
  "stair_waist_mm": 127.0,
  "lintel_bearing_mm": 152.4,
  "tank_top_slab_mm": 152.4,
  "tank_bottom_slab_mm": 203.2,
  "boundary_wall_thickness_mm": 114.3,
  "beam_formwork_mm_per_rft": 228.6,
  "lintel_formwork_mm_per_rft": 152.4,
}
FLAGS = {
  "wall_height_floor_to_floor": True,
  "rcc_ring_closed": True,
  "brick_length_centre_line": True,
}
PARAM_VALUES = {
  "stair_formwork_soffit_only": 1.0,
  "beam_depth_includes_slab": 1.0,
  "tie_band_replaces_lintel": 0.0,
}

def _a(ident, section, topic, question, answer, status, applied, confirm=None, params=None, conventions=None, workbook=None):
  return {"id": ident, "section": section, "topic": topic, "question": question, "answer": answer, "status": status, "applied": applied, "confirm": confirm,
    "params": list(params or ()), "conventions": list(conventions or ()), "workbook": workbook}

READINGS = [
  _a("S1", "A", "Basement membrane", "Is 11 ft the height the membrane goes up, and is it on the outside of every outer basement wall?",
    "Yes. The membrane is on the outside of every outer basement wall, the full height of 11 ft, counted once. Inside and outside plaster are separate items.", APPLIED,
    "On a basement floor the membrane is the outside-face length of the outer walls times 11 ft (3352.8 mm); the length is the same one the outside plaster uses, so the two never disagree. The strip along the plinth is kept for floors that are not a basement.",
    "The QS sheet adds ten 4 ft pieces (about 41 m2) that the plan does not show; they are listed as a difference, not counted.",
    conventions=["basement_wall_height_mm"], workbook="Membrane: ten room lines (164.97 ft) x 11 ft plus ten 4 ft x 11 ft pieces = 2254.5 sft (209.5 m2)"),
  _a("S2", "A", "Width of the roof projections", "Which projection width (3 ft, 2 ft, printed 6 ft) applies on which floor?",
    "No width was given. The QS calls a shade a projection and counts it inside the slab.", OPEN,
    "The printed width is read as before and flagged.", "Ask for the width on each floor.", workbook="Roof Treatment: strips of 3 ft and 2 ft on each floor"),
  _a("S3", "A", "Roof area", "Is 1,125.87 sft the roof slab with or without the projections?",
    "With the projections.", APPLIED,
    "The slab outline already includes the projection strips, so the software area is compared with the QS figure as it stands.", workbook="Roof 1,125.87 sft"),
  _a("S4", "A", "Plaster: once for the full height or once per floor", "Are outer and inner plaster counted once for the full height, or once per floor?",
    "Once per floor, which is how the sheet was made. On some buildings the outside can be done for the full height from the elevation.", APPLIED,
    "Plaster stays per floor and the note now names the QS.", "The full-height outside option needs the elevation height and is not built.", conventions=[]),
  _a("S5", "A", "Wall and column height", "Which height for each floor, floor to floor or clear?",
    "Floor to floor. The basement is 10.75 ft floor to floor; the basement concrete walls are taken as 11 ft for the estimate. Inside and outside are separate so nothing is counted twice.", APPLIED,
    "Walls and columns take the floor-to-floor height printed on the building sections; the basement takes 10.75 ft; a basement concrete wall and the membrane take 11 ft.",
    conventions=["basement_wall_height_mm", "basement_floor_to_floor_mm"]),
  _a("S6", "A", "Height of brick foundation step 2", "What is the height of step 2 for the thin wall?",
    "Not answered.", OPEN, "Typed when the step is accepted. The step heights of his workbook are shown as a suggestion on each step; nothing is filled in.", "Ask again."),
  _a("S7", "A", "Ground floor 4.5 in boundary walls", "The sheet has 66 ft. Is that measured along the boundary or his estimate?",
    "It is an estimate. The boundary is about 6 ft high and the wall is 4.5 in thick.", APPLIED,
    "The 66 ft is shown beside the drawing length as the QS estimate; the drawing length is what is measured. The 4.5 in thickness is offered when the wall is accepted.",
    conventions=["boundary_wall_thickness_mm"], workbook="66 ft of 4.5 in wall"),
  _a("S8", "A", "Fourth side of the basement concrete wall", "The drawing shows three sides as concrete. Is the fourth side concrete too?",
    "Yes, all four sides are concrete.", APPLIED,
    "The stretches that close the ring are counted in the trench, the membrane and the plaster, and their note says the QS confirmed them. They are still accepted one by one as walls.",
    workbook="RCC wall: ring of 168 ft, two faces, 11 ft high"),
  _a("X1", "A", "Brickwork length", "Is brickwork measured on the centre line, the outer face or the clear length?",
    "On the centre line. The parapet and the roof projection are separate items.", APPLIED, "Wall lengths are centre to centre, which is what the reader already does."),
  _a("Q28", "A", "Smallest opening to deduct", "What is the smallest opening deducted, and the rule where a wall meets a frame?",
    "No size was given. An opening at a junction is still deducted.", OPEN, "The 0.5 m2 placeholder stays and raises a review issue.", "Ask for the smallest size."),
  _a("X2", "A", "Window W2", "Is W2 counted as 2.5 half on purpose?",
    "2.5 is square feet, not a count.", PLOT, "Compare W2 as an area of 2.5 sft (0.232 m2). The QS counts 30 doors and 30 windows with the ventilators.", None),
  _a("X3", "A", "Small room on the mumty", "Is the unlabeled 2.65 m2 room a real room?",
    "Yes, it is a bathroom; its wall is not labelled on the drawing.", PLOT, "Label it as a bathroom when the room is accepted.", None),
  _a("S10", "B", "Three C-3 columns", "Where are they and what size?",
    "They are the three columns of the car porch, 9 x 9 in and 9 x 18 in as the details show, taken floor to floor, with three footings.", PLOT,
    "Draw the three columns by hand at the car porch (the plan has no mark) and add three footings; the size is offered as 9 x 18 in.",
    "Which of the two C-3 details applies (9 x 9 or 9 x 18).", workbook="Three C-3 columns in the QS count"),
  _a("X4", "B", "Footing thickness", "Footing thickness is only a symbol on the drawing. Is 0.75 ft right? Is 3.5 ft right?",
    "Yes, 0.75 ft thick; 3.5 ft is also right.", APPLIED,
    "A footing with no printed thickness takes 0.75 ft (228.6 mm) and the note says the QS gave it.",
    "3.5 ft is kept as a typed value (footing bottom below natural ground) because it belongs to this plot, not to every building.", conventions=["footing_depth_mm", "footing_below_ground_mm"]),
  _a("X5", "B", "Slab thickness", "Is the slab 6 in for every slab, including the basement roof?",
    "Yes, 6 in everywhere; the elevation says so.", APPLIED,
    "Where the drawing prints two thicknesses the 6 in one is chosen and the note names the QS.", conventions=["slab_thickness_mm"]),
  _a("X6", "B", "Name of the slab on a framing plan", "Is the plan called Ground Floor Framing the slab over the ground floor or at ground level?",
    "The slab over the basement is the basement roof slab and is the ground floor slab. A slab called ground floor slab is the one at ground level. A shade is a projection.", PLOT,
    "The plans are matched to floors by their level, as before.", None),
  _a("Q27", "B", "Lintel with a tie beam", "Where a tie beam runs at an opening, is the lintel still counted?",
    "Yes, the lintel is added separately.", APPLIED, "The tie band no longer replaces the lintel.", params=["tie_band_replaces_lintel"]),
  _a("Q27b", "B", "Lintel depth, steel and bearing", "What are the lintel depth, steel and bearing?",
    "The drawing prints them by span. A 4 ft door gets 6 in extra bearing.", APPLIED, "The lintel table is read by span and the bearing is 6 in each side.", conventions=["lintel_bearing_mm"]),
  _a("X7", "B", "Beam length on each floor", "Ground floor beams are 94.5 rft and first floor about 91 rft. Is the first floor a copy?",
    "No. Measure each floor on its own and keep every difference.", APPLIED, "Beams are measured per floor from that floor's plan; nothing is copied."),
  _a("S13", "B", "Beam and lintel formwork", "Soffit only (0.75 ft per rft of beam, 0.5 ft per rft of lintel) or soffit and both sides?",
    "Use 0.75 ft and 0.5 ft separately. A beam sits under the slab, so only the part below the slab is concrete and shuttered; the bars on both sides are steel.", CONFIRM,
    "A switch, Beam and lintel formwork by the QS rate, takes the formwork of a beam as 0.75 ft per rft and of a lintel as 0.5 ft per rft. It is off until the QS confirms the sides are not shuttered.",
    "Confirm that the sides below the slab are not shuttered; the measured faces (soffit and both sides) stay in use until then.",
    params=["beam_lintel_qs_rate"], conventions=["beam_formwork_mm_per_rft", "lintel_formwork_mm_per_rft"], workbook="Beams 1,386 sft (roof only), lintels 391 sft"),
  _a("N1", "B", "Beam depth on a plan", "Is the printed beam depth overall or the web below the slab?",
    "Overall: an 18 in beam under a 6 in slab has 12 in below the slab.", APPLIED, "Beam depth includes the slab, as the default was.", params=["beam_depth_includes_slab"]),
  _a("X8", "B", "Stair slab", "The stair waist slab is 5 in on the plan and 4.7 in elsewhere.",
    "Either; 5 in is taken.", APPLIED, "The waist is 5 in (127 mm) and the note names the QS.", conventions=["stair_waist_mm"]),
  _a("S12", "B", "Stair formwork", "Is 52.11 sft per set the soffit only, or soffit, risers and sides?",
    "The base slab (the waist soffit) is shuttered and the steps are built on it one by one. Taking the base slab directly is the more reliable way.", APPLIED,
    "A stair is shuttered on its soffit only; the risers and sides are no longer added.", "Confirm the step forms are not wanted as a separate item.", params=["stair_formwork_soffit_only"]),
  _a("X9", "B", "Column height", "Is the column height floor to floor or footing top to slab underside?",
    "Floor to floor.", APPLIED, "A column takes the floor-to-floor height of its floor.", conventions=["basement_floor_to_floor_mm"]),
  _a("X10", "C", "Parapet", "What is the size of the parapet, and is the shed counted?",
    "Parapet sizes come from the plan; it is brick, about 3 ft 1 in high. The shed is a projection and is already inside the slab.", PLOT,
    "Enter the parapet top at 3 ft 1 in (939.8 mm) in the datums.", "Confirm the 3 ft 1 in height.", None),
  _a("S9", "C", "Roof treatment", "What is the item, and does it go up the parapet?",
    "The item is called roof treatment. It is measured over the roof area that the sun, rain and weather reach, to protect the roof.", CONFIRM,
    "It is measured by area; the QS sheet adds the projection strips of the lower floors.", "Whether it turns up the parapet was not answered.", workbook="Roof Treatment 1,982.75 sft (184.3 m2)"),
  _a("S11", "D", "Tanks", "The sheet has 14 x 9 x 5 ft. The drawing's overhead tank is 3 ft 6 in x 7 ft. Where does it come from?",
    "Use the sizes given on his sheet. Walls and slabs are separate; the top slab is 6 in and the bottom slab 8 in; the wall thickness is on the sheet.", CONFIRM,
    "A tank takes a top slab of 6 in and a bottom slab of 8 in, and the walls the thickness typed. Its concrete is the outside box less the inside space.",
    "The sheet shows 6 in for both slabs of the water tanks and 9 in for the septic bottom. Confirm the 8 in.", conventions=["tank_top_slab_mm", "tank_bottom_slab_mm"],
    workbook="UGWT and OHWT 8 x 4.5 ft, walls 0.5 ft x 5 ft, 93.5 cft each; septic bottom 0.75 ft"),
  _a("X11", "D", "Boundary wall, gate, porch, ramp, side and rear walls", "Lengths are not printed and thickness is not on the elevations.",
    "The drawing is CAD, so the thickness can be read from the elevation. The 100 ft frontage is taken from the drawing. The thickness has to be typed.", CONFIRM,
    "The length and height are read; the thickness is typed at accept, with 4.5 in offered for the 4.5 in wall.",
    "Reading the thickness from the elevation is not built."),
  _a("S14", "B", "Footing formwork", "Are all footings shuttered?", "Not answered.", OPEN, "Proposed from his Form Work sheet: every footing, four sides. Still marked assumed.", "Ask again."),
  _a("S15", "B", "Steel conventions", "Cover, lap, hook, anchorage, ring rule and the 5 percent.", "Not answered. Bars on both sides of a beam are counted separately.", OPEN,
    "The flagged defaults stay, and the 5 percent of his Steel Summary is proposed as the wastage. Still marked assumed.", "Ask again."),
  _a("S16", "B", "Slab steel", "Is any slab steel counted that the drawing does not print?", "Not answered.", OPEN, "Asked at accept; none assumed.", "Ask again."),
  _a("S17", "D", "Rates", "Which rate system, edition and district; wastage and overhead inside the rate?", "Not answered.", OPEN, "Components are shown as stored.", "Ask again."),
]

def source_label() -> str:
  return QS_NAME

def param(name: str):
  """The value the QS gave for a site assumption, or None."""
  return PARAM_VALUES.get(name)

def convention(name: str):
  return CONVENTIONS.get(name)

def flag(name: str) -> bool:
  return bool(FLAGS.get(name))

def by_status() -> dict:
  out = {s: 0 for s in STATUSES}
  for a in READINGS:
    out[a["status"]] += 1
  return out

def public() -> dict:
  """What the API shows: the answers, the site assumptions the QS set and the conventions used while reading."""
  return {"qs": QS_NAME, "answered_on": ANSWERED_ON, "sections": [{"key": k, "title": v} for k, v in SECTIONS.items()], "answers": [dict(a) for a in READINGS],
    "params": dict(PARAM_VALUES), "conventions": dict(CONVENTIONS), "counts": by_status(), "proposed": proposed.public()}

def note_text(*ids: str) -> str:
  return "The QS readings are (" + ", ".join(ids) + ")."
