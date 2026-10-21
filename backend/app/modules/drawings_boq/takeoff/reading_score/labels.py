from __future__ import annotations
import csv
import hashlib
import io
import math
from app.modules.drawings_boq.takeoff.prep.details import norm_mark
from dataclasses import dataclass
import json

CATEGORIES = ("COLUMN", "FOOTING", "BEAM", "DOOR", "WINDOW", "WALL", "ROOM", "SLAB", "LINTEL", "STAIR", "SITE")
SITE_KINDS = ("OHWT", "UGWT", "SEPTIC", "BOUNDARY_WALL", "GATE", "PORCH_RAMP")
POSITIVE, NEGATIVE = "POSITIVE", "NEGATIVE"
REGISTER, IMPORT = "REGISTER", "IMPORT"
POINT_CATEGORIES = ("COLUMN", "FOOTING", "DOOR", "WINDOW")
SIZE_FIELDS = ("length_mm", "width_mm", "depth_mm", "thickness_mm", "height_mm", "waist_mm")
TYPED_AS = {
  "wall_height_mm": "height_mm", "column_height_mm": "height_mm", "neck_height_mm": "height_mm", "tank_wall_height_mm": "height_mm",
  "footing_depth_mm": "depth_mm", "beam_depth_mm": "depth_mm", "plinth_beam_depth_mm": "depth_mm", "tie_band_depth_mm": "depth_mm",
  "slab_thickness_mm": "thickness_mm", "stair_waist_mm": "waist_mm",
}
MAX_UNITS_PER_CANDIDATE = 2000
MAX_IMPORT_ROWS = 20000

class LabelError(ValueError):
  """A label file or a label that cannot be used. The message is a plain sentence for the person who wrote the file."""

@dataclass(frozen=True)
class Unit:
  family: str
  mark: str | None
  x: float | None
  y: float | None
  attrs: tuple = ()
  ref: str = ""
  text: str | None = None

  def size(self) -> dict:
    return dict(self.attrs)

def family_of(category: str | None, site_kind: str | None = None) -> str:
  cat = str(category or "").strip().upper()
  if cat == "SITE" and site_kind:
    return f"SITE:{str(site_kind).strip().upper()}"
  return cat

def valid_family(family: str) -> bool:
  cat, _, kind = str(family or "").partition(":")
  if cat not in CATEGORIES:
    return False
  return (cat == "SITE" and (not kind or kind in SITE_KINDS)) or (cat != "SITE" and not kind)

def _num(v) -> float | None:
  try:
    f = float(v)
  except (TypeError, ValueError):
    return None
  return f if math.isfinite(f) else None

def clean_points(pts) -> list:
  out = []
  for p in pts or []:
    try:
      x, y = float(p[0]), float(p[1])
    except (TypeError, ValueError, IndexError, KeyError):
      continue
    if math.isfinite(x) and math.isfinite(y):
      out.append((x, y))
  return out

def centroid(pts: list) -> tuple | None:
  if not pts:
    return None
  return (round(sum(p[0] for p in pts) / len(pts), 3), round(sum(p[1] for p in pts) / len(pts), 3))

def sizes_of(params: dict | None, typed: dict | None = None) -> tuple:
  out: dict = {}
  
  for f in SIZE_FIELDS:
    v = _num((params or {}).get(f))
    if v is not None and v > 0:
      out[f] = round(v, 1)
  for field_, value in (typed or {}).items():
    v = _num(value)
    if v is not None and v > 0:
      out[TYPED_AS.get(str(field_), str(field_))] = round(v, 1)
  return tuple(sorted(out.items()))

def units_of(category, tag, geometry, count, source, facts, params, *, ref: str = "", typed: dict | None = None) -> list:
  site_kind = (facts or {}).get("site_kind")
  fam = family_of(category, site_kind)
  mark = norm_mark(tag) if tag else None
  text = str(tag).strip().upper() if tag else None
  attrs = sizes_of(params, typed)
  g = geometry or {}
  
  pts = clean_points(g.get("points"))
  if str(category or "").upper() in POINT_CATEGORIES or str(source or "") == "TAG_SCAN":
    n = max(int(count or 1), 1)
    anchors = [(round(x, 3), round(y, 3)) for x, y in pts][:MAX_UNITS_PER_CANDIDATE]
    if len(anchors) < n:
      anchors += [None] * (min(n, MAX_UNITS_PER_CANDIDATE) - len(anchors))
    return [Unit(fam, mark, a[0] if a else None, a[1] if a else None, attrs, f"{ref}:{i}", text) for i, a in enumerate(anchors)]
  outer = clean_points(g.get("outer"))
  c = centroid(pts or outer)
  return [Unit(fam, mark, c[0] if c else None, c[1] if c else None, attrs, f"{ref}:0", text)]

def units_of_candidate(c, *, ref: str | None = None) -> list:
  typed = (getattr(c, "facts", None) or {}).get("typed")
  return units_of(c.category, getattr(c, "tag", None), getattr(c, "geometry", None), getattr(c, "count", 1), getattr(c, "source", None),
    getattr(c, "facts", None), getattr(c, "params", None), ref=ref if ref is not None else str(getattr(c, "id", None) or getattr(c, "key", "")), typed=typed)

def is_human_reject(c) -> bool:
  f = getattr(c, "facts", None) or {}
  return c.decision == "REJECTED" and getattr(c, "decided_by_user_id", None) is not None and not f.get("set_aside")

def labels_from_register(candidates: list) -> tuple:
  by_sheet: dict = {}
  
  for c in candidates:
    by_sheet.setdefault(c.sheet_id, []).append(c)
  labels, report = [], {"accepted": 0, "rejected": 0, "undecided": 0, "put_aside_by_system": 0, "built_after_read": 0, "sheets": 0, "complete_sheets": 0}
  for sheet_id, rows in by_sheet.items():
    complete = all(r.decision != "NEW" for r in rows)
    kept = 0
    
    for r in rows:
      f = r.facts or {}
      if r.decision == "NEW":
        report["undecided"] += 1
        continue
      if f.get("from_shapes"):
        report["built_after_read"] += 1
        continue
      if r.decision == "ACCEPTED":
        polarity = POSITIVE
        report["accepted"] += 1
      elif is_human_reject(r):
        polarity = NEGATIVE
        report["rejected"] += 1
      else:
        report["put_aside_by_system"] += 1
        continue
      for u in units_of_candidate(r, ref=str(r.id)):
        kept += 1
        labels.append({"sheet_id": sheet_id, "family": u.family, "mark": u.text, "polarity": polarity, "x_pt": u.x, "y_pt": u.y, "attrs": dict(u.attrs),
          "complete": complete, "source": REGISTER, "source_ref": u.ref, "extract_version": getattr(r, "extract_version", None)})
        
    if kept:
      report["sheets"] += 1
      report["complete_sheets"] += 1 if complete else 0
  return labels, report

IMPORT_COLUMNS = ("page_no", "family", "mark", "polarity", "x_pt", "y_pt", "length_mm", "width_mm", "depth_mm", "thickness_mm", "height_mm", "waist_mm", "complete")

def import_template() -> str:
  buf = io.StringIO()
  w = csv.writer(buf, lineterminator="\n")
  w.writerow(IMPORT_COLUMNS)
  w.writerow([1, "COLUMN", "C1", "POSITIVE", 120.5, 340.25, 300, 300, "", "", "", "", "true"])
  w.writerow([1, "WALL", "", "POSITIVE", 210.0, 400.0, "", 230, "", "", "", "", "true"])
  return buf.getvalue()

def _flag(v, default: bool = False) -> bool:
  if v is None or str(v).strip() == "":
    return default
  return str(v).strip().lower() in ("1", "true", "yes", "y", "t")

def _row(raw: dict, n: int) -> dict:
  def bad(msg: str):
    raise LabelError(f"Row {n}: {msg}")
  try:
    page = int(float(str(raw.get("page_no")).strip()))
  except (TypeError, ValueError):
    bad(f"page_no must be the sheet number, not '{raw.get('page_no')}'.")
  if page < 1:
    bad("page_no starts at 1.")
  family = str(raw.get("family") or raw.get("kind") or "").strip().upper()
  if not valid_family(family):
    bad(f"'{raw.get('family')}' is not a kind I read ({', '.join(CATEGORIES)}; a site item as SITE:OHWT, SITE:UGWT, SITE:SEPTIC, SITE:BOUNDARY_WALL, SITE:GATE or SITE:PORCH_RAMP).")
  polarity = str(raw.get("polarity") or POSITIVE).strip().upper()
  if polarity not in (POSITIVE, NEGATIVE):
    bad(f"polarity is POSITIVE (the member stands) or NEGATIVE (the reader's find is wrong), not '{raw.get('polarity')}'.")
  mark = str(raw.get("mark") or raw.get("tag") or "").strip().upper() or None
  x, y = _num(raw.get("x_pt")), _num(raw.get("y_pt"))
  if (x is None) != (y is None):
    bad("give both x_pt and y_pt, or neither.")
  if mark is None and x is None:
    bad("a row needs a mark or a position, or the reader's find cannot be matched to it.")
    
  attrs = {}
  for f in SIZE_FIELDS:
    v = raw.get(f)
    if v is None or str(v).strip() == "":
      continue
    num = _num(v)
    
    if num is None or num <= 0:
      bad(f"{f} must be a number above zero, not '{v}'.")
    attrs[f] = round(num, 1)
  return {"page_no": page, "family": family, "mark": mark, "polarity": polarity, "x_pt": x, "y_pt": y, "attrs": attrs, "complete": _flag(raw.get("complete"))}

def parse_import(content: str, fmt: str) -> list:
  fmt = str(fmt or "").strip().upper()
  if fmt == "CSV":
    rows = list(csv.DictReader(io.StringIO(content or "")))
  elif fmt == "JSON":
    try:
      data = json.loads(content or "[]")
    except json.JSONDecodeError as e:
      raise LabelError(f"The file is not valid JSON: {e}.")
  
    rows = data.get("labels") if isinstance(data, dict) else data
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
      raise LabelError("The JSON file must be a list of rows, or an object with a 'labels' list of rows.")
    for r in rows:
      if isinstance(r.get("attrs"), dict):
        r.update({k: v for k, v in r["attrs"].items() if k not in r})
        
  else:
    raise LabelError("The file format is CSV or JSON.")
  if not rows:
    raise LabelError("The file has no rows.")
  if len(rows) > MAX_IMPORT_ROWS:
    raise LabelError(f"The file has {len(rows)} rows; the limit is {MAX_IMPORT_ROWS}.")
  return [_row({str(k).strip().lower(): v for k, v in r.items() if k is not None}, i + 2 if fmt == "CSV" else i + 1) for i, r in enumerate(rows)]

def stamp(labels: list) -> str:
  rows = sorted((str(l["sheet_id"]), l["family"], l.get("mark") or "", l["polarity"], round(l["x_pt"], 2) if l.get("x_pt") is not None else "",
    round(l["y_pt"], 2) if l.get("y_pt") is not None else "", json.dumps(l.get("attrs") or {}, sort_keys=True), bool(l.get("complete"))) for l in labels)
  return hashlib.sha1(json.dumps(rows, default=str).encode()).hexdigest()[:20]

def label_unit(l: dict, i: int = 0) -> Unit:
  return Unit(l["family"], norm_mark(l["mark"]) if l.get("mark") else None, l.get("x_pt"), l.get("y_pt"), tuple(sorted((l.get("attrs") or {}).items())),
    str(l.get("id") or l.get("source_ref") or i), l.get("mark"))
