from __future__ import annotations
from app.modules.drawings_boq.takeoff.ai_reader.contract import PURPOSE
from app.modules.drawings_boq.takeoff.extract import sheet_identity as SI

WEAK, ALL = "WEAK", "ALL"
MODES = (WEAK, ALL)

def rule_state(identity: dict | None) -> dict:
  i = identity or {}
  return {k: i.get(k) for k in ("discipline", "sheet_type", "floor", "title", "sheet_no", "basis", "confidence")}

def needs_reading(identity: dict | None, mode: str) -> bool:
  if mode == ALL:
    return True
  i = identity or {}
  if i.get("basis") == "PERSON":
    return False
  return not i.get("discipline") or not i.get("sheet_type") or float(i.get("confidence") or 0.0) < SI.GATE_TITLE

def plan(identity: dict | None, mode: str) -> dict | None:
  if not needs_reading(identity, mode):
    return None
  return {"purpose": PURPOSE, "rule_state": rule_state(identity)}
