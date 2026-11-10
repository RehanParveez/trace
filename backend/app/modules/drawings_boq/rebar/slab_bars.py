from __future__ import annotations
from collections import Counter

HELD_SPANS = "SPANS_NOT_SURE"
HELD_ROLE = "ROLE_NOT_SURE"
HELD_NO_CALLOUT = "NO_CALLOUT"

def _once(group: Counter, axis: str) -> list:
  return [(bar, s) for (ax, bar, s), n in group.items() if ax == axis and n == 1]

def _repeated(group: Counter) -> list:
  return [(ax, bar, s, n) for (ax, bar, s), n in sorted(group.items()) if n > 1]

def mesh_of(panel: dict) -> dict:
  calls = panel.get("callouts") or []
  
  if not calls:
    return {"held": [HELD_NO_CALLOUT], "main": None, "dist": None, "top": []}
  x, y = panel.get("x_ft"), panel.get("y_ft")
  if panel.get("spans") != "SURE" or not x or not y:
    return {"held": [HELD_SPANS], "main": None, "dist": None, "top": []}
  if any(c.get("role") not in ("MAIN", "DISTRIBUTION") for c in calls):
    return {"held": [HELD_ROLE], "main": None, "dist": None, "top": []}

  short = "X" if x < y else "Y"
  other = "Y" if short == "X" else "X"
  group = Counter((c["axis"], int(c["bar"]), float(c["spacing_in"])) for c in calls)
  held, picked = [], {}
  for role, axis in (("main", short), ("dist", other)):
    one = _once(group, axis)
    if len(one) == 1:
      picked[role] = one[0]
    else:
      held.append(f"{role.upper()}_{'NONE' if not one else 'SEVERAL'}_ONCE")
      picked[role] = None
  return {"held": held, "main": picked["main"], "dist": picked["dist"], "top": _repeated(group), "short_ft": min(x, y), "long_ft": max(x, y)}
