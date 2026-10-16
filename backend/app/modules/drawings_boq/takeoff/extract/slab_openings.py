from __future__ import annotations
import math
import re
from app.modules.drawings_boq.takeoff.levels import LEVELS
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import rooms as R
from app.modules.drawings_boq.takeoff.extract.members import parse_size

_VOID = re.compile(r"(?<![A-Z])(?P<w>AIR\s*SHAFTS?|SERVICE\s*SHAFTS?|PIPE\s*SHAFTS?|LIFT\s*(?:WELL|SHAFT)S?|LIGHT\s*WELL|SKY\s*LIGHT|SKYLIGHT|SHAFTS?|DUCTS?|VOIDS?|"
  r"OPEN\s+TO\s+(?:SKY|ABOVE|BELOW)|SLAB\s+OPENING|OPENING\s+IN\s+SLAB)(?![A-Z])", re.I)
_LANDING = re.compile(r"(?<![A-Z])LANDINGS?(?![A-Z])", re.I)
_ABOVE = re.compile(r"LIGHT\s*WELL|SKY|OPEN\s+TO\s+ABOVE", re.I)

def below(level: str | None, known) -> str | None:
  """The nearest floor under `level` among the floors the drawing has (the ROOF is above every numbered floor)."""
  if level not in LEVELS:
    return None
  seq = LEVELS[level][1]
  lower = [(LEVELS[k][1], k) for k in known if k in LEVELS and LEVELS[k][1] < seq and k != "FOUNDATION"]
  return max(lower)[1] if lower else None

def _dist(a: tuple, b: tuple) -> float:
  return math.hypot(a[0] - b[0], a[1] - b[1])

def _pair(labels: list, sized: list, reach_pt: float, same_line_ok) -> None:
  """Gives each label the size printed with it: on its own line, else the nearest line that is only a size. A size line is given to one label."""
  pairs = []
  for li, lab in enumerate(labels):
    for si, sz in enumerate(sized):
      if sz["line"] is lab["line"]:
        if same_line_ok(lab, sz):
          pairs.append((0.0, li, si))
        continue
    
      if sz["has_name"]:
        continue
      d = _dist((lab["x"], lab["y"]), (sz["x"], sz["y"]))
      if d <= reach_pt:
        pairs.append((d, li, si))
  pairs.sort()
  done, used = set(), set()
  for d, li, si in pairs:
    if li in done or si in used:
      continue
    labels[li]["size"] = sized[si]
    done.add(li)
    used.add(si)

def read_labels(lines: list, hint: str | None, mm_per_pt: float) -> dict:
  if not lines or mm_per_pt <= 0:
    return {"voids": [], "landings": [], "unsized": 0}
  reach = C.VOID_LABEL_REACH_MM / mm_per_pt
  merged = R.merge_split_sizes(lines)
  labels = []
  for ln in merged:
    if not ln.spans:
      continue
  
    t = ln.text.upper()
    for kind, rx in (("VOID", _VOID), ("LANDING", _LANDING)):
      for m in rx.finditer(t):
        x, y = ln.locate(m.start(), m.end())
        labels.append({"kind": kind, "name": re.sub(r"\s+", " ", m.group(0).strip()), "x": x, "y": y, "line": ln, "size": None})
        
  if not labels:
    return {"voids": [], "landings": [], "unsized": 0}
  sized = []
  for ln in merged:
    if not ln.spans or getattr(ln, "angle", 0) != 0:
      continue
    size = parse_size(ln.text, hint)
    if size is None:
      continue
  
    x, y = ln.locate(0, len(ln.text))
    names = [m for m in R._NAME.finditer(ln.text.upper())]
    sized.append({"line": ln, "text": ln.text.strip(), "mm": size, "x": x, "y": y, "has_name": bool(names) or bool(_VOID.search(ln.text) or _LANDING.search(ln.text))})
  def same_line_ok(lab, sz) -> bool:
    others = [m for m in R._NAME.finditer(sz["text"].upper())]
    return not others
  _pair(labels, sized, reach, same_line_ok)
  voids, landings, unsized = [], [], 0
  for lab in labels:
    sz = lab["size"]
    if sz is None:
      unsized += 1
      continue
  
    a, b = sz["mm"]
    area = a * b / 1e6
    floor_side = C.LANDING_MIN_SIDE_MM if lab["kind"] == "LANDING" else C.VOID_MIN_SIDE_MM
    if min(a, b) < floor_side or area > C.OPENING_MAX_M2 or area <= 0:
      unsized += 1
      continue
    item = {"name": lab["name"], "text": sz["text"], "w_mm": float(a), "h_mm": float(b), "area_m2": round(area, 3), "x": round(lab["x"], 3), "y": round(lab["y"], 3)}
    if lab["kind"] == "LANDING":
      landings.append(item)
    else:
      item["side"] = "ABOVE" if _ABOVE.search(lab["name"]) else "BELOW"
      voids.append(item)
  return {"voids": voids, "landings": landings, "unsized": unsized}

def attach_landings(stairs: list, landings: list, mm_per_pt: float, gap) -> tuple:
  """Puts each printed landing on the stair whose flight is nearest to it (within STAIR_LANDING_REACH_MM). Returns (landings attached, landings left)."""
  reach = C.STAIR_LANDING_REACH_MM / mm_per_pt
  taken: dict = {}
  left = []
  for lan in landings:
    best, best_d = None, reach
    for i, st in enumerate(stairs):
      box = (st.facts or {}).get("flight_box")
      if not box:
          
        continue
      d = gap(box, lan["x"], lan["y"])
      if d <= best_d:
        best, best_d = i, d
    if best is None:
      left.append(lan)
    else:
      taken.setdefault(best, []).append(lan)
  for i, items in taken.items():
    st = stairs[i]
    st.facts = {**(st.facts or {}), "landings": [{k: v for k, v in it.items() if k not in ("x", "y")} for it in items],
      "landings_area_m2": round(sum(it["area_m2"] for it in items), 3)}
    st.notes = [n for n in st.notes if n.get("code") != "STAIR_LANDINGS_NOT_INCLUDED"]
    st.notes.append(C.note("STAIR_LANDINGS_ADDED", count=len(items), area_m2=st.facts["landings_area_m2"]))
  return sum(len(v) for v in taken.values()), left

def sheet_entries(stairs: list, voids: list, level: str | None) -> list:
  out = []
  for st in stairs:
    f = st.facts or {}
    way = f.get("direction")
    if way not in ("UP", "DOWN") or not f.get("flight_area_m2"):
      continue
    out.append({"kind": "STAIR_WELL", "way": way, "level_hint": level, "area_m2": float(f["flight_area_m2"]), "name": "Stair well", "key": st.key,
      "text": f"{f.get('steps') or '?'} steps, {f.get('treads_drawn') or '?'} treads drawn"})
  for v in voids:
    out.append({"kind": "PRINTED", "side": v["side"], "level_hint": level, "area_m2": v["area_m2"], "name": v["name"], "text": v["text"], "key": None})
  return out

def _choose_source(per_sheet: dict) -> dict:
  """When one floor is drawn on more than one sheet, the sheet whose entries cover the most area is used, not the sum."""
  best = None
  for sid, grp in per_sheet.items():
    total = sum(e["area_m2"] for e in grp["entries"])
    key = (total, -int(grp["page_no"] or 0))
    if best is None or key > best[0]:
      best = (key, grp)
  return best[1]

def by_level(sheets: list, exts: dict) -> dict:
  """{level: {"page_no", "entries"}} from the entries each sheet stored in its stats."""
  groups: dict = {}
  for s in sorted(sheets, key=lambda x: x.page_no):
    st = (exts[s.id].stats or {}) if s.id in exts else {}
    for e in st.get("slab_openings") or []:
      lvl = e.get("level_hint")
      if not lvl:
        continue
    
      g = groups.setdefault(lvl, {}).setdefault(s.id, {"page_no": s.page_no, "entries": []})
      g["entries"].append(e)
  return {lvl: _choose_source(per) for lvl, per in groups.items() if per}

def place(levels: dict, known) -> dict:
  up: dict = {}
  down: dict = {}
  other: dict = {}
  
  for lvl, grp in levels.items():
    for e in grp["entries"]:
      item = {**e, "page_no": grp["page_no"], "from_level": lvl}
      if e["kind"] == "STAIR_WELL":
        if e["way"] == "UP":
          up.setdefault(lvl, []).append(item)
        else:
          tgt = below(lvl, known)
          if tgt:
            down.setdefault(tgt, []).append(item)
      else:
        tgt = lvl if e.get("side") == "ABOVE" else below(lvl, known)
        if tgt:
          other.setdefault(tgt, []).append(item)
  out: dict = {}
  for slab in set(up) | set(down) | set(other):
    a, b = up.get(slab, []), down.get(slab, [])
    sa, sb = sum(i["area_m2"] for i in a), sum(i["area_m2"] for i in b)
    wells, twin = (a, sb or None) if sa >= sb else (b, sa or None)
    out[slab] = {"items": [*wells, *other.get(slab, [])], "twin_area_m2": twin}
  return out

def entries_for_facts(items: list) -> list:
  out = []
  for it in items:
    out.append({"kind": it["kind"], "name": it["name"], "text": it["text"], "area_m2": round(float(it["area_m2"]), 3), "from_level": it["from_level"],
      "page_no": it["page_no"], "way": it.get("way"), "deduct": float(it["area_m2"]) > C.SLAB_OPENING_FREE_M2})
  return out

def deducted_area(openings: list) -> float:
  return round(sum(float(o["area_m2"]) for o in openings or [] if o.get("deduct")), 3)

def slab_adjustments(facts: dict, depth_mm) -> list:
  """The LESS lines of a slab measurement: each opening bigger than 0.1 m2, as area x the thickness of the slab (m3). [] when there is nothing to take off or no thickness."""
  if not depth_mm:
    return []
  out = []
  for o in (facts or {}).get("openings") or []:
    if not o.get("deduct"):
      continue
    v = round(float(o["area_m2"]) * float(depth_mm) / 1000.0, 6)
    if v > 0:
      out.append({"op": "LESS", "value": v, "label": f"{o['name']} {float(o['area_m2']):.2f} m2 (page {o.get('page_no')})"[:120]})
  return out

def stair_adjustments(facts: dict, waist_mm) -> list:
  """The ADD lines of a stair measurement: each printed landing, as area x the waist thickness (m3)."""
  if not waist_mm:
    return []
  out = []
  for l in (facts or {}).get("landings") or []:
    v = round(float(l["area_m2"]) * float(waist_mm) / 1000.0, 6)
    if v > 0:
      out.append({"op": "ADD", "value": v, "label": f"Landing {l['text']} = {float(l['area_m2']):.2f} m2"[:120]})
  return out

def net_slab_m3(gross_m3: float, facts: dict, depth_mm) -> float:
  """What the register shows for a slab not yet measured: the volume less what the openings take off."""
  less = sum(a["value"] for a in slab_adjustments(facts, depth_mm))
  return max(0.0, gross_m3 - less)

def landing_m3(facts: dict, waist_mm) -> float:
  return sum(a["value"] for a in stair_adjustments(facts, waist_mm))
