from __future__ import annotations
import math
from app.modules.drawings_boq.takeoff.extract import config as C
import statistics

ROOM_AREAS = (
  (("BEDROOM", "MASTER BEDROOM", "BED ROOM", "BED"), 15.0),
  (("LOUNGE", "LIVING", "DRAWING ROOM", "DRAWING", "DINING", "DWG"), 18.0),
  (("KITCHEN",), 10.0),
  (("BATH", "BATHROOM", "TOILET", "WC", "W.C", "LAVATORY"), 4.0),
)

STANDARD = (
  (25.4 / 72.0 * 48.0, "1/4\" = 1'-0\""), (25.4 / 72.0 * 64.0, "3/16\" = 1'-0\" (1:64)"), (25.4 / 72.0 * 96.0, "1/8\" = 1'-0\""),
  (25.4 / 72.0 * 32.0, "3/8\" = 1'-0\""), (25.4 / 72.0 * 24.0, "1/2\" = 1'-0\""),
  (25.4 / 72.0 * 50.0, "1:50"), (25.4 / 72.0 * 100.0, "1:100"), (25.4 / 72.0 * 200.0, "1:200"),
)

def _family(name: str):
  up = (name or "").upper().split("/")[0].strip()
  for words, typical in ROOM_AREAS:
    if any(up == w or up.startswith(w + " ") or up.endswith(" " + w) for w in words):
      return typical
  return None

def _snap(f: float):
  best = min(STANDARD, key=lambda s: abs(math.log(s[0] / f)))
  if abs(best[0] / f - 1.0) <= C.PLAUS_SNAP_TOL:
    return best
  return f, None

def _off(factor: float, limit: float) -> bool:
  return factor > limit or factor < 1.0 / limit

def check(mm_per_pt: float, door_widths_mm: list, rooms: list) -> dict | None:
  factors, evidence = [], []
  
  doors = [w for w in door_widths_mm if w and w > 0]
  if len(doors) >= C.PLAUS_MIN_DOORS:
    med = statistics.median(doors)
    f = C.PLAUS_DOOR_TYPICAL_MM / med
    evidence.append({"kind": "DOORS", "count": len(doors), "median_width_mm": round(med), "outside": _off(f, C.PLAUS_DOOR_OFF_BY)})
    if _off(f, C.PLAUS_DOOR_OFF_BY):
      factors.append(f)
      
  judged = [(typ, a) for typ, a in ((_family(n), a) for n, a in rooms) if typ and a and a > 0]
  if len(judged) >= C.PLAUS_MIN_ROOMS:
    f = math.sqrt(statistics.median([typ / a for typ, a in judged]))
    evidence.append({"kind": "ROOMS", "count": len(judged), "median_factor": round(f, 3), "outside": _off(f, C.PLAUS_ROOM_OFF_BY)})
    
    if _off(f, C.PLAUS_ROOM_OFF_BY):
      factors.append(f)
  if not evidence:
    return None
  if not factors:
    return {"status": "PLAUSIBLE", "evidence": evidence}
  factor = statistics.median(factors) if len(factors) > 1 else factors[0]
  value, label = _snap(mm_per_pt * factor)
  return {"status": "IMPLAUSIBLE", "evidence": evidence, "used_mm_per_pt": round(mm_per_pt, 4), "suggested_mm_per_pt": round(value, 4),
    "suggested_scale": label, "factor": round(factor, 3), "agree": len(factors) > 1}
