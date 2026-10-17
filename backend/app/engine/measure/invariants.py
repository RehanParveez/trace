from __future__ import annotations
from decimal import Decimal
import json

TOLERANCE = Decimal("0.000002")
BODY_MARGIN = Decimal("1.05")     
OVERLAP = "OVERLAP_ALLOCATION"

def _group_key(r) -> tuple:
  inputs = (r.trace or {}).get("inputs") or {}
  return (r.solid_id, r.work_item_code, r.unit, getattr(r, "spec_key", None), r.material_grade, json.dumps(inputs.get("layer_split"), sort_keys=True, default=str))

def stage_split_check(ledger) -> tuple:
  groups: dict = {}
  
  for r in ledger:
    cut = ((r.trace or {}).get("inputs") or {}).get("stage_split")
    if not cut or getattr(r, "work_stage", None) is None:
      continue
    g = groups.setdefault(_group_key(r), {"whole": set(), "sum": Decimal("0"), "stages": []})
    g["whole"].add(str(cut.get("of_m3")))
    g["sum"] += r.quantity
    g["stages"].append(r.work_stage)
  failures: list = []
  
  for key, g in sorted(groups.items(), key=lambda kv: str(kv[0])):
    if len(g["whole"]) != 1:
      failures.append(f"STAGE_SPLIT_PIECES_DISAGREE: the stage pieces of solid {key[0]} ({key[1]}) do not agree on the quantity they were cut from")
      continue
    try:
      whole = Decimal(next(iter(g["whole"])))
    except Exception:
      failures.append(f"STAGE_SPLIT_NO_WHOLE: a stage piece of solid {key[0]} ({key[1]}) does not say what it was cut from")
      continue
  
    if abs(g["sum"] - whole) > TOLERANCE:
      failures.append(f"STAGE_SPLIT_NOT_CONSERVED: solid {key[0]} ({key[1]}) was {whole} and its stage pieces add up to {g['sum']}")
    if len(set(g["stages"])) != len(g["stages"]):
      failures.append(f"STAGE_SPLIT_REPEATED_STAGE: solid {key[0]} ({key[1]}) has two pieces in one stage")
  return len(groups), failures

def allocation_check(solids, deductions) -> tuple:
  gross = {s.id: s.gross_volume_m3 for s in solids}
  pairs: dict = {}
  checked = 0
  failures: list = []
  for d in deductions or ():
    if d.deduction_type != OVERLAP or d.to_solid_id is None:
      continue
  
    checked += 1
    pairs[(d.from_solid_id, d.to_solid_id)] = pairs.get((d.from_solid_id, d.to_solid_id), Decimal("0")) + d.quantity
    for sid in (d.from_solid_id, d.to_solid_id):
      g = gross.get(sid)
      if g is not None and d.quantity > g * BODY_MARGIN + TOLERANCE:
        failures.append(f"ALLOCATION_OVERLAP_TOO_BIG: the overlap {d.quantity} m3 taken from solid {d.from_solid_id} is more than solid {sid} holds ({g} m3)")
        break
  for (a, b) in sorted(pairs, key=str):
    if (b, a) in pairs and str(a) < str(b):
      failures.append(f"ALLOCATION_CYCLE: solids {a} and {b} each lose the overlap to the other")
  return checked, failures
