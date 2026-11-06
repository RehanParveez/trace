from __future__ import annotations
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS

META_KEY = "structure_inputs"
GENERATED_FROM = ("FOOTING_SECTION", "BEAM_RUNS")
REMADE_BY = (FS.STACK_BY, FS.FAMILY_BY)

def inputs_of(meta: dict | None) -> dict:
  raw = (meta or {}).get(META_KEY) or {}
  return {"sections": list(raw["sections"]) if raw.get("sections") else None, "storeys": list(raw["storeys"]) if raw.get("storeys") else None, "runs": RR.on("BEAM_RUNS") if raw.get("runs") is None else bool(raw["runs"])}

def generated(c) -> bool:
  f = c.facts or {}
  return f.get("derived_from") in GENERATED_FROM or "stack" in f or "member_of" in f

def reset(rows: list) -> list:
  removed: list = []
  for row in rows:
    kept: list = []
    for c in row.get("candidates") or []:
      if generated(c):
        removed.append((row, c))
        continue
      f = c.facts or {}

      if (f.get(FS.SET_ASIDE) or {}).get("by") in REMADE_BY:
        c.facts = {k: v for k, v in f.items() if k != FS.SET_ASIDE}
        if c.decision == "REJECTED":
          c.decision = "NEW"
      kept.append(c)
    row["candidates"] = kept
  return removed

def run(read: list, floor_keys: list, floor_heights: dict | None, *, storeys: list | None = None, sections: list | None = None, runs: bool | None = None) -> list:
  problems: list = []
  try:
    from app.modules.drawings_boq.takeoff.extract import footing_members as FM
    from app.modules.drawings_boq.takeoff.extract import structure_joins as SJ
    FM.inject(read, sections)
    SJ.join_rows(read)
  except Exception as exc:
    problems.append((0, f"structure joins: {type(exc).__name__}: {str(exc)[:80]}"))
  try:
    from app.modules.drawings_boq.takeoff.extract import storey_apply as SA
    from app.modules.drawings_boq.takeoff.model import storeys as STO
    from app.modules.drawings_boq.takeoff.extract import column_stacks as CST
    resolved = STO.resolve(floor_keys, STO.printed_records(floor_heights), None, STO.decision_records(storeys))
    if RR.on("FLOOR_FROM_SCHEDULE"):
      SA.apply(read, resolved)
    if RR.on("COLUMN_STACKS"):
      CST.apply(read, resolved)
    
  except Exception as exc:
    problems.append((0, f"storeys: {type(exc).__name__}: {str(exc)[:80]}"))
  try:
    from app.modules.drawings_boq.takeoff.extract import footing_members as FM
    if RR.on("FOOTING_FAMILIES"):
      FM.apply(read)
  except Exception as exc:
    problems.append((0, f"footing members: {type(exc).__name__}: {str(exc)[:80]}"))
  if RR.on("BEAM_RUNS") if runs is None else runs:
    try:
      from app.modules.drawings_boq.takeoff.extract import beam_members as BMEM
      BMEM.apply(read)
    except Exception as exc:
      problems.append((0, f"beam members: {type(exc).__name__}: {str(exc)[:80]}"))
  return problems
