from __future__ import annotations
from decimal import Decimal
from app.engine.measure.member_steel import FAMILY_OF, STEEL_FAMILIES, clean_steel, member_lines
from app.engine.measure.derived import PARAMS as ENGINE_PARAMS
from app.engine.measure.member_steel_more import MORE_FAMILIES
from app.modules.drawings_boq.takeoff import repository as TR

CONVENTIONS = {"cover_mm": ENGINE_PARAMS["steel_cover_mm"][0], "hook_dia": ENGINE_PARAMS["ring_hook_dia"][0], "lap_dia": ENGINE_PARAMS["bar_lap_dia"][0],
  "anchor_dia": ENGINE_PARAMS["bar_anchor_dia"][0], "wastage_pct": ENGINE_PARAMS["steel_wastage_pct"][0]}
COVER_OF = {"LINTEL": "steel_cover_beam_mm", "BEAM": "steel_cover_beam_mm", "COLUMN": "steel_cover_column_mm", "FOOTING": "steel_cover_footing_mm", "SLAB": "steel_cover_slab_mm", "RCC_WALL": "steel_cover_wall_mm"}
ESTIMATE_NOTE = "This is an estimate from the bars as they stand, before a calculation run; the run adds the project's own steel parameters and can differ by what those add."
CONVENTION_NOTE = ("Cover, hook, lap and anchorage are site conventions. Where the drawing prints a cover or a lap table this roll-up uses it; "
  "otherwise it uses the same defaults as the calculation run, and they are flagged as defaults.")
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
  if category in ("RCC_WALL", "PARAPET"):
    return length, depth, width
  return length, width, depth

def kind_of(row) -> str:
  """The reinforced kind of a register row: its category, or for a site item the cast item it is (a tank, a parapet)."""
  if row.category == "SITE":
    return TR.FORMWORK_SITE.get((row.facts or {}).get("site_kind"), "SITE")
  return row.category

def _extra(row, cat: str, depth) -> dict | None:
  if cat == "STAIR" and depth:
    return {"stair": TR.stair_detail(row, depth)}
  if cat == "TANK":
    return {"site": TR._tank_detail(row.params or {})}
  return None

def member(row, conv: dict, cat: str | None = None) -> dict:
  p = row.params or {}
  
  steel = clean_steel(p.get("steel"))
  if not steel:
    return {"reason": "NO_BARS", "kg_each": Decimal("0"), "lines": []}
  L, W, D = _d(p.get("length_mm")), _d(p.get("width_mm")), _d(p.get("depth_mm"))
  cat = cat or row.category
  need = (L, W) if cat in ("FOOTING", "SLAB") else (L, W, D)
  if cat == "COLUMN":
    need = (L, W, D)
  if any(v is None for v in need):
    return {"reason": "NO_SIZE", "kg_each": Decimal("0"), "lines": [], "steel": steel}

  length, width, depth = _plate(cat, L, W, D or Decimal("0"))
  cover = (conv.get("cover_by_category") or {}).get(cat, conv["cover_mm"])
  lines, bare = member_lines(cat, length, width, depth, steel, Decimal(str(cover)), Decimal(str(conv["hook_dia"])), Decimal(str(conv["lap_dia"])), Decimal(str(conv["anchor_dia"])),
    conv.get("lap_table_mm") or None, _extra(row, cat, D))
  if bare <= 0:
    return {"reason": "NO_SIZE", "kg_each": Decimal("0"), "lines": [], "steel": steel}
  return {"reason": None, "kg_each": bare, "lines": lines, "steel": steel}

def resolve(conventions: dict | None, printed: dict | None) -> tuple:
  """The values a roll-up uses and where each came from: what was typed, else what the drawing prints, else the engine default."""
  given = {k: v for k, v in (conventions or {}).items() if k in CONVENTIONS and v is not None}
  conv: dict = {**CONVENTIONS, **given}
  sources = {k: ("user" if k in given else "default") for k in CONVENTIONS}
  params = (printed or {}).get("params") or {}
  by_cat = {c: float(params[n]) for c, n in COVER_OF.items() if params.get(n) is not None}
  
  if "cover_mm" not in given and by_cat:
    conv["cover_by_category"] = by_cat
    sources["cover_mm"] = "drawing"
  table = (printed or {}).get("lap_table_mm") or {}
  if "lap_dia" not in given and table:
    conv["lap_table_mm"] = {k: float(v) for k, v in table.items()}
    sources["lap_dia"] = "drawing"
  return conv, sources

def rollup(rows: list, conventions: dict | None = None, ranges: dict | None = None, printed: dict | None = None) -> dict:

  conv, sources = resolve(conventions, printed)
  wastage = Decimal(str(conv["wastage_pct"]))
  marks: list = []
  without: dict = {}
  no_size = 0
  by_family: dict = {}
  by_dia: dict = {}
  total = Decimal("0")
  for r in rows:
    cat = kind_of(r)
    if r.decision == "REJECTED" or (cat not in STEEL_FAMILIES and cat not in MORE_FAMILIES):
      continue
  
    n = int(r.count or 1)
    got = member(r, conv, cat)
    fam = FAMILY_OF.get(cat, cat)
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
  scalars = {k: float(conv[k]) for k in CONVENTIONS}
  return {"ran": bool(marks), "kg": float(total), "conventions": scalars, "sources": sources, "printed": {"cover_mm_by_category": conv.get("cover_by_category") or {}, "lap_table_mm": conv.get("lap_table_mm") or {}},
    "estimate": True, "estimate_note": ESTIMATE_NOTE, "conventions_assumed": conventions is None, "convention_note": CONVENTION_NOTE,
    "by_family": fam_out, "by_diameter": {k: {"kg": float(v["kg"]), "length_m": float(v["length_m"])} for k, v in sorted(by_dia.items(), key=lambda kv: float(kv[0]))},
    "marks": sorted(marks, key=lambda m: (m["family"], str(m["floor"] or ""), str(m["tag"] or ""))),
    "without_steel": {"members": sum(v["members"] for v in without.values()), "by_family": without},
    "without_size": no_size}
