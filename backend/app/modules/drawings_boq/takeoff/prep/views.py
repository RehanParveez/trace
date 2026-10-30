from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.prep.texts import _LEVEL_WORDS, build_lines
import math
from statistics import median
from app.modules.drawings_boq.takeoff.scale import parse_scale_text
from app.modules.drawings_boq.takeoff.prep import page_unit as PU

CAPTION_SIZE_FACTOR = 1.2   
CELL_DIVISOR = 400.0          
CELL_MIN, CELL_MAX = 2.0, 10.0
LINK_CELLS = 2                 
MIN_BLOCK_CELLS = 120
FRAME_LINE_FRACTION = 0.35     
CAPTION_REACH_FRACTION = 0.12  
VIEW_MARGIN_CELLS = 2.0
MAX_CAPTION_LINES = 4
SORT_BAND_PT = 40.0   
NOTE_PAD_PT = 25.0    
MAX_SEGMENTS = 600000 

_STRUCT_WORD = re.compile(r"\b(?:FOUNDATIONS?|FOOTINGS?|FRAMING|COLUMNS?|BEAMS?|SLABS?)\b", re.I)
_PLAN_WORD = re.compile(r"\b(?:PLANS?|LAYOUTS?)\b", re.I)
_KINDS = (
  ("ELEVATION", re.compile(r"\bELEVATIONS?\b", re.I)),
  ("SECTION", re.compile(r"\bSECTIONS?\b|\bSECTIONAL\b", re.I)),
  ("SCHEDULE", re.compile(r"\bSCHEDULES?\b", re.I)),
  ("NOTES", re.compile(r"\bNOTES?\b", re.I)),
  ("PLAN", re.compile(r"\bPLANS?\b|\bLAYOUTS?\b", re.I)),
  ("DETAIL", re.compile(r"\bDETAILS?\b", re.I)),
)
_ROOF_WORDS = re.compile(r"\bMUMTY\b|\bROOF\b|\bTERRACE\b", re.I)
_SCALE_WORD = re.compile(r"\bSCALE\b", re.I)

def kind_of(text: str) -> str | None:
  """What a caption says the view is: STRUCT_PLAN (foundation / framing / column plans), PLAN, SECTION, ELEVATION, DETAIL, SCHEDULE or NOTES."""
  t = text or ""
  if _STRUCT_WORD.search(t) and _PLAN_WORD.search(t) and not re.search(r"\bSECTION\s+OF\b", t, re.I):
    return "STRUCT_PLAN"
  for kind, pat in _KINDS:
    if pat.search(t):
      return kind
  return None

def level_of(text: str) -> str | None:
  for key, pat in _LEVEL_WORDS:
    if pat.search(text or ""):
      return key
  if _ROOF_WORDS.search(text or ""):
    return "ROOF"
  return None

def _frame(ln):
  """(along_min, along_max, across, size) of a line of text, along its own writing direction."""
  ws = [w for _, _, w in ln.spans]
  rad = math.radians(ln.angle)
  ux, uy = math.cos(rad), math.sin(rad)
  alongs = [w.cx * ux + w.cy * uy for w in ws]
  half = [w.length / 2.0 for w in ws]
  lo = min(a - h for a, h in zip(alongs, half))
  hi = max(a + h for a, h in zip(alongs, half))
  across = sum(-w.cx * uy + w.cy * ux for w in ws) / len(ws)
  return lo, hi, across, max(w.size for w in ws)

def _bbox_of_words(ws) -> list:
  return [min(w.x0 for w in ws), min(w.y0 for w in ws), max(w.x1 for w in ws), max(w.y1 for w in ws)]

def captions(words: list) -> list[dict]:
  """Large lines of text that name a drawing, each joined with the lines of the same caption block (the scale line, a second title line)."""
  lines = [ln for ln in build_lines(words) if ln.spans]
  if not lines:
    return []
  sizes = [w.size for w in words if w.size > 0]
  base = median(sizes) if sizes else 1.0
  frames = {id(ln): _frame(ln) for ln in lines}
  out = []
  used: set = set()
  for ln in sorted(lines, key=lambda l: -frames[id(l)][3]):
    lo, hi, across, size = frames[id(ln)]
    if size < CAPTION_SIZE_FACTOR * base or id(ln) in used:
      continue
    kind = kind_of(ln.text)
    if kind is None:
      continue
    block = [ln]
    used.add(id(ln))
    grown = True
    
    while grown and len(block) < MAX_CAPTION_LINES:
      grown = False
      for o in lines:
        if id(o) in used or o.angle != ln.angle:
          continue
        olo, ohi, oacross, osize = frames[id(o)]
        if not (0.7 * size <= osize <= 1.35 * size or (_SCALE_WORD.search(o.text) and osize >= 0.4 * size)):
          continue
        near = min(abs(oacross - frames[id(b)][2]) for b in block)
        if near > 2.4 * size:
          continue
        blo, bhi = min(frames[id(b)][0] for b in block), max(frames[id(b)][1] for b in block)
        overlap = min(ohi, bhi) - max(olo, blo)
        if overlap < 0.2 * min(ohi - olo, bhi - blo):
          continue
        block.append(o)
        used.add(id(o))
        grown = True
        
    ws = [w for b in block for _, _, w in b.spans]
    own = [b for b in block if not _SCALE_WORD.search(b.text)]
    title = " ".join(b.text for b in sorted(own, key=lambda b: -frames[id(b)][2]))
    scale = None
    scale_text = None
    for b in block:
      if _SCALE_WORD.search(b.text):
        m = re.search(r"SCALE\s*[:=\-]?\s*(.+)$", b.text, re.I)
        scale_text = (m.group(1) if m else b.text).strip()
        r = parse_scale_text(scale_text)
        scale = float(r) if r is not None else None
    title = re.sub(r"\s+", " ", title).strip()
    out.append({"text": title, "kind": kind_of(title) or kind, "size": size, "angle": ln.angle, "bbox": _bbox_of_words(ws),
      "scale_text": scale_text, "declared_ratio": scale, "along": (lo, hi), "across": across})
  return out

def _blocks(segs, kinds, bbox, cell: float) -> list[dict]:
  x0, y0, x1, y1 = bbox
  limit = FRAME_LINE_FRACTION * min(x1 - x0, y1 - y0)
  cells: set = set()
  for i in range(len(kinds)):
    k = i * 5
    ax, ay, bx, by = segs[k], segs[k + 1], segs[k + 2], segs[k + 3]
    length = math.hypot(bx - ax, by - ay)
    if length > limit:
      continue
    steps = int(length / cell) + 1
    for j in range(steps + 1):
      t = j / steps
      cells.add((int((ax + (bx - ax) * t - x0) // cell), int((ay + (by - ay) * t - y0) // cell)))
  seen: set = set()
  out = []
  reach = range(-LINK_CELLS, LINK_CELLS + 1)
  
  for c in cells:
    if c in seen:
      continue
    seen.add(c)
    stack = [c]
    n = 0
    bx0 = bx1 = c[0]
    by0 = by1 = c[1]
    while stack:
      cx, cy = stack.pop()
      n += 1
      bx0, bx1, by0, by1 = min(bx0, cx), max(bx1, cx), min(by0, cy), max(by1, cy)
      for dx in reach:
        for dy in reach:
          nb = (cx + dx, cy + dy)
          if nb in cells and nb not in seen:
            seen.add(nb)
            stack.append(nb)
    if n >= MIN_BLOCK_CELLS:
      out.append({"cells": n, "bbox": [x0 + bx0 * cell, y0 + by0 * cell, x0 + (bx1 + 1) * cell, y0 + (by1 + 1) * cell]})
  return out

def _gap(a: list, b: list) -> float:
  dx = max(a[0] - b[2], b[0] - a[2], 0.0)
  dy = max(a[1] - b[3], b[1] - a[3], 0.0)
  return math.hypot(dx, dy)

def _along_share(cap: dict, block: list) -> float:
  """How much of the caption lies under (or over) the block, measured along the way the caption is written."""
  horizontal = cap["angle"] % 180 == 0
  c0, c1 = (cap["bbox"][0], cap["bbox"][2]) if horizontal else (cap["bbox"][1], cap["bbox"][3])
  b0, b1 = (block[0], block[2]) if horizontal else (block[1], block[3])
  length = max(c1 - c0, 1e-6)
  return max(0.0, min(c1, b1) - max(c0, b0)) / length

def _slug(text: str) -> str:
  words = re.findall(r"[A-Z0-9]+", (text or "").upper())
  return "-".join(words[:4]) or "VIEW"

def find_views(index, unit: float | None = None) -> list[dict]:
  """The drawings on a sheet: [{key, kind, caption, level_hint, bbox, declared_ratio, scale_text, plan, structural, ...}], each placed by its caption."""
  words = index.words
  if not words or not len(index.kinds) or len(index.kinds) > MAX_SEGMENTS:
    return []
  b = index.bbox
  unit = PU.of_box(b) if unit is None else unit
  diag = math.hypot(b[2] - b[0], b[3] - b[1])
  cell = min(max(diag / CELL_DIVISOR, CELL_MIN * unit), CELL_MAX * unit)
  caps = captions(words)
  if not caps:
    return []
  blocks = _blocks(index.segs, index.kinds, b, cell)
  reach = CAPTION_REACH_FRACTION * diag
  taken: dict = {}
  
  for cap in sorted(caps, key=lambda c: -c["size"]):
    best = None
    for i, blk in enumerate(blocks):
      gap = _gap(cap["bbox"], blk["bbox"])
      if gap > reach:
        continue
      share = _along_share(cap, blk["bbox"])
      score = (0 if share >= 0.5 else 1, gap - 20.0 * share * cell, -blk["cells"])
      if best is None or score < best[0]:
        best = (score, i)
    if best is None:
      continue
    cur = taken.get(best[1])
    if cur is None or cap["size"] > cur["size"]:
      taken[best[1]] = cap
  margin = VIEW_MARGIN_CELLS * cell
  views = []
  for i, cap in taken.items():
    x0, y0, x1, y1 = blocks[i]["bbox"]
    kind = cap["kind"]
    
    level = level_of(cap["text"]) if kind in ("STRUCT_PLAN", "PLAN") else None
    views.append({"kind": kind, "caption": cap["text"], "level_hint": level, "bbox": [round(x0 - margin, 2), round(y0 - margin, 2), round(x1 + margin, 2), round(y1 + margin, 2)],
      "core_bbox": [round(v, 2) for v in blocks[i]["bbox"]], "declared_ratio": cap["declared_ratio"], "scale_text": cap["scale_text"],
      "caption_bbox": [round(v, 2) for v in cap["bbox"]], "plan": kind in ("STRUCT_PLAN", "PLAN"), "structural": kind == "STRUCT_PLAN",
      "cells": blocks[i]["cells"]})
  views.sort(key=lambda v: (-round((v["bbox"][1] + v["bbox"][3]) / 2.0 / (SORT_BAND_PT * unit)), round((v["bbox"][0] + v["bbox"][2]) / 2.0 / (SORT_BAND_PT * unit))))
  count: dict = {}
  for v in views:
    base = f"{v['kind']}:{v['level_hint'] or '-'}:{_slug(v['caption'])}"
    count[base] = count.get(base, 0) + 1
    v["key"] = base if count[base] == 1 else f"{base}#{count[base]}"
  annotate(views, words, unit)
  return views

def contains(view: dict, x: float, y: float, core: bool = False) -> bool:
  b = view["core_bbox"] if core else view["bbox"]
  return b[0] <= x <= b[2] and b[1] <= y <= b[3]

def view_at(views: list, x: float, y: float, plans_only: bool = False) -> dict | None:
  """The view a point belongs to: the one whose drawing block holds it, else the nearest one whose margin holds it."""
  pool = [v for v in views if v["plan"]] if plans_only else views
  for v in pool:
    if contains(v, x, y, core=True):
      return v
  near = [v for v in pool if contains(v, x, y)]
  if not near:
    return None
  return min(near, key=lambda v: _gap([x, y, x, y], v["core_bbox"]))

def split(items: list, views: list, point) -> dict:
  """Items (words, shapes) grouped by the key of the view they sit in. point(item) -> (x, y)."""
  out: dict = {}
  for it in items:
    x, y = point(it)
    v = view_at(views, x, y)
    if v is not None:
      out.setdefault(v["key"], []).append(it)
  return out

_SLAB_NOTE = re.compile(r"\bSLABS?\s+(?:ARE|IS)\s+(\d+(?:\.\d+)?)\s*(?:\"|”|″|IN\b|INCH)", re.I)
_SLAB_PANEL = re.compile(r"^[A-Z]{1,2}S-?\d{1,2}$")
_FOUNDATION = re.compile(r"\bFOUNDATIONS?\b|\bFOOTINGS?\b", re.I)

def annotate(views: list, words: list, unit: float = 1.0) -> None:
  """What the text around a plan view says about it: whether it is the foundation plan, the slab thickness note and the slab panel marks."""
  lines = build_lines(words)
  pad = NOTE_PAD_PT * unit
  for v in views:
    v["foundation"] = bool(v["structural"] and _FOUNDATION.search(v["caption"]))
    if not v["structural"]:
      continue
    cb = v["caption_bbox"]
    x0, y0 = min(v["bbox"][0], cb[0]) - pad, min(v["bbox"][1], cb[1]) - pad
    x1, y1 = max(v["bbox"][2], cb[2]) + pad, max(v["bbox"][3], cb[3]) + pad
    note = None
    for ln in lines:
      ws = [w for _, _, w in ln.spans]
      cx, cy = sum(w.cx for w in ws) / len(ws), sum(w.cy for w in ws) / len(ws)
      if not (x0 <= cx <= x1 and y0 <= cy <= y1):
        continue
      m = _SLAB_NOTE.search(ln.text)
      if m:
        note = round(float(m.group(1)) * 25.4, 1)
        break
    v["slab_note_mm"] = note
    marks = {w.text.strip().upper() for w in words if _SLAB_PANEL.match(w.text.strip().upper()) and contains(v, w.cx, w.cy, core=True)}
    v["slab_panels"] = len(marks)
    v["slab_marks"] = sorted(marks)

def attach_scales(views: list, clusters: list, pairs: list, pt_mm: float, user_unit: float = 1.0) -> None:
  """Each view's own drawing scale: the dimension cluster with the most printed dimensions inside it. Views with none have no measured scale."""
  for v in views:
    best = None
    for c in clusters:
      n = 0
      for i, _ in c.members:
        p = pairs[i]
        if contains(v, (p.p1[0] + p.p2[0]) / 2.0, (p.p1[1] + p.p2[1]) / 2.0):
          n += 1
      if n >= 2 and (best is None or n > best[0]):
        best = (n, c)
    if best is not None:
      n, c = best
      v["scale"] = {"ratio": round(c.ratio, 4), "support": n, "mm_per_pt": round(c.ratio * pt_mm * user_unit, 5), "source": "DIMENSIONS"}
    else:
      v["scale"] = None

def summary(views: list) -> list[dict]:
  """The part of each view kept with the sheet (no geometry)."""
  keep = ("key", "kind", "caption", "level_hint", "bbox", "declared_ratio", "scale_text", "plan", "structural", "foundation", "scale", "slab_note_mm", "slab_panels")
  return [{k: v.get(k) for k in keep if k in v} for v in views]