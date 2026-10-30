from __future__ import annotations
from app.modules.drawings_boq import rule_book_service as RBS
from app.engine.measure import rulebook as RB
from app.core.exceptions import TraceException
from uuid import UUID

MAX_KEY = 64 - len(RBS.DRAFT_PREFIX)
MAX_UNIT = 24
CLASSES = (RB.PRINTED, RB.STANDARD, RB.JUDGEMENT)

def _refuse(message: str, code: str = "RULE_DRAFT_REFUSED", status: int = 422):
  raise TraceException(message, status_code=status, code=code)

def _held(row) -> dict:
  return row.value if isinstance(row.value, dict) else {}

def _problem_with(key: str, value, scope) -> str | None:
  try:
    RBS.checked_value(key, value, scope)
  except TraceException as exc:
    return exc.message
  except (ValueError, TypeError, KeyError) as exc:
    return f"The value cannot be used for {key}: {exc}."
  return None

def _seed_of(key: str, value, held: dict) -> dict | None:
  if isinstance(held.get("seed"), dict):
    return held["seed"]
  seed = RB.SEED.get(key)
  if seed is None:
    return None
  try:
    same = bool(RBS._same(value, seed.value))
  except Exception:
    same = False
  return {"key": key, "value": seed.value, "same": same}

def _item(row) -> dict:
  held = _held(row)
  key = row.key[len(RBS.DRAFT_PREFIX):]
  value = held.get("value")
  needs = [str(n) for n in held.get("needs") or []]
  problem = None if needs else _problem_with(key, value, row.scope)
  return {"id": str(row.id), "key": key, "scope": dict(row.scope or {}), "value": value, "unit": held.get("unit") or row.unit, "cls": row.cls,
    "source": dict(held.get("source") or {}), "note": row.note, "needs": needs, "seed": _seed_of(key, value, held),
    "confirmable": not needs and problem is None, "why_not": problem, "confirmed_by": None}

async def _drafts(session, org: UUID) -> list:
  book = await RBS.active_book(session, org)
  if book is None:
    return []
  rows = [r for r in await RBS.rules_of(session, book.id, drafts=True) if r.key.startswith(RBS.DRAFT_PREFIX) and r.value is not None]
  return sorted(rows, key=lambda r: (r.key, RBS._scope_key(r.scope)))

async def _draft(session, org: UUID, draft_id: UUID):
  for r in await _drafts(session, org):
    if r.id == draft_id:
      return r
  _refuse("That draft rule no longer exists. Load the list again.", "RULE_DRAFT_NOT_FOUND", 404)

async def list_drafts(session, org: UUID) -> list[dict]:
  return [_item(r) for r in await _drafts(session, org)]

async def import_drafts(session, org: UUID, payload: dict) -> list[dict]:
  changes: list = []
  seen: set = set()
  
  for n, raw in enumerate(payload.get("rules") or [], start=1):
    if not isinstance(raw, dict):
      _refuse(f"Rule {n} is not an object.")
    key = str(raw.get("key") or "").strip()
    if not key or len(key) > MAX_KEY or key.startswith(RBS.DRAFT_PREFIX):
      _refuse(f"Rule {n} needs a key of at most {MAX_KEY} characters that does not start with '{RBS.DRAFT_PREFIX}'.")
    if raw.get("value") is None:
      _refuse(f"Rule {n} ({key}) has no value.")
    scope = raw.get("scope") or {}
    if not isinstance(scope, dict):
      _refuse(f"Rule {n} ({key}) has a scope that is not an object.")
    cls = raw.get("cls") or RB.JUDGEMENT
    if cls not in CLASSES:
      _refuse(f"Rule {n} ({key}) has the class {cls!r}; it must be one of {', '.join(CLASSES)}.")
    ident = (key, RBS._scope_key(scope))
    if ident in seen:
      _refuse(f"Rule {n} repeats {key} with the same scope.")
    seen.add(ident)
    
    source = dict(raw["source"]) if isinstance(raw.get("source"), dict) else {}
    if payload.get("workbook") and not source.get("workbook"):
      source["workbook"] = str(payload["workbook"])
    unit = str(raw["unit"]) if raw.get("unit") else None
    held = {"value": raw["value"], "unit": unit, "source": source, "needs": [str(x) for x in raw.get("needs") or []],
      "seed": dict(raw["seed"]) if isinstance(raw.get("seed"), dict) else None}
    changes.append({"key": RBS.DRAFT_PREFIX + key, "scope": scope, "value": held, "unit": unit[:MAX_UNIT] if unit else None, "cls": cls, "origin": RB.QS_WORKBOOK,
      "note": raw.get("note")})
  if not changes:
    _refuse("The file has no rules.")
  await RBS.publish(session, org, changes, note="Draft rules added" + (f" from {payload['workbook']}" if payload.get("workbook") else "") + "; none is used until confirmed.")
  return await list_drafts(session, org)

async def confirm(session, org: UUID, user_id: UUID, draft_id: UUID, value) -> list[dict]:
  row = await _draft(session, org, draft_id)
  held = _held(row)
  key = row.key[len(RBS.DRAFT_PREFIX):]
  needs = [str(n) for n in held.get("needs") or []]
  
  if needs and value is None:
    _refuse(f"The workbook does not state: {', '.join(needs)}. Type the whole value, with those figures filled in.", "RULE_DRAFT_NEEDS_VALUES")
  chosen = held.get("value") if value is None else value
  checked = RBS.checked_value(key, chosen, row.scope)
  source = held.get("source") or {}
  where = f"{source.get('workbook') or 'workbook'} {source.get('sheet') or '?'}!{source.get('cell') or '?'}"
  note = f"Confirmed by user {user_id} from the draft read from {where}." + (" The figure was typed by the user." if value is not None else "")
  unit = held.get("unit") or row.unit
  scope = dict(row.scope or {})
  await RBS.publish(session, org, [
    {"key": key, "scope": scope, "value": checked, "unit": unit[:MAX_UNIT] if unit else None, "cls": row.cls, "origin": RB.QS_WORKBOOK, "note": note},
    {"key": row.key, "scope": scope, "value": None}], note=note)
  return await list_drafts(session, org)

async def reject(session, org: UUID, draft_id: UUID) -> list[dict]:
  row = await _draft(session, org, draft_id)
  await RBS.publish(session, org, [{"key": row.key, "scope": dict(row.scope or {}), "value": None}], note="A draft rule was thrown away.")
  return await list_drafts(session, org)
