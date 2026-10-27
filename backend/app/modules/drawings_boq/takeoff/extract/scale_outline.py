from __future__ import annotations
import math

OUTLINE_AGREE = 0.02            
K_MIN, K_MAX = 0.25, 4.0        
PT_MM = 25.4 / 72.0

BASE, AGREES, PROPOSED, DIFFERS, SCALE_DIFFERS, AMBIGUOUS, NONE = "BASE", "AGREES", "PROPOSED", "DIFFERS", "SCALE_DIFFERS", "AMBIGUOUS", "NONE"

def _pick(samples: list, mm_per_pt: float) -> dict | None:
  if not samples or mm_per_pt <= 0:
    return None
  return min(samples, key=lambda s: abs(math.log(float(s["f"]) / mm_per_pt)))

def _shape(s: dict) -> float:
  return float(s["short_pt"]) / float(s["long_pt"])

def _same_shape(a: dict, b: dict) -> bool:
  return abs(_shape(a) / _shape(b) - 1.0) <= OUTLINE_AGREE

def implied(ref: dict, target: dict) -> dict | None:
  s_ref = float(ref["mm_per_pt"])
  r = _pick(ref["samples"], s_ref)
  if r is None:
    return None

  fits = []
  for t in target["samples"]:
    if not _same_shape(r, t):
      continue
    s_long = s_ref * (float(r["long_pt"]) / float(t["long_pt"]))
    s_short = s_ref * (float(r["short_pt"]) / float(t["short_pt"]))
    if abs(s_long / s_short - 1.0) > OUTLINE_AGREE:
      continue
    mm = (s_long + s_short) / 2.0
    off = abs(math.log(float(t["f"]) / mm))
    nearest = _pick(target["samples"], mm)
    if nearest is t:
      fits.append((off, mm, t))
  if not fits:
    return None
  off, mm, t = min(fits, key=lambda x: x[0])
  return {"mm_per_pt": mm, "k": mm / s_ref, "ref_sample": r, "target_sample": t}

def _rank(ref: dict, target: dict, order: dict) -> tuple:
  a, b = ref.get("floor"), target.get("floor")
  if a and b and a == b:
    return (0,)
  if a in order and b in order:
    d = abs(order[a] - order[b])
    return (1,) if d == 1 else (2, d)
  return (3,)

def propose(sheets: list, floor_order: list | None = None) -> dict:
  order = {f: i for i, f in enumerate(floor_order or [])}
  live = [s for s in sheets if s.get("samples") and s.get("current", True)]
  refs = [s for s in live if s.get("trusted") and s.get("mm_per_pt")]
  out: dict = {}
  for t in live:
    others = [r for r in refs if r["id"] != t["id"]]
    if not others and t.get("trusted") and t.get("mm_per_pt"):
      out[t["id"]] = {"status": BASE, "mm_per_pt": t["mm_per_pt"], "ratio": float(t["mm_per_pt"]) / PT_MM, "k": 1.0, "refs": [], "note": ""}
      continue
    if not others:
      out[t["id"]] = {"status": NONE, "mm_per_pt": None, "ratio": None, "k": None, "refs": [], "note": "No other plan of the set has a trusted scale."}
      continue
  
    tiers: dict = {}
    for r in others:
      imp = implied(r, t)
      tiers.setdefault(_rank(r, t, order), []).append((r, imp))
    matched = [(rank, [(r, i) for r, i in rows if i]) for rank, rows in sorted(tiers.items()) if any(i for _, i in rows)]
    if not matched:
      out[t["id"]] = {"status": DIFFERS, "mm_per_pt": None, "ratio": None, "k": None, "refs": [r["id"] for rows in tiers.values() for r, _ in rows],
        "rank": None, "same_floor": [r["id"] for r, _ in tiers.get((0,), [])], "note": "The outer walls of this plan are not the shape of any other plan's."}
      continue
  
    if t.get("trusted") and t.get("mm_per_pt"):
      own = float(t["mm_per_pt"])
      allrows = [(rk, r, i) for rk, rws in matched for r, i in rws]
      agree = [(rk, r, i) for rk, r, i in allrows if abs(i["mm_per_pt"] / own - 1.0) <= OUTLINE_AGREE]
      if agree:
        near = min(rk for rk, _, _ in agree)
        out[t["id"]] = {"status": AGREES, "mm_per_pt": own, "ratio": own / PT_MM, "k": 1.0, "refs": [r["id"] for rk, r, _ in agree if rk == near], "rank": near[0],
          "note": "The outer walls of this plan are the size of the plan(s) it was compared with at the scale it has."}
        continue
    
    rank, rows = matched[0]
    vals = [i["mm_per_pt"] for _, i in rows]
    if max(vals) / min(vals) - 1.0 > OUTLINE_AGREE:
      out[t["id"]] = {"status": AMBIGUOUS, "mm_per_pt": None, "ratio": None, "k": None, "refs": [r["id"] for r, _ in rows],
        "note": "Plans of this building imply different scales for this plan."}
      continue
  
    mm = sorted(vals)[len(vals) // 2]
    ratio = mm / PT_MM
    ks = [i["k"] for _, i in rows]
    k = sorted(ks)[len(ks) // 2]
    base = {"mm_per_pt": mm, "ratio": ratio, "k": k, "refs": [r["id"] for r, _ in rows], "rank": rank[0]}
    if t.get("trusted") and t.get("mm_per_pt"):
      own = float(t["mm_per_pt"])
      
      if abs(mm / own - 1.0) <= OUTLINE_AGREE:
        out[t["id"]] = {**base, "status": AGREES, "note": "The outer walls of this plan are the size of the plan(s) it was compared with at the scale it has."}
      else:
        out[t["id"]] = {**base, "status": SCALE_DIFFERS, "note": f"At the scale this plan has, its outer walls are {own / mm:.2f} times the size of the plan(s) it was compared with."}
      continue
    if not (K_MIN <= k <= K_MAX):
      out[t["id"]] = {**base, "status": DIFFERS, "mm_per_pt": None, "ratio": None, "note": "The outer walls of this plan would need a scale more than four times different from the plan it was compared with."}
      continue
    out[t["id"]] = {**base, "status": PROPOSED, "note": "The scale that makes the outer walls of this plan the size of the plan(s) it was compared with."}
  for r in refs:
    out.setdefault(r["id"], {"status": BASE, "mm_per_pt": r["mm_per_pt"], "ratio": r["mm_per_pt"] / PT_MM, "k": 1.0, "refs": [], "note": ""})
  return out
