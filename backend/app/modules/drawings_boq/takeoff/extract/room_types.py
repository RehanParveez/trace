from __future__ import annotations
import re
from app.engine.measure import rulebook as RB

BEDROOM, BATH, PWD, WC, KITCHEN, LOUNGE, DINING, DRAWING = "BEDROOM", "BATH", "PWD", "WC", "KITCHEN", "LOUNGE", "DINING", "DRAWING"
PORCH, TERRACE, PASSAGE, LAWN = "PORCH", "TERRACE", "PASSAGE", "LAWN"
LOOK_BELOW, VOID, DOUBLE_HEIGHT, STAIR, STORE, SERVANT, OTHER = "LOOK_BELOW", "VOID", "DOUBLE_HEIGHT", "STAIR", "STORE", "SERVANT", "OTHER"
TYPES = (BEDROOM, BATH, PWD, WC, KITCHEN, LOUNGE, DINING, DRAWING, PORCH, TERRACE, PASSAGE, LAWN, LOOK_BELOW, VOID, DOUBLE_HEIGHT, STAIR, STORE, SERVANT, OTHER)
WET = (BATH, PWD, WC)
NOT_FLOORED = (LOOK_BELOW, VOID, DOUBLE_HEIGHT)
ROOM_TYPE_KEY = "finish.room_type"

_PREFIX = r"(?:(?:MASTER|ATTACHED|COMMON|MAIN|SERVANT|FRONT|REAR|UPPER|LOWER|GUEST|KIDS|GIRLS|BOYS)\s+)?"
WET_ROOM = re.compile(r"^" + _PREFIX + r"(?P<kind>BATH ?ROOM|BATH|TOILET|LAVATORY|POWDER(?: ROOM)?|PWD|W\.C|W/C|WC)(?![A-Z])")
KITCHEN_ROOM = re.compile(r"^(?:(?:MAIN|OPEN|DRY|WET|SERVANT|UPPER|LOWER|FRONT|REAR)\s+)?KITCHEN(?:ETTE)?(?![A-Z])")
KITCHEN_SHARED = re.compile(r"DIN|LOUNGE|LIVING|DRAWING|LOBBY|HALL|TV|LAUNDRY|UTILITY")

_ANYWHERE = (
  (LOOK_BELOW, re.compile(r"LOOK[\s-]*(?:DOWN|BELOW)|OPEN[\s-]+(?:TO[\s-]+)?BELOW")),
  (DOUBLE_HEIGHT, re.compile(r"DOUBLE[\s-]*(?:HEIGHT|HT)|DBL[\s.-]*(?:HEIGHT|HT)")),
  (VOID, re.compile(r"(?<![A-Z])VOID(?![A-Z])")),
)
_SEGMENT = (
  (PORCH, re.compile(r"(?<![A-Z])PORCH(?![A-Z])")),
  (TERRACE, re.compile(r"(?<![A-Z])(?:TERRACE|BALCONY|VERANDAH?|SIT[\s-]?OUT)(?![A-Z])")),
  (LAWN, re.compile(r"(?<![A-Z])(?:LAWN|GARDEN|COURT[\s-]?YARD)(?![A-Z])")),
  (STAIR, re.compile(r"(?<![A-Z])STAIR(?:CASE|S)?(?![A-Z])")),
  (PASSAGE, re.compile(r"(?<![A-Z])(?:PASSAGE|CORRIDOR|LOBBY|GALLERY)(?![A-Z])")),
  (STORE, re.compile(r"(?<![A-Z])(?:STORE|STORAGE|PANTRY)(?![A-Z])")),
  (SERVANT, re.compile(r"(?<![A-Z])(?:SERVANT|MAID|DRIVER)(?![A-Z])")),
  (DRAWING, re.compile(r"(?<![A-Z])(?:DRAWING|DRG|DWG)(?![A-Z])")),
  (DINING, re.compile(r"(?<![A-Z])DINING(?![A-Z])")),
  (LOUNGE, re.compile(r"(?<![A-Z])(?:LOUNGE|LIVING|FAMILY|SITTING|TV)(?![A-Z])")),
  (BEDROOM, re.compile(r"(?<![A-Z])(?:BED|BEDROOM|GUEST|KIDS|DRESSING|DRESS|WARDROBE|W\.?I\.?C|WALK[\s-]?IN)(?![A-Z])")),
)
_SPLIT = re.compile(r"\s*(?:/|,|&|\+|\bAND\b)\s*")

def _norm(name) -> str:
  return re.sub(r"[\s_]+", " ", str(name or "").upper()).strip()

def type_of(room_name) -> str:
  name = _norm(room_name)
  if not name:
    return OTHER
  for kind, rx in _ANYWHERE:
    if rx.search(name):
      return kind
  m = WET_ROOM.match(name)
  if m:
    word = m.group("kind")
    return PWD if word.startswith(("POWDER", "PWD")) else BATH if word.startswith("BATH") else WC
  if KITCHEN_ROOM.match(name):
    return KITCHEN
  for part in _SPLIT.split(name):
    for kind, rx in _SEGMENT:
      if rx.search(part):
        return kind
  return OTHER

def names_of(room) -> list:
  f = getattr(room, "facts", None) or {}
  out = [str(n).upper() for n in (f.get("names") or [])]
  if f.get("name"):
    out.append(str(f["name"]).upper())
  return out

def of_room(room) -> str:
  names = names_of(room)
  for n in names:
    rv = RB.resolve(ROOM_TYPE_KEY, {"room_name": _norm(n)}, record=False)
    if rv.value is not None and str(rv.value) in TYPES:
      return str(rv.value)
  types = [type_of(n) for n in names]
  return next((t for t in types if t in WET), types[0] if types else OTHER)

def type_of_name(name) -> str:
  rv = RB.resolve(ROOM_TYPE_KEY, {"room_name": _norm(name)}, record=False)
  if rv.value is not None and str(rv.value) in TYPES:
    return str(rv.value)
  return type_of(name)

def floored(room) -> bool:
  return of_room(room) not in NOT_FLOORED

def is_wet_type(kind: str) -> bool:
  return kind in WET
