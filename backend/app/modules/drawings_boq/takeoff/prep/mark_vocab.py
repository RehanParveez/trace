from __future__ import annotations
import math
import re
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.prep.texts import build_lines, is_tag

COUNTED = ("COLUMN", "FOOTING", "BEAM", "DOOR", "WINDOW")
CATEGORIES = COUNTED + ("WALL_SECTION", "SECTION_REF", "SLAB_PANEL", "UNKNOWN")
STRENGTH = {"PERSON": 6, "SECTION_TITLE": 5, "SCHEDULE": 4, "LEGEND": 3, "SECTION_SYMBOL": 2, "DEFAULT": 1}
BASES = tuple(STRENGTH)
STRUCTURAL = "STRUCTURAL"
MAX_SEEN = 80
MAX_TEXT = 90

SECTION_TITLE = re.compile(r"\bSEC(?:TION|\.)?\s*([A-Z]{1,3}\d{1,3})\s*-\s*\1\b", re.I)
_WALL_MARK = re.compile(r"^(?:W|WN|WIN)[-.]?\d")
_KEYWORDS = (
  ("WALL_SECTION", re.compile(r"\bWALL\b", re.I)),
  ("FOOTING", re.compile(r"\b(?:FOOTING|FOUNDATION|FTG|PAD)\b", re.I)),
  ("COLUMN", re.compile(r"\bCOLUMN\b", re.I)),
  ("BEAM", re.compile(r"\bBEAM\b", re.I)),
)

_LEGEND_WORD = re.compile(r"\b(?:LEGEND|SYMBOLS?|ABBREVIATIONS?|KEY)\b", re.I)
_LEGEND_LINE = re.compile(r"^\s*(?P<mark>[A-Z]{1,4}[-.]?\d{1,3}[A-Z]?)\s*(?:[-=:–]|\bIS\b|\bMEANS\b)\s*(?P<what>[A-Z][A-Z0-9 /.,&()'\"-]{2,60})$", re.I)
_LEGEND_KEYWORDS = (
  ("WALL_SECTION", re.compile(r"\bWALL\s+(?:SECTION|FOOTING)\b", re.I)),
  ("SECTION_REF", re.compile(r"\b(?:SECTION\s+(?:MARK|CUT|LINE|REF\w*)|CUTTING\s+PLANE)\b", re.I)),
  ("DOOR", re.compile(r"\bDOORS?\b", re.I)),
  ("WINDOW", re.compile(r"\b(?:WINDOWS?|VENTILATORS?)\b", re.I)),
  ("COLUMN", re.compile(r"\bCOLUMNS?\b", re.I)),
  ("FOOTING", re.compile(r"\b(?:FOOTINGS?|FOUNDATIONS?)\b", re.I)),
  ("BEAM", re.compile(r"\bBEAMS?\b", re.I)),
)

_CAPTION_IN = re.compile(r"FOOTING\s+FOR\s+(\d+(?:\.\d+)?)\s*[\"”'’]*", re.I)
_EXTERIOR = re.compile(r"\b(?:EXTERNAL|EXTERIOR|OUTER|OUTSIDE|BOUNDARY|PERIPHER\w*)\b", re.I)
_INTERIOR = re.compile(r"\b(?:INTERNAL|INTERIOR|INNER|PARTITION)\b", re.I)
EXTERIOR_MIN_MM = 200.0         
MM_INCH = 25.4
TITLE_REACH_FRAC = 0.08         
SYMBOL_THICK_FACTOR = 2.0      
SYMBOL_MIN_LEN = 4.0            
SYMBOL_MAX_LEN_FRAC = 0.2       
SYMBOL_END_REACH = 1.2          
SYMBOL_LABEL_REACH = 3.5        
SYMBOL_BUDGET = 60000

def norm(tag: str) -> str:
  return re.sub(r"[\s.\-]", "", (tag or "").upper())

def default_category(tag: str, discipline: str | None = None, plan_kind: str | None = None) -> str | None:
  t = (tag or "").strip().upper()
  base = next((cat for cat, pat in C.TAG_CATEGORIES if pat.match(t)), None)
  if base in ("DOOR", "WINDOW") and (discipline == STRUCTURAL or plan_kind == "FOUNDATION"):
    return "WALL_SECTION" if base == "WINDOW" and _WALL_MARK.match(t) else "UNKNOWN"
  return base

def entry_of(vocab: dict | None, tag: str, discipline: str | None) -> dict | None:
  if not vocab:
    return None
  group = vocab.get(discipline) if discipline else None
  if isinstance(group, dict):
    return group.get(norm(tag))
  return None

def category_of(tag: str, vocab: dict | None = None, discipline: str | None = None, plan_kind: str | None = None) -> str | None:
  e = entry_of(vocab, tag, discipline)
  if e and e.get("category") in CATEGORIES:
    return e["category"]
  return default_category(tag, discipline, plan_kind)

def counted(category: str | None) -> bool:
  return category in COUNTED

def _clip(text: str) -> str:
  return re.sub(r"\s+", " ", text or "").strip()[:MAX_TEXT]

def _category_in(text: str, table) -> str | None:
  hits = [cat for cat, pat in table if pat.search(text)]
  return hits[0] if hits else None

def title_category(text: str) -> str | None:
  found = {cat for cat, pat in _KEYWORDS if pat.search(text)}
  if "WALL_SECTION" in found:
    return "WALL_SECTION"
  if "FOOTING" in found:
    return "FOOTING"
  for cat in ("COLUMN", "BEAM"):
    if cat in found:
      return cat
  return None

def _frame(angle: float) -> tuple:
  a = round(angle / 90.0) % 4
  rad = math.radians(a * 90)
  return a * 90, math.cos(rad), math.sin(rad)

def _line_words(ln) -> list:
  return [w for _a, _b, w in ln.spans]

def _centre(ln) -> tuple:
  ws = _line_words(ln)
  return (sum(w.cx for w in ws) / len(ws), sum(w.cy for w in ws) / len(ws)) if ws else (0.0, 0.0)

def _near_text(ln, lines: list) -> str:
  ws = _line_words(ln)
  if not ws:
    return ""
  ang, ux, uy = _frame(ln.angle)
  along = [w.cx * ux + w.cy * uy for w in ws]
  across = sum(-w.cx * uy + w.cy * ux for w in ws) / len(ws)
  size = max(w.size for w in ws)
  
  out = []
  for o in lines:
    if o is ln or round(o.angle) % 360 != round(ln.angle) % 360:
      continue
    ows = _line_words(o)
    if not ows:
      continue
    oac = sum(-w.cx * uy + w.cy * ux for w in ows) / len(ows)
    oal = [w.cx * ux + w.cy * uy for w in ows]
    if 0.5 * size < abs(oac - across) <= 2.4 * size and max(oal) >= min(along) - size and min(oal) <= max(along) + 10 * size:
      out.append((abs(oac - across), o.text))
  out.sort()
  return " ".join(t for _d, t in out[:2])

def _diag(words: list) -> float:
  xs, ys = [w.cx for w in words], [w.cy for w in words]
  return math.hypot(max(xs) - min(xs), max(ys) - min(ys)) if words else 0.0

def read_titles(words: list, lines: list, page_no: int | None = None) -> list:
  caps = []
  for ln in lines:
    m = _CAPTION_IN.search(ln.text)
    if m:
      caps.append((_centre(ln), float(m.group(1))))
  reach = TITLE_REACH_FRAC * _diag(words)
  taken: set = set()
  
  out = []
  for ln in lines:
    m = SECTION_TITLE.search(ln.text)
    if not m:
      continue
    mark = norm(m.group(1))
    rest = (ln.text[:m.start()] + " " + ln.text[m.end():])
    cat = title_category(rest)
    text, shown = rest, ln.text
    if cat is None:
      near = _near_text(ln, lines)
      cat = title_category(near)
      text, shown = rest + " " + near, ln.text + " " + near
    if cat is None:
      continue
  
    params: dict = {}
    if cat == "WALL_SECTION":
      cx, cy = _centre(ln)
      best = None
      for i, ((px, py), inches) in enumerate(caps):
        d = math.hypot(px - cx, py - cy)
        if i not in taken and d <= reach and (best is None or d < best[0]):
          best = (d, i, inches)
      if best is not None:
        taken.add(best[1])
        params["wall_thickness_mm"] = round(best[2] * MM_INCH, 1)
      if _EXTERIOR.search(text):
        params["exterior"], params["exterior_basis"] = True, "TITLE"
      elif _INTERIOR.search(text):
        params["exterior"], params["exterior_basis"] = False, "TITLE"
      elif params.get("wall_thickness_mm"):
        params["exterior"], params["exterior_basis"] = params["wall_thickness_mm"] >= EXTERIOR_MIN_MM, "THICKNESS"
    out.append({"mark": mark, "category": cat, "basis": "SECTION_TITLE", "text": _clip(shown), "page_no": page_no, "params": params})
  return out

def read_legend(words: list, lines: list, page_no: int | None = None) -> list:
  if not any(_LEGEND_WORD.fullmatch(w.text.strip().strip(":.")) for w in words):
    return []
  out = []
  for ln in lines:
    m = _LEGEND_LINE.match(ln.text)
    if not m:
      continue
    cat = _category_in(m.group("what"), _LEGEND_KEYWORDS)
    if cat is None:
      continue
    out.append({"mark": norm(m.group("mark")), "category": cat, "basis": "LEGEND", "text": _clip(ln.text), "page_no": page_no, "params": {}})
  return out

def _rings_by_cell(index, cell: float) -> dict:
  grid: dict = {}
  for r in index.rings:
    w, h = r.bbox[2] - r.bbox[0], r.bbox[3] - r.bbox[1]
    if max(w, h) > 6.0 * cell:
      continue
    grid.setdefault((int((r.bbox[0] + r.bbox[2]) / 2.0 // cell), int((r.bbox[1] + r.bbox[3]) / 2.0 // cell)), []).append(r)
  return grid

def _terminated(rings: dict, cell: float, ex: float, ey: float, reach: float, length: float) -> bool:
  span = int(reach // cell) + 1
  cx, cy = int(ex // cell), int(ey // cell)
  for dx in range(-span, span + 1):
    for dy in range(-span, span + 1):
      for r in rings.get((cx + dx, cy + dy), ()):
        mx, my = (r.bbox[0] + r.bbox[2]) / 2.0, (r.bbox[1] + r.bbox[3]) / 2.0
        size = max(r.bbox[2] - r.bbox[0], r.bbox[3] - r.bbox[1])
        if math.hypot(mx - ex, my - ey) <= reach and 0.25 * reach <= size <= 0.6 * length and (r.fill or r.curved):
          return True
  return False

def read_symbols(index, words: list, page_no: int | None = None) -> list:
  marks = [w for w in words if is_tag(w.text) and default_category(w.text) is not None]
  if not marks or index is None or not index.n:
    return []

  sizes = sorted(w.size for w in words if w.size)
  size = sizes[len(sizes) // 2] if sizes else 6.0
  widths = sorted(index.segs[5 * i + 4] for i in range(0, index.n, max(1, index.n // 4000)))
  usual = widths[len(widths) // 2] if widths else 0.0
  thick_min = max(SYMBOL_THICK_FACTOR * usual, 0.0)
  x0, y0, x1, y1 = index.bbox
  max_len = SYMBOL_MAX_LEN_FRAC * min(x1 - x0, y1 - y0)
  cell = max(size * 2.0, 4.0)
  rings = _rings_by_cell(index, cell)
  
  total: dict = {}
  for w in marks:
    key = norm(w.text)
    total[key] = total.get(key, 0) + 1
  beside: dict = {}
  for i in range(min(index.n, SYMBOL_BUDGET)):
    a, b, c, d = index.seg(i)
    wid = index.segs[5 * i + 4]
    length = math.hypot(c - a, d - b)
    
    if wid < thick_min or wid <= 0.0 or not (SYMBOL_MIN_LEN * size <= length <= max_len):
      continue
    reach = SYMBOL_END_REACH * size
    if not (_terminated(rings, cell, a, b, reach, length) and _terminated(rings, cell, c, d, reach, length)):
      continue
    at_a = {norm(w.text): w for w in marks if math.hypot(w.cx - a, w.cy - b) <= SYMBOL_LABEL_REACH * max(w.size, size)}
    at_b = {norm(w.text): w for w in marks if math.hypot(w.cx - c, w.cy - d) <= SYMBOL_LABEL_REACH * max(w.size, size)}
    for key in at_a.keys() & at_b.keys():
      beside.setdefault(key, set()).update((id(at_a[key]), id(at_b[key])))
  return [{"mark": k, "category": "SECTION_REF", "basis": "SECTION_SYMBOL", "text": _clip(f"{k} printed at both ends of a section-cut symbol"), "page_no": page_no, "params": {}}
    for k, ids in sorted(beside.items()) if len(ids) >= total.get(k, 0)]

def read_members(words: list, hint: str | None, page_no: int | None = None) -> list:
  from app.modules.drawings_boq.takeoff.extract import members as M
  rows, _ids = M.schedule_rows(words, hint)
  out = []
  for key, size in sorted(rows.items()):
    cat = default_category(key)
    if cat in ("COLUMN", "FOOTING", "BEAM"):
      out.append({"mark": norm(key), "category": cat, "basis": "SCHEDULE", "text": _clip(f"{key} in a schedule row, {int(size[0])} x {int(size[1])} mm"), "page_no": page_no,
        "params": {"size_mm": [size[0], size[1]]}})
  return out

def read_seen(words: list) -> dict:
  seen: dict = {}
  for w in words:
    if is_tag(w.text) and default_category(w.text) is not None:
      key = norm(w.text)
      seen[key] = seen.get(key, 0) + 1
  return dict(sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_SEEN])

def read_sheet(index, words: list, hint: str | None = None, page_no: int | None = None) -> dict:
  out: dict = {"titles": [], "legend": [], "symbols": [], "members": [], "seen": {}}
  lines = []
  try:
    lines = build_lines(words)
  except Exception:
    out["error"] = "LINES"
  for key, fn in (("titles", lambda: read_titles(words, lines, page_no)), ("legend", lambda: read_legend(words, lines, page_no)),
      ("symbols", lambda: read_symbols(index, words, page_no)), ("members", lambda: read_members(words, hint, page_no)), ("seen", lambda: read_seen(words))):
    try:
      out[key] = fn()
    except Exception:
      out.setdefault("errors", []).append(key)
  return out

def _opening_rows(sheet_meta: dict, page_no: int) -> list:
  rows = []
  for o in ((sheet_meta.get("schedule") or {}).get("openings") or []):
    mark = norm(o.get("mark") or "")
    kind = o.get("type")
    if not mark or kind not in ("DOOR", "WINDOW", "VENTILATOR"):
      continue
    cat = "DOOR" if kind == "DOOR" else "WINDOW"
    rows.append({"mark": mark, "category": cat, "basis": "SCHEDULE", "text": _clip(f"{mark} in the {kind.lower()} schedule, {int(o['width_mm'])} x {int(o['height_mm'])} mm"), "page_no": page_no,
      "params": {"width_mm": o["width_mm"], "height_mm": o["height_mm"], "opening_kind": kind}})
  return rows

def _brief(e: dict) -> dict:
  return {"category": e["category"], "basis": e["basis"], "text": e.get("text"), "page_no": e.get("page_no"), "drawing_id": e.get("drawing_id")}

def build(project_sheets: list, person: dict | None = None) -> dict:
  found: dict = {}
  default_first: dict = {}
  for item in project_sheets:
    drawing_id, s = item if isinstance(item, tuple) else (None, item)
    meta = getattr(s, "prep_meta", None) or {}
    ident = meta.get("identity") or {}
    disc = ident.get("discipline")
    if not disc or ident.get("read_as") == "SKIP":
      continue
  
    page = int(getattr(s, "page_no", 0) or 0)
    ev = meta.get("mark_evidence") or {}
    rows = [*(ev.get("titles") or []), *_opening_rows(meta, page), *(ev.get("members") or []), *(ev.get("legend") or []), *(ev.get("symbols") or [])]
    for r in rows:
      if r.get("category") in CATEGORIES and r.get("mark"):
        found.setdefault(disc, {}).setdefault(r["mark"], []).append({**r, "drawing_id": drawing_id, "page_no": r.get("page_no") or page})
    for mark in (ev.get("seen") or {}):
      default_first.setdefault((disc, mark), (drawing_id, page, ident.get("plan_kind")))
      
  out: dict = {}
  for disc, marks in found.items():
    for mark, rows in marks.items():
      rows.sort(key=lambda r: -STRENGTH[r["basis"]])
      top = rows[0]
      entry = {"category": top["category"], "basis": top["basis"], "text": top.get("text"), "page_no": top.get("page_no"), "params": dict(top.get("params") or {})}
      if top.get("drawing_id") is not None:
        entry["drawing_id"] = top["drawing_id"]
      for r in rows[1:]:
        if r["category"] == top["category"]:
          for k, v in (r.get("params") or {}).items():
            entry["params"].setdefault(k, v)
        elif "conflict" not in entry:
          entry["conflict"] = _brief(r)
      out.setdefault(disc, {})[mark] = entry
      
  for (disc, mark), (drawing_id, page, kind) in default_first.items():
    if mark in out.get(disc, {}):
      continue
    cat = default_category(mark, disc, kind)
    if cat is None:
      continue
  
    e = {"category": cat, "basis": "DEFAULT", "text": _clip(f"{mark}: read by its letters, nothing on the drawing says what it is"), "page_no": page, "params": {}}
    if drawing_id is not None:
      e["drawing_id"] = drawing_id
    out.setdefault(disc, {})[mark] = e
  for disc, marks in (person or {}).items():
    for mark, p in (marks or {}).items():
      if p.get("category") in CATEGORIES:
        out.setdefault(disc, {})[norm(mark)] = {"category": p["category"], "basis": "PERSON", "text": p.get("text") or "Set by a person", "page_no": p.get("page_no"), "params": dict(p.get("params") or {})}
  return {d: dict(sorted(m.items())) for d, m in sorted(out.items())}

def person_entries(vocab: dict | None) -> dict:
  return {d: {m: e for m, e in marks.items() if e.get("basis") == "PERSON"} for d, marks in (vocab or {}).items() if any(e.get("basis") == "PERSON" for e in marks.values())}

def conflicts(vocab: dict | None, discipline: str | None) -> list:
  return [(m, e, e["conflict"]) for m, e in ((vocab or {}).get(discipline) or {}).items() if e.get("conflict")]

def lines_for(vocab: dict | None) -> list:
  out = []
  for disc, marks in (vocab or {}).items():
    plain = 0
    for mark, e in marks.items():
      if e["basis"] == "DEFAULT":
        plain += 1
        continue
      p = e.get("params") or {}
      extra = f", {p['wall_thickness_mm']:g} mm, {'outside' if p.get('exterior') else 'inside'} wall" if p.get("wall_thickness_mm") else ""
      where = f"{e['drawing_id']} p.{e.get('page_no')}" if e.get("drawing_id") else f"p.{e.get('page_no')}"
      c = e.get("conflict")
      out.append(f"{disc} {mark} -> {e['category']} ({e['basis']}, {where}){extra}" + (f"; CONFLICT: {c['category']} ({c['basis']}, p.{c.get('page_no')})" if c else ""))
    if plain:
      out.append(f"{disc}: {plain} mark(s) read by their letters only (DEFAULT)")
  return out
