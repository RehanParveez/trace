from __future__ import annotations
from decimal import Decimal
from app.engine.measure.units import q6

JOINTS_PARAM, BEARING_PARAM = "formwork_joints", "formwork_lintel_bearing_mm"
CODE = "FORMWORK_JOINT_ASSUMED"
MM2_PER_M2 = Decimal("1000000")
BY_BEARING, BY_CHAJJA, BY_BALCONY = "lintel bearing on the wall", "chajja on the lintel", "balcony on the slab edge"
KINDS = (BY_BEARING, BY_CHAJJA, BY_BALCONY)
HALF = Decimal("0.5")

def _empty(enabled: bool) -> dict:
  return {"enabled": enabled, "reason": None, "lintels": 0, "chajjas_matched": 0, "chajjas_unmatched": 0, "balconies_matched": 0, "balconies_unmatched": 0,
    "uncertain_members": 0, "removed_m2": "0", "removed_by": {}}

def _usable(m, counted: set, category: str) -> bool:
  return m.category == category and str(m.measurement_id) in counted and m.length_mm > 0 and m.width_mm > 0 and m.depth_mm > 0

def joint_cuts(inputs: tuple, counted: set, enabled: bool, bearing_mm: Decimal, slab_edges_on: bool, lintel_rate_on: bool) -> tuple:
  stats = _empty(enabled)
  if not enabled:
    return {}, stats
  out: dict = {}
  removed: dict = {k: Decimal("0") for k in KINDS}

  def add(key, face: str, kind: str, by: str, area: Decimal, uncertain: bool):
    if area <= 0:
      return
    cut = out.setdefault(key, {"faces": [], "uncertain": False, "code": CODE})
    cut["faces"].append({"face": face, "by": by, "area_mm2": float(area), "kind": kind, "joint": True})
    cut["uncertain"] = cut["uncertain"] or uncertain
    removed[kind] += area / MM2_PER_M2

  lintels = [m for m in sorted(inputs, key=lambda b: str(b.measurement_id)) if _usable(m, counted, "LINTEL")]
  if lintel_rate_on:
    stats["reason"] = "LINTEL_PER_RFT_RATE"
    lintels = []

  for m in lintels:
    each = min(2 * bearing_mm, m.length_mm * HALF) * m.width_mm
    stats["lintels"] += m.count
    for i in range(m.count):
      add((str(m.measurement_id), i), "soffit", BY_BEARING, "bearing on the wall", each, False)

  by_level: dict = {}
  for m in lintels:
    by_level.setdefault(m.level_id, []).append(m)
  room: dict = {}
  for chajja in sorted((m for m in inputs if _usable(m, counted, "CHAJJA")), key=lambda b: str(b.measurement_id)):
    here = by_level.get(chajja.level_id) or []
    if not here:
      stats["chajjas_unmatched"] += chajja.count
      continue
    seats = sum(m.count for m in here)
    guess = seats != chajja.count
    for _ in range(chajja.count):
      whole = todo = chajja.length_mm * chajja.depth_mm
      for lintel in here:
        for i in range(lintel.count):
          key = (str(lintel.measurement_id), i)
          if key not in room:
            room[key] = lintel.length_mm * min(chajja.depth_mm, lintel.depth_mm)
          take = min(todo, room[key])
          if take <= 0:
            continue
          room[key] -= take
          todo -= take
          add(key, "sides", BY_CHAJJA, f"chajja {chajja.tag or ''}".strip(), take, guess)
        if todo <= 0:
          break
      if todo < whole:
        stats["chajjas_matched"] += 1
        stats["uncertain_members"] += 1 if guess else 0
      else:
        stats["chajjas_unmatched"] += 1

  slabs: dict = {}
  for m in inputs:
    if _usable(m, counted, "SLAB"):
      slabs.setdefault(m.level_id, []).append(m)

  edge_room: dict = {}
  for balcony in sorted((m for m in inputs if _usable(m, counted, "BALCONY_SLAB")), key=lambda b: str(b.measurement_id)):
    here = slabs.get(balcony.level_id) if slab_edges_on else None
    if not here:
      stats["balconies_unmatched"] += balcony.count
      continue

    ref = max(here, key=lambda b: (b.count * b.length_mm * b.width_mm * b.depth_mm, str(b.measurement_id)))
    mixed = len({b.depth_mm for b in here}) > 1
    joined = max(balcony.length_mm, balcony.width_mm) * min(balcony.depth_mm, ref.depth_mm)
    for _ in range(balcony.count):
      whole = todo = joined
      for k in range(ref.count):
        key = (str(ref.measurement_id), k)
        if key not in edge_room:
          edge_room[key] = 2 * (ref.length_mm + ref.width_mm) * ref.depth_mm
        take = min(todo, edge_room[key])
        if take <= 0:
          continue

        edge_room[key] -= take
        todo -= take
        add(key, "edges", BY_BALCONY, f"balcony {balcony.tag or ''}".strip(), take, mixed)
        if todo <= 0:
          break
      if todo < whole:
        stats["balconies_matched"] += 1
        stats["uncertain_members"] += 1 if mixed else 0
      else:
        stats["balconies_unmatched"] += 1

  stats["removed_by"] = {k: str(q6(v)) for k, v in removed.items() if v > 0}
  stats["removed_m2"] = str(q6(sum(removed.values(), Decimal("0"))))
  return out, stats

def merge(*cuts: dict) -> dict:
  out: dict = {}
  for part in cuts:
    for key, cut in part.items():
      into = out.setdefault(key, {"faces": [], "uncertain": False, "code": cut.get("code"), "codes": []})
      into["faces"].extend(cut["faces"])
      if cut.get("uncertain"):
        into["uncertain"] = True
        for code in (cut.get("codes") or [cut.get("code")]):
          if code and code not in into["codes"]:
            into["codes"].append(code)
  return out
