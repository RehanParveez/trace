from __future__ import annotations
from app.engine.measure import rulebook as RB
from app.modules.drawings_boq.takeoff.extract import room_types as RT

FLOOR_ITEM = "finish.floor_item"
DADO_HEIGHT = "finish.dado_height_mm"
KITCHEN_BAND = "finish.kitchen_band"
CEILING_INCLUDES = "finish.ceiling_includes"
PCC_UNDER = "finish.pcc_under"
ROOM_TYPE = RT.ROOM_TYPE_KEY
KEYS = (FLOOR_ITEM, DADO_HEIGHT, KITCHEN_BAND, CEILING_INCLUDES, PCC_UNDER, ROOM_TYPE)

TO_CEILING = "CEILING"
FULL = "full"
NONE = "NONE"
DADO_FALLBACK_MM = 2134.0
DEFAULT_FLOOR_ITEM = "FIN-FLOOR"
HEIGHT_MIN_MM, HEIGHT_MAX_MM = 300.0, 6000.0
SCOPE_KEYS = {FLOOR_ITEM: ("room_type",), DADO_HEIGHT: ("room_type",), KITCHEN_BAND: ("room_type",), CEILING_INCLUDES: ("level",), PCC_UNDER: ("level",), ROOM_TYPE: ("room_name",)}
HEIGHT_TYPES = (*RT.WET, RT.KITCHEN)
TYPED_FLOORS = {RT.PORCH: "FLOOR_PORCH", RT.TERRACE: "FLOOR_TERRACE", RT.PASSAGE: "FLOOR_PASSAGE", RT.LAWN: "FLOOR_LAWN"}
TYPED_ITEM_CODE = {"FLOOR_PORCH": "FIN-PORCH-TILE", "FLOOR_TERRACE": "FIN-TERRACE-TILE", "FLOOR_PASSAGE": "FIN-PAVING", "FLOOR_LAWN": "FIN-PAVING"}
TYPED_TEXT = {"FLOOR_PORCH": "Floor tile of the porch", "FLOOR_TERRACE": "Floor tile of the terraces", "FLOOR_PASSAGE": "Paving of the passages", "FLOOR_LAWN": "Paving of the lawns and yards"}

def rule(key: str, **scope) -> RB.RuleValue:
  return RB.resolve(key, scope or None)

def evidence(key: str, rv: RB.RuleValue, **scope) -> dict:
  return {"key": key, "scope": dict(scope), "value": rv.value, "origin": rv.origin, "cls": rv.cls, "rule_id": rv.rule_id, "version": rv.version}

def is_default(rv: RB.RuleValue) -> bool:
  return rv.origin == RB.CODE_DEFAULT_ASSUMED

def floor_item(room_type: str) -> tuple:
  rv = rule(FLOOR_ITEM, room_type=room_type)
  return (str(rv.value) if rv.value is not None else DEFAULT_FLOOR_ITEM), rv

def default_floor_item() -> str:
  rv = rule(FLOOR_ITEM)
  return str(rv.value) if rv.value is not None else DEFAULT_FLOOR_ITEM

def height_mm(room_type: str, clear_mm: float | None) -> tuple:
  rv = rule(DADO_HEIGHT, room_type=room_type)
  v = rv.value
  if isinstance(v, str) and v.strip().upper() == TO_CEILING:
    if clear_mm:
      return float(clear_mm), rv, False
    return DADO_FALLBACK_MM, rv, True
  try:
    return float(v), rv, False
  except (TypeError, ValueError):
    return DADO_FALLBACK_MM, rv, True

def kitchen_band(room_type: str = RT.KITCHEN) -> tuple:
  rv = rule(KITCHEN_BAND, room_type=room_type)
  v = rv.value
  if isinstance(v, dict):
    try:
      lo, hi = float(v["from_mm"]), float(v["to_mm"])
    except (KeyError, TypeError, ValueError):
      return None, rv
    if hi > lo >= 0.0:
      return (lo, hi), rv
  return None, rv

def room_types_in(key: str, level: str | None) -> tuple:
  rv = rule(key, level=level) if level else rule(key)
  v = rv.value
  return ({str(t) for t in v} if isinstance(v, (list, tuple)) else set(RT.TYPES)), rv

def _scope_problem(key: str, scope) -> str | None:
  allowed = SCOPE_KEYS[key]
  scope = scope or {}
  if not isinstance(scope, dict) or any(k not in allowed for k in scope):
    return f"{key} can be scoped by {', '.join(allowed)} only."
  t = scope.get("room_type")
  if t is not None and t not in RT.TYPES:
    return f"{t} is not a room type."
  return None

def checked(key: str, scope, raw):
  if key not in KEYS:
    raise ValueError(f"{key} is not a finish rule.")
  bad = _scope_problem(key, scope)
  
  if bad:
    raise ValueError(bad)
  t = (scope or {}).get("room_type")
  if key == FLOOR_ITEM:
    if not isinstance(raw, str) or not raw.strip():
      raise ValueError("The floor item is a work item code, or NONE to leave the room out.")
    code = raw.strip().upper()
    if t in RT.WET:
      raise ValueError("The floor of a bath, toilet or powder room is its own line; its work item is not a rule.")
    if t is not None and code != NONE and t not in TYPED_FLOORS:
      raise ValueError(f"Only {', '.join(TYPED_FLOORS)} can have a floor item of their own; use NONE to leave {t} out, or set the item for every room.")
    if t is None and code == NONE:
      raise ValueError("NONE is for one room type; it cannot be the item of every room.")
    return code

  if key == DADO_HEIGHT:
    if t is not None and t not in HEIGHT_TYPES:
      raise ValueError(f"A tile height can be set for {', '.join(HEIGHT_TYPES)}.")
    if isinstance(raw, str) and raw.strip().upper() == TO_CEILING:
      return TO_CEILING
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not HEIGHT_MIN_MM <= float(raw) <= HEIGHT_MAX_MM:
      raise ValueError(f"The tile height is {HEIGHT_MIN_MM:g} to {HEIGHT_MAX_MM:g} mm, or CEILING.")
    return float(raw)
  if key == KITCHEN_BAND:
    if t is not None and t != RT.KITCHEN:
      raise ValueError("The band is for the kitchen.")
    if isinstance(raw, str) and raw.strip().lower() == FULL:
      return FULL
    if isinstance(raw, dict) and set(raw) == {"from_mm", "to_mm"} and all(isinstance(raw[k], (int, float)) and not isinstance(raw[k], bool) for k in raw):
      lo, hi = float(raw["from_mm"]), float(raw["to_mm"])
      if 0.0 <= lo < hi <= HEIGHT_MAX_MM:
        return {"from_mm": lo, "to_mm": hi}
    
    raise ValueError(f"The kitchen band is full, or {{from_mm, to_mm}} above the floor with from below to and to at most {HEIGHT_MAX_MM:g}.")
  if key in (CEILING_INCLUDES, PCC_UNDER):
    if not isinstance(raw, (list, tuple)) or not raw or any(x not in RT.TYPES for x in raw) or len(set(raw)) != len(raw):
      raise ValueError("Give a list of room types, each once.")
    return [str(x) for x in raw]
  if not isinstance(raw, str) or raw not in RT.TYPES:
    raise ValueError("The type of a room is one of " + ", ".join(RT.TYPES) + ".")
  if not (scope or {}).get("room_name"):
    raise ValueError("A room's type is set by the name of the room.")
  return raw

def seed_expect() -> dict:
  every = [t for t in RT.TYPES if t not in RT.NOT_FLOORED]
  return {FLOOR_ITEM: DEFAULT_FLOOR_ITEM, DADO_HEIGHT: DADO_FALLBACK_MM, KITCHEN_BAND: FULL, CEILING_INCLUDES: every, PCC_UNDER: list(every)}
