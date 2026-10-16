from __future__ import annotations
import re

EXTRACT_VERSION = 20

LINTEL_BEARING_MM = 152.4
STAIR_WAIST_DEFAULT_MM = 152.4
PLINTH_BEAM_MIN_WALL_MM = 150.0
SLAB_SECTION_MIN_MM = 75.0
SLAB_SECTION_MAX_MM = 400.0
SLAB_SECTION_TOL_MM = 2.0
FOUNDATION_THIN_WALL_MAX_MM = 150.0
TRENCH_SIDE_ALLOWANCE_MM = 76.2
BRICK_STEPS_THICK = 4
BRICK_STEPS_THIN = 3
OUTER_WALL_TOL_FACTOR = 1.5
DOOR_FRAME_THIN_SHARE = 0.5

SUGGESTIONS = {
  "COLUMN": ("CON-RCC", "COUNT_X_VOLUME", "COUNT"),
  "FOOTING": ("CON-RCC", "COUNT_X_VOLUME", "COUNT"),
  "BEAM": (None, "DIRECT", "COUNT"),
  "DOOR": ("DOR-NOS", "DIRECT", "COUNT"),
  "WINDOW": ("WIN-NOS", "DIRECT", "COUNT"),
  "WALL": ("MAS-BRICK", "LENGTH_X_HEIGHT_X_THICKNESS", "LENGTH"),
  "ROOM": ("FIN-FLOOR", "DIRECT", "AREA"),
  "SLAB": ("CON-RCC", "COUNT_X_VOLUME", "COUNT"),
  "LINTEL": ("CON-RCC", "COUNT_X_VOLUME", "COUNT"),
  "STAIR": ("CON-RCC", "COUNT_X_VOLUME", "COUNT"),
}
CATEGORIES = tuple(SUGGESTIONS)

TAG_CATEGORIES = (
  ("COLUMN", re.compile(r"^(?:C|COL)[-.]?\d{1,3}[A-Z]?$")),
  ("FOOTING", re.compile(r"^(?:F|FT|FTG|PF|SF|IF|CF)[-.]?\d{1,3}[A-Z]?$")),
  ("BEAM", re.compile(r"^(?:B|BM|GB|PB|RB|LB)[-.]?\d{1,3}[A-Z]?$")),
  ("DOOR", re.compile(r"^(?:D|DR)[-.]?\d{1,3}[A-Z]?$")),
  ("WINDOW", re.compile(r"^(?:W|WN|WIN)[-.]?\d{1,3}[A-Z]?$")),
  ("WINDOW", re.compile(r"^(?:V|VENT)[-.]?\d{1,3}[A-Z]?$")),   
)

STANDARD_WALLS_MM = (75, 100, 115, 125, 150, 200, 230, 250, 300, 343, 350, 450)
WALL_T_MIN_MM = 95.0          
WALL_T_MAX_MM = 520.0
WALL_MIN_FACE_MM = 200.0
WALL_MIN_OVERLAP_MM = 300.0   
WALL_MIN_RUN_MM = 900.0       
WALL_GAP_MAX_MM = 2500.0      
WALL_GAP_CLEAR_MAX_MM = 3200.0
STAIR_MIN_TREADS = 4
STAIR_TREAD_TOL = 0.12
STAIR_LINE_MIN = 0.6
STAIR_LINE_MAX = 1.3
STAIR_ALIGN_PT = 2.5
STAIR_LABEL_REACH_MM = 6000.0
STANDARD_TOL = 0.04           
IMPERIAL_WALLS_MM = (76.2, 114.3, 152.4, 228.6, 342.9, 457.2)           
IMPERIAL_TOL = 0.06
TANK_LABEL = re.compile(r"O\.?\s?H\.?\s?W\.?\s?T|U\.?\s?G\.?\s?W\.?\s?T|\bTANK\b|SEPTIC|\bSUMP\b|MANHOLE", re.I)
TANK_REACH_MM = 2200.0        
TANK_MAX_MM = 7000.0
WALL_BRIDGE_MAX_MM = 1600.0   
WALL_STUB_MAX_MM = 2000.0     

MEMBER_MIN_MM = 100.0
MEMBER_MAX_MM = 2500.0
MEMBER_SEARCH_MM = 1200.0     
SIZE_TOL = 0.08               

ROOM_MIN_M2 = 1.2
ROOM_MAX_M2 = 800.0
ROOM_SIZE_TOL = 0.08          
ROOM_NAMES = (
  "BED ROOM", "BEDROOM", "BED", "MASTER BED", "GUEST ROOM", "KIDS ROOM", "DRAWING ROOM", "DRAWING", "DINING", "LOUNGE", "LIVING", "TV LOUNGE",
  "FAMILY", "KITCHEN", "KIT", "PANTRY", "STORE", "STORAGE", "TOILET", "BATH ROOM", "BATHROOM", "BATH", "W.C", "WC", "W/C", "LAVATORY", "LAUNDRY",
  "UTILITY", "SERVANT", "MAID", "DRIVER", "GARAGE", "PORCH", "CAR PORCH", "LOBBY", "PASSAGE", "CORRIDOR", "HALL", "ENTRANCE", "FOYER",
  "STAIR", "STAIRCASE", "STUDY", "SITTING", "OFFICE", "PRAYER", "VERANDAH", "VERANDA", "BALCONY", "TERRACE", "LIFT", "DRESSING", "WARDROBE", "LIBRARY",
  "SHOP", "RECEPTION", "ROOM", "MEETING", "CABIN", "CLASS ROOM", "CLASSROOM", "LAB", "WARD", "OPD", "MOSQUE", "COURTYARD", "LAWN", "SERVICE",
)

HEIGHT_NOTES = (
  ("WALL", re.compile(r"\b(?:WALL|CLEAR|ROOM|CEILING)\s+HEIGHTS?\b\s*[:=\-]?\s*(?P<v>.{1,24})", re.I)),
  ("COLUMN", re.compile(r"\b(?:COLUMN\s+HEIGHT|FLOOR\s+TO\s+FLOOR(?:\s+HEIGHT)?|STOREY\s+HEIGHT|STORY\s+HEIGHT)\b\s*[:=\-]?\s*(?P<v>.{1,24})", re.I)),
)

NOTES = {
  "SCALE_UNVERIFIED": ("warning", "The scale of this sheet is not checked against a printed dimension, so every size here is only as good as that scale."),
  "THICKNESS_OFF_STANDARD": ("warning", "The drawn thickness is not a standard wall size. Check it before measuring."),
  "WALL_OPENINGS_INCLUDED": ("info", "The length runs through the door and window openings. Deduct the openings in the measurement."),
  "WALL_WIDE_OPENING": ("info", "The wall runs through an opening wider than 2.5 m with nothing drawn in it, so it is counted as one wall. Deduct the opening when you measure."),
  "WALL_BRIDGED": ("info", "The wall lines stop at an opening (a door or window) and the wall runs on to the cross wall. The length includes that opening."),
  "TANK_WALL": ("info", "These walls close in a tank (a tank label is inside them). They are listed so nothing is lost, but they are tank work, not part of the building walls."),
  "OPENINGS_ASSIGNED": ("info", "The doors, windows and ventilators marked beside this wall are listed with it and are deducted when the wall is measured. Check that each belongs to this wall."),
  "RCC_WALL_COMPLETES_ENCLOSURE": ("warning", "The concrete walls of this basement are drawn solid on three sides, and a note on the sheet calls the walls concrete. This stretch of the fourth side (or the end of a side) is drawn thin or not at all, but a retaining wall has to go round the building, so it is listed here to confirm. It is not counted in the trench, membrane or plaster items. Accept it only if the plan or the sections show a concrete wall here."),
  "NECK_COLUMN_FROM_FOOTINGS": ("warning", "Each footing carries a column up to the lowest floor. This is that stretch (the neck column). Its section is the section of the column mark that has as many columns as this footing mark; check the pairing. The height is the depth from the top of the footing to the floor and is not printed: type it when you accept the item."),
  "LINTEL_OVER_UNMARKED_OPENING": ("warning", "The wall is open for this width but no door, window or ventilator mark is written in the opening. A lintel is still needed over it, so one is listed, sized from the lintel table for this span. Check that the opening is real (not a drawing gap) and that it is not an arch or a beam that is measured elsewhere."),
   "BEAM_SECTION_FROM_DETAIL": ("info", "The depth (and the bars, if they were read) are those of the one beam section of this kind printed on the structural sheet. They were read from the drawing picture, so check them against the detail."),
  "BEAM_SECTIONS_LISTED": ("warning", "The structural sheet prints more than one beam section of this kind and does not say which lies under which wall, so no depth was chosen. The sections are listed below; type the depth of the one that applies when you accept the beam."),
  "TANK_SECTIONS_LISTED": ("info", "The structural sheet draws this tank in a plan and a section. The sizes are listed below: those written as text in the PDF are exact; those read from the picture show the number of readings that agreed (a size read only twice can be a misreading, so check it on the drawing). The drawing does not say which size is the inside depth, which is the water level and which is the wall, so none is applied: type the height and thickness from them when you accept the wall."),
  "OPENING_GAP_IS_ANOTHER_MARK": ("warning", "At least one of these marks stands beside a gap in a wall that is exactly the width of a different mark of the same kind, and is not the width of this mark. Either the mark was read wrongly or the wrong mark is drawn. Check the mark on the plan before accepting the count."),
  "RCC_WALL_FROM_FILL": ("info", "This wall is drawn as a solid black strip, so it is a concrete wall (a retaining wall below ground), not brick."),
  "SIZE_FROM_SCHEDULE": ("info", "The size comes from the schedule on the drawing."),
  "SIZE_DIFFERS_FROM_SCHEDULE": ("warning", "The drawn size is different from the schedule. The schedule size is used."),
  "COLUMN_SIZE_FROM_PLAN": ("info", "The size is measured from the black square drawn on the plan. A column detail or schedule may give a larger section; check it before measuring."),
  "SIZE_FROM_DETAIL": ("info", "The size is printed under a footing section detail of this drawing."),
  "FOOTING_SIZE_ORDER_ASSUMED": ("warning", "The footing details print sizes but not which footing mark each belongs to. Marks and sizes were paired in order (the lowest mark takes the smallest size). Check the pairing."),
  "FOOTING_SIZES_LISTED": ("warning", "The footing details print more or fewer sizes than there are footing marks, so no size was chosen. Pick the size for this mark."),
  "RUNS_OUTSIDE_CONCRETE_WALLS": ("info", "Brick wall lines that lie outside the concrete walls enclosing the building (plot lines, lines drawn on past the building) were left out. Check the sheet if a wall of the building is missing."),
  "SIZE_FROM_OTHER_VIEW": ("info", "No black square of this column mark could be measured on this plan (the columns are drawn inside the wall). The size seen for the same mark on the other plans is used."),
  "SIZE_FROM_COLUMN_DETAIL": ("info", "The size is the one written beside this mark's column detail drawing. It was read from the drawing picture, so check it against the detail."),
  "COLUMN_PLAN_VS_DETAIL": ("info", "The black square on the plan is another size than the column detail of this mark. The detail size is used (the plan square is a symbol)."),
  "COLUMN_DETAILS_DISAGREE": ("warning", "Two column details carry this mark with different sizes, so none was used. Check which detail is this column."),
  "UNMARKED_COLUMNS": ("warning", "These black squares have no column mark beside them. They are counted as columns because of their size. Check them."),
  "VIEW_SCALE_DIFFERS": ("warning", "The dimensions printed inside this drawing show another scale than the sheet. Sizes measured from it may be wrong. Calibrate this view on the Measure page."),
  "SIZE_VARIES": ("warning", "The shapes drawn for this mark are not all the same size."),
  "SIZE_NOT_FOUND": ("info", "No drawn shape or schedule row gave a size for this mark."),
  "COUNT_DIFFERS_FROM_DRAWN": ("warning", "The number of marks is not the number of matching shapes drawn on the sheet."),
  "UNTAGGED_SAME_SIZE": ("warning", "More shapes of this size are drawn than there are marks. Some may be missing a mark."),
  "BEAM_LENGTH_NOT_READ": ("info", "Beam marks are counted only. Measure the beam lengths with the length tool or from the beam schedule."),
  "ROOM_NO_LABEL": ("warning", "No room name was found inside this outline."),
  "ROOM_MULTIPLE_LABELS": ("warning", "More than one room name is inside this outline. It may be an open plan area."),
  "ROOM_SIZE_MISMATCH": ("warning", "The size printed in the room label gives another area than the outline."),
  "ROOM_INSIDE_ROOM": ("warning", "This room lies inside the outline of another room, so its area is counted in both. Check which one is right before the room areas are added up."),
  "ROOM_FROM_OUTLINE": ("warning", "This room was taken from a drawn outline, not from the wall layout."),
  "ROOM_FROM_LABEL": ("info", "The area is the size printed in the room label. The walls around this room did not close on their own, so the box is placed at the label."),
  "ROOM_OUTLINE_REPLACED": ("info", "The walls drawn around this label gave another area than the printed size, so the printed size is used."),
  "SLAB_AREA_FROM_TABLE": ("info", "The slab area is the covered area of this floor printed in the area table of the drawing, taken as one rectangle (its printed length x width). Openings in the slab (a stair well, a shaft) are not deducted and cantilevers beyond the covered area (sunshades, porch roofs) are not added. Check both against the framing plan."),
  "SLAB_SIZE_NOT_PRINTED": ("warning", "The area table gives the covered area of this floor but not its length and width, so the slab cannot be measured from it. Measure the slab with the area tool."),
  "SLAB_THICKNESS_DISAGREES": ("warning", "The slab note on the framing plan and another sheet of the drawing print different slab thicknesses. The framing plan note is used unless you type another thickness when you accept the slab. Check which one is right before measuring."),
  "SLAB_THICKNESS_FROM_OTHER_SHEET": ("info", "This framing plan has no slab note. The slab thickness printed elsewhere on the drawing is used."),
  "SLAB_THICKNESSES_LISTED": ("warning", "This framing plan has no slab note and the drawing prints more than one slab thickness, so none was chosen. Pick the thickness for this slab."),
  "SLAB_THICKNESS_SECTIONS": ("info", "The building sections of the drawing give a floor-to-floor height and a clear storey height; their difference is the slab thickness they imply. It is a second witness for this slab, not a decision: type the thickness you want to measure with."),
  "BEAM_FROM_WALLS": ("info", "This beam is not drawn on the plan. It is worked out from the walls measured on this floor: a beam runs on top of each brick wall, as wide as the wall, over the whole wall length. The section printed on the drawing is not read."),
  "BEAM_OVER_OPENINGS": ("info", "The length is the full length of the walls, door and window openings included, because the beam runs on over them."),
  "PLINTH_BEAM_UNDER_9IN": ("info", "A plinth beam is taken under the brick walls of 6 inches or more on the lowest floor. Walls thinner than that and concrete walls get none."),
  "SLAB_PROJECTIONS_ADDED": ("info", "The plans of this floor print roof projections (the slab reaches past the walls). They are added to the covered area of the floor on the sides where they are printed, corners included, so this slab is the plan outline plus its projections, as a quantity surveyor takes it. The widths are printed; which side each belongs to is read from where its label sits on the plan."),
  "SLAB_PROJECTION_UNPLACED": ("warning", "A roof projection label of this floor sits too near the middle of the page for its side to be read, so it was not added to the slab. Check which side it belongs to."),
  "SLAB_PROJECTION_CONFLICT": ("warning", "The plans of this floor print different roof projection widths for the same side, so that side was not added to the slab. Check the drawing."),
  "SLAB_PROJECTION_AXIS_UNKNOWN": ("warning", "The plans of this floor print roof projections, but the overall lengths printed on them do not match the area table's length and width, so it is not known which sides they widen. They were not added to the slab."),
  "SLAB_AREA_NOT_FOUND": ("warning", "This framing plan shows a slab but the drawing's area table has no covered area for this floor, so the slab was not listed. Measure it with the area tool."),
  "LINTEL_SECTION_FROM_TABLE": ("info", "The lintel section is the row of the lintel table printed on the drawing that holds this opening's width. The length is the opening width plus the bearing on each side."),
  "SLAB_PROJECTION_CONFLICT": ("warning", "The plans of this floor print different roof projection widths for the same side, so that side was not added to the slab. Check the drawing."),
  "SLAB_PROJECTION_AXIS_UNKNOWN": ("warning", "The plans of this floor print roof projections, but the overall lengths printed on them do not match the area table's length and width, so it is not known which sides they widen. They were not added to the slab."),
  "FOUNDATION_FROM_WALLS": ("info", "This item is not drawn on the plan. It is worked out from the walls measured on the lowest floor: a strip as long as the walls of this thickness laid end to end, concrete walls included, tank walls left out."),
  "FOUNDATION_WIDTH_TYPED": ("warning", "The widths of the footing strips are drawn on the footing section details as dimension lines, not as text that can be read. Type the width of the strip under walls of this thickness when you accept the item. Walls of the same thickness take one width, whether they stand on the outside of the plan or inside."),
  "TRENCH_WORKING_SPACE_ASSUMED": ("warning", "The trench is taken 3 inches wider than the concrete bed on each side. The drawing does not print the working space; change the width of the measurement if your practice differs."),
  "TERMITE_BOTTOM_ONLY": ("info", "Termite treatment is taken on the bottom of the trench only, as wide as the concrete bed. The sides of the trench are not included."),
  "TERMITE_NO_WORK_ITEM": ("info", "The work item catalog has no termite treatment item, so this measurement is left without one. Assign it when you build the bill."),
  "EXCAVATION_AREA_FROM_OUTLINE": ("info", "The area is the covered area of the basement printed in the area table, widened by the roof projections printed on the plans (the same outline as the basement slab). The depth is not printed; type the depth dug over the whole building."),
  "EXCAVATION_OVERLAPS_FOOTING_PITS": ("info", "If you also give the level of the footing bottom when you calculate, the footing pits the calculation derives start at natural ground, so they overlap this dig. Take the pits from one of the two, not both."),
  "UNDER_FLOOR_FROM_ROOMS": ("info", "The area is the total of the room areas found on this floor. Walls and the area under them are not included; they are taken in the wall strips."),
  "PCC_PAD_FROM_FOOTINGS": ("info", "The concrete bed under each footing is taken as large as the footing it carries, as many beds as there are footings of this mark. The bed thickness is printed on the footing section details as a dimension line; type it when you accept the item."),
  "NO_WORK_ITEM": ("info", "The work item catalog has no item for this, so this measurement is left without one. Assign it when you build the bill."),
  "BRICK_STEPS_ASSUMED": ("warning", "The steps of the brick foundation are drawn on the footing section details as dimension lines, not as text that can be read. Four steps are listed under walls of 6 inches and thicker and three under thinner walls, as is usual for a stepped footing. Reject the steps your section does not show, and type the height of each step and how much each step is narrower than the one below it when you accept."),
  "BRICK_STEPS_BRICK_ONLY": ("info", "The steps run under the brick walls only. Concrete walls of the same thickness stand on their own footing and are left out."),
  "MEMBRANE_FROM_WALLS": ("info", "This item is not drawn on the plan. It is the damp-proof membrane along the top of the plinth under all the walls of the lowest floor laid end to end, concrete walls included, tank walls left out. The width of the membrane is not printed as text; type it when you accept the item."),
  "KACHA_FROM_ROOMS": ("info", "The area of the concrete or kacha bed under the floor is the total of the room areas found on this floor. The walls and the area under them are not included."),
  "CEILING_FROM_ROOMS": ("info", "The area of the ceiling plaster is the total of the room areas found on this floor. The undersides of the roof projections are not included; they are on the slab sheet."),
  "PLASTER_FROM_WALLS": ("info", "This item is not drawn on the plan. It is worked out from the walls measured on this floor: the length of each wall, centre to centre, times its height, less the doors and windows set in it, for every face that is plastered."),
  "PLASTER_OUTER_BY_OUTLINE": ("warning", "A wall is taken as an outer wall when it lies on the outline of the walls of this floor. An outer wall has one inside face and one outside face; any other wall has two inside faces. A wall set back from the outline is taken as an inside wall. Check this against the plan."),
  "PLASTER_OUTSIDE_SEPARATE": ("info", "The outside faces of the outer walls are a separate item, so that you can accept them on the floors where outside plaster is part of the bill and reject them where it is not."),
  "PLASTER_HEIGHT_FROM_WALLS": ("info", "The height of each wall is the height found for it. Where it was not found, type the wall height when you accept the item."),
  "DOOR_FRAME_FROM_DOORS": ("info", "The frame area is the two sides and the top of the door (two heights plus one width) times the width of the frame, for every door of this mark. The width of the frame is not printed as text; type it when you accept the item."),
  "DOOR_FRAME_WIDTH_BY_WALL": ("warning", "The frame is as wide as the wall it stands in. Doors of this mark were found mostly in walls of this class, so the matching frame width is asked for. Check it against the plan."),
  "SLAB_AREA_NOT_FOUND": ("warning", "This framing plan shows a slab but the drawing's area table has no covered area for this floor, so the slab was not listed. Measure it with the area tool."),
  "LINTEL_SECTION_FROM_TABLE": ("info", "The lintel section is the row of the lintel table printed on the drawing that holds this opening's width. The length is the opening width plus the bearing on each side."),
  "SCAN_TEXT_READ": ("warning", "This sheet is a scan and its text was read by character recognition. A tag, size or figure may be misread, so check it against the drawing before accepting."),
  "LINTEL_STEEL_FROM_TABLE": ("info", "The bars and rings of this lintel are the reinforcement printed on the same row of the lintel table. Steel weight is worked out from them when the run is calculated."),
  "STEEL_FROM_DETAIL": ("info", "The bars, rings or mesh of this member are the reinforcement printed in the detail or note for its mark. Steel weight is worked out from them when the run is calculated, using the cover, hook, lap and anchorage in the site assumptions."),
  "STEEL_NOT_PRINTED": ("info", "No reinforcement note could be tied to this member on the sheet. Type the bars when you accept it, or no steel is taken for it."),
  "STEEL_DETAILS_DISAGREE": ("warning", "Two details on the drawing print different reinforcement for this mark, so none was chosen. Type the bars you want when you accept it."),
  "STAIR_FROM_DETAILS": ("info", "The staircase is sized from the riser, tread, width and number of steps printed on the drawing. The concrete is measured as the plan run of the steps x the width x an equivalent thickness (the waist slab along the slope plus half a riser)."),
  "STAIR_WAIST_ASSUMED": ("warning", "The drawing does not print the thickness of the waist slab under the steps. 6 inches (152.4 mm) is assumed. Change the depth if the stair section says otherwise."),
  "STAIR_LANDINGS_NOT_INCLUDED": ("info", "Landings and the slab where the stair starts are not part of this quantity. Measure them as slabs."),
  "STAIR_LOCATED_BY_TREADS": ("info", "This staircase was found from its treads drawn on the plan. The plan may stop drawing the treads at the cut line, so the steps of the whole stair come from the printed detail."),
  "STAIR_DOWN_FLIGHT": ("warning", "This flight is marked DN. It is the same staircase as the UP flight on the floor below. Accept it only once, on one of the two plans."),
  "STAIR_DIRECTION_UNKNOWN": ("info", "No UP or DN is written beside this staircase. Check on the plan whether it is the same staircase as one on another floor."),
  "STAIR_WAIST_NEEDED": ("warning", "The drawing does not print the thickness of the waist slab under the steps. Type it when you accept the stair."),
  "STAIR_COUNT_FROM_LABELS": ("info", "The number of staircases is the number of times this plan names a staircase. Check it against the plan."),
  "STAIR_DETAILS_INCOMPLETE": ("warning", "The drawing prints some of the stair details (riser, tread, width, number of steps) but not all of them, so the stair cannot be sized. Type the missing size when you measure it."),
  "STAIR_DETAILS_NOT_FOUND": ("info", "This plan shows a staircase but no sheet of the drawing prints its riser, tread, width and number of steps. The staircase was not listed. Measure it by hand."),
  "LINTEL_BEARING_ASSUMED": ("info", "The drawing does not print how far a lintel bears on the wall at each end. 6 inches (152.4 mm) is assumed on each side. Change it if your practice differs."),
  "LINTEL_SPAN_ABOVE_TABLE": ("warning", "This opening is wider than every row of the lintel table, so no lintel section was chosen. Type the section when you measure it."),
  "LINTEL_IN_THIN_WALL": ("warning", "Some of these openings sit in 4.5 inch walls. The lintel table is 9 inches wide, so check the section for those."),
  "LINTEL_IN_RCC_WALL": ("info", "Some of these openings sit in RCC walls, which need no separate lintel. The count includes them; reduce it if you measure."),
  "HEIGHT_FROM_NOTE": ("info", "The height comes from a note on the drawing."),
  "COUNT_MATCHES_OTHER_FLOOR": ("info", "Fewer columns of this size are drawn than there are marks (some are hidden inside the walls), but the same marks and the same number appear on another floor where every column is drawn. The marks are counted."),
  "HEIGHT_FROM_SECTION": ("info", "The height is the clear storey height printed on the building section (slab to slab, as dimensioned there). Check that it is the height you want to measure with."),
  "WALL_PEN_SELECTED": ("info", "Walls were read from the heaviest line weight on this sheet. Lines in lighter weights (dimensions, furniture, fittings, boundary lines) were not read as walls."),
  "LIGHT_PEN_WALLS_KEPT": ("info", "Some walls on this ground-level sheet are drawn in a lighter line weight than the main walls (boundary, lawn and thin partition walls). The long ones of 4.5 to 6 inch thickness were read as walls. Stair treads and furniture lines were not."),
  "LIGHT_PEN_WALL": ("info", "This wall is drawn in a lighter line weight than the main walls on the sheet. Check it is a wall and not a boundary line."),
  "STRUCTURAL_SHEET": ("info", "This looks like a foundation, column, beam or roof sheet, so walls and rooms were not read from it. Read them from the floor plan."),
  "SAME_MARK_ON_OTHER_SHEET": ("info", "This mark is also on another sheet of the same drawing. It is listed once in the element register."),
  "TIME_LIMIT": ("warning", "Reading this sheet took too long and some items may be missing. Read it again."),
  
  "SCALE_CONFLICT": ("warning", "Conflicting scale information was found on the sheet. Confirm the correct scale before relying on measured sizes."),
  "DIMENSION_CONFLICT": ("warning", "Conflicting dimension values were found for this item. Verify which dimension should be used."),
  "SCHEDULE_MARK_NOT_FOUND": ("warning", "A drawing mark has no matching entry in the available schedule."),
  "SCHEDULE_DUPLICATE_MARK": ("warning", "Multiple schedule entries match this mark. Confirm which entry applies."),
  "DIMENSION_INCOMPLETE": ("warning", "One or more dimensions required to measure this item could not be established."),
  "MEMBER_MATCH_AMBIGUOUS": ("warning", "More than one drawn shape is a plausible match for this member mark. Confirm the correct shape."),
}

def note(code: str, **extra) -> dict:
  sev, msg = NOTES[code]
  out = {"code": code, "severity": sev, "message": msg}
  out.update(extra)
  return out
