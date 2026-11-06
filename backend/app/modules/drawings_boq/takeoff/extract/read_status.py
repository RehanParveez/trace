from __future__ import annotations
import re
from app.engine.measure import readings as RD
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.extract import config as C

READ, UNSURE, NOT_READ = "READ", "UNSURE", "NOT_READ"
ROLE_BY = "ROLE_UNEXPECTED"
NO_SYMBOLS = "NO_SYMBOLS_FOUND"
LABELS_OUTLINED = "LABELS_OUTLINED"
OCR_LOW = "OCR_LOW_CONFIDENCE"
STATUS_KEY, REASONS_KEY = "read_status", "read_reasons"
HELD_PLAN_KINDS = ("COLUMN_LAYOUT", "FOOTING_LAYOUT", "EXCAVATION")
SUBSTRUCTURE_PLAN_KINDS = ("FOOTING_LAYOUT", "EXCAVATION")
SUPERSTRUCTURE = ("WALL", "ROOM", "DOOR", "WINDOW", "LINTEL", "STAIR")
SUPERSTRUCTURE_CLASSES = ("WALL", "ROOM", "DOOR", "WINDOW", "LINTEL_TYPE", "STAIR", "FINISH_LAYER", "BEAM")
SERVICES = ("ELECTRICAL", "PLUMBING", "FIRE", "HVAC", "GAS")
ROLE_OF = {"ARCH_PLAN": "PLAN", "FURNITURE_PLAN": "PLAN", "STRUCT_PLAN": "PLAN", "MEP_PLAN": "PLAN", "SCHEDULE": "SCHEDULE", "NOTES": "NOTES", "DETAIL": "DETAIL",
  "SECTION": "SECTION", "ELEVATION": "ELEVATION", "COVER": "COVER"}
STRIP_ITEMS = ("RCC_STRIP", "PCC_STRIP", "TRENCH", "BRICK_STEP", "TERMITE_STRIP")
PIPE_ITEMS = ("SEWER_PIPE", "RAIN_PIPE")
DRAIN_ITEMS = ("DRAIN_MANHOLE", "GULLY_TRAP", "INSPECTION_CHAMBER")
NO_READER = ("GRID", "SLAB_BAR_CALLOUT", "PLUMBING_FIXTURE", "COLUMN_SCHEDULE_CELL", "NOTE_FACT")
OUTLINED_TYPES = ("OUTLINED", "PARTIAL")
SLAB_WORDS = re.compile(r"SLAB|BEAM|FRAMING|REINFORCEMENT")
NOT_LAYOUT = re.compile(r"SECTION|DETAIL|SCHEDULE")

def status_of(c) -> str:
  return (getattr(c, "facts", None) or {}).get(STATUS_KEY, READ)

def reasons_of(c) -> list:
  return list((getattr(c, "facts", None) or {}).get(REASONS_KEY) or [])

def mark(c, status: str, reasons: list) -> None:
  f = dict(c.facts or {})
  f[STATUS_KEY] = status
  f[REASONS_KEY] = list(dict.fromkeys([*(f.get(REASONS_KEY) or []), *reasons]))
  c.facts = f

def class_of(c) -> str | None:
  f = c.facts or {}
  
  item = f.get("site_kind") if c.category == "SITE" else f.get("foundation_item")
  cat = c.category
  if cat in ("COLUMN", "ROOM", "DOOR", "WINDOW", "STAIR"):
    return cat
  if cat == "FOOTING":
    return "FOOTING_PAD"
  if cat == "BEAM":
    return "PLINTH_BEAM" if f.get("beam_role") == "PLINTH" else "BEAM"
  if cat == "SLAB":
    return "SLAB_PANEL"
  if cat == "LINTEL":
    return "LINTEL_TYPE"
  if cat == "WALL":
    if item in STRIP_ITEMS:
      return "FOOTING_STRIP"
    return "WALL" if item is None and "length_cc_m" in f else None
  if cat == "SITE":
    if item == "ELEC_BOARD":
      return "DISTRIBUTION_BOARD"
    if str(item or "").startswith("ELEC_"):
      return "ELECTRICAL_POINT"
    if item in PIPE_ITEMS:
      return "PIPE_RUN"
    if item in DRAIN_ITEMS:
      return "DRAIN_POINT"
  return None

def role_of(identity: dict | None) -> str | None:
  i = identity or {}
  return ROLE_OF.get((i.get("role_vote") or {}).get("role") or i.get("role") or "")

def plan_kind_of(identity: dict | None) -> str | None:
  i = identity or {}
  
  role = (i.get("role_vote") or {}).get("role") or i.get("role")
  title = " ".join([str(i.get("title") or ""), *[str(v.get("caption") or "") for v in i.get("views") or []]]).upper()
  layout = "LAYOUT" in title or "PLAN" in title
  if role == "MEP_PLAN" or i.get("discipline") in SERVICES:
    return "OVERLAY"
  if "COLUMN" in title and layout and "FOOTING" not in title and not NOT_LAYOUT.search(title):
    return "COLUMN_LAYOUT"
  if "FOOTING" in title and layout and not NOT_LAYOUT.search(title):
    return "FOOTING_LAYOUT"
  if "FOUNDATION" in title and layout or i.get("plan_kind") == "FOUNDATION":
    return "FOUNDATION"
  if role == "STRUCT_PLAN" and SLAB_WORDS.search(title):
    return "SLAB"
  if role == "FURNITURE_PLAN" or i.get("plan_kind") == "FURNITURE":
    return "FURNITURE"
  if role == "ARCH_PLAN":
    return "FLOOR"
  return None

def excavation_page(identity: dict | None) -> bool:
  i = identity or {}
  views = i.get("views") or []
  texts = [str(i.get("title") or ""), *[str(v.get("caption") or "") for v in views if len(views) == 1 and v.get("sheet_type") == "PLAN"]]
  return any("EXCAVATION" in t.upper() and ("LAYOUT" in t.upper() or "PLAN" in t.upper()) and not NOT_LAYOUT.search(t.upper()) for t in texts)

def text_type_of(pdf: dict | None) -> str:
  p = pdf or {}
  if p.get("type") in ("VECTOR_OUTLINED", "VECTOR_NOLETTER"):
    return "OUTLINED"
  if p.get("partial_outline"):
    return "PARTIAL"
  if p.get("type") in ("RASTER", "IMAGE_PAGE"):
    return "RASTER"
  return "TEXT"

def _set_aside(c, plan_kind: str, role: str | None) -> None:
  mark(c, UNSURE, [ROLE_BY])
  c.facts = {**c.facts, "set_aside": {"by": ROLE_BY, "plan_kind": plan_kind, "role": role}}

def hold(res, plan_kind: str | None, role: str | None) -> dict | None:
  if plan_kind not in HELD_PLAN_KINDS:
    return None
  expected = RD.EXPECTED_CLASSES.get(f"PLAN/{plan_kind}", ())
  held: dict = {}
  flagged: dict = {}
  length = 0.0
  
  for c in res.candidates:
    cls = class_of(c)
    if c.category in SUPERSTRUCTURE and cls != "FOOTING_STRIP":
      _set_aside(c, plan_kind, role)
      key = cls or "FINISH_LAYER"
      held[key] = held.get(key, 0) + 1
      length += float((c.facts or {}).get("length_cc_m") or 0.0) if key == "WALL" else 0.0
    elif cls and cls not in expected:
      mark(c, UNSURE, [ROLE_BY])
      if plan_kind in SUBSTRUCTURE_PLAN_KINDS and cls in SUPERSTRUCTURE_CLASSES and RR.on("HOLD_SUPERSTRUCTURE_ON_SUBSTRUCTURE_LAYOUTS"):
        _set_aside(c, plan_kind, role)
        held[cls] = held.get(cls, 0) + int(c.count or 1)
      else:
        flagged[cls] = flagged.get(cls, 0) + int(c.count or 1)
      
  if not held and not flagged:
    return None
  if held:
    res.notes.append(C.note("ROLE_UNEXPECTED_CLASS", plan_kind=plan_kind, held=dict(sorted(held.items()))))
  return {"plan_kind": plan_kind, "items": sum(held.values()), "by_class": dict(sorted(held.items())), "wall_length_m": round(length, 1), "unsure": dict(sorted(flagged.items()))}

def coverage(candidates: list, role: str | None, plan_kind: str | None, text_type: str) -> dict:
  key = f"PLAN/{plan_kind}" if role == "PLAN" and plan_kind else role
  expected = RD.EXPECTED_CLASSES.get(key or "", ())
  by_class: dict = {}
  for c in candidates:
    cls = class_of(c)
    if cls:
      by_class.setdefault(cls, []).append(c)
      
  rows = []
  for cls in expected:
    items = by_class.get(cls, [])
    if items:
      live = [c for c in items if status_of(c) == READ]
      rows.append({"class": cls, "expected": True, "count": sum(int(c.count or 1) for c in items), "status": READ if live else UNSURE,
        "reasons": [] if live else sorted({r for c in items for r in reasons_of(c)})})
    else:
      rows.append({"class": cls, "expected": True, "count": 0, "status": NOT_READ, "reasons": [LABELS_OUTLINED if text_type in OUTLINED_TYPES else NO_SYMBOLS],
        "no_reader": cls in NO_READER})
  states = {r["status"] for r in rows}
  status = None if not rows else READ if states == {READ} else NOT_READ if states == {NOT_READ} else UNSURE
  return {"key": key, "role": role, "plan_kind": plan_kind, "text_type": text_type, "status": status, "classes": rows}

def outlined(res, pdf: dict | None) -> dict:
  p = pdf or {}
  marks = {str(m).upper() for m in p.get("outlined_marks") or []}
  low = {str(m).upper() for m in p.get("outlined_low_marks") or []}
  seen = {"read": 0, "unsure": 0}
  for c in res.candidates:
    tag = str(getattr(c, "tag", None) or "").upper()
    if tag in low:
      mark(c, UNSURE, [OCR_LOW])
      seen["unsure"] += 1
    elif tag in marks:
      mark(c, READ, [LABELS_OUTLINED])
      seen["read"] += 1
  return seen

def apply(res, identity: dict | None, pdf: dict | None) -> None:
  role = role_of(identity)
  kind = plan_kind_of(identity) if role == "PLAN" else None
  text = text_type_of(pdf)
  held = hold(res, "EXCAVATION" if role == "PLAN" and kind not in ("COLUMN_LAYOUT", "FOOTING_LAYOUT") and RR.on("HOLD_SUPERSTRUCTURE_ON_SUBSTRUCTURE_LAYOUTS") and excavation_page(identity) else kind, role)
  seen = outlined(res, pdf)
  cov = coverage(res.candidates, role, kind, text)
  if held:
    cov["held"] = held
  if seen["read"] or seen["unsure"]:
    cov["outlined"] = seen
  res.stats["coverage"] = cov
