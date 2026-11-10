from __future__ import annotations
from collections import Counter
from app.modules.drawings_boq.rebar import slab_bars as SB
from decimal import Decimal as D

def summary(sheets: list, results: list) -> dict:
  panels, held, with_tops = 0, Counter(), 0
  for sh in sheets:
    for p in ((sh.get("meta") or {}).get("slab_callout_items") or {}).get("panels") or []:
      panels += 1
      m = SB.mesh_of(p)
      if m["main"] is not None and m["dist"] is not None:
        with_tops += 1 if m["top"] else 0
      else:
        held.update(m["held"])
        
  jobs = [(j, e) for j, e in results if j["cls"] == "SLAB" and not j.get("decision_only")]
  kg, needs, done = {}, Counter(), 0
  
  for _j, e in jobs:
    needs.update(e.blocked)
    if e.complete:
      done += 1
    for line in e.lines:
      if line.kg is not None:
        kg[line.dia] = kg.get(line.dia, D(0)) + line.kg
  return {"panels_with_callouts": panels, "meshes_read": len(jobs), "meshes_with_kg": done, "held": dict(sorted(held.items())), "meshes_with_top_bars_unread": with_tops,
    "inputs_missing": dict(sorted(needs.items())), "kg_by_bar": {str(k): str(v) for k, v in sorted(kg.items())}, "kg": str(sum(kg.values(), D(0)))}
