from __future__ import annotations
from dataclasses import dataclass
from app.modules.drawings_boq.takeoff.prep.spatial import VectorIndex
from decimal import Decimal
from app.modules.drawings_boq.takeoff.prep.extract import RawPage
import math
import time
from app.modules.drawings_boq.takeoff.prep import census, dimensions, facts as drawing_facts, projections as projection_reader, schedules, views as sheet_views
from app.modules.drawings_boq.takeoff.prep.texts import build_lines, find_scale_candidates, find_units_hint, has_not_to_scale, paper_size, title_hints, to_visual
from app.modules.drawings_boq.takeoff.prep import units as UN

ANALYSIS_VERSION = 15
PT_MM = 25.4 / 72.0
STANDARD_RATIOS = (1, 2, 2.5, 4, 5, 8, 10, 12, 16, 20, 24, 25, 30, 32, 40, 48, 50, 60, 64, 75, 96, 100, 120, 125, 128, 150, 192, 200, 250, 300, 400, 500, 600, 750, 1000, 1250, 1500, 2000, 2500, 5000)
AGREE_TOL = 0.015
STRONG_SUPPORT = 3
STRONG_SPREAD_PCT = 1.2
RIVAL_SHARE = 0.34

@dataclass
class PageAnalysis:
  content_kind: str
  text_chars: int
  vector_ops: int
  detected_scale: dict
  meta: dict
  index: VectorIndex

def _r4(v: float) -> float:
  return float(f"{v:.4f}")

def _dec(v: float) -> str:
  return format(Decimal(repr(round(v, 4))).normalize(), "f")

def classify_content(raw: RawPage) -> tuple[str, dict]:
  w, h = raw.width_pt, raw.height_pt
  page_area = max(w * h, 1.0)
  l, b, r, t = raw.cropbox
  cover = 0.0
  max_dpi = 0.0
  for im in raw.images:
    x0, y0, x1, y1 = im["bbox"]
    ix = max(0.0, min(x1, r) - max(x0, l))
    iy = max(0.0, min(y1, t) - max(y0, b))
    cover += ix * iy
    max_dpi = max(max_dpi, im.get("dpi") or 0.0)
  cover = min(1.0, cover / page_area)
  n = len(raw.kinds)
  total_len = 0.0
  s = raw.segs
  for i in range(n):
    k = i * 5
    total_len += math.hypot(s[k + 2] - s[k], s[k + 3] - s[k + 1])
    
  diag = math.hypot(w, h)
  info = {"image_cover": round(cover, 3), "segments": n, "line_length_pt": round(total_len, 1), "max_image_dpi": round(max_dpi, 1)}
  if cover >= 0.55 and total_len < 30.0 * diag:
    return "RASTER", info
  if cover >= 0.55:
    info["hybrid"] = True
    return "VECTOR", info
  if n >= 60 or len(raw.rings) >= 10 or total_len >= 3.0 * diag:
    return "VECTOR", info
  return "UNKNOWN", info

def _pick_declared(cands: list[dict], crop: tuple, rotation: int) -> dict:
  for c in cands:
    u, v = to_visual(c["x"], c["y"], crop, rotation)
    title_zone = u >= 0.68 or v >= 0.82
    c["zone"] = "TITLE" if title_zone else "BODY"
    c["tier"] = (0 if c["labelled"] else 2) if title_zone else (1 if c["labelled"] else 3)
  if not cands:
    return {"candidates": [], "primary": None, "multi_scale": False}
  best_tier = min(c["tier"] for c in cands)
  top = [c for c in cands if c["tier"] == best_tier]
  votes: dict = {}
  
  for c in top:
    votes.setdefault(round(c["ratio"], 2), []).append(c)
  ranked = sorted(votes.values(), key=lambda g: (-len(g), g[0]["y"]))
  primary = dict(ranked[0][0])
  trust = {0: 0.9, 1: 0.8, 2: 0.6, 3: 0.45}[best_tier]
  distinct_all = {round(c["ratio"], 2) for c in cands if c["tier"] <= 1 or c["tier"] == 3}
  multi = len(votes) > 1 or (best_tier >= 3 and len(distinct_all) > 1) or len({round(c["ratio"], 2) for c in cands}) > 2
  primary["trust"] = trust
  primary["ambiguous"] = len(votes) > 1
  return {"candidates": [{k: (_r4(v) if isinstance(v, float) else v) for k, v in c.items() if k != "line"} for c in cands[:12]],
    "primary": {k: (_r4(v) if isinstance(v, float) else v) for k, v in primary.items() if k != "line"}, "multi_scale": bool(multi)}

def snap_standard(ratio: float, tol: float = 0.01):
  best = min(STANDARD_RATIOS, key=lambda s: abs(ratio / s - 1.0))
  return float(best) if abs(ratio / best - 1.0) <= tol else None

def _reduction(declared: float, measured: float):
  f = declared / measured
  for k in range(1, 5):
    std = 2.0 ** (-k / 2.0)
    if abs(f / std - 1.0) <= 0.015:
      return k, std
  return None

def _original_paper(current: str | None, steps: int) -> str | None:
  if current and current.startswith("A") and current[1:].isdigit():
    n = int(current[1:]) - steps
    return f"A{n}" if n >= 0 else None
  return None

def _pair_json(p, cluster_members: dict, center_ratio: float | None, user_unit: float) -> dict:
  j = cluster_members.get(id(p))
  reading = p.readings[j] if j is not None else max(p.readings, key=lambda r: r.prior)
  out = {"text": p.text, "p1": [round(p.p1[0], 3), round(p.p1[1], 3)], "p2": [round(p.p2[0], 3), round(p.p2[1], 3)],
    "length_pt": round(p.length_pt, 3), "value_mm": round(reading.value_mm, 3), "reading_unit": reading.unit,
    "quality": round(p.quality, 2), "ends": p.ends, "inlier": j is not None}
  if center_ratio:
    drawn_mm = p.length_pt * PT_MM * user_unit * center_ratio
    out["drawn_mm"] = round(drawn_mm, 1)
    out["deviation_pct"] = round(100.0 * (drawn_mm / reading.value_mm - 1.0), 2) if reading.value_mm else None
  return out

def _recommend(declared: dict, clusters: list, pairs: list, paper: dict, user_unit: float, content_kind: str) -> tuple[dict, list]:
  notes: list = []
  
  d = declared["primary"]["ratio"] if declared.get("primary") else None
  d_trust = declared["primary"]["trust"] if declared.get("primary") else 0.0
  strong = [c for c in clusters if c.support >= STRONG_SUPPORT and c.spread_pct <= STRONG_SPREAD_PCT and
    (c.support / max(c.total_pairs, 1) >= 0.5 or c.support >= 5)]
  weak = [c for c in clusters if c not in strong and c.support >= 2 and c.spread_pct <= STRONG_SPREAD_PCT]
  main = strong[0] if strong else (weak[0] if weak else None)

  others = [c for c in strong[1:] if abs(c.ratio / strong[0].ratio - 1.0) > 0.05] if strong else []
  rivals = [c for c in others if c.support >= max(STRONG_SUPPORT, RIVAL_SHARE * strong[0].support)]
  if rivals:
    agreement = "MULTI_SCALE"
    notes.append({"code": "MULTI_SCALE", "message": "Printed dimensions show more than one drawing scale on this sheet. Calibrate each view separately."})
    
  elif d is not None and main is not None:
    gap = abs(main.ratio / d - 1.0)
    if gap <= AGREE_TOL:
      agreement = "VERIFIED" if main in strong else "VERIFIED_WEAK"
    else:
      agreement = "CONFLICT" if main in strong else "CONFLICT_UNRESOLVED"
  elif main is not None:
    agreement = "DIMENSIONS_ONLY" if main in strong else "DIMENSIONS_WEAK"
  elif d is not None:
    agreement = "DECLARED_ONLY"
  else:
    agreement = "NONE"
  if others and not rivals:
    notes.append({"code": "OTHER_SCALE_DIMENSIONS", "message": "A few dimensions on this sheet follow another scale (a detail drawn larger or smaller). The scale of most dimensions is used."})
  if agreement == "MULTI_SCALE" and d is not None:
    main = min(strong, key=lambda c: abs(c.ratio / d - 1.0))
  if declared.get("not_to_scale") and d is None:
    notes.append({"code": "NOT_TO_SCALE", "message": "The sheet is marked not to scale. Calibrate from a printed dimension."})

  rec = None
  chosen = main
  ratio = None
  basis = None
  trust = 0.0
  if agreement in ("VERIFIED", "VERIFIED_WEAK"):
    ratio, basis, trust = d, "DECLARED_VERIFIED", 0.97 if agreement == "VERIFIED" else 0.85
  elif agreement in ("CONFLICT", "MULTI_SCALE") and main is not None:
    red = _reduction(d, main.ratio) if d else None
    if red is not None:
      k, std = red
      ratio, basis, trust = d / std, "DECLARED_ADJUSTED_FOR_REDUCTION", 0.93
      orig = _original_paper(paper.get("name"), k)
      notes.append({"code": "SHEET_REDUCED", "message": (
        f"The printed scale is {_dec(d)} but the dimensions show about 1:{main.ratio:.1f}. This sheet looks reduced"
        + (f" from {orig} to {paper.get('name')}" if orig else "") + f" (to {std * 100:.0f}% size). The measured scale is used.")})
    else:
      ratio, basis, trust = main.ratio, "MEASURED_FROM_DIMENSIONS", 0.88
      if d is not None:
        notes.append({"code": "SCALE_CONFLICT", "message": (
          f"The printed scale 1:{_dec(d)} does not match the dimensions, which show about 1:{main.ratio:.1f}. The measured scale is used.")})
  elif agreement == "CONFLICT_UNRESOLVED":
    notes.append({"code": "SCALE_CONFLICT_UNRESOLVED", "message": (
      f"The printed scale 1:{_dec(d)} and the few readable dimensions (about 1:{main.ratio:.1f}) disagree. Calibrate with a known dimension.")})
    chosen = None
    
  elif agreement == "DIMENSIONS_ONLY":
    snapped = snap_standard(main.ratio)
    ratio, basis, trust = (snapped, "MEASURED_STANDARD_SCALE", 0.9) if snapped else (main.ratio, "MEASURED_FROM_DIMENSIONS", 0.88)
  elif agreement == "DIMENSIONS_WEAK":
    ratio, basis, trust = main.ratio, "MEASURED_WEAK", 0.6
    notes.append({"code": "FEW_DIMENSIONS", "message": "Only two printed dimensions could be read; confirm the scale on a known length."})
  elif agreement == "DECLARED_ONLY":
    ratio, basis, trust = d, "DECLARED", min(d_trust, 0.7)
    chosen = None
    if declared.get("multi_scale"):
      trust = min(trust, 0.45)
      notes.append({"code": "MULTI_SCALE", "message": "More than one scale is printed on this sheet; check which applies to the view you measure."})
    if not paper.get("standard"):
      trust = min(trust, 0.45)
      notes.append({"code": "NON_STANDARD_PAPER", "message": "The page is not a standard paper size, so the sheet may have been resized and the printed scale may not hold. Verify with a known dimension."})
    if content_kind == "RASTER":
      trust = min(trust, 0.5)
  if agreement == "NONE":
    notes.append({"code": "NO_SCALE_FOUND", "message": "No scale or readable dimensions were found. Calibrate with two points and a known distance."})

  if ratio is not None and chosen is not None:
    chosen_members = dict(chosen.members)
    inl = [(i, pairs[i]) for i, _ in chosen.members]
    inl.sort(key=lambda t: -(t[1].quality * min(t[1].length_pt, 400.0)))
    check = None
    
    if inl:
      i, p = inl[0]
      j = chosen_members[i]
      check = {"p1": [round(p.p1[0], 3), round(p.p1[1], 3)], "p2": [round(p.p2[0], 3), round(p.p2[1], 3)],
        "value": _dec(p.readings[j].value_mm), "unit": "mm", "text": p.text, "length_pt": round(p.length_pt, 3)}
    rec = {"method": "SCALE_RATIO", "ratio": _r4(ratio), "scale_text": f"1:{_dec(ratio)}", "basis": basis, "trust": round(trust, 2),
      "check": check, "support": chosen.support}
  elif ratio is not None:
    rec = {"method": "SCALE_RATIO", "ratio": _r4(ratio), "scale_text": f"1:{_dec(ratio)}", "basis": basis, "trust": round(trust, 2),
      "check": None, "support": 0}
  return {"agreement": agreement, "recommended": rec}, notes

def analyze_page(raw: RawPage, user_unit: float = 1.0, budget_s: float = 30.0) -> PageAnalysis:
  started = time.monotonic()
  deadline = started + budget_s
  index = VectorIndex(raw.segs, raw.kinds, raw.rings, raw.words, raw.cropbox)
  lines = build_lines(raw.words)
  cands = find_scale_candidates(lines)
  nts = has_not_to_scale(lines)
  hint = find_units_hint(lines)
  paper = paper_size(raw.width_pt, raw.height_pt, user_unit)
  title = title_hints(lines)
  content_kind, content_info = classify_content(raw)
  declared = _pick_declared(cands, raw.cropbox, raw.rotation)
  declared["not_to_scale"] = bool(nts)

  pairs, clusters = [], []
  if content_kind != "RASTER" or raw.words:
    pairs = dimensions.find_pairs(index, raw.words, hint, deadline)
    clusters = dimensions.consensus(pairs, user_unit)

  verdict, notes = _recommend(declared, clusters, pairs, paper, user_unit, content_kind)
  main = clusters[0] if clusters else None
  members = dict(main.members) if main else {}
  by_id = {id(pairs[i]): j for i, j in members.items()}
  measured = None
  if clusters:
    shown = [p for p in pairs if not p.alt or id(p) in by_id]
    show = sorted(shown, key=lambda p: (id(p) not in by_id, -p.quality * p.length_pt))[:16]
    member_groups = {pairs[i].group for i in members if pairs[i].group >= 0}
    measured = {
      "pairs_found": len({p.group if p.group >= 0 else id(p) for p in pairs}),
      "clusters": [{"ratio": _r4(c.ratio), "support": c.support, "spread_pct": round(c.spread_pct, 3), "weight": round(c.weight, 2),
        "bbox": _cluster_bbox(c, pairs)} for c in clusters],
      "pairs": [_pair_json(p, by_id, main.ratio, user_unit) for p in show],
    }
    
    if main.support >= STRONG_SUPPORT and main.spread_pct <= STRONG_SPREAD_PCT:
      flagged = []
      for p in pairs:
        if id(p) in by_id or p.alt or p.group in member_groups:
          continue
        drawn = p.length_pt * PT_MM * user_unit * main.ratio
        for rd in p.readings:
          if rd.prior >= 0.8 and rd.value_mm > 0:
            dev = drawn / rd.value_mm - 1.0
            if 0.02 < abs(dev) < 0.35:
              flagged.append({"text": p.text, "p1": [round(p.p1[0], 3), round(p.p1[1], 3)], "p2": [round(p.p2[0], 3), round(p.p2[1], 3)],
                "printed_mm": round(rd.value_mm, 1), "drawn_mm": round(drawn, 1), "deviation_pct": round(100 * dev, 2)})
              break
          
      if flagged:
        measured["mismatches"] = flagged[:20]
  if raw.stats.get("truncated"):
    notes.append({"code": "PAGE_TRUNCATED", "message": "The sheet is very detailed and only part of its geometry was indexed. Snapping may be missing in some areas."})
  if content_kind == "RASTER" and raw.stats.get("text_source") == "OCR" and raw.words:
    notes.append({"code": "SCAN_TEXT_READ", "message": "This sheet is a scan. Its text was read by character recognition, so a figure or tag may be misread. Check the numbers that matter against the drawing."})
  elif content_kind == "RASTER" and not raw.words:
    notes.append({"code": "NO_TEXT_LAYER", "message": "This sheet is a scan with no text layer. Scale and dimensions cannot be read automatically."})
  if content_kind == "RASTER":
    notes.append({"code": "RASTER_SHEET", "message": "This sheet is an image. Measurements carry lower confidence than on a vector drawing."})
  if hint is None and any(rd.unit in ("mm", "m", "cm", "in", "ft") and rd.prior < 1.0 for p in pairs for rd in p.readings):
    pass

  detected = {"version": ANALYSIS_VERSION, "declared": declared, "measured": measured, "agreement": verdict["agreement"],
    "recommended": verdict["recommended"], "notes": notes, "units_hint": hint, "paper": paper}
  shapes = census.shape_groups(raw.rings, max(raw.width_pt * raw.height_pt, 1.0))
  tags = census.tag_census(raw.words)
  
  found_views = sheet_views.find_views(index)
  sheet_views.attach_scales(found_views, clusters, pairs, PT_MM, user_unit)
  meta = {
    "analysis_version": ANALYSIS_VERSION, "paper": paper, "title": title, "units_hint": hint, "units": UN.count_words(raw.words), "content": content_info,
    "index": {"segments": len(raw.kinds), "rings": len(raw.rings), "words": len(raw.words), "truncated": bool(raw.stats.get("truncated")),
    "path_objects": raw.stats.get("path_objects", 0), "elapsed_s": round(time.monotonic() - started + raw.stats.get("elapsed_s", 0.0), 2)},
    "shapes_top": [{k: g[k] for k in ("id", "shape", "a_pt", "b_pt", "count")} for g in shapes[:8]],
    "tags_top": [{"tag": g["tag"], "in_drawing": g["in_drawing"], "count": g["count"]} for g in tags[:12]],
    "user_unit": user_unit, "text_source": "OCR" if raw.stats.get("text_source") == "OCR" and raw.words else "TEXT",
    "facts": drawing_facts.read_facts(lines, raw.words, scanned=raw.stats.get("text_source") == "OCR"),
    "schedule": schedules.read_schedules(raw.words),
    "projections": _projections(lines, raw),
    "views": sheet_views.summary(found_views),
  }
  return PageAnalysis(content_kind=content_kind, text_chars=int(raw.stats.get("text_chars", 0)), vector_ops=int(raw.stats.get("path_objects", 0)),
    detected_scale=detected, meta=meta, index=index)

def _projections(lines, raw) -> dict:
  try:
    return projection_reader.read_projections(lines, raw.words, lambda x, y: to_visual(x, y, raw.cropbox, raw.rotation))
  except Exception:
    return {"items": [], "dims": []}

def _cluster_bbox(c, pairs) -> list:
  xs, ys = [], []
  for i, _ in c.members:
    p = pairs[i]
    xs += [p.p1[0], p.p2[0]]
    ys += [p.p1[1], p.p2[1]]
  if not xs:
    return []
  pad = 0.05 * max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
  return [round(min(xs) - pad, 2), round(min(ys) - pad, 2), round(max(xs) + pad, 2), round(max(ys) + pad, 2)]
