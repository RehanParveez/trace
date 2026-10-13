from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass
from typing import Callable

CANONICAL_UNITS = frozenset({"m3", "m2", "m", "kg", "nos"})

def _identity(quantity: Decimal) -> Decimal:
  return quantity

@dataclass(frozen=True)
class FormulaSpec:
  code: str
  output_unit: str
  description: str
  input_unit: str | None = None 
  group_evaluator: Callable[[Decimal], Decimal] | None = None

  @property
  def needs_kernel(self) -> bool:
    return self.group_evaluator is None

  def evaluate_group(self, parent_quantity: Decimal, parent_unit: str) -> Decimal | None:
    if self.group_evaluator is None or parent_unit != self.input_unit:
      return None
    return self.group_evaluator(parent_quantity)

_SPECS = (
  FormulaSpec("SOLID_NET_VOLUME", "m3", "Net solid volume after allocation (concrete, masonry, PCC).", "m3", _identity),
  FormulaSpec("WALL_NET_VOLUME", "m3", "Wall L x H x T less openings at/above threshold and allocated intrusions.", "m3", _identity),
  FormulaSpec("WALL_FACE_AREA_NET", "m2", "Wall face area per face less openings at/above threshold; reveals per convention."),
  FormulaSpec("PAINT_AREA", "m2", "Plaster area x coats."),
  FormulaSpec("SOLID_FORMWORK_AREA", "m2", "Exposed faces by role less contact faces with other concrete."),
  FormulaSpec("SLAB_SOFFIT_AREA", "m2", "Slab plan area less column footprints."),
  FormulaSpec("FLOOR_FINISH_AREA", "m2", "From space boundaries, else slab top net."),
  FormulaSpec("OPENING_COUNT", "nos", "Doors/windows by type mark and size.", "nos", _identity),
  FormulaSpec("FOOTING_PCC_VOLUME", "m3", "Footing plan plus projection x blinding thickness."),
  FormulaSpec("EXCAVATION_VOLUME", "m3", "Footing plan plus working space x depth (convention parameters)."),
  FormulaSpec("BACKFILL_VOLUME", "m3", "Excavation less the foundation, PCC bed and other structure standing in the trench."),
  FormulaSpec("REBAR_KG", "kg", "Sum of bar marks."),
  FormulaSpec("FINISH_FLOOR_AREA", "m2", "Net floor finish area."),
  FormulaSpec("FINISH_CEILING_AREA", "m2", "Ceiling finish area."),
  FormulaSpec("FINISH_WALL_AREA_NET", "m2", "Wall finish area after opening deductions."),
  FormulaSpec("FINISH_DADO_AREA_NET", "m2", "Dado finish area after applicable deductions."),
  FormulaSpec("FINISH_SKIRTING_LENGTH_NET", "m", "Skirting length after door deductions."),
  FormulaSpec("SCHEDULE_LINE_M3", "m3", "Confirmed mapped schedule quantity."),
  FormulaSpec("SCHEDULE_LINE_M2", "m2", "Confirmed mapped schedule quantity."),
  FormulaSpec("SCHEDULE_LINE_M", "m", "Confirmed mapped schedule quantity."),
  FormulaSpec("SCHEDULE_LINE_KG", "kg", "Confirmed mapped schedule quantity."),
  FormulaSpec("PDF_TAKEOFF_LENGTH", "m", "Calibrated PDF polyline length."),
  FormulaSpec("PDF_TAKEOFF_AREA", "m2", "Calibrated PDF polygon area less deduction polygons."),
  FormulaSpec("PDF_TAKEOFF_COUNT", "nos", "Counted PDF markers."),
  FormulaSpec("PDF_TAKEOFF_LENGTH_X_HEIGHT", "m2", "PDF length x height less openings, adjustments and repeats."),
  FormulaSpec("PDF_TAKEOFF_LENGTH_X_HEIGHT_X_THICKNESS", "m3", "PDF length x height less openings x thickness."),
  FormulaSpec("PDF_TAKEOFF_LENGTH_X_SECTION", "m3", "PDF length x section width x section depth."),
  FormulaSpec("PDF_TAKEOFF_AREA_X_THICKNESS", "m3", "PDF area x thickness."),
  FormulaSpec("PDF_TAKEOFF_COUNT_X_LENGTH", "m", "PDF count x unit length."),
  FormulaSpec("PDF_TAKEOFF_COUNT_X_AREA", "m2", "PDF count x unit length x unit width."),
  FormulaSpec("PDF_TAKEOFF_COUNT_X_VOLUME", "m3", "PDF count x unit length x width x depth."),
)

FORMULAS: dict[str, FormulaSpec] = {s.code: s for s in _SPECS}

def get_formula(code: str | None) -> FormulaSpec | None:
  return FORMULAS.get(code) if code else None

def check_component_units(
  formula_code: str,
  unit: str,
  output_unit: str | None = None,
) -> list[tuple[str, str]]:
  """Returns [(issue_code, message)]; empty list means unit-safe."""
  spec = get_formula(formula_code)
  if spec is None:
    return [("FORMULA_UNKNOWN", f"Unknown formula code '{formula_code}'.")]
  problems: list[tuple[str, str]] = []
  if unit != spec.output_unit:
    problems.append((
      "RECIPE_UNIT_MISMATCH",
      f"Component unit '{unit}' does not match formula {formula_code} output unit '{spec.output_unit}'.",
    ))
  if output_unit is not None and output_unit != spec.output_unit:
    problems.append((
      "RECIPE_UNIT_MISMATCH",
      f"Component output_unit '{output_unit}' does not match formula {formula_code} output unit '{spec.output_unit}'.",
    ))
  return problems