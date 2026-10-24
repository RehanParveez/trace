from __future__ import annotations
import hashlib
import re
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.prep import texts as TX

RAIN_PIPE = "RAIN_PIPE"
SEWER_PIPE = "SEWER_PIPE"
MANHOLE = "DRAIN_MANHOLE"
INSPECTION_CHAMBER = "INSPECTION_CHAMBER"
GULLY_TRAP = "GULLY_TRAP"
ITEMS = (RAIN_PIPE, SEWER_PIPE, MANHOLE, INSPECTION_CHAMBER, GULLY_TRAP)
WORK_ITEM = {RAIN_PIPE: "DRN-RWP", SEWER_PIPE: "DRN-SEWER", MANHOLE: "DRN-MANHOLE", INSPECTION_CHAMBER: "DRN-CHAMBER", GULLY_TRAP: "DRN-GULLY"}
MODE = {RAIN_PIPE: "COUNT_X_LENGTH", SEWER_PIPE: "COUNT_X_LENGTH", MANHOLE: "DIRECT", INSPECTION_CHAMBER: "DIRECT", GULLY_TRAP: "DIRECT"}
TAG = {RAIN_PIPE: "RAIN-PIPE", SEWER_PIPE: "SEWER-PIPE", MANHOLE: "DRAIN-MANHOLE", INSPECTION_CHAMBER: "INSPECTION-CHAMBER", GULLY_TRAP: "GULLY-TRAP"}

TYPED_FIELD = {RAIN_PIPE: "rain_pipe_length_mm", SEWER_PIPE: "sewer_length_mm"}
WORDS = {RAIN_PIPE: "the length of one rain water pipe (roof to ground)", SEWER_PIPE: "the total length of the sewer pipe line"}
TOP_FLOOR, BOTTOM_FLOOR = "ROOF", "GROUND"
SAME_PLACE_PT = 3.0

RAIN_LABEL = re.compile(r"(?<![A-Za-z])(?:RAIN\s*WATER\s*(?:DOWN\s*)?PIPES?|R\.?W\.?P)(?![A-Za-z])", re.I)
SEWER_LABEL = re.compile(r"(?<![A-Za-z])(?:S\s?/\s?PIPE|SEWER(?:AGE)?\s+PIPE)(?![A-Za-z])", re.I)
NOT_A_LABEL = re.compile(r"\b(?:DETAIL|TYPICAL|SCHEDULE|LEGEND|NOTES?)\b", re.I)
DIAMETER = re.compile(r"(\d+(?:\.\d+)?)\s*(?:\"|\u201d|\u2033|'')")
DRAIN_SHEET = re.compile(r"\b(?:SEWER|SEWERAGE|DRAINAGE|MAN\s?HOLE|INSPECTION\s+CHAMBER|GULLY|SEPTIC|RAIN\s*WATER)\b", re.I)

CHAMBER_TAGS = ((MANHOLE, re.compile(r"^M\.?H\.?(?:[-.]?(\d{1,3}[A-Z]?))?$", re.I), "MH", "Manholes"),
  (INSPECTION_CHAMBER, re.compile(r"^I\.?C\.?(?:[-.]?(\d{1,3}[A-Z]?))?$", re.I), "IC", "Inspection chambers"),
  (GULLY_TRAP, re.compile(r"^G\.?T\.?(?:[-.]?(\d{1,3}[A-Z]?))?$", re.I), "GT", "Gully traps"))

def field_of(need: str) -> tuple | None:
  return None if need != "length_mm" else ("length_mm",)

def drop_mm(floor_heights: dict | None) -> dict | None:
  fh = floor_heights or {}
  top = (fh.get(TOP_FLOOR) or {}).get("level_mm")
  bottom = (fh.get(BOTTOM_FLOOR) or {}).get("level_mm")
  if top is None or bottom is None or float(top) <= float(bottom):
    return None
  return {"top_mm": float(top), "bottom_mm": float(bottom), "drop_mm": round(float(top) - float(bottom), 1)}

def _inches(text: str, before: int) -> float | None:
  for m in DIAMETER.finditer(text[:before]):
    v = float(m.group(1))
    if 0.5 <= v <= 24.0:
      return v
  return None

def _key_of(parts: tuple) -> str:
  return hashlib.sha1("|".join(str(p) for p in ("DRN", *parts)).encode()).hexdigest()[:24]

def _labels(lines: list, pattern) -> list:
  out: list = []
  for ln in lines:
    if NOT_A_LABEL.search(ln.text):
      continue
    for m in pattern.finditer(ln.text):
      x, y = ln.locate(m.start(), m.end())
      if any(abs(x - o[0]) <= SAME_PLACE_PT and abs(y - o[1]) <= SAME_PLACE_PT for o in out):
        continue
      out.append((x, y, _inches(ln.text, m.start())))
  return out

def _make(cls, ctx: dict, finish, item: str, key_parts: tuple, label: str, points: list, params: dict, missing: list, facts: dict, notes: list, base: float, count: int):
  cand = cls(key=_key_of((item, *key_parts)), category="WALL", kind="COUNT", quantity_mode=MODE[item], label=label, tag=TAG[item],
    geometry={"points": [[round(p[0], 3), round(p[1], 3)] for p in points]}, params={**params, "dims_basis": "SPECIFIED"}, missing=missing, work_item=WORK_ITEM[item],
    status="VALID", confidence=0.0, facts={**facts, "foundation_item": item, "derived_from": "LABELS"}, notes=notes, source="TAG_SCAN", count=count)
  return finish(cand, ctx, base)

def _dia_text(inches: float | None) -> str:
  return f"{inches:g} in" if inches else "size not written"

def rain_pipes(labels: list, floor_heights: dict | None, ctx: dict, cls, finish) -> list:
  if not labels:
    return []
  fall = drop_mm(floor_heights)
  sizes = sorted({lb[2] for lb in labels if lb[2]})
  inches = sizes[0] if len(sizes) == 1 else None
  n = len(labels)
  facts: dict = {"drainage": RAIN_PIPE, "labels_on_sheet": n, "diameter_in": inches, "diameters_in": sizes, "length_basis": "LEVELS" if fall else "TYPED"}
  notes = [C.note("RAIN_PIPE_COUNT_ASSUMED")]

  params: dict = {}
  missing: list = []
  text = f"Rain water pipe · {_dia_text(inches)} · {n} no{'s' if n != 1 else ''}"
  if fall:
    facts.update(fall)
    params["length_mm"] = fall["drop_mm"]
    notes.append(C.note("RAIN_PIPE_DROP_ASSUMED", top_mm=fall["top_mm"], bottom_mm=fall["bottom_mm"]))
    text += f" · {fall['drop_mm'] / 1000.0:.2f} m each"
  else:
    missing.append("length_mm")
    notes.append(C.note("RAIN_PIPE_LENGTH_TYPED"))
  return [_make(cls, ctx, finish, RAIN_PIPE, (round(labels[0][0], 1), round(labels[0][1], 1)), text, [(lb[0], lb[1]) for lb in labels], params, missing, facts, notes, 0.6, n)]

def sewer_pipe(labels: list, ctx: dict, cls, finish) -> list:
  if not labels:
    return []
  sizes = sorted({lb[2] for lb in labels if lb[2]})
  inches = sizes[0] if len(sizes) == 1 else None
  facts = {"drainage": SEWER_PIPE, "labels_on_sheet": len(labels), "diameter_in": inches, "diameters_in": sizes, "length_basis": "TYPED"}
  text = f"Sewer pipe line · {_dia_text(inches)} · length to be typed"
  return [_make(cls, ctx, finish, SEWER_PIPE, (round(labels[0][0], 1), round(labels[0][1], 1)), text, [(labels[0][0], labels[0][1])], {}, ["length_mm"], facts,
    [C.note("SEWER_LENGTH_TYPED")], 0.55, 1)]

def _near(pts: list, x: float, y: float) -> bool:
  return any(abs(x - p[0]) <= SAME_PLACE_PT and abs(y - p[1]) <= SAME_PLACE_PT for p in pts)

def chambers(lines: list, ctx: dict, cls, finish) -> list:
  if not any(DRAIN_SHEET.search(ln.text) for ln in lines):
    return []
  out: list = []

  for item, pattern, prefix, plural in CHAMBER_TAGS:
    numbered: dict = {}
    bare: list = []
    for ln in lines:
      if "=" in ln.text or NOT_A_LABEL.search(ln.text):
        continue
      for _, _, w in ln.spans:
        m = pattern.match((w.text or "").strip())
        if not m:
          continue
        if m.group(1):
          numbered.setdefault(prefix + m.group(1).upper(), (w.cx, w.cy))
        elif not _near(bare, w.cx, w.cy):
          bare.append((w.cx, w.cy))

    marks = sorted(numbered, key=lambda k: (int(re.sub(r"\D", "", k) or 0), k))
    points = [numbered[k] for k in marks] + bare
    n = len(points)
    if not n:
      continue

    shown = ", ".join(marks[:8]) + (" …" if len(marks) > 8 else "")
    facts = {"drainage": item, "marks": marks, "bare_labels": len(bare), "labels_on_sheet": n}
    out.append(_make(cls, ctx, finish, item, (round(points[0][0], 1), round(points[0][1], 1)), f"{plural} · {n} no{'s' if n != 1 else ''}" + (f" ({shown})" if marks else ""), points, {}, [],
      facts, [C.note("DRAIN_CHAMBERS_COUNT_ONLY")], 0.6, n))
  return out

def candidates(words: list, floor_heights: dict | None, ctx: dict, cls, finish) -> list:
  if not words:
    return []
  lines = TX.build_lines(words)
  return [*rain_pipes(_labels(lines, RAIN_LABEL), floor_heights, ctx, cls, finish), *sewer_pipe(_labels(lines, SEWER_LABEL), ctx, cls, finish), *chambers(lines, ctx, cls, finish)]

def fill_drainage(item: str, missing: list, params: dict, typed: dict, facts: dict) -> tuple:
  out = dict(params or {})
  field = TYPED_FIELD.get(item)
  value = typed.get(field) if field else None
  if value is not None:
    out["length_mm"] = float(value)
    out["dims_basis"] = "SPECIFIED"
    return out, None
  if "length_mm" in (missing or []):
    return out, ("CANDIDATE_NEEDS_DIMENSIONS", f"Give {WORDS.get(item, 'the length')} to measure this item.")
  return out, None
