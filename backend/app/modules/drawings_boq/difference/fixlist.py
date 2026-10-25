from __future__ import annotations

ARCHITECT, QS, TRACE = "ARCHITECT", "QS", "TRACE"
AUDIENCES = (ARCHITECT, QS, TRACE)
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
LEDGER_CAP = 50

ASK = {
  "OPENING_SIZE_MISSING": ("Door and window sizes", "Give the width and height of the doors and windows {places}, so that they can be taken out of the walls and finishes."),
  "SPEC_THICKNESS_MISSING": ("Masonry wall thickness", "State the thickness of the masonry walls {places} (115, 230 and so on)."),
  "SPEC_MORTAR_MISSING": ("Mortar ratio", "State the mortar ratio of the masonry walls {places} (for example 1:6)."),
  "SPEC_MIX_MISSING": ("Concrete mix", "State the concrete mix or grade of the members {places} (for example 1:2:4 or M20)."),
  "MATERIAL_GENERIC": ("Material not stated", "Name the material of the elements {places} (for example brick, or concrete C25)."),
  "STEEL_BARS_NOT_PRINTED": ("Bars not printed", "Print the reinforcement (bars, spacing, rings) of the {count} members whose bars are not on the drawing, or send the bar schedule."),
  "STEEL_ESTIMATED": ("Bars not printed, steel estimated", "Print the reinforcement of the {count} members whose bars are not on the drawing, or send the bar schedule; their steel is an estimate until then."),
  "STEEL_NOT_ESTIMATED": ("Bars not printed, no usual figure", "Print the reinforcement of the {count} walls, stairs, tanks or parapets whose bars are not on the drawing; there is no usual figure to estimate them from."),
  "STEEL_NOT_MEASURED": ("Steel members with no size", "Give the size or length of the {count} steel members {places}, or send the bar schedule."),
  "STEEL_MATERIAL_UNCERTAIN": ("Steel material", "State the material (steel grade) of the members {places}; the model says only metal or iron."),
  "STEEL_SOLID_SECTION_SUSPECTED": ("Steel section", "Confirm the section of the steel members {places}: they are drawn solid and may be hollow or rolled sections."),
  "STEEL_DUPLICATE_SUSPECTED": ("Possible duplicate steel member", "Confirm whether both steel members {places} exist, or remove the duplicate."),
  "STEEL_INTENSITY_OUT_OF_RANGE": ("Steel looks too light or too heavy", "Check the bars and the member sizes {places}; the steel per cubic metre of concrete is outside the usual range."),
  "DUPLICATE_SOLID": ("Duplicate element", "Remove the duplicate elements {places} from the model, or say why both are there."),
  "SAME_ROLE_OVERLAP": ("Overlapping elements", "Check the elements {places} that overlap each other in the model."),
  "SPACE_SAME_ROLE_OVERLAP": ("Same member drawn twice", "Confirm that the walls or beams {places} are not drawn twice."),
  "ELEMENT_NOT_MEASURED": ("Elements with no quantity or size", "Correct the model: the {count} elements {places} have no quantity or dimensions, or a material that cannot be measured."),
  "UNIT_SCALE_AMBIGUOUS": ("Length unit", "Export the model with its length unit stated; metres were assumed."),
  "LAYER_THICKNESS_MISMATCH": ("Layer thicknesses", "Check the layer thicknesses of the walls {places}; they do not add up to the width of the wall."),
  "PILE_WEIGHT_NOT_COMPUTED": ("Steel pile section", "Give the wall thickness or the section of the steel piles {places} if a weight is wanted."),
  "DERIVED_NEEDS_FOOTING_LEVEL": ("Depth of footings", "Give the depth of the footing bottom below natural ground level; without it the excavation, PCC and backfill of the footings {places} cannot be worked out."),
  "DERIVED_NGL_ASSUMED": ("Natural ground level", "Give the natural ground level (how far it is below the floor level); the excavation was worked out from an assumed level."),
  "DPC_LEVEL_ASSUMED": ("Damp-proof course level", "Give the level of the damp-proof course; it was assumed."),
  "DATUMS_ASSUMED": ("Reference levels", "Give the reference levels the stages of work stand on (damp-proof course, lintel, slab); they were assumed."),
  "DATUM_DEFAULTED": ("Reference levels", "Give the damp-proof course level and the lintel height; the stage a quantity falls in depends on them."),
  "STAGE_DATUM_DEFAULTED": ("Reference levels", "Give the damp-proof course level and the lintel height; the stage a quantity falls in depends on them."),
  "SPACE_NO_HEIGHT": ("Floor levels", "Give the floor levels, the lintel head or the footing level for the members {places}; their height is not known."),
  "PDF_DIMENSION_ASSUMED": ("Heights and thicknesses not on the drawing", "State the height or thickness that is not on the drawing for the measurements {places}; a standard value was assumed."),
  "PDF_MODEL_VARIANCE": ("Model and drawing disagree", "Confirm which is current, the model or the drawing, for the work items where they differ."),
  "PDF_SCANNED_LOW_PRECISION": ("Scanned sheets", "Send the vector PDF of the scanned sheets; measurements picked from a scan are less precise."),
  "FORMWORK_TANK_NO_DETAIL": ("Tank details", "Give the outside height and wall thickness of the {count} tanks."),
  "WALL_FINISH_SIDES_ASSUMED": ("Which face of the wall is outside", "State which face of the walls {places} is outside; both faces were given the same finish."),
}

QS_CODES = frozenset({
  "STEEL_ASSUMED", "FORMWORK_ASSUMED", "DERIVED_ASSUMED", "FORMWORK_ITEM_ASSUMED", "FORMWORK_BEAM_SLAB_ASSUMED", "FORMWORK_JOINT_ASSUMED", "FORMWORK_FRAME_ASSUMED", "DERIVED_MARK_POSITION",
  "DERIVED_ELEMENT_OVERRIDE", "EXCAVATION_BALANCE", "LAP_LENGTH_UNKNOWN", "FORMWORK_FOOTING_NOT_SHUTTERED", "FORMWORK_CONTACT_NOT_DEDUCTED", "FORMWORK_SHARED_TAKEN_OFF",
  "STEEL_LAP_WASTAGE_NOT_ADDED", "PDF_MEASUREMENT_NOT_COUNTED", "PDF_MEASUREMENT_UNASSIGNED", "PDF_MEASUREMENT_SKIPPED", "PDF_UNCALIBRATED", "PDF_RATIO_UNVERIFIED",
  "PDF_CAL_SHORT_BASELINE", "PDF_LOW_PRECISION", "PDF_SCALE_MISMATCH", "SCHEDULE_OVERLAPS_MODEL", "SCHEDULE_LOW_CONFIDENCE", "DATUM_OVERRIDE_UNUSED", "ELEMENT_OVERRIDE_UNMATCHED",
  "DPC_NOT_MEASURED", "DPC_VERTICAL_NOT_TAKEN", "STEEL_NOT_RUN", "FORMWORK_NOT_RUN", "DERIVED_NOT_RUN", "STAGES_NOT_DERIVED",
})

TRACE_CODES = frozenset({
  "UNMAPPED_ELEMENT_TYPE", "ROLE_NOT_MEASURED", "WORK_ITEM_NOT_IN_CATALOG", "WORK_ITEM_UNIT_MISMATCH", "RATE_UNIT_MISMATCH", "UNPRICED_ITEM", "RATE_ZERO_ITEM", "ADJUSTMENT_ORPHANED",
  "LAYER_UNPRICED", "LAYER_NOT_SPLIT", "FINISH_SKIPPED", "REBAR_ROW_SKIPPED", "NOT_ALLOCATED", "ALLOCATION_APPROXIMATE", "QTO_FALLBACK", "LOW_CONFIDENCE_GEOMETRY",
  "GEOMETRY_INCOMPLETE", "UNSUPPORTED_GEOMETRY", "ZERO_NET_QUANTITY", "OVER_DEDUCTED", "DPC_DOOR_NOT_DEDUCTED", "STAGE_NOT_SPLIT", "STAGE_UNRESOLVED",
  "STAGE_DEDUCTION_APPORTIONED", "DERIVED_BOX_FOOTPRINT", "BACKFILL_NEGATIVE", "NON_CONSERVING_ALLOCATION", "UNALLOCATED_OVERLAP",
})

def audience_of(code: str) -> str:
  if code in ASK:
    return ARCHITECT
  if code in TRACE_CODES:
    return TRACE
  return QS

def _count(details: dict) -> int:
  for k in ("count", "members", "marks", "waiting"):
    v = (details or {}).get(k)
    if isinstance(v, bool):
      continue
    if isinstance(v, (int, float)) and v > 0:
      return int(v)
  ids = (details or {}).get("ledger_ids")
  return len(ids) if isinstance(ids, list) else 0

def _words(places: dict, count: int) -> str:
  levels, marks = places.get("levels") or [], places.get("marks") or []
  parts = []
  if marks:
    parts.append("marked " + ", ".join(marks[:8]) + (f" and {len(marks) - 8} more" if len(marks) > 8 else ""))
  if levels:
    parts.append("on " + ", ".join(levels[:6]) + (f" and {len(levels) - 6} more storeys" if len(levels) > 6 else ""))
  if parts:
    return " ".join(parts)
  return f"(the {count} listed)" if count else "listed"

def entry_of(issue: dict, places: dict | None = None) -> dict:
  code, details = issue["code"], issue.get("details") or {}
  places = places or {}
  tags = [str(t) for t in details.get("tags") or [] if isinstance(t, (str, int))] if isinstance(details.get("tags"), list) else []
  places = {**places, "marks": list(dict.fromkeys((places.get("marks") or []) + tags))}
  count = _count(details)
  topic, template = ASK.get(code, (None, None))
  audience = audience_of(code)
  
  ask = template.format(count=count or "some", places=_words(places, count)).replace("  ", " ") if template else (issue.get("suggested_fix") or issue.get("message") or "")
  return {"id": issue.get("id"), "code": code, "audience": audience, "severity": issue.get("severity") or "warning", "blocks": issue.get("blocks") or "NONE",
    "topic": topic or code.replace("_", " ").capitalize(), "ask": ask, "why": issue.get("message") or "", "count": count,
    "levels": places.get("levels") or [], "marks": places.get("marks") or [], "work_items": places.get("work_items") or [], "suggested_fix": issue.get("suggested_fix") or ""}

def fix_list(issues, places: dict | None = None) -> dict:
  entries = [entry_of(i, (places or {}).get(str(i.get("id")))) for i in issues]
  entries.sort(key=lambda e: (AUDIENCES.index(e["audience"]), SEVERITY_ORDER.get(e["severity"], 3), -e["count"], e["code"]))
  for n, e in enumerate(entries, 1):
    e["no"] = n
  by = {a: sum(1 for e in entries if e["audience"] == a) for a in AUDIENCES}
  return {"counts": by, "items": entries, "total": len(entries)}

def places_of(ledger_rows) -> dict:
  levels, marks, items = [], [], []
  for r in ledger_rows:
    for bucket, v in ((levels, r.get("level")), (marks, r.get("label")), (items, r.get("code"))):
      if v and v not in bucket:
        bucket.append(str(v))
  return {"levels": levels, "marks": marks, "work_items": items}

def as_text(fix: dict, audience: str = ARCHITECT, title: str = "Drawing queries") -> str:
  rows = [e for e in fix.get("items", []) if e["audience"] == audience]
  if not rows:
    return ""
  lines = [title, ""]
  for n, e in enumerate(rows, 1):
    lines.append(f"{n}. {e['topic']}: {e['ask']}")
  return "\n".join(lines) + "\n"
