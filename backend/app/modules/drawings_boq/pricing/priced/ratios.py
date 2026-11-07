from __future__ import annotations
from decimal import Decimal

def ratios(covered_sft: Decimal | None, cost: Decimal | None, steel_kg: Decimal | None, concrete_cft: Decimal | None, bricks: Decimal | None, cement_bags: Decimal | None) -> list:
  out = []
  for name, value, unit in (("cost", cost, "Rs per sft"), ("steel", steel_kg, "kg per sft"), ("concrete", concrete_cft, "cft per sft"), ("bricks", bricks, "bricks per sft"), ("cement", cement_bags, "bags per sft")):
    if not covered_sft or covered_sft <= 0:
      out.append({"ratio": name, "value": None, "unit": unit, "why": "the covered area is not known", "inputs": {"covered_sft": covered_sft, name: value}})
    elif value is None:
      out.append({"ratio": name, "value": None, "unit": unit, "why": f"the {name} total is not known", "inputs": {"covered_sft": covered_sft, name: None}})
    else:
      out.append({"ratio": name, "value": value / covered_sft, "unit": unit, "why": None, "inputs": {"covered_sft": covered_sft, name: value}})
  return out
