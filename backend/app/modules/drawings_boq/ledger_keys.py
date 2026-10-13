from __future__ import annotations
from uuid import UUID, uuid5

def ledger_id(run_id: UUID, entry) -> UUID:
  stage = getattr(entry, "work_stage", None)
  return uuid5(run_id, f"ledger|{entry.solid_id}|{entry.work_item_code}" + (f"|{stage}" if stage else ""))

def ids_for_keys(run_id: UUID, ledger, keys) -> list[UUID]:
  wanted = set(keys)
  return [ledger_id(run_id, e) for e in ledger if (e.solid_id, e.work_item_code) in wanted]

def restage_plan(run_id: UUID, before: list, result) -> tuple[list[UUID], list]:
  return ids_for_keys(run_id, before, result.replaced), list(result.added)