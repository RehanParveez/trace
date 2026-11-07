from __future__ import annotations
import math
import re
from dataclasses import dataclass
from app.engine.measure import readings as RD

FLOOR_WORDS = {"GROUND": "GROUND", "FIRST": "FIRST", "SECOND": "SECOND", "THIRD": "THIRD", "ROOF": "ROOF", "MUMTY": "MUMTY", "BASEMENT": "BASEMENT", "TERRACE": "ROOF"}
MARK_HEADERS = ("C/NO", "C/NO.", "MARK", "COLUMN")
MARK_RE = re.compile(r"^(PC|C|CL|COL)-?\d*[A-Z]?$")
STEEL_RE = re.compile(r"^(\d+)-?#(\d+)$")
SPACING_RE = re.compile(r"^#(\d+)@(\d+)\"?(?:/(\d+)\"?)?C/?C$")
DIM_RE = re.compile(r"^(?:(\d+)')?-?(\d+)?\"?$")
SIZE_RE = re.compile(r"^(\d+(?:\.\d+)?)(½|\.5)?\"?[x×](\d+(?:\.\d+)?)(½|\.5)?\"?$")
FRACTION_GLYPHS = ("ò", "½")
SHIFT = 29
IN_MM = 25.4

@dataclass
class W:
  text: str
  u0: float
  v0: float
  u1: float
  v1: float
  size: float
  turn: int
  raw: object

  @property
  def uc(self) -> float:
    return (self.u0 + self.u1) / 2

  @property
  def vc(self) -> float:
    return (self.v0 + self.v1) / 2

def _turn_of(angle: float) -> int:
  return int(round(angle / 90.0)) % 4

def frame_turn(words: list) -> int:
  weight: dict = {}
  for w in words:
    weight[_turn_of(w.angle)] = weight.get(_turn_of(w.angle), 0) + len(w.text)
  return max(weight, key=weight.get) if weight else 0

def to_frame(turn: int):
  c, s = (1, 0, -1, 0)[turn], (0, 1, 0, -1)[turn]
  return lambda x, y: (x * c + y * s, -x * s + y * c)

def upright_words(raw) -> tuple:
  turn = frame_turn(raw.words)
  f = to_frame(turn)
  out = []
  for w in raw.words:
    ua, va = f(w.x0, w.y0)
    ub, vb = f(w.x1, w.y1)
    out.append(W(w.text, min(ua, ub), min(va, vb), max(ua, ub), max(va, vb), w.size, (_turn_of(w.angle) - turn) % 4, w))
  return out, f

def upright_lines(raw, f, min_len: float = 12.0) -> tuple:
  s = raw.segs
  hs, vs, ds = [], [], []
  for i in range(len(s) // 5):
    x0, y0, x1, y1, _w = s[5 * i:5 * i + 5]
    u0, v0 = f(x0, y0)
    u1, v1 = f(x1, y1)
    length = math.hypot(u1 - u0, v1 - v0)
    
    if length < min_len:
      continue
    tol = max(1.5, 0.004 * length)
    if abs(v1 - v0) <= tol:
      hs.append((min(u0, u1), max(u0, u1), (v0 + v1) / 2))
    elif abs(u1 - u0) <= tol:
      vs.append((min(v0, v1), max(v0, v1), (u0 + u1) / 2))
    else:
      ds.append((u0, v0, u1, v1))
  return hs, vs, ds

def _merge(lines: list, gap: float = 1.5) -> list:
  out: list = []
  for a, b, k in sorted(lines, key=lambda t: (round(t[2] / 1.5), t[0])):
    for o in out:
      if abs(o[2] - k) <= 1.5 and a <= o[1] + gap and b >= o[0] - gap:
        o[0], o[1] = min(o[0], a), max(o[1], b)
        break
    else:
      out.append([a, b, k])
  return out

def decode_digits(text: str) -> str:
  if not any(ord(ch) < 0x20 for ch in text):
    return text.replace("ò", "½")
  out = []
  for ch in text:
    if ch in FRACTION_GLYPHS:
      out.append("½")
    elif ord(ch) < 0x60:
      out.append(chr(ord(ch) + SHIFT))
    else:
      out.append(ch)
  return "".join(out)

def damaged(text: str) -> bool:
  return any(ord(ch) < 0x20 for ch in text) or any(ch in FRACTION_GLYPHS for ch in text)

def parse_size(text: str) -> tuple | None:
  t = text.replace(" ", "").replace("×", "x")
  m = SIZE_RE.match(t)
  if not m:
    return None
  a = float(m.group(1)) + (0.5 if m.group(2) else 0.0)
  b = float(m.group(3)) + (0.5 if m.group(4) else 0.0)
  return a, b

def parse_steel(text: str) -> tuple | None:
  m = STEEL_RE.match(text.replace(" ", ""))
  return (int(m.group(1)), int(m.group(2))) if m else None

def parse_spacing(text: str) -> dict | None:
  m = SPACING_RE.match(text.replace(" ", "").replace("'", '"').replace('""', '"'))
  if not m:
    return None
  first, second = int(m.group(2)), int(m.group(3)) if m.group(3) else None
  return {"bar_no": int(m.group(1)), "end": first, "mid": second if second else first, "text": f'#{m.group(1)}@{first}"' + (f'/{second}"' if second else "") + "C/C"}

def _dim_inches(words: list) -> list:
  small = [w for w in words if w.size <= 7.5]
  out = []
  
  used: set = set()
  for w in small:
    t = w.text
    if id(w) in used or damaged(t):
      continue
    m = re.match(r"^(?:(\d+)'-?)?(\d+)?\"?$", t)
    if not m or not (m.group(1) or m.group(2)):
      continue
    feet, tail = int(m.group(1) or 0), m.group(2)
    half = next((o for o in small if o is not w and id(o) not in used and re.match(r"^[248]\"$", o.text) and abs(o.uc - w.uc) + abs(o.vc - w.vc) < 16 and o.turn == w.turn and not (feet == 0 and tail is None)), None)
    if half is not None and tail and len(tail) >= 2 and "'" in t:
      den = int(half.text[0])
      whole, num = int(tail[:-1]), int(tail[-1])
      if 1 <= num < den:
        used.add(id(half))
        out.append({"inches": feet * 12 + whole + num / den, "text": f"{t}+{half.text}", "u": w.uc, "v": w.vc})
        continue
    out.append({"inches": feet * 12 + float(tail or 0), "text": t, "u": w.uc, "v": w.vc})
  return out

def _near(a: float, b: float, tol: float) -> bool:
  return abs(a - b) <= tol

def _grid(hs: list, vs: list, box: tuple) -> tuple:
  u0, v0, u1, v1 = box
  hh = [h for h in _merge(hs) if h[0] <= u0 + 4 and h[1] >= u1 - 4 and v0 - 3 <= h[2] <= v1 + 3]
  vv = [v for v in _merge(vs) if v[0] <= v0 + 4 and v[1] >= v1 - 4 and u0 - 3 <= v[2] <= u1 + 3]
  return sorted({round(h[2], 1) for h in hh}, reverse=True), sorted({round(v[2], 1) for v in vv})

def _floor_headers(words: list) -> list:
  out = []
  for w in words:
    if w.text in FLOOR_WORDS and w.turn == 0:
      nxt = next((o for o in words if o.text == "FLOOR" and o.turn == 0 and abs(o.vc - w.vc) < 3 and 0 <= o.u0 - w.u1 < 8), None)
      out.append({"floor": FLOOR_WORDS[w.text], "u": (w.u0 + (nxt.u1 if nxt else w.u1)) / 2, "v": w.vc, "w": w})
  return out

def _tables(words: list) -> list:
  heads = [w for w in words if w.text in MARK_HEADERS and w.turn == 0]
  floors = _floor_headers(words)
  
  out = []
  for h in sorted(heads, key=lambda w: w.u0):
    mine = [f for f in floors if abs(f["v"] - h.vc) < 4 and f["u"] > h.u1]
    if not mine:
      continue
    out.append({"head": h, "floors": mine})
  for i, t in enumerate(out):
    right = out[i + 1]["head"].u0 if i + 1 < len(out) else 1e9
    t["floors"] = [f for f in t["floors"] if f["u"] < right]
  return out

def _labels(words: list, col: tuple, rows: tuple) -> dict:
  lines: dict = {}
  for w in words:
    if w.turn != 0 or not (col[0] <= w.uc <= col[1]) or not (rows[1] <= w.vc <= rows[0]):
      continue
    if w.text in ("SIZE", "STEEL", "SPACING", "AT", "MID", "JOINT"):
      lines.setdefault(round(w.vc / 3.0), []).append(w)
  out = {}
  for k, ws in lines.items():
    names = {w.text for w in ws}
    kind = "SIZE" if "SIZE" in names else "STEEL" if "STEEL" in names else "MID" if "MID" in names else "JOINT" if "JOINT" in names else None
    if kind:
      out[kind] = sum(w.vc for w in ws) / len(ws)
  return out

def _line_text(words: list, vc: float, cell: tuple, height: float) -> list:
  hit = [w for w in words if w.turn == 0 and cell[0] <= w.uc <= cell[1] and abs(w.vc - vc) <= 0.55 * height and w.size >= 7.0 and not w.text in ("SIZE", "STEEL", "SPACING", "AT", "MID", "JOINT")]
  return sorted(hit, key=lambda w: w.u0)

def _struck(ds: list, cell: tuple, vrange: tuple) -> bool:
  u0, u1 = cell
  v1, v0 = vrange
  diag = math.hypot(u1 - u0, v1 - v0)
  for a, b, c, d in ds:
    if min(a, c) >= u0 - 4 and max(a, c) <= u1 + 4 and min(b, d) >= v0 - 4 and max(b, d) <= v1 + 4 and math.hypot(c - a, d - b) >= 0.8 * diag:
      return True
  return False

def _bars(raw, f, cell: tuple, vrange: tuple) -> dict:
  u0, u1 = cell
  v1, v0 = vrange
  items = []
  for r in raw.rings:
    if not r.fill:
      continue
    ua, va = f(r.bbox[0], r.bbox[1])
    ub, vb = f(r.bbox[2], r.bbox[3])
    box = (min(ua, ub), min(va, vb), max(ua, ub), max(va, vb))
    if max(box[2] - box[0], box[3] - box[1]) > RD.SKETCH_BAR_MAX_PT:
      continue
    if u0 <= (box[0] + box[2]) / 2 <= u1 and v0 <= (box[1] + box[3]) / 2 <= v1:
      items.append((box, r.area))
  parent = list(range(len(items)))

  def find(i: int) -> int:
    while parent[i] != i:
      parent[i] = parent[parent[i]]
      i = parent[i]
    return i

  for i in range(len(items)):
    a = items[i][0]
    for j in range(i + 1, len(items)):
      b = items[j][0]
      if a[0] <= b[2] + 0.2 and b[0] <= a[2] + 0.2 and a[1] <= b[3] + 0.2 and b[1] <= a[3] + 0.2:
        parent[find(i)] = find(j)
        
  groups: dict = {}
  for i, it in enumerate(items):
    groups.setdefault(find(i), []).append(it)
  bars = []
  for g in groups.values():
    box = (min(x[0][0] for x in g), min(x[0][1] for x in g), max(x[0][2] for x in g), max(x[0][3] for x in g))
    w, h = box[2] - box[0], box[3] - box[1]
    fill = sum(x[1] for x in g) / max(w * h, 1e-9)
    if RD.SKETCH_BAR_MIN_PT <= min(w, h) and max(w, h) <= RD.SKETCH_BAR_MAX_PT and 0.8 <= w / max(h, 1e-9) <= 1.25 and fill >= 0.6:
      bars.append(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2, max(w, h)))
  return {"count": len(bars), "centres": [(round(b[0], 1), round(b[1], 1)) for b in bars]}

def _sketch_sides(dims: list) -> list:
  seen = sorted({round(d["inches"] * 2) / 2 for d in dims})
  return [s for s in seen if s >= 4.0]

def check_sketch(size_in: tuple | None, dims: list, bars: int, count: int | None) -> dict:
  out = {"sketch_sides_in": _sketch_sides(dims), "bars_drawn": bars, "conflicts": []}
  if size_in:
    want = {round(size_in[0] * 2) / 2, round(size_in[1] * 2) / 2}
    sides = out["sketch_sides_in"]
    if len(sides) >= 2 and any(all(abs(s - w) > RD.SKETCH_SIDE_TOL_IN for w in want) for s in sides):
      out["conflicts"].append({"kind": "SIZE_TEXT_VS_SKETCH", "printed_in": [size_in[0], size_in[1]], "sketch_in": sides})
  if count is not None and bars and bars != count:
    out["conflicts"].append({"kind": "BARS_TEXT_VS_SKETCH", "printed": count, "drawn": bars})
  return out

def _size_of(tokens: list, dims: list) -> dict:
  raw = "".join(w.text for w in tokens)
  
  if not raw:
    return {"raw": "", "size_in": None, "how": None}
  text, how = raw, "TEXT"
  if damaged(raw):
    text, how = decode_digits(raw), "DECODED"
  size = parse_size(text)
  if size is None and how == "DECODED":
    m = re.match(r"^(\d+)(½)?\"?[x×]\"?$", text)
    sides = _sketch_sides(dims)
    if m:
      first = float(m.group(1)) + (0.5 if m.group(2) else 0.0)
      rest = [s for s in sides if abs(s - first) > RD.SKETCH_SIDE_TOL_IN]
      if any(abs(s - first) <= RD.SKETCH_SIDE_TOL_IN for s in sides) and len(rest) == 1:
        return {"raw": raw, "text": text, "size_in": (first, rest[0]), "how": "DECODED_PARTIAL", "confirmed": False}
    
  if size is None:
    return {"raw": raw, "size_in": None, "how": None}
  if how == "DECODED":
    sides = _sketch_sides(dims)
    ok = all(any(abs(s - side) <= RD.SKETCH_SIDE_TOL_IN for s in sides) for side in size)
    return {"raw": raw, "text": text, "size_in": size, "how": "DECODED", "confirmed": bool(ok)}
  return {"raw": raw, "text": text, "size_in": size, "how": "TEXT", "confirmed": True}

def read(raw) -> dict | None:
  if not raw.words or not len(raw.segs):
    return None

  words, f = upright_words(raw)
  tables = _tables(words)
  if not tables:
    return None
  hs, vs, ds = upright_lines(raw, f)
  cells: list = []
  for t in tables:
    head = t["head"]
    ys = [w.vc for w in words if w.turn == 0 and MARK_RE.match(w.text.upper()) and w.size >= 12 and w.u0 >= head.u0 - 25 and w.u1 <= head.u1 + 40 and w.vc < head.vc]
    if not ys:
      continue
    span_u = (head.u0 - 25, max(fl["u"] for fl in t["floors"]) + 120)
    hh = [h for h in _merge(hs) if h[1] - h[0] >= 0.7 * (span_u[1] - span_u[0]) * 0.5 and h[0] <= head.u0 + 5]
    rows_v = sorted({round(h[2], 1) for h in hh if h[2] < head.vc and h[2] > min(ys) - 130}, reverse=True)
    vv = [v for v in _merge(vs) if v[1] - v[0] >= 0.5 * (head.vc - min(ys)) and v[2] >= span_u[0] - 5 and v[2] <= span_u[1] + 5 and v[1] >= head.vc - 2]
    cols_u = sorted({round(v[2], 1) for v in vv})
    if len(rows_v) < 2 or len(cols_u) < 2:
      continue
    below = [r for r in rows_v if r < head.vc - 2]
    bounds = [r for r in below]
    marks = []
    
    for w in words:
      if w.turn == 0 and MARK_RE.match(w.text.upper()) and w.size >= 12 and w.u0 >= head.u0 - 25 and w.u1 <= head.u1 + 40 and w.vc < head.vc:
        marks.append(w)
    mark_col = (max([c for c in cols_u if c <= head.uc] or [head.u0 - 5]), min([c for c in cols_u if c > head.uc] or [head.u1 + 5]))
    for m in sorted(marks, key=lambda w: -w.vc):
      top = min([b for b in bounds if b >= m.vc] or [head.vc])
      bot = max([b for b in bounds if b < m.vc] or [m.vc - 90])
      labels = _labels(words, mark_col, (top, bot))
      for fl in t["floors"]:
        left = max([c for c in cols_u if c <= fl["u"]] or [fl["u"] - 40])
        right = min([c for c in cols_u if c > fl["u"]] or [fl["u"] + 40])
        cell = (left, right)
        vr = (top, bot)
        height = 8.0
        cells.append({"mark": m.text.upper(), "floor": fl["floor"], "cell": cell, "vrange": vr, "labels": labels, "mark_word": m, "height": height})
  if not cells:
    return None
  out: list = []
  
  for c in cells:
    cell, vr, labels = c["cell"], c["vrange"], c["labels"]
    inside = [w for w in words if cell[0] <= w.uc <= cell[1] and vr[1] <= w.vc <= vr[0]]
    rec = {"mark": c["mark"], "floor": c["floor"], "cell_uv": [cell[0], vr[1], cell[1], vr[0]]}
    if _struck(ds, cell, vr):
      rec.update(state="NONE", why="struck")
      out.append(rec)
      continue
  
    lines = {k: _line_text(inside, v, cell, c["height"]) for k, v in labels.items()}
    if not any(lines.values()):
      rec.update(state="NONE", why="blank")
      out.append(rec)
      continue
  
    dims = _dim_inches(inside)
    size = _size_of(lines.get("SIZE") or [], dims)
    steel = parse_steel(" ".join(w.text for w in lines.get("STEEL") or []))
    mid = parse_spacing("".join(w.text for w in lines.get("MID") or []))
    joint = parse_spacing("".join(w.text for w in lines.get("JOINT") or []))
    bars = _bars(raw, f, cell, vr)
    check = check_sketch(size.get("size_in"), dims, bars["count"], steel[0] if steel else None)
    anchor = (lines.get("SIZE") or [None])[0]
    rec.update(state="READ", size=size, steel=steel, mid=mid, joint=joint, sketch=check, anchor_native=[anchor.raw.x0, anchor.raw.y0] if anchor else None)
    out.append(rec)
  return {"kind": "COLUMN_SCHEDULE", "cells": out, "tables": len(tables)}

def cell_attrs(rec: dict) -> dict:
  if rec.get("state") != "READ":
    return {}

  a: dict = {"floor": rec["floor"], "key": f"{rec['mark']}:{rec['floor']}"}
  size = (rec.get("size") or {}).get("size_in")
  if size:
    a["size_mm"] = [round(size[0] * IN_MM, 1), round(size[1] * IN_MM, 1)]
  if rec.get("steel"):
    a["bar_count"], a["bar_dia_no"] = rec["steel"]
  if rec.get("mid"):
    a["stirrup_mid_spacing_in"] = rec["mid"]["mid"]
  if rec.get("joint"):
    a["stirrup_joint_spacing_in"] = rec["joint"]["end"]
  if rec.get("mid"):
    a["stirrup"] = rec["mid"]["text"]
  return a

SIZE_PART = r"(\d+(?:\.\d+)?)(½)?\"?\s*[x×]\s*(\d+(?:\.\d+)?)(½)?\"?"
TITLE_RE = re.compile(r"^([A-Z]{1,3}\d*[a-z]?(?:-\d+)?)-?\(" + SIZE_PART + r"\)$")
TITLE_BARE_RE = re.compile(r"^([A-Z]{1,3}\d*[a-z]?)-" + SIZE_PART + r"$")
CALLOUT_RE = re.compile(r"^(\d+)-?#(\d+)$")

def _decoded(text: str) -> str:
  return decode_digits(text) if damaged(text) else text

def _title_match(text: str):
  t = text.replace(" ", "")
  return TITLE_RE.match(t) or TITLE_BARE_RE.match(t)

def _title_words(words: list) -> list:
  out = []
  used: set = set()
  line = sorted([w for w in words if w.turn == 0], key=lambda w: w.u0)
  for i, w in enumerate(line):
    if id(w) in used:
      continue
    t = _decoded(w.text)
    m = _title_match(t)
    parts = [w]
    if not m:
      for o in line:
        if id(o) in used or o is w or abs(o.vc - parts[-1].vc) > 3.0 or not (-0.5 <= o.u0 - parts[-1].u1 <= 6.0):
          continue
        parts.append(o)
        t = "".join(_decoded(p.text) for p in parts)
        m = _title_match(t)
        if m or len(parts) >= 3:
          break
      
    if not m:
      continue
    for p in parts:
      used.add(id(p))
    width = float(m.group(2)) + (0.5 if m.group(3) else 0.0)
    depth = float(m.group(4)) + (0.5 if m.group(5) else 0.0)
    out.append({"mark": m.group(1), "width_in": width, "depth_in": depth, "word": parts[0], "decoded": any(damaged(p.text) for p in parts)})
  return out

def _callouts(words: list) -> list:
  out = []
  
  bars = [w for w in words if w.turn == 0 and CALLOUT_RE.match(w.text.replace(" ", ""))]
  for b in bars:
    nxt = next((o for o in words if o.turn == 0 and o.text in ("Thr.", "Ext.", "Thr", "Ext", "Thru.") and abs(o.vc - b.vc) <= 1.6 and -1.0 <= o.u0 - b.u1 <= 6.0), None)
    if nxt is None:
      continue
    out.append({"text": f"{b.text} {'Thr.' if nxt.text.startswith('Thr') else 'Ext.'}", "v": b.vc, "u": b.uc})
  return out

def read_beam_sections(raw) -> dict | None:
  if not raw.words:
    return None
  words, _f = upright_words(raw)
  titles = sorted(_title_words(words), key=lambda t: -t["word"].vc)
  if len(titles) < 2:
    return None

  sections = []
  for i, t in enumerate(titles):
    tw = t["word"]
    top = titles[i - 1]["word"].vc if i else tw.vc + RD.SECTION_STACK_PT
    if top - tw.vc > 2 * RD.SECTION_STACK_PT:
      top = tw.vc + RD.SECTION_STACK_PT
      
    box = [w for w in words if tw.vc + 1.0 < w.vc < top - 1.0 and abs(w.uc - tw.uc) <= RD.SECTION_HALF_WIDTH_PT]
    stir = next((w for w in sorted(box, key=lambda w: -w.vc) if w.turn == 0 and SPACING_RE.match(w.text.replace(" ", "").replace("'", '"'))), None)
    calls = _callouts(box)
    mid = stir.vc if stir else (max(c["v"] for c in calls) + min(c["v"] for c in calls)) / 2 if calls else None
    topb = [c["text"] for c in sorted(calls, key=lambda c: -c["v"]) if mid is not None and c["v"] > mid]
    botb = [c["text"] for c in sorted(calls, key=lambda c: -c["v"]) if mid is not None and c["v"] <= mid]
    dims = [d["inches"] for d in _dim_inches(box)]
    
    conflicts = []
    if len(dims) >= 2:
      for name, want in (("width", t["width_in"]), ("depth", t["depth_in"])):
        if not any(abs(d - want) <= RD.SKETCH_SIDE_TOL_IN for d in dims):
          conflicts.append({"kind": "SIZE_TEXT_VS_SKETCH", "side": name, "printed_in": want, "sketch_in": sorted(set(round(d * 2) / 2 for d in dims))})
    sections.append({"mark": t["mark"], "width_in": t["width_in"], "depth_in": t["depth_in"], "top_bars": topb, "bottom_bars": botb, "stirrup": parse_spacing(stir.text)["text"] if stir and parse_spacing(stir.text) else None,
      "decoded": t["decoded"], "sketch_dims": len(dims), "conflicts": conflicts, "anchor_native": [tw.raw.x0, tw.raw.y0], "uv": [tw.uc, tw.vc]})
  return {"kind": "BEAM_SECTION", "sections": sections}

def beam_section_attrs(rec: dict) -> dict:
  a = {"key": f"{rec['mark']}-section", "width_in": rec["width_in"], "depth_in": rec["depth_in"], "width_mm": round(rec["width_in"] * IN_MM, 1), "depth_mm": round(rec["depth_in"] * IN_MM, 1)}
  if rec.get("top_bars"):
    a["top_bars"] = list(rec["top_bars"])
  if rec.get("bottom_bars"):
    a["bottom_bars"] = list(rec["bottom_bars"])
  if rec.get("stirrup"):
    a["stirrup"] = rec["stirrup"]
  return a

PLANTED_RE = re.compile(r"^PC-?\d*[A-Z]?$")

def read_planted(raw) -> dict | None:
  if not raw.words:
    return None
  words, _f = upright_words(raw)
  labels = [w for w in words if w.turn == 0 and w.size >= 8.0 and PLANTED_RE.match(w.text.upper())]
  if not labels:
    return None
  return {"kind": "PLANTED_LABELS", "labels": [{"mark": w.text.upper(), "at": [round((w.raw.x0 + w.raw.x1) / 2, 1), round((w.raw.y0 + w.raw.y1) / 2, 1)], "uv": [round(w.uc, 1), round(w.vc, 1)]} for w in labels]}

def read_all(raw) -> dict | None:
  out: dict = {}
  
  sched = read(raw)
  if not (sched and sched.get("cells")):
    from app.modules.drawings_boq.takeoff.extract import schedule_axes
    sched = schedule_axes.read(raw)
  if sched and sched.get("cells"):
    out["column_schedule"] = sched
  beams = read_beam_sections(raw)
  if beams and beams.get("sections"):
    out["beam_sections"] = beams
  planted = read_planted(raw)
  if planted:
    out["planted_labels"] = planted
  from app.modules.drawings_boq.takeoff.extract import beam_callouts
  callouts = beam_callouts.read(raw)
  if callouts:
    out["beam_callouts"] = callouts
  from app.modules.drawings_boq.takeoff.extract import slab_callouts
  slabs = slab_callouts.read(raw)
  if slabs:
    out[slab_callouts.SOURCE_KEY] = slabs
  from app.modules.drawings_boq.takeoff.extract import finish_spec_items
  specs = finish_spec_items.read(raw)
  if specs:
    out[finish_spec_items.SOURCE_KEY] = specs
  from app.modules.drawings_boq.takeoff.extract import drain_labels
  drains = drain_labels.read(raw)
  if drains:
    out[drain_labels.SOURCE_KEY] = drains
  from app.modules.drawings_boq.takeoff.extract import level_marks
  levels = level_marks.read(raw)
  if levels:
    out[level_marks.SOURCE_KEY] = levels
  from app.modules.drawings_boq.takeoff.extract import tube_fixtures
  tubes = tube_fixtures.read(raw)
  if tubes:
    out[tube_fixtures.SOURCE_KEY] = tubes
  return out or None

