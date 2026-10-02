from __future__ import annotations
from collections import defaultdict
from app.engine.measure.formulas import check_component_units

def _issue(code: str, severity: str, message: str, ref: str | None = None) -> dict:
  return {"code": code, "severity": severity, "message": message, "ref": ref}

def validate_bundle(
  *,
  rule_set,
  opening_rules,
  wastage_rules,
  reinforcement_rules,
  mappings,
  recipes,
  work_item_units: dict[str, str],
  known_conventions: set[str],
) -> list[dict]:
  issues: list[dict] = []

  if not rule_set.convention_code:
    issues.append(_issue("CONVENTION_REQUIRED", "error", "A convention_code is required before publishing."))
  elif rule_set.convention_code not in known_conventions:
    issues.append(_issue("CONVENTION_UNKNOWN", "error", f"Unknown or inactive convention '{rule_set.convention_code}'."))

  if not opening_rules:
    issues.append(_issue("NO_OPENING_RULES", "warning", "No opening rules; every opening will be fully deducted."))
  by_scope: dict[str, list] = defaultdict(list)
  for rule in opening_rules:
    by_scope[rule.element_scope].append(rule)
  for scope, rules in by_scope.items():
    rules = sorted(rules, key=lambda r: r.lower_area_m2)
    for prev, cur in zip(rules, rules[1:]):
      if prev.upper_area_m2 is None or prev.upper_area_m2 > cur.lower_area_m2:
        issues.append(_issue("OPENING_RANGE_OVERLAP", "error", f"Opening ranges overlap in scope '{scope}'.", scope))
      elif prev.upper_area_m2 < cur.lower_area_m2:
        issues.append(_issue("OPENING_RANGE_GAP", "warning", f"Gap between opening ranges in scope '{scope}'; gap areas are fully deducted.", scope))
    if rules[-1].upper_area_m2 is not None:
      issues.append(_issue("OPENING_RANGE_NOT_OPEN_ENDED", "warning", f"Largest openings in scope '{scope}' fall outside every range.", scope))

  if "DEFAULT" not in {w.material_class for w in wastage_rules}:
    issues.append(_issue("NO_DEFAULT_WASTE", "warning", "No DEFAULT wastage rule; unclassified materials get factor 1.0."))

  if not mappings:
    issues.append(_issue("NO_MAPPINGS", "warning", "No element type mappings; base items get no work-item code."))
  for m in mappings:
    if not m.work_item_code:
      continue
    unit = work_item_units.get(m.work_item_code)
    if unit is None:
      issues.append(_issue("MAPPING_WORK_ITEM_UNKNOWN", "error", f"Mapping {m.ifc_type} uses unknown work item '{m.work_item_code}'.", m.ifc_type))
    elif m.unit_override and m.unit_override != unit:
      issues.append(_issue("MAPPING_UNIT_OVERRIDE", "warning", f"Mapping {m.ifc_type}: unit_override '{m.unit_override}' differs from work item unit '{unit}'.", m.ifc_type))

  for recipe in recipes:
    components = list(recipe.components)
    if not components:
      issues.append(_issue("RECIPE_EMPTY", "error", f"Recipe {recipe.code} has no components.", recipe.code))
    sequences = [c.sequence for c in components]
    if len(sequences) != len(set(sequences)):
      issues.append(_issue("RECIPE_DUPLICATE_SEQUENCE", "error", f"Recipe {recipe.code} has duplicate component sequences.", recipe.code))
    for c in components:
      ref = f"{recipe.code}#{c.sequence}"
      for code, message in check_component_units(c.quantity_formula_code, c.unit, c.output_unit):
        issues.append(_issue(code, "error", f"{ref}: {message}", ref))
      if c.work_item_code:
        unit = work_item_units.get(c.work_item_code)
        if unit is None:
          issues.append(_issue("RECIPE_WORK_ITEM_UNKNOWN", "error", f"{ref}: unknown work item '{c.work_item_code}'.", ref))
        elif unit != c.unit:
          issues.append(_issue("RECIPE_WORK_ITEM_UNIT_MISMATCH", "error", f"{ref}: component unit '{c.unit}' differs from work item unit '{unit}'.", ref))

  if any((r.extra_config or {}).get("status") == "CANDIDATE_UNCONFIRMED" for r in reinforcement_rules):
    issues.append(_issue("UNCONFIRMED_REBAR_VALUES", "warning", "Reinforcement rules contain candidate values not yet confirmed by a structural engineer (Q5)."))

  return issues