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
  _p("P62-1", "D", "Plaster, paint and the side and rear walls of the boundary", "The elevation shows the front of the boundary wall. Which faces are finished, and how long are the side and rear walls?",
    "Three lines are made from the front wall: the brick of the side and rear walls, the plaster on both faces and the paint on both faces. Both faces are taken as finished, for the front wall (the gate taken out) and for the side and rear walls, which are at the height of the front wall and, for the brick, at its thickness. The length of one side and of the rear are typed when the lines are accepted (0 where there is no wall of your own); the two sides are taken as equal. Nothing is taken off for piers and nothing is added for the coping, the top or the ends. The gate is its own item and its faces are not counted.",
    PRACTICE, SUGGESTION,
    "Islamabad_Plot_1, page 5: the elevation prints the boundary wall 15.25 ft long and 6 ft high with the 14.75 ft gate taken out of the overall length, so the front wall has 17.00 m2 of face (both sides). The side and rear lengths are not printed as text the reader takes, and the thickness is not printed (4.5 in from the QS, S7).",
    confirm="Are both faces of the boundary plastered and painted, are the sides as high as the front, and are the side walls of the same length? Is any side a wall built by a neighbour?"),
  _p("P61-1", "L", "Which roof heading of the specification block belongs to which roof", "When the specification prints a terrace, a roof and a porch roof, which roof of the drawing does each one belong to?",
    "The roof of a roof plan takes the ROOF heading. The main roof under a roof plan takes the TERRACE heading. A sheet that shows no roof plan takes the TERRACE heading for its top floor. When the heading of a roof is not printed but only one roof heading is, that one is used. When several are printed and none is the heading of the roof, no layer is made into an item and the sheet says so. A porch roof or mumty heading is not used until a porch roof or mumty is found.",
    PRACTICE, SUGGESTION,
    "Architectural_Drawings_10_Marla_House, page 20: the TERRACE heading prints brick ballast 3 in, a cement-sand bed 1 in (1:3) and a plain concrete bed 1.5 in (1:2:4) with two coats of waterproofing; the ROOF heading prints brick tiles 1.5 in, mud plaster 1 in, one layer of polythene and two coats; the PORCH ROOF heading prints a cement-sand bed 1 in. This set has no roof slab on its sheets, so the roof layers were checked on a roof of 104 m2 put in by hand, not on a real roof.",
    confirm="Is the roof over the stair room the one the ROOF heading describes, and the main terrace the one the TERRACE heading describes? Is a porch roof laid with its own bed?"),
  _p("P61-2", "L", "Roof layers and the roof deck assembly", "When the drawing prints the layers of a roof, should the roof deck assembly (coba, screed, membrane) still add its own?",
    "A layer printed on the drawing is measured as its own item, and it takes the code of the assembly layer it stands for: brick ballast is the coba (FIN-ROOF-COBA), the cement-sand bed is the screed (FIN-ROOF-SCREED) and the coats are the membrane (FIN-ROOF-MEMBRANE). The assembly, when it is switched on, then leaves out each layer already measured and adds only the ones the drawing does not print.",
    PRACTICE, SUGGESTION,
    "The assembly already skips a layer whose code is measured from the drawing (roof_deck.py); the printed layers use those codes so that skip applies. The assembly is off by default.",
    confirm="Is the brick ballast on a terrace the same work as the coba in your bills?"),
  _p("P61-3", "L", "How the layers of a floor or roof are measured", "Is a layer of the floor or roof build-up measured by volume or by area?",
    "Brick ballast, plain concrete, sand filling and compacted mud are measured by volume (the area times the printed thickness). The cement-sand bed, brick tiles and mud plaster are measured by area, with the thickness printed in the label of the item.",
    PRACTICE, SUGGESTION,
    "Architectural_Drawings_10_Marla_House: the cement-sand bed under the floor finish (1 in, 1:3) is 126.37 m2 on the ground floor (page 6) and 114.74 m2 on the ground working plan (page 9); on the first floor 92.56 m2 (page 7) and 89.00 m2 (page 10). They are the room areas, the same as the other layers under the floor.",
    confirm="Does your bill price the cement-sand bed per square metre, or per cubic metre at the thickness?"),
  _p("P61-4", "L", "Mix on mortar and plain concrete lines", "Does the mortar behind plaster take the mix of the plaster, and does a bed take the mix printed for it?",
    "A line takes the mix the drawing prints for its work when it prints exactly one (plaster mortar, the plain concrete bed, the cement-sand bed). The mortar behind the plaster takes the mix of the plaster line it sits behind. The grades panel can give the printed mix to lines already accepted and take it back. The bill then shows one line for each mix.",
    PRACTICE, SUGGESTION,
    "Architectural_Drawings_10_Marla_House: the plain concrete bed prints 1:2:4 and the cement-sand bed 1:3 under every floor heading. Islamabad_Plot_1 prints a plain concrete bed 1:4:8 and no plaster mix.",
    confirm="Should the bill keep one line for each mortar mix, or one line for all the mortar?"),
  _p("P60-1", "L", "How high the waterproofing of a bath or toilet goes up the wall", "Is the waterproofing of a wet room the floor plus a turn-up, and how high is the turn-up?",
    "The floor of every bath and toilet plus 300 mm (1 ft) up the walls round it, less the doors. It is a line of its own (wet-area waterproofing). The walls above the turn-up, a shower area for one, are not in it.",
    PRACTICE, SUGGESTION,
    "Islamabad_Plot_1, ground floor: two baths, floor 5.85 m2, 12.4 m of wall less one door, 300 mm up: 9.57 m2. Architectural_Drawings_10_Marla_House, ground floor: floor 8.36 m2, waterproofing 12.57 m2. Neither drawing prints a turn-up height or a waterproofing line for the wet rooms.",
    confirm="Does the QS's sheet waterproof the floor of the baths only, or the floor and the walls up to a height? How high, and is the shower area carried higher?"),
  _p("P60-2", "L", "Which rooms have wall tile besides the baths, and how high", "A bath or toilet has a tile dado of 7 ft. Does a kitchen have wall tile, and how high?",
    "The kitchens (a kitchen on its own, not one shared with a dining or living space) get a wall tile line: the length round the kitchen less the doors, times a tile height that is typed when the item is accepted, less the part of each window inside that height. Nothing is assumed for the height, because the plan does not print it. The tile is not taken off the paint of the kitchen walls.",
    PRACTICE, SUGGESTION,
    "Islamabad_Plot_1, ground floor plan (page 1): kitchen 12.12 m of wall; on the sheet that shows all four plans, the ground-floor kitchen is 10.67 m with its 1524 x 914 mm window (sill assumed at 3 ft 6 in) to come off once the height is typed. Architectural_Drawings_10_Marla_House, ground floor (page 6): 11.73 m of wall. Neither drawing prints a kitchen tile height.",
    confirm="Is a kitchen tiled to a fixed height in your bills (2 ft above the counter, 4 ft, full height)? Is the tile taken off the kitchen paint?"),
  _p("P60-3", "L", "Windows inside the dado zone of a bath", "Does a window in a bath come off the tile dado, and where does its sill stand when the plan does not print it?",
    "The part of each window that is below the top of the dado (7 ft) comes off the dado. A window with no printed sill is taken with its sill at 5 ft in a bath or toilet (a ventilator) and at 3 ft 6 in in a kitchen. A window with no size on the plan or in a schedule is not taken off and the item says how many.",
    PRACTICE, SUGGESTION,
    "Islamabad_Plot_1, ground floor on the sheet that shows all four plans: one 914 x 610 mm ventilator with its sill assumed at 5 ft: 0.557 m2 off a dado of 25.66 m2, which is 25.11 m2. Architectural_Drawings_10_Marla_House, ground floor: 0.83 m2 off 33.49 m2. The inside paint of the same wall is no longer short by the window twice.",
    confirm="Does the QS take the window off the dado of a bath? What sill does he assume for a bath ventilator?"),
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
     
    "A free-standing wall has two faces. The area of both (length x height x 2, the gate taken out) is shown with the wall. Pack 62 makes the plaster and the paint of both faces lines of their own (P62-1), taking the side and rear walls with the front. Coping is not assumed.",
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
  _p("P48-1", "B", "Rooms closed across their doors", "The wall lines stop at every door and window, so most rooms are not closed polygons and were placed at their label as a box of the printed size. How is a room taken from the walls?",
    "The gaps of door and window width (up to 2.5 m) are bridged with a piece of the wall's thickness. A closed space is a room only when exactly one room label is inside it and its area is within 8% of the printed size; otherwise the label box is kept.",
    SOFTWARE, SUGGESTION, "Islamabad_Plot_1 plans 1 and 2: 5 and 6 of 10 rooms close and agree with their labels within 5%; the architectural plans: 3 of 9 and 3 of 8. The rest stay as label boxes.",
    confirm="Is the room area in your workbook taken inside the wall faces, or from the room size printed on the plan?"),
  _p("P48-2", "B", "Lintels in 4.5 inch walls and in RCC walls", "The lintel table prints one 9 inch wide section per span. What is the lintel over an opening in a 4.5 inch wall, and over an opening in an RCC wall?",
    "Over a 4.5 inch wall the lintel is as wide as the wall (4.5 in), with the table's depth and bars. An opening in an RCC wall gets no lintel: the wall is concrete.",
    PRACTICE, VALUE, "No lintel table is printed on the two drawings in hand, so this is checked on the walls and openings they do have (Islamabad_Plot_1, 4.5 and 9 inch brick walls and RCC walls) with a table fed in, not on a printed table.",
    confirm="Does your workbook make a lintel as wide as the wall in 4.5 inch walls, and leave openings in RCC walls without one?"),
  _p("P55-1", "B", "Sheets that are not floor plans", "A drawing set holds sections, elevations, details and specification sheets next to the plans. Walls, rooms and openings can be read from them too (hatching, drawn detail). What is done with them?",
    "They are read and shown, but their walls, rooms, doors, windows, lintels, stairs and wall-derived beams are held back from the bulk accept, and such a sheet takes no part in choosing the sheet of a floor. Each item can still be accepted by hand.",
    SOFTWARE, SUGGESTION, "Architectural_Drawings_10_Marla_House: the 14 sheets that are not plans (dividers, elevations, sections, details, specification) give 804 candidate items, 801 of them walls, rooms and wall-derived beams, a window and a lintel.",
    confirm="Should anything read from a section or an elevation ever go into the quantities, for example the heights, or only the plans?"),
  _p("P55-2", "B", "Furniture layout or working plan", "A floor is drawn twice: once as a furniture layout and once as the working plan. Which one is read for the quantities?",
    "The title block says which is which (FURNITURE LAYOUT against WORKING LAYOUT PLAN). The working plan is suggested for the floor and chosen when the person does not choose; the furniture layout is set aside, nothing is deleted and the choice can be turned round.",
    SOFTWARE, SUGGESTION, "Architectural_Drawings_10_Marla_House: sheets 6 to 8 are the furniture layouts and 9 to 11 the working plans of the ground, first and roof floors; before, each floor was offered as read from both, with nothing to choose.",
    confirm="Is the working plan always the one to measure from when a set also has a furniture layout?"),
  _p("P49-1", "B", "A stair drawn but its size not printed", "A plan draws a flight of steps with UP or DN beside it, but no sheet prints the riser, tread and number of steps of the stair. What is listed?",
    "The flight is listed as a stair with what is drawn (the width and the tread of the flight, the treads drawn) and left to be measured by hand. No riser, number of steps or waist is guessed, and nothing is quantified. It is not taken by the bulk accept.",
    SOFTWARE, SUGGESTION, "Architectural_Drawings_10_Marla_House: the set prints no stair detail at all (no riser, tread or number of steps on any of its 23 sheets), yet sheets 9 and 10 draw the stair of the stair hall, 3 ft 6 in wide; before, no stair was listed for the house.",
    confirm="When a set prints no stair detail, is a stair listed to be measured by hand enough, or should the riser and the number of steps be worked out from the storey height?"),
  _p("P49-2", "B", "A flight with only three treads drawn", "A stair that turns, or goes on as a dotted flight below the cut, shows only three or four clean treads. Four are needed to take a row of lines as a flight. When is three enough?",
    "Three treads are taken as a flight only where an UP or DN word that no other flight has stands within 2 m of them. Three parallel lines alone are never a stair.",
    SOFTWARE, SUGGESTION, "Islamabad_Plot_1 sheet 1: the stair beside the lounge (DN) shows three treads at 250 mm before it turns; it is the stair the basement draws going UP, which had no partner on the ground floor.",
    confirm="Is a stair that turns after three drawn treads normal in your drawings, and is UP or DN always written beside it?"),
  _p("P49-3", "B", "Plan run of a stair", "The detail prints the number of risers (steps) of the stair. The concrete is the plan run x the width x an equivalent thickness. What is the plan run?",
    "One tread fewer than the risers: the top riser meets the floor or the landing, so a stair of 18 risers has 17 treads (17 x 10 in), not 18. Landings are not included.",
    SOFTWARE, SUGGESTION, "Islamabad_Plot_1: the stair prints 'NO-Of RISER Steps:18', tread 10 in, riser 7 in; each flight draws 8 treads (two flights of 9 risers); the run was 18 x 254 = 4 572 mm and is now 17 x 254 = 4 318 mm, 5.6 percent less concrete per stair.",
    confirm="Does your workbook take the run of a stair as the risers less one, times the tread?"),
  _p("P49-4", "B", "Rise of the stair against the storey", "The stair prints the riser and the number of risers. The storey height is printed on the sections. Do they agree?",
    "The rise (risers x riser) is set beside the floor-to-floor height of the storey the stair serves; a gap of more than 3 percent is a warning on the stair. Nothing is changed by it.",
    SOFTWARE, SUGGESTION, "Islamabad_Plot_1: 18 x 177.8 mm = 3 200.4 mm, the floor-to-floor height of the ground and first floors read from the sections (3 200.4 mm): the stair agrees with its storey.",
    confirm="Is 3 percent the gap you would still accept between the rise of the stair and the storey?"),
  _p("P50-1", "B", "Anchorage and starter bars", "The drawing prints the cover and the lap table but no anchorage. How long is the anchorage of a beam bar into its support, and the starter bar of a column bar into its footing?",
    "40 bar diameters at each end of a beam bar and as the starter bar at the foot of a column bar. It is the usual development length of deformed bars in 3000 psi concrete (IS 456 cl. 26.2.1 gives 40 to 55 diameters by grade and concrete); the lap of a column bar stays what the lap table prints, else 40 diameters. The value is still marked assumed; type another to replace it.",
    PRACTICE, VALUE, "Islamabad_Plot_1 page 6 prints the cover (1.5 in), the lap table and the footing sections with a 'Dowel Length' label but no length. Before, the anchorage was 0, so a beam bar was as long as its clear run and a column bar had no starter; the steel review already priced 40 diameters as a what-if.",
    params=("bar_anchor_dia",),
    confirm="Does your workbook add 40 diameters of anchorage to a beam bar at each end and to a column bar at its foot, or another figure?"),
  _p("P50-2", "B", "Column bars read from the column detail", "The column detail draws the section with its bars and writes the bar note beside it. Are those bars the column's steel?",
    "The bars and rings written round a column detail (read from the text, else from the picture, each note read twice in the same place) are the steel of the column that carries its mark. A note on the sheet is kept; the detail fills what the note did not give. A detail that prints two different bar counts, or that differs from the note, applies nothing and lists the numbers.",
    SOFTWARE, SUGGESTION, "Islamabad_Plot_1 page 6: C-2 6-#6 with #3@6 in; C-4 8-#6 with #3@6 in; C-5 4-#5; the second C-3 detail 4-#6 and the first prints 8-#6 and 6-#6 at once (eight bars drawn), so C-3 is listed, not applied. Before, no column had its main bars: only the ring of C1 was read.",
    confirm="When one column detail prints two different bar counts, should the drawn bars be counted, or should the person always be asked?"),
  _p("P51-1", "B", "A printed note against the size drawn", "A note prints a thickness (a slab, a concrete wall) and the plan draws something a little different. Which one is measured?",
    "The drawn size is measured and the note is never applied over it. A drawn thickness within 10 mm (3/8 in) of the note agrees with it; a thicker or thinner one is listed under the note as a contradiction, with both numbers and the pages, for the person to settle. It is the usual rule of IS 1200: measure what is drawn, check it against what is written.",
    PRACTICE, KEPT, "Islamabad_Plot_1: the note '9\" Thick R.c.c Wall' (pages 4, 5, 6) agrees with the walls drawn 223 to 232 mm thick; the section label '6\" Thick R.c.c Slab' (page 5) does not agree with the slab items measured at 5 in from the plan note, and is listed.",
    confirm="Is 10 mm (3/8 in) the gap you would still call the same thickness, and do you want a larger gap to stop the item being accepted?"),
  _p("P51-2", "B", "A stair width printed beside a stair against the general note", "The sheet prints 'Stair Width = 3'-6\"' and a stair has 3'-0\" printed beside it. Which width is measured?",
    "The width printed beside the stair is measured for that stair, and the general note is listed as a contradiction. A figure written on the stair itself is the closer evidence; a general note is the fallback.",
    PRACTICE, KEPT, "Islamabad_Plot_1: the note on page 5 gives 3'-6\" (1 066.8 mm); the stairs on pages 1 and 4 are measured at 3'-0\" (914.4 mm) from the width printed beside them.",
    confirm="For a stair with its own width printed beside it, is the width beside it the one to bill, or the general note?"),
  _p("P51-3", "B", "A layer the specification prints but no item exists for", "The specification block prints a layer under a floor (a cement sand bed under the tiles). Is it billed?",
    "It is listed as 'no item is made' and is not in the bill. Only the layers that have a work item (the plain concrete bed, the brick ballast and the sand filling) are made, and a layer with no item is never guessed into the bill. This is a gap to close by giving the layer an item (the finishes pack), not by estimating.",
    SOFTWARE, HOLD, "Architectural_Drawings_10_Marla_House pages 6 and 9: the plain concrete bed, brick ballast and sand filling are made under the ground floor; the cement sand bed is printed and left out.",
    confirm="Is the cement sand bed under the floor finish billed as its own item, and in what unit (area or volume)?"),
  _p("P52-1", "B", "When a read should not be relied on", "A sheet was read with an older version of the reader, has no usable scale, or an accepted item has lost its measurement. Should the quantities still be used?",
    "They are shown, and the integrity panel says what to look at. Nothing is blocked and no quantity is changed: a sheet read by an older reader is flagged so it is read again before the bill is trusted, and a sheet with no scale gives no length or area at all.",
    SOFTWARE, KEPT, "The panel flags: a sheet read with a reader older than the code (the panel names the version), a scale taken from the title block and not confirmed by a measured dimension, an accepted item whose measurement was deleted, a sheet read from a scan, and a printed note the drawing contradicts.",
    confirm="Should the bulk accept be held back while the panel has something to look at, or is a warning enough?"),
  _p("P53-1", "A", "Where the wall height, the tie band and the lintel net are decided", "P43-1 and P44-1 wait for a person. Where is the choice made, and what happens to what was already read?",
    "On the drawing, on screen, in the Decisions panel; the choice is saved with the drawing. Until a person chooses, the default stays (floor to floor; the tie band and the roof band as one member; brick net of its lintels). A choice applies to the sheets read after it. A sheet read before it is listed, and read again on request. An item already accepted keeps the value it was accepted with, and the panel says how many those are.",
    SOFTWARE, KEPT, "Islamabad_Plot_1, four floors read with the defaults: brick 180.93 m3. Floor to floor against the plinth beam off the basement 176.38 m3 (-4.56), between the beams 171.42 m3 (-9.51), clear height 170.27 m3 (-10.67). Tie band and roof band as one member: 306.5 cft of band and lintel concrete; the tie band listed as well: 618.4 cft (+311.9). The brick net of 52 lintels: 2.97 m3 off.",
    confirm="Should a choice made for one drawing be offered as the default for the next drawing of the same project?"),
  _p("P57-1", "L", "Which openings come off each work item", "Does one rule decide which openings come off, whatever the work item, or has each work item its own?",
    "The default stays the QS sheet's single rule (an opening of 0.5 m2 or more comes off, a smaller one does not). A person can choose IS 1200 per work item for a drawing, in the Decisions panel. Under it: brickwork takes off every opening of 0.1 m2 or more (Part 3); an RCC wall every opening of 0.4 m2 or more (Part 5, clause 6.4, each opening, for the formwork; the concrete uses the same size so concrete and formwork agree, assumed); plaster and paint nothing under 0.5 m2, one face only from 0.5 to 3 m2, every face above 3 m2 with the reveals added to the inside (Part 12). The reveals of an opening that does not come off are not added to the wall formwork. Damp proof course is unchanged: the door widths come off, as before (no size rule found in IS 1200 for it).",
    PRACTICE, SUGGESTION,
    "Islamabad_Plot_1, four floors: no wall opening is under 0.5 m2 (the smallest is the 0.557 m2 ventilator), so brick and RCC wall do not change; plaster 4 252.8 m2 on the sheet's rule, 4 455.8 m2 under IS 1200 (+203.1), paint the same +203.1. Architectural_Drawings_10_Marla_House: one 914 x 508 mm window (0.465 m2) comes off the brick under IS 1200, +0.106 m3 less brick (a 9 in wall). Sources: IS 1200 Part 3 (brickwork), Part 5 clause 6.4 (formwork, 'each of opening', amendment 1) and Part 12 (plastering). The 0.1 m2 brick figure is taken from published summaries of Part 3, because the printed clause could not be read clearly; the concrete size of an RCC wall (Part 2) was not found, so the formwork size is used.",
    confirm="Does the QS's sheet take off an opening of 0.1 m2 or more from the brick, or only from 0.5 m2? Does it take plaster off one face for openings between 0.5 and 3 m2?"),
  _p("P58-1", "R", "Roof deck: turn-up at the parapet and the fall", "How high is the waterproofing membrane (and the screed over it) turned up the parapet, and how thick is the coba that gives the fall?",
    "The membrane and the screed are turned up 300 mm along the roof edge (the roof edge is the perimeter of the roof as printed), added to the roof area; the setting is roof_turnup_mm and 0 leaves it out. The coba is the average of the thin and the thick end when the drawing prints both (4 in to 7 in is 5.5 in, 139.7 mm), else the standard 100 mm. A thickness set in the run settings is used before either.",
    PRACTICE, SUGGESTION,
    "A membrane is carried up the parapet to at least 150 mm above the finished roof and chased into the wall, 300 mm being the usual height; the height is assumed here because the parapet detail of Architectural_Drawings_10_Marla_House prints 1'-6\", 1'-3\", 9\" and 3\" without tying one of them to the turn-up. Islamabad_Plot_1 roof (the mumty, 15 x 32 ft, 44.59 m2): 28.65 m of edge, 8.60 m2 of turn-up on the membrane and on the screed. The Islamabad set prints no fall, so its coba stays at 100 mm; the architectural set prints 4 in to 7 in (139.7 mm average, +39.7 mm on the standard).",
    confirm="Does the QS's sheet turn the membrane up the parapet, and to what height? Is the coba measured at the average of the thin and the thick end?"),
  _p("P59-1", "F", "Formwork joints: lintel on the wall, chajja, balcony", "Where the form of one member stops because another member is there, does the QS take that face off?",
    "Off by default, so nothing changes until a run turns on `formwork_joints`. When on: (1) the soffit of a lintel over its bearing on the wall takes no form (2 x the bearing, 152.4 mm each end, times the lintel width; a bearing is never more than half the lintel); (2) a chajja is cast with the lintel it springs from, so the outer side of that lintel is covered over the chajja's length by the chajja's thickness; (3) a balcony slab is cast with the floor slab, so that slab's edge is covered over the balcony's joined (longer) side by the thinner of the two thicknesses. The chajja and the balcony already leave their own joined side unshuttered. The plan does not say which lintel a chajja springs from or which slab a balcony joins, so they are matched by floor and flagged.",
    PRACTICE, SUGGESTION,
    "Formwork is the surface of concrete that touches the form: concrete resting on masonry, or cast together with the next member, has no form on that face. The bearing length is the 152.4 mm the lintel length already includes (span + 2 x bearing). Islamabad_Plot_1: 111 lintel marks read, 99.52 m2 of lintel formwork, of which 7.07 m2 (7.1 %) is soffit over the bearings. Neither set yet gives a chajja or a balcony slab as a measured item, so those two joints are tested on hand-made members only. I could not read the IS 1200 formwork clause itself, so this rests on the contact principle and not on a clause.",
    confirm="Does the QS's formwork for a lintel include the soffit over its bearing on the wall? Is the side of a lintel under a chajja measured whole or less the chajja's thickness? Is the edge of the floor slab at a balcony measured whole?"),
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
