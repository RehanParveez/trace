from __future__ import annotations
import math
import re
from itertools import combinations
from app.modules.drawings_boq.takeoff.prep import region_ocr as RO
from app.modules.drawings_boq.takeoff.prep import sheet_marks as SM

PT_MM = 25.4 / 72.0
UNIT_MM = {"ft": 304.8, "m": 1000.0, "mm": 1.0, "cm": 10.0, "in": 25.4}
_UNIT_WORD = re.compile(r"^[\(\[]?(FEET|FOOT|FEETS|FT|MTRS?|METERS?|METRES?|M|MM|CM|INCHES|INCH|IN)[\.\)\]:]*$", re.I)
_NUMBER = re.compile(r"^[\(\[]?(\d{1,4})(?:\s*(FT|FEET|MTRS?|METERS?|METRES?|M|MM|CM))?[\.\)\]]*$", re.I)
_UNIT_KEY = {"FEET": "ft", "FOOT": "ft", "FEETS": "ft", "FT": "ft", "MTR": "m", "MTRS": "m", "METER": "m", "METERS": "m", "METRE": "m", "METRES": "m", "M": "m", "MM": "mm", "CM": "cm",
  "INCH": "in", "INCHES": "in", "IN": "in"}

SNAP_TOL = 0.035            
AGREE_TOL = 0.06            
MIN_INLIERS = 3
MIN_LENGTH_PT = 24.0        
MAX_PAGE_SHARE = 0.6        
FIT_SHARE = 0.04            
FIT_MIN_PT = 1.5
LINE_TOL = 0.8              
SIZE_RATIO = 1.7            
UNIT_AHEAD = 12.0           
UNIT_BEHIND = 3.0
UNIT_ACROSS = 3.5           

BAR_REGIONS = (("BOTTOM_RIGHT", (0.45, 0.58, 1.0, 1.0)), ("BOTTOM_LEFT", (0.0, 0.58, 0.55, 1.0)))
BAR_PASSES = ((300.0, "11"), (300.0, "6"))

STANDARD = (1, 2, 2.5, 4, 5, 8, 10, 12, 16, 20, 24, 25, 30, 32, 40, 48, 50, 60, 64, 75, 96, 100, 120, 125, 128, 150, 192, 200, 240, 250, 300, 360, 400, 480, 500, 600, 720, 750, 1000, 1200,
  1250, 1500, 2000, 2500, 5000)

def snap(ratio: float):
  best = min(STANDARD, key=lambda s: abs(ratio / s - 1.0))
  return (float(best), True) if abs(ratio / best - 1.0) <= SNAP_TOL else (float(ratio), False)

def _h(w) -> float:
  v = getattr(w, "height", None) or getattr(w, "size", None) or 0.0
  return float(v) if v else max(abs(w.y1 - w.y0), 1.0)

def _basis(w):
  th = math.radians(float(getattr(w, "angle", 0.0) or 0.0))
  return math.cos(th), math.sin(th)

def _lines(items: list) -> list:
  out: list = []
  for it in sorted(items, key=lambda i: (round((i["ang"] % 180.0) / 4.0), i["p"], i["s"])):
    for ln in out:
      if abs(((ln["ang"] - it["ang"] + 90.0) % 180.0) - 90.0) <= 4.0 and abs(ln["p"] - it["p"]) <= LINE_TOL * max(ln["h"], it["h"]) and 1.0 / SIZE_RATIO <= it["h"] / ln["h"] <= SIZE_RATIO:
        ln["items"].append(it)
        break
    else:
      out.append({"ang": it["ang"], "p": it["p"], "h": it["h"], "items": [it]})
  return out

def _fit(items: list):
  vals = {}
  for it in items:
    vals.setdefault(it["v"], []).append(it)
  if len(vals) < MIN_INLIERS:
    return None

  vmax = max(vals)
  best = None
  for i, j in combinations(items, 2):
    if i["v"] == j["v"]:
      continue
    b = (j["s"] - i["s"]) / (j["v"] - i["v"])
    if b == 0:
      continue
    a = i["s"] - b * i["v"]
    tol = max(FIT_MIN_PT, FIT_SHARE * abs(b) * vmax)
    chosen: dict = {}
    for it in items:
      res = abs(it["s"] - (a + b * it["v"]))
      if res <= tol and (it["v"] not in chosen or res < chosen[it["v"]][0]):
        chosen[it["v"]] = (res, it)
    if len(chosen) < MIN_INLIERS:
      continue
    ordered = sorted(chosen)
    triple = any(ordered[k + 1] - ordered[k] == ordered[k + 2] - ordered[k + 1] for k in range(len(ordered) - 2))
    if not triple:
      continue
    rms = math.sqrt(sum(r ** 2 for r, _ in chosen.values()) / len(chosen))
    key = (len(chosen), 0 in chosen, -rms)
    if best is None or key > best[0]:
      best = (key, [it for _, it in chosen.values()], a, b, rms)
  return None if best is None else best[1:]

def _find_unit(words: list, line: dict, inl: list, b: float, hint: str | None):
  ux, uy = _basis(inl[0]["w"])
  nx, ny = -uy, ux
  h = line["h"]
  s_lo, s_hi = min(i["s"] for i in inl), max(i["s"] for i in inl)
  pitch = abs(b) * max(1.0, min((sorted({i["v"] for i in inl})[k + 1] - sorted({i["v"] for i in inl})[k]) for k in range(len(inl) - 1)) if len(inl) > 1 else 1.0)
  best = None

  for w in words:
    t = (w.text or "").strip()
    m = _UNIT_WORD.match(t)
    if not m:
      continue
    s = w.cx * ux + w.cy * uy
    p = w.cx * nx + w.cy * ny
    if abs(p - line["p"]) > UNIT_ACROSS * h:
      continue
    if s < s_lo - UNIT_BEHIND * pitch or s > s_hi + UNIT_AHEAD * pitch:
      continue
    unit = _UNIT_KEY.get(m.group(1).upper())
    if unit == "m" and len(t) == 1 and t.upper() == "M" and abs(s - s_hi) > 3.0 * pitch and abs(s - s_lo) > 3.0 * pitch:
      continue
    d = min(abs(s - s_hi), abs(s - s_lo))
    if best is None or d < best[0]:
      best = (d, unit, t)
  if best:
    return best[1], best[2]
  for i in inl:
    m = _NUMBER.match((i["w"].text or "").strip())
    if m and m.group(2):
      return _UNIT_KEY.get(m.group(2).upper()), m.group(0)
  if hint in ("ft-in", "ft"):
    return "ft", None
  if hint in ("mm", "m", "cm"):
    return hint, None
  return None, None

def read(words: list, user_unit: float = 1.0, hint: str | None = None, page_pt: tuple | None = None) -> dict | None:
  items: list = []

  for w in words:
    t = (w.text or "").strip()
    m = _NUMBER.match(t)
    zero = t in ("O", "o")
    if not (m or zero) or float(getattr(w, "size", 1.0) or 1.0) <= 0.4:
      continue
    ux, uy = _basis(w)
    nx, ny = -uy, ux
    items.append({"w": w, "v": 0 if zero else int(m.group(1)), "s": w.cx * ux + w.cy * uy, "p": w.cx * nx + w.cy * ny, "h": _h(w), "ang": float(getattr(w, "angle", 0.0) or 0.0)})

  if len(items) < MIN_INLIERS:
    return None
  found: list = []
  for ln in _lines(items):
    if len(ln["items"]) < MIN_INLIERS:
      continue
    fit = _fit(ln["items"])
    if fit is None:
      continue
    inl, a, b, rms = fit
    has_zero = any(i["v"] == 0 for i in inl)
    length = abs(b) * (max(i["v"] for i in inl) - min(i["v"] for i in inl))
    limit = MAX_PAGE_SHARE * max(page_pt or (1e9, 1e9))
    if length < MIN_LENGTH_PT or length > limit:
      continue
    unit, unit_text = _find_unit(words, ln, inl, b, hint)
    if unit is None:
      continue
    if not has_zero and not (len(inl) >= 4 and unit_text):
      continue
    mm_per_pt = UNIT_MM[unit] / abs(b)
    ratio = mm_per_pt / (PT_MM * user_unit)
    if not (0.5 <= ratio <= 20000):
      continue

    snapped, is_std = snap(ratio)
    values = sorted({i["v"] for i in inl})
    found.append({"source": "SCALE_BAR", "ratio": round(ratio, 3), "scale_ratio": round(snapped, 3), "snapped": is_std, "unit": unit, "unit_text": unit_text,
      "labels": values, "pitch_pt": round(abs(b), 3), "length_pt": round(length, 1), "fit_pt": round(rms, 3), "inliers": len(inl), "zero": has_zero,
      "strong": len(inl) >= 4 or (len(inl) >= 3 and rms <= 0.8),
      "x": round(sum(i["w"].cx for i in inl) / len(inl), 1), "y": round(sum(i["w"].cy for i in inl) / len(inl), 1)})

  if not found:
    return None
  found.sort(key=lambda f: (-f["inliers"], f["fit_pt"]))
  best = found[0]
  best["others"] = [{"ratio": f["scale_ratio"], "labels": f["labels"]} for f in found[1:4]]
  best["agree"] = all(abs(f["scale_ratio"] / best["scale_ratio"] - 1.0) <= AGREE_TOL for f in found[1:])
  return best

_BARE_SLASH = re.compile(r"^\s*([13])\s*/\s*(\d{1,2})\s*$")

def imperial_reading(text: str | None) -> float | None:
  m = _BARE_SLASH.match(text or "")
  if not m:
    return None
  a, b = int(m.group(1)), int(m.group(2))
  if b not in (2, 4, 8, 16, 32) or a >= b:
    return None
  return 12.0 * b / a

def caption(words: list, bar: dict) -> float | None:
  from app.modules.drawings_boq.takeoff.prep.texts import build_lines, find_scale_candidates
  reach = max(1.3 * float(bar.get("length_pt") or 0.0), 45.0)
  near = [w for w in words if math.hypot(w.cx - bar["x"], w.cy - bar["y"]) <= reach]
  if not near:
    return None
  try:
    cands = find_scale_candidates(build_lines(near))
  except Exception:
    return None
  cands = [c for c in cands if math.hypot(c["x"] - bar["x"], c["y"] - bar["y"]) <= reach]
  if not cands:
    return None

  cands.sort(key=lambda c: (not c.get("labelled"), math.hypot(c["x"] - bar["x"], c["y"] - bar["y"])))
  best = cands[0]
  if bar.get("unit") in ("ft", "in"):
    fixed = imperial_reading(best.get("text"))
    if fixed is not None:
      return fixed
  return float(best["ratio"])

def witness(bar: dict, caption_ratio: float | None = None) -> dict:
  return {"source": "SCALE_BAR", "labels": len(bar["labels"]), "read": bar["inliers"], "ratio": bar["ratio"], "scale_ratio": bar["scale_ratio"], "snapped": bar["snapped"], "support": bar["inliers"],
    "spread_pct": round(100.0 * bar["fit_pt"] / max(bar["length_pt"], 1.0), 3), "strong": bool(bar["strong"]), "unit": bar["unit"], "values": bar["labels"], "pitch_pt": bar["pitch_pt"],
    "length_pt": bar["length_pt"], "caption_ratio": caption_ratio, "check": None}

def _text(ratio: float) -> str:
  return "1:" + format(round(float(ratio), 4), "f").rstrip("0").rstrip(".")

def _rec(ratio: float, basis: str, trust: float, support: int) -> dict:
  return {"method": "SCALE_RATIO", "ratio": round(float(ratio), 4), "scale_text": _text(ratio), "basis": basis, "trust": trust, "check": None, "support": int(support)}

def _strip_declared(text: str | None):
  from app.modules.drawings_boq.takeoff.scale import parse_scale_text
  t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text or "")
  ratio = parse_scale_text(t)
  if ratio is None:
    return None
  r = float(ratio)
  snapped, usual = snap(r)
  return (snapped, t) if usual else None

def _relation(bar_ratio: float, base: float) -> str:
  g = bar_ratio / base
  if abs(g - 1.0) <= AGREE_TOL:
    return "AGREE"
  return "CONFLICT"

def apply(full: dict, bar: dict | None, caption_ratio: float | None, strip_text: str | None, raster: bool) -> dict:
  out = dict(full)
  notes = [dict(n) for n in (out.get("notes") or [])]
  declared = dict(out.get("declared") or {"candidates": [], "primary": None, "multi_scale": False})
  agreement, rec = out.get("agreement"), out.get("recommended")

  if declared.get("primary") is None and strip_text and not declared.get("not_to_scale"):
    got = _strip_declared(strip_text)
    if got is not None:
      ratio, text = got
      declared["primary"] = {"text": text, "ratio": ratio, "labelled": True, "zone": "TITLE", "tier": 0, "trust": 0.6, "ambiguous": False, "source": "TITLE_STRIP"}
      out["declared"] = declared
      if agreement == "NONE" and rec is None:
        agreement = out["agreement"] = "DECLARED_ONLY"
        rec = out["recommended"] = _rec(ratio, "DECLARED", 0.5 if raster else 0.6, 0)
        notes = [n for n in notes if n.get("code") != "NO_SCALE_FOUND"]
        notes.append({"code": "SCALE_FROM_TITLE_STRIP", "message": f"The scale was read from the scale box of the title strip ({text}). No dimension confirmed it."})

  if bar is not None:
    wit = witness(bar, caption_ratio)
    out["witnesses"] = [*(out.get("witnesses") or []), wit]
    b = float(bar["scale_ratio"] if bar["snapped"] else bar["ratio"])
    prim = declared.get("primary")
    if agreement == "DECLARED_ONLY" and prim and rec and bar["strong"]:
      if declared.get("multi_scale") and caption_ratio is None:
        pass
      else:
        d = float(caption_ratio or prim["ratio"])
        reads = [d]
        
        alt = imperial_reading(prim.get("text")) if caption_ratio is None else None
        if alt is not None and abs(alt / d - 1.0) > 0.01:
          reads.append(alt)
        agreeing = next((r for r in reads if _relation(b, r) == "AGREE"), None)
        if agreeing is not None:
          if agreeing != d:
            declared["primary"] = {**prim, "ratio": agreeing, "text": f"{prim.get('text')} (read as {_text(agreeing)})", "repaired": True}
            out["declared"] = declared
            notes.append({"code": "SCALE_TEXT_REPAIRED", "message": f"The printed scale reads {prim.get('text')}; with its quote marks lost it is {_text(agreeing)}, which the scale bar confirms."})
          out["agreement"] = "VERIFIED_WEAK"
          out["recommended"] = _rec(agreeing, "DECLARED_AND_BAR", 0.9, bar["inliers"])
          if declared.get("multi_scale"):
            notes.append({"code": "MULTI_SCALE", "message": "Other drawings on this sheet carry their own scale caption. The scale bar and its caption give the scale of the rest of the sheet; calibrate the captioned views separately."})
        else:
          out["agreement"] = "WITNESS_CONFLICT"
          notes.append({"code": "SCALE_WITNESS_CONFLICT", "message": (
            f"The printed scale is {_text(d)} but the graphic scale bar of the sheet measures about {_text(b)}. Either the sheet was printed at another size than its label says, or the bar was not drawn "
            "to the sheet's scale. Check one known length before measuring.")})
    elif agreement == "DIMENSIONS_WEAK" and rec and bar["strong"]:
      if _relation(b, float(rec["ratio"])) == "AGREE":
        out["agreement"] = "VERIFIED_WEAK"
        out["recommended"] = {**rec, "trust": max(float(rec.get("trust") or 0.0), 0.85), "basis": "DIMENSIONS_AND_BAR"}
      else:
        notes.append({"code": "SCALE_BAR_DIFFERS", "message": f"The scale bar of the sheet measures about {_text(b)}, which is not the scale the few readable dimensions give ({_text(float(rec['ratio']))})."})
    elif agreement in ("NONE", "CONFLICT_UNRESOLVED", "MULTI_SCALE") and bar["strong"]:
      notes.append({"code": "SCALE_BAR_UNCONFIRMED", "message": f"A graphic scale bar was found (about {_text(b)}), but no printed scale or dimension confirms it. A bar alone is not used to set the scale."})
  out["notes"] = notes
  return out

def read_bar(page, rotation: int, cropbox: tuple, words: list, user_unit: float = 1.0, hint: str | None = None, picture: bool = False) -> dict:
  size = None
  if page is not None:
    try:
      size = page.get_size()
    except Exception:
      size = None

  bar = read(words, user_unit, hint, size)
  basis, pool, tried = "TEXT", words, []
  if bar is None and picture and page is not None and size is not None:
    Wv, Hv = size
    for name, (fx0, fy0, fx1, fy1) in BAR_REGIONS:
      box = (Wv * fx0, Hv * fy0, Wv * fx1, Hv * fy1)
      for dpi, psm in BAR_PASSES:
        extra, _info = RO.read_region(page, rotation, cropbox, box, dpi=dpi, psm=psm)
        tried.append({"region": name, "dpi": dpi, "psm": psm, "words": len(extra)})
        if not extra:
          continue

        merged = SM._merge(words, extra, RO.user_box(box, rotation, cropbox))
        for cand, label in ((extra, "REGION_OCR"), (merged, "REGION_OCR")):
          bar = read(cand, user_unit, hint, size)
          if bar is not None:
            basis, pool = label, cand
            break
        if bar is not None:
          break
      if bar is not None:
        break
  cap = caption(pool, bar) if bar is not None else None
  return {"bar": bar, "caption": cap, "basis": basis if bar is not None else "NONE", "tried": tried}
