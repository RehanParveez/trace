from __future__ import annotations
import math
import re

from app.modules.drawings_boq.takeoff.prep import page_unit as PU

CAPTION = re.compile(r"FOOTING\s+FOR\s+(\d+(?:\.\d+)?)\s*[\"”'’]*\s*(?:THICK|THK)?", re.I)
STEEL = re.compile(r"#\s*(\d+)\s*@\s*(\d+(?:\.\d+)?)\s*[\"”]?", re.I)
INCH_LABEL = re.compile(r"^(\d+)\s*[\"”]$")
V_TOL = 0.12          
MIN_RUN = 1.2         
JOIN_GAP = 0.35
CLOSE_SHARE = 0.8     
AXIS_TOL = 0.35
SNAP_IN = 0.5
LABEL_AGREE = 0.04
MAX_PICTURE_Z = 175.0
MAX_HALF_X = 60.0
MM = 25.4
BRICK_WALLS_IN = (4.5, 9.0, 13.5)
SEC_CAPTION = re.compile(r"SEC\.?\s*(?P<mark>[A-Z]{1,2}\d{1,2})\s*-\s*(?P=mark)?.*?(?P<t>\d+(?:\s*½|\s*1\s*/\s*2|\.5)?)\s*[\"”]\s*TH(?:ICK|K)\.?\s*(?P<where>INTERIOR|EXTERIOR|INTERNAL|EXTERNAL)?\s*.*?WALL\s+FOOTING", re.I)
SEC_HEAD = re.compile(r"^SEC\.?\s*[A-Z]{1,2}\d{1,2}\s*-", re.I)
FEET_INCHES = re.compile(r"^(\d+)\s*'\s*-?\s*(\d+)?\s*[\"”]?$")
LAYER_LABEL = re.compile(r"(?P<n>\d+(?:\s*½|\s*1\s*/\s*2|\.5)?)\s*[\"”]\s*THICK\s+(?P<what>P\.?\s*C\.?\s*C|SAND)", re.I)
CAPTION_X_REACH = 40.0
CAPTION_LINE_GAP = 22.0
CAPTION_LINES_MAX = 4
SEC_HALF_X = 80.0
SEC_PICTURE_Z = 240.0
SEC_AXIS_SLACK = 12.0
STEP_MIN_OFFSET = 1.0
STEP_Z_TOL = 0.8
STEP_MIN_H = 4.0
STEP_MAX = 12
STEP_SYMMETRY = 0.8
PAIRS_TRIED = 6
LAYER_AGREE_IN = 0.75
LABEL_REACH = 170.0
WIDTH_AGREE_IN = 1.0
MARK_WALL_AGREE = 0.12
BAD_ISSUES = {"WIDTHS_NOT_STEPPED", "ECCENTRIC_FOOTING", "DIMENSIONS_NOT_ON_HALF_INCH", "NO_FOOTING_FOUND", "NO_STEPS_FOUND", "PICTURE_NOT_FOUND", "LAYERS_DISAGREE", "LAYERS_UNLABELLED", "BASE_WIDTH_DISAGREES",
  "DEPTH_NOT_PRINTED", "DEPTH_LESS_THAN_LAYERS"}

def _frame(words: list):
  votes: dict = {}
  
  for w in words:
    a = int(round(w.angle / 90.0)) % 4
    votes[a] = votes.get(a, 0) + len(w.text)
  a = max(votes, key=votes.get) if votes else 0
  th = math.radians(90 * a)
  return (math.cos(th), math.sin(th)), (-math.sin(th), math.cos(th))

def _lines(words: list, u: tuple, w: tuple) -> list:
  """[{"text", "X", "Z", "x0", "x1"}]: the words of one baseline joined, in the text frame (X to the right, Z up)."""
  rows: dict = {}
  for wd in words:
    X, Z = wd.cx * u[0] + wd.cy * u[1], wd.cx * w[0] + wd.cy * w[1]
    rows.setdefault(round(Z / max(wd.size * 0.7, 1.0)), []).append((X, Z, wd))
  out = []
  for items in rows.values():
    items.sort(key=lambda t: t[0])
    group: list = []
    for it in items:
      if group:
        prev = group[-1][2]
        gap = it[0] - group[-1][0] - (prev.length + it[2].length) / 2.0
        if gap > 2.5 * max(prev.size, it[2].size, 1.0):
          out.append(_join(group))
          group = []
      group.append(it)
    if group:
      out.append(_join(group))
  return out

def _join(items: list) -> dict:
  return {"text": " ".join(t[2].text for t in items), "X": sum(t[0] for t in items) / len(items), "Z": sum(t[1] for t in items) / len(items), "x0": items[0][0], "x1": items[-1][0]}

def _merge(runs: list) -> list:
  runs.sort()
  out: list = []
  for pos, a, b in runs:
    for o in out:
      if abs(o[0] - pos) <= 0.15 and a <= o[2] + JOIN_GAP and b >= o[1] - JOIN_GAP:
        o[1], o[2] = min(o[1], a), max(o[2], b)
        break
    else:
      out.append([pos, a, b])
  return out

def _snap(inches: float) -> float:
  return round(inches / SNAP_IN) * SNAP_IN

def _label_inches(tokens: list) -> float | None:
  nums = [t for t in tokens]
  if not nums:
    return None

  joined = " ".join(nums)
  m = re.match(r"^(\d+)\s+(\d)\s+(\d)\s*[\"”]?$", joined)
  if m and int(m.group(3)):
    return int(m.group(1)) + int(m.group(2)) / int(m.group(3))
  m = re.match(r"^(\d{1,2})(\d)\s+(\d)\s*[\"”]?$", joined)
  if m and int(m.group(3)) and int(m.group(2)) < int(m.group(3)):
    return int(m.group(1)) + int(m.group(2)) / int(m.group(3))
  m = re.match(r"^(\d+)\s*[\"”]$", joined)
  if m:
    return float(m.group(1))
  return None

def rectangles(vruns: list, hruns: list, axis: float) -> list:
  def closed(z: float, xl: float, xr: float) -> bool:
    cov = 0.0
    for hz, a, b in hruns:
      if abs(hz - z) <= 0.35:
        cov += max(0.0, min(b, xr + 0.3) - max(a, xl - 0.3))
    return cov >= CLOSE_SHARE * (xr - xl)
  out = []
  for i in range(len(vruns)):
    for j in range(i + 1, len(vruns)):
      xl, xr = vruns[i][0], vruns[j][0]
      if xl > xr:
        xl, xr = xr, xl
      if xr - xl < 2.0 or not (xl - 0.3 <= axis <= xr + 0.3):
        continue
    
      lo, hi = max(vruns[i][1], vruns[j][1]), min(vruns[i][2], vruns[j][2])
      if hi - lo < MIN_RUN or abs(vruns[i][1] - vruns[j][1]) > 0.4 or abs(vruns[i][2] - vruns[j][2]) > 0.4:
        continue
      if closed(lo, xl, xr) and closed(hi, xl, xr):
        out.append({"xl": xl, "xr": xr, "z0": lo, "z1": hi, "w": xr - xl, "h": hi - lo})
  seen, uniq = set(), []
  for r in sorted(out, key=lambda r: (-r["z1"], r["w"])):
    k = (round(r["w"], 1), round(r["z0"], 1), round(r["z1"], 1))
    if k not in seen:
      seen.add(k)
      uniq.append(r)
  return uniq

def _wall_width(vruns: list, axis: float, z_top: float) -> float | None:
  best = None
  for i in range(len(vruns)):
    for j in range(i + 1, len(vruns)):
      xl, xr = sorted((vruns[i][0], vruns[j][0]))
      if not (xl < axis < xr) or xr - xl < 2.0:
        continue
      lo, hi = max(vruns[i][1], vruns[j][1]), min(vruns[i][2], vruns[j][2])
      if hi - lo >= 15.0 and (best is None or xr - xl < best):
        best = xr - xl
  return best

def _stack(rects: list) -> dict:
  rs = sorted(rects, key=lambda r: -r["z1"])
  issues: list = []
  if not rs:
    return {"steps": [], "footing": None, "pcc": None, "issues": ["NO_RECTANGLES"]}
  for a, b in zip(rs, rs[1:]):
    if b["w"] + 0.3 < a["w"]:
      issues.append("WIDTHS_NOT_STEPPED")
      break
  
  pcc = footing = None
  body = list(rs)
  if len(body) >= 2 and body[-1]["h"] < 0.6 * body[-2]["h"] and body[-1]["w"] >= body[-2]["w"] - 0.3:
    pcc = body.pop()
  if body and len(body) >= 2:
    footing = body.pop()
  elif body and pcc is not None:
    footing = body.pop()
  return {"steps": body, "footing": footing, "pcc": pcc, "issues": issues}

def _steel(words: list, X0: float, X1: float, Z0: float, Z1: float, u: tuple, w: tuple) -> list:
  out: list = []
  for wd in words:
    X, Z = wd.cx * u[0] + wd.cy * u[1], wd.cx * w[0] + wd.cy * w[1]
    if X0 <= X <= X1 and Z0 <= Z <= Z1:
      m = STEEL.search(wd.text)
      if m:
        item = {"bar": int(m.group(1)), "spacing_in": float(m.group(2)), "text": wd.text}
        if item not in out:
          out.append(item)
  return out

def _inside(words: list, r: dict, u: tuple, w: tuple) -> list:
  got = []
  for wd in words:
    X, Z = wd.cx * u[0] + wd.cy * u[1], wd.cx * w[0] + wd.cy * w[1]
    if r["xl"] <= X <= r["xr"] and r["z0"] <= Z <= r["z1"]:
      got.append((X, Z, wd.text))
  got.sort(key=lambda t: (round(t[0] / 3), -t[1]))
  return [t[2] for t in got]

def _calibrate(wall_in: float, wall_w: float | None, steps: list, words: list, u: tuple, w: tuple) -> dict:
  """mm per point of the picture, from the wall thickness in the caption and the widths printed inside the steps."""
  from_wall = (wall_in * MM / wall_w) if wall_w else None
  
  labels: list = []
  for r in steps:
    inches = _label_inches(_inside(words, r, u, w))
    if inches:
      labels.append({"label_in": inches, "width_pt": r["w"], "mm_per_pt": inches * MM / r["w"]})
  from_labels = sorted(l["mm_per_pt"] for l in labels)
  lab = from_labels[len(from_labels) // 2] if from_labels else None
  
  if from_wall and lab:
    if abs(from_wall - lab) / lab <= LABEL_AGREE:
      return {"mm_per_pt": (from_wall + lab) / 2.0, "basis": "WALL_AND_LABELS", "labels": labels, "agree": True}
    implied = lab * wall_w / MM
    usual = min(BRICK_WALLS_IN, key=lambda s: abs(s - implied))
    spread = (from_labels[-1] - from_labels[0]) / lab
    if len(from_labels) >= 2 and spread <= LABEL_AGREE and abs(implied - usual) <= 0.1 * usual:
      return {"mm_per_pt": lab, "basis": "LABELS_WALL_FROM_PICTURE", "labels": labels, "agree": True, "wall_in": usual, "caption_wall_in": wall_in}
    return {"mm_per_pt": None, "basis": "DISAGREE", "labels": labels, "agree": False, "from_wall": from_wall, "from_labels": lab}
  if lab:
    return {"mm_per_pt": lab, "basis": "LABELS", "labels": labels, "agree": True}
  if from_wall:
    return {"mm_per_pt": from_wall, "basis": "WALL", "labels": labels, "agree": True}
  return {"mm_per_pt": None, "basis": "NONE", "labels": labels, "agree": False}

def _inches(text: str | None) -> float | None:
  """Inches from 9, 4½, 4.5 or 4 1/2."""
  s = (text or "").strip().replace("½", ".5")
  m = re.match(r"^(\d+)\s*1\s*/\s*2$", s)
  if m:
    return int(m.group(1)) + 0.5
  try:
    return float(re.sub(r"\s+", "", s))
  except ValueError:
    return None

def _feet_inches(text: str) -> float | None:
  m = FEET_INCHES.match((text or "").strip())
  return None if not m else int(m.group(1)) * 12.0 + int(m.group(2) or 0)

def sec_captions(lines: list) -> list:
  """The sections whose caption is SEC. W1-W1 over TYP. 4½" THICK INTERIOR over BRICK WALL FOOTING, each line of it its own line of text: the head line and the lines under it, read as one."""
  out: list = []
  for head in lines:
    if not SEC_HEAD.match(head["text"].strip()):
      continue
    block, last = [head], head
    under = sorted((l for l in lines if l is not head and abs(l["X"] - head["X"]) <= CAPTION_X_REACH and l["Z"] < head["Z"]), key=lambda l: -l["Z"])
    for l in under:
      if len(block) > CAPTION_LINES_MAX or last["Z"] - l["Z"] > CAPTION_LINE_GAP:
        break
      block.append(l)
      last = l
    text = " ".join(l["text"] for l in block)
    m = SEC_CAPTION.search(text)
    thick = _inches(m.group("t")) if m else None
    if not m or not thick:
      continue
    where = (m.group("where") or "").upper()
    out.append({**head, "text": text, "mark": m.group("mark").upper(), "wall_in": thick, "exterior": True if where in ("EXTERIOR", "EXTERNAL") else False if where else None, "Z_bottom": last["Z"]})
  return out

def _spans(hruns: list, z: float, a: float, b: float) -> bool:
  lo, hi = min(a, b), max(a, b)
  cov = sum(max(0.0, min(h[2], hi) - max(h[1], lo)) for h in hruns if abs(h[0] - z) <= 0.4)
  return cov >= 0.6 * (hi - lo)

def _wall_pairs(vruns: list) -> list:
  """[(left x, right x, z where the wall ends on the top step)], the narrowest pairs of tall vertical lines first: the two faces of the wall."""
  seen: set = set()
  found = []
  for i in range(len(vruns)):
    for j in range(i + 1, len(vruns)):
      xl, xr = sorted((vruns[i][0], vruns[j][0]))
      lo, hi = max(vruns[i][1], vruns[j][1]), min(vruns[i][2], vruns[j][2])
      if xr - xl < 2.0 or hi - lo < 15.0 or (round(xl, 1), round(xr, 1)) in seen:
        continue
      seen.add((round(xl, 1), round(xr, 1)))
      ends = [min(v[1] for v in vruns if abs(v[0] - x) <= 0.2 and v[2] - v[1] >= STEP_MIN_H) for x in (xl, xr)]
      found.append((xl, xr, max(ends)))
  return sorted(found, key=lambda t: t[1] - t[0])[:PAIRS_TRIED]

def _chain(vruns: list, hruns: list, x0: float, z0: float, sign: int) -> list:
  """The steps going down and out from the wall on one side: each is a vertical line that starts where the one before it ended, with a horizontal line between them."""
  out: list = []
  cx, cz = x0, z0
  while len(out) < STEP_MAX:
    near = [v for v in vruns if sign * (v[0] - cx) >= STEP_MIN_OFFSET and abs(v[2] - cz) <= STEP_Z_TOL and v[2] - v[1] >= STEP_MIN_H and _spans(hruns, cz, cx, v[0])]
    if not near:
      break
    v = min(near, key=lambda r: sign * (r[0] - cx))
    out.append({"x": v[0], "z1": v[2], "z0": v[1]})
    cx, cz = v[0], v[1]
  return out

def _splits(hruns: list, xl: float, xr: float, z0: float, z1: float) -> list:
  zs: list = []
  for h in hruns:
    if z0 + 0.8 < h[0] < z1 - 0.8 and min(h[2], xr) - max(h[1], xl) >= 0.8 * (xr - xl) and all(abs(h[0] - z) > 0.5 for z in zs):
      zs.append(h[0])
  return sorted(zs, reverse=True)

def _printed(lines: list, x0: float, x1: float, z0: float, z1: float, near_x: float) -> float | None:
  got = [(abs(l["X"] - near_x), _feet_inches(l["text"])) for l in lines if x0 <= l["X"] <= x1 and z0 <= l["Z"] <= z1 and _feet_inches(l["text"]) is not None]
  return min(got)[1] if got else None

def read_stepped(index, words: list, u: tuple, w: tuple, lines: list, caps: list) -> list:
  out: list = []
  for cap in caps:
    rec = {"caption": cap["text"][:120], "mark": cap["mark"], "wall_in": cap["wall_in"], "exterior": cap["exterior"], "grammar": "SEC", "axis": round(cap["X"], 1), "read": "UNUSABLE", "issues": [], "steel": [],
      "masonry_only": True, "footing": None}
    out.append(rec)
    
    near = [abs(c["X"] - cap["X"]) for c in caps if c is not cap and abs(c["Z"] - cap["Z"]) < 40.0]
    half = min(SEC_HALF_X, 0.5 * min(near)) if near else SEC_HALF_X
    above = [c["Z_bottom"] for c in caps if c is not cap and abs(c["X"] - cap["X"]) < 2.0 * half and c["Z"] > cap["Z"] + 20.0]
    X0, X1, Z0 = cap["X"] - half, cap["X"] + half, cap["Z"] + 1.0
    Z1 = min([Z0 + SEC_PICTURE_Z] + [z - 2.0 for z in above])
    corners = [(X * u[0] + Z * w[0], X * u[1] + Z * w[1]) for X in (X0, X1) for Z in (Z0, Z1)]
    segs, _, _ = index.window(min(c[0] for c in corners), min(c[1] for c in corners), max(c[0] for c in corners), max(c[1] for c in corners), max_segments=60000)
    V, H = [], []
    
    for a, b, c, d, _k in segs:
      xa, za = a * u[0] + b * u[1], a * w[0] + b * w[1]
      xb, zb = c * u[0] + d * u[1], c * w[0] + d * w[1]
      if not (X0 <= xa <= X1 and X0 <= xb <= X1 and Z0 - 1.0 <= min(za, zb) and max(za, zb) <= Z1 + 1.0):
        continue
      if abs(xa - xb) < V_TOL and abs(za - zb) >= MIN_RUN:
        V.append((round((xa + xb) / 2, 2), min(za, zb), max(za, zb)))
      elif abs(za - zb) < V_TOL and abs(xa - xb) >= MIN_RUN:
        H.append((round((za + zb) / 2, 2), min(xa, xb), max(xa, xb)))
    V, H = _merge(V), _merge(H)
    main = None
    
    for xl, xr, zb in _wall_pairs(V):
      left, right = _chain(V, H, xl, zb, -1), _chain(V, H, xr, zb, 1)
      if max(len(left), len(right)) >= 2:
        main = left if len(left) >= len(right) else right
        break
    if main is None:
      rec["issues"].append("PICTURE_NOT_FOUND" if not V else "NO_STEPS_FOUND")
      continue
    sign = -1 if main is left else 1
    other = right if main is left else left
    wall_w = xr - xl
    base_z0, base_z1 = main[-1]["z0"], main[-1]["z1"]
    face = xr if sign < 0 else xl
    flush = not other and any(abs(v[0] - face) <= 0.5 and v[1] <= base_z0 + 1.0 and v[2] >= base_z1 - 1.0 for v in V)
    if other and (len(other) != len(main) or any(abs(abs(a["x"] - (xl if sign < 0 else xr)) - abs(b["x"] - face)) > STEP_SYMMETRY for a, b in zip(main, other))):
      rec["issues"].append("ECCENTRIC_FOOTING")
    elif not other and not flush:
      rec["issues"].append("ECCENTRIC_FOOTING")
    elif flush:
      rec["issues"].append("FLUSH_ONE_SIDE")
    offs = [abs(a["x"] - (xl if sign < 0 else xr)) for a in main]
    if other and len(other) == len(main):
      offs = [(o + abs(b["x"] - face)) / 2.0 for o, b in zip(offs, other)]
    grow = 1.0 if flush else 2.0
    ext = [(wall_w + grow * o) for o in offs]
    spans = [((xl - o, xr) if sign < 0 else (xl, xr + o)) if flush else (xl - o, xr + o) for o in offs]
    steps_pt = [{"z0": s["z0"], "z1": s["z1"], "w": wp, "h": s["z1"] - s["z0"], "xl": sp[0], "xr": sp[1]} for s, wp, sp in zip(main[:-1], ext[:-1], spans[:-1])]
    base = {"z0": base_z0, "z1": base_z1, "w": ext[-1], "h": base_z1 - base_z0}
    bx = spans[-1]
    
    cx = (bx[0] + bx[1]) / 2.0
    cal = _calibrate(cap["wall_in"], wall_w, steps_pt, words, u, w)
    rec["calibration"] = cal["basis"]
    wall_in = cal.get("wall_in") or cap["wall_in"]
    if cal.get("wall_in"):
      rec["wall_in"], rec["caption_wall_in"] = wall_in, cal["caption_wall_in"]
      rec["issues"].append("CAPTION_WALL_DIFFERS")
    if cal["mm_per_pt"] is None:
      rec["issues"].append("SCALE_DISAGREES" if cal["basis"] == "DISAGREE" else "SCALE_UNKNOWN")
      continue
    s = cal["mm_per_pt"]
    rec["scale_mm_per_pt"] = round(s, 4)
    snap_err = 0.0

    def dim(pt: float) -> float:
      nonlocal snap_err
      inches = pt * s / MM
      snapped = _snap(inches)
      snap_err = max(snap_err, abs(inches - snapped))
      return snapped
    steps = [{"width_in": dim(r["w"]), "height_in": dim(r["h"])} for r in steps_pt]
    steps = [{**t, "width_mm": round(t["width_in"] * MM, 1), "height_mm": round(t["height_in"] * MM, 1)} for t in steps]
    base_in = base["w"] * s / MM
    block_in = base["h"] * s / MM
    printed_w = _printed(lines, cx - 35.0, cx + 35.0, base["z0"] - 25.0, base["z0"] + 2.0, cx)
    if printed_w is not None and abs(printed_w - base_in) > WIDTH_AGREE_IN:
      rec["issues"].append("BASE_WIDTH_DISAGREES")
    base_w_in = printed_w if printed_w is not None else _snap(base_in)
    labels: dict = {}
    for ln in lines:
      m = LAYER_LABEL.search(ln["text"])
      if not m or not (base["z0"] - 12.0 <= ln["Z"] <= base["z1"] + 10.0):
        continue
      if not (bx[1] - 2.0 <= ln["X"] <= bx[1] + LABEL_REACH or bx[0] - LABEL_REACH <= ln["X"] <= bx[0] + 2.0):
        continue
      what = "SAND" if m.group("what").upper().startswith("S") else "PCC"
      gap = min(abs(ln["X"] - bx[0]), abs(ln["X"] - bx[1]))
      if what not in labels or gap < labels[what][0]:
        labels[what] = (gap, _inches(m.group("n")))
        
    pcc_in = labels.get("PCC", (0, None))[1]
    sand_in = labels.get("SAND", (0, None))[1]
    layers = _splits(H, bx[0], bx[1], base["z0"], base["z1"])
    if pcc_in is None and sand_in is None:
      if layers:
        rec["issues"].append("LAYERS_UNLABELLED")
      pcc_in, sand_in = _snap(block_in), 0.0
    else:
      pcc_in = pcc_in if pcc_in is not None else max(0.0, _snap(block_in) - (sand_in or 0.0))
      sand_in = sand_in if sand_in is not None else max(0.0, _snap(block_in) - pcc_in)
      if abs(pcc_in + sand_in - block_in) > LAYER_AGREE_IN:
        rec["issues"].append("LAYERS_DISAGREE")
    depth_in = _printed(lines, bx[0] - 100.0, bx[0] - 3.0, base["z0"] - 8.0, zb + 80.0, bx[0])
    if depth_in is None:
      rec["issues"].append("DEPTH_NOT_PRINTED")
    stack_in = sum(t["height_in"] for t in steps) + pcc_in + sand_in
    if depth_in is not None and depth_in + LAYER_AGREE_IN < stack_in:
      rec["issues"].append("DEPTH_LESS_THAN_LAYERS")
      
    rec["steps"] = list(reversed(steps))
    rec["pcc"] = {"width_in": base_w_in, "depth_in": pcc_in, "width_mm": round(base_w_in * MM, 1), "depth_mm": round(pcc_in * MM, 1)}
    rec["sand"] = {"width_in": base_w_in, "depth_in": sand_in, "width_mm": round(base_w_in * MM, 1), "depth_mm": round(sand_in * MM, 1)} if sand_in else None
    rec["base_width_mm"], rec["pcc_mm"], rec["sand_mm"] = rec["pcc"]["width_mm"], rec["pcc"]["depth_mm"], round(sand_in * MM, 1)
    rec["depth_mm"] = rec["total_depth_mm"] = round(depth_in * MM, 1) if depth_in is not None else None
    rec["shaft_mm"] = round(max(0.0, depth_in - stack_in) * MM, 1) if depth_in is not None else None
    rec["wall_width_mm"] = round(wall_in * MM, 1)
    rec["steel"] = _steel(words, X0, X1, Z0, Z1, u, w)
    rec["pcc_free"] = False
    rec["snap_error_in"] = round(snap_err, 2)
    rec["labels"] = [{"label_in": round(l["label_in"], 2), "width_in": round(l["width_pt"] * s / MM, 2)} for l in cal["labels"]]
    if snap_err > 0.35:
      rec["issues"].append("DIMENSIONS_NOT_ON_HALF_INCH")
    rec["read"] = "UNUSABLE" if BAD_ISSUES & set(rec["issues"]) else "OK"
  return out

def read(index, words: list, page_wh: tuple | None = None) -> list:
  if not words:
    return []
  if page_wh is None:
    return _read(index, words)
  cindex, cwords, k = PU.canon(index, words, page_wh)
  out = _read(cindex, cwords)
  for rec in out:
    if rec.get("axis") is not None:
      rec["axis"] = round(rec["axis"] * k, 1)
    if rec.get("scale_mm_per_pt") is not None:
      rec["scale_mm_per_pt"] = round(rec["scale_mm_per_pt"] / k, 4)
  return out

def _read(index, words: list) -> list:
  u, w = _frame(words)
  lines = _lines(words, u, w)
  caps = []
  for ln in lines:
    m = CAPTION.search(ln["text"])
    if m:
      caps.append({**ln, "wall_in": float(m.group(1))})
  sec_caps = sec_captions(lines)
  if not caps and not sec_caps:
    return []
  caps.sort(key=lambda c: c["X"])
  out: list = []
  
  for i, cap in enumerate(caps):
    nxt = [abs(c["X"] - cap["X"]) for c in caps if c is not cap and abs(c["Z"] - cap["Z"]) < 40.0]
    half = min(MAX_HALF_X, 0.5 * min(nxt)) if nxt else MAX_HALF_X
    block_top = max([l["Z"] for l in lines if abs(l["X"] - cap["X"]) <= max(35.0, half) and cap["Z"] - 45.0 <= l["Z"] <= cap["Z"] + 6.0 and re.search(r"SECTION|FOOTING|THICK|MASONRY|WALL", l["text"], re.I)] or [cap["Z"]])
    X0, X1, Z0, Z1 = cap["X"] - half, cap["X"] + half, block_top + 1.0, block_top + MAX_PICTURE_Z
    corners = [(X * u[0] + Z * w[0], X * u[1] + Z * w[1]) for X in (X0, X1) for Z in (Z0, Z1)]
    nx0, nx1 = min(c[0] for c in corners), max(c[0] for c in corners)
    ny0, ny1 = min(c[1] for c in corners), max(c[1] for c in corners)
    segs, _, _ = index.window(nx0, ny0, nx1, ny1, max_segments=60000)
    
    V, H = [], []
    for a, b, c, d, _k in segs:
      xa, za = a * u[0] + b * u[1], a * w[0] + b * w[1]
      xb, zb = c * u[0] + d * u[1], c * w[0] + d * w[1]
      if not (X0 <= xa <= X1 and X0 <= xb <= X1):
        continue
      if abs(xa - xb) < V_TOL and abs(za - zb) >= MIN_RUN:
        V.append((round((xa + xb) / 2, 2), min(za, zb), max(za, zb)))
      elif abs(za - zb) < V_TOL and abs(xa - xb) >= MIN_RUN:
        H.append((round((za + zb) / 2, 2), min(xa, xb), max(xa, xb)))
        
    V, H = _merge(V), _merge(H)
    rects = rectangles(V, H, cap["X"])
    rec = {"caption": cap["text"][:80], "wall_in": cap["wall_in"], "axis": round(cap["X"], 1), "read": "UNUSABLE", "issues": [], "steel": []}
    if len(rects) < 2:
      rec["issues"].append("PICTURE_NOT_FOUND")
      out.append(rec)
      continue
  
    st = _stack(rects)
    rec["issues"] += st["issues"]
    wall_w = _wall_width(V, cap["X"], max(r["z1"] for r in rects))
    cal = _calibrate(cap["wall_in"], wall_w, st["steps"] + ([st["footing"]] if st["footing"] else []), words, u, w)
    rec["calibration"] = cal["basis"]
    wall_in = cal.get("wall_in") or cap["wall_in"]
    if cal.get("wall_in"):
      rec["wall_in"], rec["caption_wall_in"] = wall_in, cal["caption_wall_in"]
      rec["issues"].append("CAPTION_WALL_DIFFERS")
    if cal["mm_per_pt"] is None:
      rec["issues"].append("SCALE_DISAGREES" if cal["basis"] == "DISAGREE" else "SCALE_UNKNOWN")
      out.append(rec)
      continue
    s = cal["mm_per_pt"]
    rec["scale_mm_per_pt"] = round(s, 4)
    snap_err = 0.0

    def dim(pt: float) -> float:
      nonlocal snap_err
      inches = pt * s / MM
      snapped = _snap(inches)
      snap_err = max(snap_err, abs(inches - snapped))
      return snapped
    masonry_only = False
    if st["footing"] is not None and st["steps"]:
      top_first = sorted(st["steps"], key=lambda r: -r["z1"])
      chain_in = [wall_in] + [dim(r["w"]) for r in top_first]
      offsets_in = [b - a for a, b in zip(chain_in, chain_in[1:])]
      if offsets_in and dim(st["footing"]["w"]) - chain_in[-1] <= 1.5 * max(offsets_in):
        st["steps"] = [*st["steps"], st["footing"]]
        st["footing"] = None
        masonry_only = True
    rec["masonry_only"] = masonry_only
    steps_bottom_first = sorted(st["steps"], key=lambda r: r["z1"])
    rec["steps"] = [{"width_in": dim(r["w"]), "height_in": dim(r["h"]), "width_mm": round(dim(r["w"]) * MM, 1), "height_mm": round(dim(r["h"]) * MM, 1)} for r in steps_bottom_first]
    for key in ("footing", "pcc"):
      r = st[key]
      
      rec[key] = {"width_in": dim(r["w"]), "depth_in": dim(r["h"]), "width_mm": round(dim(r["w"]) * MM, 1), "depth_mm": round(dim(r["h"]) * MM, 1)} if r else None
    rec["wall_width_mm"] = round(wall_in * MM, 1)
    widths = [s_["width_mm"] for s_ in rec["steps"]]
    chain = [rec["wall_width_mm"]] + sorted(widths)
    diffs = [round(b - a, 1) for a, b in zip(chain, chain[1:])]
    rec["step_offset_mm"] = diffs[0] if diffs and all(abs(d - diffs[0]) <= 0.5 * MM for d in diffs) else None
    rec["step_offsets_mm"] = diffs
    rec["total_depth_mm"] = round(sum(s_["height_mm"] for s_ in rec["steps"]) + (rec["footing"] or {}).get("depth_mm", 0.0) + (rec["pcc"] or {}).get("depth_mm", 0.0), 1)
    rec["pcc_free"] = bool(rec["pcc"])
    centres = sorted((r["xl"] + r["xr"]) / 2.0 for r in rects)
    mid = centres[len(centres) // 2]
    rec["eccentric"] = any(abs(c - mid) > 0.6 for c in centres)
    rec["snap_error_in"] = round(snap_err, 2)
    rec["labels"] = [{"label_in": round(l["label_in"], 2), "width_in": round(l["width_pt"] * s / MM, 2)} for l in cal["labels"]]
    rec["steel"] = _steel(words, X0, X1, Z0, Z1, u, w)
    
    if rec["eccentric"]:
      rec["issues"].append("ECCENTRIC_FOOTING")
    if snap_err > 0.35:
      rec["issues"].append("DIMENSIONS_NOT_ON_HALF_INCH")
    if st["footing"] is None and not masonry_only:
      rec["issues"].append("NO_FOOTING_FOUND")
    if not rec["steps"]:
      rec["issues"].append("NO_STEPS_FOUND")
    bad = {"WIDTHS_NOT_STEPPED", "ECCENTRIC_FOOTING", "DIMENSIONS_NOT_ON_HALF_INCH", "NO_FOOTING_FOUND", "NO_STEPS_FOUND"}
    rec["read"] = "UNUSABLE" if bad & set(rec["issues"]) else "OK"
    out.append(rec)
  out.extend(read_stepped(index, words, u, w, lines, sec_caps))
  return out

def _section_key(s: dict) -> tuple:
  if s.get("footing"):
    return (s["footing"]["width_mm"], s["total_depth_mm"])
  return ((s.get("pcc") or {}).get("width_mm"), s.get("total_depth_mm"), tuple(t["width_mm"] for t in s.get("steps") or []))

def _one(fit: list) -> dict | None:
  if len(fit) == 1:
    return fit[0]
  if len(fit) > 1:
    return fit[0] if len({_section_key(s) for s in fit}) == 1 else None
  return None

def type_run(sections: list, thickness_mm: float, tol: float = 0.05, drawn_mm: float | None = None, exterior: bool | None = None, mark: str | None = None) -> tuple:
  ok = [s for s in sections or [] if s.get("read") == "OK" and s.get("wall_width_mm")]
  if mark:
    named = _one([s for s in ok if str(s.get("mark") or "").upper() == str(mark).upper()])
    if named and any(abs(named["wall_width_mm"] - t) <= MARK_WALL_AGREE * t for t in (thickness_mm, drawn_mm) if t):
      return named, "MARK"

  def by(t: float) -> list:
    return [s for s in ok if abs(s["wall_width_mm"] - t) <= tol * t]
  fit = by(thickness_mm)
  if not fit and drawn_mm:
    fit = by(drawn_mm)
  if exterior is not None and len(fit) > 1:
    same = [s for s in fit if s.get("exterior") is exterior]
    got = _one(same) if same and len(same) < len(fit) else None
    if got:
      return got, "THICKNESS_SIDE"
  got = _one(fit)
  return (got, "THICKNESS") if got else (None, None)

def options(sections: list, thickness_mm: float, tol: float = 0.05, drawn_mm: float | None = None) -> list:
  ok = [s for s in sections or [] if s.get("read") == "OK" and s.get("wall_width_mm") and s.get("mark")]
  fit = [s for s in ok if abs(s["wall_width_mm"] - thickness_mm) <= tol * thickness_mm] or ([s for s in ok if abs(s["wall_width_mm"] - drawn_mm) <= tol * drawn_mm] if drawn_mm else [])
  seen: dict = {}
  for s in fit:
    seen.setdefault(_section_key(s), s)
  return list(seen.values()) if len(seen) > 1 else []

def for_wall(sections: list, thickness_mm: float, tol: float = 0.05) -> dict | None:
  return type_run(sections, thickness_mm, tol)[0]
