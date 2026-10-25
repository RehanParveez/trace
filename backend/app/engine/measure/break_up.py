from __future__ import annotations
import re
from app.engine.measure import proposed as QP

CEMENT, SAND, COARSE, BRICK = "Cement (OPC)", "Sand (fine aggregate)", "Coarse aggregate", "Brick"
BAG, M3, NOS = "bag (50 kg)", "m3", "nos"
CONCRETE_KIND, MASONRY_KIND, PLASTER_KIND = "CONCRETE", "MASONRY", "PLASTER_MORTAR"
PLASTER_MORTAR_CODE = "FIN-PLASTER-MORTAR"
NEEDS_THICKNESS = {"FIN-PLASTER": "plaster", "FLR-CS-BED": "cement-sand bed", "FIN-ROOF-SCREED": "roof screed"}
_RATIO3 = re.compile(r"^\s*1\s*:\s*(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\s*$")
_RATIO2 = re.compile(r"^\s*1\s*:\s*(\d+(?:\.\d+)?)\s*$")

def _f(v) -> float:
  try:
    return float(v)
  except (TypeError, ValueError):
    return 0.0

def _unit(u) -> str:
  return re.sub(r"[^a-z0-9]", "", str(u or "").lower().replace("\u00b3", "3").replace("\u00b2", "2")).replace("cum", "m3")

def _label(parts: tuple) -> str:
  return ":".join(format(p, "g") for p in parts)

def concrete_mix(texts: list) -> tuple:
  """(mix, label, basis, unresolved): the mix printed on the drawing, else None. A grade that is not a nominal mix (M30, C25/30, 5000 psi) is unresolved."""
  unresolved = None
  for text in texts:
    if not text:
      continue
    g = str(text).strip()
    m = _RATIO3.match(g)
    if m:
      return (1.0, float(m.group(1)), float(m.group(2))), g, "DRAWING", None
    mix = QP.NOMINAL_MIX_BY_GRADE.get(g.upper().replace(" ", "")) or QP.NOMINAL_MIX_BY_PSI.get(g.lower().replace(" ", ""))
    if mix:
      return mix, f"{g} (as {_label(mix)})", "DRAWING", None
    unresolved = unresolved or g
  return None, None, None, unresolved

def mortar_mix(texts: list, default: tuple) -> tuple:
  for text in texts:
    m = _RATIO2.match(str(text or ""))
    if m:
      return (1.0, float(m.group(1))), str(text).strip(), "DRAWING"
  return default, _label(default), "ASSUMED"

def _material(name: str, unit: str, per_unit: float, qty: float, waste: float | None) -> dict:
  return {"material": name, "unit": unit, "per_unit": round(per_unit, 4), "quantity": round(qty, 4), "with_waste": round(qty * (waste or 1.0), 4)}

def _binder(wet_m3: float, dry_factor: float, mix: tuple) -> dict:
  """Cement, sand and (for a three-part mix) coarse aggregate of wet_m3 of concrete or mortar, by the dry-volume method."""
  dry = wet_m3 * dry_factor
  parts = sum(mix)
  cement_m3 = dry / parts
  out = {CEMENT: cement_m3 * QP.CEMENT_KG_M3 / QP.BAG_KG, SAND: cement_m3 * mix[1]}
  if len(mix) > 2:
    out[COARSE] = cement_m3 * mix[2]
  return out

def bricks_per_m3() -> tuple:
  """(bricks, mortar m3) in one m3 of brickwork: the brick size with the joint on every face; the rest of the volume is mortar."""
  l, w, h = (x / 1000.0 for x in QP.BRICK_MM)
  j = QP.JOINT_MM / 1000.0
  n = 1.0 / ((l + j) * (w + j) * (h + j))
  return n, 1.0 - n * l * w * h

def _line(row: dict, kind: str, mix_label: str, basis: str, mats: dict, qty: float, waste: float | None, units: dict) -> dict:
  return {"item_id": str(row.get("item_id") or row.get("source_item_id") or ""), "name": row.get("name") or row.get("material_name"), "work_item_code": row.get("work_item_code"),
    "unit": row.get("unit"), "quantity": round(qty, 4), "kind": kind, "mix": mix_label, "mix_basis": basis, "waste_factor": waste,
    "materials": [_material(k, units[k], v / qty if qty else 0.0, v, waste) for k, v in mats.items()]}

def build(rows: list) -> dict:
  lines: list = []
  skipped: list = []
  totals: dict = {}
  plaster_mortar_present = any(str(r.get("work_item_code") or "") == PLASTER_MORTAR_CODE for r in rows)
  UNITS = {CEMENT: BAG, SAND: M3, COARSE: M3, BRICK: NOS}

  for row in rows:
    code = str(row.get("work_item_code") or "")
    item_type = str(getattr(row.get("item_type"), "value", row.get("item_type")) or "")
    if item_type == "LABOUR" or row.get("is_manual"):
      continue
    qty = _f(row.get("quantity"))
    unit = _unit(row.get("unit"))
    name = row.get("name") or row.get("material_name")
    item_id = str(row.get("item_id") or row.get("source_item_id") or "")
    waste = _f(row.get("waste_factor_applied")) or None
    spec = row.get("spec") if isinstance(row.get("spec"), dict) else {}
    if qty <= 0:
      continue

    def skip(why: str):
      skipped.append({"item_id": item_id, "name": name, "work_item_code": code, "reason": why})

    if code in NEEDS_THICKNESS and not (code == "FIN-PLASTER" and plaster_mortar_present):
      skip(f"The {NEEDS_THICKNESS[code]} is billed by area and the drawing prints no thickness, so its mortar cannot be worked out. Give the thickness (for plaster, the plaster thickness in the site assumptions makes the mortar a line of its own).")
      continue

    if code in ("CON-RCC", "CON-PCC") or (code.startswith("CON-") and unit == "m3"):
      if unit != "m3":
        skip("The concrete is not billed in cubic metres, so the mix cannot be applied.")
        continue
      mix, label, basis, unresolved = concrete_mix([spec.get("grade"), row.get("material_grade")])
      if mix is None and unresolved:
        skip(f"The mix {unresolved} is a design mix: its cement content is not a ratio. Give the cement content per cubic metre, or the nominal mix to use.")
        continue
      if mix is None:
        mix = QP.DEFAULT_PCC_MIX if code == "CON-PCC" else QP.DEFAULT_RCC_MIX
        label, basis = _label(mix), "ASSUMED"
      lines.append(_line(row, CONCRETE_KIND, label, basis, _binder(qty, QP.CONCRETE_DRY_FACTOR, mix), qty, waste, UNITS))
    elif code == "MAS-BRICK":
      if unit != "m3":
        skip("The brickwork is not billed in cubic metres, so the bricks and mortar cannot be worked out.")
        continue

      n, mortar_wet = bricks_per_m3()
      mix, label, basis = mortar_mix([spec.get("mortar"), row.get("material_grade")], QP.DEFAULT_BRICK_MORTAR)
      mats = {BRICK: n * qty, **_binder(mortar_wet * qty, QP.MORTAR_DRY_FACTOR, mix)}
      lines.append(_line(row, MASONRY_KIND, label, basis, mats, qty, waste, UNITS))
    elif code == PLASTER_MORTAR_CODE:
      if unit != "m3":
        skip("The plaster mortar is not in cubic metres.")
        continue
      mix, label, basis = mortar_mix([row.get("material_grade")], QP.DEFAULT_PLASTER_MORTAR)
      lines.append(_line(row, PLASTER_KIND, label, basis, _binder(qty, QP.PLASTER_DRY_FACTOR, mix), qty, waste, UNITS))

  for ln in lines:
    for m in ln["materials"]:
      t = totals.setdefault((m["material"], m["unit"]), {"material": m["material"], "unit": m["unit"], "quantity": 0.0, "with_waste": 0.0, "lines": 0})
      t["quantity"] += m["quantity"]
      t["with_waste"] += m["with_waste"]
      t["lines"] += 1
  order = {CEMENT: 0, SAND: 1, COARSE: 2, BRICK: 3}
  out_totals = [{**t, "quantity": round(t["quantity"], 3), "with_waste": round(t["with_waste"], 3)} for t in sorted(totals.values(), key=lambda t: order.get(t["material"], 9))]
  for t in out_totals:
    if t["material"] == CEMENT:
      t["kg"] = round(t["quantity"] * QP.BAG_KG, 1)

  n, mortar = bricks_per_m3()
  return {"lines": lines, "totals": out_totals, "not_broken": skipped,
    "assumptions": [
      f"Concrete: dry volume is {QP.CONCRETE_DRY_FACTOR:g} times the wet volume; brickwork mortar {QP.MORTAR_DRY_FACTOR:g}; plaster mortar {QP.PLASTER_DRY_FACTOR:g}.",
      f"Cement: a bag is {QP.BAG_KG:g} kg and cement weighs {QP.CEMENT_KG_M3:g} kg per cubic metre.",
      f"Brickwork: a brick of {QP.BRICK_MM[0]:g} x {QP.BRICK_MM[1]:g} x {QP.BRICK_MM[2]:g} mm with a {QP.JOINT_MM:g} mm joint gives {n:.0f} bricks and {mortar:.3f} m3 of mortar in a cubic metre.",
      f"Where the drawing prints no mix: concrete {_label(QP.DEFAULT_RCC_MIX)}, plain concrete {_label(QP.DEFAULT_PCC_MIX)}, brickwork mortar {_label(QP.DEFAULT_BRICK_MORTAR)}, plaster mortar {_label(QP.DEFAULT_PLASTER_MORTAR)} (marked ASSUMED on the line).",
      "Nominal mixes of the grades follow IS 456 (M10 1:3:6, M15 1:2:4, M20 1:1.5:3, M25 1:1:2); 3000 psi is taken as 1:2:4 and 4000 psi as 1:1.5:3, as site practice.",
    ]}
