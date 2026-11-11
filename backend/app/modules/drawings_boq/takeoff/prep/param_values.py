from __future__ import annotations
import re
from app.engine.catalogue import param_keys as PK
from app.engine.measure import rule_registry as RR

HEIGHTS, MIXES = "PARAM_HEIGHTS", "PARAM_MIXES"
MM_INCH, MM_FOOT = 25.4, 304.8
LEVEL = "NOTE"
WINDOW_BEFORE, WINDOW_AFTER = 70, 12

TWO = re.compile(r"(?<![\d:.])1\s*:\s*(\d)(?![\d.])(?!\s*:)(?!\s*\d/)")
THREE = re.compile(r"(?<![\d:.])1\s*:\s*(\d(?:\.\d)?(?:\s+1/2)?)\s*:\s*(\d(?:\.\d)?)(?![\d:.])")
BRICK = re.compile(r"\bBRICK(?:S|\s*-?\s*WORK|\s*-?\s*MASONRY)?\b|\bMASONRY\b", re.I)
PLASTER = re.compile(r"\bPLASTER(?:ING)?\b", re.I)
MUD = re.compile(r"\bMUD\b", re.I)
CONCRETE_WORD = re.compile(r"R\.?\s?C\.?\s?C\b|\bCONCRETE\b|P\.?\s?C\.?\s?C\b|\bSLABS?\b|\bBEAMS?\b|\bCOLUMNS?\b|\bFOOTINGS?\b|\bLINTELS?\b", re.I)
CLASS_NOTE = re.compile(r"CLASS\s+[\"“”']?[A-D]\b", re.I)
WALL_4 = re.compile(r"(?<![\d.])(?:4\s+1/2|4\.5)\s*(?:\"|″|”|''|IN\b|INCH)", re.I)
WALL_9 = re.compile(r"(?<![\d.])9\s*(?:\"|″|”|''|IN\b|INCH)", re.I)
BELOW = re.compile(r"BELOW\s+(?:PLINTH|D\.?\s?P\.?\s?C|GROUND)|\bFOUNDATIONS?\b|\bFOOTINGS?\b|PLINTH\s+(?:MASONRY|WALL)", re.I)
INSIDE = re.compile(r"\b(?:INSIDE|INTERNAL|INTERIOR)\b", re.I)
OUTSIDE = re.compile(r"\b(?:OUTSIDE|EXTERNAL|EXTERIOR)\b", re.I)
CEILING = re.compile(r"\b(?:CEILINGS?|SOFFIT)\b", re.I)
MEMBERS = (("pcc", re.compile(r"P\.?\s?C\.?\s?C\b", re.I)), ("footing", re.compile(r"\bFOOTINGS?\b|\bFOUNDATIONS?\b", re.I)), ("column", re.compile(r"\bCOLUMNS?\b", re.I)),
  ("beam", re.compile(r"\bBEAMS?\b", re.I)), ("slab", re.compile(r"\bSLABS?\b", re.I)), ("lintel", re.compile(r"\bLINTELS?\b", re.I)))
FT_IN = r"(?P<ft>\d{1,2})\s*'\s*-?\s*(?P<in>\d{1,2}(?:\s+\d{1,2}/\d{1,2})?)?\s*(?:\"|″|”|'')?"
DEPTH_A = re.compile(r"\b(?:EXCAVATION|EXCAVATED|FOUNDATION|FOOTING|TRENCH)\b[^0-9]{0,40}?\bDEPTH\b\s*(?:OF|=|:|IS)?\s*" + FT_IN, re.I)
DEPTH_B = re.compile(r"\bDEPTH\s+OF\s+(?:EXCAVATION|FOUNDATION|FOOTING|TRENCH)\b\s*(?:=|:|IS)?\s*" + FT_IN, re.I)

def _item(key: str, text: str, **extra) -> dict:
  return {"kind": PK.kind_of(key), "key": key, "text": text[:140], "level": LEVEL, **extra}

def _window(t: str, m: re.Match, floor: int = 0, tail: int = WINDOW_AFTER) -> str:
  return t[max(floor, m.start() - WINDOW_BEFORE):m.end() + tail]

def _in_range(key: str, n: float) -> bool:
  low, high = PK.get(key)["range"]
  return low <= n <= high

def _mortars(t: str) -> list:
  out, floor = [], 0
  for m in TWO.finditer(t):
    near = _window(t, m, floor)
    floor = m.end()
    if not BRICK.search(near) or PLASTER.search(near) or not _in_range("MORTAR_RATIO", int(m.group(1))):
      continue
    scope = "below plinth" if BELOW.search(near) else "4.5 in wall" if WALL_4.search(near) else "9 in wall" if WALL_9.search(near) else "wall"
    out.append(_item("MORTAR_RATIO", t, scope=scope, value=f"1:{m.group(1)}", unit="ratio"))
  return out

def _plasters(t: str) -> list:
  out, floor = [], 0
  for m in TWO.finditer(t):
    near = _window(t, m, floor)
    floor = m.end()
    if not PLASTER.search(near) or MUD.search(near) or not _in_range("PLASTER_MIX", int(m.group(1))):
      continue
    scope = "ceiling" if CEILING.search(near) else "outside" if OUTSIDE.search(near) else "inside" if INSIDE.search(near) else "plaster"
    out.append(_item("PLASTER_MIX", t, scope=scope, value=f"1:{m.group(1)}", unit="ratio"))
  return out

def _mix_text(mid: str, last: str) -> str | None:
  mid = re.sub(r"\s+1/2", ".5", mid.strip())
  try:
    a, b = float(mid), float(last)
  except ValueError:
    return None
  if not (_in_range("CONCRETE_MIX", a) and _in_range("CONCRETE_MIX", b)):
    return None
  return f"1:{mid}:{last}"

def _concretes(t: str) -> list:
  if CLASS_NOTE.search(t) or not CONCRETE_WORD.search(t):
    return []
  out, floor = [], 0
  for m in THREE.finditer(t):
    near = _window(t, m, floor, 0)
    floor = m.end()
    value = _mix_text(m.group(1), m.group(2))
    if value is None:
      continue
    scopes = [name for name, rx in MEMBERS if rx.search(near)] or ["rcc"]
    for scope in ["pcc"] if "pcc" in scopes else scopes:
      out.append(_item("CONCRETE_MIX", t, scope=scope, value=value, unit="ratio"))
  return out

def _fraction(s: str) -> float:
  a, _, b = s.partition("/")
  return int(a) / int(b) if b and int(b) else 0.0

def _depths(t: str) -> list:
  for rx in (DEPTH_B, DEPTH_A):
    m = rx.search(t)
    if not m:
      continue
    inch = 0.0
    if m.group("in"):
      parts = m.group("in").split()
      inch = float(parts[0]) + (_fraction(parts[1]) if len(parts) > 1 else 0.0)
    mm = round(int(m.group("ft")) * MM_FOOT + inch * MM_INCH, 2)
    return [_item("EXCAVATION_DEPTH", t, scope="foundation", value_mm=mm, unit="mm")] if _in_range("EXCAVATION_DEPTH", mm) else []
  return []

def read_line(t: str) -> list:
  out: list = []
  if RR.on(MIXES):
    out += _mortars(t) + _plasters(t) + _concretes(t)
  if RR.on(HEIGHTS):
    out += _depths(t)
  return out

def strongest(rows: list) -> list:
  if not rows:
    return []
  best = min(PK.rank(r.get("level")) for r in rows)
  return [r for r in rows if PK.rank(r.get("level")) == best]

def _same(a: dict, b: dict, shape: str) -> bool:
  if shape == "MM":
    return abs(float(a["value_mm"]) - float(b["value_mm"])) <= PK.tolerance_mm()
  return str(a.get("value")) == str(b.get("value"))

def pick(rows: list, shape: str) -> dict:
  top = strongest(rows)
  if not top:
    return {"state": "NONE", "row": None, "level": None, "values": []}
  groups: list = []
  for r in top:
    if not any(_same(r, g[0], shape) for g in groups):
      groups.append([r])
    else:
      next(g for g in groups if _same(r, g[0], shape)).append(r)
  level = PK.LEVELS[min(PK.rank(r.get("level")) for r in top)]
  if len(groups) == 1:
    return {"state": "PICKED", "row": groups[0][0], "level": level, "values": [groups[0][0].get("value", groups[0][0].get("value_mm"))]}
  return {"state": "CONFLICT", "row": None, "level": level, "values": [g[0].get("value", g[0].get("value_mm")) for g in groups]}

def from_items(items: list) -> dict:
  by: dict = {}
  for it in items or []:
    key = PK.key_of(it.get("kind"))
    if key is None or PK.get(key)["status"] != "LIVE":
      continue
    by.setdefault((key, str(it.get("scope") or "")), []).append(it)
    
  spec: dict = {}
  clash: list = []
  for (key, scope), rows in sorted(by.items()):
    got = pick(rows, PK.get(key)["shape"])
    if got["state"] == "PICKED":
      row = got["row"]
      spec.setdefault(key, {})[scope] = {"value": row.get("value", row.get("value_mm")), "text": row.get("text"), "pages": sorted(row.get("pages") or []), "level": got["level"]}
    elif got["state"] == "CONFLICT":
      clash.append({"key": key, "scope": scope, "level": got["level"], "values": got["values"]})
  return {"spec": spec, "spec_conflicts": clash}
