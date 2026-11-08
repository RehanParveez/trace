from __future__ import annotations
import functools
import os
import re
import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "self_checks.yaml")
FIELDS = ("id", "compares", "classes", "tolerance", "needs", "say")

KINDS = {
  "marks_in": ("left", "right"),
  "marks_agree": ("left", "right"),
  "area_fill": ("left", "right", "band"),
  "values_agree": ("left", "right", "within"),
  "ratio_band": ("top", "bottom", "band"),
  "totals_agree": ("left", "right"),
}

READ_KINDS = ("marks_in", "marks_agree", "area_fill", "values_agree")
LEDGER_KINDS = ("ratio_band", "totals_agree")
SAY_KEYS = ("pass", "fail")
ID = re.compile(r"^[A-Z][A-Z0-9_]*$")

@functools.lru_cache(maxsize=1)
def _load() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def reload() -> None:
  _load.cache_clear()

def _num(v) -> bool:
  return isinstance(v, (int, float)) and not isinstance(v, bool)

def _side_classes(side) -> set:
  return {str(c) for c in (side or {}).get("classes") or []}

def independent(compares: dict) -> bool:
  a, b = compares.get("left") or {}, compares.get("right") or {}
  if _side_classes(a) & _side_classes(b):
    ra, rb = set(a.get("roles") or []), set(b.get("roles") or [])
    return bool(ra) and bool(rb) and not ra & rb
  return True

def check_problems(c: dict) -> list:
  who = c.get("id") or "?"
  out = [f"self_checks.yaml: {who} has no {f}" for f in FIELDS if f not in c or c[f] in (None, "", [], {}) and f not in ("classes", "needs")]
  if out:
    return out
  
  if not ID.match(str(c["id"])):
    out.append(f"self_checks.yaml: {who} is not an upper-case id")
  cmp_ = c["compares"]
  if not isinstance(cmp_, dict) or cmp_.get("kind") not in KINDS:
    return out + [f"self_checks.yaml: {who} compares must be a mapping with a kind in {', '.join(sorted(KINDS))}"]
  for k in KINDS[cmp_["kind"]]:
    if k not in cmp_:
      out.append(f"self_checks.yaml: {who} ({cmp_['kind']}) needs {k} in compares")
  if out:
    return out
  if cmp_["kind"] in READ_KINDS:
    for side in ("left", "right"):
      if not _side_classes(cmp_[side]):
        out.append(f"self_checks.yaml: {who} {side} names no reading class")
    if not out and not independent(cmp_):
      out.append(f"self_checks.yaml: {who} compares a reading with itself: the two sides share a class and are not on sheets of different roles")
    if not c["classes"]:
      out.append(f"self_checks.yaml: {who} speaks for no reading class")
  if cmp_["kind"] in ("area_fill", "values_agree"):
    for side in ("left", "right"):
      if not (cmp_.get(side) or {}).get("field"):
        out.append(f"self_checks.yaml: {who} {side} names no field to compare")
        
  band = cmp_.get("band")
  if band is not None and not (isinstance(band, list) and len(band) == 2 and all(_num(x) for x in band) and band[0] < band[1]):
    out.append(f"self_checks.yaml: {who} band must be [low, high] with low below high")
  if cmp_["kind"] == "values_agree" and not (_num(cmp_.get("within")) and cmp_["within"] >= 0):
    out.append(f"self_checks.yaml: {who} within must be a number from 0")
  if not (_num(c["tolerance"]) and 0 <= c["tolerance"] <= 1):
    out.append(f"self_checks.yaml: {who} tolerance must be a share from 0 to 1")
  if not isinstance(c.get("needs"), list) or not c["needs"]:
    out.append(f"self_checks.yaml: {who} needs must name what the check cannot run without")
  say = c.get("say")
  if not isinstance(say, dict) or any(not isinstance(say.get(k), str) or not say[k] for k in SAY_KEYS):
    out.append(f"self_checks.yaml: {who} say needs a pass and a fail sentence")
  return out

def problems(doc: dict | None = None) -> list:
  doc = _load() if doc is None else doc
  checks = doc.get("checks")
  if not isinstance(checks, list) or not checks:
    return ["self_checks.yaml: checks must be a list of checks"]
  out, seen = [], set()
  
  for c in checks:
    if not isinstance(c, dict):
      out.append("self_checks.yaml: a check is not a mapping")
      continue
    if c.get("id") in seen:
      out.append(f"self_checks.yaml: {c.get('id')} appears twice")
    seen.add(c.get("id"))
    out += check_problems(c)
    
  try:
    re.compile(str(doc.get("placeholder_marks") or ""))
  except re.error:
    out.append("self_checks.yaml: placeholder_marks is not a regular expression")
  if not doc.get("placeholder_marks"):
    out.append("self_checks.yaml: placeholder_marks must name the marks the reader makes up, so they are not compared")
  units = doc.get("units")
  if not isinstance(units, dict) or not all(isinstance(v, dict) and all(_num(x) and x > 0 for x in v.values()) for v in units.values()):
    out.append("self_checks.yaml: units must map a unit to the units that convert into it, each by a number above 0")
  else:
    for c in checks:
      cmp_ = c.get("compares") or {}
      for side in ("top", "bottom", "left"):
        to = (cmp_.get(side) or {}).get("to") if cmp_.get("kind") in LEDGER_KINDS else None
        if to and to not in units:
          out.append(f"self_checks.yaml: {c.get('id')} converts to {to}, which has no conversion table")
  return out

def placeholder():
  return re.compile(str(_load().get("placeholder_marks") or "$^"))

def checks() -> list:
  bad = problems()
  if bad:
    raise ValueError("; ".join(bad[:3]))
  return list(_load()["checks"])

def units() -> dict:
  return dict(_load().get("units") or {})

def read_classes() -> set:
  out: set = set()
  for c in checks():
    cmp_ = c["compares"]
    if cmp_["kind"] in READ_KINDS:
      out |= _side_classes(cmp_["left"]) | _side_classes(cmp_["right"])
  return out

def read_fields() -> set:
  out: set = set()
  for c in checks():
    cmp_ = c["compares"]
    if cmp_["kind"] in READ_KINDS:
      out |= {s["field"] for s in (cmp_["left"], cmp_["right"]) if s.get("field")}
  return out
