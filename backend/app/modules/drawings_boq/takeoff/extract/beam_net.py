from __future__ import annotations
import math

def net_legs(legs: list, squares: list, mm_per_pt: float) -> dict:
  nets: list = []
  hit: set = set()
  
  for leg in legs:
    (x0, y0), (x1, y1) = leg["p0"], leg["p1"]
    length = float(leg["length_mm"])
    dx, dy = (x1 - x0) * mm_per_pt, (y1 - y0) * mm_per_pt
    norm = math.hypot(dx, dy)
    cuts: list = []
    
    if norm > 0.0:
      ux, uy = dx / norm, dy / norm
      for i, s in enumerate(squares):
        half = (s["a"] + s["b"]) / 4.0
        px, py = (s["cx"] - x0) * mm_per_pt, (s["cy"] - y0) * mm_per_pt
        t = px * ux + py * uy
        if abs(-px * uy + py * ux) > half:
          continue
        lo, hi = max(t - half, 0.0), min(t + half, length)
        if hi > lo:
          cuts.append((lo, hi))
          hit.add(i)
    taken, end = 0.0, 0.0
    
    for lo, hi in sorted(cuts):
      lo = max(lo, end)
      if hi > lo:
        taken += hi - lo
        end = hi
    nets.append(round(length - taken, 1))
  gross = sum(float(l["length_mm"]) for l in legs)
  net = sum(nets)
  return {"gross_mm": gross, "net_mm": net, "taken_mm": gross - net, "columns": len(hit), "legs": nets}
