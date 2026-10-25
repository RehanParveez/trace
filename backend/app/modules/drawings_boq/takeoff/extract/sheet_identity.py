from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import pageroles as PR
from app.modules.drawings_boq.takeoff.extract import identity_words as IW
from app.modules.drawings_boq.takeoff.prep import title_block as TB

HEADLINES = 6
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
  return {"discipline": discipline, "sheet_type": sheet_type, "floor": floor, "title": fields.get("title") or title.get("title"), "sheet_no": fields.get("sheet_no") or title.get("sheet_no"),
    "scale_text": fields.get("scale"), "revision": fields.get("revision"), "project": fields.get("project"), "basis": basis, "confidence": confidence,
    "evidence": [h for h in hits if h["discipline"] == discipline][:4] + ([{"sheet_type": sheet_type, "text": type_line[:60]}] if sheet_type and type_line else []),
    "views": found_views}

def gates_services(identity: dict | None) -> bool:
  i = identity or {}
  if i.get("basis") == "PERSON":
    return bool(i.get("discipline") in IW.SERVICES and i.get("sheet_type") in IW.PLAN_TYPES)
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
