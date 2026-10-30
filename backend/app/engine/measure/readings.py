from __future__ import annotations
import contextvars
from contextlib import contextmanager
from app.engine.measure import proposed
from app.engine.measure import company as CO
from app.engine.measure import rulebook as RB

QS_NAME = RB.QS_SEED.get("name", "")
ANSWERED_BEFORE = RB.QS_SEED.get("answered_before", "")
ANSWERED_ON = RB.QS_SEED.get("answered_on", "")
NEW = ANSWERED_ON
LATEST = RB.QS_SEED.get("latest", "")
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
  "floor_finish_by_room": False,
  "wall_plaster_drawn": True,
  "deduct_opening_brick": True,
  "deduct_opening_plaster": True,
  "deduct_opening_paint": True,
  "derived_scaffold": True,
  "derived_props": True,
  "page_role_vote": True,
}

CHOICES = {
  "wall_height_basis": "BETWEEN_BEAMS",
  "opening_rules_basis": "SHEET",
}
CHOICE_OPTIONS = {
  "wall_height_basis": {
    "FLOOR_TO_FLOOR": "Floor to floor, as printed on the building sections (the QS's answer S5). A beam or band inside the wall is not taken off the height.",
    "CLEAR": "Clear storey height printed on the building sections (floor to the soffit of the slab above).",
    "ABOVE_PLINTH_BEAM": "Floor to floor less the depth of the plinth beam, on the lowest storey only: the wall stands from the top of the plinth beam (the QS's own worksheet, 9.25 ft in the basement). Needs the QS to confirm.",
    "BETWEEN_BEAMS": "As ABOVE_PLINTH_BEAM, and also less the web of the roof beam below the slab on every storey (the beam depth less the slab, as the beam depth includes the slab, N1): the wall stands between the two beams (the QS's answer R1, 26 Oct; it is where every drawing starts).",
  },
  "opening_rules_basis": {
    "SHEET": "One rule for every work item, as the QS's sheet has it: an opening of 0.5 m2 or more comes off, whatever the item; a smaller one does not. Plaster and paint: off every face, no reveals.",
    "IS1200": "A rule for each work item (IS 1200, assumed): brickwork from 0.1 m2; an RCC wall from 0.4 m2 (the formwork rule, so concrete and formwork agree); plaster and paint from 0.5 m2, one face only up to 3 m2, every face above 3 m2 with the reveals added. Damp proof course unchanged: door widths come off.",
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
  "working_space_mm": 76.2,
  "finish_opening_rule": 0.0,
  "roof_turnup_mm": 0.0,
  "beam_lintel_qs_rate": 0.0,
  "wall_plaster_face_mm": 12.5,
  "brick_opening_min_m2": 0.1,
  "rcc_wall_opening_min_m2": 0.4,
  "plaster_opening_min_m2": 0.5,
  "plaster_opening_one_face_max_m2": 3.0,
  "scaffold_above_mm": 3600.0,
  "props_above_mm": 3600.0,
  "cft_per_m3": 35.3146667,
  "sft_per_m2": 10.7639104,
  "round_cft_dp": -1.0,
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
    "Use 0.75 ft and 0.5 ft separately. A beam sits under the slab, so only the part below the slab is concrete and shuttered; the bars on both sides are steel.", APPLIED,
    "A switch, Beam and lintel formwork by the QS rate, takes the formwork of a beam as 0.75 ft per rft and of a lintel as 0.5 ft per rft. It stays off: on 26 Oct the QS said a lintel is shuttered on its bottom and both sides (R8), so the measured faces are used.",
    "Answered on 26 Oct (R8): the sides are shuttered, so the measured faces stay.",
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
    "The item is called roof treatment. It is measured over the roof area that the sun, rain and weather reach, to protect the roof.", APPLIED,
    "It is measured by area; the QS sheet adds the projection strips of the lower floors.", "Answered on 26 Oct (R12): it does not go up the parapet.", workbook="Roof Treatment 1,982.75 sft (184.3 m2)"),
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
    "1 ft extra on each side of the trench, as the file already says.", APPLIED,
    "The software adds 3 in on each side of the concrete bed, which is what the workbook shows (a 3.5 ft bed in a 4 ft trench). On 26 Oct the QS settled it (R17): 3 in for a foundation trench, because a lean bed is laid under it; about 1 ft each side only for open excavation.",
    "Answered on 26 Oct (R17). working_space_mm is now 76.2 as the QS's value; the PCC projection stays 100 (not answered).", on=NEW),
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
    "The contract bill (PDF and Excel) now runs stage first, in the order of the stage report, with the trades of a stage inside it, a sub-total for each trade and a total for each stage. The kinds of item (materials, labour, additional works) are totalled beside it, and a labour or additional line says so. The stage report export is as before.",
    "The order of the trades inside a stage is alphabetical here (assumed); his own chapter order was not given.", on=NEW),
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
    "Beam depth includes the slab, so the part inside the slab is the slab's. A beam section captioned 'upstand' or 'inverted' is read as a beam above the slab: its concrete is the depth less the slab, it is shuttered on both sides above the slab with no soffit, and the section is not offered for a beam the plan does not mark.",
    "Which beam of the plan is the upstand one: the plan of Plot_1 does not mark it, so none is shuttered that way yet.", params=["beam_depth_includes_slab"], on=NEW),
  _a("v4-N2", "D", "Tank base slab", "Is the base slab of a tank shuttered?",
    "Yes, shuttered.", APPLIED, "The soffit of a tank's base slab is shuttered (tank_base_formwork is 1 by the QS's answer).", params=["tank_base_formwork"], on=NEW),
  _a("v4-N3", "B", "Chajja", "Is a chajja inside the projection or balcony slab, and shuttered?",
    "A chajja is counted in the projection or balcony slab, and it is shuttered.", APPLIED,
    "A chajja is read as a slab member and its formwork is measured (soffit and edges).", on=NEW),
  _a("N13", "B", "Arches", "Are arches counted?",
    "Yes, arches are counted and shuttered.", CONFIRM, "An opening whose schedule row says ARCH gets a line for its centring: the soffit girth (a semicircle, assumed) times the wall thickness, in m2. The opening is still deducted as the full rectangle to the crown. An arch the schedule does not say is arched is still drawn by hand.",
    "How high the arch rises and how thick it is: the schedule prints neither, so a semicircle in the thickness of the wall is used.", on=NEW),
  _a("v4-N4", "C", "Coping", "Coping: which faces are shuttered?",
    "Both sides.", APPLIED, "Coping formwork is both sides already.", on=NEW),
  _a("N12", "C", "Coping size", "Coping width on a 9 in boundary wall.",
    "1 ft wide on a 9 in wall; it projects a little outward and is cast in plain cement concrete with plaster.", PLOT,
    "Type the coping as 1 ft (304.8 mm) wide when the item is accepted.", on=NEW),
  _a("v4-N5", "C", "35 percent of slab soffit", "The 35 percent figure.",
    "The answer was cut off in the recording.", OPEN, "Nothing is changed.", "Ask again.", on=NEW),
  _a("R1", "A", "Brick wall height and the lintels", "Is brick measured (a) top of plinth beam to underside of roof beam, (b) floor to floor, or (c) another height? Are the lintels taken off the brick?",
    "(a) Top of the plinth beam to the underside of the roof beam. The lintels are separate concrete and are taken off the brick.", APPLIED,
    "Every drawing now starts with the wall height basis BETWEEN_BEAMS: the plinth beam comes off the lowest storey and the web of the roof beam off every storey. The brick stays net of its lintels. A person can still choose another basis for one drawing in the Decisions panel.",
    "This replaces the floor-to-floor height of S5 (22 Oct) for brick walls. Tell me if S5 was meant for a different job.", params=["brick_net_of_lintels"], on=LATEST),
  _a("R2", "A", "Tie band", "Is there a separate continuous tie band at lintel level, or is the concrete one member?",
    "No separate band. The lintel is one member; the roof beams sit above it only where the slab is depressed, and every roof beam is measured. Lintel first, then the roof beam above it.", APPLIED,
    "No change: the tie band and the lintel are one member and the lintel is still added (tie_band_replaces_lintel stays 0).", params=["tie_band_replaces_lintel"], on=LATEST),
  _a("R3", "B", "Slab thickness", "Is the slab 5 in (structural note) or 6 in (sections)?",
    "6 in.", APPLIED, "No change: 6 in is already taken where two thicknesses are printed (X5).", conventions=["slab_thickness_mm"], on=LATEST),
  _a("R7", "B", "Roof projection", "Is the 1'-6\" strip beyond the wall line slab, a chajja or something else?",
    "Slab, counted with the slab.", APPLIED, "No change: the projection is part of the slab outline (S3).", on=LATEST),
  _a("R4", "B", "Slab steel", "Is the steel taken from the framing plan's bar strings, are the top bars over the supports separate, and what bearing does a bar take into its beam?",
    "From the framing plan strings, with separate top bars, and the bearing into the beam is the beam width less 25 mm of cover.", APPLIED,
    "No change: this is how the steel reader already works. The answer is now the QS's, not the software's proposal.", on=LATEST),
  _a("R5", "B", "Footing concrete and the other figures", "Is 142 to 159 cft at 9 in depth the right range for the plot's footings? Please send the QS's figures for columns, beams, slabs, walls and brickwork.",
    "Yes, 142 to 159 cft at 9 in. The other figures: leave them.", APPLIED,
    "The footing range stays the benchmark check. No other figure was given, so nothing else is checked against a QS number.", "Send the QS's totals later if you want columns, beams, slabs and walls checked.", on=LATEST),
  _a("R6", "A", "Opening deductions and the mortar", "From what area does an opening come off brick, plaster and paint? Does plaster come off one face only for openings from 0.5 to 3 m2?",
    "Plaster is on both faces, so an opening comes off both. Brick mortar is 1:5 and plaster mortar 1:4.", APPLIED,
    "The opening rule stays 'every face' and is now the QS's value (finish_opening_rule 0). The brickwork mortar where the drawing prints none is 1:5 (it was 1:6); plaster stays 1:4.",
    "The smallest opening deducted (0.1 m2 for brick, 0.5 m2 for plaster) was not answered, so 0.5 m2 stays.", params=["finish_opening_rule"], on=LATEST),
  _a("R8", "B", "Lintel formwork", "Does a lintel's formwork include the soffit over its bearing, and is the side under a chajja measured whole?",
    "The bottom and both sides of a lintel are shuttered, because it is cast over the opening.", APPLIED,
    "The measured faces (soffit and both sides) stay; the QS-rate switch stays off and is now the QS's value.",
    "Whether the soffit over the bearing in the wall is included, and the chajja and balcony edges, were not answered; the present rules stay.", params=["beam_lintel_qs_rate"], on=LATEST),
  _a("R9", "C", "Bath waterproofing", "Floor only, or floor plus the walls up to a height?",
    "Floor only.", APPLIED, "The waterproofing of a bath or toilet is its floor area. The 300 mm turn-up the PDF reader added is gone.", on=LATEST),
  _a("R10", "C", "Kitchen wall tile", "Does the kitchen get wall tile, to what height, and is the tile taken off the kitchen paint?",
    "Yes, tiled to 7 ft, as in the baths.", APPLIED,
    "A kitchen wall tile is measured at 7 ft (2134 mm) with no height to type; the part of a window inside that height comes off. The height can still be changed on the measurement.",
    "Whether the tile comes off the kitchen paint was not answered; it is not taken off.", on=LATEST),
  _a("R11", "C", "Bath windows", "Does a bath window come off the dado, and what sill is assumed?",
    "It comes off; the sill is 5 ft.", APPLIED, "No change: a bath window comes off the dado with a 5 ft (1524 mm) sill where none is printed.", on=LATEST),
  _a("R12", "C", "Roof waterproofing", "Is the membrane turned up the parapet, and is the coba measured at its average thickness?",
    "The whole roof is done, with a small chamfer at the parapet. It is not taken up the parapet.", APPLIED,
    "The turn-up is 0 (roof_turnup_mm, the QS's value), so the membrane and the screed are the roof area only.",
    "The small chamfer has no size and is not measured. The coba thickness was not answered.", params=["roof_turnup_mm"], on=LATEST),
  _a("R13", "C", "Boundary wall faces", "Are both faces plastered and painted, and are the sides as high as the front?",
    "Both faces are plastered and painted. Where the outer face is left unplastered, a polythene sheet goes on it before building.", APPLIED,
    "No change: both faces are already taken.", "The height and length of the side and rear walls were not answered.", on=LATEST),
  _a("R14", "C", "Coping", "Is there a standard coping size?",
    "No standard thickness. On a 9 in wall the coping is 1 ft wide; any overhang beyond that is not measured.", PLOT,
    "Type the coping as 1 ft (304.8 mm) wide when the item is accepted (N12).", "The thickness of the coping was not given.", on=LATEST),
  _a("R15", "D", "Scaffolding", "Is it billed for the wall above 3.6 m only, or for the whole facade from the ground once the building is higher than 3.6 m?",
    "The whole facade from the ground to the top of the roof, once the building is higher than 3.6 m, built in stages.", APPLIED,
    "Scaffolding is the outside face of each floor times its height: the lowest floor from the ground (the section datum) to its top, each floor above it its floor-to-floor height. Nothing is made while the whole building is 3.6 m or lower.",
    "The ground is taken as the datum of the building sections.", on=LATEST),
  _a("R16", "D", "Props", "From what clear height are props billed under a slab, and is it per m2 of soffit?",
    "There is no per-metre rule for extra height; the props, sockets included, are one item.", APPLIED,
    "Props are the slab area once, for every slab whose storey is clearer than 3.6 m. The extra-metre steps are gone.",
    "My reading of a recorded answer. Tell me if props should be billed from a different height or not at all.", on=LATEST),
  _a("R17", "E", "Excavation", "Working space 3 in and 3.5 ft depth (workbook) or 1 ft and 4 ft (later answer)?",
    "A foundation trench is dug 3 in wider than the bed, because lean concrete is laid under it. Other excavation takes about 1 ft on each side.", APPLIED,
    "A foundation trench takes 3 in a side (the PDF reader already does; the model calculation now uses 76.2 mm as the QS's value). The 1 ft is not applied to any item: the dig over a basement is the area typed.",
    "The depth (3.5 ft or 4 ft, N17) was not answered again.", params=["working_space_mm"], on=LATEST),
  _a("R18", "E", "Electrical points", "Are points priced per point including the wiring, or per fitting with the wiring by length?",
    "Per point; the wiring from the board is included in the point.", APPLIED,
    "Points are counted and no wiring length is taken, as now. Which rate book prices them is a pricing question and is left for later.", on=LATEST),
  _a("R19", "E", "Rain water pipe", "A pipe is labelled on the roof plan and again on the floor plans: one pipe, or one for each label?",
    "One pipe. It runs from the roof down.", APPLIED, "No change: a pipe seen on two sheets is counted once.", on=LATEST),
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

def qs() -> dict:
  return RB.qs()

def param(name: str):
  decided = _DECIDED.get()
  if decided and name in decided:
    return decided[name]
  return RB.pick(name, PARAM_VALUES.get(name))

def convention(name: str):
  return RB.pick(name, CONVENTIONS.get(name))

def choice(name: str):
  decided = _DECIDED.get()
  if decided and name in decided:
    return decided[name]
  return RB.pick(name, CHOICES.get(name))

def flag(name: str) -> bool:
  if name == "wall_height_floor_to_floor":
    return choice("wall_height_basis") != "CLEAR"
  return bool(RB.pick(name, FLAGS.get(name)))

PER_DRAWING = ("wall_height_basis", "opening_rules_basis", "tie_band_single_count", "brick_net_of_lintels")
NOT_READ = ("footing_below_ground_mm", "stair_waist_mm", "lintel_bearing_mm", "beam_formwork_mm_per_rft", "lintel_formwork_mm_per_rft", "brick_length_centre_line")
DEPTHS = {"basement_dig_mm": "BASEMENT_DIG_MM", "trench_depth_mm": "TRENCH_DEPTH_MM", "fill_depth_mm": "FILL_DEPTH_MM"}
BOUNDS = {"mm": (1.0, 30000.0), "mm per rft": (1.0, 2000.0), "%": (0.0, 100.0), "kg/m2": (0.0, 200.0), "m2": (0.0, 20.0), "cft per m3": (30.0, 40.0), "sft per m2": (10.0, 11.5),
  "decimals": (-1.0, 6.0)}
WHY_FIXED = {
  "PER_DRAWING": "Decided for each drawing on its decisions screen. The figure here is only where every drawing starts.",
  "NOT_READ": "Held for reference. The software does not read this figure yet; the value it uses is a constant in the code.",
}
LABELS = {
  "basement_wall_height_mm": ("Heights and depths", "Basement concrete wall height"),
  "basement_floor_to_floor_mm": ("Heights and depths", "Basement floor to floor"),
  "footing_depth_mm": ("Heights and depths", "Footing depth when only a symbol is printed"),
  "footing_below_ground_mm": ("Heights and depths", "Footing below ground"),
  "slab_thickness_mm": ("Heights and depths", "Slab thickness when none is printed"),
  "stair_waist_mm": ("Heights and depths", "Stair waist"),
  "lintel_bearing_mm": ("Heights and depths", "Lintel bearing at each end"),
  "neck_height_mm": ("Heights and depths", "Neck column height"),
  "beam_depth_mm": ("Heights and depths", "Roof beam depth when none is printed"),
  "plinth_beam_depth_mm": ("Heights and depths", "Plinth beam depth"),
  "basement_dig_mm": ("Heights and depths", "Basement dig depth"),
  "trench_depth_mm": ("Heights and depths", "Wall trench depth"),
  "fill_depth_mm": ("Heights and depths", "Filling depth up to the plinth"),
  "pcc_thickness_mm": ("Heights and depths", "Plain concrete bed thickness"),
  "slab_projection_chajja_max_mm": ("Heights and depths", "Largest slab projection counted as a chajja"),
  "tank_top_slab_mm": ("Tanks and site", "Tank top slab"),
  "tank_bottom_slab_mm": ("Tanks and site", "Tank bottom slab"),
  "tank_wall_height_mm": ("Tanks and site", "Tank wall height"),
  "boundary_wall_thickness_mm": ("Tanks and site", "Boundary wall thickness"),
  "tank_base_formwork": ("Tanks and site", "Tank base formwork taken"),
  "beam_formwork_mm_per_rft": ("Formwork and steel", "Beam formwork, per running foot"),
  "lintel_formwork_mm_per_rft": ("Formwork and steel", "Lintel formwork, per running foot"),
  "footing_formwork": ("Formwork and steel", "Footing formwork taken"),
  "stair_formwork_soffit_only": ("Formwork and steel", "Stair formwork: soffit only"),
  "steel_wastage_pct": ("Formwork and steel", "Steel wastage"),
  "slab_steel_kg_per_m2": ("Formwork and steel", "Slab steel by rule of thumb"),
  "earth_swell_pct": ("Earthwork", "Earth swell"),
  "fill_compaction_pct": ("Earthwork", "Fill compaction"),
  "beam_depth_includes_slab": ("How the QS counts", "Beam depth includes the slab"),
  "tie_band_replaces_lintel": ("How the QS counts", "A tie band replaces the lintel"),
  "rcc_ring_closed": ("How the QS counts", "Concrete wall ring counted as closed"),
  "brick_length_centre_line": ("How the QS counts", "Brick wall length on the centre line"),
  "floor_finish_by_room": ("How the QS counts", "Floor finish billed room by room"),
  "wall_plaster_drawn": ("How the QS counts", "A sheet drawn at the plaster faces is read as brick walls"),
  "wall_plaster_face_mm": ("Heights and depths", "Plaster on each face of a wall"),
  "deduct_opening_brick": ("How the QS counts", "Openings come off brickwork"),
  "deduct_opening_plaster": ("How the QS counts", "Openings come off plaster"),
  "deduct_opening_paint": ("How the QS counts", "Openings come off paint"),
  "derived_scaffold": ("How the QS counts", "Scaffolding on the outside walls is billed"),
  "derived_props": ("How the QS counts", "Props under a high slab are billed"),
  "page_role_vote": ("How the QS counts", "A page's role is voted from several signals"),
  "brick_opening_min_m2": ("Openings and units", "Smallest opening deducted from brickwork"),
  "rcc_wall_opening_min_m2": ("Openings and units", "Smallest opening deducted from a concrete wall"),
  "plaster_opening_min_m2": ("Openings and units", "Smallest opening deducted from plaster and paint"),
  "plaster_opening_one_face_max_m2": ("Openings and units", "Largest opening that comes off one face of the plaster only"),
  "scaffold_above_mm": ("Heights and depths", "Building height above which scaffolding is billed"),
  "props_above_mm": ("Heights and depths", "Clear height above which props are billed"),
  "cft_per_m3": ("Openings and units", "Cubic feet in a cubic metre"),
  "sft_per_m2": ("Openings and units", "Square feet in a square metre"),
  "round_cft_dp": ("Openings and units", "Decimals of a cubic foot in the bill (-1 for none)"),
  "wall_height_basis": ("Decided for each drawing", "Height of a brick wall"),
  "tie_band_single_count": ("Decided for each drawing", "Tie band at lintel level"),
  "brick_net_of_lintels": ("Decided for each drawing", "Brick and the lintels over its openings"),
  "opening_rules_basis": ("Decided for each drawing", "Which openings come off each work item"),
}

def code_default(key: str):
  """The figure the software starts from, whatever the company holds."""
  if key in CONVENTIONS:
    return CONVENTIONS[key]
  if key in PARAM_VALUES:
    return PARAM_VALUES[key]
  if key in CHOICES:
    return CHOICES[key]
  if key in FLAGS:
    return 1.0 if FLAGS[key] else 0.0
  if key in proposed.SIZE_VALUES:
    return proposed.SIZE_VALUES[key]["mm"]
  if key in DEPTHS:
    return getattr(proposed, DEPTHS[key])
  return None

UNIT_OF = {"brick_opening_min_m2": "m2", "rcc_wall_opening_min_m2": "m2", "plaster_opening_min_m2": "m2", "plaster_opening_one_face_max_m2": "m2",
  "cft_per_m3": "cft per m3", "sft_per_m2": "sft per m2", "round_cft_dp": "decimals"}

def _unit(key: str):
  if key in UNIT_OF:
    return UNIT_OF[key]
  if key in CHOICES or key in FLAGS or (key in PARAM_VALUES and not key.endswith(("_mm", "_pct", "_kg_per_m2"))):
    return None
  if key.endswith("_mm_per_rft"):
    return "mm per rft"
  if key.endswith("_mm"):
    return "mm"
  if key.endswith("_pct"):
    return "%"
  if key.endswith("_kg_per_m2"):
    return "kg/m2"
  return None

def registry() -> list:
  """Every convention a company can hold: key, group, label, unit, the software's own figure, the range a value must lie in and whether the software reads the company's figure."""
  rows = []
  for key, (group, label) in LABELS.items():
    unit = _unit(key)
    kind = "CHOICE" if key in CHOICES else "NUMBER" if unit else "SWITCH"
    low, high = BOUNDS.get(unit, (0.0, 1.0))
    row = {"key": key, "group": group, "label": label, "kind": kind, "unit": unit, "default": code_default(key), "low": low, "high": high, "editable": True, "why_fixed": None}
    if kind == "CHOICE":
      row["options"] = [{"value": v, "text": t} for v, t in CHOICE_OPTIONS[key].items()]
    if key in PER_DRAWING:
      row["editable"], row["why_fixed"] = False, WHY_FIXED["PER_DRAWING"]
    elif key in NOT_READ:
      row["editable"], row["why_fixed"] = False, WHY_FIXED["NOT_READ"]
    rows.append(row)
  return rows

def figure(key: str, value) -> str:
  unit = _unit(key)
  if unit is None:
    return str(value) if isinstance(value, str) else ("yes" if float(value) >= 0.5 else "no")
  v = float(value)
  if unit == "mm":
    return f"{v:g} mm ({v / 25.4:.4g} in)"
  return f"{v:g} {unit}"

def in_force(key: str):
  return RB.pick(key, code_default(key))

def company_differs(*keys: str) -> bool:
  """True when the company holds a figure for any of these that is not the software's own."""
  for key in keys:
    held = CO.value(key)
    if held is None:
      continue
    base = code_default(key)
    if isinstance(base, str) or isinstance(held, str):
      if str(held) != str(base):
        return True
    elif abs(float(held) - float(base)) > 1e-9:
      return True
  return False

def conventions_words(*keys: str) -> str:
  return "; ".join(f"{LABELS[k][1][0].lower() + LABELS[k][1][1:]} {figure(k, in_force(k))}" for k in keys)

def whose(keys, as_qs: str, as_company: str) -> str:
  """The wording of a note: the QS's own when the figure is still the QS's, the company's when the company set it."""
  return as_company if CO.origin_of(*keys) in (CO.COMPANY, CO.PROJECT) else as_qs

def by_status() -> dict:
  out = {s: 0 for s in STATUSES}
  for a in READINGS:
    out[a["status"]] += 1
  return out

def public() -> dict:
  """What the API shows: the answers, the site assumptions the QS set and the conventions used while reading."""
  return {"qs": qs()["name"], "answered_on": qs()["answered_on"], "sections": [{"key": k, "title": v} for k, v in SECTIONS.items()], "answers": [dict(a) for a in READINGS],
    "params": dict(PARAM_VALUES), "conventions": dict(CONVENTIONS), "choices": dict(CHOICES), "choice_options": {k: dict(v) for k, v in CHOICE_OPTIONS.items()}, "counts": by_status(), "proposed": proposed.public()}

def note_text(*ids: str) -> str:
  return "The QS readings are (" + ", ".join(ids) + ")."