from __future__ import annotations
import math
import re
from statistics import median
from app.modules.drawings_boq.takeoff.prep.schedules import feet_inches_mm
from collections import Counter

MIN_PROJECTION_MM = 150.0
MAX_PROJECTION_MM = 3000.0
MIN_SPAN_MM = 2000.0
MIN_SIDE_OFFSET = 0.08
MAX_LABELS = 24
MAX_DIMS = 40
_WIDTH_TOKEN = re.compile(r"^[\d'\"\-/½¼¾″”’′]+$")
_PLAIN_LENGTH = re.compile(r"^\d{1,3}\s*'\s*-\s*\d{1,2}\s*(?:\"|''|″|”)$")
SIDES = ("TOP", "BOTTOM", "LEFT", "RIGHT")
MIN_PAIR_GAP = 0.15
BIND_REACH = 0.12

def _frame(w) -> tuple:
  a = round(w.angle / 90.0) % 4
  rad = math.radians(a * 90)
  ux, uy = math.cos(rad), math.sin(rad)
  return a, ux, uy

def _axis(w, ux: float, uy: float, visual) -> str | None:
  """H when text runs left to right on the page as it is seen, V when it runs up or down, whatever the page rotation is."""
  a = visual(w.cx, w.cy)
  b = visual(w.cx + ux * 10.0, w.cy + uy * 10.0)
  du, dv = abs(b[0] - a[0]), abs(b[1] - a[1])
  if abs(du - dv) < 1e-9:
    return None
  return "H" if du > dv else "V"

def _labels(words: list, visual) -> list:
  out = []
  
  for w in words:
    if not re.fullmatch(r"projections?", w.text.strip(), re.I):
      continue
    a, ux, uy = _frame(w)
    def along(x):
      return x.cx * ux + x.cy * uy
    def across(x):
      return -x.cx * uy + x.cy * ux
    reach = max(w.size, 1.0) * 2.5
    def gap(after, before):
      return (along(after) - after.length / 2.0) - (along(before) + before.length / 2.0)
    peers = [x for x in words if x is not w and _frame(x)[0] == a and abs(across(x) - across(w)) <= max(w.size, 1.0) * 0.8 and along(x) < along(w)]
    peers.sort(key=lambda x: -along(x))
    if not peers or peers[0].text.strip().lower() != "roof" or gap(w, peers[0]) > reach:
      continue
    used, prev = [w, peers[0]], peers[0]
    tokens: list = []
    
    for x in peers[1:4]:
      if gap(prev, x) > reach or not _WIDTH_TOKEN.match(x.text.strip()):
        break
      tokens.insert(0, x.text.strip())
      used.append(x)
      prev = x
    if not tokens:
      continue
    mm = feet_inches_mm(" ".join(tokens))
    if mm is None or not (MIN_PROJECTION_MM <= mm <= MAX_PROJECTION_MM):
      continue
    pts = [visual(x.cx, x.cy) for x in used]
    out.append({"text": " ".join(tokens) + " roof projection", "width_mm": round(mm, 1), "axis": _axis(w, ux, uy, visual),
      "u": sum(p[0] for p in pts) / len(pts), "v": sum(p[1] for p in pts) / len(pts)})
  return out

def _place(labels: list, mid_u: float, mid_v: float) -> None:
  """Sets the side of each label. Two or more labels running the same way that stand well apart are the two opposite sides of the plan (first and last);
  a single one, or those standing close together, are judged against where most of the text of the sheet is."""
  for axis, key, low, high in (("H", "v", "TOP", "BOTTOM"), ("V", "u", "LEFT", "RIGHT")):
    group = [l for l in labels if l["axis"] == axis]
    mid = mid_v if axis == "H" else mid_u
    if len(group) >= 2:
      lo, hi = min(l[key] for l in group), max(l[key] for l in group)
      if hi - lo >= MIN_PAIR_GAP:
        centre = (lo + hi) / 2.0
        for l in group:
          l["side"] = low if l[key] < centre else high
        continue
    for l in group:
      l["side"] = (low if l[key] < mid else high) if abs(l[key] - mid) >= MIN_SIDE_OFFSET else None

def _bind_lengths(labels: list, dims: list, mid_u: float, mid_v: float) -> None:
  for l in labels:
    l["length_mm"], l["length_text"], l["length_via"] = None, None, None
    if not l.get("side"):
      continue
    horizontal = l["axis"] == "H"
    across, along = ("v", "u") if horizontal else ("u", "v")
    mid = mid_v if horizontal else mid_u
    low = l["side"] in ("TOP", "LEFT")
    pool = [d for d in dims if d["axis"] == l["axis"] and ((d[across] < mid) == low) and abs(d[across] - l[across]) <= BIND_REACH]
    if not pool:
      continue
    best = min(pool, key=lambda d: (round(abs(d[across] - l[across]), 3), abs(d[along] - l[along])))
    l["length_mm"], l["length_text"], l["length_via"] = best["mm"], best["text"], "OWN_SIDE"
  opposite = {"TOP": "BOTTOM", "BOTTOM": "TOP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
  for l in labels:
    if not l.get("side") or l["length_mm"] is not None:
      continue
    twin = next((m for m in labels if m is not l and m.get("side") == opposite[l["side"]] and m["axis"] == l["axis"] and m.get("length_mm")), None)
    if twin is not None:
      l["length_mm"], l["length_text"], l["length_via"] = twin["length_mm"], twin["length_text"], "OPPOSITE_SIDE"

def read_projections(lines: list, words: list, visual) -> dict:
  if not words:
    return {"items": [], "dims": []}
  mid_u = median(visual(w.cx, w.cy)[0] for w in words)
  mid_v = median(visual(w.cx, w.cy)[1] for w in words)
  labels = _labels(words, visual)
  
  for l in labels:
    l["side"] = None
  _place(labels, mid_u, mid_v)
  dims, seen, spots = [], set(), []
  for w in words:
    t = w.text.strip()
    if not _PLAIN_LENGTH.match(t):
      continue
    
    mm = feet_inches_mm(t)
    if not mm or mm < MIN_SPAN_MM:
      continue
    _, ux, uy = _frame(w)
    axis = _axis(w, ux, uy, visual)
    if not axis:
      continue
    
    u, v = visual(w.cx, w.cy)
    if (round(mm, 1), axis) not in seen:
      seen.add((round(mm, 1), axis))
      dims.append({"mm": round(mm, 1), "axis": axis})
    spots.append({"mm": round(mm, 1), "axis": axis, "u": u, "v": v, "text": t})
  _bind_lengths(labels, spots, mid_u, mid_v)
  items = [{"text": l["text"], "width_mm": l["width_mm"], "side": l["side"], "axis": l["axis"], "u": round(l["u"], 4), "v": round(l["v"], 4),
    "length_mm": l["length_mm"], "length_text": l["length_text"], "length_via": l["length_via"]} for l in labels]
  return {"items": items[:MAX_LABELS], "dims": dims[:MAX_DIMS]}

def gather(sheets: list) -> dict:
  floors: dict = {}
  for sh in sheets:
    hint, pr = sh.get("level_hint"), sh.get("projections") or {}
    if not hint or not (pr.get("items") or pr.get("dims")):
      continue
  
    fl = floors.setdefault(hint, {"labels": [], "dims": []})
    for it in pr.get("items") or []:
      fl["labels"].append({**it, "page": sh["page_no"]})
    for d in pr.get("dims") or []:
      fl["dims"].append({**d, "page": sh["page_no"]})
  out: dict = {}
  for hint, fl in floors.items():
    by_side: dict = {}
    unplaced = []
    for it in fl["labels"]:
      if it["side"] is None:
        unplaced.append({"text": it["text"], "width_mm": it["width_mm"], "page": it["page"]})
        
      else:
        by_side.setdefault(it["side"], []).append(it)
    sides, conflicts = {}, []
    for side, recs in by_side.items():
      widths = Counter(r["width_mm"] for r in recs)
      pages = sorted({r["page"] for r in recs})
      if len(widths) > 1:
        conflicts.append({"side": side, "widths_mm": sorted(widths), "pages": pages})
        continue
      
      lengths = Counter(r["length_mm"] for r in recs if r.get("length_mm"))
      sides[side] = {"width_mm": recs[0]["width_mm"], "text": recs[0]["text"], "pages": pages, "lengths_mm": sorted(lengths),
        "length_mm": lengths.most_common(1)[0][0] if lengths else None,
        "length_via": "OPPOSITE_SIDE" if lengths and all(r.get("length_via") == "OPPOSITE_SIDE" for r in recs if r.get("length_mm")) else ("OWN_SIDE" if lengths else None)}
      
    dims: dict = {}
    for d in fl["dims"]:
      dims.setdefault((d["mm"], d["axis"]), set()).add(d["page"])
    out[hint] = {"sides": sides, "unplaced": unplaced, "conflicts": conflicts,
      "dims": [{"mm": k[0], "axis": k[1], "pages": sorted(v)} for k, v in sorted(dims.items())]}
  return out
