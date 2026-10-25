from __future__ import annotations
import hashlib
import math
import re
from app.engine.measure import proposed as QP
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.prep import texts as TX
from app.engine.measure import spec as SPEC

PILE_BORE = "PILE_BORE"
PILE_CONCRETE = "PILE_CONCRETE"
RAFT_SLAB = "RAFT_SLAB"
RAFT_PCC = "RAFT_PCC"
RAFT_EDGE_FORM = "RAFT_EDGE_FORM"
ITEMS = (PILE_BORE, PILE_CONCRETE, RAFT_SLAB, RAFT_PCC, RAFT_EDGE_FORM)
WORK_ITEM = {PILE_BORE: "PIL-BORE", PILE_CONCRETE: "CON-RCC", RAFT_SLAB: "CON-RCC", RAFT_PCC: "CON-PCC", RAFT_EDGE_FORM: "FRM-STRUCT"}
MODE = {PILE_BORE: "COUNT_X_LENGTH", PILE_CONCRETE: "COUNT_X_VOLUME", RAFT_SLAB: "COUNT_X_VOLUME", RAFT_PCC: "COUNT_X_VOLUME", RAFT_EDGE_FORM: "COUNT_X_AREA"}
TAG = {PILE_BORE: "PILE-BORE", PILE_CONCRETE: "PILE-CONCRETE", RAFT_SLAB: "RAFT-SLAB", RAFT_PCC: "RAFT-PCC", RAFT_EDGE_FORM: "RAFT-EDGE-FORM"}
FLOOR_ORDER = ("FOUNDATION", "BASEMENT", "GROUND", "MEZZANINE", "FIRST", "SECOND", "THIRD", "FOURTH", "TYPICAL", "ROOF")
MM_PER_INCH, MM_PER_FOOT = 25.4, 304.8

_NUM = r"(\d+(?:\.\d+)?)"
PILE_WORD = re.compile(r"\bPILES?\b", re.I)
RAFT_WORD = re.compile(r"\bRAFT\b|\bMAT\s+(?:FOUNDATION|FOOTING|SLAB)\b", re.I)
NOT_A_PILE_LINE = re.compile(r"\b(?:DETAIL|LEGEND|PILE\s*CAPS?|CAPS?)\b", re.I)
DIA_AFTER = re.compile(_NUM + r"\s*(mm|\"|”|″|in\b|inch(?:es)?)?\s*(?:DIA\b\.?|DIAMETER|Ø|⌀)", re.I)
DIA_BEFORE = re.compile(r"(?:DIA\b\.?|DIAMETER|Ø|⌀)\s*[:=]?\s*" + _NUM + r"\s*(mm|\"|”|″|in\b|inch(?:es)?)?", re.I)
LEN_AFTER = re.compile(_NUM + r"\s*(mm|m\b|mtrs?\b|meters?\b|metres?\b|ft\b|feet|')\s*(?:DEEP|LONG|LENGTH|DEPTH|LEN\b)", re.I)
LEN_BEFORE = re.compile(r"(?:LENGTH|DEPTH|LEN\b|L)\s*[:=]\s*" + _NUM + r"\s*(mm|m\b|mtrs?\b|meters?\b|metres?\b|ft\b|feet|')?", re.I)
COUNT_BEFORE = re.compile(r"(?<![\d.])(\d{1,4})\s*(?:NOS?\b\.?|NUMBERS?\b|X\b)", re.I)
COUNT_PILES = re.compile(r"(?<![\d.:])(\d{1,4})\s+(?:(?:NO\.?\s+)?(?:BORED|CAST|RCC|R\.C\.C|CONCRETE|DRIVEN|PRECAST)\b[A-Z\s\-\.]*?)?PILES?\b", re.I)
THICK_AFTER = re.compile(_NUM + r"\s*(mm|\"|”|″|in\b|inch(?:es)?)?\s*(?:THK\.?|THICK\b|THICKNESS|DEEP)", re.I)
THICK_BEFORE = re.compile(r"(?:THK\.?|THICKNESS|THICK\b)\s*[:=]?\s*" + _NUM + r"\s*(mm|\"|”|″|in\b|inch(?:es)?)?", re.I)
FT_IN = re.compile(r"(\d+)\s*'\s*-?\s*(\d+(?:\.\d+)?)?\s*(?:\"|”|″)?")
ROW_MARK = re.compile(r"^[A-Z]{1,3}\s?-?\s?\d{1,3}[A-Z]?$")
PILE_HEAD = re.compile(r"\bPILE\b|\bMARK\b|\bTYPE\b", re.I)

def _key_of(parts: tuple) -> str:
  return hashlib.sha1("|".join(str(p) for p in ("PRF", *parts)).encode()).hexdigest()[:24]

def _mm(value: float, unit: str | None, bare_is: str) -> tuple:
  """(mm, how): the figure in millimetres and how the unit was known (PRINTED, or ASSUMED where none is written)."""
  u = (unit or "").lower()
  if u in ("mm",):
    return value, "PRINTED"
  if u in ("m", "mtr", "mtrs", "meter", "meters", "metre", "metres"):
    return value * 1000.0, "PRINTED"
  if u in ("ft", "feet", "'"):
    return value * MM_PER_FOOT, "PRINTED"
  if u in ('"', "”", "″", "in", "inch", "inches"):
    return value * MM_PER_INCH, "PRINTED"
  if bare_is == "DIA":
    return (value, "ASSUMED") if value >= QP.BARE_FIGURE_INCHES_BELOW else (value * MM_PER_INCH, "ASSUMED")
  if bare_is == "THICK":
    return (value, "ASSUMED") if value >= QP.BARE_FIGURE_INCHES_BELOW else (value * MM_PER_INCH, "ASSUMED")
  return value * 1000.0, "ASSUMED"

def _find(patterns: tuple, text: str):
  for p in patterns:
    m = p.search(text)
    if m:
      return m
  return None

def parse_pile_text(text: str) -> dict | None:
  """The pile written in one line or note: {dia_mm, length_mm, count, how}; None when the diameter, the length or the number is not there."""
  if not PILE_WORD.search(text) or NOT_A_PILE_LINE.search(text):
    return None

  md = _find((DIA_AFTER, DIA_BEFORE), text)
  ml = _find((LEN_AFTER, LEN_BEFORE), text)
  mc = _find((COUNT_PILES, COUNT_BEFORE), text)
  if not (md and ml and mc):
    return None

  dia, d_how = _mm(float(md.group(1)), md.group(2), "DIA")
  length, l_how = _mm(float(ml.group(1)), ml.group(2), "LEN")
  count = int(mc.group(1))
  if not (150.0 <= dia <= 3000.0 and 1000.0 <= length <= 100000.0 and 1 <= count <= 5000):
    return None
  return {"dia_mm": round(dia, 1), "length_mm": round(length, 1), "count": count, "how": {"dia": d_how, "length": l_how}}

def parse_schedule(lines: list) -> list:
  out: list = []
  for i, ln in enumerate(lines):
    head = ln.text.upper()
    if not (PILE_HEAD.search(head) and re.search(r"\bDIA", head) and re.search(r"LENGTH|DEPTH|\bLEN\b", head) and re.search(r"\bNOS?\b|\bQTY\b|NUMBER", head)):
      continue
    order = sorted(((head.find(k), name) for k, name in (("DIA", "dia"), ("LENGTH", "length"), ("DEPTH", "length"), ("LEN", "length"), ("NOS", "count"), ("NO.", "count"), ("QTY", "count"), ("NUMBER", "count"))
      if head.find(k) >= 0), key=lambda t: t[0])
    cols: list = []
    for _, name in order:
      if name not in cols:
        cols.append(name)
    if len(cols) < 3:
      continue

    h_dia_unit = "mm" if re.search(r"DIA[^A-Z]{0,4}\(?\s*MM", head) else None
    h_len_unit = "m" if re.search(r"(?:LENGTH|DEPTH|LEN)[^A-Z]{0,4}\(?\s*M\b", head) else ("ft" if re.search(r"(?:LENGTH|DEPTH|LEN)[^A-Z]{0,4}\(?\s*(?:FT|')", head) else None)
    for row in lines[i + 1:i + 41]:
      toks = row.text.replace(",", " ").split()
      if not toks or not ROW_MARK.match(toks[0].upper()):
        break
      nums = [t for t in toks[1:] if re.match(r"^\d+(?:\.\d+)?(?:mm|m|ft|\"|')?$", t, re.I)]
      if len(nums) < 3:
        break

      vals = {name: nums[k] for k, name in enumerate(cols[:3])}
      dm = re.match(r"^(\d+(?:\.\d+)?)(mm|m|ft|\"|')?$", vals["dia"], re.I)
      lm = re.match(r"^(\d+(?:\.\d+)?)(mm|m|ft|\"|')?$", vals["length"], re.I)
      dia, d_how = _mm(float(dm.group(1)), dm.group(2) or h_dia_unit, "DIA")
      length, l_how = _mm(float(lm.group(1)), lm.group(2) or h_len_unit, "LEN")
      count = int(float(vals["count"]))
      if not (150.0 <= dia <= 3000.0 and 1000.0 <= length <= 100000.0 and 1 <= count <= 5000):
        continue
      x, y = row.locate(0, len(toks[0]))
      out.append({"mark": toks[0].upper(), "dia_mm": round(dia, 1), "length_mm": round(length, 1), "count": count, "how": {"dia": d_how, "length": l_how}, "point": (x, y)})
  return out

def raft_thickness(text: str) -> tuple | None:
  """(thickness_mm, how, grade): the thickness written with the word raft (not a tank's raft), and the grade printed beside it."""
  if not RAFT_WORD.search(text) or re.search(r"\bTANK\b|\bO\.?/?H\.?(?:W?T)?\b|\bUGWT\b|\bSUMP\b|\bSEPTIC\b", text, re.I):
    return None
  m = None if re.search(r"\d\s*'", text) else _find((THICK_AFTER, THICK_BEFORE), text)
  if m:
    mm, how = _mm(float(m.group(1)), m.group(2), "THICK")
  else:
    f = FT_IN.search(text)
    if not f:
      return None
    mm, how = int(f.group(1)) * MM_PER_FOOT + float(f.group(2) or 0.0) * MM_PER_INCH, "PRINTED"
  if not (150.0 <= mm <= 3000.0):
    return None
  return round(mm, 1), how, SPEC.concrete_grade(text)

def footprint(schedule: dict | None) -> tuple | None:
  """(length_mm, width_mm, floor): the covered-area outline of the lowest floor that has one."""
  rows = [a for a in ((schedule or {}).get("areas") or []) if a.get("kind") == "FLOOR" and a.get("dims_mm") and len(a["dims_mm"]) == 2]
  if not rows:
    return None
  rows.sort(key=lambda a: (FLOOR_ORDER.index(a.get("key")) if a.get("key") in FLOOR_ORDER else len(FLOOR_ORDER), str(a.get("key"))))
  d = rows[0]["dims_mm"]
  return float(d[0]), float(d[1]), rows[0].get("key")

def _make(cls, ctx: dict, finish, item: str, key_parts: tuple, label: str, point: tuple, params: dict, facts: dict, notes: list, base: float):
  cand = cls(key=_key_of((item, *key_parts)), category="WALL", kind="COUNT", quantity_mode=MODE[item], label=label, tag=TAG[item],
    geometry={"points": [[round(point[0], 3), round(point[1], 3)]]}, params={**params, "dims_basis": "SPECIFIED"}, missing=[], work_item=WORK_ITEM[item],
    status="VALID", confidence=0.0, facts={**facts, "foundation_item": item, "derived_from": "LABELS"}, notes=notes, source="TAG_SCAN", count=1)
  return finish(cand, ctx, base)

def pile_candidates(pile: dict, point: tuple, mark: str | None, ctx: dict, cls, finish) -> list:
  """Two items for a pile type: the boring (metres of pile) and the concrete (cubic metres). The count is in the total length, since a note gives no position for each pile."""
  n, length, dia = pile["count"], pile["length_mm"], pile["dia_mm"]
  side = dia * math.sqrt(math.pi) / 2.0
  facts = {"piles": n, "pile_length_mm": length, "pile_dia_mm": dia, "pile_mark": mark, "pile_units": pile["how"], "section": "CIRCULAR"}
  notes = [C.note("PILE_FROM_NOTE_OR_SCHEDULE"), C.note("PILE_CAPS_NOT_TAKEN")]
  if "ASSUMED" in pile["how"].values():
    notes.append(C.note("PILE_UNIT_ASSUMED", diameter_unit=pile["how"]["dia"], length_unit=pile["how"]["length"]))
  name = f"{mark + ' · ' if mark else ''}{dia:g} mm dia · {n} nos · {length / 1000.0:g} m each"
  key = (mark or "", dia, length, n)
  total = length * n

  return [
    _make(cls, ctx, finish, PILE_BORE, key, f"Boring of piles · {name} · {total / 1000.0:g} m", point, {"length_mm": round(total, 1)}, {**facts, "total_length_m": round(total / 1000.0, 3)}, list(notes), 0.65),
    _make(cls, ctx, finish, PILE_CONCRETE, key, f"Concrete in piles · {name}", point, {"length_mm": round(side, 3), "width_mm": round(side, 3), "depth_mm": round(total, 1)},
      {**facts, "equivalent_square_mm": round(side, 3)}, list(notes), 0.65)]

def raft_candidates(thickness: tuple, point: tuple, schedule: dict | None, ctx: dict, cls, finish) -> tuple:
  mm, how, grade = thickness
  fp = footprint(schedule)
  if fp is None:
    return [], [C.note("RAFT_FOOTPRINT_UNKNOWN", thickness_mm=mm)]

  length, width, floor = fp
  facts = {"raft_thickness_mm": mm, "raft_thickness_unit": how, "raft_grade": grade, "footprint_mm": [round(length, 1), round(width, 1)], "footprint_floor": floor}
  notes = [C.note("RAFT_FOOTPRINT_FROM_AREA_TABLE", floor=floor), C.note("RAFT_STEEL_NOT_TAKEN")]
  if how == "ASSUMED":
    notes.append(C.note("RAFT_UNIT_ASSUMED"))
  area = length * width / 1e6
  perimeter = 2.0 * (length + width)
  key = (round(length), round(width), mm)

  return [
    _make(cls, ctx, finish, RAFT_SLAB, key, f"Raft slab · {mm:g} mm thick{' · ' + grade if grade else ''} · {area:.2f} m²", point, {"length_mm": length, "width_mm": width, "depth_mm": mm}, facts, list(notes), 0.6),
    _make(cls, ctx, finish, RAFT_PCC, key, f"Concrete bed under the raft · {QP.RAFT_PCC_MM:g} mm · {area:.2f} m²", point, {"length_mm": length, "width_mm": width, "depth_mm": QP.RAFT_PCC_MM},
      {**facts, "pcc_thickness_mm": QP.RAFT_PCC_MM}, [*notes, C.note("RAFT_PCC_ASSUMED")], 0.55),
    _make(cls, ctx, finish, RAFT_EDGE_FORM, key, f"Shuttering to the raft edge · {perimeter / 1000.0:.2f} m × {mm:g} mm", point, {"length_mm": round(perimeter, 1), "width_mm": mm},
      {**facts, "perimeter_mm": round(perimeter, 1)}, [*notes, C.note("RAFT_EDGE_FORM_ASSUMED")], 0.55)], []

def candidates(words: list, schedule: dict | None, ctx: dict, cls, finish) -> tuple:
  if not words:
    return [], []
  lines = TX.build_lines(words)
  out: list = []
  notes: list = []
  seen: set = set()

  scheduled = parse_schedule(lines)
  for row in scheduled:
    seen.add((row["dia_mm"], row["length_mm"], row["count"]))
    out.extend(pile_candidates(row, row["point"], row["mark"], ctx, cls, finish))
  unread = 0
  for ln in lines:
    if PILE_WORD.search(ln.text) and not NOT_A_PILE_LINE.search(ln.text):
      pile = parse_pile_text(ln.text)
      if pile is None:
        if re.search(r"\d", ln.text) and not re.search(r"\bDIA\b.*\bLENGTH\b|\bMARK\b", ln.text, re.I):
          unread += 1
        continue

      if (pile["dia_mm"], pile["length_mm"], pile["count"]) in seen:
        continue
      seen.add((pile["dia_mm"], pile["length_mm"], pile["count"]))
      x, y = ln.locate(0, len(ln.text))
      out.extend(pile_candidates(pile, (x, y), None, ctx, cls, finish))
  if unread and not out:
    notes.append(C.note("PILES_NOT_READ", lines=unread))
  for k, ln in enumerate(lines):
    t = raft_thickness(ln.text)
    if t is None and RAFT_WORD.search(ln.text) and k + 1 < len(lines):
      t = raft_thickness(ln.text + " " + lines[k + 1].text)
    if t is not None:
      x, y = ln.locate(0, len(ln.text))
      items, rn = raft_candidates(t, (x, y), schedule, ctx, cls, finish)
      out.extend(items)
      notes.extend(rn)
      break
  return out, notes
