from __future__ import annotations
import math

OUTLINE_AGREE = 0.02            
PLOTTING_SCALES = (50, 75, 100, 125, 150, 200)    
PLOTTING_TOL = 0.02
WALL_MM = 229.0                  
MIN_ELONGATION = 0.05           
K_MIN, K_MAX = 0.25, 4.0        
PT_MM = 25.4 / 72.0
FLOOR_PAPER_TOL = 0.01
FLOOR_DIMS_TOL = 0.03
FLOOR_LABELS_VETO = 0.10
FLOOR_PLAN = "FLOOR_PLAN"

BASE, AGREES, PROPOSED, DIFFERS, SCALE_DIFFERS, AMBIGUOUS, NONE = "BASE", "AGREES", "PROPOSED", "DIFFERS", "SCALE_DIFFERS", "AMBIGUOUS", "NONE"

def _pick(samples: list, mm_per_pt: float) -> dict | None:
  if not samples or mm_per_pt <= 0:
    return None
  return min(samples, key=lambda s: abs(math.log(float(s["f"]) / mm_per_pt)))

def _shape(s: dict) -> float:
  return float(s["short_pt"]) / float(s["long_pt"])

def _same_shape(a: dict, b: dict) -> bool:
  return abs(_shape(a) / _shape(b) - 1.0) <= OUTLINE_AGREE

def plotting_scale(ratio: float | None) -> int | None:
  """The plotting scale (1:50 ... 1:200) a ratio is within PLOTTING_TOL of, or None."""
  if not ratio or ratio <= 0:
    return None
  best = min(PLOTTING_SCALES, key=lambda s: abs(math.log(float(ratio) / s)))
  return best if abs(float(ratio) / best - 1.0) <= PLOTTING_TOL else None

def implied_offset(ref: dict, target: dict, wall_mm: float = WALL_MM) -> dict | None:
  s_ref = float(ref["mm_per_pt"])
  r = _pick(ref["samples"], s_ref)
  if r is None:
    return None
  ref_short, ref_long = s_ref * float(r["short_pt"]), s_ref * float(r["long_pt"])
  fits = []
  for t in target["samples"]:
    gap = float(t["long_pt"]) - float(t["short_pt"])
    if gap <= 0 or gap / float(t["long_pt"]) < MIN_ELONGATION or ref_long <= ref_short:
      continue
    s = (ref_long - ref_short) / gap
    d = s * float(t["short_pt"]) - ref_short
    plot = plotting_scale(s / PT_MM)
    if plot is None or not (0.0 <= d <= 4.0 * wall_mm) or _pick(target["samples"], s) is not t:
      continue
    fits.append((abs(math.log(float(t["f"]) / s)), s, d, plot, t))
  if not fits:
    return None
  _off, s, d, plot, t = min(fits, key=lambda x: x[0])
  return {"mm_per_pt": s, "k": s / s_ref, "ref_sample": r, "target_sample": t, "offset_mm": round(d, 1), "t_mm": round(d / 2.0, 1), "plotting_scale": plot}

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
  plain = None
  if fits:
    off, mm, t = min(fits, key=lambda x: x[0])
    plain = {"mm_per_pt": mm, "k": mm / s_ref, "ref_sample": r, "target_sample": t}
  if plain is not None and plotting_scale(plain["mm_per_pt"] / PT_MM) is not None:
    return plain
  shifted = implied_offset(ref, target)
  return shifted or plain      

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

def floor_fields(full: dict, ident: dict, paper: dict | None) -> dict:
  """What inherit needs to know of a sheet: its role, what it is read as, the scale and the dimensions that were read on it, and the paper size."""
  rec = full.get("recommended") or {}
  clusters = (full.get("measured") or {}).get("clusters") or []
  top = clusters[0] if clusters else None
  weak = next((float(w["ratio"]) for w in full.get("witnesses") or [] if w.get("source") == "ROOM_LABELS" and w.get("ratio") and not w.get("strong") and int(w.get("support") or 0) >= 2), None)
  size = tuple(sorted((float(paper["width_mm"]), float(paper["height_mm"])))) if paper and paper.get("width_mm") and paper.get("height_mm") else None
  return {"role": ident.get("role"), "plan_kind": ident.get("plan_kind"), "read_as": ident.get("read_as"), "agreement": full.get("agreement"), "size": size, "labels": weak,
    "ratio": float(rec["ratio"]) if rec.get("ratio") else None, "support": int(rec.get("support") or 0),
    "dims": {"ratio": float(top["ratio"]), "support": int(top.get("support") or 0)} if top and top.get("ratio") else None}

def _same_paper(a: tuple | None, b: tuple | None) -> bool:
  return bool(a) and bool(b) and all(abs(x / y - 1.0) <= FLOOR_PAPER_TOL for x, y in zip(a, b))

def inherit(sheets: list) -> dict:
  out: dict = {}
  for t in sheets:
    if not t.get("wanted") or t.get("role") != "PLAN" or t.get("plan_kind") != "OVERLAY" or not t.get("floor") or t.get("agreement") not in (None, "NONE", "DIMENSIONS_WEAK"):
      continue
    sources = [s for s in sheets if s["id"] != t["id"] and s.get("drawing") == t.get("drawing") and s.get("trusted") and s.get("ratio") and s.get("support") and s.get("role") == "PLAN"
      and s.get("read_as") == "PLAN_ITEMS" and s.get("floor") == t["floor"] and _same_paper(s.get("size"), t.get("size"))]
    
    if not sources:
      continue
    src = max(sources, key=lambda s: (s["support"], -s["page_no"]))
    ratio, own = float(src["ratio"]), t.get("dims")
    if own and abs(float(own["ratio"]) / ratio - 1.0) > FLOOR_DIMS_TOL:
      continue
    if t.get("labels") and abs(float(t["labels"]) / ratio - 1.0) > FLOOR_LABELS_VETO:
      continue
    out[t["id"]] = {"status": FLOOR_PLAN, "ratio": ratio, "dims": bool(own), "own": float(own["ratio"]) if own else None, "support": int(own["support"]) if own else 0,
      "ref": src["id"], "page_no": src["page_no"], "floor": t["floor"]}
  return out
