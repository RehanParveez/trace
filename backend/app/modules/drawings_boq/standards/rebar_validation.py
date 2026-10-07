from __future__ import annotations

BAR_ROLES = ("MAIN", "STIRRUP", "ESTIMATE")
LAP_BASES = (None, "diameter_multiple", "fixed_mm")

def _issue(code: str, severity: str, message: str, ref: str | None = None) -> dict:
  return {"code": code, "severity": severity, "message": message, "ref": ref}

def _num(value):
  try:
    return float(value)
  except (TypeError, ValueError):
    return None

def validate_reinforcement_rules(rules) -> list[dict]:
  issues: list[dict] = []
  
  for r in rules:
    ref = f"{r.element_scope}/{r.bar_role}"
    role = (r.bar_role or "").upper()
    extra = r.extra_config or {}
    if role not in BAR_ROLES:
      issues.append(_issue("REBAR_ROLE_UNKNOWN", "warning", f"Bar role '{r.bar_role}' is not used by the engine (MAIN, STIRRUP, ESTIMATE).", ref))
    if "CANDIDATE" in str(extra.get("status", "")).upper() or "PLACEHOLDER" in str(extra.get("status", "")).upper():
      issues.append(_issue("REBAR_RULE_UNCONFIRMED", "info", "This rule is still a placeholder; confirm it with the QS.", ref))
      
    if role == "ESTIMATE":
      if (r.element_scope or "").upper() == "ALL":
        issues.append(_issue("REBAR_ESTIMATE_SCOPE_ALL", "error",
          "Estimate rules must name a member family (COLUMN, BEAM, SLAB, FOOTING ...); ALL is ignored by the engine.", ref))
      if not (_num(extra.get("kg_per_m3")) and _num(extra.get("kg_per_m3")) > 0):
        issues.append(_issue("REBAR_ESTIMATE_NEEDS_INTENSITY", "error", "An estimate rule needs extra_config.kg_per_m3 greater than zero.", ref))
      if "assumed_dia_mm" in extra and not (_num(extra["assumed_dia_mm"]) and _num(extra["assumed_dia_mm"]) > 0):
        issues.append(_issue("REBAR_ESTIMATE_BAD_DIAMETER", "error", "extra_config.assumed_dia_mm must be greater than zero.", ref))
      continue
  
    if r.lap_basis not in LAP_BASES:
      issues.append(_issue("REBAR_LAP_BASIS_UNKNOWN", "error", f"Lap basis '{r.lap_basis}' is not supported (diameter_multiple, fixed_mm).", ref))
    if r.lap_basis and r.lap_coefficient is None:
      issues.append(_issue("REBAR_LAP_NEEDS_COEFFICIENT", "error", "A lap basis needs a lap coefficient.", ref))
    stock = r.stock_length_mm or ((r.splice_constraints or {}).get("stock_length_m") and 1)
    if role == "MAIN" and stock and not r.lap_basis:
      issues.append(_issue("REBAR_LAP_RULE_MISSING", "warning", "Stock length is set but no lap rule: long bars cannot get a lap length.", ref))
    for key in ("standard_hook_d_multiple", "stirrup_hook_d_multiple"):
      if key in (r.hook_rules or {}) and _num((r.hook_rules or {})[key]) is None:
        issues.append(_issue("REBAR_HOOK_NOT_NUMERIC", "error", f"hook_rules.{key} must be a number.", ref))
    table = (r.bend_rules or {}).get("deduction_d_multiple")
    
    if table is not None:
      if not isinstance(table, dict) or any(_num(k) is None or _num(v) is None for k, v in table.items()):
        issues.append(_issue("REBAR_BEND_TABLE_INVALID", "error", "bend_rules.deduction_d_multiple must map angle to a number.", ref))
    for field, label in (("stock_length_mm", "Stock length"), ("min_lap_mm", "Minimum lap"), ("cover_mm", "Cover")):
      value = getattr(r, field, None)
      if value is not None and value < 0 or (field == "stock_length_mm" and value is not None and value == 0):
        issues.append(_issue("REBAR_VALUE_INVALID", "error", f"{label} must be positive.", ref))
  return issues