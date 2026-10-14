from __future__ import annotations
import re
from collections import Counter

MM_INCH = 25.4
MM_FOOT = 304.8
_FRACTIONS = {"½": " 1/2", "¼": " 1/4", "¾": " 3/4", "⅛": " 1/8", "⅜": " 3/8", "⅝": " 5/8", "⅞": " 7/8"}
MAX_ITEMS_PER_SHEET = 60
MAX_LEVEL_MM = 120000.0
MIN_LEVEL_REPEATS = 2

_IN = r"(?P<in>\d{1,3}(?:\s+\d{1,2}/\d{1,2}|\s*/\s*\d{1,2})?)\s*(?:\"|″|”|'')"
_SLAB_THICK = re.compile(_IN + r"\s*THICK\s+(?:R\.?\s?C\.?\s?C\.?\s+)?SLAB", re.I)
_SLAB_NOTE = re.compile(r"(?P<scope>[A-Z][A-Z ]*?)\bSLABS?\s+(?:ARE|IS)\s+" + _IN + r"\s*THICK", re.I)
_WALL_THICK = re.compile(_IN + r"\s*THICK\s+R\.?\s?C\.?\s?C\.?\s+WALL", re.I)
_BRICK_COLUMN = re.compile(r"BRICK\s+COLUMNS?\s+(?P<a>\d{1,2})\s*(?:\"|″|”)?\s*[X×]\s*(?P<b>\d{1,2})\s*(?:\"|″|”)?", re.I)
_STEEL = re.compile(r"\bG\s*-?\s*(?P<grade>40|60|75)\b\s+DEFORMED\s+STEEL\s+FOR\s+(?P<scope>.+)$", re.I)
_CONCRETE = re.compile(r"CLASS\s+[\"“”']?(?P<cls>[A-D])[\"“”']?\s*\((?P<mix>[\d.]+\s*:\s*[\d.]+(?:\s*1/2)?\s*:\s*[\d.]+)\)\s*CONCRETE\s*(?:IN\s+)?(?P<scope>.*)$", re.I)
_COVER = re.compile(r"\(\s*[a-f]\s*\)\s*(?P<member>SLABS?|BEAMS?|COLUMNS?|FOOTINGS?|WALLS?)\s+" + _IN + r"\s*(?P<where>[A-Z ]*)", re.I)
_BEARING = re.compile(r"BEARING\s+CAPACITY[^0-9]{0,40}(?P<v>\d+(?:\.\d+)?)\s*(?P<u>TSF|KSF|PSF|PSI|KN\s*/\s*M2|KPA)", re.I)
_PLASTER = re.compile(_IN + r"\s*TH\.?\s*C\.?\s?M\.?\s*PLASTER", re.I)
_FILL_LAYER = re.compile(_IN + r"\s*THICK\s+COMPACTED\s+LAYERS", re.I)
_STAIR_WIDTH = re.compile(r"STAIR\s+WIDTH\s*=\s*(?P<ft>\d+)\s*'\s*-?\s*(?P<in>\d+)?", re.I)
_LEVEL = re.compile(r"^\s*(?P<sign>[+\-±]|\+/-)\s*(?P<ft>\d{1,3})\s*'\s*-?\s*(?P<in>\d{1,2}(?:\s+\d/\d)?)?\s*(?:\"|″|”|'')?\s*$")

SINGLE_VALUE = {"SLAB_THICKNESS": "slab thickness", "BEARING_CAPACITY": "soil bearing capacity", "RCC_WALL_THICKNESS": "RCC wall thickness"}

def _fix(text: str) -> str:
  s = text
  for k, v in _FRACTIONS.items():
    s = s.replace(k, v)
  return re.sub(r"\s+", " ", s).strip()

def inches_mm(s: str) -> float | None:
  """'6' -> 152.4, '1 1/2' -> 38.1, '3/4' -> 19.05."""
  s = (s or "").strip()
  m = re.fullmatch(r"(\d{1,3})(?:\s+(\d{1,2})\s*/\s*(\d{1,2}))?", s)
  if m:
    whole = float(m.group(1))
    if m.group(2):
      if int(m.group(3)) == 0:
        return None
      whole += int(m.group(2)) / int(m.group(3))
    return round(whole * MM_INCH, 2)
  m = re.fullmatch(r"(\d{1,2})\s*/\s*(\d{1,2})", s)
  if m and int(m.group(2)) != 0:
    return round(int(m.group(1)) / int(m.group(2)) * MM_INCH, 2)
  return None

def _clean_scope(s: str) -> str:
  s = re.sub(r"[^A-Za-z0-9,/&\- ]+", " ", s or "")
  s = re.sub(r"\s*,\s*", ", ", s)
  return re.sub(r"\s+", " ", s).strip(" ,-").lower()[:80]

def _item(kind: str, text: str, **extra) -> dict:
  return {"kind": kind, "text": text[:140], **extra}

def read_line(text: str) -> list[dict]:
  """The facts one line of drawing text states. Most lines state none."""
  t = _fix(text)
  if len(t) < 6:
    return []
  out: list[dict] = []
  m = _SLAB_THICK.search(t)
  if m and inches_mm(m.group("in")):
    out.append(_item("SLAB_THICKNESS", t, value_mm=inches_mm(m.group("in")), scope="slab"))
  else:
    m = _SLAB_NOTE.search(t)
    if m and inches_mm(m.group("in")):
      scope = _clean_scope(m.group("scope"))
      scope = re.sub(r"^(?:all|\*)\s*", "all ", scope).strip() or "all"
      out.append(_item("SLAB_THICKNESS", t, value_mm=inches_mm(m.group("in")), scope=("all slabs" if scope in ("all", "") else scope + " slab")))
  m = _WALL_THICK.search(t)
  if m and inches_mm(m.group("in")):
    out.append(_item("RCC_WALL_THICKNESS", t, value_mm=inches_mm(m.group("in")), scope="rcc wall"))
  m = _BRICK_COLUMN.search(t)
  if m:
    out.append(_item("BRICK_COLUMN", t, value_mm=round(int(m.group("a")) * MM_INCH, 2), value2_mm=round(int(m.group("b")) * MM_INCH, 2), scope="brick column"))
  m = _STEEL.search(t)
  if m:
    out.append(_item("STEEL_GRADE", t, grade=int(m.group("grade")), scope=_clean_scope(m.group("scope"))))
  m = _CONCRETE.search(t)
  if m:
    mix = re.sub(r"\s+", "", m.group("mix")).replace("1/2", ".5")
    out.append(_item("CONCRETE_CLASS", t, concrete_class=m.group("cls").upper(), mix=mix, scope=_clean_scope(m.group("scope"))))
  m = _COVER.search(t)
  if m and inches_mm(m.group("in")):
    member = m.group("member").lower().rstrip("s")
    out.append(_item("CLEAR_COVER", t, value_mm=inches_mm(m.group("in")), scope=member, where=_clean_scope(m.group("where"))))
  m = _BEARING.search(t)
  
  if m:
    out.append(_item("BEARING_CAPACITY", t, value=float(m.group("v")), unit=re.sub(r"\s+", "", m.group("u")).upper(), scope="soil"))
  m = _PLASTER.search(t)
  if m and inches_mm(m.group("in")):
    out.append(_item("PLASTER_THICKNESS", t, value_mm=inches_mm(m.group("in")), scope="cement mortar plaster"))
  m = _FILL_LAYER.search(t)
  if m and inches_mm(m.group("in")):
    out.append(_item("FILL_LAYER", t, value_mm=inches_mm(m.group("in")), scope="compacted fill layer"))
  m = _STAIR_WIDTH.search(t)
  if m:
    out.append(_item("STAIR_WIDTH", t, value_mm=round(int(m.group("ft")) * MM_FOOT + int(m.group("in") or 0) * MM_INCH, 2), scope="stair"))
  return out

def level_mark_mm(text: str) -> float | None:
  """A bare level mark such as +3'-6", +14'-0" or ±0'-0", in millimetres above the datum. Anything else on the line makes it not a bare mark."""
  m = _LEVEL.match(_fix(text))
  if not m:
    return None
  inch = inches_mm(m.group("in")) if m.group("in") else 0.0
  if inch is None:
    return None
  mm = int(m.group("ft")) * MM_FOOT + inch
  if mm > MAX_LEVEL_MM:
    return None
  return round(-mm if m.group("sign") == "-" else mm, 1)

def read_facts(lines: list, words: list | None = None) -> dict:
  """Facts and level marks from one sheet's text lines. Counts repeats, so a note printed on every view is one fact seen many times.
  With the sheet's words, the storey heights printed on a building section are read as well."""
  seen: dict = {}
  marks: Counter = Counter()
  for ln in lines:
    text = getattr(ln, "text", ln)
    lvl = level_mark_mm(text)
    if lvl is not None:
      marks[lvl] += 1
      continue
  
    for it in read_line(text):
      key = (it["kind"], it.get("scope"), it.get("value_mm"), it.get("value"), it.get("grade"), it.get("concrete_class"), it.get("mix"), it.get("where"))
      if key in seen:
        seen[key]["count"] += 1
      elif len(seen) < MAX_ITEMS_PER_SHEET:
        seen[key] = {**it, "count": 1}
  out = {"items": list(seen.values()), "level_marks": [{"mm": k, "count": v} for k, v in sorted(marks.items())]}
  if words:
    from app.modules.drawings_boq.takeoff.prep.storeys import read_storeys
    found = read_storeys(words, lines)
    if found:
      out["storeys"] = found
  return out

def level_ladder(marks: list[dict]) -> dict:
  """The floor levels shown on the elevations and the height between each pair. A mark seen once may be a stray, so a level needs a repeat to count."""
  by_mm: Counter = Counter()
  
  for m in marks:
    by_mm[m["mm"]] += int(m.get("count", 1))
  levels = sorted(mm for mm, n in by_mm.items() if n >= MIN_LEVEL_REPEATS)
  gaps = [round(b - a, 1) for a, b in zip(levels, levels[1:])]
  typical = None
  if len(gaps) >= 2:
    common = Counter(round(g / 5.0) * 5.0 for g in gaps).most_common(1)[0]
    if common[1] >= 2:
      typical = round(sum(g for g in gaps if round(g / 5.0) * 5.0 == common[0]) / common[1], 1)
  return {"levels_mm": levels, "gaps_mm": gaps, "typical_floor_to_floor_mm": typical}

def suggest_wall_height(items: list, ladder: dict) -> dict | None:
  """A wall height to offer the estimator, never to apply on its own: the floor-to-floor height on the elevations minus the slab thickness
  in the notes. Where two slab thicknesses are printed, the more often printed one is offered and the other is listed beside it."""
  f2f = (ladder or {}).get("typical_floor_to_floor_mm")
  slabs: dict = {}
  for it in items:
    if it.get("kind") == "SLAB_THICKNESS" and it.get("value_mm"):
      row = slabs.setdefault(round(it["value_mm"], 1), {"slab_mm": round(it["value_mm"], 1), "count": 0, "pages": set()})
      row["count"] += int(it.get("count", 1))
      row["pages"].update(it.get("pages") or [])
  if not f2f or not slabs:
    return None
  ranked = sorted(slabs.values(), key=lambda r: (-r["count"], -r["slab_mm"]))
  top = ranked[0]
  out = {"value_mm": round(f2f - top["slab_mm"], 1), "floor_to_floor_mm": f2f, "slab_mm": top["slab_mm"], "basis": "FLOOR_TO_FLOOR_LESS_SLAB",
    "alternatives": [{"slab_mm": r["slab_mm"], "value_mm": round(f2f - r["slab_mm"], 1), "pages": sorted(r["pages"])} for r in ranked[1:4]]}
  if not 1500.0 <= out["value_mm"] <= 6500.0:
    return None
  return out

GENERIC_SLAB_SCOPES = ("slab", "all slabs")

def slab_values(items: list) -> list[dict]:
  """The slab thicknesses the drawing prints for slabs in general (a note "ALL SLABS ARE 5" THICK", a section label "6" Thick R.c.c Slab"),
  one row per distinct value: {"mm", "count", "pages", "scopes"}. Most often printed first. A slab named in a note of its own (a waist slab, a tank slab) is not general."""
  by: dict = {}
  
  for it in items or []:
    if it.get("kind") != "SLAB_THICKNESS" or not it.get("value_mm"):
      continue
    if (it.get("scope") or "slab") not in GENERIC_SLAB_SCOPES:
      continue
    row = by.setdefault(round(float(it["value_mm"]), 1), {"mm": round(float(it["value_mm"]), 1), "count": 0, "pages": set(), "scopes": set()})
    row["count"] += int(it.get("count", 1))
    row["pages"].update(it.get("pages") or [])
    row["scopes"].add(it.get("scope") or "slab")
  rows = sorted(by.values(), key=lambda r: (-r["count"], r["mm"]))
  return [{"mm": r["mm"], "count": r["count"], "pages": sorted(r["pages"]), "scopes": sorted(r["scopes"])} for r in rows]

FLOOR_ORDER = ("BASEMENT", "GROUND", "FIRST", "SECOND", "THIRD", "FOURTH", "ROOF")

def floor_heights(floor_keys: list, ladder: dict, slab_mm: float | None) -> dict:
  """The clear wall height offered for each floor: the gap between its level mark and the next one up, less the slab. The floors above the ground
  take the top level marks in order (the last mark is the roof of the top floor); a floor below the ground has no mark and takes the typical
  floor-to-floor height. Nothing is offered without a slab thickness."""
  if not slab_mm:
    return {}
  keys = [k for k in FLOOR_ORDER if k in floor_keys]
  above = [k for k in keys if k != "BASEMENT"]
  levels = (ladder or {}).get("levels_mm") or []
  typical = (ladder or {}).get("typical_floor_to_floor_mm")
  out: dict = {}
  if above and len(levels) >= len(above) + 1:
    marks = levels[-(len(above) + 1):]
    for i, k in enumerate(above):
      gap = marks[i + 1] - marks[i]
      if 1500.0 <= gap - slab_mm <= 6500.0:
        out[k] = {"clear_mm": round(gap - slab_mm, 1), "floor_to_floor_mm": round(gap, 1), "basis": "LEVEL_MARKS"}
  for k in keys:
    if k not in out and typical and 1500.0 <= typical - slab_mm <= 6500.0:
      out[k] = {"clear_mm": round(typical - slab_mm, 1), "floor_to_floor_mm": typical, "basis": "TYPICAL"}
  return out

def gather(sheets: list[dict]) -> dict:
  """All sheets' facts together. Each sheet is {"page_no", "label", "facts"}. The same fact on several sheets is one row with its pages.
  A fact that must be one number but is printed as two is returned under conflicts, so nobody builds a quantity on the wrong one."""
  rows: dict = {}
  marks: list = []
  
  storeys = None
  for sh in sheets:
    facts = sh.get("facts") or {}
    marks.extend(facts.get("level_marks") or [])
    got = facts.get("storeys")
    
    if got and (storeys is None or (got.get("consistent"), len(got.get("clusters") or [])) > (storeys.get("consistent"), len(storeys.get("clusters") or []))):
      storeys = {**got, "page_no": sh["page_no"]}
    for it in facts.get("items") or []:
      key = (it["kind"], it.get("scope"), it.get("value_mm"), it.get("value"), it.get("grade"), it.get("concrete_class"), it.get("mix"), it.get("where"))
      row = rows.get(key)
      
      if row is None:
        row = rows[key] = {**{k: v for k, v in it.items() if k != "count"}, "count": 0, "pages": []}
      row["count"] += int(it.get("count", 1))
      if sh["page_no"] not in row["pages"]:
        row["pages"].append(sh["page_no"])
        
  items = sorted(rows.values(), key=lambda r: (r["kind"], r.get("scope") or "", r.get("value_mm") or r.get("value") or 0))
  conflicts = []
  for kind, name in SINGLE_VALUE.items():
    mine = [r for r in items if r["kind"] == kind]
    by_value: dict = {}
    for r in mine:
      v = by_value.setdefault(r.get("value_mm", r.get("value")), {"value_mm": r.get("value_mm"), "value": r.get("value"), "unit": r.get("unit"), "scopes": [], "pages": [], "text": r["text"]})
      if r.get("scope") and r["scope"] not in v["scopes"]:
        v["scopes"].append(r["scope"])
      v["pages"] = sorted(set(v["pages"]) | set(r["pages"]))
    if len(by_value) > 1:
      conflicts.append({"kind": kind, "name": name, "values": list(by_value.values())})
  ladder = level_ladder(marks)
  return {"items": items, "conflicts": conflicts, "ladder": ladder, "storeys": storeys, "suggest": {"wall_height": suggest_wall_height(items, ladder)}}