from __future__ import annotations
import math
import statistics
import time

PT_MM = 25.4 / 72.0
TRIALS = (96.0, 48.0, 192.0)
MIN_LABELS = 3
KEEP_ITEMS = 12
BUDGET_S = 8.0

def _span(union, x: float, y: float, ux: float, uy: float, reach: float):
  """(lo, hi): where a line through (x, y) along (ux, uy) first meets a wall on each side, as distances from (x, y). None when a side has no wall."""
  from shapely.geometry import LineString
  ray = LineString([(x - ux * reach, y - uy * reach), (x + ux * reach, y + uy * reach)])
  hit = ray.intersection(union)
  lo = hi = None
  
  for g in (list(hit.geoms) if hasattr(hit, "geoms") else [hit]):
    if g.is_empty or not hasattr(g, "coords"):
      continue
    ts = [(px - x) * ux + (py - y) * uy for px, py in g.coords]
    t0, t1 = min(ts), max(ts)
    if t1 <= 0:
      lo = t1 if lo is None else max(lo, t1)
    elif t0 >= 0:
      hi = t0 if hi is None else min(hi, t0)
    else:
      return None
  if lo is None or hi is None:
    return None
  return lo, hi

def _items(index, lines, hint, mm_per_pt: float, user_unit: float, deadline: float) -> tuple:
  from app.modules.drawings_boq.takeoff.extract import config as C, rooms as R, walls as W
  from shapely.geometry import Point
  from shapely.ops import unary_union
  names, sizes = R.labels(lines, hint)
  if len(sizes) < MIN_LABELS:
    return [], len(sizes)
  frames, runs, _stats = W.detect_walls(index, mm_per_pt, deadline)
  if not runs:
    return [], len(sizes)
  union = unary_union([W.run_polygon(r, frames[r.peak], extended=True) for r in runs])
  fr = frames[0]
  bx0, by0, bx1, by1 = index.bbox
  reach = math.hypot(bx1 - bx0, by1 - by0)
  out = []

  for text, (sa, sb), x, y in sizes:
    if union.contains(Point(x, y)):
      continue
    along = _span(union, x, y, fr.ux, fr.uy, reach)
    across = _span(union, x, y, -fr.uy, fr.ux, reach)
    if along is None or across is None:
      continue

    w1, w2 = (along[1] - along[0]) * user_unit, (across[1] - across[0]) * user_unit
    best = None
    for p, q, first in ((sa, sb, True), (sb, sa, False)):
      ra, rb = float(p) / (w1 * PT_MM), float(q) / (w2 * PT_MM)
      miss = abs(ra / rb - 1.0)
      if best is None or miss < best[0]:
        best = (miss, math.sqrt(ra * rb), first)
    if best[0] > C.ROOM_SIZE_TOL:
      continue
    use_along = w1 >= w2

    ux, uy, (lo, hi) = (fr.ux, fr.uy, along) if use_along else (-fr.uy, fr.ux, across)
    value = float(sa if best[2] else sb) if use_along else float(sb if best[2] else sa)
    out.append({"text": text, "ratio": best[1], "x": x, "y": y, "miss": best[0], "value_mm": value,
      "p1": [x + ux * lo, y + uy * lo], "p2": [x + ux * hi, y + uy * hi], "length_pt": (hi - lo)})
  return out, len(sizes)

def _cluster(items: list, tol: float) -> tuple:
  if not items:
    return [], None
  ordered = sorted(items, key=lambda i: i["ratio"])
  best = []
  for left in range(len(ordered)):
    top = ordered[left]["ratio"] * (1.0 + 2.0 * tol)
    window = [i for i in ordered[left:] if i["ratio"] <= top]
    if len(window) > len(best):
      best = window
  centre = statistics.median(i["ratio"] for i in best)
  members = [i for i in ordered if abs(i["ratio"] / centre - 1.0) <= tol]
  if not members:
    return [], None
  return members, statistics.median(i["ratio"] for i in members)

def read(index, lines, hint, user_unit: float, tol: float, strong_support: int, strong_spread: float, deadline: float | None = None, first_trial: float | None = None) -> dict | None:
  started = time.monotonic()
  limit = min(deadline, started + BUDGET_S) if deadline is not None else started + BUDGET_S
  best = None
  labels = 0
  trials = (first_trial, *[x for x in TRIALS if not first_trial or abs(x / first_trial - 1.0) > 0.25]) if first_trial else TRIALS

  for trial in trials:
    try:
      items, labels = _items(index, lines, hint, PT_MM * trial * user_unit, user_unit, limit)
    except Exception:
      return None
    if labels < MIN_LABELS:
      return None
    members, centre = _cluster(items, tol)
    if not members:
      continue
    
    mean = sum(m["ratio"] for m in members) / len(members)
    spread = 100.0 * math.sqrt(sum((m["ratio"] - mean) ** 2 for m in members) / len(members)) / mean if mean else 0.0
    cand = {"source": "ROOM_LABELS", "labels": labels, "read": len(items), "ratio": round(centre, 4), "support": len(members), "spread_pct": round(spread, 3),
      "trial_ratio": trial, "strong": len(members) >= strong_support and spread <= strong_spread and (len(members) / max(len(items), 1) >= 0.5 or len(members) >= 5)}
    if best is None or (cand["support"], -cand["spread_pct"]) > (best[0]["support"], -best[0]["spread_pct"]):
      best = (cand, members, items)
    if cand["strong"]:
      break
    if time.monotonic() > limit:
      break
  if best is None:
    return {"source": "ROOM_LABELS", "labels": labels, "read": 0, "ratio": None, "support": 0, "spread_pct": None, "strong": False, "items": []}

  cand, members, items = best
  member_ids = {id(m) for m in members}
  shown = sorted(items, key=lambda i: (id(i) not in member_ids, i["miss"]))[:KEEP_ITEMS]
  cand["items"] = [{"text": i["text"], "ratio": round(i["ratio"], 3), "inlier": id(i) in member_ids, "x": round(i["x"], 2), "y": round(i["y"], 2)} for i in shown]
  longest = max(members, key=lambda m: m["length_pt"])
  cand["check"] = {"p1": [round(v, 3) for v in longest["p1"]], "p2": [round(v, 3) for v in longest["p2"]], "value": format(round(longest["value_mm"], 3), "f"),
    "unit": "mm", "text": longest["text"], "length_pt": round(longest["length_pt"], 3)}
  return cand

def _rooms_rec(rooms: dict, trust: float) -> dict:
  ratio = float(rooms["ratio"])
  text = format(round(ratio, 4), "f").rstrip("0").rstrip(".")
  return {"method": "SCALE_RATIO", "ratio": round(ratio, 4), "scale_text": f"1:{text}", "basis": "MEASURED_FROM_ROOMS", "trust": trust, "check": rooms.get("check"), "support": int(rooms["support"])}

def apply(verdict: dict, notes: list, rooms: dict | None, declared: dict, agree_tol: float, conflict_tol: float) -> tuple:
  if not rooms or not rooms.get("strong") or not rooms.get("ratio"):
    return verdict, notes

  agreement, rec = verdict.get("agreement"), verdict.get("recommended")
  w = float(rooms["ratio"])
  support = int(rooms["support"])
  out = dict(verdict)

  if rec is None and agreement == "NONE":
    if declared.get("not_to_scale"):
      return verdict, notes
    out["agreement"] = "ROOMS_ONLY"
    out["recommended"] = _rooms_rec(rooms, 0.88)
    notes = [n for n in notes if n.get("code") != "NO_SCALE_FOUND"]
    notes.append({"code": "SCALE_FROM_ROOMS", "message": f"No scale or dimension is printed on this sheet. The scale comes from the room sizes written on the plan ({support} rooms agree)."})
    return out, notes

  if rec is None or agreement not in ("DIMENSIONS_ONLY", "DIMENSIONS_WEAK", "VERIFIED_WEAK", "DECLARED_ONLY", "CONFLICT"):
    return verdict, notes
  gap = abs(w / float(rec["ratio"]) - 1.0)
  if gap <= agree_tol:
    new = {"DIMENSIONS_ONLY": ("VERIFIED", 0.97, "DIMENSIONS_AND_ROOMS"), "DIMENSIONS_WEAK": ("VERIFIED_WEAK", 0.85, "DIMENSIONS_AND_ROOMS"),
      "VERIFIED_WEAK": ("VERIFIED", 0.97, rec.get("basis")), "DECLARED_ONLY": ("VERIFIED_WEAK", 0.85, "DECLARED_AND_ROOMS")}.get(agreement)
    if new is None:
      return verdict, notes
    out["agreement"] = new[0]
    out["recommended"] = {**rec, "trust": max(float(rec.get("trust") or 0.0), new[1]), "basis": new[2]}
    return out, notes

  if gap > conflict_tol:
    out["agreement"] = "WITNESS_CONFLICT"
    weak = agreement == "DIMENSIONS_WEAK"
    if weak:
      out["recommended"] = _rooms_rec(rooms, 0.6)
    notes = [*notes, {"code": "SCALE_WITNESS_CONFLICT", "message": (
      f"The scale found on this sheet (about 1:{float(rec['ratio']):.1f}) and the room sizes written on the plan (about 1:{w:.1f}, {support} rooms agree) give different scales. "
      + ("The room sizes rest on more readings, so they are recommended. " if weak else "")
      + "Check one known length before measuring.")}]
    return out, notes
  return verdict, notes

PANEL_KINDS = ("FRAMING",)
PANEL_BASIS = {"MEASURED_FROM_ROOMS": "MEASURED_FROM_PANELS", "DIMENSIONS_AND_ROOMS": "DIMENSIONS_AND_PANELS", "DECLARED_AND_ROOMS": "DECLARED_AND_PANELS"}

def label_panels(detected: dict, identity: dict | None) -> bool:
  """On a framing plan (a slab and beam plan) the size labels the witness read are slab-panel sizes, not room sizes: the basis of the scale, the witness and the notes say so.
  detected is the scale block of the analysis and is changed in place. True when the sheet is a framing plan and something was named."""
  if not identity or identity.get("plan_kind") not in PANEL_KINDS:
    return False
  named = False
  rec = detected.get("recommended")
  if rec and rec.get("basis") in PANEL_BASIS:
    rec["basis"] = PANEL_BASIS[rec["basis"]]
    named = True
  for w in detected.get("witnesses") or []:
    if w.get("source") == "ROOM_LABELS":
      w["panels"] = True
      named = True
  for n in detected.get("notes") or []:
    if n.get("code") in ("SCALE_FROM_ROOMS", "SCALE_WITNESS_CONFLICT"):
      if n["code"] == "SCALE_FROM_ROOMS":
        n["code"] = "SCALE_FROM_PANELS"
      n["message"] = str(n.get("message") or "").replace("room sizes", "slab panel sizes").replace("rooms agree", "panels agree")
      named = True
  return named
