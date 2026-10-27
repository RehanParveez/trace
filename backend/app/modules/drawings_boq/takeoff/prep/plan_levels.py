from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.prep import facts as F
from app.modules.drawings_boq.takeoff.prep import storeys as SR
from collections import Counter
from statistics import median

VALUE_REACH_SIZES = 1.5       
STACK_REACH_SIZES = 2.5       
PAIR_REACH_SIZES = 3.0        
ROOF_REACH_SIZES = 3.0        
SAME_LINE_SIZES = 0.5         
SIDE_REACH_SIZES = 1.5        
LEVEL_ROUND_MM = 5            
GROUP_ROUND_MM = 25           
MIN_AGREE = 0.75              

_CH = re.compile(r"^C\.?H\.?\s*=\s*(.*)$", re.I)
_FROM = re.compile(r"^FROM[\s\-]*R\.?L\.?$", re.I)
_ROOF = re.compile(r"\b(?:TOP\s+ROOF|ROOF|MUMTY\s+TOP)\b", re.I)
_SIGN = re.compile(r"^[+\-±]$")

_FRAMES = {0: ((1.0, 0.0), (0.0, -1.0)), 90: ((0.0, 1.0), (1.0, 0.0)), 180: ((-1.0, 0.0), (0.0, 1.0)), 270: ((0.0, -1.0), (-1.0, 0.0))}

class _W:
  __slots__ = ("w", "text", "angle", "size", "u", "v", "half")
  def __init__(self, w, angle: int):
    (ax, ay), (dx, dy) = _FRAMES[angle]
    self.w, self.angle = w, angle
    self.text = F._fix((w.text or "").strip())
    self.size = max(float(w.size or 0.0), 1.0)
    self.u = w.cx * ax + w.cy * ay
    self.v = w.cx * dx + w.cy * dy
    self.half = max(float(w.length or 0.0), 0.0) / 2.0

def _upright(words: list) -> list:
  out = []
  for w in words or []:
    if not (w.text or "").strip():
      continue
    a = SR._snap(w.angle)
    if a is None:
      continue
    out.append(_W(w, a))
  return out

def _ft_in(text: str) -> float | None:
  return SR.feet_inch_mm(text)

def _next_on_line(a: _W, ws: list) -> _W | None:
  best = None
  for x in ws:
    if x is a or x.angle != a.angle or abs(x.v - a.v) > SAME_LINE_SIZES * a.size:
      continue
    gap = (x.u - x.half) - (a.u + a.half)
    if -0.3 * a.size <= gap <= VALUE_REACH_SIZES * a.size and (best is None or x.u < best.u):
      best = x
  return best

def _ch_notes(ws: list) -> list:
  out = []

  for w in ws:
    m = _CH.match(w.text)
    if not m:
      continue
    rest = m.group(1).strip()
    used = w
    if not rest:
      nxt = _next_on_line(w, ws)
      if nxt is None:
        continue
      rest, used = nxt.text, nxt

    mm = _ft_in(rest)
    if mm is None or not SR.MIN_CLEAR_MM <= mm <= SR.MAX_CLEAR_MM:
      continue
    out.append((w, mm, f"CH={rest}"))
  return out

def _line_above(anchor: _W, ws: list, reach_sizes: float, first_line: bool) -> list:
  reach = reach_sizes * anchor.size
  lo, hi = anchor.u - anchor.half - SIDE_REACH_SIZES * anchor.size, anchor.u + anchor.half + SIDE_REACH_SIZES * anchor.size
  cand = [x for x in ws if x is not anchor and x.angle == anchor.angle and 0.2 * anchor.size <= anchor.v - x.v <= reach and lo <= x.u <= hi]
  if not cand:
    return []

  top = max(x.v for x in cand)
  line = [x for x in cand if top - x.v <= SAME_LINE_SIZES * anchor.size]
  return sorted(line, key=lambda x: x.u)

def _level_stacks(ws: list) -> list:
  out = []
  for a in ws:
    if not _FROM.match(a.text):
      continue
    line = _line_above(a, ws, STACK_REACH_SIZES, True)
    if not line:
      continue

    joined = "".join(x.text for x in line)
    mm = F.level_mark_mm(joined)
    if mm is None:
      for x in line:                                    
        mm = F.level_mark_mm(x.text)
        if mm is not None:
          joined = x.text
          break
    if mm is None:
      continue
    value_line = line[0]
    above = _line_above(value_line, ws, ROOF_REACH_SIZES, True)
    caption = " ".join(x.text for x in above)
    out.append({"anchor": a, "level_mm": mm, "text": f"{joined} FROM-RL", "roof": bool(_ROOF.search(caption)), "top": min(x.v for x in line)})
  return out

def _pair(notes: list, stacks: list) -> tuple:
  cand = []

  for i, (w, mm, text) in enumerate(notes):
    for j, s in enumerate(stacks):
      a = s["anchor"]
      if a.angle != w.angle:
        continue
      after = s["top"] - w.v
      if not 0.0 < after <= PAIR_REACH_SIZES * w.size:
        continue
      if abs(a.u - w.u) > max(a.half, w.half) + SIDE_REACH_SIZES * w.size:
        continue
      cand.append((after, i, j))

  pairs, used_n, used_s = [], set(), set()
  for after, i, j in sorted(cand):
    if i in used_n or j in used_s:
      continue
    used_n.add(i), used_s.add(j)
    w, mm, text = notes[i]
    s = stacks[j]
    pairs.append({"clear_mm": round(mm, 1), "level_mm": round(s["level_mm"], 1), "text": f"{text} {s['text']}", "roof": s["roof"]})
  return pairs, [s for j, s in enumerate(stacks) if j not in used_s]

def read(words: list | None) -> dict | None:
  ws = _upright(words)
  if not ws:
    return None
  notes = _ch_notes(ws)
  stacks = _level_stacks(ws)
  if not stacks:
    return None
  pairs, loose = _pair(notes, stacks)
  roofs = [s["level_mm"] for s in stacks if s["roof"]]
  roof_mm = round(max(roofs), 1) if roofs else None

  if not pairs and roof_mm is None:
    return None
  floor = None
  if pairs:
    by = Counter(round(p["level_mm"] / LEVEL_ROUND_MM) * LEVEL_ROUND_MM for p in pairs)
    key, count = by.most_common(1)[0]
    mine = [p for p in pairs if round(p["level_mm"] / LEVEL_ROUND_MM) * LEVEL_ROUND_MM == key]
    floor = {"level_mm": round(median(p["level_mm"] for p in mine), 1), "clear_mm": round(median(p["clear_mm"] for p in mine), 1), "count": count, "agree": round(count / len(pairs), 2)}
  others = {round(s["level_mm"], 1) for s in loose}
  others |= {p["level_mm"] for p in pairs if floor and round(p["level_mm"] / LEVEL_ROUND_MM) * LEVEL_ROUND_MM != round(floor["level_mm"] / LEVEL_ROUND_MM) * LEVEL_ROUND_MM}
  
  if floor:
    others.discard(floor["level_mm"])
  if roof_mm is not None:
    others.discard(roof_mm)
  return {"floor": floor, "other_levels_mm": sorted(others), "pairs": [{k: p[k] for k in ("clear_mm", "level_mm", "text")} for p in pairs], "roof_mm": roof_mm}

def storeys(plan_sheets: list) -> dict | None:
  groups: dict = {}
  roofs, others, pages = [], [], []
  for sh in plan_sheets or []:
    pl = sh.get("plan_levels") or {}
    fl = pl.get("floor")

    if pl.get("roof_mm") is not None:
      roofs.append(float(pl["roof_mm"]))
    others.extend(float(x) for x in pl.get("other_levels_mm") or [])
    if fl and fl.get("level_mm") is not None and fl.get("clear_mm"):
      groups.setdefault(round(float(fl["level_mm"]) / GROUP_ROUND_MM) * GROUP_ROUND_MM, []).append(fl)
      pages.append(sh.get("page_no"))
  if not groups:
    return None
  levels = []

  for key in sorted(groups):
    rows = groups[key]
    clear = float(median(r["clear_mm"] for r in rows))
    agree = sum(1 for r in rows if abs(float(r["clear_mm"]) - clear) <= GROUP_ROUND_MM) / len(rows)
    levels.append({"level": float(median(r["level_mm"] for r in rows)), "clear": clear, "agree": agree, "count": sum(int(r.get("count") or 1) for r in rows)})
  clusters, fits = [], []

  for i, lv in enumerate(levels):
    if i + 1 < len(levels):
      upper = levels[i + 1]["level"]
    elif roofs:
      upper = max(roofs)
    else:
      above = [x for x in others if x - lv["level"] > SR.MIN_CLEAR_MM]
      upper = max(above) if above else None
    between = [round(lv["level"], 1), round(upper, 1)] if upper is not None and upper > lv["level"] else None
    slab = round(between[1] - between[0] - lv["clear"], 1) if between else None
    clusters.append({"clear_mm": round(lv["clear"], 1), "count": lv["count"], "agree": round(lv["agree"], 2), "below_ground": lv["level"] < 0, "between_mm": between, "implied_slab_mm": slab})
    fits.append(slab is not None and -SR.FIT_TOL_MM <= slab <= SR.FIT_SLAB_MAX_MM and lv["agree"] >= MIN_AGREE)

  first = min((p for p in pages if p), default=None)
  return {"clusters": clusters, "consistent": all(fits), "basis": "PLAN_NOTES", **({"page_no": first} if first else {})}
