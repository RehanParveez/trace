from __future__ import annotations
import math
import re
from app.engine.measure import readings as QS
from app.modules.drawings_boq.takeoff.prep import schedules as S
from app.modules.drawings_boq.takeoff.extract import tank_sections as TS
from app.modules.drawings_boq.takeoff.extract import tank_steel as TSTEEL
from app.modules.drawings_boq.takeoff.prep import views as VW
from app.modules.drawings_boq.takeoff.prep.texts import build_lines

TANK_WORDS = (
  ("OHWT", re.compile(r"^(?:O[./]?\s?H[./]?\s?W[./]?\s?T|OVER[- ]?HEAD)", re.I)),
  ("UGWT", re.compile(r"^U[./]?\s?G[./]?\s?W[./]?\s?T", re.I)),
)

SEPTIC_WORD = re.compile(r"^SEPTIC$", re.I)
TANK_WORD = re.compile(r"^TANK\.?$", re.I)
BOUNDARY_CAPTION = re.compile(r"\b(?:BOUNDARY|COMPOUND)\s+WALL\b", re.I)
RAMP_CAPTION = re.compile(r"\bRAMP\b", re.I)
GATE_LETTERS = "GATE"
TANK_LABEL_TEXT = {"OHWT": "Over head water tank", "UGWT": "Underground water tank", "SEPTIC": "Septic tank"}
TANK_TAG = {"OHWT": "OHWT", "UGWT": "UGWT", "SEPTIC": "SEPTIC"}
SITE_KINDS = ("OHWT", "UGWT", "SEPTIC", "BOUNDARY_WALL", "GATE", "PORCH_RAMP")
TANK_KINDS = ("OHWT", "UGWT", "SEPTIC")
WORK_ITEM = {"OHWT": "CON-RCC", "UGWT": "CON-RCC", "SEPTIC": "CON-RCC", "BOUNDARY_WALL": "MAS-BRICK", "PORCH_RAMP": "CON-RCC"}
LABEL = {"OHWT": "Over head water tank", "UGWT": "Underground water tank", "SEPTIC": "Septic tank", "BOUNDARY_WALL": "Boundary wall", "GATE": "Gate", "PORCH_RAMP": "Porch ramp"}

TYPED_FIELD = {"length_mm": "site_length_mm", "width_mm": "site_width_mm", "height_mm": "site_height_mm", "thickness_mm": "site_thickness_mm"}

TARGETS = {
  "BOUNDARY_WALL": {"length_mm": ("length_mm", "the length of the boundary wall"), "height_mm": ("depth_mm", "the height of the boundary wall"),
    "thickness_mm": ("width_mm", "the thickness of the boundary wall")},
  "GATE": {"length_mm": ("length_mm", "the width of the gate"), "height_mm": ("width_mm", "the height of the gate")},
  "PORCH_RAMP": {"length_mm": ("length_mm", "the length of the ramp"), "width_mm": ("width_mm", "the width of the ramp"), "thickness_mm": ("depth_mm", "the thickness of the ramp slab")},
}

TANK_WORDS_FOR = {"length_mm": "the outside length of the tank", "width_mm": "the outside width of the tank", "height_mm": "the outside height of the tank",
  "thickness_mm": "the thickness of the tank walls and slabs"}

def _axes(angle: float) -> tuple:
  rad = math.radians(round(angle / 90.0) % 4 * 90)
  return math.cos(rad), math.sin(rad)

def _along(w, ux: float, uy: float) -> float:
  return w.cx * ux + w.cy * uy

def _across(w, ux: float, uy: float) -> float:
  return -w.cx * uy + w.cy * ux

def _length_mm(text: str) -> float | None:
  """A dimension string as a length. A level (+12", ±0'-0") is not a length."""
  t = (text or "").strip()
  if not t or t[0] in "+±-":
    return None
  v = S.feet_inches_mm(t)
  return v if v is not None and v > 0 else None

def _side_axis(w, ux: float, uy: float) -> bool:
  """True when the text of the word runs along the caption's own writing direction (a horizontal dimension); False when it stands across it."""
  return round(((w.angle - math.degrees(math.atan2(uy, ux))) % 360) / 90.0) % 2 == 0

def _tank_labels(words: list) -> dict:
  """kind -> [word] of the labels of the tanks on this sheet."""
  out: dict = {}
  for w in words:
    t = (w.text or "").strip()
    for kind, pat in TANK_WORDS:
      if pat.search(t):
        out.setdefault(kind, []).append(w)
        
  for w in words:
    if not SEPTIC_WORD.match((w.text or "").strip()):
      continue
    ux, uy = _axes(w.angle)
    a0, c0, h = _along(w, ux, uy), _across(w, ux, uy), max(w.height, 1.0)
    for o in words:
      if o is w or not TANK_WORD.match((o.text or "").strip()) or _axes(o.angle) != (ux, uy):
        continue
      da, dc = _along(o, ux, uy) - a0, abs(_across(o, ux, uy) - c0)
      if 0 < da <= 4.0 * max(w.length, h) and dc <= 1.2 * h:
        out.setdefault("SEPTIC", []).append(w)
        break
  return out

def _tank_item(kind: str, labels: list, details: list, own: set | None = None) -> dict:
  first = labels[0]
  facts: dict = {"site_kind": kind, "tank_kind": kind, "labels_on_sheet": len(labels), "sizes_mm": {}}
  codes = [("SITE_TANK_SIZES_TYPED", {"kind": kind})]
  listed = TS.describe(kind if kind != "SEPTIC" else None, details if kind != "SEPTIC" else [])
  if listed is not None:
    facts["tank_drawings"] = listed["drawings"]
    facts["steel_options"] = TSTEEL.options(listed["drawings"])
    if facts["steel_options"]:
      codes.append(("TANK_STEEL_NOTES_LISTED", {"kind": kind, "count": len(facts["steel_options"])}))
    codes.append(("SITE_TANK_SIZES_LISTED", {"kind": kind, "printed": listed["message"]}))
  missing = ["length_mm", "width_mm", "height_mm", "thickness_mm"]
  derived = TS.derive(kind, [d for d in details if d.get("kind") == kind and (d.get("caption") or "").strip() in (own or ())] or details)

  if derived is not None:
    facts["sizes_mm"] = dict(derived["sizes_mm"])
    facts["sizes_source"] = "DRAWING_ASSUMED"
    facts["sizes_assumed"] = dict(derived["basis"])
    facts["sizes_from"] = dict(derived.get("source") or {})
    if derived["slabs_mm"]:
      facts["tank_slabs_mm"] = dict(derived["slabs_mm"])
    missing = [m for m in missing if m not in derived["sizes_mm"]]
    codes = [(c, e) for c, e in codes if c not in ("SITE_TANK_SIZES_TYPED", "SITE_TANK_SIZES_LISTED")]
    said = "; ".join(f"{TANK_WORDS_FOR[t].replace('the ', '', 1)}: {b}" for t, b in derived["basis"].items())
    codes.append(("TANK_SIZES_DERIVED", {"kind": kind, "derived": said, "left": ", ".join(derived["left"]) or None, "printed": listed["message"] if listed else None}))
  if len(labels) > 1:
    codes.append(("SITE_LABEL_REPEATED", {"count": len(labels)}))
  return {"site_kind": kind, "tag": TANK_TAG[kind], "label": LABEL[kind], "x": first.cx, "y": first.cy, "facts": facts, "params": {}, "missing": missing,
    "codes": codes, "base": 0.7}

def _within(cap: dict, size_factor: float) -> tuple:
  mid = (cap["along"][0] + cap["along"][1]) / 2.0
  half = size_factor * cap["size"]
  return mid - half, mid + half

def _top_bound(cap: dict, caps: list, lo: float, hi: float) -> float | None:
  """Across value of the nearest other caption above this one whose text overlaps the window: the view of this caption ends under it."""
  top = None
  for o in caps:
    if o is cap or o["angle"] != cap["angle"] or o["across"] <= cap["across"]:
      continue
    if min(o["along"][1], hi) - max(o["along"][0], lo) <= 0:
      continue
    if top is None or o["across"] < top:
      top = o["across"]
  return top

def _rows(items: list, tol: float) -> list:
  """Horizontal dimension strings grouped by the line they are written on (items are (along, across, value, text))."""
  rows: list = []
  for it in sorted(items, key=lambda i: -i[1]):
    for r in rows:
      if abs(r[0][1] - it[1]) <= tol:
        r.append(it)
        break
    else:
      rows.append([it])
  return rows

def _gate_label(ws: list, ux: float, uy: float) -> float | None:
  for w in ws:
    if re.fullmatch(r"GATE\.?", (w.text or "").strip(), re.I):
      return _along(w, ux, uy)
  
  singles = sorted([w for w in ws if len((w.text or "").strip()) == 1 and (w.text or "").strip().upper() in GATE_LETTERS], key=lambda w: (round(_across(w, ux, uy)), _along(w, ux, uy)))
  for i in range(len(singles) - 3):
    run = singles[i:i + 4]
    if "".join(w.text.strip().upper() for w in run) != GATE_LETTERS:
      continue
    h = max(w.height for w in run) or 1.0
    if max(_across(w, ux, uy) for w in run) - min(_across(w, ux, uy) for w in run) > h:
      continue
    al = [_along(w, ux, uy) for w in run]
    if all(b - a <= 2.5 * h for a, b in zip(al, al[1:])):
      return sum(al) / 4.0
  return None

def _near(pairs: list, at: float) -> tuple | None:
  best = None
  for al, v in pairs:
    d = abs(al - at)
    if best is None or d < best[0]:
      best = (d, v, al)
  return best

def boundary_wall(words: list, cap: dict, caps: list, mm_per_pt: float) -> list:
  ux, uy = _axes(cap["angle"])
  lo, hi = _within(cap, 20.0)
  top = _top_bound(cap, caps, lo, hi)
  inside = []
  
  for w in words:
    al, ac = _along(w, ux, uy), _across(w, ux, uy)
    if lo <= al <= hi and ac > cap["across"] + 0.5 * cap["size"] and (top is None or ac < top):
      inside.append((w, al, ac))
  across_tol = 0.9 * max((w.height for w, _, _ in inside), default=3.0)
  horiz = [(al, ac, v, w.text) for w, al, ac in inside if _side_axis(w, ux, uy) and (v := _length_mm(w.text)) is not None and v >= 150.0]
  if not horiz:
    return []
  overall = max(horiz, key=lambda i: i[2])
  rows = [r for r in _rows([h for h in horiz if h is not overall], across_tol) if len(r) >= 2]
  rows.sort(key=lambda r: abs(r[0][1] - overall[1]))
  
  pieces = None
  for r in rows:
    if abs(sum(i[2] for i in r) - overall[2]) <= max(25.0, 0.01 * overall[2]):
      pieces = sorted(r, key=lambda i: i[0])
      break
  facts: dict = {"caption": cap["text"], "overall_mm": round(overall[2], 1), "overall_text": overall[3], "pieces_mm": [round(p[2], 1) for p in pieces] if pieces else []}
  tall = [(_along(w, ux, uy), v) for w, al, ac in inside if not _side_axis(w, ux, uy) and (v := _length_mm(w.text)) is not None and 1219.2 <= v <= 4000.0]
  gate_at = _gate_label([w for w, _, _ in inside], ux, uy)
  gate = None
  
  if pieces and gate_at is not None:
    centres = [p[0] for p in pieces]
    k = min(range(len(pieces)), key=lambda i: abs(centres[i] - gate_at))
    others = [abs(centres[k] - c) for i, c in enumerate(centres) if i != k]
    if not others or abs(centres[k] - gate_at) <= 0.5 * min(others):
      gate = k
      
  out = []
  x, y = (cap["bbox"][0] + cap["bbox"][2]) / 2.0, (cap["bbox"][1] + cap["bbox"][3]) / 2.0
  if gate is not None:
    facts["gate_mm"] = round(pieces[gate][2], 1)
    wall_len = overall[2] - pieces[gate][2]
    wall_centre = max((p for i, p in enumerate(pieces) if i != gate), key=lambda p: p[2])[0] if len(pieces) > 1 else pieces[gate][0]
    wall_h = _near(tall, wall_centre)
    gate_h = _near(tall, pieces[gate][0])
  else:
    wall_len = overall[2]
    wall_h = _near(tall, (cap["along"][0] + cap["along"][1]) / 2.0)
    gate_h = None
  wall_params: dict = {"length_mm": round(wall_len, 1)}
  wall_missing = ["thickness_mm"]
  wall_codes = [("SITE_WALL_THICKNESS_TYPED", {})]
  
  several = len({round(v, 1) for _, v in tall}) > 1
  if wall_h is not None:
    wall_params["depth_mm"] = round(wall_h[1], 1)
    if several:
      wall_codes.append(("SITE_HEIGHT_NEAREST_DIMENSION", {"text": f"{wall_h[1] / 304.8:g} ft", "printed_mm": sorted({round(v, 1) for _, v in tall})}))
  else:
    wall_missing.append("height_mm")
  if pieces is None:
    wall_codes.append(("SITE_PIECES_DO_NOT_ADD_UP", {"overall": overall[3]}))
  elif gate is None:
    wall_codes.append(("SITE_GATE_NOT_LOCATED", {}))
  else:
    wall_codes.append(("SITE_GATE_TAKEN_OUT", {"gate_mm": round(pieces[gate][2], 1)}))
  wall_facts = {**facts, "site_kind": "BOUNDARY_WALL", "length_mm": round(wall_len, 1), "height_mm": round(wall_h[1], 1) if wall_h else None,
    "faces": 2, "faces_area_mm2": round(2.0 * wall_len * wall_h[1], 1) if wall_h else None,
    "gate_deducted": gate is not None, "height_pick": ("NEAREST" if several else "ONLY") if wall_h else None, "sizes_mm": {"length_mm": round(wall_len, 1), **({"height_mm": round(wall_h[1], 1)} if wall_h else {})}}
  out.append({"site_kind": "BOUNDARY_WALL", "tag": "BOUNDARY WALL", "label": f"Boundary wall · {wall_len / 304.8:g} ft long" + (f" · {wall_h[1] / 304.8:g} ft high" if wall_h else ""),
    "x": x, "y": y, "facts": wall_facts, "params": wall_params, "missing": wall_missing, "codes": wall_codes, "base": 0.8 if pieces else 0.65})
  if gate is not None:
    gw = pieces[gate][2]
    gate_params: dict = {"length_mm": round(gw, 1)}
    gate_missing: list = []
    gate_codes: list = []
    
    if gate_h is not None:
      gate_params["width_mm"] = round(gate_h[1], 1)
      if several:
        gate_codes.append(("SITE_HEIGHT_NEAREST_DIMENSION", {"text": f"{gate_h[1] / 304.8:g} ft", "printed_mm": sorted({round(v, 1) for _, v in tall})}))
    else:
      gate_missing.append("height_mm")
    out.append({"site_kind": "GATE", "tag": "GATE", "label": f"Gate · {gw / 304.8:g} ft wide" + (f" · {gate_h[1] / 304.8:g} ft high" if gate_h else ""), "x": x, "y": y,
      "facts": {**facts, "site_kind": "GATE", "width_mm": round(gw, 1), "height_mm": round(gate_h[1], 1) if gate_h else None, "height_pick": ("NEAREST" if several else "ONLY") if gate_h else None,
        "sizes_mm": {"length_mm": round(gw, 1), **({"height_mm": round(gate_h[1], 1)} if gate_h else {})}},
      "params": gate_params, "missing": gate_missing, "codes": gate_codes, "base": 0.8})
  return out

def porch_ramp(words: list, cap: dict, caps: list) -> dict:
  ux, uy = _axes(cap["angle"])
  lo, hi = _within(cap, 40.0)  
  top = _top_bound(cap, caps, lo, hi)
  found = []
  
  for w in words:
    al, ac = _along(w, ux, uy), _across(w, ux, uy)
    t = (w.text or "").strip()
    if lo <= al <= hi and ac > cap["across"] and (top is None or ac < top) and re.fullmatch(r"[+±]\s?\d{1,2}(?:'\s?-?\s?\d{1,2}\"?|\")", t):
      found.append((al, t))
  levels = list(dict.fromkeys(t for _, t in sorted(found)))
  facts = {"site_kind": "PORCH_RAMP", "caption": cap["text"], "levels_printed": levels, "sizes_mm": {}}
  return {"site_kind": "PORCH_RAMP", "tag": "PORCH RAMP", "label": LABEL["PORCH_RAMP"], "x": cap["bbox"][0], "y": cap["bbox"][1], "facts": facts, "params": {},
    "missing": ["length_mm", "width_mm", "thickness_mm"], "codes": [("SITE_RAMP_SIZES_TYPED", {"levels": levels})], "base": 0.6}

def find(words: list, mm_per_pt: float, tank_details: list | None = None) -> list:
  """[{"site_kind", "tag", "label", "x", "y", "facts", "params", "missing", "codes": [(code, extras)], "base"}] for the sheet's site items."""
  if not words:
    return []
  out: list = []
  
  own = {(ln.text or "").strip() for ln in build_lines(words)} if tank_details else set()
  for kind, labels in sorted(_tank_labels(words).items()):
    out.append(_tank_item(kind, labels, tank_details or [], own))
  caps = VW.captions(words)
  for cap in caps:
    if cap["kind"] == "ELEVATION" and BOUNDARY_CAPTION.search(cap["text"]):
      out.extend(boundary_wall(words, cap, caps, mm_per_pt))
    elif cap["kind"] in ("SECTION", "DETAIL", "PLAN") and RAMP_CAPTION.search(cap["text"]) and not BOUNDARY_CAPTION.search(cap["text"]):
        
      out.append(porch_ramp(words, cap, caps))
  seen: set = set()
  keep = []
  for it in out:
    if it["site_kind"] in seen:
      continue
    seen.add(it["site_kind"])
    keep.append(it)
  return keep

def equivalent_depth_mm(length: float, width: float, height: float, wall: float, top: float | None = None, bottom: float | None = None) -> float | None:
  top = wall if top is None else top
  bottom = wall if bottom is None else bottom
  if min(length, width) <= 2.0 * wall or height <= top + bottom or wall <= 0:
    return None
  concrete = length * width * height - (length - 2 * wall) * (width - 2 * wall) * (height - top - bottom)
  return concrete / (length * width)

def typed_sizes(kind: str, missing: list, typed: dict, facts: dict) -> dict:
  """The sizes of an item as known now: the ones the sheet printed (in facts) with the ones typed for the missing tokens on top."""
  out = dict((facts or {}).get("sizes_mm") or {})
  tank = (facts or {}).get("site_kind") in TANK_KINDS
  for token in (TYPED_FIELD if tank else (missing or [])):
    v = (typed or {}).get(TYPED_FIELD.get(token, ""))
    if v is not None:
      out[token] = float(v)
  return out

def fill_site(kind: str, missing: list, params: dict, typed: dict, facts: dict) -> tuple:
  """(params, problem) for a site item being accepted: every missing size must have been typed. A tank's concrete is walls and slabs of one thickness, so its
  params carry the outside length and width and the equivalent depth."""
  out = dict(params or {})
  sizes = typed_sizes(kind, missing, typed, facts)
  
  if kind in TANK_KINDS:
    for token in ("length_mm", "width_mm", "height_mm", "thickness_mm"):
      if sizes.get(token) is None:
         return out, ("CANDIDATE_NEEDS_DIMENSIONS", f"Give {TANK_WORDS_FOR[token]} to measure this item.")
    slabs = (facts or {}).get("tank_slabs_mm") or {}
    top = float(slabs.get("top_mm") or QS.convention("tank_top_slab_mm"))
    bottom = float(slabs.get("bottom_mm") or QS.convention("tank_bottom_slab_mm"))
    depth = equivalent_depth_mm(sizes["length_mm"], sizes["width_mm"], sizes["height_mm"], sizes["thickness_mm"], top, bottom)
    if depth is None:
      return out, ("CANDIDATE_BAD_VALUES", "The walls are thicker than half the tank. Check the sizes you typed.")
    out.update({"length_mm": sizes["length_mm"], "width_mm": sizes["width_mm"], "depth_mm": round(depth, 1), "dims_basis": "SPECIFIED",
      "height_mm": sizes["height_mm"], "wall_mm": sizes["thickness_mm"], "top_mm": top, "bottom_mm": bottom})
    return out, None
  targets = TARGETS.get(kind) or {}
  
  for token in missing or []:
    spec = targets.get(token)
    if spec is None:
      return out, ("CANDIDATE_NEEDS_DIMENSIONS", "No size was found for this item. Draw it by hand.")
    value = (typed or {}).get(TYPED_FIELD[token])
    
    if value is None:
      return out, ("CANDIDATE_NEEDS_DIMENSIONS", f"Give {spec[1]} to measure this item.")
    out[spec[0]] = float(value)
    out["dims_basis"] = "SPECIFIED"
  return out, None
