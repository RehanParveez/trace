from __future__ import annotations
import re

M3_TO_CFT = 35.3146667
M2_TO_SFT = 10.7639104

BILL_ALIASES = (
  (r"\bexcavation\b", "EXCAVATION"),
  (r"\btermite\b", "TERMITE"),
  (r"\bmembrane\b", "MEMBRANE"),
  (r"brick\s*work\s*foundation", "BRICK_FOUNDATION"),
  (r"brick\s*work", "BRICK_WALLS"),
  (r"\blean\b|\bpcc\s*1\s*[:;]\s*4\s*[:;]\s*8", "PCC"),
  (r"rcc\s*foundation|rcc\s*footing", "RCC_FOOTINGS"),
  (r"plinth\s*beam", "RCC_PLINTH_BEAM"),
  (r"rcc\s*columns?", "RCC_COLUMNS"),
  (r"rcc\s*walls?", "RCC_WALLS"),
  (r"lintel", "RCC_LINTELS"),
  (r"roof\s*beams?", "RCC_ROOF_BEAMS"),
  (r"stair", "RCC_STAIR"),
  (r"slab", "RCC_SLABS"),
  (r"ceiling|roof\s*plaster", "CEILING_PLASTER"),
  (r"plaster", "WALL_PLASTER"),
  (r"\bsteel\b", "STEEL"),
  (r"door\s*frames?", "DOOR_FRAMES"),
  (r"\bdoors?\b", "DOORS"),
  (r"window|ventilator", "WINDOWS"),
  (r"kacha|pcc\s*/\s*kacha", "KACHA"),
  (r"roof\s*treatment", "ROOF_TREATMENT"),
  (r"form\s*work|shuttering", "FORMWORK"),
  (r"ugwt|ohwt|septic|tank", "TANKS"),
  (r"gate|electrical|plumbing|conduit|piping", "LUMP_SUM"),
)

KEY_LABEL = {
  "EXCAVATION": "Excavation", "TERMITE": "Termite treatment", "MEMBRANE": "Membrane", "BRICK_FOUNDATION": "Brick work in foundation",
  "PCC": "Lean concrete", "RCC_FOOTINGS": "RCC footings", "RCC_PLINTH_BEAM": "RCC plinth beam", "RCC_COLUMNS": "RCC columns",
  "RCC_WALLS": "RCC walls", "RCC_LINTELS": "RCC lintels", "RCC_ROOF_BEAMS": "RCC roof beams", "RCC_STAIR": "RCC staircase",
  "RCC_SLABS": "RCC slabs", "CEILING_PLASTER": "Ceiling plaster", "WALL_PLASTER": "Wall plaster", "BRICK_WALLS": "Brick work above plinth",
  "STEEL": "Reinforcement steel", "DOOR_FRAMES": "Door frames", "DOORS": "Doors", "WINDOWS": "Windows and ventilators",
  "KACHA": "Kacha or PCC on floor", "ROOF_TREATMENT": "Roof treatment", "FORMWORK": "Form work", "TANKS": "Tanks", "LUMP_SUM": "Lump-sum items",
}

SOFTWARE_UNIT = {
  "EXCAVATION": "m3", "TERMITE": "m2", "MEMBRANE": "m2", "BRICK_FOUNDATION": "m3", "PCC": "m3", "RCC_FOOTINGS": "m3",
  "RCC_PLINTH_BEAM": "m3", "RCC_COLUMNS": "m3", "RCC_WALLS": "m3", "RCC_LINTELS": "m3", "RCC_ROOF_BEAMS": "m3", "RCC_STAIR": "m3",
  "RCC_SLABS": "m3", "CEILING_PLASTER": "m2", "WALL_PLASTER": "m2", "BRICK_WALLS": "m3", "STEEL": "kg", "DOOR_FRAMES": "m2",
  "DOORS": "m2", "WINDOWS": "m2", "KACHA": "m2", "ROOF_TREATMENT": "m2", "FORMWORK": "m2", "TANKS": "m3",
}

NOT_MEASURED = ("DOORS", "WINDOWS", "ROOF_TREATMENT", "TANKS", "LUMP_SUM")

_COMPILED = tuple((re.compile(p, re.I), k) for p, k in BILL_ALIASES)

def bill_key(item: str, overrides: dict | None = None) -> str | None:
  if overrides and item in overrides:
    return overrides[item]
  for rx, key in _COMPILED:
    if rx.search(item):
      return key
  return None

def bill_quantity(key: str, unit: str, quantity: float) -> tuple:
  u = unit.strip().lower()
  if u in ("sft", "sqft", "sq ft", "sq.ft", "sq.ft."):
    return quantity, "m2", quantity / M2_TO_SFT
  if u in ("cft", "cuft", "cu ft", "cu.ft", "cu.ft."):
    return quantity, "m3", quantity / M3_TO_CFT
  if u in ("sqm", "m2", "sq m", "m²"):
    return quantity, "m2", quantity
  if u in ("cum", "m3", "cu m", "m³"):
    return quantity, "m3", quantity
  if u in ("kg", "kgs"):
    return quantity, "kg", quantity
  if u in ("rft", "rft."):
    return quantity, "m", quantity * 0.3048
  if u in ("nos", "no", "no.", "each"):
    return quantity, "nos", quantity
  return quantity, u or "?", quantity

def software_key(formula: str, tag: str | None, label: str | None) -> str | None:
  t = (tag or "").upper()
  lab = (label or "").lower()
  if formula == "SOLID_FORMWORK_AREA":
    return "FORMWORK"
  if formula == "PDF_MEMBER_STEEL_WEIGHT":
    return "STEEL"
  if formula == "PDF_TAKEOFF_LENGTH_X_HEIGHT_X_THICKNESS":
    if "rcc" in lab or "concrete" in lab:
      return "RCC_WALLS"
    if "brick" in lab:
      return "BRICK_WALLS"
    return None

  if re.match(r"EXCAVATION|TRENCH", t):
    return "EXCAVATION"
  if t.startswith("TERMITE"):
    return "TERMITE"
  if t.startswith("MEMBRANE"):
    return "MEMBRANE"
  if t.startswith("BRICK-STEP"):
    return "BRICK_FOUNDATION"
  if t.startswith("PCC"):
    return "PCC"
  if t.startswith("PLINTH-BEAM"):
    return "RCC_PLINTH_BEAM"
  if t.startswith("ROOF-BEAM"):
    return "RCC_ROOF_BEAMS"
  if t.startswith("CEILING-PLASTER"):
    return "CEILING_PLASTER"
  if t.startswith("PLASTER"):
    return "WALL_PLASTER"
  if t.startswith("FRAME-"):
    return "DOOR_FRAMES"
  if t.startswith("KACHA"):
    return "KACHA"
  if t.startswith("L-"):
    return "RCC_LINTELS"
  if t == "STAIR":
    return "RCC_STAIR"
  if t == "SLAB":
    return "RCC_SLABS"
  if re.match(r"F\d+$", t):
    return "RCC_FOOTINGS"
  if re.match(r"C\d+$", t) or "columns" in lab:
    return "RCC_COLUMNS"
  if "brick" in lab:
    return "BRICK_WALLS"
  return None

def software_to_bill_unit(unit: str, quantity: float) -> float:
  if unit == "m3":
    return quantity * M3_TO_CFT
  if unit == "m2":
    return quantity * M2_TO_SFT
  return quantity
