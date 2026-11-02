from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import identity_words as IW
from app.modules.drawings_boq.takeoff.prep import title_block as TB

SPARSE_WORDS = 8
CODE_RX = re.compile(r"^([A-Z]{1,4})\s?-?\s?(\d{1,3})[A-Z]?$")
CODE_STRONG = {"EL": "ELECTRICAL", "ELE": "ELECTRICAL", "PH": "PLUMBING", "PL": "PLUMBING", "PLB": "PLUMBING", "SAN": "PLUMBING", "HV": "HVAC", "HVAC": "HVAC", "FP": "FIRE",
  "AD": "ARCHITECTURAL", "AR": "ARCHITECTURAL", "ARCH": "ARCHITECTURAL", "ST": "STRUCTURAL", "STR": "STRUCTURAL"}
CODE_WEAK = {"E": "ELECTRICAL"}   
GROUPS = {"ELECTRICAL": "E", "PLUMBING": "W", "GAS": "W", "HVAC": "H", "FIRE": "F"}
CONF_BOTH, CONF_ONE = 0.9, 0.75
BASES = ("SECTION", "SHEET_CODE", "SECTION_AND_CODE")
NOT_A_PLAN_ROLES = ("COVER", "DIVIDER")
HEADING_ROLES = ("SECTION", "ELEVATION", "DETAIL", "SCHEDULE", "LEGEND", "SPEC")   
DETAIL_ROLES = ("DETAIL", "SECTION", "SCHEDULE", "ELEVATION")   

def code_of(words: list, cropbox: tuple) -> str | None:
  found: dict = {}
  for w in TB.zone_words(words, cropbox):
    m = CODE_RX.match(str(w.text).strip().upper())
    if m and (m.group(1) in CODE_STRONG or m.group(1) in CODE_WEAK):
      found.setdefault(m.group(1), str(w.text).strip().upper())
  return next(iter(found.values())) if len(found) == 1 else None

def _prefix(code: str | None) -> str | None:
  m = CODE_RX.match(code or "")
  return m.group(1) if m else None

def code_discipline(code: str | None) -> tuple:
  p = _prefix(code)
  if p in CODE_STRONG:
    return CODE_STRONG[p], True
  if p in CODE_WEAK:
    return CODE_WEAK[p], False
  return None, False

def is_divider(identity: dict) -> bool:
  return identity.get("role") in ("DIVIDER", "COVER") or bool(identity.get("sparse"))

def _same_group(a: str | None, b: str | None) -> bool:
  return a is not None and b is not None and (a == b or (a in GROUPS and GROUPS.get(a) == GROUPS.get(b)))

def settle(section: str | None, code: str | None, own: str | None, named: bool) -> tuple:
  by_code, strong = code_discipline(code)
  if by_code and not strong and not _same_group(by_code, section):
    by_code = None
  if section is None and by_code is None:
    return None
  if section and by_code and not _same_group(section, by_code):
    return None
  if named and own and not _same_group(own, section or by_code) and not (section and by_code):
    return None
  if section and by_code:
    return (section if section == by_code else by_code), "SECTION_AND_CODE", CONF_BOTH, f"under the divider for {section.lower()} and numbered {code}"
  if section:
    return section, "SECTION", CONF_ONE, f"under the divider for {section.lower()}"
  return by_code, "SHEET_CODE", CONF_ONE, f"numbered {code}"

def apply(sheets: list) -> list:
  from app.modules.drawings_boq.takeoff.extract import sheet_identity as SID
  from app.modules.drawings_boq.takeoff.extract import config as C
  from app.modules.drawings_boq.takeoff.extract import note_scope as NS
  from app.modules.drawings_boq.takeoff.prep import page_role as PRL
  
  changed: list = []
  section, since = None, None
  for page, identity in sorted(((p, i) for p, i in sheets if i), key=lambda x: x[0]):
    if is_divider(identity):
      d = identity.get("discipline")
      section, since = (d, page) if d else (None, None)
      continue
    if identity.get("basis") == "PERSON":
      continue
    got = settle(section, identity.get("sheet_code"), identity.get("discipline"), bool(identity.get("named")))
    
    if got is None:
      continue
    discipline, basis, confidence, why = got
    own = identity.get("discipline")
    if own == discipline and identity.get("basis") in BASES:
      continue
    if discipline not in IW.SERVICES and own:
      continue
  
    was = {"discipline": own, "read_as": identity.get("read_as"), "plan_kind": identity.get("plan_kind")}
    identity["discipline"], identity["basis"], identity["confidence"] = discipline, basis, confidence
    identity["evidence"] = [{"discipline": discipline, "text": why, "matched": basis}] + [e for e in identity.get("evidence") or [] if e.get("sheet_type")]
    if section:
      identity["section"] = {"discipline": section, "page": since}
    if identity.get("role") in DETAIL_ROLES:
      changed.append({"page": page, "was": was, "now": {"discipline": discipline, "read_as": identity.get("read_as"), "plan_kind": identity.get("plan_kind")}, "basis": basis, "why": why})
      continue
  
    if discipline in IW.SERVICES and identity.get("sheet_type") in IW.PLAN_TYPES:
      role = {"role": identity.get("role"), "title": identity.get("role_title")}
      identity["plan_kind"] = SID.plan_kind(identity, role, None)
    elif discipline in IW.SERVICES and identity.get("plan_kind") in ("WORKING", "FURNITURE"):
      identity["plan_kind"] = None
    if not (identity.get("role_vote") or {}).get("read_as"):
      PRL.apply(identity, [PRL.title_block_signal(identity, SID.read_view)])
    identity["read_as"] = SID.read_as(identity)
    changed.append({"page": page, "was": was, "now": {"discipline": discipline, "read_as": identity["read_as"], "plan_kind": identity.get("plan_kind")}, "basis": basis, "why": why})
  changed.extend(furniture_pass(sheets))
  changed.extend(detail_pass(sheets))
  return changed

def _floor(identity: dict) -> str | None:
  from app.modules.drawings_boq.takeoff.extract import sheet_identity as SID
  return identity.get("floor") or SID._level_of([x for x in (identity.get("title"), identity.get("role_title")) if x])

def furniture_pass(sheets: list) -> list:
  working: dict = {}
  for page, i in sorted(((p, i) for p, i in sheets if i), key=lambda x: x[0]):
    if i.get("plan_kind") == "WORKING" and i.get("purpose") != "FURNITURE" and i.get("read_as") == "PLAN_ITEMS" and _floor(i):
      working.setdefault(_floor(i), page)
      
  changed: list = []
  for page, i in sorted(((p, i) for p, i in sheets if i), key=lambda x: x[0]):
    floor = _floor(i)
    if i.get("basis") == "PERSON" or i.get("read_as") != "PLAN_ITEMS" or not floor or floor not in working or working[floor] == page:
      continue
    if i.get("plan_kind") != "FURNITURE" and i.get("purpose") != "FURNITURE":
      continue
  
    was = {"discipline": i.get("discipline"), "read_as": i.get("read_as"), "plan_kind": i.get("plan_kind")}
    i["plan_kind"], i["duplicate_of"] = "FURNITURE", {"page": working[floor], "floor": floor, "why": "furniture layout of a floor that has a working plan"}
    i["read_as"] = "SYMBOLS_ONLY"
    changed.append({"page": page, "was": was, "now": {"discipline": i.get("discipline"), "read_as": "SYMBOLS_ONLY", "plan_kind": "FURNITURE"}, "basis": "FURNITURE_OF_WORKING_PLAN", "why": i["duplicate_of"]["why"]})
  return changed

def detail_pass(sheets: list) -> list:
  changed: list = []
  for page, i in sorted(((p, i) for p, i in sheets if i), key=lambda x: x[0]):
    if i.get("basis") == "PERSON" or i.get("role") not in DETAIL_ROLES or i.get("read_as") != "SYMBOLS_ONLY" or _floor(i):
      continue
    if any(v.get("sheet_type") in IW.PLAN_TYPES for v in i.get("views") or []):
      continue
  
    was = {"discipline": i.get("discipline"), "read_as": i.get("read_as"), "plan_kind": i.get("plan_kind")}
    i["read_as"] = "DETAILS_ONLY"
    changed.append({"page": page, "was": was, "now": {"discipline": i.get("discipline"), "read_as": "DETAILS_ONLY", "plan_kind": i.get("plan_kind")}, "basis": "DETAIL_SHEET", "why": "a detail sheet with no plan on it"})
  return changed

SCALE_CODES = ("SCALE_NOT_FOUND", "SCALE_NEEDS_CONFIRMATION")

def scale_not_needed(identity: dict | None) -> tuple | None:
  i = identity or {}
  if i.get("basis") == "PERSON":
    return None
  if i.get("read_as") == "SKIP":
    return ("NOTHING_TO_MEASURE", "INFO", "This sheet has pictures, notes or a legend and nothing measured to scale. It needs no scale.")
  if i.get("duplicate_of"):
    floor = str(i["duplicate_of"].get("floor") or _floor(i) or "").lower()
    return ("FURNITURE_COPY", "INFO", f"This is the furniture layout of the {floor + ' ' if floor else ''}floor, which is read from sheet {i['duplicate_of'].get('page')}. It needs no scale.")
  if i.get("read_as") == "DETAILS_ONLY":
    return ("DETAIL_SIZES_ONLY", "INFO", "This detail sheet is used for the sizes it prints; nothing on it is measured to scale.")
  return None

def not_a_plan(identity: dict | None) -> tuple | None:
  i = identity or {}
  if i.get("basis") == "PERSON" or i.get("read_as") not in ("SKIP", "DETAILS_ONLY"):
    return None
  if i.get("role") in NOT_A_PLAN_ROLES or (i.get("sparse") and i.get("role") in HEADING_ROLES):
    return ("NOT_A_PLAN", "INFO", "This sheet is a cover or a divider (a title and little else). It has nothing to measure and needs no scale.")
  return None
