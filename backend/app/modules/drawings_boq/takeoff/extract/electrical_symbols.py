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
SYMBOL_MAX_PT = 60.0           
SYMBOL_MIN_PT = 2.5
SYMBOL_TOUCH_PT = 1.5          
SYMBOL_GAP_MAX_PT = 70.0       
ROW_ALIGN_PT = 8.0             
SYMBOL_ALIGN_PT = 25.0         
LINE_MERGE = 2.5              
MAX_TEXT_RUNS = 6000
MAX_CLUSTER_OBJECTS = 400
MAX_LINE_GAP = 6.0             
OCR_DPI = 300.0
OCR_BUDGET_S = 20.0
OCR_MIN_CONF = 50.0
TITLE_ZONE_RIGHT, TITLE_ZONE_BOTTOM = 1.0, 0.30
TITLE_PAD_PT = 6.0
TITLE_LABEL = re.compile(r"^(?:CLIENT|PROJECT|CONSULTANT|DRAWN|CHECKED|TITLE|DRG|DWG|REVISION|SHEET)\b", re.I)

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
  block: tuple | None = None
  inner: tuple = ()
  ocr: bool = False

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

def _ocr_cell(page, rect: tuple, started: float) -> str:
  """The text of one cell of a legend that has no native text (outlined letters): the cell is drawn and read by OCR. Empty when OCR is not available or the budget of the legend is spent."""
  import time
  from app.modules.drawings_boq.takeoff.prep import ocr_layer
  left = OCR_BUDGET_S - (time.monotonic() - started)
  if left < 3.0 or not ocr_layer.available():
    return ""
  try:
    Wv, Hv = page.get_size()
    x0, y0, x1, y1 = max(0.0, rect[0]), max(0.0, rect[1]), min(Wv, rect[2]), min(Hv, rect[3])
    if x1 - x0 < 8.0 or y1 - y0 < 4.0:
      return ""
    scale = OCR_DPI / 72.0
    img = page.render(scale=scale, crop=(x0, Hv - y1, Wv - x1, y0)).to_pil().convert("L")
    rows = [r for r in ocr_layer._tsv(img, left, "6") if r["conf"] >= OCR_MIN_CONF and any(ch.isalnum() for ch in r["text"])]
  except Exception:
    return ""
  lines: list = []
  for r in sorted(rows, key=lambda r: (r["t"], r["l"])):
    if lines and abs(r["t"] - lines[-1][0]) <= 0.6 * max(r["h"], 1):
      lines[-1][1].append(r)
    else:
      lines.append([r["t"], [r]])
  return re.sub(r"\s+", " ", " ".join(w["text"] for _t, ws in lines for w in sorted(ws, key=lambda w: w["l"]))).strip()

def _symbol(desc: str, cell: list, token: str, ti: int, ri: int, heights: dict, block, inner: tuple, ocr: bool = False) -> LegendSymbol:
  m = IN_NAME_HEIGHT_RE.search(desc)
  name = re.sub(r"\s+", " ", IN_NAME_HEIGHT_RE.sub("", desc)).strip().rstrip(" -(")
  key = name.upper()
  height = round(int(m.group("ft")) * 304.8 + int(m.group("in")) * 25.4, 1) if m else next((v for k, v in heights.items() if k and (k in key or key in k)), None)
  return LegendSymbol(description=desc, name=name, table=ti, row=ri, objects=sorted(cell, key=lambda o: o.index), mounting_height_mm=height, token=token, block=block, inner=inner, ocr=ocr)

def _read_ruled(page, objs: list, tp, rot, ox, oy, wu, hu, heights: dict) -> list:
  import time
  started = time.monotonic()
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
    block = (tb["x0"], rows[0], tb["x1"], rows[-1])
    for ri in range(first, len(rows) - 1):
      y0, y1 = rows[ri], rows[ri + 1]
      desc = _text(tp, rot, ox, oy, wu, hu, (dx0 + 1, y0 + 1, dx1 - 1, y1 - 1))
      cell = [o for o in objs if x0 + 1 <= _centre(o.box)[0] <= x1 - 1 and y0 + 1 <= _centre(o.box)[1] <= y1 - 1
        and _w(o.box) < (x1 - x0) - 2.0 and _h(o.box) < (y1 - y0) - 1.0]
      ocr = False
      if not desc and cell:
        desc = _ocr_cell(page, (dx0 + 1, y0 + 1, dx1 - 1, y1 - 1), started)
        ocr = bool(desc)
      if not desc or not cell:
        continue
    
      token = _usable_token(_text(tp, rot, ox, oy, wu, hu, (x0 + 1, y0 + 1, x1 - 1, y1 - 1))) if any(o.kind == 1 for o in cell) else ""
      inner = tuple(sorted(t for t in (_usable_token(_text(tp, rot, ox, oy, wu, hu, o.box)) for o in cell if o.kind == 1) if t))
      symbols.append(_symbol(desc, cell, token, ti, ri, heights, block, inner, ocr))
  return symbols

def read_text_lines(page) -> list:
  """The text of a page as lines: [{"text", "box"}], the boxes in the display frame. Text runs of one baseline that stand close together are one line."""
  import pypdfium2.raw as raw
  rot, ox, oy, wu, hu = _geometry(page)
  to_d = _to_display(rot, ox, oy, wu, hu)
  tp = page.get_textpage()
  runs: list = []
  for o in page.get_objects(filter=[raw.FPDF_PAGEOBJ_TEXT], max_depth=0):
    if len(runs) >= MAX_TEXT_RUNS:
      break
    try:
      l, b, r, t = o.get_bounds()
      text = re.sub(r"\s+", " ", tp.get_text_bounded(left=l, bottom=b, right=r, top=t) or "").strip()
      box = tuple(float(v) for v in to_d((l, b, r, t)))
    except Exception:
      continue
    if text and _h(box) > 0.0:
      runs.append({"text": text, "box": box})
  runs.sort(key=lambda r: (round(_centre(r["box"])[1] / max(_h(r["box"]) * 0.6, 1.0)), r["box"][0]))
  lines: list = []
  for r in runs:
    p = lines[-1] if lines else None
    h = max(_h(r["box"]), _h(p["box"]), 1.0) if p else 1.0
    if p and abs(_centre(p["box"])[1] - _centre(r["box"])[1]) <= 0.5 * h and -0.5 * h <= r["box"][0] - p["box"][2] <= LINE_MERGE * h:
      p["text"] = p["text"] + " " + r["text"]
      p["box"] = (min(p["box"][0], r["box"][0]), min(p["box"][1], r["box"][1]), max(p["box"][2], r["box"][2]), max(p["box"][3], r["box"][3]))
    else:
      lines.append(dict(r))
  return lines

def _grid(objs: list, cell: float = 24.0) -> dict:
  g: dict = collections.defaultdict(list)
  for o in objs:
    cx, cy = _centre(o.box)
    g[(int(cx // cell), int(cy // cell))].append(o)
  return g

def _near(g: dict, box: tuple, pad: float, cell: float = 24.0) -> list:
  x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
  out: list = []
  for gx in range(int(x0 // cell) - 1, int(x1 // cell) + 2):
    for gy in range(int(y0 // cell) - 1, int(y1 // cell) + 2):
      for o in g.get((gx, gy), ()):
        b = o.box
        if b[0] <= x1 and b[2] >= x0 and b[1] <= y1 and b[3] >= y0:
          out.append(o)
  return out

def _cluster(g: dict, seed) -> list | None:
  """The strokes that touch one another, from one stroke: a symbol. None when what is found is too large to be a symbol."""
  seen = {seed.index: seed}
  todo = [seed]
  while todo:
    o = todo.pop()
    for n in _near(g, o.box, SYMBOL_TOUCH_PT):
      if n.index not in seen:
        seen[n.index] = n
        todo.append(n)
        if len(seen) > MAX_CLUSTER_OBJECTS:
          return None
  items = list(seen.values())
  b = _box(items)
  return items if max(_w(b), _h(b)) <= SYMBOL_MAX_PT * 1.25 else None

def _description_groups(lines: list) -> list:
  """The lines that one symbol claims, as the descriptions they make: lines under one another with less than a letter height between them are one description, lines further apart are two rows whose symbols touch."""
  out: list = []
  for ln in sorted(lines, key=lambda x: x["box"][1]):
    if out and ln["box"][1] - out[-1][-1]["box"][3] <= 1.0 * max(_h(ln["box"]), _h(out[-1][-1]["box"]), 1.0):
      out[-1].append(ln)
    else:
      out.append([ln])
  return out

def _read_structured(page, objs: list, tp, rot, ox, oy, wu, hu, heights: dict) -> list:
  lines = read_text_lines(page)
  if len(lines) < MIN_TABLE_ROWS:
    return []
  small = [o for o in objs if o.kind in (1, 2) and SYMBOL_MIN_PT <= max(_w(o.box), _h(o.box)) <= SYMBOL_MAX_PT]
  g = _grid(small)
  paths = [o for o in small if o.kind == 2]
  gp = _grid(paths)
  rows: dict = {}
  loose: list = []
  for ln in lines:
    bx = ln["box"]
    h = max(_h(bx), 1.0)
    band = max(0.9 * h, 6.0)
    zone = (bx[0] - SYMBOL_GAP_MAX_PT, _centre(bx)[1] - band, bx[0] - 0.5, _centre(bx)[1] + band)
    seeds = [o for o in _near(gp, zone, 0.0) if zone[0] <= _centre(o.box)[0] <= zone[2] and zone[1] <= _centre(o.box)[1] <= zone[3] and o.box[2] <= bx[0] - 0.5]
    if not seeds:
      loose.append(ln)
      continue
    
    seed = max(seeds, key=lambda o: o.box[2])
    cl = _cluster(g, seed)
    if cl is None:
      continue
    cb = _box(cl)
    if cb[2] > bx[0] - 0.2 or bx[0] - cb[2] > SYMBOL_GAP_MAX_PT or cb[3] < bx[1] - band or cb[1] > bx[3] + band:
      continue
    key = min(o.index for o in cl)
    row = rows.setdefault(key, {"cluster": cl, "box": cb, "lines": []})
    row["lines"].append(ln)
  for key in list(rows):
    groups = _description_groups(rows[key]["lines"])
    if len(groups) < 2:
      continue
    row = rows.pop(key)
    
    mids = [sum(_centre(x["box"])[1] for x in grp) / len(grp) for grp in groups]
    parts: list = [[] for _ in groups]
    for o in row["cluster"]:
      parts[min(range(len(groups)), key=lambda i: abs(_centre(o.box)[1] - mids[i]))].append(o)
    for grp, part in zip(groups, parts):
      if part:
        rows[min(o.index for o in part)] = {"cluster": part, "box": _box(part), "lines": grp}
  order = sorted(rows.values(), key=lambda r: _centre(r["box"])[1])
  
  for ln in loose:
    best = None
    for r in order:
      last = max(r["lines"], key=lambda x: x["box"][3])
      gap = ln["box"][1] - last["box"][3]
      first_x = min(x["box"][0] for x in r["lines"])
      if -0.5 <= gap <= 1.8 * max(_h(ln["box"]), 1.0) and abs(ln["box"][0] - first_x) <= ROW_ALIGN_PT and (best is None or gap < best[0]):
        best = (gap, r)
    if best is not None:
      best[1]["lines"].append(ln)
      
  cols: list = []
  for r in sorted(order, key=lambda r: min(x["box"][0] for x in r["lines"])):
    r["x_txt"] = min(x["box"][0] for x in r["lines"])
    r["x_sym"] = _centre(r["box"])[0]
    for c in cols:
      if abs(r["x_txt"] - c[0]["x_txt"]) <= ROW_ALIGN_PT and abs(r["x_sym"] - c[0]["x_sym"]) <= SYMBOL_ALIGN_PT:
        c.append(r)
        break
    else:
      cols.append([r])
  symbols: list = []
  for ti, col in enumerate(c for c in cols if len(c) >= MIN_TABLE_ROWS):
    col.sort(key=lambda r: _centre(r["box"])[1])
    gaps = sorted(b["box"][1] - a["box"][3] for a, b in zip(col, col[1:]))
    usual = max(gaps[len(gaps) // 2], 3.0) if gaps else 3.0
    runs: list = [[col[0]]]
    for a, b in zip(col, col[1:]):
      if b["box"][1] - a["box"][3] > MAX_LINE_GAP * usual + 12.0:
        runs.append([])
      runs[-1].append(b)
      
    for part in (p for p in runs if len(p) >= MIN_TABLE_ROWS):
      pts = [r["box"] for r in part] + [x["box"] for r in part for x in r["lines"]]
      block = (min(b[0] for b in pts) - 3.0, min(b[1] for b in pts) - 3.0, max(b[2] for b in pts) + 3.0, max(b[3] for b in pts) + 3.0)
      for ri, r in enumerate(part):
        desc = re.sub(r"\s+", " ", " ".join(x["text"] for x in sorted(r["lines"], key=lambda x: x["box"][1]))).strip()
        texts = [o for o in r["cluster"] if o.kind == 1]
        token = _usable_token(" ".join(_text(tp, rot, ox, oy, wu, hu, o.box) for o in texts)) if texts else ""
        inner = tuple(sorted(t for t in (_usable_token(_text(tp, rot, ox, oy, wu, hu, o.box)) for o in texts) if t))
        if desc:
          symbols.append(_symbol(desc, r["cluster"], token, 100 + ti, ri, heights, block, inner))
  return symbols

def read_legend(page) -> list:
  """The symbols of the legends on a page: from a table drawn with ruling lines and a PLAN column when there is one, else from the structure of the page (a symbol with its description to the right of it, row after row)."""
  objs, _ = load_objects(page)
  rot, ox, oy, wu, hu = _geometry(page)
  tp = page.get_textpage()
  heights = _height_table(tp)
  found = _read_ruled(page, objs, tp, rot, ox, oy, wu, hu, heights)
  return found if found else _read_structured(page, objs, tp, rot, ox, oy, wu, hu, heights)

def title_box(page, lines: list | None = None) -> tuple | None:
  """The box of the title block, from its own label words (client, project, drawn, checked, title ...) in the lower right of the sheet, in the display frame; None when fewer than three are found."""
  rot, ox, oy, wu, hu = _geometry(page)
  W, H = (hu, wu) if rot in (90, 270) else (wu, hu)
  lines = lines if lines is not None else read_text_lines(page)
  found = [l["box"] for l in lines if TITLE_LABEL.match(l["text"].strip()) and _centre(l["box"])[0] >= W * (1.0 - TITLE_ZONE_RIGHT) and _centre(l["box"])[1] >= H * (1.0 - TITLE_ZONE_BOTTOM)]
  if len(found) < 3:
    return None
  return (min(b[0] for b in found) - TITLE_PAD_PT, min(b[1] for b in found) - TITLE_PAD_PT, W, H)

def _radial(objs: list) -> list:
  x0, y0 = min(o.box[0] for o in objs), min(o.box[1] for o in objs)
  x1, y1 = max(o.box[2] for o in objs), max(o.box[3] for o in objs)
  cx, cy, diag = (x0 + x1) / 2.0, (y0 + y1) / 2.0, max(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5, 1e-6)
  return sorted((o.n, round((((_centre(o.box)[0] - cx) ** 2 + (_centre(o.box)[1] - cy) ** 2) ** 0.5) / diag, 3)) for o in objs)

def _box(objs: list) -> tuple:
  return (min(o.box[0] for o in objs), min(o.box[1] for o in objs), max(o.box[2] for o in objs), max(o.box[3] for o in objs))

def _tokmap(tokens: list | None) -> dict:
  return {tuple(round(v, 1) for v in box): _usable_token(key) for _i, key, box in tokens or []}

def _find(plan: list, symbol: LegendSymbol, narr, prefix, tokmap: dict | None = None) -> list:
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
    if symbol.inner and tokmap is not None and tuple(sorted(t for t in (tokmap.get(tuple(round(v, 1) for v in o.box), "") for o in run if o.kind == 1) if t)) != tuple(symbol.inner):
      continue
    hits.append(Hit(symbol.name, run[0].index, run[-1].index, round(scale, 2), pb, _centre(pb)))
  return hits

def _count_text(rep: PageReport, sym: LegendSymbol, tokens: list) -> None:
  found = [t for t in tokens if t[1] == sym.token]
  for i, _, box in found:
    rep.hits.append(Hit(sym.name, i, i, 1.0, box, _centre(box)))
  rep.counts[sym.name] = rep.counts.get(sym.name, 0) + len(found)

def count_symbols(plan_objects: list, legend: list, tokens: list | None = None, exclude: list | None = None) -> PageReport:
  rep = PageReport()
  if exclude:
    plan_objects = [o for o in plan_objects if not any(b[0] <= _centre(o.box)[0] <= b[2] and b[1] <= _centre(o.box)[1] <= b[3] for b in exclude)]
  if not plan_objects:
    return rep
  tokmap = _tokmap(tokens)

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
  
    kept, aside = _one_size([h for h in _find(plan_objects, sym, narr, prefix, tokmap)
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
