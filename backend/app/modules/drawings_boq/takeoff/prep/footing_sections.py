from __future__ import annotations
import math
import re

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
    return {"mm_per_pt": None, "basis": "DISAGREE", "labels": labels, "agree": False, "from_wall": from_wall, "from_labels": lab}
  if lab:
    return {"mm_per_pt": lab, "basis": "LABELS", "labels": labels, "agree": True}
  if from_wall:
    return {"mm_per_pt": from_wall, "basis": "WALL", "labels": labels, "agree": True}
  return {"mm_per_pt": None, "basis": "NONE", "labels": labels, "agree": False}

def read(index, words: list) -> list:
  if not words:
    return []
  u, w = _frame(words)
  lines = _lines(words, u, w)
  caps = []
  for ln in lines:
    m = CAPTION.search(ln["text"])
    if m:
      caps.append({**ln, "wall_in": float(m.group(1))})
  if not caps:
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
    cal = _calibrate(cap["wall_in"], wall_w, st["steps"], words, u, w)
    rec["calibration"] = cal["basis"]
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
    steps_bottom_first = sorted(st["steps"], key=lambda r: r["z1"])
    rec["steps"] = [{"width_in": dim(r["w"]), "height_in": dim(r["h"]), "width_mm": round(dim(r["w"]) * MM, 1), "height_mm": round(dim(r["h"]) * MM, 1)} for r in steps_bottom_first]
    for key in ("footing", "pcc"):
      r = st[key]
      
      rec[key] = {"width_in": dim(r["w"]), "depth_in": dim(r["h"]), "width_mm": round(dim(r["w"]) * MM, 1), "depth_mm": round(dim(r["h"]) * MM, 1)} if r else None
    rec["wall_width_mm"] = round(cap["wall_in"] * MM, 1)
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
    if st["footing"] is None:
      rec["issues"].append("NO_FOOTING_FOUND")
    if not rec["steps"]:
      rec["issues"].append("NO_STEPS_FOUND")
    bad = {"WIDTHS_NOT_STEPPED", "ECCENTRIC_FOOTING", "DIMENSIONS_NOT_ON_HALF_INCH", "NO_FOOTING_FOUND", "NO_STEPS_FOUND"}
    rec["read"] = "UNUSABLE" if bad & set(rec["issues"]) else "OK"
    out.append(rec)
  return out

def for_wall(sections: list, thickness_mm: float, tol: float = 0.05) -> dict | None:
  """The usable footing section drawn for a wall of this thickness. When more than one fits (a section for the same wall in two widths), none is chosen."""
  fit = [s for s in sections or [] if s.get("read") == "OK" and s.get("wall_width_mm") and abs(s["wall_width_mm"] - thickness_mm) <= tol * thickness_mm]
  if len(fit) == 1:
    return fit[0]
  if len(fit) > 1:
    key = {(s["footing"]["width_mm"], s["total_depth_mm"]) for s in fit}
    return fit[0] if len(key) == 1 else None
  return None
