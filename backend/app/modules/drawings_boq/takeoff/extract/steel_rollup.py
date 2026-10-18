from __future__ import annotations
from decimal import Decimal
from app.engine.measure.member_steel import FAMILY_OF, STEEL_FAMILIES, clean_steel, member_lines

CONVENTIONS = {"cover_mm": 40.0, "hook_dia": 16.0, "lap_dia": 0.0, "anchor_dia": 0.0, "wastage_pct": 0.0}
CONVENTION_NOTE = ("Cover, hook, lap and anchorage are site conventions. This roll-up uses the values above (laps and anchorage are not added unless you set them); "
  "the calculation run uses the steel parameters of your project, so its weight can differ by what those add.")
MM3_PER_M3 = Decimal("1000000000")

def _d(v) -> Decimal | None:
  try:
    x = Decimal(str(v))
  except Exception:
    return None
  return x if x > 0 else None

def _floor(f: dict) -> str | None:
  return f.get("floor") or f.get("level_hint") or (f.get("view") or {}).get("level_hint") or (f.get("floor_union") or {}).get("floor")

def _plate(category: str, length: Decimal, width: Decimal, depth: Decimal) -> tuple:
  if category == "RCC_WALL":
    return length, depth, width
  return length, width, depth

def member(row, conv: dict) -> dict:
  p = row.params or {}
  
  steel = clean_steel(p.get("steel"))
  if not steel:
    return {"reason": "NO_BARS", "kg_each": Decimal("0"), "lines": []}
  L, W, D = _d(p.get("length_mm")), _d(p.get("width_mm")), _d(p.get("depth_mm"))
  cat = row.category
  need = (L, W) if cat in ("FOOTING", "SLAB") else (L, W, D)
  if cat == "COLUMN":
    need = (L, W, D)
  if any(v is None for v in need):
    return {"reason": "NO_SIZE", "kg_each": Decimal("0"), "lines": [], "steel": steel}

  length, width, depth = _plate(cat, L, W, D or Decimal("0"))
  lines, bare = member_lines(cat, length, width, depth, steel, Decimal(str(conv["cover_mm"])), Decimal(str(conv["hook_dia"])), Decimal(str(conv["lap_dia"])), Decimal(str(conv["anchor_dia"])))
  if bare <= 0:
    return {"reason": "NO_SIZE", "kg_each": Decimal("0"), "lines": [], "steel": steel}
  return {"reason": None, "kg_each": bare, "lines": lines, "steel": steel}

def rollup(rows: list, conventions: dict | None = None, ranges: dict | None = None) -> dict:
  conv = {**CONVENTIONS, **{k: v for k, v in (conventions or {}).items() if k in CONVENTIONS and v is not None}}
  wastage = Decimal(str(conv["wastage_pct"]))
  marks: list = []
  without: dict = {}
  no_size = 0
  by_family: dict = {}
  by_dia: dict = {}
  total = Decimal("0")
  for r in rows:
    if r.decision == "REJECTED" or r.category not in STEEL_FAMILIES:
      continue
  
    n = int(r.count or 1)
    got = member(r, conv)
    fam = FAMILY_OF.get(r.category, r.category)
    if got["reason"] == "NO_BARS":
      slot = without.setdefault(fam, {"members": 0, "marks": []})
      slot["members"] += n
      if r.tag and r.tag not in slot["marks"]:
        slot["marks"].append(r.tag)
      continue
    if got["reason"] == "NO_SIZE":
      no_size += n
      continue
  
    kg = (got["kg_each"] * n * (1 + wastage / 100)).quantize(Decimal("0.000001"))
    total += kg
    f = r.facts or {}
    src = ((f.get("steel_source") or {}).get("grade")) or "PRINTED"
    p = r.params or {}
    conc = None
    
    if all(_d(p.get(k)) is not None for k in ("length_mm", "width_mm", "depth_mm")):
      conc = Decimal(str(p["length_mm"])) * Decimal(str(p["width_mm"])) * Decimal(str(p["depth_mm"])) * n / MM3_PER_M3
    marks.append({"item_ids": [str(r.id)], "tag": r.tag, "category": r.category, "family": fam, "floor": _floor(f), "count": n, "decision": r.decision,
      "steel_text": f.get("steel_text"), "source": src, "kg_each": float(got["kg_each"]), "kg": float(kg), "concrete_m3": float(conc) if conc is not None else None})
    slot = by_family.setdefault(fam, {"marks": 0, "members": 0, "kg": Decimal("0"), "bare_kg": Decimal("0"), "kg_sized": Decimal("0"), "concrete_m3": Decimal("0")})
    slot["marks"] += 1
    slot["members"] += n
    slot["kg"] += kg
    slot["bare_kg"] += got["kg_each"] * n
    if conc is not None:
      slot["kg_sized"] += got["kg_each"] * n
      slot["concrete_m3"] += conc
    for ln in got["lines"]:
      d = by_dia.setdefault(str(Decimal(ln["dia_mm"]).quantize(Decimal("0.1"))), {"kg": Decimal("0"), "length_m": Decimal("0")})
      d["kg"] += Decimal(ln["kg"]) * n
      d["length_m"] += Decimal(ln["length_m"]) * n
      
  fam_out = {}
  for fam, s in sorted(by_family.items()):
    band = (ranges or {}).get(fam)
    value = float(s["kg_sized"] / s["concrete_m3"]) if s["concrete_m3"] > 0 else None
    status = None
    
    if value is not None and band:
      status = "BELOW_RANGE" if value < band[0] else "ABOVE_RANGE" if value > band[1] else "IN_RANGE"
    fam_out[fam] = {"marks": s["marks"], "members": s["members"], "kg": float(s["kg"]), "concrete_m3": float(s["concrete_m3"]) if s["concrete_m3"] > 0 else None,
      "kg_per_m3": round(value, 1) if value is not None else None, "range": list(band) if band else None, "status": status}
  return {"ran": bool(marks), "kg": float(total), "conventions": conv, "conventions_assumed": conventions is None, "convention_note": CONVENTION_NOTE,
    "by_family": fam_out, "by_diameter": {k: {"kg": float(v["kg"]), "length_m": float(v["length_m"])} for k, v in sorted(by_dia.items(), key=lambda kv: float(kv[0]))},
    "marks": sorted(marks, key=lambda m: (m["family"], str(m["floor"] or ""), str(m["tag"] or ""))),
    "without_steel": {"members": sum(v["members"] for v in without.values()), "by_family": without},
    "without_size": no_size}
