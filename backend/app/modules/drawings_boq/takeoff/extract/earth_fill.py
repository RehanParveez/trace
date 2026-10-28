from __future__ import annotations
import math
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import spec_facts as SF
from app.modules.drawings_boq.takeoff.prep import facts as DF
import re
from statistics import median

FILL_ITEM = FD.EARTH_FILL
DEFAULT_LAYER_MM = 152.4
NGL_WORD = re.compile(r"^(?:N\.?\s?G\.?\s?L\.?|NATURAL\s+GROUND(?:\s+LEVEL)?)$", re.I)
NGL_SAME_LINE = 1.5
NGL_AGREE_MM = 25.0
BUILD_UP = ("pcc", "brick ballast", "sand filling", "cement sand bed", "brick tiles", "mud plaster")

def natural_ground_mm(words: list) -> float | None:
  """The level printed beside an NGL / N.G.L. mark on the sheet (a sign and its value may be two words), or None when no mark has a level beside it or the marks disagree."""
  vals = []
  for w in words or []:
    if not NGL_WORD.match(DF._fix((w.text or "").strip())):
      continue
    size = max(float(getattr(w, "size", 0.0) or 0.0), 1.0)
    near = sorted((x for x in words if x is not w and abs(x.cy - w.cy) <= NGL_SAME_LINE * size and abs(x.cx - w.cx) <= C.NGL_REACH * size), key=lambda x: abs(x.cx - w.cx))
    for i, x in enumerate(near):
      text = DF._fix((x.text or "").strip())
      mm = DF.level_mark_mm(text)
      if mm is None and text in ("+", "-", "\u00b1") and i + 1 < len(near):
        mm = DF.level_mark_mm(text + DF._fix((near[i + 1].text or "").strip()))
      if mm is not None:
        vals.append(mm)
        break
  if not vals or max(vals) - min(vals) > NGL_AGREE_MM:
    return None
  return float(median(vals))

def fill_depth(floor_heights: dict | None, level_hint: str | None, ngl_mm: float | None, spec_facts: dict | None) -> dict | None:
  fh = (floor_heights or {}).get(level_hint or "") or {}
  level = fh.get("level_mm")
  if level is None:
    return None
  if ngl_mm is not None:
    ground, how = float(ngl_mm), "NGL"
  elif fh.get("basis") == "PLAN_NOTES":
    ground, how = 0.0, "ROAD_LEVEL"
  else:
    return None
  head = SF.floor_set(spec_facts, level_hint)
  layers = head["layers"] if head else (spec_facts or {}).get("layers") or {}
  got = {n: float(layers[n]["value_mm"]) for n in BUILD_UP if layers.get(n) and layers[n].get("value_mm")}
  if not got:
    return None
  up = round(sum(got.values()), 1)
  return {"mm": round(float(level) - ground - up, 1), "level_mm": float(level), "ground_mm": ground, "ground_basis": how, "build_up_mm": up, "build_up": got}

def layers_of(depth_mm: float, layer_mm: float | None) -> int:
  layer = float(layer_mm or DEFAULT_LAYER_MM)
  if depth_mm <= 0 or layer <= 0:
    return 0
  return int(math.ceil(round(depth_mm / layer, 6)))

def fill_candidate(rooms: list, ctx: dict, level_hint: str | None, spec, cls, finish, levels: dict | None = None):
  if level_hint == "BASEMENT":
    return None
  total, used, pts = 0.0, 0, []
  
  for r in rooms:
    f = r.facts or {}
    if r.category != "ROOM" or r.status == "INVALID" or any(n.get("code") == "ROOM_INSIDE_ROOM" for n in r.notes or []):
      continue
    a = float(f.get("area_m2") or 0.0)
    if a > 0.0:
      total += a
      used += 1
      
      pts.extend((r.geometry or {}).get("outer") or (r.geometry or {}).get("points") or [])
  if used == 0:
    return None
  if levels is not None and levels["mm"] < C.FILL_MIN_MM:
    return None
  from_levels = levels is not None and levels["mm"] <= C.FILL_MAX_MM
  dug = FD._assumed(FILL_ITEM)
  depth = levels["mm"] if from_levels else dug["mm"]
  facts = {"derived_from": "ROOMS", "room_count": used, "area_m2": round(total, 3), "layers": layers_of(depth, None)}
  if from_levels:
    facts["depth_from_levels"] = levels
  else:
    facts["depth_assumed"] = dug
  label = f"Earth filling under the floor · {total:.2f} m²" + (f" · {spec[0]}" if spec else "")
  return FD._make(cls, ctx, finish, (FILL_ITEM, level_hint or ""), FILL_ITEM, label, "EARTH-FILL", [FD._centre(pts)],
    {"length_mm": round(total * 1000.0, 1), "width_mm": 1000.0, "depth_mm": depth}, [],
    [C.note("FILL_FROM_ROOMS"), C.note("FILL_DEPTH_FROM_LEVELS", **{k: levels[k] for k in ("mm", "level_mm", "ground_mm", "ground_basis", "build_up_mm")}) if from_levels else C.note("FILL_DEPTH_ASSUMED", reason=dug["text"])], facts, 0.7)

