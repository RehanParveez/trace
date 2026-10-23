from __future__ import annotations
from decimal import Decimal, Context, InvalidOperation, ROUND_HALF_EVEN
from app.engine.measure.rebar import REBAR_WORK_ITEM
from app.engine.measure.steel import STEEL_PILE_CODE, STEEL_SECTION_CODE
from uuid import UUID, uuid5
import hashlib
import json
from dataclasses import dataclass, field
from collections import defaultdict
from app.engine.measure.units import q4, q6
from app.engine.measure.models import Solid, LedgerEntry
from app.engine.measure.spec import spec_key as _spec_key

MEMBERS = ("foundation", "frame", "wall", "pile")

def member_spec(m) -> dict | None:
  member = str((m.params or {}).get("member") or "").lower()
  if member not in MEMBERS or not str(m.work_item_code or "").upper().startswith("CON-RCC"):
    return None
  return {"kind": "CONCRETE", "member": member, "basis": {"member": "drawing_category"}}

ZERO, ONE, HUNDRED = Decimal("0"), Decimal("1"), Decimal("100")
Q4 = Decimal("0.0001")
MM2_PER_M2 = Decimal("1000000")
MM_PER_M = Decimal("1000")
_C = Context(prec=40, rounding=ROUND_HALF_EVEN)

SOURCE_KIND = "PDF_TAKEOFF"
PT_MM = _C.divide(Decimal("25.4"), Decimal("72"))
RESERVED_CODES = frozenset({REBAR_WORK_ITEM, STEEL_SECTION_CODE, STEEL_PILE_CODE})
MAX_VERTICES = 2000
MAX_REPEAT = 1000
MIN_BASELINE_PT = Decimal("100")
CAL_PICK_TOL_PT = Decimal("0.5")
RATIO_PRINT_TOLERANCE = Decimal("0.02")
TAKEOFF_BASE_CONFIDENCE = Decimal("0.95")
DEFAULT_VARIANCE_TOLERANCE_PCT = Decimal("5")

CONTENT_FACTOR = {"VECTOR": ONE, "UNKNOWN": Decimal("0.95"), "RASTER": Decimal("0.85")}
PICK_TOLERANCE_PT = {
  ("VECTOR", "VECTOR_SNAP"): Decimal("0.10"), ("VECTOR", "MANUAL"): Decimal("0.50"),
  ("UNKNOWN", "VECTOR_SNAP"): Decimal("0.15"), ("UNKNOWN", "MANUAL"): Decimal("0.60"),
  ("RASTER", "VECTOR_SNAP"): Decimal("1.00"), ("RASTER", "MANUAL"): Decimal("1.00"),
}

MODES = {
  ("LENGTH", "DIRECT"): ("PDF_TAKEOFF_LENGTH", "m", ()),
  ("LENGTH", "LENGTH_X_HEIGHT"): ("PDF_TAKEOFF_LENGTH_X_HEIGHT", "m2", ("height_mm",)),
  ("LENGTH", "LENGTH_X_HEIGHT_X_THICKNESS"): ("PDF_TAKEOFF_LENGTH_X_HEIGHT_X_THICKNESS", "m3", ("height_mm", "thickness_mm")),
  ("LENGTH", "LENGTH_X_SECTION"): ("PDF_TAKEOFF_LENGTH_X_SECTION", "m3", ("width_mm", "depth_mm")),
  ("AREA", "DIRECT"): ("PDF_TAKEOFF_AREA", "m2", ()),
  ("AREA", "AREA_X_THICKNESS"): ("PDF_TAKEOFF_AREA_X_THICKNESS", "m3", ("thickness_mm",)),
  ("COUNT", "DIRECT"): ("PDF_TAKEOFF_COUNT", "nos", ()),
  ("COUNT", "COUNT_X_LENGTH"): ("PDF_TAKEOFF_COUNT_X_LENGTH", "m", ("length_mm",)),
  ("COUNT", "COUNT_X_AREA"): ("PDF_TAKEOFF_COUNT_X_AREA", "m2", ("length_mm", "width_mm")),
  ("COUNT", "COUNT_X_VOLUME"): ("PDF_TAKEOFF_COUNT_X_VOLUME", "m3", ("length_mm", "width_mm", "depth_mm")),
}

TAKEOFF_FORMULA_UNITS = {f: u for f, u, _ in MODES.values()}
RECON_MODES = ("AUTO", "ADD", "REPLACE_MODEL", "VERIFY_ONLY")
WARNING_CODES = ("PDF_LOW_PRECISION", "PDF_SCALE_MISMATCH", "PDF_SCANNED_LOW_PRECISION", "PDF_DIMENSION_ASSUMED",
  "PDF_CAL_SHORT_BASELINE", "PDF_RATIO_UNVERIFIED", "PDF_GEOMETRY_WARNING", "PDF_OVER_DEDUCTED",
  "PDF_ADDED_TO_MODEL", "PDF_REPLACES_MODEL")

class TakeoffError(Exception):
  def __init__(self, code: str, message: str):
    super().__init__(message)
    self.code = code
    self.message = message

@dataclass(frozen=True)
class SheetInput:
  id: UUID
  drawing_id: UUID
  page_no: int
  content_kind: str = "UNKNOWN"
  label: str | None = None
  level_id: UUID | None = None

@dataclass(frozen=True)
class CalibrationInput:
  id: UUID
  sheet_id: UUID
  method: str
  ratio: Decimal | None = None
  p1: tuple | None = None
  p2: tuple | None = None
  known_mm: Decimal | None = None
  check_p1: tuple | None = None
  check_p2: tuple | None = None
  check_known_mm: Decimal | None = None
  label: str | None = None
  user_unit: Decimal = ONE

@dataclass(frozen=True)
class MeasurementInput:
  id: UUID
  sheet_id: UUID
  calibration_id: UUID | None
  kind: str
  quantity_mode: str
  geometry: dict
  params: dict
  work_item_code: str | None
  level_id: UUID | None = None
  label: str | None = None
  tag: str | None = None
  material_grade: str | None = None
  recon_mode: str = "AUTO"
  source: str = "MANUAL"


@dataclass(frozen=True)
class MemberInput:
  """One mark of a counted member read from a PDF (a footing mark), placed on its drawing view. The element ids are the ones the PDF register
  gave each mark, so the derived rows can point back to them. Positions are the mark positions in millimetres, not drawn outlines."""
  measurement_id: UUID
  candidate_id: UUID
  sheet_id: UUID
  page_no: int
  category: str
  tag: str | None
  frame: str
  level_id: UUID | None
  element_ids: tuple
  points_mm: tuple
  length_mm: Decimal
  width_mm: Decimal
  depth_mm: Decimal
  confidence: Decimal = ONE
  position_basis: str = "MARK"


@dataclass(frozen=True)
class FormworkInput:
  """One counted concrete member read from a PDF (a column, footing, slab or lintel mark) with the size its measurement used. It carries no position,
  so a member on a sheet whose scale is unusable can still be shuttered: the area comes from the size alone."""
  measurement_id: UUID
  candidate_id: UUID
  sheet_id: UUID
  page_no: int
  category: str
  tag: str | None
  level_id: UUID | None
  element_ids: tuple
  count: int
  length_mm: Decimal
  width_mm: Decimal
  depth_mm: Decimal
  confidence: Decimal = ONE
  steel: dict | None = None
  stair: dict | None = None
  frame: str | None = None
  points_mm: tuple = ()
  role: str | None = None
  site: dict | None = None
  openings: tuple = ()

@dataclass(frozen=True)
class RangeInput:
  measurement_id: UUID
  grade: str
  bounded: bool
  low_pct: float | None = None
  high_pct: float | None = None
  leaves_out: bool = False
  drivers: tuple = ()

@dataclass(frozen=True)
class AlignmentInput:
  view: str
  dx_mm: Decimal
  dy_mm: Decimal
  method: str
  grade: str = "ASSUMED"
  supporters: int = 0
  compared: int = 0
  residual_mm: Decimal = Decimal("0")
  reference: bool = False
  group: str = ""
  origin_x_mm: Decimal = Decimal("0")
  origin_y_mm: Decimal = Decimal("0")

@dataclass(frozen=True)
class SpaceInput:
  measurement_id: UUID
  candidate_id: UUID
  sheet_id: UUID
  group: str
  page_no: int
  category: str
  tag: str | None
  level_id: UUID | None
  frame: str
  shape: str = "NONE"
  parts: tuple = ()
  length_mm: Decimal = ZERO
  width_mm: Decimal = ZERO
  z0_mm: float | None = None
  z1_mm: float | None = None
  z_grade: str = "ASSUMED"
  floor: str | None = None
  covered_by_band: bool = False

@dataclass(frozen=True)
class FloorDatum:
  group: str
  key: str
  level_mm: float
  soffit_mm: float | None = None
  top_mm: float | None = None
  grade: str = "ASSUMED"

@dataclass(frozen=True)
class TakeoffInputs:
  sheets: tuple = ()
  calibrations: tuple = ()
  measurements: tuple = ()
  members: tuple = ()
  formwork: tuple = ()
  alignments: tuple = ()
  space: tuple = ()
  floors: tuple = ()
  ranges: tuple = ()

@dataclass(frozen=True)
class CalibrationEval:
  usable: bool
  mm_per_pt: Decimal | None
  error_pct: Decimal | None
  factor: Decimal
  scale_uncertainty: Decimal
  baseline_pt: Decimal | None
  warnings: tuple = ()
  reason: str | None = None

@dataclass(frozen=True)
class Computed:
  quantity: Decimal
  unit: str
  formula: str
  steps: list
  warnings: tuple
  confidence: Decimal
  uncertainty_pct: Decimal
  inputs: dict
  geometry_hash: str

@dataclass(frozen=True)
class TakeoffResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  results: list = field(default_factory=list)
  dropped_keys: frozenset = frozenset()
  stats: dict = field(default_factory=dict)

def output_unit(kind: str, quantity_mode: str) -> str | None:
  spec = MODES.get((kind, quantity_mode))
  return spec[1] if spec else None

def required_params(kind: str, quantity_mode: str) -> tuple:
  spec = MODES.get((kind, quantity_mode))
  return spec[2] if spec else ()

def needs_calibration(kind: str, quantity_mode: str) -> bool:
  return kind in ("LENGTH", "AREA")

def _dec(value, name: str) -> Decimal:
  try:
    d = value if isinstance(value, Decimal) else Decimal(str(value).strip())
  except (InvalidOperation, ValueError, AttributeError):
    raise TakeoffError("INVALID_NUMBER", f"{name} is not a number.")
  if not d.is_finite():
    raise TakeoffError("INVALID_NUMBER", f"{name} is not a finite number.")
  return d

def _positive(value, name: str) -> Decimal:
  d = _dec(value, name)
  if d <= 0:
    raise TakeoffError("INVALID_NUMBER", f"{name} must be greater than zero.")
  return d

def _pt(raw, name: str) -> tuple:
  try:
    x, y = raw
  except (TypeError, ValueError):
    raise TakeoffError("INVALID_POINT", f"{name} must be an [x, y] pair.")
  return (_dec(x, name).quantize(Q4), _dec(y, name).quantize(Q4))

def _dist(a: tuple, b: tuple) -> Decimal:
  dx, dy = a[0] - b[0], a[1] - b[1]
  return _C.sqrt(dx * dx + dy * dy)

def _dedupe_consecutive(points: list) -> list:
  out: list = []
  for p in points:
    if not out or out[-1] != p:
      out.append(p)
  return out

def _points(raw, name: str, minimum: int) -> list:
  if not isinstance(raw, (list, tuple)):
    raise TakeoffError("INVALID_GEOMETRY", f"{name} must be a list of points.")
  if len(raw) > MAX_VERTICES:
    raise TakeoffError("GEOMETRY_TOO_LARGE", f"{name} has more than {MAX_VERTICES} points.")
  pts = [_pt(p, name) for p in raw]
  return pts

def polyline_length_pt(points: list, closed: bool = False) -> Decimal:
  total = sum((_dist(points[i], points[i + 1]) for i in range(len(points) - 1)), ZERO)
  if closed and len(points) > 2:
    total += _dist(points[-1], points[0])
  return total

def ring_area_pt2(ring: list) -> Decimal:
  s = ZERO
  for i in range(len(ring)):
    x1, y1 = ring[i]
    x2, y2 = ring[(i + 1) % len(ring)]
    s += x1 * y2 - x2 * y1
  return abs(s) / 2

def _orient(a, b, c) -> int:
  v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
  return (v > 0) - (v < 0)

def _on_segment(a, b, c) -> bool:
  return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])

def _segments_intersect(p1, p2, p3, p4) -> bool:
  o1, o2, o3, o4 = _orient(p1, p2, p3), _orient(p1, p2, p4), _orient(p3, p4, p1), _orient(p3, p4, p2)
  if o1 != o2 and o3 != o4:
    return True
  return ((o1 == 0 and _on_segment(p1, p2, p3)) or (o2 == 0 and _on_segment(p1, p2, p4))
    or (o3 == 0 and _on_segment(p3, p4, p1)) or (o4 == 0 and _on_segment(p3, p4, p2)))

def ring_is_simple(ring: list) -> bool:
  n = len(ring)
  boxes = [(float(min(ring[i][0], ring[(i + 1) % n][0])), float(max(ring[i][0], ring[(i + 1) % n][0])),
    float(min(ring[i][1], ring[(i + 1) % n][1])), float(max(ring[i][1], ring[(i + 1) % n][1]))) for i in range(n)]
  
  for i in range(n):
    for j in range(i + 2, n):
      if i == 0 and j == n - 1:
        continue
      bi, bj = boxes[i], boxes[j]
      if bi[1] < bj[0] or bj[1] < bi[0] or bi[3] < bj[2] or bj[3] < bi[2]:
        continue
      if _segments_intersect(ring[i], ring[(i + 1) % n], ring[j], ring[(j + 1) % n]):
        return False
  return True

def point_in_ring(pt: tuple, ring: list) -> bool:
  x, y = pt
  inside = False
  n = len(ring)
  for i in range(n):
    a, b = ring[i], ring[(i + 1) % n]
    if _orient(a, b, pt) == 0 and _on_segment(a, b, pt):
      return True
    if (a[1] > y) != (b[1] > y):
      x_cross = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
      if x < x_cross:
        inside = not inside
  return inside

def _ring(raw, name: str) -> list:
  pts = _dedupe_consecutive(_points(raw, name, 3))
  if len(pts) > 1 and pts[0] == pts[-1]:
    pts.pop()
  if len(pts) < 3:
    raise TakeoffError("INVALID_GEOMETRY", f"{name} needs at least three distinct points.")
  if not ring_is_simple(pts):
    raise TakeoffError("SELF_INTERSECTING", f"{name} crosses itself; redraw it without crossing lines.")
  if ring_area_pt2(pts) <= 0:
    raise TakeoffError("INVALID_GEOMETRY", f"{name} has no area (all points on one line).")
  return pts

def _norm_geometry(kind: str, geometry: dict) -> dict:
  g = geometry or {}
  if kind == "LENGTH":
    pts = _dedupe_consecutive(_points(g.get("points"), "points", 2))
    if len(pts) < 2:
      raise TakeoffError("INVALID_GEOMETRY", "A length needs at least two distinct points.")
    return {"points": pts, "closed": bool(g.get("closed", False))}

  if kind == "AREA":
    outer = _ring(g.get("outer"), "outer")
    holes = [_ring(h, f"hole {i + 1}") for i, h in enumerate(g.get("holes") or [])]
    return {"outer": outer, "holes": holes}

  if kind == "COUNT":
    raw = _points(g.get("points"), "points", 1)
    seen, uniq = set(), []
    for p in raw:
      if p not in seen:
        seen.add(p)
        uniq.append(p)
        
    if not uniq:
      raise TakeoffError("INVALID_GEOMETRY", "A count needs at least one marker.")
    return {"points": uniq, "duplicates_removed": len(raw) - len(uniq)}
  raise TakeoffError("INVALID_KIND", f"Unknown measurement kind '{kind}'.")

def parse_point(raw, name: str = "point") -> tuple:
  return _pt(raw, name)

def normalized_geometry(kind: str, geometry: dict) -> dict:
  g = _norm_geometry(kind, geometry)
  def pt(p):
    return [float(p[0]), float(p[1])]
  if kind == "LENGTH":
    return {"points": [pt(p) for p in g["points"]], "closed": g["closed"]}
  if kind == "AREA":
    return {"outer": [pt(p) for p in g["outer"]], "holes": [[pt(p) for p in h] for h in g["holes"]]}
  return {"points": [pt(p) for p in g["points"]]}

def geometry_hash(kind: str, geometry: dict) -> str:
  g = _norm_geometry(kind, geometry)
  def enc(v):
    if isinstance(v, tuple):
      return [str(x) for x in v]
    if isinstance(v, list):
      return [enc(x) for x in v]
    return v
  blob = json.dumps({"k": kind, "g": {k: enc(v) for k, v in g.items()}}, sort_keys=True, separators=(",", ":"))
  return hashlib.sha256(blob.encode("utf-8")).hexdigest()

def ratio_from_imperial(paper_inches: Decimal, real_inches: Decimal) -> Decimal:
  return _C.divide(_positive(real_inches, "real"), _positive(paper_inches, "paper"))

def evaluate_calibration(cal: CalibrationInput) -> CalibrationEval:
  warnings: list = []
  if cal.method == "TWO_POINT":
    if cal.p1 is None or cal.p2 is None or cal.known_mm is None:
      return CalibrationEval(False, None, None, ZERO, ONE, None, (), "Two points and a known distance are required.")
    baseline = _dist(cal.p1, cal.p2)
    
    if baseline <= 0:
      return CalibrationEval(False, None, None, ZERO, ONE, baseline, (), "The two calibration points are the same.")
    if cal.known_mm <= 0:
      return CalibrationEval(False, None, None, ZERO, ONE, baseline, (), "The known distance must be greater than zero.")
    mm_per_pt = _C.divide(cal.known_mm, baseline)
    factor = Decimal("0.92")
    unc = _C.divide(CAL_PICK_TOL_PT * _C.sqrt(Decimal(2)), baseline)
    if baseline < MIN_BASELINE_PT:
      warnings.append("PDF_CAL_SHORT_BASELINE")
      factor *= Decimal("0.9")
      
  elif cal.method == "SCALE_RATIO":
    if cal.ratio is None or cal.ratio <= 0:
      return CalibrationEval(False, None, None, ZERO, ONE, None, (), "A scale ratio greater than zero is required.")
    mm_per_pt = cal.ratio * PT_MM * cal.user_unit
    baseline = None
    factor = Decimal("0.80")
    unc = RATIO_PRINT_TOLERANCE
    warnings.append("PDF_RATIO_UNVERIFIED")
  else:
    return CalibrationEval(False, None, None, ZERO, ONE, None, (), f"Unknown calibration method '{cal.method}'.")

  error_pct = None
  if cal.check_p1 is not None and cal.check_p2 is not None and cal.check_known_mm:
    check_pt = _dist(cal.check_p1, cal.check_p2)
    if check_pt <= 0 or cal.check_known_mm <= 0:
      return CalibrationEval(False, mm_per_pt, None, ZERO, unc, baseline, tuple(warnings), "The check dimension is invalid.")
    measured = check_pt * mm_per_pt
    error_pct = q4(abs(measured - cal.check_known_mm) / cal.check_known_mm * HUNDRED)
    warnings = [w for w in warnings if w != "PDF_RATIO_UNVERIFIED"]
    
    if error_pct > 2:
      warnings.append("PDF_SCALE_MISMATCH")
      return CalibrationEval(False, mm_per_pt, error_pct, ZERO, unc, baseline, tuple(warnings),
        f"The check dimension differs by {error_pct}% (limit 2%). Re-calibrate.")
      
    if error_pct > 1:
      warnings.append("PDF_SCALE_MISMATCH")
      factor = Decimal("0.85")
    elif error_pct > Decimal("0.5"):
      factor = Decimal("0.95")
    else:
      factor = ONE if baseline is None or baseline >= MIN_BASELINE_PT else Decimal("0.9")
    unc = max(error_pct / HUNDRED, _C.divide(CAL_PICK_TOL_PT * _C.sqrt(Decimal(2)), check_pt))
  return CalibrationEval(True, mm_per_pt, error_pct, factor, unc, baseline, tuple(dict.fromkeys(warnings)))

def _precision_factor(pct: Decimal) -> Decimal:
  for limit, factor in ((ONE, ONE), (Decimal(2), Decimal("0.95")), (Decimal(3), Decimal("0.9")),
    (Decimal(5), Decimal("0.8")), (Decimal(10), Decimal("0.65"))):
    if pct <= limit:
      return factor
  return Decimal("0.5")

def _clamp01(v: Decimal) -> Decimal:
  return max(ZERO, min(ONE, v))

def _params(kind: str, mode: str, params: dict) -> dict:
  p = params or {}
  out: dict = {}
  for name in required_params(kind, mode):
    if p.get(name) in (None, ""):
      raise TakeoffError("MISSING_DIMENSION", f"{name} is required for {mode}.")
    out[name] = _positive(p[name], name)
  repeat = p.get("repeat", 1)
  
  try:
    repeat = int(repeat)
  except (TypeError, ValueError):
    raise TakeoffError("INVALID_NUMBER", "repeat must be a whole number.")
  if repeat < 1 or repeat > MAX_REPEAT:
    raise TakeoffError("INVALID_NUMBER", f"repeat must be between 1 and {MAX_REPEAT}.")
  out["repeat"] = repeat
  basis = str(p.get("dims_basis") or "DRAWN").upper()
  out["dims_basis"] = basis if basis in ("DRAWN", "SPECIFIED", "ASSUMED") else "DRAWN"
  
  openings = []
  for i, o in enumerate(p.get("openings") or []):
    role = str(o.get("role") or "OPENING").upper()
    openings.append({"role": role, "width_mm": _positive(o.get("width_mm"), f"opening {i + 1} width"),
      "height_mm": _positive(o.get("height_mm"), f"opening {i + 1} height"),
      "nos": int(_positive(o.get("nos", 1), f"opening {i + 1} nos")), "label": o.get("label")})
  if openings and mode not in ("LENGTH_X_HEIGHT", "LENGTH_X_HEIGHT_X_THICKNESS"):
    raise TakeoffError("INVALID_PARAMS", "Openings can only be deducted from wall length x height measurements.")
  out["openings"] = openings
  adjustments = []
  for i, a in enumerate(p.get("adjustments") or []):
    op = str(a.get("op") or "").upper()
    if op not in ("LESS", "ADD"):
      raise TakeoffError("INVALID_PARAMS", f"adjustment {i + 1} must be LESS or ADD.")
    adjustments.append({"op": op, "value": _positive(a.get("value"), f"adjustment {i + 1}"), "label": a.get("label")})
  out["adjustments"] = adjustments
  return out

def compute_measurement(m: MeasurementInput, sheet: SheetInput, cal: CalibrationEval | None, profile=None) -> Computed:
  spec = MODES.get((m.kind, m.quantity_mode))
  
  if spec is None:
    raise TakeoffError("INVALID_MODE", f"{m.quantity_mode} is not available for a {m.kind.lower()} measurement.")
  formula, unit, _ = spec
  geo = _norm_geometry(m.kind, m.geometry)
  prm = _params(m.kind, m.quantity_mode, m.params)
  ghash = geometry_hash(m.kind, m.geometry)
  steps: list = []
  warnings: list = []
  inputs: dict = {"kind": m.kind, "quantity_mode": m.quantity_mode}
  tol = PICK_TOLERANCE_PT.get((sheet.content_kind, "VECTOR_SNAP" if m.source == "VECTOR_SNAP" else "MANUAL"), Decimal("0.6"))
  rel_pick = ZERO
  rel_scale = ZERO

  if m.kind in ("LENGTH", "AREA"):
    if cal is None:
      raise TakeoffError("PDF_UNCALIBRATED", "This measurement has no calibration.")
    if not cal.usable:
      raise TakeoffError("CALIBRATION_UNUSABLE", cal.reason or "The calibration is not usable.")
    scale = cal.mm_per_pt
    inputs["mm_per_pt"] = str(scale.quantize(Decimal("0.00000001")))
    warnings.extend(cal.warnings)

  if m.kind == "LENGTH":
    length_pt = polyline_length_pt(geo["points"], geo["closed"])
    length_m = length_pt * scale / MM_PER_M
    steps.append({"op": "measure_length", "points": len(geo["points"]), "pt": str(q6(length_pt)), "m": str(q6(length_m))})
    rel_pick = _C.divide(tol * _C.sqrt(Decimal(len(geo["points"]))), length_pt)
    rel_scale = cal.scale_uncertainty
    base = length_m
    inputs["length_m"] = str(q6(length_m))
    
  elif m.kind == "AREA":
    outer_pt2 = ring_area_pt2(geo["outer"])
    hole_pt2 = ZERO
    for h in geo["holes"]:
      if not all(point_in_ring(p, geo["outer"]) for p in h):
        warnings.append("PDF_GEOMETRY_WARNING")
        steps.append({"op": "warning", "note": "A deduction polygon lies partly outside the outer boundary."})
      hole_pt2 += ring_area_pt2(h)
    k = scale * scale / MM2_PER_M2
    gross_m2, holes_m2 = outer_pt2 * k, hole_pt2 * k
    net_m2 = gross_m2 - holes_m2
    steps.append({"op": "gross_area", "m2": str(q6(gross_m2))})
    
    for i, h in enumerate(geo["holes"]):
      steps.append({"op": "deduction", "type": "VOID_DEDUCTION", "m2": str(q6(ring_area_pt2(h) * k)), "note": f"Deduction polygon {i + 1}"})
    if net_m2 < 0:
      warnings.append("PDF_OVER_DEDUCTED")
      net_m2 = ZERO
    perimeter_pt = polyline_length_pt(geo["outer"], True) + sum((polyline_length_pt(h, True) for h in geo["holes"]), ZERO)
    rel_pick = _C.divide(tol * perimeter_pt, outer_pt2 - hole_pt2) if outer_pt2 > hole_pt2 else ONE
    rel_scale = cal.scale_uncertainty * 2
    base = net_m2
    inputs["area_m2"] = str(q6(net_m2))
    
  else:
    n = len(geo["points"])
    steps.append({"op": "count", "nos": str(n)})
    if geo.get("duplicates_removed"):
      steps.append({"op": "note", "note": f"{geo['duplicates_removed']} duplicate marker(s) ignored."})
    base = Decimal(n)

  mode = m.quantity_mode
  quantity = base
  if mode == "LENGTH_X_HEIGHT":
    quantity = base * prm["height_mm"] / MM_PER_M
    steps.append({"op": "multiply", "by": "height_mm", "value": str(prm["height_mm"]), "m2": str(q6(quantity))})
    quantity = _openings(quantity, prm, profile, steps, warnings, volume=False)
  elif mode == "LENGTH_X_HEIGHT_X_THICKNESS":
    area = base * prm["height_mm"] / MM_PER_M
    steps.append({"op": "multiply", "by": "height_mm", "value": str(prm["height_mm"]), "m2": str(q6(area))})
    area = _openings(area, prm, profile, steps, warnings, volume=False)
    quantity = area * prm["thickness_mm"] / MM_PER_M
    steps.append({"op": "multiply", "by": "thickness_mm", "value": str(prm["thickness_mm"]), "m3": str(q6(quantity))})
  elif mode == "LENGTH_X_SECTION":
    quantity = base * prm["width_mm"] * prm["depth_mm"] / MM2_PER_M2
    steps.append({"op": "multiply", "by": "width_mm x depth_mm", "value": f"{prm['width_mm']} x {prm['depth_mm']}", "m3": str(q6(quantity))})
  elif mode == "AREA_X_THICKNESS":
    quantity = base * prm["thickness_mm"] / MM_PER_M
    steps.append({"op": "multiply", "by": "thickness_mm", "value": str(prm["thickness_mm"]), "m3": str(q6(quantity))})
  elif mode == "COUNT_X_LENGTH":
    quantity = base * prm["length_mm"] / MM_PER_M
    steps.append({"op": "multiply", "by": "length_mm", "value": str(prm["length_mm"]), "m": str(q6(quantity))})
  elif mode == "COUNT_X_AREA":
    quantity = base * prm["length_mm"] * prm["width_mm"] / MM2_PER_M2
    steps.append({"op": "multiply", "by": "length_mm x width_mm", "value": f"{prm['length_mm']} x {prm['width_mm']}", "m2": str(q6(quantity))})
  elif mode == "COUNT_X_VOLUME":
    quantity = base * prm["length_mm"] * prm["width_mm"] * prm["depth_mm"] / (MM_PER_M ** 3)
    steps.append({"op": "multiply", "by": "length_mm x width_mm x depth_mm",
      "value": f"{prm['length_mm']} x {prm['width_mm']} x {prm['depth_mm']}", "m3": str(q6(quantity))})

  for a in prm["adjustments"]:
    delta = a["value"] if a["op"] == "ADD" else -a["value"]
    quantity += delta
    steps.append({"op": "adjustment", "type": a["op"], unit: str(q6(a["value"])), "note": a["label"] or a["op"].title()})
  if quantity < 0:
    warnings.append("PDF_OVER_DEDUCTED")
    quantity = ZERO
  if prm["repeat"] > 1:
    quantity *= prm["repeat"]
    steps.append({"op": "repeat", "times": prm["repeat"], unit: str(q6(quantity))})
    inputs["repeat"] = prm["repeat"]

  final = Decimal(int(quantity.to_integral_value())) if unit == "nos" else q6(quantity)
  steps.append({"op": "net", unit: str(final)})

  if m.kind == "COUNT":
    unc_pct = ZERO
    confidence = TAKEOFF_BASE_CONFIDENCE
    
  else:
    rel = _C.sqrt(rel_pick * rel_pick + rel_scale * rel_scale)
    unc_pct = q4(rel * HUNDRED)
    pf = _precision_factor(unc_pct)
    if sheet.content_kind == "RASTER":
      warnings.append("PDF_SCANNED_LOW_PRECISION")
      
    if pf < Decimal("0.8"):
      warnings.append("PDF_LOW_PRECISION")
    confidence = TAKEOFF_BASE_CONFIDENCE * cal.factor * CONTENT_FACTOR.get(sheet.content_kind, Decimal("0.95")) * pf
    inputs["uncertainty_pct"] = str(unc_pct)
  if prm["dims_basis"] == "ASSUMED" and mode != "DIRECT":
    warnings.append("PDF_DIMENSION_ASSUMED")
    confidence *= Decimal("0.85")
    
  for name in ("height_mm", "thickness_mm", "width_mm", "depth_mm", "length_mm"):
    if name in prm:
      inputs[name] = str(prm[name])
  inputs["dims_basis"] = prm["dims_basis"]
  return Computed(quantity=final, unit=unit, formula=formula, steps=steps,
    warnings=tuple(dict.fromkeys(warnings)), confidence=q4(_clamp01(confidence)), uncertainty_pct=unc_pct,
    inputs=inputs, geometry_hash=ghash)

def _openings(area: Decimal, prm: dict, profile, steps: list, warnings: list, volume: bool) -> Decimal:
  net = area
  
  for o in prm["openings"]:
    each = o["width_mm"] * o["height_mm"] / MM2_PER_M2
    scope = o["role"] if o["role"] in ("DOOR", "WINDOW") else "ALL"
    behavior, fraction = profile.opening_behavior(scope, each) if profile is not None else ("DEDUCT", ONE)
    label = f"{o['role'].title()} {int(o['width_mm'])}x{int(o['height_mm'])} mm x {o['nos']}"
    
    if behavior == "IGNORE":
      steps.append({"op": "deduction", "type": "OPENING_IGNORED", "m2": "0", "note": f"{label}: below the deduction threshold, not deducted."})
      continue
    cut = each * o["nos"] * fraction
    net -= cut
    steps.append({"op": "deduction", "type": "VOID_DEDUCTION", "m2": str(q6(cut)), "behavior": behavior, "note": label})
  if net < 0:
    warnings.append("PDF_OVER_DEDUCTED")
    net = ZERO
  return net

def _variance_tolerance(profile) -> Decimal:
  try:
    raw = (getattr(profile, "tolerances", None) or {}).get("pdf_model_variance_pct")
    return _positive(raw, "tolerance") if raw is not None else DEFAULT_VARIANCE_TOLERANCE_PCT
  except TakeoffError:
    return DEFAULT_VARIANCE_TOLERANCE_PCT

def range_trace(inputs, measurement_id) -> dict | None:
  """The range of the mark behind a measurement, as it is written on a ledger row's trace, or None when the mark was graded by no one (a hand measurement)."""
  for r in tuple(getattr(inputs, "ranges", ()) or ()):
    if str(r.measurement_id) == str(measurement_id):
      return {"grade": r.grade, "bounded": bool(r.bounded), "low_pct": r.low_pct, "high_pct": r.high_pct, "leaves_out": bool(r.leaves_out),
        "drivers": [dict(d) for d in r.drivers]}
  return None

def measure_takeoff(ctx, profile, inputs: TakeoffInputs | None, model_ledger=(), elements=()) -> TakeoffResult:
  if inputs is None or not inputs.measurements:
    return TakeoffResult(stats={"measurements": 0})
  sheets = {s.id: s for s in inputs.sheets}
  cals = {c.id: c for c in inputs.calibrations}
  cal_evals: dict = {}
  for cid, c in cals.items():
    try:
      cal_evals[cid] = evaluate_calibration(c)
    except TakeoffError as exc:
      cal_evals[cid] = CalibrationEval(False, None, None, ZERO, ONE, None, (), exc.message)

  skipped: dict = {}
  results: list = []
  ok: list = []
  from app.engine.measure import one_total_rules as RU
  import dataclasses as _dc
  item_rules = tuple(r for r in (getattr(ctx, "one_total_rules", ()) or ()) if r.kind == RU.ITEM)
  item_ruled: dict = {}
  item_ruled_groups: dict = {}

  def skip(m, code: str, reason: str):
    skipped[code] = skipped.get(code, 0) + 1
    results.append({"measurement_id": str(m.id), "decision": "SKIPPED", "reason": code, "message": reason,
      "work_item_code": m.work_item_code, "level_id": str(m.level_id) if m.level_id else None})

  for m in sorted(inputs.measurements, key=lambda x: str(x.id)):
    sheet = sheets.get(m.sheet_id)
    if sheet is None:
      skip(m, "SHEET_MISSING", "The sheet no longer exists.")
      continue
    if not m.work_item_code:
      skip(m, "PDF_MEASUREMENT_UNASSIGNED", "No work item was chosen.")
      continue
    if m.work_item_code in RESERVED_CODES:
      skip(m, "WORK_ITEM_RESERVED", f"{m.work_item_code} is measured from bar schedules or the model, not from a PDF.")
      continue
    cal = None
    if needs_calibration(m.kind, m.quantity_mode):
      cal = cal_evals.get(m.calibration_id) if m.calibration_id else None
      if cal is None:
        skip(m, "PDF_UNCALIBRATED", "The measurement has no calibration.")
        continue
      if not cal.usable:
        skip(m, "CALIBRATION_UNUSABLE", cal.reason or "The calibration is not usable.")
        continue
    
    try:
      comp = compute_measurement(m, sheet, cal, profile)
    except TakeoffError as exc:
      skip(m, exc.code, exc.message)
      continue
    if comp.quantity <= 0:
      skip(m, "ZERO_QUANTITY", "The measurement came to zero.")
      continue
    rule = RU.find(item_rules, RU.ITEM, m.work_item_code, m.level_id) if (item_rules and m.recon_mode == "AUTO") else None
    if rule is not None:
      item_ruled[str(m.id)] = rule.prefer
      item_ruled_groups[(m.work_item_code, m.level_id)] = rule.prefer
      m = _dc.replace(m, recon_mode={RU.DRAWING: "REPLACE_MODEL", RU.BOTH: "ADD", RU.MODEL: "AUTO"}[rule.prefer])
    ok.append((m, sheet, cals.get(m.calibration_id), comp))

  model_rows = [r for r in model_ledger if getattr(r, "source_kind", "MODEL") != SOURCE_KIND and r.quantity > 0]
  from app.engine.measure import one_total as OT
  one_total_on = OT.is_on(ctx)
  one_total_ids = (OT.adjudicable_ids(ctx) & {str(m.id) for m, _, _, _ in ok if m.recon_mode == "AUTO" and item_ruled.get(str(m.id)) != "MODEL"}) if (one_total_on and elements) else frozenset()

  def rows_for(code: str, level) -> list:
    if level is None:
      return [r for r in model_rows if r.work_item_code == code]
    return [r for r in model_rows if r.work_item_code == code and r.level_id in (level, None)]

  replace_keys = {(m.work_item_code, m.level_id) for m, _, _, _ in ok if m.recon_mode == "REPLACE_MODEL"}

  def replaced(code: str, level) -> bool:
    return (code, None) in replace_keys or (code, level) in replace_keys

  dropped: dict = {}
  for code, level in sorted(replace_keys, key=lambda k: (k[0], str(k[1]))):
    for r in rows_for(code, level):
      dropped[(r.solid_id, r.work_item_code)] = r

  solids: list = []
  ledger: list = []
  decided: list = []
  not_counted: dict = {}
  for m, sheet, cal_in, comp in ok:
    covering = rows_for(m.work_item_code, m.level_id)
    if m.recon_mode != "REPLACE_MODEL" and replaced(m.work_item_code, m.level_id):
      covering = []
    model_qty = sum((r.quantity for r in covering if r.unit == comp.unit), ZERO)
    covered = bool(covering)
    if m.recon_mode == "VERIFY_ONLY":
      decision, reason = "VERIFIED", "Verification only; not counted in the BOQ."
    elif m.recon_mode == "ADD":
      decision, reason = "COUNTED", "Added to the model quantity by choice." if covered else "No model quantity for this work item."
    elif m.recon_mode == "REPLACE_MODEL":
      decision, reason = "COUNTED", "Replaces the model quantity by choice." if covered else "No model quantity to replace."
      
    else:
      if covered and not replaced(m.work_item_code, m.level_id) and str(m.id) not in one_total_ids:
        decision, reason = "VERIFIED", "The model already measures this work item; not counted. Choose Add or Replace to count it."
        key = (m.work_item_code, str(m.level_id) if m.level_id else None)
        not_counted[key] = not_counted.get(key, 0) + 1
      else:
        decision, reason = "COUNTED", ("Decided member by member against the model (one total)." if (covered and str(m.id) in one_total_ids) else "No model quantity for this work item.")
    decided.append((m, sheet, cal_in, comp, decision, ("By your rule for this item. " + reason) if str(m.id) in item_ruled else reason, model_qty, covered))

  groups: dict = defaultdict(lambda: [ZERO, ZERO])
  for m, sheet, cal_in, comp, decision, reason, model_qty, covered in decided:
    if decision == "COUNTED" or m.recon_mode == "VERIFY_ONLY" or decision == "VERIFIED":
      g = groups[(m.work_item_code, m.level_id, comp.unit)]
      g[0] += comp.quantity
      g[1] = max(g[1], model_qty)
  tolerance = _variance_tolerance(profile)
  variances: list = []
  variance_by_key: dict = {}
  
  for (code, level, unit), (pdf_qty, model_qty) in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]), kv[0][2])):
    if model_qty > 0:
      pct = q4((pdf_qty - model_qty) / model_qty * HUNDRED)
      variance_by_key[(code, level, unit)] = pct
      variances.append({"work_item_code": code, "level_id": str(level) if level else None, "unit": unit,
        "pdf_quantity": str(q6(pdf_qty)), "model_quantity": str(q6(model_qty)), "variance_pct": str(pct),
        "over_tolerance": abs(pct) > tolerance, "tolerance_pct": str(tolerance), "rule": item_ruled_groups.get((code, level)),
        "level_name": (getattr(ctx, "level_names", None) or {}).get(str(level)) if level else None})

  counted = verified = 0
  for m, sheet, cal_in, comp, decision, reason, model_qty, covered in decided:
    pct = variance_by_key.get((m.work_item_code, m.level_id, comp.unit))
    record = {"measurement_id": str(m.id), "decision": decision, "reason": reason, "work_item_code": m.work_item_code,
      "level_id": str(m.level_id) if m.level_id else None, "quantity": str(comp.quantity), "unit": comp.unit,
      "model_quantity": str(q6(model_qty)) if covered else None, "variance_pct": str(pct) if pct is not None else None,
      "confidence": str(comp.confidence), "warnings": list(comp.warnings), "mode": m.recon_mode, "rule": item_ruled.get(str(m.id))}
    
    if decision == "VERIFIED":
      verified += 1
      results.append(record)
      continue
    counted += 1
    warnings = list(comp.warnings)
    if m.recon_mode == "ADD" and covered:
      warnings.append("PDF_ADDED_TO_MODEL")
    if m.recon_mode == "REPLACE_MODEL" and covered:
      warnings.append("PDF_REPLACES_MODEL")
      
    if decision == "COUNTED":
      record["decision"] = "REPLACED_MODEL" if (m.recon_mode == "REPLACE_MODEL" and covered) else "COUNTED"
    results.append(record)
    solid_id = uuid5(ctx.run_id, f"solid|takeoff:{m.id}")
    
    solids.append(Solid(
      id=solid_id, element_id=None, ifc_type="PdfMeasurement", role="PDF_TAKEOFF", level_id=m.level_id,
      geometry_kind="QTO_ONLY", classification_confidence=ONE, confidence_factor=ONE, component_type="PDF_TAKEOFF",
      material_grade=m.material_grade,
      gross_volume_m3=comp.quantity if comp.unit == "m3" else None,
      gross_area_m2=comp.quantity if comp.unit == "m2" else None,
      gross_length_m=comp.quantity if comp.unit == "m" else None,
      count=int(comp.quantity) if comp.unit == "nos" else None,
      status="REVIEW_REQUIRED" if warnings else "OK",
    ))
    
    cal_eval = cal_evals.get(m.calibration_id) if m.calibration_id else None
    trace_inputs = {
      **comp.inputs, "measurement_id": str(m.id), "sheet_id": str(sheet.id), "drawing_id": str(sheet.drawing_id),
      "page_no": sheet.page_no, "geometry_hash": comp.geometry_hash, "content_kind": sheet.content_kind,
      "source": m.source, "tag": m.tag, "recon_mode": m.recon_mode,
      "calibration": ({"id": str(cal_in.id), "method": cal_in.method,
        "mm_per_pt": str(cal_eval.mm_per_pt.quantize(Decimal("0.00000001"))), "check_error_pct": str(cal_eval.error_pct) if cal_eval.error_pct is not None else None,
        "quality_factor": str(cal_eval.factor)} if cal_in is not None and cal_eval is not None and cal_eval.mm_per_pt is not None else None),
      "reconciliation": {"decision": record["decision"], "model_quantity": record["model_quantity"], "variance_pct": record["variance_pct"]},
    }
    
    ledger.append(LedgerEntry(
      solid_id=solid_id, element_id=None, level_id=m.level_id, work_item_code=m.work_item_code, quantity=comp.quantity,
      unit=comp.unit, material_grade=m.material_grade, confidence=comp.confidence, formula_code=comp.formula,
      trace={
        "formula_code": comp.formula, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
        "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
        "inputs": trace_inputs, "steps": comp.steps, "net": {comp.unit: str(comp.quantity)},
        "label": f"PDF p.{sheet.page_no} {m.label or m.tag or m.kind.title()}".strip(), "rounding": "half_up,6dp",
        **({"range": rg} if (rg := range_trace(inputs, m.id)) else {}),
      },
      warnings=tuple(dict.fromkeys(warnings)), source_kind=SOURCE_KIND,
      spec=(mspec := member_spec(m)), spec_key=_spec_key(mspec),
    ))
  one_total_stats: dict = {"enabled": False}
  one_total_drop: frozenset = frozenset()
  
  if one_total_on:
    ot = OT.adjudicate(ctx, profile, elements, [r for r in model_rows if (r.solid_id, r.work_item_code) not in dropped], ledger, frozenset(dropped), _variance_tolerance(profile), one_total_ids)
    one_total_stats, one_total_drop = ot.stats, frozenset(ot.drop_model)
    if ot.drop_pdf:
      gone_solids = {r.solid_id for r in ledger if str(((r.trace or {}).get("inputs") or {}).get("measurement_id")) in ot.drop_pdf}
      ledger = [r for r in ledger if r.solid_id not in gone_solids]
      solids = [s for s in solids if s.id not in gone_solids]
      for rec in results:
        if rec["measurement_id"] in ot.drop_pdf and rec["decision"] in ("COUNTED", "REPLACED_MODEL"):
          rec["decision"], rec["reason"] = "VERIFIED", "The model has this member; its quantity is used (one total)."
          counted, verified = counted - 1, verified + 1
    ledger = [OT.annotate_row(r, ot.annotate[str(((r.trace or {}).get("inputs") or {}).get("measurement_id"))]) if str(((r.trace or {}).get("inputs") or {}).get("measurement_id")) in ot.annotate else r for r in ledger]
  ledger.sort(key=lambda r: (r.work_item_code, str(r.level_id), str(r.solid_id)))
  solids.sort(key=lambda s: str(s.id))
  results.sort(key=lambda r: r["measurement_id"])
  
  stats = {
    "measurements": len(inputs.measurements), "counted": counted, "verified": verified,
    "skipped": dict(sorted(skipped.items())), "variances": variances,
    "not_counted": [{"work_item_code": k[0], "level_id": k[1], "measurements": n} for k, n in sorted(not_counted.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))],
    "replaced": [{"work_item_code": code, "level_id": str(level) if level else None,
      "rows_dropped": sum(1 for r in dropped.values() if r.work_item_code == code and (level is None or r.level_id in (level, None))),
      "model_quantity": str(q6(sum((r.quantity for r in dropped.values() if r.work_item_code == code and (level is None or r.level_id in (level, None))), ZERO)))}
      for code, level in sorted(replace_keys, key=lambda k: (k[0], str(k[1])))],
    "tolerance_pct": str(tolerance),
  }
  stats["one_total"] = one_total_stats if one_total_on else {"enabled": False}
  if one_total_on and not elements:
    stats["one_total"] = {"enabled": True, "ran": False, "reason": "NO_MODEL_ELEMENTS"}
  return TakeoffResult(solids=solids, ledger=ledger, results=results, dropped_keys=frozenset(dropped) | one_total_drop, stats=stats)

def apply_replacements(ledger: list, dropped_keys) -> list:
  if not dropped_keys:
    return list(ledger)
  return [r for r in ledger if (r.solid_id, r.work_item_code) not in dropped_keys]

def takeoff_check(solids: list, ledger: list, deductions=()) -> list:
  by_id = {s.id: s for s in solids}
  failures: list = []
  taken: dict = defaultdict(lambda: ZERO)
  
  for d in deductions or ():
    if d.quantity < 0:
      failures.append(f"negative PDF deduction on solid {d.from_solid_id}")
    taken[d.from_solid_id] += d.quantity
  held_rows: dict = defaultdict(lambda: ZERO)
  units: dict = {}
  for r in ledger:
    if getattr(r, "source_kind", "MODEL") != SOURCE_KIND:
      continue
    if r.formula_code not in TAKEOFF_FORMULA_UNITS or TAKEOFF_FORMULA_UNITS[r.formula_code] != r.unit:
      failures.append(f"takeoff row has formula {r.formula_code} with unit {r.unit} on solid {r.solid_id}")
    if r.work_item_code in RESERVED_CODES:
      failures.append(f"takeoff row uses reserved work item {r.work_item_code}")
    inputs = (r.trace or {}).get("inputs") or {}
    if not inputs.get("measurement_id") or not inputs.get("sheet_id"):
      failures.append(f"takeoff row without measurement reference on solid {r.solid_id}")
    if inputs.get("kind") in ("LENGTH", "AREA") and not inputs.get("calibration"):
      failures.append(f"takeoff row without calibration on solid {r.solid_id}")
    held_rows[(r.solid_id, r.work_item_code)] += r.quantity
    units[(r.solid_id, r.work_item_code)] = r.unit
  for (solid_id, code), total in held_rows.items():
    s = by_id.get(solid_id)
    if s is None:
      continue
    
    unit = units[(solid_id, code)]
    held = {"m3": s.gross_volume_m3, "m2": s.gross_area_m2, "m": s.gross_length_m,
      "nos": Decimal(s.count) if s.count is not None else None}.get(unit)
    if held is None:
      failures.append(f"takeoff quantity {total} != solid quantity {held} on solid {solid_id}")
      continue
    
    expected = q6(held)
    if unit == "m3" and taken.get(solid_id):
      expected = max(ZERO, q6(held - taken[solid_id]))
    if total != expected:
      failures.append(f"takeoff quantity {total} != solid quantity {expected} on solid {solid_id}")
  return failures

def _enc(v):
  if isinstance(v, Decimal):
    return str(v)
  if isinstance(v, tuple):
    return [_enc(x) for x in v]
  if isinstance(v, list):
    return [_enc(x) for x in v]
  if isinstance(v, dict):
    return {str(k): _enc(x) for k, x in sorted(v.items(), key=lambda kv: str(kv[0]))}
  return v

def takeoff_payload(inputs: TakeoffInputs | None) -> dict:
  if inputs is None or not inputs.measurements:
    return {}

  return {
    "sheets": [[str(s.id), str(s.drawing_id), s.page_no, s.content_kind, str(s.level_id) if s.level_id else None]
      for s in sorted(inputs.sheets, key=lambda s: str(s.id))],
    "calibrations": [_enc([str(c.id), str(c.sheet_id), c.method, c.ratio, c.p1, c.p2, c.known_mm, c.check_p1, c.check_p2, c.check_known_mm, c.user_unit])
      for c in sorted(inputs.calibrations, key=lambda c: str(c.id))],
    "measurements": [_enc({
      "id": str(m.id), "sheet": str(m.sheet_id), "cal": str(m.calibration_id) if m.calibration_id else None, "kind": m.kind,
      "mode": m.quantity_mode, "geometry": m.geometry, "params": m.params, "code": m.work_item_code,
      "level": str(m.level_id) if m.level_id else None, "grade": m.material_grade, "recon": m.recon_mode, "source": m.source,
    }) for m in sorted(inputs.measurements, key=lambda m: str(m.id))],
    **({"members": [_enc([str(b.measurement_id), str(b.candidate_id), b.category, b.tag, b.frame, str(b.level_id) if b.level_id else None,
      [str(i) for i in b.element_ids], [list(p) for p in b.points_mm], b.length_mm, b.width_mm, b.depth_mm, b.confidence, b.position_basis])
     for b in sorted(inputs.members, key=lambda b: str(b.measurement_id))]} if inputs.members else {}),
    **({"formwork": [_enc([str(b.measurement_id), str(b.candidate_id), b.category, b.tag, str(b.level_id) if b.level_id else None,
      [str(i) for i in b.element_ids], b.count, b.length_mm, b.width_mm, b.depth_mm, b.confidence, b.steel, *([b.stair] if b.stair else []),
      *([b.frame, [list(p) for p in b.points_mm]] if b.frame else []),
      *([{"role": b.role, "site": b.site}] if (b.role or b.site) else [])])
      for b in sorted(inputs.formwork, key=lambda b: str(b.measurement_id))]} if inputs.formwork else {}),
    **({"ranges": [_enc([str(r.measurement_id), r.grade, r.bounded, r.low_pct, r.high_pct, r.leaves_out, [dict(d) for d in r.drivers]])
      for r in sorted(inputs.ranges, key=lambda r: str(r.measurement_id))]} if inputs.ranges else {}),
    **({"alignments": [_enc([a.view, a.group, a.dx_mm, a.dy_mm, a.method, a.grade, a.supporters, a.compared, a.residual_mm, a.reference, a.origin_x_mm, a.origin_y_mm])
      for a in sorted(inputs.alignments, key=lambda a: (a.group, a.view))]} if inputs.alignments else {}),
    **({"space": [_enc([str(b.measurement_id), b.group, b.category, b.frame, b.shape, [list(p) for p in b.parts], b.length_mm, b.width_mm, b.z0_mm, b.z1_mm, b.z_grade, b.floor,
      str(b.level_id) if b.level_id else None, b.covered_by_band])
      for b in sorted(inputs.space, key=lambda b: str(b.measurement_id))]} if inputs.space else {}),
    **({"floors": [_enc([f.group, f.key, f.level_mm, f.soffit_mm, f.top_mm, f.grade]) for f in sorted(inputs.floors, key=lambda f: (f.group, f.key))]} if inputs.floors else {}),
  }
