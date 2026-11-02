from __future__ import annotations
from app.engine.measure import rulebook as RB

WORK_ITEM = "electrical.work_item"
KEYS = (WORK_ITEM,)
NONE = "NONE"
LIGHT, FAN, EXHAUST, SOCKET_5A, SOCKET_15A, SOCKET = "LIGHT", "FAN", "EXHAUST", "SOCKET_5A", "SOCKET_15A", "SOCKET"
SWITCH_PLATE, SWITCH_2WAY, TEL, TV, DATA, ALARM, BELL, CCTV, AUDIO, BOARD, OTHER = "SWITCH_PLATE", "SWITCH_2WAY", "TEL", "TV", "DATA", "ALARM", "BELL", "CCTV", "AUDIO", "BOARD", "OTHER"
GROUPS = (LIGHT, FAN, EXHAUST, SOCKET_5A, SOCKET_15A, SOCKET, SWITCH_PLATE, SWITCH_2WAY, TEL, TV, DATA, ALARM, BELL, CCTV, AUDIO, BOARD, OTHER)
SEED_ITEM = {LIGHT: "ELE-LIGHT", FAN: "ELE-FAN", EXHAUST: "ELE-FAN", SOCKET_5A: "ELE-SOCKET", SOCKET_15A: "ELE-SOCKET", SOCKET: "ELE-SOCKET", SWITCH_PLATE: "ELE-SWITCH", SWITCH_2WAY: "ELE-SWITCH",
  TEL: "ELE-LOWV", TV: "ELE-LOWV", DATA: "ELE-LOWV", ALARM: "ELE-LOWV", BELL: "ELE-LOWV", CCTV: "ELE-LOWV", AUDIO: "ELE-LOWV", BOARD: "ELE-BOARD", OTHER: "ELE-OTHER"}

def _scope_problem(scope) -> str | None:
  scope = scope or {}
  if not isinstance(scope, dict) or any(k != "group" for k in scope):
    return f"{WORK_ITEM} can be scoped by group only."
  if scope.get("group") is not None and scope["group"] not in GROUPS:
    return f"{scope['group']} is not an electrical group: {', '.join(GROUPS)}."
  return None

def checked(key: str, scope, raw):
  if key != WORK_ITEM:
    raise ValueError(f"{key} is not an electrical rule.")
  bad = _scope_problem(scope)
  if bad:
    raise ValueError(bad)
  if not isinstance(raw, str) or not raw.strip():
    raise ValueError("The item of an electrical group is a work item code, or NONE to bill nothing from it.")
  code = raw.strip().upper()
  if not (scope or {}).get("group") and code == NONE:
    raise ValueError("NONE is for one group; it cannot be the item of every group.")
  return code

def work_item(group: str, record: bool = True) -> tuple:
  rv = RB.resolve(WORK_ITEM, {"group": group}, record=record)
  return (str(rv.value) if rv.value is not None else SEED_ITEM.get(group, SEED_ITEM[OTHER])), rv

def evidence(group: str, rv) -> dict:
  return {"key": WORK_ITEM, "scope": {"group": group}, "value": rv.value, "origin": rv.origin, "cls": rv.cls, "rule_id": rv.rule_id, "version": rv.version}

def seed_problems(seed_rows: dict) -> list:
  out: list = []
  rows = {tuple(sorted(scope.items())): rv for scope, rv in seed_rows.get(WORK_ITEM, ())}
  for g in GROUPS:
    rv = rows.get((("group", g),))
    if rv is None:
      out.append((WORK_ITEM, f"group {g} is missing from the seed"))
    elif rv.value != SEED_ITEM[g]:
      out.append((rv.rule_id, f"seed {rv.value!r}, code {SEED_ITEM[g]!r}"))
  for scope, rv in seed_rows.get(WORK_ITEM, ()):
    try:
      checked(WORK_ITEM, scope, rv.value)
    except ValueError as exc:
      out.append((rv.rule_id, str(exc)))
  return out
