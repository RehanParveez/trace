from __future__ import annotations
from app.modules.drawings_boq.takeoff.tuning import usage as U
from dataclasses import dataclass
from app.modules.drawings_boq.takeoff.proof import trace as TR
import math
from app.modules.drawings_boq.takeoff.extract import scalegate as SG
from app.modules.drawings_boq.takeoff.extract import config as C

SWEEPABLE, NOT_SWEEPABLE = "SWEEPABLE", "NOT_SWEEPABLE"
READ, GATE, POLICY = "READ", "GATE", "POLICY"     
CONFIG_MODULE, GATE_MODULE = U.DOTTED["C"], U.DOTTED["SG"]

FAMILIES = {
  "SCALE_GATE": ("*",), "WALL_PEN": ("WALL",), "WALL_GAP_BRIDGE": ("WALL",), "OUTER_WALL_FILTER": ("WALL",), "STAIR_TREADS": ("STAIR", "WALL"),
  "COLUMN_SHAPES": ("COLUMN",), "MEMBER_MATCH": ("COLUMN", "FOOTING", "BEAM"), "ROOM_OUTLINE": ("ROOM",), "BEAM_STRIPS": ("BEAM",), "SLAB_THICKNESS": ("SLAB",),
  "SITE_ITEMS": ("SITE",), "SLAB_OPENINGS": ("SLAB", "STAIR"), "WALL_THICKNESS": ("WALL",), "ASSUMED_VALUES": ("STAIR", "LINTEL", "FOOTING"),
}

RANGES = {
  "SG.MIN_DECLARED_TRUST": ("ratio", 0.3, 0.95), "SG.STRONG_CONFLICT_SUPPORT": ("count", 3, 30),
  "WALL_T_MIN_MM": ("mm", 50, 200), "WALL_T_MAX_MM": ("mm", 400, 800), "WALL_MIN_FACE_MM": ("mm", 100, 400), "WALL_MIN_OVERLAP_MM": ("mm", 150, 600),
  "WALL_MIN_RUN_MM": ("mm", 400, 2000), "WALL_BRIDGE_MAX_MM": ("mm", 600, 3000), "WALL_GAP_MAX_MM": ("mm", 1200, 4000), "WALL_GAP_CLEAR_MAX_MM": ("mm", 1500, 5000),
  "WALL_STUB_MAX_MM": ("mm", 800, 4000), "OUTER_CORE_MIN_MM": ("mm", 100, 400), "OUTER_TOL_MM": ("mm", 50, 400), "OUTER_WALL_TOL_FACTOR": ("ratio", 1.0, 3.0),
  "LADDER_MIN_RUNGS": ("count", 3, 8), "LADDER_MAX_STEP_MM": ("mm", 300, 900), "LADDER_LENGTH_TOL": ("ratio", 0.05, 0.5), "LADDER_STEP_TOL": ("ratio", 0.1, 0.9),
  "STAIR_MIN_TREADS": ("count", 3, 8), "STAIR_TREAD_TOL": ("ratio", 0.03, 0.3), "STAIR_SHORT_MIN_TREADS": ("count", 2, 4), "STAIR_SHORT_LABEL_REACH_MM": ("mm", 500, 4000),
  "COLUMN_PIECE_MIN_MM": ("mm", 80, 400), "COLUMN_PIECE_MAX_MM": ("mm", 600, 2000), "COLUMN_FILL_MIN": ("ratio", 0.2, 0.9), "COLUMN_JOIN_GAP_MM": ("mm", 5, 100),
  "COLUMN_JOIN_ALIGN": ("ratio", 0.5, 0.98), "COLUMN_CLASS_TOL": ("ratio", 0.02, 0.2), "COLUMN_GRID_BIN_MM": ("mm", 20, 150), "COLUMN_GRID_MIN_VOTES": ("count", 2, 8),
  "COLUMN_GRID_MIN_SHARE": ("ratio", 0.1, 0.7),
  "MEMBER_SEARCH_MM": ("mm", 400, 3000), "SIZE_TOL": ("ratio", 0.02, 0.3), "MEMBER_MIN_MM": ("mm", 50, 300), "MEMBER_MAX_MM": ("mm", 1500, 4000),
  "ROOM_SIZE_TOL": ("ratio", 0.02, 0.3), "STRIP_MAX_SEGMENTS": ("count", 1000, 1000000), "BEAM_WIDTH_SNAP_TOL": ("ratio", 0.01, 0.15),
  "SLAB_LABEL_MIN_COUNT": ("count", 1, 5), "SLAB_LABEL_SECTIONS_TOL_MM": ("mm", 2, 20), "SLAB_SECTION_MIN_MM": ("mm", 50, 150),
  "SLAB_SECTION_MAX_MM": ("mm", 250, 600), "TANK_REACH_MM": ("mm", 800, 5000), "TANK_MAX_MM": ("mm", 3000, 12000),
  "VOID_LABEL_REACH_MM": ("mm", 500, 3000), "VOID_MIN_SIDE_MM": ("mm", 80, 500), "LANDING_MIN_SIDE_MM": ("mm", 300, 1200), "STAIR_LANDING_REACH_MM": ("mm", 1000, 4500),
  "STANDARD_TOL": ("ratio", 0.01, 0.12), "IMPERIAL_TOL": ("ratio", 0.02, 0.15),
  "STAIR_WAIST_DEFAULT_MM": ("mm", 75, 250), "LINTEL_BEARING_MM": ("mm", 75, 300), "TRENCH_SIDE_ALLOWANCE_MM": ("mm", 0, 300),
}

HAND = {
  "SG.MIN_DECLARED_TRUST": 0.6, "SG.STRONG_CONFLICT_SUPPORT": 8,
  "WALL_T_MIN_MM": 95.0, "WALL_T_MAX_MM": 520.0, "WALL_MIN_FACE_MM": 200.0, "WALL_MIN_OVERLAP_MM": 300.0, "WALL_MIN_RUN_MM": 900.0,
  "WALL_BRIDGE_MAX_MM": 1600.0, "WALL_GAP_MAX_MM": 2500.0, "WALL_GAP_CLEAR_MAX_MM": 3200.0, "WALL_STUB_MAX_MM": 2000.0,
  "OUTER_CORE_MIN_MM": 190.0, "OUTER_TOL_MM": 150.0, "OUTER_WALL_TOL_FACTOR": 1.5,
  "LADDER_MIN_RUNGS": 4, "LADDER_MAX_STEP_MM": 650.0, "LADDER_LENGTH_TOL": 0.2, "LADDER_STEP_TOL": 0.5, "STAIR_MIN_TREADS": 4, "STAIR_TREAD_TOL": 0.12, "STAIR_SHORT_MIN_TREADS": 3, "STAIR_SHORT_LABEL_REACH_MM": 2000.0,
  "COLUMN_PIECE_MIN_MM": 150.0, "COLUMN_PIECE_MAX_MM": 1100.0, "COLUMN_FILL_MIN": 0.4, "COLUMN_JOIN_GAP_MM": 30.0, "COLUMN_JOIN_ALIGN": 0.8, "COLUMN_CLASS_TOL": 0.06,
  "COLUMN_GRID_BIN_MM": 50.0, "COLUMN_GRID_MIN_VOTES": 3, "COLUMN_GRID_MIN_SHARE": 0.3,
  "MEMBER_SEARCH_MM": 1200.0, "SIZE_TOL": 0.08, "MEMBER_MIN_MM": 100.0, "MEMBER_MAX_MM": 2500.0, "ROOM_SIZE_TOL": 0.08,
  "STRIP_MAX_SEGMENTS": 150000, "BEAM_WIDTH_SNAP_TOL": 0.035,
  "SLAB_LABEL_MIN_COUNT": 2, "SLAB_LABEL_SECTIONS_TOL_MM": 6.0, "SLAB_SECTION_MIN_MM": 75.0, "SLAB_SECTION_MAX_MM": 400.0,
  "TANK_REACH_MM": 2200.0, "TANK_MAX_MM": 7000.0,
  "VOID_LABEL_REACH_MM": 1500.0, "VOID_MIN_SIDE_MM": 150.0, "LANDING_MIN_SIDE_MM": 600.0, "STAIR_LANDING_REACH_MM": 2500.0,
  "STANDARD_TOL": 0.04, "IMPERIAL_TOL": 0.06, "STAIR_WAIST_DEFAULT_MM": 127.0, "LINTEL_BEARING_MM": 152.4, "TRENCH_SIDE_ALLOWANCE_MM": 76.2,
}

NOT_THRESHOLDS = {"STRIP_MAX_SEGMENTS": "a safety cap on the work done on one sheet, not a reading threshold"}

@dataclass(frozen=True)
class Param:
  key: str                  
  name: str                 
  module: str               
  attr: str
  rule_id: str
  rule_label: str
  basis: str                
  families: tuple
  unit: str
  kind: str                 
  lo: float
  hi: float
  hand: float
  stage: str               
  status: str               
  reasons: tuple            
  copies: tuple             
  uses: tuple               

  @property
  def calibratable(self) -> bool:
    return self.status == SWEEPABLE and self.basis == TR.TUNED

  @property
  def live(self):
    return live_value(self)

def live_value(p: Param):
  mod = SG if p.module == GATE_MODULE else C
  return getattr(mod, p.attr)

def _key(name: str) -> tuple:
  mod, _, attr = name.rpartition(".")
  return ("SG" if mod == "SG" else "C"), attr

def _stage(rule_id: str, basis: str, name: str) -> str:
  if rule_id == "SCALE_GATE":
    return GATE
  if basis == TR.DEFAULT or name in NOT_THRESHOLDS:
    return POLICY
  return READ

def build(root: str = str(U.ROOT)) -> tuple:
  scan, imported = U.scan_package(root), U.imported_by_name(root)
  out = []
  
  for rid, label, basis, _codes, consts in TR.RULES:
    for name in consts:
      key, attr = _key(name)
      if name not in RANGES or name not in HAND:
        raise ValueError(f"{name} is named by rule {rid} but has no entry in the tuning register (RANGES and HAND).")
      unit, lo, hi = RANGES[name]
      hand = HAND[name]
      uses = scan.get((key, attr), [])
      stage = _stage(rid, basis, name)
      reasons = list(U.sweep_blockers(uses, imported))
      
      if stage == GATE:
        reasons.append("decided before the sheet is read (the scale gate), so a replay of the reader does not run it; it needs sheets whose true scale is labelled")
      if stage == POLICY:
        reasons.append(NOT_THRESHOLDS.get(name) or "an assumed value used because the drawing prints none; a policy of the estimator, not a reading threshold")
      out.append(Param(
        key=f"{key}.{attr}", name=name, module=GATE_MODULE if key == "SG" else CONFIG_MODULE, attr=attr, rule_id=rid, rule_label=label, basis=basis,
        families=FAMILIES.get(rid, ()), unit=unit, kind="int" if isinstance(hand, int) else "float", lo=float(lo), hi=float(hi), hand=hand, stage=stage,
        status=SWEEPABLE if not reasons else NOT_SWEEPABLE, reasons=tuple(reasons), copies=tuple(U.linked_copies(uses)),
        uses=tuple((u.file, u.line, u.where, u.how) for u in uses)))
  return tuple(out)

_BUILT: dict = {}

def params() -> tuple:
  if "p" not in _BUILT:
    _BUILT["p"] = build()
  return _BUILT["p"]

def by_key() -> dict:
  return {p.key: p for p in params()}

def get(key_or_name: str) -> Param:
  idx = by_key()
  if key_or_name in idx:
    return idx[key_or_name]
  for p in params():
    if p.name == key_or_name:
      return p
  raise KeyError(key_or_name)

def rules() -> list:
  out = []
  for rid, label, basis, codes, consts in TR.RULES:
    mine = [p for p in params() if p.rule_id == rid]
    out.append({"id": rid, "label": label, "basis": basis, "codes": list(codes), "params": [p.key for p in mine], "families": list(FAMILIES.get(rid, ())),
      "sweepable": sum(1 for p in mine if p.status == SWEEPABLE), "calibratable": sum(1 for p in mine if p.calibratable)})
  return out

def family_matches(family: str, families: tuple) -> bool:
  fam = str(family)
  return "*" in families or fam in families or fam.split(":", 1)[0] in families

LADDERS = {"narrow": (0.9, 1.1), "standard": (0.75, 0.9, 1.1, 1.25), "wide": (0.5, 0.7, 0.85, 1.15, 1.4, 2.0)}
INT_STEPS = {"narrow": (-1, 1), "standard": (-2, -1, 1, 2), "wide": (-3, -2, -1, 1, 2, 3)}

def _nice(v: float) -> float:
  if v == 0 or not math.isfinite(v):
    return v
  digits = 3 - int(math.floor(math.log10(abs(v)))) - 1
  return round(v, max(digits, 0)) if abs(v) < 1000 else round(v, 0)

def min_max_pairs(keys: list) -> list:
  out = []
  for a in keys:
    if "_MIN" in a:
      b = a.replace("_MIN", "_MAX", 1)
      if b in keys:
        out.append((a, b))
  return out

def candidates(p: Param, ladder: str = "standard", current=None) -> list:
  if ladder not in LADDERS:
    raise ValueError(f"ladder is one of {', '.join(LADDERS)}.")
  cur = p.live if current is None else current
  out = set()
  
  if p.kind == "int":
    for s in INT_STEPS[ladder]:
      out.add(int(cur) + s)
  else:
    for f in LADDERS[ladder]:
      out.add(_nice(float(cur) * f))
  vals = sorted(v for v in out if p.lo <= v <= p.hi and v != cur)
  return vals

def unregistered(root: str = str(U.ROOT)) -> dict:
  rows = U.numeric_constants(root)
  return {"total": sum(len(v) for v in rows.values()), "modules": [{"file": f, "count": len(v), "names": [n for n, _, _ in v[:8]]} for f, v in rows.items()]}
