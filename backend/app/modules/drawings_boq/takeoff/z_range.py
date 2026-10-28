from __future__ import annotations
from dataclasses import dataclass
from app.modules.drawings_boq.takeoff.prep.facts import FLOOR_ORDER
from app.modules.drawings_boq.takeoff.model import levels as LV

PRINTED, TYPED, ASSUMED = "PRINTED", "TYPED", "ASSUMED"
TYPED_NGL, MARK_NGL = "TYPED", "LEVEL_MARK"
DRAWING_ZERO, GROUND_LEVEL = "DRAWING_LEVEL_ZERO", "GROUND_FLOOR_LEVEL"
SECTION, LEVEL_MARKS, TYPICAL, DATUM = "SECTION", "LEVEL_MARKS", "TYPICAL", "DATUM"
PRINTED_MARK, SUM_OF_STOREYS, AT_DATUM = "PRINTED_MARK", "SUM_OF_STOREYS", "AT_DATUM"
TYPED_LEVEL = "TYPED_LEVEL"
FLOOR_LEVEL, SLAB_SOFFIT, SLAB_TOP = "FLOOR_LEVEL", "SLAB_SOFFIT", "SLAB_TOP"
ELEMENT_HEIGHT, ELEMENT_DEPTH, FOOTING_LEVEL = "ELEMENT_HEIGHT", "ELEMENT_DEPTH", "FOOTING_LEVEL"
NO_FLOOR, NO_SIZE, NEEDS_FOOTING_LEVEL, NEEDS_OPENING_HEAD = "NO_FLOOR", "NO_SIZE", "NEEDS_FOOTING_LEVEL", "NEEDS_OPENING_HEAD"
OPENING_HEAD = "OPENING_HEAD"
HEIGHT_DIFFERS = "HEIGHT_DIFFERS_FROM_DATUM"
DIFFERS_TOL_MM = 50.0
KINDS = ("COLUMN", "NECK", "WALL", "BEAM", "PLINTH_BEAM", "BAND", "SLAB", "FOOTING", "LINTEL")

@dataclass(frozen=True)
class Floor:
  key: str
  level_mm: float
  clear_mm: float | None
  floor_to_floor_mm: float | None
  source: str
  grade: str
  level_source: str = SUM_OF_STOREYS
  datum: str = GROUND_LEVEL
  sources: tuple = ()
  decisions: tuple = ()

  @property
  def soffit_mm(self) -> float | None:
    return None if self.clear_mm is None else round(self.level_mm + self.clear_mm, 1)

  @property
  def top_mm(self) -> float | None:
    return None if self.floor_to_floor_mm is None else round(self.level_mm + self.floor_to_floor_mm, 1)

  def as_dict(self) -> dict:
    return {"key": self.key, "level_mm": self.level_mm, "clear_mm": self.clear_mm, "floor_to_floor_mm": self.floor_to_floor_mm, "soffit_mm": self.soffit_mm,
      "top_mm": self.top_mm, "source": self.source, "level_source": self.level_source, "grade": self.grade, "sources": list(self.sources), "decisions": list(self.decisions)}

@dataclass(frozen=True)
class ZRange:
  base_mm: float | None
  top_mm: float | None
  base_source: str
  top_source: str
  grade: str = ASSUMED
  notes: tuple = ()
  datum: str = GROUND_LEVEL

  @property
  def known(self) -> bool:
    return self.base_mm is not None and self.top_mm is not None

  def as_dict(self) -> dict:
    return {"base_mm": self.base_mm, "top_mm": self.top_mm, "base_source": self.base_source, "top_source": self.top_source, "grade": self.grade,
      "notes": list(self.notes), "datum": self.datum}

@dataclass(frozen=True)
class FootingLevel:
  """Natural ground level (z of the ground) and how far the bottom of a footing is below it. ngl_source says where the ground level came from: TYPED (the site
  assumption a person saved) or LEVEL_MARK (the lowest level mark printed below the ground floor, which is only a reading). datum is the datum ngl_mm is in."""
  ngl_mm: float | None = None
  bottom_below_ngl_mm: float | None = None
  ngl_source: str = TYPED_NGL
  datum: str = GROUND_LEVEL

  @property
  def usable(self) -> bool:
    return self.ngl_mm is not None and self.bottom_below_ngl_mm is not None and self.bottom_below_ngl_mm > 0

def _num(value) -> float | None:
  try:
    v = float(value)
  except (TypeError, ValueError):
    return None
  return v if v == v and v > 0 else None

def _signed(value) -> float | None:
  try:
    v = float(value)
  except (TypeError, ValueError):
    return None
  return v if v == v else None

def _grade(basis: str) -> str:
  return PRINTED if basis in (SECTION, DATUM) else ASSUMED

def _lowest(*grades: str) -> str:
  return ASSUMED if ASSUMED in grades else TYPED if TYPED in grades else PRINTED

def floors_from_levels(levels, decisions=()) -> dict:
  rows = {l.key: l for l in (levels or ()) if l.level_mm is not None}
  if "GROUND" not in rows:
    return {}
  by_floor: dict = {}
  for d in decisions or ():
    by_floor.setdefault(str(d.id).split(":", 1)[1], []).append(d.as_dict())

  def make(l, basis, grade, how, datum):
    return Floor(l.key, l.level_mm, l.clear_mm, l.f2f_mm, basis, grade, how, datum, tuple(s.as_dict() for s in l.sources), tuple(by_floor.get(l.key, ())))

  def how_of(l):
    return TYPED_LEVEL if l.level_how == LV.TYPED else PRINTED_MARK if l.level_how == LV.PRINTED_MARK else SUM_OF_STOREYS if l.level_how == LV.SUM_OF_STOREYS else AT_DATUM

  g = rows["GROUND"]
  datum = GROUND_LEVEL if g.level_how == LV.AT_DATUM else DRAWING_ZERO
  basis = g.basis or DATUM
  out: dict = {"GROUND": make(g, basis, TYPED if g.level_how == LV.TYPED else _grade(basis), how_of(g), datum)}
  grade_below = out["GROUND"].grade
  for key in [k for k in FLOOR_ORDER if k in rows and FLOOR_ORDER.index(k) > FLOOR_ORDER.index("GROUND")]:
    l = rows[key]
    basis = l.basis or TYPICAL
    if l.level_how in (LV.PRINTED_MARK, LV.TYPED):
      grade = TYPED if l.level_how == LV.TYPED else _grade(basis)
    else:
      grade = _lowest(grade_below, _grade(basis))
    grade_below = grade
    out[key] = make(l, basis, grade, how_of(l), datum)
  if "BASEMENT" in rows:
    l = rows["BASEMENT"]
    basis = l.basis or TYPICAL
    grade = (TYPED if l.level_how == LV.TYPED else _grade(basis)) if l.level_how in (LV.PRINTED_MARK, LV.TYPED) else _lowest(out["GROUND"].grade, _grade(basis))
    out["BASEMENT"] = make(l, basis, grade, how_of(l), datum)
  return out

def build_floors(heights: dict | None, floor_keys: list | None, levels=None, decisions=()) -> dict:
  if levels is None:
    levels = LV.from_heights(heights, floor_keys)
  return floors_from_levels(levels, decisions)

def datum_of(floors: dict) -> str:
  for f in floors.values():
    return f.datum
  return GROUND_LEVEL

def ngl_from_marks(floors: dict, levels_mm: list | None) -> float | None:
  """The natural ground level as a reading of the level marks: only when the drawing's own zero is the datum, the lowest mark printed on the elevations when it lies
  below the ground floor. It is a guess at what that mark stands for, so the caller grades it as such."""
  ground = (floors or {}).get("GROUND")
  marks = [float(x) for x in (levels_mm or ()) if x is not None]
  if ground is None or ground.datum != DRAWING_ZERO or not marks:
    return None
  lowest = min(marks)
  return lowest if lowest < ground.level_mm - 1.0 else None

def _range(base, top, base_source, top_source, grades: list, notes: list, datum: str) -> ZRange:
  return ZRange(None if base is None else round(base, 1), None if top is None else round(top, 1), base_source, top_source, _lowest(*grades), tuple(notes), datum)

def z_range(kind: str, floor: Floor | None, *, height_mm=None, depth_mm=None, footing: FootingLevel | None = None, head_mm=None, head_grade: str = ASSUMED) -> ZRange:
  """The height range of one member. kind is one of KINDS. height_mm is the member's own height (a wall, a column or a neck column), depth_mm its depth or
  thickness (a beam, a slab, a footing). floor is the floor the member is shown on; footing the natural ground and footing level, for footings; head_mm how high
  the head of the opening stands above the floor level, for a lintel or a tie band, and head_grade whether that was printed."""
  height, depth = _num(height_mm), _num(depth_mm)
  datum = floor.datum if floor is not None else footing.datum if footing is not None else GROUND_LEVEL
  
  if kind in ("LINTEL", "BAND"):
    head = _num(head_mm)
    if floor is None:
      return ZRange(None, None, NO_FLOOR, NO_FLOOR, ASSUMED, ("the floor of this member has no level on the building",), datum)
    if head is None:
      return ZRange(None, None, NEEDS_OPENING_HEAD, NEEDS_OPENING_HEAD, ASSUMED, ("how high the opening head stands is not printed with the lintel",), datum)
    base = floor.level_mm + head
    if depth is None:
      return ZRange(round(base, 1), None, OPENING_HEAD, NO_SIZE, _lowest(floor.grade, head_grade), ("no depth to stand above the opening head",), datum)
    return _range(base, base + depth, OPENING_HEAD, ELEMENT_DEPTH, [floor.grade, head_grade], [], datum)

  if kind == "FOOTING":
    f = footing
    if f is None or not f.usable:
      return ZRange(None, None, NEEDS_FOOTING_LEVEL, NEEDS_FOOTING_LEVEL, ASSUMED, ("the footing level below natural ground and the natural ground level are both needed",), datum)
    if depth is None:
      return ZRange(None, None, NO_SIZE, NO_SIZE, ASSUMED, ("the footing has no depth",), datum)
    base = f.ngl_mm - f.bottom_below_ngl_mm
    return _range(base, base + depth, FOOTING_LEVEL, ELEMENT_DEPTH, [ASSUMED if f.ngl_source == MARK_NGL else TYPED], [], datum)
  if floor is None:
    return ZRange(None, None, NO_FLOOR, NO_FLOOR, ASSUMED, ("the floor of this member has no level on the building",), datum)

  g, notes = [floor.grade], []
  if kind in ("COLUMN", "WALL"):
    base = floor.level_mm
    if height is not None:
      top, top_source = base + height, ELEMENT_HEIGHT
      if floor.soffit_mm is not None and abs(top - floor.soffit_mm) > DIFFERS_TOL_MM:
        notes.append(f"{HEIGHT_DIFFERS}: its own height reaches {round(top, 1)} mm, the slab above is at {floor.soffit_mm} mm")
    elif floor.soffit_mm is not None:
      top, top_source = floor.soffit_mm, SLAB_SOFFIT
    else:
      return ZRange(base, None, FLOOR_LEVEL, NO_SIZE, floor.grade, ("no storey height for this floor and no height of its own",), datum)
    return _range(base, top, FLOOR_LEVEL, top_source, g, notes, datum)

  if kind == "NECK":
    if height is None:
      return ZRange(None, floor.level_mm, NO_SIZE, FLOOR_LEVEL, floor.grade, ("the neck column has no height",), datum)
    return _range(floor.level_mm - height, floor.level_mm, ELEMENT_HEIGHT, FLOOR_LEVEL, g, [], datum)

  if kind in ("BEAM", "SLAB", "PLINTH_BEAM"):
    if kind == "PLINTH_BEAM":
      top, top_source = floor.level_mm, FLOOR_LEVEL
    elif floor.top_mm is not None:
      top, top_source = floor.top_mm, SLAB_TOP
    else:
      return ZRange(None, None, NO_SIZE, NO_SIZE, floor.grade, ("no floor-to-floor height for this floor",), datum)
    if depth is None:
      return ZRange(None, top, NO_SIZE, top_source, floor.grade, ("no depth to hang below the top",), datum)
    return _range(top - depth, top, ELEMENT_DEPTH, top_source, g, [], datum)
  raise ValueError(f"unknown member kind {kind}")

def member_kind(category: str, facts: dict | None) -> str | None:
  """The kind of a found item as far as its height is concerned, or None for the items that have no height range (doors, windows, rooms, stairs and the
  works worked out from other readings)."""
  facts = facts or {}
  if facts.get("foundation_item"):
    return None
  if category == "COLUMN":
    return "NECK" if isinstance(facts.get("neck_of"), str) else "COLUMN"
  if category == "BEAM":
    return "PLINTH_BEAM" if facts.get("beam_role") == "PLINTH" else "BAND" if facts.get("beam_role") == "BAND" else "BEAM"
  if category in ("WALL", "SLAB", "FOOTING", "LINTEL"):
    return category
  return None

def floors_report(floors: dict, floor_keys: list | None, heights: dict | None = None) -> list:
  """The floors of a drawing for the screen, lowest first, each with its level, soffit, top and where they came from; a floor whose level cannot be worked out
  is listed with a reason."""
  wanted = set(floor_keys or ()) | set(heights or ()) | set(floors)
  rows = []
  for key in FLOOR_ORDER:
    if key not in wanted:
      continue
    f = floors.get(key)
    if f is not None:
      rows.append({**f.as_dict(), "reason": None})
      continue
    why = "no ground floor on the drawing" if "GROUND" not in floors else "no level and no height printed for the basement" if key == "BASEMENT" else "the floor below has no floor-to-floor height"
    rows.append({"key": key, "level_mm": None, "clear_mm": None, "floor_to_floor_mm": None, "soffit_mm": None, "top_mm": None, "source": None, "level_source": None,
      "grade": ASSUMED, "reason": why})
  return rows