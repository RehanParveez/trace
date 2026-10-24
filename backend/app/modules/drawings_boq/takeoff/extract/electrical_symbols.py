from __future__ import annotations
import re
from dataclasses import dataclass, field
import collections
import numpy as np

MAX_OBJECTS = 400_000
MIN_TABLE_ROWS = 4
LINE_THICK_PT = 2.5
LONG_LINE_PT = 120.0          
COLUMN_LINE_PT = 40.0          
MIN_SYMBOL_OBJECTS = 3         
MIN_SCALE, MAX_SCALE = 0.4, 5.0
SIZE_TOL = 0.40                
SIZE_ATOL_PT = 1.5
BOX_TOL = 0.45
BOX_ATOL_PT = 3.0
RADIAL_TOL = 0.10              
HEIGHT_RE = re.compile(r"(?P<what>[A-Z][A-Za-z /\[\]()&.\-]{2,60}?)\s*=\s*(?P<ft>\d{1,2})\s*'\s*-\s*(?P<in>\d{1,2})\s*\"")
IN_NAME_HEIGHT_RE = re.compile(r"\(?\s*(?:AT\s+)?(?P<ft>\d{1,2})\s*'\s*-\s*(?P<in>\d{1,2})\s*\"\s*(?:\(?\s*A\.?\s*F\.?\s*FL\.?\s*\)?)?\s*\)?", re.I)
SIZE_CLUSTER = 1.15            
MIN_TOKEN_CHARS = 2

@dataclass
class Obj:
  index: int
  kind: int                   
  n: int                       
  box: tuple                   

@dataclass
class LegendSymbol:
  description: str
  name: str
  table: int
  row: int
  objects: list
  mounting_height_mm: float | None = None
  token: str = ""

  @property
  def by_text(self) -> bool:
    return len(self.objects) < MIN_SYMBOL_OBJECTS and bool(self.token)

  @property
  def countable(self) -> bool:
    return len(self.objects) >= MIN_SYMBOL_OBJECTS or bool(self.token)

@dataclass
class Hit:
  name: str
  first_index: int
  last_index: int
  scale: float
  box: tuple                  
  centre: tuple = (0.0, 0.0)

@dataclass
class PageReport:
  counts: dict = field(default_factory=dict)
  hits: list = field(default_factory=list)
  set_aside: list = field(default_factory=list)
  not_found: list = field(default_factory=list)
  not_countable: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def _geometry(page) -> tuple:
  rotation = int(page.get_rotation() or 0) % 360
  x0, y0, x1, y1 = (float(v) for v in page.get_mediabox())
  return rotation if rotation in (0, 90, 180, 270) else 0, x0, y0, x1 - x0, y1 - y0

def _to_display(rot: int, ox: float, oy: float, wu: float, hu: float):
  def f(b):
    l, bt, r, t = b[0] - ox, b[1] - oy, b[2] - ox, b[3] - oy
    if rot == 0:
      return (l, hu - t, r, hu - bt)
    if rot == 90:
      return (bt, l, t, r)
    if rot == 180:
      return (wu - r, bt, wu - l, t)
    return (hu - t, wu - r, hu - bt, wu - l)
  return f

def _to_page_rect(rot: int, ox: float, oy: float, wu: float, hu: float, d: tuple) -> tuple:
  x0, y0, x1, y1 = d
  if rot == 0:
    l, b, r, t = x0, hu - y1, x1, hu - y0
  elif rot == 90:
    l, b, r, t = y0, x0, y1, x1
  elif rot == 180:
    l, b, r, t = wu - x1, y0, wu - x0, y1
  else:
    l, b, r, t = wu - y1, hu - x1, wu - y0, hu - x0
  return l + ox, b + oy, r + ox, t + oy

def load_objects(page) -> tuple[list, dict]:
  import pypdfium2.raw as raw
  rot, ox, oy, wu, hu = _geometry(page)
  to_d = _to_display(rot, ox, oy, wu, hu)
  
  out: list = []
  stats = {"forms": 0, "objects": 0, "truncated": False}
  for i, o in enumerate(page.get_objects(filter=[raw.FPDF_PAGEOBJ_PATH, raw.FPDF_PAGEOBJ_TEXT, raw.FPDF_PAGEOBJ_FORM], max_depth=0)):
    if o.type == raw.FPDF_PAGEOBJ_FORM:
      stats["forms"] += 1
      continue
    if len(out) >= MAX_OBJECTS:
      stats["truncated"] = True
      break
    try:
      b = to_d(o.get_bounds())
    except Exception:
      continue
  
    n = int(raw.FPDFPath_CountSegments(o.raw)) if o.type == raw.FPDF_PAGEOBJ_PATH else -1
    out.append(Obj(i, int(o.type), n, tuple(float(v) for v in b)))
  stats["objects"] = len(out)
  return out, stats

def _token_key(text: str) -> str:
  return re.sub(r"\s+", "", text or "").upper()

def _usable_token(text: str) -> str:
  key = _token_key(text)
  return key if len(re.sub(r"[^A-Z0-9]", "", key)) >= MIN_TOKEN_CHARS else ""

def read_tokens(page) -> list:
  import pypdfium2.raw as raw
  rot, ox, oy, wu, hu = _geometry(page)
  to_d = _to_display(rot, ox, oy, wu, hu)
  tp = page.get_textpage()
  out: list = []

  for i, o in enumerate(page.get_objects(filter=[raw.FPDF_PAGEOBJ_TEXT], max_depth=0)):
    try:
      l, b, r, t = o.get_bounds()
      text = tp.get_text_bounded(left=l, bottom=b, right=r, top=t) or ""
      box = to_d((l, b, r, t))
    except Exception:
      continue
    key = _token_key(text)
    if key:
      out.append((i, key, tuple(float(v) for v in box)))
  return out

def _w(b) -> float:
  return b[2] - b[0]

def _h(b) -> float:
  return b[3] - b[1]

def _centre(b) -> tuple:
  return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)

def _tables(objs: list) -> list:
  hor = [o for o in objs if o.kind == 2 and _h(o.box) < LINE_THICK_PT and _w(o.box) >= LONG_LINE_PT]
  ver = [o for o in objs if o.kind == 2 and _w(o.box) < LINE_THICK_PT and _h(o.box) >= COLUMN_LINE_PT]
  groups: dict = collections.defaultdict(list)
  
  for o in hor:
    groups[(round(o.box[0] / 3.0), round(o.box[2] / 3.0))].append(o)
  tables = []
  for (_, _), lines in groups.items():
    ys = sorted({round(_centre(o.box)[1], 1) for o in lines})
    if len(ys) < MIN_TABLE_ROWS:
      continue
    x0 = min(o.box[0] for o in lines)
    x1 = max(o.box[2] for o in lines)
    inside = [o for o in ver if x0 - 2.0 <= _centre(o.box)[0] <= x1 + 2.0 and o.box[1] <= ys[0] + 2.0 and o.box[3] >= ys[-1] - 2.0]
    xs = sorted({round(_centre(o.box)[0], 1) for o in inside})
    edges = sorted({round(x0, 1), *xs, round(x1, 1)})
    
    merged: list = []
    for e in edges:
      if not merged or e - merged[-1] > 3.0:
        merged.append(e)
    top = min([o.box[1] for o in inside], default=ys[0] - 26.0)
    tables.append({"x0": x0, "x1": x1, "rows": ys, "cols": merged, "top": top})
  return sorted(tables, key=lambda t: t["x0"])

def _text(textpage, rot, ox, oy, wu, hu, rect: tuple) -> str:
  l, b, r, t = _to_page_rect(rot, ox, oy, wu, hu, rect)
  try:
    return re.sub(r"\s+", " ", textpage.get_text_bounded(left=l, bottom=b, right=r, top=t) or "").strip()
  except Exception:
    return ""

def _height_table(textpage) -> dict:
  text = (textpage.get_text_range() or "").replace("\r", "\n")
  out: dict = {}
  for line in text.split("\n"):
    m = HEIGHT_RE.search(line.strip())
    if m:
      what = re.sub(r"\s+", " ", m.group("what")).strip().upper()
      out[what] = round(int(m.group("ft")) * 304.8 + int(m.group("in")) * 25.4, 1)
  return out

def read_legend(page) -> list:
  objs, _ = load_objects(page)
  rot, ox, oy, wu, hu = _geometry(page)
  tp = page.get_textpage()
  heights = _height_table(tp)
  
  symbols: list = []
  for ti, tb in enumerate(_tables(objs)):
    cols, rows = tb["cols"], tb["rows"]
    if len(cols) < 3:
      continue
  
    plan_col = None
    first = 0 if tb["top"] < rows[0] - 3.0 else 1     
    head_bottom = rows[first]
    for ci in range(len(cols) - 2):
      head = _text(tp, rot, ox, oy, wu, hu, (cols[ci] + 1, tb["top"] + 1, cols[ci + 1] - 1, head_bottom - 1)).upper()
      if "PLAN" in head and "ELEVATION" not in head:
        plan_col = ci
        break
    if plan_col is None:
      continue
  
    x0, x1, dx0, dx1 = cols[plan_col], cols[plan_col + 1], cols[-2], cols[-1]
    for ri in range(first, len(rows) - 1):
      y0, y1 = rows[ri], rows[ri + 1]
      desc = _text(tp, rot, ox, oy, wu, hu, (dx0 + 1, y0 + 1, dx1 - 1, y1 - 1))
      cell = [o for o in objs if x0 + 1 <= _centre(o.box)[0] <= x1 - 1 and y0 + 1 <= _centre(o.box)[1] <= y1 - 1
        and _w(o.box) < (x1 - x0) - 2.0 and _h(o.box) < (y1 - y0) - 1.0]
      if not desc or not cell:
        continue
    
      token = _usable_token(_text(tp, rot, ox, oy, wu, hu, (x0 + 1, y0 + 1, x1 - 1, y1 - 1))) if any(o.kind == 1 for o in cell) else ""
      m = IN_NAME_HEIGHT_RE.search(desc)
      name = re.sub(r"\s+", " ", IN_NAME_HEIGHT_RE.sub("", desc)).strip().rstrip(" -(")
      key = name.upper()
      height = round(int(m.group("ft")) * 304.8 + int(m.group("in")) * 25.4, 1) if m else next((v for k, v in heights.items() if k and (k in key or key in k)), None)
      symbols.append(LegendSymbol(description=desc, name=name, table=ti, row=ri, objects=sorted(cell, key=lambda o: o.index), mounting_height_mm=height, token=token))
  return symbols

def _radial(objs: list) -> list:
  x0, y0 = min(o.box[0] for o in objs), min(o.box[1] for o in objs)
  x1, y1 = max(o.box[2] for o in objs), max(o.box[3] for o in objs)
  cx, cy, diag = (x0 + x1) / 2.0, (y0 + y1) / 2.0, max(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5, 1e-6)
  return sorted((o.n, round((((_centre(o.box)[0] - cx) ** 2 + (_centre(o.box)[1] - cy) ** 2) ** 0.5) / diag, 3)) for o in objs)

def _box(objs: list) -> tuple:
  return (min(o.box[0] for o in objs), min(o.box[1] for o in objs), max(o.box[2] for o in objs), max(o.box[3] for o in objs))

def _find(plan: list, symbol: LegendSymbol, narr, prefix) -> list:
  sym = symbol.objects
  k = len(sym)
  if len(plan) < k:
    return []

  want = collections.Counter(o.n for o in sym)
  ok = np.ones(len(plan) - k + 1, dtype=bool)
  for v, pre in prefix.items():
    ok &= (pre[k:] - pre[:-k]) == want.get(v, 0)
  if any(v not in prefix for v in want):
    return []

  sizes = sorted(max(_w(o.box), _h(o.box)) for o in sym)
  box = _box(sym)
  dims = sorted((_w(box), _h(box)))
  radial = _radial(sym)
  hits = []
  
  for j in np.where(ok)[0]:
    run = plan[j:j + k]
    got = sorted(max(_w(o.box), _h(o.box)) for o in run)
    scale = sum(got) / max(sum(sizes), 1e-6)
    if not MIN_SCALE <= scale <= MAX_SCALE:
      continue
    if any(abs(a - scale * b) > max(SIZE_TOL * scale * b, SIZE_ATOL_PT) for a, b in zip(got, sizes)):
      continue
    pb = _box(run)
    pd = sorted((_w(pb), _h(pb)))
    if any(abs(a - scale * b) > max(BOX_TOL * scale * b, BOX_ATOL_PT) for a, b in zip(pd, dims)):
      continue
  
    rr = _radial(run)
    if any(a[0] != b[0] or abs(a[1] - b[1]) > RADIAL_TOL for a, b in zip(rr, radial)):
      continue
    hits.append(Hit(symbol.name, run[0].index, run[-1].index, round(scale, 2), pb, _centre(pb)))
  return hits

def _count_text(rep: PageReport, sym: LegendSymbol, tokens: list) -> None:
  found = [t for t in tokens if t[1] == sym.token]
  for i, _, box in found:
    rep.hits.append(Hit(sym.name, i, i, 1.0, box, _centre(box)))
  rep.counts[sym.name] = rep.counts.get(sym.name, 0) + len(found)

def count_symbols(plan_objects: list, legend: list, tokens: list | None = None) -> PageReport:
  rep = PageReport()
  if not plan_objects:
    return rep

  narr = np.array([o.n for o in plan_objects])
  prefix = {int(v): np.concatenate([[0], np.cumsum(narr == v)]) for v in np.unique(narr)}
  taken: list = []
  for sym in sorted(legend, key=lambda s: -len(s.objects)):
    key = sym.name
    if not sym.countable:
      if key not in rep.not_countable:
        rep.not_countable.append(key)
      continue
    if sym.by_text:
      _count_text(rep, sym, tokens or [])
      continue
  
    kept, aside = _one_size([h for h in _find(plan_objects, sym, narr, prefix)
      if not any(not (h.last_index < a or h.first_index > b) for a, b in taken)])
    for h in kept:
      taken.append((h.first_index, h.last_index))
    rep.hits += kept
    rep.set_aside += aside
    rep.counts[key] = rep.counts.get(key, 0) + len(kept)
  rep.not_found = [k for k, v in rep.counts.items() if v == 0]
  rep.hits.sort(key=lambda h: (h.centre[1], h.centre[0]))
  return rep

def _one_size(hits: list) -> tuple:
  if len(hits) < 2:
    return hits, []

  order = sorted(hits, key=lambda h: h.scale)
  groups: list = [[order[0]]]
  for h in order[1:]:
    if h.scale / max(groups[-1][-1].scale, 1e-6) <= SIZE_CLUSTER:
      groups[-1].append(h)
    else:
      groups.append([h])
      
  best = max(groups, key=lambda g: (len(g), -abs(g[0].scale - 1.0)))
  aside = [h for g in groups if g is not best for h in g]
  return sorted(best, key=lambda h: h.first_index), aside

def read_electrical(doc, legend_page_index: int, plan_page_indexes: list) -> dict:
  legend = read_legend(doc[legend_page_index])
  out = {"legend_page": legend_page_index + 1, "symbols": [{"name": s.name, "description": s.description, "objects": len(s.objects),
    "countable": s.countable, "by_text": s.by_text, "text": s.token, "mounting_height_mm": s.mounting_height_mm} for s in legend], "pages": {}}
  
  for pi in plan_page_indexes:
    objs, st = load_objects(doc[pi])
    rep = count_symbols(objs, legend, read_tokens(doc[pi]))
    rep.stats = st
    out["pages"][pi + 1] = {"counts": rep.counts, "not_found": rep.not_found, "not_countable": rep.not_countable, "stats": st,
      "set_aside_other_size": collections.Counter(h.name for h in rep.set_aside),
      "hits": [{"name": h.name, "scale": h.scale, "centre": [round(h.centre[0], 1), round(h.centre[1], 1)]} for h in rep.hits]}
    out["pages"][pi + 1]["set_aside_other_size"] = dict(out["pages"][pi + 1]["set_aside_other_size"])
  return out
