from __future__ import annotations
from app.engine.measure import readings as QS

LENGTH_TOL = 0.015
CHAJJA_MAX_MM = 457.2
SIDES = ("TOP", "BOTTOM", "LEFT", "RIGHT")
ACROSS = {"TOP": ("LEFT", "RIGHT"), "BOTTOM": ("LEFT", "RIGHT"), "LEFT": ("TOP", "BOTTOM"), "RIGHT": ("TOP", "BOTTOM")}

def chajja_max_mm() -> float:
  v = QS.param("slab_projection_chajja_max_mm")
  return float(v) if v else CHAJJA_MAX_MM

def feet_text(mm: float) -> str:
  inches = round(float(mm) / 25.4)
  ft, inch = divmod(int(inches), 12)
  return f"{ft}'-{inch}\"" if inch else f"{ft}'-0\""

def _near(a: float, b: float) -> bool:
  return b > 0 and abs(a - b) <= LENGTH_TOL * b

def classify(sides: dict, axes: tuple) -> list:
  h, v = float(axes[0]), float(axes[1])
  chajja = chajja_max_mm()
  out = []
  
  for side in SIDES:
    rec = sides.get(side)
    if not rec:
      continue
    lengths = [float(x) for x in (rec.get("lengths_mm") or ([rec["length_mm"]] if rec.get("length_mm") else []))]
    base = h if side in ("TOP", "BOTTOM") else v
    wide = base + sum(float(sides[o]["width_mm"]) for o in ACROSS[side] if o in sides)
    width = float(rec["width_mm"])
    row = {"side": side, "width_mm": width, "text": rec.get("text"), "lengths_mm": sorted(lengths), "length_mm": rec.get("length_mm"), "outline_mm": round(base, 1),
      "outline_widened_mm": round(wide, 1), "length_via": rec.get("length_via"), "status": None, "reason": None}
    
    if not lengths:
      row["status"], row["reason"] = "NOT_BOUND", "no overall length printed beside the label"
    elif not any(_near(x, base) or _near(x, wide) for x in lengths):
      row["status"], row["reason"] = "NOT_VERIFIED", "the length it is bound to is not the length of this side of the plan outline"
    elif width <= chajja:
      row["status"], row["reason"] = "CHAJJA", f"{feet_text(width)} wide, not more than the chajja limit {feet_text(chajja)}"
    else:
      row["status"] = "ADDED"
      match = next(x for x in lengths if _near(x, base) or _near(x, wide))
      row["length_mm"] = round(match, 1)
    out.append(row)
  return out

def strip_m2(row: dict) -> float:
  return float(row["width_mm"]) * float(row["outline_mm"]) / 1e6
