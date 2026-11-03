from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.proof import known_facts as KF
from app.modules.drawings_boq.takeoff.prep import closure_facts as CF
from app.engine.measure import readings as RD

FT_TOL = 0.05
IN_TOL = 0.26
MM_FOOT = 304.8
MM_INCH = 25.4
LEVEL_KEYS = ("porch", "ground", "first", "terrace", "roof", "parapet_level", "parapet_top", "plinth")

def _result(text: str, status: str, expected, found, message: str, pages: list) -> dict:
  return {"text": text, "status": status, "expected": expected, "found": found, "message": message, "pages": sorted(set(p for p in pages if p))}

def _near(a, b, tol: float) -> bool:
  return a is not None and b is not None and abs(float(a) - float(b)) <= tol

def _same_mix(a, b) -> bool:
  return a is not None and b is not None and re.sub(r"\s+", "", str(a)) == re.sub(r"\s+", "", str(b))

def _steps(rec: list) -> list:
  return sorted((float(s["width_in"]), float(s["height_in"])) for s in rec or [])

def _verdict(text: str, rows: list, pages: list, stated_only: list | None = None) -> dict:
  extra = f" Stated, not read by Trace: {', '.join(stated_only)}." if stated_only else ""
  if not rows or all(r[2] is None for r in rows):
    return _result(text, KF.MISSING, [r[1] for r in rows], None, "Nothing of this was read from the sheets." + extra, pages)
  bad = [r for r in rows if not r[3]]
  shown = {r[0]: r[2] for r in rows}
  if not bad:
    return _result(text, KF.PASS, {r[0]: r[1] for r in rows}, shown, f"{len(rows)} value(s) read: as printed." + extra, pages)
  return _result(text, KF.FAIL, {r[0]: r[1] for r in rows}, shown, "; ".join(f"{r[0]}: {r[2] if r[2] is not None else 'not read'} read, {r[1]} stated" for r in bad) + "." + extra, pages)

def wall_footing(read: list, f: dict) -> dict:
  mark = str(f["mark"]).upper()
  text = f"wall footing {mark}"
  got = CF.wall_footing(read, mark)
  
  if got is None:
    return _result(text, KF.MISSING, mark, None, f"No section marked {mark} was read with steps.", [])
  rows = [("wall_in", f.get("wall_in"), got["wall_in"], _near(got["wall_in"], f.get("wall_in"), 0.01)),
    ("exterior", f.get("exterior"), got["exterior"], got["exterior"] == bool(f.get("exterior")))]
  for key in ("trench_width_in", "depth_below_ngl_in", "pcc_in", "sand_in", "dpc_in"):
    if f.get(key) is not None:
      rows.append((key, f[key], got[key], _near(got[key], f[key], IN_TOL)))
  for key in ("pcc_mix", "dpc_mix"):
    if f.get(key) is not None:
      rows.append((key, f[key], got[key], _same_mix(got[key], f[key])))
  if f.get("steps") is not None:
    want, have = _steps(f["steps"]), _steps(got["steps"])
    rows.append(("steps", want, have, len(want) == len(have) and all(_near(a[0], b[0], IN_TOL) and _near(a[1], b[1], IN_TOL) for a, b in zip(want, have))))
    
  return _verdict(text, rows, [got["page"]])

def vertical_dpc(read: list, f: dict) -> dict:
  hits = CF.items(read, "VERTICAL_DPC")
  text = "vertical DPC on exterior walls"
  if not hits:
    return _result(text, KF.MISSING, "VERTICAL_DPC", None, "No vertical DPC detail was read.", [])
  page, it = hits[0]
  
  rows = [("from_outside_level", True, it["from_outside_level"], bool(it["from_outside_level"])), ("to_inside_ffl", True, it["to_inside_ffl"], bool(it["to_inside_ffl"]))]
  if f.get("plaster_mix") is not None:
    rows.append(("plaster_mix", f["plaster_mix"], it.get("plaster_mix"), _same_mix(it.get("plaster_mix"), f["plaster_mix"])))
  if f.get("bitumen_coats") is not None:
    rows.append(("bitumen_coats", f["bitumen_coats"], it.get("bitumen_coats"), it.get("bitumen_coats") == int(f["bitumen_coats"])))
  return _verdict(text, rows, [page])

def column_footing(read: list, f: dict) -> dict:
  mark = re.sub(r"[^A-Z0-9]", "", str(f["mark"]).upper())
  text = f"column footing {f['mark']}"
  sized, pages = [], []
  
  for sh in read:
    for c in sh["candidates"]:
      p = c.params or {}
      if c.category == "FOOTING" and re.sub(r"[^A-Z0-9]", "", str(c.tag or "").upper()) == mark and p.get("length_mm") and p.get("width_mm"):
        sized.append(sorted([float(p["length_mm"]), float(p["width_mm"])]))
        pages.append(sh["page_no"])
        
  if not sized:
    return _result(text, KF.MISSING, str(f["mark"]), None, f"No footing marked {f['mark']} was read with a size.", [])
  want = sorted([float(f["l_ft"]) * MM_FOOT, float(f["w_ft"]) * MM_FOOT])
  rows = [("size_ft", sorted([float(f["l_ft"]), float(f["w_ft"])]), [round(v / MM_FOOT, 2) for v in sized[0]], any(all(_near(a, b, FT_TOL * MM_FOOT) for a, b in zip(s, want)) for s in sized))]
  drawings = {sh.get("drawing") for sh in read if sh["page_no"] in set(pages)}
  beds = {(round(it["value_mm"], 1), it["mix"]) for sh in read if sh.get("drawing") in drawings for it in ((sh.get("meta") or {}).get("facts") or {}).get("items") or []
    if it.get("kind") == "PCC_THICKNESS" and it.get("scope") == "pcc bed" and it.get("mix")}
  
  one = next(iter(beds)) if len(beds) == 1 else None
  if f.get("pcc_in") is not None:
    got = round(one[0] / MM_INCH, 2) if one else None
    rows.append(("pcc_in", f["pcc_in"], got, _near(got, f["pcc_in"], IN_TOL)))
  if f.get("pcc_mix") is not None:
    rows.append(("pcc_mix", f["pcc_mix"], one[1] if one else None, _same_mix(one[1] if one else None, f["pcc_mix"])))
  return _verdict(text, rows, pages, ["pcc_offset_in"] if f.get("pcc_offset_in") is not None else None)

def _layer_key(l: dict) -> tuple:
  return (str(l["material"]).lower(), round(float(l["thickness_mm"]), 0), re.sub(r"\s+", "", str(l.get("mix") or "")))

def floor_buildup(read: list, f: dict) -> dict:
  floor = str(f["floor"]).upper()
  text = f"floor build-up {floor.lower().replace('_', ' ')}"
  got = CF.floor_buildup(read, floor)
  
  if got is None:
    return _result(text, KF.MISSING, floor, None, f"No specification block for {floor.lower()} was read.", [])
  want = sorted(_layer_key({"material": l["material"], "thickness_mm": float(l["thickness_in"]) * MM_INCH, "mix": l.get("mix")}) for l in f["layers"])
  have = sorted(_layer_key(l) for l in got["layers"])
  rows = [("layers", [f"{k[0]} {k[1] / MM_INCH:g} in {k[2]}".strip() for k in want], [f"{k[0]} {k[1] / MM_INCH:g} in {k[2]}".strip() for k in have], want == have)]
  for key in ("termite_proofed", "compacted_earth", "waterproofed"):
    if f.get(key) is not None:
      rows.append((key, bool(f[key]), got[key], got[key] == bool(f[key])))
  block = CF.blocks(read).get(floor)
  return _verdict(text, rows, [block["page_no"]] if block else [])

def roof_spec(read: list, f: dict) -> dict:
  roof = str(f["roof"]).upper()
  text = f"roof {roof.lower().replace('_', ' ')} waterproofing"
  got = CF.floor_buildup(read, roof)
  if got is None:
    return _result(text, KF.MISSING, roof, None, f"No specification block for {roof.lower()} was read.", [])
  rows = [("waterproofed", bool(f["waterproofed"]), got["waterproofed"], got["waterproofed"] == bool(f["waterproofed"]))]
  return _verdict(text, rows, [CF.blocks(read)[roof]["page_no"]] if roof in CF.blocks(read) else [])

def termite_scope(read: list, f: dict) -> dict:
  text = "termite treatment scope"
  notes = CF.items(read, "TERMITE_NOTE")
  ground = CF.floor_buildup(read, "GROUND")
  if not notes and not (ground and ground["termite_proofed"]):
    return _result(text, KF.MISSING, "TERMITE_SCOPE", None, "No termite treatment note was read.", [])
  beds = any(it["beds"] for _p, it in notes)
  sides = any(it["side_slopes"] for _p, it in notes)
  
  rows = []
  for key, got in (("beds", beds), ("side_slopes", sides), ("floor", bool(ground and ground["termite_proofed"]))):
    if f.get(key) is not None:
      rows.append((key, bool(f[key]), got, got == bool(f[key])))
  return _verdict(text, rows, [p for p, _it in notes])

def do_not_scale(read: list, f: dict) -> dict:
  hits = CF.items(read, "DO_NOT_SCALE")
  if not hits:
    return _result("do not scale note", KF.MISSING, "printed", None, "No do-not-scale note was read.", [])
  return _result("do not scale note", KF.PASS, "printed", "printed", f"The note is printed on {len({p for p, _i in hits})} sheet(s): dimensions written on the drawing govern.", [p for p, _i in hits])

def plaster_mix(read: list, f: dict) -> dict:
  hits = CF.items(read, "PLASTER_MIX")
  if not hits:
    return _result("plaster mixes", KF.MISSING, "PLASTER_MIX", None, "No plaster mix note was read.", [])
  page, it = hits[0]
  return _verdict("plaster mixes", [("internal", f["internal"], it["internal"], _same_mix(it["internal"], f["internal"])), ("external", f["external"], it["external"], _same_mix(it["external"], f["external"]))], [page])

def mortar_mix(read: list, f: dict) -> dict:
  hits = CF.items(read, "MORTAR_MIX")
  if not hits:
    return _result("brickwork mortar mixes", KF.MISSING, "MORTAR_MIX", None, "No mortar mix note was read.", [])
  page, it = hits[0]
  want = {"9": f.get("in_9"), "4.5": f.get("in_4_5")}
  rows = [(f"{k} in wall", v, it["by_wall_in"].get(k), _same_mix(it["by_wall_in"].get(k), v)) for k, v in want.items() if v is not None]
  return _verdict("brickwork mortar mixes", rows, [page])

def lintel_table(read: list, f: dict) -> dict:
  hits = CF.items(read, "LINTEL_SPAN")
  if not hits:
    return _result("lintel table", KF.MISSING, "LINTEL_TABLE", None, "No lintel table was read.", [])
  have = {it["mark"]: it["max_span_ft"] for _p, it in hits}
  rows = [(r["mark"], r["max_span_ft"], have.get(str(r["mark"]).upper()), _near(have.get(str(r["mark"]).upper()), r["max_span_ft"], 0.01)) for r in f["rows"]]
  return _verdict("lintel table", rows, [p for p, _i in hits])

def levels(read: list, f: dict) -> dict:
  got = CF.level_names(read)
  rows = []
  for key in LEVEL_KEYS:
    want = f.get(f"{key}_ft")
    if want is not None:
      mm = got.get(f"{key}_mm")
      rows.append((f"{key}_ft", want, round(mm / MM_FOOT, 3) if mm is not None else None, mm is not None and abs(mm / MM_FOOT - float(want)) <= FT_TOL))
  return _verdict("levels above the road", rows, [])

def sill_detail(read: list, f: dict) -> dict:
  hits = CF.items(read, "SILL_DETAIL")
  if not hits:
    return _result("window sill detail", KF.MISSING, "SILL_DETAIL", None, "No window sill detail was read.", [])
  rows = [("mark", str(f["mark"]).upper(), hits[0][1]["mark"], hits[0][1]["mark"] == str(f["mark"]).upper())]
  if f.get("material"):
    mat = CF.items(read, "SILL_MATERIAL")
    rows.append(("material", f["material"], mat[0][1]["material"] if mat else None, bool(mat) and mat[0][1]["material"] == f["material"]))
  return _verdict("window sill detail", rows, [p for p, _i in hits])

def fact_conflict(read: list, f: dict) -> dict:
  about = str(f["about"]).upper()
  text = f"printed conflict: {about.lower().replace('_', ' ')}"
  if about == "SLAB_THICKNESS":
    got = CF.slab_conflict(read, RD.flag("facts.structure_governs_concrete"))
    if got is None:
      return _result(text, KF.MISSING, f.get("values_in"), None, "The layout-plan slab note was not read, so the conflict is not shown.", [])
    have = sorted(round(v / MM_INCH, 2) for v in got["values_mm"])
    want = sorted(float(v) for v in f["values_in"])
    return _verdict(text, [("values_in", want, have, len(want) == len(have) and all(_near(a, b, IN_TOL) for a, b in zip(want, have)))], [])

  if about == "ROOF_LEVEL":
    got = CF.level_conflicts(read)
    if not got:
      return _result(text, KF.MISSING, f.get("other_ft"), None, "No elevation mark differing from the sections was read.", [])
    rows = [("section_ft", f["section_ft"], round(got[0]["section_mm"] / MM_FOOT, 3), _near(got[0]["section_mm"] / MM_FOOT, f["section_ft"], FT_TOL)),
      ("other_ft", f["other_ft"], round(got[0]["other_mm"] / MM_FOOT, 3), any(_near(g["other_mm"] / MM_FOOT, f["other_ft"], FT_TOL) for g in got))]
    return _verdict(text, rows, [g["page"] for g in got])
  raise ValueError("about must be SLAB_THICKNESS or ROOF_LEVEL")

def foundation_outline(read: list, f: dict) -> dict:
  docs = [(sh["page_no"], (sh.get("meta") or {}).get("foundation_runs") or {}) for sh in read]
  docs = [(p, d) for p, d in docs if d.get("read") == "OK"]
  text = "foundation plan outline"
  if not docs:
    return _result(text, KF.MISSING, [f["long_ft"], f["short_ft"]], None, "No foundation layout plan was read as a wall plan (no scale agreed with its printed dimensions).", [])

  page, d = docs[0]
  got = sorted(v / MM_FOOT for v in d["outline_mm"])
  want = sorted([float(f["short_ft"]), float(f["long_ft"])])
  rows = [("outline_ft", want, [round(v, 2) for v in got], all(_near(a, b, 0.5) for a, b in zip(got, want)))]
  if f.get("runs_min") is not None:
    rows.append(("runs", f"at least {f['runs_min']}", len(d["runs"]), len(d["runs"]) >= int(f["runs_min"])))
  return _verdict(text, rows, [page])

from app.modules.drawings_boq.takeoff.extract.crosschecks import _live, _sheet_floor
SFT_PER_M2 = 10.7639104

def covered_area(read: list, f: dict) -> dict:
  floor = KF.floor_key(f["floor"])
  text = f"printed area of the {floor.title()} floor plan"
  got = CF.covered_area(read, floor)
  
  if got is None:
    return _result(text, KF.MISSING, f["area_sft"], None, f"No printed area was read under a {floor.title()} floor plan title.", [])
  slab = sum(float((c.facts or {}).get("area_m2") or 0.0) for sh in read if _sheet_floor(sh) == floor for c in sh["candidates"] if c.category == "SLAB" and _live(c)) * SFT_PER_M2
  extra = f" The slab Trace measured for this floor is {slab:,.0f} sft ({(slab - got['value_sft']) / got['value_sft'] * 100:+.1f}% from the printed area)." if slab else ""
  verdict = _verdict(text, [("area_sft", float(f["area_sft"]), got["value_sft"], _near(got["value_sft"], f["area_sft"], 0.5))], got["pages"])
  verdict["message"] += extra
  return verdict

CHECKS = {"COVERED_AREA": covered_area, "FOUNDATION_OUTLINE": foundation_outline, "WALL_FOOTING": wall_footing, "VERTICAL_DPC": vertical_dpc, "COLUMN_FOOTING": column_footing, "FLOOR_BUILDUP": floor_buildup, "ROOF_SPEC": roof_spec, "TERMITE_SCOPE": termite_scope,
  "DO_NOT_SCALE": do_not_scale, "PLASTER_MIX": plaster_mix, "MORTAR_MIX": mortar_mix, "LINTEL_TABLE": lintel_table, "LEVELS": levels, "SILL_DETAIL": sill_detail, "FACT_CONFLICT": fact_conflict}
