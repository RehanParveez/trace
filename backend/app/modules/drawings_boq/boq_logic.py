from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import Callable, Iterable
import hashlib
import json
from app.engine.measure.spec import describe_spec
from app.engine.measure.stages import stage_label
from app.modules.drawings_boq import quantity_range as QR

ZERO = Decimal("0")
ONE = Decimal("1")
LOW_CONFIDENCE_THRESHOLD = Decimal("0.6")

UNIT_TABLE: dict[str, tuple[str, Decimal]] = {
  "m3": ("m3", ONE), "cft": ("m3", Decimal("35.3146667")),
  "m2": ("m2", ONE), "sft": ("m2", Decimal("10.7639104")),
  "m": ("m", ONE), "rft": ("m", Decimal("3.280839895")),
  "kg": ("kg", ONE), "nos": ("nos", ONE),
  "quintal": ("kg", Decimal("0.01")),
  "tonne": ("kg", Decimal("0.001")),
}
_CATEGORY = {"m3": "volume", "m2": "area", "m": "length", "kg": "weight", "nos": "count"}

UNIT_ALIASES: dict[str, str] = {
  "cum": "m3", "cu.m": "m3", "cu m": "m3", "m³": "m3", "cubic metre": "m3", "cubic meter": "m3",
  "sqm": "m2", "sq.m": "m2", "sq m": "m2", "m²": "m2", "square metre": "m2", "square meter": "m2",
  "sq ft": "sft", "sq.ft": "sft", "sqft": "sft", "square feet": "sft", "square foot": "sft",
  "cu ft": "cft", "cu.ft": "cft", "cuft": "cft", "cubic feet": "cft", "cubic foot": "cft",
  "rm": "m", "rmt": "m", "mtr": "m", "metre": "m", "meter": "m", "r.ft": "rft", "running feet": "rft",
  "kgs": "kg", "kilogram": "kg",
  "no": "nos", "no.": "nos", "nos.": "nos", "each": "nos", "ea": "nos", "unit": "nos", "units": "nos", "pcs": "nos",
}

def normalise_unit(unit: str | None) -> str:
  key = (unit or "").strip().lower()
  return UNIT_ALIASES.get(key, key)

REVIEW_WARNING_CODES = frozenset({
  "GEOMETRY_INCOMPLETE", "QTO_FALLBACK", "LOW_CONFIDENCE_GEOMETRY", "UNSUPPORTED_GEOMETRY",
  "QTO_GEOMETRY_MISMATCH", "ALLOCATION_APPROXIMATE", "NOT_ALLOCATED", "OVER_DEDUCTED",
  "ZERO_NET_QUANTITY", "SAME_ROLE_OVERLAP", "OPENING_SIZE_MISSING", "OPENING_ASSIGNMENT_APPROXIMATE",
  "FINISH_NEEDS_REVIEW","STEEL_ESTIMATED", "STEEL_SOLID_SECTION_SUSPECTED", "STEEL_DUPLICATE_SUSPECTED", "STEEL_MATERIAL_UNCERTAIN", "DECLARED_WEIGHT_MISMATCH", "MIXED_GRADES", "LAP_LENGTH_UNKNOWN",
    "PDF_LOW_PRECISION", "PDF_SCALE_MISMATCH", "PDF_SCANNED_LOW_PRECISION", "PDF_DIMENSION_ASSUMED", "PDF_CAL_SHORT_BASELINE", "PDF_RATIO_UNVERIFIED", "PDF_GEOMETRY_WARNING", "PDF_OVER_DEDUCTED",
    "LAYER_UNPRICED", "LAYER_THICKNESS_MISMATCH", "LAYER_NOT_SPLIT", "MATERIAL_GENERIC", "DERIVED_ASSUMED", "DERIVED_NGL_ASSUMED", "DERIVED_BOX_FOOTPRINT", "DERIVED_MARK_POSITION", "DPC_LEVEL_ASSUMED", "DPC_DOOR_NOT_DEDUCTED", "FORMWORK_ASSUMED", "FORMWORK_FRAME_ASSUMED", "FORMWORK_ITEM_ASSUMED", "FORMWORK_BEAM_SLAB_ASSUMED", "STEEL_ASSUMED",
    "SPACE_OVER_DEDUCTED", "SPACE_VIEW_NOT_PLACED", "SPACE_NO_HEIGHT", "SPACE_SAME_ROLE_OVERLAP",
})

NON_WAIVABLE_CODES = frozenset({"NON_CONSERVING_ALLOCATION", "UNALLOCATED_OVERLAP"})

def _q(value, places: int) -> Decimal:
  return Decimal(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)

def q2(value) -> Decimal:
  return _q(value, 2)

def q4(value) -> Decimal:
  return _q(value, 4)

def q6(value) -> Decimal:
  return _q(value, 6)

def fmt(value, places: int = 4):
  return None if value is None else format(_q(value, places), "f")

def resolve_display_unit(canonical: str, preferred: dict | None, fallback: str | None = None) -> tuple[str, Decimal]:
  prefs = preferred or {}
  for key in (canonical, _CATEGORY.get(canonical)):
    wanted = prefs.get(key) if key else None
    if isinstance(wanted, str):
      name = wanted.strip().lower()
      entry = UNIT_TABLE.get(name)
      if entry is not None and entry[0] == canonical:
        return name, entry[1]
  if isinstance(fallback, str):
    name = fallback.strip().lower()
    entry = UNIT_TABLE.get(name)
    if entry is not None and entry[0] == canonical:
      return name, entry[1]
  return canonical, ONE

def convert_rate(rate: Decimal, from_unit: str, to_unit: str) -> Decimal | None:
  a = UNIT_TABLE.get(normalise_unit(from_unit))
  b = UNIT_TABLE.get(normalise_unit(to_unit))
  if a is None or b is None or a[0] != b[0]:
    return None
  
  return q2(Decimal(rate) * a[1] / b[1])

@dataclass(frozen=True)
class LedgerLine:
  id: object
  solid_id: object
  element_id: object
  level_id: object
  work_item_code: str
  quantity: Decimal
  unit: str
  material_grade: str | None
  confidence: Decimal
  warnings: tuple = ()
  spec_key: str | None = None
  spec: dict | None = None
  work_stage: str | None = None
  range: dict | None = None

@dataclass(frozen=True)
class WorkItemInfo:
  code: str
  description: str
  unit: str
  trade: str | None = None
  wbs_code: str | None = None
  material_class: str | None = None

@dataclass(frozen=True)
class AdjustmentLine:
  kind: str
  value: Decimal

@dataclass
class ItemDraft:
  item_key: str
  work_item_code: str
  level_id: object
  material_grade: str | None
  canonical_unit: str
  unit: str
  unit_factor: Decimal
  canonical_total: Decimal
  net_quantity: Decimal
  waste_factor: Decimal
  confidence: Decimal
  review_status: str
  material_name: str
  description: str
  category: str | None
  formula_text: str
  element_count: int
  lines: list = field(default_factory=list)
  spec_key: str | None = None
  spec: dict | None = None
  work_stage: str | None = None
  quantity_range: dict | None = None

def make_item_key(code: str, unit: str, grade: str | None, level, spec_key: str | None = None, stage: str | None = None) -> str:
  key = f"{code}|{unit}|{grade or '-'}|{level or '-'}"
  if spec_key:
    key = f"{key}|{spec_key}"
  return f"{key}|@{stage}" if stage else key

def aggregate(lines: Iterable[LedgerLine], *, scope: str, preferred_units: dict | None,
  work_items: dict, waste_for: Callable[[str | None], Decimal]):
  groups: dict = {}
  for ln in lines:
    level = ln.level_id if scope == "level" else None
    groups.setdefault((ln.work_item_code, ln.unit, ln.material_grade or None, ln.spec_key or None, ln.work_stage or None, level), []).append(ln)

  drafts: list[ItemDraft] = []
  unknown: set = set()
  mismatch: set = set()
  for key in sorted(groups, key=lambda k: (k[0], k[1], k[2] or "", k[3] or "", k[4] or "", str(k[5] or ""))):
    code, unit, grade, spec_key, stage, level = key
    group = sorted(groups[key], key=lambda l: (str(l.element_id), str(l.id)))
    wi = work_items.get(code)
    if wi is None:
      unknown.add(code)
    else:
      catalog = UNIT_TABLE.get((wi.unit or "").strip().lower())
      if catalog is not None and catalog[0] != unit:
        mismatch.add(code)

    display, factor = resolve_display_unit(unit, preferred_units, wi.unit if wi else None)
    total = sum((l.quantity for l in group), ZERO)
    net = q4(total * factor)
    waste = max(ONE, Decimal(waste_for(wi.material_class if wi else None)))
    confidence = q4(min(l.confidence for l in group))
    flagged = confidence < LOW_CONFIDENCE_THRESHOLD or any(
      w in REVIEW_WARNING_CODES for l in group for w in l.warnings)
    description = wi.description if wi else code
    spec = next((l.spec for l in group if l.spec), None)
    described = describe_spec(spec)
    label = ", ".join(x for x in (described, f"grade {grade}" if grade and grade not in (described or "") else None, stage_label(stage)) if x)
    
    if label:
      description = f"{description} ({label})"
    drafts.append(ItemDraft(
      item_key=make_item_key(code, unit, grade, level, spec_key, stage), work_item_code=code, level_id=level,
      material_grade=grade, canonical_unit=unit, unit=display, unit_factor=factor,
      canonical_total=total, net_quantity=net, waste_factor=waste, confidence=confidence,
      review_status="REVIEW_REQUIRED" if flagged else "OK",
      material_name=description[:300], description=description,
      category=wi.trade if wi else None,
      formula_text=f"Sum of {len(group)} ledger row(s) in {unit} x {factor} = {display}"[:500],
      element_count=len({l.element_id for l in group if l.element_id is not None}),
      lines=group, spec_key=spec_key, spec=spec, work_stage=stage,
      quantity_range=QR.combine([(l.quantity, l.range) for l in group], factor, net),
    ))
  return drafts, sorted(unknown), sorted(mismatch)

def compute_quantity(net: Decimal, adjustments: Iterable[AdjustmentLine]) -> Decimal:
  base = Decimal(net)
  delta = ZERO
  for a in adjustments:
    if a.kind == "REPLACE":
      base = Decimal(a.value)
    else:
      delta += Decimal(a.value)
  return q4(base + delta)

_TYPE_ORDER = {"MATERIAL": 0, "LABOUR": 1, "CUSTOM": 2}
_PLACES = {
  "net_quantity": 4, "adjustment_total": 4, "quantity": 4, "gross_quantity": 4,
  "waste_factor_applied": 4, "unit_factor": 10, "unit_rate": 2, "amount": 2, "confidence": 4,
  "base_rate": 2, "escalation_factor": 4,
}

def ledger_hash(pairs: Iterable[tuple]) -> str | None:
  parts = sorted(f"{lid}:{fmt(Decimal(qty), 6)}" for lid, qty in pairs)
  if not parts:
    return None
  return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

def build_snapshot(items: list[dict], header: dict):
  ordered = sorted(items, key=lambda i: (
    _TYPE_ORDER.get(i["item_type"], 9), i.get("work_item_code") or "~",
    i["material_name"], i.get("item_key") or "", str(i["id"])))

  rows: list[dict] = []
  sums = {"MATERIAL": ZERO, "LABOUR": ZERO, "CUSTOM": ZERO}
  unpriced = 0
  for n, i in enumerate(ordered, start=1):
    quantity = q4(i["quantity"])
    rate = i.get("unit_rate")
    amount = q2(quantity * Decimal(rate)) if rate is not None else None
    if amount is None:
      unpriced += 1
    else:
      sums[i["item_type"]] = sums.get(i["item_type"], ZERO) + amount
    net = i.get("net_quantity")
    rows.append({
      "line_no": n, "source_item_id": i["id"], "item_key": i.get("item_key"),
      "work_item_code": i.get("work_item_code"), "material_name": i["material_name"],
      "description": i.get("description"), "category": i.get("category"),
      "item_type": i["item_type"], "level_id": i.get("level_id"),
      "material_grade": i.get("material_grade"), "unit": i["unit"],
      "canonical_unit": i.get("canonical_unit"), "unit_factor": i.get("unit_factor"),
      "net_quantity": q4(net if net is not None else quantity),
      "adjustment_total": q4(i.get("adjustment_total") or ZERO), "quantity": quantity,
      "waste_factor_applied": i.get("waste_factor_applied"),
      "unit_rate": rate,
      "amount": amount,
      "base_rate": i.get("base_rate"), "escalation_factor": i.get("escalation_factor"),
      "rate_resolution": i.get("rate_resolution"),
      "confidence": i.get("confidence"), "review_status": i.get("review_status") or "OK",
      "source_kind": i.get("source_kind") or "MODEL", "is_manual": bool(i.get("is_manual")),
      "ledger_row_count": int(i.get("ledger_row_count") or 0), "ledger_hash": i.get("ledger_hash"),
      **{k: i[k] for k in ("work_stage", "spec_key", "spec", "quantity_range") if i.get(k)},
    })

  grand = sum(sums.values(), ZERO)
  totals = {
    "materials": fmt(sums["MATERIAL"], 2), "labour": fmt(sums["LABOUR"], 2),
    "custom": fmt(sums["CUSTOM"], 2), "grand": fmt(grand, 2),
    "item_count": len(rows), "unpriced_item_count": unpriced,
  }

  hashed = []
  for r in rows:
    hashed.append({
      k: (fmt(v, _PLACES[k]) if k in _PLACES else v)
      for k, v in r.items() if k != "source_item_id"
    })
  blob = json.dumps({"header": header, "lines": hashed}, sort_keys=True,
    separators=(",", ":"), default=str)
  return rows, totals, hashlib.sha256(blob.encode("utf-8")).hexdigest()

@dataclass
class IssueSpec:
  code: str
  severity: str
  blocks: str
  message: str
  dedupe_key: str
  suggested_fix: str | None = None
  details: dict = field(default_factory=dict)
  drawing_element_id: object = None
  boq_item_id: object = None

LEDGER_WARNING_CATALOG = {
  "PDF_LOW_PRECISION": ("warning", "NONE",
    "A PDF measurement is too small or too coarse for its scale; a one-pixel pick error moves the quantity by more than 5%.",
    "Measure a larger extent, snap to the vector geometry, or use a drawing with a larger scale."),
  "PDF_SCALE_MISMATCH": ("warning", "APPROVAL",
    "The check dimension on the calibration disagrees with the scale by 1% to 2%, so the measurements on this sheet may be off by that much.",
    "Re-calibrate using a longer known dimension, or confirm the sheet is printed at the stated scale."),
  "PDF_SCANNED_LOW_PRECISION": ("warning", "NONE",
    "The sheet is a scanned image; measurements were picked by eye and are less precise than on vector drawings.",
    "Ask for the vector PDF export of this drawing if the quantity is large."),
  "PDF_DIMENSION_ASSUMED": ("warning", "NONE",
    "A height or thickness used with a PDF measurement was assumed, not read from the drawing.",
    "Enter the dimension from the drawing or the specification and mark it as drawn or specified."),
  "PDF_CAL_SHORT_BASELINE": ("warning", "NONE",
    "The calibration was taken over a short distance, which magnifies picking error across the whole sheet.",
    "Calibrate over the longest known dimension on the sheet."),
  "PDF_RATIO_UNVERIFIED": ("warning", "NONE",
    "The scale was typed from the title block and not checked against a known dimension; plotted sheets are often not at the printed scale.",
    "Add a check dimension to the calibration."),
  "PDF_GEOMETRY_WARNING": ("warning", "NONE",
    "A deduction polygon lies partly outside the boundary it is deducted from.", "Redraw the deduction inside the boundary."),
  "PDF_OVER_DEDUCTED": ("error", "APPROVAL",
    "Deductions on a PDF measurement exceeded its gross quantity; the quantity was clamped to zero.",
    "Check the openings and adjustments entered on this measurement."),
  "PDF_ADDED_TO_MODEL": ("info", "NONE",
    "A PDF measurement was added on top of a model quantity for the same work item, by choice.", None),
  "PDF_REPLACES_MODEL": ("info", "NONE",
    "A PDF measurement replaced the model quantity for the same work item, by choice.", None),
  "OPENINGS_NOT_DEDUCTED": ("info", "NONE",
    "No door or window opening was deducted from these wall volumes, so they are gross of openings.",
    "Check that the rule set has opening rules and that the doors and windows in the model have sizes and sit in these walls; "
    "otherwise enter an adjustment."),
  "SPEC_MIX_MISSING": ("info", "NONE",
    "The model does not state a concrete mix or grade for these elements, so they are grouped without one.",
    "Give the concrete a material name that carries the mix (for example Reinforced Concrete 1:2:4 or M20), or confirm the mix with the engineer."),
  "SPEC_MORTAR_MISSING": ("info", "NONE",
    "The model does not state a mortar ratio for these masonry walls, so they are grouped without one.",
    "Read the mortar ratio from the drawing notes or specification and set it on the rule set or the wall material."),
  "SPEC_THICKNESS_MISSING": ("warning", "NONE",
    "The model does not give a thickness for these masonry walls, so walls of different thickness may be grouped together.",
    "Give the walls a thickness in the model, or check them one by one."),
  "DATUM_DEFAULTED": ("info", "NONE",
    "The stage this quantity falls in depends on a reference level that the model does not give (the DPC or the lintel level), "
    "so an assumed level was used. The total quantity is not affected, only which stage it is shown under.",
    "Set the DPC drop below floor level or the lintel height on the measurement convention, or confirm the levels with the engineer."),
  "STAGE_NOT_SPLIT": ("warning", "NONE",
    "This element stands across a stage level but could not be cut there (no exact footprint, or not upright), so all of it was put "
    "in the stage holding its middle.",
    "Check the element in the model; re-upload with the current reader so footprints are stored."),
  "STAGE_UNRESOLVED": ("warning", "NONE",
    "The height of this element is not known, so it could not be placed in a stage of work.",
    "Check the element in the model."),
  "STAGE_DEDUCTION_APPORTIONED": ("info", "NONE",
    "A deduction on this element has no recorded height, so it was shared between the stages in proportion to their height.",
    "Re-run with the current reader so openings carry their heights."),
  "SAME_ROLE_OVERLAP": ("warning", "NONE", "Elements of the same role overlap; the lowest element id owns the shared volume.",
    "Check these overlaps in the model."),
  "ALLOCATION_APPROXIMATE": ("warning", "NONE", "Overlaps were allocated from bounding boxes, not exact footprints.",
    "Re-upload the model with the current reader so footprints are stored."),
  "NOT_ALLOCATED": ("warning", "NONE",
    "Elements were not allocated (no usable footprint, sloped or non-prismatic shape, a role the convention does not rank, "
    "or no convention on the rule set); their volume is gross and may overlap other elements.",
    "Check these elements in the model, or set a convention on the rule set."),
  "DUPLICATE_SOLID": ("warning", "NONE", "An element is fully inside another element of the same role (duplicate in the model); "
    "it was given zero volume.", "Delete the duplicate element in the model."),
  "SCHEDULE_OVERLAPS_MODEL": ("warning", "APPROVAL", "A schedule row uses a work item that the model or the finish rules "
    "already measured in this run, so the quantity may be counted twice.",
    "Archive the schedule row, change its work item, or waive this issue with a reason."),
  "SCHEDULE_LOW_CONFIDENCE": ("warning", "NONE", "A schedule row was read with low confidence.",
    "Check the row against the drawing."),
  "QTO_FALLBACK": ("warning", "NONE", "Volume was taken from the model's Qto value because geometry was incomplete.", None),
  "LOW_CONFIDENCE_GEOMETRY": ("warning", "NONE", "Volume is approximate (bounding box or Qto only).", None),
  "GEOMETRY_INCOMPLETE": ("warning", "NONE", "Profile or depth missing; no volume was measured.", None),
  "UNSUPPORTED_GEOMETRY": ("warning", "NONE", "Geometry could not be measured.", None),
  "ZERO_NET_QUANTITY": ("warning", "NONE", "Net quantity became zero after allocation.", None),
  "OPENING_SIZE_MISSING": ("warning", "NONE", "An opening has no usable size, so it was not deducted.",
    "Add width and height to the door or window in the model."),
  "OPENING_ASSIGNMENT_APPROXIMATE": ("warning", "NONE",
    "Openings were assigned to rooms by wall membership, without a position check.",
    "Check the deducted openings in the measurement book."),
  "FINISH_NEEDS_REVIEW": ("warning", "NONE", "The finish for this surface needs review.", None),
  "STEEL_ESTIMATED": ("warning", "ISSUE", "Steel is estimated from concrete volume, not measured from a bar schedule.",
    "Import and confirm a bar bending schedule, or waive this issue with a reason."),
  "DECLARED_WEIGHT_MISMATCH": ("warning", "NONE", "A bar schedule weight differs from the computed weight.",
    "Check the bar sizes, counts and lengths in the schedule."),
  "MIXED_GRADES": ("warning", "NONE", "Bars of different grades share one member; the line has no single grade.", None),
  "LAP_LENGTH_UNKNOWN": ("warning", "NONE", "A bar longer than stock length has no lap rule, so no lap was added.",
    "Set a lap basis and coefficient on the reinforcement rule."),
  "MATCHED_ELEMENT_NOT_MEASURED": ("warning", "NONE", "A bar row was matched to an element that is not measured.", None),
  "UNIT_WEIGHT_COMPUTED": ("info", "NONE", "Unit weight was computed from the diameter (no bar-size entry).", None),
  "PILE_WEIGHT_NOT_COMPUTED": ("info", "NONE",
    "Steel piles are billed by driven length. The model draws a pipe pile as a solid cylinder, so no weight was taken from its volume.",
    "Give the pile its wall thickness or section in the model if a weight is needed."),
  "STEEL_SOLID_SECTION_SUSPECTED": ("warning", "NONE",
  "A steel member looks like a solid section: it weighs more than 800 kg per metre, or it is a plain solid rectangle or circle "
    "of section size. The model may have drawn a hollow or rolled section as a solid, which overstates the weight.",
    "Check the section of these members in the model."),
  "STEEL_DUPLICATE_SUSPECTED": ("warning", "NONE",
    "Another steel member has the same type, position and size, so this one may be a duplicate in the model and counted twice.",
    "Delete the duplicate in the model, or confirm both members exist."),
  "STEEL_MATERIAL_UNCERTAIN": ("warning", "NONE",
    "The material only says metal or iron, or steel was inferred from the element name, so it may not be structural steel.",
    "Give the member a steel material (for example Steel S275) in the model."),
    "LAYER_FINISH_EXCLUDED": ("info", "NONE",
    "The wall is built up of layers in the model. The plaster, paint and other finish layers were taken out of the masonry volume, "
    "so the brickwork is measured at its own thickness only.",
    "Nothing to do. Plaster and paint are measured separately from the room finishes."),
  "LAYER_UNPRICED": ("warning", "NONE",
    "A layer of this element (for example insulation, a membrane or a cavity) has no work item, so it is not in the BOQ. "
    "The element's volume was reduced by it.",
    "Map this layer family to a work item on the rule set (a mapping named LAYER:<FAMILY>), or confirm it is not to be billed."),
  "LAYER_THICKNESS_MISMATCH": ("warning", "NONE",
    "The layers of this element add up to a different thickness from the element's own width in the model. "
    "The layers were scaled to the element's volume.",
    "Check the layer thicknesses in the model."),
  "LAYER_NOT_SPLIT": ("warning", "NONE",
    "None of this element's layers could be matched to a billable work item, so the element was left whole as one material.",
    "Check the material layers of this element in the model, or map the layer families to work items on the rule set."),
  "MATERIAL_GENERIC": ("warning", "NONE",
    "The model gives this element no real material (it says generic, default or nothing), so the grade or mortar could not be read "
    "and the masonry or concrete class is a guess.",
    "Give the element a material in the model, for example Brick or Concrete C25."),
  "DERIVED_ASSUMED": ("warning", "NONE",
    "This quantity is not drawn in the model. It is worked out from the foundation using site assumptions that were not given "
    "(working space, PCC projection, PCC thickness, or the brick ballast clearance and thickness under masonry walls), so standard values were used.",
    "Confirm the working space, PCC projection and thickness, and the ballast clearance and thickness for this site when starting the run."),
  "DERIVED_NGL_ASSUMED": ("warning", "NONE",
    "The natural ground level is not in the model, so the excavation and backfill depth was worked out from an assumed level "
    "below the floor level.",
    "Give the natural ground level (how far below floor level) when starting the run."),
  "DERIVED_BOX_FOOTPRINT": ("warning", "NONE",
    "The foundation has no exact outline in the model, so its bounding rectangle was used for the excavation and PCC. "
    "A foundation that is not rectangular is overstated.",
    "Re-upload the model with the current reader so outlines are stored."),
  "DERIVED_MARK_POSITION": ("warning", "NONE",
    "This footing was read from a drawing, so it is placed at its mark with the size from the schedule or the drawing, not at a drawn outline. "
    "Footings close together may share a trench in the drawing, and the shared part is only approximate here.",
    "Check the excavation, PCC and backfill of these footings against the foundation plan, or measure the trench by hand."),
  "DERIVED_ELEMENT_OVERRIDE": ("info", "NONE",
    "A value was typed for this one footing or wall (its working space, or its bed projection or thickness) and is used here in place of the project's value.",
    "Check the typed value in the element parameters of the project."),
  "DPC_LEVEL_ASSUMED": ("warning", "NONE",
    "The level of the damp-proof course is not in the model or on the drawing, so it was taken at the floor level less the DPC drop (none, unless one is set). "
    "A wall that starts or stops near that level may or may not be counted.",
    "Type the DPC level in the stage levels of the project, or set the DPC drop below floor level on the measurement convention."),
  "DPC_DOOR_NOT_DEDUCTED": ("warning", "NONE",
    "A door reaches the DPC level of this wall but the model gives it no outline, so the width of the door was not taken out of the DPC.",
    "Re-upload the model with the current reader so doors carry their outline, or take the door width off by hand."),
  "STEEL_ASSUMED": ("warning", "NONE",
    "This steel was worked out from the bars printed for the member, using a site choice that was not given (the concrete cover, the length added to a "
    "ring for its hooks, the lap of a column bar or the anchorage of a bar), so the standard value was used.",
    "Give the cover, ring hook, lap and anchorage in the site assumptions, then calculate again."),
  "FORMWORK_ASSUMED": ("warning", "NONE",
    "This formwork was worked out from concrete read from a drawing, using a site choice that was not given (whether slab edges are shuttered, whether "
    "footing sides are shuttered, whether the base of a tank is shuttered, or whether a beam's depth includes the slab), so the standard choice was used.",
    "Say these in the site assumptions, then calculate again."),
  "FORMWORK_ITEM_ASSUMED": ("warning", "NONE",
    "This formwork is for a tank, coping, chajja or balcony slab. Which of its faces are shuttered follows the usual way of casting it (a coping is cast on the "
    "parapet so its underside is not shuttered; a chajja is cast against the wall; one long side of a balcony slab joins the floor slab) and is not on the drawing.",
    "Check the faces in the trace against how the item is cast on site."),
  "FORMWORK_BEAM_SLAB_ASSUMED": ("warning", "NONE",
    "Part of this beam's or slab's formwork was taken off where the beam meets the slab, but the floor has slabs of different thickness (so which one covers the "
    "beam is a guess), or the beams were more than a third of the slab soffit and the take-off was limited.",
    "Check the slab thickness of this floor, then calculate again."),
  "FORMWORK_FRAME_ASSUMED": ("warning", "NONE",
    "Part of this column's formwork was taken off because a slab covers it, but where the two drawing views sit on the building was found by the program, "
    "or the floor of one of them was not given, and no one has confirmed it.",
    "Open the frame view of the drawing, confirm or move the placement of each view, give the floors, then calculate again."),
  "SPACE_OVER_DEDUCTED": ("error", "APPROVAL",
    "The parts of the drawing that overlap this member took more than its own volume, so what was taken off was scaled down to fit. The total is kept, "
    "but which member the overlap belongs to is uncertain.",
    "Check the views of this member for a duplicate mark or a view placed on top of another, then calculate again."),
  "SPACE_VIEW_NOT_PLACED": ("warning", "NONE",
    "The drawing view this member was measured on has no placement on the building, so it was only compared with members of its own view.",
    "Open the frame view of the drawing and confirm the placement of this view, then calculate again."),
  "SPACE_NO_HEIGHT": ("warning", "NONE",
    "The height range of this member is not known (its floor has no level, or the lintel head or footing level is not given), so it could not be "
    "compared with other members or placed in a stage of work.",
    "Give the floor levels, the lintel head or the footing level, then calculate again."),
  "SPACE_SAME_ROLE_OVERLAP": ("warning", "NONE",
    "Two measurements of the same kind of member lie over each other on the drawing, so the shared part was counted once.",
    "Check that the same wall or beam was not measured twice."),
  "STAGE_DATUM_DEFAULTED": ("info", "NONE",
    "The stage this quantity falls in depends on a reference level the drawing does not give (the DPC or the lintel level), so an assumed level was used. "
    "The total quantity is not affected, only which stage it is shown under.",
    "Set the DPC drop below floor level or the lintel height on the measurement convention, or confirm the levels with the engineer."),
  "OVER_DEDUCTED": ("error", "APPROVAL", "Deductions exceeded the gross volume; the quantity was clamped to zero.",
    "Report this model; the allocation is inconsistent."),
}

STAGE_REASON_TEXT = {
  "NO_DOORS_FOR_FLOOR_LEVEL": "the model has no doors, so the floor level could not be found",
  "NO_FLOOR_SLAB_FOUND": "no floor slab was found a storey above the floor level",
  "DATUMS_OUT_OF_ORDER": "the floor level, lintel level and slab level found in the model are not in a workable order",
}

def stage_issue_specs(stats: dict) -> list[IssueSpec]:
  if not stats.get("enabled") or stats.get("resolved"):
    return []
  reason = stats.get("reason") or "UNKNOWN"
  return [IssueSpec(
    code="STAGES_NOT_DERIVED", severity="info", blocks="NONE", dedupe_key="STAGES_NOT_DERIVED",
    message=f"Quantities were not split by stage of work because {STAGE_REASON_TEXT.get(reason, reason)}.",
    suggested_fix="Check the doors and the floor slabs in the model, or set the reference levels on the measurement convention.",
    details={"reason": reason})]
  
DERIVED_REASON_TEXT = {
  "NO_RECIPE": "the rule set has no footing preparation recipe (excavation and PCC under footings)",
  "ALL_ITEMS_IN_MODEL": "the model already draws these items",
  "NO_FOUNDATIONS": "the model has no footings",
  "TOO_MANY_FOUNDATIONS": "the model has more footings than the derived works can handle in one run",
  "NEEDS_FOOTING_LEVEL": "the depth of the footing bottom below natural ground is not known",
}

def derived_issue_specs(stats: dict) -> list[IssueSpec]:
  if not stats.get("enabled"):
    return []
  waiting = ((stats.get("claims") or {}).get("waiting")) or 0
  if waiting:
    tags = sorted({str(x.get("tag")) for x in stats["claims"].get("waiting_list") or [] if x.get("tag")})
    return [IssueSpec(
      code="DERIVED_NEEDS_FOOTING_LEVEL", severity="warning", blocks="NONE", dedupe_key="DERIVED_NEEDS_FOOTING_LEVEL",
      message=f"{waiting} footing{'s' if waiting != 1 else ''} counted from the drawing"
        + (f" ({', '.join(tags[:8])})" if tags else "")
        + " could not be dug and bedded: the depth of the footing bottom below natural ground is not on the drawing, so excavation, PCC and backfill were not worked out for them.",
      suggested_fix="Give the depth of the footing bottom below natural ground level in the site assumptions, then calculate again.",
      details={"waiting": waiting, "tags": tags})]
    
  if stats.get("ran"):
    return []
  reason = stats.get("reason") or "UNKNOWN"
  if reason == "ALL_ITEMS_IN_MODEL":
    return []
  return [IssueSpec(
    code="DERIVED_NOT_RUN", severity="info", blocks="NONE", dedupe_key="DERIVED_NOT_RUN",
    message=f"Excavation, PCC and backfill were not worked out because {DERIVED_REASON_TEXT.get(reason, reason)}.",
    suggested_fix="Add the footing preparation recipe to the rule set, or measure these items another way.",
    details={"reason": reason})]

BALANCE_NOTICE_M3 = Decimal("0.05")
BALANCE_NOTICE_SHARE = Decimal("0.01")

def balance_issue_specs(stats: dict) -> list[IssueSpec]:
  """The earth balance of the trenches (derived works). Backfill is the excavation less the structure in the trench, so a gap, or more backfill than excavation, is
  a fault in the working; structure below natural ground that has no trench around it is a missing excavation."""
  bal = (stats or {}).get("balance") or {}
  if not (stats or {}).get("ran") or not bal:
    return []
  
  specs: list[IssueSpec] = []
  negative = int(bal.get("negative_backfill_rows") or 0)
  if negative or not bal.get("closes", True):
    specs.append(IssueSpec(
      code="BACKFILL_NEGATIVE", severity="error", blocks="APPROVAL", dedupe_key="BACKFILL_NEGATIVE",
      message=("Backfill does not balance with the excavation: " + (f"{negative} trench(es) hold more structure than was dug. " if negative else "")
        + f"Excavation {bal.get('excavation_m3')} m3, backfill {bal.get('backfill_m3')} m3, structure in the trenches {bal.get('buried_m3')} m3 (gap {bal.get('gap_m3')} m3)."),
      suggested_fix="A footing outline or a level in the model is wrong. Check the footings and the natural ground level, then calculate again.",
      details={k: bal.get(k) for k in ("excavation_m3", "backfill_m3", "buried_m3", "gap_m3", "negative_backfill_rows")}))
  try:
    outside, structure = Decimal(str(bal.get("structure_outside_trench_m3") or "0")), Decimal(str(bal.get("structure_below_ground_m3") or "0"))
  except Exception:
    return specs
  if outside > BALANCE_NOTICE_M3 and (structure <= 0 or outside / structure > BALANCE_NOTICE_SHARE):
    specs.append(IssueSpec(
      code="EXCAVATION_BALANCE", severity="warning", blocks="NONE", dedupe_key="EXCAVATION_BALANCE",
      message=f"{fmt(outside, 3)} m3 of the structure below natural ground level has no trench dug around it, so no excavation or backfill was taken for it "
        f"(of {fmt(structure, 3)} m3 below ground in all). A basement or a retaining wall is dug in a different way from a footing trench.",
      suggested_fix="Measure the excavation for the basement or the retaining wall by hand, or add it as a measurement.",
      details={"structure_outside_trench_m3": str(outside), "structure_below_ground_m3": str(structure)}))
  return specs

def dpc_issue_specs(stats: dict) -> list[IssueSpec]:
  dpc = (stats or {}).get("dpc") or {}
  if not dpc or dpc.get("reason") in (None, "ALL_ITEMS_IN_MODEL", "NO_PROFILE") and not dpc.get("ran"):
    return []
  if dpc.get("ran"):
    return [IssueSpec(
      code="DPC_VERTICAL_NOT_TAKEN", severity="info", blocks="NONE", dedupe_key="DPC_VERTICAL_NOT_TAKEN",
      message="The damp-proof course is measured as the horizontal layer under the walls. A vertical DPC (against earth on the face of a wall below ground level) is not taken.",
      suggested_fix="Add the vertical DPC by hand where the specification asks for it.", details={"area_m2": dpc.get("area_m2")})]
    
  return [IssueSpec(
    code="DPC_NOT_MEASURED", severity="info", blocks="NONE", dedupe_key="DPC_NOT_MEASURED",
    message="The damp-proof course was not measured because " + (
      "no wall was found standing across the DPC level." if dpc.get("reason") == "NO_WALL_ON_DPC" else "the DPC level could not be found (there are no doors in the model, and no ground floor on the drawing, to give the floor level)."),
    suggested_fix="Type the DPC level in the stage levels of the project, then calculate again.", details={"reason": dpc.get("reason"), "model": dpc.get("model"), "pdf": dpc.get("pdf")})]

ASSUMED_DATUM_TEXT = {"DPC": "the damp-proof course level", "LINTEL": "the lintel level", "PARAPET_TOP": "the top of the parapet"}

def datum_issue_specs(stats: dict) -> list[IssueSpec]:
  stages = (stats or {}).get("stages") or {}
  pdf = ((stats or {}).get("pdf_space") or {}).get("datums") or {}
  sets = [stages] if stages.get("resolved") else [pdf[g] for g in sorted(pdf) if (pdf[g] or {}).get("resolved")]
  specs: list[IssueSpec] = []
  assumed = sorted({d["name"] for s in sets for d in s.get("datums") or [] if d.get("source") == "default" and d.get("name") in ASSUMED_DATUM_TEXT})
  
  if assumed:
    names = ", ".join(ASSUMED_DATUM_TEXT[n] for n in assumed)
    specs.append(IssueSpec(
      code="DATUMS_ASSUMED", severity="info", blocks="NONE", dedupe_key="DATUMS_ASSUMED",
      message=f"The stages of work stand on levels that were assumed because the model or drawing does not give them: {names}. The total of each item is not affected, "
        "only which stage it is shown under (and, for the DPC, whether a wall at that level is counted).",
      suggested_fix="Type the levels in the stage levels of the project, or confirm them with the engineer.", details={"datums": assumed}))
  unused = sorted(set(stages.get("unused_overrides") or []) | set(((stats or {}).get("pdf_space") or {}).get("unused_overrides") or []))
  if unused and (stages.get("enabled") or pdf):
    specs.append(IssueSpec(
      code="DATUM_OVERRIDE_UNUSED", severity="warning", blocks="NONE", dedupe_key="DATUM_OVERRIDE_UNUSED",
      message=f"A level typed for {', '.join(unused)} was not used: the building has no such level, or the stages could not be worked out.",
      suggested_fix="Open the stage levels of the project and remove or correct it.", details={"datums": unused}))
  return specs

def element_override_issue_specs(stats: dict) -> list[IssueSpec]:
  over = (stats or {}).get("element_overrides") or {}
  unmatched = over.get("unmatched") or []
  if not unmatched:
    return []
  return [IssueSpec(
    code="ELEMENT_OVERRIDE_UNMATCHED", severity="warning", blocks="NONE", dedupe_key="ELEMENT_OVERRIDE_UNMATCHED",
    message=f"{len(unmatched)} value(s) typed for a single footing or wall were not used: the element is not a footing or wall dug in this run (it may be gone from the model, or "
      "the footing level is not known).",
    suggested_fix="Open the element parameters of the project and remove the values for elements that are gone.", details={"elements": unmatched[:50]})]

FORMWORK_REASON_TEXT = {
  "NO_RECIPE": "the rule set has no structural formwork recipe",
  "ALL_ITEMS_IN_MODEL": "the model or a hand measurement already carries formwork",
  "TOO_MANY_MARKS": "the drawing has more marks than the formwork stage can handle in one run",
}

def formwork_issue_specs(stats: dict) -> list[IssueSpec]:
  """Notes about the formwork worked out from concrete read from a drawing. Silent when the run had no such concrete."""
  fw = (stats or {}).get("formwork") or {}
  if not fw or fw.get("reason") == "NO_MEMBERS":
    return []
  specs: list[IssueSpec] = []
  reason = fw.get("reason")
  if reason in FORMWORK_REASON_TEXT:
    specs.append(IssueSpec(
      code="FORMWORK_NOT_RUN", severity="info", blocks="NONE", dedupe_key="FORMWORK_NOT_RUN",
      message=f"Formwork was not worked out for the concrete read from the drawing because {FORMWORK_REASON_TEXT[reason]}.",
      suggested_fix="Add the structural formwork recipe to the rule set, or measure formwork another way.", details={"reason": reason}))
    return specs
  skipped = fw.get("skipped") or {}
  n = int(skipped.get("FOOTING_NOT_SHUTTERED_DEFAULT") or 0)
  
  if n:
    specs.append(IssueSpec(
      code="FORMWORK_FOOTING_NOT_SHUTTERED", severity="info", blocks="NONE", dedupe_key="FORMWORK_FOOTING_NOT_SHUTTERED",
      message=f"No formwork was taken for {n} footing mark{'s' if n != 1 else ''} read from the drawing: footings are taken as cast against the earth unless you say otherwise.",
      suggested_fix="If the footings are cast in shuttering, set 'footing sides shuttered' to yes in the site assumptions and calculate again.",
      details={"marks": n}))
  n = int(skipped.get("TANK_NO_DETAIL") or 0)
  if n:
    specs.append(IssueSpec(
      code="FORMWORK_TANK_NO_DETAIL", severity="warning", blocks="NONE", dedupe_key="FORMWORK_TANK_NO_DETAIL",
      message=f"No formwork was taken for {n} tank{'s' if n != 1 else ''}: the outside height and wall thickness were not kept when the tank was accepted.",
      suggested_fix="Open the tank in the register, give its height and wall thickness again, accept it, then calculate again.", details={"marks": n}))
  if fw.get("contact_not_deducted"):
    specs.append(IssueSpec(
      code="FORMWORK_CONTACT_NOT_DEDUCTED", severity="info", blocks="NONE", dedupe_key="FORMWORK_CONTACT_NOT_DEDUCTED",
      message="Formwork is the gross shuttering of each member read from the drawing. No face where concrete meets other concrete was taken off in this run: a beam needs a slab "
        "counted on its floor, and a column needs its drawing view placed on the building frame. The total is overstated by those faces.",
      suggested_fix="Check the formwork total against a hand take-off of one floor.", details={"area_m2": fw.get("area_m2")}))
  cmp = fw.get("comparison") or {}
  
  if cmp and fw.get("ran") and cmp.get("gross_m2") not in (None, fw.get("area_m2")):
    specs.append(IssueSpec(
      code="FORMWORK_SHARED_TAKEN_OFF", severity="info", blocks="NONE", dedupe_key="FORMWORK_SHARED_TAKEN_OFF",
      message=f"Faces where members meet were taken off once: gross shuttering {cmp['gross_m2']} m², net {fw.get('area_m2')} m².",
      suggested_fix="Open the formwork trace of a beam or a column to see each face that was taken off.",
      details={"gross_m2": cmp.get("gross_m2"), "net_m2": fw.get("area_m2")}))
  return specs

STEEL_REASON_TEXT = {
  "ALL_ITEMS_IN_MODEL": "the model or a hand measurement already carries reinforcement steel",
  "TOO_MANY_MARKS": "the drawing has more marks than the steel stage can handle in one run",
}

def steel_issue_specs(stats: dict) -> list[IssueSpec]:
  """Notes about the steel worked out from the bars printed for concrete read from a drawing. Silent when the run had no such concrete."""
  st = (stats or {}).get("steel") or {}
  if not st or st.get("reason") == "NO_MEMBERS":
    return []
  reason = st.get("reason")
  if reason in STEEL_REASON_TEXT:
    return [IssueSpec(
      code="STEEL_NOT_RUN", severity="info", blocks="NONE", dedupe_key="STEEL_NOT_RUN",
      message=f"Steel was not worked out from the bars printed on the drawing because {STEEL_REASON_TEXT[reason]}.",
      suggested_fix="Measure the reinforcement one way only, or remove the other.", details={"reason": reason})]
  specs: list[IssueSpec] = []
  skipped = st.get("skipped") or {}
  n = int(skipped.get("NO_BARS") or 0)
  
  if n:
    specs.append(IssueSpec(
      code="STEEL_BARS_NOT_PRINTED", severity="info", blocks="NONE", dedupe_key="STEEL_BARS_NOT_PRINTED",
      message=f"{n} member mark{'s' if n != 1 else ''} had no bars printed or typed, so no steel was taken for them.",
      suggested_fix="Type the bars when you accept the member, or add the steel for these members by hand.", details={"marks": n}))
  est = st.get("estimate") or {}
  if est.get("enabled") and int(est.get("members") or 0):
    total = float(st.get("kg") or 0)
    share = round(float(est["kg"]) / total * 100) if total > 0 else 0
    specs.append(IssueSpec(
      
      code="STEEL_ESTIMATED", severity="warning", blocks="NONE", dedupe_key="STEEL_ESTIMATED",
      message=f"{est['members']} member{' prints' if est['members'] == 1 else 's print'} no bars, so {'its' if est['members'] == 1 else 'their'} steel is an estimate: {float(est['kg']):.0f} kg, between {float(est['kg_low']):.0f} and {float(est['kg_high']):.0f} kg, "
        f"{share} percent of the {total:.0f} kg of steel. Slabs use the slab rule (kg per m2) and the other members the usual kg per m3 of concrete.",
      suggested_fix="Type the bars when you accept a member, and its estimate is replaced by its weight. Set the slab rule in the site assumptions if your surveyor uses another.",
      details={"members": est["members"], "kg": est["kg"], "kg_low": est["kg_low"], "kg_high": est["kg_high"], "by_family": est.get("by_family") or {}}))
  left = int((est.get("skipped") or {}).get("NO_USUAL_FIGURE") or 0)
  
  if est.get("enabled") and left:
    specs.append(IssueSpec(
      code="STEEL_NOT_ESTIMATED", severity="info", blocks="NONE", dedupe_key="STEEL_NOT_ESTIMATED",
      message=f"{left} wall, stair, tank or parapet member{'s' if left != 1 else ''} print no bars and have no usual steel figure, so no steel was taken for them.",
      suggested_fix="Type the bars when you accept the member, or add the steel for these members by hand.", details={"members": left}))
  for family, row in sorted((st.get("intensity") or {}).items()):
    if row.get("status") in ("BELOW_RANGE", "ABOVE_RANGE"):
      low, high = row["range"]
      specs.append(IssueSpec(
        code="STEEL_INTENSITY_OUT_OF_RANGE", severity="warning", blocks="NONE", dedupe_key=f"STEEL_INTENSITY_OUT_OF_RANGE:{family}",
        message=f"Steel in {family.lower()} members works out to {row['kg_per_m3']} kg per m3 of concrete, {'below' if row['status'] == 'BELOW_RANGE' else 'above'} the usual "
          f"range of {low} to {high}. The figure is not changed.",
        suggested_fix="Check the bar callouts and the member sizes read for these members.", details={"family": family, **row}))
  if st.get("lap_and_wastage_not_added"):
    specs.append(IssueSpec(
      code="STEEL_LAP_WASTAGE_NOT_ADDED", severity="info", blocks="NONE", dedupe_key="STEEL_LAP_WASTAGE_NOT_ADDED",
      message="Steel is the weight of the bars, rings and mesh as printed, cut by the site conventions in the assumptions (cover, hooks, column laps, anchorage). "
        "Chairs, binding wire and wastage are not added.",
      suggested_fix="Set the wastage percent in the site assumptions, or add it on the rate, as your estimating practice does.", details={"kg": st.get("kg"), "with_5pct_kg": st.get("with_5pct_kg")}))
  return specs

def takeoff_issue_specs(stats: dict) -> list[IssueSpec]:
  specs: list[IssueSpec] = []
  for n in stats.get("not_counted") or []:
    code, level = n["work_item_code"], n.get("level_id")
    specs.append(IssueSpec(
      code="PDF_MEASUREMENT_NOT_COUNTED", severity="warning", blocks="APPROVAL",
      message=f"{n['measurements']} PDF measurement(s) for {code} were not counted because the model already measures this work item.",
      suggested_fix="Open the PDF takeoff and choose Add to model, Replace model or Verify only for these measurements.",
      details={"work_item_code": code, "level_id": level, "count": n["measurements"]},
      dedupe_key=f"PDF_NOT_COUNTED:{code}:{level or 'ALL'}"))
    
  for reason, n in sorted((stats.get("skipped") or {}).items()):
    if reason == "PDF_UNCALIBRATED":
      specs.append(IssueSpec(
        code="PDF_UNCALIBRATED", severity="error", blocks="APPROVAL",
        message=f"{n} PDF measurement(s) have no calibration and were not measured.",
        suggested_fix="Calibrate the sheet and confirm the measurements again.", details={"count": n},
        dedupe_key="PDF_UNCALIBRATED"))
      
    elif reason == "PDF_MEASUREMENT_UNASSIGNED":
      specs.append(IssueSpec(
        code="PDF_MEASUREMENT_UNASSIGNED", severity="warning", blocks="NONE",
        message=f"{n} PDF measurement(s) have no work item and were not counted.",
        suggested_fix="Choose a work item for each measurement.", details={"count": n},
        dedupe_key="PDF_UNASSIGNED"))
      
    else:
      specs.append(IssueSpec(
        code="PDF_MEASUREMENT_SKIPPED", severity="warning", blocks="NONE",
        message=f"{n} PDF measurement(s) were not measured ({reason}).",
        suggested_fix="Open the PDF takeoff, fix these measurements and confirm them again.",
        details={"reason": reason, "count": n}, dedupe_key=f"PDF_SKIPPED:{reason}"))
      
  for v in stats.get("variances") or []:
    if not v.get("over_tolerance"):
      continue
    level = v.get("level_id")
    specs.append(IssueSpec(
      code="PDF_MODEL_VARIANCE", severity="warning" if level else "info", blocks="NONE",
      message=(f"The PDF takeoff differs from the model by {v['variance_pct']}% for {v['work_item_code']} "
        f"(PDF {v['pdf_quantity']} {v['unit']}, model {v['model_quantity']} {v['unit']}; tolerance {v['tolerance_pct']}%)."),
      suggested_fix="Check which of the two is right before approving; either the model or the PDF measurement is incomplete.",
      details=dict(v), dedupe_key=f"PDF_VARIANCE:{v['work_item_code']}:{level or 'ALL'}:{v['unit']}"))
  return specs

def ledger_warning_specs(rows: Iterable[tuple]) -> list[IssueSpec]:
  grouped: dict = {}
  for ledger_id, warnings in rows:
    for code in warnings or ():
      grouped.setdefault(code, []).append(str(ledger_id))
  specs = []
  for code in sorted(grouped):
    ids = grouped[code]
    severity, blocks, message, fix = LEDGER_WARNING_CATALOG.get(
      code, ("warning", "NONE", f"Ledger warning {code}.", None))
    specs.append(IssueSpec(
      code=code, severity=severity, blocks=blocks, message=f"{message} ({len(ids)} ledger row(s))",
      suggested_fix=fix, details={"count": len(ids), "ledger_ids": sorted(ids)[:50]},
      dedupe_key=f"LEDGER:{code}",
    ))
  return specs
