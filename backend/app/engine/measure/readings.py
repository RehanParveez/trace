from __future__ import annotations
import contextvars
from contextlib import contextmanager
from app.engine.measure import proposed

QS_NAME = "M. Junaid"
ANSWERED_BEFORE = "2026-10-19"
ANSWERED_ON = "2026-10-22"          
NEW = ANSWERED_ON
SOURCE = "qs"

APPLIED, CONFIRM, OPEN, PLOT = "APPLIED", "CONFIRM", "OPEN", "PLOT"
STATUSES = (APPLIED, CONFIRM, OPEN, PLOT)
SECTIONS = {"A": "Walls, finishes and openings", "B": "Columns, footings, beams, slabs, lintels and stairs", "C": "Parapet and roof", "D": "Tanks and site works",
  "E": "Excavation, foundations and termite", "F": "Formwork and steel", "G": "Order, roofs and rates"}

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

CHOICES = {
  "wall_height_basis": "FLOOR_TO_FLOOR",
}
CHOICE_OPTIONS = {
  "wall_height_basis": {
    "FLOOR_TO_FLOOR": "Floor to floor, as printed on the building sections (the QS's answer S5). A beam or band inside the wall is not taken off the height.",
    "CLEAR": "Clear storey height printed on the building sections (floor to the soffit of the slab above).",
    "ABOVE_PLINTH_BEAM": "Floor to floor less the depth of the plinth beam, on the lowest storey only: the wall stands from the top of the plinth beam (the QS's own worksheet, 9.25 ft in the basement). Needs the QS to confirm.",
    "BETWEEN_BEAMS": "As ABOVE_PLINTH_BEAM, and also less the web of the roof beam below the slab on every storey (the beam depth less the slab, as the beam depth includes the slab, N1): the wall stands between the two beams. Needs the QS to confirm.",
  },
}
PARAM_VALUES = {
  "brick_net_of_lintels": 1.0,
  "stair_formwork_soffit_only": 1.0,
  "beam_depth_includes_slab": 1.0,
  "tie_band_replaces_lintel": 0.0,
  "tie_band_single_count": 1.0,
  "slab_projection_chajja_max_mm": 457.2,
  "footing_formwork": 1.0,             
  "steel_wastage_pct": 5.0,            
  "pcc_thickness_mm": 76.2,                        
  "slab_steel_kg_per_m2": 16.1459,     
  "tank_base_formwork": 1.0,           
  "earth_swell_pct": 0.0,              
  "fill_compaction_pct": 0.0,
}

def _a(ident, section, topic, question, answer, status, applied, confirm=None, params=None, conventions=None, workbook=None, on=None):
  return {"id": ident, "section": section, "topic": topic, "question": question, "answer": answer, "status": status, "applied": applied, "confirm": confirm,
    "params": list(params or ()), "conventions": list(conventions or ()), "workbook": workbook, "answered_on": on or ANSWERED_BEFORE}

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
    "0.75 ft (9 in).", APPLIED,
    "Step 2 of the thin wall is 0.75 ft (228.6 mm). That is the height the workbook's step table already offers on that step, so the suggestion stands and is now the QS's value. The other steps stay the workbook's, offered as suggestions.",
    on=NEW),
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
  _a("S14", "B", "Footing formwork", "Are all footings shuttered?",
    "Yes. Every footing is shuttered and its sides are counted.", APPLIED,
    "Footing formwork is on for every footing: four sides at the footing depth. It was proposed from the Form Work sheet and is now the QS's answer.", params=["footing_formwork"], on=NEW),
  _a("S15", "B", "Steel conventions", "Cover, lap, hook, anchorage, ring rule and the 5 percent.",
    "The usual conventions for cover, lap length and hook allowance, and 5 percent extra for wastage.", APPLIED,
    "Wastage is 5 percent, now the QS's value. Cover, lap and hook stay the drawing's own notes where it prints them, and the flagged standard values where it does not.",
    "Whether the 5 percent is wastage only, with no lap or hook allowance inside it, was not said. Bars on both sides of a beam are still counted separately.",
    params=["steel_wastage_pct"], on=NEW),
  _a("S16", "B", "Slab steel", "Is any slab steel counted that the drawing does not print?",
    "Yes, by the rule of thumb of 1.5 kg per sq ft where the slab bars are not fully printed. Where the software works the steel out itself, that is accepted.", APPLIED,
    "A slab with no printed bars takes 1.5 kg per sq ft (16.1459 kg per m2); it was 1.6. A slab with printed bars is weighed from its bars, and the steel roll-up now sets that weight beside the rule of thumb so the two can be compared.",
    params=["slab_steel_kg_per_m2"], workbook="Steel Summary: slab area x 1.6 kg/sft (the QS now gives 1.5)", on=NEW),
  _a("S17", "G", "Rates", "Which rate system, edition and district; wastage and overhead inside the rate?",
    "Use the Market Rates System rates. Leave the other rate topics for now.", APPLIED,
    "Rate books come from the Market Rates System lists. The Bahawalpur lists for January to June and July to December 2026 are read with the table layout (MRS_TABLE) and loaded as rate books; the edition is chosen when the book is published.",
    "Wastage and overhead inside the rates (Q33) were not answered.", on=NEW),
  _a("Q21", "B", "Load-bearing, framed or both", "Is the building load-bearing, framed, or both?",
    "A load-bearing frame: both. The structural answer can confirm it.", APPLIED,
    "No change: the reader already counts columns and beams on every floor and the brick walls between them.", on=NEW),
  _a("Q22", "E", "Working space per side of the trench", "Working space per side of the trench.",
    "1 ft extra on each side of the trench, as the file already says.", CONFIRM,
    "Not changed: the software adds 3 in on each side of the concrete bed, which is what the workbook shows (a 3.5 ft bed in a 4 ft trench).",
    "The answer (1 ft each side) and the workbook (3 in each side) differ. Which is right? Until then working_space_mm stays 150 and the PCC projection stays 100.", on=NEW),
  _a("Q23", "E", "Ballast or PCC under foundations", "Thickness, projection beyond the foundation, under every footing?",
    "PCC bed 3 in thick.", APPLIED, "The PCC bed is 3 in (76.2 mm); the QS has now confirmed it.",
    "The projection of the bed beyond the footing (100 mm a side in the software) was not answered.", params=["pcc_thickness_mm"], on=NEW),
  _a("Q24", "E", "Backfill extras", "Compaction, swell, carted-away surplus, plinth filling.",
    "Backfill comes from the same excavation item, with no compaction, swell or surplus extras.", APPLIED,
    "Swell and compaction are 0 percent, now the QS's value; backfill is the excavated volume less the concrete and brickwork below ground. No surplus item is added.",
    params=["earth_swell_pct", "fill_compaction_pct"], on=NEW),
  _a("Q25", "E", "Anti-termite", "On the faces of the excavation, or on the wall footprint?",
    "Under the foundation and under all the floors, on the wall footprint.", APPLIED,
    "Termite treatment is measured on the bottom of the trench along each wall and on the area under the floors. The wording now says so.",
    "The sides (faces) of the excavation are not treated; the QS's answer names the footprint and the floors only. Confirm that the sides are left out.", on=NEW),
  _a("Q29", "F", "Formwork faces by member", "Formwork faces for each member type, and footings.",
    "Footings: the sides. A slab: from the bottom. A column: all four sides. A beam: the soffit and both sides below the slab.", APPLIED,
    "This is how the formwork is already measured; nothing changes. The beam sides below the slab stay with S13.", on=NEW),
  _a("Q30", "G", "Bill order", "Should the BOQ run by trade or by stage, and in what chapter order?",
    "By stage, with the trades inside each stage, as the QS did before.", CONFIRM,
    "Not built. Every BOQ row carries its stage and the rows are ordered by trade (work item); the export is not yet sorted stage first, then trade.",
    "Whether a stage-first report should replace the trade order, or be offered beside it.", on=NEW),
  _a("Q31", "G", "Roof types", "Roof types and units (RCC only today).",
    "RCC roofs only.", APPLIED, "No change: only RCC slab roofs are read.", on=NEW),
  _a("Q32", "G", "Datum defaults", "Datum defaults: floor, DPC, lintel and slab levels.",
    "Leave the DPC and the levels between slabs aside for now.", APPLIED, "Nothing changes for the DPC or the inter-slab levels; only the rates come from the Market Rates System.", on=NEW),
  _a("N17", "E", "Footing and basement levels", "How far below natural ground is the underside of the footing?",
    "4 ft overall for the footing: 3 ft 3 in with more below it.", CONFIRM,
    "Not changed: the footing underside stays 3.5 ft (1066.8 mm) below natural ground, as X4 gave.",
    "X4 said 3.5 ft and this answer says 4 ft overall. Which is the depth of the footing underside below natural ground?", on=NEW),
  _a("v4-N1", "B", "Beam depth, inverted beams", "Beam depth on the section: overall? Inverted beams?",
    "The depth is overall. Only the part below the slab is concrete of the beam. An inverted beam (above the slab) is included. Concrete is never counted twice.", CONFIRM,
    "Beam depth includes the slab, so the part inside the slab is the slab's. Counting the part of an inverted beam above the slab is not checked in this pass.",
    "Whether an inverted beam is read as a beam above the slab.", params=["beam_depth_includes_slab"], on=NEW),
  _a("v4-N2", "D", "Tank base slab", "Is the base slab of a tank shuttered?",
    "Yes, shuttered.", APPLIED, "The soffit of a tank's base slab is shuttered (tank_base_formwork is 1 by the QS's answer).", params=["tank_base_formwork"], on=NEW),
  _a("v4-N3", "B", "Chajja", "Is a chajja inside the projection or balcony slab, and shuttered?",
    "A chajja is counted in the projection or balcony slab, and it is shuttered.", APPLIED,
    "A chajja is read as a slab member and its formwork is measured (soffit and edges).", on=NEW),
  _a("N13", "B", "Arches", "Are arches counted?",
    "Yes, arches are counted and shuttered.", CONFIRM, "Not built: there is no arch member. An arch is drawn by hand as a slab or lintel.",
    "How an arch is to be measured (rise, thickness).", on=NEW),
  _a("v4-N4", "C", "Coping", "Coping: which faces are shuttered?",
    "Both sides.", APPLIED, "Coping formwork is both sides already.", on=NEW),
  _a("N12", "C", "Coping size", "Coping width on a 9 in boundary wall.",
    "1 ft wide on a 9 in wall; it projects a little outward and is cast in plain cement concrete with plaster.", PLOT,
    "Type the coping as 1 ft (304.8 mm) wide when the item is accepted.", on=NEW),
  _a("v4-N5", "C", "35 percent of slab soffit", "The 35 percent figure.",
    "The answer was cut off in the recording.", OPEN, "Nothing is changed.", "Ask again.", on=NEW),
]

def source_label() -> str:
  return QS_NAME

_DECIDED = contextvars.ContextVar("qs_decided", default=None)

@contextmanager
def deciding(values: dict | None):
  token = _DECIDED.set(dict(values or {}))
  try:
    yield
  finally:
    _DECIDED.reset(token)

def param(name: str):
  decided = _DECIDED.get()
  if decided and name in decided:
    return decided[name]
  return PARAM_VALUES.get(name)

def convention(name: str):
  return CONVENTIONS.get(name)

def choice(name: str):
  decided = _DECIDED.get()
  if decided and name in decided:
    return decided[name]
  return CHOICES.get(name)

def flag(name: str) -> bool:
  if name == "wall_height_floor_to_floor":
    return choice("wall_height_basis") != "CLEAR"          
  return bool(FLAGS.get(name))

def by_status() -> dict:
  out = {s: 0 for s in STATUSES}
  for a in READINGS:
    out[a["status"]] += 1
  return out

def public() -> dict:
  """What the API shows: the answers, the site assumptions the QS set and the conventions used while reading."""
  return {"qs": QS_NAME, "answered_on": ANSWERED_ON, "sections": [{"key": k, "title": v} for k, v in SECTIONS.items()], "answers": [dict(a) for a in READINGS],
    "params": dict(PARAM_VALUES), "conventions": dict(CONVENTIONS), "choices": dict(CHOICES), "choice_options": {k: dict(v) for k, v in CHOICE_OPTIONS.items()}, "counts": by_status(), "proposed": proposed.public()}

def note_text(*ids: str) -> str:
  return "The QS readings are (" + ", ".join(ids) + ")."