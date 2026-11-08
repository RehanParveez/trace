from __future__ import annotations
from app.modules.drawings_boq.takeoff.ai_reader.contract import PURPOSE
from app.modules.drawings_boq.takeoff.extract import sheet_identity as SI
from app.modules.drawings_boq.takeoff.prep import page_role as PRL

WEAK, ALL = "WEAK", "ALL"
MODES = (WEAK, ALL)

def rule_state(identity: dict | None) -> dict:
  i = identity or {}
  vote = i.get("role_vote") or {}
  return {**{k: i.get(k) for k in ("discipline", "sheet_type", "floor", "title", "sheet_no", "basis", "confidence")}, "role": vote.get("role"), "signals": vote.get("signals") or []}

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

SCHEDULE_TABLES = ("column_schedule", "beam_sections", "finish_specs")

def schedule_page(meta: dict | None) -> bool:
  m = meta or {}
  ident = m.get("identity") or {}
  tables = m.get("structure_tables") or {}
  return (ident.get("role_vote") or {}).get("role") == PRL.SCHEDULE or ident.get("role") == PRL.SCHEDULE or any(tables.get(k) for k in SCHEDULE_TABLES)

def note_page(meta: dict | None) -> bool:
  m = meta or {}
  vote = (m.get("identity") or {}).get("role_vote") or {}
  return vote.get("role") == PRL.NOTES or bool((m.get("facts") or {}).get("items"))
