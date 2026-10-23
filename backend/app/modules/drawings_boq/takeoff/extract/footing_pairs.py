from __future__ import annotations
import math
import re
from collections import Counter
from app.modules.drawings_boq.takeoff.extract import structure as ST
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.prep.details import norm_mark

FOOTING_MARK = re.compile(r"^F-?\s?\d+$", re.I)
COLUMN_MARK = re.compile(r"^C-?\s?\d+$", re.I)

def label_pairs(words: list) -> list:
  fs = [w for w in words if FOOTING_MARK.match((w.text or "").strip())]
  cs = [w for w in words if COLUMN_MARK.match((w.text or "").strip())]
  if not fs or not cs:
    return []
  near = lambda w, pool: min(pool, key=lambda o: math.hypot(w.cx - o.cx, w.cy - o.cy))
  out = []
  for f in fs:
    c = near(f, cs)
    if near(c, fs) is not f:
      continue
    if math.hypot(f.cx - c.cx, f.cy - c.cy) <= C.FOOTING_PAIR_REACH_EM * max(f.size, c.size, 1.0):
      out.append((f.text.strip().upper(), norm_mark(c.text)))
  return out

def summary(pairs: list) -> dict:
  by: dict = {}
  for f, c in pairs:
    by.setdefault(f, Counter())[c] += 1
  out = {}
  for f, cnt in by.items():
    c, n = cnt.most_common(1)[0]
    if n >= C.FOOTING_PAIR_RATIO * sum(cnt.values()):
      out[f] = [c, n, sum(cnt.values())]
  return out

def _area(mm) -> float:
  return float(mm[0]) * float(mm[1]) if mm else 0.0

def assign(groups: list, sizes: list, pairs: dict, column_mm: dict, n_stair: int) -> dict:
  out = ST.assign_footing_sizes(groups, sizes)
  out.update({"basis": "ORDER", "stair": None, "pair_of": {}, "evidence": []})
  marks = sorted({g["tag"] for g in groups if g["category"] == "FOOTING" and not g.get("stair")}, key=ST._mark_order)
  distinct = sorted(set(sizes), key=lambda s: (s[0] * s[1], s))
  
  if len(marks) > 1 and len(distinct) == len(marks):
    cols = {m: (pairs.get(m) or [None])[0] for m in marks}
    areas = {m: _area(column_mm.get(cols[m])) for m in marks}
    if all(areas.values()) and len(set(areas.values())) == len(marks):
      ranked = sorted(marks, key=lambda m: areas[m])
      out["assigned"] = dict(zip(ranked, distinct))
      out["assumed"], out["basis"] = True, "PAIRS"
      out["pair_of"] = {m: [cols[m], pairs[m][1]] for m in marks}
      out["evidence"] = [{"footing": m, "column": cols[m], "labels": pairs[m][1], "column_mm": list(column_mm[cols[m]]), "size_mm": list(out["assigned"][m])} for m in ranked]
      
  if out["assigned"] and len(out["assigned"]) == len(marks) and n_stair == 1:
    left = Counter(sizes)
    left.subtract(Counter(out["assigned"].values()))
    spare = [s for s, n in left.items() if n > 0 for _ in range(n)]
    if len(spare) == 1 and not any(n < 0 for n in left.values()):
      out["stair"] = spare[0]
  return out

def _ft(mm) -> str:
  return f"{round(mm / 304.8, 2):g} ft"

def paired_message(footing: dict, tag: str) -> str:
  e = next((x for x in footing["evidence"] if x["footing"] == tag), None)
  if e is None:
    return C.NOTES["FOOTING_SIZE_PAIRED"][1]
  return (f"The footing details print sizes but not which footing mark each belongs to. On the foundation plan {tag} is written beside {e['column']} ({e['labels']} labels), and the larger column "
    f"takes the larger pad, so {tag} takes {_ft(e['size_mm'][0])} × {_ft(e['size_mm'][1])}. Check the pairing.")

def stair_message(size) -> str:
  return (f"The footing details print one more size than the footing marks use. The size left over, {_ft(size[0])} × {_ft(size[1])}, is taken for the stair footing, "
    "which has a name on the plan but no mark. Check it.")
