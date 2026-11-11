from __future__ import annotations
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.engine.catalogue import loader as CL
from app.engine.measure import line_sources as LS

DRAWN, ASSUMED, NONE = "DRAWN", "ASSUMED", "NONE"

def of_entry(entry: dict, evidence: dict) -> str:
  if entry["quantity"] is None or entry["state"] in (LG.NOT_READ, LG.NOT_APPLICABLE):
    return NONE
  if entry["state"] != LG.MEASURED or entry["assumptions"] or LG.METHOD_DEFAULT in entry["reasons"]:
    return ASSUMED
  item = CL.get(entry["element"])
  lines = LG._lines_for(item, entry["floor"], evidence) if item is not None else []
  return ASSUMED if any(LS.assumed(ln.get("inputs")) for ln in lines) else DRAWN
