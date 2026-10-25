from __future__ import annotations

STEPS = (
  ("main", "Excavation, PCC and backfill of the footings", "EARTHWORK"),
  ("dpc", "Damp-proof course", None),
  ("wall_foundation", "Wall foundations", None),
  ("wall_finishes", "Plaster and paint worked out from the walls", "FINISHES"),
  ("opening_area", "Door and window area from the model", None),
  ("roof_treatment", "Roof treatment", "ROOF"),
  ("roof_deck", "Roof deck layers", None),
  ("plaster_mortar", "Plaster mortar", None),
  ("soil_stabilisation", "Soil stabilisation", None),
  ("floor_works", "Floor works", "FINISHES"),
  ("formwork", "Formwork", "FORMWORK"),
  ("steel", "Reinforcement steel", "STEEL"),
  ("steel_allowances", "Binding wire and bar chairs", None),
)

EXPECTED = frozenset({
  "ALL_ITEMS_IN_MODEL", "ALL_ITEMS_ALREADY_MEASURED", "ALREADY_MEASURED", "ALL_LAYERS_ALREADY_MEASURED", "HAS_ROOMS",
  "NOTHING_TO_MEASURE", "NOTHING_TO_ADD", "NOTHING_TO_REINFORCE", "NOTHING_TO_SHUTTER", "NO_LAYER_WANTED",
})

SWITCH = {
  "wall_foundation": "wall_foundation_works", "wall_finishes": "wall_finishes_from_walls", "opening_area": "opening_area_from_model", "roof_treatment": "roof_treatment_from_slabs",
  "roof_deck": "roof_deck_assembly", "soil_stabilisation": "soil_stabilisation", "floor_works": "floor_works_from_spaces",
  "steel_allowances": "steel_binding_wire or steel_chairs",
}

TEXT = {
  "SWITCHED_OFF": "The switch for this step is off.",
  "ALL_ITEMS_IN_MODEL": "The model already has these items, so the step added none.",
  "ALL_ITEMS_ALREADY_MEASURED": "These items were already measured, so the step added none.",
  "ALREADY_MEASURED": "These items were already measured, so the step added none.",
  "ALL_LAYERS_ALREADY_MEASURED": "These layers were already measured, so the step added none.",
  "HAS_ROOMS": "Rooms are in the run, so the finishes come from the rooms.",
  "NOTHING_TO_MEASURE": "The step found nothing to measure.",
  "NOTHING_TO_ADD": "The step found nothing to add.",
  "NOTHING_TO_REINFORCE": "The step found no member to reinforce.",
  "NOTHING_TO_SHUTTER": "The step found no member to shutter.",
  "NO_LAYER_WANTED": "No deck layer is switched on.",
  "NO_PROFILE": "The rule set of this run has no derived-works profile.",
  "NO_RECIPE": "The rule set of this run has no recipe for this step.",
  "NEEDS_FOOTING_LEVEL": "The footing level is not given, so the excavation, PCC and backfill of the footings can not be worked out.",
  "NO_FOUNDATIONS": "No footing was found among the accepted items.",
  "TOO_MANY_FOUNDATIONS": "There are more footings than the step takes in one run.",
  "TOO_MANY_MARKS": "There are more marks than the step takes in one run.",
  "NO_MEMBERS": "No accepted concrete member with a size is in the run.",
  "NO_DPC_LEVEL": "The damp-proof course level is not known.",
  "NO_WALL_ON_DPC": "No wall stands on the damp-proof course level.",
  "NO_WALLS": "No wall with a height is in the run.",
  "NO_OPENINGS": "No door or window with a size is in the model.",
  "NO_ROOMS": "No room is in the run.",
  "LOWEST_LEVEL_UNKNOWN": "The lowest floor level is not known.",
  "NO_THICKNESS": "The plaster thickness is 0, so no mortar is taken.",
  "NO_PLASTER": "No plaster rows exist to take mortar from.",
  "NO_FILLING": "No filling rows exist to stabilise.",
  "DEPTH_NOT_GIVEN": "The stabilisation depth is 0.",
  "NO_REINFORCEMENT": "No reinforcement steel rows exist to add wire or chairs to.",
  "NO_ROOF_SLAB": "This step reads roof slabs of the model only, and none is in the run (a PDF drawing has no model slab).",
  "NO_ROOF_TREATMENT": "No roof treatment rows exist to build the deck layers on.",
}

FIX = {
  "NEEDS_FOOTING_LEVEL": "Type the footing level once for the project (parameter footing_bottom_below_ngl_mm, in mm below natural ground level), then run again.",
  "NO_RECIPE": "Use a rule set that carries the recipe for this step, then run again.",
  "NO_PROFILE": "Use a rule set that carries the derived-works profile, then run again.",
  "NO_FOUNDATIONS": "Accept and confirm the footings of the foundation plan, then run again.",
  "TOO_MANY_FOUNDATIONS": "Run fewer drawings together (one floor or one drawing at a time).",
  "TOO_MANY_MARKS": "Run fewer drawings together (one floor or one drawing at a time).",
  "NO_MEMBERS": "Accept and confirm the members (with their sizes) on the approve screen, then run again.",
  "NO_DPC_LEVEL": "Give the floor levels of the project (datums), then run again.",
  "NO_WALLS": "Accept and confirm the walls with their height, then run again.",
  "NO_OPENINGS": "Accept the doors and windows with their sizes, or read them from the schedule.",
  "NO_ROOMS": "Accept the rooms of the plan or the room schedule, then run again.",
  "LOWEST_LEVEL_UNKNOWN": "Give the floor levels of the project (datums), then run again.",
  "NO_THICKNESS": "Set plaster_thickness_mm for the project (for example 15) if mortar is wanted, then run again.",
  "DEPTH_NOT_GIVEN": "Set soil_stab_depth_mm for the project if soil stabilisation is wanted, then run again.",
  "NO_ROOF_TREATMENT": "Switch roof_treatment_from_slabs on first, then run again.",
}

def _fix(key: str, reason: str) -> str | None:
  if reason == "SWITCHED_OFF":
    p = SWITCH.get(key)
    return f"If you want this measured, set {p} to 1 in the project parameters of the derived works, then run again." if p else None
  return FIX.get(reason)

def steps(derived: dict | None) -> list:
  """One row per derived step: did it run, what did it add, and if not, why."""
  derived = derived or {}
  if derived.get("enabled") is False:
    return []
  out: list = []

  for key, label, family in STEPS:
    s = derived if key == "main" else derived.get(key)
    if not isinstance(s, dict) or ("ran" not in s and "enabled" not in s):
      continue

    ran = bool(s.get("ran"))
    reason = None if ran else (str(s["reason"]) if s.get("reason") else None)
    out.append({
      "step": key, "label": label, "family": family, "enabled": bool(s.get("enabled", True)), "ran": ran,
      "rows": int(s.get("rows") or 0), "reason": reason,
      "reason_text": None if ran or reason is None else TEXT.get(reason, reason.replace("_", " ").lower().capitalize() + "."),
      "gap": (not ran) and reason is not None and reason not in EXPECTED,
      "fix": None if ran or reason is None else _fix(key, reason),
    })
  return out

def why_missing(rows: list, family: str) -> tuple[str, str | None] | None:
  hit = [r for r in rows if r["family"] == family and not r["ran"] and r["reason"]]
  if not hit:
    return None
  detail = " ".join(f"{r['label']}: {r['reason_text']}" for r in hit)
  fix = next((r["fix"] for r in hit if r["fix"]), None)
  return detail, fix

def findings(rows: list, present: set, covered: set) -> list:
  out: list = []
  for r in rows:
    if not r["gap"] or r["family"] in covered:
      continue
    needed = r["family"] is not None and r["family"] not in present
    out.append((f"STEP_{r['step'].upper()}_DID_NOT_RUN", "WARNING" if needed else "INFO", f"{r['label']} did not run",
      r["reason_text"] or "", r["fix"]))
  return out
