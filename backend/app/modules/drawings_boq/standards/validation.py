from __future__ import annotations
from collections import defaultdict
from app.engine.measure.formulas import check_component_units

SURFACE_UNIT = {"FLOOR": "m2", "WALL": "m2", "CEILING": "m2", "DADO": "m2", "SKIRTING": "m"}
SURFACE_NEEDS_HEIGHT = {"DADO": True}

KNOWN_CATEGORIES = (
  "ALL", "UNKNOWN", "TOILET", "BATHROOM", "KITCHEN", "BEDROOM", "LIVING", "DINING", "CORRIDOR", "STAIR", "STORE",
  "GARAGE", "BALCONY", "TERRACE", "PORCH", "LAUNDRY", "OFFICE",
)

def _issue(code: str, severity: str, message: str, ref: str | None = None) -> dict:
  return {"code": code, "severity": severity, "message": message, "ref": ref}

def _is_excluded(rule) -> bool:
  return bool((getattr(rule, "extra_config", None) or {}).get("exclude"))

def validate_finish_rules(rules, work_item_units: dict[str, str]) -> list[dict]:
  issues: list[dict] = []
  
  if not rules:
    return [_issue("FINISH_RULES_EMPTY", "info",
      "No default finish rules. Rooms get finishes only from explicit entries or schedules.")]
    
  active = [r for r in rules if not _is_excluded(r)]
  all_keys = {(r.surface, r.work_item_code) for r in rules if r.space_category == "ALL" and not _is_excluded(r)}
  
  for r in rules:
    ref = f"{r.space_category}/{r.surface}/{r.work_item_code}"
    excluded = _is_excluded(r)
    if r.space_category not in KNOWN_CATEGORIES:
      issues.append(_issue("FINISH_CATEGORY_UNKNOWN", "warning",
        f"Space category '{r.space_category}' is not one the reader assigns, so this rule may never apply.", ref))
      
    if excluded:
      if r.space_category == "ALL":
        issues.append(_issue("FINISH_EXCLUDE_EVERYWHERE", "warning",
          "An exclusion on category ALL removes this finish from every room.", ref))
      elif (r.surface, r.work_item_code) not in all_keys:
        issues.append(_issue("FINISH_EXCLUDE_NO_TARGET", "warning",
          "This exclusion has no matching rule on category ALL, so it has no effect.", ref))
      unit = work_item_units.get(r.work_item_code)
      
      if unit is None:
        issues.append(_issue("FINISH_WORK_ITEM_UNKNOWN", "error",
          f"Work item '{r.work_item_code}' is not in the catalog.", ref))
      continue
    unit = work_item_units.get(r.work_item_code)
    
    if unit is None:
      issues.append(_issue("FINISH_WORK_ITEM_UNKNOWN", "error",
        f"Work item '{r.work_item_code}' is not in the catalog.", ref))
    elif unit != SURFACE_UNIT.get(r.surface):
      issues.append(_issue("FINISH_UNIT_MISMATCH", "error",
        f"{r.surface.title()} finishes are measured in {SURFACE_UNIT.get(r.surface)}, but {r.work_item_code} is in {unit}.", ref))
    if SURFACE_NEEDS_HEIGHT.get(r.surface) and r.height_mm is None:
      issues.append(_issue("FINISH_DADO_NEEDS_HEIGHT", "error", "A dado rule needs a height.", ref))
    if r.height_mm is not None and r.surface in ("FLOOR", "CEILING", "SKIRTING"):
      issues.append(_issue("FINISH_HEIGHT_NOT_USED", "info", f"Height has no effect on {r.surface.title()} rules.", ref))
      
  for cat in sorted({r.space_category for r in active if r.surface == "DADO"}):
    if any(r.surface == "WALL" and r.space_category in (cat, "ALL") for r in active):
      issues.append(_issue("FINISH_DADO_OVERLAPS_WALL", "warning",
        f"Category {cat}: wall finishes are measured at full height and the dado is measured on top. "
        "The dado height is not deducted from the wall finish.", cat))
  return issues

def finish_options() -> dict:
  return {
    "surfaces": [{"surface": s, "unit": u, "needs_height": SURFACE_NEEDS_HEIGHT.get(s, False)} for s, u in SURFACE_UNIT.items()],
    "categories": list(KNOWN_CATEGORIES),
  }

def validate_bundle(
  *,
  rule_set,
  opening_rules,
  wastage_rules,
  reinforcement_rules,
  mappings,
  recipes,
  finish_rules,
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
          
  issues.extend(validate_finish_rules(finish_rules, work_item_units))
  if any((r.extra_config or {}).get("status") == "CANDIDATE_UNCONFIRMED" for r in reinforcement_rules):
    issues.append(_issue("UNCONFIRMED_REBAR_VALUES", "warning", "Reinforcement rules contain candidate values not yet confirmed by a structural engineer (Q5)."))

  return issues