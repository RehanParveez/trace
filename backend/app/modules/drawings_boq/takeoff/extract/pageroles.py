from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import config as C

_ROLES = (
  ("SCHEDULE", re.compile(r"\b(?:DOOR|WINDOW|OPENING|FINISH|FINISHES|COLUMN|BEAM|FOOTING|LINTEL|ROOM|BAR\s+BENDING)\s+(?:AND\s+\w+\s+)?SCHEDULES?\b|\bSCHEDULES?\s+OF\b", re.I)),
  ("SECTION", re.compile(r"\b(?:BUILDING\s+|WALL\s+|TYPICAL\s+)?SECTIONS?\b(?:\s+(?:AT|ON|THROUGH)\b|\s+[A-Z]\s*[-–]\s*[A-Z]\b|\s*$)|\bSECTION\s+[A-Z][-–][A-Z]\b|\bBUILDING\s+SECTIONS?\b", re.I)),
  ("ELEVATION", re.compile(r"\b(?:FRONT|REAR|LEFT|RIGHT|SIDE|NORTH|SOUTH|EAST|WEST|BUILDING)?\s*ELEVATIONS?\b", re.I)),
  ("DETAIL", re.compile(r"\b(?:BLOW[\s-]*UP\s+)?DETAILS?\b", re.I)),
  ("SITE", re.compile(r"\b(?:SITE|LOCATION|BLOCK|KEY)\s+PLAN\b|\bPLOT\s+PLAN\b", re.I)),
  ("LEGEND", re.compile(r"\b(?:LEGENDS?|SYMBOLS?|ABBREVIATIONS?|DRAWING\s+LIST|LIST\s+OF\s+DRAWINGS|INDEX)\b", re.I)),
  ("SPEC", re.compile(r"\b(?:SPECIFICATIONS?|GENERAL\s+NOTES|NOTES\s+AND\s+SPECIFICATIONS?|BILL\s+OF\s+QUANTITIES|SCOPE\s+OF\s+WORK)\b", re.I)),
)
_STRONG_TITLE = re.compile(r"\b(?:PLAN|LAYOUT|MUMTY|FRAMING|REINFORCEMENT|FOUNDATIONS?)\b", re.I)
_DRAWING_ROLES = ("PLAN", "STRUCTURAL")
_FURNITURE = re.compile(r"^(?:[A-Z0-9.]+\s+){0,3}FURNITURE\s+(?:LAYOUTS?|PLANS?)(?:\s+PLANS?)?$", re.I)
_WORKING = re.compile(r"^(?:[A-Z0-9.]+\s+){0,3}WORKING\s+(?:LAYOUTS?|PLANS?|DRAWINGS?)(?:\s+PLANS?)?$", re.I)
NOT_A_PLAN = ("SECTION", "ELEVATION", "DETAIL", "SCHEDULE", "LEGEND", "SPEC", "COVER", "DIVIDER", "SITE")

def _title_lines(words: list) -> list:
  by_line: dict = {}
  for w in words:
    if abs(((w.angle + 45) % 90) - 45) > 6:
      continue
    by_line.setdefault((round(w.angle / 90.0) % 4, round(w.cy / max(w.size * 0.6, 1.0))), []).append(w)
  out = []
  for ws in by_line.values():
    ws.sort(key=lambda o: o.x0)
    out.append((" ".join(o.text for o in ws), max(o.size for o in ws)))
  return out

def purpose(lines: list) -> str | None:
  """What the title block says the plan is for: FURNITURE (a furniture layout, the same walls with furniture drawn in) or WORKING (the working drawing)."""
  texts = [t.strip() for t, _s in lines]
  if any(_WORKING.match(t) for t in texts):
    return "WORKING"
  return "FURNITURE" if any(_FURNITURE.match(t) for t in texts) else None

def page_role(words: list, kind: dict | None = None, drawn: int = 0) -> dict:
  kind = kind or {"kind": "UNKNOWN", "title": None}
  lines = _title_lines(words)
  found: dict = {}
  
  for text, size in lines:
    for role, rx in _ROLES:
      if rx.search(text):
        if role not in found or size > found[role][0]:
          found[role] = (size, text[:80])
        break
  base = kind.get("kind")

  if base in _DRAWING_ROLES and found and not _STRONG_TITLE.search(kind.get("title") or ""):
    base = None
  if base in _DRAWING_ROLES:
    plan_size = max((s for t, s in lines if kind.get("title") and t[:80] == kind["title"]), default=0.0)
    others = sorted(r for r, (s, _t) in found.items() if plan_size and s >= plan_size * C.PAGE_COMPOSITE_SHARE and r in ("SECTION", "ELEVATION", "DETAIL", "SCHEDULE"))
    
    if others:
      return {"role": "COMPOSITE", "title": kind.get("title"), "also": [base, *others], "basis": "TITLE"}
    return {"role": base, "title": kind.get("title"), "also": sorted(found), "basis": "TITLE", "purpose": purpose(lines)}
  if found:
    role = max(found, key=lambda r: found[r][0])
    return {"role": role, "title": found[role][1], "also": sorted(r for r in found if r != role), "basis": "TITLE"}

  if len(words) < C.PAGE_SPARSE_WORDS:
    if drawn >= C.PAGE_DRAWN_SEGMENTS:
      return {"role": "UNKNOWN", "title": None, "also": [], "basis": "SPARSE_TEXT_DRAWN"}
    title =max(lines, key=lambda t: t[1])[0][:80] if lines else None
    return {"role": "DIVIDER" if title else "COVER", "title": title, "also": [], "basis": "SPARSE_TEXT"}
  return {"role": "UNKNOWN", "title": None, "also": [], "basis": "NONE"}

def reading_advice(role: dict) -> str:
  r = role.get("role")
  if r in _DRAWING_ROLES:
    return "READ"
  if r in NOT_A_PLAN:
    return "SKIP"
  return "ASK"
