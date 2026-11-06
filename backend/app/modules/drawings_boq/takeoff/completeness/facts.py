from __future__ import annotations
import re

HOUSE, PLAZA = "HOUSE", "PLAZA"
RCC_FRAME, LOAD_BEARING = "RCC_FRAME", "LOAD_BEARING"
ARCHITECTURE, STRUCTURE, ELECTRICAL, PLUMBING, HVAC, FIRE, INTERIOR = "ARCHITECTURE", "STRUCTURE", "ELECTRICAL", "PLUMBING", "HVAC", "FIRE", "INTERIOR"
SOURCE_REGISTER, SOURCE_DECISION, SOURCE_DEFAULT, SOURCE_NONE = "REGISTER", "DECISION", "DEFAULT", "NONE"
STRUCTURE_KINDS = ("COLUMN_LAYOUT", "FOOTING_LAYOUT", "FOUNDATION", "SLAB", "EXCAVATION")
ARCHITECTURE_KINDS = ("FLOOR", "FURNITURE")
SERVICE_SETS = {"ELECTRICAL": ELECTRICAL, "PLUMBING": PLUMBING, "GAS": PLUMBING, "HVAC": HVAC, "FIRE": FIRE}
PLAZA_WORDS = re.compile(r"\b(PLAZA|COMMERCIAL|SHOPPING|MALL|HOTEL|APARTMENTS?)\b")
FLOOR_PLAN_WORDS = re.compile(r"\b(FLOOR|ROOF) PLAN\b")
BASEMENT_WORDS = re.compile(r"\bBASEMENT\b")
SHEET_ROLES = ("PLAN", "SCHEDULE", "SECTION", "DETAIL", None)
SERVICE_ROLES = ("PLAN", "SCHEDULE")
MIN_SERVICE_SHEETS = 2
NOT_FLOORS = ("FOUNDATION", "ALL")
FLOOR_ORDER = ("BASEMENT", "GROUND", "FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "MUMTY", "ROOF")
FACT_KEYS = ("type", "structure", "floors", "basement", "sets_present")

def _fact(value, source: str, detail: str = "", **extra) -> dict:
  return {"value": value, "source": source, "detail": detail, **extra}

def _floor_key(name: str) -> tuple:
  return (FLOOR_ORDER.index(name), name) if name in FLOOR_ORDER else (len(FLOOR_ORDER), name)

def _title(row: dict) -> str:
  return str(row.get("title") or "").upper()

def _is_plan(row: dict) -> bool:
  return row.get("role") in ("PLAN", "SCHEDULE")

def sets_of(rows: list) -> tuple:
  found: dict = {}
  loose: list = []
  
  for r in rows:
    kind = r.get("plan_kind")
    disc = str(r.get("discipline") or "").upper()
    role = r.get("role")
    page = r.get("page")
    
    if kind in STRUCTURE_KINDS or (disc == "STRUCTURAL" and role in SHEET_ROLES):
      found.setdefault(STRUCTURE, []).append(page)
    elif kind == "FLOOR" and disc == "ARCHITECTURAL":
      found.setdefault(ARCHITECTURE, []).append(page)
    elif kind == "FLOOR" and disc in ("", "NONE") and role == "PLAN":
      (found.setdefault(ARCHITECTURE, []) if FLOOR_PLAN_WORDS.search(_title(r)) else loose).append(page)
    elif role == "ELEVATION" and disc != "STRUCTURAL":
      found.setdefault(ARCHITECTURE, []).append(page)
    if kind == "FURNITURE":
      found.setdefault(INTERIOR, []).append(page)
    if disc in SERVICE_SETS and role in SERVICE_ROLES:
      found.setdefault(SERVICE_SETS[disc], []).append(page)
  if loose and STRUCTURE not in found:
    found.setdefault(ARCHITECTURE, []).extend(loose)
  for name in (ELECTRICAL, PLUMBING, HVAC, FIRE):
    if len(set(found.get(name, ()))) < MIN_SERVICE_SHEETS:
      found.pop(name, None)
      
  order = (ARCHITECTURE, STRUCTURE, ELECTRICAL, PLUMBING, HVAC, FIRE, INTERIOR)
  return [s for s in order if s in found], {s: sorted(set(p for p in found[s] if p is not None)) for s in order if s in found}

def type_of(rows: list) -> dict:
  hits = sorted({r.get("page") for r in rows if PLAZA_WORDS.search(_title(r)) and r.get("page") is not None})
  if hits:
    return _fact(PLAZA, SOURCE_REGISTER, "a sheet title names a commercial building", pages=hits)
  return _fact(HOUSE, SOURCE_DEFAULT, "no sheet title names a commercial building; a house is assumed")

def structure_of(rows: list) -> dict:
  cols = sorted({r.get("page") for r in rows if r.get("plan_kind") == "COLUMN_LAYOUT" or (r.get("role") == "SCHEDULE" and str(r.get("discipline") or "").upper() == "STRUCTURAL")} - {None})
  if cols:
    return _fact(RCC_FRAME, SOURCE_REGISTER, "a column layout or a structural schedule is in the set", pages=cols)
  strc = sorted({r.get("page") for r in rows if r.get("role") == "PLAN" and r.get("plan_kind") in STRUCTURE_KINDS} - {None})
  if strc:
    return _fact(LOAD_BEARING, SOURCE_REGISTER, "foundation or slab plans without a column layout or schedule", pages=strc)
  return _fact(None, SOURCE_NONE, "no structural sheet in the set")

def floors_of(rows: list, storeys: list | None = None, extra: list | None = None) -> dict:
  seen = {r.get("floor") for r in rows if r.get("floor") and _is_plan(r)}
  seen |= {f for f in (storeys or []) if f}
  seen |= {f for f in (extra or []) if f}
  names = sorted((str(f).upper() for f in seen if str(f).upper() not in NOT_FLOORS), key=_floor_key)
  if not names:
    return _fact([], SOURCE_NONE, "no sheet names a floor")
  parts = [p for p, ok in (("sheets", any(r.get("floor") for r in rows)), ("storeys", bool(storeys)), ("schedule joins", bool(extra))) if ok]
  return _fact(names, SOURCE_REGISTER, "floors named by " + ", ".join(parts))

def basement_of(rows: list, floors: list) -> dict:
  pages = sorted({r.get("page") for r in rows if _is_plan(r) and (r.get("floor") == "BASEMENT" or BASEMENT_WORDS.search(_title(r))) and r.get("page") is not None})
  if "BASEMENT" in floors and not pages:
    return _fact(True, SOURCE_REGISTER, "a storey record names a basement", pages=[], single_sheet=False)
  if pages:
    return _fact(True, SOURCE_REGISTER, "a sheet names a basement" if len(pages) == 1 else f"{len(pages)} sheets name a basement", pages=pages, single_sheet=len(pages) == 1)
  return _fact(False, SOURCE_DEFAULT, "no sheet names a basement")

def project_facts(rows: list, decisions: dict | None = None, storeys: list | None = None, join_floors: list | None = None) -> dict:
  sets, set_pages = sets_of(rows)
  floors = floors_of(rows, storeys, join_floors)
  
  facts = {
    "type": type_of(rows),
    "structure": structure_of(rows),
    "floors": floors,
    "basement": basement_of(rows, floors["value"]),
    "sets_present": _fact(sets, SOURCE_REGISTER if sets else SOURCE_NONE, "sets found on the sheets" if sets else "no sheet shows a drawing set", pages=set_pages),
  }
  
  for key, value in (decisions or {}).items():
    if key in facts:
      facts[key] = _fact(value, SOURCE_DECISION, "set by a decision", was=facts[key]["value"])
  return facts

def values(facts: dict) -> dict:
  return {k: v["value"] for k, v in facts.items()}

def scope_of(facts: dict) -> str:
  sets = list(facts["sets_present"]["value"] or [])
  return "STRUCTURE_ONLY" if sets == [STRUCTURE] else "FULL"
