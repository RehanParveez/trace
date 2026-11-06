from __future__ import annotations
from app.modules.drawings_boq.takeoff.completeness import facts as F

APPLICABLE, NOT_APPLICABLE = "APPLICABLE", "NOT_APPLICABLE"
ROLE_SETS = {
  "COLUMN_LAYOUT": F.STRUCTURE, "FOOTING_LAYOUT": F.STRUCTURE, "EXCAVATION_PLAN": F.STRUCTURE, "BASEMENT_PLAN": F.STRUCTURE, "RAFT_PLAN": F.STRUCTURE, "PILE_LAYOUT": F.STRUCTURE,
  "COLUMN_SCHEDULE": F.STRUCTURE, "BEAM_LAYOUT": F.STRUCTURE, "SLAB_PLAN": F.STRUCTURE, "STRUCTURAL_PLAN": F.STRUCTURE, "REINFORCEMENT_SCHEDULE": F.STRUCTURE,
  "FLOOR_PLAN": F.ARCHITECTURE, "ROOF_PLAN": F.ARCHITECTURE, "ELEVATION": F.ARCHITECTURE, "OPENING_SCHEDULE": F.ARCHITECTURE, "FINISH_SCHEDULE": F.ARCHITECTURE, "CEILING_PLAN": F.ARCHITECTURE,
  "FACADE": F.ARCHITECTURE, "BOUNDARY_DETAIL": F.ARCHITECTURE, "GATE_DETAIL": F.ARCHITECTURE, "SITE_PLAN": F.ARCHITECTURE, "LINTEL_TABLE": F.ARCHITECTURE, "PARKING_PLAN": F.ARCHITECTURE,
  "TOILET_DETAIL": F.ARCHITECTURE, "KITCHEN_DETAIL": F.ARCHITECTURE,
  "FURNITURE_PLAN": F.INTERIOR, "INTERIOR_DRAWINGS": F.INTERIOR,
  "ELECTRICAL_PLAN": F.ELECTRICAL, "SINGLE_LINE_DIAGRAM": F.ELECTRICAL, "LOW_VOLTAGE_PLAN": F.ELECTRICAL,
  "PLUMBING_PLAN": F.PLUMBING, "DRAINAGE_PLAN": F.PLUMBING, "ISOMETRIC": F.PLUMBING, "GAS_PLAN": F.PLUMBING,
  "FIRE_PLAN": F.FIRE, "HVAC_PLAN": F.HVAC,
}
GENERIC_ROLES = ("SECTION", "DETAIL", "SPEC", "SOIL_REPORT", "GENERAL_NOTES", "STAIR_DETAIL", "TANK_DETAIL", "SEPTIC_DETAIL")

def needed_sets(item) -> list:
  named = item.applies_when.get("sets_present")
  if named:
    return list(named)
  out = []
  
  for r in item.page_roles:
    s = ROLE_SETS.get(r)
    if s and s not in out:
      out.append(s)
  return out

def applicability(item, facts: dict) -> tuple:
  v = F.values(facts)
  why = []
  
  kind = v["type"]
  if kind == F.HOUSE and "H" not in item.use:
    why.append("NOT_FOR_HOUSE")
  if kind == F.PLAZA and "P" not in item.use:
    why.append("NOT_FOR_PLAZA")
  aw = item.applies_when
  if "type" in aw:
    want = aw["type"] if isinstance(aw["type"], list) else [aw["type"]]
    if kind not in want:
      why.append(f"TYPE_{'_'.join(want)}_ONLY")
      
  if "structure" in aw and v["structure"] is not None and v["structure"] != aw["structure"]:
    why.append(f"STRUCTURE_IS_{v['structure']}")
  if "basement" in aw and bool(v["basement"]) != bool(aw["basement"]):
    why.append("NO_BASEMENT" if aw["basement"] else "HAS_BASEMENT")
  if "floors_min" in aw and v["floors"] and len(v["floors"]) < aw["floors_min"]:
    why.append(f"FEWER_THAN_{aw['floors_min']}_FLOORS")
  return (NOT_APPLICABLE if why else APPLICABLE), why

def floor_scope(item, facts: dict) -> list:
  floors = list(facts["floors"]["value"] or [])
  by_floor = any("floor" in y.split for y in item.yields)
  return floors if by_floor and floors else ["ALL"]
