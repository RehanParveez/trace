from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import Callable, Iterable
import hashlib
import json

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

def make_item_key(code: str, unit: str, grade: str | None, level) -> str:
  return f"{code}|{unit}|{grade or '-'}|{level or '-'}"

def aggregate(lines: Iterable[LedgerLine], *, scope: str, preferred_units: dict | None,
  work_items: dict, waste_for: Callable[[str | None], Decimal]):
  groups: dict = {}
  for ln in lines:
    level = ln.level_id if scope == "level" else None
    groups.setdefault((ln.work_item_code, ln.unit, ln.material_grade or None, level), []).append(ln)

  drafts: list[ItemDraft] = []
  unknown: set = set()
  mismatch: set = set()
  for key in sorted(groups, key=lambda k: (k[0], k[1], k[2] or "", str(k[3] or ""))):
    code, unit, grade, level = key
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
    drafts.append(ItemDraft(
      item_key=make_item_key(code, unit, grade, level), work_item_code=code, level_id=level,
      material_grade=grade, canonical_unit=unit, unit=display, unit_factor=factor,
      canonical_total=total, net_quantity=net, waste_factor=waste, confidence=confidence,
      review_status="REVIEW_REQUIRED" if flagged else "OK",
      material_name=description[:300], description=description,
      category=wi.trade if wi else None,
      formula_text=f"Sum of {len(group)} ledger row(s) in {unit} x {factor} = {display}"[:500],
      element_count=len({l.element_id for l in group if l.element_id is not None}),
      lines=group,
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
  "OPENINGS_NOT_DEDUCTED": ("info", "NONE", "Wall volumes are gross of door and window openings.",
    "Opening deductions arrive with finishes and schedules; use an adjustment if one is needed now."),
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
  "OVER_DEDUCTED": ("error", "APPROVAL", "Deductions exceeded the gross volume; the quantity was clamped to zero.",
    "Report this model; the allocation is inconsistent."),
}

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