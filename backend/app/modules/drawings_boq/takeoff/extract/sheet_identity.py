from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import pageroles as PR
from app.modules.drawings_boq.takeoff.extract import identity_words as IW
from app.modules.drawings_boq.takeoff.prep import title_block as TB

HEADLINES = 6
READ_AS = ("PLAN_ITEMS", "SYMBOLS_ONLY", "DETAILS_ONLY", "SKIP")
PLAN_KINDS = ("WORKING", "FURNITURE", "OVERLAY", "FRAMING", "FOUNDATION")
FLOOR_BASES = ("TITLE", "VIEW", "ORDER", "PERSON")
MIXED_DIMENSIONS = 10          
MIXED_ROOM_SIZES = 4
COVER_MAX_DRAWN = 200            
COVER_MAX_WORDS = 150
TITLE_OCR_BUDGET_S = 4.0
TOP_LINES = 3
MIN_LINE_CHARS = 4
REST_WEIGHT = 0.6
MIN_SCORE = 2.0
PAGE_MIN_LINES = 5
PAGE_DOMINANCE = 2.0
CONF_BASE, CONF_STEP, CONF_MAX, CONF_PAGE = 0.5, 0.1, 0.95, 0.72
LEVEL = (("BASEMENT", r"\bBASEMENT\b|\bLOWER\s+GROUND\b"), ("GROUND", r"\bGROUND\b|\bG\.?F\.?\b"), ("FIRST", r"\bFIRST\b|\b1ST\b"), ("SECOND", r"\bSECOND\b|\b2ND\b"),
  ("THIRD", r"\bTHIRD\b|\b3RD\b"), ("FOURTH", r"\bFOURTH\b|\b4TH\b"), ("MEZZANINE", r"\bMEZZANINE\b"), ("ROOF", r"\bROOF\b|\bTERRACE\b|\bMUMTY\b"),
  ("FOUNDATION", r"\bFOUNDATION\b|\bFOOTING\b"), ("TYPICAL", r"\bTYPICAL\b"))
_D = [(c, re.compile(p, re.I), s) for c, p, s in IW.DISCIPLINE_WORDS]
_T = [(c, re.compile(p, re.I)) for c, p in IW.SHEET_TYPE_WORDS]
_L = [(c, re.compile(p, re.I)) for c, p in LEVEL]
_SITE = re.compile(r"\bSITE\b", re.I)
GATE_TITLE, GATE_TEXT = 0.55, 0.7
_TITLE_LINE = re.compile(r"\b(?:PLANS?|POINTS?|LAYOUT)\s*$", re.I)
_NOISE = re.compile(r"[A-Za-z]{3,}")

def _lines(words: list) -> list:
  out = [(t, s) for t, s in PR._title_lines(words) if len(t.strip()) >= MIN_LINE_CHARS and _NOISE.search(t)]
  out.sort(key=lambda x: -x[1])
  return out

def _scores(lines: list) -> tuple:
  score: dict = {}
  hits: list = []
  top_strength: dict = {}

  for rank, (text, _s) in enumerate(lines):
    weight = 1.0 if rank < TOP_LINES or _TITLE_LINE.search(text) else REST_WEIGHT
    for code, rx, strength in _D:
      m = rx.search(text)
      if m:
        score[code] = score.get(code, 0.0) + strength * weight
        top_strength[code] = max(top_strength.get(code, 0), strength)
        hits.append({"discipline": code, "text": text[:60], "matched": m.group(0)[:30]})
  return score, hits, top_strength

def _page_services(words: list) -> dict:
  counted: dict = {}
  for text, _s in PR._title_lines(words):
    for code, rx, strength in _D:
      if code in IW.SERVICES and strength >= 2 and rx.search(text):
        counted[code] = counted.get(code, 0) + 1
  return counted

def _type_of(texts: list) -> tuple:
  for text in texts:
    for code, rx in _T:
      if rx.search(text):
        return code, text
  return None, None

_FLOOR_LINE = re.compile(r"\b(?:FLOORS?|PLANS?|LEVELS?|LAYOUTS?|POINTS?|STOREY|STORY|ROOF|SLAB|FOUNDATION|BASEMENT)\b", re.I)

def _level_of(texts: list) -> str | None:
  for text in texts:
    if not _FLOOR_LINE.search(text):
      continue
    for code, rx in _L:
      if rx.search(text):
        return code
  return None

def read_view(caption: str | None) -> dict:
  text = caption or ""
  score, _hits, _top = _scores([(text, 1.0)])
  ordered = sorted(score.items(), key=lambda kv: -kv[1])
  discipline = ordered[0][0] if ordered and ordered[0][1] >= MIN_SCORE else None
  sheet_type, _ = _type_of([text])
  return {"discipline": discipline, "sheet_type": sheet_type, "floor": _level_of([text])}

def identify(words: list, cropbox: tuple, title: dict | None = None, views: list | None = None) -> dict:
  title = title or {}
  headlines = _lines(words)[:HEADLINES]
  block = TB.read(_lines(TB.zone_words(words, cropbox)))
  fields = block["fields"]
  source = ([(fields["title"], 99.0)] if fields.get("title") else []) + headlines
  score, hits, top_strength = _scores(source)
  ordered = sorted(score.items(), key=lambda kv: -kv[1])
  discipline = ordered[0][0] if ordered and ordered[0][1] >= MIN_SCORE else None
  named = discipline is not None and top_strength.get(discipline, 0) >= 3
  basis = "TITLE_BLOCK" if discipline and fields.get("title") and any(h["discipline"] == discipline and h["text"] == fields["title"][:60] for h in hits) else "TITLE" if discipline else "NONE"
  confidence = round(min(CONF_MAX, CONF_BASE + CONF_STEP * (ordered[0][1] - (ordered[1][1] if len(ordered) > 1 else 0.0))), 2) if discipline else 0.0

  if not named:
    counted = _page_services(words)
    ranked = sorted(counted.items(), key=lambda kv: -kv[1])
    if ranked and ranked[0][1] >= PAGE_MIN_LINES and (len(ranked) == 1 or ranked[0][1] >= PAGE_DOMINANCE * ranked[1][1]):
      discipline, basis, confidence = ranked[0][0], "TEXT", CONF_PAGE
      hits = [{"discipline": discipline, "text": "words across the sheet", "matched": f"{ranked[0][1]} lines"}]
  type_texts = ([fields["title"]] if fields.get("title") else []) + [t for t, _s in headlines]

  sheet_type, type_line = _type_of(type_texts)
  floor = _level_of(type_texts) or title.get("level_hint")
  if sheet_type is None and discipline in IW.SERVICES and _page_services(words).get(discipline, 0) >= PAGE_MIN_LINES:
    sheet_type, type_line = "PLAN", "many lines of the sheet carry its words"
  found_views = []
  for v in views or []:
    found_views.append({"key": v.get("key"), "caption": v.get("caption"), "scale_text": v.get("scale_text"), **read_view(v.get("caption"))})
  every = [t for t, _s in _lines(words)]
  return {"discipline": discipline, "sheet_type": sheet_type, "floor": floor, "title": fields.get("title") or title.get("title"), "sheet_no": fields.get("sheet_no") or title.get("sheet_no"),
    "scale_text": fields.get("scale"), "revision": fields.get("revision"), "project": fields.get("project"), "basis": basis, "confidence": confidence,
    "option": TB.option_of(every), "stamps": TB.stamps_of(every),
    "evidence": [h for h in hits if h["discipline"] == discipline][:4] + ([{"sheet_type": sheet_type, "text": type_line[:60]}] if sheet_type and type_line else []),
    "views": found_views}

_FRAMING = re.compile(r"\b(?:BEAMS?|SLABS?|FRAMING)\b|\bROOF\s+PLAN\b", re.I)
_FOUNDATION = re.compile(r"\bFOUNDATIONS?\b|\bFOOTINGS?\b", re.I)
_FURNITURE = re.compile(r"\bFURNITURE\b", re.I)

def _services_plan(i: dict, clues: dict | None = None) -> bool:
  """A plan of the services: a service discipline and a plan title; or, when no title says what the sheet is, a confidently named service discipline and a drawing with sized rooms."""
  if i.get("discipline") not in IW.SERVICES:
    return False
  if i.get("sheet_type") in IW.PLAN_TYPES:
    return True
  need = GATE_TEXT if i.get("basis") == "TEXT" else GATE_TITLE
  return i.get("sheet_type") is None and i.get("basis") != "PERSON" and float(i.get("confidence") or 0.0) >= need and int((clues or {}).get("room_sizes") or 0) >= MIXED_ROOM_SIZES

def plan_kind(identity: dict, role: dict | None = None, clues: dict | None = None) -> str | None:
  role = role or {}
  clues = clues or {}
  kind = role.get("role")
  title = " ".join(str(x) for x in (identity.get("title"), role.get("title")) if x)
  dense = int(clues.get("dim_pairs") or 0) >= MIXED_DIMENSIONS and int(clues.get("room_sizes") or 0) >= MIXED_ROOM_SIZES
  identity.pop("mixed", None)
  
  if _services_plan(identity, clues):
    if dense:
      identity["mixed"] = True
      return "WORKING"
    return "OVERLAY"
  if kind in ("SECTION", "ELEVATION", "DETAIL", "SCHEDULE", "LEGEND", "SPEC", "COVER", "DIVIDER", "SITE"):
    return None
  if _FOUNDATION.search(title):
    return "FOUNDATION"
  if (identity.get("discipline") == "STRUCTURAL" or kind == "STRUCTURAL") and _FRAMING.search(title):
    return "FRAMING"
  if role.get("purpose") == "FURNITURE" or _FURNITURE.search(title):
    return "FURNITURE"
  return "WORKING" if (role.get("purpose") == "WORKING" or dense) else None

def read_as(identity: dict | None) -> str:
  i = identity or {}
  if i.get("basis") == "PERSON":
    if i.get("read_as") in READ_AS:
      return i["read_as"]
    if i.get("sheet_type") in ("SECTION", "DETAIL", "SCHEDULE"):
      return "DETAILS_ONLY"
    if i.get("sheet_type") in ("LEGEND", "SPEC", "ELEVATION"):
      return "SKIP"
    return "SYMBOLS_ONLY" if gates_services(i) or is_electrical_plan(i) else "PLAN_ITEMS"

  if i.get("mixed"):
    return "PLAN_ITEMS"
  role = i.get("role")
  if (gates_services(i) or is_electrical_plan(i) or i.get("plan_kind") == "OVERLAY") and role not in ("COVER", "DIVIDER"):
    return "SYMBOLS_ONLY"
  if role in ("DETAIL", "SCHEDULE", "SECTION"):
    return "DETAILS_ONLY"
  if role == "SITE":
    return "SYMBOLS_ONLY"
  if role in PR.NOT_A_PLAN:
    return "SKIP"
  return "PLAN_ITEMS"

def refresh_person(identity: dict) -> dict:
  if "read_as" not in (identity.get("person_set") or []):
    identity["read_as"] = read_as({**identity, "read_as": None})
  return identity

def _floor_texts(identity: dict, words: list) -> list:
  headlines = [t for t, _s in _lines(words)[:HEADLINES]]
  return [x for x in ([identity.get("title")] + headlines + [identity.get("role_title")]) if x]

def _view_floor(views: list | None) -> str | None:
  plans = [v for v in views or [] if v.get("plan")]
  floors = [v.get("level_hint") or read_view(v.get("caption")).get("floor") for v in plans]
  return floors[0] if plans and all(floors) and len(set(floors)) == 1 else None

def floor_of(identity: dict, words: list, views: list | None = None, ocr_lines: list | None = None) -> tuple:
  key = _level_of(_floor_texts(identity, words))
  if key:
    return key, "TITLE"
  key = _view_floor(views if views is not None else identity.get("views"))
  if key:
    return key, "VIEW"
  if ocr_lines:
    key = _level_of([t for t, _s in sorted(ocr_lines, key=lambda x: -x[1])])
    if key:
      return key, "TITLE"
  return None, None

def wants_title_ocr(identity: dict | None) -> bool:
  i = identity or {}
  return bool(i) and i.get("basis") != "PERSON" and not i.get("floor") and not i.get("title") and i.get("role") in ("PLAN", "UNKNOWN", None) and i.get("read_as") in (None, "PLAN_ITEMS")

def _holds_floor_plans(views: list | None) -> bool:
  return any(v.get("plan") and (v.get("level_hint") or v.get("structural")) for v in views or [])

def complete(identity: dict | None, words: list, role: dict | None, views: list | None = None, clues: dict | None = None, composite: bool = False) -> dict | None:
  if not identity:
    return identity
  role = dict(role or {})
  if role.get("role") in ("SECTION", "ELEVATION", "DETAIL", "SCHEDULE", "SITE", "UNKNOWN", None) and _holds_floor_plans(views):
    role = {"role": "COMPOSITE", "title": role.get("title"), "also": [r for r in [role.get("role"), *(role.get("also") or [])] if r], "basis": "VIEWS", "purpose": role.get("purpose")}

  c = clues or {}
  if role.get("role") in ("PLAN", "STRUCTURAL", "UNKNOWN", None) and c.get("pdf_type") == "VECTOR_TEXT" and 0 <= int(c.get("drawn", -1)) < COVER_MAX_DRAWN and int(c.get("words") or 0) < COVER_MAX_WORDS       and not int(c.get("room_sizes") or 0) and not int(c.get("dim_pairs") or 0):
    role = {"role": "DIVIDER" if role.get("title") or identity.get("title") else "COVER", "title": role.get("title") or identity.get("title"), "also": [], "basis": "SPARSE_DRAWING"}
  identity["role"] = role.get("role")
  identity["role_title"] = (role.get("title") or "")[:80] or None
  identity["plan_kind"] = plan_kind(identity, role, clues)
  had = identity.get("floor")
  floor, basis = floor_of(identity, words, views if views is not None else identity.get("views"))

  if had:
    basis = "TITLE"
  elif floor:
    identity["floor"] = floor
  identity["floor_basis"] = basis if identity.get("floor") else None
  if composite or role.get("role") == "COMPOSITE":
    identity["floor"], identity["floor_basis"] = None, None
  identity["read_as"] = read_as(identity)
  return identity

def gates_services(identity: dict | None) -> bool:
  i = identity or {}
  if i.get("mixed"):
    return False
  if i.get("basis") == "PERSON":
    return bool(i.get("read_as") != "PLAN_ITEMS" and i.get("discipline") in IW.SERVICES and i.get("sheet_type") in IW.PLAN_TYPES)
  if i.get("discipline") not in IW.SERVICES or i.get("sheet_type") not in IW.PLAN_TYPES or _SITE.search(str(i.get("title") or "")):
    return False
  return float(i.get("confidence") or 0.0) >= (GATE_TEXT if i.get("basis") == "TEXT" else GATE_TITLE)

def is_electrical_plan(identity: dict | None) -> bool:
  i = identity or {}
  if i.get("discipline") != "ELECTRICAL" or i.get("sheet_type") not in IW.PLAN_TYPES:
    return False
  return i.get("basis") == "PERSON" or float(i.get("confidence") or 0.0) >= (GATE_TEXT if i.get("basis") == "TEXT" else GATE_TITLE)

def is_electrical_legend(identity: dict | None) -> bool:
  i = identity or {}
  return i.get("discipline") == "ELECTRICAL" and i.get("sheet_type") == "LEGEND" and (i.get("basis") == "PERSON" or float(i.get("confidence") or 0.0) >= GATE_TITLE)
